"""
WebSocket manager — PySide2 / QWebSocket implementation.

Replaces the blocking websocket-client library with Qt's native QWebSocket.
Lives on the main thread; signals are automatically main-thread safe.
URL pattern: ws://10.5.96.4:8000/ws/auth/{user_id}/?token=<JWT>
Origin header satisfies Django's AllowedHostsOriginValidator.
"""
import json
from typing import Optional

from PySide2.QtCore import QObject, Signal, QUrl, QTimer
from PySide2.QtNetwork import QAbstractSocket
from PySide2.QtWebSockets import QWebSocket, QWebSocketProtocol

from config.settings import settings
from utils.logger import logger


class WebSocketManager(QObject):
    """
    Qt-native WebSocket manager for real-time verification updates.

    Signals forwarded from here to app_signals by app_window.py.
    """

    connected = Signal()
    disconnected = Signal()
    message_received = Signal(dict)
    error_occurred = Signal(str)

    # Reconnect settings
    _RECONNECT_INTERVAL_MS = 5_000
    _MAX_RECONNECT_ATTEMPTS = 10
    _PING_INTERVAL_MS = 25_000

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._ws = QWebSocket(
            origin=settings.get_websocket_origin(),
            version=QWebSocketProtocol.Version13,
            parent=self,
        )
        self._user_id: Optional[int] = None
        self._token: Optional[str] = None
        self._should_reconnect = False
        self._reconnect_attempts = 0
        self._is_connected = False

        # Reconnect timer
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._attempt_connect)

        # Keepalive ping timer
        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(self._PING_INTERVAL_MS)
        self._ping_timer.timeout.connect(self._send_ping)

        # Wire QWebSocket signals
        self._ws.connected.connect(self._on_connected)
        self._ws.disconnected.connect(self._on_disconnected)
        self._ws.textMessageReceived.connect(self._on_message)
        self._ws.error.connect(self._on_error)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect_user(self, user_id: int, token: str):
        """Open WebSocket for the authenticated user."""
        self._user_id = user_id
        self._token = token
        self._should_reconnect = True
        self._reconnect_attempts = 0
        self._attempt_connect()

    def disconnect_user(self):
        """Close the WebSocket cleanly and stop reconnection."""
        self._should_reconnect = False
        self._ping_timer.stop()
        self._reconnect_timer.stop()
        if self._is_connected:
            self._ws.close()
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _attempt_connect(self):
        """Build URL and open the WebSocket."""
        if not self._user_id or not self._token:
            return

        url_str = settings.get_websocket_url(self._user_id, self._token)
        safe_url = url_str.split("?")[0]
        logger.info(f"Connecting WebSocket: {safe_url}")
        self._ws.open(QUrl(url_str))

    def _on_connected(self):
        self._is_connected = True
        self._reconnect_attempts = 0
        self._reconnect_timer.stop()
        self._ping_timer.start()
        logger.info(f"WebSocket connected (user {self._user_id})")
        self.connected.emit()

    def _on_disconnected(self):
        self._is_connected = False
        self._ping_timer.stop()
        logger.info("WebSocket disconnected")
        self.disconnected.emit()

        if self._should_reconnect and self._reconnect_attempts < self._MAX_RECONNECT_ATTEMPTS:
            self._reconnect_attempts += 1
            logger.info(
                f"Scheduling reconnect {self._reconnect_attempts}/{self._MAX_RECONNECT_ATTEMPTS} "
                f"in {self._RECONNECT_INTERVAL_MS // 1000}s"
            )
            self._reconnect_timer.start(self._RECONNECT_INTERVAL_MS)
        elif self._reconnect_attempts >= self._MAX_RECONNECT_ATTEMPTS:
            logger.warning("WebSocket: max reconnect attempts reached")
            self.error_occurred.emit("Real-time connection lost after max retries")

    def _on_message(self, text: str):
        try:
            data = json.loads(text)
            msg_type = data.get("type", "")
            logger.debug(f"WS message: {msg_type}")
            self.message_received.emit(data)
        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON from WebSocket: {exc}")

    def _on_error(self, error_code: QAbstractSocket.SocketError):
        error_str = self._ws.errorString()
        logger.error(f"WebSocket error {error_code}: {error_str}")
        self.error_occurred.emit(error_str)

    def _send_ping(self):
        if self._is_connected:
            self._ws.ping(b"keepalive")
