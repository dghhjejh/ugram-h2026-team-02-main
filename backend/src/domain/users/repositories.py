"""User repository port (hexagonal architecture)."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.users.entities import User


class IUserRepository(ABC):
    """Port defining persistence contract for User aggregate."""

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> User | None:
        """Lookup by UUID."""
        ...

    @abstractmethod
    def get_by_username(self, username: str) -> User | None:
        """Lookup by username."""
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Lookup by email."""
        ...

    @abstractmethod
    def get_by_google_id(self, google_id: str) -> User | None:
        """Lookup by Google ID."""
        ...

    @abstractmethod
    def username_exists(self, username: str) -> bool:
        """Check if username exists."""
        ...

    @abstractmethod
    def save(self, user: User) -> User:
        """Insert new user."""
        ...

    @abstractmethod
    def update(self, user: User) -> User:
        """Update existing user. Raises ValueError if not found."""
        ...

    @abstractmethod
    def list_all(self, limit: int = 100, offset: int = 0, keyword: str | None = None) -> list[User]:
        """Paginated list optionally filtered by username keyword."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Total user count."""
        ...

    @abstractmethod
    def get_by_ids(self, user_ids: list[UUID]) -> list[User]:
        """Bulk fetch by IDs preserving input order."""
        ...

    @abstractmethod
    def delete(self, user_id: UUID) -> None:
        """Delete user by ID."""
        ...
