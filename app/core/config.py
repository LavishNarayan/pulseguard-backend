from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "PulseGuard Industrial Telemetry Engine"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_SUPER_SECRET_KEY_2026"
    EDGE_API_KEY: str = "pg_edge_live_98a76b54c32d10e"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database (Async for FastAPI, Sync for Celery)
    ASYNC_DATABASE_URL: str = "postgresql+asyncpg://pulseguard:pulseguard@db:5432/pulseguard"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://pulseguard:pulseguard@db:5432/pulseguard"

    # Redis & Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Business Logic Thresholds
    ALERT_COOLDOWN_SECONDS: int = 300
    CRITICAL_RUL_THRESHOLD: float = 25.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
