#!/usr/bin/env python
"""
Keyboard Shortcuts Manager for CurveEditor.

This module provides a centralized way to manage keyboard shortcuts for the
application, supporting file operations, view operations, and edit operations.
"""

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget

logger = logging.getLogger("keyboard_shortcuts")


class ShortcutManager(QObject):
    """
    Manages keyboard shortcuts for the CurveEditor application.

    This class provides a centralized way to define, register, and manage
    keyboard shortcuts throughout the application lifecycle.
    """

    # Signals for shortcut activation
    shortcut_activated = Signal(str)  # Emits shortcut name when activated

    def __init__(self, parent: QWidget | None = None):
        """
        Initialize the shortcut manager.

        Args:
            parent: Parent widget for the shortcuts (typically MainWindow)
        """
        super().__init__(parent)
        self.parent_widget = parent
        self.shortcuts: dict[str, QShortcut] = {}
        self._setup_default_shortcuts()

        logger.info("ShortcutManager initialized")

    def _setup_default_shortcuts(self) -> None:
        """Setup default keyboard shortcuts for the application."""
        if not self.parent_widget:
            logger.warning("No parent widget provided, shortcuts will not be functional")
            return

        # Define default shortcuts
        # NOTE: Single keys like C, F, arrow keys are handled directly by CurveViewWidget
        # to avoid conflicts with widget-specific keyboard handling
        default_shortcuts = {
            # File operations
            "new_file": ("Ctrl+N", self._on_new_file),
            "open_file": ("Ctrl+O", self._on_open_file),
            "save_file": ("Ctrl+S", self._on_save_file),
            "save_as": ("Ctrl+Shift+S", self._on_save_as),
            "load_images": ("Ctrl+I", self._on_load_images),
            "export_data": ("Ctrl+E", self._on_export_data),
            "quit": ("Ctrl+Q", self._on_quit),
            # Edit operations
            "undo": ("Ctrl+Z", self._on_undo),
            "redo": ("Ctrl+Y", self._on_redo),
            "add_point": ("Ctrl+A", self._on_add_point),
            # "delete_point": ("Delete", self._on_delete_point),  # Handled by CurveViewWidget
            "select_all": ("Ctrl+Shift+A", self._on_select_all),
            # View operations
            "zoom_in": ("Ctrl++", self._on_zoom_in),
            "zoom_out": ("Ctrl+-", self._on_zoom_out),
            "zoom_fit": ("Ctrl+0", self._on_zoom_fit),
            # "fit_image": ("F", self._on_fit_image),  # Handled by CurveViewWidget
            "reset_view": ("Ctrl+R", self._on_reset_view),
            # "center_view": ("Ctrl+C", self._on_center_view),  # Removed to avoid conflict
            # Curve operations
            "smooth_curve": ("Ctrl+M", self._on_smooth_curve),
            "filter_curve": ("Ctrl+F", self._on_filter_curve),
            "analyze_curve": ("Ctrl+L", self._on_analyze_curve),
            # Navigation - Primary shortcuts use arrow keys, Alt+Arrow as secondary
            "next_frame": ("Right", self._on_next_frame),
            "prev_frame": ("Left", self._on_prev_frame),
            "next_frame_alt": ("Alt+Right", self._on_next_frame),
            "prev_frame_alt": ("Alt+Left", self._on_prev_frame),
            "first_frame": ("Home", self._on_first_frame),
            "last_frame": ("End", self._on_last_frame),
            # Playback controls
            "oscillate_playback": ("Space", self._on_oscillate_playback),
        }

        # Register all default shortcuts
        for name, (key_sequence, callback) in default_shortcuts.items():
            self.register_shortcut(name, key_sequence, callback)

    def register_shortcut(self, name: str, key_sequence: str, callback: Callable[[], None]) -> bool:
        """
        Register a new keyboard shortcut.

        Args:
            name: Unique name for the shortcut
            key_sequence: Key sequence string (e.g., "Ctrl+S")
            callback: Function to call when shortcut is activated

        Returns:
            True if shortcut was registered successfully, False otherwise
        """
        if not self.parent_widget:
            logger.error(f"Cannot register shortcut '{name}': no parent widget")
            return False

        try:
            # Create the shortcut
            shortcut = QShortcut(QKeySequence(key_sequence), self.parent_widget)
            shortcut.activated.connect(callback)
            shortcut.activated.connect(lambda: self.shortcut_activated.emit(name))

            # Store the shortcut
            if name in self.shortcuts:
                logger.warning(f"Overriding existing shortcut: {name}")
                self.shortcuts[name].deleteLater()

            self.shortcuts[name] = shortcut
            logger.debug(f"Registered shortcut: {name} -> {key_sequence}")
            return True

        except Exception as e:
            logger.error(f"Failed to register shortcut '{name}': {e}")
            return False

    def unregister_shortcut(self, name: str) -> bool:
        """
        Remove a keyboard shortcut.

        Args:
            name: Name of the shortcut to remove

        Returns:
            True if shortcut was removed successfully, False otherwise
        """
        if name not in self.shortcuts:
            logger.warning(f"Shortcut '{name}' not found for removal")
            return False

        try:
            self.shortcuts[name].deleteLater()
            del self.shortcuts[name]
            logger.debug(f"Unregistered shortcut: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister shortcut '{name}': {e}")
            return False

    def get_shortcut(self, name: str) -> QShortcut | None:
        """
        Get a shortcut by name.

        Args:
            name: Name of the shortcut

        Returns:
            QShortcut object if found, None otherwise
        """
        return self.shortcuts.get(name)

    def get_all_shortcuts(self) -> dict[str, str]:
        """
        Get all registered shortcuts as name -> key sequence mapping.

        Returns:
            Dictionary mapping shortcut names to key sequences
        """
        result = {}
        for name, shortcut in self.shortcuts.items():
            result[name] = shortcut.key().toString()
        return result

    def enable_shortcut(self, name: str, enabled: bool = True) -> bool:
        """
        Enable or disable a specific shortcut.

        Args:
            name: Name of the shortcut
            enabled: True to enable, False to disable

        Returns:
            True if operation was successful, False otherwise
        """
        shortcut = self.get_shortcut(name)
        if not shortcut:
            logger.warning(f"Shortcut '{name}' not found for enable/disable")
            return False

        shortcut.setEnabled(enabled)
        logger.debug(f"Shortcut '{name}' {'enabled' if enabled else 'disabled'}")
        return True

    def enable_all_shortcuts(self, enabled: bool = True) -> None:
        """
        Enable or disable all shortcuts.

        Args:
            enabled: True to enable all, False to disable all
        """
        for shortcut in self.shortcuts.values():
            shortcut.setEnabled(enabled)
        logger.info(f"All shortcuts {'enabled' if enabled else 'disabled'}")

    # Default shortcut handlers - these emit signals that the main window can connect to

    def _on_new_file(self) -> None:
        """Handle new file shortcut."""
        logger.debug("New file shortcut activated")
        # Implementation will be handled by main window signal connections

    def _on_open_file(self) -> None:
        """Handle open file shortcut."""
        logger.debug("Open file shortcut activated")

    def _on_save_file(self) -> None:
        """Handle save file shortcut."""
        logger.debug("Save file shortcut activated")

    def _on_save_as(self) -> None:
        """Handle save as shortcut."""
        logger.debug("Save as shortcut activated")

    def _on_load_images(self) -> None:
        """Handle load images shortcut."""
        logger.debug("Load images shortcut activated")

    def _on_export_data(self) -> None:
        """Handle export data shortcut."""
        logger.debug("Export data shortcut activated")

    def _on_quit(self) -> None:
        """Handle quit shortcut."""
        logger.debug("Quit shortcut activated")

    def _on_undo(self) -> None:
        """Handle undo shortcut."""
        logger.debug("Undo shortcut activated")

    def _on_redo(self) -> None:
        """Handle redo shortcut."""
        logger.debug("Redo shortcut activated")

    def _on_add_point(self) -> None:
        """Handle add point shortcut."""
        logger.debug("Add point shortcut activated")

    def _on_delete_point(self) -> None:
        """Handle delete point shortcut."""
        logger.debug("Delete point shortcut activated")

    def _on_select_all(self) -> None:
        """Handle select all shortcut."""
        logger.debug("Select all shortcut activated")

    def _on_zoom_in(self) -> None:
        """Handle zoom in shortcut."""
        logger.debug("Zoom in shortcut activated")

    def _on_zoom_out(self) -> None:
        """Handle zoom out shortcut."""
        logger.debug("Zoom out shortcut activated")

    def _on_zoom_fit(self) -> None:
        """Handle zoom fit shortcut."""
        logger.debug("Zoom fit shortcut activated")

    def _on_fit_image(self) -> None:
        """Handle fit image shortcut (F key)."""
        logger.debug("Fit image shortcut activated")
        # Access the curve widget through parent (MainWindow)
        if hasattr(self.parent_widget, "curve_widget") and self.parent_widget.curve_widget:
            self.parent_widget.curve_widget.fit_to_background_image()

    def _on_reset_view(self) -> None:
        """Handle reset view shortcut."""
        logger.debug("Reset view shortcut activated")

    def _on_center_view(self) -> None:
        """Handle center view shortcut."""
        logger.debug("Center view shortcut activated")

    def _on_smooth_curve(self) -> None:
        """Handle smooth curve shortcut."""
        logger.debug("Smooth curve shortcut activated")

    def _on_filter_curve(self) -> None:
        """Handle filter curve shortcut."""
        logger.debug("Filter curve shortcut activated")

    def _on_analyze_curve(self) -> None:
        """Handle analyze curve shortcut."""
        logger.debug("Analyze curve shortcut activated")

    def _on_next_frame(self) -> None:
        """Handle next frame shortcut."""
        logger.debug("Next frame shortcut activated")
        # Trigger frame navigation through parent widget
        if hasattr(self.parent_widget, "_on_next_frame"):
            self.parent_widget._on_next_frame()

    def _on_prev_frame(self) -> None:
        """Handle previous frame shortcut."""
        logger.debug("Previous frame shortcut activated")
        # Trigger frame navigation through parent widget
        if hasattr(self.parent_widget, "_on_prev_frame"):
            self.parent_widget._on_prev_frame()

    def _on_first_frame(self) -> None:
        """Handle first frame shortcut."""
        logger.debug("First frame shortcut activated")
        # Trigger frame navigation through parent widget
        if hasattr(self.parent_widget, "_on_first_frame"):
            self.parent_widget._on_first_frame()

    def _on_last_frame(self) -> None:
        """Handle last frame shortcut."""
        logger.debug("Last frame shortcut activated")
        # Trigger frame navigation through parent widget
        if hasattr(self.parent_widget, "_on_last_frame"):
            self.parent_widget._on_last_frame()

    def _on_oscillate_playback(self) -> None:
        """Handle oscillating playback toggle shortcut (spacebar)."""
        logger.debug("Oscillating playback toggle shortcut activated")
        # Trigger oscillating playback through parent widget
        if hasattr(self.parent_widget, "_toggle_oscillating_playback"):
            self.parent_widget._toggle_oscillating_playback()
