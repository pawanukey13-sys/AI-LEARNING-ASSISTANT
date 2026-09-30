"""
Pydantic request models with comprehensive validation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re


class RoadmapRequest(BaseModel):
    """Request model for generating a learning roadmap."""
    
    goal_title: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="The career goal or role the user wants to achieve",
        examples=["Backend Developer", "ML Engineer", "Full Stack Developer"]
    )
    
    experience: str = Field(
        ...,
        description="Current experience level",
        examples=["Less than 1 year", "1-3 years", "3-5 years", "5+ years"]
    )
    
    known_skills: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of skills the user already knows"
    )
    
    learning_style: str = Field(
        ...,
        description="Preferred learning approach",
        examples=["Project Based", "Theory First", "Hybrid", "Video Tutorials"]
    )
    
    weekly_hours: int = Field(
        ...,
        ge=1,
        le=80,
        description="Hours available per week for learning"
    )
    
    @field_validator("goal_title")
    @classmethod
    def validate_goal_title(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r'^[a-zA-Z\s\-]+$', v):
            raise ValueError("Goal title should contain only letters, spaces, and hyphens")
        return v
    
    @field_validator("known_skills", mode="before")
    @classmethod
    def clean_skills(cls, v: List[str]) -> List[str]:
        return [skill.strip().title() for skill in v if skill.strip()]
    
    @field_validator("experience")
    @classmethod
    def validate_experience(cls, v: str) -> str:
        valid_levels = [
            "less than 1 year", "1-3 years", "3-5 years", "5+ years",
            "no experience", "beginner", "intermediate", "advanced"
        ]
        v_lower = v.lower().strip()
        for level in valid_levels:
            if level in v_lower or v_lower in level:
                return v.strip()
        return v.strip()


class ProjectRequest(BaseModel):
    """Request model for project recommendation."""
    
    roadmap_id: Optional[str] = Field(
        None,
        description="UUID of a previously generated roadmap"
    )
    
    goal_title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="Career goal (used if roadmap_id not provided)"
    )
    
    skills: Optional[List[str]] = Field(
        None,
        min_length=1,
        max_length=20,
        description="Skills to incorporate (used if roadmap_id not provided)"
    )
    
    @field_validator("roadmap_id", mode="before")
    @classmethod
    def normalize_roadmap_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                return None
            return v_stripped
        return v
        
    @field_validator("skills", mode="before")
    @classmethod
    def clean_skills(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [skill.strip().title() for skill in v if skill.strip()]
    
    @model_validator(mode='after')
    def validate_request_pattern(self) -> 'ProjectRequest':
        """Pydantic v2 model validator to enforce XOR logic cleanly."""
        if self.roadmap_id is None and not (self.goal_title and self.skills):
            raise ValueError("Either 'roadmap_id' OR both 'goal_title' and 'skills' must be provided")
        return self


class ChatRequest(BaseModel):
    """Request model for AI chat with RAG."""
    
    roadmap_id: str = Field(
        ...,
        description="UUID of the roadmap context for this conversation"
    )
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's question or message"
    )
    
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID for maintaining context"
    )
    
    stream: bool = Field(
        default=False,
        description="Whether to stream the response"
    )
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Message cannot be empty")
        return v