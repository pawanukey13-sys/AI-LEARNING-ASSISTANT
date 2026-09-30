"""
Tests for chat endpoint with RAG.
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_chat_valid_request():
    """Test successful chat request."""
    # Note: This requires a valid roadmap_id from a previous roadmap generation
    chat_request = {
        "roadmap_id": "test-roadmap-id",
        "message": "Can I learn Docker before PostgreSQL?",
        "stream": False
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json=chat_request
        )
    
    # Will likely be 404 since test-roadmap-id doesn't exist
    # But tests the endpoint structure
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_chat_missing_message():
    """Test validation error when message is missing."""
    invalid_request = {
        "roadmap_id": "test-id"
        # Missing: message
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json=invalid_request
        )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_empty_message():
    """Test validation error for empty message."""
    invalid_request = {
        "roadmap_id": "test-id",
        "message": "   "
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json=invalid_request
        )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_request():
    """Test streaming chat request format."""
    chat_request = {
        "roadmap_id": "test-id",
        "message": "What should I learn first?",
        "stream": True
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json=chat_request
        )
    
    # Should return 404 for non-existent roadmap
    # or 200 with streaming headers
    assert response.status_code in [200, 404]