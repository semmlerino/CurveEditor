"""
UI component protocols for CurveEditor.

This module contains Protocol definitions for UI components like MainWindow,
CurveView, and related widgets. These protocols define the interface contracts
that UI components must implement.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QPushButton, QRubberBand, QStatusBar

from protocols.data import CurveDataInput, CurveDataList, HistoryState, QtPointF

# Import authoritative SignalProtocol from protocols.services
# to avoid duplicate incompatible definitions
from protocols.services import SignalProtocol  # noqa: F401 - re-exported for convenience


class StateManagerProtocol(Protocol):
    """Protocol for state manager."""

    is_modified: bool
    auto_center_enabled: bool

    @property
    def current_frame(self) -> int:
        """Get current frame."""
        ...

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        """Set current frame."""
        ...

    @property
    def active_timeline_point(self) -> str | None:
        """Get the active timeline point (which tracking point's timeline is displayed)."""
        ...

    @active_timeline_point.setter
    def active_timeline_point(self, value: str | None) -> None:
        """Set the active timeline point (which tracking point's timeline to display)."""
        ...

    @property
    def image_directory(self) -> str | None:
        """Get image directory."""
        ...

    # Methods needed by file_operations_manager.py
    @property
    def current_file(self) -> str | None:
        """Get current file path."""
        ...

    @current_file.setter
    def current_file(self, value: str | None) -> None:
        """Set current file path."""
        ...

    @image_directory.setter
    def image_directory(self, value: str | None) -> None:
        """Set image directory."""
        ...

    @property
    def track_data(self) -> object | None:  # CurveDataList | CurveDataWithMetadata
        """Get track data."""
        ...

    @property
    def total_frames(self) -> int:
        """Get total frames."""
        ...

    @total_frames.setter
    def total_frames(self, value: int) -> None:
        """Set total frames."""
        ...

    def reset_to_defaults(self) -> None:
        """Reset state to defaults."""
        ...

    def set_track_data(self, data: object, mark_modified: bool) -> None:
        """Set track data."""
        ...

    def set_image_files(self, files: list[str]) -> None:
        """Set image files."""
        ...

    def get_window_title(self) -> str:
        """Get window title."""
        ...

    def set_selected_points(self, indices: list[int]) -> None:
        """Set selected point indices."""
        ...

    def undo(self) -> None:
        """Undo the last operation."""
        ...

    def redo(self) -> None:
        """Redo the last undone operation."""
        ...

    def set_history_state(self, can_undo: bool, can_redo: bool, position: int, size: int) -> None:
        """Update history state information for UI indicators."""
        ...


class CurveViewProtocol(Protocol):
    """Protocol for curve view widgets.

    Unified interface that curve view widgets must implement
    to work with services and controllers.
    """

    # Basic attributes
    selected_point_idx: int
    curve_data: CurveDataList
    current_image_idx: int

    # Point management
    points: CurveDataList
    selected_points: set[int]

    # Transform and positioning
    offset_x: float
    offset_y: float
    x_offset: float  # Alias for offset_x
    y_offset: float  # Alias for offset_y
    zoom_factor: float
    pan_offset_x: float
    pan_offset_y: float
    manual_offset_x: float
    manual_offset_y: float

    # Interaction state
    drag_active: bool
    pan_active: bool
    last_drag_pos: QtPointF | None
    last_pan_pos: QtPointF | None

    # Rubber band selection
    rubber_band: "QRubberBand | None"
    rubber_band_active: bool
    rubber_band_origin: QtPointF

    # Visualization settings
    show_grid: bool
    show_background: bool
    show_velocity_vectors: bool
    show_all_frame_numbers: bool

    # Background image
    background_image: "QPixmap | None"
    background_opacity: float

    # Image and display settings
    image_width: int
    image_height: int
    scale_to_image: bool
    flip_y_axis: bool

    # Parent reference
    main_window: "MainWindowProtocol"

    # Qt signals
    point_selected: SignalProtocol
    point_moved: SignalProtocol

    # Methods
    def update(self) -> None:
        """Update the view."""
        ...

    def repaint(self) -> None:
        """Repaint the view."""
        ...

    def width(self) -> int:
        """Get widget width."""
        ...

    def height(self) -> int:
        """Get widget height."""
        ...

    def setCursor(self, cursor: object) -> None:
        """Set widget cursor."""
        ...

    def unsetCursor(self) -> None:
        """Unset widget cursor."""
        ...

    def findPointAt(self, pos: QtPointF) -> int:
        """Find point at the given position."""
        ...

    def selectPointByIndex(self, idx: int) -> bool:
        """Select a point by its index."""
        ...

    def get_current_transform(self) -> object:
        """Get current transform object."""
        ...

    def get_transform(self) -> object:
        """Get transform object (alias for compatibility)."""
        ...

    def _invalidate_caches(self) -> None:
        """Invalidate any cached data."""
        ...

    def get_point_data(self, idx: int) -> tuple[int, float, float, str | None]:
        """Get point data for the given index."""
        ...

    def toggleBackgroundVisible(self, visible: bool) -> None:
        """Toggle background visibility."""
        ...

    def toggle_point_interpolation(self, idx: int) -> None:
        """Toggle interpolation status of a point."""
        ...

    def set_curve_data(self, data: CurveDataInput) -> None:
        """Set the curve data."""
        ...

    def setPoints(self, data: CurveDataList, width: int, height: int) -> None:
        """Set points with image dimensions (legacy compatibility)."""
        ...

    def set_selected_indices(self, indices: list[int]) -> None:
        """Set the selected point indices."""
        ...

    def setup_for_3dequalizer_data(self) -> None:
        """Set up the view for 3DEqualizer coordinate tracking data."""
        ...

    def setup_for_pixel_tracking(self) -> None:
        """Set up the view for screen/pixel-coordinate tracking data."""
        ...


class MultiCurveViewProtocol(CurveViewProtocol, Protocol):
    """
    Protocol for widgets that display and manipulate multiple curves.

    This protocol extends CurveViewProtocol with multi-curve specific
    attributes and methods added in Phase 8.

    Key Features:
    - Multiple curve display and selection
    - Active curve management
    - Per-curve visibility control
    - Curve metadata management

    Example Usage:
        view: MultiCurveViewProtocol = CurveViewWidget()

        # Set multiple curves
        curves = {
            "pp56_TM_138G": [(1, 10.0, 20.0), (2, 15.0, 25.0)],
            "pp53_TM_134G": [(1, 30.0, 40.0), (2, 35.0, 45.0)],
        }
        view.set_curves_data(curves)

        # Set active curve for editing
        view.set_active_curve("pp56_TM_138G")

        # Set display mode
        view.widget.display_mode = DisplayMode.ALL_VISIBLE
    """

    # Multi-curve state
    active_curve_name: str | None
    """Name of the currently active curve for editing."""

    curves_data: dict[str, CurveDataList]
    """Dictionary mapping curve names to their data."""

    selected_curve_names: set[str]
    """Set of selected curve names (for multi-curve selection)."""

    selected_curves_ordered: list[str]
    """Ordered list of selected curves (preserves selection order)."""

    # Multi-curve methods
    def set_curves_data(
        self,
        curves: dict[str, CurveDataList],
        metadata: dict[str, dict[str, object]] | None = None,
        active_curve: str | None = None,
        selected_curves: list[str] | None = None,
    ) -> None:
        """
        Set multiple curves with optional metadata.

        Args:
            curves: Dictionary mapping curve names to curve data
            metadata: Optional per-curve metadata (visibility, color, etc.)
            active_curve: Optional active curve name to set
            selected_curves: Optional list of selected curve names
        """
        ...

    def add_curve(self, name: str, data: CurveDataList, metadata: dict[str, object] | None = None) -> None:
        """
        Add a single curve to the view.

        Args:
            name: Unique curve identifier
            data: Curve data points
            metadata: Optional curve metadata
        """
        ...

    def remove_curve(self, name: str) -> None:
        """
        Remove a curve from the view.

        Args:
            name: Curve name to remove
        """
        ...

    def set_active_curve(self, name: str) -> None:
        """
        Set the active curve for editing.

        Args:
            name: Curve name to activate
        """
        ...

    def set_selected_curves(self, curve_names: list[str]) -> None:
        """
        Set the selected curves.

        Args:
            curve_names: List of curve names to select
        """
        ...

    def update_curve_visibility(self, curve_name: str, visible: bool) -> None:
        """
        Update visibility of a specific curve.

        Args:
            curve_name: Curve to update
            visible: True to show, False to hide
        """
        ...

    def update_curve_color(self, curve_name: str, color: tuple[int, int, int]) -> None:
        """
        Update color of a specific curve.

        Args:
            curve_name: Curve to update
            color: RGB color tuple (0-255)
        """
        ...

    def get_curve_metadata(self, curve_name: str) -> dict[str, object]:
        """
        Get metadata for a specific curve.

        Args:
            curve_name: Curve name

        Returns:
            Dictionary of metadata (visibility, color, etc.)
        """
        ...

    def center_on_selected_curves(self) -> None:
        """Center the view on all selected curves."""
        ...


class MainWindowProtocol(Protocol):
    """Protocol for main window widgets.

    Consolidated interface that main window widgets must implement
    to work with services and controllers. This merges 6+ duplicate
    definitions into one authoritative protocol.
    """

    # Basic attributes
    @property
    def selected_indices(self) -> list[int]:
        """Get list of selected point indices."""
        ...

    @selected_indices.setter
    def selected_indices(self, value: list[int]) -> None:
        """Set list of selected point indices."""
        ...

    curve_view: CurveViewProtocol

    @property
    def curve_data(self) -> CurveDataList:
        """Get curve data."""
        ...

    @curve_data.setter
    def curve_data(self, value: CurveDataList) -> None:
        """Set curve data."""
        ...

    curve_widget: CurveViewProtocol | None  # CurveViewWidget (replaces deprecated curve_view)

    # Frame management
    @property
    def current_frame(self) -> int:
        """Get the current frame number."""
        ...

    # History management
    history: list[object]
    history_index: int
    max_history_size: int

    # Point attributes
    point_name: str
    point_color: str

    # UI component references
    undo_button: "QPushButton | None"
    redo_button: "QPushButton | None"
    save_button: "QPushButton | None"
    ui_components: object
    _point_spinbox_connected: bool
    file_operations: object  # FileOperations instance

    # Service references (readonly to allow covariance)
    @property
    def services(self) -> object:
        """Get services facade."""
        ...

    # State management (readonly to allow covariance)
    @property
    def state_manager(self) -> StateManagerProtocol:
        """Get state manager."""
        ...

    @property
    def is_modified(self) -> bool:
        """Get modified state."""
        ...

    # Methods
    def add_to_history(self) -> None:
        """Add current state to history."""
        ...

    def restore_state(self, state: HistoryState) -> None:
        """Restore state from history."""
        ...

    def update_status(self, message: str) -> None:
        """Update status bar message."""
        ...

    def setWindowTitle(self, title: str) -> None:
        """Set window title."""
        ...

    def statusBar(self) -> "QStatusBar":
        """Get status bar widget."""
        ...

    def close(self) -> bool:
        """Close the window."""
        ...

    def set_centering_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-centering on frame change."""
        ...

    def apply_smooth_operation(self) -> None:
        """Apply smoothing operation to selected points."""
        ...

    # Controller friend methods (Strangler Fig pattern)
    def _get_current_frame(self) -> int:
        """Get current frame (controller friend method)."""
        ...

    def _set_current_frame(self, frame: int) -> None:
        """Set current frame (controller friend method)."""
        ...

    # Methods needed by controllers
    def update_timeline_tabs(self, curve_data: object | None) -> None:
        """Update timeline tabs."""
        ...

    def update_tracking_panel(self) -> None:
        """Update tracking panel display."""
        ...

    def update_ui_state(self) -> None:
        """Update UI state."""
        ...

    def update_zoom_label(self) -> None:
        """Update zoom level label."""
        ...

    def _get_current_curve_data(self) -> CurveDataList:
        """Get current curve data (controller friend method)."""
        ...

    # Properties needed by controllers
    @property
    def shortcut_manager(self) -> "ShortcutManagerProtocol | None":
        """Get shortcut manager."""
        ...

    @property
    def multi_point_controller(self) -> "MultiPointTrackingProtocol":
        """Get multi-point tracking controller (alias for tracking_controller)."""
        ...

    # UI widget attributes (initialized by UIInitializationController)
    fps_spinbox: object | None  # QSpinBox
    btn_play_pause: object | None  # QPushButton
    timeline_tabs: object | None  # QTabWidget

    @property
    def curve_view(self) -> "CurveViewProtocol | None":
        """Get curve view (deprecated, use curve_widget)."""
        ...

    # Frame navigation widget attributes
    frame_spinbox: object | None  # QSpinBox
    frame_slider: object | None  # QSlider

    @property
    def image_filenames(self) -> list[str]:
        """Get image filenames."""
        ...

    @image_filenames.setter
    def image_filenames(self, value: list[str]) -> None:
        """Set image filenames."""
        ...

    # File operations manager properties
    @property
    def file_load_worker(self) -> object | None:  # FileLoadWorkerProtocol
        """Get file load worker."""
        ...

    @property
    def total_frames_label(self) -> object | None:  # QLabel
        """Get total frames label."""
        ...

    @property
    def tracked_data(self) -> dict[str, object]:  # dict[str, CurveDataList]
        """Get tracked data."""
        ...

    @tracked_data.setter
    def tracked_data(self, value: dict[str, object]) -> None:
        """Set tracked data."""
        ...

    @property
    def active_points(self) -> list[str]:
        """Get active points."""
        ...

    @active_points.setter
    def active_points(self, value: list[str]) -> None:
        """Set active points."""
        ...

    @property
    def active_timeline_point(self) -> str | None:
        """Get the active timeline point (which tracking point's timeline is displayed)."""
        ...

    @active_timeline_point.setter
    def active_timeline_point(self, value: str | None) -> None:
        """Set the active timeline point (which tracking point's timeline to display)."""
        ...

    @property
    def session_manager(self) -> object:  # SessionManagerProtocol
        """Get session manager."""
        ...

    @property
    def view_update_manager(self) -> object:
        """Get view update manager."""
        ...

    @property
    def current_image_idx(self) -> int:
        """Get current image index."""
        ...

    @current_image_idx.setter
    def current_image_idx(self, value: int) -> None:
        """Set current image index."""
        ...

    def geometry(self) -> object:  # QRect
        """Get window geometry."""
        ...

    def set_tracked_data_atomic(self, data: dict[str, object]) -> None:
        """Set tracked data atomically."""
        ...

    def set_file_loading_state(self, loading: bool) -> None:
        """Set file loading state."""
        ...

    # Event coordinator integration
    def play_toggled(self) -> object:  # Signal
        """Signal emitted when play is toggled."""
        ...

    def frame_rate_changed(self) -> object:  # Signal
        """Signal emitted when frame rate changes."""
        ...


class CurveWidgetProtocol(Protocol):
    """Protocol for curve widget components."""

    curve_view: CurveViewProtocol

    def update(self) -> None:
        """Update the widget."""
        ...

    def repaint(self) -> None:
        """Repaint the widget."""
        ...

    # Frame navigation controller methods
    def on_frame_changed(self, frame: int) -> None:
        """Handle frame change for centering mode."""
        ...

    def invalidate_caches(self) -> None:
        """Invalidate rendering caches."""
        ...

    @property
    def background_image(self) -> object:  # QPixmap | None
        """Get background image."""
        ...

    @background_image.setter
    def background_image(self, value: object) -> None:  # QPixmap
        """Set background image."""
        ...

    # Methods needed by file_operations_manager.py
    def set_curve_data(self, data: object) -> None:  # CurveDataList | CurveDataWithMetadata
        """Set curve data."""
        ...

    def setup_for_pixel_tracking(self) -> None:
        """Set up for pixel tracking mode."""
        ...

    def setup_for_3dequalizer_data(self) -> None:
        """Set up for 3DEqualizer data mode."""
        ...

    def fit_to_view(self) -> None:
        """Fit view to data."""
        ...

    def set_background_image(self, pixmap: object) -> None:  # QPixmap
        """Set background image."""
        ...

    def fit_to_background_image(self) -> None:
        """Fit view to background image."""
        ...

    @property
    def curve_data(self) -> object | None:  # CurveDataList | CurveDataWithMetadata
        """Get curve data."""
        ...

    @property
    def show_background(self) -> bool:
        """Get show background flag."""
        ...

    @show_background.setter
    def show_background(self, value: bool) -> None:
        """Set show background flag."""
        ...


class CommandManagerProtocol(Protocol):
    """Protocol for command manager components."""

    def execute_command(self, command: str, *args: object) -> None:
        """Execute a command."""
        ...

    def execute(self, command: object) -> bool:
        """Execute a command object and add to history."""
        ...

    def can_undo(self) -> bool:
        """Check if undo is available."""
        ...

    def can_redo(self) -> bool:
        """Check if redo is available."""
        ...

    def undo(self) -> None:
        """Undo the last command."""
        ...

    def redo(self) -> None:
        """Redo the last undone command."""
        ...


class FrameNavigationProtocol(Protocol):
    """Protocol for frame navigation components."""

    def navigate_to_frame(self, frame: int) -> None:
        """Navigate to specific frame."""
        ...

    def jump_frames(self, delta: int) -> None:
        """Jump by delta frames."""
        ...

    def next_frame(self) -> None:
        """Go to next frame."""
        ...

    def previous_frame(self) -> None:
        """Go to previous frame."""
        ...

    def first_frame(self) -> None:
        """Go to first frame."""
        ...

    def last_frame(self) -> None:
        """Go to last frame."""
        ...


class MultiPointTrackingProtocol(Protocol):
    """Protocol for multi-point tracking controller."""

    tracked_data: dict[str, CurveDataList]

    def update_tracking_panel(self) -> None:
        """Update the tracking panel display."""
        ...


class ShortcutManagerProtocol(Protocol):
    """Protocol for shortcut manager components."""

    def register_shortcut(self, key: str, action: Callable[[], None]) -> None:
        """Register a keyboard shortcut."""
        ...

    def unregister_shortcut(self, key: str) -> None:
        """Unregister a keyboard shortcut."""
        ...

    def trigger_shortcut(self, key: str) -> bool:
        """Trigger shortcut action if registered."""
        ...

    def show_shortcuts(self) -> None:
        """Show shortcuts dialog/help."""
        ...


class WidgetProtocol(Protocol):
    """Protocol for generic Qt widgets."""

    def update(self) -> None:
        """Update the widget."""
        ...

    def repaint(self) -> None:
        """Repaint the widget."""
        ...

    def width(self) -> int:
        """Get widget width."""
        ...

    def height(self) -> int:
        """Get widget height."""
        ...

    def setVisible(self, visible: bool) -> None:
        """Set widget visibility."""
        ...

    def isVisible(self) -> bool:
        """Check if widget is visible."""
        ...


class EventProtocol(Protocol):
    """Protocol for Qt events."""

    def accept(self) -> None:
        """Accept the event."""
        ...

    def ignore(self) -> None:
        """Ignore the event."""
        ...

    def isAccepted(self) -> bool:
        """Check if event is accepted."""
        ...

    def pos(self) -> "QPoint":
        """Get event position."""
        ...

    def globalPos(self) -> "QPoint":
        """Get global event position."""
        ...

    def modifiers(self) -> object:
        """Get keyboard modifiers."""
        ...
