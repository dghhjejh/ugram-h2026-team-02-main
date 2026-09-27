"""Social API endpoints for followers, likes, and comments."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from src.adapters.outbound.persistence.database import DBSession
from src.adapters.outbound.persistence.models import ImageORM
from src.application.dtos import APIErrorResponse, SocialStatsResponse

router = APIRouter(prefix="/social", tags=["social"])


def _error_response(description: str, detail_example: str) -> dict[str, object]:
    return {
        "model": APIErrorResponse,
        "description": description,
        "content": {"application/json": {"example": {"detail": detail_example}}},
    }


@router.get(
    "/stats/{user_id}",
    response_model=SocialStatsResponse,
    summary="Get public social counters for a user",
    description=(
        "Return the public counters currently exposed by the social module. `posts_count` is backed by persisted images, "
        "while follow-related counters remain `0` until that capability is implemented."
    ),
)
def get_user_stats(user_id: UUID, db: DBSession) -> SocialStatsResponse:
    """Get social stats for a user.

    posts_count is computed from persisted images. Follower metrics are not yet
    backed by tables, so they are returned as 0 until implemented.
    """
    posts_count = db.scalar(select(func.count()).select_from(ImageORM).where(ImageORM.owner_user_id == user_id)) or 0

    return SocialStatsResponse(
        posts_count=int(posts_count),
        followers_count=0,
        following_count=0,
    )


@router.post(
    "/comment",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Comment on an image (not yet implemented)",
    description=(
        "Placeholder endpoint reserved for Livrable 3 commenting. The route is intentionally exposed in the OpenAPI "
        "schema, but the backend currently returns `501 Not Implemented` until comment persistence is available."
    ),
    responses={
        501: _error_response(
            "Comments are not implemented yet in the backend social module.",
            "Comment posting is not implemented yet",
        )
    },
)
def post_comment() -> None:
    """Post a comment (to be implemented)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Comment posting is not implemented yet")
