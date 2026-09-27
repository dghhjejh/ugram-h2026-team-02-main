from collections.abc import Generator
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from src.adapters.outbound.persistence.database import get_db
from src.adapters.outbound.storage.s3_presigner import S3Presigner
from src.application.config import settings
from src.application.dependencies import get_s3_presigner
from src.main import app

from tests.conftest import override_get_db


@pytest.fixture
def moto_s3() -> Generator[dict[str, Any]]:
    region = "us-east-2"
    bucket = "test-images-bucket"

    with mock_aws():
        client = boto3.client("s3", region_name=region)
        client.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
        yield {"client": client, "bucket": bucket, "region": region}


@pytest.fixture
def client_with_s3(moto_s3: dict[str, Any]) -> Generator[TestClient]:
    """FastAPI test client wired to the mocked S3 presigner."""
    presigner = S3Presigner(
        bucket=moto_s3["bucket"],
        region=moto_s3["region"],
        upload_prefix="images",
        expires_in=600,
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_s3_presigner] = lambda: presigner

    with patch("src.main.create_tables"), TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


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

    with patch("src.main.create_tables"), TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class BrokenPresigner:
    bucket = "test-bucket"
    region = "us-east-1"
    upload_prefix = "images"

    def presign_get(self, storage_key: str, expires_in: int | None = None) -> str:  # noqa: ARG002
        raise RuntimeError("presign unavailable")

    def get_object_info(self, storage_key: str) -> SimpleNamespace | None:  # noqa: ARG002
        return SimpleNamespace(content_length=1024, content_type="image/jpeg")


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
    assert resp.status_code == 201, f"Failed to create user: {resp.json()}"
    user_id = resp.json()["id"]
    token_resp = client.post(
        "/users/token",
        data={"username": unique_username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 200
    return user_id, token_resp.json()["access_token"]


def create_image(
    client: TestClient, owner_user_id: str, description: str, hashtags: list[str], token: str
) -> dict[str, Any]:
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
    assert resp.status_code == 201, f"Failed to create image: {resp.json()}"
    return resp.json()


def test_image_response_uses_variant_fields_when_available(client: TestClient) -> None:
    owner_id, token = create_user_and_get_token(client, "variantfields")

    created = create_image(client, owner_id, "variant description", ["variant"], token)
    assert ".large.jpg" in created["view_url"]
    assert created["thumbnail_view_url"] is not None
    assert ".thumbnail.jpg" in created["thumbnail_view_url"]

    fetched = client.get(
        f"/images/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200
    body = fetched.json()
    assert ".large.jpg" in body["view_url"]
    assert body["thumbnail_view_url"] is not None
    assert ".thumbnail.jpg" in body["thumbnail_view_url"]


def test_presign_and_store_image_metadata(client_with_s3: TestClient, moto_s3: dict[str, Any]) -> None:
    owner_id, token = create_user_and_get_token(client_with_s3, "presignuser")
    auth_headers = {"Authorization": f"Bearer {token}"}

    presign_resp = client_with_s3.post(
        "/images/presign",
        json={
            "owner_user_id": owner_id,
            "filename": "cat.png",
            "content_type": "image/png",
            "content_length": 1024,
        },
        headers=auth_headers,
    )
    assert presign_resp.status_code == 200
    presign_data = presign_resp.json()
    storage_key = presign_data["storage_key"]
    assert storage_key.startswith("images/")
    assert presign_data["image_url"].endswith("cat.png") is False  # key uses UUID, not original name

    moto_s3["client"].put_object(
        Bucket=moto_s3["bucket"],
        Key=storage_key,
        Body=b"img-bytes",
        ContentType="image/png",
    )

    create_resp = client_with_s3.post(
        "/images",
        json={
            "owner_user_id": owner_id,
            "description": "A sleepy cat",
            "image_url": presign_data["image_url"],
            "hashtags": ["Cats", "Sleepy"],
            "mentions_user_ids": [],
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    image_id = create_resp.json()["id"]

    fetch_resp = client_with_s3.get(f"/images/{image_id}", headers=auth_headers)
    assert fetch_resp.status_code == 200
    fetched = fetch_resp.json()
    assert fetched["image_url"] == presign_data["image_url"]
    assert "X-Amz-Signature" in fetched["view_url"]
    assert fetched["view_url"].startswith("https://")

    obj = moto_s3["client"].get_object(Bucket=moto_s3["bucket"], Key=storage_key)
    assert obj["ContentLength"] == len(b"img-bytes")


def test_store_image_metadata_rejects_actual_upload_larger_than_limit(
    client_with_s3: TestClient,
    moto_s3: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 4)

    owner_id, token = create_user_and_get_token(client_with_s3, "oversizeuser")
    auth_headers = {"Authorization": f"Bearer {token}"}

    presign_resp = client_with_s3.post(
        "/images/presign",
        json={
            "owner_user_id": owner_id,
            "filename": "cat.png",
            "content_type": "image/png",
            "content_length": 1,
        },
        headers=auth_headers,
    )
    assert presign_resp.status_code == 200
    presign_data = presign_resp.json()

    moto_s3["client"].put_object(
        Bucket=moto_s3["bucket"],
        Key=presign_data["storage_key"],
        Body=b"img-bytes",
        ContentType="image/png",
    )

    create_resp = client_with_s3.post(
        "/images",
        json={
            "owner_user_id": owner_id,
            "description": "Too large",
            "image_url": presign_data["image_url"],
            "hashtags": [],
            "mentions_user_ids": [],
        },
        headers=auth_headers,
    )

    assert create_resp.status_code == 413
    assert create_resp.json()["detail"] == "Upload exceeds the maximum allowed size of 4 bytes"


def test_no_images_for_hashtag(client: TestClient) -> None:
    _, token = create_user_and_get_token(client, "hashtaguser0")
    resp = client.get("/images/hashtags/doesnotexist", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["images"] == []
    assert data["total"] == 0


def test_images_returned_for_hashtag(client: TestClient) -> None:
    user_id, token = create_user_and_get_token(client, "hashtaguser2")
    img1 = create_image(client, user_id, "desc1", ["cat", "dog"], token)
    img2 = create_image(client, user_id, "desc2", ["cat"], token)
    img3 = create_image(client, user_id, "desc3", ["dog"], token)

    resp = client.get("/images/hashtags/cat", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    returned_ids = {img["id"] for img in data["images"]}
    assert img1["id"] in returned_ids
    assert img2["id"] in returned_ids
    assert img3["id"] not in returned_ids
    assert data["total"] == 2


def test_multiple_hashtags(client: TestClient) -> None:
    user_id, token = create_user_and_get_token(client, "hashtaguser4")
    img = create_image(client, user_id, "desc", ["a", "b", "c"], token)

    for tag in ["a", "b", "c"]:
        resp = client.get(f"/images/hashtags/{tag}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert img["id"] in {i["id"] for i in data["images"]}


def test_no_images_for_description_keyword(client: TestClient) -> None:
    _, token = create_user_and_get_token(client, "descuser0")
    resp = client.get("/images/description/doesnotexist", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["images"] == []
    assert data["total"] == 0


def test_images_returned_for_description_keyword(client: TestClient) -> None:
    user_id, token = create_user_and_get_token(client, "descuser1")
    img1 = create_image(client, user_id, "A photo of a cat sleeping", [], token)
    img2 = create_image(client, user_id, "A photo of a dog running", [], token)
    img3 = create_image(client, user_id, "cat and dog together", [], token)

    resp = client.get("/images/description/cat", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    returned_ids = {img["id"] for img in data["images"]}
    assert img1["id"] in returned_ids
    assert img3["id"] in returned_ids
    assert img2["id"] not in returned_ids
    assert data["total"] == 2


def test_description_search_case_insensitive(client: TestClient) -> None:
    user_id, token = create_user_and_get_token(client, "descuser2")
    img = create_image(client, user_id, "Beautiful Sunset over the ocean", [], token)

    for keyword in ["sunset", "SUNSET", "Sunset", "SuNsEt"]:
        resp = client.get(f"/images/description/{keyword}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert img["id"] in {i["id"] for i in data["images"]}, f"Expected match for keyword '{keyword}'"


def test_description_search_partial_match(client: TestClient) -> None:
    user_id, token = create_user_and_get_token(client, "descuser3")
    img = create_image(client, user_id, "hiking in the mountains", [], token)

    resp = client.get("/images/description/mount", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert img["id"] in {i["id"] for i in data["images"]}


def test_description_search_excludes_non_matching(client: TestClient) -> None:
    user_id, token = create_user_and_get_token(client, "descuser4")
    img_match = create_image(client, user_id, "a rainy day in paris", [], token)
    img_no_match = create_image(client, user_id, "sunny beach vacation", [], token)

    resp = client.get("/images/description/paris", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    returned_ids = {img["id"] for img in data["images"]}
    assert img_match["id"] in returned_ids
    assert img_no_match["id"] not in returned_ids


def test_update_image_returns_mentions_with_usernames(client: TestClient) -> None:
    owner_id, owner_token = create_user_and_get_token(client, "patchowner")
    mentioned_id, _ = create_user_and_get_token(client, "emma")
    mentioned_user = client.get(f"/users/{mentioned_id}", headers={"Authorization": f"Bearer {owner_token}"}).json()

    create_resp = client.post(
        "/images",
        json={
            "owner_user_id": owner_id,
            "description": "original",
            "hashtags": ["friends"],
            "mentions_user_ids": [mentioned_id],
            "mention_tags": [
                {
                    "user_id": mentioned_id,
                    "x_percent": 35,
                    "y_percent": 42,
                }
            ],
            "image_url": f"https://test-bucket.s3.us-east-1.amazonaws.com/images/{owner_id}/{uuid4()}.jpg",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert create_resp.status_code == 201, f"Failed to create image: {create_resp.json()}"
    image_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/images/{image_id}",
        json={"description": "updated"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["description"] == "updated"
    assert body["mentions_user_ids"] == [mentioned_id]
    assert body["mentions"] == [
        {
            "id": mentioned_id,
            "username": mentioned_user["username"],
            "first_name": "Test",
            "last_name": "User",
            "profile_photo_url": None,
            "tag_position": {
                "user_id": mentioned_id,
                "x_percent": 35.0,
                "y_percent": 42.0,
            },
        }
    ]
    assert body["mention_tags"] == [
        {
            "user_id": mentioned_id,
            "x_percent": 35.0,
            "y_percent": 42.0,
        }
    ]


def test_update_image_can_replace_mention_tags(client: TestClient) -> None:
    owner_id, owner_token = create_user_and_get_token(client, "patchtagowner")
    mentioned_id, _ = create_user_and_get_token(client, "patchtagfriend")
    mentioned_user = client.get(f"/users/{mentioned_id}", headers={"Authorization": f"Bearer {owner_token}"}).json()

    create_resp = client.post(
        "/images",
        json={
            "owner_user_id": owner_id,
            "description": "",
            "hashtags": [],
            "mentions_user_ids": [mentioned_id],
            "mention_tags": [
                {
                    "user_id": mentioned_id,
                    "x_percent": 35,
                    "y_percent": 42,
                }
            ],
            "image_url": f"https://test-bucket.s3.us-east-1.amazonaws.com/images/{owner_id}/{uuid4()}.jpg",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert create_resp.status_code == 201, f"Failed to create image: {create_resp.json()}"
    image_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/images/{image_id}",
        json={
            "description": "",
            "mentions_user_ids": [mentioned_id],
            "mention_tags": [
                {
                    "user_id": mentioned_id,
                    "x_percent": 62,
                    "y_percent": 18,
                }
            ],
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["description"] == ""
    assert body["mention_tags"] == [
        {
            "user_id": mentioned_id,
            "x_percent": 62.0,
            "y_percent": 18.0,
        }
    ]
    assert body["mentions"] == [
        {
            "id": mentioned_id,
            "username": mentioned_user["username"],
            "first_name": "Test",
            "last_name": "User",
            "profile_photo_url": None,
            "tag_position": {
                "user_id": mentioned_id,
                "x_percent": 62.0,
                "y_percent": 18.0,
            },
        }
    ]


def test_update_image_falls_back_when_presigning_fails(client: TestClient) -> None:
    app.dependency_overrides[get_s3_presigner] = BrokenPresigner
    owner_id, owner_token = create_user_and_get_token(client, "patchpresignowner")

    create_resp = client.post(
        "/images",
        json={
            "owner_user_id": owner_id,
            "description": "original",
            "hashtags": ["friends"],
            "mentions_user_ids": [],
            "mention_tags": [],
            "image_url": f"https://test-bucket.s3.us-east-1.amazonaws.com/images/{owner_id}/{uuid4()}.jpg",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert create_resp.status_code == 201, f"Failed to create image: {create_resp.json()}"
    image_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/images/{image_id}",
        json={"description": "updated"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["description"] == "updated"
    assert body["view_url"] == body["image_url"]
    assert body["thumbnail_view_url"] is None


class TestImageAuthorization:
    """Tests for 401/403 protection on image write endpoints."""

    def test_create_image_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/images",
            json={
                "owner_user_id": str(uuid4()),
                "description": "test",
                "image_url": "https://example.com/img.jpg",
                "hashtags": [],
                "mentions_user_ids": [],
            },
        )
        assert resp.status_code == 401

    def test_create_image_forbidden_for_other_owner(self, client: TestClient) -> None:
        _, token = create_user_and_get_token(client, "authimg1")
        other_id, _ = create_user_and_get_token(client, "authimg2")
        resp = client.post(
            "/images",
            json={
                "owner_user_id": other_id,
                "description": "test",
                "image_url": "https://example.com/img.jpg",
                "hashtags": [],
                "mentions_user_ids": [],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_presign_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/images/presign",
            json={
                "owner_user_id": str(uuid4()),
                "filename": "photo.jpg",
                "content_type": "image/jpeg",
                "content_length": 1024,
            },
        )
        assert resp.status_code == 401

    def test_presign_forbidden_for_other_owner(self, client: TestClient) -> None:
        _, token = create_user_and_get_token(client, "authimg3")
        other_id, _ = create_user_and_get_token(client, "authimg4")
        resp = client.post(
            "/images/presign",
            json={
                "owner_user_id": other_id,
                "filename": "photo.jpg",
                "content_type": "image/jpeg",
                "content_length": 1024,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_delete_image_requires_auth(self, client: TestClient) -> None:
        owner_id, token = create_user_and_get_token(client, "authimg5")
        image = create_image(client, owner_id, "to delete", [], token)
        resp = client.delete(f"/images/{image['id']}")
        assert resp.status_code == 401

    def test_delete_image_forbidden_for_non_owner(self, client: TestClient) -> None:
        owner_id, owner_token = create_user_and_get_token(client, "authimg6")
        _, other_token = create_user_and_get_token(client, "authimg7")
        image = create_image(client, owner_id, "to delete", [], owner_token)
        resp = client.delete(f"/images/{image['id']}", headers={"Authorization": f"Bearer {other_token}"})
        assert resp.status_code == 403

    def test_update_image_requires_auth(self, client: TestClient) -> None:
        owner_id, token = create_user_and_get_token(client, "authimg8")
        image = create_image(client, owner_id, "original", [], token)
        resp = client.patch(
            f"/images/{image['id']}",
            json={"description": "updated", "hashtags": [], "mentions_user_ids": []},
        )
        assert resp.status_code == 401

    def test_update_image_forbidden_for_non_owner(self, client: TestClient) -> None:
        owner_id, owner_token = create_user_and_get_token(client, "authimg9")
        _, other_token = create_user_and_get_token(client, "authimg10")
        image = create_image(client, owner_id, "original", [], owner_token)
        resp = client.patch(
            f"/images/{image['id']}",
            json={"description": "updated", "hashtags": [], "mentions_user_ids": []},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403


class TestAutocompleteDescriptions:
    def test_returns_matching_descriptions(self, client: TestClient) -> None:
        user_id, token = create_user_and_get_token(client, "acDesc1")
        auth = {"Authorization": f"Bearer {token}"}
        create_image(client, user_id, "sunset over the ocean", [], token)
        create_image(client, user_id, "sunrise at the beach", [], token)
        create_image(client, user_id, "mountains in winter", [], token)

        resp = client.get("/images/autocomplete?partial=sun&search_type=description", headers=auth)
        assert resp.status_code == 200
        suggestions = resp.json()["suggestions"]
        assert any("sunset" in s for s in suggestions)
        assert any("sunrise" in s for s in suggestions)
        assert all("mountain" not in s for s in suggestions)

    def test_case_insensitive(self, client: TestClient) -> None:
        user_id, token = create_user_and_get_token(client, "acDesc2")
        auth = {"Authorization": f"Bearer {token}"}
        create_image(client, user_id, "Beautiful Sunset", [], token)

        resp = client.get("/images/autocomplete?partial=sunset&search_type=description", headers=auth)
        assert resp.status_code == 200
        assert len(resp.json()["suggestions"]) == 1

    def test_no_match_returns_empty(self, client: TestClient) -> None:
        user_id, token = create_user_and_get_token(client, "acDesc3")
        auth = {"Authorization": f"Bearer {token}"}
        create_image(client, user_id, "a photo of a cat", [], token)

        resp = client.get("/images/autocomplete?partial=zzznomatch&search_type=description", headers=auth)
        assert resp.status_code == 200
        assert resp.json()["suggestions"] == []

    def test_most_frequent_first(self, client: TestClient) -> None:
        user_id, token = create_user_and_get_token(client, "acDesc4")
        auth = {"Authorization": f"Bearer {token}"}
        create_image(client, user_id, "cat photo", [], token)
        create_image(client, user_id, "cat photo", [], token)
        create_image(client, user_id, "cat photo", [], token)
        create_image(client, user_id, "cat nap", [], token)

        resp = client.get("/images/autocomplete?partial=cat&search_type=description", headers=auth)
        assert resp.status_code == 200
        suggestions = resp.json()["suggestions"]
        assert suggestions[0] == "cat photo"

    def test_limited_to_10_results(self, client: TestClient) -> None:
        user_id, token = create_user_and_get_token(client, "acDesc5")
        auth = {"Authorization": f"Bearer {token}"}
        for i in range(15):
            create_image(client, user_id, f"photo number {i}", [], token)

        resp = client.get("/images/autocomplete?partial=photo&search_type=description", headers=auth)
        assert resp.status_code == 200
        assert len(resp.json()["suggestions"]) <= 10


class TestAutocompleteHashtags:
    def test_returns_matching_hashtags(self, client: TestClient) -> None:
        user_id, token = create_user_and_get_token(client, "acHash1")
        auth = {"Authorization": f"Bearer {token}"}
        create_image(client, user_id, "desc", ["sunset", "summer"], token)
        create_image(client, user_id, "desc", ["sunrise"], token)
        create_image(client, user_id, "desc", ["winter"], token)

        resp = client.get("/images/autocomplete?partial=sun&search_type=hashtag", headers=auth)
        assert resp.status_code == 200
        suggestions = resp.json()["suggestions"]
        assert "sunset" in suggestions
        assert "sunrise" in suggestions
        assert "winter" not in suggestions

    def test_case_insensitive(self, client: TestClient) -> None:
        user_id, token = create_user_and_get_token(client, "acHash2")
        auth = {"Authorization": f"Bearer {token}"}
        create_image(client, user_id, "desc", ["Sunset"], token)

        resp = client.get("/images/autocomplete?partial=sunset&search_type=hashtag", headers=auth)
        assert resp.status_code == 200
        assert len(resp.json()["suggestions"]) == 1

    def test_no_match_returns_empty(self, client: TestClient) -> None:
        user_id, token = create_user_and_get_token(client, "acHash3")
        auth = {"Authorization": f"Bearer {token}"}
        create_image(client, user_id, "desc", ["cat"], token)

        resp = client.get("/images/autocomplete?partial=zzznomatch&search_type=hashtag", headers=auth)
        assert resp.status_code == 200
        assert resp.json()["suggestions"] == []

    def test_most_frequent_first(self, client: TestClient) -> None:
        user_id, token = create_user_and_get_token(client, "acHash4")
        auth = {"Authorization": f"Bearer {token}"}
        create_image(client, user_id, "desc", ["cats", "animals"], token)
        create_image(client, user_id, "desc", ["cats", "animals"], token)
        create_image(client, user_id, "desc", ["cats"], token)
        create_image(client, user_id, "desc", ["animals"], token)

        resp = client.get("/images/autocomplete?partial=an&search_type=hashtag", headers=auth)
        assert resp.status_code == 200
        suggestions = resp.json()["suggestions"]
        assert suggestions[0] == "animals"

    def test_limited_to_10_results(self, client: TestClient) -> None:
        user_id, token = create_user_and_get_token(client, "acHash5")
        auth = {"Authorization": f"Bearer {token}"}
        for i in range(15):
            create_image(client, user_id, "desc", [f"tag{i}"], token)

        resp = client.get("/images/autocomplete?partial=tag&search_type=hashtag", headers=auth)
        assert resp.status_code == 200
        assert len(resp.json()["suggestions"]) <= 10


class TestAutocompleteValidation:
    def test_invalid_search_type_returns_422(self, client: TestClient) -> None:
        _, token = create_user_and_get_token(client, "acVal1")
        auth = {"Authorization": f"Bearer {token}"}
        resp = client.get("/images/autocomplete?partial=sun&search_type=invalid", headers=auth)
        assert resp.status_code == 422

    def test_missing_partial_returns_422(self, client: TestClient) -> None:
        _, token = create_user_and_get_token(client, "acVal2")
        auth = {"Authorization": f"Bearer {token}"}
        resp = client.get("/images/autocomplete?search_type=description", headers=auth)
        assert resp.status_code == 422

    def test_missing_search_type_returns_422(self, client: TestClient) -> None:
        _, token = create_user_and_get_token(client, "acVal3")
        auth = {"Authorization": f"Bearer {token}"}
        resp = client.get("/images/autocomplete?partial=sun", headers=auth)
        assert resp.status_code == 422

    def test_empty_partial_returns_422(self, client: TestClient) -> None:
        _, token = create_user_and_get_token(client, "acVal4")
        auth = {"Authorization": f"Bearer {token}"}
        resp = client.get("/images/autocomplete?partial=&search_type=description", headers=auth)
        assert resp.status_code == 422
