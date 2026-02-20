"""
Email verification panel — PySide2.

State machine: IDLE → SELECTED → SENDING → AWAITING_CODE → VERIFYING → COMPLETE/FAILED

Bug 3 FIX: After successful PIN verify, emits app_signals.merchant_search_cleared
           so the search widget resets for the next merchant — no logout needed.
"""
from enum import Enum, auto
from typing import Optional, Dict, Any

from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QLineEdit,
)
from PySide2.QtCore import Qt, QThreadPool

from ui.components.merchant_search_widget import MerchantSearchWidget
from ui.components.pin_entry_widget import PinEntryWidget
from services.verification_service import verification_service
from core.app_signals import app_signals
from utils.threading_utils import ApiWorker
from utils.logger import logger


class State(Enum):
    IDLE = auto()
    SELECTED = auto()
    SENDING = auto()
    AWAITING_CODE = auto()
    VERIFYING = auto()
    COMPLETE = auto()
    FAILED = auto()


class EmailVerificationPanel(QWidget):
    """
    Email 2FA panel with enforced state machine.

    Payload bug fixes are in verification_service.py, not here.
    Bug 3 fix lives in _on_pin_verified().
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._user_data: Dict[str, Any] = {}
        self._selected_merchant: Optional[Dict[str, Any]] = None
        self._current_merchant_id: Optional[str] = None
        self._state = State.IDLE
        self._setup_ui()
        self._wire_signals()
        self._apply_state()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Section: Merchant selection
        search_group = QGroupBox("1. Select Merchant")
        sg_layout = QVBoxLayout(search_group)
        self._search_widget = MerchantSearchWidget()
        sg_layout.addWidget(self._search_widget)
        layout.addWidget(search_group)

        # Section: Email info
        email_group = QGroupBox("2. Merchant Email")
        eg_layout = QFormLayout(email_group)
        self._email_label = QLabel("—")
        self._email_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        eg_layout.addRow("Email on file:", self._email_label)
        layout.addWidget(email_group)

        # Send button
        self._send_btn = QPushButton("Send Verification Email")
        self._send_btn.setFixedHeight(36)
        self._send_btn.setStyleSheet(
            "background-color: #1f538d; color: white; border-radius: 4px;"
        )
        self._send_btn.clicked.connect(self._on_send_clicked)
        layout.addWidget(self._send_btn)

        # Section: PIN entry
        pin_group = QGroupBox("3. Enter PIN Code")
        pg_layout = QVBoxLayout(pin_group)

        self._pin_instruction = QLabel(
            "Enter the 6-digit PIN sent to the merchant's email:"
        )
        self._pin_instruction.setWordWrap(True)
        pg_layout.addWidget(self._pin_instruction)

        self._pin_widget = PinEntryWidget()
        pg_layout.addWidget(self._pin_widget, alignment=Qt.AlignCenter)

        btn_row = QHBoxLayout()
        self._verify_btn = QPushButton("Verify PIN")
        self._verify_btn.setFixedHeight(34)
        self._verify_btn.setStyleSheet(
            "background-color: #28a745; color: white; border-radius: 4px;"
        )
        self._verify_btn.clicked.connect(self._on_verify_clicked)
        btn_row.addWidget(self._verify_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedHeight(34)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_row.addWidget(self._cancel_btn)

        pg_layout.addLayout(btn_row)
        layout.addWidget(pin_group)

        # Status message
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _wire_signals(self):
        app_signals.merchant_selected.connect(self._on_merchant_selected)
        app_signals.ws_verification_update.connect(self._on_ws_update)
        self._pin_widget.pin_entered.connect(self._on_pin_auto_entered)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_user_data(self, user_data: Dict[str, Any]):
        self._user_data = user_data

    def reset(self):
        self._selected_merchant = None
        self._current_merchant_id = None
        self._email_label.setText("—")
        self._pin_widget.clear()
        self._status_label.setText("")
        self._transition(State.IDLE)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def _transition(self, new_state: State):
        self._state = new_state
        self._apply_state()

    def _apply_state(self):
        s = self._state

        self._send_btn.setEnabled(s == State.SELECTED)
        self._pin_widget.set_enabled(s == State.AWAITING_CODE)
        self._verify_btn.setEnabled(s == State.AWAITING_CODE)
        self._cancel_btn.setEnabled(s in (State.SENDING, State.AWAITING_CODE, State.VERIFYING))

        if s == State.IDLE:
            self._send_btn.setText("Send Verification Email")
            self._set_status("", "")
        elif s == State.SELECTED:
            self._send_btn.setText("Send Verification Email")
        elif s == State.SENDING:
            self._send_btn.setText("Sending…")
            self._set_status("Sending verification email…", "info")
        elif s == State.AWAITING_CODE:
            self._set_status("PIN sent. Enter the 6-digit code from the merchant's email.", "info")
        elif s == State.VERIFYING:
            self._verify_btn.setText("Verifying…")
            self._set_status("Verifying PIN…", "info")
        elif s == State.COMPLETE:
            self._verify_btn.setText("Verify PIN")
            self._set_status("Verification successful!", "success")
        elif s == State.FAILED:
            self._verify_btn.setText("Verify PIN")
            self._set_status("Verification failed. Please try again.", "error")

    def _set_status(self, msg: str, level: str):
        color_map = {
            'info':    "#1565c0",
            'success': "#1a7a1a",
            'warning': "#856200",
            'error':   "#c0392b",
            '':        "#333",
        }
        color = color_map.get(level, "#333")
        self._status_label.setStyleSheet(f"color: {color};")
        self._status_label.setText(msg)

    # ------------------------------------------------------------------
    # Slots — merchant selection
    # ------------------------------------------------------------------

    def _on_merchant_selected(self, merchant: Dict[str, Any]):
        self._selected_merchant = merchant
        self._current_merchant_id = merchant.get('merchant_id')
        email = merchant.get('contact_email', merchant.get('email', 'N/A'))
        self._email_label.setText(email)
        self._pin_widget.clear()
        self._transition(State.SELECTED)
        logger.debug(f"EmailPanel: merchant selected {self._current_merchant_id}")

    # ------------------------------------------------------------------
    # Slots — send email
    # ------------------------------------------------------------------

    def _on_send_clicked(self):
        if not self._selected_merchant:
            self._set_status("Please select a merchant first.", "warning")
            return
        self._transition(State.SENDING)

        user_id = self._user_data.get('id') or self._user_data.get('user_id', 0)
        worker = ApiWorker(
            verification_service.start_email_verification,
            self._selected_merchant,
            user_id,
        )
        worker.signals.result.connect(self._on_send_result)
        worker.signals.error.connect(self._on_send_error)
        QThreadPool.globalInstance().start(worker)

    def _on_send_result(self, result):
        if result.success:
            self._transition(State.AWAITING_CODE)
            app_signals.pin_sent.emit(result.auth_id or "")
        else:
            self._transition(State.SELECTED)
            self._set_status(result.message, "error")
            app_signals.status_message.emit(result.message, "error")

    def _on_send_error(self, error_msg: str):
        self._transition(State.SELECTED)
        self._set_status(f"Error: {error_msg}", "error")

    # ------------------------------------------------------------------
    # Slots — verify PIN
    # ------------------------------------------------------------------

    def _on_pin_auto_entered(self, pin: str):
        """Triggered when all 6 digits are filled in."""
        if self._state == State.AWAITING_CODE:
            self._submit_pin(pin)

    def _on_verify_clicked(self):
        pin = self._pin_widget.get_pin()
        if len(pin) != 6:
            self._set_status("Please enter all 6 digits.", "warning")
            return
        self._submit_pin(pin)

    def _submit_pin(self, pin: str):
        if self._state != State.AWAITING_CODE:
            return
        self._transition(State.VERIFYING)
        user_id = self._user_data.get('id') or self._user_data.get('user_id', 0)
        worker = ApiWorker(
            verification_service.verify_pin_code,
            pin,
            self._current_merchant_id,
            user_id,
        )
        worker.signals.result.connect(self._on_verify_result)
        worker.signals.error.connect(self._on_verify_error)
        QThreadPool.globalInstance().start(worker)

    def _on_verify_result(self, result):
        if result.success:
            self._on_pin_verified(result.auth_id or "")
        else:
            self._transition(State.AWAITING_CODE)
            self._set_status(result.message, "error")
            self._pin_widget.clear()
            app_signals.status_message.emit(result.message, "error")

    def _on_verify_error(self, error_msg: str):
        self._transition(State.AWAITING_CODE)
        self._set_status(f"Error: {error_msg}", "error")
        self._pin_widget.clear()

    def _on_pin_verified(self, auth_id: str):
        """
        BUG 3 FIX: After successful verification emit merchant_search_cleared
        so MerchantSearchWidget resets — user can verify a new merchant without
        logging out.
        """
        self._transition(State.COMPLETE)
        app_signals.verification_completed.emit(True, "PIN verified successfully", auth_id)
        app_signals.status_message.emit("Verification complete!", "success")

        # Reset for next merchant (Bug 3 fix)
        app_signals.merchant_search_cleared.emit()
        self._selected_merchant = None
        self._current_merchant_id = None
        logger.info(f"Email verification complete. auth_id={auth_id}")

    # ------------------------------------------------------------------
    # Slots — WebSocket real-time update
    # ------------------------------------------------------------------

    def _on_ws_update(self, data: Dict[str, Any]):
        """Handle real-time verification status push from backend."""
        status = data.get('status', '')
        if status in ('verified', 'completed', 'success'):
            if self._state == State.AWAITING_CODE:
                auth_id = data.get('auth_id', '')
                self._on_pin_verified(auth_id)
        elif status in ('failed', 'expired'):
            if self._state in (State.AWAITING_CODE, State.VERIFYING):
                self._transition(State.FAILED)

    # ------------------------------------------------------------------
    # Slots — cancel
    # ------------------------------------------------------------------

    def _on_cancel_clicked(self):
        verification_service.cancel_session()
        self._pin_widget.clear()
        self._transition(State.SELECTED if self._selected_merchant else State.IDLE)
        self._set_status("Cancelled.", "info")
