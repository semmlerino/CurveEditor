#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Visualization signal connector for CurveEditor.

This module handles all signal connections related to visualization controls
including grid, vectors, frame numbers, and view manipulation.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from main_window import MainWindow
    from signal_registry import RegistryConnector

from services.centering_zoom_service import CenteringZoomService as ZoomOperations
from services.curve_service import CurveService as CurveViewOperations
from services.visualization_service import VisualizationService as VisualizationOperations


class VisualizationSignalConnector:
    """Handles signal connections for visualization operations."""

    @staticmethod
    def connect_signals(main_window: 'MainWindow', registry: 'RegistryConnector') -> None:
        """Connect all visualization related signals.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        VisualizationSignalConnector._connect_basic_view_signals(main_window, registry)
        VisualizationSignalConnector._connect_enhanced_view_signals(main_window, registry)
        VisualizationSignalConnector._connect_centering_signals(main_window, registry)

    @staticmethod
    def _connect_basic_view_signals(main_window: Any, registry: Any) -> None:
        """Connect basic view control signals.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        # Reset view button
        if hasattr(main_window, 'reset_view_button'):
            registry._connect_signal(
                main_window,
                main_window.reset_view_button.clicked,
                lambda: CurveViewOperations.reset_view(main_window),
                "reset_view_button.clicked"
            )

    @staticmethod
    def _connect_enhanced_view_signals(main_window: Any, registry: Any) -> None:
        """Connect enhanced visualization control signals.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        # Grid toggle
        if hasattr(main_window, 'toggle_grid_button'):
            registry._connect_signal(
                main_window,
                main_window.toggle_grid_button.toggled,
                lambda checked: VisualizationOperations.toggle_grid(main_window.curve_view, bool(checked)),
                "toggle_grid_button.toggled"
            )

        # Velocity vectors toggle
        if hasattr(main_window, 'toggle_vectors_button'):
            registry._connect_signal(
                main_window,
                main_window.toggle_vectors_button.toggled,
                lambda checked: VisualizationOperations.toggle_velocity_vectors(
                    main_window,
                    bool(not main_window.toggle_vectors_button.isChecked())
                    if hasattr(main_window, 'toggle_vectors_button') else False
                ),
                "toggle_vectors_button.toggled"
            )

        # Frame numbers toggle
        if hasattr(main_window, 'toggle_frame_numbers_button'):
            registry._connect_signal(
                main_window,
                main_window.toggle_frame_numbers_button.toggled,
                lambda checked: VisualizationOperations.toggle_frame_numbers(
                    main_window,
                    bool(checked)
                ),
                "toggle_frame_numbers_button.toggled"
            )

    @staticmethod
    def _connect_centering_signals(main_window: Any, registry: Any) -> None:
        """Connect centering and zoom related signals.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        # Center on point button
        if hasattr(main_window, 'center_on_point_button'):
            registry._connect_signal(
                main_window,
                main_window.center_on_point_button.clicked,
                lambda: ZoomOperations.center_on_selected_point(main_window),
                "center_on_point_button.clicked"
            )

        # Auto-centering toggle
        if hasattr(main_window, 'centering_toggle'):
            registry._connect_signal(
                main_window,
                main_window.centering_toggle.toggled,
                lambda checked: main_window.set_centering_enabled(bool(checked)),
                "centering_toggle.toggled"
            )
