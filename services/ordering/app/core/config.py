from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://smartserve:smartserve@localhost:5432/smartserve"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # Auth
    SECRET_KEY: str = "change-me-in-production-use-a-256-bit-random-string"
    AUTH_SERVICE_URL: str = "http://auth:8000"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:8081"]

    # PIN brute-force protection (manager override)
    MAX_PIN_ATTEMPTS: int = 5
    PIN_LOCKOUT_MINUTES: int = 15


settings = Settings()
