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
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QFocusEvent,
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
from core.display_mode import DisplayMode
from core.models import PointCollection, PointStatus
from core.point_types import safe_extract_point
from core.signal_manager import SignalManager
from core.type_aliases import CurveDataInput, CurveDataList

# Import optimized renderer for 47x performance improvement
from rendering.optimized_curve_renderer import OptimizedCurveRenderer
from rendering.render_state import RenderState
from rendering.visual_settings import VisualSettings

# Import services
from services import get_interaction_service
from services.transform_service import Transform, ViewState
from ui.qt_utils import safe_slot
from ui.ui_constants import (
    DEFAULT_IMAGE_HEIGHT,
    DEFAULT_IMAGE_WIDTH,
)

if TYPE_CHECKING:
    from typing import Protocol

    from services.interaction_service import InteractionService
    from stores import StoreManager
    from stores.application_state import ApplicationState
    from ui.controllers.curve_view.state_sync_controller import StateSyncController
    from ui.controllers.view_camera_controller import ViewCameraController
    from ui.state_manager import StateManager

    class MainWindow(Protocol):
        """Main window protocol for type checking."""

        current_frame: int
        status_bar: QStatusBar
        state_manager: StateManager
        tracking_controller: Any  # MultiPointTrackingController - avoid cycle

        def add_to_history(self) -> None: ...
else:
    MainWindow = Any  # Runtime fallback to avoid import cycle
    InteractionService = Any  # Runtime fallback to avoid import cycle
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

    IMPORTANT ARCHITECTURE NOTES:

    1. RENDERING: All rendering is delegated to OptimizedCurveRenderer for performance.
       This widget does NOT implement its own painting methods - the renderer
       handles everything including background, grid, lines, points, etc.

    2. SELECTION STATE ARCHITECTURE (Phase 1-5 Refactoring):
       - Single Source of Truth: ApplicationState manages selection and display mode
       - display_mode is a COMPUTED PROPERTY (not stored) - eliminates sync bugs
       - Widget caches selection for rendering performance (O(1) membership checks)
       - Cache updated via selection_state_changed signal (reactive architecture)
       - Defense-in-depth: Value comparison + re-entrancy guards prevent loops

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

    def __init__(self, parent: QWidget | None = None, state_manager: StateManager | None = None) -> None:
        """
        Initialize the CurveViewWidget.

        Args:
            parent: Parent widget (typically MainWindow)
            state_manager: Optional state manager for dependency injection
        """
        super().__init__(parent)

        # Visual settings (single source of truth for rendering appearance)
        self.visual: VisualSettings = VisualSettings()

        # Signal management for proper cleanup
        self.signal_manager: SignalManager = SignalManager(self)

        # Store injected state manager
        self._state_manager: StateManager | None = state_manager

        # Get store manager and ApplicationState
        self._store_manager: StoreManager = get_store_manager()
        self._app_state: ApplicationState = get_application_state()

        # NEW: Subscribe to selection state changes for repainting
        # Use SignalManager to ensure automatic cleanup on widget destruction
        _ = self.signal_manager.connect(
            self._app_state.selection_state_changed,
            self._on_selection_state_changed,
            "selection_state_changed",
        )

        # State synchronization controller (Phase 3 extraction)
        # Handles all signal connections and reactive updates from stores
        from ui.controllers.curve_view.state_sync_controller import StateSyncController

        self.state_sync: StateSyncController = StateSyncController(self)
        self.state_sync.connect_all_signals()

        # Data management facade (Phase 4 extraction)
        # Encapsulates all data operations, delegating to ApplicationState
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
        # Display mode management (removed _display_mode storage - now read from ApplicationState)

        # CACHE COHERENCE STRATEGY (Read-Only Cache Pattern):
        # These fields cache ApplicationState selection for rendering performance (O(1) membership checks).
        # Cache synchronization: Automatically updated via selection_state_changed signal.
        # Signal handler (_on_selection_state_changed) updates these fields directly.
        #
        # Why cache? Rendering checks "if curve_name in self.selected_curve_names" on every frame.
        # Reading from ApplicationState each time would add overhead. Local set provides O(1) lookups.
        #
        # Cache validity: Guaranteed by Qt signals - always reflects ApplicationState after signal fires.
        # Updates: Use ApplicationState.set_selected_curves() or widget.set_selected_curves() - cache updates automatically.
        self._selected_curve_names: set[str] = set()  # Cache of ApplicationState.get_selected_curves()
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
        # Note: Visual rendering parameters (point_radius, line_width, show_grid, etc.)
        # are centralized in self.visual (VisualSettings). See CLAUDE.md for pattern.
        self.show_background: bool = True  # Architectural setting, not visual

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

        # Widget setup
        self._setup_widget()

        logger.info("CurveViewWidget initialized with OptimizedCurveRenderer and reactive store")

    @property
    def curve_data(self) -> CurveDataList:
        """Get active curve data from ApplicationState.

        NOTE: For code in MainWindow, prefer direct ApplicationState access:
            app_state = get_application_state()
            if (cd := app_state.active_curve_data) is None:
                return []
            curve_name, curve_data = cd

        This property is a convenience wrapper for other UI components.
        """
        active_curve = self._app_state.active_curve
        if not active_curve:
            logger.warning("No active curve set, returning empty data")
            return []
        return self._app_state.get_curve_data(active_curve)

    @curve_data.setter
    def curve_data(self, _value: CurveDataList) -> None:
        """Prevent writes - property is read-only.

        Raises:
            AttributeError: Always raised - property is read-only
        """
        raise AttributeError("widget.curve_data is read-only. Use app_state.set_curve_data(curve_name, data) instead.")

    @property
    def selected_indices(self) -> set[int]:
        """Get selection for active curve from ApplicationState."""
        active_curve = self._app_state.active_curve
        if not active_curve:
            logger.warning("No active curve set, returning empty selection")
            return set()
        return self._app_state.get_selection(active_curve)

    @selected_indices.setter
    def selected_indices(self, _value: set[int]) -> None:
        """Prevent writes - property is read-only.

        Raises:
            AttributeError: Always raised - property is read-only
        """
        raise AttributeError(
            "widget.selected_indices is read-only. Use app_state.set_selection(curve_name, indices) instead."
        )

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
    def curves_data(self) -> dict[str, CurveDataList]:
        """Get all curves data from ApplicationState.

        Phase 4: Removed __default__ filtering - all curves are real named curves.

        Returns dict mapping curve names to their data.
        """
        from stores.application_state import get_application_state

        app_state = get_application_state()
        result: dict[str, CurveDataList] = {}
        for curve_name in app_state.get_all_curve_names():
            result[curve_name] = app_state.get_curve_data(curve_name)
        return result

    @property
    def selected_curve_names(self) -> set[str]:
        """
        Get selected curve names (read-only).

        This is a cached view of ApplicationState.get_selected_curves().
        The cache is synchronized via selection_state_changed signal.

        For updates, use ApplicationState.set_selected_curves() directly,
        or use the set_selected_curves() method on this widget.
        """
        return self._selected_curve_names

    @property
    def display_mode(self) -> DisplayMode:
        """
        Get current display mode from ApplicationState.

        This is a VIEW of ApplicationState - always fresh, no stale data.
        Display mode is computed from selection inputs, never stored.

        Returns:
            DisplayMode computed from ApplicationState selection state

        Example:
            >>> widget = CurveViewWidget()
            >>> app_state = get_application_state()
            >>> app_state.set_show_all_curves(True)
            >>> widget.display_mode
            <DisplayMode.ALL_VISIBLE: 1>

            >>> app_state.set_selected_curves({"Track1", "Track2"})
            >>> app_state.set_show_all_curves(False)
            >>> widget.display_mode
            <DisplayMode.SELECTED: 2>
        """
        return self._app_state.display_mode

    # Note: display_mode setter removed in Phase 8 - use ApplicationState API instead
    # - app_state.set_show_all_curves(True) → ALL_VISIBLE
    # - app_state.set_selected_curves({...}) → SELECTED
    # - app_state.set_selected_curves(set()) → ACTIVE_ONLY

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
    def offset_x(self) -> float:
        """X offset for OptimizedCurveRenderer compatibility."""
        return self.pan_offset_x + self.manual_offset_x

    @property
    def offset_y(self) -> float:
        """Y offset for OptimizedCurveRenderer compatibility."""
        return self.pan_offset_y + self.manual_offset_y

    @property
    def x_offset(self) -> float:
        """X offset alias (protocol compatibility)."""
        return self.offset_x

    @property
    def y_offset(self) -> float:
        """Y offset alias (protocol compatibility)."""
        return self.offset_y

    def set_curve_data(self, data: CurveDataInput) -> None:
        """
        Set the curve data to display.

        Args:
            data: List of point tuples (frame, x, y, [status])

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        self.data_facade.set_curve_data(data)

    def add_point(self, point: tuple[int, float, float] | tuple[int, float, float, str]) -> int:
        """
        Add a single point to the curve.

        Args:
            point: Point tuple (frame, x, y, [status])

        Returns:
            Index of added point, or -1 if no active curve

        Note: Delegates to CurveDataFacade (Phase 4 extraction)
        """
        return self.data_facade.add_point(point)

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
        metadata: dict[str, dict[str, object]] | None = None,
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

    def add_curve(self, name: str, data: CurveDataList, metadata: dict[str, object] | None = None) -> None:
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

    def set_selected_curves(self, curve_names: list[str]) -> None:
        """
        Set which curves are currently selected for display.

        Note: Delegates to MultiPointTrackingController (Phase 6 extraction)

        In SELECTED display mode, only these selected curves will be displayed.
        The last curve in the list becomes the active curve for editing.

        Args:
            curve_names: List of curve names to select and display
        """
        if self.main_window is not None:
            self.main_window.tracking_controller.set_selected_curves(curve_names)
        else:
            # Fallback for tests or when main_window not available
            # Update via ApplicationState (cache updates automatically via signal)
            self._app_state.set_selected_curves(set(curve_names))
            # selected_curves_ordered is not reactive - update manually
            self.selected_curves_ordered = list(curve_names)

            # Set the last selected as the active curve for editing
            all_curve_names = self._app_state.get_all_curve_names()
            if curve_names and curve_names[-1] in all_curve_names:
                self.set_active_curve(curve_names[-1])

            self.update()
            logger.debug(f"Selected curves: {self._selected_curve_names}, Active: {self._app_state.active_curve}")

    def compute_render_state(self) -> RenderState:
        """
        Compute current render state with pre-computed visibility.

        This method creates a RenderState by extracting all necessary state
        from the widget and pre-computing which curves should be visible.
        This is more efficient than checking visibility for each curve during
        rendering.

        Performance Benefits:
            - Single visibility computation per frame instead of N checks
            - Eliminates repeated metadata lookups during rendering
            - Cleaner separation between state computation and rendering

        Returns:
            Immutable RenderState with visible_curves set pre-computed

        Example:
            >>> # In paintEvent()
            >>> render_state = self.compute_render_state()
            >>> self._renderer.render(painter, event, render_state)

        See Also:
            - RenderState.compute(): Factory method that performs the computation
        """
        from rendering.render_state import RenderState

        return RenderState.compute(self)

    def center_on_selected_curves(self) -> None:
        """
        Center the view on all selected curves.

        Note: Delegates to MultiPointTrackingController (Phase 6 extraction)

        Calculates the bounding box of all selected curves and centers the view on it.
        """
        if self.main_window is not None:
            self.main_window.tracking_controller.center_on_selected_curves()
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
                    all_points.extend(
                        (float(point[1]), float(point[2])) for point in curve_data if len(point) >= 3
                    )

            if not all_points:
                logger.debug("No points found in selected curves")
                return
            logger.debug(f"Collected {len(all_points)} points for centering")

            # Calculate fit bounds using service
            from services import get_transform_service

            transform_service = get_transform_service()
            center_x, center_y, optimal_zoom = transform_service.calculate_fit_bounds(
                all_points, self.width(), self.height(), padding_factor=1.2
            )

            # Apply zoom
            self.zoom_factor = optimal_zoom

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
        from ui.color_manager import COLORS_DARK

        # Clear background with theme color
        bg_color = QColor(COLORS_DARK["bg_primary"])
        painter.fillRect(event.rect(), bg_color)

        # DELEGATE ALL RENDERING TO OPTIMIZED RENDERER
        # This is the ONLY rendering path - do not add paint methods to this widget

        # Compute render state with pre-computed visibility (performance optimization)
        # This eliminates redundant visibility checks during rendering by computing
        # the visible_curves set once instead of checking each curve multiple times
        render_state = self.compute_render_state()

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
            painter.drawEllipse(pos, self.visual.point_radius + 5, self.visual.point_radius + 5)

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
        from ui.color_manager import COLORS_DARK

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
        radius = max(self.visual.point_radius, self.visual.selected_point_radius) + 10  # Extra padding for hover

        # Return rectangle around point
        return QRect(int(screen_pos.x() - radius), int(screen_pos.y() - radius), int(radius * 2), int(radius * 2))

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events.

        Delegates business logic to InteractionService while maintaining Qt-specific
        widget lifecycle (focus management, repaint).

        Args:
            event: Mouse event
        """
        # Widget-specific: Ensure keyboard focus when clicked
        if not self.hasFocus():
            logger.info("[FOCUS] CurveViewWidget gaining focus from mouse press")
        self.setFocus(Qt.FocusReason.MouseFocusReason)

        # Delegate business logic to InteractionService
        # Note: Properties satisfy protocol attributes at runtime (variance issue)
        self.interaction_service.handle_mouse_press(self, event)  # pyright: ignore[reportArgumentType]

        # Widget-specific: Trigger repaint
        self.update()

    @override
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse move events.

        Delegates business logic to InteractionService while maintaining widget-specific
        hover tracking for visual feedback.

        Args:
            event: Mouse event
        """
        pos = event.position()

        # Widget-specific: Update hover index for visual feedback (cursor highlighting)
        old_hover = self.hover_index
        self.hover_index = self._find_point_at(pos)
        if self.hover_index != old_hover:
            # Partial repaint optimization - only update affected point areas
            if old_hover >= 0:
                old_rect = self._get_point_update_rect(old_hover)
                self.update(old_rect)
            if self.hover_index >= 0:
                new_rect = self._get_point_update_rect(self.hover_index)
                self.update(new_rect)

        # Delegate business logic (drag, pan, rubber band) to InteractionService
        # Note: Properties satisfy protocol attributes at runtime (variance issue)
        self.interaction_service.handle_mouse_move(self, event)  # pyright: ignore[reportArgumentType]

    @override
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse release events.

        Delegates business logic to InteractionService.

        Args:
            event: Mouse event
        """
        # Delegate business logic (drag cleanup, pan cleanup, rubber band finalization)
        # Note: Properties satisfy protocol attributes at runtime (variance issue)
        self.interaction_service.handle_mouse_release(self, event)  # pyright: ignore[reportArgumentType]

        # Widget-specific: Trigger repaint
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
                # Connect to handler (store status/index as properties to avoid lambda)
                action.setProperty("point_status", status)
                action.setProperty("point_index", idx)
                _ = action.triggered.connect(self._set_point_status)

            # Add separator
            _ = menu.addSeparator()

            # Add info display
            frame_num = point[0]
            info_action = menu.addAction(f"Frame {frame_num}")
            info_action.setEnabled(False)

            # Show menu at cursor position
            _ = menu.exec(event.globalPos())

        else:
            # No point under cursor, show general menu or pass to parent
            super().contextMenuEvent(event)

    def _set_point_status(self, checked: bool = False) -> None:
        """
        Change the status of a point (from QAction.triggered signal).

        Args:
            checked: Action checked state (from QAction.triggered signal)
        """
        # Get status and index from sender action properties
        action = self.sender()
        if not action:
            return
        status = action.property("point_status")
        idx = action.property("point_index")
        if status is None or idx is None:
            return

        # Update via ApplicationState - use active_curve_data property
        if (cd := self._app_state.active_curve_data) is None:
            return
        curve_name, curve_data = cd

        if 0 <= idx < len(curve_data):
            point = curve_data[idx]
            frame = point[0]
            logger.info(f"Changed point {idx} (frame {frame}) status to {status.value}")

            # Update point status via ApplicationState
            from core.models import CurvePoint

            updated_point = CurvePoint.from_tuple(point).with_status(status)
            self._app_state.update_point(curve_name, idx, updated_point)

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
    def focusInEvent(self, event: QFocusEvent) -> None:
        """Handle focus in event."""
        logger.info(f"[FOCUS] CurveViewWidget gained focus! Reason: {event.reason()}")
        super().focusInEvent(event)

    @override
    def focusOutEvent(self, event: QFocusEvent) -> None:
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
        The main frame update logic is handled by FrameChangeCoordinator.

        Args:
            frame: The new current frame number
        """
        # The StateManager will be updated by the caller, which will trigger our signal handler
        # This method is kept for compatibility with any direct calls

        # Handle centering mode for legacy compatibility
        if self.centering_mode:
            self.center_on_frame(frame)

    @safe_slot
    def _on_selection_state_changed(self, selected_curves: set[str], _show_all: bool) -> None:
        """
        Update widget and repaint when ApplicationState selection changes.

        FIX #2: Sync widget fields that renderer might use.
        The widget maintains local copies of selected_curve_names and
        selected_curves_ordered for rendering performance. These MUST
        be kept in sync with ApplicationState.

        Args:
            selected_curves: Selected curve names from ApplicationState
            _show_all: Show-all mode from ApplicationState (unused, display_mode computed from ApplicationState)
        """
        # FIX #2: Update widget's local fields for rendering
        # These are caches of ApplicationState for O(1) membership checks
        # IMPORTANT: Use direct field access to avoid triggering setter
        # which would create circular ApplicationState updates
        self._selected_curve_names = selected_curves.copy()
        self.selected_curves_ordered = list(selected_curves)

        # Trigger repaint to reflect updated state
        # display_mode property automatically reflects new ApplicationState
        self.update()

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

    def pan(self, delta_x: float, delta_y: float) -> None:
        """
        Pan the view by screen pixel deltas.

        Args:
            delta_x: Horizontal screen pixels to pan (positive = right)
            delta_y: Vertical screen pixels to pan (positive = down)

        Note: Delegates to ViewCameraController (Phase 1 extraction)
        """
        self.view_camera.pan(delta_x, delta_y)

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
        result = self.interaction_service.find_point_at(self, pos.x(), pos.y())  # pyright: ignore[reportArgumentType]

        # Extract index from PointSearchResult (Increment 4 changed return type)
        # PointSearchResult.index is always int, -1 if not found
        point_index: int = result.index

        return point_index

    def select_point(self, point_index: int, add_to_selection: bool = False, curve_name: str | None = None) -> None:
        """
        Public API for point selection.

        Args:
            point_index: Index of point to select
            add_to_selection: If True, add to existing selection; if False, replace selection
            curve_name: Optional curve name (defaults to active curve if None)
        """
        self._select_point(point_index, add_to_selection, curve_name)

    def _select_point(self, index: int, add_to_selection: bool = False, curve_name: str | None = None) -> None:
        """
        Select a point (internal implementation).

        Args:
            index: Point index
            add_to_selection: Whether to add to existing selection
            curve_name: Optional curve name if selecting from multi-curve mode
        """
        # Handle multi-curve selection
        all_curve_names = self._app_state.get_all_curve_names()
        if curve_name and curve_name in all_curve_names:
            # Add this curve to selected curves for visibility
            # Update via ApplicationState (cache updates automatically via signal)
            current_selected = self._app_state.get_selected_curves()
            self._app_state.set_selected_curves(current_selected | {curve_name})

            # If selecting from a different curve, switch to it
            if curve_name != self._app_state.active_curve:
                logger.debug(
                    f"[MULTI-CURVE] Switching active curve from {self._app_state.active_curve} to {curve_name}"
                )
                self.set_active_curve(curve_name)

        # Update via ApplicationState for active curve
        active = self._app_state.active_curve
        if active:
            # Match legacy toggle behavior when add_to_selection=True
            if add_to_selection:
                # Toggle: add if not selected, remove if already selected
                current_selection = self._app_state.get_selection(active)
                if index in current_selection:
                    self._app_state.remove_from_selection(active, index)
                else:
                    self._app_state.add_to_selection(active, index)
            else:
                self._app_state.set_selection(active, {index})

        # Emit our own signal for compatibility
        self.point_selected.emit(index)

        # Update interaction service if available
        if self.interaction_service and self.main_window:
            # Note: Protocol mismatch with InteractionService - using pyright: ignore for service integration
            self.interaction_service.on_point_selected(self, self.main_window, index)  # pyright: ignore[reportArgumentType]

    def clear_selection(self) -> None:
        """Clear all selection.

        Phase 4: Removed __default__ sync - uses active curve.
        """
        # Update via ApplicationState for active curve
        active = self._app_state.active_curve
        if active:
            self._app_state.clear_selection(active)

    def select_all(self) -> None:
        """Select all points.

        Phase 4: Removed __default__ sync - uses active curve.
        """
        # Update via ApplicationState for active curve
        active = self._app_state.active_curve
        if active:
            # Get all indices from curve data
            all_indices = set(range(len(self._app_state.get_curve_data(active))))
            self._app_state.set_selection(active, all_indices)

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

    # Main Window Helper Methods

    @property
    def has_main_window(self) -> bool:
        """Check if main window is available."""
        return self.main_window is not None

    def update_status(self, message: str, timeout: int = 2000) -> None:
        """Update status bar if main window available.

        Args:
            message: Status message to display
            timeout: Timeout in milliseconds
        """
        if self.main_window is not None and getattr(self.main_window, "status_bar", None) is not None:
            self.main_window.status_bar.showMessage(message, timeout)

    def get_current_frame(self) -> int | None:
        """Get the current frame from ApplicationState if available.
        Used by renderer for frame highlighting.
        Returns None if ApplicationState is not accessible.
        """
        try:
            return get_application_state().current_frame
        except (AttributeError, RuntimeError):
            return None

    @property
    def current_frame(self) -> int:
        """Current frame property - reads from ApplicationState."""
        try:
            return get_application_state().current_frame
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
        Nudge selected points and convert them to keyframes (except endframes which are preserved).

        Args:
            dx: X offset in data units
            dy: Y offset in data units
        """
        if not self.selected_indices or not self.main_window:
            return

        from services import get_interaction_service

        # Collect moves and status changes
        moves: list[tuple[int, tuple[float, float], tuple[float, float]]] = []
        status_changes: list[tuple[int, str, str]] = []
        for idx in self.selected_indices:
            if 0 <= idx < len(self.curve_data):
                _, x, y, _ = safe_extract_point(self.curve_data[idx])
                old_pos = (x, y)
                new_pos = (x + dx, y + dy)
                moves.append((idx, old_pos, new_pos))

                # Collect status changes - convert non-keyframes to keyframes
                # EXCEPT endframes which should be preserved
                point = self.curve_data[idx]
                if len(point) >= 4:
                    old_status = point[3]
                    # Convert bool to string if needed
                    if isinstance(old_status, bool):
                        old_status_str: str = "interpolated" if old_status else "normal"
                    else:
                        old_status_str = str(old_status)
                    # Only add status change if not already a keyframe AND not an endframe
                    # Endframes should remain endframes when nudged
                    if old_status_str != PointStatus.KEYFRAME.value and old_status_str != PointStatus.ENDFRAME.value:
                        status_changes.append((idx, old_status_str, PointStatus.KEYFRAME.value))
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
            if interaction_service and self.main_window:
                # Protocol variance: MainWindow satisfies MainWindowProtocol at runtime
                _ = interaction_service.command_manager.execute_command(composite, self.main_window)  # pyright: ignore[reportArgumentType]

    def delete_selected_points(self) -> None:
        """Delete selected points."""
        if not self.selected_indices or not self.main_window:
            return

        from services import get_interaction_service

        # Collect points to delete
        indices = list(self.selected_indices)
        deleted_points = [(idx, self.curve_data[idx]) for idx in sorted(indices) if 0 <= idx < len(self.curve_data)]

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
            if interaction_service and self.main_window:
                # Protocol variance: MainWindow satisfies MainWindowProtocol at runtime
                _ = interaction_service.command_manager.execute_command(command, self.main_window)  # pyright: ignore[reportArgumentType]

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

        # Invalidate SegmentedCurve cache in optimized renderer
        self._optimized_renderer.clear_segmented_curve_cache()

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

        # State manager is injected via constructor (ui_initialization_controller.py)
        # Signal connections are made in __init__ via state_sync.connect_all_signals()
        # No fallback needed - proper initialization order is enforced

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
        current_selection = self.selected_indices
        if current_selection != value:  # Only update if changed
            # Update via ApplicationState for active curve
            active = self._app_state.active_curve
            if active:
                self._app_state.set_selection(active, set(value))
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
            active = self._app_state.active_curve
            if active and value not in self._app_state.get_selection(active):
                self._app_state.add_to_selection(active, value)
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
        from ui.color_manager import SPECIAL_COLORS

        return QColor(SPECIAL_COLORS["current_frame"])

    # Protocol Compatibility Methods (CurveViewProtocol)

    @property
    def current_image_idx(self) -> int:
        """Get current image index (protocol compatibility).

        Delegates to main_window.current_image_idx if available, otherwise returns 0.
        """
        if self.main_window is not None:
            return getattr(self.main_window, "current_image_idx", 0)
        return 0

    @current_image_idx.setter
    def current_image_idx(self, _value: int) -> None:
        """Set current image index (protocol compatibility).

        Note: This is a no-op as image index is managed by ViewManagementController.
        """
        # Image index is managed by ViewManagementController in main_window
        # This setter exists for protocol compatibility but doesn't modify state

    def findPointAt(self, pos: QPointF) -> int:
        """Find point at position (protocol compatibility).

        Args:
            pos: Position in screen coordinates

        Returns:
            Point index or -1 if no point found
        """
        return self._find_point_at(pos)

    def selectPointByIndex(self, idx: int) -> bool:
        """Select point by index (protocol compatibility).

        Args:
            idx: Point index to select

        Returns:
            True if point was selected successfully
        """
        self._select_point(idx)
        return idx >= 0 and idx < len(self.curve_data)

    def get_current_transform(self) -> object:
        """Get current transform (protocol compatibility).

        Alias for get_transform().
        """
        return self.get_transform()

    def _invalidate_caches(self) -> None:
        """Invalidate caches (protocol compatibility).

        Alias for invalidate_caches().
        """
        self.invalidate_caches()

    def get_point_data(self, idx: int) -> tuple[int, float, float, str | None]:
        """Get point data for given index (protocol compatibility).

        Args:
            idx: Point index

        Returns:
            Tuple of (frame, x, y, status_str)
        """
        if 0 <= idx < len(self.curve_data):
            point = self.curve_data[idx]
            if len(point) == 3:
                frame, x, y = point
                return (frame, x, y, None)
            frame, x, y, status = point
            status_str = status if isinstance(status, str) else None
            return (frame, x, y, status_str)
        return (-1, 0.0, 0.0, None)

    def toggleBackgroundVisible(self, visible: bool) -> None:
        """Toggle background visibility (protocol compatibility).

        Args:
            visible: Whether background should be visible
        """
        self.show_background = visible
        self.update()

    def toggle_point_interpolation(self, _idx: int) -> None:
        """Toggle interpolation status of a point (protocol compatibility).

        Args:
            _idx: Point index to toggle (unused)
        """
        # This is a no-op as interpolation status is managed differently
        # in the current architecture (via PointStatus)

    def setPoints(self, data: CurveDataList, width: int, height: int) -> None:
        """Set points with image dimensions (protocol compatibility).

        Args:
            data: Curve data list
            width: Image width
            height: Image height
        """
        self.image_width = width
        self.image_height = height
        self.set_curve_data(data)

    def set_selected_indices(self, indices: list[int]) -> None:
        """Set selected point indices (protocol compatibility).

        Args:
            indices: List of indices to select
        """
        # Update via ApplicationState for active curve
        active = self._app_state.active_curve
        if active:
            # Filter valid indices
            valid_indices = {idx for idx in indices if 0 <= idx < len(self.curve_data)}
            self._app_state.set_selection(active, valid_indices)
        self.update()

    def setup_for_3dequalizer_data(self) -> None:
        """Set up view for 3DEqualizer coordinate tracking data (protocol compatibility).

        3DEqualizer uses normalized coordinates, so this is similar to pixel tracking
        but may have different coordinate space assumptions.
        """
        # For now, use same setup as pixel tracking
        # (Both use screen-space coordinates that scale with background)
        self.setup_for_pixel_tracking()

    def _get_live_curves_data(self) -> dict[str, CurveDataList]:
        """
        Get curves data with live status information for active curve.

        This fixes the gap visualization issue by ensuring the active curve
        uses live data from the curve store (which has current status changes)
        instead of static data from the tracking controller.

        Returns:
            Dictionary of curve data with active curve having live status data
        """
        # All curve data now comes from ApplicationState (Phase 6.3)
        # Read directly from ApplicationState for live data
        all_curves = self._app_state.get_all_curves()

        # If no data in ApplicationState, check for static curves_data attribute (legacy)
        if not all_curves:
            curves_data: dict[str, CurveDataList] | None = getattr(self, "curves_data", None)
            if curves_data:
                return curves_data.copy()
            return {}

        return all_curves


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
    curve_widget.visual.show_grid = True
    curve_widget.visual.show_labels = True
    curve_widget.visual.show_all_frame_numbers = True

    # Set as central widget
    main_window.setCentralWidget(curve_widget)

    # Connect signals for testing
    # Note: Test code - type ignores not needed for example code
    _ = curve_widget.point_selected.connect(lambda idx: print(f"Selected point {idx}"))
    _ = curve_widget.point_moved.connect(lambda idx, x, y: print(f"Moved point {idx} to ({x:.1f}, {y:.1f})"))
    _ = curve_widget.zoom_changed.connect(lambda z: print(f"Zoom: {z:.1f}x"))

    main_window.show()
    sys.exit(app.exec())
