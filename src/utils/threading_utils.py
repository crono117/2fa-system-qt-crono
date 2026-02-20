"""
Qt threading utilities — QRunnable/ApiWorker pattern.

Replaces all threading.Thread + root.after() usage from the Tkinter frontend.
Worker threads emit signals that Qt delivers safely on the main thread.
"""
from typing import Callable, Any

from PySide2.QtCore import QRunnable, QObject, Signal, Slot


class WorkerSignals(QObject):
    """Signals emitted by ApiWorker (must live in a QObject)."""

    result = Signal(object)   # successful return value
    error = Signal(str)       # error message string
    finished = Signal()       # always emitted last


class ApiWorker(QRunnable):
    """
    Generic QRunnable for background API calls.

    Usage::

        worker = ApiWorker(merchant_service.search_merchants, query)
        worker.signals.result.connect(self._on_search_result)
        worker.signals.error.connect(self._on_search_error)
        QThreadPool.globalInstance().start(worker)

    The result/error slots run on the main thread — no after() needed.
    """

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        # Keep alive until signals are delivered
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()
