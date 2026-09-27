from collections.abc import Generator
from types import SimpleNamespace
from typing import Any
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
    """FastAPI test client with mocked S3 presigner."""

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
    """Create a user and return their ID and access token."""
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
    assert resp.status_code == 201, f"Failed to create user: {resp.json()}"
    user_id = resp.json()["id"]
    token_resp = client.post(
        "/users/token",
        data={"username": unique_username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 200, f"Failed to get token: {token_resp.json()}"
    return user_id, token_resp.json()["access_token"]


def create_image(
    client: TestClient, owner_user_id: str, description: str, hashtags: list[str], token: str
) -> dict[str, Any]:
    """Create an image and return the response data."""
    resp = client.post(
        "/images",
        json={
            "owner_user_id": owner_user_id,
            "description": description,
            "hashtags": hashtags,
            "mentions_user_ids": [],
            "image_url": f"https://test-bucket.s3.us-east-1.amazonaws.com/images/{owner_user_id}/{uuid4().hex}.jpg",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Failed to create image: {resp.json()}"
    return resp.json()


def test_like_image_success(client: TestClient) -> None:
    """201: Authenticated user can like an image."""
    user1_id, user1_token = create_user_and_get_token(client, "user1")
    user2_id, user2_token = create_user_and_get_token(client, "user2")
    image = create_image(client, user2_id, "Test image", [], user2_token)

    response = client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user1_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user1_id
    assert data["image_id"] == image["id"]
    assert data["created_at"] is not None
    assert "id" in data


def test_like_image_unauthenticated_fails(client: TestClient) -> None:
    """401: Unauthenticated request is rejected."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    response = client.post(f"/images/{image['id']}/likes")

    assert response.status_code == 401


def test_like_image_not_found(client: TestClient) -> None:
    """404: Liking non-existent image fails."""
    user_id, token = create_user_and_get_token(client, "user1")
    fake_image_id = str(uuid4())

    response = client.post(
        f"/images/{fake_image_id}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_like_image_already_liked_fails(client: TestClient) -> None:
    """409: User cannot like the same image twice."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    response1 = client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response1.status_code == 201

    response2 = client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response2.status_code == 409
    assert "already liked" in response2.json()["detail"]


def test_multiple_users_can_like_same_image(client: TestClient) -> None:
    """Multiple users can like the same image."""
    user1_id, user1_token = create_user_and_get_token(client, "user1")
    user2_id, user2_token = create_user_and_get_token(client, "user2")
    user3_id, user3_token = create_user_and_get_token(client, "user3")
    image = create_image(client, user1_id, "Test image", [], user1_token)

    resp1 = client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    assert resp2.status_code == 201

    resp3 = client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert resp3.status_code == 201


def test_user_can_like_own_and_others_images(client: TestClient) -> None:
    """User can like their own and other users' images."""
    user1_id, user1_token = create_user_and_get_token(client, "user1")
    user2_id, user2_token = create_user_and_get_token(client, "user2")
    image1 = create_image(client, user1_id, "User1's image", [], user1_token)
    image2 = create_image(client, user2_id, "User2's image", [], user2_token)

    resp1 = client.post(
        f"/images/{image1['id']}/likes",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        f"/images/{image2['id']}/likes",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert resp2.status_code == 201


def test_unlike_image_success(client: TestClient) -> None:
    """204: User can unlike an image they previously liked."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    # First add a like
    client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Then remove it
    response = client.delete(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204


def test_unlike_image_not_liked_idempotent(client: TestClient) -> None:
    """204: Unliking an image user didn't like returns 204 (idempotent)."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    response = client.delete(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204


def test_unlike_image_unauthenticated_fails(client: TestClient) -> None:
    """401: Unauthenticated request is rejected."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    response = client.delete(f"/images/{image['id']}/likes")

    assert response.status_code == 401


def test_unlike_image_not_found(client: TestClient) -> None:
    """404: Unliking non-existent image fails."""
    user_id, token = create_user_and_get_token(client, "user1")
    fake_image_id = str(uuid4())

    response = client.delete(
        f"/images/{fake_image_id}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_like_unlike_like_sequence(client: TestClient) -> None:
    """User can like, unlike, and like again the same image."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    resp1 = client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 201

    resp2 = client.delete(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 204

    resp3 = client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp3.status_code == 201


def test_get_like_stats_success(client: TestClient) -> None:
    """200: Get like statistics for an image."""
    user1_id, user1_token = create_user_and_get_token(client, "user1")
    user2_id, user2_token = create_user_and_get_token(client, "user2")
    user3_id, user3_token = create_user_and_get_token(client, "user3")
    image = create_image(client, user1_id, "Test image", [], user1_token)

    client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user3_token}"},
    )

    response = client.get(
        f"/images/{image['id']}/likes/stats",
        headers={"Authorization": f"Bearer {user1_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_likes"] == 3
    assert data["user_has_liked"] is True


def test_get_like_stats_user_not_liked(client: TestClient) -> None:
    """200: Stats show user_has_liked=false for users who haven't liked."""
    user1_id, user1_token = create_user_and_get_token(client, "user1")
    user2_id, user2_token = create_user_and_get_token(client, "user2")
    user3_id, user3_token = create_user_and_get_token(client, "user3")
    image = create_image(client, user1_id, "Test image", [], user1_token)

    client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user3_token}"},
    )

    response = client.get(
        f"/images/{image['id']}/likes/stats",
        headers={"Authorization": f"Bearer {user1_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_likes"] == 2
    assert data["user_has_liked"] is False


def test_get_like_stats_no_likes(client: TestClient) -> None:
    """200: Stats show 0 likes for image with no likes."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    response = client.get(
        f"/images/{image['id']}/likes/stats",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_likes"] == 0
    assert data["user_has_liked"] is False


def test_get_like_stats_unauthenticated_fails(client: TestClient) -> None:
    """401: Unauthenticated request is rejected."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    response = client.get(f"/images/{image['id']}/likes/stats")

    assert response.status_code == 401


def test_get_like_stats_image_not_found(client: TestClient) -> None:
    """404: Non-existent image returns 404."""
    user_id, token = create_user_and_get_token(client, "user1")
    fake_image_id = str(uuid4())

    response = client.get(
        f"/images/{fake_image_id}/likes/stats",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_get_like_stats_after_unlike(client: TestClient) -> None:
    """200: Stats update correctly after unlike."""
    user1_id, user1_token = create_user_and_get_token(client, "user1")
    user2_id, user2_token = create_user_and_get_token(client, "user2")
    image = create_image(client, user1_id, "Test image", [], user1_token)

    client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user2_token}"},
    )

    client.delete(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user1_token}"},
    )

    response = client.get(
        f"/images/{image['id']}/likes/stats",
        headers={"Authorization": f"Bearer {user1_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_likes"] == 1
    assert data["user_has_liked"] is False


def test_like_count_accumulates_correctly(client: TestClient) -> None:
    """Like count increases with each new user like."""
    image_owner_id, image_owner_token = create_user_and_get_token(client, "owner")
    image = create_image(client, image_owner_id, "Test image", [], image_owner_token)

    for i in range(5):
        user_id, token = create_user_and_get_token(client, f"user{i}")
        client.post(
            f"/images/{image['id']}/likes",
            headers={"Authorization": f"Bearer {token}"},
        )

        stats_resp = client.get(
            f"/images/{image['id']}/likes/stats",
            headers={"Authorization": f"Bearer {image_owner_token}"},
        )
        assert stats_resp.status_code == 200
        assert stats_resp.json()["total_likes"] == i + 1


def test_likes_are_independent_across_images(client: TestClient) -> None:
    """Liking one image doesn't affect another image."""
    user_id, token = create_user_and_get_token(client, "user1")
    owner_id, owner_token = create_user_and_get_token(client, "owner")
    image1 = create_image(client, owner_id, "Image 1", [], owner_token)
    image2 = create_image(client, owner_id, "Image 2", [], owner_token)

    client.post(
        f"/images/{image1['id']}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )

    stats1 = client.get(
        f"/images/{image1['id']}/likes/stats",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    stats2 = client.get(
        f"/images/{image2['id']}/likes/stats",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    assert stats1["total_likes"] == 1
    assert stats1["user_has_liked"] is True
    assert stats2["total_likes"] == 0
    assert stats2["user_has_liked"] is False


def test_likes_are_independent_across_users(client: TestClient) -> None:
    """User1's like doesn't affect user2's like status on same image."""
    user1_id, user1_token = create_user_and_get_token(client, "user1")
    user2_id, user2_token = create_user_and_get_token(client, "user2")
    owner_id, owner_token = create_user_and_get_token(client, "owner")
    image = create_image(client, owner_id, "Test image", [], owner_token)

    client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {user1_token}"},
    )

    stats1 = client.get(
        f"/images/{image['id']}/likes/stats",
        headers={"Authorization": f"Bearer {user1_token}"},
    ).json()

    stats2 = client.get(
        f"/images/{image['id']}/likes/stats",
        headers={"Authorization": f"Bearer {user2_token}"},
    ).json()

    assert stats1["total_likes"] == 1
    assert stats1["user_has_liked"] is True
    assert stats2["total_likes"] == 1
    assert stats2["user_has_liked"] is False


def test_user_can_interact_with_comments_and_likes_on_same_image(client: TestClient) -> None:
    """User can both comment and like the same image."""
    user_id, token = create_user_and_get_token(client, "user1")
    owner_id, owner_token = create_user_and_get_token(client, "owner")
    image = create_image(client, owner_id, "Test image", [], owner_token)

    comment_resp = client.post(
        f"/images/{image['id']}/comments",
        json={"content": "Great photo!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert comment_resp.status_code == 201

    like_resp = client.post(
        f"/images/{image['id']}/likes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert like_resp.status_code == 201

    comments = client.get(f"/images/{image['id']}/comments").json()
    stats = client.get(
        f"/images/{image['id']}/likes/stats",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    assert comments["total"] == 1
    assert stats["total_likes"] == 1
