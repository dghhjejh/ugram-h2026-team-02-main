from typing import Any


class OAuthProvider:
    def verify_token(self, token: str) -> dict[str, Any]:
        # Verify OAuth token
        raise NotImplementedError
