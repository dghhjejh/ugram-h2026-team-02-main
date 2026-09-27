import asyncio
import json
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sse_starlette.sse import EventSourceResponse

from src.adapters.inbound.api.dependencies import UserServiceDep, get_current_user
from src.adapters.inbound.api.sse_manager import sse_manager
from src.application.config import settings
from src.application.dependencies import NotificationServiceDep
from src.application.dtos import NotificationListResponse, NotificationResponse
from src.domain.notifications.services import NotificationNotFoundError
from src.domain.users.entities import User
from src.domain.users.services import UserService

router = APIRouter(prefix="/notifications", tags=["notifications"])

_KEEP_ALIVE_INTERVAL_SECONDS = 15


def _build_notification_response(notification, user_service: UserService) -> NotificationResponse:
    try:
        actor = user_service.get_user(notification.actor_user_id)
    except Exception:
        actor = None
    return NotificationResponse(
        id=notification.id,
        actor_user_id=notification.actor_user_id,
        image_id=notification.image_id,
        notification_type=notification.notification_type,
        is_read=notification.is_read,
        created_at=notification.created_at,
        actor=actor,
    )


def _decode_user_id_from_token(token: str) -> UUID:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    raw_user_id = payload.get("sub")
    if raw_user_id is None:
        raise ValueError("Missing sub claim")
    return UUID(str(raw_user_id))


@router.get(
    "/",
    response_model=NotificationListResponse,
    summary="List notifications for the authenticated user",
)
def list_notifications(
    notification_service: NotificationServiceDep,
    user_service: UserServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=100),
) -> NotificationListResponse:
    notifications = notification_service.get_user_notifications(current_user.id, limit=limit)
    unread_count = notification_service.count_unread(current_user.id)
    notification_responses = [_build_notification_response(n, user_service) for n in notifications]
    return NotificationListResponse(
        notifications=notification_responses,
        unread_count=unread_count,
        total=len(notification_responses),
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
def mark_notification_read(
    notification_id: UUID,
    notification_service: NotificationServiceDep,
    user_service: UserServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationResponse:
    try:
        notification = notification_service.mark_as_read(notification_id, current_user.id)
    except NotificationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found") from exc
    return _build_notification_response(notification, user_service)


@router.get("/stream", summary="SSE stream of new notifications")
async def notification_stream(token: str = Query(...)) -> EventSourceResponse:
    try:
        user_id = _decode_user_id_from_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    async def event_generator():
        queue = sse_manager.register(user_id)
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=_KEEP_ALIVE_INTERVAL_SECONDS)
                    yield {"event": "notification", "data": json.dumps(data)}
                except TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            sse_manager.unregister(user_id, queue)

    return EventSourceResponse(event_generator())
