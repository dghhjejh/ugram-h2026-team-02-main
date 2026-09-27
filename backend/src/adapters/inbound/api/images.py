"""Image API endpoints for photo management."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from src.adapters.inbound.api.dependencies import get_current_user
from src.adapters.inbound.api.sse_manager import sse_manager
from src.adapters.outbound.storage.s3_presigner import S3Presigner
from src.application.config import settings
from src.application.dependencies import (
    NotificationServiceDep,
    SocialServiceDep,
    TimeProviderDep,
    get_image_service,
    get_s3_presigner,
    get_user_service,
)
from src.application.dtos import (
    APIErrorResponse,
    AutoCompleteImageRequest,
    AutoCompleteImageResponse,
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
    FeedItemResponse,
    FeedListRequest,
    FeedListResponse,
    ImageCreateRequest,
    ImageLikeStatsResponse,
    ImageListRequest,
    ImageListResponse,
    ImagePresignRequest,
    ImagePresignResponse,
    ImageResponse,
    LikeResponse,
    MentionedUserResponse,
    MentionTagPosition,
    TrendingKeywordItemResponse,
    TrendingKeywordsGeneratedFromResponse,
    TrendingKeywordsResponse,
    UpdateImageMetadataRequest,
)
from src.domain.images.entities import FeedImageItem, Image, MentionTag, TrendingKeywordSnapshot
from src.domain.images.image_processor import ImageFormat, ImageProcessor
from src.domain.images.services import ImageFeedCursorError, ImageNotFoundError, ImageService
from src.domain.notifications.entities import NotificationType
from src.domain.social.services import CommentNotFoundError, InvalidCommentContentError, ReactionAlreadyExistsError
from src.domain.users.entities import User
from src.domain.users.services import UserService

router = APIRouter(prefix="/images", tags=["images"])
logger = logging.getLogger(__name__)

ImageServiceDep = Annotated[ImageService, Depends(get_image_service)]
S3PresignerDep = Annotated[S3Presigner, Depends(get_s3_presigner)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def _error_response(description: str, detail_example: str) -> dict[str, object]:
    return {
        "model": APIErrorResponse,
        "description": description,
        "content": {"application/json": {"example": {"detail": detail_example}}},
    }


VALIDATION_ERROR_RESPONSE = {
    422: {
        "description": "Validation error raised when the request body or query parameters do not satisfy schema constraints.",
    }
}


@dataclass(frozen=True)
class _TrendCacheEntry:
    expires_at: datetime
    response: TrendingKeywordsResponse


_TRENDING_CACHE: dict[tuple[int, str], _TrendCacheEntry] = {}
_TRENDING_CACHE_LOCK = Lock()
_IMAGE_PROCESSOR = ImageProcessor(output_format="JPEG", quality=90)


def _invalidate_trending_cache() -> None:
    with _TRENDING_CACHE_LOCK:
        _TRENDING_CACHE.clear()


def _storage_key_from_image_url(image_url: str, bucket: str, region: str) -> str:
    base = f"https://{bucket}.s3.{region}.amazonaws.com/"
    return image_url.replace(base, "", 1) if image_url.startswith(base) else image_url


def _variant_storage_key(storage_key: str, variant: ImageFormat) -> str:
    base_path = Path(storage_key)
    directory = str(base_path.parent).replace("\\", "/")
    stem = base_path.stem
    if directory in {"", "."}:
        return f"{stem}.{variant.value}.jpg"
    return f"{directory}/{stem}.{variant.value}.jpg"


def _presigned_variant_url(storage_key: str, variant: ImageFormat, presigner: S3Presigner) -> str | None:
    variant_key = _variant_storage_key(storage_key, variant)
    try:
        return presigner.presign_get(variant_key)
    except Exception:
        return None


def _variant_bundle_exists(storage_key: str, presigner: S3Presigner) -> bool:
    """Check once whether generated variants exist for this image key."""
    thumbnail_key = _variant_storage_key(storage_key, ImageFormat.THUMBNAIL)
    try:
        return presigner.get_object_info(thumbnail_key) is not None
    except Exception:
        return False


def _build_image_variants_for_storage(request: ImageCreateRequest, presigner: S3Presigner) -> None:
    image_url = request.image_url
    storage_key = _storage_key_from_image_url(image_url, presigner.bucket, presigner.region)
    if storage_key == image_url:
        logger.warning("Skipping image variants generation: image_url is not a storage key (%s)", image_url)
        return

    if not hasattr(presigner, "download_object_bytes") or not hasattr(presigner, "upload_object_bytes"):
        logger.warning("Configured presigner does not support server-side image variant generation")
        return

    try:
        original_bytes = presigner.download_object_bytes(storage_key)
        source_image_input = original_bytes
        if request.crop_aspect_ratio is not None:
            source_image_input = _IMAGE_PROCESSOR.crop_image(
                original_bytes,
                aspect_ratio=request.crop_aspect_ratio,
                zoom=request.crop_zoom,
                center_x_percent=request.crop_center_x_percent,
                center_y_percent=request.crop_center_y_percent,
            )

        processed = _IMAGE_PROCESSOR.process_image(source_image_input)
        for variant, payload in processed.items():
            if variant == ImageFormat.ORIGINAL:
                continue
            presigner.upload_object_bytes(
                storage_key=_variant_storage_key(storage_key, variant),
                content=payload,
                content_type="image/jpeg",
            )
    except ValueError as exc:
        logger.warning("Skipping image variants generation for key %s: %s", storage_key, str(exc))
    except HTTPException as exc:
        logger.warning("Skipping image variants generation for key %s: %s", storage_key, str(exc.detail))
    except Exception as exc:
        logger.warning(
            "Skipping image variants generation for key %s due to unexpected error: %s", storage_key, str(exc)
        )


def _validate_uploaded_image(request: ImageCreateRequest, presigner: S3Presigner) -> None:
    storage_key = _storage_key_from_image_url(request.image_url, presigner.bucket, presigner.region)
    expected_prefix = f"{presigner.upload_prefix}/{request.owner_user_id}/"

    if storage_key == request.image_url or not storage_key.startswith(expected_prefix):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "image_url must reference an uploaded image for the owner",
        )

    try:
        object_info = presigner.get_object_info(storage_key)
    except Exception as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc

    if object_info is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded image not found in storage")

    if object_info.content_type not in settings.ALLOWED_IMAGE_CONTENT_TYPES:
        allowed_types = ", ".join(settings.ALLOWED_IMAGE_CONTENT_TYPES)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported uploaded content type '{object_info.content_type}'. Allowed: {allowed_types}",
        )

    if object_info.content_length > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Upload exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes",
        )


def _to_viewable_profile_photo_url(profile_photo_url: str | None, presigner: S3Presigner) -> str | None:
    if not profile_photo_url:
        return None

    base = f"https://{presigner.bucket}.s3.{presigner.region}.amazonaws.com/"
    if profile_photo_url.startswith(base):
        storage_key = profile_photo_url.replace(base, "", 1)
        try:
            return presigner.presign_get(storage_key)
        except Exception:
            return profile_photo_url

    return profile_photo_url


def _view_url_or_fallback(image_url: str, presigner: S3Presigner) -> str:
    storage_key = _storage_key_from_image_url(image_url, presigner.bucket, presigner.region)
    try:
        return presigner.presign_get(storage_key)
    except Exception:
        return image_url


def _build_mentions_lookup(user_ids: set[UUID], user_service: UserService) -> dict[UUID, User]:
    if not user_ids:
        return {}
    users = user_service.get_users_by_ids(list(user_ids))
    return {user.id: user for user in users}


def _build_tag_positions_map(mention_tags: list[MentionTag]) -> dict[UUID, MentionTagPosition]:
    return {
        tag.user_id: MentionTagPosition(
            user_id=tag.user_id,
            x_percent=tag.x_percent,
            y_percent=tag.y_percent,
        )
        for tag in mention_tags
    }


def _format_mentions(
    mention_ids: list[UUID],
    mention_lookup: dict[UUID, User],
    tag_positions: dict[UUID, MentionTagPosition],
) -> list[MentionedUserResponse]:
    formatted: list[MentionedUserResponse] = []
    for mid in mention_ids:
        user = mention_lookup.get(mid)
        if not user:
            continue
        formatted.append(
            MentionedUserResponse(
                id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                profile_photo_url=user.profile_photo_url,
                tag_position=tag_positions.get(mid),
            )
        )
    return formatted


def _to_response(
    image: Image,
    presigner: S3Presigner,
    mention_lookup: dict[UUID, User] | None = None,
    include_large_variant: bool = True,
) -> ImageResponse:
    storage_key = _storage_key_from_image_url(image.image_url, presigner.bucket, presigner.region)
    variant_bundle_exists = _variant_bundle_exists(storage_key, presigner)
    if include_large_variant:
        if variant_bundle_exists:
            view_url = _presigned_variant_url(storage_key, ImageFormat.LARGE, presigner) or _view_url_or_fallback(
                image.image_url,
                presigner,
            )
        else:
            view_url = _view_url_or_fallback(image.image_url, presigner)
    else:
        view_url = _view_url_or_fallback(image.image_url, presigner)
    thumbnail_view_url = (
        _presigned_variant_url(storage_key, ImageFormat.THUMBNAIL, presigner) if variant_bundle_exists else None
    )
    mention_lookup = mention_lookup or {}
    tag_positions = _build_tag_positions_map(image.mention_tags)
    mention_tags_list = [tag_positions[tag.user_id] for tag in image.mention_tags if tag.user_id in tag_positions]
    return ImageResponse(
        id=image.id,
        owner_user_id=image.owner_user_id,
        description=image.description,
        hashtags=image.hashtags,
        mentions_user_ids=image.mentions_user_ids,
        mentions=_format_mentions(image.mentions_user_ids, mention_lookup, tag_positions),
        mention_tags=mention_tags_list,
        image_url=image.image_url,
        thumbnail_view_url=thumbnail_view_url,
        view_url=view_url,
        created_at=image.created_at,
        updated_at=image.updated_at,
    )


def _to_feed_item_response(
    item: FeedImageItem,
    presigner: S3Presigner,
    mention_lookup: dict[UUID, User],
) -> FeedItemResponse:
    storage_key = _storage_key_from_image_url(item.image.image_url, presigner.bucket, presigner.region)
    variant_bundle_exists = _variant_bundle_exists(storage_key, presigner)
    if variant_bundle_exists:
        view_url = _presigned_variant_url(storage_key, ImageFormat.LARGE, presigner) or _view_url_or_fallback(
            item.image.image_url,
            presigner,
        )
        feed_view_url = _presigned_variant_url(storage_key, ImageFormat.MEDIUM, presigner) or view_url
    else:
        view_url = _view_url_or_fallback(item.image.image_url, presigner)
        feed_view_url = view_url
    tag_positions = _build_tag_positions_map(item.image.mention_tags)
    mention_tags_list = [tag_positions[tag.user_id] for tag in item.image.mention_tags if tag.user_id in tag_positions]
    return FeedItemResponse(
        id=item.image.id,
        owner_user_id=item.image.owner_user_id,
        owner_username=item.owner_username,
        owner_profile_photo_url=_to_viewable_profile_photo_url(item.owner_profile_photo_url, presigner),
        description=item.image.description,
        hashtags=item.image.hashtags,
        mentions_user_ids=item.image.mentions_user_ids,
        mentions=_format_mentions(item.image.mentions_user_ids, mention_lookup, tag_positions),
        mention_tags=mention_tags_list,
        image_url=item.image.image_url,
        feed_view_url=feed_view_url,
        view_url=view_url,
        like_count=item.like_count,
        comment_count=item.comment_count,
        created_at=item.image.created_at,
        updated_at=item.image.updated_at,
    )


def _to_trending_keywords_response(
    snapshot: TrendingKeywordSnapshot,
    *,
    window: str,
) -> TrendingKeywordsResponse:
    return TrendingKeywordsResponse(
        hashtags=[TrendingKeywordItemResponse(keyword=item.keyword, count=item.count) for item in snapshot.hashtags],
        description_keywords=[
            TrendingKeywordItemResponse(keyword=item.keyword, count=item.count)
            for item in snapshot.description_keywords
        ],
        generated_from=TrendingKeywordsGeneratedFromResponse(
            source_fields=["search_events.keyword", "search_events.trend_type", "search_trends_daily.search_count"],
            window=window,
            count_unit="searches",
            aggregation_mode="async_daily_aggregate",
        ),
    )


@router.post(
    "",
    response_model=ImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create image metadata",
    description=(
        "Finalize the upload workflow after a successful `POST /images/presign` request and direct upload to storage. "
        "The `image_url` must reference an existing uploaded object owned by the authenticated user."
    ),
    responses={
        400: _error_response(
            "Business validation error for image metadata or uploaded object verification.",
            "image_url must reference an uploaded image for the owner",
        ),
        403: _error_response(
            "The authenticated user is trying to create an image for another owner.",
            "You can only create images for yourself",
        ),
        413: _error_response(
            "The uploaded object exceeds the configured upload limit.",
            f"Upload exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes",
        ),
        500: _error_response(
            "Storage metadata could not be verified due to an upstream storage error.",
            "Unable to inspect uploaded image in storage",
        ),
        **VALIDATION_ERROR_RESPONSE,
    },
)
def create_image(
    request: ImageCreateRequest,
    service: ImageServiceDep,
    presigner: S3PresignerDep,
    user_service: UserServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ImageResponse:
    """Persist image metadata after upload to storage (s3)."""
    if current_user.id != request.owner_user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only create images for yourself")
    _validate_uploaded_image(request, presigner)
    _build_image_variants_for_storage(request, presigner)
    try:
        image = service.create_image(
            owner_user_id=request.owner_user_id,
            description=request.description,
            image_url=request.image_url,
            hashtags=request.hashtags,
            mentions_user_ids=request.mentions_user_ids,
            mention_tags=[
                MentionTag(
                    user_id=tag.user_id,
                    x_percent=tag.x_percent,
                    y_percent=tag.y_percent,
                )
                for tag in request.mention_tags
            ],
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    mention_lookup = _build_mentions_lookup(set(image.mentions_user_ids), user_service)
    return _to_response(image, presigner, mention_lookup)


@router.get(
    "/feed",
    response_model=FeedListResponse,
    summary="List global image feed",
    description="Return images from all users ordered by creation date using keyset pagination.",
    responses={
        400: _error_response("The supplied feed cursor is invalid or expired.", "Invalid feed cursor"),
        **VALIDATION_ERROR_RESPONSE,
    },
)
def list_feed(
    _: Annotated[User, Depends(get_current_user)],
    service: ImageServiceDep,
    presigner: S3PresignerDep,
    user_service: UserServiceDep,
    params: Annotated[FeedListRequest, Depends()],
) -> FeedListResponse:
    """List images from all users ordered by creation date using keyset pagination."""
    try:
        page = service.list_feed(limit=params.limit, cursor=params.cursor)
    except ImageFeedCursorError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    mention_ids = {uid for item in page.items for uid in item.image.mentions_user_ids}
    mention_lookup = _build_mentions_lookup(mention_ids, user_service)

    return FeedListResponse(
        items=[_to_feed_item_response(item, presigner, mention_lookup) for item in page.items],
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get(
    "/trending-keywords",
    response_model=TrendingKeywordsResponse,
    summary="List most searched hashtags and description keywords",
    description="Return aggregated keyword trends derived from recorded hashtag and description searches.",
    responses=VALIDATION_ERROR_RESPONSE,
)
def list_trending_keywords(
    service: ImageServiceDep,
    time_provider: TimeProviderDep,
    _: Annotated[User, Depends(get_current_user)],
    limit: int = Query(10, ge=1, le=50, description="Max items to return per keyword list"),
    window: Literal["all_time", "today"] = Query("all_time", description="Time window for the trends calculation"),
) -> TrendingKeywordsResponse:
    """List keyword trends derived from aggregated search activity."""
    cache_key = (limit, window)
    now = time_provider.now()
    started_at = perf_counter()

    if settings.TRENDING_CACHE_TTL_SECONDS > 0:
        with _TRENDING_CACHE_LOCK:
            cached_entry = _TRENDING_CACHE.get(cache_key)
            if cached_entry and cached_entry.expires_at > now:
                elapsed_ms = (perf_counter() - started_at) * 1000
                logger.info(
                    "trending_keywords window=%s limit=%s cache_hit=true elapsed_ms=%.2f",
                    window,
                    limit,
                    elapsed_ms,
                )
                return cached_entry.response.model_copy(deep=True)

    snapshot = service.get_trending_keywords(limit=limit, window=window)
    response = _to_trending_keywords_response(
        snapshot,
        window=window,
    )

    has_trends = bool(response.hashtags or response.description_keywords)

    if settings.TRENDING_CACHE_TTL_SECONDS > 0 and has_trends:
        with _TRENDING_CACHE_LOCK:
            _TRENDING_CACHE[cache_key] = _TrendCacheEntry(
                expires_at=now + timedelta(seconds=settings.TRENDING_CACHE_TTL_SECONDS),
                response=response.model_copy(deep=True),
            )
    elif settings.TRENDING_CACHE_TTL_SECONDS > 0:
        with _TRENDING_CACHE_LOCK:
            _TRENDING_CACHE.pop(cache_key, None)

    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "trending_keywords window=%s limit=%s cache_hit=false elapsed_ms=%.2f",
        window,
        limit,
        elapsed_ms,
    )
    return response


@router.get(
    "/autocomplete",
    response_model=AutoCompleteImageResponse,
    summary="Auto-complete image descriptions and hashtags",
    description="Suggest matching caption fragments or hashtags based on previously stored image metadata.",
    responses=VALIDATION_ERROR_RESPONSE,
)
def autocomplete_image_metadata(
    image_service: ImageServiceDep,
    req: Annotated[AutoCompleteImageRequest, Depends()],
    _: Annotated[User, Depends(get_current_user)],
) -> AutoCompleteImageResponse:
    """Provide auto-complete suggestions for image descriptions and hashtags."""
    if req.search_type == "description":
        suggestions = image_service.get_autocomplete_descriptions(req.partial)
    else:
        suggestions = image_service.get_autocomplete_hashtags(req.partial)
    return AutoCompleteImageResponse(suggestions=suggestions)


@router.get(
    "/{image_id}",
    response_model=ImageResponse,
    summary="Get image by ID",
    description="Retrieve one image with mention metadata and a signed `view_url` for display.",
    responses={
        404: _error_response("No image exists for the supplied identifier.", "Image not found"),
        **VALIDATION_ERROR_RESPONSE,
    },
)
def get_image(
    image_id: UUID,
    service: ImageServiceDep,
    presigner: S3PresignerDep,
    user_service: UserServiceDep,
    _: Annotated[User, Depends(get_current_user)],
) -> ImageResponse:
    """Retrieve a single image metadata record."""
    try:
        image = service.get_image(image_id)
    except ImageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    mention_lookup = _build_mentions_lookup(set(image.mentions_user_ids), user_service)
    return _to_response(image, presigner, mention_lookup)


@router.get(
    "/user/{user_id}",
    response_model=ImageListResponse,
    summary="List images for a user",
    description="Return a paginated slice of images owned by the specified user.",
    responses=VALIDATION_ERROR_RESPONSE,
)
def list_user_images(
    user_id: UUID,
    service: ImageServiceDep,
    presigner: S3PresignerDep,
    user_service: UserServiceDep,
    params: Annotated[ImageListRequest, Depends()],
    _: Annotated[User, Depends(get_current_user)],
) -> ImageListResponse:
    """Paginated list of images for the given user."""
    images = service.list_user_images(owner_user_id=user_id, limit=params.limit, offset=params.offset)

    mention_ids = {uid for img in images for uid in img.mentions_user_ids}
    mention_lookup = _build_mentions_lookup(mention_ids, user_service)

    return ImageListResponse(
        images=[_to_response(img, presigner, mention_lookup, include_large_variant=False) for img in images],
        total=len(images),
        limit=params.limit,
        offset=params.offset,
    )


@router.post(
    "/presign",
    response_model=ImagePresignResponse,
    summary="Get presigned URL for direct S3 upload",
    description=(
        "Start the upload flow by generating a short-lived presigned URL. Upload the binary file with the returned "
        "`upload_url`, then call `POST /images` with the returned `image_url` to persist metadata."
    ),
    responses={
        400: _error_response(
            "The requested file type is not allowed for uploads.",
            "Unsupported content type 'application/pdf'. Allowed: image/jpeg, image/png",
        ),
        403: _error_response(
            "The authenticated user is trying to upload an image for another owner.",
            "You can only upload images for yourself",
        ),
        413: _error_response(
            "The declared file size exceeds the configured upload limit.",
            f"Upload exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes",
        ),
        500: _error_response(
            "The storage presigner could not generate an upload URL.",
            "Unable to generate a presigned upload URL",
        ),
        **VALIDATION_ERROR_RESPONSE,
    },
)
def presign_image_upload(
    request: ImagePresignRequest,
    presigner: S3PresignerDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ImagePresignResponse:
    """Provide a presigned URL for the client to upload directly to S3."""
    if current_user.id != request.owner_user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only upload images for yourself")
    if request.content_type not in settings.ALLOWED_IMAGE_CONTENT_TYPES:
        allowed_types = ", ".join(settings.ALLOWED_IMAGE_CONTENT_TYPES)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported content type '{request.content_type}'. Allowed: {allowed_types}",
        )
    if request.content_length > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Upload exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes",
        )
    try:
        result = presigner.presign_put(
            owner_user_id=request.owner_user_id,
            filename=request.filename,
            content_type=request.content_type,
        )
    except Exception as exc:  # broad to surface AWS credential/config issues
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc

    return ImagePresignResponse(
        upload_url=result.upload_url,
        storage_key=result.storage_key,
        image_url=result.image_url,
        expires_in=result.expires_in,
    )


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete image by ID",
    description="Delete an existing image and its backing storage object. Only the image owner can perform this action.",
    responses={
        403: _error_response(
            "The authenticated user does not own the target image.", "You can only delete your own images"
        ),
        404: _error_response("No image exists for the supplied identifier.", "Image not found"),
        **VALIDATION_ERROR_RESPONSE,
    },
)
def delete_image(
    image_id: UUID,
    service: ImageServiceDep,
    presigner: S3PresignerDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete an image by its ID."""
    try:
        image = service.get_image(image_id)
        if current_user.id != image.owner_user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only delete your own images")
        storage_key = _storage_key_from_image_url(image.image_url, presigner.bucket, presigner.region)
        presigner.presign_delete(storage_key)
        service.delete_image(image_id)
    except ImageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get(
    "/hashtags/{hashtag}",
    response_model=ImageListResponse,
    summary="List images by hashtag",
    description="Return every image whose normalized hashtag list contains the supplied hashtag.",
    responses=VALIDATION_ERROR_RESPONSE,
)
def list_images_by_hashtag(
    hashtag: str,
    service: ImageServiceDep,
    presigner: S3PresignerDep,
    _: Annotated[User, Depends(get_current_user)],
) -> ImageListResponse:
    """List all images containing the given hashtag."""
    normalized_hashtag = hashtag.strip().lower()
    images = service.get_all_images_by_hashtag(normalized_hashtag)
    service.record_search(normalized_hashtag, "hashtag")
    _invalidate_trending_cache()
    return ImageListResponse(
        images=[_to_response(img, presigner) for img in images],
        total=len(images),
        limit=len(images),
        offset=0,
    )


@router.get(
    "/description/{keyword}",
    response_model=ImageListResponse,
    summary="List images by description keyword",
    description="Return every image whose description contains the supplied keyword fragment.",
    responses=VALIDATION_ERROR_RESPONSE,
)
def list_images_by_description_keyword(
    keyword: str,
    service: ImageServiceDep,
    presigner: S3PresignerDep,
    _: Annotated[User, Depends(get_current_user)],
) -> ImageListResponse:
    """List all images whose description contains the given keyword."""
    normalized_keyword = keyword.strip()
    images = service.get_all_images_by_description_keyword(normalized_keyword)
    service.record_search(normalized_keyword, "description")
    _invalidate_trending_cache()
    return ImageListResponse(
        images=[_to_response(img, presigner) for img in images],
        total=len(images),
        limit=len(images),
        offset=0,
    )


@router.patch(
    "/{image_id}",
    response_model=ImageResponse,
    summary="Update image metadata",
    description="Partially update the caption, hashtags, or mentions of an image owned by the authenticated user.",
    responses={
        403: _error_response(
            "The authenticated user does not own the target image.", "You can only update your own images"
        ),
        404: _error_response("No image exists for the supplied identifier.", "Image not found"),
        **VALIDATION_ERROR_RESPONSE,
    },
)
def update_image_metadata(
    image_id: UUID,
    req: UpdateImageMetadataRequest,
    image_service: ImageServiceDep,
    presigner: S3PresignerDep,
    user_service: UserServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ImageResponse:
    """Update metadata for an existing image."""
    try:
        image = image_service.get_image(image_id)
        if current_user.id != image.owner_user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only update your own images")
        image = image_service.update_image_metadata(
            image_id=image_id,
            description=req.description,
            hashtags=req.hashtags,
            mentions_user_ids=req.mentions_user_ids,
            mention_tags=(
                [
                    MentionTag(
                        user_id=tag.user_id,
                        x_percent=tag.x_percent,
                        y_percent=tag.y_percent,
                    )
                    for tag in req.mention_tags
                ]
                if req.mention_tags is not None
                else None
            ),
        )
        mention_lookup = _build_mentions_lookup(set(image.mentions_user_ids), user_service)
        return _to_response(image, presigner, mention_lookup)
    except ImageNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Image not found")


@router.post(
    "/{image_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a comment on an image",
    description="An authenticated user can comment on any image.",
)
def create_comment(
    image_id: UUID,
    request: CreateCommentRequest,
    service: ImageServiceDep,
    social_service: SocialServiceDep,
    notification_service: NotificationServiceDep,
    user_service: UserServiceDep,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CommentResponse:
    try:
        image = service.get_image(image_id)
    except ImageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    try:
        comment = social_service.post_comment(
            user_id=current_user.id,
            image_id=image_id,
            content=request.content,
        )
    except InvalidCommentContentError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    if image.owner_user_id != current_user.id:
        notification = notification_service.create_notification(
            recipient_user_id=image.owner_user_id,
            actor_user_id=current_user.id,
            image_id=image_id,
            notification_type=NotificationType.COMMENT,
        )
        background_tasks.add_task(
            sse_manager.push,
            image.owner_user_id,
            {
                "id": str(notification.id),
                "actor_user_id": str(notification.actor_user_id),
                "image_id": str(notification.image_id),
                "notification_type": notification.notification_type,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
                "actor": {
                    "id": str(current_user.id),
                    "username": current_user.username,
                    "first_name": current_user.first_name,
                    "last_name": current_user.last_name,
                    "profile_photo_url": current_user.profile_photo_url,
                    "registration_date": current_user.registration_date.isoformat(),
                },
            },
        )

    try:
        author = user_service.get_user(comment.user_id)
    except Exception:
        author = None

    return CommentResponse(
        id=comment.id,
        user_id=comment.user_id,
        image_id=comment.target_id,
        content=comment.content,
        created_at=comment.created_at,
        author=author,
    )


@router.get(
    "/{image_id}/comments",
    response_model=CommentListResponse,
    summary="List comments on an image",
    description="Retrieve paginated comments for an image, ordered by most recent first.",
)
def list_image_comments(
    image_id: UUID,
    service: ImageServiceDep,
    social_service: SocialServiceDep,
    user_service: UserServiceDep,
    limit: int = Query(20, ge=1, le=100),
) -> CommentListResponse:
    """List paginated comments for an image."""
    try:
        service.get_image(image_id)
    except ImageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    comments = social_service.get_image_comments(image_id, limit=limit)
    total = social_service.get_image_comment_count(image_id)

    user_ids = [c.user_id for c in comments]
    user_lookup = {}
    if user_ids:
        try:
            users = user_service.get_users_by_ids(user_ids)
            user_lookup = {u.id: u for u in users}
        except Exception:
            pass

    comment_responses = [
        CommentResponse(
            id=c.id,
            user_id=c.user_id,
            image_id=c.target_id,
            content=c.content,
            created_at=c.created_at,
            author=user_lookup.get(c.user_id),
        )
        for c in comments
    ]

    return CommentListResponse(
        comments=comment_responses,
        total=total,
        limit=limit,
    )


@router.delete(
    "/{image_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment on an image",
    description="Delete a comment authored by the authenticated user.",
)
def delete_comment(
    image_id: UUID,
    comment_id: UUID,
    service: ImageServiceDep,
    social_service: SocialServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a comment authored by the current user."""
    try:
        service.get_image(image_id)
    except ImageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    try:
        comment = social_service.get_comment(comment_id)
    except CommentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    if comment.target_id != image_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")

    if comment.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only delete your own comments")

    try:
        social_service.delete_comment(comment_id)
    except CommentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post(
    "/{image_id}/likes",
    response_model=LikeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Like an image",
    description="An authenticated user can like an image. Only one like per user per image.",
)
def like_image(
    image_id: UUID,
    service: ImageServiceDep,
    social_service: SocialServiceDep,
    notification_service: NotificationServiceDep,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
) -> LikeResponse:
    try:
        image = service.get_image(image_id)
    except ImageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    try:
        like = social_service.add_like(
            user_id=current_user.id,
            image_id=image_id,
        )
    except ReactionAlreadyExistsError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e

    if image.owner_user_id != current_user.id:
        notification = notification_service.create_notification(
            recipient_user_id=image.owner_user_id,
            actor_user_id=current_user.id,
            image_id=image_id,
            notification_type=NotificationType.LIKE,
        )
        background_tasks.add_task(
            sse_manager.push,
            image.owner_user_id,
            {
                "id": str(notification.id),
                "actor_user_id": str(notification.actor_user_id),
                "image_id": str(notification.image_id),
                "notification_type": notification.notification_type,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
                "actor": {
                    "id": str(current_user.id),
                    "username": current_user.username,
                    "first_name": current_user.first_name,
                    "last_name": current_user.last_name,
                    "profile_photo_url": current_user.profile_photo_url,
                    "registration_date": current_user.registration_date.isoformat(),
                },
            },
        )

    return LikeResponse(
        id=like.id,
        user_id=like.user_id,
        image_id=like.target_id,
        created_at=like.created_at,
    )


@router.delete(
    "/{image_id}/likes",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unlike an image",
    description="An authenticated user can unlike (remove their like from) an image.",
)
def unlike_image(
    image_id: UUID,
    service: ImageServiceDep,
    social_service: SocialServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Remove a like from an image."""
    try:
        service.get_image(image_id)
    except ImageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    social_service.remove_like(
        user_id=current_user.id,
        image_id=image_id,
    )


@router.get(
    "/{image_id}/likes/stats",
    response_model=ImageLikeStatsResponse,
    summary="Get like statistics for an image",
    description="Get total like count and whether the authenticated user has liked the image.",
)
def get_image_like_stats(
    image_id: UUID,
    service: ImageServiceDep,
    social_service: SocialServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ImageLikeStatsResponse:
    """Get like statistics for an image."""
    try:
        service.get_image(image_id)
    except ImageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    total_likes = social_service.get_image_like_count(image_id)
    user_has_liked = social_service.user_has_liked(current_user.id, image_id)

    return ImageLikeStatsResponse(
        total_likes=total_likes,
        user_has_liked=user_has_liked,
    )
