"""
Roadmap endpoint handlers.
"""

from fastapi import APIRouter, Depends
from app.models.requests import RoadmapRequest
from app.models.responses import RoadmapResponse
from app.services.roadmap_service import roadmap_service
from app.core.logging_config import get_logger
from app.api.deps import get_current_user
from app.models.auth import UserResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/roadmap", tags=["Roadmap"])


@router.post(
    "",
    response_model=RoadmapResponse,
    status_code=201,
    summary="Generate Learning Roadmap",
    description="Generate a personalized learning roadmap based on user's goal, experience, and skills.",
    responses={
        201: {"description": "Roadmap generated successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
        503: {"description": "LLM service unavailable"}
    }
)
async def generate_roadmap(
    request: RoadmapRequest,
    current_user: UserResponse = Depends(get_current_user)
) -> RoadmapResponse:
    """
    Generate a personalized learning roadmap.
    
    Creates a structured learning path with tasks, subtasks, and time estimates
    based on the user's goal, current skills, and learning preferences.
    """
    logger.info(
        f"Generating roadmap for goal: {request.goal_title}",
        extra={"extra_fields": {
            "experience": request.experience,
            "known_skills": request.known_skills,
            "learning_style": request.learning_style
        }}
    )
    
    return await roadmap_service.generate_roadmap(request)