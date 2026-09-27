"""Test suite for image comments functionality - E2E style like test_images_api.py."""

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


def test_create_comment_success(client: TestClient) -> None:
    """201: Authenticated user can comment on an image."""
    user1_id, user1_token = create_user_and_get_token(client, "user1")
    user2_id, user2_token = create_user_and_get_token(client, "user2")
    image = create_image(client, user2_id, "Test image", [], user2_token)

    response = client.post(
        f"/images/{image['id']}/comments",
        json={"content": "Great photo!"},
        headers={"Authorization": f"Bearer {user1_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Great photo!"
    assert data["user_id"] == user1_id
    assert data["image_id"] == image["id"]
    assert data["author"] is not None


def test_create_comment_empty_content_fails(client: TestClient) -> None:
    """422: Empty comment content is rejected by Pydantic validation."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    response = client.post(
        f"/images/{image['id']}/comments",
        json={"content": ""},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_create_comment_whitespace_only_fails(client: TestClient) -> None:
    """400: Whitespace-only comment content is rejected by service validation."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    response = client.post(
        f"/images/{image['id']}/comments",
        json={"content": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


def test_create_comment_unauthenticated_fails(client: TestClient) -> None:
    """401: Unauthenticated request is rejected."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    response = client.post(
        f"/images/{image['id']}/comments",
        json={"content": "Great photo!"},
    )

    assert response.status_code == 401


def test_create_comment_image_not_found(client: TestClient) -> None:
    """404: Commenting on non-existent image fails."""
    user_id, token = create_user_and_get_token(client, "user1")
    fake_image_id = str(uuid4())

    response = client.post(
        f"/images/{fake_image_id}/comments",
        json={"content": "Great photo!"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_list_comments_success(client: TestClient) -> None:
    """200: List comments for an image with pagination."""
    user1_id, user1_token = create_user_and_get_token(client, "user1")
    user2_id, user2_token = create_user_and_get_token(client, "user2")
    image = create_image(client, user1_id, "Test image", [], user1_token)

    client.post(
        f"/images/{image['id']}/comments",
        json={"content": "First comment!"},
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    client.post(
        f"/images/{image['id']}/comments",
        json={"content": "Second comment!"},
        headers={"Authorization": f"Bearer {user1_token}"},
    )

    response = client.get(f"/images/{image['id']}/comments")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["comments"]) == 2
    assert data["comments"][0]["content"] == "Second comment!"
    assert data["comments"][1]["content"] == "First comment!"


def test_list_comments_pagination(client: TestClient) -> None:
    """200: Pagination works correctly."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    for i in range(5):
        client.post(
            f"/images/{image['id']}/comments",
            json={"content": f"Comment {i}"},
            headers={"Authorization": f"Bearer {token}"},
        )

    response = client.get(f"/images/{image['id']}/comments?limit=2")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["comments"]) == 2
    assert data["limit"] == 2


def test_list_comments_empty(client: TestClient) -> None:
    """200: Empty list when image has no comments."""
    user_id, token = create_user_and_get_token(client, "user1")
    image = create_image(client, user_id, "Test image", [], token)

    response = client.get(f"/images/{image['id']}/comments")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["comments"]) == 0


def test_list_comments_image_not_found(client: TestClient) -> None:
    """404: Non-existent image returns 404."""
    fake_image_id = str(uuid4())
    response = client.get(f"/images/{fake_image_id}/comments")

    assert response.status_code == 404


def test_list_comments_includes_author_info(client: TestClient) -> None:
    """200: Comments include author information."""
    user1_id, user1_token = create_user_and_get_token(client, "commenter")
    user2_id, user2_token = create_user_and_get_token(client, "owner")
    image = create_image(client, user2_id, "Test image", [], user2_token)

    client.post(
        f"/images/{image['id']}/comments",
        json={"content": "Nice photo!"},
        headers={"Authorization": f"Bearer {user1_token}"},
    )

    response = client.get(f"/images/{image['id']}/comments")

    assert response.status_code == 200
    data = response.json()
    assert len(data["comments"]) == 1
    comment = data["comments"][0]
    assert comment["author"] is not None
    assert comment["author"]["id"] == user1_id
    assert comment["author"]["first_name"] == "Test"
    assert comment["author"]["last_name"] == "User"


def test_user_can_comment_on_own_and_others_images(client: TestClient) -> None:
    """User can comment on their own and other users' images."""
    user1_id, user1_token = create_user_and_get_token(client, "user1")
    user2_id, user2_token = create_user_and_get_token(client, "user2")
    image1 = create_image(client, user1_id, "User1's image", [], user1_token)
    image2 = create_image(client, user2_id, "User2's image", [], user2_token)

    resp1 = client.post(
        f"/images/{image1['id']}/comments",
        json={"content": "My own photo!"},
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        f"/images/{image2['id']}/comments",
        json={"content": "Your photo is nice!"},
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert resp2.status_code == 201

    list_resp1 = client.get(f"/images/{image1['id']}/comments")
    assert list_resp1.status_code == 200
    assert list_resp1.json()["total"] == 1

    list_resp2 = client.get(f"/images/{image2['id']}/comments")
    assert list_resp2.status_code == 200
    assert list_resp2.json()["total"] == 1


def test_delete_comment_success(client: TestClient) -> None:
    """204: Comment author can delete their comment."""
    owner_id, owner_token = create_user_and_get_token(client, "owner")
    commenter_id, commenter_token = create_user_and_get_token(client, "commenter")
    image = create_image(client, owner_id, "Owner image", [], owner_token)

    create_resp = client.post(
        f"/images/{image['id']}/comments",
        json={"content": "delete me"},
        headers={"Authorization": f"Bearer {commenter_token}"},
    )
    assert create_resp.status_code == 201
    comment_id = create_resp.json()["id"]
    assert create_resp.json()["user_id"] == commenter_id

    delete_resp = client.delete(
        f"/images/{image['id']}/comments/{comment_id}",
        headers={"Authorization": f"Bearer {commenter_token}"},
    )
    assert delete_resp.status_code == 204

    list_resp = client.get(f"/images/{image['id']}/comments")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 0


def test_delete_comment_forbidden_for_non_author(client: TestClient) -> None:
    """403: Users cannot delete comments authored by others."""
    owner_id, owner_token = create_user_and_get_token(client, "owner")
    author_id, author_token = create_user_and_get_token(client, "author")
    other_id, other_token = create_user_and_get_token(client, "other")
    image = create_image(client, owner_id, "Owner image", [], owner_token)

    create_resp = client.post(
        f"/images/{image['id']}/comments",
        json={"content": "keep me"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    comment_id = create_resp.json()["id"]
    assert create_resp.json()["user_id"] == author_id

    delete_resp = client.delete(
        f"/images/{image['id']}/comments/{comment_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert delete_resp.status_code == 403
    assert other_id != author_id

    list_resp = client.get(f"/images/{image['id']}/comments")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1


def test_delete_comment_requires_authentication(client: TestClient) -> None:
    """401: Unauthenticated requests cannot delete comments."""
    owner_id, owner_token = create_user_and_get_token(client, "owner")
    image = create_image(client, owner_id, "Owner image", [], owner_token)

    create_resp = client.post(
        f"/images/{image['id']}/comments",
        json={"content": "protected"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    comment_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/images/{image['id']}/comments/{comment_id}")
    assert delete_resp.status_code == 401


def test_delete_comment_not_found(client: TestClient) -> None:
    """404: Deleting a missing comment returns not found."""
    owner_id, owner_token = create_user_and_get_token(client, "owner")
    image = create_image(client, owner_id, "Owner image", [], owner_token)

    delete_resp = client.delete(
        f"/images/{image['id']}/comments/{uuid4()}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert delete_resp.status_code == 404


def test_delete_comment_with_wrong_image_path_returns_not_found(client: TestClient) -> None:
    """404: Comment cannot be deleted through an unrelated image path."""
    owner_id, owner_token = create_user_and_get_token(client, "owner")
    image_1 = create_image(client, owner_id, "Image one", [], owner_token)
    image_2 = create_image(client, owner_id, "Image two", [], owner_token)

    create_resp = client.post(
        f"/images/{image_1['id']}/comments",
        json={"content": "bound to image one"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    comment_id = create_resp.json()["id"]

    delete_resp = client.delete(
        f"/images/{image_2['id']}/comments/{comment_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert delete_resp.status_code == 404
