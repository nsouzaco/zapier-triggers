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
    dynamodb_events_table: Optional[str] = None
    dynamodb_table_name: Optional[str] = None  # Alias for dynamodb_events_table

    # RDS PostgreSQL Configuration
    rds_endpoint: Optional[str] = None
    rds_port: int = 5432
    rds_database: str = "triggers_api"
    rds_username: str = "triggers_api"
    rds_password: Optional[str] = None
    database_url: Optional[str] = None
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis Configuration
    redis_endpoint: Optional[str] = None
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

    # Email Service (Resend)
    resend_api_key: Optional[str] = None
    urgent_jira_email_recipient: str = "notifications@example.com"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() in ("development", "dev")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        host = self.redis_endpoint or self.redis_host
        if self.redis_password:
            return f"redis://:{self.redis_password}@{host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{host}:{self.redis_port}/{self.redis_db}"

    @property
    def postgresql_url(self) -> str:
        """Get PostgreSQL connection URL."""
        # ALWAYS use RDS - we don't use local database
        # Priority: RDS configuration > explicit DATABASE_URL (if pointing to RDS)
        import os
        is_lambda = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
        is_aws = os.environ.get("AWS_EXECUTION_ENV") is not None or is_lambda
        
        # In AWS/Lambda, ALWAYS use RDS - never use local database
        if is_aws:
            if not (self.rds_endpoint and self.rds_username and self.rds_password):
                raise ValueError(
                    "Running in AWS but RDS configuration is missing. "
                    "Set RDS_ENDPOINT, RDS_USERNAME, and RDS_PASSWORD environment variables."
                )
            # RDS endpoint may already include port (e.g., "hostname:5432")
            # If it does, use it as-is; otherwise append the port
            endpoint = self.rds_endpoint
            if ":" not in endpoint.split("/")[-1]:  # Check if port is already in endpoint
                endpoint = f"{endpoint}:{self.rds_port}"
            return f"postgresql://{self.rds_username}:{self.rds_password}@{endpoint}/{self.rds_database}"
        
        # Local development: ALWAYS use RDS if configured
        # We don't use local database - everything goes to RDS
        if self.rds_endpoint and self.rds_username and self.rds_password:
            endpoint = self.rds_endpoint
            if ":" not in endpoint.split("/")[-1]:
                endpoint = f"{endpoint}:{self.rds_port}"
            return f"postgresql://{self.rds_username}:{self.rds_password}@{endpoint}/{self.rds_database}"
        
        # If DATABASE_URL is explicitly set and points to RDS, use it
        # (This allows override for testing, but should point to RDS, not localhost)
        if self.database_url:
            # Warn if trying to use localhost
            if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
                import warnings
                warnings.warn(
                    "DATABASE_URL points to localhost. This is not recommended. "
                    "All operations should use RDS. Set RDS_ENDPOINT, RDS_USERNAME, and RDS_PASSWORD instead.",
                    UserWarning
                )
            return self.database_url
        
        # No RDS configuration available - raise error instead of falling back to localhost
        raise ValueError(
            "RDS configuration is required. Set RDS_ENDPOINT, RDS_USERNAME, and RDS_PASSWORD environment variables. "
            "Local database is not used - all operations must use AWS RDS."
        )

    @property
    def dynamodb_table(self) -> str:
        """Get DynamoDB table name."""
        return self.dynamodb_table_name or self.dynamodb_events_table or "triggers-api-events-dev"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

