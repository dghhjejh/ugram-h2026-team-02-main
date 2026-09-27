import base64
import json
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from src.domain.images.entities import (
    FeedPage,
    Image,
    MentionTag,
    SearchTrendStat,
    TrendingKeyword,
    TrendingKeywordSnapshot,
)
from src.domain.images.repositories import IImageRepository
from src.domain.time_provider import ITimeProvider


class ImageNotFoundError(Exception):
    """Raised when an image cannot be found."""


class ImageFeedCursorError(Exception):
    """Raised when feed cursor cannot be decoded."""


class ImageService:
    """Image use cases: create, fetch, list."""

    def __init__(self, image_repo: IImageRepository, time_provider: ITimeProvider) -> None:
        self._repo = image_repo
        self._time = time_provider

    def create_image(
        self,
        owner_user_id: UUID,
        description: str,
        image_url: str,
        hashtags: list[str] | None = None,
        mentions_user_ids: list[UUID] | None = None,
        mention_tags: list[MentionTag] | None = None,
    ) -> Image:
        """Create and persist an image record (metadata only)."""
        now = self._time.now()
        image = Image(
            id=uuid4(),
            owner_user_id=owner_user_id,
            description=description or "",
            hashtags=hashtags or [],
            mentions_user_ids=mentions_user_ids or [],
            mention_tags=mention_tags or [],
            image_url=image_url,
            created_at=now,
            updated_at=now,
        )
        return self._repo.save(image)

    def get_all_images_by_hashtag(self, hashtag: str) -> list[Image]:
        """Retrieve images associated with a specific hashtag."""
        return self._repo.get_all_by_hashtag(hashtag)

    def get_all_images_by_description_keyword(self, keyword: str) -> list[Image]:
        """Retrieve images whose description contains a specific keyword."""
        return self._repo.get_all_by_description_keyword(keyword)

    def record_search(self, keyword: str, trend_type: Literal["hashtag", "description"]) -> None:
        normalized_keyword = keyword.strip().lower()
        if not normalized_keyword:
            return
        searched_at = self._time.now()
        self._repo.enqueue_search_event(
            keyword=normalized_keyword,
            trend_type=trend_type,
            search_date=searched_at.date(),
            searched_at=searched_at,
        )

    def get_trending_keywords(
        self, limit: int, window: Literal["all_time", "today"] = "all_time"
    ) -> TrendingKeywordSnapshot:
        search_date = self._time.now().date() if window == "today" else None
        trends = self._repo.list_search_trends(search_date=search_date)

        return TrendingKeywordSnapshot(
            hashtags=self._rank_trends(trends, "hashtag")[:limit],
            description_keywords=self._rank_trends(trends, "description")[:limit],
        )

    def process_pending_search_events(self, batch_size: int = 500) -> int:
        return self._repo.process_pending_search_events(
            batch_size=batch_size,
            processed_at=self._time.now(),
        )

    def get_image(self, image_id: UUID) -> Image:
        image = self._repo.get_by_id(image_id)
        if not image:
            raise ImageNotFoundError(f"Image {image_id} not found")
        return image

    def list_user_images(self, owner_user_id: UUID, limit: int, offset: int) -> list[Image]:
        return self._repo.get_all_by_owner(owner_user_id, limit=limit, offset=offset)

    def delete_image(self, image_id: UUID) -> None:
        """Delete an image by its ID."""
        deleted = self._repo.delete(image_id)
        if not deleted:
            raise ImageNotFoundError(f"Image {image_id} not found")

    def list_feed(self, limit: int, cursor: str | None = None) -> FeedPage:
        cursor_created_at: datetime | None = None
        cursor_image_id: UUID | None = None

        if cursor:
            cursor_created_at, cursor_image_id = self._decode_cursor(cursor)

        rows = self._repo.get_feed(
            limit=limit + 1,
            cursor_created_at=cursor_created_at,
            cursor_image_id=cursor_image_id,
        )
        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last_image = items[-1].image
            next_cursor = self._encode_cursor(last_image.created_at, last_image.id)

        return FeedPage(items=items, next_cursor=next_cursor, has_more=has_more)

    @staticmethod
    def _encode_cursor(created_at: datetime, image_id: UUID) -> str:
        payload = {"created_at": created_at.isoformat(), "id": str(image_id)}
        token = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(token).decode("utf-8")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("utf-8"))
            payload = json.loads(raw)
            created_at = datetime.fromisoformat(payload["created_at"])
            image_id = UUID(payload["id"])
            return created_at, image_id
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ImageFeedCursorError("Invalid feed cursor") from exc

    def update_image_metadata(
        self,
        image_id: UUID,
        description: str | None = None,
        hashtags: list[str] | None = None,
        mentions_user_ids: list[UUID] | None = None,
        mention_tags: list[MentionTag] | None = None,
    ) -> Image:
        image = self._repo.get_by_id(image_id)
        if not image:
            raise ImageNotFoundError(f"Image {image_id} not found")

        updated = False

        if description is not None and image.description != description:
            image.description = description
            updated = True

        if hashtags is not None and image.hashtags != hashtags:
            image.hashtags = hashtags
            updated = True

        if mentions_user_ids is not None and image.mentions_user_ids != mentions_user_ids:
            image.mentions_user_ids = mentions_user_ids
            updated = True

        if mention_tags is not None:
            allowed_ids = set(mentions_user_ids if mentions_user_ids is not None else image.mentions_user_ids)
            filtered_tags = [tag for tag in mention_tags if tag.user_id in allowed_ids]
            if image.mention_tags != filtered_tags:
                image.mention_tags = filtered_tags
                updated = True
        elif mentions_user_ids is not None:
            filtered_existing_tags = [tag for tag in image.mention_tags if tag.user_id in set(image.mentions_user_ids)]
            if image.mention_tags != filtered_existing_tags:
                image.mention_tags = filtered_existing_tags
                updated = True

        if updated:
            image.updated_at = self._time.now()
            self._repo.save(image)

        return image

    def get_autocomplete_descriptions(self, partial: str) -> list[str]:
        """Get auto-complete suggestions for image descriptions."""
        return self._repo.get_autocomplete_descriptions(partial)

    def get_autocomplete_hashtags(self, partial: str) -> list[str]:
        """Get auto-complete suggestions for image hashtags."""
        return self._repo.get_autocomplete_hashtags(partial)

    @staticmethod
    def _rank_trends(
        trends: list[SearchTrendStat],
        trend_type: Literal["hashtag", "description"],
    ) -> list[TrendingKeyword]:
        ranked = sorted(
            (trend for trend in trends if trend.trend_type == trend_type),
            key=lambda item: (-item.count, item.keyword),
        )
        return [TrendingKeyword(keyword=trend.keyword, count=trend.count) for trend in ranked]
