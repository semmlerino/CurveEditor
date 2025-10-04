#!/usr/bin/env python
"""
CurveViewWidget - High-performance curve visualization and editing widget.

This module provides a comprehensive curve viewing and editing widget that integrates
with the CurveEditor's service architecture. It implements efficient painting,
mouse interaction, zoom/pan operations, and state management.

Key Features:
    - Custom QPainter-based rendering with optimization
    - Mouse-based point manipulation with drag & drop
    - Zoom and pan operations with smooth transitions
    - Integration with Transform and ViewState services
    - Efficient update regions for large datasets
    - Grid and background image support
    - Multi-point selection with rubber band
    - Real-time coordinate transformation

Architecture:
    - Uses Transform service for coordinate mapping
    - Integrates with CurveService for data operations
    - Connects to StateManager for application state
    - Implements caching for performance optimization
"""

# Import cycle is expected due to circular dependency with MainWindow
# This is resolved by using Protocol pattern for type safety
# pyright: reportImportCycles=false

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import (
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import QRubberBand, QStatusBar, QWidget
from typing_extensions import override

# Import core modules
from core.models import CurvePoint, PointCollection, PointStatus
from core.point_types import safe_extract_point
from core.signal_manager import SignalManager
from core.type_aliases import CurveDataInput, CurveDataList

# Import optimized renderer for 47x performance improvement
from rendering.optimized_curve_renderer import OptimizedCurveRenderer
from rendering.render_state import RenderState

# Import services
from services import get_data_service, get_interaction_service
from services.transform_service import Transform, ViewState
from ui.ui_constants import (
    DEFAULT_BACKGROUND_OPACITY,
    DEFAULT_IMAGE_HEIGHT,
    DEFAULT_IMAGE_WIDTH,
    DEFAULT_ZOOM_FACTOR,
    MAX_ZOOM_FACTOR,
    MIN_ZOOM_FACTOR,
)

if TYPE_CHECKING:
    from typing import Protocol

    from core.commands.curve_commands import BatchMoveCommand, DeletePointsCommand
    from services.interaction_service import InteractionService
    from ui.controllers.curve_view.state_sync_controller import StateSyncController
    from ui.controllers.view_camera_controller import ViewCameraController
    from ui.state_manager import StateManager

    class MainWindow(Protocol):
        """Main window protocol for type checking."""

        current_frame: int
        status_bar: QStatusBar
        state_manager: StateManager

        def add_to_history(self) -> None: ...
else:
    MainWindow = Any  # Runtime fallback to avoid import cycle
    InteractionService = Any  # Runtime fallback to avoid import cycle
    BatchMoveCommand = Any  # Runtime fallback to avoid import cycle
    DeletePointsCommand = Any  # Runtime fallback to avoid import cycle
    StateSyncController = Any  # Runtime fallback to avoid import cycle
    ViewCameraController = Any  # Runtime fallback to avoid import cycle

from core.logger_utils import get_logger

# Import stores
from stores import get_store_manager
from stores.application_state import get_application_state

logger = get_logger("curve_view_widget")


class CurveViewWidget(QWidget):
    """
    High-performance widget for curve visualization and editing.

    This widget provides a complete curve editing interface with optimized
    rendering, interaction handling, and service integration.

    IMPORTANT ARCHITECTURE NOTE:
    All rendering is delegated to OptimizedCurveRenderer for performance.
    This widget does NOT implement its own painting methods - the renderer
    handles everything including background, grid, lines, points, etc.

    Signals:
        point_selected: Emitted when a point is selected (index: int)
        point_moved: Emitted when a point is moved (index: int, x: float, y: float)
        selection_changed: Emitted when selection changes (indices: list[int])
        view_changed: Emitted when view transform changes
        zoom_changed: Emitted when zoom level changes (zoom: float)

    Attributes:
        curve_data: List of curve points in tuple format
        selected_indices: Set of selected point indices
        transform: Current transformation for coordinate mapping
        view_state: Current view state snapshot
    """

    # Signals
    point_selected: Signal = Signal(int)  # index
    point_moved: Signal = Signal(int, float, float)  # index, x, y
    selection_changed: Signal = Signal(list)  # list of indices
    view_changed: Signal = Signal()  # view transform changed
    zoom_changed: Signal = Signal(float)  # zoom level
    data_changed: Signal = Signal()  # curve data changed

    def __init__(self, parent: QWidget | None = None, state_manager: StateManager | None = None):
        """
        Initialize the CurveViewWidget.

        Args:
            parent: Parent widget (typically MainWindow)
            state_manager: Optional state manager for dependency injection
        """
        super().__init__(parent)

        # Signal management for proper cleanup
        self.signal_manager: SignalManager = SignalManager(self)

        # Store injected state manager
        self._state_manager = state_manager

        # Get the reactive data store
        self._store_manager = get_store_manager()
        self._curve_store = self._store_manager.get_curve_store()

        # Get centralized ApplicationState (Week 3 migration)
        self._app_state = get_application_state()

        # State synchronization controller (Phase 3 extraction)
        # Handles all signal connections and reactive updates from stores
        from ui.controllers.curve_view.state_sync_controller import StateSyncController

        self.state_sync: StateSyncController = StateSyncController(self)
        self.state_sync.connect_all_signals()

        # Data management facade (Phase 4 extraction)
        # Encapsulates all data operations, delegating to ApplicationState + CurveDataStore
        from ui.controllers.curve_view.curve_data_facade import CurveDataFacade

        self.data_facade: CurveDataFacade = CurveDataFacade(self)

        # Rendering cache management (Phase 5 extraction)
        # Manages screen points cache, visible indices, and update regions for performance
        from ui.controllers.curve_view.render_cache_controller import RenderCacheController

        self.render_cache: RenderCacheController = RenderCacheController(self)

        # Core data (now derived from store)
        self.point_collection: PointCollection | None = None
        self.hover_index: int = -1

        # Multi-curve support (VIEW state - stays in widget)
        # NOTE: DATA state (curves_data, curve_metadata, active_curve_name) migrated to ApplicationState
        self.show_all_curves: bool = False  # Toggle for showing all curves
        self.selected_curve_names: set[str] = set()  # Currently selected curves to display
        self.selected_curves_ordered: list[str] = []  # Ordered list for visual differentiation

        # View transformation (zoom/pan managed by view_camera controller)
        # Note: zoom_factor, pan_offset_x, pan_offset_y are now properties delegating to view_camera
        self.manual_offset_x: float = 0.0
        self.manual_offset_y: float = 0.0
        # For tracking data from video, Y=0 is at top, Y increases downward
        # Qt's coordinate system also has Y=0 at top, so we don't need to flip
        self.flip_y_axis: bool = False
        self.scale_to_image: bool = True

        # Display settings
        self.show_grid: bool = False
        self.show_points: bool = True
        self.show_lines: bool = True
        self.show_labels: bool = False
        self.show_velocity_vectors: bool = False
        self.show_all_frame_numbers: bool = False
        self.show_background: bool = True
        self.background_opacity: float = DEFAULT_BACKGROUND_OPACITY

        # Grid settings
        self.grid_size: int = 50
        self.grid_color: QColor = QColor(100, 100, 100, 50)
        self.grid_line_width: int = 1

        # Point rendering settings
        self.point_radius: int = 5
        self.selected_point_radius: int = 7
        # Colors are now centralized in ui_constants.py - use get_status_color() and SPECIAL_COLORS

        # Line rendering settings
        self.line_color: QColor = QColor(200, 200, 200)
        self.line_width: int = 2
        self.selected_line_color: QColor = QColor(255, 255, 100)
        self.selected_line_width: int = 3

        # Background image
        self.background_image: QPixmap | None = None
        self.image_width: int = DEFAULT_IMAGE_WIDTH
        self.image_height: int = DEFAULT_IMAGE_HEIGHT

        # Centering mode - stays centered on current frame when navigating timeline
        self.centering_mode: bool = False

        # Interaction state (Phase 2: InteractionService integration)
        self.drag_active: bool = False
        self.pan_active: bool = False
        self.rubber_band_active: bool = False
        self.last_drag_pos: QPointF | None = None  # For dragging points
        self.last_pan_pos: QPointF | None = None  # For panning view
        self.drag_start_pos: QPointF | None = None
        self.dragged_index: int = -1
        self._context_menu_point: int = -1

        # Rubber band selection
        self.rubber_band: QRubberBand | None = None
        self.rubber_band_origin: QPointF = QPointF()

        # Performance optimization caches
        # Transform cache → view_camera controller (Phase 1)
        # Rendering caches → render_cache controller (Phase 5)

        # Services (will be set by main window)
        self.main_window: MainWindow | None = None
        self.interaction_service: InteractionService = get_interaction_service()

        # View camera controller for zoom, pan, centering, fitting (Phase 1 extraction)
        from ui.controllers.view_camera_controller import ViewCameraController

        # Protocol conformance verified at runtime - structural type matching not perfect
        self.view_camera: ViewCameraController = ViewCameraController(self)  # pyright: ignore[reportArgumentType]

        # Initialize optimized renderer for 47x performance improvement
        self._optimized_renderer: OptimizedCurveRenderer = OptimizedCurveRenderer()
        self._optimized_renderer.background_opacity = self.background_opacity

        # Widget setup
        self._setup_widget()

        logger.info("CurveViewWidget initialized with OptimizedCurveRenderer and reactive store")

    @property
    def curve_data(self) -> list[tuple[int, float, float] | tuple[int, float, float, str | bool]]:
        """Get curve data from the store."""
        return self._curve_store.get_data()

    @property
    def selected_indices(self) -> set[int]:
        """Get selected indices from the store."""
        selection = self._curve_store.get_selection()

        # BACKWARD COMPATIBILITY: Also sync to ApplicationState default curve
        default_curve = "__default__"
        if default_curve in self._app_state.get_all_curve_names():
            app_state_selection = self._app_state.get_selection(default_curve)
            # Sync if they differ (prefer CurveDataStore as source of truth for single-curve)
            if selection != app_state_selection:
                self._app_state.set_selection(default_curve, selection)

        return selection

    @selected_indices.setter
    def selected_indices(self, value: set[int]) -> None:
        """Set selected indices in the store."""
        if not value:
            self._curve_store.clear_selection()
            # BACKWARD COMPATIBILITY: Also clear in ApplicationState
            default_curve = "__default__"
            if default_curve in self._app_state.get_all_curve_names():
                self._app_state.clear_selection(default_curve)
        else:
            # Clear first then add each index
            self._curve_store.clear_selection()
            for idx in value:
                self._curve_store.select(idx, add_to_selection=True)
            # BACKWARD COMPATIBILITY: Also update in ApplicationState
            default_curve = "__default__"
            if default_curve in self._app_state.get_all_curve_names():
                self._app_state.set_selection(default_curve, value)

    @property
    def active_curve_name(self) -> str | None:
        """
        Get active curve name from ApplicationState.

        Backward-compatible property for accessing active_curve during migration.
        Delegates to ApplicationState.active_curve.
        """
        from stores.application_state import get_application_state

        return get_application_state().active_curve

    @property
    def curves_data(self) -> dict[str, list[tuple[int, float, float] | tuple[int, float, float, str | bool]]]:
        """
        Get all curves data from ApplicationState.

        Backward-compatible property for accessing multi-curve data during migration.
        Returns dict mapping curve names to their data.
        Filters out "__default__" which is internal for single-curve backward compatibility.
        """
        from stores.application_state import get_application_state

        app_state = get_application_state()
        result = {}
        for curve_name in app_state.get_all_curve_names():
            # Filter out "__default__" - it's for internal single-curve compatibility
            if curve_name != "__default__":
                result[curve_name] = app_state.get_curve_data(curve_name)
        return result

    # View transformation properties (delegate to view_camera controller)

    @property
    def zoom_factor(self) -> float:
        """Get current zoom factor from view camera controller."""
        return self.view_camera.zoom_factor

    @zoom_factor.setter
    def zoom_factor(self, value: float) -> None:
        """Set zoom factor via view camera controller."""
        self.view_camera.set_zoom_factor(value)

    @property
    def pan_offset_x(self) -> float:
        """Get current X pan offset from view camera controller."""
        return self.view_camera.pan_offset_x

    @pan_offset_x.setter
    def pan_offset_x(self, value: float) -> None:
        """Set X pan offset via view camera controller."""
        self.view_camera.pan_offset_x = value
        self.view_camera.invalidate_caches()

    @property
    def pan_offset_y(self) -> float:
        """Get current Y pan offset from view camera controller."""
        return self.view_camera.pan_offset_y

    @pan_offset_y.setter
    def pan_offset_y(self, value: float) -> None:
        """Set Y pan offset via view camera controller."""
        self.view_camera.pan_offset_y = value
        self.view_camera.invalidate_caches()

    # ==================== Signal Handlers (Phase 3: Extracted to StateSyncController) ====================
    # All signal connection and handling logic moved to ui/controllers/curve_view/state_sync_controller.py
    # This eliminates 186 lines of signal handling code from the widget

    def _setup_widget(self) -> None:
        """Configure widget properties and settings."""
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Set focus policy for keyboard events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Set comprehensive accessibility tooltip
        tooltip_text = (
            "Curve Editor - Interactive curve visualization and editing\n\n"
            "VISUAL POINT INDICATORS:\n"
            "• Circles: Regular points\n"
            "• Squares: Keyframe points\n"
            "• Triangles: Interpolated points\n"
            "• Larger size: Current frame point\n"
            "• White outline: Selected points\n\n"
            "MOUSE CONTROLS:\n"
            "• Left click: Select point\n"
            "• Ctrl+Left click: Add to selection\n"
            "• Alt+Left drag: Rubber band selection\n"
            "• Left drag: Move selected point(s)\n"
            "• Middle drag: Pan view\n"
            "• Scroll wheel: Zoom (centered on mouse)\n\n"
            "KEYBOARD SHORTCUTS:\n"
            "• C: Center view on selection\n"
            "• F: Fit background image to view\n"
            "• Delete: Remove selected points\n"
            "• Ctrl+A: Select all points\n"
            "• Escape: Clear selection\n"
            "• 2/4/6/8: Nudge selected points (down/left/right/up)\n"
            "• Shift+2/4/6/8: Nudge by 10x amount\n"
            "• Ctrl+2/4/6/8: Nudge by 0.1x amount"
        )
        self.setToolTip(tooltip_text)

        # Optimization attributes
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # Set minimum size
        self.setMinimumSize(400, 300)

        # Set background
        self.setAutoFillBackground(False)

        # Create rubber band for selection
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)

    # Data Management

    @property
    def offset_x(self):
        """X offset for OptimizedCurveRenderer compatibility."""
        return self.pan_offset_x + self.manual_offset_x

    @property
    def offset_y(self):
        """Y offset for OptimizedCurveRenderer compatibility."""
        return self.pan_offset_y + self.manual_offset_y

    def set_curve_data(self, data: CurveDataInput) -> None:
        """
        Set the curve data to display.

        Args:
            data: List of point tuples (frame, x, y, [status])

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.set_curve_data(data)

    def add_point(self, point: tuple[int, float, float] | tuple[int, float, float, str]) -> None:
        """
        Add a single point to the curve.

        Args:
            point: Point tuple (frame, x, y, [status])

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.add_point(point)

    def update_point(self, index: int, x: float, y: float) -> None:
        """
        Update coordinates of a point.

        Args:
            index: Point index
            x: New X coordinate
            y: New Y coordinate

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.update_point(index, x, y)

    def remove_point(self, index: int) -> None:
        """
        Remove a point from the curve.

        Args:
            index: Point index to remove

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.remove_point(index)

    # Multi-curve Management

    def set_curves_data(
        self,
        curves: dict[str, CurveDataList],
        metadata: dict[str, dict[str, Any]] | None = None,
        active_curve: str | None = None,
        selected_curves: list[str] | None = None,
    ) -> None:
        """
        Set multiple curves to display.

        Args:
            curves: Dictionary mapping curve names to curve data
            metadata: Optional dictionary with per-curve metadata (visibility, color, etc.)
            active_curve: Name of the currently active curve for editing
            selected_curves: Optional list of curves to select for display

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.set_curves_data(curves, metadata, active_curve, selected_curves)

    def add_curve(self, name: str, data: CurveDataList, metadata: dict[str, Any] | None = None) -> None:
        """
        Add a new curve to the display.

        Args:
            name: Unique name for the curve
            data: Curve data points
            metadata: Optional metadata for the curve

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.add_curve(name, data, metadata)

    def remove_curve(self, name: str) -> None:
        """
        Remove a curve from the display.

        Args:
            name: Name of the curve to remove

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.remove_curve(name)

    def update_curve_visibility(self, name: str, visible: bool) -> None:
        """
        Update visibility of a specific curve.

        Args:
            name: Name of the curve
            visible: Whether the curve should be visible

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.update_curve_visibility(name, visible)

    def update_curve_color(self, name: str, color: str) -> None:
        """
        Update color of a specific curve.

        Args:
            name: Name of the curve
            color: Color in hex format (e.g., "#FF0000")

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.update_curve_color(name, color)

    def set_active_curve(self, name: str) -> None:
        """
        Set the active curve for editing operations.

        Args:
            name: Name of the curve to make active

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.set_active_curve(name)

    def toggle_show_all_curves(self, show_all: bool) -> None:
        """
        Toggle whether to show all curves or just the active one.

        Note: Delegates to MultiPointTrackingController (Phase 6 extraction)

        Args:
            show_all: If True, show all visible curves; if False, show only active curve
        """
        if self.main_window and hasattr(self.main_window, "tracking_controller"):
            self.main_window.tracking_controller.toggle_show_all_curves(show_all)  # pyright: ignore[reportAttributeAccessIssue]
        else:
            # Fallback for tests or when main_window not available
            self.show_all_curves = show_all
            self.update()
            logger.debug(f"Show all curves: {show_all}")

    def set_selected_curves(self, curve_names: list[str]) -> None:
        """
        Set which curves are currently selected for display.

        Note: Delegates to MultiPointTrackingController (Phase 6 extraction)

        When show_all_curves is False, only these selected curves will be displayed.
        The last curve in the list becomes the active curve for editing.

        Args:
            curve_names: List of curve names to select and display
        """
        if self.main_window and hasattr(self.main_window, "tracking_controller"):
            self.main_window.tracking_controller.set_selected_curves(curve_names)  # pyright: ignore[reportAttributeAccessIssue]
        else:
            # Fallback for tests or when main_window not available
            self.selected_curve_names = set(curve_names)
            self.selected_curves_ordered = list(curve_names)

            # Set the last selected as the active curve for editing
            all_curve_names = self._app_state.get_all_curve_names()
            if curve_names and curve_names[-1] in all_curve_names:
                self.set_active_curve(curve_names[-1])

            self.update()
            logger.debug(f"Selected curves: {self.selected_curve_names}, Active: {self._app_state.active_curve}")

    def center_on_selected_curves(self) -> None:
        """
        Center the view on all selected curves.

        Note: Delegates to MultiPointTrackingController (Phase 6 extraction)

        Calculates the bounding box of all selected curves and centers the view on it.
        """
        if self.main_window and hasattr(self.main_window, "tracking_controller"):
            self.main_window.tracking_controller.center_on_selected_curves()  # pyright: ignore[reportAttributeAccessIssue]
        else:
            # Fallback for tests or when main_window not available
            # Get all curve names from ApplicationState
            all_curve_names = self._app_state.get_all_curve_names()
            logger.debug(
                f"center_on_selected_curves called with selected: {self.selected_curve_names}, ApplicationState curves: {all_curve_names}"
            )
            if not self.selected_curve_names or not all_curve_names:
                logger.debug("Early return - no selected curves or no data")
                return

            # Collect all points from selected curves
            all_points: list[tuple[float, float]] = []
            for curve_name in self.selected_curve_names:
                if curve_name in all_curve_names:
                    curve_data = self._app_state.get_curve_data(curve_name)
                    logger.debug(f"Processing curve {curve_name} with {len(curve_data)} points")
                    for point in curve_data:
                        if len(point) >= 3:
                            all_points.append((float(point[1]), float(point[2])))

            if not all_points:
                logger.debug("No points found in selected curves")
                return
            logger.debug(f"Collected {len(all_points)} points for centering")

            # Calculate bounding box
            x_coords = [p[0] for p in all_points]
            y_coords = [p[1] for p in all_points]

            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)

            # Calculate center point
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2

            # Calculate required zoom to fit all points with some padding
            padding_factor = 1.2
            width_needed = (max_x - min_x) * padding_factor
            height_needed = (max_y - min_y) * padding_factor

            if width_needed > 0 and height_needed > 0:
                zoom_x = self.width() / width_needed
                zoom_y = self.height() / height_needed
                optimal_zoom = min(zoom_x, zoom_y, MAX_ZOOM_FACTOR)

                # Apply zoom
                self.zoom_factor = max(MIN_ZOOM_FACTOR, optimal_zoom)

            # Use the proper centering method that handles coordinate transformation and Y-flip
            self._center_view_on_point(center_x, center_y)

            self.invalidate_caches()
            self.update()
            self.view_changed.emit()

    # Coordinate Transformation (delegated to ViewCameraController)

    def get_transform(self) -> Transform:
        """
        Get the current transformation object.

        Returns:
            Transform object for coordinate mapping

        Note: Delegates to ViewCameraController (Phase 1 extraction)
        """
        return self.view_camera.get_transform()

    def _get_display_dimensions(self) -> tuple[int, int]:
        """
        Get display dimensions based on Y-axis flip mode.

        When Y-flip is enabled (for pixel tracking), use widget dimensions.
        Otherwise use image dimensions for traditional image-based coordinates.

        Returns:
            Tuple of (width, height) for display calculations
        """
        if self.flip_y_axis:
            return self.width(), self.height()
        else:
            display_width = self.image_width
            display_height = self.image_height

            if self.background_image:
                display_width = self.background_image.width()
                display_height = self.background_image.height()

            return display_width, display_height

    def data_to_screen(self, x: float, y: float) -> QPointF:
        """
        Convert data coordinates to screen coordinates.

        Args:
            x: Data X coordinate
            y: Data Y coordinate

        Returns:
            Screen position as QPointF

        Note: Delegates to ViewCameraController (Phase 1 extraction)
        """
        return self.view_camera.data_to_screen(x, y)

    def screen_to_data(self, pos: QPointF) -> tuple[float, float]:
        """
        Convert screen coordinates to data coordinates.

        Args:
            pos: Screen position

        Returns:
            Data coordinates as (x, y) tuple

        Note: Delegates to ViewCameraController (Phase 1 extraction)
        """
        return self.view_camera.screen_to_data(pos)

    def screen_to_data_qpoint(self, pos: QPointF) -> QPointF:
        """
        Convert screen coordinates to data coordinates as QPointF.

        Args:
            pos: Screen position

        Returns:
            Data coordinates as QPointF
        """
        transform = self.get_transform()
        data_x, data_y = transform.screen_to_data(pos.x(), pos.y())
        return QPointF(data_x, data_y)

    # Painting

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the widget content using OptimizedCurveRenderer for 47x performance.

        CRITICAL ARCHITECTURE DECISION:
        This method delegates ALL rendering to OptimizedCurveRenderer.
        Do NOT implement paint methods directly in this widget - all painting
        logic should be in the renderer for performance and consistency.

        The renderer handles:
        - Background image rendering
        - Grid overlay
        - Curve lines and segments
        - Point markers (with shapes, colors, selection, current frame highlight)
        - Velocity vectors
        - Labels and overlays

        Args:
            event: Paint event with exposed region
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Import theme colors
        from ui.ui_constants import COLORS_DARK

        # Clear background with theme color
        bg_color = QColor(COLORS_DARK["bg_primary"])
        painter.fillRect(event.rect(), bg_color)

        # DELEGATE ALL RENDERING TO OPTIMIZED RENDERER
        # This is the ONLY rendering path - do not add paint methods to this widget

        # Build RenderState from StateManager and widget properties (KISS/SOLID decoupling)
        current_frame = 1  # Default fallback
        selected_points: set[int] = set()  # Default fallback

        if self._state_manager is not None:
            state_manager = self._state_manager
            current_frame = state_manager.current_frame
            selected_points = set(state_manager.selected_points)

        # Create RenderState with all necessary data for rendering (explicit state passing)
        render_state = RenderState(
            # Core data
            points=self.points,
            current_frame=current_frame,
            selected_points=selected_points,
            # Widget dimensions
            widget_width=self.width(),
            widget_height=self.height(),
            # View transform settings
            zoom_factor=self.zoom_factor,
            pan_offset_x=self.pan_offset_x,
            pan_offset_y=self.pan_offset_y,
            manual_offset_x=self.manual_offset_x,
            manual_offset_y=self.manual_offset_y,
            flip_y_axis=self.flip_y_axis,
            # Background settings
            show_background=self.show_background,
            background_image=self.background_image,
            background_opacity=self.background_opacity,
            # Image dimensions
            image_width=self.image_width,
            image_height=self.image_height,
            # Grid and visual settings
            show_grid=self.show_grid,
            point_radius=self.point_radius,
            # Multi-curve support - CRITICAL FIX for gap visualization
            # Use live curves data that includes current status changes for active curve
            curves_data=self._get_live_curves_data(),
            show_all_curves=self.show_all_curves,
            selected_curve_names=self.selected_curve_names,
            selected_curves_ordered=self.selected_curves_ordered,  # For visual differentiation
        )

        # Pass explicit state to renderer instead of widget reference
        self._optimized_renderer.render(painter, event, render_state)

        # Draw overlay elements that aren't handled by the renderer
        # These are lightweight UI elements that don't impact performance

        # Draw rubber band if active
        if self.rubber_band_active and self.rubber_band:
            _ = self.rubber_band.show()  # Suppress unused return value

        # Draw hover indicator
        if self.hover_index >= 0:
            self._paint_hover_indicator(painter)

        # Draw centering mode indicator
        if self.centering_mode:
            self._paint_centering_indicator(painter)

    def _paint_hover_indicator(self, painter: QPainter) -> None:
        """Paint hover indicator for point under mouse."""
        if self.hover_index >= 0:
            pos = self.render_cache.get_screen_position(self.hover_index)
            if pos is None:
                return

            painter.save()

            # Draw highlight circle
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 100), 2))
            painter.drawEllipse(pos, self.point_radius + 5, self.point_radius + 5)

            painter.restore()

    def _paint_centering_indicator(self, painter: QPainter) -> None:
        """Paint centering mode indicator in the top-right corner."""
        painter.save()

        # Set up text properties
        font = painter.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)

        # Import theme colors
        from ui.ui_constants import COLORS_DARK

        # Draw background rectangle with theme accent color
        text = "CENTERING ON"
        rect = QRectF(self.width() - 120, 10, 110, 25)
        accent_color = QColor(COLORS_DARK["accent_warning"])  # Use warning color for attention
        accent_color.setAlpha(180)
        painter.fillRect(rect, accent_color)

        # Draw border
        border_color = QColor(COLORS_DARK["border_warning"])
        painter.setPen(QPen(border_color, 2))
        _ = painter.drawRect(rect)

        # Draw text
        painter.setPen(QColor(COLORS_DARK["text_primary"]))
        _ = painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()

    # Mouse Events

    def _get_point_update_rect(self, index: int) -> QRect:
        """Get minimal update rectangle for a point to optimize repainting.

        Args:
            index: Point index

        Returns:
            Rectangle covering the point and its selection/hover indicators
        """
        if index < 0 or index >= len(self.curve_data):
            return QRect()

        # Get screen position of point
        point = self.curve_data[index]
        # Extract x, y from the point tuple (frame, x, y, ...)
        if len(point) >= 3:
            x, y = point[1], point[2]
        else:
            # Fallback for malformed points
            x, y = float(point[0]), float(point[1])
        screen_pos = self.data_to_screen(x, y)

        # Calculate radius including hover and selection indicators
        radius = max(self.point_radius, self.selected_point_radius) + 10  # Extra padding for hover

        # Return rectangle around point
        return QRect(int(screen_pos.x() - radius), int(screen_pos.y() - radius), int(radius * 2), int(radius * 2))

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events.

        Args:
            event: Mouse event
        """
        # Ensure this widget has keyboard focus when clicked
        if not self.hasFocus():
            logger.info("[FOCUS] CurveViewWidget gaining focus from mouse press")
        self.setFocus(Qt.FocusReason.MouseFocusReason)

        pos = event.position()
        button = event.button()
        modifiers = event.modifiers()

        if button == Qt.MouseButton.LeftButton:
            if modifiers & Qt.KeyboardModifier.AltModifier:
                # Start rubber band selection
                self._start_rubber_band(pos)
            else:
                # Check for point selection/drag
                # Use multi-curve search if we have multiple curves in ApplicationState
                all_curve_names = self._app_state.get_all_curve_names()
                if all_curve_names:
                    idx, curve_name = self._find_point_at_multi_curve(pos)
                else:
                    idx = self._find_point_at(pos)
                    curve_name = None

                if idx >= 0:
                    # Select and start dragging point
                    add_to_selection = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
                    self._select_point(idx, add_to_selection, curve_name)
                    self.drag_active = True
                    self.dragged_index = idx
                    self.drag_start_pos = pos
                    self.last_drag_pos = pos
                else:
                    # Clear selection if not Ctrl-clicking
                    if not (modifiers & Qt.KeyboardModifier.ControlModifier):
                        self.clear_selection()

        elif button == Qt.MouseButton.MiddleButton:
            # Start panning
            self.pan_active = True
            self.last_pan_pos = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        elif button == Qt.MouseButton.RightButton:
            # Find point at position for context menu
            idx = self._find_point_at(pos)
            if idx >= 0:
                # Store for context menu
                self._context_menu_point = idx
            else:
                self._context_menu_point = -1

        self.update()

    @override
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse move events.

        Args:
            event: Mouse event
        """
        pos = event.position()

        # Update hover with partial update
        old_hover = self.hover_index
        self.hover_index = self._find_point_at(pos)
        if self.hover_index != old_hover:
            # Only update areas around affected points for better performance
            if old_hover >= 0:
                old_rect = self._get_point_update_rect(old_hover)
                self.update(old_rect)
            if self.hover_index >= 0:
                new_rect = self._get_point_update_rect(self.hover_index)
                self.update(new_rect)

        # Handle rubber band
        if self.rubber_band_active and self.rubber_band:
            self._update_rubber_band(pos)

        # Handle dragging
        elif self.drag_active and self.last_drag_pos:
            delta = pos - self.last_drag_pos
            self._drag_point(self.dragged_index, delta)
            self.last_drag_pos = pos

        # Handle panning
        elif self.pan_active and self.last_pan_pos:
            delta = pos - self.last_pan_pos
            self.pan_offset_x += delta.x()
            # Apply Y pan offset with conditional inversion for Y-flip mode
            self.view_camera.apply_pan_offset_y(delta.y())
            self.last_pan_pos = pos
            self.invalidate_caches()
            self.update()
            self.view_changed.emit()

    @override
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse release events.

        Args:
            event: Mouse event
        """
        button = event.button()

        if button == Qt.MouseButton.LeftButton:
            if self.rubber_band_active:
                self._finish_rubber_band()
            elif self.drag_active:
                self.drag_active = False
                self.dragged_index = -1
                self.drag_start_pos = None
                self.last_drag_pos = None

                # History is now handled by commands in InteractionService
                # self._add_to_history()  # Legacy - removed in favor of command system

        elif button == Qt.MouseButton.MiddleButton:
            self.pan_active = False
            self.last_pan_pos = None
            self.unsetCursor()

        self.update()

    @override
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        Handle context menu events for point status changes.

        Args:
            event: Context menu event
        """
        from PySide6.QtWidgets import QMenu

        # Check if we have a point under cursor
        pos = QPointF(event.pos())  # Convert QPoint to QPointF
        idx = self._find_point_at(pos)

        if idx >= 0 and idx < len(self.curve_data):
            # Create context menu
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2d2d30;
                    color: #e0e0e0;
                    border: 1px solid #495057;
                }
                QMenu::item:selected {
                    background-color: #3a3a3c;
                }
            """)

            # Get current point status
            point = self.curve_data[idx]
            current_status = point[3] if len(point) > 3 else "normal"

            # Add status change actions
            status_menu = menu.addMenu("Set Point Status")

            # Create actions for each status
            statuses = [
                ("Keyframe", PointStatus.KEYFRAME),
                ("Tracked", PointStatus.TRACKED),
                ("Interpolated", PointStatus.INTERPOLATED),
                ("Endframe", PointStatus.ENDFRAME),
                ("Normal", PointStatus.NORMAL),
            ]

            for label, status in statuses:
                action = status_menu.addAction(label)
                # Add checkmark for current status
                if status.value == current_status:
                    action.setCheckable(True)
                    action.setChecked(True)
                # Connect to handler
                action.triggered.connect(lambda checked, s=status, i=idx: self._set_point_status(i, s))

            # Add separator
            menu.addSeparator()

            # Add info display
            frame_num = point[0]
            info_action = menu.addAction(f"Frame {frame_num}")
            info_action.setEnabled(False)

            # Show menu at cursor position
            menu.exec(event.globalPos())

        else:
            # No point under cursor, show general menu or pass to parent
            super().contextMenuEvent(event)

    def _set_point_status(self, idx: int, status: PointStatus) -> None:
        """
        Change the status of a point.

        Args:
            idx: Index of the point to change
            status: New PointStatus value
        """
        # Delegate to store - it will emit signals that trigger our updates
        self._curve_store.set_point_status(idx, status.value)

        # History is now handled by commands
        # self._add_to_history()  # Legacy - removed in favor of command system

        point = self._curve_store.get_point(idx)
        if point:
            frame = point[0]
            logger.info(f"Changed point {idx} (frame {frame}) status to {status.value}")

    @override
    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        Handle mouse wheel events for zooming.

        Note: Delegates to ViewCameraController (Phase 1 extraction)

        Args:
            event: Wheel event
        """
        # Delegate to view camera controller
        self.view_camera.handle_wheel_zoom(event, event.position())

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handle keyboard events.

        All keyboard shortcuts are now handled by the global shortcut system.
        This method just ensures proper event propagation.

        Args:
            event: Key event
        """
        # Let the event propagate to the global event filter
        super().keyPressEvent(event)

    @override
    def focusInEvent(self, event) -> None:
        """Handle focus in event."""
        logger.info(f"[FOCUS] CurveViewWidget gained focus! Reason: {event.reason()}")
        super().focusInEvent(event)

    @override
    def focusOutEvent(self, event) -> None:
        """Handle focus out event."""
        logger.info(f"[FOCUS] CurveViewWidget lost focus! Reason: {event.reason()}")
        super().focusOutEvent(event)

    # View Operations

    def reset_view(self) -> None:
        """
        Reset view to default state.

        Note: Delegates to ViewCameraController (Phase 1 extraction)
        """
        self.view_camera.reset_view()

    def fit_to_view(self) -> None:
        """
        Fit all points in view.

        Note: Delegates to ViewCameraController.fit_to_curve() (Phase 1 extraction)
        """
        self.view_camera.fit_to_curve()

    def on_frame_changed(self, frame: int) -> None:
        """Handle frame change event from timeline navigation.

        Note: This method is now primarily for legacy compatibility.
        The main frame update logic is handled by _on_state_frame_changed.

        Args:
            frame: The new current frame number
        """
        logger.debug(f"[FRAME] Legacy on_frame_changed called with frame {frame}")
        # The StateManager will be updated by the caller, which will trigger our signal handler
        # This method is kept for compatibility with any direct calls

        # Handle centering mode for legacy compatibility
        if self.centering_mode:
            logger.debug(f"[CENTERING] Auto-centering on frame {frame} (centering mode enabled via legacy call)")
            self.center_on_frame(frame)

    def setup_for_pixel_tracking(self) -> None:
        """Set up the view for pixel-coordinate tracking data.

        Tracking data from 3DEqualizer is in the same coordinate space
        as the background image (1280x720), so it should scale with the image.
        """
        # Don't reset zoom if we already have a background image
        # The zoom should match the background image scale
        if not self.background_image:
            # Only reset if no background loaded yet
            self.zoom_factor = 1.0
            self.pan_offset_x = 0.0
            self.pan_offset_y = 0.0

        self.manual_offset_x = 0.0
        self.manual_offset_y = 0.0

        # Keep scale_to_image TRUE so tracking scales with background
        self.scale_to_image = True  # Scale tracking with background image
        self.flip_y_axis = False  # Tracking data uses screen coordinates (Y=0 at top)

        logger.info(f"[COORD] Set up view for tracking data (zoom={self.zoom_factor:.3f}, scales with background)")
        self.invalidate_caches()
        self.update()

    def fit_to_background_image(self) -> None:
        """
        Fit the background image fully in view.

        Note: Delegates to ViewCameraController (Phase 1 extraction)
        """
        self.view_camera.fit_to_background_image()

    def _center_view_on_point(self, x: float, y: float) -> None:
        """
        Center the view on a specific data coordinate point.

        Args:
            x: Data x-coordinate to center on
            y: Data y-coordinate to center on

        Note: Delegates to ViewCameraController (Phase 1 extraction)
        """
        self.view_camera.center_on_point(x, y)

    def center_on_selection(self) -> None:
        """
        Center view on selected points.

        Note: Delegates to ViewCameraController (Phase 1 extraction)
        """
        self.view_camera.center_on_selection()

    def center_on_frame(self, frame: int) -> None:
        """
        Center view on a specific frame using gap-aware position logic.

        Args:
            frame: Frame number to center on

        Note: Delegates to ViewCameraController (Phase 1 extraction)
        """
        self.view_camera.center_on_frame(frame)

    # Selection Operations

    def _find_point_at(self, pos: QPointF) -> int:
        """
        Find point at given screen position using spatial indexing for O(1) performance.

        Args:
            pos: Screen position

        Returns:
            Point index or -1 if not found
        """
        # SPRINT 11.5 FIX: Use spatial indexing service instead of O(n) linear search
        # This provides the claimed 64.7x speedup for point operations

        # Use the optimized InteractionService with spatial indexing
        # Note: Protocol mismatch with InteractionService - using pyright: ignore for service integration
        result: int = self.interaction_service.find_point_at(self, pos.x(), pos.y())  # pyright: ignore[reportArgumentType]

        # Log for verification during integration testing
        logger.debug(f"[SPATIAL INDEX] find_point_at({pos.x():.1f}, {pos.y():.1f}) -> {result}")

        return result

    def _find_point_at_multi_curve(self, pos: QPointF) -> tuple[int, str | None]:
        """
        Find point at given screen position across ALL visible curves.

        This enables selecting points from any visible curve, not just the active one.
        When a point is found, returns both the point index and the curve it belongs to.

        Args:
            pos: Screen position

        Returns:
            Tuple of (point_index, curve_name) or (-1, None) if not found
        """
        all_curve_names = self._app_state.get_all_curve_names()
        if not all_curve_names:
            # Fall back to single-curve mode
            idx = self._find_point_at(pos)
            return (idx, self._app_state.active_curve if idx >= 0 else None)

        # ALWAYS search all curves to enable cross-curve selection
        # When a user clicks a point on any curve, that curve gets added to selected_curve_names
        # and becomes visible in the rendering. This enables the workflow:
        # 1. User browses with show_all_curves enabled
        # 2. Clicks point on curve A -> curve A added to selected_curve_names
        # 3. Ctrl+clicks point on curve B -> curve B added to selected_curve_names
        # 4. Both curves remain visible because they're both in selected_curve_names
        curves_to_search = [
            (name, self._app_state.get_curve_data(name))
            for name in all_curve_names
            if self._app_state.get_curve_metadata(name).get("visible", True)
        ]

        # Search each curve using spatial indexing
        threshold = 5.0  # Screen pixels
        best_match: tuple[int, str, float] | None = None  # (index, curve_name, distance)

        for curve_name, curve_data in curves_to_search:
            if not curve_data:
                continue

            # Temporarily set this curve as active to use spatial index
            # IMPORTANT: Save both data AND selection since set_data() clears selection
            saved_data = self.curve_data
            saved_selection = self._curve_store.get_selection().copy()
            try:
                # Temporarily update to search this curve
                self._curve_store.set_data(curve_data)

                # Find point in this curve
                idx = self._find_point_at(pos)
                if idx >= 0:
                    # Calculate distance to determine best match if multiple curves have points nearby
                    point = curve_data[idx]
                    data_x, data_y = float(point[1]), float(point[2])
                    screen_point = self.data_to_screen(data_x, data_y)
                    distance = ((screen_point.x() - pos.x()) ** 2 + (screen_point.y() - pos.y()) ** 2) ** 0.5

                    if distance <= threshold:
                        if best_match is None or distance < best_match[2]:
                            best_match = (idx, curve_name, distance)
            finally:
                # Restore original curve store data and selection
                self._curve_store.set_data(saved_data)
                # Restore selection (set_data cleared it)
                for idx in saved_selection:
                    self._curve_store.select(idx, add_to_selection=True)

        if best_match:
            logger.debug(
                f"[MULTI-CURVE] Found point at ({pos.x():.1f}, {pos.y():.1f}): idx={best_match[0]}, curve={best_match[1]}"
            )
            return (best_match[0], best_match[1])

        return (-1, None)

    def _select_point(self, index: int, add_to_selection: bool = False, curve_name: str | None = None) -> None:
        """
        Select a point.

        Args:
            index: Point index
            add_to_selection: Whether to add to existing selection
            curve_name: Optional curve name if selecting from multi-curve mode
        """
        # Handle multi-curve selection
        all_curve_names = self._app_state.get_all_curve_names()
        if curve_name and curve_name in all_curve_names:
            # Add this curve to selected curves for visibility
            self.selected_curve_names.add(curve_name)

            # If selecting from a different curve, switch to it
            if curve_name != self._app_state.active_curve:
                logger.debug(
                    f"[MULTI-CURVE] Switching active curve from {self._app_state.active_curve} to {curve_name}"
                )
                self.set_active_curve(curve_name)

        # Delegate to store - it will emit signals that trigger our updates
        self._curve_store.select(index, add_to_selection)

        # BACKWARD COMPATIBILITY: Also update ApplicationState for single-curve default
        default_curve = "__default__"
        if curve_name == default_curve or (not curve_name and default_curve in all_curve_names):
            # Single-curve mode - sync to ApplicationState
            # Match CurveDataStore's toggle behavior when add_to_selection=True
            if add_to_selection:
                # Toggle: add if not selected, remove if already selected
                current_selection = self._app_state.get_selection(default_curve)
                if index in current_selection:
                    self._app_state.remove_from_selection(default_curve, index)
                else:
                    self._app_state.add_to_selection(default_curve, index)
            else:
                self._app_state.set_selection(default_curve, {index})

        # Emit our own signal for compatibility
        self.point_selected.emit(index)

        # Update interaction service if available
        if self.interaction_service and self.main_window:
            # Note: Protocol mismatch with InteractionService - using pyright: ignore for service integration
            self.interaction_service.on_point_selected(self, self.main_window, index)  # pyright: ignore[reportArgumentType]

    def clear_selection(self) -> None:
        """Clear all selection."""
        self._curve_store.clear_selection()

        # BACKWARD COMPATIBILITY: Also clear in ApplicationState
        default_curve = "__default__"
        if default_curve in self._app_state.get_all_curve_names():
            self._app_state.clear_selection(default_curve)

    def select_all(self) -> None:
        """Select all points."""
        self._curve_store.select_all()

        # BACKWARD COMPATIBILITY: Also sync to ApplicationState
        default_curve = "__default__"
        if default_curve in self._app_state.get_all_curve_names():
            # Get all indices from curve data
            all_indices = set(range(len(self._curve_store.get_data())))
            self._app_state.set_selection(default_curve, all_indices)

    def select_point_at_frame(self, frame: int) -> int | None:
        """
        Select the point at the given frame (or closest to it).

        Args:
            frame: Frame number to find point at

        Returns:
            Index of selected point, or None if no points exist
        """
        if not self.curve_data:
            return None

        # First try to find exact match at frame
        for i, point in enumerate(self.curve_data):
            try:
                if len(point) < 1:
                    logger.warning(f"Invalid point data at index {i}: {point} (insufficient data)")
                    continue
                point_frame = int(point[0])
            except (ValueError, TypeError, IndexError) as e:
                logger.warning(f"Invalid point data at index {i}: {point} - {e}")
                continue

            if point_frame == frame:
                self.clear_selection()
                self._select_point(i)
                logger.debug(f"Selected point at exact frame {frame}, index {i}")
                return i

        # If no exact match, find closest point
        min_distance = float("inf")
        closest_index = None

        for i, point in enumerate(self.curve_data):
            try:
                if len(point) < 1:
                    logger.warning(f"Invalid point data at index {i}: {point} (insufficient data)")
                    continue
                point_frame = int(point[0])
            except (ValueError, TypeError, IndexError) as e:
                logger.warning(f"Invalid point data at index {i}: {point} - {e}")
                continue

            distance = abs(point_frame - frame)
            if distance < min_distance:
                min_distance = distance
                closest_index = i

        if closest_index is not None:
            self.clear_selection()
            self._select_point(closest_index)
            logger.debug(
                f"Selected closest point to frame {frame} at index {closest_index} (frame {int(self.curve_data[closest_index][0])})"
            )
            return closest_index

        return None

    def _start_rubber_band(self, pos: QPointF) -> None:
        """Start rubber band selection."""
        self.rubber_band_active = True
        self.rubber_band_origin = pos

        if self.rubber_band:
            self.rubber_band.setGeometry(QRect(pos.toPoint(), QSize()))
            self.rubber_band.show()

    def _update_rubber_band(self, pos: QPointF) -> None:
        """Update rubber band selection."""
        if self.rubber_band:
            rect = QRect(self.rubber_band_origin.toPoint(), pos.toPoint()).normalized()
            self.rubber_band.setGeometry(rect)

            # Select points in rectangle
            self._select_points_in_rect(rect)

    def _finish_rubber_band(self) -> None:
        """Finish rubber band selection."""
        self.rubber_band_active = False

        if self.rubber_band:
            self.rubber_band.hide()

        # Emit final selection
        self.selection_changed.emit(list(self.selected_indices))

    def _select_points_in_rect(self, rect: QRect) -> None:
        """
        Select points within rectangle.

        Args:
            rect: Selection rectangle in screen coordinates
        """
        # Clear selection first
        self._curve_store.clear_selection()

        # Update screen cache
        self._update_screen_points_cache()

        # Check each point and build selection
        selected_points = []
        for idx, screen_pos in self.render_cache.get_screen_points_items():
            if rect.contains(screen_pos.toPoint()):
                selected_points.append(idx)

        # Select all points at once
        for idx in selected_points:
            self._curve_store.select(idx, add_to_selection=True)

    # Main Window Helper Methods

    @property
    def has_main_window(self) -> bool:
        """Check if main window is available."""
        return self.main_window is not None

    def _add_to_history(self) -> None:
        """Legacy method - history is now handled by command system."""
        # This method is kept for backward compatibility but should not be used
        # All history operations should go through the command system
        pass

    def update_status(self, message: str, timeout: int = 2000) -> None:
        """Update status bar if main window available.

        Args:
            message: Status message to display
            timeout: Timeout in milliseconds
        """
        if self.main_window is not None:
            if getattr(self.main_window, "status_bar", None) is not None:
                self.main_window.status_bar.showMessage(message, timeout)  # pyright: ignore[reportAttributeAccessIssue]

    def get_current_frame(self) -> int | None:
        """Get the current frame from state manager if available.
        Used by renderer for frame highlighting.
        Returns None if state manager is not accessible.
        """
        try:
            if self._state_manager is not None:
                return self._state_manager.current_frame
            return None
        except (AttributeError, RuntimeError):
            return None

    @property
    def current_frame(self) -> int:
        """Current frame property - reads from state manager."""
        try:
            if self._state_manager is not None:
                return self._state_manager.current_frame
            return 1  # Default fallback
        except (AttributeError, RuntimeError):
            return 1  # Default fallback

    # Point Operations

    def _drag_point(self, index: int, delta: QPointF) -> None:
        """
        Drag a point by delta.

        Args:
            index: Point index
            delta: Screen space delta
        """
        if 0 <= index < len(self.curve_data):
            # Convert delta to data space
            transform = self.get_transform()
            params = transform.get_parameters()

            scale: float = cast(float, params["scale"])

            if scale > 0:
                dx: float = delta.x() / scale
                dy: float = delta.y() / scale

                # Get current position
                _, x, y, _ = safe_extract_point(self.curve_data[index])

                # Update position
                new_x: float = x + dx
                new_y: float = y + dy

                self.update_point(index, new_x, new_y)

                # Update cache for this point
                self.render_cache.update_single_point_cache(index, new_x, new_y)

    def nudge_selected(self, dx: float, dy: float) -> None:
        """
        Nudge selected points and convert them to keyframes.

        Args:
            dx: X offset in data units
            dy: Y offset in data units
        """
        if not self.selected_indices or not self.main_window:
            return

        from services import get_interaction_service

        # Collect moves and status changes
        moves = []
        status_changes = []
        for idx in self.selected_indices:
            if 0 <= idx < len(self.curve_data):
                _, x, y, _ = safe_extract_point(self.curve_data[idx])
                old_pos = (x, y)
                new_pos = (x + dx, y + dy)
                moves.append((idx, old_pos, new_pos))

                # Collect status changes - convert non-keyframes to keyframes
                point = self.curve_data[idx]
                if len(point) >= 4:
                    old_status = point[3]
                    # Convert bool to string if needed
                    if isinstance(old_status, bool):
                        old_status = "interpolated" if old_status else "normal"
                    # Only add status change if not already a keyframe
                    if old_status != PointStatus.KEYFRAME.value:
                        status_changes.append((idx, old_status, PointStatus.KEYFRAME.value))
                else:
                    # 3-tuple point has implicit "normal" status
                    status_changes.append((idx, "normal", PointStatus.KEYFRAME.value))

        if moves:
            # Create composite command with both move and status change (lazy import to avoid cycle)
            from core.commands.base_command import CompositeCommand
            from core.commands.curve_commands import BatchMoveCommand, SetPointStatusCommand

            composite = CompositeCommand(
                description=f"Nudge {len(moves)} point{'s' if len(moves) > 1 else ''} to keyframe"
            )

            # Add move command
            move_command = BatchMoveCommand(
                description=f"Move {len(moves)} point{'s' if len(moves) > 1 else ''}",
                moves=moves,
            )
            composite.add_command(move_command)

            # Add status change command if there are any non-keyframes
            if status_changes:
                status_command = SetPointStatusCommand(
                    description=f"Convert {len(status_changes)} point{'s' if len(status_changes) > 1 else ''} to keyframe",
                    changes=status_changes,
                )
                composite.add_command(status_command)

            # Execute the composite command through the interaction service's command manager
            interaction_service = get_interaction_service()
            if interaction_service and interaction_service.command_manager is not None and self.main_window is not None:
                # Protocol mismatch between local MainWindow and service's MainWindowProtocol
                # At runtime, the actual main_window satisfies both protocols
                interaction_service.command_manager.execute_command(composite, self.main_window)  # pyright: ignore[reportArgumentType]

    def delete_selected_points(self) -> None:
        """Delete selected points."""
        if not self.selected_indices or not self.main_window:
            return

        from services import get_interaction_service

        # Collect points to delete
        indices = list(self.selected_indices)
        deleted_points = []
        for idx in sorted(indices):
            if 0 <= idx < len(self.curve_data):
                deleted_points.append((idx, self.curve_data[idx]))

        if deleted_points:
            # Create and execute delete command (lazy import to avoid cycle)
            from core.commands.curve_commands import DeletePointsCommand

            command = DeletePointsCommand(
                description=f"Delete {len(deleted_points)} point{'s' if len(deleted_points) > 1 else ''}",
                indices=indices,
                deleted_points=deleted_points,
            )

            # Execute the command through the interaction service's command manager
            interaction_service = get_interaction_service()
            if interaction_service and interaction_service.command_manager is not None and self.main_window is not None:
                # Protocol mismatch between local MainWindow and service's MainWindowProtocol
                # At runtime, the actual main_window satisfies both protocols
                interaction_service.command_manager.execute_command(command, self.main_window)  # pyright: ignore[reportArgumentType]

        # Selection is cleared automatically by the command

    # Cache Management

    def invalidate_caches(self) -> None:
        """
        Invalidate all cached data.

        Note: Delegates to ViewCameraController (Phase 1) and RenderCacheController (Phase 5)
        """
        # Delegate transform cache invalidation to view_camera
        self.view_camera.invalidate_caches()

        # Delegate rendering cache invalidation to render_cache
        self.render_cache.invalidate_all()

    def _invalidate_point_region(self, index: int) -> None:
        """Note: Delegates to RenderCacheController (Phase 5 extraction)"""
        self.render_cache.invalidate_point_region(index)

    def _update_screen_points_cache(self) -> None:
        """Note: Delegates to RenderCacheController (Phase 5 extraction)"""
        self.render_cache.update_screen_points_cache()

    def _update_visible_indices(self, rect: QRect) -> None:
        """Note: Delegates to RenderCacheController (Phase 5 extraction)"""
        self.render_cache.update_visible_indices(rect)

    # Service Integration

    def set_main_window(self, main_window: MainWindow) -> None:
        """
        Set reference to main window.

        Args:
            main_window: Main window instance
        """
        self.main_window = main_window
        # Services are already initialized in __init__

        # Legacy compatibility - state_manager now injected via constructor
        # If state manager wasn't injected, try to get from main window as fallback
        if self._state_manager is None and getattr(main_window, "state_manager", None) is not None:
            self._state_manager = main_window.state_manager
            # Update controller's state manager reference and reconnect signals
            self.state_sync._state_manager = self._state_manager
            # Only connect if not already connected to prevent duplicates
            try:
                self._state_manager.frame_changed.connect(self.state_sync._on_state_frame_changed)
                logger.debug("Connected to fallback state manager from main window via StateSyncController")
            except (RuntimeError, TypeError) as e:
                # Signal might already be connected or other connection issue
                logger.debug(f"State manager signal connection issue: {e}")

        # State manager signals are connected above if needed

    def set_background_image(self, pixmap: QPixmap | None) -> None:
        """
        Set background image.

        Args:
            pixmap: Background image pixmap or None
        """
        self.background_image = pixmap

        # Update image dimensions to match the actual image
        # This ensures tracking data coordinates map correctly to image pixels
        if pixmap:
            self.image_width = pixmap.width()
            self.image_height = pixmap.height()
            logger.info(f"[COORD] Set image dimensions to {self.image_width}x{self.image_height} from background image")

        self.invalidate_caches()
        self.update()

    def get_view_state(self) -> ViewState:
        """
        Get current view state.

        Returns:
            ViewState object with current parameters
        """
        return self.view_camera.get_view_state()

    # Compatibility properties for InteractionService
    @property
    def selected_points(self) -> set[int]:
        """Compatibility property for InteractionService.

        Maps selected_indices to selected_points for backward compatibility.
        """
        return self.selected_indices

    @selected_points.setter
    def selected_points(self, value: set[int]) -> None:
        """Set selected points (compatibility with InteractionService)."""
        current_selection = self._curve_store.get_selection()
        if current_selection != value:  # Only update if changed
            # Clear and rebuild selection
            self._curve_store.clear_selection()
            for idx in value:
                self._curve_store.select(idx, add_to_selection=True)
            # Don't call update() here - InteractionService will call it

    @property
    def selected_point_idx(self) -> int:
        """Compatibility property for InteractionService.

        Returns the minimum selected index or -1 if none selected.
        """
        if self.selected_indices:
            return min(self.selected_indices)
        return -1

    @selected_point_idx.setter
    def selected_point_idx(self, value: int) -> None:
        """Set primary selected point (compatibility with InteractionService)."""
        if value >= 0:
            if value not in self._curve_store.get_selection():
                self._curve_store.select(value, add_to_selection=True)
                self.update()

    @property
    def points(self) -> list[tuple[int, float, float] | tuple[int, float, float, str | bool]]:
        """Compatibility property for InteractionService.

        Returns curve_data for backward compatibility.
        """
        return self.curve_data

    @points.setter
    def points(self, value: list[tuple[int, float, float] | tuple[int, float, float, str | bool]]) -> None:
        """Set points data (compatibility with InteractionService)."""
        self.set_curve_data(value)

    @property
    def current_frame_point_color(self) -> QColor:
        """Get current frame point color from centralized color system."""
        from ui.ui_constants import SPECIAL_COLORS

        return QColor(SPECIAL_COLORS["current_frame"])

    def _get_live_curves_data(self) -> dict[str, CurveDataList]:
        """
        Get curves data with live status information for active curve.

        This fixes the gap visualization issue by ensuring the active curve
        uses live data from the curve store (which has current status changes)
        instead of static data from the tracking controller.

        Returns:
            Dictionary of curve data with active curve having live status data
        """
        # Start with static curves data as base
        curves_data: dict[str, CurveDataList] | None = getattr(self, "curves_data", None)
        if not curves_data:
            return {}

        # Create a copy to avoid modifying the original
        live_curves_data: dict[str, CurveDataList] = curves_data.copy()

        # Get the active curve name from the tracking controller if available
        active_curve_name: str | None = getattr(self, "active_curve_name", None)

        # If we have an active curve and live curve store data, replace with live data
        if active_curve_name and active_curve_name in live_curves_data and hasattr(self, "_curve_store"):
            live_data = self._curve_store.get_data()
            if live_data:
                # Replace the active curve's static data with live data from store
                live_curves_data[active_curve_name] = live_data
                logger.debug(
                    f"Using live curve store data for active curve '{active_curve_name}' ({len(live_data)} points)"
                )
            else:
                logger.debug(f"No live data available for active curve '{active_curve_name}'")

        return live_curves_data


# Example usage and testing
if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)

    # Create main window
    main_window = QMainWindow()
    main_window.setWindowTitle("CurveViewWidget Test")
    main_window.resize(1200, 800)

    # Create curve widget
    curve_widget = CurveViewWidget()

    # Set some test data
    test_data: list[tuple[int, float, float] | tuple[int, float, float, str]] = [
        (0, 100.0, 100.0),
        (10, 200.0, 150.0, "keyframe"),
        (20, 300.0, 200.0),
        (30, 400.0, 180.0, "interpolated"),
        (40, 500.0, 220.0),
        (50, 600.0, 250.0, "keyframe"),
    ]
    curve_widget.set_curve_data(list(test_data))

    # Enable features
    curve_widget.show_grid = True
    curve_widget.show_labels = True
    curve_widget.show_all_frame_numbers = True

    # Set as central widget
    main_window.setCentralWidget(curve_widget)

    # Connect signals for testing
    _ = curve_widget.point_selected.connect(lambda idx: print(f"Selected point {idx}"))
    _ = curve_widget.point_moved.connect(lambda idx, x, y: print(f"Moved point {idx} to ({x:.1f}, {y:.1f})"))
    _ = curve_widget.zoom_changed.connect(lambda z: print(f"Zoom: {z:.1f}x"))

    main_window.show()
    sys.exit(app.exec())
