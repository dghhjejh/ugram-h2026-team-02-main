from abc import ABC, abstractmethod
from datetime import date, datetime
from uuid import UUID

from src.domain.images.entities import FeedImageItem, Image, SearchTrendStat


class IImageRepository(ABC):
    @abstractmethod
    def save(self, image: Image) -> Image:
        pass

    @abstractmethod
    def get_by_id(self, image_id: UUID) -> Image | None:
        pass

    @abstractmethod
    def get_all_by_hashtag(self, hashtag: str) -> list[Image]:
        pass

    @abstractmethod
    def get_all_by_description_keyword(self, keyword: str) -> list[Image]:
        pass

    @abstractmethod
    def get_all_by_owner(self, owner_id: UUID, limit: int, offset: int) -> list[Image]:
        pass

    @abstractmethod
    def enqueue_search_event(self, keyword: str, trend_type: str, search_date: date, searched_at: datetime) -> None:
        pass

    @abstractmethod
    def process_pending_search_events(self, batch_size: int, processed_at: datetime) -> int:
        pass

    @abstractmethod
    def list_search_trends(self, search_date: date | None = None) -> list[SearchTrendStat]:
        pass

    @abstractmethod
    def delete(self, image_id: UUID) -> bool:
        """Delete image by ID. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    def get_feed(
        self,
        limit: int,
        cursor_created_at: datetime | None = None,
        cursor_image_id: UUID | None = None,
    ) -> list[FeedImageItem]:
        pass

    @abstractmethod
    def get_autocomplete_descriptions(self, partial: str) -> list[str]:
        """Get auto-complete suggestions for image descriptions."""
        pass

    @abstractmethod
    def get_autocomplete_hashtags(self, partial: str) -> list[str]:
        """Get auto-complete suggestions for image hashtags."""
        pass
