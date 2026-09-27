from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from src.application.config import settings

password_hash = PasswordHash.recommended()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


def hash_password(plain_password: str) -> str:
    """This function uses bycrypt algorithm of passlib to hash the password and returns it"""
    return password_hash.hash(plain_password)


def compare_password(plain_password: str, hashed_password: str) -> bool:
    """Check if plain password matches the hashed password."""
    return password_hash.verify(plain_password, hashed_password)


def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY must be configured before tokens can be created")

    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # type: ignore[attr-defined]


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Docstring for create_access_token

    :param data: Description
    :type data: dict[str, Any]
    :param expires_delta: Description
    :type expires_delta: timedelta | None
    :return: Description
    :rtype: str
    """
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY must be configured before tokens can be created")

    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta if expires_delta else datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # type: ignore[attr-defined]
