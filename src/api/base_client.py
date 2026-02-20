"""
Base API Client with HTTP request handling and authentication.
"""
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException, ConnectionError, Timeout, HTTPError
from urllib3.util.retry import Retry

from config.settings import settings
from utils.logger import logger


@dataclass
class ApiResponse:
    """Standardized API response container."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None

    def __bool__(self):
        return self.success


@dataclass
class AuthTokens:
    """Authentication token container."""
    access_token: str
    refresh_token: str
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        return datetime.now() >= self.expires_at

    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (within threshold)."""
        threshold = timedelta(seconds=settings.TOKEN_REFRESH_THRESHOLD)
        return datetime.now() >= (self.expires_at - threshold)


class BaseApiClient:
    """
    Base HTTP API client with authentication support.

    Provides low-level HTTP request handling with retry logic,
    connection pooling, and JWT token management.
    """

    # CLASS-LEVEL token storage (shared across all instances)
    _shared_tokens: Optional[AuthTokens] = None
    _shared_lock = threading.Lock()

    def __init__(self):
        """Initialize base API client."""
        self._session = requests.Session()
        self._lock = threading.Lock()
        self._setup_session()

        # Callbacks for token events
        self._on_token_refresh: List[Callable] = []
        self._on_logout: List[Callable] = []

    def _setup_session(self):
        """Configure HTTP session with retry strategy."""
        # Retry strategy
        retry_strategy = Retry(
            total=settings.API_RETRY_ATTEMPTS,
            backoff_factor=settings.API_RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )

        # HTTP adapter
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )

        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        # Default headers
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def add_token_refresh_callback(self, callback: Callable):
        """Add callback for token refresh events."""
        self._on_token_refresh.append(callback)

    def add_logout_callback(self, callback: Callable):
        """Add callback for logout events."""
        self._on_logout.append(callback)

    def _fire_token_refresh_callbacks(self):
        """Fire all token refresh callbacks."""
        for callback in self._on_token_refresh:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in token refresh callback: {e}")

    def _fire_logout_callbacks(self):
        """Fire all logout callbacks."""
        for callback in self._on_logout:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in logout callback: {e}")

    def _update_auth_header(self):
        """Update Authorization header with current token."""
        with BaseApiClient._shared_lock:
            if BaseApiClient._shared_tokens:
                self._session.headers["Authorization"] = f"Bearer {BaseApiClient._shared_tokens.access_token}"
            elif "Authorization" in self._session.headers:
                del self._session.headers["Authorization"]

    def set_tokens(self, access_token: str, refresh_token: str, expires_in: int):
        """
        Set authentication tokens.

        Args:
            access_token: JWT access token
            refresh_token: JWT refresh token
            expires_in: Token expiration time in seconds
        """
        with BaseApiClient._shared_lock:
            BaseApiClient._shared_tokens = AuthTokens(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=datetime.now() + timedelta(seconds=expires_in)
            )
        self._update_auth_header()

    def clear_tokens(self):
        """Clear authentication tokens."""
        with BaseApiClient._shared_lock:
            BaseApiClient._shared_tokens = None
        self._update_auth_header()
        self._fire_logout_callbacks()

    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        with BaseApiClient._shared_lock:
            return BaseApiClient._shared_tokens is not None and not BaseApiClient._shared_tokens.is_expired

    def get_access_token(self) -> Optional[str]:
        """Get current access token."""
        with BaseApiClient._shared_lock:
            return BaseApiClient._shared_tokens.access_token if BaseApiClient._shared_tokens else None

    def get_refresh_token(self) -> Optional[str]:
        """Get current refresh token."""
        with BaseApiClient._shared_lock:
            return BaseApiClient._shared_tokens.refresh_token if BaseApiClient._shared_tokens else None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        authenticated: bool = True,
        **kwargs
    ) -> ApiResponse:
        """
        Make HTTP request with error handling.

        Args:
            method: HTTP method
            endpoint: API endpoint
            authenticated: Whether to include auth header
            **kwargs: Additional request arguments

        Returns:
            ApiResponse object
        """
        # Handle both full URLs and relative paths
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            url = endpoint  # Already a full URL
        else:
            url = f"{settings.API_BASE_URL}/{endpoint.lstrip('/')}"

        # Check authentication requirement
        if authenticated and not self.is_authenticated():
            return ApiResponse(
                success=False,
                error="Authentication required",
                status_code=401
            )

        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = settings.API_TIMEOUT

        # Convert data to JSON if present
        if 'data' in kwargs and not isinstance(kwargs['data'], str):
            kwargs['data'] = json.dumps(kwargs['data'])

        try:
            logger.debug(f"{method} {endpoint}")

            # Update authorization header if authenticated
            if authenticated:
                self._update_auth_header()

            response = self._session.request(method, url, **kwargs)
            response.raise_for_status()

            # Parse response
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = {"message": response.text}

            return ApiResponse(
                success=True,
                data=data,
                status_code=response.status_code
            )

        except HTTPError as e:
            logger.error(f"HTTP error for {method} {endpoint}: {e}")

            try:
                error_data = e.response.json()
                error_message = error_data.get('detail') or error_data.get('error') or str(e)
            except:
                error_message = str(e)

            return ApiResponse(
                success=False,
                error=error_message,
                status_code=e.response.status_code if e.response else None
            )

        except ConnectionError as e:
            logger.error(f"Connection error for {method} {endpoint}: {e}")
            return ApiResponse(
                success=False,
                error="Unable to connect to server. Please check your internet connection.",
                status_code=None
            )

        except Timeout as e:
            logger.error(f"Timeout for {method} {endpoint}: {e}")
            return ApiResponse(
                success=False,
                error="Request timed out. Please try again.",
                status_code=None
            )

        except RequestException as e:
            logger.error(f"Request error for {method} {endpoint}: {e}")
            return ApiResponse(
                success=False,
                error=str(e),
                status_code=None
            )

    def get(self, endpoint: str, **kwargs) -> ApiResponse:
        """Make authenticated GET request."""
        return self._make_request("GET", endpoint, authenticated=True, **kwargs)

    def post(self, endpoint: str, **kwargs) -> ApiResponse:
        """Make authenticated POST request."""
        return self._make_request("POST", endpoint, authenticated=True, **kwargs)

    def put(self, endpoint: str, **kwargs) -> ApiResponse:
        """Make authenticated PUT request."""
        return self._make_request("PUT", endpoint, authenticated=True, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> ApiResponse:
        """Make authenticated PATCH request."""
        return self._make_request("PATCH", endpoint, authenticated=True, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> ApiResponse:
        """Make authenticated DELETE request."""
        return self._make_request("DELETE", endpoint, authenticated=True, **kwargs)

    def get_public(self, endpoint: str, **kwargs) -> ApiResponse:
        """Make unauthenticated GET request."""
        return self._make_request("GET", endpoint, authenticated=False, **kwargs)

    def post_public(self, endpoint: str, **kwargs) -> ApiResponse:
        """Make unauthenticated POST request."""
        return self._make_request("POST", endpoint, authenticated=False, **kwargs)