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

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import Protocol

    class TimelineFrameMarker(Protocol):
        """Protocol for timeline frame marker."""

        pass

    class MainWindow(Protocol):
        """Main window protocol for type checking."""

        pass
else:
    TimelineFrameMarker = Any
    MainWindow = Any

from PySide6.QtCore import QTimer
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

from core.logger_utils import get_logger

logger = get_logger("ui_components")


class ToolbarUIComponents:
    """Container for toolbar-related UI components."""

    def __init__(self) -> None:
        # File operations
        self.save_button: QPushButton | None = None
        self.load_button: QPushButton | None = None
        self.export_button: QPushButton | None = None
        self.load_images_button: QPushButton | None = None

        # History operations
        self.undo_button: QPushButton | None = None
        self.redo_button: QPushButton | None = None

        # Curve editing operations
        self.add_point_button: QPushButton | None = None
        self.smooth_button: QPushButton | None = None
        self.fill_gaps_button: QPushButton | None = None
        self.filter_button: QPushButton | None = None
        self.detect_problems_button: QPushButton | None = None
        self.extrapolate_button: QPushButton | None = None

        # View operations
        self.center_button: QPushButton | None = None
        self.reset_zoom_button: QPushButton | None = None
        self.toggle_bg_button: QPushButton | None = None
        self.toggle_background_button: QPushButton | None = None
        self.maximize_view_button: QPushButton | None = None
        self.reset_view_button: QPushButton | None = None

        # Analysis operations
        self.analyze_button: QPushButton | None = None

        # Utility
        self.shortcuts_button: QPushButton | None = None


class TimelineUIComponents:
    """Container for timeline and playback UI components."""

    def __init__(self) -> None:
        # Timeline controls
        self.timeline_slider: QSlider | None = None
        self.frame_edit: QLineEdit | None = None
        self.go_button: QPushButton | None = None

        # Playback controls
        self.play_button: QPushButton | None = None
        # NOTE: Removed orphaned frame navigation buttons - they were never added to UI

        # Image navigation
        self.prev_image_button: QPushButton | None = None
        self.next_image_button: QPushButton | None = None

        # Timeline components
        self.playback_timer: QTimer | None = None
        self.frame_marker: TimelineFrameMarker | None = None

        # Frame controls
        self.frame_spinbox: QSpinBox | None = None
        self.fps_spinbox: QSpinBox | None = None

        # Labels
        self.frame_label: QLabel | None = None
        self.frame_info_label: QLabel | None = None


class StatusUIComponents:
    """Container for status and information UI components."""

    def __init__(self) -> None:
        # Status bar
        self.status_bar: QStatusBar | None = None

        # Information displays
        self.info_label: QLabel | None = None
        self.image_label: QLabel | None = None

        # Quality metrics
        self.quality_score_label: QLabel | None = None
        self.quality_consistency_label: QLabel | None = None
        self.quality_coverage_label: QLabel | None = None
        self.quality_smoothness_label: QLabel | None = None

        # Quality metrics (alternate names)
        self.consistency_label: QLabel | None = None
        self.coverage_label: QLabel | None = None
        self.smoothness_label: QLabel | None = None


class VisualizationUIComponents:
    """Container for visualization and display UI components."""

    def __init__(self) -> None:
        # Visualization toggles
        self.toggle_grid_button: QPushButton | None = None
        self.toggle_vectors_button: QPushButton | None = None
        self.toggle_frame_numbers_button: QPushButton | None = None
        self.toggle_crosshair_button: QPushButton | None = None
        self.toggle_grid_view_button: QPushButton | None = None

        # View controls
        self.centering_toggle: QPushButton | None = None
        self.center_on_point_button: QPushButton | None = None
        self.opacity_slider: QSlider | None = None

        # Rendering controls
        self.point_size_slider: QSlider | None = None
        self.line_width_slider: QSlider | None = None

        # Display components
        self.nudge_indicator: QWidget | None = None


class PointEditUIComponents:
    """Container for point editing UI components."""

    def __init__(self) -> None:
        # Point editing controls
        self.update_point_button: QPushButton | None = None
        self.x_edit: QDoubleSpinBox | None = None  # Changed from QLineEdit to match MainWindow
        self.y_edit: QDoubleSpinBox | None = None  # Changed from QLineEdit to match MainWindow
        self.type_edit: QLineEdit | None = None

        # Point display settings
        self.point_size_spin: QSpinBox | None = None
        self.point_radius_spinbox: QSpinBox | None = None
        self.point_size_label: QLabel | None = None

        # Labels
        self.type_label: QLabel | None = None


class SmoothingUIComponents:
    """Container for smoothing and filtering UI components."""

    def __init__(self) -> None:
        # Smoothing controls
        self.smoothing_apply_button: QPushButton | None = None
        self.smoothing_method_combo: QComboBox | None = None
        self.smoothing_window_spinbox: QSpinBox | None = None
        self.smoothing_window_spin: QSpinBox | None = None  # Alias
        self.smoothing_sigma_spin: QDoubleSpinBox | None = None
        self.smoothing_range_combo: QComboBox | None = None

        # Filter controls
        self.filter_preset_combo: QComboBox | None = None
        self.apply_preset_button: QPushButton | None = None
        self.presets_combo: QComboBox | None = None

        # Precision controls
        self.precision_spinbox: QSpinBox | None = None


class UIComponents:
    """
    Master container for all UI components organized by functional groups.

    This class implements the Component Container Pattern to reduce MainWindow
    complexity from 85+ individual widget attributes to organized component groups.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize UI components container."""
        self.main_window: MainWindow = main_window

        # Create component groups
        self.toolbar: ToolbarUIComponents = ToolbarUIComponents()
        self.timeline: TimelineUIComponents = TimelineUIComponents()
        self.status: StatusUIComponents = StatusUIComponents()
        self.visualization: VisualizationUIComponents = VisualizationUIComponents()
        self.point_edit: PointEditUIComponents = PointEditUIComponents()
        self.smoothing: SmoothingUIComponents = SmoothingUIComponents()

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

    # NOTE: Removed orphaned frame navigation button properties - buttons never existed in UI

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
    def frame_marker(self) -> object:
        return self.timeline.frame_marker

    @property
    def frame_label(self) -> QLabel | None:
        return self.timeline.frame_label

    @property
    def frame_info_label(self) -> QLabel | None:
        return self.timeline.frame_info_label

    @property
    def frame_spinbox(self) -> QSpinBox | None:
        return self.timeline.frame_spinbox

    @property
    def fps_spinbox(self) -> QSpinBox | None:
        return self.timeline.fps_spinbox

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

    @property
    def point_size_slider(self) -> QSlider | None:
        return self.visualization.point_size_slider

    @property
    def line_width_slider(self) -> QSlider | None:
        return self.visualization.line_width_slider

    # =========================================================================
    # POINT EDIT COMPONENT ACCESS
    # =========================================================================

    @property
    def update_point_button(self) -> QPushButton | None:
        return self.point_edit.update_point_button

    @property
    def x_edit(self) -> QDoubleSpinBox | None:
        return self.point_edit.x_edit

    @property
    def y_edit(self) -> QDoubleSpinBox | None:
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
        missing: list[str] = []

        # Define critical components that must exist
        critical_components = [
            "save_button",
            "load_button",
            "timeline_slider",
            "frame_edit",
            "status_bar",
            "info_label",
            "undo_button",
            "redo_button",
        ]

        for component_name in critical_components:
            if getattr(self, component_name) is None:
                missing.append(component_name)

        return missing

    def get_component_groups(self) -> dict[str, object]:
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
