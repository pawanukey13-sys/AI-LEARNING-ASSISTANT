"""
Custom exception classes for the application.
Provides clear error categorization and HTTP status mapping.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BaseAppException(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for response."""
        result = {
            "error": {
                "code": self.code,
                "message": self.message
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result


class LLMEmptyResponseError(BaseAppException):
    """Raised when the LLM returns an empty response."""
    def __init__(self, message: str = "Empty response from LLM", raw_response: Optional[str] = None):
        super().__init__(
            message=message,
            code="LLM_EMPTY_RESPONSE",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"raw_response": raw_response} if raw_response is not None else None
        )


class LLMInvalidJSONError(BaseAppException):
    """Raised when the LLM response is not valid JSON."""
    def __init__(self, message: str = "Could not parse JSON from LLM response", raw_response: Optional[str] = None):
        super().__init__(
            message=message,
            code="LLM_INVALID_JSON",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"raw_response": raw_response} if raw_response is not None else None
        )


class LLMResponseValidationError(BaseAppException):
    """Raised when the parsed LLM response does not match the Pydantic schema."""
    def __init__(self, message: str = "LLM response schema validation failed", raw_response: Optional[str] = None, errors: Optional[Any] = None):
        details = {}
        if raw_response is not None:
            details["raw_response"] = raw_response
        if errors is not None:
            details["validation_errors"] = errors
        super().__init__(
            message=message,
            code="LLM_RESPONSE_VALIDATION_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details if details else None
        )


class LLMConnectionError(BaseAppException):
    """Raised when unable to connect to the LLM service."""
    def __init__(self, message: str = "Unable to connect to LLM service. Please ensure Ollama is running.", details: Optional[Dict[str, Any]] = None):
        default_details = {
            "suggestion": "Start Ollama with: ollama serve",
            "check_url": "http://localhost:11434/api/tags"
        }
        if details:
            default_details.update(details)
        super().__init__(
            message=message,
            code="LLM_CONNECTION_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=default_details
        )


class LLMTimeoutError(BaseAppException):
    """Raised when the LLM call times out."""
    def __init__(self, message: str = "LLM request timed out", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="LLM_TIMEOUT",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details=details
        )


class LLMProviderError(BaseAppException):
    """Raised when the LLM provider returns an API error."""
    def __init__(self, message: str, code: str = "LLM_PROVIDER_ERROR", status_code: int = 502, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details
        )


class LLMServiceError(LLMProviderError):
    """Errors related to LLM service operations (keeps backwards compatibility)."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="LLM_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class LLMResponseParsingError(LLMInvalidJSONError):
    """Errors when parsing LLM responses (keeps backwards compatibility)."""
    
    def __init__(self, message: str, raw_response: Optional[str] = None):
        super().__init__(
            message=message,
            raw_response=raw_response
        )
        self.code = "LLM_PARSING_ERROR"
        self.status_code = status.HTTP_502_BAD_GATEWAY


class EmbeddingServiceError(BaseAppException):
    """Errors related to embedding service operations."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="EMBEDDING_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class VectorStoreError(BaseAppException):
    """Errors related to vector store operations."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VECTOR_STORE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class RoadmapNotFoundError(BaseAppException):
    """When a requested roadmap doesn't exist."""
    
    def __init__(self, roadmap_id: str):
        super().__init__(
            message=f"Roadmap with id '{roadmap_id}' not found",
            code="ROADMAP_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"roadmap_id": roadmap_id}
        )


class ValidationError(BaseAppException):
    """Custom validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else None
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class OllamaConnectionError(LLMConnectionError):
    """When Ollama service is unavailable (keeps backwards compatibility)."""
    
    def __init__(self):
        super().__init__(
            message="Unable to connect to Ollama service. Please ensure Ollama is running."
        )
        self.code = "OLLAMA_CONNECTION_ERROR"
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE