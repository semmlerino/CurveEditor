#!/usr/bin/env python

"""
UI Components Container for MainWindow Architecture Simplification.

This module implements the Component Container Pattern to reduce MainWindow
complexity from 85+ UI attributes to organized component groups.

Key responsibilities:
1. Organize UI widgets into logical component groups
2. Provide type-safe access to all UI components
3. Maintain backward compatibility with existing code
4. Implement protocol requirements at the container level
5. Support lazy initialization and validation
"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QWidget,
)

import logging

logger = logging.getLogger("ui_components")

class ToolbarUIComponents:
    """Container for toolbar-related UI components."""

    def __init__(self) -> None:
        # File operations
        self.ui_components.save_button: QPushButton | None = None
        self.ui_components.load_button: QPushButton | None = None
        self.ui_components.export_button: QPushButton | None = None
        self.ui_components.load_images_button: QPushButton | None = None

        # History operations
        self.ui_components.undo_button: QPushButton | None = None
        self.ui_components.redo_button: QPushButton | None = None

        # Curve editing operations
        self.ui_components.add_point_button: QPushButton | None = None
        self.ui_components.smooth_button: QPushButton | None = None
        self.ui_components.fill_gaps_button: QPushButton | None = None
        self.ui_components.filter_button: QPushButton | None = None
        self.ui_components.detect_problems_button: QPushButton | None = None
        self.ui_components.extrapolate_button: QPushButton | None = None

        # View operations
        self.ui_components.center_button: QPushButton | None = None
        self.ui_components.reset_zoom_button: QPushButton | None = None
        self.ui_components.toggle_bg_button: QPushButton | None = None
        self.ui_components.toggle_background_button: QPushButton | None = None
        self.ui_components.maximize_view_button: QPushButton | None = None
        self.ui_components.reset_view_button: QPushButton | None = None

        # Analysis operations
        self.ui_components.analyze_button: QPushButton | None = None

        # Utility
        self.ui_components.shortcuts_button: QPushButton | None = None

class TimelineUIComponents:
    """Container for timeline and playback UI components."""

    def __init__(self) -> None:
        # Timeline controls
        self.ui_components.timeline_slider: QSlider | None = None
        self.ui_components.frame_edit: QLineEdit | None = None
        self.ui_components.go_button: QPushButton | None = None

        # Playback controls
        self.ui_components.play_button: QPushButton | None = None
        self.ui_components.prev_frame_button: QPushButton | None = None
        self.ui_components.next_frame_button: QPushButton | None = None
        self.ui_components.first_frame_button: QPushButton | None = None
        self.ui_components.last_frame_button: QPushButton | None = None

        # Image navigation
        self.ui_components.prev_image_button: QPushButton | None = None
        self.ui_components.next_image_button: QPushButton | None = None

        # Timeline components
        self.ui_components.playback_timer: QTimer | None = None
        self.ui_components.frame_marker: Any | None = None  # TimelineFrameMarker

        # Labels
        self.ui_components.frame_label: QLabel | None = None
        self.ui_components.frame_info_label: QLabel | None = None

class StatusUIComponents:
    """Container for status and information UI components."""

    def __init__(self) -> None:
        # Status bar
        self.ui_components.status_bar: QStatusBar | None = None

        # Information displays
        self.ui_components.info_label: QLabel | None = None
        self.ui_components.image_label: QLabel | None = None

        # Quality metrics
        self.ui_components.quality_score_label: QLabel | None = None
        self.ui_components.quality_consistency_label: QLabel | None = None
        self.ui_components.quality_coverage_label: QLabel | None = None
        self.ui_components.quality_smoothness_label: QLabel | None = None

        # Quality metrics (alternate names)
        self.ui_components.consistency_label: QLabel | None = None
        self.ui_components.coverage_label: QLabel | None = None
        self.ui_components.smoothness_label: QLabel | None = None

class VisualizationUIComponents:
    """Container for visualization and display UI components."""

    def __init__(self) -> None:
        # Visualization toggles
        self.ui_components.toggle_grid_button: QPushButton | None = None
        self.ui_components.toggle_vectors_button: QPushButton | None = None
        self.ui_components.toggle_frame_numbers_button: QPushButton | None = None
        self.ui_components.toggle_crosshair_button: QPushButton | None = None
        self.ui_components.toggle_grid_view_button: QPushButton | None = None

        # View controls
        self.ui_components.centering_toggle: QPushButton | None = None
        self.ui_components.center_on_point_button: QPushButton | None = None
        self.ui_components.opacity_slider: QSlider | None = None

        # Display components
        self.ui_components.nudge_indicator: QWidget | None = None

class PointEditUIComponents:
    """Container for point editing UI components."""

    def __init__(self) -> None:
        # Point editing controls
        self.ui_components.update_point_button: QPushButton | None = None
        self.ui_components.x_edit: QLineEdit | None = None
        self.ui_components.y_edit: QLineEdit | None = None
        self.ui_components.type_edit: QLineEdit | None = None

        # Point display settings
        self.ui_components.point_size_spin: QSpinBox | None = None
        self.ui_components.point_radius_spinbox: QSpinBox | None = None
        self.ui_components.point_size_label: QLabel | None = None

        # Labels
        self.ui_components.type_label: QLabel | None = None

class SmoothingUIComponents:
    """Container for smoothing and filtering UI components."""

    def __init__(self) -> None:
        # Smoothing controls
        self.ui_components.smoothing_apply_button: QPushButton | None = None
        self.ui_components.smoothing_method_combo: QComboBox | None = None
        self.ui_components.smoothing_window_spinbox: QSpinBox | None = None
        self.ui_components.smoothing_window_spin: QSpinBox | None = None  # Alias
        self.ui_components.smoothing_sigma_spin: QDoubleSpinBox | None = None
        self.ui_components.smoothing_range_combo: QComboBox | None = None

        # Filter controls
        self.ui_components.filter_preset_combo: QComboBox | None = None
        self.ui_components.apply_preset_button: QPushButton | None = None
        self.ui_components.presets_combo: QComboBox | None = None

        # Precision controls
        self.ui_components.precision_spinbox: QSpinBox | None = None

class UIComponents:
    """
    Master container for all UI components organized by functional groups.

    This class implements the Component Container Pattern to reduce MainWindow
    complexity from 85+ individual widget attributes to organized component groups.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize UI components container."""
        self.main_window = main_window

        # Create component groups
        self.toolbar = ToolbarUIComponents()
        self.timeline = TimelineUIComponents()
        self.status = StatusUIComponents()
        self.visualization = VisualizationUIComponents()
        self.point_edit = PointEditUIComponents()
        self.smoothing = SmoothingUIComponents()

        logger.info("UIComponents container initialized with component groups")

    # =========================================================================
    # TOOLBAR COMPONENT ACCESS
    # =========================================================================

    @property
    def save_button(self) -> QPushButton | None:
        return self.toolbar.save_button

    @property
    def load_button(self) -> QPushButton | None:
        return self.toolbar.load_button

    @property
    def export_button(self) -> QPushButton | None:
        return self.toolbar.export_button

    @property
    def load_images_button(self) -> QPushButton | None:
        return self.toolbar.load_images_button

    @property
    def undo_button(self) -> QPushButton | None:
        return self.toolbar.undo_button

    @property
    def redo_button(self) -> QPushButton | None:
        return self.toolbar.redo_button

    @property
    def add_point_button(self) -> QPushButton | None:
        return self.toolbar.add_point_button

    @property
    def smooth_button(self) -> QPushButton | None:
        return self.toolbar.smooth_button

    @property
    def fill_gaps_button(self) -> QPushButton | None:
        return self.toolbar.fill_gaps_button

    @property
    def filter_button(self) -> QPushButton | None:
        return self.toolbar.filter_button

    @property
    def detect_problems_button(self) -> QPushButton | None:
        return self.toolbar.detect_problems_button

    @property
    def extrapolate_button(self) -> QPushButton | None:
        return self.toolbar.extrapolate_button

    @property
    def center_button(self) -> QPushButton | None:
        return self.toolbar.center_button

    @property
    def reset_zoom_button(self) -> QPushButton | None:
        return self.toolbar.reset_zoom_button

    @property
    def toggle_bg_button(self) -> QPushButton | None:
        return self.toolbar.toggle_bg_button

    @property
    def toggle_background_button(self) -> QPushButton | None:
        return self.toolbar.toggle_background_button

    @property
    def maximize_view_button(self) -> QPushButton | None:
        return self.toolbar.maximize_view_button

    @property
    def reset_view_button(self) -> QPushButton | None:
        return self.toolbar.reset_view_button

    @property
    def analyze_button(self) -> QPushButton | None:
        return self.toolbar.analyze_button

    @property
    def shortcuts_button(self) -> QPushButton | None:
        return self.toolbar.shortcuts_button

    # =========================================================================
    # TIMELINE COMPONENT ACCESS
    # =========================================================================

    @property
    def timeline_slider(self) -> QSlider | None:
        return self.timeline.timeline_slider

    @property
    def frame_edit(self) -> QLineEdit | None:
        return self.timeline.frame_edit

    @property
    def go_button(self) -> QPushButton | None:
        return self.timeline.go_button

    @property
    def play_button(self) -> QPushButton | None:
        return self.timeline.play_button

    @property
    def prev_frame_button(self) -> QPushButton | None:
        return self.timeline.prev_frame_button

    @property
    def next_frame_button(self) -> QPushButton | None:
        return self.timeline.next_frame_button

    @property
    def first_frame_button(self) -> QPushButton | None:
        return self.timeline.first_frame_button

    @property
    def last_frame_button(self) -> QPushButton | None:
        return self.timeline.last_frame_button

    @property
    def prev_image_button(self) -> QPushButton | None:
        return self.timeline.prev_image_button

    @property
    def next_image_button(self) -> QPushButton | None:
        return self.timeline.next_image_button

    @property
    def playback_timer(self) -> QTimer | None:
        return self.timeline.playback_timer

    @property
    def frame_marker(self) -> Any:
        return self.timeline.frame_marker

    @property
    def frame_label(self) -> QLabel | None:
        return self.timeline.frame_label

    @property
    def frame_info_label(self) -> QLabel | None:
        return self.timeline.frame_info_label

    # =========================================================================
    # STATUS COMPONENT ACCESS
    # =========================================================================

    @property
    def status_bar(self) -> QStatusBar | None:
        return self.status.status_bar

    @property
    def info_label(self) -> QLabel | None:
        return self.status.info_label

    @property
    def image_label(self) -> QLabel | None:
        return self.status.image_label

    @property
    def quality_score_label(self) -> QLabel | None:
        return self.status.quality_score_label

    @property
    def quality_consistency_label(self) -> QLabel | None:
        return self.status.quality_consistency_label

    @property
    def quality_coverage_label(self) -> QLabel | None:
        return self.status.quality_coverage_label

    @property
    def quality_smoothness_label(self) -> QLabel | None:
        return self.status.quality_smoothness_label

    @property
    def consistency_label(self) -> QLabel | None:
        return self.status.consistency_label

    @property
    def coverage_label(self) -> QLabel | None:
        return self.status.coverage_label

    @property
    def smoothness_label(self) -> QLabel | None:
        return self.status.smoothness_label

    # =========================================================================
    # VISUALIZATION COMPONENT ACCESS
    # =========================================================================

    @property
    def toggle_grid_button(self) -> QPushButton | None:
        return self.visualization.toggle_grid_button

    @property
    def toggle_vectors_button(self) -> QPushButton | None:
        return self.visualization.toggle_vectors_button

    @property
    def toggle_frame_numbers_button(self) -> QPushButton | None:
        return self.visualization.toggle_frame_numbers_button

    @property
    def toggle_crosshair_button(self) -> QPushButton | None:
        return self.visualization.toggle_crosshair_button

    @property
    def toggle_grid_view_button(self) -> QPushButton | None:
        return self.visualization.toggle_grid_view_button

    @property
    def centering_toggle(self) -> QPushButton | None:
        return self.visualization.centering_toggle

    @property
    def center_on_point_button(self) -> QPushButton | None:
        return self.visualization.center_on_point_button

    @property
    def opacity_slider(self) -> QSlider | None:
        return self.visualization.opacity_slider

    @property
    def nudge_indicator(self) -> QWidget | None:
        return self.visualization.nudge_indicator

    # =========================================================================
    # POINT EDIT COMPONENT ACCESS
    # =========================================================================

    @property
    def update_point_button(self) -> QPushButton | None:
        return self.point_edit.update_point_button

    @property
    def x_edit(self) -> QLineEdit | None:
        return self.point_edit.x_edit

    @property
    def y_edit(self) -> QLineEdit | None:
        return self.point_edit.y_edit

    @property
    def type_edit(self) -> QLineEdit | None:
        return self.point_edit.type_edit

    @property
    def point_size_spin(self) -> QSpinBox | None:
        return self.point_edit.point_size_spin

    @property
    def point_radius_spinbox(self) -> QSpinBox | None:
        return self.point_edit.point_radius_spinbox

    @property
    def point_size_label(self) -> QLabel | None:
        return self.point_edit.point_size_label

    @property
    def type_label(self) -> QLabel | None:
        return self.point_edit.type_label

    # =========================================================================
    # SMOOTHING COMPONENT ACCESS
    # =========================================================================

    @property
    def smoothing_apply_button(self) -> QPushButton | None:
        return self.smoothing.smoothing_apply_button

    @property
    def smoothing_method_combo(self) -> QComboBox | None:
        return self.smoothing.smoothing_method_combo

    @property
    def smoothing_window_spinbox(self) -> QSpinBox | None:
        return self.smoothing.smoothing_window_spinbox

    @property
    def smoothing_window_spin(self) -> QSpinBox | None:
        return self.smoothing.smoothing_window_spin

    @property
    def smoothing_sigma_spin(self) -> QDoubleSpinBox | None:
        return self.smoothing.smoothing_sigma_spin

    @property
    def smoothing_range_combo(self) -> QComboBox | None:
        return self.smoothing.smoothing_range_combo

    @property
    def filter_preset_combo(self) -> QComboBox | None:
        return self.smoothing.filter_preset_combo

    @property
    def apply_preset_button(self) -> QPushButton | None:
        return self.smoothing.apply_preset_button

    @property
    def presets_combo(self) -> QComboBox | None:
        return self.smoothing.presets_combo

    @property
    def precision_spinbox(self) -> QSpinBox | None:
        return self.smoothing.precision_spinbox

    def validate_completeness(self) -> list[str]:
        """
        Validate that all required components exist.

        Returns:
            List of missing component names, empty if all are present
        """
        missing = []

        # Define critical components that must exist
        critical_components = [
            "save_button", "load_button", "timeline_slider", "frame_edit",
            "status_bar", "info_label", "undo_button", "redo_button"
        ]

        for component_name in critical_components:
            if getattr(self, component_name) is None:
                missing.append(component_name)

        return missing

    def get_component_groups(self) -> dict[str, Any]:
        """
        Get all component groups for inspection or testing.

        Returns:
            Dictionary mapping group names to their instances
        """
        return {
            "toolbar": self.toolbar,
            "timeline": self.timeline,
            "status": self.status,
            "visualization": self.visualization,
            "point_edit": self.point_edit,
            "smoothing": self.smoothing,
        }