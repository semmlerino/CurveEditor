#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Status and information display components for the Curve Editor.

This module contains UI components related to status display, track quality metrics,
and information labels.
"""

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QComboBox
)


class StatusComponents:
    """Static utility class for status and information display components."""

    @staticmethod
    def create_track_quality_panel(main_window: Any) -> QWidget:
        """
        Create the track quality metrics panel.

        This panel displays:
        - Overall quality score
        - Smoothness metric
        - Consistency metric
        - Coverage metric
        - Analyze button

        Args:
            main_window: The main application window instance

        Returns:
            QWidget: The track quality panel widget
        """
        # Track Quality Group
        quality_group = QGroupBox("Track Quality")
        quality_layout = QGridLayout(quality_group)

        # Quality metrics labels
        quality_layout.addWidget(QLabel("Overall Score:"), 0, 0)
        main_window.quality_score_label = QLabel("N/A")
        quality_font = QFont("Arial")  # type: ignore[arg-type]
        quality_font.setPointSize(10)
        quality_font.setWeight(QFont.Weight.Bold)
        main_window.quality_score_label.setFont(quality_font)
        quality_layout.addWidget(main_window.quality_score_label, 0, 1)  # type: ignore[arg-type]

        quality_layout.addWidget(QLabel("Smoothness:"), 1, 0)
        main_window.smoothness_label = QLabel("N/A")
        quality_layout.addWidget(main_window.smoothness_label, 1, 1)

        quality_layout.addWidget(QLabel("Consistency:"), 2, 0)
        main_window.consistency_label = QLabel("N/A")
        quality_layout.addWidget(main_window.consistency_label, 2, 1)

        quality_layout.addWidget(QLabel("Coverage:"), 3, 0)
        main_window.coverage_label = QLabel("N/A")
        quality_layout.addWidget(main_window.coverage_label, 3, 1)

        # Analyze button
        main_window.analyze_button = QPushButton("Analyze Quality")
        main_window.analyze_button.setToolTip("Analyze the quality of the current track data")
        quality_layout.addWidget(main_window.analyze_button, 4, 0, 1, 2)

        return quality_group

    @staticmethod
    def create_quick_filter_presets(main_window: Any) -> QWidget:
        """
        Create the quick filter presets panel.

        Args:
            main_window: The main application window instance

        Returns:
            QWidget: The quick filter presets widget
        """
        # Quick Filter Presets Group
        filter_group = QGroupBox("Quick Filters")
        filter_layout = QVBoxLayout(filter_group)

        main_window.presets_combo = QComboBox()
        main_window.presets_combo.addItems([
            "Select Preset...",
            "Smooth Light",
            "Smooth Medium",
            "Smooth Heavy",
            "Filter Jitter"
        ])
        main_window.presets_combo.setEnabled(False)

        main_window.apply_preset_button = QPushButton("Apply Preset")
        main_window.apply_preset_button.setToolTip("Apply the selected filter preset")
        main_window.apply_preset_button.setEnabled(False)

        filter_layout.addWidget(main_window.presets_combo)
        filter_layout.addWidget(main_window.apply_preset_button)

        return filter_group

    @staticmethod
    def update_info_label(main_window: Any, text: str) -> None:
        """
        Update the main info label text.

        Args:
            main_window: The main application window instance
            text: The text to display
        """
        if hasattr(main_window, 'info_label'):
            main_window.info_label.setText(text)

    @staticmethod
    def update_quality_metrics(
        main_window: Any,
        overall_score: Optional[float] = None,
        smoothness: Optional[float] = None,
        consistency: Optional[float] = None,
        coverage: Optional[float] = None
    ) -> None:
        """
        Update the track quality metrics display.

        Args:
            main_window: The main application window instance
            overall_score: Overall quality score (0-100)
            smoothness: Smoothness metric (0-100)
            consistency: Consistency metric (0-100)
            coverage: Coverage metric (0-100)
        """
        if overall_score is not None and hasattr(main_window, 'quality_score_label'):
            main_window.quality_score_label.setText(f"Overall: {overall_score:.1f}%")

        if smoothness is not None and hasattr(main_window, 'quality_smoothness_label'):
            main_window.quality_smoothness_label.setText(f"Smoothness: {smoothness:.1f}%")

        if consistency is not None and hasattr(main_window, 'quality_consistency_label'):
            main_window.quality_consistency_label.setText(f"Consistency: {consistency:.1f}%")

        if coverage is not None and hasattr(main_window, 'quality_coverage_label'):
            main_window.quality_coverage_label.setText(f"Coverage: {coverage:.1f}%")

    @staticmethod
    def clear_quality_metrics(main_window: Any) -> None:
        """
        Clear all quality metrics displays.

        Args:
            main_window: The main application window instance
        """
        labels = [
            'quality_score_label',
            'quality_smoothness_label',
            'quality_consistency_label',
            'quality_coverage_label'
        ]

        for label_name in labels:
            if hasattr(main_window, label_name):
                label = getattr(main_window, label_name)
                metric_name = label.text().split(':')[0]
                label.setText(f"{metric_name}: N/A")

    @staticmethod
    def set_quality_panel_enabled(main_window: Any, enabled: bool) -> None:
        """
        Enable or disable the quality panel controls.

        Args:
            main_window: The main application window instance
            enabled: Whether to enable or disable the controls
        """
        if hasattr(main_window, 'analyze_button'):
            main_window.analyze_button.setEnabled(enabled)

    @staticmethod
    def set_filter_presets_enabled(main_window: Any, enabled: bool) -> None:
        """
        Enable or disable the filter preset controls.

        Args:
            main_window: The main application window instance
            enabled: Whether to enable or disable the controls
        """
        if hasattr(main_window, 'filter_preset_combo'):
            main_window.filter_preset_combo.setEnabled(enabled)
        if hasattr(main_window, 'apply_preset_button'):
            main_window.apply_preset_button.setEnabled(enabled)
