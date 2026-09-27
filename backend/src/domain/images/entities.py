from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID


@dataclass
class MentionTag:
    """Represents a positioned mention tag on an image."""

    user_id: UUID
    x_percent: float
    y_percent: float


@dataclass
class Image:
    id: UUID
    owner_user_id: UUID
    description: str
    hashtags: list[str]
    mentions_user_ids: list[UUID]
    mention_tags: list[MentionTag]
    image_url: str  # stored URL or key in object storage
    created_at: datetime
    updated_at: datetime


@dataclass
class ImageMetadata:
    image_id: UUID
    width: int
    height: int
    format: str


@dataclass
class FeedImageItem:
    image: Image
    owner_username: str
    owner_profile_photo_url: str | None
    like_count: int = 0
    comment_count: int = 0


@dataclass
class FeedPage:
    items: list[FeedImageItem]
    next_cursor: str | None
    has_more: bool


@dataclass(frozen=True)
class SearchTrendStat:
    keyword: str
    trend_type: Literal["hashtag", "description"]
    count: int
    search_date: date | None = None


@dataclass(frozen=True)
class TrendingKeyword:
    keyword: str
    count: int


@dataclass(frozen=True)
class TrendingKeywordSnapshot:
    hashtags: list[TrendingKeyword]
    description_keywords: list[TrendingKeyword]
