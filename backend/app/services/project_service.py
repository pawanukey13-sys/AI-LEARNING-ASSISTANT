"""
Project recommendation service.
Generates project suggestions based on skills or roadmap context.
"""

from typing import Dict, Any, Optional
from cachetools import TTLCache

from app.models.requests import ProjectRequest
from app.models.responses import ProjectResponse
from app.services.llm_service import llm_service
from app.services.roadmap_service import roadmap_service
from app.prompts.templates import PROJECT_SYSTEM_PROMPT, PROJECT_USER_PROMPT
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Cache for project recommendations
_project_cache: TTLCache = TTLCache(maxsize=100, ttl=3600)


class ProjectService:
    """Service for generating project recommendations."""
    
    async def recommend_project(self, request: ProjectRequest) -> ProjectResponse:
        """
        Recommend a project based on roadmap or direct skills input.
        
        Args:
            request: Project request (with roadmap_id OR goal_title + skills)
        
        Returns:
            Project recommendation
        """
        goal_title: str
        skills: list[str]
        
        if request.roadmap_id:
            # Fetch from roadmap
            goal_title, skills = await self._get_from_roadmap(request.roadmap_id)
        else:
            goal_title = request.goal_title or ""
            skills = request.skills or []
        
        # Check cache
        cache_key = f"{goal_title}|{','.join(sorted(skills))}"
        if cache_key in _project_cache:
            logger.info("Returning cached project recommendation")
            return _project_cache[cache_key]
        
        # Generate project using LLM
        prompt = PROJECT_USER_PROMPT.format(
            goal_title=goal_title,
            skills=", ".join(skills)
        )
        
        response = await llm_service.generate_json(
            prompt=prompt,
            response_model=ProjectResponse,
            system_prompt=PROJECT_SYSTEM_PROMPT,
            temperature=0.4
        )
        
        # Cache the response
        _project_cache[cache_key] = response
        
        return response
    
    async def _get_from_roadmap(self, roadmap_id: str) -> tuple[str, list[str]]:
        """Extract goal and skills from a cached roadmap."""
        roadmap = roadmap_service.get_roadmap_from_cache(roadmap_id)
        if roadmap:
            return roadmap.skills[0] if roadmap.skills else "", roadmap.skills
        
        # If not in cache, we need to handle this case
        # For now, raise an error or use defaults
        logger.warning(f"Roadmap {roadmap_id} not in cache, using fallback")
        return "Developer", ["Python"]


# Singleton instance
project_service = ProjectService()