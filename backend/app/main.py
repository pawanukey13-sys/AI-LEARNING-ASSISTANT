"""
FastAPI application entry point.
Configures all services, middleware, and routes.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.exceptions import (
    BaseAppException,
    OllamaConnectionError
)
from app.middleware.error_handler import (
    base_app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    unhandled_exception_handler
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.services.llm_service import llm_service
from app.services.embedding_service import embedding_service
from app.models.responses import HealthResponse

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Check service health
    llm_healthy = await llm_service.check_health()
    embedding_healthy = await embedding_service.check_health()
    
    if not llm_healthy or not embedding_healthy:
        logger.warning(
            "Ollama services not fully available. "
            "Make sure Ollama is running and models are pulled."
        )
    
    logger.info("Application started successfully")
    
    yield  # Application runs here
    
    # Cleanup
    await llm_service.close()
    await embedding_service.close()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Setup logging first
    setup_logging()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        AI Learning Assistant - A RAG-powered backend service that generates 
        personalized learning roadmaps, recommends projects, and answers 
        follow-up questions.
        
        ## Features
        - **Roadmap Generation**: Create personalized learning paths
        - **Project Recommendations**: Get tailored project suggestions
        - **RAG Chat**: Ask questions about your roadmap with context-aware answers
        - **Streaming**: Real-time response streaming for chat
        - **Conversation History**: Maintain context across messages
        
        ## Tech Stack
        - FastAPI + Pydantic
        - Local LLM via Ollama (Llama 3.2)
        - BGE-M3 Embeddings
        - ChromaDB Vector Store
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handlers
    app.add_exception_handler(BaseAppException, base_app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={"extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params)
            }}
        )
        response = await call_next(request)
        logger.info(
            f"Response: {response.status_code}",
            extra={"extra_fields": {"status_code": response.status_code}}
        )
        return response
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        """Check service health and dependencies."""
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            services={
                "ollama_llm": "available" if await llm_service.check_health() else "unavailable",
                "ollama_embedding": "available" if await embedding_service.check_health() else "unavailable",
                "vector_store": "available"  # ChromaDB is local, always available
            }
        )
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )