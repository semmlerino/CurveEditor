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

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

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

# Import core modules
from core.models import CurvePoint, PointCollection, PointStatus
from core.point_types import safe_extract_point
from core.signal_manager import SignalManager
from core.type_aliases import CurveDataList

# Import optimized renderer for 47x performance improvement
from rendering.optimized_curve_renderer import OptimizedCurveRenderer

# Import services
from services import get_interaction_service
from services.transform_service import Transform, ViewState
from ui.ui_constants import (
    DEFAULT_BACKGROUND_OPACITY,
    DEFAULT_IMAGE_HEIGHT,
    DEFAULT_IMAGE_WIDTH,
    DEFAULT_NUDGE_AMOUNT,
    DEFAULT_ZOOM_FACTOR,
)

if TYPE_CHECKING:
    from typing import Protocol

    class MainWindow(Protocol):
        """Main window protocol for type checking."""

        current_frame: int
        status_bar: QStatusBar

        def add_to_history(self) -> None: ...
else:
    MainWindow = Any  # Runtime fallback to avoid import cycle

from core.logger_utils import get_logger

# Import stores
from stores import get_store_manager

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

    def __init__(self, parent: QWidget | None = None):
        """
        Initialize the CurveViewWidget.

        Args:
            parent: Parent widget (typically MainWindow)
        """
        super().__init__(parent)

        # Signal management for proper cleanup
        self.signal_manager: SignalManager = SignalManager(self)

        # Get the reactive data store
        self._store_manager = get_store_manager()
        self._curve_store = self._store_manager.get_curve_store()

        # Connect to store signals for reactive updates
        self._connect_store_signals()

        # Core data (now derived from store)
        self.point_collection: PointCollection | None = None
        self.hover_index: int = -1

        # View transformation
        self.zoom_factor: float = DEFAULT_ZOOM_FACTOR
        self.pan_offset_x: float = 0.0
        self.pan_offset_y: float = 0.0
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

        # Interaction state
        self.drag_active: bool = False
        self.pan_active: bool = False
        self.rubber_band_active: bool = False
        self.last_mouse_pos: QPointF | None = None
        self.drag_start_pos: QPointF | None = None
        self.dragged_index: int = -1
        self._context_menu_point: int = -1

        # Rubber band selection
        self.rubber_band: QRubberBand | None = None
        self.rubber_band_origin: QPointF = QPointF()

        # Performance optimization
        self._transform_cache: Transform | None = None
        self._screen_points_cache: dict[int, QPointF] = {}
        self._visible_indices_cache: set[int] = set()
        self._update_region: QRectF | None = None

        # Services (will be set by main window)
        self.main_window: MainWindow | None = None
        self.interaction_service: object = (
            get_interaction_service()
        )  # InteractionService type not imported to avoid cycle

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
        return self._curve_store.get_selection()

    def _connect_store_signals(self) -> None:
        """Connect to reactive store signals for automatic updates."""
        # Connect store signals to widget updates
        self._curve_store.data_changed.connect(self._on_store_data_changed)
        self._curve_store.point_added.connect(self._on_store_point_added)
        self._curve_store.point_updated.connect(self._on_store_point_updated)
        self._curve_store.point_removed.connect(self._on_store_point_removed)
        self._curve_store.point_status_changed.connect(self._on_store_status_changed)
        self._curve_store.selection_changed.connect(self._on_store_selection_changed)

        logger.debug("Connected to reactive store signals")

    def _on_store_data_changed(self) -> None:
        """Handle store data changed signal."""
        # Update internal point collection
        data = self.curve_data
        if data:
            formatted_data = []
            for point in data:
                if len(point) >= 3:
                    formatted_data.append((int(point[0]), float(point[1]), float(point[2])))
            self.point_collection = PointCollection.from_tuples(formatted_data)
        else:
            self.point_collection = None

        # Clear caches and update display
        self.invalidate_caches()
        self.update()

        # Propagate signal to widget listeners
        self.data_changed.emit()

    def _on_store_point_added(self, index: int, point: object) -> None:
        """Handle store point added signal."""
        # Update collection if needed
        if self.point_collection:
            self.point_collection.points.append(CurvePoint.from_tuple(point))
        else:
            self.point_collection = PointCollection([CurvePoint.from_tuple(point)])

        self._invalidate_point_region(index)
        self.update()
        self.data_changed.emit()

    def _on_store_point_updated(self, index: int, x: float, y: float) -> None:
        """Handle store point updated signal."""
        # Update collection
        if self.point_collection and index < len(self.point_collection.points):
            old_cp = self.point_collection.points[index]
            self.point_collection.points[index] = old_cp.with_coordinates(x, y)

        self._invalidate_point_region(index)
        self.point_moved.emit(index, x, y)
        self.update()
        self.data_changed.emit()

    def _on_store_point_removed(self, index: int) -> None:
        """Handle store point removed signal."""
        # Update collection
        if self.point_collection and index < len(self.point_collection.points):
            del self.point_collection.points[index]

        self.invalidate_caches()
        self.update()
        self.data_changed.emit()

    def _on_store_status_changed(self, index: int, status: str) -> None:
        """Handle store point status changed signal."""
        # Update collection if needed
        if self.point_collection and index < len(self.point_collection.points):
            old_cp = self.point_collection.points[index]
            # Map string status to PointStatus enum using from_legacy
            status_enum = PointStatus.from_legacy(status)
            self.point_collection.points[index] = old_cp.with_status(status_enum)

        self.update()
        self.data_changed.emit()
        # Emit point_moved for compatibility with old code that listens for status changes
        point = self._curve_store.get_point(index)
        if point and len(point) >= 3:
            self.point_moved.emit(index, point[1], point[2])

    def _on_store_selection_changed(self, selection: set[int]) -> None:
        """Handle store selection changed signal."""
        # Update display and notify listeners
        self.update()
        self.selection_changed.emit(list(selection))

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
            "• Numpad 2/4/6/8: Nudge selected points (down/left/right/up)\n"
            "• Shift+Numpad: Nudge by 10x amount\n"
            "• Ctrl+Numpad: Nudge by 0.1x amount"
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

    def set_curve_data(self, data: CurveDataList) -> None:
        """
        Set the curve data to display.

        Args:
            data: List of point tuples (frame, x, y, [status])
        """
        # Delegate to store - it will emit signals that trigger our updates
        self._curve_store.set_data(data)
        logger.debug(f"Set curve data with {len(data)} points via store")

    def add_point(self, point: tuple[int, float, float] | tuple[int, float, float, str]) -> None:
        """
        Add a single point to the curve.

        Args:
            point: Point tuple (frame, x, y, [status])
        """
        # Delegate to store - it will emit signals that trigger our updates
        self._curve_store.add_point(point)

    def update_point(self, index: int, x: float, y: float) -> None:
        """
        Update coordinates of a point.

        Args:
            index: Point index
            x: New X coordinate
            y: New Y coordinate
        """
        # Delegate to store - it will emit signals that trigger our updates
        self._curve_store.update_point(index, x, y)

    def remove_point(self, index: int) -> None:
        """
        Remove a point from the curve.

        Args:
            index: Point index to remove
        """
        # Delegate to store - it will emit signals that trigger our updates
        # Store handles selection updates automatically
        self._curve_store.remove_point(index)

    # Coordinate Transformation

    def get_transform(self) -> Transform:
        """
        Get the current transformation object.

        Returns:
            Transform object for coordinate mapping
        """
        if self._transform_cache is None:
            self._update_transform()
        assert self._transform_cache is not None
        return self._transform_cache

    def _update_transform(self) -> None:
        """Update the cached transformation object using TransformService for LRU caching."""
        # SPRINT 11.5 FIX: Use TransformService with caching instead of creating Transform directly
        # This provides the claimed 99.9% cache hit rate for transform operations

        from services import get_transform_service

        # Calculate display dimensions
        # When Y-flip is enabled (for pixel tracking), use widget dimensions for coordinate system
        # Otherwise use image dimensions for traditional image-based coordinates
        if self.flip_y_axis:
            display_width = self.width()
            display_height = self.height()
        else:
            display_width = self.image_width
            display_height = self.image_height

            if self.background_image:
                display_width = self.background_image.width()
                display_height = self.background_image.height()

        logger.info(
            f"[TRANSFORM] Display dimensions: {display_width}x{display_height}, zoom_factor: {self.zoom_factor}"
        )

        # Calculate centering offsets
        widget_width = self.width()
        widget_height = self.height()
        logger.info(f"[TRANSFORM] Widget dimensions: {widget_width}x{widget_height}")

        # Base scale to fit content in widget
        scale_x = widget_width / display_width if display_width > 0 else 1.0
        scale_y = widget_height / display_height if display_height > 0 else 1.0
        base_scale = min(scale_x, scale_y) * 0.9  # 90% to leave margin

        # Apply zoom on top of base scale
        total_scale = base_scale * self.zoom_factor

        # Calculate center offsets
        scaled_width = display_width * total_scale
        scaled_height = display_height * total_scale
        _ = (widget_width - scaled_width) / 2  # center_offset_x - calculated but not used in current implementation
        _ = (widget_height - scaled_height) / 2  # center_offset_y - calculated but not used in current implementation

        # Image scale factors for data-to-image mapping
        _ = display_width / self.image_width  # image_scale_x - calculated but not used in current implementation
        _ = display_height / self.image_height  # image_scale_y - calculated but not used in current implementation

        # Create ViewState for caching
        view_state = ViewState(
            display_width=int(display_width),
            display_height=int(display_height),
            widget_width=int(widget_width),
            widget_height=int(widget_height),
            zoom_factor=self.zoom_factor,
            offset_x=self.pan_offset_x,
            offset_y=self.pan_offset_y,
            scale_to_image=self.scale_to_image,
            flip_y_axis=self.flip_y_axis,
            manual_x_offset=self.manual_offset_x,
            manual_y_offset=self.manual_offset_y,
            background_image=self.background_image,
            image_width=self.image_width,
            image_height=self.image_height,
        )

        # Use cached transform service - this enables 99.9% cache hits
        transform_service = get_transform_service()
        self._transform_cache = transform_service.create_transform_from_view_state(view_state)

        # Log cache stats for verification
        cache_info = transform_service.get_cache_info()
        if cache_info["hits"] > 0:
            logger.debug(
                f"[TRANSFORM CACHE] Hit rate: {cache_info['hit_rate']:.1%} ({cache_info['hits']}/{cache_info['hits'] + cache_info['misses']})"
            )

    def data_to_screen(self, x: float, y: float) -> QPointF:
        """
        Convert data coordinates to screen coordinates.

        Args:
            x: Data X coordinate
            y: Data Y coordinate

        Returns:
            Screen position as QPointF
        """
        transform = self.get_transform()
        screen_x, screen_y = transform.data_to_screen(x, y)
        return QPointF(screen_x, screen_y)

    def screen_to_data(self, pos: QPointF) -> tuple[float, float]:
        """
        Convert screen coordinates to data coordinates.

        Args:
            pos: Screen position

        Returns:
            Data coordinates as (x, y) tuple
        """
        transform = self.get_transform()
        return transform.screen_to_data(pos.x(), pos.y())

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
        self._optimized_renderer.render(painter, event, self)

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
        if self.hover_index >= 0 and self.hover_index in self._screen_points_cache:
            painter.save()

            pos = self._screen_points_cache[self.hover_index]

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
                idx = self._find_point_at(pos)
                if idx >= 0:
                    # Select and start dragging point
                    add_to_selection = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
                    self._select_point(idx, add_to_selection)
                    self.drag_active = True
                    self.dragged_index = idx
                    self.drag_start_pos = pos
                    self.last_mouse_pos = pos
                else:
                    # Clear selection if not Ctrl-clicking
                    if not (modifiers & Qt.KeyboardModifier.ControlModifier):
                        self._clear_selection()

        elif button == Qt.MouseButton.MiddleButton:
            # Start panning
            self.pan_active = True
            self.last_mouse_pos = pos
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
        elif self.drag_active and self.last_mouse_pos:
            delta = pos - self.last_mouse_pos
            self._drag_point(self.dragged_index, delta)
            self.last_mouse_pos = pos

        # Handle panning
        elif self.pan_active and self.last_mouse_pos:
            delta = pos - self.last_mouse_pos
            self.pan_offset_x += delta.x()
            # When Y-axis is flipped, invert the pan direction for Y
            # This ensures the curve follows the mouse drag direction
            if self.flip_y_axis:
                self.pan_offset_y -= delta.y()
            else:
                self.pan_offset_y += delta.y()
            self.last_mouse_pos = pos
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
                self.last_mouse_pos = None

                # Notify about changes
                self._add_to_history()

        elif button == Qt.MouseButton.MiddleButton:
            self.pan_active = False
            self.last_mouse_pos = None
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

        # Add to history if main window available
        self._add_to_history()

        point = self._curve_store.get_point(idx)
        if point:
            frame = point[0]
            logger.info(f"Changed point {idx} (frame {frame}) status to {status.value}")

    @override
    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        Handle mouse wheel events for zooming.

        Args:
            event: Wheel event
        """
        # Get mouse position for zoom center
        pos = event.position()

        # Calculate zoom factor
        delta = event.angleDelta().y()
        zoom_speed = 1.1
        zoom_factor = zoom_speed if delta > 0 else 1.0 / zoom_speed

        # Get current data position under mouse
        data_x, data_y = self.screen_to_data(pos)

        # Apply zoom
        old_zoom = self.zoom_factor
        self.zoom_factor = max(0.1, min(10.0, self.zoom_factor * zoom_factor))

        if self.zoom_factor != old_zoom:
            # Adjust pan to keep point under mouse stationary
            self.invalidate_caches()
            new_screen_pos = self.data_to_screen(data_x, data_y)

            offset = pos - new_screen_pos
            self.pan_offset_x += offset.x()

            # When Y-axis is flipped, invert the pan adjustment for Y
            # This ensures zoom keeps the point under cursor stationary
            if self.flip_y_axis:
                self.pan_offset_y -= offset.y()
            else:
                self.pan_offset_y += offset.y()

            # Invalidate caches again after pan adjustment
            self.invalidate_caches()

            self.update()
            self.zoom_changed.emit(self.zoom_factor)
            self.view_changed.emit()

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handle keyboard events.

        Keyboard shortcuts:
            Delete: Delete selected points
            Ctrl+A: Select all points
            Escape: Clear selection
            C: Center view on selected points
            F: Fit background image to view
            Numpad 2/4/6/8: Nudge selected points (Shift for 10x, Ctrl for 0.1x)

        Args:
            event: Key event
        """
        key = event.key()
        modifiers = event.modifiers()

        # Debug logging for all key events
        logger.info(
            f"[KEYPRESSEVENT] Key pressed: key={key} (Qt.Key.Key_C={Qt.Key.Key_C}), modifiers={modifiers}, has_focus={self.hasFocus()}"
        )

        # Debug logging to verify key events are received
        logger.debug(f"[KEYPRESS] Key: {key}, Modifiers: {modifiers}, HasFocus: {self.hasFocus()}")

        # Check if this is a numpad key
        is_numpad = bool(modifiers & Qt.KeyboardModifier.KeypadModifier)

        # Delete selected points
        if key == Qt.Key.Key_Delete and self.selected_indices:
            self._delete_selected_points()
            event.accept()

        # Select all
        elif key == Qt.Key.Key_A and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.select_all()
            event.accept()

        # Deselect all
        elif key == Qt.Key.Key_Escape:
            self._clear_selection()
            event.accept()

        # Toggle centering mode - keeps view centered on current frame/selection
        elif key == Qt.Key.Key_C and not (modifiers & ~Qt.KeyboardModifier.KeypadModifier):
            self.centering_mode = not self.centering_mode
            logger.info(f"[KEY_C] Centering mode {'enabled' if self.centering_mode else 'disabled'}")

            # If enabling centering mode, immediately center on selection or current frame
            if self.centering_mode:
                if self.selected_indices:
                    logger.info(f"[KEY_C] Centering view on {len(self.selected_indices)} selected points...")
                    self.center_on_selection()
                    logger.info("[KEY_C] View centering completed")
                else:
                    current_frame = self._get_current_frame()
                    if current_frame is not None:
                        logger.info(f"[KEY_C] No points selected, centering on current frame {current_frame}")
                        self.center_on_frame(current_frame)
                    logger.info("[KEY_C] View centered on current frame")

            # Update status bar to show centering mode state
            status_msg = "Centering: ON" if self.centering_mode else "Centering: OFF"
            self._update_status(status_msg, 2000)

            event.accept()

        # Fit background image to view
        elif key == Qt.Key.Key_F and not (modifiers & ~Qt.KeyboardModifier.KeypadModifier):
            if self.background_image:
                self.fit_to_background_image()
                logger.debug("[VIEW] Fitted background image to view")
                event.accept()
            else:
                event.ignore()

        # Nudge selected points using numpad keys
        elif self.selected_indices and is_numpad:
            # Check if it's a numpad number key for nudging
            handled = False

            # Calculate nudge amount based on modifiers (ignoring KeypadModifier)
            nudge_amount = DEFAULT_NUDGE_AMOUNT
            clean_modifiers = modifiers & ~Qt.KeyboardModifier.KeypadModifier
            if clean_modifiers & Qt.KeyboardModifier.ShiftModifier:
                nudge_amount = 10.0
            elif clean_modifiers & Qt.KeyboardModifier.ControlModifier:
                nudge_amount = 0.1

            if key == Qt.Key.Key_4:  # Numpad 4 - left
                self._nudge_selected(-nudge_amount, 0)
                handled = True
            elif key == Qt.Key.Key_6:  # Numpad 6 - right
                self._nudge_selected(nudge_amount, 0)
                handled = True
            elif key == Qt.Key.Key_8:  # Numpad 8 - up
                self._nudge_selected(0, -nudge_amount)
                handled = True
            elif key == Qt.Key.Key_2:  # Numpad 2 - down
                self._nudge_selected(0, nudge_amount)
                handled = True

            if handled:
                self.update()
                event.accept()
            else:
                event.ignore()

        # For arrow keys, always pass them through to parent for frame navigation
        elif key in [Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down]:
            event.ignore()  # Let parent handle arrow keys for frame navigation

        else:
            event.ignore()  # Let parent handle unrecognized keys

    # View Operations

    def reset_view(self) -> None:
        """Reset view to default state."""
        self.zoom_factor = DEFAULT_ZOOM_FACTOR
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.manual_offset_x = 0.0
        self.manual_offset_y = 0.0

        self.invalidate_caches()
        self.update()
        self.view_changed.emit()
        self.zoom_changed.emit(self.zoom_factor)

    def fit_to_view(self) -> None:
        """Fit all points in view."""
        if not self.curve_data:
            return

        # Get bounds of all points
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for point in self.curve_data:
            _, x, y, _ = safe_extract_point(point)
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

        # Calculate required zoom and offset
        data_width = max_x - min_x
        data_height = max_y - min_y

        if data_width > 0 and data_height > 0:
            # Calculate zoom to fit
            margin = 0.1  # 10% margin
            widget_width = self.width() * (1 - 2 * margin)
            widget_height = self.height() * (1 - 2 * margin)

            zoom_x = widget_width / data_width if data_width > 0 else 1.0
            zoom_y = widget_height / data_height if data_height > 0 else 1.0

            self.zoom_factor = min(zoom_x, zoom_y)

            # Center the data
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2

            # Reset offsets
            self.pan_offset_x = 0
            self.pan_offset_y = 0

            self.invalidate_caches()

            # Calculate center position
            screen_center = self.data_to_screen(center_x, center_y)
            widget_center = QPointF(self.width() / 2, self.height() / 2)

            # Adjust pan to center
            offset = widget_center - screen_center
            self.pan_offset_x = offset.x()
            self.pan_offset_y = offset.y()

    def on_frame_changed(self, frame: int) -> None:
        """Handle frame change event from timeline navigation.

        Centers the view on the current frame if centering mode is enabled.

        Args:
            frame: The new current frame number
        """
        if self.centering_mode:
            logger.debug(f"[CENTERING] Auto-centering on frame {frame} (centering mode enabled)")
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
        """Fit the background image fully in view."""
        if not self.background_image:
            return

        # Get actual image dimensions
        img_width = self.background_image.width()
        img_height = self.background_image.height()
        logger.info(f"[FIT_BG] Image dimensions: {img_width}x{img_height}")

        if img_width <= 0 or img_height <= 0:
            return

        # Get widget dimensions
        widget_width = self.width()
        widget_height = self.height()
        logger.info(f"[FIT_BG] Widget dimensions: {widget_width}x{widget_height}")

        if widget_width <= 0 or widget_height <= 0:
            return

        # Calculate the scale needed to fit the image
        # We want to fit the entire image, so use the smaller scale
        # Apply 95% margin for visual breathing room
        margin = 0.95
        scale_x = (widget_width * margin) / img_width
        scale_y = (widget_height * margin) / img_height
        desired_scale = min(scale_x, scale_y)
        logger.info(
            f"[FIT_BG] Calculated desired_scale: {desired_scale} (scale_x={scale_x}, scale_y={scale_y}, margin={margin})"
        )

        # The transform system uses zoom_factor directly as the scale
        # So we can set zoom_factor to our desired_scale directly
        old_zoom = self.zoom_factor
        self.zoom_factor = desired_scale
        logger.info(f"[FIT_BG] Set zoom_factor: {old_zoom} -> {self.zoom_factor}")

        # Reset manual offsets
        old_manual_x, old_manual_y = self.manual_offset_x, self.manual_offset_y
        self.manual_offset_x = 0
        self.manual_offset_y = 0
        logger.info(f"[FIT_BG] Reset manual offsets: ({old_manual_x}, {old_manual_y}) -> (0, 0)")

        # Reset pan offsets - let Transform's automatic centering handle positioning
        old_pan_x, old_pan_y = self.pan_offset_x, self.pan_offset_y
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        logger.info(f"[FIT_BG] Reset pan offsets: ({old_pan_x}, {old_pan_y}) -> (0, 0)")

        # Invalidate caches and update
        self.invalidate_caches()

        # Debug the transform after setting everything up
        transform = self.get_transform()
        params = transform.get_parameters()
        logger.info(f"[FIT_BG] Final transform scale: {params['scale']}")
        logger.info(f"[FIT_BG] Final center offsets: ({params['center_offset_x']}, {params['center_offset_y']})")
        logger.info(f"[FIT_BG] Final pan offsets: ({params['pan_offset_x']}, {params['pan_offset_y']})")

        # Test image positioning - account for Y-flip
        if self.flip_y_axis:
            # With Y-flip, image top is at Y=image_height in data space
            top_left_x, top_left_y = transform.data_to_screen(0, img_height)
        else:
            # Without Y-flip, image top is at Y=0 in data space
            top_left_x, top_left_y = transform.data_to_screen(0, 0)
        logger.info(f"[FIT_BG] Image top-left will be at: ({top_left_x}, {top_left_y})")

        self.update()

        # Emit signals
        self.view_changed.emit()
        self.zoom_changed.emit(self.zoom_factor)

    def center_on_selection(self) -> None:
        """Center view on selected points."""
        if not self.selected_indices:
            return

        logger.debug(f"[CENTER] Centering on {len(self.selected_indices)} selected points")

        # Calculate center of selected points
        sum_x = sum_y = 0
        count = 0

        for idx in self.selected_indices:
            if 0 <= idx < len(self.curve_data):
                _, x, y, _ = safe_extract_point(self.curve_data[idx])
                sum_x += x
                sum_y += y
                count += 1

        if count > 0:
            center_x = sum_x / count
            center_y = sum_y / count
            logger.debug(f"[CENTER] Data center: ({center_x:.2f}, {center_y:.2f})")

            # Get screen position of center
            screen_pos = self.data_to_screen(center_x, center_y)
            widget_center = QPointF(self.width() / 2, self.height() / 2)
            logger.debug(f"[CENTER] Screen pos: ({screen_pos.x():.2f}, {screen_pos.y():.2f})")
            logger.debug(f"[CENTER] Widget center: ({widget_center.x():.2f}, {widget_center.y():.2f})")

            # Adjust pan
            offset = widget_center - screen_pos
            old_pan_x = self.pan_offset_x
            old_pan_y = self.pan_offset_y
            self.pan_offset_x += offset.x()
            # When Y-axis is flipped, invert the pan adjustment for Y
            # This ensures centering works consistently with panning behavior
            if self.flip_y_axis:
                self.pan_offset_y -= offset.y()
            else:
                self.pan_offset_y += offset.y()
            logger.debug(
                f"[CENTER] Pan offset changed from ({old_pan_x:.2f}, {old_pan_y:.2f}) to ({self.pan_offset_x:.2f}, {self.pan_offset_y:.2f})"
            )

            self.invalidate_caches()
            self.update()
            self.repaint()  # Force immediate repaint
            self.view_changed.emit()

    def center_on_frame(self, frame: int) -> None:
        """Center view on a specific frame.

        Args:
            frame: Frame number to center on (1-based)
        """
        # Find the point at the given frame
        frame_index = frame - 1  # Convert to 0-based index

        if 0 <= frame_index < len(self.curve_data):
            _, x, y, _ = safe_extract_point(self.curve_data[frame_index])
            logger.debug(f"[CENTER] Centering on frame {frame} at ({x:.2f}, {y:.2f})")

            # Get screen position of the point
            screen_pos = self.data_to_screen(x, y)
            widget_center = QPointF(self.width() / 2, self.height() / 2)

            # Adjust pan
            offset = widget_center - screen_pos
            self.pan_offset_x += offset.x()
            # When Y-axis is flipped, invert the pan adjustment for Y
            # This ensures centering works consistently with panning behavior
            if self.flip_y_axis:
                self.pan_offset_y -= offset.y()
            else:
                self.pan_offset_y += offset.y()

            logger.debug(f"[CENTER] View centered on frame {frame}")

            self.invalidate_caches()
            self.update()
            self.repaint()
            self.view_changed.emit()
        else:
            logger.warning(f"[CENTER] Frame {frame} is out of range (data has {len(self.curve_data)} points)")

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

    def _select_point(self, index: int, add_to_selection: bool = False) -> None:
        """
        Select a point.

        Args:
            index: Point index
            add_to_selection: Whether to add to existing selection
        """
        # Delegate to store - it will emit signals that trigger our updates
        self._curve_store.select(index, add_to_selection)

        # Emit our own signal for compatibility
        self.point_selected.emit(index)

        # Update interaction service if available
        if self.interaction_service and self.main_window:
            # Note: Protocol mismatch with InteractionService - using pyright: ignore for service integration
            self.interaction_service.on_point_selected(self, self.main_window, index)  # pyright: ignore[reportArgumentType]

    def _clear_selection(self) -> None:
        """Clear all selection."""
        self._curve_store.clear_selection()

    def select_all(self) -> None:
        """Select all points."""
        self._curve_store.select_all()

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
        for idx, screen_pos in self._screen_points_cache.items():
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
        """Add current state to history if main window available."""
        if self.main_window is not None:
            if getattr(self.main_window, "add_to_history", None) is not None:
                self.main_window.add_to_history()  # pyright: ignore[reportAttributeAccessIssue]

    def _update_status(self, message: str, timeout: int = 2000) -> None:
        """Update status bar if main window available.

        Args:
            message: Status message to display
            timeout: Timeout in milliseconds
        """
        if self.main_window is not None:
            if getattr(self.main_window, "status_bar", None) is not None:
                self.main_window.status_bar.showMessage(message, timeout)  # pyright: ignore[reportAttributeAccessIssue]

    def _get_current_frame(self) -> int | None:
        """Get current frame from main window if available.

        Returns:
            Current frame number or None if not available
        """
        if self.main_window is not None:
            if getattr(self.main_window, "current_frame", None) is not None:
                return self.main_window.current_frame  # pyright: ignore[reportAttributeAccessIssue]
        return None

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
            scale: float = params["scale"]

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
                if index in self._screen_points_cache:
                    self._screen_points_cache[index] = self.data_to_screen(new_x, new_y)

    def _nudge_selected(self, dx: float, dy: float) -> None:
        """
        Nudge selected points.

        Args:
            dx: X offset in data units
            dy: Y offset in data units
        """
        for idx in self.selected_indices:
            if 0 <= idx < len(self.curve_data):
                _, x, y, _ = safe_extract_point(self.curve_data[idx])
                self.update_point(idx, x + dx, y + dy)

        self._add_to_history()

    def _delete_selected_points(self) -> None:
        """Delete selected points."""
        # Sort indices in reverse to delete from end first
        indices = sorted(self.selected_indices, reverse=True)

        for idx in indices:
            self.remove_point(idx)

        # Selection is cleared automatically by the store when points are removed

        self._add_to_history()

    # Cache Management

    def invalidate_caches(self) -> None:
        """Invalidate all cached data."""
        self._transform_cache = None
        self._screen_points_cache.clear()
        self._visible_indices_cache.clear()
        self._update_region = None

    def _invalidate_point_region(self, index: int) -> None:
        """
        Invalidate region around a point.

        Args:
            index: Point index
        """
        if index in self._screen_points_cache:
            pos = self._screen_points_cache[index]

            # Create update region around point
            margin = self.point_radius + 10
            region = QRectF(pos.x() - margin, pos.y() - margin, margin * 2, margin * 2)

            if self._update_region:
                self._update_region = self._update_region.united(region)
            else:
                self._update_region = region

    def _update_screen_points_cache(self) -> None:
        """Update cached screen positions for all points."""
        if not self._screen_points_cache or not self._transform_cache:
            self._screen_points_cache.clear()

            for idx, point in enumerate(self.curve_data):
                _, x, y, _ = safe_extract_point(point)
                self._screen_points_cache[idx] = self.data_to_screen(x, y)

    def _update_visible_indices(self, rect: QRect) -> None:
        """
        Update cache of visible point indices.

        Args:
            rect: Visible rectangle
        """
        self._visible_indices_cache.clear()

        # Expand rect slightly for points on edges
        expanded = rect.adjusted(-self.point_radius, -self.point_radius, self.point_radius, self.point_radius)

        for idx, pos in self._screen_points_cache.items():
            if expanded.contains(pos.toPoint()):
                self._visible_indices_cache.add(idx)

    # Service Integration

    def set_main_window(self, main_window: MainWindow) -> None:
        """
        Set reference to main window.

        Args:
            main_window: Main window instance
        """
        self.main_window = main_window
        # Services are already initialized in __init__

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
        # When Y-flip is enabled (for pixel tracking), use widget dimensions for coordinate system
        # Otherwise use image dimensions for traditional image-based coordinates
        if self.flip_y_axis:
            display_width = self.width()
            display_height = self.height()
        else:
            display_width = self.image_width
            display_height = self.image_height

            if self.background_image:
                display_width = self.background_image.width()
                display_height = self.background_image.height()

        return ViewState(
            display_width=display_width,
            display_height=display_height,
            widget_width=self.width(),
            widget_height=self.height(),
            zoom_factor=self.zoom_factor,
            offset_x=self.pan_offset_x,
            offset_y=self.pan_offset_y,
            scale_to_image=self.scale_to_image,
            flip_y_axis=self.flip_y_axis,
            manual_x_offset=self.manual_offset_x,
            manual_y_offset=self.manual_offset_y,
            background_image=self.background_image,
            image_width=self.image_width,
            image_height=self.image_height,
        )

    def get_selected_indices(self) -> list[int]:
        """
        Get list of selected point indices.

        Returns:
            List of selected indices
        """
        return list(self.selected_indices)

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
