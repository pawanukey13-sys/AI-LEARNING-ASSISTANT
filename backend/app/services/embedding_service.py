
"""
Embedding Service using Ollama with BGE-M3 model.
Handles text embedding generation for RAG pipeline.
"""

from typing import List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.exceptions import EmbeddingServiceError, OllamaConnectionError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using Ollama's BGE-M3 model.
    """
    
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model = settings.embedding_model
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(120.0, connect=10.0)
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def check_health(self) -> bool:
        """Check if embedding model is available."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=5.0)
            if response.status_code != 200:
                return False
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            return any(self.model in name for name in model_names)
        except Exception:
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embed_batch([text])
        return embeddings[0]
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        Loops through texts because Ollama raw HTTP API only accepts 
        a single 'prompt' string per request.
        """
        if not texts:
            return []
        
        client = await self._get_client()
        embeddings = []
        
        for text in texts:
            payload = {
                "model": self.model,
                "prompt": text,  # Ollama requires 'prompt', not 'input'
            }
            
            try:
                response = await client.post("/api/embeddings", json=payload)
                response.raise_for_status()
                
                result = response.json()
                embedding = result.get("embedding", [])
                
                if not embedding:
                    raise EmbeddingServiceError("Empty embedding returned from Ollama")
                embeddings.append(embedding)
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Embedding HTTP error: {e.response.status_code}")
                raise EmbeddingServiceError(
                    f"Embedding service error: {e.response.status_code}"
                )
            except httpx.HTTPError as e:
                logger.error(f"Embedding connection error: {e}")
                raise OllamaConnectionError()
        
        logger.info(f"Successfully generated {len(embeddings)} embeddings")
        return embeddings
    
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding optimized for query/search."""
        prefixed_query = f"Represent this sentence for searching relevant passages: {query}"
        return await self.embed_text(prefixed_query)


# Singleton instance
embedding_service = EmbeddingService()