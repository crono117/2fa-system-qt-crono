"""
Configuration settings for the 2FA Merchant Verification Desktop Application (PySide2).
"""
import os
import sys
import configparser
from typing import Dict, Any
from pathlib import Path


def get_config_path() -> Path:
    """Get the path to config.ini file."""
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        config_path = exe_dir / 'config.ini'
    else:
        # Go up from src/config/ to frontend_pyside2/
        config_path = Path(__file__).parent.parent.parent / 'config.ini'
    return config_path


def load_config() -> configparser.ConfigParser:
    """Load configuration from config.ini file."""
    config = configparser.ConfigParser()
    config_path = get_config_path()
    if config_path.exists():
        config.read(config_path)
    return config


_config = load_config()


class AppSettings:
    """Application configuration settings."""

    # Application metadata
    APP_NAME = "2FA System"
    APP_VERSION = "3.0.0"
    APP_TITLE = "2FA System v3.0.0 (Qt)"

    # Window dimensions
    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 620
    MIN_WINDOW_WIDTH = 350
    MIN_WINDOW_HEIGHT = 480
    DASHBOARD_WIDTH = 460
    DASHBOARD_HEIGHT = 720

    # API Configuration
    API_BASE_URL = _config.get('server', 'api_base_url',
                               fallback=os.getenv("API_BASE_URL", "http://10.5.96.4:8000/api"))
    API_TIMEOUT = int(_config.get('server', 'api_timeout',
                                  fallback=os.getenv("API_TIMEOUT", "30")))
    API_RETRY_ATTEMPTS = int(_config.get('server', 'api_retry_attempts',
                                         fallback=os.getenv("API_RETRY_ATTEMPTS", "3")))
    API_RETRY_DELAY = float(os.getenv("API_RETRY_DELAY", "1.0"))

    # Authentication / session
    TOKEN_REFRESH_THRESHOLD = 300   # seconds before expiry to refresh
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour
    AUTO_LOGOUT_WARNING = 300

    # QSettings keys (PySide2-specific)
    QSETTINGS_ORG = "2FASystem"
    QSETTINGS_APP = "MerchantVerification"
    QSETTINGS_LAST_USER_KEY = "login/last_username"

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "merchant_verification_qt.log")
    LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))   # 10 MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # Security
    CREDENTIAL_STORE_SERVICE = "2FA_Merchant_Verification"
    ENCRYPT_LOCAL_DATA = True

    # Data refresh intervals (seconds)
    MERCHANT_DATA_REFRESH = 300
    VERIFICATION_STATUS_REFRESH = 10
    HISTORY_REFRESH_INTERVAL = 30

    # Pagination
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 100

    # File paths
    CONFIG_DIR = Path.home() / ".merchant_verification_qt"
    CACHE_DIR = CONFIG_DIR / "cache"
    LOG_DIR = CONFIG_DIR / "logs"

    # Features
    ENABLE_EXPORT_FUNCTIONALITY = True

    # Debug
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        for directory in [cls.CONFIG_DIR, cls.CACHE_DIR, cls.LOG_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_api_endpoints(cls) -> Dict[str, str]:
        """Get all API endpoints."""
        base = cls.API_BASE_URL
        return {
            # Authentication
            "login": f"{base}/auth/login/",
            "refresh": f"{base}/auth/refresh/",
            "logout": f"{base}/auth/logout/",

            # Email 2FA
            "send_email_auth": f"{base}/auth/send-email/",
            "verify_pin": f"{base}/auth/verify-pin/",
            "authentication_history": f"{base}/auth/history/",

            # Merchants
            "merchants": f"{base}/merchants/merchants/",
            "merchant_search": f"{base}/merchants/merchants/",

            # SMS Verification
            "verification_initiate": f"{base}/verification/initiate/",
            "verification_confirm": f"{base}/verification/confirm/",

            # Health
            "health": f"{base}/verification/health/",
        }

    @classmethod
    def get_websocket_url(cls, user_id: int, token: str) -> str:
        """Build WebSocket URL with JWT token."""
        base = cls.API_BASE_URL
        ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
        # Remove /api suffix
        if ws_base.endswith("/api"):
            ws_base = ws_base[:-4]
        return f"{ws_base}/ws/auth/{user_id}/?token={token}"

    @classmethod
    def get_websocket_origin(cls) -> str:
        """Get Origin header value for WebSocket AllowedHostsOriginValidator."""
        base = cls.API_BASE_URL
        if base.endswith("/api"):
            base = base[:-4]
        return base


# Global settings instance
settings = AppSettings()
