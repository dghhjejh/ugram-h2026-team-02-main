from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from src.domain.notifications.entities import Notification, NotificationType
from src.domain.notifications.repositories import INotificationRepository
from src.domain.notifications.services import NotificationNotFoundError, NotificationService
from src.domain.time_provider import ITimeProvider


class FixedTimeProvider(ITimeProvider):
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)


def make_notification(
    recipient_user_id=None,
    actor_user_id=None,
    image_id=None,
    notification_type=NotificationType.LIKE,
    is_read=False,
) -> Notification:
    return Notification(
        id=uuid4(),
        recipient_user_id=recipient_user_id or uuid4(),
        actor_user_id=actor_user_id or uuid4(),
        image_id=image_id or uuid4(),
        notification_type=notification_type,
        is_read=is_read,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


class TestCreateNotification:
    def test_persists_notification_with_correct_fields(self) -> None:
        repo = Mock(spec=INotificationRepository)
        recipient_id = uuid4()
        actor_id = uuid4()
        image_id = uuid4()
        notification = make_notification(recipient_user_id=recipient_id, actor_user_id=actor_id, image_id=image_id)
        repo.add.return_value = notification

        service = NotificationService(repo, FixedTimeProvider())
        result = service.create_notification(
            recipient_user_id=recipient_id,
            actor_user_id=actor_id,
            image_id=image_id,
            notification_type=NotificationType.LIKE,
        )

        repo.add.assert_called_once()
        assert result.recipient_user_id == recipient_id
        assert result.actor_user_id == actor_id
        assert result.image_id == image_id
        assert result.notification_type == NotificationType.LIKE
        assert result.is_read is False

    def test_creates_comment_notification(self) -> None:
        repo = Mock(spec=INotificationRepository)
        notification = make_notification(notification_type=NotificationType.COMMENT)
        repo.add.return_value = notification

        service = NotificationService(repo, FixedTimeProvider())
        result = service.create_notification(
            recipient_user_id=uuid4(),
            actor_user_id=uuid4(),
            image_id=uuid4(),
            notification_type=NotificationType.COMMENT,
        )

        assert result.notification_type == NotificationType.COMMENT


class TestGetUserNotifications:
    def test_returns_notifications_for_user(self) -> None:
        repo = Mock(spec=INotificationRepository)
        user_id = uuid4()
        notifications = [make_notification(recipient_user_id=user_id) for _ in range(3)]
        repo.get_for_user.return_value = notifications

        service = NotificationService(repo, FixedTimeProvider())
        result = service.get_user_notifications(user_id, limit=10)

        repo.get_for_user.assert_called_once_with(user_id, limit=10)
        assert len(result) == 3

    def test_returns_empty_list_when_no_notifications(self) -> None:
        repo = Mock(spec=INotificationRepository)
        repo.get_for_user.return_value = []

        service = NotificationService(repo, FixedTimeProvider())
        result = service.get_user_notifications(uuid4())

        assert result == []


class TestMarkAsRead:
    def test_marks_notification_as_read(self) -> None:
        repo = Mock(spec=INotificationRepository)
        user_id = uuid4()
        notification_id = uuid4()
        read_notification = make_notification(recipient_user_id=user_id, is_read=True)
        repo.mark_as_read.return_value = read_notification

        service = NotificationService(repo, FixedTimeProvider())
        result = service.mark_as_read(notification_id, user_id)

        repo.mark_as_read.assert_called_once_with(notification_id, user_id)
        assert result.is_read is True

    def test_raises_not_found_when_notification_does_not_exist(self) -> None:
        repo = Mock(spec=INotificationRepository)
        repo.mark_as_read.return_value = None

        service = NotificationService(repo, FixedTimeProvider())

        with pytest.raises(NotificationNotFoundError):
            service.mark_as_read(uuid4(), uuid4())


class TestCountUnread:
    def test_returns_unread_count(self) -> None:
        repo = Mock(spec=INotificationRepository)
        repo.count_unread.return_value = 5

        service = NotificationService(repo, FixedTimeProvider())
        result = service.count_unread(uuid4())

        assert result == 5

    def test_returns_zero_when_all_read(self) -> None:
        repo = Mock(spec=INotificationRepository)
        repo.count_unread.return_value = 0

        service = NotificationService(repo, FixedTimeProvider())
        result = service.count_unread(uuid4())

        assert result == 0
