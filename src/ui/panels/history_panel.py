"""
History panel — QTableView with auto-refresh and CSV export.
"""
import csv
from typing import Optional, Dict, Any

from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView,
    QLabel, QDialog, QTextEdit, QFileDialog, QMessageBox, QHeaderView,
    QAbstractItemView, QSizePolicy,
)
from PySide2.QtCore import Qt, QTimer, QThreadPool, QSortFilterProxyModel

from models.history_table_model import HistoryTableModel
from services.verification_service import verification_service
from core.app_signals import app_signals
from utils.threading_utils import ApiWorker
from config.settings import settings
from utils.logger import logger


class HistoryPanel(QWidget):
    """
    Verification history with:
    - QTimer auto-refresh every 30 seconds
    - Double-click → detail dialog
    - Export to CSV
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._records = []
        self._setup_ui()
        self._setup_timer()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setFixedWidth(80)
        self._refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self._refresh_btn)

        self._export_btn = QPushButton("Export CSV")
        self._export_btn.setFixedWidth(90)
        self._export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(self._export_btn)

        toolbar.addStretch()

        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: gray; font-size: 11px;")
        toolbar.addWidget(self._count_label)

        layout.addLayout(toolbar)

        # Table
        self._model = HistoryTableModel(self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self._table)

        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._status_label)

    def _setup_timer(self):
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(settings.HISTORY_REFRESH_INTERVAL * 1000)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def refresh(self):
        self._status_label.setText("Loading…")
        self._refresh_btn.setEnabled(False)
        worker = ApiWorker(verification_service.get_authentication_history, 100)
        worker.signals.result.connect(self._on_data_loaded)
        worker.signals.error.connect(self._on_load_error)
        QThreadPool.globalInstance().start(worker)

    def _on_data_loaded(self, response):
        self._refresh_btn.setEnabled(True)
        if response.success:
            data = response.data or {}
            records = data.get('results', [])
            self._records = records
            self._model.set_records(records)
            count = len(records)
            self._count_label.setText(f"{count} record{'s' if count != 1 else ''}")
            self._status_label.setText("")
        else:
            self._status_label.setText(f"Failed to load: {response.error}")

    def _on_load_error(self, error_msg: str):
        self._refresh_btn.setEnabled(True)
        self._status_label.setText(f"Error: {error_msg}")

    def _on_row_double_clicked(self, proxy_index):
        source_index = self._proxy.mapToSource(proxy_index)
        record = self._model.get_record(source_index.row())
        if record:
            self._show_detail_dialog(record)

    def _show_detail_dialog(self, record: Dict[str, Any]):
        dlg = QDialog(self)
        dlg.setWindowTitle("Verification Record")
        dlg.resize(480, 400)

        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)

        lines = []
        for key, value in record.items():
            lines.append(f"{key}: {value}")

        text.setPlainText("\n".join(lines))
        layout.addWidget(text)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

        dlg.exec_()

    def _export_csv(self):
        if not self._records:
            QMessageBox.information(self, "Export", "No records to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export History",
            "verification_history.csv",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                if self._records:
                    writer = csv.DictWriter(f, fieldnames=self._records[0].keys())
                    writer.writeheader()
                    writer.writerows(self._records)
            QMessageBox.information(self, "Export", f"Exported {len(self._records)} records.")
            logger.info(f"History exported to {file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
            logger.error(f"Export failed: {exc}")
