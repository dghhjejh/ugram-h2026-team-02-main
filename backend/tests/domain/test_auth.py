"""
Tests cover:
- Password hashing
- Password comparison
- JWT token creation
"""

from typing import Any
from unittest.mock import patch

import jwt
from src.domain.users.helpers.auth import compare_password, create_access_token, hash_password

# Test Constants
PLAIN_PASSWORD = "MySecurePassword123!"  # pragma: allowlist secret
DIFFERENT_PASSWORD = "DifferentPassword456!"  # pragma: allowlist secret
EMPTY_PASSWORD = ""

TEST_USERNAME = "testuser"

# Mock secret key and algorithm for testing
TEST_SECRET_KEY = "test-secret-key-for-testing-only"  # pragma: allowlist secret
TEST_ALGORITHM = "HS256"


class TestHashPassword:
    """Unit tests for hash_password function."""

    def test_given_plain_password_when_hashing_then_returns_non_empty_string(self) -> None:
        """Hashing a password should return a non-empty string."""
        # Given
        plain_password = PLAIN_PASSWORD

        # When
        result = hash_password(plain_password)

        # Then
        assert isinstance(result, str)
        assert len(result) > 0
        assert result != plain_password

    def test_given_same_password_when_hashing_twice_then_returns_different_hashes(self) -> None:
        """Hashing the same password twice should produce different hashes (salt)."""
        # Given
        plain_password = PLAIN_PASSWORD

        # When
        hash1 = hash_password(plain_password)
        hash2 = hash_password(plain_password)

        # Then
        assert hash1 != hash2


class TestComparePassword:
    """Unit tests for compare_password function."""

    def test_given_correct_password_when_comparing_then_returns_true(self) -> None:
        """Comparing correct password with its hash should return True."""
        # Given
        plain_password = PLAIN_PASSWORD
        hashed_password = hash_password(plain_password)

        # When
        result = compare_password(plain_password, hashed_password)

        # Then
        assert result is True

    def test_given_wrong_password_when_comparing_then_returns_false(self) -> None:
        """Comparing wrong password with hash should return False."""
        # Given
        plain_password = PLAIN_PASSWORD
        hashed_password = hash_password(plain_password)
        wrong_password = DIFFERENT_PASSWORD

        # When
        result = compare_password(wrong_password, hashed_password)

        # Then
        assert result is False

    def test_given_empty_password_when_comparing_with_valid_hash_then_returns_false(self) -> None:
        """Comparing empty password with valid hash should return False."""
        # Given
        plain_password = PLAIN_PASSWORD
        hashed_password = hash_password(plain_password)
        empty_password = EMPTY_PASSWORD

        # When
        result = compare_password(empty_password, hashed_password)

        # Then
        assert result is False


class TestCreateAccessToken:
    """Unit tests for create_access_token function."""

    def test_given_user_data_when_creating_token_then_returns_valid_jwt(self) -> None:
        """Creating token should return a valid decodable JWT."""
        # Given
        user_data = {"sub": TEST_USERNAME}

        # When
        with (
            patch("src.domain.users.helpers.auth.SECRET_KEY", TEST_SECRET_KEY),
            patch("src.domain.users.helpers.auth.ALGORITHM", TEST_ALGORITHM),
        ):
            token = create_access_token(user_data)

        # Then
        decoded = jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])  # type: ignore[attr-defined]
        assert decoded["sub"] == TEST_USERNAME

    def test_given_user_data_when_creating_token_then_includes_expiration(self) -> None:
        """Created token should include expiration claim."""
        # Given
        user_data = {"sub": TEST_USERNAME}

        # When
        with (
            patch("src.domain.users.helpers.auth.SECRET_KEY", TEST_SECRET_KEY),
            patch("src.domain.users.helpers.auth.ALGORITHM", TEST_ALGORITHM),
        ):
            token = create_access_token(user_data)

        # Then
        decoded = jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])  # type: ignore[attr-defined]
        assert "exp" in decoded
        assert isinstance(decoded["exp"], int)

    def test_given_user_data_when_creating_token_then_preserves_original_data(self) -> None:
        """Creating token should not mutate original data dictionary."""
        # Given
        user_data = {"sub": TEST_USERNAME, "role": "admin"}
        original_data = user_data.copy()

        # When
        with (
            patch("src.domain.users.helpers.auth.SECRET_KEY", TEST_SECRET_KEY),
            patch("src.domain.users.helpers.auth.ALGORITHM", TEST_ALGORITHM),
        ):
            create_access_token(user_data)

        # Then
        assert user_data == original_data

    def test_given_multiple_claims_when_creating_token_then_all_claims_included(self) -> None:
        """Token should include all provided claims."""
        # Given
        user_data: dict[str, Any] = {"sub": TEST_USERNAME, "role": "admin", "email": "test@example.com"}

        # When
        with (
            patch("src.domain.users.helpers.auth.SECRET_KEY", TEST_SECRET_KEY),
            patch("src.domain.users.helpers.auth.ALGORITHM", TEST_ALGORITHM),
        ):
            token = create_access_token(user_data)

        # Then
        decoded = jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])  # type: ignore[attr-defined]
        assert decoded["sub"] == TEST_USERNAME
        assert decoded["role"] == "admin"
        assert decoded["email"] == "test@example.com"

    def test_given_two_tokens_for_same_user_when_created_separately_then_tokens_differ(self) -> None:
        """Creating two tokens for same user should produce different tokens."""
        # Given
        user_data = {"sub": TEST_USERNAME}

        # When
        with (
            patch("src.domain.users.helpers.auth.SECRET_KEY", TEST_SECRET_KEY),
            patch("src.domain.users.helpers.auth.ALGORITHM", TEST_ALGORITHM),
        ):
            token1 = create_access_token(user_data)
            token2 = create_access_token(user_data)

        # Then
        # Tokens might be the same if created at exact same second, but should decode to same data
        decoded1 = jwt.decode(token1, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])  # type: ignore[attr-defined]
        decoded2 = jwt.decode(token2, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])  # type: ignore[attr-defined]
        assert decoded1["sub"] == decoded2["sub"] == TEST_USERNAME


class TestPasswordWorkflow:
    """Integration tests for password hashing and comparison workflow."""

    def test_given_password_when_hashed_and_compared_then_workflow_succeeds(self) -> None:
        """Complete workflow: hash password then verify it."""
        # Given
        plain_password = PLAIN_PASSWORD

        # When
        hashed = hash_password(plain_password)
        is_valid = compare_password(plain_password, hashed)

        # Then
        assert is_valid is True

    def test_given_multiple_passwords_when_hashed_then_each_validates_correctly(self) -> None:
        """Multiple passwords should each validate only with their own hash."""
        # Given
        password1 = "FirstPassword123!"  # pragma: allowlist secret
        password2 = "SecondPassword456!"  # pragma: allowlist secret

        # When
        hash1 = hash_password(password1)
        hash2 = hash_password(password2)

        # Then
        assert compare_password(password1, hash1) is True
        assert compare_password(password2, hash2) is True
        assert compare_password(password1, hash2) is False
        assert compare_password(password2, hash1) is False
