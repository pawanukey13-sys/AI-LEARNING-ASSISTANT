"""
Main API router that combines all endpoint routers.
"""

from fastapi import APIRouter
from app.api.endpoints import roadmap, project, chat, auth

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(roadmap.router)
api_router.include_router(project.router)
api_router.include_router(chat.router)