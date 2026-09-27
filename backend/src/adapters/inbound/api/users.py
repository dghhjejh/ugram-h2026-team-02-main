"""User API endpoints for profile management."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from src.adapters.inbound.api.dependencies import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    UserServiceDep,
    delete_refresh_token_cookie,
    get_current_user,
    require_resource_owner,
    set_refresh_token_cookie,
)
from src.adapters.inbound.api.user_to_user_profile_mapper import UserToUserProfileMapper
from src.adapters.outbound.storage.s3_presigner import S3Presigner
from src.application.config import settings
from src.application.dependencies import get_s3_presigner
from src.application.dtos import (
    CreateUserRequest,
    DeleteAccountRequest,
    PrivateUserProfileResponse,
    PublicUserProfileResponse,
    Token,
    UpdateUserProfileRequest,
    UserListResponse,
)
from src.domain.users.entities import User
from src.domain.users.helpers.auth import ALGORITHM, SECRET_KEY, create_access_token, create_refresh_token
from src.domain.users.services import UserAlreadyExistsError, UserNotFoundError

S3PresignerDep = Annotated[S3Presigner, Depends(get_s3_presigner)]

router = APIRouter(prefix="/users", tags=["users"])


@contextmanager
def handle_user_exceptions() -> Generator[None]:
    """Map domain exceptions to appropriate HTTP responses."""
    try:
        yield
    except UserNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except UserAlreadyExistsError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.post(
    "/register",
    response_model=PrivateUserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user. Username and email must be unique.",
)
def create_user(request: CreateUserRequest, service: UserServiceDep) -> PrivateUserProfileResponse:
    """Create user with the provided profile data."""
    with handle_user_exceptions():
        user = service.create_user(
            username=request.username,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            phone_number=request.phone_number,
            profile_photo_url=request.profile_photo_url,
            password=request.user_password,
        )
        return UserToUserProfileMapper.to_private_user_profile_response(user)


@router.post(
    "/token",
    response_model=Token,
    summary="Login and get access token",
    description="Authenticate user with username and password, returns JWT access token",
)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: UserServiceDep,
    response: Response,
) -> Token:
    """Authenticate user and return JWT token. Refresh token is set as an HttpOnly cookie."""
    with handle_user_exceptions():
        is_authenticated = service.authenticate(form_data.username, form_data.password)
        if not is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = service.get_user_by_username(form_data.username)

        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        set_refresh_token_cookie(response, refresh_token)
        return Token(access_token=access_token, token_type="bearer")  # nosec B106


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Reads the refresh token from the HttpOnly cookie and issues a new access token.",
)
def refresh_access_token(
    request: Request,
    response: Response,
    service: UserServiceDep,
) -> Token:
    """Validate the refresh token cookie and rotate both tokens."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication is not configured"
        )

    refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        raise credentials_exception

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        if payload.get("type") != "refresh":
            raise credentials_exception
        raw_user_id = payload.get("sub")
        if raw_user_id is None:
            raise credentials_exception
        user_id = UUID(str(raw_user_id))
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_exception  # noqa: B904

    with handle_user_exceptions():
        user = service.get_user(user_id)

    new_access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    set_refresh_token_cookie(response, new_refresh_token)
    return Token(access_token=new_access_token, token_type="bearer")  # nosec B106


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout and clear refresh token cookie",
    description="Clears the HttpOnly refresh token cookie, invalidating future token refresh.",
)
def logout(response: Response) -> None:
    """Delete the refresh token cookie server-side."""
    delete_refresh_token_cookie(response)


@router.get(
    "",
    response_model=UserListResponse,
    summary="List all users",
    description="Paginated public user list. Excludes email and phone number. Default limit: 20, max: 100.",
)
def list_users(
    service: UserServiceDep,
    _: Annotated[User, Depends(get_current_user)],
    limit: int = Query(20, ge=1, le=100, description="Max users to return"),
    offset: int = Query(0, ge=0, description="Users to skip"),
    keyword: str | None = Query(None, min_length=1, max_length=50, description="Filter by username substring"),
) -> UserListResponse:
    """Return paginated public profiles without private contact fields."""
    users = service.list_users(limit=limit, offset=offset, keyword=keyword)
    total = service.get_total_user_count() if keyword is None else len(users)
    return UserListResponse(
        users=[UserToUserProfileMapper.to_public_user_profile_response(u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/me",
    response_model=PrivateUserProfileResponse,
    summary="get the current authenticated user profile",
    description="Returns the current authenticated user profile",
)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> PrivateUserProfileResponse:
    return UserToUserProfileMapper.to_private_user_profile_response(current_user)


@router.get(
    "/{user_id}",
    response_model=PublicUserProfileResponse,
    summary="Get user by ID",
    description="Retrieve profile for a specific user.",
)
def get_user(
    user_id: UUID, service: UserServiceDep, _current_user: Annotated[User, Depends(get_current_user)]
) -> PublicUserProfileResponse:
    """Fetch user by ID or raise 404."""
    with handle_user_exceptions():
        return UserToUserProfileMapper.to_public_user_profile_response(service.get_user(user_id))


@router.put(
    "/{user_id}",
    response_model=PrivateUserProfileResponse,
    summary="Update user profile",
    description="Partial update of user profile fields.",
)
def update_user_profile(
    user_id: UUID,
    request: UpdateUserProfileRequest,
    service: UserServiceDep,
    _: Annotated[User, Depends(require_resource_owner)],
) -> PrivateUserProfileResponse:
    """Update user profile with provided fields."""
    with handle_user_exceptions():
        user = service.update_user_profile(
            user_id=user_id,
            username=request.username,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            phone_number=request.phone_number,
            profile_photo_url=request.profile_photo_url,
        )
        return UserToUserProfileMapper.to_private_user_profile_response(user)


@router.get(
    "/{user_id}/profile-photo",
    summary="Get signed profile photo URL",
    description="Get a signed URL for viewing a user's profile photo.",
)
def get_profile_photo_url(
    user_id: UUID,
    service: UserServiceDep,
    presigner: S3PresignerDep,
    _: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Get signed URL for user's profile photo."""
    with handle_user_exceptions():
        user = service.get_user(user_id)
        if not user.profile_photo_url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User has no profile photo")

        # Extract storage key from S3 URL
        base_url = f"https://{presigner.bucket}.s3.{presigner.region}.amazonaws.com/"
        if user.profile_photo_url.startswith(base_url):
            storage_key = user.profile_photo_url.replace(base_url, "", 1)
            try:
                signed_url = presigner.presign_get(storage_key)
                return {"signed_url": signed_url}
            except Exception:
                return {"signed_url": user.profile_photo_url}

        # If not an S3 URL, return as-is (external URL)
        return {"signed_url": user.profile_photo_url}


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user account",
    description="Permanently delete a user account. Requires authentication as the account owner and username confirmation.",
)
def delete_user(
    user_id: UUID,
    request: DeleteAccountRequest,
    service: UserServiceDep,
    _: Annotated[User, Depends(require_resource_owner)],
) -> None:
    """Delete user account after username confirmation."""
    with handle_user_exceptions():
        service.delete_user(user_id, confirmation=request.confirmation)
