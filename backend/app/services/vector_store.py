"""
Vector Store service using ChromaDB.
Manages document storage, retrieval, and similarity search for RAG.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.core.exceptions import VectorStoreError, RoadmapNotFoundError
from app.core.logging_config import get_logger
from app.services.embedding_service import embedding_service

logger = get_logger(__name__)


class VectorStoreService:
    """
    Vector database service for RAG pipeline.
    
    Uses ChromaDB for persistent vector storage with BGE-M3 embeddings.
    Implements semantic chunking and metadata-based filtering.
    """
    
    def __init__(self) -> None:
        self.persist_directory = settings.storage_path
        self.collection_name = settings.collection_name
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection: Optional[chromadb.Collection] = None
    
    def _get_client(self) -> chromadb.ClientAPI:
        """Get or create ChromaDB client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        return self._client
    
    def _get_collection(self) -> chromadb.Collection:
        """Get or create the roadmap collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection
    
    async def index_roadmap(
        self,
        roadmap_id: str,
        roadmap_data: Dict[str, Any]
    ) -> int:
        """
        Index a roadmap for RAG retrieval.
        
        Implements semantic chunking strategy:
        1. Create overview chunk with full context
        2. Create skill-specific chunks
        3. Create task-level chunks with details
        
        Args:
            roadmap_id: Unique roadmap identifier
            roadmap_data: Full roadmap data to index
        
        Returns:
            Number of chunks indexed
        """
        chunks = []
        metadatas = []
        ids = []
        
        # Chunk 1: Overview
        overview_text = self._create_overview_chunk(roadmap_id, roadmap_data)
        chunks.append(overview_text)
        metadatas.append({
            "roadmap_id": roadmap_id,
            "chunk_type": "overview",
            "goal_title": roadmap_data.get("goal_title", "")
        })
        ids.append(f"{roadmap_id}_overview")
        
        # Chunk 2: Skills
        skills_text = self._create_skills_chunk(roadmap_id, roadmap_data)
        chunks.append(skills_text)
        metadatas.append({
            "roadmap_id": roadmap_id,
            "chunk_type": "skills",
            "goal_title": roadmap_data.get("goal_title", "")
        })
        ids.append(f"{roadmap_id}_skills")
        
        # Chunks 3+: Tasks and subtasks
        for i, task in enumerate(roadmap_data.get("tasks", [])):
            task_text = self._create_task_chunk(roadmap_id, task, i)
            chunks.append(task_text)
            metadatas.append({
                "roadmap_id": roadmap_id,
                "chunk_type": "task",
                "task_title": task.get("title", ""),
                "task_index": i,
                "goal_title": roadmap_data.get("goal_title", "")
            })
            ids.append(f"{roadmap_id}_task_{i}")
            
            # Subtask chunks for fine-grained retrieval
            for j, subtask in enumerate(task.get("subtasks", [])):
                subtask_text = self._create_subtask_chunk(
                    roadmap_id, task, subtask, i, j
                )
                chunks.append(subtask_text)
                metadatas.append({
                    "roadmap_id": roadmap_id,
                    "chunk_type": "subtask",
                    "task_title": task.get("title", ""),
                    "subtask_title": subtask.get("title", ""),
                    "task_index": i,
                    "subtask_index": j,
                    "goal_title": roadmap_data.get("goal_title", "")
                })
                ids.append(f"{roadmap_id}_subtask_{i}_{j}")
        
        # Generate embeddings
        embeddings = await embedding_service.embed_batch(chunks)
        
        # Store in ChromaDB
        collection = self._get_collection()
        
        # Delete existing chunks for this roadmap (for updates)
        try:
            collection.delete(where={"roadmap_id": roadmap_id})
        except Exception:
            pass  # No existing data to delete
        
        # Add new chunks
        if chunks:
            collection.add(
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
        
        logger.info(
            f"Indexed {len(chunks)} chunks for roadmap {roadmap_id}",
            extra={"extra_fields": {
                "roadmap_id": roadmap_id,
                "chunk_count": len(chunks)
            }}
        )
        
        return len(chunks)
    
    async def search(
        self,
        roadmap_id: str,
        query: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks within a specific roadmap.
        
        Uses metadata filtering to ensure results are from the
        correct roadmap context.
        
        Args:
            roadmap_id: Roadmap to search within
            query: Search query
            n_results: Number of results to return
        
        Returns:
            List of relevant chunks with metadata and scores
        """
        collection = self._get_collection()
        
        # Check if roadmap exists
        existing = collection.get(
            where={"roadmap_id": roadmap_id},
            limit=1
        )
        if not existing["ids"]:
            raise RoadmapNotFoundError(roadmap_id)
        
        # Generate query embedding
        query_embedding = await embedding_service.embed_query(query)
        
        # Search with roadmap filter
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, 10),
            where={"roadmap_id": roadmap_id},
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                formatted_results.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1 - results["distances"][0][i] if results["distances"] else 0
                })
        
        logger.info(
            f"Search completed for roadmap {roadmap_id}",
            extra={"extra_fields": {
                "query": query[:100],
                "results_count": len(formatted_results)
            }}
        )
        
        return formatted_results
    
    def delete_roadmap(self, roadmap_id: str) -> bool:
        """Delete all chunks for a roadmap."""
        collection = self._get_collection()
        try:
            collection.delete(where={"roadmap_id": roadmap_id})
            logger.info(f"Deleted all chunks for roadmap {roadmap_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete roadmap chunks: {e}")
            return False
    
    def _create_overview_chunk(self, roadmap_id: str, data: Dict) -> str:
        """Create overview chunk with full context."""
        skills = ", ".join(data.get("skills", []))
        return f"""Learning Roadmap Overview
Goal: {data.get('goal_title', '')}
Experience Level: {data.get('experience', '')}
Known Skills: {data.get('known_skills', [])}
Target Skills: {skills}
Total Estimated Hours: {data.get('estimated_hours', 0)}
Learning Style: {data.get('learning_style', '')}
Weekly Hours Available: {data.get('weekly_hours', 0)}
Number of Tasks: {len(data.get('tasks', []))}"""
    
    def _create_skills_chunk(self, roadmap_id: str, data: Dict) -> str:
        """Create skills-focused chunk."""
        skills = data.get("skills", [])
        known = data.get("known_skills", [])
        new_skills = [s for s in skills if s not in known]
        
        return f"""Skills for {data.get('goal_title', '')} Roadmap
Already Known: {', '.join(known)}
Skills to Learn: {', '.join(new_skills)}
All Required Skills: {', '.join(skills)}
The learning path progresses from known skills to new skills, building upon existing knowledge."""
    
    def _create_task_chunk(self, roadmap_id: str, task: Dict, index: int) -> str:
        """Create task-level chunk."""
        subtasks = task.get("subtasks", [])
        subtask_list = "\n".join([f"  - {st.get('title', '')}" for st in subtasks])
        
        return f"""Task {index + 1}: {task.get('title', '')}
Estimated Hours: {task.get('estimated_hours', 0)}
Priority: {task.get('priority', 'Medium')}
Subtasks:
{subtask_list}
This task is part of the learning roadmap and should be completed to progress to the next stage."""
    
    def _create_subtask_chunk(
        self, roadmap_id: str, task: Dict, subtask: Dict, task_idx: int, subtask_idx: int
    ) -> str:
        """Create fine-grained subtask chunk."""
        resources = subtask.get("resources", [])
        resource_text = ""
        if resources:
            resource_text = f"\nResources: {', '.join(resources)}"
        
        return f"""Subtask: {subtask.get('title', '')}
Part of Task: {task.get('title', '')}
Description: {subtask.get('description', 'No description')}{resource_text}
Focus on understanding and practicing this specific concept before moving to the next subtask."""


# Singleton instance
vector_store = VectorStoreService()