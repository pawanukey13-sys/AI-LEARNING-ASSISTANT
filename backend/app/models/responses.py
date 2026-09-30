"""
Pydantic response models with detailed typing.
Provides clear API documentation and type safety.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


# ============ Roadmap Responses ============

class SubTask(BaseModel):
    """A subtask within a learning task."""
    title: str = Field(..., description="Subtask title")
    description: Optional[str] = Field(None, description="Brief description of the subtask")
    resources: Optional[List[str]] = Field(None, description="Learning resources for this subtask")


class Task(BaseModel):
    """A learning task in the roadmap."""
    title: str = Field(..., description="Task title")
    estimated_hours: int = Field(..., ge=1, description="Estimated hours to complete")
    subtasks: List[SubTask] = Field(default_factory=list, description="List of subtasks")
    priority: Optional[str] = Field(None, description="Priority level: High, Medium, Low")


class RoadmapResponse(BaseModel):
    """Response model for roadmap generation."""
    roadmap_id: str = Field(..., description="Unique identifier for the roadmap")
    estimated_hours: int = Field(..., ge=1, description="Total estimated hours")
    skills: List[str] = Field(..., description="Skills covered in this roadmap")
    tasks: List[Task] = Field(..., description="List of learning tasks")
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "roadmap_id": "550e8400-e29b-41d4-a716-446655440000",
                "estimated_hours": 120,
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                "tasks": [{
                    "title": "Learn FastAPI",
                    "estimated_hours": 12,
                    "subtasks": [{"title": "Routing"}],
                    "priority": "High"
                }]
            }]
        }
    }


# ============ Project Responses ============

class ProjectResponse(BaseModel):
    """Response model for project recommendation."""
    title: str = Field(..., description="Project title")
    difficulty: str = Field(..., description="Difficulty level: Beginner, Intermediate, Advanced")
    estimated_hours: int = Field(..., ge=1, description="Estimated hours to complete")
    tech_stack: List[str] = Field(..., description="Technologies used")
    features: List[str] = Field(..., description="Key features to implement")
    why_this_project: str = Field(..., description="Explanation of why this project is recommended")
    learning_outcomes: Optional[List[str]] = Field(
        None, 
        description="Skills that will be learned/practiced"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "title": "Task Management API",
                "difficulty": "Intermediate",
                "estimated_hours": 20,
                "tech_stack": ["FastAPI", "PostgreSQL", "Docker"],
                "features": ["JWT Authentication", "CRUD APIs", "Pagination"],
                "why_this_project": "Helps practice REST API development.",
                "learning_outcomes": ["REST API Design", "Database Operations"]
            }]
        }
    }


# ============ Chat Responses ============

class ChatResponse(BaseModel):
    """Response model for AI chat."""
    response: str = Field(..., description="AI response to the user's question")
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions"
    )
    sources: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Source chunks used for RAG response"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="ID for continuing this conversation"
    )


class ChatStreamChunk(BaseModel):
    """Single chunk for streaming responses."""
    type: str = Field(..., description="Chunk type: 'content', 'follow_up', 'done', 'error'")
    content: Optional[str] = Field(None, description="Content for this chunk")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# ============ Error Responses ============

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: Dict[str, Any] = Field(..., description="Error details")


# ============ Health Check ============

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    services: Dict[str, str] = Field(..., description="Status of dependent services")


# ============ LLM Parsing / Intermediary Responses ============

class RoadmapLLMResponse(BaseModel):
    """Intermediate Pydantic model for validating raw LLM roadmap output."""
    estimated_hours: int = Field(..., ge=1)
    skills: List[str] = Field(...)
    tasks: List[Task] = Field(...)


class ChatLLMResponse(BaseModel):
    """Intermediate Pydantic model for validating raw LLM chat output."""
    response: str = Field(...)
    follow_up_questions: List[str] = Field(default_factory=list)