"""API dependencies for authentication and authorization."""

from typing import Annotated
from uuid import UUID

import jwt
import sentry_sdk
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer

from src.application.config import settings
from src.application.dependencies import get_user_service
from src.application.dtos import TokenData
from src.domain.users.entities import User
from src.domain.users.services import UserNotFoundError, UserService

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def _refresh_cookie_samesite() -> str:
    # Cloud frontend/backend run on different origins, so the refresh cookie
    # must be cross-site in deployed environments.
    return "none" if settings.use_secure_cookies else "lax"


def set_refresh_token_cookie(response: Response, token: str) -> None:
    """Attach the refresh token as an HttpOnly cookie."""
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.use_secure_cookies,
        samesite=_refresh_cookie_samesite(),
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )


def delete_refresh_token_cookie(response: Response) -> None:
    """Clear the refresh token cookie (used on logout)."""
    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        httponly=True,
        secure=settings.use_secure_cookies,
        samesite=_refresh_cookie_samesite(),
        path="/",
    )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token", auto_error=False)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def _bind_user_to_sentry_scope(user: User) -> None:
    sentry_sdk.set_user(
        {
            "id": str(user.id),
            "username": user.username,
        }
    )


def _extract_token(_: Request, bearer_token: str | None) -> str | None:
    """Return token only from Authorization header (no cookie fallback to avoid CSRF)."""
    return bearer_token


def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    service: UserServiceDep,
) -> User:
    """Validate JWT token (Bearer header or httpOnly cookie) and return current user."""
    if not SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication is not configured"
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    jwt_token = _extract_token(request, token)
    if not jwt_token:
        raise credentials_exception
    try:
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        raw_user_id = payload.get("sub")
        if raw_user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=UUID(str(raw_user_id)))
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_exception  # noqa: B904

    if token_data.user_id is None:
        raise credentials_exception

    try:
        user = service.get_user(token_data.user_id)
    except UserNotFoundError:
        raise credentials_exception  # noqa: B904

    _bind_user_to_sentry_scope(user)
    return user


def require_resource_owner(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Verify that the current user is the owner of the resource.

    Raises HTTP 403 if user_id doesn't match current_user.id.
    Use this for routes where users can only modify their own resources.
    """
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own resources",
        )
    return current_user
