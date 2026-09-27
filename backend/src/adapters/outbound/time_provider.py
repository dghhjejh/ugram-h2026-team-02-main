"""Concrete time provider implementation using system time."""

from datetime import UTC, datetime


class SystemTimeProvider:
    """Production time provider using system time.

    Returns timezone-aware UTC datetime using the modern Python API.
    """

    def now(self) -> datetime:
        """Get current UTC time as timezone-aware datetime.

        Returns:
            Current system time in UTC with timezone information
        """
        return datetime.now(UTC)
