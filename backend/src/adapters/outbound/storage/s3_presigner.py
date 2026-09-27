from __future__ import annotations

import os
from collections import OrderedDict
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import time
from typing import Any, cast
from uuid import UUID, uuid4

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]


@dataclass
class PresignResult:
    upload_url: str
    storage_key: str
    image_url: str
    expires_in: int


@dataclass
class StoredObjectInfo:
    content_length: int
    content_type: str | None


@dataclass
class _CachedViewUrl:
    url: str
    expires_at: float


@dataclass
class _CachedObjectInfo:
    value: StoredObjectInfo | None
    expires_at: float


class S3Presigner:
    """Generate presigned URLs for direct-to-S3 uploads."""

    def __init__(
        self,
        bucket: str,
        region: str,
        upload_prefix: str = "images",
        expires_in: int = 900,
        view_url_cache_ttl_seconds: int = 300,
        view_url_cache_max_entries: int = 1000,
        object_info_cache_ttl_seconds: int = 120,
        object_info_cache_max_entries: int = 5000,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        aws_profile: str | None = None,
        aws_sdk_load_config: bool = False,
    ) -> None:
        self.bucket = bucket
        self.region = region
        self.upload_prefix = upload_prefix.strip("/")
        self.expires_in = expires_in
        self.view_url_cache_ttl_seconds = max(0, view_url_cache_ttl_seconds)
        self.view_url_cache_max_entries = max(0, view_url_cache_max_entries)
        self.object_info_cache_ttl_seconds = max(0, object_info_cache_ttl_seconds)
        self.object_info_cache_max_entries = max(0, object_info_cache_max_entries)
        self._view_url_cache: OrderedDict[tuple[str, int], _CachedViewUrl] = OrderedDict()
        self._view_url_cache_lock = Lock()
        self._object_info_cache: OrderedDict[str, _CachedObjectInfo] = OrderedDict()
        self._object_info_cache_lock = Lock()
        self._client: Any | None = None
        self._client_lock = Lock()
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_session_token = aws_session_token
        self._aws_profile = aws_profile
        if aws_sdk_load_config:
            os.environ.setdefault("AWS_SDK_LOAD_CONFIG", "1")

    @property
    def client(self) -> Any:
        if self._client is not None:
            return self._client

        with self._client_lock:
            if self._client is not None:
                return self._client

            if self._aws_profile:
                session = boto3.Session(profile_name=self._aws_profile, region_name=self.region)
                self._client = session.client("s3")
            elif self._aws_access_key_id and self._aws_secret_access_key:
                self._client = boto3.client(
                    "s3",
                    region_name=self.region,
                    aws_access_key_id=self._aws_access_key_id,
                    aws_secret_access_key=self._aws_secret_access_key,
                    aws_session_token=self._aws_session_token,
                )
            else:
                # Fall back to default credential chain (env vars/IMDS/Shared config)
                self._client = boto3.client("s3", region_name=self.region)

            return self._client

    def presign_put(
        self,
        owner_user_id: UUID,
        filename: str,
        content_type: str,
    ) -> PresignResult:
        key = self._build_key(owner_user_id, filename)
        upload_url = cast(
            str,
            self.client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=self.expires_in,
            ),
        )
        image_url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
        return PresignResult(
            upload_url=upload_url,
            storage_key=key,
            image_url=image_url,
            expires_in=self.expires_in,
        )

    def presign_get(self, storage_key: str, expires_in: int | None = None) -> str:
        """Generate a short-lived signed URL for viewing a private object."""
        ttl = expires_in or self.expires_in
        cache_ttl = min(self.view_url_cache_ttl_seconds, max(ttl - 5, 0))
        cache_key = (storage_key, ttl)

        if cache_ttl > 0 and self.view_url_cache_max_entries > 0:
            now = time()
            with self._view_url_cache_lock:
                self._purge_expired_locked(now)
                cached = self._view_url_cache.get(cache_key)
                if cached and cached.expires_at > now:
                    self._view_url_cache.move_to_end(cache_key)
                    return cached.url
                if cached:
                    self._view_url_cache.pop(cache_key, None)

        signed_url = cast(
            str,
            self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": storage_key,
                },
                ExpiresIn=ttl,
            ),
        )
        if cache_ttl > 0 and self.view_url_cache_max_entries > 0:
            now = time()
            with self._view_url_cache_lock:
                self._purge_expired_locked(now)
                self._view_url_cache[cache_key] = _CachedViewUrl(
                    url=signed_url,
                    expires_at=now + cache_ttl,
                )
                self._view_url_cache.move_to_end(cache_key)
                self._evict_extra_entries_locked()
        return signed_url

    def presign_delete(self, storage_key: str) -> None:
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=storage_key,
            )
            with self._view_url_cache_lock:
                stale_keys = [key for key in self._view_url_cache if key[0] == storage_key]
                for cache_key in stale_keys:
                    self._view_url_cache.pop(cache_key, None)
            with self._object_info_cache_lock:
                self._object_info_cache.pop(storage_key, None)
        except Exception as exc:
            raise Exception(f"Failed to delete object from S3: {str(exc)}") from exc

    def get_object_info(self, storage_key: str) -> StoredObjectInfo | None:
        if self.object_info_cache_ttl_seconds > 0 and self.object_info_cache_max_entries > 0:
            now = time()
            with self._object_info_cache_lock:
                self._purge_object_info_expired_locked(now)
                cached = self._object_info_cache.get(storage_key)
                if cached and cached.expires_at > now:
                    self._object_info_cache.move_to_end(storage_key)
                    return cached.value
                if cached:
                    self._object_info_cache.pop(storage_key, None)

        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=storage_key,
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                if self.object_info_cache_ttl_seconds > 0 and self.object_info_cache_max_entries > 0:
                    now = time()
                    with self._object_info_cache_lock:
                        self._purge_object_info_expired_locked(now)
                        self._object_info_cache[storage_key] = _CachedObjectInfo(
                            value=None,
                            expires_at=now + self.object_info_cache_ttl_seconds,
                        )
                        self._object_info_cache.move_to_end(storage_key)
                        self._evict_object_info_extra_entries_locked()
                return None
            raise Exception(f"Failed to inspect object in S3: {str(exc)}") from exc

        object_info = StoredObjectInfo(
            content_length=int(response["ContentLength"]),
            content_type=response.get("ContentType"),
        )
        if self.object_info_cache_ttl_seconds > 0 and self.object_info_cache_max_entries > 0:
            now = time()
            with self._object_info_cache_lock:
                self._purge_object_info_expired_locked(now)
                self._object_info_cache[storage_key] = _CachedObjectInfo(
                    value=object_info,
                    expires_at=now + self.object_info_cache_ttl_seconds,
                )
                self._object_info_cache.move_to_end(storage_key)
                self._evict_object_info_extra_entries_locked()

        return object_info

    def download_object_bytes(self, storage_key: str) -> bytes:
        """Download an object payload from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=storage_key)
            body = response.get("Body")
            if body is None:
                raise Exception("S3 get_object response did not include a Body stream")
            with closing(body):
                return bytes(body.read())
        except ClientError as exc:
            raise Exception(f"Failed to download object from S3: {str(exc)}") from exc

    def upload_object_bytes(self, storage_key: str, content: bytes, content_type: str) -> None:
        """Upload an object payload to S3."""
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=storage_key,
                Body=content,
                ContentType=content_type,
            )
            with self._view_url_cache_lock:
                stale_keys = [key for key in self._view_url_cache if key[0] == storage_key]
                for cache_key in stale_keys:
                    self._view_url_cache.pop(cache_key, None)
            with self._object_info_cache_lock:
                self._object_info_cache.pop(storage_key, None)
        except ClientError as exc:
            raise Exception(f"Failed to upload object to S3: {str(exc)}") from exc

    def _purge_expired_locked(self, now: float) -> None:
        expired_keys = [key for key, cached in self._view_url_cache.items() if cached.expires_at <= now]
        for key in expired_keys:
            self._view_url_cache.pop(key, None)

    def _evict_extra_entries_locked(self) -> None:
        while len(self._view_url_cache) > self.view_url_cache_max_entries:
            self._view_url_cache.popitem(last=False)

    def _purge_object_info_expired_locked(self, now: float) -> None:
        expired_keys = [key for key, cached in self._object_info_cache.items() if cached.expires_at <= now]
        for key in expired_keys:
            self._object_info_cache.pop(key, None)

    def _evict_object_info_extra_entries_locked(self) -> None:
        while len(self._object_info_cache) > self.object_info_cache_max_entries:
            self._object_info_cache.popitem(last=False)

    def _build_key(self, owner_user_id: UUID, filename: str) -> str:
        ext = Path(filename).suffix
        suffix = ext if ext else ""
        return f"{self.upload_prefix}/{owner_user_id}/{uuid4()}{suffix}"
