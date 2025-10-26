"""
UI component protocols for CurveEditor.

This module contains Protocol definitions for UI components like MainWindow,
CurveView, and related widgets. These protocols define the interface contracts
that UI components must implement.
"""

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QPushButton, QRubberBand, QStatusBar

    from ui.protocols.controller_protocols import TimelineControllerProtocol

from protocols.data import CurveDataInput, CurveDataList, HistoryState, QtPointF

# Import authoritative SignalProtocol from protocols.services
# to avoid duplicate incompatible definitions
from protocols.services import SignalProtocol


class StateManagerProtocol(Protocol):
    """Protocol for state manager.

    StateManager owns UI preferences and view state only.
    ApplicationState owns all application data (curves, images, frames).

    This protocol was updated to match the StateManager Simplified Migration
    which separated UI state (StateManager) from application data (ApplicationState).
    """

    @property
    def is_modified(self) -> bool:
        """Get the modification status."""
        ...

    @is_modified.setter
    def is_modified(self, modified: bool) -> None:
        """Set the modification status."""
        ...

    @property
    def current_frame(self) -> int:
        """Get current frame (delegates to ApplicationState)."""
        ...

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        """Set current frame (delegates to ApplicationState)."""
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

    @image_directory.setter
    def image_directory(self, value: str | None) -> None:
        """Set image directory."""
        ...

    @property
    def current_file(self) -> str | None:
        """Get current file path."""
        ...

    @current_file.setter
    def current_file(self, value: str | None) -> None:
        """Set current file path."""
        ...

    # View state properties
    @property
    def zoom_level(self) -> float:
        """Get current zoom level."""
        ...

    @zoom_level.setter
    def zoom_level(self, value: float) -> None:
        """Set zoom level."""
        ...

    @property
    def pan_offset(self) -> tuple[float, float]:
        """Get current pan offset (x, y)."""
        ...

    @pan_offset.setter
    def pan_offset(self, value: tuple[float, float]) -> None:
        """Set pan offset (x, y)."""
        ...

    @property
    def smoothing_window_size(self) -> int:
        """Get smoothing window size (read-only)."""
        ...

    @property
    def smoothing_filter_type(self) -> str:
        """Get smoothing filter type (read-only)."""
        ...

    def reset_to_defaults(self) -> None:
        """Reset state to defaults."""
        ...

    def get_window_title(self) -> str:
        """Get window title."""
        ...

    def set_selected_points(self, indices: list[int]) -> None:
        """Set selected point indices."""
        ...

    def set_history_state(self, can_undo: bool, can_redo: bool, position: int, size: int) -> None:
        """Update history state information for UI indicators."""
        ...

    # Signals
    file_changed: SignalProtocol  # Emits new file path (str)
    modified_changed: SignalProtocol  # Emits modification status (bool)
    selection_changed: SignalProtocol  # Emits set of selected indices (set)
    view_state_changed: SignalProtocol  # Emits when view state changes
    total_frames_changed: SignalProtocol  # Emits new total_frames value (int)


class CurveViewProtocol(Protocol):
    """Protocol for curve view widgets.

    Unified interface that curve view widgets must implement
    to work with services and controllers.
    """

    # Basic attributes (as properties to match CurveViewWidget implementation)
    @property
    def selected_point_idx(self) -> int:
        """Current selected point index."""
        ...

    @selected_point_idx.setter
    def selected_point_idx(self, value: int) -> None:
        """Set current selected point index."""
        ...

    @property
    def curve_data(self) -> CurveDataList:
        """Active curve data."""
        ...

    @property
    def current_image_idx(self) -> int:
        """Current image index."""
        ...

    # Point management (as properties to match CurveViewWidget implementation)
    @property
    def points(self) -> CurveDataList:
        """All points in the curve."""
        ...

    @property
    def selected_points(self) -> set[int]:
        """Set of selected point indices."""
        ...

    @selected_points.setter
    def selected_points(self, value: set[int]) -> None:
        """Set selected point indices."""
        ...

    # Transform and positioning (most are properties in CurveViewWidget)
    @property
    def offset_x(self) -> float:
        """X offset for rendering."""
        ...

    @property
    def offset_y(self) -> float:
        """Y offset for rendering."""
        ...

    @property
    def x_offset(self) -> float:
        """X offset alias for compatibility."""
        ...

    @property
    def y_offset(self) -> float:
        """Y offset alias for compatibility."""
        ...

    @property
    def zoom_factor(self) -> float:
        """Current zoom level."""
        ...

    @zoom_factor.setter
    def zoom_factor(self, value: float) -> None:
        """Set zoom level."""
        ...

    @property
    def pan_offset_x(self) -> float:
        """Pan offset in X direction."""
        ...

    @pan_offset_x.setter
    def pan_offset_x(self, value: float) -> None:
        """Set pan offset X."""
        ...

    @property
    def pan_offset_y(self) -> float:
        """Pan offset in Y direction."""
        ...

    @pan_offset_y.setter
    def pan_offset_y(self, value: float) -> None:
        """Set pan offset Y."""
        ...

    # Manual offsets are plain attributes (not properties)
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
    selection_changed: SignalProtocol  # Emits list of selected indices
    view_changed: SignalProtocol  # Emits when view transform changes

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
        from stores.application_state import get_application_state

        view: MultiCurveViewProtocol = CurveViewWidget()
        app_state = get_application_state()

        # Set multiple curves
        curves = {
            "pp56_TM_138G": [(1, 10.0, 20.0), (2, 15.0, 25.0)],
            "pp53_TM_134G": [(1, 30.0, 40.0), (2, 35.0, 45.0)],
        }
        view.set_curves_data(curves)

        # Set active curve for editing
        view.set_active_curve("pp56_TM_138G")

        # Set display mode via ApplicationState
        app_state.set_show_all_curves(True)  # → display_mode = ALL_VISIBLE
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

    def select_point(self, point_index: int, add_to_selection: bool = False, curve_name: str | None = None) -> None:
        """
        Select a point by index.

        Public API for point selection, replacing _select_point() private method.

        Args:
            point_index: Index of point to select
            add_to_selection: If True, add to existing selection; if False, replace selection
            curve_name: Optional curve name (defaults to active curve if None)
        """
        ...

    def center_on_selected_curves(self) -> None:
        """Center the view on all selected curves."""
        ...

    # Additional methods needed by ActionHandlerController
    def select_all(self) -> None:
        """Select all points in active curve."""
        ...

    def invalidate_caches(self) -> None:
        """Invalidate rendering caches."""
        ...

    zoom_changed: SignalProtocol  # Signal emitted when zoom changes

    def reset_view(self) -> None:
        """Reset view to default state."""
        ...

    def fit_to_view(self) -> None:
        """Fit view to show all curve data."""
        ...


class QLabelProtocol(Protocol):
    """Protocol for QLabel widgets."""

    def setText(self, text: str) -> None:
        """Set label text."""
        ...

    def text(self) -> str:
        """Get label text."""
        ...


class ServicesProtocol(Protocol):
    """Protocol for services facade.

    Provides access to application services like undo/redo.
    """

    def undo(self) -> None:
        """Undo the last operation."""
        ...

    def redo(self) -> None:
        """Redo the last undone operation."""
        ...


class FileOperationsProtocol(Protocol):
    """Protocol for file operations manager.

    Handles loading, saving, and exporting curve data and images.
    """

    def new_file(self) -> bool:
        """Create new file, prompting to save if modified.

        Returns:
            True if new file created, False if cancelled
        """
        ...

    def open_file(self, parent: object) -> object | None:
        """Open file dialog and load curve data.

        Args:
            parent: Parent widget for dialog

        Returns:
            Loaded curve data or None if cancelled
        """
        ...

    def save_file(self, data: object) -> bool:
        """Save data to current file.

        Args:
            data: Curve data to save

        Returns:
            True if saved successfully, False otherwise
        """
        ...

    def save_file_as(self, data: object, parent: object) -> bool:
        """Save data to new file via dialog.

        Args:
            data: Curve data to save
            parent: Parent widget for dialog

        Returns:
            True if saved successfully, False if cancelled
        """
        ...

    def load_images(self, parent: object) -> bool:
        """Load image sequence via dialog.

        Args:
            parent: Parent widget for dialog

        Returns:
            True if images loaded, False if cancelled
        """
        ...

    def export_data(self, data: object, parent: object) -> bool:
        """Export data to file via dialog.

        Args:
            data: Curve data to export
            parent: Parent widget for dialog

        Returns:
            True if exported successfully, False if cancelled
        """
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

    @property
    def curve_widget(self) -> MultiCurveViewProtocol | None:
        """Get curve widget (CurveViewWidget - replaces deprecated curve_view)."""
        ...

    # UI label widgets (needed by ActionHandlerController)
    status_label: "QLabelProtocol | None"  # Status bar label
    zoom_label: "QLabelProtocol | None"  # Zoom level display

    # Controller references (needed by ActionHandlerController)
    tracking_controller: "MultiPointTrackingProtocol"  # Multi-point tracking controller

    # Frame management
    @property
    def current_frame(self) -> int:
        """Get the current frame number."""
        ...

    # History management (optional - interaction service has internal fallback)
    history: list[object] | None
    history_index: int | None
    max_history_size: int

    # Point attributes
    point_name: str
    point_color: str

    # UI component references
    undo_button: "QPushButton | None"
    redo_button: "QPushButton | None"
    save_button: "QPushButton | None"
    _point_spinbox_connected: bool
    file_operations: FileOperationsProtocol  # File operations manager

    # Service references (readonly to allow covariance)
    @property
    def services(self) -> ServicesProtocol:
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
    def multi_point_controller(self) -> "MultiPointTrackingProtocol | None":
        """Get multi-point tracking controller if available.

        Returns:
            Controller instance or None if not initialized.
        """
        ...

    # UI widget attributes (initialized by UIInitializationController)
    fps_spinbox: object | None  # QSpinBox
    btn_play_pause: object | None  # QPushButton
    timeline_tabs: "TimelineTabsProtocol | None"
    timeline_controller: "TimelineControllerProtocol | None"  # TimelineController
    tracking_panel: "TrackingPointsPanelProtocol | None"

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

    def on_multi_point_data_loaded(self, data: dict[str, object]) -> None:
        """Handle multi-point tracking data loaded from file.

        Args:
            data: Dictionary mapping curve names to curve data
        """
        ...

    def on_tracking_data_loaded(self, data: object) -> None:
        """Handle single-curve tracking data loaded from file.

        Args:
            data: Single curve data to merge into tracked data
        """
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


class TrackingPointsPanelProtocol(Protocol):
    """Protocol for tracking points panel widget.

    Defines the public interface for the tracking points panel,
    which manages multi-point tracking operations.
    """

    def set_direction_for_points(self, points: list[str], direction: object) -> None:
        """Set tracking direction for selected points.

        Args:
            points: List of point names to update
            direction: TrackingDirection enum value (FORWARD/BACKWARD/BOTH/NONE)
        """
        ...

    def delete_points(self, points: list[str]) -> None:
        """Delete tracking points by name.

        Args:
            points: List of point names to delete
        """
        ...

    def get_selected_points(self) -> list[str]:
        """Get list of selected point names.

        Returns:
            List of selected tracking point names
        """
        ...

    def set_selected_points(self, points: list[str]) -> None:
        """Set selected points by name.

        Args:
            points: List of point names to select
        """
        ...

    def set_tracked_data(self, tracked_data: "Mapping[str, object]") -> None:
        """Set tracking data for all points.

        Args:
            tracked_data: Mapping from point names to curve data
        """
        ...

    def get_point_visibility(self, point_name: str) -> bool:
        """Get visibility status of a point.

        Args:
            point_name: Name of the point

        Returns:
            True if point is visible, False otherwise
        """
        ...

    def get_point_color(self, point_name: str) -> tuple[int, int, int]:
        """Get color of a point.

        Args:
            point_name: Name of the point

        Returns:
            RGB color tuple (0-255)
        """
        ...


class TimelineTabsProtocol(Protocol):
    """Protocol for timeline tabs widget.

    Defines the public interface for the timeline tab container,
    which displays curve data across multiple tabs/frames.
    """

    def on_frame_changed(self, frame: int) -> None:
        """Handle frame change notification.

        Args:
            frame: New frame number
        """
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
