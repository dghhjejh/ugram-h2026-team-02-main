from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from src.adapters.outbound.persistence.database import get_db
from src.application.dependencies import get_s3_presigner
from src.main import app

from tests.conftest import override_get_db


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
            "first_name": "Test",
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


def create_image(client: TestClient, owner_user_id: str, token: str) -> dict:
    resp = client.post(
        "/images",
        json={
            "owner_user_id": owner_user_id,
            "description": "test image",
            "hashtags": [],
            "mentions_user_ids": [],
            "image_url": f"https://test-bucket.s3.us-east-1.amazonaws.com/images/{owner_user_id}/{uuid4().hex}.jpg",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()


class TestListNotifications:
    def test_returns_empty_list_for_new_user(self, client: TestClient) -> None:
        _, token = create_user_and_get_token(client, "owner")

        resp = client.get("/notifications/", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["notifications"] == []
        assert data["unread_count"] == 0
        assert data["total"] == 0

    def test_requires_authentication(self, client: TestClient) -> None:
        resp = client.get("/notifications/")

        assert resp.status_code == 401

    def test_like_creates_notification_for_owner(self, client: TestClient) -> None:
        owner_id, owner_token = create_user_and_get_token(client, "owner")
        _, liker_token = create_user_and_get_token(client, "liker")
        image = create_image(client, owner_id, owner_token)

        client.post(
            f"/images/{image['id']}/likes",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        resp = client.get("/notifications/", headers={"Authorization": f"Bearer {owner_token}"})
        data = resp.json()

        assert data["unread_count"] == 1
        assert len(data["notifications"]) == 1
        assert data["notifications"][0]["notification_type"] == "like"
        assert data["notifications"][0]["image_id"] == image["id"]
        assert data["notifications"][0]["is_read"] is False

    def test_comment_creates_notification_for_owner(self, client: TestClient) -> None:
        owner_id, owner_token = create_user_and_get_token(client, "owner")
        _, commenter_token = create_user_and_get_token(client, "commenter")
        image = create_image(client, owner_id, owner_token)

        client.post(
            f"/images/{image['id']}/comments",
            json={"content": "nice photo!"},
            headers={"Authorization": f"Bearer {commenter_token}"},
        )

        resp = client.get("/notifications/", headers={"Authorization": f"Bearer {owner_token}"})
        data = resp.json()

        assert data["unread_count"] == 1
        assert data["notifications"][0]["notification_type"] == "comment"

    def test_no_self_notification_on_like(self, client: TestClient) -> None:
        owner_id, owner_token = create_user_and_get_token(client, "owner")
        image = create_image(client, owner_id, owner_token)

        client.post(
            f"/images/{image['id']}/likes",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        resp = client.get("/notifications/", headers={"Authorization": f"Bearer {owner_token}"})
        assert resp.json()["unread_count"] == 0

    def test_no_self_notification_on_comment(self, client: TestClient) -> None:
        owner_id, owner_token = create_user_and_get_token(client, "owner")
        image = create_image(client, owner_id, owner_token)

        client.post(
            f"/images/{image['id']}/comments",
            json={"content": "my own photo"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        resp = client.get("/notifications/", headers={"Authorization": f"Bearer {owner_token}"})
        assert resp.json()["unread_count"] == 0

    def test_multiple_notifications_ordered_by_most_recent(self, client: TestClient) -> None:
        owner_id, owner_token = create_user_and_get_token(client, "owner")
        _, actor_token = create_user_and_get_token(client, "actor")
        image = create_image(client, owner_id, owner_token)

        client.post(f"/images/{image['id']}/likes", headers={"Authorization": f"Bearer {actor_token}"})
        client.post(
            f"/images/{image['id']}/comments",
            json={"content": "great!"},
            headers={"Authorization": f"Bearer {actor_token}"},
        )

        resp = client.get("/notifications/", headers={"Authorization": f"Bearer {owner_token}"})
        data = resp.json()

        assert data["unread_count"] == 2
        assert data["notifications"][0]["notification_type"] == "comment"
        assert data["notifications"][1]["notification_type"] == "like"

    def test_notifications_isolated_between_users(self, client: TestClient) -> None:
        owner_a_id, owner_a_token = create_user_and_get_token(client, "owner_a")
        owner_b_id, owner_b_token = create_user_and_get_token(client, "owner_b")
        _, liker_token = create_user_and_get_token(client, "liker")

        image_a = create_image(client, owner_a_id, owner_a_token)
        client.post(f"/images/{image_a['id']}/likes", headers={"Authorization": f"Bearer {liker_token}"})

        resp = client.get("/notifications/", headers={"Authorization": f"Bearer {owner_b_token}"})
        assert resp.json()["unread_count"] == 0


class TestMarkNotificationRead:
    def test_marks_notification_as_read(self, client: TestClient) -> None:
        owner_id, owner_token = create_user_and_get_token(client, "owner")
        _, liker_token = create_user_and_get_token(client, "liker")
        image = create_image(client, owner_id, owner_token)

        client.post(f"/images/{image['id']}/likes", headers={"Authorization": f"Bearer {liker_token}"})
        notifications = client.get("/notifications/", headers={"Authorization": f"Bearer {owner_token}"}).json()[
            "notifications"
        ]
        notification_id = notifications[0]["id"]

        resp = client.patch(
            f"/notifications/{notification_id}/read",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert resp.status_code == 200
        assert resp.json()["is_read"] is True

    def test_unread_count_decrements_after_mark_read(self, client: TestClient) -> None:
        owner_id, owner_token = create_user_and_get_token(client, "owner")
        _, liker_token = create_user_and_get_token(client, "liker")
        image = create_image(client, owner_id, owner_token)

        client.post(f"/images/{image['id']}/likes", headers={"Authorization": f"Bearer {liker_token}"})
        notification_id = client.get("/notifications/", headers={"Authorization": f"Bearer {owner_token}"}).json()[
            "notifications"
        ][0]["id"]

        client.patch(f"/notifications/{notification_id}/read", headers={"Authorization": f"Bearer {owner_token}"})

        resp = client.get("/notifications/", headers={"Authorization": f"Bearer {owner_token}"})
        assert resp.json()["unread_count"] == 0

    def test_returns_404_for_nonexistent_notification(self, client: TestClient) -> None:
        _, token = create_user_and_get_token(client, "user")

        resp = client.patch(
            f"/notifications/{uuid4()}/read",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 404

    def test_cannot_mark_another_users_notification_as_read(self, client: TestClient) -> None:
        owner_id, owner_token = create_user_and_get_token(client, "owner")
        _, liker_token = create_user_and_get_token(client, "liker")
        _, other_token = create_user_and_get_token(client, "other")
        image = create_image(client, owner_id, owner_token)

        client.post(f"/images/{image['id']}/likes", headers={"Authorization": f"Bearer {liker_token}"})
        notification_id = client.get("/notifications/", headers={"Authorization": f"Bearer {owner_token}"}).json()[
            "notifications"
        ][0]["id"]

        resp = client.patch(
            f"/notifications/{notification_id}/read",
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert resp.status_code == 404

    def test_requires_authentication(self, client: TestClient) -> None:
        resp = client.patch(f"/notifications/{uuid4()}/read")

        assert resp.status_code == 401
