"""Configuration management for the Zapier Triggers API."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = "development"

    # API Configuration
    api_title: str = "Zapier Triggers API"
    api_version: str = "1.0.0"
    api_description: str = "Unified event-driven API for triggering Zapier workflows"

    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # SQS Configuration
    sqs_event_queue_url: Optional[str] = None
    sqs_dlq_url: Optional[str] = None

    # DynamoDB Configuration
    dynamodb_events_table: str = "triggers-api-events-dev"

    # RDS PostgreSQL Configuration
    database_url: str = "postgresql://triggers_api:triggers_api_dev@localhost:5432/triggers_api_dev"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Rate Limiting
    rate_limit_per_second: int = 1000
    rate_limit_window_seconds: int = 1

    # Idempotency
    idempotency_ttl_hours: int = 24

    # Webhook Configuration
    webhook_timeout_seconds: int = 30
    webhook_max_retries: int = 5
    webhook_retry_backoff_base: float = 2.0
    webhook_retry_max_delay_seconds: int = 86400  # 24 hours

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Security
    api_key_header: str = "Authorization"
    api_key_prefix: str = "Bearer"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

