"""
Chat service with full RAG implementation.
Handles conversation history, retrieval, and response generation.
"""

from typing import List, Dict, Any, AsyncGenerator, Optional
from uuid import uuid4
from cachetools import TTLCache

from app.models.requests import ChatRequest
import json
import asyncio
from app.models.responses import ChatResponse, ChatStreamChunk, ChatLLMResponse
from app.services.llm_service import llm_service
from app.services.vector_store import vector_store
from app.prompts.templates import (
    CHAT_SYSTEM_PROMPT, 
    CHAT_USER_PROMPT,
    format_conversation_history,
    format_rag_context
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Conversation history storage (in production, use a proper database)
_conversation_history: Dict[str, List[Dict[str, str]]] = TTLCache(maxsize=1000, ttl=7200)


class ChatService:
    """
    RAG-based chat service.
    
    Implements:
    - Semantic retrieval from indexed roadmaps
    - Conversation history management
    - Context-aware response generation
    - Streaming support
    """
    
    def __init__(self):
        self.max_history_length = 10
        self.retrieval_top_k = 5
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message with RAG.
        
        Args:
            request: Chat request with message and roadmap context
        
        Returns:
            AI response with follow-up suggestions
        """
        # Get or create conversation ID
        conversation_id = request.conversation_id or str(uuid4())
        
        # Retrieve relevant context
        context_chunks = await vector_store.search(
            roadmap_id=request.roadmap_id,
            query=request.message,
            n_results=self.retrieval_top_k
        )
        
        # Get conversation history
        history = self._get_history(conversation_id)
        
        # Format context for prompt
        rag_context = format_rag_context(context_chunks)
        history_text = format_conversation_history(history)
        
        # Generate response
        prompt = CHAT_USER_PROMPT.format(
            context=rag_context,
            conversation_history=history_text,
            message=request.message
        )
        
        raw_response = await llm_service.generate_json(
            prompt=prompt,
            response_model=ChatLLMResponse,
            system_prompt=CHAT_SYSTEM_PROMPT,
            temperature=0.5
        )
        
        # Update conversation history
        self._add_to_history(conversation_id, "user", request.message)
        self._add_to_history(
            conversation_id, 
            "assistant", 
            raw_response.response
        )
        
        return ChatResponse(
            response=raw_response.response,
            follow_up_questions=raw_response.follow_up_questions,
            sources=[
                {
                    "content": chunk["content"][:200] + "...",
                    "type": chunk["metadata"].get("chunk_type"),
                    "score": round(chunk["score"], 3)
                }
                for chunk in context_chunks[:3]
            ],
            conversation_id=conversation_id
        )
    
    async def chat_stream(
        self, 
        request: ChatRequest
    ) -> AsyncGenerator[ChatStreamChunk, None]:
        """
        Stream a chat response with RAG.
        
        Yields:
            Stream chunks for progressive response delivery
        """
        conversation_id = request.conversation_id or str(uuid4())
        
        # Retrieve context
        context_chunks = await vector_store.search(
            roadmap_id=request.roadmap_id,
            query=request.message,
            n_results=self.retrieval_top_k
        )
        
        history = self._get_history(conversation_id)
        rag_context = format_rag_context(context_chunks)
        history_text = format_conversation_history(history)
        
        prompt = CHAT_USER_PROMPT.format(
            context=rag_context,
            conversation_history=history_text,
            message=request.message
        )
        
        # Call generate_stream to perform real streaming!
        stream = await llm_service.generate_stream(
            prompt=prompt,
            system_prompt=CHAT_SYSTEM_PROMPT,
            temperature=0.5
        )
        
        buffer = ""
        inside_response = False
        escape_next = False
        yielded_idx = 0
        
        async for chunk in stream:
            buffer += chunk
            
            if not inside_response:
                key_idx = buffer.lower().find('"response"')
                if key_idx != -1:
                    colon_idx = buffer.find(':', key_idx + 10)
                    if colon_idx != -1:
                        quote_idx = buffer.find('"', colon_idx + 1)
                        if quote_idx != -1:
                            inside_response = True
                            yielded_idx = quote_idx + 1
            
            if inside_response:
                content_to_send = ""
                i = yielded_idx
                while i < len(buffer):
                    char = buffer[i]
                    if escape_next:
                        content_to_send += char
                        escape_next = False
                        i += 1
                        yielded_idx = i
                    elif char == '\\':
                        escape_next = True
                        i += 1
                    elif char == '"':
                        inside_response = False
                        break
                    else:
                        content_to_send += char
                        i += 1
                        yielded_idx = i
                
                if content_to_send:
                    yield ChatStreamChunk(
                        type="content",
                        content=content_to_send
                    )
        
        # Extract follow-up questions from the complete stream buffer
        follow_ups = []
        response_text = ""
        try:
            from app.services.llm_service import parse_and_validate_json
            parsed = parse_and_validate_json(buffer, ChatLLMResponse)
            follow_ups = parsed.follow_up_questions
            response_text = parsed.response
        except Exception as e:
            logger.warning(f"Could not parse follow-up questions from streaming buffer: {e}")
            try:
                data = json.loads(buffer)
                follow_ups = data.get("follow_up_questions", [])
                response_text = data.get("response", "")
            except Exception:
                pass
                
        if not response_text:
            response_text = buffer
            
        if follow_ups:
            yield ChatStreamChunk(
                type="follow_up",
                content=None,
                metadata={"questions": follow_ups}
            )
            
        # Send done signal
        yield ChatStreamChunk(
            type="done",
            content=None,
            metadata={
                "conversation_id": conversation_id,
                "sources": [
                    {
                        "type": chunk["metadata"].get("chunk_type"),
                        "score": round(chunk["score"], 3)
                    }
                    for chunk in context_chunks[:3]
                ]
            }
        )
        
        # Update history
        self._add_to_history(conversation_id, "user", request.message)
        self._add_to_history(conversation_id, "assistant", response_text)
    
    def _get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """Get conversation history."""
        return _conversation_history.get(conversation_id, [])
    
    def _add_to_history(
        self, 
        conversation_id: str, 
        role: str, 
        content: str
    ) -> None:
        """Add a message to conversation history."""
        if conversation_id not in _conversation_history:
            _conversation_history[conversation_id] = []
        
        history = _conversation_history[conversation_id]
        history.append({"role": role, "content": content})
        
        # Trim to max length
        if len(history) > self.max_history_length:
            _conversation_history[conversation_id] = history[-self.max_history_length:]



chat_service = ChatService()