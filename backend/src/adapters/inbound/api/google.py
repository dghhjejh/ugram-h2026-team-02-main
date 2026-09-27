"""Google OAuth authentication endpoints."""

import logging
import secrets
import urllib.parse
from datetime import timedelta

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from jwt import PyJWKClient

from ....adapters.inbound.api.dependencies import set_refresh_token_cookie
from ....application.config import settings
from ....application.dependencies import get_user_service
from ....application.dtos import GoogleRegisterRequest
from ....domain.users.helpers.auth import create_access_token, create_refresh_token
from ....domain.users.services import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserService,
)

router = APIRouter(prefix="/auth/google", tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/login")
def google_login() -> RedirectResponse:
    config = _require_google_oauth_config()
    state = secrets.token_urlsafe(32)
    params = urllib.parse.urlencode(
        {
            "client_id": config["client_id"],
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": config["redirect_uri"],
            "state": state,
        }
    )
    response = RedirectResponse(f"{config['auth_url']}?{params}")
    response.set_cookie(
        key=settings.OAUTH_STATE_COOKIE_NAME,
        value=state,
        max_age=settings.OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        secure=settings.use_secure_cookies,
        samesite="lax",
        path="/auth/google/callback",
    )
    return response


def _require_google_oauth_config() -> dict[str, str]:
    required_values = {
        "auth_url": settings.GOOGLE_AUTH_URL,
        "token_url": settings.GOOGLE_TOKEN_URL,
        "certs_url": settings.GOOGLE_CERTS_URL,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "frontend_url": settings.FRONTEND_URL,
    }
    missing = [name for name, value in required_values.items() if not value]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Google OAuth is not configured: missing {', '.join(sorted(missing))}",
        )
    return {key: value for key, value in required_values.items() if value is not None}


def _verify_google_token(id_token: str, certs_url: str, client_id: str) -> dict:
    """Verify Google JWT signature and return payload."""
    try:
        jwks_client = PyJWKClient(certs_url)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)

        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer="https://accounts.google.com",
            leeway=10,
        )
        return payload
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {e}") from e


def _frontend_redirect(path: str, fragment_params: dict[str, str]) -> str:
    frontend_url = (settings.FRONTEND_URL or "").rstrip("/")
    fragment = urllib.parse.urlencode(fragment_params, quote_via=urllib.parse.quote)
    return f"{frontend_url}{path}#{fragment}"


def _redirect_with_oauth_cleanup(url: str) -> RedirectResponse:
    response = RedirectResponse(url=url)
    response.delete_cookie(
        key=settings.OAUTH_STATE_COOKIE_NAME,
        path="/auth/google/callback",
        secure=settings.use_secure_cookies,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/callback")
async def google_callback(
    request: Request,
    code: str,
    state: str | None = None,
    service: UserService = Depends(get_user_service),  # noqa: B008
) -> RedirectResponse:
    config = _require_google_oauth_config()
    cookie_state = request.cookies.get(settings.OAUTH_STATE_COOKIE_NAME)
    if not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_res = await client.post(
            config["token_url"],
            data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": config["redirect_uri"],
            },
        )

    if token_res.status_code != 200:
        logger.warning("Google token exchange failed with status %s", token_res.status_code)
        raise HTTPException(status_code=400, detail="Google token exchange failed")

    token_data = token_res.json()
    id_token = token_data["id_token"]

    payload = _verify_google_token(id_token, config["certs_url"], config["client_id"])
    email = payload["email"]
    google_id = payload["sub"]
    first_name = payload.get("given_name", "")
    last_name = payload.get("family_name", "")

    try:
        user = service.get_user_by_google_id(google_id)

        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=30),
        )
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        redirect = _redirect_with_oauth_cleanup(_frontend_redirect("/auth/callback", {"token": access_token}))
        set_refresh_token_cookie(redirect, refresh_token)
        return redirect

    except UserNotFoundError:
        registration_token = create_access_token(
            {
                "token_use": "google_registration",
                "google_id": google_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            },
            expires_delta=timedelta(minutes=10),
        )
        return _redirect_with_oauth_cleanup(_frontend_redirect("/register", {"token": registration_token}))


@router.post("/register")
async def complete_google_registration(
    data: GoogleRegisterRequest,
    response: Response,
    service: UserService = Depends(get_user_service),  # noqa: B008
) -> dict[str, str]:
    """Complete Google OAuth registration after user chooses username.

    This endpoint is called by the frontend after the user selects their username.
    """
    try:
        if not settings.SECRET_KEY:
            raise HTTPException(status_code=500, detail="Authentication is not configured")
        decoded = jwt.decode(
            data.registration_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False},
        )
        if decoded.get("token_use") != "google_registration":
            raise HTTPException(status_code=400, detail="Invalid registration token")
        google_id = decoded["google_id"]
        email = decoded["email"]
        first_name = decoded.get("first_name", "")
        last_name = decoded.get("last_name", "")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=400, detail=f"Invalid or expired registration token: {e}") from e

    try:
        existing_google_user = service.get_user_by_google_id(google_id)
        if existing_google_user.email == email:
            access_token = create_access_token(
                data={"sub": str(existing_google_user.id)},
                expires_delta=timedelta(minutes=30),
            )
            refresh_token = create_refresh_token(data={"sub": str(existing_google_user.id)})
            set_refresh_token_cookie(response, refresh_token)
            return {"access_token": access_token, "token_type": "bearer"}  # nosec B105
        else:
            raise HTTPException(status_code=400, detail="User already registered with this Google account")
    except UserNotFoundError:
        pass

    try:
        existing_user = service.get_user_by_email(email)

        try:
            user = service.link_google_account(existing_user.id, google_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="This account is already linked to another Google account",
            ) from None
    except UserNotFoundError:
        try:
            user = service.create_user(
                username=data.username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                google_id=google_id,
            )
        except UserAlreadyExistsError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=30),
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    set_refresh_token_cookie(response, refresh_token)
    return {"access_token": access_token, "token_type": "bearer"}  # nosec B105
