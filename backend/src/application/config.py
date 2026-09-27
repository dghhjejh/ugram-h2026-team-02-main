import os
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = os.getenv("ENV_FILE", ".env")
_NON_PROD_ENVIRONMENTS = {"development", "dev", "local", "test", "testing"}
_WEAK_SECRET_VALUES = {
    "secret",
    "test-secret-key-for-testing-only",
    "your-secret-key-here-change-this-in-production",
}


class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_MODE: Literal["local", "rds", "custom"] = "local"
    SQL_ECHO: bool = False
    TRENDING_CACHE_TTL_SECONDS: int = 5
    DATABASE_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "DB_URL"),
    )
    LOCAL_DATABASE_URL: str = "postgresql://user:pass@localhost:5433/ugram"  # pragma: allowlist secret
    RDS_DATABASE_URL: str | None = None
    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FRONTEND_URL: str | None = None
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str | None = None
    SENTRY_RELEASE: str | None = None
    SENTRY_SEND_DEFAULT_PII: bool = False
    SENTRY_ENABLE_LOGS: bool = False
    SENTRY_TRACES_SAMPLE_RATE: float | None = Field(default=None, ge=0.0, le=1.0)
    SENTRY_PROFILE_SESSION_SAMPLE_RATE: float | None = Field(default=None, ge=0.0, le=1.0)
    S3_BUCKET: str = "ugram-images-dev-315883835287"
    S3_REGION: str = "us-east-2"
    S3_UPLOAD_PREFIX: str = "images"
    S3_PRESIGN_TTL: int = 900  # seconds
    S3_VIEW_URL_CACHE_TTL_SECONDS: int = 300
    S3_VIEW_URL_CACHE_MAX_ENTRIES: int = 1000
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024
    REFRESH_TOKEN_COOKIE_NAME: str = "ugram_refresh_token"
    OAUTH_STATE_COOKIE_NAME: str = "ugram_oauth_state"
    OAUTH_STATE_TTL_SECONDS: int = 600
    GOOGLE_AUTH_URL: str | None = None
    GOOGLE_TOKEN_URL: str | None = None
    GOOGLE_CERTS_URL: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None  # optional explicit creds
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_SESSION_TOKEN: str | None = None
    AWS_PROFILE: str | None = None  # optional profile name for boto3
    AWS_SDK_LOAD_CONFIG: bool = False
    ALLOWED_IMAGE_CONTENT_TYPES: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    )

    # Load env from backend/.env and repo root .env (for task run from backend/)
    model_config = SettingsConfigDict(
        env_file=(ENV_FILE, f"../{ENV_FILE}"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_test_env(self) -> bool:
        return self.APP_ENV.lower() in {"test", "testing"}

    @property
    def use_secure_cookies(self) -> bool:
        return self.APP_ENV.lower() not in _NON_PROD_ENVIRONMENTS

    @property
    def resolved_database_url(self) -> str:
        if self.DATABASE_MODE == "local":
            if self.APP_ENV.lower() in _NON_PROD_ENVIRONMENTS:
                return self.LOCAL_DATABASE_URL
            if self.RDS_DATABASE_URL:
                return self.RDS_DATABASE_URL
            if self.DATABASE_URL:
                return self.DATABASE_URL
            raise ValueError(
                "RDS_DATABASE_URL must be set for production when DATABASE_MODE is 'local' "
                "(or provide DATABASE_URL/DB_URL for compatibility)"
            )
        if self.DATABASE_MODE == "rds":
            if self.RDS_DATABASE_URL:
                return self.RDS_DATABASE_URL
            if self.DATABASE_URL:
                return self.DATABASE_URL
            raise ValueError(
                "RDS_DATABASE_URL must be set when DATABASE_MODE is 'rds' "
                "(or provide DATABASE_URL/DB_URL for compatibility)"
            )
        if self.DATABASE_URL:
            return self.DATABASE_URL
        raise ValueError("DATABASE_URL (or DB_URL) must be set when DATABASE_MODE is 'custom'")

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        env = self.APP_ENV.lower()

        if env not in _NON_PROD_ENVIRONMENTS:
            if not self.SECRET_KEY:
                raise ValueError("SECRET_KEY must be set outside test and local development environments")
            if self.SECRET_KEY in _WEAK_SECRET_VALUES:
                raise ValueError("SECRET_KEY is using an insecure placeholder value")
            if not self.FRONTEND_URL:
                raise ValueError("FRONTEND_URL must be set outside test and local development environments")

        if self.SECRET_KEY and self.SECRET_KEY in _WEAK_SECRET_VALUES and env not in {"test", "testing"}:
            raise ValueError("SECRET_KEY is using an insecure placeholder value")

        return self


settings = Settings()
