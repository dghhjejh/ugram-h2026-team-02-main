"""FastAPI dependency injection wiring.

Connects infrastructure adapters to domain services via dependency inversion.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from src.adapters.outbound.persistence.database import get_db
from src.adapters.outbound.persistence.sqlalchemy_comment_repository import (
    SQLAlchemyCommentRepository,
)
from src.adapters.outbound.persistence.sqlalchemy_image_repository import (
    SQLAlchemyImageRepository,
)
from src.adapters.outbound.persistence.sqlalchemy_notification_repository import (
    SQLAlchemyNotificationRepository,
)
from src.adapters.outbound.persistence.sqlalchemy_reaction_repository import (
    SQLAlchemyReactionRepository,
)
from src.adapters.outbound.persistence.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from src.adapters.outbound.storage.s3_presigner import S3Presigner
from src.adapters.outbound.time_provider import SystemTimeProvider
from src.application.config import settings
from src.domain.images.services import ImageService
from src.domain.notifications.services import NotificationService
from src.domain.social.services import SocialService
from src.domain.time_provider import ITimeProvider
from src.domain.users.services import UserService

# Type alias for database session injection
DbSession = Annotated[Session, Depends(get_db)]


def get_time_provider() -> ITimeProvider:
    """Production time provider."""
    return SystemTimeProvider()


# Type alias for time provider injection (defined after get_time_provider)
TimeProviderDep = Annotated[ITimeProvider, Depends(get_time_provider)]


def get_user_service(db: DbSession, time_provider: TimeProviderDep) -> UserService:
    """Wire UserService with SQLAlchemy repository."""
    return UserService(SQLAlchemyUserRepository(db), time_provider)


def get_image_service(db: DbSession, time_provider: TimeProviderDep) -> ImageService:
    """Wire ImageService with SQLAlchemy repository."""
    return ImageService(SQLAlchemyImageRepository(db), time_provider)


@lru_cache(maxsize=1)
def get_s3_presigner() -> S3Presigner:
    """Provide S3 presigner configured via settings."""
    return S3Presigner(
        bucket=settings.S3_BUCKET,
        region=settings.S3_REGION,
        upload_prefix=settings.S3_UPLOAD_PREFIX,
        expires_in=settings.S3_PRESIGN_TTL,
        view_url_cache_ttl_seconds=settings.S3_VIEW_URL_CACHE_TTL_SECONDS,
        view_url_cache_max_entries=settings.S3_VIEW_URL_CACHE_MAX_ENTRIES,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
        aws_profile=settings.AWS_PROFILE,
        aws_sdk_load_config=settings.AWS_SDK_LOAD_CONFIG,
    )


def get_social_service(db: DbSession, time_provider: TimeProviderDep) -> SocialService:
    """Wire SocialService with SQLAlchemy comment and reaction repositories."""
    return SocialService(
        comment_repo=SQLAlchemyCommentRepository(db),
        reaction_repo=SQLAlchemyReactionRepository(db),
        time_provider=time_provider,
    )


SocialServiceDep = Annotated[SocialService, Depends(get_social_service)]


def get_notification_service(db: DbSession, time_provider: TimeProviderDep) -> NotificationService:
    return NotificationService(
        notification_repo=SQLAlchemyNotificationRepository(db),
        time_provider=time_provider,
    )


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
