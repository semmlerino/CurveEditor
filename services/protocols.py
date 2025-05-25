from __future__ import annotations
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Protocols for CurveEditor components.

This module defines structural protocols that enforce interface consistency
across the application. These protocols help ensure type safety while allowing
flexibility in implementation.
"""

from typing import Protocol, Optional, Any, Tuple, List, Dict, Union, TypeVar, Set, runtime_checkable
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import QRect

# Type aliases for common data structures
PointTuple = Tuple[int, float, float]  # frame, x, y
PointTupleWithStatus = Tuple[int, float, float, Union[bool, str]]  # frame, x, y, status (bool or str)
PointsList = List[Union[PointTuple, PointTupleWithStatus]]

# Image Service Protocols
@runtime_checkable
class ImageSequenceProtocol(Protocol):
    # Added for image_service compatibility
    image_sequence_path: str
    current_image_idx: int
    image_filenames: list[str]
    image_width: int
    image_height: int
    zoom_factor: float
    offset_x: float
    offset_y: float
    selected_point_idx: int
    def setFocus(self) -> None: ...
    def setCurrentImageByIndex(self, idx: int) -> None: ...
    def centerOnSelectedPoint(self) -> bool: ...
    def setImageSequence(self, path: str, filenames: list[str]) -> None: ...
    background_image: Any
    scale_to_image: bool
    image_changed: Any
    def emit(self, *args: Any, **kwargs: Any) -> None: ...
    def update(self) -> None: ...

@runtime_checkable
class CurveViewProtocol(ImageSequenceProtocol, Protocol):
    # Added for image_service compatibility
    current_image_idx: int
    def setCurrentImageByIndex(self, idx: int) -> None: ...
    def setImageSequence(self, path: str, filenames: list[str]) -> None: ...
    def toggleBackgroundVisible(self, visible: bool) -> None: ...
    def setBackgroundOpacity(self, opacity: float) -> None: ...
    image_filenames: list[str]
    show_background: bool
    image_width: int
    image_height: int
    zoom_factor: float
    offset_x: float
    offset_y: float
    selected_point_idx: int
    def centerOnSelectedPoint(self) -> bool: ...
    """Protocol defining the interface for curve view components."""

    # Common attributes
    x_offset: float
    y_offset: float
    flip_y_axis: bool
    scale_to_image: bool
    background_image: Optional[QPixmap]  # Changed from Any to QPixmap

    # Visualization attributes (added for type safety)
    show_grid: bool
    show_velocity_vectors: bool
    show_all_frame_numbers: bool
    show_crosshair: bool
    background_opacity: float
    point_radius: int
    grid_color: QColor  # Now properly typed as QColor
    grid_line_width: int

    # Data and selection
    curve_data: PointsList
    selected_points: Set[int]
    frame_marker_label: Any
    timeline_slider: Any
    points: PointsList  # Specific point data list
    nudge_increment: float
    current_increment_index: int
    available_increments: List[float]
    main_window: Any  # Reference to main window for status updates
    # Selection rectangle
    selection_rect: QRect  # Properly typed as QRect
    # Signals
    point_selected: Any  # Signal
    point_moved: Any  # Signal
    selection_changed: Any  # Signal
    # Points manipulation
    def set_curve_data(self, curve_data: PointsList) -> None: ...
    def get_selected_indices(self) -> List[int]: ...
    def setPoints(self, points: PointsList, image_width: int = 0, image_height: int = 0, preserve_view: bool = False) -> None: ...
    def get_selected_points(self) -> List[int]: ...
    def setVelocityData(self, velocities: Any) -> None: ...
    def toggleVelocityVectors(self, enabled: bool) -> None: ...


from PySide6.QtWidgets import QWidget

class MainWindowProtocol(Protocol):
    # For image_service compatibility
    image_sequence_path: str
    image_filenames: list[str]
    image_label: Any
    toggle_bg_button: Any
    default_directory: str
    image_width: int
    image_height: int
    curve_view: CurveViewProtocol
    curve_data: PointsList
    point_name: str
    point_color: str
    status_bar: Any
    save_button: Any
    add_point_button: Any
    smooth_button: Any
    fill_gaps_button: Any
    filter_button: Any
    detect_problems_button: Any
    extrapolate_button: Any
    timeline_slider: Any
    frame_edit: Any
    go_button: Any
    info_label: Any
    prev_image_button: Any
    next_image_button: Any
    opacity_slider: Any
    
    @property
    def qwidget(self) -> Any: ...
    def update_image_label(self) -> None: ...
    def statusBar(self) -> Any: ...
    def update_status_message(self, message: str) -> None: ...
    def refresh_point_edit_controls(self) -> None: ...
    def add_to_history(self) -> None: ...
    def setup_timeline(self, start_frame: int, end_frame: int) -> None: ...
    def setImageSequence(self, filenames: list[str]) -> None: ...



class ImageProtocol(Protocol):
    """Protocol defining the interface for image objects.
    
    This protocol is compatible with QPixmap and other image types
    that provide width() and height() methods.
    """

    def width(self) -> int: ...
    def height(self) -> int: ...


class PointDataProtocol(Protocol):
    """Protocol defining the expected structure of point data."""

    frame: int
    x: float
    y: float
    interpolated: bool = False


# File Service Protocols
class FileServiceProtocol(Protocol):
    """Protocol defining the interface for file operations."""

    def export_to_csv(self, main_window: MainWindowProtocol) -> None: ...
    def load_track_data(self, main_window: MainWindowProtocol) -> None: ...
    def add_track_data(self, main_window: MainWindowProtocol) -> None: ...
    def save_track_data(self, main_window: MainWindowProtocol) -> None: ...
    def load_image_sequence(self, main_window: MainWindowProtocol) -> None: ...



class ImageServiceProtocol(Protocol):
    """Protocol defining the interface for image operations."""

    def set_current_image_by_frame(self, curve_view: CurveViewProtocol, frame: int) -> None: ...
    def load_current_image(self, curve_view: ImageSequenceProtocol) -> None: ...
    def set_current_image_by_index(self, curve_view: ImageSequenceProtocol, idx: int) -> None: ...
    def load_image_sequence(self, main_window: MainWindowProtocol) -> None: ...
    def set_image_sequence(self, curve_view: ImageSequenceProtocol, path: str, filenames: List[str]) -> None: ...


# History Service Protocols
class HistoryStateProtocol(Protocol):
    """Protocol defining the structure of a history state."""

    curve_data: PointsList
    point_name: str
    point_color: str


class HistoryContainerProtocol(Protocol):
    """Protocol defining the interface for a component that contains history."""

    history: List[Dict[str, Any]]
    history_index: int
    max_history_size: int
    undo_button: Any
    redo_button: Any
    curve_data: PointsList
    point_name: str
    point_color: str
    curve_view: CurveViewProtocol
    info_label: Any
    qwidget: QWidget  # Underlying QWidget for dialogs


class HistoryServiceProtocol(Protocol):
    """Protocol defining the interface for history operations."""

    def add_to_history(self, main_window: HistoryContainerProtocol) -> None: ...
    def update_history_buttons(self, main_window: HistoryContainerProtocol) -> None: ...
    def undo_action(self, main_window: HistoryContainerProtocol) -> None: ...
    def redo_action(self, main_window: HistoryContainerProtocol) -> None: ...
    def restore_state(self, main_window: HistoryContainerProtocol, state: Dict[str, Any]) -> None: ...


# Track Quality Protocols
class TrackQualityUIProtocol(MainWindowProtocol):
    """Protocol defining the interface for UI components used in track quality analysis.
    
    Extends MainWindowProtocol to support use with DialogService and other services
    that expect the MainWindowProtocol interface.
    """
    
    quality_score_label: Any
    smoothness_label: Any
    consistency_label: Any
    coverage_label: Any
    analyze_button: Any
    toggle_vectors_button: Any

# Dialog Service Protocols
class DialogServiceProtocol(Protocol):
    """Protocol defining the interface for dialog operations."""

    def show_smooth_dialog(
        self, parent_widget: Any, curve_data: PointsList, selected_indices: List[int],
        selected_point_idx: int
    ) -> Optional[PointsList]: ...

    def show_filter_dialog(self, main_window: MainWindowProtocol) -> None: ...
    def detect_gaps(self, main_window: MainWindowProtocol) -> List[Tuple[int, int]]: ...
    def show_fill_gaps_dialog(self, main_window: MainWindowProtocol) -> None: ...
    def fill_gap(self, main_window: MainWindowProtocol, start_frame: int, end_frame: int,
                method_index: int, preserve_endpoints: bool) -> None: ...
    def show_extrapolate_dialog(self, main_window: MainWindowProtocol) -> None: ...
    def show_shortcuts_dialog(self, main_window: MainWindowProtocol) -> None: ...
    def show_offset_dialog(self, main_window: MainWindowProtocol) -> Optional[PointsList]: ...
    def show_problem_detection_dialog(
        self, main_window: MainWindowProtocol, problems: Optional[List[Tuple[int, Any, Any, Any]]] = None
    ) -> Optional[Any]: ...


# Generic type for service method return values
T = TypeVar('T')
