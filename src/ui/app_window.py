"""
AppWindow — QMainWindow root container.

Manages:
  - QStackedWidget (login → dashboard swap)
  - WebSocketManager lifecycle (connect at login, disconnect at logout)
  - Session timeout QTimer (1-hour idle → auto-logout)
  - Status bar widget
"""
from typing import Optional, Dict, Any

from PySide2.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QStatusBar,
)
from PySide2.QtCore import Qt, QTimer

from api.websocket_manager import WebSocketManager
from ui.screens.login_screen import LoginScreen
from ui.screens.main_tabbed_screen import MainTabbedScreen
from ui.components.status_bar_widget import StatusBarWidget
from core.app_signals import app_signals
from config.settings import settings
from utils.logger import logger


class AppWindow(QMainWindow):
    """Root application window."""

    _LOGIN_IDX = 0
    _DASHBOARD_IDX = 1

    def __init__(self):
        super().__init__()
        self._user_data: Dict[str, Any] = {}
        self._session_timer = QTimer(self)
        self._session_timer.setSingleShot(True)
        self._session_timer.timeout.connect(self._on_session_timeout)

        self._ws_manager = WebSocketManager(parent=self)

        self._setup_ui()
        self._wire_signals()
        self._show_login()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        self.setWindowTitle(settings.APP_TITLE)
        self.setMinimumSize(settings.MIN_WINDOW_WIDTH, settings.MIN_WINDOW_HEIGHT)

        # Central stack
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._login_screen = LoginScreen()
        self._stack.addWidget(self._login_screen)          # index 0

        self._dashboard = MainTabbedScreen()
        self._stack.addWidget(self._dashboard)              # index 1

        # Status bar
        self._status_bar = StatusBarWidget()
        self.statusBar().addPermanentWidget(self._status_bar, 1)

    def _wire_signals(self):
        # App lifecycle
        app_signals.login_success.connect(self._on_login_success)
        app_signals.logout_requested.connect(self._on_logout)
        app_signals.session_expired.connect(self._on_session_timeout)

        # Status messages → status bar
        app_signals.status_message.connect(self._status_bar.show_message)

        # WebSocket → forward to app_signals
        self._ws_manager.connected.connect(app_signals.ws_connected)
        self._ws_manager.disconnected.connect(app_signals.ws_disconnected)
        self._ws_manager.message_received.connect(self._on_ws_message)
        self._ws_manager.error_occurred.connect(self._on_ws_error)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _show_login(self):
        self.resize(settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)
        self._stack.setCurrentIndex(self._LOGIN_IDX)
        self._login_screen.reset()

    def _show_dashboard(self):
        self.resize(settings.DASHBOARD_WIDTH, settings.DASHBOARD_HEIGHT)
        self._stack.setCurrentIndex(self._DASHBOARD_IDX)

    # ------------------------------------------------------------------
    # Slots — auth
    # ------------------------------------------------------------------

    def _on_login_success(self, user_data: Dict[str, Any]):
        self._user_data = user_data
        user_info = user_data.get('user', user_data)
        user_id = user_info.get('id') or user_info.get('user_id')

        logger.info(f"Login success: user_id={user_id}")

        self._dashboard.set_user_data(user_data)
        self._show_dashboard()

        # Start session timeout (1 hour)
        self._session_timer.start(settings.SESSION_TIMEOUT * 1000)

        # Connect WebSocket
        from api.base_client import BaseApiClient
        token = BaseApiClient.get_access_token(BaseApiClient())
        if user_id and token:
            self._ws_manager.connect_user(int(user_id), token)
        else:
            logger.warning("Could not connect WebSocket: missing user_id or token")

        app_signals.status_message.emit(
            f"Welcome, {user_info.get('username', 'User')}!", "success"
        )

    def _on_logout(self):
        logger.info("Logout requested")
        self._session_timer.stop()
        self._ws_manager.disconnect_user()

        app_signals.reset_all_panels.emit()

        from services.auth_service import auth_service
        auth_service.logout()

        self._user_data = {}
        self._show_login()
        app_signals.status_message.emit("Logged out.", "info")

    def _on_session_timeout(self):
        logger.warning("Session timed out — auto logout")
        app_signals.session_expired.emit()
        self._on_logout()

    # ------------------------------------------------------------------
    # Slots — WebSocket
    # ------------------------------------------------------------------

    def _on_ws_message(self, data: Dict[str, Any]):
        """Route incoming WebSocket messages to the appropriate signal."""
        msg_type = data.get('type', '')

        if msg_type in ('verification.status', 'auth_update',
                        'customer_verification_update', 'verification_update'):
            app_signals.ws_verification_update.emit(data)

        elif msg_type == 'connection_established':
            logger.info("WebSocket: connection_established")

    def _on_ws_error(self, error_msg: str):
        logger.error(f"WebSocket error: {error_msg}")
        app_signals.status_message.emit(
            f"Real-time connection error: {error_msg}", "warning"
        )
