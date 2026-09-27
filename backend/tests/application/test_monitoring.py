from unittest.mock import Mock, patch, sentinel

from src.application.config import Settings
from src.application.monitoring import configure_sentry


def test_configure_sentry_skips_without_dsn(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SENTRY_DSN", raising=False)

    init = Mock()

    with (
        patch("src.application.monitoring._sentry_initialized", False),
        patch("src.application.monitoring.sentry_sdk.init", init),
    ):
        configure_sentry(Settings())

    init.assert_not_called()


def test_configure_sentry_initializes_with_configured_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-production")
    monkeypatch.setenv("FRONTEND_URL", "https://app.example.com")
    monkeypatch.setenv("SENTRY_DSN", "https://examplePublicKey@o0.ingest.sentry.io/0")
    monkeypatch.setenv("SENTRY_RELEASE", "backend@1.2.3")

    init = Mock()
    event_scrubber = Mock(return_value=sentinel.event_scrubber)

    with (
        patch("src.application.monitoring._sentry_initialized", False),
        patch("src.application.monitoring.EventScrubber", event_scrubber),
        patch("src.application.monitoring.sentry_sdk.init", init),
    ):
        configure_sentry(Settings())

    init.assert_called_once()
    init_kwargs = init.call_args.kwargs

    assert init_kwargs["dsn"] == "https://examplePublicKey@o0.ingest.sentry.io/0"
    assert init_kwargs["environment"] == "production"
    assert init_kwargs["release"] == "backend@1.2.3"
    assert init_kwargs["send_default_pii"] is False
    assert init_kwargs["enable_logs"] is False
    assert init_kwargs["traces_sample_rate"] == 0.1
    assert init_kwargs["profile_session_sample_rate"] == 0.0
    assert init_kwargs["profile_lifecycle"] == "trace"
    assert init_kwargs["event_scrubber"] is sentinel.event_scrubber
    assert len(init_kwargs["integrations"]) == 2

    scrubber_kwargs = event_scrubber.call_args.kwargs
    assert scrubber_kwargs["send_default_pii"] is False
    assert "email" in scrubber_kwargs["pii_denylist"]
    assert "phone_number" in scrubber_kwargs["pii_denylist"]


def test_configure_sentry_preserves_email_when_default_pii_enabled(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SENTRY_DSN", "https://examplePublicKey@o0.ingest.sentry.io/0")
    monkeypatch.setenv("SENTRY_SEND_DEFAULT_PII", "true")

    init = Mock()
    event_scrubber = Mock(return_value=sentinel.event_scrubber)

    with (
        patch("src.application.monitoring._sentry_initialized", False),
        patch("src.application.monitoring.EventScrubber", event_scrubber),
        patch("src.application.monitoring.sentry_sdk.init", init),
    ):
        configure_sentry(Settings())

    init_kwargs = init.call_args.kwargs
    assert init_kwargs["send_default_pii"] is True
    assert init_kwargs["event_scrubber"] is sentinel.event_scrubber

    scrubber_kwargs = event_scrubber.call_args.kwargs
    assert scrubber_kwargs["send_default_pii"] is True
    assert "email" not in scrubber_kwargs["pii_denylist"]
    assert "phone_number" in scrubber_kwargs["pii_denylist"]


def test_configure_sentry_is_idempotent(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SENTRY_DSN", "https://examplePublicKey@o0.ingest.sentry.io/0")

    init = Mock()

    with (
        patch("src.application.monitoring._sentry_initialized", True),
        patch("src.application.monitoring.sentry_sdk.init", init),
    ):
        configure_sentry(Settings())

    init.assert_not_called()
