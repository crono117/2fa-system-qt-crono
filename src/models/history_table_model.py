"""
QAbstractTableModel for the authentication history QTableView.
"""
from typing import List, Dict, Any, Optional

from PySide2.QtCore import QAbstractTableModel, Qt, QModelIndex

from utils.formatters import format_datetime, format_boolean


COLUMNS = [
    ("Date / Time",      "authenticated_at"),
    ("Method",           "authentication_method"),
    ("Merchant ID",      "merchant_id"),
    ("Success",          "success"),
    ("Auth ID",          "auth_id"),
    ("Staff User",       "staff_user_id"),
]


class HistoryTableModel(QAbstractTableModel):
    """
    Drives the QTableView in HistoryPanel.

    Each row is a verification history record dict from the API.
    Double-click signals are handled by the view; fetch raw record via get_record().
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._records: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # QAbstractTableModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return COLUMNS[section][0]
        return str(section + 1)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._records):
            return None

        record = self._records[index.row()]
        col_label, field_key = COLUMNS[index.column()]

        if role == Qt.DisplayRole:
            value = record.get(field_key)

            if field_key == "authenticated_at":
                return format_datetime(value) if value else "N/A"

            if field_key == "success":
                return "Yes" if value else "No"

            if field_key == "authentication_method":
                method_map = {'email': 'Email', 'sms': 'SMS', 'totp': 'TOTP'}
                return method_map.get(str(value).lower(), str(value)) if value else "N/A"

            if field_key == "auth_id" and value:
                # Truncate UUID for display
                return f"{str(value)[:8]}..."

            return str(value) if value is not None else "N/A"

        if role == Qt.UserRole:
            return record

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_records(self, records: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._records = list(records)
        self.endResetModel()

    def clear(self) -> None:
        self.set_records([])

    def get_record(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._records):
            return self._records[row]
        return None
