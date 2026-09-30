"""
Integration tests for JWT Cookie Authentication system.
"""

import pytest
from httpx import AsyncClient
from app.main import app
from app.core.mock_db import fake_users_db


@pytest.fixture(autouse=True)
def clean_fake_db():
    """Clear the fake user database before each test to ensure test isolation."""
    fake_users_db.clear()
    yield
    fake_users_db.clear()


@pytest.mark.asyncio
async def test_register_success():
    """POST /api/v1/auth/register should create user and return HTTP-only cookie."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "username": "testuser",
            "password": "password123"
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        
        # Assert status code is 201 Created or 200 OK
        assert response.status_code in (200, 201)
        
        # Assert set-cookie header is present and contains access_token and httponly
        assert "set-cookie" in response.headers
        set_cookie_header = response.headers["set-cookie"]
        assert "access_token" in set_cookie_header
        assert "httponly" in set_cookie_header.lower()


@pytest.mark.asyncio
async def test_login_success():
    """POST /api/v1/auth/login should authenticate credentials and set cookie."""
    # Pre-register user in fake database
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First register
        reg_payload = {
            "username": "testuser",
            "password": "password123"
        }
        await client.post("/api/v1/auth/register", json=reg_payload)
        
        # Clear client cookies to test clean login
        client.cookies.clear()
        
        # Login
        response = await client.post("/api/v1/auth/login", json=reg_payload)
        assert response.status_code == 200
        
        # Assert set-cookie header is present
        assert "set-cookie" in response.headers
        assert "access_token" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_protected_route_without_cookie_returns_401():
    """Making request to a protected endpoint without cookie should return 401."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        dummy_roadmap_request = {
            "goal_title": "Backend Developer",
            "experience": "Less than 1 year",
            "known_skills": ["Python"],
            "learning_style": "Project Based",
            "weekly_hours": 15
        }
        
        response = await client.post("/api/v1/roadmap", json=dummy_roadmap_request)
        
        # Assert status code is 401 Unauthorized or 403 Forbidden
        assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_protected_route_with_invalid_cookie_returns_401():
    """Making request to a protected endpoint with an invalid cookie should return 401."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        dummy_roadmap_request = {
            "goal_title": "Backend Developer",
            "experience": "Less than 1 year",
            "known_skills": ["Python"],
            "learning_style": "Project Based",
            "weekly_hours": 15
        }
        
        # Explicitly pass a fake invalid cookie
        response = await client.post(
            "/api/v1/roadmap",
            json=dummy_roadmap_request,
            cookies={"access_token": "invalid.token.here"}
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookie():
    """POST /api/v1/auth/logout should clear the access token cookie."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Pre-login (register) to get valid cookie
        payload = {
            "username": "testuser",
            "password": "password123"
        }
        await client.post("/api/v1/auth/register", json=payload)
        
        # Call logout
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        
        # Assert response contains set-cookie that deletes/expires cookie (value empty or max-age=0 or expires in past)
        assert "set-cookie" in response.headers
        set_cookie = response.headers["set-cookie"]
        assert "access_token" in set_cookie
        # Standard deletion signs: either empty value ("access_token="), max-age=0, or "expires="
        assert 'max-age=0' in set_cookie.lower() or 'expires=' in set_cookie.lower() or 'access_token=;' in set_cookie
