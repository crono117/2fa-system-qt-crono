"""
PIN entry widget — 6-digit masked input with auto-submit on completion.
"""
from typing import Optional

from PySide2.QtWidgets import QWidget, QHBoxLayout, QLineEdit
from PySide2.QtCore import Signal, Qt
from PySide2.QtGui import QFont


class PinEntryWidget(QWidget):
    """
    Six individual single-digit fields that auto-advance focus.
    Emits pin_entered(str) with the 6-digit string when all filled.
    """

    pin_entered = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._boxes = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        font = QFont()
        font.setPointSize(18)
        font.setBold(True)

        for i in range(6):
            box = QLineEdit()
            box.setMaxLength(1)
            box.setAlignment(Qt.AlignCenter)
            box.setFont(font)
            box.setEchoMode(QLineEdit.Password)
            box.setFixedSize(42, 48)
            box.setStyleSheet(
                "border: 2px solid #aaa; border-radius: 4px; background: #fafafa;"
            )
            box.textChanged.connect(lambda text, idx=i: self._on_text_changed(text, idx))
            box.installEventFilter(self)
            self._boxes.append(box)
            layout.addWidget(box)

    def _on_text_changed(self, text: str, idx: int):
        if text:
            # Advance to next box
            if idx < 5:
                self._boxes[idx + 1].setFocus()
        # Check completion
        pin = self.get_pin()
        if len(pin) == 6:
            self.pin_entered.emit(pin)

    def eventFilter(self, obj, event):
        from PySide2.QtCore import QEvent
        from PySide2.QtGui import QKeyEvent
        if event.type() == QEvent.KeyPress:
            if isinstance(event, QKeyEvent):
                if event.key() == Qt.Key_Backspace:
                    # Find which box and go back
                    for i, box in enumerate(self._boxes):
                        if box is obj and i > 0 and not box.text():
                            self._boxes[i - 1].setFocus()
                            self._boxes[i - 1].clear()
                            return True
        return super().eventFilter(obj, event)

    def get_pin(self) -> str:
        return "".join(b.text() for b in self._boxes)

    def clear(self):
        for box in self._boxes:
            box.clear()
        if self._boxes:
            self._boxes[0].setFocus()

    def set_enabled(self, enabled: bool):
        for box in self._boxes:
            box.setEnabled(enabled)
