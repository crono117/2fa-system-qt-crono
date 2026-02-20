"""
Logging configuration for the desktop application.
"""
import sys
from pathlib import Path
from loguru import logger as _logger

from config.settings import settings


def setup_logging():
    """Configure logging for the application."""
    # Ensure log directory exists
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Remove default logger
    _logger.remove()
    
    # Console logging
    _logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # File logging
    log_file = settings.LOG_DIR / settings.LOG_FILE
    _logger.add(
        log_file,
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=settings.LOG_MAX_SIZE,
        retention=settings.LOG_BACKUP_COUNT,
        compression="gz"
    )
    
    # Add application info
    _logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    _logger.info(f"Log directory: {settings.LOG_DIR}")
    _logger.info(f"API base URL: {settings.API_BASE_URL}")


# Setup logging when module is imported
setup_logging()

# Export the configured logger
logger = _logger