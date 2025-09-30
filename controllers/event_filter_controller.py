"""Event filter controller for managing key event redirection.

This controller handles special key event filtering and redirection,
particularly for the C key used in curve editing operations.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class EventFilterController:
    """Controller for event filtering operations."""

    def __init__(self, main_window: "MainWindow"):
        """Initialize the event filter controller.

        Args:
            main_window: Reference to the main window
        """
        self.main_window = main_window  # Type inferred as MainWindow (compatible with MainWindowProtocol)

    def filter_event(self, watched: QObject, event: QEvent) -> bool:
        """Filter and handle key events for special processing.

        Args:
            watched: The object that received the event
            event: The event to filter

        Returns:
            True if event was handled, False to pass through
        """
        if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            key = event.key()
            logger.debug(f"[EVENT_FILTER] KeyPress detected: key={key}, object={watched.__class__.__name__}")

            # Handle C key specifically without modifiers
            if key == Qt.Key.Key_C and not event.modifiers():
                # If C key pressed on curve widget, let it handle normally
                if watched == self.main_window.curve_widget:
                    logger.debug("[EVENT_FILTER] C key on curve_widget, passing through")
                    return False  # Let it pass through

                # If C key pressed elsewhere, redirect to curve widget
                elif watched != self.main_window.curve_widget and self.main_window.curve_widget:
                    logger.debug("[EVENT_FILTER] Redirecting C key to curve_widget")
                    self.main_window.curve_widget.setFocus()  # pyright: ignore[reportAttributeAccessIssue]
                    QApplication.sendEvent(self.main_window.curve_widget, event)  # pyright: ignore[reportArgumentType]
                    return True  # Consume original event to prevent double handling

        return False  # Let other events pass through
