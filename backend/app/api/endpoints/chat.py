"""
Chat endpoint handlers with streaming support.
"""

import json
from typing import Union
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from app.models.requests import ChatRequest
from app.models.responses import ChatResponse, ChatStreamChunk
from app.services.chat_service import chat_service
from app.core.logging_config import get_logger
from app.api.deps import get_current_user
from app.models.auth import UserResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=200,
    summary="AI Chat with RAG",
    description="Ask questions about your learning roadmap with RAG-powered responses.",
    responses={
        200: {"description": "Chat response generated"},
        401: {"description": "Not authenticated"},
        404: {"description": "Roadmap not found"},
        503: {"description": "LLM service unavailable"}
    }
)
async def chat(
    request: ChatRequest,
    current_user: UserResponse = Depends(get_current_user)
) -> Union[ChatResponse, StreamingResponse]:
    """
    Chat with the AI about your learning roadmap.
    
    Uses Retrieval-Augmented Generation (RAG) to provide context-aware
    responses based on your specific roadmap. Returns follow-up questions
    to continue the conversation.
    """
    logger.info(
        f"Chat request for roadmap: {request.roadmap_id}",
        extra={"extra_fields": {
            "message_length": len(request.message),
            "stream": request.stream,
            "conversation_id": request.conversation_id
        }}
    )
    
    if request.stream:
        # Return streaming response
        return StreamingResponse(
            _stream_generator(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    return await chat_service.chat(request)


async def _stream_generator(request: ChatRequest):
    """Generate SSE stream for chat responses."""
    try:
        async for chunk in chat_service.chat_stream(request):
            # Format as Server-Sent Events
            data = chunk.model_dump_json(exclude_none=True)
            yield f"data: {data}\n\n"
        
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        error_chunk = ChatStreamChunk(
            type="error",
            content=str(e)
        )
        yield f"data: {error_chunk.model_dump_json()}\n\n"