from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


# Insecure defaults that must never ship as production SECRET_KEY
_WEAK_SECRET_KEYS = frozenset(
    {
        "",
        "super-secret-key-change-in-production",
        "change-me-long-random-secret-key",
        "secret",
        "changeme",
    }
)


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

    # Comma-separated browser origins. Empty + development → allow all (*).
    # Production requires an explicit list (never * with credentials).
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # External Services
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"

    # LLM — dual profiles; switch at runtime via PUT /api/v1/llm/provider
    LLM_PROVIDER: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    LLM_MODEL: str = "gpt-4o"
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_API_KEY: str = "ollama"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_MAX_TOKENS: int = 400
    OLLAMA_NUM_CTX: int = 2048
    OLLAMA_KEEP_ALIVE: str = "30m"
    OLLAMA_TIMEOUT_SECONDS: float = 300.0
    OLLAMA_NUM_THREAD: int = 0
    LLM_TIMEOUT_SECONDS: float = 45.0
    LLM_MAX_TOKENS: int = 700
    LLM_FORCE_MOCK: bool = False
    # When false (default), Canvas cannot select "mock" and agents never invent
    # fake JD/resume/recruiter content on LLM failure — errors surface instead.
    LLM_ALLOW_MOCK: bool = False

    CHECKPOINT_BACKEND: str = "postgres"

    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMS: int = 768

    ENVIRONMENT: str = "development"
    # When false (default in production), /auth/demo and /auth/credentials are disabled
    ALLOW_DEMO_AUTH: bool | None = None
    # When false (default in production), skip seeding demo/admin passwords
    SEED_DEV_USERS: bool | None = None

    # Portable defaults; Docker compose overrides to /data/resumes and /data/packages
    RESUME_SOURCE_DIR: str = "./data/resumes"
    APPLICATION_PACKAGE_DIR: str = "./data/packages"
    # Local Obsidian vault (Jay OS). Windows example:
    # OBSIDIAN_VAULT_PATH=C:\Users\Asus\OneDrive\Desktop\Jay OS
    # Docker: mount that folder to /data/obsidian and set OBSIDIAN_VAULT_PATH=/data/obsidian
    OBSIDIAN_VAULT_PATH: str = "./data/obsidian"
    OBSIDIAN_SYNC_ON_STAGE_CHANGE: bool = True

    # SMTP — optional; without it, outreach uses copy/mailto (no fake Sent in prod)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""

    # Optional Token Harbor gateway (OpenAI-compatible) — https://tokenharbor.ai/docs/getting-started/quickstart
    TOKENHARBOR_API_KEY: str = ""
    TOKENHARBOR_BASE_URL: str = "https://tokenharbor.ai/v1"
    # Structured agents: prefer a chat/completions model (not coding-only orchestra).
    # Prefer free catalog ids for daily Career OS agents (structured JSON).
    # See https://tokenharbor.ai/docs/api/models and /models — e.g. kimi-k3:free,
    # deepseek-v4-flash:free. Paid upgrades: deepseek-v4-flash, gpt-5.6-luna, claude-sonnet-5.
    TOKENHARBOR_MODEL: str = "kimi-k3:free"
    TOKENHARBOR_TIMEOUT_SECONDS: float = 90.0
    TOKENHARBOR_MAX_TOKENS: int = 1200

    # Phase C — gated Auto Apply (extension only; LinkedIn never allowed by default)
    AUTO_APPLY_ENABLED: bool = True
    AUTO_APPLY_REQUIRE_CONSENT: bool = True
    AUTO_APPLY_MAX_PER_HOUR: int = 8
    AUTO_APPLY_MAX_PER_DAY: int = 30
    AUTO_APPLY_MIN_CONFIDENCE: float = 0.72
    AUTO_APPLY_ALLOWLIST: str = (
        "boards.greenhouse.io,job-boards.greenhouse.io,jobs.lever.co,"
        "*.myworkdayjobs.com"
    )
    AUTO_APPLY_BLOCKLIST: str = "linkedin.com,www.linkedin.com"

    # Discovery: Vault job_portal KBs first; Remotive/RemoteOK/Arbeitnow fill gaps
    JOB_DISCOVERY_SOURCES: str = "vault_portals,remotive,remoteok,arbeitnow"
    JOB_DISCOVERY_PER_SOURCE: int = 3
    JOB_DISCOVERY_VAULT_LIMIT: int = 12
    JOB_DISCOVERY_MAX_RESULTS: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return (self.ENVIRONMENT or "").lower() in {"production", "prod"}

    @property
    def demo_auth_enabled(self) -> bool:
        if self.ALLOW_DEMO_AUTH is not None:
            return bool(self.ALLOW_DEMO_AUTH)
        return not self.is_production

    @property
    def seed_dev_users_enabled(self) -> bool:
        if self.SEED_DEV_USERS is not None:
            return bool(self.SEED_DEV_USERS)
        return not self.is_production

    def cors_origin_list(self) -> List[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw:
            return ["*"] if not self.is_production else []
        return [o.strip() for o in raw.split(",") if o.strip()]

    def auto_apply_allowlist(self) -> List[str]:
        return [o.strip().lower() for o in self.AUTO_APPLY_ALLOWLIST.split(",") if o.strip()]

    def auto_apply_blocklist(self) -> List[str]:
        return [o.strip().lower() for o in self.AUTO_APPLY_BLOCKLIST.split(",") if o.strip()]

    def job_discovery_source_list(self) -> List[str]:
        return [o.strip().lower() for o in self.JOB_DISCOVERY_SOURCES.split(",") if o.strip()]

    def validate_for_boot(self) -> None:
        """Raise in production when secrets / CORS are unsafe."""
        if not self.is_production:
            return
        key = (self.SECRET_KEY or "").strip()
        if key in _WEAK_SECRET_KEYS or len(key) < 32:
            raise RuntimeError(
                "Production requires SECRET_KEY of at least 32 characters "
                "(not the example/default value)."
            )
        origins = self.cors_origin_list()
        if not origins or origins == ["*"]:
            raise RuntimeError(
                "Production requires CORS_ORIGINS to be an explicit comma-separated "
                "list of frontend origins (not *)."
            )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
