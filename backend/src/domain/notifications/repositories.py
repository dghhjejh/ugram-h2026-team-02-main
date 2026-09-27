from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.notifications.entities import Notification


class INotificationRepository(ABC):
    @abstractmethod
    def add(self, notification: Notification) -> Notification:
        pass

    @abstractmethod
    def get_for_user(self, user_id: UUID, limit: int) -> list[Notification]:
        pass

    @abstractmethod
    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        pass

    @abstractmethod
    def count_unread(self, user_id: UUID) -> int:
        pass
