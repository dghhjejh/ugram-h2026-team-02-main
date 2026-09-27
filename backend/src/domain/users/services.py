"""User domain service containing business logic and use cases."""

from uuid import UUID

from src.domain.time_provider import ITimeProvider
from src.domain.users.entities import User
from src.domain.users.helpers.auth import compare_password, hash_password
from src.domain.users.repositories import IUserRepository


class UserNotFoundError(Exception):
    """User lookup failed."""


class UserAlreadyExistsError(Exception):
    """Username or email already taken."""


class UserService:
    """Orchestrates user-related use cases and enforces business rules."""

    def __init__(self, user_repo: IUserRepository, time_provider: ITimeProvider) -> None:
        self._repo = user_repo
        self._time = time_provider

    def get_user(self, user_id: UUID) -> User:
        """Fetch user by ID or raise UserNotFoundError."""
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        return user

    def get_user_by_username(self, username: str) -> User:
        """Fetch user by username or raise UserNotFoundError."""
        user = self._repo.get_by_username(username)
        if not user:
            raise UserNotFoundError(f"User with username '{username}' not found")
        return user

    def get_user_by_email(self, email: str) -> User:
        """Fetch user by user's email or raise UserNotFoundError."""
        user = self._repo.get_by_email(email)
        if not user:
            raise UserNotFoundError(f"User with the email '{email}' not found")
        return user

    def get_user_by_google_id(self, google_id: str) -> User:
        """Fetch user by Google ID or raise UserNotFoundError."""
        user = self._repo.get_by_google_id(google_id)
        if not user:
            raise UserNotFoundError(f"User with Google ID '{google_id}' not found")
        return user

    def username_exists(self, username: str) -> bool:
        """Check if username exists."""
        return self._repo.username_exists(username)

    def link_google_account(self, user_id: UUID, google_id: str) -> User:
        """Link an existing user account to a Google ID."""
        user = self.get_user(user_id)
        if user.google_id and user.google_id != google_id:
            raise ValueError("User already linked to a different Google account")
        user.google_id = google_id
        return self._repo.update(user)

    def create_user(
        self,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        password: str | None = None,
        phone_number: str | None = None,
        profile_photo_url: str | None = None,
        google_id: str | None = None,
    ) -> User:
        """Create user after validating uniqueness constraints."""
        if self._repo.get_by_username(username):
            raise UserAlreadyExistsError(f"Username '{username}' already exists")
        if self._repo.get_by_email(email):
            raise UserAlreadyExistsError(f"Email '{email}' already exists")

        user = User.create_new(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            time_provider=self._time,
            phone_number=phone_number,
            profile_photo_url=profile_photo_url,
            password=hash_password(password) if password else None,
            google_id=google_id,
        )
        return self._repo.save(user)

    def update_user_profile(
        self,
        user_id: UUID,
        username: str | None = None,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        phone_number: str | None = None,
        profile_photo_url: str | None = None,
    ) -> User:
        """Partial update of profile fields with username and email uniqueness check."""
        user = self.get_user(user_id)

        # Check username uniqueness if changing
        if username and username != user.username:
            existing = self._repo.get_by_username(username)
            if existing and existing.id != user_id:
                raise UserAlreadyExistsError(f"Username '{username}' already in use")

        if email and email != user.email:
            existing = self._repo.get_by_email(email)
            if existing and existing.id != user_id:
                raise UserAlreadyExistsError(f"Email '{email}' already in use")

        user.update_profile(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )

        # Update profile photo separately if provided
        if profile_photo_url is not None:
            user.update_profile_photo(profile_photo_url if profile_photo_url else None)

        return self._repo.update(user)

    def list_users(self, limit: int = 100, offset: int = 0, keyword: str | None = None) -> list[User]:
        """Paginated user list optionally filtered by username. Limit: 1-1000."""
        if not 1 <= limit <= 1000:
            raise ValueError("Limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("Offset must be non-negative")
        return self._repo.list_all(limit=limit, offset=offset, keyword=keyword)

    def get_total_user_count(self) -> int:
        """Total user count for pagination metadata."""
        return self._repo.count()

    def get_users_by_ids(self, user_ids: list[UUID]) -> list[User]:
        """Bulk fetch helper preserving order."""
        if not user_ids:
            return []
        return self._repo.get_by_ids(user_ids)

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user by checking if password matches the stored hash."""
        try:
            user = self.get_user_by_username(username)
        except UserNotFoundError:
            return False

        return compare_password(password, user.password) if user.password else False

    def delete_user(self, user_id: UUID, confirmation: str) -> None:
        """Delete user account after verifying username confirmation.

        User must type their exact username to confirm deletion.
        """
        user = self.get_user(user_id)

        # Verify username confirmation
        if confirmation != user.username:
            raise ValueError("Username does not match")

        self._repo.delete(user_id)
