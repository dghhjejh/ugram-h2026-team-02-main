"""End-to-end test for S3 image presign + metadata flow using a mocked S3 backend."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import boto3  # type: ignore[import-untyped]
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from src.adapters.outbound.persistence.database import get_db
from src.adapters.outbound.storage.s3_presigner import S3Presigner
from src.application.dependencies import get_s3_presigner
from src.main import app

from tests.conftest import override_get_db


@pytest.fixture
def moto_s3() -> Generator[dict[str, Any]]:
    """Provide a mocked S3 client with a pre-created bucket."""
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


def test_presign_and_store_image_metadata(client_with_s3: TestClient, moto_s3: dict[str, Any]) -> None:
    """Full flow: presign -> upload -> save metadata -> fetch with view URL."""
    auth_username = f"authuser_{uuid4().hex[:8]}"
    password = "TestPassword123!"
    register_resp = client_with_s3.post(
        "/users/register",
        json={
            "username": auth_username,
            "email": f"{auth_username}@example.com",
            "first_name": "Auth",
            "last_name": "User",
            "user_password": password,
        },
    )
    owner_id = register_resp.json()["id"]
    token_resp = client_with_s3.post(
        "/users/token",
        data={"username": auth_username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    auth_headers = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}

    # 1) Presign upload
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

    # 2) Simulate client upload using the same mocked S3
    moto_s3["client"].put_object(
        Bucket=moto_s3["bucket"],
        Key=storage_key,
        Body=b"img-bytes",
        ContentType="image/png",
    )

    # 3) Save metadata in DB
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

    # 4) Fetch image and ensure view_url is a signed GET link
    fetch_resp = client_with_s3.get(f"/images/{image_id}", headers=auth_headers)
    assert fetch_resp.status_code == 200
    fetched = fetch_resp.json()
    assert fetched["image_url"] == presign_data["image_url"]
    assert "X-Amz-Signature" in fetched["view_url"]
    assert fetched["view_url"].startswith("https://")

    # 5) Verify object exists in mocked S3
    obj = moto_s3["client"].get_object(Bucket=moto_s3["bucket"], Key=storage_key)
    assert obj["ContentLength"] == len(b"img-bytes")
