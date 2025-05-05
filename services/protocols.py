#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Protocols for CurveEditor components.

This module defines structural protocols that enforce interface consistency
across the application. These protocols help ensure type safety while allowing
flexibility in implementation.
"""

from typing import Protocol, Optional, Any, Tuple, List, Dict, Union, TypeVar, cast, Set


class CurveViewProtocol(Protocol):
    """Protocol defining the interface for curve view components."""

    # Common attributes
    x_offset: float
    y_offset: float
    flip_y_axis: bool
    scale_to_image: bool
    background_image: Optional[Any]
    image_width: int
    image_height: int
    zoom_factor: float

    # Required methods
    def update(self) -> None: ...
    def setPoints(self, points: List[Tuple[int, float, float]]) -> None: ...
    def get_selected_points(self) -> List[int]: ...


class MainWindowProtocol(Protocol):
    """Protocol defining the interface for the main window."""

    # Required attributes
    curve_view: CurveViewProtocol

    # Required methods
    def update_status_message(self, message: str) -> None: ...
    def refresh_point_edit_controls(self) -> None: ...


class ImageProtocol(Protocol):
    """Protocol defining the interface for image objects."""

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
    background_image: Optional[ImageProtocol]
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


# Type aliases for common data structures
PointTuple = Tuple[int, float, float]  # frame, x, y
PointTupleWithStatus = Tuple[int, float, float, bool]  # frame, x, y, interpolated
PointsList = List[Union[PointTuple, PointTupleWithStatus]]

# Generic type for service method return values
T = TypeVar('T')
