#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Protocols for CurveEditor components.

This module defines structural protocols that enforce interface consistency
across the application. These protocols help ensure type safety while allowing
flexibility in implementation.
"""

from typing import Protocol, Optional, Any, Tuple, List, Dict, Union, TypeVar, Set
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import QRect

# Type aliases for common data structures
PointTuple = Tuple[int, float, float]  # frame, x, y
PointTupleWithStatus = Tuple[int, float, float, bool]  # frame, x, y, interpolated
PointsList = List[Union[PointTuple, PointTupleWithStatus]]


class CurveViewProtocol(Protocol):
    """Protocol defining the interface for curve view components."""

    # Common attributes
    x_offset: float
    y_offset: float
    flip_y_axis: bool
    scale_to_image: bool
    background_image: Optional[QPixmap]  # Changed from Any to QPixmap
    image_width: int
    image_height: int
    zoom_factor: float

    # Visualization attributes (added for type safety)
    show_background: bool
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
    selected_point_idx: int
    selected_points: Set[int]
    frame_marker_label: Any
    timeline_slider: Any
    points: List[Union[PointTuple, PointTupleWithStatus]]  # Specific point data list
    main_window: Any  # Reference to main window
    nudge_increment: float
    current_increment_index: int
    available_increments: List[float]
    image_filenames: List[str]  # Added for extract_frame_number
    
    # Selection rectangle
    selection_rect: QRect  # Properly typed as QRect
    
    # Pan/offset attributes
    offset_x: float
    offset_y: float
    
    # Signals
    point_selected: Any  # Signal
    point_moved: Any  # Signal
    selection_changed: Any  # Signal
    
    # Methods for points manipulation
    def set_curve_data(self, curve_data: PointsList) -> None: ...
    def get_selected_indices(self) -> List[int]: ...

    # Required methods
    def update(self) -> None: ...
    def setPoints(self, points: List[Tuple[Any, ...]], image_width: int = 0, 
                 image_height: int = 0, preserve_view: bool = False) -> None: ...
    def get_selected_points(self) -> List[int]: ...
    def setVelocityData(self, velocities: Any) -> None: ...
    def toggleVelocityVectors(self, enabled: bool) -> None: ...


class MainWindowProtocol(Protocol):
    """Protocol defining the interface for the main window."""

    # Required attributes
    curve_view: Optional[CurveViewProtocol]
    quality_score_label: Any
    smoothness_label: Any
    consistency_label: Any
    coverage_label: Any
    curve_data: PointsList
    analyze_button: Any
    toggle_vectors_button: Any
    
    # Required methods that match QMainWindow behavior
    def statusBar(self) -> Any: ...
    # Add a property to get the underlying QWidget for QMessageBox
    @property
    def widget(self) -> Any: ...

    # Required methods
    def update_status_message(self, message: str) -> None: ...
    def refresh_point_edit_controls(self) -> None: ...


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


# Image Service Protocols
class ImageSequenceProtocol(Protocol):
    """Protocol defining the interface for image sequence operations."""

    image_filenames: List[str]
    image_sequence_path: str
    current_image_idx: int
    background_image: Optional[QPixmap]  # Changed from ImageProtocol to QPixmap
    scale_to_image: bool

    def update(self) -> None: ...


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
