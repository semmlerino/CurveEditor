#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI Signal Connector for 3DE4 Curve Editor.

This module handles signal connections for various UI operations including:
- Timeline and frame navigation
- Dialog operations (smooth, filter, fill gaps, etc.)
- History operations (undo/redo)
- Image operations
- Analysis operations
"""

# Standard library imports
from typing import TYPE_CHECKING, Any, Callable

# Local imports
from services.dialog_service import DialogService
from services.history_service import HistoryService as HistoryOperations
from services.image_service import ImageService as ImageOperations
from services.centering_zoom_service import CenteringZoomService as ZoomOperations
from ui_components import UIComponents

if TYPE_CHECKING:
    from main_window import MainWindow


class UISignalConnector:
    """Handles signal connections for UI operations."""

    @staticmethod
    def connect_signals(main_window: Any, connect_signal_func: Callable) -> None:
        """Connect all UI-related signals.

        Args:
            main_window: The main application window
            connect_signal_func: Function to connect signals with tracking
        """
        UISignalConnector._connect_timeline_signals(main_window, connect_signal_func)
        UISignalConnector._connect_dialog_signals(main_window, connect_signal_func)
        UISignalConnector._connect_history_signals(main_window, connect_signal_func)
        UISignalConnector._connect_image_operations_signals(main_window, connect_signal_func)
        UISignalConnector._connect_analysis_signals(main_window, connect_signal_func)

    @staticmethod
    def _connect_timeline_signals(main_window: Any, connect_signal: Callable) -> None:
        """Connect signals for timeline and frame navigation.

        Args:
            main_window: The main application window
            connect_signal: Function to connect signals
        """
        # Timeline slider
        if hasattr(main_window, 'timeline_slider'):
            connect_signal(
                main_window,
                main_window.timeline_slider.valueChanged,
                lambda frame: UIComponents.on_timeline_changed(main_window, int(frame)),
                "timeline_slider.valueChanged"
            )

        # Frame edit field
        if hasattr(main_window, 'frame_edit'):
            connect_signal(
                main_window,
                main_window.frame_edit.textChanged,
                lambda text: UIComponents.on_frame_edit_changed(main_window, text),
                "frame_edit.textChanged"
            )

        # Go button
        if hasattr(main_window, 'go_button'):
            connect_signal(
                main_window,
                main_window.go_button.clicked,
                lambda: UIComponents.go_to_frame(main_window),
                "go_button.clicked"
            )

        # Frame navigation buttons
        if hasattr(main_window, 'next_frame_button'):
            connect_signal(
                main_window,
                main_window.next_frame_button.clicked,
                lambda: UIComponents.next_frame(main_window),
                "next_frame_button.clicked"
            )

        if hasattr(main_window, 'prev_frame_button'):
            connect_signal(
                main_window,
                main_window.prev_frame_button.clicked,
                lambda: UIComponents.prev_frame(main_window),
                "prev_frame_button.clicked"
            )

        if hasattr(main_window, 'first_frame_button'):
            connect_signal(
                main_window,
                main_window.first_frame_button.clicked,
                lambda: UIComponents.go_to_first_frame(main_window),
                "first_frame_button.clicked"
            )

        if hasattr(main_window, 'last_frame_button'):
            connect_signal(
                main_window,
                main_window.last_frame_button.clicked,
                lambda: UIComponents.go_to_last_frame(main_window),
                "last_frame_button.clicked"
            )

        if hasattr(main_window, 'play_button'):
            connect_signal(
                main_window,
                main_window.play_button.clicked,
                lambda: UIComponents.toggle_playback(main_window),
                "play_button.clicked"
            )

    @staticmethod
    def _connect_dialog_signals(main_window: Any, connect_signal: Callable) -> None:
        """Connect signals for dialog operations.

        Args:
            main_window: The main application window
            connect_signal: Function to connect signals
        """
        # Tool dialog buttons
        if hasattr(main_window, 'smooth_button'):
            connect_signal(
                main_window,
                main_window.smooth_button.clicked,
                main_window.apply_smooth_operation,  # Connect to MainWindow method
                "smooth_button.clicked"
            )

        if hasattr(main_window, 'filter_button'):
            connect_signal(
                main_window,
                main_window.filter_button.clicked,
                lambda: DialogService.show_filter_dialog(main_window),
                "filter_button.clicked"
            )

        if hasattr(main_window, 'fill_gaps_button'):
            connect_signal(
                main_window,
                main_window.fill_gaps_button.clicked,
                lambda: DialogService.show_fill_gaps_dialog(main_window),
                "fill_gaps_button.clicked"
            )

        if hasattr(main_window, 'extrapolate_button'):
            connect_signal(
                main_window,
                main_window.extrapolate_button.clicked,
                lambda: DialogService.show_extrapolate_dialog(main_window),
                "extrapolate_button.clicked"
            )

        if hasattr(main_window, 'detect_problems_button'):
            connect_signal(
                main_window,
                main_window.detect_problems_button.clicked,
                lambda: print("Problem detection temporarily disabled."),
                "detect_problems_button.clicked"
            )

        if hasattr(main_window, 'shortcuts_button'):
            connect_signal(
                main_window,
                main_window.shortcuts_button.clicked,
                lambda: DialogService.show_shortcuts_dialog(main_window),
                "shortcuts_button.clicked"
            )

    @staticmethod
    def _connect_history_signals(main_window: Any, connect_signal: Callable) -> None:
        """Connect signals for history operations (undo/redo).

        Args:
            main_window: The main application window
            connect_signal: Function to connect signals
        """
        # History buttons
        if hasattr(main_window, 'undo_button'):
            connect_signal(
                main_window,
                main_window.undo_button.clicked,
                lambda: HistoryOperations.undo_action(main_window),
                "undo_button.clicked"
            )

        if hasattr(main_window, 'redo_button'):
            connect_signal(
                main_window,
                main_window.redo_button.clicked,
                lambda: HistoryOperations.redo_action(main_window),
                "redo_button.clicked"
            )

    @staticmethod
    def _connect_image_operations_signals(main_window: Any, connect_signal: Callable) -> None:
        """Connect signals for image operations.

        Args:
            main_window: The main application window
            connect_signal: Function to connect signals
        """
        # Background toggle button
        if hasattr(main_window, 'toggle_bg_button'):
            connect_signal(
                main_window,
                main_window.toggle_bg_button.clicked,
                lambda: ImageOperations.toggle_background(main_window),
                "toggle_bg_button.clicked"
            )

        # Opacity slider
        if hasattr(main_window, 'opacity_slider'):
            connect_signal(
                main_window,
                main_window.opacity_slider.valueChanged,
                lambda value: ImageOperations.update_background_opacity(main_window, int(value)),
                "opacity_slider.valueChanged"
            )

        # Image navigation buttons
        if hasattr(main_window, 'load_images_button'):
            connect_signal(
                main_window,
                main_window.load_images_button.clicked,
                lambda: ImageOperations.load_background_images(main_window),
                "load_images_button.clicked"
            )

        if hasattr(main_window, 'next_image_button'):
            connect_signal(
                main_window,
                main_window.next_image_button.clicked,
                lambda: ImageOperations.next_background_image(main_window),
                "next_image_button.clicked"
            )

        if hasattr(main_window, 'prev_image_button'):
            connect_signal(
                main_window,
                main_window.prev_image_button.clicked,
                lambda: ImageOperations.previous_background_image(main_window),
                "prev_image_button.clicked"
            )

        # Centering toggle
        if hasattr(main_window, 'centering_toggle'):
            connect_signal(
                main_window,
                main_window.centering_toggle.toggled,
                lambda checked: ZoomOperations.auto_center_view(main_window) if bool(checked) else None,
                "centering_toggle.toggled"
            )

    @staticmethod
    def _connect_analysis_signals(main_window: Any, connect_signal: Callable) -> None:
        """Connect signals for analysis operations.

        Args:
            main_window: The main application window
            connect_signal: Function to connect signals
        """
        # Track quality analysis
        if hasattr(main_window, 'analyze_button'):
            connect_signal(
                main_window,
                main_window.analyze_button.clicked,
                lambda: main_window.quality_ui.analyze_track_quality(main_window) if hasattr(main_window, 'quality_ui') else None,
                "analyze_button.clicked"
            )
