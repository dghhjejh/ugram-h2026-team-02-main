from uuid import UUID, uuid4

from src.domain.notifications.entities import Notification, NotificationType
from src.domain.notifications.repositories import INotificationRepository
from src.domain.time_provider import ITimeProvider


class NotificationNotFoundError(Exception):
    pass


class NotificationService:
    def __init__(self, notification_repo: INotificationRepository, time_provider: ITimeProvider) -> None:
        self.notification_repo = notification_repo
        self.time_provider = time_provider

    def create_notification(
        self,
        recipient_user_id: UUID,
        actor_user_id: UUID,
        image_id: UUID,
        notification_type: NotificationType,
    ) -> Notification:
        notification = Notification(
            id=uuid4(),
            recipient_user_id=recipient_user_id,
            actor_user_id=actor_user_id,
            image_id=image_id,
            notification_type=notification_type,
            is_read=False,
            created_at=self.time_provider.now(),
        )
        return self.notification_repo.add(notification)

    def get_user_notifications(self, user_id: UUID, limit: int = 50) -> list[Notification]:
        return self.notification_repo.get_for_user(user_id, limit=limit)

    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        notification = self.notification_repo.mark_as_read(notification_id, user_id)
        if notification is None:
            raise NotificationNotFoundError("Notification not found")
        return notification

    def count_unread(self, user_id: UUID) -> int:
        return self.notification_repo.count_unread(user_id)
