"""API request/response DTOs for HTTP boundary."""

from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.domain.notifications.entities import NotificationType


class PublicUserProfileResponse(BaseModel):
    """Public user profile data safe to share with other authenticated users."""

    id: UUID
    username: str
    first_name: str
    last_name: str
    profile_photo_url: str | None
    registration_date: datetime

    model_config = ConfigDict(
        from_attributes=True,  # Allow creating from ORM models
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "profile_photo_url": "https://example.com/photos/john.jpg",
                "registration_date": "2026-01-14T10:30:00Z",
            }
        },
    )


class PrivateUserProfileResponse(PublicUserProfileResponse):
    """Private user profile data returned only to the profile owner."""

    email: str
    phone_number: str | None


class UpdateUserProfileRequest(BaseModel):
    """Partial update - only provided fields are changed."""

    username: str | None = Field(None, min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    email: EmailStr | None = None
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    phone_number: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    profile_photo_url: str | None = Field(None, max_length=500)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str | None) -> str | None:
        """Validate phone number format."""
        if v and not v.startswith("+"):
            # Optionally auto-format to international format
            pass
        return v

    @field_validator("profile_photo_url")
    @classmethod
    def validate_profile_photo_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("https://"):
            raise ValueError("profile_photo_url must use HTTPS")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "[email protected]",
                "phone_number": "+15551234567",
            }
        }
    )


class CreateUserRequest(BaseModel):
    """Request DTO for creating a new user."""

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    profile_photo_url: str | None = Field(None, max_length=500)
    user_password: str = Field(..., min_length=8, max_length=50)

    @field_validator("profile_photo_url")
    @classmethod
    def validate_profile_photo_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("https://"):
            raise ValueError("profile_photo_url must use HTTPS")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "email": "[email protected]",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+15551234567",
                "user_password": "example-password-123",  # nosec B105 example only
            }
        }
    )


class DeleteAccountRequest(BaseModel):
    """Request DTO for deleting user account with username confirmation."""

    confirmation: str = Field(..., min_length=1, description="Type your username to confirm deletion")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "confirmation": "myusername",
            }
        }
    )


class GoogleRegisterRequest(BaseModel):
    """Request DTO for completing Google OAuth registration with chosen username.

    Includes a short-lived registration token issued by the backend at /auth/google/callback.
    """

    registration_token: str = Field(..., min_length=10)
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "registration_token": "<jwt-from-callback>",
                "username": "johndoe",
            }
        }
    )


class UserListResponse(BaseModel):
    """Response DTO for paginated list of users."""

    users: list[PublicUserProfileResponse]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [],
                "total": 100,
                "limit": 20,
                "offset": 0,
            }
        }
    )


class UserAuthenticationRequest(BaseModel):
    """Request DTO for authenticating a user.

    username and password must be provided.
    """

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    user_password: str = Field(..., min_length=8, max_length=50)
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "johndoe",
                    "user_password": "example-password-123",  # nosec B105 example only
                },
                {"email": "[email protected]", "user_password": "another-pass-456"},  # nosec B105 example only
            ]
        }
    )


class Token(BaseModel):
    """JWT token response.

    The refresh token is NOT returned in the response body; it is delivered
    exclusively via an HttpOnly cookie to keep it out of JS-accessible storage.
    """

    access_token: str
    token_type: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "example-access-token",  # nosec B105 example only
                "token_type": "bearer",
            }
        }
    )


class TokenData(BaseModel):
    """Data extracted from JWT token."""

    user_id: UUID | None = None


class APIErrorResponse(BaseModel):
    """Standard error payload returned by FastAPI HTTP exceptions."""

    detail: str = Field(..., description="Human-readable explanation of the error.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Image not found",
            }
        }
    )


class SocialStatsResponse(BaseModel):
    """Aggregated social counters displayed on a user profile."""

    posts_count: int = Field(..., ge=0, description="Number of images published by the user.")
    followers_count: int = Field(..., ge=0, description="Number of followers. Returns 0 until follower support exists.")
    following_count: int = Field(
        ..., ge=0, description="Number of followed users. Returns 0 until follow support exists."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "posts_count": 12,
                "followers_count": 0,
                "following_count": 0,
            }
        }
    )


class ImageCreateRequest(BaseModel):
    """Request payload for creating an image metadata record after a successful upload."""

    ALLOWED_IMAGE_EXTENSIONS: ClassVar[set[str]] = {"jpg", "jpeg", "png", "webp", "gif"}

    owner_user_id: UUID = Field(..., description="Identifier of the authenticated user who owns the uploaded image.")
    description: str = Field("", max_length=2000, description="Caption displayed with the image.")
    hashtags: list[str] = Field(default_factory=list, description="Normalized hashtags associated with the image.")
    mentions_user_ids: list[UUID] = Field(
        default_factory=list,
        description="Mentioned user IDs that should be linked to this image.",
    )
    image_url: str = Field(
        ...,
        max_length=500,
        description="Permanent object URL returned by the direct upload flow. The file must already exist in storage.",
    )
    mention_tags: list["MentionTagPosition"] = Field(
        default_factory=list,
        description="Optional coordinates used to place mention tags on top of the image.",
    )
    crop_aspect_ratio: float | None = Field(
        None,
        gt=0,
        description="Optional target aspect ratio (width/height) applied server-side before generating formats.",
    )
    crop_zoom: float = Field(
        1.0,
        ge=1.0,
        le=3.0,
        description="Optional zoom factor applied during server-side crop. 1.0 means no additional zoom.",
    )
    crop_center_x_percent: float = Field(
        50.0,
        ge=0,
        le=100,
        description="Horizontal crop center in percent of source image width.",
    )
    crop_center_y_percent: float = Field(
        50.0,
        ge=0,
        le=100,
        description="Vertical crop center in percent of source image height.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "owner_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "description": "Sunset at the beach",
                "hashtags": ["sunset", "vacay"],
                "mentions_user_ids": ["223e4567-e89b-12d3-a456-426614174000"],
                "image_url": "https://bucket.s3.amazonaws.com/images/dev/user/uuid.jpg",
                "crop_aspect_ratio": 1.0,
                "crop_zoom": 1.0,
                "crop_center_x_percent": 50,
                "crop_center_y_percent": 50,
                "mention_tags": [
                    {
                        "user_id": "223e4567-e89b-12d3-a456-426614174000",
                        "x_percent": 42.5,
                        "y_percent": 63.3,
                    }
                ],
            }
        }
    )

    @field_validator("hashtags", mode="before")
    @classmethod
    def normalize_hashtags(cls, v: list[str] | str) -> list[str]:
        raw = v.split(",") if isinstance(v, str) else v or []
        cleaned = [t.strip().lower() for t in raw if isinstance(t, str) and t.strip()]
        return cleaned

    @field_validator("mentions_user_ids")
    @classmethod
    def ensure_unique_mentions(cls, v: list[UUID]) -> list[UUID]:
        seen = set()
        unique: list[UUID] = []
        for uid in v:
            if uid not in seen:
                seen.add(uid)
                unique.append(uid)
        return unique

    @field_validator("image_url")
    @classmethod
    def validate_image_extension(cls, url: str) -> str:
        if "." not in url:
            raise ValueError("image_url must include a file extension")
        ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
        if ext not in cls.ALLOWED_IMAGE_EXTENSIONS:
            allowed = ", ".join(sorted(cls.ALLOWED_IMAGE_EXTENSIONS))
            raise ValueError(f"unsupported image type '{ext}'. Allowed: {allowed}")
        return url


class MentionTagPosition(BaseModel):
    """Coordinates for a mention tag overlay."""

    user_id: UUID = Field(..., description="Identifier of the tagged user.")
    x_percent: float = Field(..., ge=0, le=100, description="Horizontal coordinate of the tag, in percent.")
    y_percent: float = Field(..., ge=0, le=100, description="Vertical coordinate of the tag, in percent.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "223e4567-e89b-12d3-a456-426614174000",
                "x_percent": 42.5,
                "y_percent": 63.3,
            }
        }
    )


class MentionedUserResponse(BaseModel):
    """User brief returned for mentions."""

    id: UUID = Field(..., description="Mentioned user identifier.")
    username: str = Field(..., description="Mentioned user's public username.")
    profile_photo_url: str | None = Field(None, description="Profile photo URL visible to the requesting user.")
    first_name: str | None = Field(None, description="Mentioned user's first name when available.")
    last_name: str | None = Field(None, description="Mentioned user's last name when available.")
    tag_position: MentionTagPosition | None = Field(
        None, description="Rendered coordinates of the mention tag when set."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "223e4567-e89b-12d3-a456-426614174000",
                "username": "janedoe",
                "first_name": "Jane",
                "last_name": "Doe",
                "profile_photo_url": "https://example.com/avatar.jpg",
                "tag_position": {
                    "user_id": "223e4567-e89b-12d3-a456-426614174000",
                    "x_percent": 40,
                    "y_percent": 55,
                },
            }
        }
    )


class ImageResponse(BaseModel):
    """Image metadata returned to clients."""

    id: UUID = Field(..., description="Image identifier.")
    owner_user_id: UUID = Field(..., description="Identifier of the image owner.")
    description: str = Field(..., description="Image caption stored by the API.")
    hashtags: list[str] = Field(default_factory=list, description="Normalized hashtags extracted from the request.")
    mentions_user_ids: list[UUID] = Field(default_factory=list, description="Mentioned user identifiers.")
    mentions: list[MentionedUserResponse] = Field(
        default_factory=list, description="Expanded public details for mentioned users."
    )
    mention_tags: list[MentionTagPosition] = Field(
        default_factory=list,
        description="Coordinates used by the client to render mention pins over the image.",
    )
    image_url: str = Field(..., description="Stable object URL stored in persistence after upload.")
    thumbnail_view_url: str | None = Field(
        None,
        description="Short-lived signed URL for profile-grid thumbnail variant when available.",
    )
    view_url: str = Field(..., description="Short-lived signed URL generated for viewing the image content.")
    created_at: datetime = Field(..., description="Creation timestamp in UTC.")
    updated_at: datetime = Field(..., description="Last update timestamp in UTC.")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "323e4567-e89b-12d3-a456-426614174000",
                "owner_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "description": "Sunset at the beach",
                "hashtags": ["sunset", "vacay"],
                "mentions_user_ids": ["223e4567-e89b-12d3-a456-426614174000"],
                "mentions": [
                    {
                        "id": "223e4567-e89b-12d3-a456-426614174000",
                        "username": "janedoe",
                        "first_name": "Jane",
                        "last_name": "Doe",
                        "profile_photo_url": "https://example.com/avatar.jpg",
                        "tag_position": {
                            "user_id": "223e4567-e89b-12d3-a456-426614174000",
                            "x_percent": 40,
                            "y_percent": 55,
                        },
                    }
                ],
                "mention_tags": [
                    {
                        "user_id": "223e4567-e89b-12d3-a456-426614174000",
                        "x_percent": 40,
                        "y_percent": 55,
                    }
                ],
                "image_url": "https://bucket.s3.amazonaws.com/images/dev/user/uuid.jpg",
                "thumbnail_view_url": "https://bucket.s3.amazonaws.com/images/dev/user/uuid.thumbnail.jpg?X-Amz-Signature=example",
                "view_url": "https://bucket.s3.amazonaws.com/images/dev/user/uuid.jpg?X-Amz-Signature=example",
                "created_at": "2026-01-20T10:30:00Z",
                "updated_at": "2026-01-20T10:30:00Z",
            }
        },
    )


class ImageListResponse(BaseModel):
    """Paginated list of images."""

    images: list[ImageResponse] = Field(
        default_factory=list, description="Image metadata returned for the requested page."
    )
    total: int = Field(..., ge=0, description="Number of images included in this response.")
    limit: int = Field(..., ge=0, description="Requested page size. Can be 0 when a search returns no images.")
    offset: int = Field(..., ge=0, description="Zero-based starting position used for this page.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "images": [],
                "total": 0,
                "limit": 12,
                "offset": 0,
            }
        }
    )


class TrendingKeywordItemResponse(BaseModel):
    """Single keyword entry for the trends response."""

    keyword: str = Field(..., description="Hashtag or description keyword that was searched.")
    count: int = Field(..., ge=1, description="Number of recorded searches for that keyword.")


class TrendingKeywordsGeneratedFromResponse(BaseModel):
    """Metadata describing the trend data source."""

    source_fields: list[str] = Field(default_factory=list, description="Fields used to build the aggregate snapshot.")
    window: str = Field(..., description="Aggregation window used for the response.")
    count_unit: str = Field(..., description="Unit represented by the count field.")
    aggregation_mode: str = Field(..., description="Backend strategy used to aggregate the trends.")


class TrendingKeywordsResponse(BaseModel):
    """Popular hashtags and description keywords derived from search activity."""

    hashtags: list[TrendingKeywordItemResponse] = Field(
        default_factory=list,
        description="Most searched hashtags for the selected time window.",
    )
    description_keywords: list[TrendingKeywordItemResponse] = Field(
        default_factory=list,
        description="Most searched description keywords for the selected time window.",
    )
    generated_from: TrendingKeywordsGeneratedFromResponse = Field(
        ...,
        description="Metadata explaining how the trend snapshot was produced.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hashtags": [{"keyword": "sunset", "count": 18}],
                "description_keywords": [{"keyword": "beach", "count": 11}],
                "generated_from": {
                    "source_fields": [
                        "search_events.keyword",
                        "search_events.trend_type",
                        "search_trends_daily.search_count",
                    ],
                    "window": "all_time",
                    "count_unit": "searches",
                    "aggregation_mode": "async_daily_aggregate",
                },
            }
        }
    )


class ImageListRequest(BaseModel):
    """Query params for listing user images."""

    limit: int = Field(12, ge=1, le=100, description="Maximum number of images to return.")
    offset: int = Field(0, ge=0, description="Number of images to skip before collecting results.")


class FeedListRequest(BaseModel):
    """Query params for global feed listing."""

    limit: int = Field(12, ge=1, le=100, description="Maximum number of feed items to return.")
    cursor: str | None = Field(
        None,
        min_length=1,
        description="Opaque cursor returned by a previous feed response for keyset pagination.",
    )


class FeedItemResponse(BaseModel):
    """Feed item with image metadata and owner info."""

    id: UUID = Field(..., description="Image identifier.")
    owner_user_id: UUID = Field(..., description="Identifier of the image owner.")
    owner_username: str = Field(..., description="Public username of the image owner.")
    owner_profile_photo_url: str | None = Field(
        None,
        description="Signed or external URL of the owner's profile photo when available.",
    )
    description: str = Field(..., description="Image caption shown in the feed.")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags attached to the image.")
    mentions_user_ids: list[UUID] = Field(default_factory=list, description="Mentioned user identifiers.")
    mentions: list[MentionedUserResponse] = Field(default_factory=list, description="Expanded mention metadata.")
    mention_tags: list[MentionTagPosition] = Field(
        default_factory=list, description="Coordinates of rendered mention tags."
    )
    image_url: str = Field(..., description="Stable object URL stored in persistence.")
    feed_view_url: str | None = Field(
        None,
        description="Short-lived signed URL for feed-optimized image variant when available.",
    )
    view_url: str = Field(..., description="Short-lived signed URL used to display the image.")
    like_count: int = Field(..., ge=0, description="Total number of likes for the image.")
    comment_count: int = Field(..., ge=0, description="Total number of comments for the image.")
    created_at: datetime = Field(..., description="Creation timestamp in UTC.")
    updated_at: datetime = Field(..., description="Last update timestamp in UTC.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "323e4567-e89b-12d3-a456-426614174000",
                "owner_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "owner_username": "johndoe",
                "owner_profile_photo_url": "https://example.com/profile-photo.jpg",
                "description": "Sunset at the beach",
                "hashtags": ["sunset", "vacay"],
                "mentions_user_ids": ["223e4567-e89b-12d3-a456-426614174000"],
                "mentions": [
                    {
                        "id": "223e4567-e89b-12d3-a456-426614174000",
                        "username": "janedoe",
                        "tag_position": {
                            "user_id": "223e4567-e89b-12d3-a456-426614174000",
                            "x_percent": 40,
                            "y_percent": 55,
                        },
                    }
                ],
                "mention_tags": [
                    {
                        "user_id": "223e4567-e89b-12d3-a456-426614174000",
                        "x_percent": 40,
                        "y_percent": 55,
                    }
                ],
                "image_url": "https://bucket.s3.amazonaws.com/images/dev/user/uuid.jpg",
                "feed_view_url": "https://bucket.s3.amazonaws.com/images/dev/user/uuid.small.jpg?X-Amz-Signature=example",
                "view_url": "https://bucket.s3.amazonaws.com/images/dev/user/uuid.jpg?X-Amz-Signature=example",
                "like_count": 12,
                "comment_count": 4,
                "created_at": "2026-01-20T10:30:00Z",
                "updated_at": "2026-01-20T10:30:00Z",
            }
        }
    )


class FeedListResponse(BaseModel):
    """Paginated global feed response."""

    items: list[FeedItemResponse] = Field(default_factory=list, description="Feed items for the requested page.")
    next_cursor: str | None = Field(None, description="Cursor to send on the next request when more items exist.")
    has_more: bool = Field(..., description="Whether another feed page is available.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "next_cursor": None,
                "has_more": False,
            }
        }
    )


class ImagePresignRequest(BaseModel):
    """Request to generate a presigned upload URL."""

    ALLOWED_IMAGE_EXTENSIONS: ClassVar[set[str]] = {"jpg", "jpeg", "png", "webp", "gif"}

    owner_user_id: UUID = Field(..., description="Identifier of the authenticated user who will own the image.")
    filename: str = Field(
        ..., max_length=255, description="Original filename used to derive the object key and extension."
    )
    content_type: str = Field(..., max_length=100, description="MIME type that will be sent to S3 during upload.")
    content_length: int = Field(..., gt=0, description="File size in bytes, validated against the API upload limit.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "owner_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "photo.jpg",
                "content_type": "image/jpeg",
                "content_length": 524288,
            }
        }
    )

    @field_validator("filename")
    @classmethod
    def validate_filename_extension(cls, filename: str) -> str:
        if "." not in filename:
            raise ValueError("filename must include a file extension")
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in cls.ALLOWED_IMAGE_EXTENSIONS:
            allowed = ", ".join(sorted(cls.ALLOWED_IMAGE_EXTENSIONS))
            raise ValueError(f"unsupported file extension '{ext}'. Allowed: {allowed}")
        return filename


class ImagePresignResponse(BaseModel):
    """Presigned URL payload for direct-to-S3 upload."""

    upload_url: str = Field(..., description="Single-use presigned URL to upload the binary file directly to storage.")
    storage_key: str = Field(..., description="Internal object key generated for the uploaded file.")
    image_url: str = Field(..., description="Persistent object URL to send back to POST /images after upload succeeds.")
    expires_in: int = Field(..., ge=1, description="Lifetime of the presigned URL in seconds.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "upload_url": "https://bucket.s3.amazonaws.com/images/dev/user/uuid.jpg?X-Amz-Signature=example",
                "storage_key": "images/dev/123e4567-e89b-12d3-a456-426614174000/uuid.jpg",
                "image_url": "https://bucket.s3.amazonaws.com/images/dev/123e4567-e89b-12d3-a456-426614174000/uuid.jpg",
                "expires_in": 900,
            }
        }
    )


class UpdateImageMetadataRequest(BaseModel):
    """Request DTO for partially updating image metadata."""

    description: str | None = Field(None, max_length=2000, description="New caption for the image.")
    hashtags: list[str] | None = Field(
        None, description="Replacement list of hashtags. Omit to keep the current value."
    )
    mentions_user_ids: list[UUID] | None = Field(
        None,
        description="Replacement list of mentioned user IDs. Omit to keep the current value.",
    )
    mention_tags: list["MentionTagPosition"] | None = Field(
        None,
        description="Replacement list of positioned mention tags. Omit to keep the current value.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Sunset at the beach after the storm",
                "hashtags": ["sunset", "storm", "vacay"],
                "mentions_user_ids": ["223e4567-e89b-12d3-a456-426614174000"],
                "mention_tags": [
                    {
                        "user_id": "223e4567-e89b-12d3-a456-426614174000",
                        "x_percent": 42.5,
                        "y_percent": 63.3,
                    }
                ],
            }
        }
    )


class AutoCompleteImageRequest(BaseModel):
    """Request DTO for image description and hashtag auto-completion."""

    partial: str = Field(..., min_length=2, max_length=2000, description="Partial text to auto-complete.")
    search_type: Literal["description", "hashtag"] = Field(
        ...,
        description="Target field to search. Use 'description' for captions and 'hashtag' for hashtag suggestions.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "partial": "sun",
                "search_type": "hashtag",
            }
        }
    )


class AutoCompleteImageResponse(BaseModel):
    """Response DTO for auto-complete suggestions."""

    suggestions: list[str] = Field(
        default_factory=list, description="Suggested completions ordered by backend relevance."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "suggestions": ["sunset", "sunrise"],
            }
        }
    )


class CreateCommentRequest(BaseModel):
    """Request DTO for creating a comment on an image."""

    content: str = Field(..., min_length=1, max_length=1000, description="Comment text")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Great photo! Love the composition.",
            }
        }
    )


class CommentResponse(BaseModel):
    """Response DTO for a single comment."""

    id: UUID
    user_id: UUID
    image_id: UUID
    content: str
    created_at: datetime
    author: "PublicUserProfileResponse | None" = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "image_id": "550e8400-e29b-41d4-a716-446655440002",
                "content": "Great photo!",
                "created_at": "2026-04-07T10:30:00Z",
                "author": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "username": "johndoe",
                    "first_name": "John",
                    "last_name": "Doe",
                    "profile_photo_url": None,
                    "registration_date": "2026-01-14T10:30:00Z",
                },
            }
        },
    )


class CommentListResponse(BaseModel):
    """Response DTO for paginated list of comments."""

    comments: list[CommentResponse]
    total: int
    limit: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "comments": [],
                "total": 5,
                "limit": 20,
            }
        }
    )


class LikeResponse(BaseModel):
    """Response DTO for a like reaction."""

    id: UUID
    user_id: UUID
    image_id: UUID
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "image_id": "550e8400-e29b-41d4-a716-446655440002",
                "created_at": "2026-04-07T10:30:00Z",
            }
        },
    )


class ImageLikeStatsResponse(BaseModel):
    """Response DTO for image like statistics and user's like status."""

    total_likes: int
    user_has_liked: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_likes": 42,
                "user_has_liked": True,
            }
        }
    )


class NotificationResponse(BaseModel):
    id: UUID
    actor_user_id: UUID
    image_id: UUID
    notification_type: NotificationType
    is_read: bool
    created_at: datetime
    actor: "PublicUserProfileResponse | None" = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "actor_user_id": "550e8400-e29b-41d4-a716-446655440001",
                "image_id": "550e8400-e29b-41d4-a716-446655440002",
                "notification_type": "comment",
                "is_read": False,
                "created_at": "2026-04-07T10:30:00Z",
                "actor": None,
            }
        },
    )


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int
    total: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "notifications": [],
                "unread_count": 3,
                "total": 10,
            }
        }
    )
