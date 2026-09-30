"""
Application configuration using Pydantic Settings.
Centralized configuration management with environment variable support.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Resolve env files dynamically from app/config.py location
    _config_dir = Path(__file__).resolve().parent
    _backend_dir = _config_dir.parent
    _repo_root_dir = _backend_dir.parent
    
    _env_files = [
        _repo_root_dir / ".env",
        _backend_dir / ".env",
    ]
    _existing_env_files = tuple(f for f in _env_files if f.exists())

    model_config = SettingsConfigDict(
        env_file=_existing_env_files if _existing_env_files else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="AI Learning Assistant", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # JWT Authentication Settings
    secret_key: str = Field(
        default="YOUR_UNBREAKABLE_SECRET_KEY_HERE",
        alias="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS Configuration
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"], 
        alias="CORS_ORIGINS"
    )
    
    # Ollama Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434", 
        alias="OLLAMA_BASE_URL"
    )
    llm_model: str = Field(default="llama3.2:3b", alias="LLM_MODEL")
    embedding_model: str = Field(default="bge-m3", alias="EMBEDDING_MODEL")
    
    # Ollama Options and Timeouts
    ollama_timeout_seconds: float = Field(
        default=300.0,
        alias="OLLAMA_TIMEOUT_SECONDS",
        gt=0.0
    )
    llm_temperature: float = Field(
        default=0.3,
        alias="LLM_TEMPERATURE",
        ge=0.0,
        le=1.0
    )
    llm_max_tokens: int = Field(
        default=4096,
        alias="LLM_MAX_TOKENS",
        ge=1
    )
    
    # Vector Store
    chroma_persist_directory: str = Field(
        default="./storage/chroma_db", 
        alias="CHROMA_PERSIST_DIRECTORY"
    )
    collection_name: str = Field(
        default="learning_roadmaps", 
        alias="COLLECTION_NAME"
    )
    
    # Cache
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")
    
    @property
    def storage_path(self) -> Path:
        """Get storage path as Path object, creating if needed."""
        path = Path(self.chroma_persist_directory)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Singleton instance
settings = Settings()