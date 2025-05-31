#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main Window Operations for Curve Editor.

This module contains operation methods that were previously in MainWindow,
helping to reduce the size of the MainWindow class by extracting business logic.
"""

import logging
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QTimer

from services.file_service import FileService
from services.image_service import ImageService
from services.history_service import HistoryService
from services.dialog_service import DialogService
from services.settings_service import SettingsService
from services.curve_service import CurveService as CurveViewOperations
from services.analysis_service import AnalysisService as CurveDataOperations
from services.centering_zoom_service import CenteringZoomService as ZoomOperations
from services.unified_transformation_service import UnifiedTransformationService
from track_quality import TrackQualityUI
from ui_components import UIComponents

if TYPE_CHECKING:
    from main_window import MainWindow
    from typing import List

logger = logging.getLogger(__name__)


class MainWindowOperations:
    """Handles various operations for MainWindow."""

    # File Operations
    @staticmethod
    def set_image_sequence(window: 'MainWindow', path: str, filenames: 'List[str]'):
        """Set the current image sequence."""
        ImageService.set_image_sequence(window.curve_view, path, filenames)
        window.update_image_label()

    @staticmethod
    def load_track_data(window: 'MainWindow'):
        """Load track data using FileService."""
        FileService.load_track_data(window)

    @staticmethod
    def add_track_data(window: 'MainWindow'):
        """Add track data using FileService."""
        FileService.add_track_data(window)

    @staticmethod
    def save_track_data(window: 'MainWindow'):
        """Save track data using FileService."""
        FileService.save_track_data(window)

    @staticmethod
    def load_image_sequence(window: 'MainWindow'):
        """Load image sequence using ImageService."""
        ImageService.load_image_sequence(window, window.state.image_sequence_path, window.state.image_filenames)

    # Point Editing Operations
    @staticmethod
    def on_point_selected(window: 'MainWindow', idx: int):
        """Handle point selection in the view."""
        CurveViewOperations.on_point_selected(window.curve_view, window, idx)

    @staticmethod
    def on_point_moved(window: 'MainWindow', idx: int, x: float, y: float):
        """Handle point moved in the view."""
        CurveViewOperations.on_point_moved(window, idx, x, y)

    @staticmethod
    def update_point_info(window: 'MainWindow', idx: int, x: float, y: float):
        """Update the point information panel."""
        CurveViewOperations.update_point_info(window, idx, x, y)

    # History Operations
    @staticmethod
    def add_to_history(window: 'MainWindow'):
        """Add current state to history."""
        HistoryService.add_to_history(window)

    @staticmethod
    def update_history_buttons(window: 'MainWindow'):
        """Update the state of undo/redo buttons."""
        HistoryService.update_history_buttons(window)

    @staticmethod
    def undo_action(window: 'MainWindow'):
        """Undo the last action."""
        HistoryService.undo_action(window)

    @staticmethod
    def redo_action(window: 'MainWindow'):
        """Redo the previously undone action."""
        HistoryService.redo_action(window)

    @staticmethod
    def restore_state(window: 'MainWindow', state):
        """Restore application state from history."""
        HistoryService.restore_state(window, state)

    # Dialog Operations
    @staticmethod
    def show_shortcuts_dialog(window: 'MainWindow'):
        """Show dialog with keyboard shortcuts."""
        DialogService.show_shortcuts_dialog(window)

    @staticmethod
    def show_filter_dialog(window: 'MainWindow'):
        """Show the filter dialog for the curve data."""
        DialogService.show_filter_dialog(window)

    @staticmethod
    def show_fill_gaps_dialog(window: 'MainWindow'):
        """Show dialog for filling gaps in the curve data."""
        DialogService.show_fill_gaps_dialog(window)

    @staticmethod
    def show_extrapolate_dialog(window: 'MainWindow'):
        """Show extrapolate dialog."""
        DialogService.show_extrapolate_dialog(window)

    @staticmethod
    def fill_gap(window: 'MainWindow', start_frame: int, end_frame: int, method_index: int, preserve_endpoints: bool = True):
        """Delegate gap filling to DialogService."""
        DialogService.fill_gap(window, start_frame, end_frame, method_index, preserve_endpoints)

    # View Operations
    @staticmethod
    def set_centering_enabled(window: 'MainWindow', enabled: bool):
        """Enable or disable auto-centering of the view."""
        window.state.auto_center_enabled = enabled
        if hasattr(window, 'auto_center_action'):
            window.auto_center_action.setChecked(enabled)

        # Immediately center on selected point if available
        if enabled:
            if hasattr(window, 'curve_view') and hasattr(window.curve_view, 'selected_point_idx') and window.curve_view.selected_point_idx >= 0:
                ZoomOperations.center_on_selected_point(window.curve_view)

    @staticmethod
    def enable_point_controls(window: 'MainWindow', enabled: bool):
        """Enable or disable point editing controls."""
        window.update_point_button.setEnabled(enabled)
        if hasattr(window, 'type_edit'):
            window.type_edit.setEnabled(enabled)

    @staticmethod
    def update_image_label(window: 'MainWindow'):
        """Update the image label with current image info."""
        ImageService.update_image_label(window)

    @staticmethod
    def setup_timeline(window: 'MainWindow'):
        """Setup timeline slider based on frame range."""
        UIComponents.setup_timeline(window)

    # Frame Operations
    @staticmethod
    def on_frame_changed(window: 'MainWindow', frame_num: int):
        """Called when the frame changes."""
        # Select point for frame
        if hasattr(window, '_select_point_for_frame'):
            window._select_point_for_frame(frame_num)

        if window.state.auto_center_enabled:
            # Center view on selected point
            if hasattr(window.curve_view, 'centerOnSelectedPoint'):
                window.curve_view.centerOnSelectedPoint()

    @staticmethod
    def update_status_message(window: 'MainWindow', message: str):
        """Update the status bar message."""
        window.statusBar().showMessage(message, 3000)
        logger.debug(f"Status message updated: {message}")

    @staticmethod
    def refresh_point_edit_controls(window: 'MainWindow'):
        """Refresh the point editing controls to match current selection."""
        if not hasattr(window, 'curve_view') or not window.curve_view:
            return

        selected_idx = getattr(window.curve_view, 'selected_point_idx', -1)
        if selected_idx >= 0 and window.state.curve_data and selected_idx < len(window.state.curve_data):
            selected_point = window.state.curve_data[selected_idx]
            logger.debug(f"Refreshing point edit controls for point {selected_idx}: {selected_point}")
        else:
            logger.debug("No valid point selected, clearing edit controls")
