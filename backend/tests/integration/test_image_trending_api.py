from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from src.adapters.outbound.persistence.database import get_db
from src.adapters.outbound.persistence.sqlalchemy_image_repository import SQLAlchemyImageRepository
from src.application.dependencies import get_s3_presigner, get_time_provider
from src.domain.images.services import ImageService
from src.main import app

from tests.conftest import TestSessionLocal, override_get_db


class FixedTimeProvider:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, 12, tzinfo=UTC)


@pytest.fixture
def client() -> Generator[TestClient]:
    class FakePresigner:
        bucket = "test-bucket"
        region = "us-east-1"
        upload_prefix = "images"

        def presign_get(self, storage_key: str, expires_in: int | None = None) -> str:
            return f"https://signed.example.com/{storage_key}"

        def get_object_info(self, storage_key: str) -> SimpleNamespace | None:
            return SimpleNamespace(content_length=1024, content_type="image/jpeg")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_s3_presigner] = FakePresigner
    app.dependency_overrides[get_time_provider] = FixedTimeProvider

    with patch("src.main.create_tables"), TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def create_user_and_get_token(client: TestClient, username: str) -> tuple[str, str]:
    unique_username = f"{username}_{uuid4().hex[:8]}"
    password = "TestPassword123!"
    resp = client.post(
        "/users/register",
        json={
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "first_name": "Trend",
            "last_name": "User",
            "user_password": password,
        },
    )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    token_resp = client.post(
        "/users/token",
        data={"username": unique_username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 200
    return user_id, token_resp.json()["access_token"]


def create_image(client: TestClient, owner_user_id: str, description: str, hashtags: list[str], token: str) -> None:
    resp = client.post(
        "/images",
        json={
            "owner_user_id": owner_user_id,
            "description": description,
            "hashtags": hashtags,
            "mentions_user_ids": [],
            "image_url": f"https://test-bucket.s3.us-east-1.amazonaws.com/images/{owner_user_id}/{uuid4()}.jpg",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


def process_trends(batch_size: int = 500) -> int:
    with TestSessionLocal() as session:
        service = ImageService(SQLAlchemyImageRepository(session), FixedTimeProvider())
        processed = service.process_pending_search_events(batch_size=batch_size)
        session.commit()
        return processed


def test_search_events_are_aggregated_into_daily_trends(client: TestClient) -> None:
    user_id, token = create_user_and_get_token(client, "trend_api")
    create_image(client, user_id, "Sunny beach escape", ["beach"], token)
    create_image(client, user_id, "Bright skyline", ["city"], token)

    before = client.get("/images/trending-keywords?limit=5&window=today", headers={"Authorization": f"Bearer {token}"})
    assert before.status_code == 200
    assert before.json()["hashtags"] == []
    assert before.json()["description_keywords"] == []

    client.get("/images/hashtags/beach", headers={"Authorization": f"Bearer {token}"})
    client.get("/images/hashtags/beach", headers={"Authorization": f"Bearer {token}"})
    client.get("/images/description/sunny", headers={"Authorization": f"Bearer {token}"})
    client.get("/images/description/unknown", headers={"Authorization": f"Bearer {token}"})

    still_unprocessed = client.get(
        "/images/trending-keywords?limit=5&window=today",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert still_unprocessed.status_code == 200
    assert still_unprocessed.json()["hashtags"] == []
    assert still_unprocessed.json()["description_keywords"] == []

    assert process_trends() == 4

    resp = client.get("/images/trending-keywords?limit=5&window=today", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["hashtags"] == [{"keyword": "beach", "count": 2}]
    assert data["description_keywords"] == [
        {"keyword": "sunny", "count": 1},
        {"keyword": "unknown", "count": 1},
    ]
    assert data["generated_from"] == {
        "source_fields": ["search_events.keyword", "search_events.trend_type", "search_trends_daily.search_count"],
        "window": "today",
        "count_unit": "searches",
        "aggregation_mode": "async_daily_aggregate",
    }


def test_trending_keywords_window_today_filters_out_older_searches(client: TestClient) -> None:
    user_id, token = create_user_and_get_token(client, "trend_window")
    create_image(client, user_id, "Sunny beach escape", ["beach"], token)

    client.get("/images/hashtags/beach", headers={"Authorization": f"Bearer {token}"})

    with TestSessionLocal() as db:
        db.execute(
            text(
                "UPDATE search_events SET search_date = :search_date, searched_at = :searched_at WHERE keyword = :keyword"
            ),
            {
                "search_date": datetime(2025, 12, 31, tzinfo=UTC).date(),
                "searched_at": datetime(2025, 12, 31, 23, tzinfo=UTC),
                "keyword": "beach",
            },
        )
        db.commit()

    client.get("/images/description/sunny", headers={"Authorization": f"Bearer {token}"})

    assert process_trends() == 2

    today_resp = client.get(
        "/images/trending-keywords?limit=5&window=today", headers={"Authorization": f"Bearer {token}"}
    )
    all_time_resp = client.get(
        "/images/trending-keywords?limit=5&window=all_time", headers={"Authorization": f"Bearer {token}"}
    )

    assert today_resp.status_code == 200
    assert today_resp.json()["hashtags"] == []
    assert today_resp.json()["description_keywords"] == [{"keyword": "sunny", "count": 1}]

    assert all_time_resp.status_code == 200
    assert all_time_resp.json()["hashtags"] == [{"keyword": "beach", "count": 1}]
    assert all_time_resp.json()["description_keywords"] == [{"keyword": "sunny", "count": 1}]


def test_list_trending_keywords_requires_authentication(client: TestClient) -> None:
    resp = client.get("/images/trending-keywords")
    assert resp.status_code == 401
