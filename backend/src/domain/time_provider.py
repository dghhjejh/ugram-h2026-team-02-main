"""Time provider port for dependency injection.

This interface allows the domain layer to remain independent of concrete
time implementations, following the Dependency Inversion Principle.
"""

from datetime import datetime
from typing import Protocol


class ITimeProvider(Protocol):
    """Protocol for providing current time.

    This abstraction allows for:
    - Testability (mock time in tests)
    - Flexibility (different time sources)
    - Decoupling from system time
    """

    def now(self) -> datetime:
        """Get current UTC time as timezone-aware datetime.

        Returns:
            Current time in UTC with timezone information
        """
        ...
