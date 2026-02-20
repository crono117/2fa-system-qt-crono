"""
Authentication API Client for 2FA Merchant Verification System.

Handles user authentication, token management, and session operations.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from .base_client import BaseApiClient, ApiResponse, AuthTokens
from config.settings import settings
from utils.security import CredentialManager
from utils.logger import logger


class AuthClient(BaseApiClient):
    """
    Authentication API client for login, logout, and token management.

    Features:
    - JWT token authentication
    - Automatic token refresh
    - Secure credential storage
    - User session management
    - Health check endpoint
    """

    def __init__(self):
        """Initialize authentication client."""
        super().__init__()
        self._credential_manager = CredentialManager()

    def login(self, username: str, password: str, remember_me: bool = False) -> ApiResponse:
        """
        Authenticate user and obtain JWT tokens.

        Args:
            username: User's username
            password: User's password
            remember_me: Store credentials securely for auto-login

        Returns:
            ApiResponse with authentication result and user data
        """
        logger.info(f"Attempting login for user: {username}")

        try:
            # Make login request
            response = self.post_public(
                settings.get_api_endpoints()["login"],
                json={"username": username, "password": password}
            )

            if response.success and response.data:
                # Extract tokens
                access_token = response.data.get("access")
                refresh_token = response.data.get("refresh")

                if not access_token or not refresh_token:
                    return ApiResponse(
                        success=False,
                        error="Invalid response: missing tokens",
                        status_code=response.status_code
                    )

                # Calculate expiry (assuming 1-hour tokens)
                expires_in = 3600  # 1 hour in seconds
                expires_at = datetime.now() + timedelta(seconds=expires_in)

                # Store tokens in client
                self.set_tokens(access_token, refresh_token, expires_in)

                # Store credentials securely if requested
                if remember_me:
                    self._credential_manager.store_credentials(username, password)

                logger.info("Login successful")
                return ApiResponse(
                    success=True,
                    data={
                        "user": response.data.get("user", {}),
                        "expires_at": expires_at.isoformat()
                    },
                    status_code=response.status_code
                )

            return response

        except Exception as e:
            logger.error(f"Unexpected login error: {e}")
            return ApiResponse(
                success=False,
                error=f"Login failed: {str(e)}"
            )

    def logout(self) -> ApiResponse:
        """
        Logout user and clear all authentication data.

        Returns:
            ApiResponse with logout result
        """
        logger.info("Logging out")

        try:
            # Clear stored credentials
            self._credential_manager.clear_credentials()

            # Clear tokens (this also fires logout callbacks)
            self.clear_tokens()

            return ApiResponse(success=True, data={"message": "Logged out successfully"})

        except Exception as e:
            logger.error(f"Logout error: {e}")
            return ApiResponse(
                success=False,
                error=f"Logout failed: {str(e)}"
            )

    def refresh_token(self) -> ApiResponse:
        """
        Refresh the access token using refresh token.

        Returns:
            ApiResponse with refresh result
        """
        refresh_token = self.get_refresh_token()

        if not refresh_token:
            return ApiResponse(
                success=False,
                error="No refresh token available"
            )

        try:
            logger.info("Refreshing access token")

            response = self.post_public(
                settings.get_api_endpoints()["refresh"],
                json={"refresh": refresh_token}
            )

            if response.success and response.data:
                access_token = response.data.get("access")

                if not access_token:
                    return ApiResponse(
                        success=False,
                        error="Invalid refresh response: missing access token",
                        status_code=response.status_code
                    )

                # Update tokens (keep same refresh token)
                expires_in = 3600  # 1 hour
                self.set_tokens(access_token, refresh_token, expires_in)

                # Fire token refresh callbacks
                self._fire_token_refresh_callbacks()

                logger.info("Token refresh successful")
                return ApiResponse(success=True, data={"message": "Token refreshed"})

            else:
                # Refresh failed, clear tokens
                self.clear_tokens()
                logger.warning("Token refresh failed, clearing tokens")
                return response

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            self.clear_tokens()
            return ApiResponse(
                success=False,
                error=f"Token refresh failed: {str(e)}"
            )

    def get_current_user(self) -> ApiResponse:
        """
        Get current authenticated user information.

        Returns:
            ApiResponse with user data
        """
        if not self.is_authenticated():
            return ApiResponse(
                success=False,
                error="Not authenticated",
                status_code=401
            )

        try:
            logger.info("Fetching current user info")

            # Attempt token refresh if needed
            if self._tokens and self._tokens.needs_refresh:
                refresh_result = self.refresh_token()
                if not refresh_result.success:
                    return refresh_result

            response = self.get(settings.get_api_endpoints().get("current_user", "/api/auth/me/"))

            if response.success:
                logger.info("User info retrieved successfully")
            else:
                logger.warning(f"Failed to get user info: {response.error}")

            return response

        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return ApiResponse(
                success=False,
                error=f"Failed to get user info: {str(e)}"
            )

    def check_server_health(self) -> ApiResponse:
        """
        Check API server health status.

        Returns:
            ApiResponse with health status
        """
        try:
            logger.debug("Checking server health")

            response = self.get_public(
                settings.get_api_endpoints().get("health", "/api/auth/health/")
            )

            if response.success:
                logger.info("Server health check passed")
            else:
                logger.warning("Server health check failed")

            return response

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return ApiResponse(
                success=False,
                error=f"Health check failed: {str(e)}"
            )

    def get_stored_credentials(self) -> Optional[tuple[str, str]]:
        """
        Get stored credentials if available.

        Returns:
            Tuple of (username, password) or None
        """
        return self._credential_manager.get_credentials()

    def has_stored_credentials(self) -> bool:
        """
        Check if credentials are stored.

        Returns:
            True if credentials are stored
        """
        return self._credential_manager.has_credentials()