"""
Shared test configuration and fixtures.
Mocks external LLM calls so tests run fast and don't require Ollama.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.main import app


# --- Mock Data Generators ---

def get_mock_roadmap_response():
    """Returns a valid mock roadmap response."""
    from app.models.responses import RoadmapResponse, Task, SubTask
    return RoadmapResponse(
        roadmap_id="test-uuid-1234",
        estimated_hours=120,
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        tasks=[
            Task(
                title="Learn FastAPI",
                estimated_hours=12,
                subtasks=[SubTask(title="Routing")],
                priority="High"
            )
        ]
    )

def get_mock_project_response():
    """Returns a valid mock project response."""
    from app.models.responses import ProjectResponse
    return ProjectResponse(
        title="Task Management API",
        difficulty="Intermediate",
        estimated_hours=20,
        tech_stack=["FastAPI", "PostgreSQL", "Docker"],
        features=["JWT Authentication", "CRUD APIs", "Pagination"],
        why_this_project="Helps practice REST API development.",
        learning_outcomes=["REST API Design"]
    )

def get_mock_chat_response():
    """Returns a valid mock chat response."""
    from app.models.responses import ChatResponse
    return ChatResponse(
        response="Yes. Docker can be learned before PostgreSQL.",
        follow_up_questions=["Would you like a suggested order?"],
        sources=[{"type": "task", "score": 0.95}],
        conversation_id="conv-uuid-1234"
    )


# --- Fixtures ---

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "no_mock_llm: Opt out of automatic LLM service mocking for testing production parser logic.")


@pytest.fixture(autouse=True)
def mock_llm_services(request):
    """
    Automatically mock all external LLM and Embedding calls for every test
    except when marked with 'no_mock_llm' to let tests verify real parsing logic.
    """
    if "no_mock_llm" in request.keywords:
        yield
        return

    from unittest.mock import AsyncMock, patch
    from app.models.responses import ProjectResponse, RoadmapLLMResponse, ChatLLMResponse, Task, SubTask
    
    async def mock_generate_json(prompt, response_model, system_prompt=None, temperature=0.3):
        if response_model == RoadmapLLMResponse:
            return RoadmapLLMResponse(
                estimated_hours=120,
                skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
                tasks=[
                    Task(
                        title="Learn FastAPI",
                        estimated_hours=12,
                        subtasks=[SubTask(title="Routing", description="Learn path params", resources=["FastAPI docs"])],
                        priority="High"
                    )
                ]
            )
        elif response_model == ProjectResponse:
            return ProjectResponse(
                title="Task Management API",
                difficulty="Intermediate",
                estimated_hours=20,
                tech_stack=["FastAPI", "PostgreSQL", "Docker"],
                features=["JWT Authentication", "CRUD APIs", "Pagination"],
                why_this_project="Helps practice REST API development.",
                learning_outcomes=["REST API Design"]
            )
        elif response_model == ChatLLMResponse:
            return ChatLLMResponse(
                response="Yes. Docker can be learned before PostgreSQL.",
                follow_up_questions=["Would you like a suggested order?"]
            )
        raise ValueError(f"Unknown response_model in mock: {response_model}")

    async def mock_generate_stream(prompt, system_prompt=None, temperature=0.7):
        json_str = '{"response": "Yes. Docker can be learned before PostgreSQL.", "follow_up_questions": ["Would you like a suggested order?"]}'
        # Yield in small chunks to simulate real streaming
        for i in range(0, len(json_str), 5):
            yield json_str[i : i + 5]

    from app.api.deps import get_current_user
    from app.models.auth import UserResponse
    
    async def mock_get_current_user():
        return UserResponse(id="test-user-123", username="testuser")

    # Check if this is an authentication test (we don't want to mock dependency override there)
    is_auth_test = hasattr(request, "module") and "test_auth" in request.module.__name__

    with patch("app.services.llm_service.llm_service.generate_json", new_callable=AsyncMock, side_effect=mock_generate_json) as mock_gen, \
         patch("app.services.llm_service.llm_service.generate_stream", side_effect=mock_generate_stream) as mock_stream, \
         patch("app.services.chat_service.vector_store.search", new_callable=AsyncMock) as mock_search, \
         patch("app.api.deps.get_current_user", return_value={"id": "test-user-123", "username": "testuser"}):
        
        mock_search.return_value = [
            {
                "content": "Task 1: Learn FastAPI...",
                "metadata": {"chunk_type": "task", "task_title": "Learn FastAPI"},
                "score": 0.95
            }
        ]
        
        if not is_auth_test:
            app.dependency_overrides[get_current_user] = mock_get_current_user
            
        yield

        if not is_auth_test:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def client():
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c