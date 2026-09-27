"""SQLAlchemy ORM models for database persistence."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class UserORM(Base):
    """ORM model for users table.

    This is the infrastructure concern - mapping domain entities to database tables.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    profile_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    registration_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    password: Mapped[str | None] = mapped_column(String(), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)


class ImageORM(Base):
    """ORM model for images table."""

    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hashtags: Mapped[list[str]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)
    mentions_user_ids: Mapped[list[str]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)
    mention_tags: Mapped[list[dict]] = mapped_column(JSON, default=list)
    image_url: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_images_created_at_id", created_at.desc(), id.desc()),
        Index("ix_images_owner_created_at", owner_user_id, created_at.desc(), id.desc()),
    )


class SearchEventORM(Base):
    """Durable search event outbox."""

    __tablename__ = "search_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    trend_type: Mapped[str] = mapped_column(String(20), nullable=False)
    search_date: Mapped[date] = mapped_column(Date, nullable=False)
    searched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_search_events_processed_at", processed_at),
        Index("ix_search_events_search_date_type", search_date, trend_type),
    )


class SearchTrendDailyORM(Base):
    """Daily aggregated search counters for image search terms."""

    __tablename__ = "search_trends_daily"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    trend_type: Mapped[str] = mapped_column(String(20), nullable=False)
    search_date: Mapped[date] = mapped_column(Date, nullable=False)
    search_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("keyword", "trend_type", "search_date", name="uq_search_trends_daily_keyword_type_date"),
        Index("ix_search_trends_daily_date_type_count", search_date, trend_type, search_count),
    )


class CommentORM(Base):
    """ORM model for comments on images."""

    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (Index("ix_comments_image_id_created_at", image_id, created_at.desc()),)


class ReactionORM(Base):
    """ORM model for reactions (likes) on images."""

    __tablename__ = "reactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint("user_id", "image_id", "type", name="uq_reactions_user_image_type"),
        Index("ix_reactions_image_id_type", image_id, type),
    )


class NotificationORM(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    notification_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (Index("ix_notifications_recipient_created_at", recipient_user_id, created_at.desc()),)
