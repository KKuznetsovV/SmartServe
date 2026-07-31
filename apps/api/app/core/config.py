from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://smartserve:smartserve@localhost:5432/smartserve"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    SECRET_KEY: str = "change-me-in-production-use-a-256-bit-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI
    ANTHROPIC_API_KEY: str = ""
    AI_INTENT_MODEL: str = "claude-haiku-4-5"  # fast, cheap — intent classification
    AI_COMPLEX_MODEL: str = "claude-sonnet-4-5"  # complex reasoning, report queries
    AI_INTENT_CONFIDENCE_THRESHOLD: float = 0.85

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8081"]

    # PIN brute-force protection
    MAX_PIN_ATTEMPTS: int = 5
    PIN_LOCKOUT_MINUTES: int = 15


settings = Settings()
