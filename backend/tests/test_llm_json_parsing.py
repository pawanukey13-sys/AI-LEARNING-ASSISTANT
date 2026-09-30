import pytest
import json
import asyncio
from typing import List, Optional
from pydantic import BaseModel, Field
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.responses import ProjectResponse
from app.services.llm_service import (
    parse_and_validate_json,
    find_balanced_candidates,
    LLMService
)
from app.core.exceptions import (
    LLMEmptyResponseError,
    LLMInvalidJSONError,
    LLMResponseValidationError,
    LLMTimeoutError,
    LLMConnectionError,
    LLMProviderError
)

# A simple schema for parsing tests
class SimpleSchema(BaseModel):
    name: str
    age: int
    tags: List[str]
    description: Optional[str] = None


@pytest.mark.no_mock_llm
class TestPureJSONParser:
    """Pure unit tests for the string-aware JSON parser logic."""

    def test_valid_simple_json(self):
        text = '{"name": "Alice", "age": 25, "tags": ["admin"]}'
        result = parse_and_validate_json(text, SimpleSchema)
        assert result.name == "Alice"
        assert result.age == 25

    def test_fenced_block_with_language_identifier(self):
        text = '```json\n{"name": "Bob", "age": 30, "tags": ["user"]}\n```'
        result = parse_and_validate_json(text, SimpleSchema)
        assert result.name == "Bob"

    def test_incomplete_code_fence(self):
        # Starts with fence but doesn't end properly, or vice-versa
        # Balanced extraction should recover it
        text = '```json\n{"name": "Charlie", "age": 35, "tags": []}'
        result = parse_and_validate_json(text, SimpleSchema)
        assert result.name == "Charlie"

    def test_json_containing_braces_inside_strings(self):
        # Brace inside string should not confuse the balanced braces tracking
        text = '{"name": "Alice {Admin}", "age": 25, "tags": ["{x}"]}'
        result = parse_and_validate_json(text, SimpleSchema)
        assert result.name == "Alice {Admin}"
        assert result.tags == ["{x}"]

    def test_json_containing_escaped_quotes(self):
        text = '{"name": "Bob \\"Builder\\"", "age": 40, "tags": ["engineer"]}'
        result = parse_and_validate_json(text, SimpleSchema)
        assert result.name == 'Bob "Builder"'

    def test_nested_objects_and_arrays(self):
        text = 'prose {"name": "Charlie", "age": 20, "tags": ["a", ["b", {"nested": 1}]]} more prose'
        # The schema expects List[str], so we must pass list of string to pass validation
        # Let's check candidate extraction matches
        candidates = find_balanced_candidates(text)
        assert len(candidates) > 0
        assert candidates[0].startswith('{"name"')

    def test_root_json_array(self):
        # Valid JSON followed/preceded by prose where root is array
        from pydantic import RootModel
        class RootArraySchema(RootModel[List[SimpleSchema]]):
            pass
            
        text = 'some text [{"name": "A", "age": 1, "tags": []}] end text'
        candidates = find_balanced_candidates(text)
        assert len(candidates) > 0
        result = parse_and_validate_json(candidates[0], RootArraySchema)
        assert len(result.root) == 1
        assert result.root[0].name == "A"

    def test_multiple_json_fragments_only_one_valid(self):
        # First fragment is invalid/wrong schema, second is correct
        text = 'Random text {"age": "not-an-int"} and then {"name": "Valid", "age": 42, "tags": []}'
        result = parse_and_validate_json(text, SimpleSchema)
        assert result.name == "Valid"
        assert result.age == 42

    def test_valid_json_followed_by_prose(self):
        text = '{"name": "Dave", "age": 50, "tags": []} \nHere is some explanatory text.'
        result = parse_and_validate_json(text, SimpleSchema)
        assert result.name == "Dave"

    def test_prose_followed_by_valid_json(self):
        text = 'Here is some explanation first:\n{"name": "Eve", "age": 22, "tags": []}'
        result = parse_and_validate_json(text, SimpleSchema)
        assert result.name == "Eve"

    def test_whitespace_only_response(self):
        with pytest.raises(LLMEmptyResponseError):
            parse_and_validate_json("    \n   ", SimpleSchema)

    def test_none_response(self):
        with pytest.raises(LLMEmptyResponseError):
            parse_and_validate_json(None, SimpleSchema)

    def test_non_string_response(self):
        with pytest.raises(LLMInvalidJSONError):
            parse_and_validate_json(12345, SimpleSchema)

    def test_malformed_json_fails(self):
        with pytest.raises(LLMInvalidJSONError):
            parse_and_validate_json("not a json at all", SimpleSchema)

    def test_valid_json_with_wrong_field_types(self):
        # age should be int, but here is string that cannot be coerced,
        # or tags is string instead of list.
        text = '{"name": "Frank", "age": "thirty", "tags": []}'
        with pytest.raises(LLMResponseValidationError) as excinfo:
            parse_and_validate_json(text, SimpleSchema)
        assert excinfo.value.code == "LLM_RESPONSE_VALIDATION_ERROR"
        assert "validation_errors" in excinfo.value.details


@pytest.mark.no_mock_llm
class TestLLMServiceWrapper:
    """Tests LLMService SDK integration and exception mappings."""

    @pytest.mark.asyncio
    async def test_sdk_response_missing_content(self):
        service = LLMService()
        mock_client = MagicMock()
        # Mock generate returning dict without response field
        mock_client.generate = AsyncMock(return_value={"done": True})
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            with pytest.raises(LLMEmptyResponseError) as excinfo:
                await service.generate("prompt")
            assert "empty" in excinfo.value.message

    @pytest.mark.asyncio
    async def test_sdk_response_empty_content(self):
        service = LLMService()
        mock_client = MagicMock()
        mock_client.generate = AsyncMock(return_value={"response": "   ", "done": True})
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            with pytest.raises(LLMEmptyResponseError):
                await service.generate("prompt")

    @pytest.mark.asyncio
    async def test_exact_model_tag_matching_success(self):
        service = LLMService()
        service.model = "llama3.2:latest"
        mock_client = MagicMock()
        # SDK return value
        mock_client.list = AsyncMock(return_value={
            "models": [{"name": "llama3.2:latest"}, {"name": "bge-m3:latest"}]
        })
        service._client = mock_client
        
        # Should not raise any error
        await service._ensure_model_available()

    @pytest.mark.asyncio
    async def test_model_not_installed_fails(self):
        service = LLMService()
        # Expecting llama3.2:3b, but only llama3.2:latest is installed
        service.model = "llama3.2:3b"
        mock_client = MagicMock()
        mock_client.list = AsyncMock(return_value={
            "models": [{"name": "llama3.2:latest"}]
        })
        service._client = mock_client
        
        from app.core.exceptions import LLMServiceError
        with pytest.raises(LLMServiceError) as excinfo:
            await service._ensure_model_available()
        assert "not found" in excinfo.value.message

    @pytest.mark.asyncio
    async def test_timeout_mapping(self):
        import httpx
        service = LLMService()
        mock_client = MagicMock()
        mock_client.generate = AsyncMock(side_effect=httpx.TimeoutException("Read timed out"))
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            with pytest.raises(LLMTimeoutError):
                await service.generate("prompt")

    @pytest.mark.asyncio
    async def test_connection_failure_mapping(self):
        import httpx
        service = LLMService()
        mock_client = MagicMock()
        mock_client.generate = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            with pytest.raises(LLMConnectionError):
                await service.generate("prompt")

    @pytest.mark.asyncio
    async def test_provider_failure_mapping(self):
        from ollama import ResponseError
        service = LLMService()
        mock_client = MagicMock()
        # Create a mock response error with status_code
        mock_err = ResponseError("Ollama failed", 500)
        mock_client.generate = AsyncMock(side_effect=mock_err)
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            with pytest.raises(LLMProviderError) as excinfo:
                await service.generate("prompt")
            assert excinfo.value.status_code == 500

    @pytest.mark.asyncio
    async def test_cancellation_propagation(self):
        service = LLMService()
        mock_client = MagicMock()
        mock_client.generate = AsyncMock(side_effect=asyncio.CancelledError())
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            with pytest.raises(asyncio.CancelledError):
                await service.generate("prompt")

    @pytest.mark.asyncio
    async def test_streaming_success(self):
        service = LLMService()
        mock_client = MagicMock()
        
        # Async generator for chunks
        async def mock_stream():
            yield {"response": "Hello"}
            yield {"response": " World"}
            
        mock_client.generate = AsyncMock(return_value=mock_stream())
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            generator = service.generate_stream("prompt")
            chunks = [c async for c in generator]
            assert chunks == ["Hello", " World"]

    @pytest.mark.asyncio
    async def test_streaming_failure(self):
        service = LLMService()
        mock_client = MagicMock()
        
        async def mock_stream_fail():
            yield {"response": "Hi"}
            raise Exception("Stream crash")
            
        mock_client.generate = AsyncMock(return_value=mock_stream_fail())
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            generator = service.generate_stream("prompt")
            chunks = []
            with pytest.raises(LLMProviderError):
                async for chunk in generator:
                    chunks.append(chunk)


@pytest.mark.asyncio
async def test_endpoint_error_envelope_consistency():
    """Test that global exception handlers output correct standardized error envelope."""
    from app.services.project_service import project_service
    from httpx import AsyncClient
    from app.main import app
    
    with patch.object(project_service, "recommend_project", AsyncMock(side_effect=LLMInvalidJSONError("Parse error test", raw_response="{}"))):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/project",
                json={"goal_title": "Backend Developer", "skills": ["Python"]}
            )
        
        assert response.status_code == 502
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "LLM_INVALID_JSON"
        assert data["error"]["message"] == "Parse error test"


@pytest.mark.no_mock_llm
class TestBalancedCandidateSelection:
    """Tests that balanced candidate selection handles multiple fragments and validation mappings."""

    def test_balanced_candidate_skips_schema_invalid(self):
        # First candidate is valid JSON but schema-invalid. Second candidate matches schema.
        text = """
        Metadata: {"status":"ok"}
        
        Actual response:
        {"name": "API Project", "age": 20, "tags": ["REST"]}
        """
        result = parse_and_validate_json(text, SimpleSchema)
        assert result.name == "API Project"
        assert result.age == 20

    def test_balanced_candidate_all_schema_invalid_raises_validation_error(self):
        text = 'Metadata: {"status":"ok"} and {"name": "Invalid", "age": "not-an-int", "tags": []}'
        with pytest.raises(LLMResponseValidationError) as excinfo:
            parse_and_validate_json(text, SimpleSchema)
        assert excinfo.value.code == "LLM_RESPONSE_VALIDATION_ERROR"

    def test_balanced_candidate_no_json_raises_invalid_json_error(self):
        text = 'Prose text without any valid brackets'
        with pytest.raises(LLMInvalidJSONError) as excinfo:
            parse_and_validate_json(text, SimpleSchema)
        assert excinfo.value.code == "LLM_INVALID_JSON"


@pytest.mark.no_mock_llm
class TestEnvironmentPrecedence:
    """Tests settings environment loading precedence using isolated directories."""
    
    def test_precedence_order(self):
        import os
        import tempfile
        from pathlib import Path
        from pydantic_settings import SettingsConfigDict
        from app.config import Settings

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create isolated repo_root and backend directories
            repo_root = tmpdir_path / "repo"
            backend = repo_root / "backend"
            backend.mkdir(parents=True)
            
            # Write different models to .envs
            repo_env = repo_root / ".env"
            repo_env.write_text("LLM_MODEL=llama-from-repo\nAPP_NAME=RepoApp", encoding="utf-8")
            
            backend_env = backend / ".env"
            backend_env.write_text("LLM_MODEL=llama-from-backend\nAPP_NAME=BackendApp", encoding="utf-8")
            
            class TempSettings(Settings):
                model_config = SettingsConfigDict(
                    env_file=[repo_env, backend_env],
                    env_file_encoding="utf-8",
                    case_sensitive=False,
                    extra="ignore"
                )
                
            settings_inst = TempSettings()
            
            # Precedence rule 1: backend/.env overrides repo-root/.env
            assert settings_inst.llm_model == "llama-from-backend"
            assert settings_inst.app_name == "BackendApp"
            
            # Precedence rule 2: OS environment variables override backend/.env
            os.environ["LLM_MODEL"] = "llama-from-os"
            os.environ["APP_NAME"] = "OSApp"
            try:
                settings_os = TempSettings()
                assert settings_os.llm_model == "llama-from-os"
                assert settings_os.app_name == "OSApp"
            finally:
                del os.environ["LLM_MODEL"]
                del os.environ["APP_NAME"]


@pytest.mark.no_mock_llm
class TestGenerateJsonFlow:
    """Tests the detailed request count and exception propagation in LLMService.generate_json."""
    
    @pytest.mark.asyncio
    async def test_generate_json_success_one_request(self):
        service = LLMService()
        mock_client = MagicMock()
        mock_client.generate = AsyncMock(return_value={"response": '{"name": "Success", "age": 25, "tags": []}'})
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            result = await service.generate_json(
                prompt="test",
                response_model=SimpleSchema,
                temperature=0.3
            )
            assert result.name == "Success"
            # Successful native JSON generation makes exactly 1 request
            assert mock_client.generate.call_count == 1
            args, kwargs = mock_client.generate.call_args
            assert kwargs.get("format") == "json"

    @pytest.mark.asyncio
    async def test_generate_json_malformed_fallback_two_requests(self):
        service = LLMService()
        mock_client = MagicMock()
        # First call fails decoding (raises JSONDecodeError internally or through utility), second call succeeds
        mock_client.generate = AsyncMock(side_effect=[
            {"response": '{"name": "Malformed", '},  # Malformed
            {"response": '{"name": "Recovered", "age": 30, "tags": []}'}
        ])
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            result = await service.generate_json(
                prompt="test",
                response_model=SimpleSchema,
                temperature=0.3
            )
            assert result.name == "Recovered"
            # Fallback block initiates a second call, making 2 requests in total
            assert mock_client.generate.call_count == 2
            
            calls = mock_client.generate.call_args_list
            assert calls[0][1].get("format") == "json"
            assert calls[1][1].get("format") is None

    @pytest.mark.asyncio
    async def test_generate_json_validation_fallback_two_requests(self):
        service = LLMService()
        mock_client = MagicMock()
        # First call returns valid JSON but validation fails, second succeeds
        mock_client.generate = AsyncMock(side_effect=[
            {"response": '{"name": "InvalidType", "age": "thirty", "tags": []}'},  # Validation failure
            {"response": '{"name": "Recovered", "age": 30, "tags": []}'}
        ])
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            result = await service.generate_json(
                prompt="test",
                response_model=SimpleSchema,
                temperature=0.3
            )
            assert result.name == "Recovered"
            # Fallback block initiates a second call, making 2 requests in total
            assert mock_client.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_json_provider_error_no_fallback(self):
        from ollama import ResponseError
        service = LLMService()
        mock_client = MagicMock()
        # First call raises ResponseError (provider failure)
        mock_client.generate = AsyncMock(side_effect=ResponseError("Ollama failed", 500))
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            with pytest.raises(LLMProviderError):
                await service.generate_json(
                    prompt="test",
                    response_model=SimpleSchema,
                    temperature=0.3
                )
            # Provider failures must NOT trigger a fallback, making exactly 1 request
            assert mock_client.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_json_timeout_no_fallback(self):
        import httpx
        service = LLMService()
        mock_client = MagicMock()
        # First call raises httpx.TimeoutException
        mock_client.generate = AsyncMock(side_effect=httpx.TimeoutException("Read timed out"))
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            with pytest.raises(LLMTimeoutError):
                await service.generate_json(
                    prompt="test",
                    response_model=SimpleSchema,
                    temperature=0.3
                )
            assert mock_client.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_json_connection_error_no_fallback(self):
        import httpx
        service = LLMService()
        mock_client = MagicMock()
        # First call raises httpx.ConnectError
        mock_client.generate = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            with pytest.raises(LLMConnectionError):
                await service.generate_json(
                    prompt="test",
                    response_model=SimpleSchema,
                    temperature=0.3
                )
            assert mock_client.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_json_cancellation_no_fallback(self):
        service = LLMService()
        mock_client = MagicMock()
        # First call raises asyncio.CancelledError
        mock_client.generate = AsyncMock(side_effect=asyncio.CancelledError())
        service._client = mock_client
        
        with patch.object(service, "_ensure_model_available", AsyncMock()):
            with pytest.raises(asyncio.CancelledError):
                await service.generate_json(
                    prompt="test",
                    response_model=SimpleSchema,
                    temperature=0.3
                )
            assert mock_client.generate.call_count == 1


