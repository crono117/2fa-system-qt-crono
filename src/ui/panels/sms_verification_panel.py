"""
SMS verification panel — PySide2.

State machine: IDLE → SELECTED → SENDING → AWAITING_CODE → VERIFYING → COMPLETE/FAILED
Phone auto-populated from merchant.contact_phone.
After successful verification emits merchant_search_cleared for next merchant.
"""
from enum import Enum, auto
from typing import Optional, Dict, Any

from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QLineEdit,
)
from PySide2.QtCore import Qt, QThreadPool

from ui.components.merchant_search_widget import MerchantSearchWidget
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


class SmsVerificationPanel(QWidget):
    """SMS 2FA panel using verification/initiate + verification/confirm endpoints."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._user_data: Dict[str, Any] = {}
        self._selected_merchant: Optional[Dict[str, Any]] = None
        self._session_id: Optional[str] = None
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

        # Merchant selection
        search_group = QGroupBox("1. Select Merchant")
        sg_layout = QVBoxLayout(search_group)
        self._search_widget = MerchantSearchWidget()
        sg_layout.addWidget(self._search_widget)
        layout.addWidget(search_group)

        # Phone number
        phone_group = QGroupBox("2. Merchant Phone")
        pg_layout = QFormLayout(phone_group)
        self._phone_input = QLineEdit()
        self._phone_input.setPlaceholderText("+1XXXXXXXXXX")
        pg_layout.addRow("Phone:", self._phone_input)
        layout.addWidget(phone_group)

        # Send button
        self._send_btn = QPushButton("Send SMS Code")
        self._send_btn.setFixedHeight(36)
        self._send_btn.setStyleSheet(
            "background-color: #1f538d; color: white; border-radius: 4px;"
        )
        self._send_btn.clicked.connect(self._on_send_clicked)
        layout.addWidget(self._send_btn)

        # Code entry
        code_group = QGroupBox("3. Enter SMS Code")
        cg_layout = QVBoxLayout(code_group)

        self._code_instruction = QLabel("Enter the 6-digit code sent via SMS:")
        self._code_instruction.setWordWrap(True)
        cg_layout.addWidget(self._code_instruction)

        self._code_input = QLineEdit()
        self._code_input.setMaxLength(6)
        self._code_input.setPlaceholderText("6-digit code")
        self._code_input.setAlignment(Qt.AlignCenter)
        self._code_input.setStyleSheet("font-size: 20px; letter-spacing: 4px; padding: 6px;")
        self._code_input.returnPressed.connect(self._on_verify_clicked)
        cg_layout.addWidget(self._code_input)

        btn_row = QHBoxLayout()
        self._verify_btn = QPushButton("Confirm Code")
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

        cg_layout.addLayout(btn_row)
        layout.addWidget(code_group)

        # Status
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _wire_signals(self):
        app_signals.merchant_selected.connect(self._on_merchant_selected)
        app_signals.ws_verification_update.connect(self._on_ws_update)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_user_data(self, user_data: Dict[str, Any]):
        self._user_data = user_data

    def reset(self):
        self._selected_merchant = None
        self._session_id = None
        self._phone_input.clear()
        self._code_input.clear()
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

        self._phone_input.setEnabled(s in (State.SELECTED, State.FAILED))
        self._send_btn.setEnabled(s in (State.SELECTED, State.FAILED))
        self._code_input.setEnabled(s == State.AWAITING_CODE)
        self._verify_btn.setEnabled(s == State.AWAITING_CODE)
        self._cancel_btn.setEnabled(s in (State.SENDING, State.AWAITING_CODE, State.VERIFYING))

        if s == State.IDLE:
            self._send_btn.setText("Send SMS Code")
            self._set_status("", "")
        elif s == State.SELECTED:
            self._send_btn.setText("Send SMS Code")
        elif s == State.SENDING:
            self._send_btn.setText("Sending…")
            self._set_status("Sending SMS code…", "info")
        elif s == State.AWAITING_CODE:
            self._set_status("SMS sent! Enter the 6-digit code.", "info")
        elif s == State.VERIFYING:
            self._verify_btn.setText("Verifying…")
            self._set_status("Verifying code…", "info")
        elif s == State.COMPLETE:
            self._verify_btn.setText("Confirm Code")
            self._set_status("SMS verification successful!", "success")
        elif s == State.FAILED:
            self._verify_btn.setText("Confirm Code")
            self._set_status("Verification failed. Try again.", "error")

    def _set_status(self, msg: str, level: str):
        color_map = {
            'info':    "#1565c0",
            'success': "#1a7a1a",
            'warning': "#856200",
            'error':   "#c0392b",
            '':        "#333",
        }
        self._status_label.setStyleSheet(f"color: {color_map.get(level, '#333')};")
        self._status_label.setText(msg)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_merchant_selected(self, merchant: Dict[str, Any]):
        self._selected_merchant = merchant
        phone = merchant.get('contact_phone', merchant.get('phone', ''))
        self._phone_input.setText(phone)
        self._code_input.clear()
        self._transition(State.SELECTED)

    def _on_send_clicked(self):
        if not self._selected_merchant:
            self._set_status("Please select a merchant first.", "warning")
            return
        phone = self._phone_input.text().strip()
        if not phone:
            self._set_status("Phone number is required.", "warning")
            return
        # Patch merchant with possibly-edited phone
        merchant = dict(self._selected_merchant)
        merchant['contact_phone'] = phone
        self._transition(State.SENDING)

        user_id = self._user_data.get('id') or self._user_data.get('user_id', 0)
        worker = ApiWorker(
            verification_service.start_sms_verification,
            merchant,
            user_id,
        )
        worker.signals.result.connect(self._on_send_result)
        worker.signals.error.connect(self._on_send_error)
        QThreadPool.globalInstance().start(worker)

    def _on_send_result(self, result):
        if result.success:
            self._session_id = result.session_id
            self._transition(State.AWAITING_CODE)
            app_signals.sms_sent.emit(result.session_id or "")
        else:
            self._transition(State.SELECTED)
            self._set_status(result.message, "error")

    def _on_send_error(self, error_msg: str):
        self._transition(State.SELECTED)
        self._set_status(f"Error: {error_msg}", "error")

    def _on_verify_clicked(self):
        code = self._code_input.text().strip()
        if len(code) != 6 or not code.isdigit():
            self._set_status("Please enter a valid 6-digit code.", "warning")
            return
        if not self._session_id:
            self._set_status("No active session. Please resend SMS.", "warning")
            return
        self._transition(State.VERIFYING)
        worker = ApiWorker(
            verification_service.verify_sms_code,
            code,
            self._session_id,
        )
        worker.signals.result.connect(self._on_verify_result)
        worker.signals.error.connect(self._on_verify_error)
        QThreadPool.globalInstance().start(worker)

    def _on_verify_result(self, result):
        if result.success:
            self._on_sms_verified(result.auth_id or "")
        else:
            self._transition(State.AWAITING_CODE)
            self._set_status(result.message, "error")
            self._code_input.clear()

    def _on_verify_error(self, error_msg: str):
        self._transition(State.AWAITING_CODE)
        self._set_status(f"Error: {error_msg}", "error")
        self._code_input.clear()

    def _on_sms_verified(self, auth_id: str):
        self._transition(State.COMPLETE)
        app_signals.verification_completed.emit(True, "SMS verified successfully", auth_id)
        app_signals.status_message.emit("SMS Verification complete!", "success")
        # Reset for next merchant (consistent with Bug 3 fix)
        app_signals.merchant_search_cleared.emit()
        self._selected_merchant = None
        self._session_id = None
        logger.info(f"SMS verification complete. auth_id={auth_id}")

    def _on_ws_update(self, data: Dict[str, Any]):
        status = data.get('status', '')
        if status in ('verified', 'completed', 'success'):
            if self._state == State.AWAITING_CODE:
                auth_id = data.get('auth_id', '')
                self._on_sms_verified(auth_id)
        elif status in ('failed', 'expired'):
            if self._state in (State.AWAITING_CODE, State.VERIFYING):
                self._transition(State.FAILED)

    def _on_cancel_clicked(self):
        verification_service.cancel_session()
        self._session_id = None
        self._code_input.clear()
        self._transition(State.SELECTED if self._selected_merchant else State.IDLE)
        self._set_status("Cancelled.", "info")
