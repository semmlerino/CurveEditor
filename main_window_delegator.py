#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main Window Delegator for Curve Editor.

This module provides a delegator class that handles all method delegations
for MainWindow, keeping the MainWindow class small and focused.
"""

from typing import TYPE_CHECKING, Any, List

from main_window_operations import MainWindowOperations
from main_window_smoothing import SmoothingOperations
from services.logging_service import LoggingService

if TYPE_CHECKING:
    from main_window import MainWindow

logger = LoggingService.get_logger("main_window_delegator")


class MainWindowDelegator:
    """Delegates operations for MainWindow to keep it under 300 lines."""

    def __init__(self, main_window: 'MainWindow'):
        """Initialize the delegator with a reference to the main window.

        Args:
            main_window: The MainWindow instance
        """
        self.window = main_window

    # View operations
    def set_centering_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-centering of the view."""
        MainWindowOperations.set_centering_enabled(self.window, enabled)

    def enable_point_controls(self, enabled: bool) -> None:
        """Enable or disable point editing controls."""
        MainWindowOperations.enable_point_controls(self.window, enabled)

    # Image operations
    def set_image_sequence(self, path: str, filenames: List[str]) -> None:
        """Set the current image sequence."""
        MainWindowOperations.set_image_sequence(self.window, path, filenames)

    def update_image_label(self) -> None:
        """Update image label."""
        MainWindowOperations.update_image_label(self.window)

    # File operations
    def load_track_data(self) -> None:
        """Load track data."""
        MainWindowOperations.load_track_data(self.window)

    def add_track_data(self) -> None:
        """Add track data."""
        MainWindowOperations.add_track_data(self.window)

    def save_track_data(self) -> None:
        """Save track data."""
        MainWindowOperations.save_track_data(self.window)

    def load_image_sequence(self) -> None:
        """Load image sequence."""
        MainWindowOperations.load_image_sequence(self.window)

    # Timeline operations
    def setup_timeline(self) -> None:
        """Setup timeline slider."""
        MainWindowOperations.setup_timeline(self.window)

    # Point editing operations
    def on_point_selected(self, idx: int) -> None:
        """Handle point selection."""
        MainWindowOperations.on_point_selected(self.window, idx)

    def on_point_moved(self, idx: int, x: float, y: float) -> None:
        """Handle point moved."""
        MainWindowOperations.on_point_moved(self.window, idx, x, y)

    def update_point_info(self, idx: int, x: float, y: float) -> None:
        """Update point information."""
        MainWindowOperations.update_point_info(self.window, idx, x, y)

    # Dialog operations
    def show_shortcuts_dialog(self) -> None:
        """Show shortcuts dialog."""
        MainWindowOperations.show_shortcuts_dialog(self.window)

    def show_filter_dialog(self) -> None:
        """Show filter dialog."""
        MainWindowOperations.show_filter_dialog(self.window)

    def show_fill_gaps_dialog(self) -> None:
        """Show fill gaps dialog."""
        MainWindowOperations.show_fill_gaps_dialog(self.window)

    def show_extrapolate_dialog(self) -> None:
        """Show extrapolate dialog."""
        MainWindowOperations.show_extrapolate_dialog(self.window)

    def fill_gap(self, start_frame: int, end_frame: int, method_index: int, preserve_endpoints: bool = True) -> None:
        """Fill gap in curve data."""
        MainWindowOperations.fill_gap(self.window, start_frame, end_frame, method_index, preserve_endpoints)

    # History operations
    def add_to_history(self) -> None:
        """Add to history."""
        self.window._sync_state_from_attributes()
        MainWindowOperations.add_to_history(self.window)

    def update_history_buttons(self) -> None:
        """Update history buttons."""
        MainWindowOperations.update_history_buttons(self.window)

    def undo_action(self) -> None:
        """Undo action."""
        MainWindowOperations.undo_action(self.window)
        self.window._sync_protocol_attributes()

    def redo_action(self) -> None:
        """Redo action."""
        MainWindowOperations.redo_action(self.window)
        self.window._sync_protocol_attributes()

    def restore_state(self, state: Any) -> None:
        """Restore state."""
        MainWindowOperations.restore_state(self.window, state)
        self.window._sync_protocol_attributes()

    # Frame operations
    def on_frame_changed(self, frame_num: int) -> None:
        """Handle frame change."""
        MainWindowOperations.on_frame_changed(self.window, frame_num)

    # Status operations
    def update_status_message(self, message: str) -> None:
        """Update status message."""
        MainWindowOperations.update_status_message(self.window, message)

    def refresh_point_edit_controls(self) -> None:
        """Refresh point edit controls."""
        MainWindowOperations.refresh_point_edit_controls(self.window)

    # Smoothing operations
    def apply_ui_smoothing(self) -> None:
        """Apply smoothing based on inline UI controls."""
        SmoothingOperations.apply_ui_smoothing(self.window)

    def apply_smooth_operation(self) -> None:
        """Entry point for smoothing operations."""
        SmoothingOperations.apply_smooth_operation(self.window)
