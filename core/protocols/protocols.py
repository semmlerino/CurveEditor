#!/usr/bin/env python
"""Protocol definitions for CurveEditor components.

This module defines structural protocols that enforce interface consistency
across the application. These protocols help ensure type safety while allowing
flexibility in implementation, following the PEP 544 structural subtyping approach.

The protocols define contracts for various components:
- Image and curve view operations
- File and dialog services
- History management
- Track quality analysis

Example:
    Using protocols for type hints::

        def process_curve(view: CurveViewProtocol) -> None:
            view.set_curve_data(points)
            view.update()

Note:
    All protocols use @runtime_checkable to allow isinstance() checks at runtime.

"""
from __future__ import annotations

from typing import Protocol, Optional, Any, Tuple, List, Dict, Union, TypeVar, Set, runtime_checkable

from PySide6.QtCore import QRect, Signal
from PySide6.QtGui import QPixmap, QColor, QPaintEvent, QMouseEvent, QWheelEvent, QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QSlider, QLineEdit, 
    QStatusBar, QSpinBox, QComboBox, QSizePolicy, QSplitter
)

# Type aliases for common data structures
PointTuple = tuple[int, float, float]  # frame, x, y
PointTupleWithStatus = tuple[int, float, float, bool | str]  # frame, x, y, status (bool or str)
PointsList = list[PointTuple | PointTupleWithStatus]
VelocityData = list[tuple[float, float]]  # List of (vx, vy) velocity tuples

# Type aliases for Qt event types
PaintEventType = QPaintEvent
MouseEventType = QMouseEvent
WheelEventType = QWheelEvent
KeyEventType = QKeyEvent

# Type aliases for Qt Signal types
PointMovedSignal = Signal  # Signal[int, float, float]
PointSelectedSignal = Signal  # Signal[int]
ImageChangedSignal = Signal  # Signal[int]
SelectionChangedSignal = Signal  # Signal[list]

# Image Service Protocols
@runtime_checkable
class ImageSequenceProtocol(Protocol):
    """Protocol for image sequence handling components.

    Defines the interface for components that manage image sequences,
    including loading, navigation, and display properties.

    Attributes:
        image_sequence_path: Path to the current image sequence directory.
        current_image_idx: Index of the currently displayed image.
        image_filenames: List of image filenames in the sequence.
        image_width: Width of the current image in pixels.
        image_height: Height of the current image in pixels.
        zoom_factor: Current zoom level for image display.
        offset_x: Horizontal offset for image panning.
        offset_y: Vertical offset for image panning.
        selected_point_idx: Index of the currently selected point.
        background_image: The loaded background image object.
        scale_to_image: Whether to scale view to image dimensions.
        image_changed: Signal emitted when the current image changes.

    """
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
    background_image: Optional[QPixmap]
    scale_to_image: bool
    image_changed: ImageChangedSignal
    def emit(self, *args: Any, **kwargs: Any) -> None: ...
    def update(self) -> None: ...

@runtime_checkable
class CurveViewProtocol(ImageSequenceProtocol, Protocol):
    """Protocol defining the interface for curve view components.

    Extends ImageSequenceProtocol to provide curve editing functionality,
    including point manipulation, visualization options, and selection management.

    Attributes:
        x_offset: Horizontal offset for curve display.
        y_offset: Vertical offset for curve display.
        flip_y_axis: Whether to flip the Y-axis (image coordinates vs math coordinates).
        scale_to_image: Whether to scale curve to image dimensions.
        background_image: Optional background image for overlay.
        show_grid: Whether to display the grid overlay.
        show_velocity_vectors: Whether to display velocity vectors.
        show_all_frame_numbers: Whether to show frame numbers for all points.
        show_crosshair: Whether to display crosshair at cursor position.
        background_opacity: Opacity level for background image (0.0-1.0).
        point_radius: Radius of point markers in pixels.
        grid_color: Color of the grid lines.
        grid_line_width: Width of grid lines in pixels.
        curve_data: List of curve points with position and status.
        selected_points: Set of indices for selected points.
        frame_marker_label: UI label for frame marker display.
        timeline_slider: UI slider for timeline navigation.
        points: List of point data.
        nudge_increment: Current increment for nudging operations.
        current_increment_index: Index of current nudge increment.
        available_increments: List of available nudge increment values.
        main_window: Reference to main window for status updates.
        selection_rect: Rectangle for area selection.
        point_selected: Signal emitted when a point is selected.
        point_moved: Signal emitted when a point is moved.
        selection_changed: Signal emitted when selection changes.

    """
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

    # Common attributes
    x_offset: float
    y_offset: float
    flip_y_axis: bool
    scale_to_image: bool
    background_image: QPixmap | None  # Changed from Any to QPixmap

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
    selected_points: set[int]
    frame_marker_label: QLabel
    timeline_slider: QSlider
    points: PointsList  # Specific point data list
    nudge_increment: float
    current_increment_index: int
    available_increments: list[float]
    main_window: 'MainWindowProtocol'  # Reference to main window for status updates
    last_action_was_fit: bool  # Tracks if last action was fit-to-window
    # Selection rectangle
    selection_rect: QRect  # Properly typed as QRect
    # Signals
    point_selected: PointSelectedSignal
    point_moved: PointMovedSignal
    selection_changed: SelectionChangedSignal
    # Points manipulation
    def set_curve_data(self, curve_data: PointsList) -> None: ...
    def get_selected_indices(self) -> list[int]: ...
    def setPoints(self, points: PointsList, image_width: int = 0, image_height: int = 0, preserve_view: bool = False) -> None: ...
    def get_selected_points(self) -> list[int]: ...
    def setVelocityData(self, velocities: VelocityData) -> None: ...
    def toggleVelocityVectors(self, enabled: bool) -> None: ...
    
    # Qt Widget methods
    def setSizePolicy(self, h_policy: QSizePolicy.Policy, v_policy: QSizePolicy.Policy) -> None: ...
    def deleteLater(self) -> None: ...
    def width(self) -> int: ...
    def height(self) -> int: ...


class MainWindowProtocol(Protocol):
    """Protocol defining the interface for the main application window.

    This protocol ensures consistent interface for components that need to
    interact with the main window, including UI updates, data management,
    and application state.

    Attributes:
        image_sequence_path: Path to the current image sequence.
        image_filenames: List of loaded image filenames.
        image_label: UI label for image display.
        toggle_bg_button: Button for toggling background visibility.
        default_directory: Default directory for file operations.
        last_opened_file: Path to the last opened file.
        image_width: Width of the current image.
        image_height: Height of the current image.
        curve_view: The curve view component instance.
        curve_data: List of curve point data.
        point_name: Name of the current point set.
        point_color: Color for point display.
        status_bar: Application status bar widget.
        save_button: Save action button.
        add_point_button: Add point action button.
        smooth_button: Smooth curve action button.
        fill_gaps_button: Fill gaps action button.
        filter_button: Filter action button.
        detect_problems_button: Problem detection action button.
        extrapolate_button: Extrapolation action button.
        timeline_slider: Timeline navigation slider.
        frame_edit: Frame number input field.
        go_button: Go to frame button.
        info_label: Information display label.
        prev_image_button: Previous image navigation button.
        next_image_button: Next image navigation button.
        opacity_slider: Background opacity control slider.
        track_data_loaded: Whether track data has been loaded.

    """
    # For image_service compatibility
    image_sequence_path: str
    image_filenames: list[str]
    image_label: QLabel
    toggle_bg_button: QPushButton
    default_directory: str
    last_opened_file: str
    image_width: int
    image_height: int
    curve_view: CurveViewProtocol
    curve_data: PointsList
    point_name: str
    point_color: str
    status_bar: QStatusBar
    save_button: QPushButton
    add_point_button: QPushButton
    smooth_button: QPushButton
    fill_gaps_button: QPushButton
    filter_button: QPushButton
    detect_problems_button: QPushButton
    extrapolate_button: QPushButton
    timeline_slider: QSlider
    frame_edit: QLineEdit
    go_button: QPushButton
    info_label: QLabel
    prev_image_button: QPushButton
    next_image_button: QPushButton
    opacity_slider: QSlider
    track_data_loaded: bool
    
    # Additional UI components used throughout the application
    undo_button: QPushButton
    redo_button: QPushButton
    play_button: QPushButton
    prev_frame_button: QPushButton
    next_frame_button: QPushButton
    first_frame_button: QPushButton
    last_frame_button: QPushButton
    frame_label: QLabel
    point_radius_spinbox: QSpinBox
    precision_spinbox: QSpinBox
    
    # Smoothing UI components
    smoothing_apply_button: QPushButton
    smoothing_method_combo: QComboBox
    smoothing_window_spinbox: QSpinBox
    
    # Current state tracking
    current_frame: int
    selected_indices: list[int]
    history: list[dict[str, Any]]
    history_index: int
    max_history_size: int
    
    # UI layout components
    main_splitter: QSplitter
    curve_view_container: QWidget
    original_curve_view: CurveViewProtocol | None  # Original curve view reference
    
    # Visualization control buttons
    toggle_grid_button: QPushButton
    toggle_vectors_button: QPushButton
    toggle_frame_numbers_button: QPushButton
    toggle_crosshair_button: QPushButton
    center_on_point_button: QPushButton
    
    # Point size controls
    point_size_label: QLabel
    point_size_spin: QSpinBox
    
    # Nudge indicator
    nudge_indicator: QWidget
    
    # Missing UI components
    analyze_button: QPushButton
    apply_preset_button: QPushButton
    center_button: QPushButton
    export_button: QPushButton
    filter_preset_combo: QComboBox
    frame_info_label: QLabel
    frame_marker: QLabel
    load_button: QPushButton
    maximize_view_button: QPushButton
    playback_timer: Any  # QTimer from Qt
    presets_combo: QComboBox
    quality_consistency_label: QLabel
    quality_coverage_label: QLabel
    quality_score_label: QLabel
    quality_smoothness_label: QLabel
    reset_zoom_button: QPushButton
    toggle_background_button: QPushButton
    toggle_grid_view_button: QPushButton
    type_edit: QLineEdit
    type_label: QLabel
    update_point_button: QPushButton
    consistency_label: QLabel
    coverage_label: QLabel
    smoothness_label: QLabel
    curve_view_class: type[Any]  # Class type for curve view

    @property
    def qwidget(self) -> QWidget: ...
    def update_image_label(self) -> None: ...
    def statusBar(self) -> QStatusBar: ...
    def update_status_message(self, message: str) -> None: ...
    def refresh_point_edit_controls(self) -> None: ...
    def add_to_history(self) -> None: ...
    def setup_timeline(self) -> None: ...
    def setImageSequence(self, filenames: list[str]) -> None: ...
    def enable_point_controls(self, enabled: bool) -> None: ...
    def on_image_changed(self, index: int) -> None: ...
    def apply_ui_smoothing(self) -> None: ...
    def setCentralWidget(self, widget: QWidget) -> None: ...
    def setStatusBar(self, statusbar: QStatusBar) -> None: ...
    def set_centering_enabled(self, enabled: bool) -> None: ...
    def centralWidget(self) -> QWidget | None: ...
    def restoreGeometry(self, geometry: bytes) -> bool: ...
    def restoreState(self, state: bytes, version: int = 0) -> bool: ...
    def saveGeometry(self) -> bytes: ...
    def saveState(self, version: int = 0) -> bytes: ...



class ImageProtocol(Protocol):
    """Protocol defining the interface for image objects.

    This protocol is compatible with QPixmap and other image types
    that provide width() and height() methods.

    Methods:
        width: Returns the width of the image in pixels.
        height: Returns the height of the image in pixels.

    Example:
        def process_image(image: ImageProtocol) -> Tuple[int, int]:
            return image.width(), image.height()

    """

    def width(self) -> int: ...
    def height(self) -> int: ...


class PointDataProtocol(Protocol):
    """Protocol defining the expected structure of point data.

    This protocol defines the standard structure for tracking points
    in the curve editor, including position and interpolation status.

    Attributes:
        frame: The frame number where this point exists.
        x: The x-coordinate of the point.
        y: The y-coordinate of the point.
        interpolated: Whether this point was interpolated (default: False).

    Example:
        class TrackPoint:
            def __init__(self, frame: int, x: float, y: float):
                self.frame = frame
                self.x = x
                self.y = y
                self.interpolated = False

    """

    frame: int
    x: float
    y: float
    interpolated: bool = False


# File Service Protocols
class FileServiceProtocol(Protocol):
    """Protocol defining the interface for file operations.

    This protocol ensures consistent file operation interfaces across
    the application, including import/export and data persistence.

    Methods:
        export_to_csv: Exports curve data to CSV format.
        load_track_data: Loads tracking data from a file.
        add_track_data: Adds additional tracking data to existing data.
        save_track_data: Saves current tracking data to a file.
        load_image_sequence: Loads a sequence of images for background display.

    Example:
        def save_project(file_service: FileServiceProtocol,
                        main_window: MainWindowProtocol) -> None:
            file_service.save_track_data(main_window)

    """

    def export_to_csv(self, main_window: MainWindowProtocol) -> None: ...
    def load_track_data(self, main_window: MainWindowProtocol) -> None: ...
    def add_track_data(self, main_window: MainWindowProtocol) -> None: ...
    def save_track_data(self, main_window: MainWindowProtocol) -> None: ...
    def load_image_sequence(self, main_window: MainWindowProtocol) -> None: ...



class ImageServiceProtocol(Protocol):
    """Protocol defining the interface for image operations.

    This protocol provides a consistent interface for image-related
    operations including loading, navigation, and sequence management.

    Methods:
        set_current_image_by_frame: Sets the current image based on frame number.
        load_current_image: Loads the currently selected image.
        set_current_image_by_index: Sets the current image by its index.
        load_image_sequence: Loads a sequence of images from the file system.
        set_image_sequence: Sets the image sequence with path and filenames.

    Example:
        def navigate_to_frame(image_service: ImageServiceProtocol,
                            curve_view: CurveViewProtocol,
                            frame: int) -> None:
            image_service.set_current_image_by_frame(curve_view, frame)

    """

    def set_current_image_by_frame(self, curve_view: CurveViewProtocol, frame: int) -> None: ...
    def load_current_image(self, curve_view: ImageSequenceProtocol) -> None: ...
    def set_current_image_by_index(self, curve_view: ImageSequenceProtocol, idx: int) -> None: ...
    def load_image_sequence(self, main_window: MainWindowProtocol) -> None: ...
    def set_image_sequence(self, curve_view: ImageSequenceProtocol, path: str, filenames: List[str]) -> None: ...


# History Service Protocols
class HistoryStateProtocol(Protocol):
    """Protocol defining the structure of a history state.

    This protocol defines the data structure for storing application
    state snapshots in the undo/redo history system.

    Attributes:
        curve_data: List of curve points at this state.
        point_name: Name identifier for the point set.
        point_color: Color used to display the points.

    Example:
        class HistoryState:
            def __init__(self, data: PointsList, name: str, color: str):
                self.curve_data = data
                self.point_name = name
                self.point_color = color

    """

    curve_data: PointsList
    point_name: str
    point_color: str


class HistoryContainerProtocol(Protocol):
    """Protocol defining the interface for a component that contains history.

    This protocol defines the requirements for components that manage
    undo/redo history, including state storage and UI elements.

    Attributes:
        history: List of historical states stored as dictionaries.
        history_index: Current position in the history list.
        max_history_size: Maximum number of states to retain.
        undo_button: UI button for undo action.
        redo_button: UI button for redo action.
        curve_data: Current curve point data.
        point_name: Current point set name.
        point_color: Current point display color.
        curve_view: The curve view component for display updates.
        info_label: UI label for displaying information.

    Properties:
        qwidget: Returns the underlying QWidget for dialog operations.

    Example:
        def can_undo(container: HistoryContainerProtocol) -> bool:
            return container.history_index > 0

    """

    history: list[dict[str, Any]]
    history_index: int
    max_history_size: int
    undo_button: QPushButton
    redo_button: QPushButton
    curve_data: PointsList
    point_name: str
    point_color: str
    curve_view: CurveViewProtocol
    info_label: QLabel

    @property
    def qwidget(self) -> QWidget: ...  # Underlying QWidget for dialogs


class HistoryServiceProtocol(Protocol):
    """Protocol defining the interface for history operations.

    This protocol provides methods for managing undo/redo functionality,
    including state capture, restoration, and UI synchronization.

    Methods:
        add_to_history: Captures current state and adds it to history.
        update_history_buttons: Updates the enabled state of undo/redo buttons.
        undo_action: Reverts to the previous state in history.
        redo_action: Advances to the next state in history.
        restore_state: Restores the application to a specific saved state.

    Example:
        def save_checkpoint(history_service: HistoryServiceProtocol,
                          main_window: HistoryContainerProtocol) -> None:
            history_service.add_to_history(main_window)
            history_service.update_history_buttons(main_window)

    """

    def add_to_history(self, main_window: HistoryContainerProtocol) -> None: ...
    def update_history_buttons(self, main_window: HistoryContainerProtocol) -> None: ...
    def undo_action(self, main_window: HistoryContainerProtocol) -> None: ...
    def redo_action(self, main_window: HistoryContainerProtocol) -> None: ...
    def restore_state(self, main_window: HistoryContainerProtocol, state: Dict[str, Any]) -> None: ...


# Track Quality Protocols
class TrackQualityUIProtocol(MainWindowProtocol, Protocol):
    """Protocol defining the interface for UI components used in track quality analysis.

    Extends MainWindowProtocol to support use with DialogService and other services
    that expect the MainWindowProtocol interface.
    """

    quality_score_label: QLabel
    smoothness_label: QLabel
    consistency_label: QLabel
    coverage_label: QLabel
    analyze_button: QPushButton
    toggle_vectors_button: QPushButton

# Dialog Service Protocols
class DialogServiceProtocol(Protocol):
    """Protocol defining the interface for dialog operations.

    This protocol provides methods for displaying various dialogs
    throughout the application, including smoothing, filtering,
    gap detection, and other curve editing operations.

    Methods:
        show_smooth_dialog: Displays smoothing options for selected points.
        show_filter_dialog: Shows filtering options for curve data.
        detect_gaps: Identifies gaps in the curve data.
        show_fill_gaps_dialog: Displays gap filling options.
        fill_gap: Fills a specific gap using the selected method.
        show_extrapolate_dialog: Shows extrapolation options.
        show_shortcuts_dialog: Displays keyboard shortcuts reference.
        show_offset_dialog: Shows offset adjustment options.
        show_problem_detection_dialog: Displays detected problems in curve data.

    Example:
        def smooth_selection(dialog_service: DialogServiceProtocol,
                           main_window: MainWindowProtocol) -> None:
            smoothed = dialog_service.show_smooth_dialog(
                main_window.qwidget,
                main_window.curve_data,
                main_window.curve_view.get_selected_indices(),
                main_window.curve_view.selected_point_idx
            )
            if smoothed:
                main_window.curve_data = smoothed

    """

    def show_smooth_dialog(
        self, parent_widget: QWidget, curve_data: PointsList, selected_indices: List[int],
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


@runtime_checkable
class SmoothingServiceProtocol(Protocol):
    """Protocol for smoothing operations on curve data."""
    
    def smooth_moving_average(self, data: PointsList, indices: list[int], window_size: int) -> PointsList: ...
    def smooth_gaussian(self, data: PointsList, indices: list[int], window_size: int, sigma: float) -> PointsList: ...
    def apply_spline(self, data: PointsList, control_indices: list[int]) -> PointsList: ...


@runtime_checkable  
class FilteringServiceProtocol(Protocol):
    """Protocol for filtering operations on curve data."""
    
    def filter_median(self, data: PointsList, indices: list[int], window_size: int) -> PointsList: ...
    def filter_butterworth(self, data: PointsList, indices: list[int], cutoff: float, order: int) -> PointsList: ...
    def remove_duplicates(self, data: PointsList) -> tuple[PointsList, int]: ...


@runtime_checkable
class GapFillingServiceProtocol(Protocol):
    """Protocol for gap filling operations on curve data."""
    
    def fill_gap_linear(self, data: PointsList, start_frame: int, end_frame: int) -> PointsList: ...
    def fill_gap_spline(self, data: PointsList, start_frame: int, end_frame: int) -> PointsList: ...
    def fill_constant_velocity(self, data: PointsList, start_frame: int, end_frame: int) -> PointsList: ...
    def fill_accelerated_motion(self, data: PointsList, start_frame: int, end_frame: int) -> PointsList: ...
    def fill_average(self, data: PointsList, start_frame: int, end_frame: int, window_size: int) -> PointsList: ...


@runtime_checkable
class ExtrapolationServiceProtocol(Protocol):
    """Protocol for extrapolation operations on curve data."""
    
    def extrapolate_forward(self, data: PointsList, num_frames: int, method: int, fit_points: int) -> PointsList: ...
    def extrapolate_backward(self, data: PointsList, num_frames: int, method: int, fit_points: int) -> PointsList: ...
    def interpolate_missing_frames(self, data: PointsList) -> PointsList: ...


@runtime_checkable
class GeometryServiceProtocol(Protocol):
    """Protocol for geometric operations on curve data."""
    
    def rotate_curve(self, data: PointsList, angle_degrees: float, 
                    center_x: Optional[float] = None, center_y: Optional[float] = None) -> PointsList: ...
    def offset_points(self, data: PointsList, indices: list[int], dx: float, dy: float) -> PointsList: ...
    def normalize_velocity(self, data: PointsList, target_velocity: float) -> PointsList: ...


@runtime_checkable
class ProblemDetectionServiceProtocol(Protocol):
    """Protocol for problem detection and analysis operations."""
    
    def detect_problems(self, data: PointsList) -> dict[int, dict[str, str]]: ...
    def find_velocity_outliers(self, data: PointsList, threshold_factor: float) -> list[int]: ...
    def calculate_curvature(self, data: PointsList) -> list[float]: ...
