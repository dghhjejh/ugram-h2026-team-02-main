"""Unit tests for UserService delete-user behavior."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from src.domain.time_provider import ITimeProvider
from src.domain.users.entities import User
from src.domain.users.repositories import IUserRepository
from src.domain.users.services import UserNotFoundError, UserService


class FixedTimeProvider(ITimeProvider):
    """Deterministic time provider for domain tests."""

    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)


def make_user(username: str = "domain_delete_user") -> User:
    """Create a valid user entity for tests."""
    return User.create_new(
        username=username,
        email=f"{username}@example.com",
        first_name="Domain",
        last_name="User",
        time_provider=FixedTimeProvider(),
        password=None,
    )


class TestDeleteUserService:
    """Delete-user unit tests for UserService."""

    def test_delete_user_deletes_when_confirmation_matches_username(self) -> None:
        """Service should delete user when confirmation exactly matches username."""
        repo = Mock(spec=IUserRepository)
        user = make_user("exact_match")
        repo.get_by_id.return_value = user

        service = UserService(repo, FixedTimeProvider())

        service.delete_user(user.id, confirmation="exact_match")

        repo.delete.assert_called_once_with(user.id)

    def test_delete_user_raises_when_confirmation_does_not_match(self) -> None:
        """Service should reject deletion and not call repository delete on mismatch."""
        repo = Mock(spec=IUserRepository)
        user = make_user("expected_name")
        repo.get_by_id.return_value = user

        service = UserService(repo, FixedTimeProvider())

        with pytest.raises(ValueError, match="Username does not match"):
            service.delete_user(user.id, confirmation="wrong_name")

        repo.delete.assert_not_called()

    def test_delete_user_raises_not_found_when_user_does_not_exist(self) -> None:
        """Service should raise UserNotFoundError if user ID does not exist."""
        repo = Mock(spec=IUserRepository)
        repo.get_by_id.return_value = None

        service = UserService(repo, FixedTimeProvider())

        with pytest.raises(UserNotFoundError, match="not found"):
            service.delete_user(make_user("missing_user").id, confirmation="missing_user")

        repo.delete.assert_not_called()
