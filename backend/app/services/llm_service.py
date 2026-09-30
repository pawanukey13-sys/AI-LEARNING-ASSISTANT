"""
LLM Service for interacting with Ollama.
Handles model communication, retry logic, and response parsing.
"""

import json
import asyncio
from typing import Any, Dict, Optional, AsyncGenerator, List, TypeVar, Type
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from pydantic import BaseModel, ValidationError as PydanticValidationError
from ollama import AsyncClient, ResponseError

from app.config import settings
from app.core.exceptions import (
    BaseAppException,
    LLMEmptyResponseError,
    LLMInvalidJSONError,
    LLMResponseValidationError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMProviderError,
    LLMServiceError,
    LLMResponseParsingError,
    OllamaConnectionError
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


def find_balanced_candidates(text: str) -> List[str]:
    """
    Find all balanced JSON object and array candidate substrings in text,
    ordered by their start position (left-to-right).
    Handles nested structures and ignores characters inside double-quoted strings.
    """
    candidates = []
    n = len(text)
    
    # Find all start indices for '{' and '['
    start_indices = [i for i, c in enumerate(text) if c in ('{', '[')]
    
    for start_idx in start_indices:
        start_char = text[start_idx]
        
        # Initialize trackers
        in_string = False
        escape_state = False
        object_depth = 1 if start_char == '{' else 0
        array_depth = 1 if start_char == '[' else 0
        
        for i in range(start_idx + 1, n):
            char = text[i]
            
            if escape_state:
                escape_state = False
                continue
                
            if char == '\\':
                escape_state = True
                continue
                
            if char == '"':
                in_string = not in_string
                continue
                
            if in_string:
                continue
                
            if char == '{':
                object_depth += 1
            elif char == '}':
                object_depth -= 1
                if object_depth < 0:
                    break
            elif char == '[':
                array_depth += 1
            elif char == ']':
                array_depth -= 1
                if array_depth < 0:
                    break
                    
            if object_depth == 0 and array_depth == 0:
                # Found a balanced candidate!
                candidates.append(text[start_idx : i + 1])
                break  # Stop searching for this start_idx
                
    return candidates


def parse_and_validate_json(text: Any, response_model: Type[T]) -> T:
    """
    Centralized parsing pipeline:
    1. Reject None, non-string, and empty/whitespace-only text.
    2. Attempt direct json.loads.
    3. Remove exactly one outer markdown code fence when the complete response is fenced.
    4. Retry json.loads.
    5. Search for string-aware balanced object/array candidates.
    6. Attempt candidates in deterministic order.
    7. Validate the decoded value with response_model.model_validate.
    8. Raise: LLMEmptyResponseError, LLMInvalidJSONError, LLMResponseValidationError.
    """
    # 1. Reject None, non-string, and empty/whitespace-only text.
    if text is None:
        raise LLMEmptyResponseError("LLM response is None", raw_response="")
        
    if not isinstance(text, str):
        raise LLMInvalidJSONError(
            f"Expected string response, got {type(text).__name__}",
            raw_response=str(text)
        )
        
    text_stripped = text.strip()
    if not text_stripped:
        raise LLMEmptyResponseError("LLM response is empty or whitespace-only", raw_response=text)

    # 2. Attempt direct json.loads.
    try:
        parsed_data = json.loads(text_stripped)
        try:
            return response_model.model_validate(parsed_data)
        except PydanticValidationError as e:
            raise LLMResponseValidationError(
                f"Schema validation failed: {str(e)}",
                raw_response=text,
                errors=e.errors()
            )
    except json.JSONDecodeError:
        pass

    # Helper to clean up EXACTLY ONE outer markdown code fence when the complete response is fenced
    def clean_outer_code_fence(s: str) -> str:
        if s.startswith("```") and s.endswith("```") and len(s) >= 6:
            first_newline = s.find("\n")
            if first_newline != -1 and first_newline < s.rfind("```"):
                return s[first_newline + 1 : -3].strip()
            return s[3:-3].strip()
        return s

    # 3. Remove exactly one outer markdown code fence when the complete response is fenced.
    cleaned_text = clean_outer_code_fence(text_stripped)
    
    # 4. Retry json.loads.
    try:
        parsed_data = json.loads(cleaned_text)
        try:
            return response_model.model_validate(parsed_data)
        except PydanticValidationError as e:
            raise LLMResponseValidationError(
                f"Schema validation failed: {str(e)}",
                raw_response=text,
                errors=e.errors()
            )
    except json.JSONDecodeError:
        pass

    # 5. Search for string-aware balanced object/array candidates and attempt in deterministic order.
    candidates = find_balanced_candidates(cleaned_text)
    
    last_validation_error = None
    for candidate in candidates:
        try:
            parsed_data = json.loads(candidate)
            try:
                return response_model.model_validate(parsed_data)
            except PydanticValidationError as pve:
                last_validation_error = pve
        except json.JSONDecodeError:
            continue

    if last_validation_error is not None:
        raise LLMResponseValidationError(
            f"Schema validation failed: {str(last_validation_error)}",
            raw_response=text,
            errors=last_validation_error.errors()
        )

    # 8. Raise LLMInvalidJSONError if no candidates parsed successfully
    preview = text_stripped[:400] + "..." if len(text_stripped) > 400 else text_stripped
    logger.error(f"Failed to extract valid JSON from LLM response. Preview: {preview}")
    raise LLMInvalidJSONError(
        "Could not parse valid JSON from LLM response",
        raw_response=text
    )


class LLMService:
    """
    Service for interacting with local Ollama LLM using the official SDK.
    Implements retry logic and structured output parsing.
    """
    
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model = settings.llm_model
        self.timeout = settings.ollama_timeout_seconds
        self._client: Optional[AsyncClient] = None
    
    def _get_client(self) -> AsyncClient:
        """Get or create Ollama AsyncClient."""
        if self._client is None:
            self._client = AsyncClient(
                host=self.base_url,
                timeout=self.timeout
            )
        return self._client
    
    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and hasattr(self._client, "_client") and not self._client._client.is_closed:
            await self._client._client.aclose()
    
    async def check_health(self) -> bool:
        """Check if Ollama service is available."""
        try:
            client = self._get_client()
            await client.list()
            return True
        except asyncio.CancelledError:
            raise
        except Exception:
            return False
    
    async def _ensure_model_available(self) -> None:
        """Verify the configured model is available."""
        try:
            client = self._get_client()
            response = await client.list()
            
            models = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
            model_names = []
            for m in models:
                if isinstance(m, dict) and "name" in m:
                    model_names.append(m["name"].strip().lower())
                elif hasattr(m, "name"):
                    model_names.append(getattr(m, "name").strip().lower())
            
            target_model = self.model.strip().lower()
            
            if ":" not in target_model:
                target_model_with_latest = f"{target_model}:latest"
            else:
                target_model_with_latest = target_model
                
            if target_model not in model_names and target_model_with_latest not in model_names:
                raise LLMServiceError(
                    f"Model '{self.model}' not found in Ollama. Available models: {model_names}",
                    details={"available_models": model_names}
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if isinstance(e, BaseAppException):
                raise
            logger.error(f"Failed to check model availability: {e}")
            raise OllamaConnectionError() from e
    
    def _extract_text_from_ollama_response(self, response: Any) -> str:
        """Safely extracts text response from Ollama SDK response structure."""
        if response is None:
            raise LLMEmptyResponseError("Ollama response is None", raw_response="")
            
        text = ""
        if isinstance(response, dict):
            text = response.get("response", "")
        elif hasattr(response, "response"):
            text = getattr(response, "response", "")
        elif hasattr(response, "message") and isinstance(getattr(response, "message"), dict):
            text = getattr(response, "message").get("content", "")
        elif isinstance(response, dict) and "message" in response and isinstance(response["message"], dict):
            text = response["message"].get("content", "")
        else:
            text = str(response)

        if not text or not isinstance(text, str) or not text.strip():
            raise LLMEmptyResponseError("Ollama response text content is empty", raw_response=str(response))
            
        return text.strip()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        format: Optional[str] = None
    ) -> str:
        """
        Generate a response from the LLM.
        """
        await self._ensure_model_available()
        
        client = self._get_client()
        
        temp = temperature if temperature is not None else settings.llm_temperature
        tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens
        
        options = {
            "temperature": temp,
            "num_predict": tokens,
        }
        
        logger.info(
            "Sending LLM request",
            extra={"extra_fields": {
                "model": self.model,
                "prompt_length": len(prompt),
                "format": format
            }}
        )
        
        try:
            response = await client.generate(
                model=self.model,
                prompt=prompt,
                system=system_prompt,
                format=format,
                options=options
            )
            
            generated_text = self._extract_text_from_ollama_response(response)
            
            logger.info(
                "LLM response received",
                extra={"extra_fields": {
                    "response_length": len(generated_text)
                }}
            )
            
            return generated_text
            
        except asyncio.CancelledError:
            logger.warning("LLM request was cancelled")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timed out: {e}")
            raise LLMTimeoutError("Ollama request timed out", details={"error": str(e)}) from e
        except ResponseError as e:
            logger.error(f"Ollama API error: {e.status_code} - {e.error}")
            raise LLMProviderError(
                f"Ollama provider error: {e.error}",
                status_code=e.status_code,
                details={"error": e.error}
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Ollama connection error: {e}")
            raise LLMConnectionError("Ollama connection error", details={"error": str(e)}) from e
        except Exception as e:
            if isinstance(e, BaseAppException):
                raise
            logger.error(f"Ollama unexpected error: {e}")
            raise LLMProviderError(f"Unexpected provider error: {str(e)}") from e
    
    async def generate_json(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3
    ) -> T:
        """
        Generate and parse a JSON response from the LLM.
        """
        raw_response = ""
        try:
            raw_response = await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                format="json"
            )
            return parse_and_validate_json(raw_response, response_model)
        except (LLMEmptyResponseError, LLMInvalidJSONError, LLMResponseValidationError) as e:
            logger.warning(f"Native JSON generation or validation failed, attempting fallback: {e}")
        except Exception as e:
            if isinstance(e, BaseAppException):
                raise
            raise LLMProviderError(f"Native JSON generation failed: {e}") from e

        try:
            raw_response = await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature
            )
            return parse_and_validate_json(raw_response, response_model)
        except Exception as e:
            if isinstance(e, BaseAppException):
                raise
            raise LLMProviderError(f"Fallback JSON generation failed: {e}") from e
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from the LLM.
        """
        await self._ensure_model_available()
        
        client = self._get_client()
        temp = temperature if temperature is not None else settings.llm_temperature
        
        options = {
            "temperature": temp,
            "num_predict": settings.llm_max_tokens,
        }
        
        try:
            stream = await client.generate(
                model=self.model,
                prompt=prompt,
                system=system_prompt,
                stream=True,
                options=options
            )
            async for chunk in stream:
                content = ""
                if isinstance(chunk, dict):
                    content = chunk.get("response", "")
                elif hasattr(chunk, "response"):
                    content = getattr(chunk, "response", "")
                
                if not content:
                    if isinstance(chunk, dict) and "message" in chunk:
                        content = chunk["message"].get("content", "")
                    elif hasattr(chunk, "message") and isinstance(getattr(chunk, "message"), dict):
                        content = getattr(chunk, "message").get("content", "")
                        
                if content:
                    yield content
                            
        except asyncio.CancelledError:
            logger.warning("LLM streaming request was cancelled")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"Ollama streaming timed out: {e}")
            raise LLMTimeoutError("Ollama streaming request timed out") from e
        except ResponseError as e:
            logger.error(f"Ollama API error during stream: {e.status_code} - {e.error}")
            raise LLMProviderError(f"Ollama stream error: {e.error}", status_code=e.status_code) from e
        except httpx.RequestError as e:
            logger.error(f"Ollama connection error during stream: {e}")
            raise LLMConnectionError("Ollama stream connection error") from e
        except Exception as e:
            logger.error(f"Ollama unexpected stream error: {e}")
            raise LLMProviderError(f"Unexpected stream error: {str(e)}") from e


# Singleton instance
llm_service = LLMService()