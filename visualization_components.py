#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Visualization components for the Curve Editor.

This module contains UI components related to visualization controls,
including grid, vectors, frame numbers, crosshair toggles, and point size controls.
"""

from typing import Any, Callable

from PySide6.QtWidgets import (
    QGridLayout, QGroupBox, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget
)

from services.centering_zoom_service import CenteringZoomService


class VisualizationComponents:
    """Static utility class for visualization control components."""

    @staticmethod
    def create_visualization_panel(main_window: Any) -> QWidget:
        """
        Create the visualization controls panel.

        This panel includes:
        - Grid toggle button
        - Vectors toggle button
        - Frame numbers toggle button
        - Crosshair toggle button
        - Center on point toggle button
        - Point size controls

        Args:
            main_window: The main application window instance

        Returns:
            QWidget: The visualization panel widget
        """
        # Center: Visualization Controls
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)

        vis_group = QGroupBox("Visualization")
        vis_layout = QGridLayout(vis_group)

        main_window.toggle_grid_button = QPushButton("Grid")
        main_window.toggle_grid_button.setCheckable(True)
        main_window.toggle_grid_button.setToolTip("Toggle Grid Visibility (G)")

        main_window.toggle_vectors_button = QPushButton("Vectors")
        main_window.toggle_vectors_button.setCheckable(True)
        main_window.toggle_vectors_button.setToolTip("Toggle Velocity Vectors (V)")

        main_window.toggle_frame_numbers_button = QPushButton("Numbers")
        main_window.toggle_frame_numbers_button.setCheckable(True)
        main_window.toggle_frame_numbers_button.setToolTip("Toggle Frame Numbers (F)")

        main_window.toggle_crosshair_button = QPushButton("Crosshair")
        main_window.toggle_crosshair_button.setCheckable(True)
        main_window.toggle_crosshair_button.setToolTip("Toggle Crosshair (X)")

        # Typed slot for center toggled in control panel
        def on_control_center_toggled(checked: bool) -> None:
            main_window.set_centering_enabled(checked)
            if checked:
                CenteringZoomService.auto_center_view(main_window, preserve_zoom=True)

        main_window.center_on_point_button = QPushButton("Center")
        main_window.center_on_point_button.setCheckable(True)
        main_window.center_on_point_button.toggled.connect(on_control_center_toggled)
        main_window.center_on_point_button.setStyleSheet("QPushButton:checked { background-color: lightblue; }")
        main_window.center_on_point_button.setToolTip("Center View on Selected Point (C)")

        main_window.point_size_label = QLabel("Point Size:")
        main_window.point_size_spin = QSpinBox()
        main_window.point_size_spin.setRange(1, 20)
        main_window.point_size_spin.setValue(5)  # Default size
        main_window.point_size_spin.setToolTip("Adjust Point Size")

        vis_layout.addWidget(main_window.toggle_grid_button, 0, 0)
        vis_layout.addWidget(main_window.toggle_vectors_button, 0, 1)
        vis_layout.addWidget(main_window.toggle_frame_numbers_button, 1, 0)
        vis_layout.addWidget(main_window.toggle_crosshair_button, 1, 1)
        vis_layout.addWidget(main_window.center_on_point_button, 2, 0, 1, 2)
        vis_layout.addWidget(main_window.point_size_label, 3, 0)
        vis_layout.addWidget(main_window.point_size_spin, 3, 1)

        center_layout.addWidget(vis_group)
        center_layout.addStretch()

        return center_panel

    @staticmethod
    def set_visualization_controls_enabled(main_window: Any, enabled: bool) -> None:
        """
        Enable or disable visualization controls.

        Args:
            main_window: The main application window instance
            enabled: Whether to enable or disable the controls
        """
        controls = [
            'toggle_grid_button',
            'toggle_vectors_button',
            'toggle_frame_numbers_button',
            'toggle_crosshair_button',
            'center_on_point_button',
            'point_size_spin'
        ]

        for control_name in controls:
            if hasattr(main_window, control_name):
                control = getattr(main_window, control_name)
                if control:
                    control.setEnabled(enabled)

    @staticmethod
    def reset_visualization_toggles(main_window: Any) -> None:
        """
        Reset all visualization toggle buttons to their default states.

        Args:
            main_window: The main application window instance
        """
        toggle_buttons = [
            ('toggle_grid_button', False),
            ('toggle_vectors_button', False),
            ('toggle_frame_numbers_button', False),
            ('toggle_crosshair_button', False),
            ('center_on_point_button', False)
        ]

        for button_name, default_state in toggle_buttons:
            if hasattr(main_window, button_name):
                button = getattr(main_window, button_name)
                if button and hasattr(button, 'setChecked'):
                    button.setChecked(default_state)
