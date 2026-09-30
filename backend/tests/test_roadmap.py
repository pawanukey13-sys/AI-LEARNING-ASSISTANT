"""
Tests for roadmap generation endpoint.
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
def valid_roadmap_request():
    return {
        "goal_title": "Backend Developer",
        "experience": "Less than 1 year",
        "known_skills": ["Python", "SQL"],
        "learning_style": "Project Based",
        "weekly_hours": 15
    }


@pytest.mark.asyncio
async def test_roadmap_valid_request(valid_roadmap_request):
    """Test successful roadmap generation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/roadmap",
            json=valid_roadmap_request
        )
    
    assert response.status_code == 201
    data = response.json()
    assert "roadmap_id" in data
    assert "estimated_hours" in data
    assert "skills" in data
    assert "tasks" in data
    assert isinstance(data["tasks"], list)
    assert len(data["tasks"]) > 0


@pytest.mark.asyncio
async def test_roadmap_missing_required_field():
    """Test validation error when required field is missing."""
    invalid_request = {
        "goal_title": "Backend Developer",
        # Missing: experience, known_skills, learning_style, weekly_hours
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/roadmap",
            json=invalid_request
        )
    
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_roadmap_invalid_weekly_hours():
    """Test validation error for invalid weekly hours."""
    invalid_request = {
        "goal_title": "Backend Developer",
        "experience": "Less than 1 year",
        "known_skills": ["Python"],
        "learning_style": "Project Based",
        "weekly_hours": 100  # Exceeds max of 80
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/roadmap",
            json=invalid_request
        )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_roadmap_empty_known_skills():
    """Test validation error for empty known skills."""
    invalid_request = {
        "goal_title": "Backend Developer",
        "experience": "Less than 1 year",
        "known_skills": [],
        "learning_style": "Project Based",
        "weekly_hours": 15
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/roadmap",
            json=invalid_request
        )
    
    assert response.status_code == 422