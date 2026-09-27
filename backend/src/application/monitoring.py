"""Observability setup for external monitoring providers."""

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.scrubber import DEFAULT_DENYLIST, DEFAULT_PII_DENYLIST, EventScrubber

from .config import Settings

_NON_PROD_ENVIRONMENTS = {"development", "dev", "local", "test", "testing"}
_sentry_initialized = False
_REDACTED = "[Filtered]"
_SENSITIVE_KEY_TOKENS = (
    "authorization",
    "cookie",
    "apikey",
    "token",
    "secret",
    "password",
    "session",
    "csrf",
    "xsrf",
)
_URL_KEY_TOKENS = ("url", "href", "location", "requesturl")


def _default_traces_sample_rate(app_env: str) -> float:
    return 1.0 if app_env.lower() in _NON_PROD_ENVIRONMENTS else 0.1


def _default_profile_session_sample_rate(app_env: str) -> float:
    return 1.0 if app_env.lower() in _NON_PROD_ENVIRONMENTS else 0.0


def _normalize_key(key: str) -> str:
    return "".join(character for character in key.lower() if character.isalnum())


def _is_sensitive_key(key: str) -> bool:
    normalized_key = _normalize_key(key)
    return any(token in normalized_key for token in _SENSITIVE_KEY_TOKENS)


def _is_url_key(key: str) -> bool:
    normalized_key = _normalize_key(key)
    return any(normalized_key == token or normalized_key.endswith(token) for token in _URL_KEY_TOKENS)


def _strip_query_and_fragment(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _scrub_value(value: Any, key: str | None = None) -> Any:
    if key and _is_sensitive_key(key):
        return _REDACTED

    if isinstance(value, Mapping):
        scrubbed_mapping: dict[str, Any] = {}
        for child_key, child_value in value.items():
            if _is_sensitive_key(child_key):
                scrubbed_mapping[child_key] = _REDACTED
            elif isinstance(child_value, str) and _is_url_key(child_key):
                scrubbed_mapping[child_key] = _strip_query_and_fragment(child_value)
            else:
                scrubbed_mapping[child_key] = _scrub_value(child_value, child_key)
        return scrubbed_mapping

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_scrub_value(item, key) for item in value]

    if isinstance(value, str) and key and _is_url_key(key):
        return _strip_query_and_fragment(value)

    return value


def _build_scrub_callback(send_default_pii: bool) -> Any:
    def _scrub_event(event: dict[str, Any], _hint: object) -> dict[str, Any]:
        scrubbed_event = _scrub_value(event)

        if not isinstance(scrubbed_event, dict):
            return event

        if not send_default_pii and isinstance(scrubbed_event.get("user"), dict):
            scrubbed_event["user"].pop("email", None)
            scrubbed_event["user"].pop("ip_address", None)

        transaction = scrubbed_event.get("transaction")
        if isinstance(transaction, str):
            scrubbed_event["transaction"] = _strip_query_and_fragment(transaction)

        return scrubbed_event

    return _scrub_event


def _build_event_scrubber(send_default_pii: bool) -> EventScrubber:
    pii_denylist = ["phone_number"]
    if not send_default_pii:
        pii_denylist = [*DEFAULT_PII_DENYLIST, "email", *pii_denylist]

    return EventScrubber(
        send_default_pii=send_default_pii,
        denylist=[*DEFAULT_DENYLIST, "access_token", "refresh_token", "id_token", "x_api_key"],
        pii_denylist=list(dict.fromkeys(pii_denylist)),
        recursive=True,
    )


def configure_sentry(settings: Settings) -> None:
    """Initialize Sentry once when a DSN is configured for the app."""
    global _sentry_initialized

    if _sentry_initialized or settings.is_test_env or not settings.SENTRY_DSN:
        return

    scrub_callback = _build_scrub_callback(settings.SENTRY_SEND_DEFAULT_PII)

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT or settings.APP_ENV.lower(),
        release=settings.SENTRY_RELEASE,
        send_default_pii=settings.SENTRY_SEND_DEFAULT_PII,
        enable_logs=settings.SENTRY_ENABLE_LOGS,
        traces_sample_rate=(
            settings.SENTRY_TRACES_SAMPLE_RATE
            if settings.SENTRY_TRACES_SAMPLE_RATE is not None
            else _default_traces_sample_rate(settings.APP_ENV)
        ),
        profile_session_sample_rate=(
            settings.SENTRY_PROFILE_SESSION_SAMPLE_RATE
            if settings.SENTRY_PROFILE_SESSION_SAMPLE_RATE is not None
            else _default_profile_session_sample_rate(settings.APP_ENV)
        ),
        profile_lifecycle="trace",
        event_scrubber=_build_event_scrubber(settings.SENTRY_SEND_DEFAULT_PII),
        before_send=scrub_callback,
        before_send_transaction=scrub_callback,
        integrations=[
            StarletteIntegration(middleware_spans=True),
            FastApiIntegration(middleware_spans=True),
        ],
    )
    _sentry_initialized = True
