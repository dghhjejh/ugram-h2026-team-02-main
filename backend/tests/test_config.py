import pytest
from src.application.config import Settings


def test_defaults_to_local_database_url() -> None:
    settings = Settings(
        _env_file=None,
        SECRET_KEY="test-secret-key-for-testing-only",
        APP_ENV="testing",
    )

    assert settings.DATABASE_MODE == "local"
    assert settings.SQL_ECHO is False
    assert settings.TRENDING_CACHE_TTL_SECONDS == 5
    assert settings.S3_VIEW_URL_CACHE_TTL_SECONDS == 300
    assert settings.S3_VIEW_URL_CACHE_MAX_ENTRIES == 1000
    assert settings.resolved_database_url == "postgresql://user:pass@localhost:5433/ugram"


def test_local_mode_ignores_database_url_in_non_prod() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="testing",
        SECRET_KEY="test-secret-key-for-testing-only",
        DATABASE_MODE="local",
        DATABASE_URL="postgresql://user:pass@legacy-host:5432/ugram",
    )

    assert settings.resolved_database_url == "postgresql://user:pass@localhost:5433/ugram"


def test_local_mode_uses_rds_database_url_in_production() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="prod-secret-key-not-weak",
        FRONTEND_URL="https://ugram.example",
        DATABASE_MODE="local",
        RDS_DATABASE_URL="postgresql://user:pass@prod-rds:5432/ugram",
    )

    assert settings.resolved_database_url == "postgresql://user:pass@prod-rds:5432/ugram"


def test_local_mode_falls_back_to_database_url_in_production() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="prod-secret-key-not-weak",
        FRONTEND_URL="https://ugram.example",
        DATABASE_MODE="local",
        DATABASE_URL="postgresql://user:pass@legacy-prod:5432/ugram",
    )

    assert settings.resolved_database_url == "postgresql://user:pass@legacy-prod:5432/ugram"


def test_local_mode_requires_rds_or_database_url_in_production() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="prod-secret-key-not-weak",
        FRONTEND_URL="https://ugram.example",
        DATABASE_MODE="local",
    )
    with pytest.raises(ValueError, match="RDS_DATABASE_URL"):
        _ = settings.resolved_database_url


def test_rds_mode_uses_rds_database_url() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="testing",
        SECRET_KEY="test-secret-key-for-testing-only",
        DATABASE_MODE="rds",
        RDS_DATABASE_URL="postgresql://user:pass@prod-rds:5432/ugram",
    )

    assert settings.resolved_database_url == "postgresql://user:pass@prod-rds:5432/ugram"


def test_custom_mode_uses_database_url_alias() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="testing",
        SECRET_KEY="test-secret-key-for-testing-only",
        DATABASE_MODE="custom",
        DATABASE_URL="postgresql://user:pass@custom-host:5432/ugram",
    )

    assert settings.resolved_database_url == "postgresql://user:pass@custom-host:5432/ugram"


def test_rds_mode_requires_rds_database_url() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="testing",
        SECRET_KEY="test-secret-key-for-testing-only",
        DATABASE_MODE="rds",
    )
    with pytest.raises(ValueError, match="RDS_DATABASE_URL"):
        _ = settings.resolved_database_url


def test_rds_mode_falls_back_to_database_url_for_backward_compatibility() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="testing",
        SECRET_KEY="test-secret-key-for-testing-only",
        DATABASE_MODE="rds",
        DATABASE_URL="postgresql://user:pass@legacy-rds-host:5432/ugram",
    )

    assert settings.resolved_database_url == "postgresql://user:pass@legacy-rds-host:5432/ugram"
