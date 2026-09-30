"""
Global error handling middleware.
Converts exceptions to consistent error responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import BaseAppException
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def base_app_exception_handler(
    request: Request, 
    exc: BaseAppException
) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.error(
        f"Application error: {exc.code} - {exc.message}",
        extra={"extra_fields": {
            "path": str(request.url),
            "method": request.method,
            "error_code": exc.code,
            "details": exc.details
        }}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = exc.errors()
    
    # Format validation errors for better readability
    formatted_errors = []
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        formatted_errors.append({
            "field": field,
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "")
        })
    
    logger.warning(
        f"Validation error on {request.method} {request.url}",
        extra={"extra_fields": {"errors": formatted_errors}}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"fields": formatted_errors}
            }
        }
    )


async def http_exception_handler(
    request: Request, 
    exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    logger.warning(
        f"HTTP error: {exc.status_code} on {request.method} {request.url}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail
            }
        }
    )


async def unhandled_exception_handler(
    request: Request, 
    exc: Exception
) -> JSONResponse:
    """Handle uncaught exceptions."""
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={"extra_fields": {
            "path": str(request.url),
            "method": request.method
        }}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )