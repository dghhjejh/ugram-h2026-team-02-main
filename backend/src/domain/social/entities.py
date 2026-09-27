from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Reaction:
    id: UUID
    user_id: UUID
    target_id: UUID
    type: str
    created_at: datetime


@dataclass
class Comment:
    id: UUID
    user_id: UUID
    target_id: UUID
    content: str
    created_at: datetime
