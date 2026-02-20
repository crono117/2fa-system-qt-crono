"""
Login screen — QWidget shown in the QStackedWidget before authentication.
"""
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QCheckBox, QSizePolicy,
)
from PySide2.QtCore import Qt, QSettings, QThreadPool

from services.auth_service import auth_service
from core.app_signals import app_signals
from utils.threading_utils import ApiWorker
from config.settings import settings
from utils.logger import logger


class LoginScreen(QWidget):
    """Simple login form.  Credentials are validated via ApiWorker thread."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_last_username()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.setSpacing(16)

        # Title
        title = QLabel(settings.APP_TITLE)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 8px;")
        outer.addWidget(title)

        subtitle = QLabel("Staff Merchant Verification")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: gray; font-size: 12px;")
        outer.addWidget(subtitle)

        outer.addSpacing(12)

        # Form
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("Username")
        self._username_input.returnPressed.connect(self._on_login_clicked)
        form.addRow("Username:", self._username_input)

        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.Password)
        self._password_input.setPlaceholderText("Password")
        self._password_input.returnPressed.connect(self._on_login_clicked)
        form.addRow("Password:", self._password_input)

        outer.addLayout(form)

        self._remember_check = QCheckBox("Remember me")
        outer.addWidget(self._remember_check)

        # Status
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #c0392b;")
        outer.addWidget(self._status_label)

        # Login button
        self._login_btn = QPushButton("Log In")
        self._login_btn.setFixedHeight(38)
        self._login_btn.setStyleSheet(
            "background-color: #1f538d; color: white; font-size: 14px; border-radius: 4px;"
        )
        self._login_btn.clicked.connect(self._on_login_clicked)
        outer.addWidget(self._login_btn)

        outer.addStretch()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_last_username(self):
        qs = QSettings(settings.QSETTINGS_ORG, settings.QSETTINGS_APP)
        last = qs.value(settings.QSETTINGS_LAST_USER_KEY, "")
        if last:
            self._username_input.setText(last)
            self._password_input.setFocus()

    def _save_last_username(self, username: str):
        qs = QSettings(settings.QSETTINGS_ORG, settings.QSETTINGS_APP)
        qs.setValue(settings.QSETTINGS_LAST_USER_KEY, username)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_login_clicked(self):
        username = self._username_input.text().strip()
        password = self._password_input.text()

        if not username or not password:
            self._status_label.setText("Please enter both username and password.")
            return

        self._set_busy(True)
        self._status_label.setText("Logging in…")

        remember = self._remember_check.isChecked()
        worker = ApiWorker(auth_service.login, username, password, remember)
        worker.signals.result.connect(self._on_login_result)
        worker.signals.error.connect(self._on_login_error)
        QThreadPool.globalInstance().start(worker)

    def _on_login_result(self, response):
        self._set_busy(False)
        if response.success:
            user_data = response.data or {}
            self._save_last_username(self._username_input.text().strip())
            self._status_label.setText("")
            self._password_input.clear()
            logger.info("Login successful")
            app_signals.login_success.emit(user_data)
        else:
            error_msg = response.error or "Login failed"
            self._status_label.setText(error_msg)
            logger.warning(f"Login failed: {error_msg}")

    def _on_login_error(self, error_msg: str):
        self._set_busy(False)
        self._status_label.setText(f"Error: {error_msg}")

    def _set_busy(self, busy: bool):
        self._login_btn.setEnabled(not busy)
        self._username_input.setEnabled(not busy)
        self._password_input.setEnabled(not busy)
        self._login_btn.setText("Logging in…" if busy else "Log In")

    def reset(self):
        """Return widget to clean state (called after logout)."""
        self._password_input.clear()
        self._status_label.setText("")
        self._set_busy(False)
        self._username_input.setFocus()
