"""SQLAlchemy implementation of the User repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

from src.adapters.outbound.persistence.models import UserORM
from src.domain.users.entities import User
from src.domain.users.repositories import IUserRepository


class SQLAlchemyUserRepository(IUserRepository):
    """SQLAlchemy adapter for user persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._get_one_by(UserORM.id, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self._get_one_by(UserORM.username, username)

    def get_by_email(self, email: str) -> User | None:
        return self._get_one_by(UserORM.email, email)

    def get_by_google_id(self, google_id: str) -> User | None:
        return self._get_one_by(UserORM.google_id, google_id)

    def username_exists(self, username: str) -> bool:
        count = self._session.scalar(select(func.count()).select_from(UserORM).where(UserORM.username == username))
        return count is not None and count > 0

    def save(self, user: User) -> User:
        orm = self._to_orm(user)
        self._session.add(orm)
        self._session.flush()
        return self._to_entity(orm)

    def update(self, user: User) -> User:
        orm = self._session.scalars(select(UserORM).where(UserORM.id == user.id)).first()

        if not orm:
            raise ValueError(f"User with ID {user.id} not found")

        orm.username = user.username
        orm.email = user.email
        orm.first_name = user.first_name
        orm.last_name = user.last_name
        orm.phone_number = user.phone_number
        orm.profile_photo_url = user.profile_photo_url
        # registration_date is immutable
        orm.password = user.password
        orm.google_id = user.google_id

        self._session.flush()
        return self._to_entity(orm)

    def list_all(self, limit: int = 100, offset: int = 0, keyword: str | None = None) -> list[User]:
        stmt = select(UserORM)
        if keyword:
            stmt = stmt.where(UserORM.username.ilike(f"%{keyword}%"))
        stmt = stmt.order_by(UserORM.username).limit(limit).offset(offset)
        return [self._to_entity(orm) for orm in self._session.scalars(stmt)]

    def count(self) -> int:
        return self._session.scalar(select(func.count()).select_from(UserORM)) or 0

    def get_by_ids(self, user_ids: list[UUID]) -> list[User]:
        if not user_ids:
            return []
        unique_ids = list(dict.fromkeys(user_ids))
        stmt = select(UserORM).where(UserORM.id.in_(unique_ids))
        orms = self._session.scalars(stmt).all()
        mapped = {orm.id: self._to_entity(orm) for orm in orms}
        return [mapped[user_id] for user_id in user_ids if user_id in mapped]

    def delete(self, user_id: UUID) -> None:
        """Delete user by ID."""
        orm = self._session.scalars(select(UserORM).where(UserORM.id == user_id)).first()
        if orm:
            self._session.delete(orm)
            self._session.flush()

    # --- Private helpers ---

    def _get_one_by[T](self, column: InstrumentedAttribute[T], value: T) -> User | None:
        """Fetch single user by column match."""
        orm = self._session.scalars(select(UserORM).where(column == value)).first()
        return self._to_entity(orm) if orm else None

    def _to_entity(self, orm: UserORM) -> User:
        """Map ORM to domain entity (anti-corruption layer)."""
        return User(
            id=orm.id,
            username=orm.username,
            email=orm.email,
            first_name=orm.first_name,
            last_name=orm.last_name,
            phone_number=orm.phone_number,
            profile_photo_url=orm.profile_photo_url,
            registration_date=orm.registration_date,
            password=orm.password,
            google_id=orm.google_id,
        )

    def _to_orm(self, entity: User) -> UserORM:
        """Map domain entity to ORM."""
        return UserORM(
            id=entity.id,
            username=entity.username,
            email=entity.email,
            first_name=entity.first_name,
            last_name=entity.last_name,
            phone_number=entity.phone_number,
            profile_photo_url=entity.profile_photo_url,
            registration_date=entity.registration_date,
            password=entity.password,
            google_id=entity.google_id,
        )
