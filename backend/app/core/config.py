from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Job Application Assistant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/aijobdb"
    
    # Security
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # External Services
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"

    # LLM — dual profiles; switch at runtime via PUT /api/v1/llm/provider
    # Boot default: openai | ollama | mock (empty = auto-detect from env)
    LLM_PROVIDER: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""  # leave empty for OpenAI cloud (legacy / boot hint)
    OPENAI_MODEL: str = "gpt-4o"
    LLM_MODEL: str = "gpt-4o"  # legacy alias; runtime uses provider-specific model
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_API_KEY: str = "ollama"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    # Local CPU is ~3 tok/s — keep completions short and the model resident
    OLLAMA_MAX_TOKENS: int = 200
    OLLAMA_NUM_CTX: int = 2048
    OLLAMA_KEEP_ALIVE: str = "30m"
    OLLAMA_TIMEOUT_SECONDS: float = 75.0
    OLLAMA_NUM_THREAD: int = 0  # 0 = Ollama default (use all cores)
    # Cap wait for cloud / shared; Ollama uses OLLAMA_TIMEOUT_SECONDS
    LLM_TIMEOUT_SECONDS: float = 45.0
    LLM_MAX_TOKENS: int = 700
    # Set true for instant Simulate demos (skip real LLM entirely)
    LLM_FORCE_MOCK: bool = False

    # LangGraph checkpoints: postgres (durable) | memory (process-local)
    CHECKPOINT_BACKEND: str = "postgres"

    # Embeddings / Vector memory (Qdrant)
    # Local: docker compose exec ollama ollama pull nomic-embed-text
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMS: int = 768
    
    ENVIRONMENT: str = "development"

    # Local resume templates + where tailored application packages are written
    RESUME_SOURCE_DIR: str = r"C:\Users\Asus\Downloads\resume based on JD"
    # Empty = write company folders under RESUME_SOURCE_DIR
    APPLICATION_PACKAGE_DIR: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()
