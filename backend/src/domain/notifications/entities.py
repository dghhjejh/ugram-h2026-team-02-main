from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class NotificationType(StrEnum):
    COMMENT = "comment"
    LIKE = "like"


@dataclass
class Notification:
    id: UUID
    recipient_user_id: UUID
    actor_user_id: UUID
    image_id: UUID
    notification_type: NotificationType
    is_read: bool
    created_at: datetime
