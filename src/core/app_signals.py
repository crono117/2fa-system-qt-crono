"""
Central Qt signal hub for the PySide2 frontend.

All cross-component communication goes through this singleton
instead of Tkinter callback-passing patterns.
"""
from PySide2.QtCore import QObject, Signal


class AppSignals(QObject):
    """
    Singleton signal hub — emit from any thread, connect slots in main thread.

    Qt's signal/slot mechanism ensures slot calls are delivered on the
    receiver's thread, so worker threads can safely emit these signals.
    """

    # Authentication
    login_success = Signal(dict)       # user_data dict
    logout_requested = Signal()
    session_expired = Signal()
    token_refreshed = Signal()

    # Verification lifecycle
    verification_completed = Signal(bool, str, str)  # success, message, auth_id
    pin_sent = Signal(str)             # auth_id
    sms_sent = Signal(str)             # session_id

    # Merchant selection
    merchant_selected = Signal(dict)   # merchant data dict
    merchant_search_cleared = Signal() # resets search widget after verification (Bug 3 fix)

    # WebSocket real-time updates
    ws_connected = Signal()
    ws_disconnected = Signal()
    ws_verification_update = Signal(dict)   # raw message dict from backend

    # Panel reset
    reset_all_panels = Signal()

    # Status bar
    status_message = Signal(str, str)  # message, level ('info'|'success'|'warning'|'error')


# Global singleton — import this everywhere
app_signals = AppSignals()
