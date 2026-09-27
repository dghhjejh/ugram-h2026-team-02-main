"""API tests for Google OAuth authentication endpoints."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from src.adapters.inbound.api.google import _verify_google_token
from src.application.config import settings
from src.domain.users.helpers.auth import create_access_token

MOCK_GOOGLE_ID = "google_123456789"
MOCK_EMAIL = "test@example.com"
MOCK_FIRST_NAME = "John"
MOCK_LAST_NAME = "Doe"
MOCK_USERNAME = "johndoe"
MOCK_AUTH_CODE = "mock_auth_code_from_google"
MOCK_ID_TOKEN = "mock.jwt.token"

GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "test-client-secret"  # pragma: allowlist secret
GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/google/callback"
FRONTEND_URL = "http://localhost:3000"

ENDPOINT_GOOGLE_LOGIN = "/auth/google/login"
ENDPOINT_GOOGLE_CALLBACK = "/auth/google/callback"
ENDPOINT_GOOGLE_REGISTER = "/auth/google/register"


def _registration_token(
    google_id: str = MOCK_GOOGLE_ID,
    email: str = MOCK_EMAIL,
    first_name: str = MOCK_FIRST_NAME,
    last_name: str = MOCK_LAST_NAME,
) -> str:
    return create_access_token(
        {
            "token_use": "google_registration",
            "google_id": google_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }
    )


def _start_google_login(client: TestClient) -> str:
    response = client.get(ENDPOINT_GOOGLE_LOGIN, follow_redirects=False)
    assert response.status_code == 307

    location = response.headers["location"]
    query = parse_qs(urlparse(location).query)
    state = query["state"][0]

    assert client.cookies.get(settings.OAUTH_STATE_COOKIE_NAME) == state
    return state


@pytest.fixture(autouse=True)
def mock_google_settings() -> Generator[None]:
    previous_values = {
        "GOOGLE_AUTH_URL": settings.GOOGLE_AUTH_URL,
        "GOOGLE_TOKEN_URL": settings.GOOGLE_TOKEN_URL,
        "GOOGLE_CERTS_URL": settings.GOOGLE_CERTS_URL,
        "GOOGLE_REDIRECT_URI": settings.GOOGLE_REDIRECT_URI,
        "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
        "FRONTEND_URL": settings.FRONTEND_URL,
    }

    settings.GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    settings.GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    settings.GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
    settings.GOOGLE_REDIRECT_URI = GOOGLE_REDIRECT_URI
    settings.GOOGLE_CLIENT_ID = GOOGLE_CLIENT_ID
    settings.GOOGLE_CLIENT_SECRET = GOOGLE_CLIENT_SECRET
    settings.FRONTEND_URL = FRONTEND_URL
    yield

    for key, value in previous_values.items():
        setattr(settings, key, value)


@pytest.fixture
def mock_google_token_payload() -> dict[str, str]:
    return {
        "iss": "https://accounts.google.com",
        "sub": MOCK_GOOGLE_ID,
        "email": MOCK_EMAIL,
        "given_name": MOCK_FIRST_NAME,
        "family_name": MOCK_LAST_NAME,
        "aud": GOOGLE_CLIENT_ID,
    }


class TestGoogleLogin:
    def test_google_login_redirect_sets_state_cookie(self, client: TestClient) -> None:
        response = client.get(ENDPOINT_GOOGLE_LOGIN, follow_redirects=False)

        assert response.status_code == 307
        redirect_url = response.headers["location"]
        parsed = urlparse(redirect_url)
        query = parse_qs(parsed.query)

        assert parsed.netloc == "accounts.google.com"
        assert query["client_id"] == [GOOGLE_CLIENT_ID]
        assert query["response_type"] == ["code"]
        assert query["redirect_uri"] == [GOOGLE_REDIRECT_URI]
        assert query["state"][0]
        assert client.cookies.get(settings.OAUTH_STATE_COOKIE_NAME) == query["state"][0]


class TestGoogleCallback:
    @patch("src.adapters.inbound.api.google.httpx.AsyncClient")
    @patch("src.adapters.inbound.api.google._verify_google_token")
    def test_callback_existing_user_redirects_with_fragment_token(
        self,
        mock_verify: MagicMock,
        mock_httpx: MagicMock,
        client: TestClient,
        mock_google_token_payload: dict[str, Any],
    ) -> None:
        register_response = client.post(
            ENDPOINT_GOOGLE_REGISTER,
            json={"registration_token": _registration_token(), "username": MOCK_USERNAME},
        )
        assert register_response.status_code == 200

        state = _start_google_login(client)
        mock_client_instance = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"id_token": MOCK_ID_TOKEN}
        mock_client_instance.post.return_value = mock_token_response
        mock_verify.return_value = mock_google_token_payload

        response = client.get(
            ENDPOINT_GOOGLE_CALLBACK,
            params={"code": MOCK_AUTH_CODE, "state": state},
            follow_redirects=False,
        )

        assert response.status_code == 307
        assert response.headers["location"].startswith(f"{FRONTEND_URL}/auth/callback#token=")
        assert client.cookies.get(settings.OAUTH_STATE_COOKIE_NAME) is None
        assert response.headers["Cache-Control"] == "no-store"

    @patch("src.adapters.inbound.api.google.httpx.AsyncClient")
    @patch("src.adapters.inbound.api.google._verify_google_token")
    def test_callback_new_user_redirects_to_registration_fragment(
        self,
        mock_verify: MagicMock,
        mock_httpx: MagicMock,
        client: TestClient,
        mock_google_token_payload: dict[str, Any],
    ) -> None:
        state = _start_google_login(client)
        mock_client_instance = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"id_token": MOCK_ID_TOKEN}
        mock_client_instance.post.return_value = mock_token_response
        mock_verify.return_value = mock_google_token_payload

        response = client.get(
            ENDPOINT_GOOGLE_CALLBACK,
            params={"code": MOCK_AUTH_CODE, "state": state},
            follow_redirects=False,
        )

        assert response.status_code == 307
        assert response.headers["location"].startswith(f"{FRONTEND_URL}/register#token=")

    def test_callback_rejects_missing_state(self, client: TestClient) -> None:
        _start_google_login(client)

        response = client.get(ENDPOINT_GOOGLE_CALLBACK, params={"code": MOCK_AUTH_CODE})

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid OAuth state"

    @patch("src.adapters.inbound.api.google.logger")
    @patch("src.adapters.inbound.api.google.httpx.AsyncClient")
    def test_callback_token_exchange_failure(
        self,
        mock_httpx: MagicMock,
        mock_logger: MagicMock,
        client: TestClient,
    ) -> None:
        state = _start_google_login(client)
        mock_client_instance = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance
        mock_token_response = MagicMock()
        mock_token_response.status_code = 400
        mock_token_response.text = "exchange failed"
        mock_client_instance.post.return_value = mock_token_response

        response = client.get(
            ENDPOINT_GOOGLE_CALLBACK,
            params={"code": MOCK_AUTH_CODE, "state": state},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Google token exchange failed"
        mock_logger.warning.assert_called_once_with("Google token exchange failed with status %s", 400)

    @patch("src.adapters.inbound.api.google.httpx.AsyncClient")
    @patch("src.adapters.inbound.api.google._verify_google_token")
    def test_callback_invalid_google_token(
        self,
        mock_verify: MagicMock,
        mock_httpx: MagicMock,
        client: TestClient,
    ) -> None:
        state = _start_google_login(client)
        mock_client_instance = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"id_token": MOCK_ID_TOKEN}
        mock_client_instance.post.return_value = mock_token_response
        mock_verify.side_effect = HTTPException(status_code=400, detail="Invalid Google token: bad signature")

        response = client.get(
            ENDPOINT_GOOGLE_CALLBACK,
            params={"code": MOCK_AUTH_CODE, "state": state},
        )

        assert response.status_code == 400
        assert "Invalid Google token" in response.json()["detail"]


class TestGoogleRegistration:
    def test_complete_registration_new_user(self, client: TestClient) -> None:
        response = client.post(
            ENDPOINT_GOOGLE_REGISTER,
            json={"registration_token": _registration_token(), "username": MOCK_USERNAME},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    def test_complete_registration_rejects_wrong_token_use(self, client: TestClient) -> None:
        invalid_token = create_access_token({"sub": MOCK_USERNAME})

        response = client.post(
            ENDPOINT_GOOGLE_REGISTER,
            json={"registration_token": invalid_token, "username": MOCK_USERNAME},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid registration token"


class TestGoogleTokenVerification:
    @patch("src.adapters.inbound.api.google.PyJWKClient")
    def test_verify_valid_token(
        self,
        mock_jwks_client: MagicMock,
        mock_google_token_payload: dict[str, Any],
    ) -> None:
        mock_client_instance = MagicMock()
        mock_jwks_client.return_value = mock_client_instance
        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock_key"
        mock_client_instance.get_signing_key_from_jwt.return_value = mock_signing_key

        with patch("src.adapters.inbound.api.google.jwt.decode") as mock_decode:
            mock_decode.return_value = mock_google_token_payload

            result = _verify_google_token(MOCK_ID_TOKEN, settings.GOOGLE_CERTS_URL or "", GOOGLE_CLIENT_ID)

            assert result == mock_google_token_payload
            mock_decode.assert_called_once_with(
                MOCK_ID_TOKEN,
                "mock_key",
                algorithms=["RS256"],
                audience=GOOGLE_CLIENT_ID,
                issuer="https://accounts.google.com",
                leeway=10,
            )

    @patch("src.adapters.inbound.api.google.PyJWKClient")
    def test_verify_invalid_token(self, mock_jwks_client: MagicMock) -> None:
        mock_client_instance = MagicMock()
        mock_jwks_client.return_value = mock_client_instance
        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock_key"
        mock_client_instance.get_signing_key_from_jwt.return_value = mock_signing_key

        with patch("src.adapters.inbound.api.google.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidTokenError("Invalid signature")

            with pytest.raises(HTTPException) as exc_info:
                _verify_google_token(MOCK_ID_TOKEN, settings.GOOGLE_CERTS_URL or "", GOOGLE_CLIENT_ID)

            assert exc_info.value.status_code == 400
            assert "Invalid Google token" in exc_info.value.detail
