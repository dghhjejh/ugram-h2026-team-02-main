from unittest.mock import Mock

from src.adapters.outbound.storage.s3_presigner import S3Presigner


def test_presign_get_reuses_cached_signed_url(monkeypatch) -> None:
    fake_client = Mock()
    fake_client.generate_presigned_url.side_effect = [
        "https://signed.example.com/images/cat.jpg?sig=1",
        "https://signed.example.com/images/cat.jpg?sig=2",
    ]

    monkeypatch.setattr("src.adapters.outbound.storage.s3_presigner.boto3.client", lambda *args, **kwargs: fake_client)

    presigner = S3Presigner(
        bucket="bucket",
        region="us-east-1",
        expires_in=900,
        view_url_cache_ttl_seconds=300,
    )

    first = presigner.presign_get("images/cat.jpg")
    second = presigner.presign_get("images/cat.jpg")

    assert first == second
    assert fake_client.generate_presigned_url.call_count == 1


def test_presign_get_regenerates_when_view_url_cache_disabled(monkeypatch) -> None:
    fake_client = Mock()
    fake_client.generate_presigned_url.side_effect = [
        "https://signed.example.com/images/cat.jpg?sig=1",
        "https://signed.example.com/images/cat.jpg?sig=2",
    ]

    monkeypatch.setattr("src.adapters.outbound.storage.s3_presigner.boto3.client", lambda *args, **kwargs: fake_client)

    presigner = S3Presigner(
        bucket="bucket",
        region="us-east-1",
        expires_in=900,
        view_url_cache_ttl_seconds=0,
    )

    first = presigner.presign_get("images/cat.jpg")
    second = presigner.presign_get("images/cat.jpg")

    assert first != second
    assert fake_client.generate_presigned_url.call_count == 2


def test_presign_get_evicts_oldest_entry_when_cache_is_full(monkeypatch) -> None:
    fake_client = Mock()
    fake_client.generate_presigned_url.side_effect = [
        "https://signed.example.com/images/a.jpg?sig=1",
        "https://signed.example.com/images/b.jpg?sig=1",
        "https://signed.example.com/images/a.jpg?sig=2",
    ]

    monkeypatch.setattr("src.adapters.outbound.storage.s3_presigner.boto3.client", lambda *args, **kwargs: fake_client)

    presigner = S3Presigner(
        bucket="bucket",
        region="us-east-1",
        expires_in=900,
        view_url_cache_ttl_seconds=300,
        view_url_cache_max_entries=1,
    )

    first = presigner.presign_get("images/a.jpg")
    presigner.presign_get("images/b.jpg")
    second = presigner.presign_get("images/a.jpg")

    assert first != second
    assert fake_client.generate_presigned_url.call_count == 3


def test_presign_get_purges_expired_entries_before_reuse(monkeypatch) -> None:
    fake_client = Mock()
    fake_client.generate_presigned_url.side_effect = [
        "https://signed.example.com/images/cat.jpg?sig=1",
        "https://signed.example.com/images/cat.jpg?sig=2",
    ]
    now = {"value": 100.0}

    monkeypatch.setattr("src.adapters.outbound.storage.s3_presigner.boto3.client", lambda *args, **kwargs: fake_client)
    monkeypatch.setattr("src.adapters.outbound.storage.s3_presigner.time", lambda: now["value"])

    presigner = S3Presigner(
        bucket="bucket",
        region="us-east-1",
        expires_in=900,
        view_url_cache_ttl_seconds=10,
        view_url_cache_max_entries=10,
    )

    first = presigner.presign_get("images/cat.jpg")
    now["value"] = 111.0
    second = presigner.presign_get("images/cat.jpg")

    assert first != second
    assert fake_client.generate_presigned_url.call_count == 2


def test_get_object_info_reuses_cached_head_object(monkeypatch) -> None:
    fake_client = Mock()
    fake_client.head_object.return_value = {
        "ContentLength": 123,
        "ContentType": "image/jpeg",
    }

    monkeypatch.setattr("src.adapters.outbound.storage.s3_presigner.boto3.client", lambda *args, **kwargs: fake_client)

    presigner = S3Presigner(
        bucket="bucket",
        region="us-east-1",
        object_info_cache_ttl_seconds=120,
        object_info_cache_max_entries=100,
    )

    first = presigner.get_object_info("images/cat.jpg")
    second = presigner.get_object_info("images/cat.jpg")

    assert first is not None
    assert second is not None
    assert first.content_length == 123
    assert second.content_length == 123
    assert fake_client.head_object.call_count == 1


def test_get_object_info_cache_is_invalidated_on_upload_and_delete(monkeypatch) -> None:
    fake_client = Mock()
    fake_client.head_object.return_value = {
        "ContentLength": 123,
        "ContentType": "image/jpeg",
    }

    monkeypatch.setattr("src.adapters.outbound.storage.s3_presigner.boto3.client", lambda *args, **kwargs: fake_client)

    presigner = S3Presigner(
        bucket="bucket",
        region="us-east-1",
        object_info_cache_ttl_seconds=120,
        object_info_cache_max_entries=100,
    )

    presigner.get_object_info("images/cat.jpg")
    presigner.get_object_info("images/cat.jpg")
    assert fake_client.head_object.call_count == 1

    presigner.upload_object_bytes("images/cat.jpg", b"abc", "image/jpeg")
    presigner.get_object_info("images/cat.jpg")
    assert fake_client.head_object.call_count == 2

    presigner.presign_delete("images/cat.jpg")
    presigner.get_object_info("images/cat.jpg")
    assert fake_client.head_object.call_count == 3
