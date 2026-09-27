"""API tests for authentication endpoints.

Tests cover:
- User registration with password
- Login and token generation
- Token validation and current user retrieval
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

# Test Constants
VALID_PASSWORD = "SecurePassword123!"  # pragma: allowlist secret
SHORT_PASSWORD = "short"  # pragma: allowlist secret
WRONG_PASSWORD = "WrongPassword123!"  # pragma: allowlist secret
INVALID_TOKEN = "invalid.token.here"
MALFORMED_TOKEN = "notavalidjwttoken"
EMPTY_STRING = ""

DEFAULT_FIRST_NAME = "Test"
DEFAULT_LAST_NAME = "User"

TOKEN_TYPE_BEARER = "bearer"
CONTENT_TYPE_FORM = "application/x-www-form-urlencoded"

# HTTP Status Codes
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_401_UNAUTHORIZED = 401
HTTP_409_CONFLICT = 409
HTTP_422_UNPROCESSABLE_ENTITY = 422

# API Endpoints
ENDPOINT_REGISTER = "/users/register"
ENDPOINT_TOKEN = "/users/token"
ENDPOINT_REFRESH = "/users/refresh"
ENDPOINT_CURRENT_USER = "/users/me"

# Cookie names
REFRESH_TOKEN_COOKIE_NAME = "ugram_refresh_token"

# Error Messages
ERROR_INCORRECT_CREDENTIALS = "Incorrect username or password"
ERROR_INVALID_CREDENTIALS = "Could not validate credentials"


class AuthAPIClient:
    """Helper class for authentication API operations."""

    def __init__(self, client: TestClient) -> None:
        self.client = client

    def register(self, username: str, email: str, password: str, **kwargs: Any) -> tuple[int, dict[str, Any]]:  # noqa: ANN401
        """Register a new user."""
        payload = {  # type: ignore[misc]
            "username": username,
            "email": email,
            "first_name": kwargs.get("first_name", DEFAULT_FIRST_NAME),
            "last_name": kwargs.get("last_name", DEFAULT_LAST_NAME),
            "user_password": password,
        }
        if "phone_number" in kwargs:
            payload["phone_number"] = kwargs["phone_number"]
        if "profile_photo_url" in kwargs:
            payload["profile_photo_url"] = kwargs["profile_photo_url"]

        response = self.client.post(ENDPOINT_REGISTER, json=payload)
        return response.status_code, response.json()

    def login(self, username: str, password: str) -> tuple[int, dict[str, Any]]:
        """Login and get access token."""
        response = self.client.post(
            ENDPOINT_TOKEN,
            data={"username": username, "password": password},
            headers={"Content-Type": CONTENT_TYPE_FORM},
        )
        return response.status_code, response.json()

    def get_current_user(self, token: str) -> tuple[int, dict[str, Any]]:
        """Get current authenticated user."""
        response = self.client.get(
            ENDPOINT_CURRENT_USER,
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.status_code, response.json()

    def refresh(self, override_token: str | None = None) -> tuple[int, dict[str, Any]]:
        """Exchange the refresh token cookie for a new access token.

        Pass override_token to test behaviour with a specific token value
        (e.g. an invalid or expired token) instead of the session cookie.
        """
        if override_token is not None:
            self.client.cookies.set(REFRESH_TOKEN_COOKIE_NAME, override_token)
        response = self.client.post(ENDPOINT_REFRESH)
        return response.status_code, response.json()


@pytest.fixture
def auth_api(client: TestClient) -> AuthAPIClient:
    """Provide an AuthAPIClient wrapper."""
    return AuthAPIClient(client)


@pytest.fixture
def registered_user(auth_api: AuthAPIClient) -> dict[str, Any]:
    """Create and return a registered user with known credentials."""
    username = "testuser"
    password = VALID_PASSWORD
    email = "test@example.com"

    status, user = auth_api.register(
        username=username,
        email=email,
        password=password,
        first_name=DEFAULT_FIRST_NAME,
        last_name=DEFAULT_LAST_NAME,
    )
    assert status == HTTP_201_CREATED

    return {
        "user_data": user,
        "username": username,
        "password": password,
        "email": email,
    }


class TestUserRegistration:
    """Tests for user registration with password."""

    def test_given_valid_credentials_when_registering_then_returns_user_without_password(
        self, auth_api: AuthAPIClient
    ) -> None:
        """User registration should return profile without exposing password."""
        username = "newuser"
        email = "new@example.com"
        password = VALID_PASSWORD

        status, data = auth_api.register(
            username=username,
            email=email,
            password=password,
            first_name="New",
            last_name="User",
        )

        assert status == HTTP_201_CREATED
        assert data["username"] == username
        assert data["email"] == email
        assert "password" not in data
        assert "user_password" not in data
        assert "id" in data

    def test_given_short_password_when_registering_then_returns_validation_error(self, auth_api: AuthAPIClient) -> None:
        """Password validation should reject passwords shorter than 8 characters."""
        username = "shortpass"
        email = "short@example.com"
        password = SHORT_PASSWORD

        status, _ = auth_api.register(username=username, email=email, password=password)

        assert status == HTTP_422_UNPROCESSABLE_ENTITY

    def test_given_existing_username_when_registering_then_returns_conflict(
        self, auth_api: AuthAPIClient, registered_user: dict[str, Any]
    ) -> None:
        """System should prevent duplicate usernames."""
        existing_username = registered_user["username"]
        different_email = "different@example.com"
        password = VALID_PASSWORD

        status, _ = auth_api.register(username=existing_username, email=different_email, password=password)

        assert status == HTTP_409_CONFLICT


class TestLogin:
    """Tests for login and token generation."""

    def test_given_valid_credentials_when_logging_in_then_returns_access_token(
        self, auth_api: AuthAPIClient, registered_user: dict[str, Any]
    ) -> None:
        """Valid credentials should generate a JWT access token."""
        username = registered_user["username"]
        password = registered_user["password"]

        status, data = auth_api.login(username=username, password=password)

        assert status == HTTP_200_OK
        assert "access_token" in data
        assert "refresh_token" not in data
        assert data["token_type"] == TOKEN_TYPE_BEARER

    def test_given_wrong_password_when_logging_in_then_returns_unauthorized(
        self, auth_api: AuthAPIClient, registered_user: dict[str, Any]
    ) -> None:
        """Incorrect password should be rejected with 401."""
        username = registered_user["username"]
        wrong_password = WRONG_PASSWORD

        status, data = auth_api.login(username=username, password=wrong_password)

        assert status == HTTP_401_UNAUTHORIZED
        assert "detail" in data
        assert ERROR_INCORRECT_CREDENTIALS in data["detail"]

    def test_given_nonexistent_user_when_logging_in_then_returns_unauthorized(self, auth_api: AuthAPIClient) -> None:
        """Non-existent username should be rejected with 401."""
        nonexistent_username = "nonexistent"
        password = VALID_PASSWORD

        status, _ = auth_api.login(username=nonexistent_username, password=password)

        assert status == HTTP_401_UNAUTHORIZED

    def test_given_empty_credentials_when_logging_in_then_returns_validation_error(
        self, auth_api: AuthAPIClient
    ) -> None:
        """Empty credentials should fail validation."""
        empty_username = EMPTY_STRING
        empty_password = EMPTY_STRING

        response = auth_api.client.post(
            ENDPOINT_TOKEN,
            data={"username": empty_username, "password": empty_password},
            headers={"Content-Type": CONTENT_TYPE_FORM},
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY


class TestCurrentUser:
    """Tests for retrieving current authenticated user."""

    def test_given_valid_token_when_accessing_me_then_returns_user_profile(
        self, auth_api: AuthAPIClient, registered_user: dict[str, Any]
    ) -> None:
        """Valid JWT token should grant access to user profile."""
        # Given - Login to get token
        _, token_response = auth_api.login(
            username=registered_user["username"],
            password=registered_user["password"],
        )
        token = token_response["access_token"]

        # When
        status, user_data = auth_api.get_current_user(token)

        # Then
        assert status == HTTP_200_OK
        assert user_data["username"] == registered_user["username"]
        assert user_data["email"] == registered_user["email"]
        assert user_data["id"] == registered_user["user_data"]["id"]
        assert "password" not in user_data

    def test_given_no_token_when_accessing_me_then_returns_unauthorized(self, client: TestClient) -> None:
        """Missing token should be rejected with 401."""
        # Given - No token provided

        # When
        response = client.get(ENDPOINT_CURRENT_USER)

        # Then
        assert response.status_code == HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()

    def test_given_invalid_token_when_accessing_me_then_returns_unauthorized(self, auth_api: AuthAPIClient) -> None:
        """Invalid JWT token should be rejected with 401."""
        # Given
        invalid_token = INVALID_TOKEN

        # When
        status, data = auth_api.get_current_user(invalid_token)

        # Then
        assert status == HTTP_401_UNAUTHORIZED
        assert ERROR_INVALID_CREDENTIALS in data["detail"]

    def test_given_malformed_token_when_accessing_me_then_returns_unauthorized(self, auth_api: AuthAPIClient) -> None:
        """Malformed token should be rejected with 401."""
        # Given
        malformed_token = MALFORMED_TOKEN

        # When
        status, _ = auth_api.get_current_user(malformed_token)

        # Then
        assert status == HTTP_401_UNAUTHORIZED


class TestTokenIsolation:
    """Tests for token isolation between users."""

    def test_given_two_users_when_using_token_then_cannot_access_other_user_data(
        self, auth_api: AuthAPIClient, registered_user: dict[str, Any]
    ) -> None:
        """Token isolation: user A's token should only access user A's data."""
        # Given - Create second user
        status, _ = auth_api.register(
            username="otheruser",
            email="other@example.com",
            password=VALID_PASSWORD,
        )
        assert status == HTTP_201_CREATED

        # Given - Login as first user
        _, token_response = auth_api.login(
            username=registered_user["username"],
            password=registered_user["password"],
        )
        token = token_response["access_token"]

        # When
        _, current_user = auth_api.get_current_user(token)

        # Then - Should return first user, not second
        assert current_user["username"] == registered_user["username"]
        assert current_user["username"] != "otheruser"


class TestRefreshToken:
    """Tests for the refresh token endpoint."""

    def test_given_valid_refresh_token_when_refreshing_then_returns_new_tokens(
        self, auth_api: AuthAPIClient, registered_user: dict[str, Any]
    ) -> None:
        """Valid refresh token cookie set by login should return a new access token."""
        # Given - login sets the refresh token cookie on the test client session
        auth_api.login(
            username=registered_user["username"],
            password=registered_user["password"],
        )

        # When
        status, data = auth_api.refresh()

        # Then
        assert status == HTTP_200_OK
        assert "access_token" in data
        assert "refresh_token" not in data
        assert data["token_type"] == TOKEN_TYPE_BEARER

    def test_given_new_access_token_when_accessing_me_then_returns_user(
        self, auth_api: AuthAPIClient, registered_user: dict[str, Any]
    ) -> None:
        """New access token from refresh should grant access to protected endpoints."""
        # Given
        auth_api.login(
            username=registered_user["username"],
            password=registered_user["password"],
        )
        _, refresh_response = auth_api.refresh()
        new_access_token = refresh_response["access_token"]

        # When
        status, user_data = auth_api.get_current_user(new_access_token)

        # Then
        assert status == HTTP_200_OK
        assert user_data["username"] == registered_user["username"]

    def test_given_invalid_refresh_token_when_refreshing_then_returns_unauthorized(
        self, auth_api: AuthAPIClient
    ) -> None:
        """Invalid refresh token cookie should be rejected with 401."""
        # When
        status, data = auth_api.refresh(override_token=INVALID_TOKEN)

        # Then
        assert status == HTTP_401_UNAUTHORIZED
        assert "detail" in data

    def test_given_no_refresh_token_cookie_when_refreshing_then_returns_unauthorized(
        self, auth_api: AuthAPIClient
    ) -> None:
        """Missing refresh token cookie should be rejected with 401."""
        # When - no prior login, no cookie
        status, data = auth_api.refresh()

        # Then
        assert status == HTTP_401_UNAUTHORIZED
        assert "detail" in data

    def test_given_access_token_as_refresh_token_when_refreshing_then_returns_unauthorized(
        self, auth_api: AuthAPIClient, registered_user: dict[str, Any]
    ) -> None:
        """Access token must not be accepted as a refresh token."""
        # Given
        _, token_response = auth_api.login(
            username=registered_user["username"],
            password=registered_user["password"],
        )
        access_token = token_response["access_token"]

        # When - override the cookie with the access token
        status, data = auth_api.refresh(override_token=access_token)

        # Then
        assert status == HTTP_401_UNAUTHORIZED

    def test_given_expired_refresh_token_when_refreshing_then_returns_unauthorized(
        self, auth_api: AuthAPIClient
    ) -> None:
        """Expired refresh token should be rejected with 401."""
        from datetime import UTC, datetime, timedelta

        import jwt

        # Given - craft an already-expired refresh token
        expired_token = jwt.encode(
            {"sub": "someuser", "type": "refresh", "exp": datetime.now(UTC) - timedelta(seconds=1)},
            "test-secret-key-for-testing-only",  # nosec B106
            algorithm="HS256",
        )

        # When
        status, _ = auth_api.refresh(override_token=expired_token)

        # Then
        assert status == HTTP_401_UNAUTHORIZED
