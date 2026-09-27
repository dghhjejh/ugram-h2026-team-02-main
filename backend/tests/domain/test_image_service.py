from datetime import UTC, datetime
from unittest.mock import Mock

from src.domain.images.entities import SearchTrendStat, TrendingKeyword
from src.domain.images.repositories import IImageRepository
from src.domain.images.services import ImageService
from src.domain.time_provider import ITimeProvider


class FixedTimeProvider(ITimeProvider):
    def now(self) -> datetime:
        return datetime(2026, 1, 1, 12, tzinfo=UTC)


def test_record_search_normalizes_and_enqueues_event() -> None:
    repo = Mock(spec=IImageRepository)
    service = ImageService(repo, FixedTimeProvider())

    service.record_search("  Beach  ", "hashtag")

    repo.enqueue_search_event.assert_called_once_with(
        keyword="beach",
        trend_type="hashtag",
        search_date=datetime(2026, 1, 1, 12, tzinfo=UTC).date(),
        searched_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )


def test_get_trending_keywords_returns_ranked_search_counts() -> None:
    repo = Mock(spec=IImageRepository)
    repo.list_search_trends.return_value = [
        SearchTrendStat(keyword="beach", trend_type="description", count=4),
        SearchTrendStat(keyword="cat", trend_type="description", count=2),
        SearchTrendStat(keyword="vacay", trend_type="hashtag", count=3),
        SearchTrendStat(keyword="beach", trend_type="hashtag", count=5),
    ]

    service = ImageService(repo, FixedTimeProvider())

    trends = service.get_trending_keywords(limit=2, window="today")

    repo.list_search_trends.assert_called_once_with(search_date=datetime(2026, 1, 1, 12, tzinfo=UTC).date())
    assert trends.hashtags == [
        TrendingKeyword(keyword="beach", count=5),
        TrendingKeyword(keyword="vacay", count=3),
    ]
    assert trends.description_keywords == [
        TrendingKeyword(keyword="beach", count=4),
        TrendingKeyword(keyword="cat", count=2),
    ]


def test_process_pending_search_events_delegates_to_repo() -> None:
    repo = Mock(spec=IImageRepository)
    repo.process_pending_search_events.return_value = 7

    service = ImageService(repo, FixedTimeProvider())

    processed = service.process_pending_search_events(batch_size=250)

    assert processed == 7
    repo.process_pending_search_events.assert_called_once_with(
        batch_size=250,
        processed_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
