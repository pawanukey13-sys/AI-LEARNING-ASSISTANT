"""
Roadmap generation service.
Orchestrates LLM calls, vector indexing, and caching.
"""

from typing import Dict, Any
from uuid import uuid4
from cachetools import TTLCache

from app.models.requests import RoadmapRequest
from app.models.responses import RoadmapResponse, Task, SubTask, RoadmapLLMResponse
from app.services.llm_service import llm_service
from app.services.vector_store import vector_store
from app.prompts.templates import ROADMAP_SYSTEM_PROMPT, ROADMAP_USER_PROMPT
from app.core.exceptions import LLMResponseParsingError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# In-memory cache for roadmaps (TTL: 1 hour)
_roadmap_cache: TTLCache = TTLCache(maxsize=100, ttl=3600)


class RoadmapService:
    """Service for generating and managing learning roadmaps."""
    
    async def generate_roadmap(self, request: RoadmapRequest) -> RoadmapResponse:
        """
        Generate a personalized learning roadmap.
        
        Args:
            request: Validated roadmap request
        
        Returns:
            Generated roadmap with unique ID
        """
        # Check cache first
        cache_key = self._get_cache_key(request)
        if cache_key in _roadmap_cache:
            logger.info(f"Returning cached roadmap for {request.goal_title}")
            return _roadmap_cache[cache_key]
        
        # Generate roadmap using LLM
        prompt = ROADMAP_USER_PROMPT.format(
            goal_title=request.goal_title,
            experience=request.experience,
            known_skills=", ".join(request.known_skills),
            learning_style=request.learning_style,
            weekly_hours=request.weekly_hours
        )
        
        raw_response = await llm_service.generate_json(
            prompt=prompt,
            response_model=RoadmapLLMResponse,
            system_prompt=ROADMAP_SYSTEM_PROMPT,
            temperature=0.3
        )
        
        # Generate unique ID
        roadmap_id = str(uuid4())
        
        # Build response
        response = self._build_response(roadmap_id, raw_response, request)
        
        # Store full data for RAG indexing
        full_data = {
            "roadmap_id": roadmap_id,
            "goal_title": request.goal_title,
            "experience": request.experience,
            "known_skills": request.known_skills,
            "learning_style": request.learning_style,
            "weekly_hours": request.weekly_hours,
            "estimated_hours": response.estimated_hours,
            "skills": response.skills,
            "tasks": [task.model_dump() for task in response.tasks]
        }
        
        # Index for RAG (async, don't block response)
        try:
            chunk_count = await vector_store.index_roadmap(roadmap_id, full_data)
            logger.info(f"Indexed {chunk_count} chunks for roadmap {roadmap_id}")
        except Exception as e:
            logger.error(f"Failed to index roadmap: {e}")
            # Don't fail the request if indexing fails
        
        # Cache the response
        _roadmap_cache[cache_key] = response
        
        return response
    
    def _build_response(
        self, 
        roadmap_id: str, 
        data: RoadmapLLMResponse,
        request: RoadmapRequest
    ) -> RoadmapResponse:
        """Build Pydantic response from LLM data."""
        tasks = []
        for task_data in data.tasks:
            subtasks = []
            for subtask_data in task_data.subtasks:
                subtasks.append(SubTask(
                    title=subtask_data.title,
                    description=subtask_data.description,
                    resources=subtask_data.resources
                ))
            
            tasks.append(Task(
                title=task_data.title,
                estimated_hours=task_data.estimated_hours,
                subtasks=subtasks,
                priority=task_data.priority
            ))
        
        return RoadmapResponse(
            roadmap_id=roadmap_id,
            estimated_hours=data.estimated_hours,
            skills=data.skills,
            tasks=tasks
        )
    
    def _get_cache_key(self, request: RoadmapRequest) -> str:
        """Generate cache key from request parameters."""
        skills_str = ",".join(sorted(request.known_skills))
        return f"{request.goal_title}|{request.experience}|{skills_str}|{request.learning_style}|{request.weekly_hours}"
    
    def get_roadmap_from_cache(self, roadmap_id: str) -> RoadmapResponse | None:
        """Retrieve a roadmap from cache by ID."""
        for cached in _roadmap_cache.values():
            if cached.roadmap_id == roadmap_id:
                return cached
        return None


# Singleton instance
roadmap_service = RoadmapService()