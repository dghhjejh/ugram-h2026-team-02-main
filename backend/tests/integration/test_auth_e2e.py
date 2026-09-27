"""End-to-end tests for authentication flows.

Tests cover complete user journeys:
- Registration to protected resource access
- Multiple user interactions
- Session management
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

# Test Constants
VALID_PASSWORD = "SecurePassword123!"  # pragma: allowlist secret
TOKEN_TYPE_BEARER = "bearer"
CONTENT_TYPE_FORM = "application/x-www-form-urlencoded"

DEFAULT_FIRST_NAME = "Test"
DEFAULT_LAST_NAME = "User"

# HTTP Status Codes
HTTP_200_OK = 200
HTTP_201_CREATED = 201

# API Endpoints
ENDPOINT_REGISTER = "/users/register"
ENDPOINT_TOKEN = "/users/token"
ENDPOINT_CURRENT_USER = "/users/me"


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


@pytest.fixture
def auth_api(client: TestClient) -> AuthAPIClient:
    """Provide an AuthAPIClient wrapper."""
    return AuthAPIClient(client)


@pytest.fixture
def registered_and_logged_in_user(auth_api: AuthAPIClient) -> dict[str, Any]:
    """Fixture providing a registered user with an active token."""
    username = "e2euser"
    password = VALID_PASSWORD
    email = "e2e@example.com"

    # Register
    status, user = auth_api.register(username=username, email=email, password=password)
    assert status == HTTP_201_CREATED

    # Login
    status, token_data = auth_api.login(username=username, password=password)
    assert status == HTTP_200_OK

    return {
        "user_data": user,
        "username": username,
        "password": password,
        "email": email,
        "token": token_data["access_token"],
    }


class TestCompleteRegistrationFlow:
    """End-to-end tests for user registration."""

    def test_given_valid_data_when_user_registers_then_profile_is_created(self, auth_api: AuthAPIClient) -> None:
        """User can successfully register with valid credentials."""
        # Given
        username = "newregistered"
        password = VALID_PASSWORD
        email = "newregistered@example.com"

        # When
        status, user = auth_api.register(username=username, email=email, password=password)

        # Then
        assert status == HTTP_201_CREATED
        assert user["username"] == username
        assert user["email"] == email
        assert "id" in user
        assert "password" not in user


class TestCompleteLoginFlow:
    """End-to-end tests for user login."""

    def test_given_registered_user_when_logging_in_then_receives_valid_token(self, auth_api: AuthAPIClient) -> None:
        """Registered user can login and receive JWT token."""
        # Given - Register user first
        username = "loginuser"
        password = VALID_PASSWORD
        email = "login@example.com"
        status, _ = auth_api.register(username=username, email=email, password=password)
        assert status == HTTP_201_CREATED

        # When
        status, token_data = auth_api.login(username=username, password=password)

        # Then
        assert status == HTTP_200_OK
        assert "access_token" in token_data
        assert token_data["token_type"] == TOKEN_TYPE_BEARER


class TestProtectedResourceAccess:
    """End-to-end tests for accessing protected resources."""

    def test_given_authenticated_user_when_accessing_profile_then_returns_correct_data(
        self, auth_api: AuthAPIClient, registered_and_logged_in_user: dict[str, Any]
    ) -> None:
        """Authenticated user can access their profile via /users/me."""
        # Given
        token = registered_and_logged_in_user["token"]
        expected_username = registered_and_logged_in_user["username"]
        expected_user_id = registered_and_logged_in_user["user_data"]["id"]

        # When
        status, profile = auth_api.get_current_user(token)

        # Then
        assert status == HTTP_200_OK
        assert profile["id"] == expected_user_id
        assert profile["username"] == expected_username
        assert "password" not in profile


class TestMultipleUsersFlow:
    """End-to-end tests for multiple users interacting."""

    def test_given_two_users_when_both_login_then_tokens_are_different(self, auth_api: AuthAPIClient) -> None:
        """Two different users receive different authentication tokens."""
        # Given - User 1
        user1_username = "user1"
        user1_password = "User1Pass123!"  # pragma: allowlist secret
        user1_email = "user1@example.com"
        status, _ = auth_api.register(username=user1_username, email=user1_email, password=user1_password)
        assert status == HTTP_201_CREATED

        # Given - User 2
        user2_username = "user2"
        user2_password = "User2Pass123!"  # pragma: allowlist secret
        user2_email = "user2@example.com"
        status, _ = auth_api.register(username=user2_username, email=user2_email, password=user2_password)
        assert status == HTTP_201_CREATED

        # When
        _, token1_data = auth_api.login(username=user1_username, password=user1_password)
        _, token2_data = auth_api.login(username=user2_username, password=user2_password)

        # Then
        assert token1_data["access_token"] != token2_data["access_token"]

    def test_given_two_logged_in_users_when_accessing_profiles_then_each_gets_own_data(
        self, auth_api: AuthAPIClient
    ) -> None:
        """Each user's token only provides access to their own data."""
        # Given - User 1 registered and logged in
        user1_username = "alice"
        user1_password = "AlicePass123!"  # pragma: allowlist secret
        user1_email = "alice@example.com"
        _, user1_data = auth_api.register(username=user1_username, email=user1_email, password=user1_password)
        _, token1_response = auth_api.login(username=user1_username, password=user1_password)
        user1_token = token1_response["access_token"]

        # Given - User 2 registered and logged in
        user2_username = "bob"
        user2_password = "BobPass123!"  # pragma: allowlist secret
        user2_email = "bob@example.com"
        _, user2_data = auth_api.register(username=user2_username, email=user2_email, password=user2_password)
        _, token2_response = auth_api.login(username=user2_username, password=user2_password)
        user2_token = token2_response["access_token"]

        # When
        _, user1_profile = auth_api.get_current_user(user1_token)
        _, user2_profile = auth_api.get_current_user(user2_token)

        # Then
        assert user1_profile["username"] == user1_username
        assert user1_profile["id"] == user1_data["id"]
        assert user2_profile["username"] == user2_username
        assert user2_profile["id"] == user2_data["id"]


class TestMultipleLoginSessions:
    """End-to-end tests for multiple login sessions."""

    def test_given_user_when_logging_in_twice_then_both_tokens_work(self, auth_api: AuthAPIClient) -> None:
        """User can have multiple active sessions with different tokens."""
        # Given - Registered user
        username = "multisession"
        password = VALID_PASSWORD
        email = "multisession@example.com"
        status, user_data = auth_api.register(username=username, email=email, password=password)
        assert status == HTTP_201_CREATED
        user_id = user_data["id"]

        # When - Login first time
        _, first_login = auth_api.login(username=username, password=password)
        first_token = first_login["access_token"]

        # When - Login second time
        _, second_login = auth_api.login(username=username, password=password)
        second_token = second_login["access_token"]

        # Then - Both tokens work
        _, profile_from_first = auth_api.get_current_user(first_token)
        _, profile_from_second = auth_api.get_current_user(second_token)

        assert profile_from_first["id"] == user_id
        assert profile_from_second["id"] == user_id


class TestDataPersistence:
    """End-to-end tests for data persistence through authentication."""

    def test_given_user_with_all_fields_when_accessing_after_login_then_all_data_persists(
        self, auth_api: AuthAPIClient
    ) -> None:
        """All user data including optional fields persists through authentication flow."""
        # Given
        username = "fulldata"
        password = VALID_PASSWORD
        email = "fulldata@example.com"
        first_name = "Full"
        last_name = "Data"
        phone_number = "+15551234567"
        profile_photo_url = "https://example.com/photo.jpg"

        status, _ = auth_api.register(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            profile_photo_url=profile_photo_url,
        )
        assert status == HTTP_201_CREATED

        _, token_data = auth_api.login(username=username, password=password)
        token = token_data["access_token"]

        # When
        _, profile = auth_api.get_current_user(token)

        # Then
        assert profile["username"] == username
        assert profile["email"] == email
        assert profile["first_name"] == first_name
        assert profile["last_name"] == last_name
        assert profile["phone_number"] == phone_number
        assert profile["profile_photo_url"] == profile_photo_url
