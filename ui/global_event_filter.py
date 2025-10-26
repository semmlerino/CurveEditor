#!/usr/bin/env python
"""
Application-level event filter for global keyboard shortcuts.

This module provides an event filter that intercepts keyboard events at the
application level, enabling global keyboard shortcuts that work regardless
of which widget has focus.
"""
# pyright: reportImportCycles=false

from __future__ import annotations

from typing import TYPE_CHECKING, override

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent

if TYPE_CHECKING:
    from ui.main_window import MainWindow
    from ui.shortcut_registry import ShortcutRegistry

from core.commands.shortcut_command import ShortcutContext
from core.logger_utils import get_logger

logger = get_logger("global_event_filter")


class GlobalEventFilter(QObject):
    """Application-level event filter for keyboard shortcuts.

    Intercepts keyboard events before they reach individual widgets,
    allowing for consistent global shortcut handling throughout the application.
    """

    def __init__(self, main_window: MainWindow, registry: ShortcutRegistry) -> None:
        """Initialize the global event filter.

        Args:
            main_window: Reference to the main application window
            registry: The shortcut registry to use for command lookup
        """
        super().__init__()
        self.main_window: MainWindow = main_window
        self.registry: ShortcutRegistry = registry
        logger.info("GlobalEventFilter initialized")

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Filter events for the application.

        Args:
            watched: The object that would normally receive the event
            event: The event to filter

        Returns:
            True if the event was handled and should be filtered out,
            False to allow normal event processing to continue
        """
        # Only handle key press events
        if event.type() != QEvent.Type.KeyPress:
            return False

        # Ensure it's a QKeyEvent
        if not isinstance(event, QKeyEvent):
            return False

        # Handle Page Up/Down for keyframe navigation (check before skipping widgets)
        key = event.key()
        if key == Qt.Key.Key_PageUp or key == Qt.Key.Key_PageDown:
            logger.debug(f"[GLOBAL_EVENT_FILTER] KeyPress: key={key}, watching {watched.__class__.__name__}")
            if key == Qt.Key.Key_PageUp:
                logger.debug("[GLOBAL_EVENT_FILTER] Page Up pressed, navigating to previous keyframe")
                self.main_window.navigate_to_prev_keyframe()
            else:
                logger.debug("[GLOBAL_EVENT_FILTER] Page Down pressed, navigating to next keyframe")
                self.main_window.navigate_to_next_keyframe()
            event.accept()
            return True

        # Don't interfere with text input in certain widgets
        if self._should_skip_widget(watched):
            return False

        # Build context for the shortcut
        try:
            context = self._build_context(event, watched)
        except Exception as e:
            logger.error(f"Failed to build shortcut context: {e}")
            return False

        # Look up command in registry
        command = self.registry.get_command(event)
        if not command:
            # No command registered for this key
            return False

        # Check if command can execute in this context
        if not command.can_execute(context):
            logger.debug(
                f"Shortcut [{command.key_sequence}] cannot execute in current context (widget: {context.widget_type})"
            )
            return False

        # Execute the command
        try:
            success = command.execute(context)
            command.log_execution(context, success)

            if success:
                # Event was handled, stop propagation
                event.accept()
                return True
            else:
                # Command failed, let event continue
                return False

        except Exception as e:
            logger.error(f"Error executing shortcut [{command.key_sequence}]: {e}")
            return False

    def _build_context(self, event: QKeyEvent, watched: QObject) -> ShortcutContext:
        """Build a context object for shortcut execution.

        Args:
            event: The key event that triggered the shortcut
            watched: The object that would normally receive the event

        Returns:
            Context object with current application state
        """
        from PySide6.QtWidgets import QApplication, QWidget

        # Get focused widget
        focused_widget = None
        if isinstance(watched, QWidget):
            focused_widget = watched
        else:
            # Try to get the currently focused widget
            app = QApplication.instance()
            if app and isinstance(app, QApplication):
                focused_widget = app.focusWidget()

        # Get selected curve points
        selected_curve_points = set()
        if self.main_window.curve_widget is not None:
            selected_curve_points = self.main_window.curve_widget.selected_indices

        # Get selected tracking points - UNIFIED SELECTION STATE
        # Selection synchronization is now handled by proper signal connections
        # in MultiPointTrackingController, not during shortcut context building
        selected_tracking_points = []
        tracking_panel = getattr(self.main_window, "tracking_panel", None)
        if tracking_panel is not None:
            selected_tracking_points = tracking_panel.get_selected_points()

        # Get current frame
        current_frame = None
        if getattr(self.main_window, "current_frame", None) is not None:
            current_frame = self.main_window.current_frame

        return ShortcutContext(
            main_window=self.main_window,
            focused_widget=focused_widget,
            key_event=event,
            selected_curve_points=selected_curve_points,
            selected_tracking_points=selected_tracking_points,
            current_frame=current_frame,
        )

    def _should_skip_widget(self, obj: QObject) -> bool:
        """Check if we should skip shortcut processing for this widget.

        Some widgets need normal key handling for text input and shouldn't
        have their events intercepted.

        Args:
            obj: The object to check

        Returns:
            True if shortcuts should be skipped for this widget
        """
        from PySide6.QtWidgets import QDoubleSpinBox, QLineEdit, QPlainTextEdit, QSpinBox, QTextEdit

        # Skip text input widgets when they have focus
        skip_types = (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox)

        if isinstance(obj, skip_types):
            # Check if the widget is in edit mode
            if obj.hasFocus():
                return True

        # Check for combo box dropdown
        from PySide6.QtWidgets import QComboBox

        return bool(isinstance(obj, QComboBox) and obj.isEditable())
