"""
Main dashboard screen — QTabWidget with three tabs.
"""
from PySide2.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PySide2.QtCore import Qt

from ui.panels.email_verification_panel import EmailVerificationPanel
from ui.panels.sms_verification_panel import SmsVerificationPanel
from ui.panels.history_panel import HistoryPanel
from core.app_signals import app_signals


class MainTabbedScreen(QWidget):
    """
    Dashboard widget shown after login.
    Three tabs: Email 2FA | SMS 2FA | History
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_data = {}
        self._setup_ui()
        self._wire_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        # Tab 1 — Email verification
        self._email_panel = EmailVerificationPanel()
        self._tabs.addTab(self._email_panel, "Email 2FA")

        # Tab 2 — SMS verification
        self._sms_panel = SmsVerificationPanel()
        self._tabs.addTab(self._sms_panel, "SMS 2FA")

        # Tab 3 — History
        self._history_panel = HistoryPanel()
        self._tabs.addTab(self._history_panel, "History")

        layout.addWidget(self._tabs)

    def _wire_signals(self):
        # Reset all panels when user logs out
        app_signals.reset_all_panels.connect(self._on_reset)
        app_signals.logout_requested.connect(self._on_reset)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_user_data(self, user_data: dict):
        self._user_data = user_data
        user_info = user_data.get('user', user_data)
        self._email_panel.set_user_data(user_info)
        self._sms_panel.set_user_data(user_info)
        self._history_panel.refresh()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_reset(self):
        self._email_panel.reset()
        self._sms_panel.reset()
        self._tabs.setCurrentIndex(0)
