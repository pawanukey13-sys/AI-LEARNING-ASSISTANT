"""
Tests for project recommendation endpoint.
Covers both request patterns: roadmap_id based and direct skill based.
"""

import pytest
from httpx import AsyncClient
from app.main import app


class TestProjectEndpointWithRoadmapId:
    """Tests for project recommendation using roadmap_id."""

    @pytest.mark.asyncio
    async def test_project_with_roadmap_id_format(self):
        """Test that roadmap_id request format is valid."""
        request_body = {
            "roadmap_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # With mocked LLM, missing roadmap in cache falls back to defaults
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_project_with_invalid_uuid_format(self):
        """Test handling of invalid UUID format for roadmap_id."""
        request_body = {
            "roadmap_id": "not-a-valid-uuid"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_project_with_empty_roadmap_id(self):
        """Test that empty string roadmap_id is normalized to None and fails validation."""
        request_body = {
            "roadmap_id": ""
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # Empty string gets normalized to None, and since goal_title and skills are missing, validation fails.
        assert response.status_code == 422


class TestProjectEndpointWithDirectSkills:
    """Tests for project recommendation using goal_title and skills directly."""

    @pytest.mark.asyncio
    async def test_project_with_goal_and_skills(self):
        """Test valid request with goal_title and skills array."""
        request_body = {
            "goal_title": "Backend Developer",
            "skills": ["Python", "FastAPI", "SQL"]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # Mocked LLM ensures this succeeds
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_project_with_single_skill(self):
        """Test request with only one skill."""
        request_body = {
            "goal_title": "Frontend Developer",
            "skills": ["React"]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_project_with_many_skills(self):
        """Test request with maximum allowed skills (20)."""
        skills = [f"Skill{i}" for i in range(20)]
        request_body = {
            "goal_title": "Full Stack Developer",
            "skills": skills
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_project_with_too_many_skills(self):
        """Test validation error when exceeding max skills (20)."""
        skills = [f"Skill{i}" for i in range(21)]  # 21 skills
        request_body = {
            "goal_title": "Full Stack Developer",
            "skills": skills
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_project_with_empty_skills_array(self):
        """Test validation when skills array is empty."""
        request_body = {
            "goal_title": "Backend Developer",
            "skills": []
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # Empty skills should fail min_length validation
        assert response.status_code == 422


class TestProjectEndpointValidationErrors:
    """Tests for validation error cases."""

    @pytest.mark.asyncio
    async def test_project_missing_all_fields(self):
        """Test error when neither roadmap_id nor goal_title+skills provided."""
        request_body = {}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # Now cleanly returns 422 due to Pydantic model_validator
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_project_only_goal_title(self):
        """Test error when only goal_title is provided without skills."""
        request_body = {
            "goal_title": "Backend Developer"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # Clean 422
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_project_only_skills(self):
        """Test error when only skills are provided without goal_title."""
        request_body = {
            "skills": ["Python", "FastAPI"]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # Clean 422
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_project_short_goal_title(self):
        """Test validation error for goal_title that's too short."""
        request_body = {
            "goal_title": "AB",  # Less than min_length of 3
            "skills": ["Python"]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "goal_title" in str(data)

    @pytest.mark.asyncio
    async def test_project_long_goal_title(self):
        """Test validation error for goal_title that's too long."""
        long_title = "A" * 101  # More than max_length of 100
        request_body = {
            "goal_title": long_title,
            "skills": ["Python"]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_project_with_null_values(self):
        """Test handling of explicit null values."""
        request_body = {
            "roadmap_id": None,
            "goal_title": None,
            "skills": None
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # Now cleanly returns 422 due to Pydantic model_validator
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_project_with_extra_fields(self):
        """Test that extra fields are ignored (not cause errors)."""
        request_body = {
            "goal_title": "Backend Developer",
            "skills": ["Python", "FastAPI"],
            "extra_field": "should be ignored",
            "another_extra": 123
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # Extra fields should be ignored, not cause errors
        assert response.status_code == 200


class TestProjectEndpointSkillNormalization:
    """Tests for skill name normalization/cleaning."""

    @pytest.mark.asyncio
    async def test_project_skills_are_normalized(self):
        """Test that skill names are properly normalized."""
        request_body = {
            "goal_title": "Backend Developer",
            "skills": ["  python  ", "  FASTAPI  ", "sql  "]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_project_empty_skill_strings_filtered(self):
        """Test that empty skill strings are filtered out."""
        request_body = {
            "goal_title": "Backend Developer",
            "skills": ["Python", "", "  ", "FastAPI"]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # Empty strings are filtered, but "Python" and "FastAPI" remain, so it passes
        assert response.status_code == 200


class TestProjectEndpointResponseStructure:
    """Tests for response structure when request succeeds."""

    @pytest.mark.asyncio
    async def test_project_response_structure(self):
        """Test that successful response has correct structure."""
        request_body = {
            "goal_title": "Backend Developer",
            "skills": ["Python", "FastAPI", "PostgreSQL"]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "title" in data
        assert "difficulty" in data
        assert "estimated_hours" in data
        assert "tech_stack" in data
        assert "features" in data
        assert "why_this_project" in data
        
        # Verify types
        assert isinstance(data["title"], str)
        assert isinstance(data["difficulty"], str)
        assert isinstance(data["estimated_hours"], int)
        assert isinstance(data["tech_stack"], list)
        assert isinstance(data["features"], list)
        assert isinstance(data["why_this_project"], str)
        
        # Verify difficulty is valid
        assert data["difficulty"] in ["Beginner", "Intermediate", "Advanced"]
        
        # Verify estimated hours is positive
        assert data["estimated_hours"] > 0
        
        # Verify tech_stack and features are not empty
        assert len(data["tech_stack"]) > 0
        assert len(data["features"]) > 0


class TestProjectEndpointBothPatterns:
    """Tests for when both patterns are provided."""

    @pytest.mark.asyncio
    async def test_project_both_patterns_roadmap_priority(self):
        """Test that when both patterns provided, one takes priority."""
        request_body = {
            "roadmap_id": "550e8400-e29b-41d4-a716-446655440000",
            "goal_title": "Backend Developer",
            "skills": ["Python", "FastAPI"]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 200


class TestProjectEndpointEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_project_special_characters_in_goal(self):
        """Test handling of special characters in goal_title."""
        request_body = {
            "goal_title": "Backend Developer (Senior Level)",
            "skills": ["Python"]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_project_unicode_in_skills(self):
        """Test handling of unicode characters in skills."""
        request_body = {
            "goal_title": "Backend Developer",
            "skills": ["Python", "机器学习"]  # Chinese for Machine Learning
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_project_duplicate_skills(self):
        """Test handling of duplicate skills in array."""
        request_body = {
            "goal_title": "Backend Developer",
            "skills": ["Python", "Python", "FastAPI", "python"]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # With mocked LLM, this is accepted successfully
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_project_very_long_skill_name(self):
        """Test handling of very long skill name."""
        long_skill = "A" * 100
        request_body = {
            "goal_title": "Backend Developer",
            "skills": [long_skill]
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json=request_body
            )
        
        # Accepted because there's no max_length on individual skill strings
        assert response.status_code == 200