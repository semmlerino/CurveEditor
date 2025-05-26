#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Smoothing components for the Curve Editor.

This module contains UI components related to curve smoothing controls,
including moving average parameters and smoothing range selection.
"""

from typing import Any

from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox, QLabel, QPushButton,
    QSpinBox, QVBoxLayout, QWidget
)


class SmoothingComponents:
    """Static utility class for smoothing control components."""

    @staticmethod
    def create_smoothing_panel(main_window: Any) -> QWidget:
        """
        Create the smoothing controls panel.

        This panel includes:
        - Window size control for moving average
        - Sigma control for smoothing strength
        - Range selection (entire curve, selected range, current window)
        - Apply button

        Args:
            main_window: The main application window instance

        Returns:
            QWidget: The smoothing panel widget
        """
        # Add inline smoothing controls
        smoothing_group = QGroupBox("Smoothing")
        smoothing_layout = QGridLayout(smoothing_group)
        smoothing_layout.addWidget(QLabel("Moving Average"), 0, 0, 1, 2)
        smoothing_layout.addWidget(QLabel("Window:"), 1, 0)

        main_window.smoothing_window_spin = QSpinBox()
        main_window.smoothing_window_spin.setRange(1, 51)
        main_window.smoothing_window_spin.setValue(5)
        smoothing_layout.addWidget(main_window.smoothing_window_spin, 1, 1)

        smoothing_layout.addWidget(QLabel("Sigma:"), 2, 0)
        main_window.smoothing_sigma_spin = QDoubleSpinBox()
        main_window.smoothing_sigma_spin.setRange(0.1, 10.0)
        main_window.smoothing_sigma_spin.setSingleStep(0.1)
        main_window.smoothing_sigma_spin.setValue(1.0)
        smoothing_layout.addWidget(main_window.smoothing_sigma_spin, 2, 1)

        smoothing_layout.addWidget(QLabel("Range:"), 3, 0)
        main_window.smoothing_range_combo = QComboBox()
        main_window.smoothing_range_combo.addItems(["Entire Curve", "Selected Range", "Current Window"])
        smoothing_layout.addWidget(main_window.smoothing_range_combo, 3, 1)

        main_window.smoothing_apply_button = QPushButton("Apply Smoothing")
        main_window.smoothing_apply_button.setToolTip("Apply smoothing to curve")
        smoothing_layout.addWidget(main_window.smoothing_apply_button, 4, 0, 1, 2)

        return smoothing_group

    @staticmethod
    def get_smoothing_parameters(main_window: Any) -> dict:
        """
        Get the current smoothing parameters from the UI.

        Args:
            main_window: The main application window instance

        Returns:
            dict: Dictionary containing window_size, sigma, and range values
        """
        params = {
            'window_size': 5,
            'sigma': 1.0,
            'range': 'Entire Curve'
        }

        if hasattr(main_window, 'smoothing_window_spin'):
            params['window_size'] = main_window.smoothing_window_spin.value()

        if hasattr(main_window, 'smoothing_sigma_spin'):
            params['sigma'] = main_window.smoothing_sigma_spin.value()

        if hasattr(main_window, 'smoothing_range_combo'):
            params['range'] = main_window.smoothing_range_combo.currentText()

        return params

    @staticmethod
    def set_smoothing_enabled(main_window: Any, enabled: bool) -> None:
        """
        Enable or disable smoothing controls.

        Args:
            main_window: The main application window instance
            enabled: Whether to enable or disable the controls
        """
        controls = [
            'smoothing_window_spin',
            'smoothing_sigma_spin',
            'smoothing_range_combo',
            'smoothing_apply_button'
        ]

        for control_name in controls:
            if hasattr(main_window, control_name):
                control = getattr(main_window, control_name)
                if control:
                    control.setEnabled(enabled)

    @staticmethod
    def reset_smoothing_parameters(main_window: Any) -> None:
        """
        Reset smoothing parameters to default values.

        Args:
            main_window: The main application window instance
        """
        if hasattr(main_window, 'smoothing_window_spin'):
            main_window.smoothing_window_spin.setValue(5)

        if hasattr(main_window, 'smoothing_sigma_spin'):
            main_window.smoothing_sigma_spin.setValue(1.0)

        if hasattr(main_window, 'smoothing_range_combo'):
            main_window.smoothing_range_combo.setCurrentIndex(0)  # "Entire Curve"
