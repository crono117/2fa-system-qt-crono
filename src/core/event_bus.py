"""
Event Bus for application-wide event handling.

Provides a centralized pub/sub mechanism for decoupled component communication.
"""
from typing import Dict, List, Callable, Any
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """
    Centralized event bus for application-wide communication.

    Implements the Observer pattern for loosely coupled components.
    Thread-safe for multi-threaded Tkinter applications.
    """

    def __init__(self):
        """Initialize the event bus."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = Lock()

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: The type of event to subscribe to
            callback: Function to call when event is published
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []

            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                logger.debug(f"Subscribed to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: The type of event to unsubscribe from
            callback: The callback to remove
        """
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
                    logger.debug(f"Unsubscribed from event: {event_type}")

                    # Clean up empty subscriber lists
                    if not self._subscribers[event_type]:
                        del self._subscribers[event_type]

    def publish(self, event_type: str, data: Any = None) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event_type: The type of event to publish
            data: Optional data to pass to subscribers
        """
        with self._lock:
            subscribers = self._subscribers.get(event_type, []).copy()

        logger.debug(f"Publishing event: {event_type} to {len(subscribers)} subscribers")

        for callback in subscribers:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

    def clear_subscribers(self, event_type: str = None) -> None:
        """
        Clear subscribers for a specific event type or all events.

        Args:
            event_type: Specific event type to clear, or None to clear all
        """
        with self._lock:
            if event_type:
                if event_type in self._subscribers:
                    del self._subscribers[event_type]
                    logger.debug(f"Cleared subscribers for: {event_type}")
            else:
                self._subscribers.clear()
                logger.debug("Cleared all event subscribers")

    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get the number of subscribers for an event type.

        Args:
            event_type: The event type to check

        Returns:
            Number of subscribers
        """
        with self._lock:
            return len(self._subscribers.get(event_type, []))


# Global event bus instance
event_bus = EventBus()


# Common event types
class EventTypes:
    """Standard event types used across the application."""

    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGOUT = "auth.logout"
    SESSION_EXPIRED = "auth.session.expired"
    TOKEN_REFRESHED = "auth.token.refreshed"

    # Verification events
    VERIFICATION_STARTED = "verification.started"
    VERIFICATION_COMPLETED = "verification.completed"
    VERIFICATION_FAILED = "verification.failed"
    VERIFICATION_STATUS_UPDATED = "verification.status.updated"
    PIN_SENT = "verification.pin.sent"

    # WebSocket events
    WS_CONNECTED = "websocket.connected"
    WS_DISCONNECTED = "websocket.disconnected"
    WS_MESSAGE_RECEIVED = "websocket.message.received"
    WS_ERROR = "websocket.error"

    # UI events
    UI_STATE_CHANGED = "ui.state.changed"
    TAB_CHANGED = "ui.tab.changed"
    THEME_CHANGED = "ui.theme.changed"

    # Error events
    API_ERROR = "error.api"
    NETWORK_ERROR = "error.network"
    VALIDATION_ERROR = "error.validation"