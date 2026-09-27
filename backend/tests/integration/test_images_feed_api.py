"""Integration tests for global image feed endpoint.

These tests verify authentication, pagination behavior, and response shape
for the /images/feed API.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from src.adapters.outbound.persistence.models import ImageORM
from src.application.dependencies import get_s3_presigner
from src.main import app

from tests.conftest import TestSessionLocal

# Test constants
VALID_PASSWORD = "SecurePassword123!"  # pragma: allowlist secret
FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"

HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401

ENDPOINT_REGISTER = "/users/register"
ENDPOINT_TOKEN = "/users/token"
ENDPOINT_IMAGES = "/images"
ENDPOINT_FEED = "/images/feed"

ERROR_INVALID_FEED_CURSOR = "Invalid feed cursor"


@dataclass
class FeedUserAuth:
    """Authenticated user test context."""

    user_id: str
    token: str


class FakePresigner:
    """Deterministic presigner to avoid real AWS calls in feed tests."""

    bucket = "test-bucket"
    region = "us-east-1"
    upload_prefix = "images"

    def presign_get(self, storage_key: str, expires_in: int | None = None) -> str:  # noqa: ARG002
        return f"https://signed.example.com/{storage_key}"

    def get_object_info(self, storage_key: str) -> SimpleNamespace | None:  # noqa: ARG002
        return SimpleNamespace(content_length=1024, content_type="image/jpeg")


class BrokenPresigner(FakePresigner):
    """Presigner that fails to sign view URLs so endpoints must fall back."""

    def presign_get(self, storage_key: str, expires_in: int | None = None) -> str:  # noqa: ARG002
        raise RuntimeError("presign unavailable")


class FeedAPIClient:
    """Helper class for feed API operations."""

    def __init__(self, client: TestClient) -> None:
        self.client = client

    @staticmethod
    def _auth_headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def register_and_login(self, username: str, profile_photo_url: str | None = None) -> FeedUserAuth:
        """Create a user then return authenticated context."""
        payload = {
            "username": username,
            "email": f"{username}@example.com",
            "first_name": "Feed",
            "last_name": "User",
            "user_password": VALID_PASSWORD,
        }
        if profile_photo_url is not None:
            payload["profile_photo_url"] = profile_photo_url

        register_response = self.client.post(
            ENDPOINT_REGISTER,
            json=payload,
        )
        assert register_response.status_code == HTTP_201_CREATED
        user_id = register_response.json()["id"]

        login_response = self.client.post(
            ENDPOINT_TOKEN,
            data={"username": username, "password": VALID_PASSWORD},
            headers={"Content-Type": FORM_CONTENT_TYPE},
        )
        assert login_response.status_code == HTTP_200_OK
        token = login_response.json()["access_token"]

        return FeedUserAuth(user_id=user_id, token=token)

    def create_image(self, owner_user_id: str, label: str, token: str) -> UUID:
        """Create an image metadata row."""
        image_url = f"https://test-bucket.s3.us-east-1.amazonaws.com/images/{owner_user_id}/{label}.jpg"
        response = self.client.post(
            ENDPOINT_IMAGES,
            json={
                "owner_user_id": owner_user_id,
                "description": f"{label}-description",
                "hashtags": [label],
                "mentions_user_ids": [],
                "image_url": image_url,
            },
            headers=self._auth_headers(token),
        )
        assert response.status_code == HTTP_201_CREATED
        return UUID(response.json()["id"])

    def list_feed(self, token: str, limit: int = 12, cursor: str | None = None) -> tuple[int, dict[str, Any]]:
        """Fetch feed page with optional keyset cursor."""
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor

        response = self.client.get(
            ENDPOINT_FEED,
            params=params,
            headers=self._auth_headers(token),
        )
        return response.status_code, response.json()

    def like_image(self, image_id: UUID, token: str) -> int:
        response = self.client.post(
            f"{ENDPOINT_IMAGES}/{image_id}/likes",
            headers=self._auth_headers(token),
        )
        return response.status_code

    def comment_image(self, image_id: UUID, token: str, content: str) -> int:
        response = self.client.post(
            f"{ENDPOINT_IMAGES}/{image_id}/comments",
            json={"content": content},
            headers=self._auth_headers(token),
        )
        return response.status_code


@pytest.fixture
def feed_api(client: TestClient) -> FeedAPIClient:
    """Provide a feed API client with deterministic signed URLs."""
    app.dependency_overrides[get_s3_presigner] = FakePresigner
    return FeedAPIClient(client)


class TestFeedAuthentication:
    """Tests related to feed authentication requirements."""

    def test_requires_bearer_token(self, client: TestClient) -> None:
        """Request without token should return 401."""
        response = client.get(ENDPOINT_FEED)
        assert response.status_code == HTTP_401_UNAUTHORIZED


class TestFeedListing:
    """Tests for standard feed listing behavior."""

    def test_returns_empty_when_no_images(self, feed_api: FeedAPIClient) -> None:
        """Fresh user should get an empty feed response."""
        auth = feed_api.register_and_login("emptyfeeduser")

        status, payload = feed_api.list_feed(auth.token)

        assert status == HTTP_200_OK
        assert payload["items"] == []
        assert payload["next_cursor"] is None
        assert payload["has_more"] is False

    def test_rejects_invalid_cursor(self, feed_api: FeedAPIClient) -> None:
        """Malformed cursor should return a 400 with clear message."""
        auth = feed_api.register_and_login("invalidcursoruser")

        status, payload = feed_api.list_feed(auth.token, cursor="not-a-valid-cursor")

        assert status == HTTP_400_BAD_REQUEST
        assert payload["detail"] == ERROR_INVALID_FEED_CURSOR

    def test_accepts_limit_max_value(self, feed_api: FeedAPIClient) -> None:
        """API should allow the max limit boundary."""
        auth = feed_api.register_and_login("limitmaxuser")
        feed_api.create_image(auth.user_id, "single", auth.token)

        status, payload = feed_api.list_feed(auth.token, limit=100)

        assert status == HTTP_200_OK
        assert len(payload["items"]) == 1
        assert payload["has_more"] is False
        assert payload["next_cursor"] is None

    def test_signs_owner_profile_photo_url_for_s3_images(self, feed_api: FeedAPIClient) -> None:
        """Owner profile photo URL should be signed when it points to private S3."""
        owner_photo_url = "https://test-bucket.s3.us-east-1.amazonaws.com/profile-photos/feed-owner.jpg"
        auth = feed_api.register_and_login("feedprofileowner", profile_photo_url=owner_photo_url)
        feed_api.create_image(auth.user_id, "owner-photo", auth.token)

        status, payload = feed_api.list_feed(auth.token, limit=10)

        assert status == HTTP_200_OK
        assert len(payload["items"]) == 1
        assert payload["items"][0]["owner_profile_photo_url"] == (
            "https://signed.example.com/profile-photos/feed-owner.jpg"
        )

    def test_returns_like_and_comment_counts(self, feed_api: FeedAPIClient) -> None:
        owner = feed_api.register_and_login("feedcountowner")
        fan = feed_api.register_and_login("feedcountfan")

        image_with_engagement = feed_api.create_image(owner.user_id, "with-engagement", owner.token)
        image_without_engagement = feed_api.create_image(owner.user_id, "without-engagement", owner.token)

        assert feed_api.like_image(image_with_engagement, fan.token) == HTTP_201_CREATED
        assert feed_api.comment_image(image_with_engagement, fan.token, "nice shot") == HTTP_201_CREATED
        assert feed_api.comment_image(image_with_engagement, owner.token, "thanks") == HTTP_201_CREATED

        status, payload = feed_api.list_feed(owner.token, limit=10)

        assert status == HTTP_200_OK
        by_id = {item["id"]: item for item in payload["items"]}
        engaged_item = by_id[str(image_with_engagement)]
        empty_item = by_id[str(image_without_engagement)]

        assert engaged_item["like_count"] == 1
        assert engaged_item["comment_count"] == 2
        assert empty_item["like_count"] == 0
        assert empty_item["comment_count"] == 0

    def test_returns_variant_urls_when_available(self, feed_api: FeedAPIClient) -> None:
        owner = feed_api.register_and_login("feedvariantsowner")
        feed_api.create_image(owner.user_id, "variant-available", owner.token)

        status, payload = feed_api.list_feed(owner.token, limit=10)

        assert status == HTTP_200_OK
        assert len(payload["items"]) == 1
        item = payload["items"][0]
        assert ".large.jpg" in item["view_url"]
        assert ".medium.jpg" in item["feed_view_url"]


class TestFeedPagination:
    """Tests for keyset pagination behavior."""

    def test_keyset_orders_by_created_at_then_id(self, feed_api: FeedAPIClient) -> None:
        """Feed should paginate deterministically with (created_at, id) ordering."""
        owner_a = feed_api.register_and_login("feedownera")
        owner_b = feed_api.register_and_login("feedownerb")

        image_a = feed_api.create_image(owner_a.user_id, "a", owner_a.token)
        image_b = feed_api.create_image(owner_a.user_id, "b", owner_a.token)
        image_c = feed_api.create_image(owner_b.user_id, "c", owner_b.token)
        image_d = feed_api.create_image(owner_b.user_id, "d", owner_b.token)

        newest_shared_ts = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
        older_ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        target_ids = {image_a, image_b, image_c, image_d}

        with TestSessionLocal() as session:
            images = session.query(ImageORM).filter(ImageORM.id.in_(target_ids)).all()
            for image in images:
                if image.id in {image_a, image_b, image_c}:
                    image.created_at = newest_shared_ts
                elif image.id == image_d:
                    image.created_at = older_ts
                image.updated_at = image.created_at
            session.commit()

        expected_order = sorted(
            [image_a, image_b, image_c, image_d],
            key=lambda image_id: (newest_shared_ts if image_id != image_d else older_ts, image_id),
            reverse=True,
        )

        status_1, payload_1 = feed_api.list_feed(owner_a.token, limit=2)
        assert status_1 == HTTP_200_OK
        assert payload_1["has_more"] is True
        assert payload_1["next_cursor"] is not None

        page_1_ids = [UUID(item["id"]) for item in payload_1["items"]]
        assert page_1_ids == expected_order[:2]
        assert payload_1["items"][0]["owner_username"] in {"feedownera", "feedownerb"}
        assert payload_1["items"][0]["view_url"].startswith("https://signed.example.com/images/")

        status_2, payload_2 = feed_api.list_feed(owner_a.token, limit=2, cursor=payload_1["next_cursor"])
        assert status_2 == HTTP_200_OK

        page_2_ids = [UUID(item["id"]) for item in payload_2["items"]]
        assert page_2_ids == expected_order[2:]
        assert payload_2["has_more"] is False
        assert payload_2["next_cursor"] is None
        assert set(page_1_ids).isdisjoint(page_2_ids)


def test_feed_falls_back_to_image_url_when_presigning_fails(client: TestClient) -> None:
    app.dependency_overrides[get_s3_presigner] = BrokenPresigner
    feed_api = FeedAPIClient(client)
    auth = feed_api.register_and_login("brokenpresignerfeed")
    feed_api.create_image(auth.user_id, "fallback", auth.token)

    status, payload = feed_api.list_feed(auth.token, limit=10)

    assert status == HTTP_200_OK
    assert len(payload["items"]) == 1
    assert payload["items"][0]["view_url"] == payload["items"][0]["image_url"]
    assert payload["items"][0]["feed_view_url"] == payload["items"][0]["image_url"]
