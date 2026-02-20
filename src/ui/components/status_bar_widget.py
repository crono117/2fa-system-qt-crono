"""
Status bar widget — displays status messages and WebSocket connection state.
"""
from PySide2.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide2.QtCore import Qt, QTimer

from core.app_signals import app_signals


_LEVEL_STYLES = {
    'info':    "color: #333; background: transparent;",
    'success': "color: #1a7a1a; background: transparent;",
    'warning': "color: #856200; background: transparent;",
    'error':   "color: #c0392b; background: transparent;",
}


class StatusBarWidget(QWidget):
    """
    Persistent status strip at the bottom of the dashboard.

    Left side:  scrolling status messages (auto-clears after 6 s)
    Right side: WebSocket connection indicator
    """

    _AUTO_CLEAR_MS = 6_000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._wire_signals()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(8)

        self._msg_label = QLabel("")
        self._msg_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self._msg_label, 1)

        self._ws_label = QLabel("● Offline")
        self._ws_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._ws_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._ws_label)

        self._clear_timer = QTimer(self)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._clear_message)

    def _wire_signals(self):
        app_signals.status_message.connect(self.show_message)
        app_signals.ws_connected.connect(self._on_ws_connected)
        app_signals.ws_disconnected.connect(self._on_ws_disconnected)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def show_message(self, message: str, level: str = 'info'):
        style = _LEVEL_STYLES.get(level, _LEVEL_STYLES['info'])
        self._msg_label.setStyleSheet(style)
        self._msg_label.setText(message)
        self._clear_timer.start(self._AUTO_CLEAR_MS)

    def _clear_message(self):
        self._msg_label.setText("")
        self._msg_label.setStyleSheet("")

    def _on_ws_connected(self):
        self._ws_label.setText("● Real-time active")
        self._ws_label.setStyleSheet("color: green; font-size: 11px;")

    def _on_ws_disconnected(self):
        self._ws_label.setText("● Offline")
        self._ws_label.setStyleSheet("color: gray; font-size: 11px;")
