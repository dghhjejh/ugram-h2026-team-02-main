"""Integration tests for Users API happy paths.

These tests verify the full CRUD lifecycle for users, ensuring
the API endpoints work correctly end-to-end with a clean database.
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from src.domain.users.services import UserNotFoundError


@dataclass
class UserPayload:
    """Test data factory for user payloads."""

    username: str
    email: str
    first_name: str
    last_name: str
    user_password: str = "SecurePassword123!"
    phone_number: str | None = None
    profile_photo_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API request payload."""
        data = {
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "user_password": self.user_password,
        }
        if self.phone_number:
            data["phone_number"] = self.phone_number
        if self.profile_photo_url:
            data["profile_photo_url"] = self.profile_photo_url
        return data


class UserAPIClient:
    """Helper class for user API operations - Single Responsibility."""

    def __init__(self, client: TestClient) -> None:
        self.client = client

    def create(self, payload: UserPayload) -> tuple[int, dict[str, Any]]:
        """Create a user and return (status_code, response_json)."""
        response = self.client.post("/users/register", json=payload.to_dict())
        return response.status_code, response.json()

    def get(self, user_id: str, token: str | None = None) -> tuple[int, dict[str, Any]]:
        """Get a user by ID."""
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = self.client.get(f"/users/{user_id}", headers=headers)
        return response.status_code, response.json()

    def get_me(self, token: str | None = None) -> tuple[int, dict[str, Any]]:
        """Get the current authenticated user profile."""
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = self.client.get("/users/me", headers=headers)
        return response.status_code, response.json()

    def list(
        self, limit: int = 20, offset: int = 0, token: str | None = None, keyword: str | None = None
    ) -> tuple[int, dict[str, Any]]:
        """List users with pagination and optional keyword search."""
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if keyword is not None:
            params["keyword"] = keyword
        response = self.client.get("/users", params=params, headers=headers)
        return response.status_code, response.json()

    def update(self, user_id: str, updates: dict[str, Any], token: str | None = None) -> tuple[int, dict[str, Any]]:
        """Update a user's profile."""
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.client.put(f"/users/{user_id}", json=updates, headers=headers)
        return response.status_code, response.json()

    def login(self, username: str, password: str) -> tuple[int, dict[str, Any]]:
        """Login and get access token."""
        response = self.client.post(
            "/users/token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return response.status_code, response.json()

    def delete(self, user_id: str, confirmation: str, token: str | None = None) -> int:
        """Delete a user account and return status code."""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.client.request(
            "DELETE", f"/users/{user_id}", json={"confirmation": confirmation}, headers=headers
        )
        return response.status_code


@pytest.fixture
def api(client: TestClient) -> UserAPIClient:
    """Provide a UserAPIClient wrapper."""
    return UserAPIClient(client)


@pytest.fixture
def sample_user() -> UserPayload:
    """Standard test user payload."""
    return UserPayload(
        username="updatetest",
        email="updatetest@example.com",
        first_name="Test",
        last_name="User",
        phone_number="+15551234567",
    )


@pytest.fixture
def created_user(api: UserAPIClient, sample_user: UserPayload) -> dict[str, Any]:
    """Create and return a user for tests that need an existing user."""
    status, data = api.create(sample_user)
    assert status == 201
    return data


class TestCreateUser:
    """Tests for user creation endpoint."""

    def test_creates_user_with_all_fields(self, api: UserAPIClient) -> None:
        """Creating a user returns all provided fields."""
        payload = UserPayload(
            username="fulluser",
            email="full@example.com",
            first_name="Full",
            last_name="User",
            phone_number="+15551234567",
            profile_photo_url="https://example.com/photo.jpg",
        )

        status, data = api.create(payload)

        assert status == 201
        assert data["username"] == payload.username
        assert data["email"] == payload.email
        assert data["first_name"] == payload.first_name
        assert data["last_name"] == payload.last_name
        assert data["phone_number"] == payload.phone_number
        assert data["profile_photo_url"] == payload.profile_photo_url
        UUID(data["id"])

    def test_creates_user_with_minimal_fields(self, api: UserAPIClient) -> None:
        """Creating a user works with only required fields."""
        payload = UserPayload(
            username="minimal",
            email="minimal@example.com",
            first_name="Min",
            last_name="User",
        )

        status, data = api.create(payload)

        assert status == 201
        assert data["phone_number"] is None
        assert data["profile_photo_url"] is None


class TestGetUser:
    """Tests for retrieving a user."""

    def test_retrieves_existing_user(
        self, api: UserAPIClient, created_user: dict[str, Any], sample_user: UserPayload
    ) -> None:
        """Getting a user by ID returns correct data."""
        _, token_data = api.login(sample_user.username, sample_user.user_password)
        token = token_data["access_token"]

        status, data = api.get(str(created_user["id"]), token=token)

        assert status == 200
        assert data["id"] == created_user["id"]
        assert data["username"] == created_user["username"]
        assert "email" not in data
        assert "phone_number" not in data


class TestListUsers:
    """Tests for listing users."""

    def test_returns_paginated_list(self, api: UserAPIClient) -> None:
        """Listing users returns paginated response structure."""
        first_payload = UserPayload(
            username="listuser0",
            email="list0@example.com",
            first_name="List0",
            last_name="User",
        )
        api.create(first_payload)
        for i in range(1, 3):
            api.create(
                UserPayload(
                    username=f"listuser{i}",
                    email=f"list{i}@example.com",
                    first_name=f"List{i}",
                    last_name="User",
                )
            )
        _, token_data = api.login(first_payload.username, first_payload.user_password)
        token = token_data["access_token"]

        status, data = api.list(limit=10, offset=0, token=token)

        assert status == 200
        assert "users" in data
        assert "total" in data
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["users"]) >= 3
        assert all("email" not in user for user in data["users"])
        assert all("phone_number" not in user for user in data["users"])

    def test_list_users_keeps_private_fields_out_of_public_profiles(self, api: UserAPIClient) -> None:
        """The list endpoint returns public profiles even though /users/me stays private."""
        payload = UserPayload(
            username="public_boundary",
            email="public-boundary@example.com",
            first_name="Public",
            last_name="Boundary",
            phone_number="+15559876543",
        )
        status, created = api.create(payload)
        assert status == 201

        _, token_data = api.login(payload.username, payload.user_password)
        token = token_data["access_token"]

        me_status, me = api.get_me(token=token)
        assert me_status == 200
        assert me["email"] == payload.email
        assert me["phone_number"] == payload.phone_number

        status, data = api.list(limit=10, offset=0, token=token)
        assert status == 200

        listed_user = next(user for user in data["users"] if user["id"] == created["id"])
        assert listed_user["username"] == payload.username
        assert "email" not in listed_user
        assert "phone_number" not in listed_user

    def test_pagination_returns_different_pages(self, api: UserAPIClient) -> None:
        """Different offsets return different users."""
        first_payload = UserPayload(
            username="pageuser0",
            email="page0@example.com",
            first_name="Page0",
            last_name="User",
        )
        api.create(first_payload)
        for i in range(1, 4):
            api.create(
                UserPayload(
                    username=f"pageuser{i}",
                    email=f"page{i}@example.com",
                    first_name=f"Page{i}",
                    last_name="User",
                )
            )
        _, token_data = api.login(first_payload.username, first_payload.user_password)
        token = token_data["access_token"]

        _, page1 = api.list(limit=2, offset=0, token=token)
        _, page2 = api.list(limit=2, offset=2, token=token)

        page1_ids = {u["id"] for u in page1["users"]}
        page2_ids = {u["id"] for u in page2["users"]}
        assert page1_ids.isdisjoint(page2_ids)


class TestSearchUsers:
    """Tests for keyword-based user search via GET /users?keyword=."""

    @pytest.fixture(autouse=True)
    def setup_users(self, api: UserAPIClient) -> None:
        """Create a set of users to search against."""
        users = [
            UserPayload("alice_search", "alice_s@example.com", "Alice", "Search"),
            UserPayload("alice2_search", "alice2_s@example.com", "Alice2", "Search"),
            UserPayload("bob_search", "bob_s@example.com", "Bob", "Search"),
        ]
        for u in users:
            api.create(u)
        _, token_data = api.login("alice_search", "SecurePassword123!")
        self._token = token_data["access_token"]

    def test_keyword_returns_matching_users(self, api: UserAPIClient) -> None:
        """Searching by keyword returns all users whose username contains it."""
        status, data = api.list(keyword="alice", token=self._token)

        assert status == 200
        usernames = [u["username"] for u in data["users"]]
        assert "alice_search" in usernames
        assert "alice2_search" in usernames
        assert "bob_search" not in usernames

    def test_keyword_is_case_insensitive(self, api: UserAPIClient) -> None:
        """Keyword search is case-insensitive."""
        status, data = api.list(keyword="ALICE", token=self._token)

        assert status == 200
        usernames = [u["username"] for u in data["users"]]
        assert "alice_search" in usernames

    def test_keyword_no_match_returns_empty(self, api: UserAPIClient) -> None:
        """Searching for a non-existent keyword returns an empty list."""
        status, data = api.list(keyword="zzznomatch999", token=self._token)

        assert status == 200
        assert data["users"] == []
        assert data["total"] == 0

    def test_no_keyword_returns_all_users(self, api: UserAPIClient) -> None:
        """Omitting keyword returns all users (existing behaviour unchanged)."""
        status, data = api.list(token=self._token)

        assert status == 200
        assert data["total"] >= 3


class TestUpdateUser:
    """Tests for updating user profile."""

    def test_updates_user_profile(
        self, api: UserAPIClient, created_user: dict[str, Any], sample_user: UserPayload
    ) -> None:
        """Updating a user modifies the specified fields."""
        status, token_data = api.login(sample_user.username, sample_user.user_password)
        assert status == 200
        token = token_data["access_token"]

        updates = {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
        }

        status, data = api.update(str(created_user["id"]), updates, token=token)

        assert status == 200
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["email"] == "updated@example.com"
        assert data["username"] == created_user["username"]

    def test_update_requires_auth(self, api: UserAPIClient, created_user: dict[str, Any]) -> None:
        """PUT /users/{user_id} returns 401 without token."""
        status, _ = api.update(str(created_user["id"]), {"first_name": "Hacked"})
        assert status == 401

    def test_update_forbidden_for_other_user(self, api: UserAPIClient, created_user: dict[str, Any]) -> None:
        """PUT /users/{user_id} returns 403 when token belongs to a different user."""
        other = UserPayload(
            username="other_updater", email="otherupd@example.com", first_name="Other", last_name="User"
        )
        api.create(other)
        _, token_data = api.login(other.username, other.user_password)
        other_token = token_data["access_token"]

        status, _ = api.update(str(created_user["id"]), {"first_name": "Hacked"}, token=other_token)
        assert status == 403


class TestDeleteUser:
    """Tests for deleting a user account."""

    def test_delete_user_succeeds_with_exact_username_confirmation(self, api: UserAPIClient) -> None:
        """DELETE /users/{user_id} returns 204 for valid owner + exact username confirmation."""
        payload = UserPayload(
            username="delete_ok_user",
            email="delete_ok_user@example.com",
            first_name="Delete",
            last_name="Ok",
        )
        status, created = api.create(payload)
        assert status == 201

        status, token_data = api.login(payload.username, payload.user_password)
        assert status == 200
        token = token_data["access_token"]

        delete_status = api.delete(str(created["id"]), confirmation=payload.username, token=token)

        assert delete_status == 204

        # Token should no longer resolve a current user once account is deleted.
        me_status, _ = api.get_me(token=token)
        assert me_status == 401

    def test_delete_user_returns_400_when_confirmation_is_wrong(self, api: UserAPIClient) -> None:
        """DELETE /users/{user_id} returns 400 for invalid username confirmation."""
        payload = UserPayload(
            username="delete_bad_confirm",
            email="delete_bad_confirm@example.com",
            first_name="Delete",
            last_name="Bad",
        )
        status, created = api.create(payload)
        assert status == 201

        status, token_data = api.login(payload.username, payload.user_password)
        assert status == 200
        token = token_data["access_token"]

        delete_status = api.delete(str(created["id"]), confirmation="wrong_username", token=token)
        assert delete_status == 400

        get_status, _ = api.get(str(created["id"]), token=token)
        assert get_status == 200

    def test_delete_user_requires_authentication(self, api: UserAPIClient) -> None:
        """DELETE /users/{user_id} returns 401 without token."""
        payload = UserPayload(
            username="delete_no_auth",
            email="delete_no_auth@example.com",
            first_name="Delete",
            last_name="NoAuth",
        )
        status, created = api.create(payload)
        assert status == 201

        delete_status = api.delete(str(created["id"]), confirmation=payload.username)
        assert delete_status == 401

    def test_delete_user_forbidden_for_non_owner(self, api: UserAPIClient) -> None:
        """DELETE /users/{user_id} returns 403 when token belongs to another user."""
        owner = UserPayload(
            username="delete_owner",
            email="delete_owner@example.com",
            first_name="Owner",
            last_name="User",
        )
        other = UserPayload(
            username="delete_other",
            email="delete_other@example.com",
            first_name="Other",
            last_name="User",
        )
        owner_status, owner_created = api.create(owner)
        other_status, _ = api.create(other)
        assert owner_status == 201
        assert other_status == 201

        status, token_data = api.login(other.username, other.user_password)
        assert status == 200
        other_token = token_data["access_token"]

        delete_status = api.delete(str(owner_created["id"]), confirmation=owner.username, token=other_token)
        assert delete_status == 403

    def test_delete_user_returns_404_when_service_cannot_find_user(self, api: UserAPIClient) -> None:
        """DELETE /users/{user_id} returns 404 when service raises UserNotFoundError."""
        payload = UserPayload(
            username="delete_not_found",
            email="delete_not_found@example.com",
            first_name="Delete",
            last_name="Missing",
        )
        status, created = api.create(payload)
        assert status == 201

        status, token_data = api.login(payload.username, payload.user_password)
        assert status == 200
        token = token_data["access_token"]

        with patch(
            "src.domain.users.services.UserService.delete_user",
            side_effect=UserNotFoundError(f"User with ID {created['id']} not found"),
        ):
            response = api.client.request(
                "DELETE",
                f"/users/{created['id']}",
                json={"confirmation": payload.username},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            )

        assert response.status_code == 404


class TestUserLifecycle:
    """End-to-end lifecycle test."""

    def test_full_crud_lifecycle(self, api: UserAPIClient) -> None:
        """Complete create -> read -> update -> verify flow."""
        payload = UserPayload(
            username="lifecycle",
            email="lifecycle@example.com",
            first_name="Life",
            last_name="Cycle",
            phone_number="+15550001111",
        )
        status, user = api.create(payload)
        assert status == 201
        user_id = user["id"]

        status, token_data = api.login(payload.username, payload.user_password)
        assert status == 200
        token = token_data["access_token"]

        status, fetched = api.get(str(user_id), token=token)
        assert status == 200
        assert fetched["first_name"] == "Life"
        assert "phone_number" not in fetched

        status, _ = api.update(str(user_id), {"first_name": "Updated"}, token=token)
        assert status == 200

        status, final = api.get(str(user_id), token=token)
        assert status == 200
        assert final["first_name"] == "Updated"
        assert "phone_number" not in final
