from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"

    # Database — `ai_outbox` only; pending confirmations stay in Redis
    DATABASE_URL: str = "postgresql+asyncpg://smartserve:smartserve@localhost:5432/smartserve"

    # Auth — ai only ever verifies tokens issued by `auth`, it never issues its own
    SECRET_KEY: str = "change-me-in-production-use-a-256-bit-random-string"

    # Redis — pending executions and menu-import sessions
    REDIS_URL: str = "redis://redis:6379/0"

    # RabbitMQ — publishes ai.action_executed audit events, never consumes
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # Downstream services this stateless orchestrator calls into to execute confirmed actions
    AUTH_SERVICE_URL: str = "http://auth:8000"
    CATALOG_SERVICE_URL: str = "http://catalog:8000"
    PRINTING_SERVICE_URL: str = "http://printing:8000"
    REPORTING_SERVICE_URL: str = "http://reporting:8000"

    # AI — local first-tier model (optional; empty = disabled, falls through to Haiku)
    LOCAL_MODEL_PATH: str = ""
    LOCAL_MODEL_CONFIDENCE_THRESHOLD: float = 0.9

    ANTHROPIC_API_KEY: str = ""
    AI_INTENT_MODEL: str = "claude-haiku-4-5"  # fast, cheap — intent classification
    AI_COMPLEX_MODEL: str = "claude-sonnet-4-5"  # complex reasoning, menu import, reorg
    AI_INTENT_CONFIDENCE_THRESHOLD: float = 0.85

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:8081"]


settings = Settings()
