"""
Project recommendation endpoint handlers.
"""

from fastapi import APIRouter, Depends
from app.models.requests import ProjectRequest
from app.models.responses import ProjectResponse
from app.services.project_service import project_service
from app.core.logging_config import get_logger
from app.api.deps import get_current_user
from app.models.auth import UserResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/project", tags=["Project"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=200,
    summary="Recommend a Project",
    description="Get a personalized project recommendation based on a roadmap or specific skills.",
    responses={
        200: {"description": "Project recommendation generated"},
        401: {"description": "Not authenticated"},
        404: {"description": "Roadmap not found"},
        422: {"description": "Validation error"}
    }
)
async def recommend_project(
    request: ProjectRequest,
    current_user: UserResponse = Depends(get_current_user)
) -> ProjectResponse:
    """
    Recommend a practical project.
    
    Can be used in two ways:
    1. Provide a roadmap_id to get a project based on that roadmap
    2. Provide goal_title and skills directly for a standalone recommendation
    """
    # NOTE: Validation is now handled automatically by Pydantic's model_validator in requests.py!
    
    logger.info(
        "Generating project recommendation",
        extra={"extra_fields": {
            "roadmap_id": request.roadmap_id,
            "goal_title": request.goal_title,
            "skills_count": len(request.skills) if request.skills else 0
        }}
    )
    
    return await project_service.recommend_project(request)