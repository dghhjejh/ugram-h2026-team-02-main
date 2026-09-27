from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .adapters.inbound.api.google import router as google_router
from .adapters.inbound.api.images import router as images_router
from .adapters.inbound.api.notifications import router as notifications_router
from .adapters.inbound.api.social import router as social_router
from .adapters.inbound.api.users import router as users_router
from .adapters.outbound.persistence.database import create_tables
from .application.config import settings
from .application.monitoring import configure_sentry

configure_sentry(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    # Create database tables on startup
    create_tables()
    yield


OPENAPI_TAGS = [
    {
        "name": "users",
        "description": "User registration, authentication, profile management, and account lifecycle endpoints.",
    },
    {
        "name": "images",
        "description": (
            "Image upload and discovery endpoints. The upload flow is: call `POST /images/presign`, upload the binary "
            "to the returned S3 URL, then call `POST /images` to persist metadata."
        ),
    },
    {
        "name": "social",
        "description": (
            "Livrable 3 social endpoints. Public profile counters are available today, while the comment route is exposed "
            "as a documented placeholder returning `501 Not Implemented` until full comments, reactions, and notifications "
            "are implemented server-side."
        ),
    },
    {
        "name": "auth",
        "description": "Google OAuth authentication and registration completion endpoints.",
    },
]


app = FastAPI(
    title="uGram API",
    description=(
        "Instagram-like application backend with user profiles, uploads, search, and Livrable 3 social capabilities "
        "documented through OpenAPI."
    ),
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)


def _normalize_origin(origin: str) -> str:
    return origin.strip().rstrip("/")


def _get_allowed_origins() -> list[str]:
    configured_origins = [
        normalized for origin in (settings.FRONTEND_URL or "").split(",") if (normalized := _normalize_origin(origin))
    ]
    if configured_origins:
        return list(dict.fromkeys(configured_origins))

    if settings.APP_ENV.lower() in {"development", "dev", "test", "testing", "local"}:
        return [
            "http://localhost:5173",
            "http://localhost:3000",
        ]

    return []


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'none'; img-src 'self' https:; connect-src 'self'"
        return response


# Configure CORS for frontend access
allow_origins = _get_allowed_origins()

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(images_router)
app.include_router(social_router)
app.include_router(notifications_router)
app.include_router(google_router)


def _health_payload() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return _health_payload()


@app.get("/health")
def health_check() -> dict[str, str]:
    return _health_payload()
