"""
Merchant search widget — shared by SMS and Email panels.

Emits merchant_selected (dict) via app_signals when user selects a result.
Emits merchant_search_cleared (no args) after verification resets it (Bug 3 fix).

Handles debounced search via QTimer + ApiWorker.
"""
from typing import Optional, Dict, Any

from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTableView, QLabel,
    QPushButton, QSizePolicy, QAbstractItemView, QHeaderView,
)
from PySide2.QtCore import Qt, QTimer, QThreadPool

from models.merchant_list_model import MerchantListModel
from services.merchant_service import merchant_service
from core.app_signals import app_signals
from utils.threading_utils import ApiWorker
from utils.logger import logger


class MerchantSearchWidget(QWidget):
    """
    Debounced merchant search + selection widget.

    Layout:
      [Search field]  [Clear ✕]
      [QListView with results]
      [Selected: <name>]
    """

    _DEBOUNCE_MS = 350   # wait this long after last keystroke before searching

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._selected_merchant: Optional[Dict[str, Any]] = None
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._do_search)

        self._model = MerchantListModel(self)
        self._setup_ui()
        self._wire_signals()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Search row
        search_row = QHBoxLayout()
        search_row.setSpacing(4)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search merchant (name, MID, email, phone)…")
        self._search_input.setClearButtonEnabled(True)
        search_row.addWidget(self._search_input)

        layout.addLayout(search_row)

        # Results table — two visible columns: DBA Name | MID
        self._list_view = QTableView()
        self._list_view.setModel(self._model)
        self._list_view.setMaximumHeight(200)
        self._list_view.setVisible(False)
        self._list_view.setAlternatingRowColors(True)
        self._list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._list_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list_view.verticalHeader().setVisible(False)
        self._list_view.setShowGrid(False)
        # DBA column stretches; MID column sized to content
        self._list_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._list_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._list_view.horizontalHeader().setHighlightSections(False)
        self._list_view.verticalHeader().setDefaultSectionSize(24)
        layout.addWidget(self._list_view)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._status_label)

        # Selected merchant display
        self._selected_label = QLabel("No merchant selected")
        self._selected_label.setStyleSheet("font-weight: bold; padding: 4px;")
        self._selected_label.setWordWrap(True)
        layout.addWidget(self._selected_label)

    def _wire_signals(self):
        self._search_input.textChanged.connect(self._on_text_changed)
        self._list_view.activated.connect(self._on_item_activated)
        self._list_view.clicked.connect(self._on_item_activated)

        # External reset signal (Bug 3 fix)
        app_signals.merchant_search_cleared.connect(self.reset)
        app_signals.reset_all_panels.connect(self.reset)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_text_changed(self, text: str):
        if len(text) < 2:
            self._model.clear()
            self._list_view.setVisible(False)
            self._status_label.setText("")
            return
        # Debounce
        self._debounce_timer.start(self._DEBOUNCE_MS)

    def _do_search(self):
        query = self._search_input.text().strip()
        if len(query) < 2:
            return
        self._status_label.setText("Searching…")
        worker = ApiWorker(merchant_service.search_merchants, query)
        worker.signals.result.connect(self._on_search_result)
        worker.signals.error.connect(self._on_search_error)
        QThreadPool.globalInstance().start(worker)

    def _on_search_result(self, results):
        self._model.set_merchants(results)
        count = len(results)
        if count:
            self._list_view.setVisible(True)
            self._status_label.setText(f"{count} result{'s' if count != 1 else ''} found")
        else:
            self._list_view.setVisible(False)
            self._status_label.setText("No merchants found")

    def _on_search_error(self, error_msg: str):
        self._list_view.setVisible(False)
        self._status_label.setText(f"Search error: {error_msg}")
        logger.error(f"MerchantSearch error: {error_msg}")

    def _on_item_activated(self, index):
        merchant = self._model.get_merchant(index.row())
        if not merchant:
            return
        self._selected_merchant = merchant
        self._list_view.setVisible(False)
        name = merchant.get('dba', 'Unknown')
        mid = merchant.get('back_end_mid', 'N/A')
        self._selected_label.setText(f"Selected: {name} [{mid}]")
        self._status_label.setText("")
        logger.info(f"Merchant selected: {name} (UUID: {merchant.get('merchant_id')})")
        app_signals.merchant_selected.emit(merchant)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self):
        """Clear search, selection, and list.  Called after verification completes."""
        self._debounce_timer.stop()
        self._search_input.clear()
        self._model.clear()
        self._list_view.setVisible(False)
        self._selected_merchant = None
        self._selected_label.setText("No merchant selected")
        self._status_label.setText("")
        logger.debug("MerchantSearchWidget reset")

    def get_selected_merchant(self) -> Optional[Dict[str, Any]]:
        return self._selected_merchant

    def has_selection(self) -> bool:
        return self._selected_merchant is not None
