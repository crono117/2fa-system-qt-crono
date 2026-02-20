"""
Auth service — thin Qt-signal wrapper around AuthApiClient.

Provides blocking login/logout/refresh methods designed for ApiWorker usage.
"""
from typing import Optional

from api.auth_client import AuthClient
from api.base_client import ApiResponse
from utils.logger import logger

# Module-level shared client instance
_auth_client = AuthClient()


class AuthService:
    """Thin wrapper around AuthClient for use from ApiWorker threads."""

    def login(self, username: str, password: str, remember_me: bool = False) -> ApiResponse:
        logger.info(f"AuthService.login: {username}")
        return _auth_client.login(username, password, remember_me)

    def logout(self) -> ApiResponse:
        logger.info("AuthService.logout")
        return _auth_client.logout()

    def refresh_token(self) -> ApiResponse:
        return _auth_client.refresh_token()

    def is_authenticated(self) -> bool:
        return _auth_client.is_authenticated()

    def get_access_token(self) -> Optional[str]:
        return _auth_client.get_access_token()

    def get_stored_credentials(self):
        return _auth_client.get_stored_credentials()

    def has_stored_credentials(self) -> bool:
        return _auth_client.has_stored_credentials()


# Global singleton
auth_service = AuthService()
