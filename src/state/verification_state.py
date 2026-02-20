"""
Verification state — PySide2 port.

Logic identical to frontend_ii; event_bus replaced by app_signals imports
that are resolved lazily to avoid circular imports at module load time.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from threading import Lock

from utils.logger import logger


class VerificationState:
    """
    Thread-safe verification workflow state.

    Changes are broadcast via app_signals (imported lazily to avoid
    circular-import issues at startup).
    """

    def __init__(self):
        self._current_verification: Optional[Dict[str, Any]] = None
        self._verification_status: str = "idle"
        self._current_token: Optional[str] = None
        self._current_auth_id: Optional[str] = None
        self._verification_method: Optional[str] = None
        self._attempts_count: int = 0
        self._max_attempts: int = 5
        self._started_at: Optional[datetime] = None
        self._lock = Lock()

    def _signals(self):
        """Lazy import to avoid circular dependency at module load."""
        from core.app_signals import app_signals
        return app_signals

    def start_verification(
        self,
        customer_id: str,
        method: str,
        token: Optional[str] = None,
        auth_id: Optional[str] = None,
    ) -> None:
        with self._lock:
            self._current_verification = {
                'customer_id': customer_id,
                'method': method,
                'started_at': datetime.now(),
            }
            self._verification_status = "in_progress"
            self._current_token = token
            self._current_auth_id = auth_id
            self._verification_method = method
            self._attempts_count = 0
            self._started_at = datetime.now()

        logger.info(f"Verification started: customer={customer_id}, method={method}")

    def complete_verification(self, success: bool, message: str = "") -> None:
        with self._lock:
            if not self._current_verification:
                return
            auth_id = self._current_auth_id
            self._verification_status = "completed" if success else "failed"
            self._reset_state()

        logger.info(f"Verification completed: success={success}")
        try:
            self._signals().verification_completed.emit(success, message, auth_id or "")
        except Exception as exc:
            logger.error(f"Error emitting verification_completed: {exc}")

    def update_status(self, status: str, message: str = "") -> None:
        with self._lock:
            self._verification_status = status
        logger.debug(f"Verification status: {status}")

    def increment_attempts(self) -> int:
        with self._lock:
            self._attempts_count += 1
            return self._attempts_count

    def is_max_attempts_reached(self) -> bool:
        with self._lock:
            return self._attempts_count >= self._max_attempts

    def get_current_verification(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._current_verification.copy() if self._current_verification else None

    def get_status(self) -> str:
        with self._lock:
            return self._verification_status

    def get_auth_id(self) -> Optional[str]:
        with self._lock:
            return self._current_auth_id

    def get_token(self) -> Optional[str]:
        with self._lock:
            return self._current_token

    def get_attempts(self) -> int:
        with self._lock:
            return self._attempts_count

    def is_active(self) -> bool:
        with self._lock:
            return self._current_verification is not None

    def _reset_state(self) -> None:
        self._current_verification = None
        self._verification_status = "idle"
        self._current_token = None
        self._current_auth_id = None
        self._verification_method = None
        self._attempts_count = 0
        self._started_at = None


# Global singleton
verification_state = VerificationState()
