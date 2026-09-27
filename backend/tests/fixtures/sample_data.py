"""Sample data fixtures for testing.

Add your test data here. This keeps test files clean and data reusable.
"""

# Example: API response fixtures
SAMPLE_HEALTH_RESPONSE = {
    "status": "ok",
    "version": "0.1.0",
}

SAMPLE_ROOT_RESPONSE = {
    "message": "Hello from DefaultPython API",
}

# Example: User data fixtures
SAMPLE_USER = {
    "id": 1,
    "name": "Test User",
    "email": "test@example.com",
}

# Example: Error response fixtures
SAMPLE_ERROR_RESPONSE = {
    "detail": "Internal Server Error",
    "error": "Something went wrong",
}
