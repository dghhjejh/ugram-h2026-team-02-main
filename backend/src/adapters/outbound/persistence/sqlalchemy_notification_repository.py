from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.adapters.outbound.persistence.models import NotificationORM
from src.domain.notifications.entities import Notification, NotificationType
from src.domain.notifications.repositories import INotificationRepository


class SQLAlchemyNotificationRepository(INotificationRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, notification: Notification) -> Notification:
        orm = self._to_orm(notification)
        self.db.add(orm)
        self.db.commit()
        self.db.refresh(orm)
        return self._to_entity(orm)

    def get_for_user(self, user_id: UUID, limit: int = 50) -> list[Notification]:
        query = (
            select(NotificationORM)
            .where(NotificationORM.recipient_user_id == user_id)
            .order_by(NotificationORM.created_at.desc())
            .limit(limit)
        )
        return [self._to_entity(orm) for orm in self.db.scalars(query).all()]

    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        query = select(NotificationORM).where(
            NotificationORM.id == notification_id,
            NotificationORM.recipient_user_id == user_id,
        )
        orm = self.db.scalar(query)
        if orm is None:
            return None
        orm.is_read = True
        self.db.commit()
        self.db.refresh(orm)
        return self._to_entity(orm)

    def count_unread(self, user_id: UUID) -> int:
        query = (
            select(func.count())
            .select_from(NotificationORM)
            .where(
                NotificationORM.recipient_user_id == user_id,
                NotificationORM.is_read.is_(False),
            )
        )
        return int(self.db.scalar(query) or 0)

    def _to_entity(self, orm: NotificationORM) -> Notification:
        return Notification(
            id=orm.id,
            recipient_user_id=orm.recipient_user_id,
            actor_user_id=orm.actor_user_id,
            image_id=orm.image_id,
            notification_type=NotificationType(orm.notification_type),
            is_read=orm.is_read,
            created_at=orm.created_at,
        )

    def _to_orm(self, notification: Notification) -> NotificationORM:
        return NotificationORM(
            id=notification.id,
            recipient_user_id=notification.recipient_user_id,
            actor_user_id=notification.actor_user_id,
            image_id=notification.image_id,
            notification_type=notification.notification_type,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )
