"""
QAbstractTableModel for the merchant search QTableView.

Two columns: DBA Name (col 0) and MID (col 1).
UserRole on any cell returns the full merchant dict.
"""
from typing import List, Dict, Any

from PySide2.QtCore import QAbstractTableModel, Qt, QModelIndex


class MerchantListModel(QAbstractTableModel):
    """
    Drives the QTableView in MerchantSearchWidget.

    Columns:
      0 — DBA Name
      1 — MID (back_end_mid)

    UserRole on any column returns the raw merchant dict.
    """

    HEADERS = ["DBA Name", "MID"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._merchants: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # QAbstractTableModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._merchants)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 2

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._merchants):
            return None

        merchant = self._merchants[index.row()]

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return merchant.get('dba', merchant.get('name', 'Unknown'))
            if index.column() == 1:
                return merchant.get('back_end_mid') or '—'

        if role == Qt.TextAlignmentRole:
            if index.column() == 1:
                return Qt.AlignRight | Qt.AlignVCenter

        if role == Qt.UserRole:
            return merchant

        if role == Qt.ToolTipRole:
            name = merchant.get('dba', '')
            mid = merchant.get('back_end_mid', 'N/A')
            phone = merchant.get('contact_phone', 'N/A')
            email = merchant.get('contact_email', 'N/A')
            uuid = merchant.get('merchant_id', 'N/A')
            return f"{name}\nMID: {mid}\nPhone: {phone}\nEmail: {email}\nUUID: {uuid}"

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section] if section < len(self.HEADERS) else None
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_merchants(self, merchants: List[Dict[str, Any]]) -> None:
        """Replace the entire list and notify the view."""
        self.beginResetModel()
        self._merchants = list(merchants)
        self.endResetModel()

    def clear(self) -> None:
        """Clear all items."""
        self.set_merchants([])

    def get_merchant(self, row: int) -> Dict[str, Any]:
        """Return merchant dict at the given row index."""
        if 0 <= row < len(self._merchants):
            return self._merchants[row]
        return {}
