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

import math
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import (
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QPolygonF,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import QRubberBand, QWidget

# Import core modules
from core.models import CurvePoint, PointCollection, PointStatus
from core.point_types import safe_extract_point
from core.signal_manager import SignalManager

# Import services
from services.curve_service import CurveService
from services.unified_transform import Transform
from services.view_state import ViewState

import logging

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger("curve_view_widget")


class CurveViewWidget(QWidget):
    """
    High-performance widget for curve visualization and editing.
    
    This widget provides a complete curve editing interface with optimized
    rendering, interaction handling, and service integration.
    
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
    point_selected = Signal(int)  # index
    point_moved = Signal(int, float, float)  # index, x, y
    selection_changed = Signal(list)  # list of indices
    view_changed = Signal()  # view transform changed
    zoom_changed = Signal(float)  # zoom level
    
    def __init__(self, parent: QWidget | None = None):
        """
        Initialize the CurveViewWidget.
        
        Args:
            parent: Parent widget (typically MainWindow)
        """
        super().__init__(parent)
        
        # Signal management for proper cleanup
        self.signal_manager = SignalManager(self)
        
        # Core data
        self.curve_data: list[tuple] = []
        self.point_collection: PointCollection | None = None
        self.selected_indices: set[int] = set()
        self.hover_index: int = -1
        
        # View transformation
        self.zoom_factor: float = 1.0
        self.pan_offset_x: float = 0.0
        self.pan_offset_y: float = 0.0
        self.manual_offset_x: float = 0.0
        self.manual_offset_y: float = 0.0
        self.flip_y_axis: bool = False
        self.scale_to_image: bool = True
        
        # Display settings
        self.show_grid: bool = True
        self.show_points: bool = True
        self.show_lines: bool = True
        self.show_labels: bool = False
        self.show_velocity_vectors: bool = False
        self.show_all_frame_numbers: bool = False
        self.show_background: bool = True
        self.background_opacity: float = 0.5
        
        # Grid settings
        self.grid_size: int = 50
        self.grid_color: QColor = QColor(100, 100, 100, 50)
        self.grid_line_width: int = 1
        
        # Point rendering settings
        self.point_radius: int = 5
        self.selected_point_radius: int = 7
        self.point_color: QColor = QColor(255, 100, 100)
        self.selected_point_color: QColor = QColor(255, 255, 0)
        self.interpolated_point_color: QColor = QColor(100, 150, 255)
        self.keyframe_point_color: QColor = QColor(0, 255, 0)
        
        # Line rendering settings
        self.line_color: QColor = QColor(200, 200, 200)
        self.line_width: int = 2
        self.selected_line_color: QColor = QColor(255, 255, 100)
        self.selected_line_width: int = 3
        
        # Background image
        self.background_image: QPixmap | None = None
        self.image_width: int = 1920
        self.image_height: int = 1080
        
        # Interaction state
        self.drag_active: bool = False
        self.pan_active: bool = False
        self.rubber_band_active: bool = False
        self.last_mouse_pos: QPointF | None = None
        self.drag_start_pos: QPointF | None = None
        self.dragged_index: int = -1
        
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
        self.curve_service: CurveService | None = None
        
        # Widget setup
        self._setup_widget()
        
        logger.info("CurveViewWidget initialized")
    
    def _setup_widget(self) -> None:
        """Configure widget properties and settings."""
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Set focus policy for keyboard events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
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
    
    def set_curve_data(self, data: list[tuple]) -> None:
        """
        Set the curve data to display.
        
        Args:
            data: List of point tuples (frame, x, y, [status])
        """
        self.curve_data = data
        self.point_collection = PointCollection.from_tuples(data) if data else None
        
        # Clear caches
        self._invalidate_caches()
        
        # Update display
        self.update()
        
        logger.debug(f"Set curve data with {len(data)} points")
    
    def add_point(self, point: tuple) -> None:
        """
        Add a single point to the curve.
        
        Args:
            point: Point tuple (frame, x, y, [status])
        """
        self.curve_data.append(point)
        
        # Update collection
        if self.point_collection:
            self.point_collection.points.append(CurvePoint.from_tuple(point))
        else:
            self.point_collection = PointCollection([CurvePoint.from_tuple(point)])
        
        # Invalidate only affected region
        self._invalidate_point_region(len(self.curve_data) - 1)
        
        self.update()
    
    def update_point(self, index: int, x: float, y: float) -> None:
        """
        Update coordinates of a point.
        
        Args:
            index: Point index
            x: New X coordinate
            y: New Y coordinate
        """
        if 0 <= index < len(self.curve_data):
            old_point = self.curve_data[index]
            frame, _, _, *rest = safe_extract_point(old_point)
            
            # Create updated point
            if rest:
                self.curve_data[index] = (frame, x, y, rest[0])
            else:
                self.curve_data[index] = (frame, x, y)
            
            # Update collection
            if self.point_collection and index < len(self.point_collection.points):
                old_cp = self.point_collection.points[index]
                self.point_collection.points[index] = old_cp.with_coordinates(x, y)
            
            # Invalidate affected region
            self._invalidate_point_region(index)
            
            # Emit signal
            self.point_moved.emit(index, x, y)
            
            self.update()
    
    def remove_point(self, index: int) -> None:
        """
        Remove a point from the curve.
        
        Args:
            index: Point index to remove
        """
        if 0 <= index < len(self.curve_data):
            # Remove from data
            del self.curve_data[index]
            
            # Remove from collection
            if self.point_collection:
                del self.point_collection.points[index]
            
            # Update selection
            if index in self.selected_indices:
                self.selected_indices.remove(index)
            
            # Adjust indices for points after removed one
            self.selected_indices = {
                i - 1 if i > index else i for i in self.selected_indices
            }
            
            self._invalidate_caches()
            self.update()
    
    # Coordinate Transformation
    
    def get_transform(self) -> Transform:
        """
        Get the current transformation object.
        
        Returns:
            Transform object for coordinate mapping
        """
        if self._transform_cache is None:
            self._update_transform()
        return self._transform_cache
    
    def _update_transform(self) -> None:
        """Update the cached transformation object."""
        # Calculate display dimensions
        display_width = self.image_width
        display_height = self.image_height
        
        if self.background_image:
            display_width = self.background_image.width()
            display_height = self.background_image.height()
        
        # Calculate centering offsets
        widget_width = self.width()
        widget_height = self.height()
        
        # Base scale to fit content in widget
        scale_x = widget_width / display_width if display_width > 0 else 1.0
        scale_y = widget_height / display_height if display_height > 0 else 1.0
        base_scale = min(scale_x, scale_y) * 0.9  # 90% to leave margin
        
        # Apply zoom on top of base scale
        total_scale = base_scale * self.zoom_factor
        
        # Calculate center offsets
        scaled_width = display_width * total_scale
        scaled_height = display_height * total_scale
        center_x = (widget_width - scaled_width) / 2
        center_y = (widget_height - scaled_height) / 2
        
        # Image scale factors for data-to-image mapping
        image_scale_x = display_width / self.image_width
        image_scale_y = display_height / self.image_height
        
        # Create transform
        self._transform_cache = Transform(
            scale=total_scale,
            center_offset_x=center_x,
            center_offset_y=center_y,
            pan_offset_x=self.pan_offset_x,
            pan_offset_y=self.pan_offset_y,
            manual_offset_x=self.manual_offset_x,
            manual_offset_y=self.manual_offset_y,
            flip_y=self.flip_y_axis,
            display_height=display_height,
            image_scale_x=image_scale_x,
            image_scale_y=image_scale_y,
            scale_to_image=self.scale_to_image,
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
        screen_x, screen_y = transform.apply(x, y)
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
        return transform.apply_inverse(pos.x(), pos.y())
    
    # Painting
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the widget content.
        
        Args:
            event: Paint event with exposed region
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get exposed rectangle for optimization
        exposed_rect = event.rect()
        
        # Clear background
        painter.fillRect(exposed_rect, QColor(30, 30, 30))
        
        # Draw components in order
        if self.show_background and self.background_image:
            self._paint_background(painter, exposed_rect)
        
        if self.show_grid:
            self._paint_grid(painter, exposed_rect)
        
        if self.curve_data:
            if self.show_lines:
                self._paint_lines(painter, exposed_rect)
            
            if self.show_velocity_vectors:
                self._paint_velocity_vectors(painter, exposed_rect)
            
            if self.show_points:
                self._paint_points(painter, exposed_rect)
            
            if self.show_labels or self.show_all_frame_numbers:
                self._paint_labels(painter, exposed_rect)
        
        # Draw overlay information
        self._paint_info_overlay(painter)
        
        # Draw hover indicator
        if self.hover_index >= 0:
            self._paint_hover_indicator(painter)
    
    def _paint_background(self, painter: QPainter, rect: QRect) -> None:
        """Paint background image if available."""
        if not self.background_image:
            return
        
        painter.save()
        painter.setOpacity(self.background_opacity)
        
        # Get image position from transform
        transform = self.get_transform()
        img_x, img_y = transform.apply_for_image_position()
        
        # Calculate scaled dimensions
        scale = transform.get_parameters()["scale"]
        scaled_width = int(self.background_image.width() * scale)
        scaled_height = int(self.background_image.height() * scale)
        
        # Draw scaled image
        target_rect = QRect(int(img_x), int(img_y), scaled_width, scaled_height)
        
        # Only draw if intersects with exposed area
        if target_rect.intersects(rect):
            painter.drawPixmap(target_rect, self.background_image)
        
        painter.restore()
    
    def _paint_grid(self, painter: QPainter, rect: QRect) -> None:
        """Paint grid overlay."""
        painter.save()
        
        pen = QPen(self.grid_color)
        pen.setWidth(self.grid_line_width)
        painter.setPen(pen)
        
        # Calculate grid spacing based on zoom
        base_spacing = self.grid_size
        zoom = self.zoom_factor
        
        # Adaptive grid spacing
        if zoom < 0.5:
            spacing = base_spacing * 4
        elif zoom < 1.0:
            spacing = base_spacing * 2
        elif zoom > 2.0:
            spacing = base_spacing / 2
        else:
            spacing = base_spacing
        
        # Draw vertical lines
        left = rect.left()
        right = rect.right()
        top = rect.top()
        bottom = rect.bottom()
        
        x = left - (left % spacing)
        while x <= right:
            painter.drawLine(int(x), top, int(x), bottom)
            x += spacing
        
        # Draw horizontal lines
        y = top - (top % spacing)
        while y <= bottom:
            painter.drawLine(left, int(y), right, int(y))
            y += spacing
        
        painter.restore()
    
    def _paint_lines(self, painter: QPainter, rect: QRect) -> None:
        """Paint lines connecting curve points."""
        if len(self.curve_data) < 2:
            return
        
        painter.save()
        
        # Update screen points cache if needed
        self._update_screen_points_cache()
        
        # Set pen for lines
        pen = QPen(self.line_color)
        pen.setWidth(self.line_width)
        painter.setPen(pen)
        
        # Draw lines between consecutive points
        for i in range(len(self.curve_data) - 1):
            if i in self._screen_points_cache and i + 1 in self._screen_points_cache:
                p1 = self._screen_points_cache[i]
                p2 = self._screen_points_cache[i + 1]
                
                # Check if line intersects visible area (simple bounding box check)
                line_rect = QRectF(p1, p2).normalized()
                if line_rect.intersects(QRectF(rect)):
                    # Use different style for selected segments
                    if i in self.selected_indices or i + 1 in self.selected_indices:
                        pen.setColor(self.selected_line_color)
                        pen.setWidth(self.selected_line_width)
                        painter.setPen(pen)
                        painter.drawLine(p1, p2)
                        # Reset pen
                        pen.setColor(self.line_color)
                        pen.setWidth(self.line_width)
                        painter.setPen(pen)
                    else:
                        painter.drawLine(p1, p2)
        
        painter.restore()
    
    def _paint_points(self, painter: QPainter, rect: QRect) -> None:
        """Paint curve points."""
        if not self.curve_data:
            return
        
        painter.save()
        
        # Update caches
        self._update_screen_points_cache()
        self._update_visible_indices(rect)
        
        # Draw points
        for idx in self._visible_indices_cache:
            if idx in self._screen_points_cache:
                pos = self._screen_points_cache[idx]
                
                # Determine point style based on status and selection
                if idx in self.selected_indices:
                    color = self.selected_point_color
                    radius = self.selected_point_radius
                else:
                    # Get point status
                    point_data = self.curve_data[idx]
                    _, _, _, status = safe_extract_point(point_data)
                    
                    if status == "interpolated":
                        color = self.interpolated_point_color
                    elif status == "keyframe":
                        color = self.keyframe_point_color
                    else:
                        color = self.point_color
                    radius = self.point_radius
                
                # Draw point
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.PenStyle.NoPen))
                painter.drawEllipse(pos, radius, radius)
                
                # Draw outline for selected points
                if idx in self.selected_indices:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.setPen(QPen(QColor(255, 255, 255), 2))
                    painter.drawEllipse(pos, radius + 2, radius + 2)
        
        painter.restore()
    
    def _paint_velocity_vectors(self, painter: QPainter, rect: QRect) -> None:
        """Paint velocity vectors between points."""
        if len(self.curve_data) < 2:
            return
        
        painter.save()
        
        pen = QPen(QColor(100, 200, 255, 150))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Update screen cache
        self._update_screen_points_cache()
        
        for i in range(len(self.curve_data) - 1):
            if i in self._screen_points_cache and i + 1 in self._screen_points_cache:
                p1 = self._screen_points_cache[i]
                p2 = self._screen_points_cache[i + 1]
                
                # Calculate velocity vector
                dx = p2.x() - p1.x()
                dy = p2.y() - p1.y()
                
                # Normalize and scale
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0:
                    scale = min(30, length * 0.3)
                    dx = (dx / length) * scale
                    dy = (dy / length) * scale
                    
                    # Draw arrow from point
                    end = QPointF(p1.x() + dx, p1.y() + dy)
                    painter.drawLine(p1, end)
                    
                    # Draw arrowhead
                    angle = math.atan2(dy, dx)
                    arrow_length = 8
                    arrow_angle = 0.5
                    
                    left_x = end.x() - arrow_length * math.cos(angle - arrow_angle)
                    left_y = end.y() - arrow_length * math.sin(angle - arrow_angle)
                    right_x = end.x() - arrow_length * math.cos(angle + arrow_angle)
                    right_y = end.y() - arrow_length * math.sin(angle + arrow_angle)
                    
                    painter.drawLine(end, QPointF(left_x, left_y))
                    painter.drawLine(end, QPointF(right_x, right_y))
        
        painter.restore()
    
    def _paint_labels(self, painter: QPainter, rect: QRect) -> None:
        """Paint point labels and frame numbers."""
        if not self.curve_data:
            return
        
        painter.save()
        
        font = QFont("Arial", 9)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        metrics = QFontMetrics(font)
        
        # Update caches
        self._update_screen_points_cache()
        self._update_visible_indices(rect)
        
        for idx in self._visible_indices_cache:
            if idx in self._screen_points_cache:
                pos = self._screen_points_cache[idx]
                point_data = self.curve_data[idx]
                frame, x, y, _ = safe_extract_point(point_data)
                
                # Build label text
                if self.show_all_frame_numbers or idx in self.selected_indices:
                    label = f"F{frame}"
                    
                    if self.show_labels and idx in self.selected_indices:
                        label += f"\n({x:.1f}, {y:.1f})"
                    
                    # Draw text with background for readability
                    text_rect = metrics.boundingRect(label)
                    text_pos = QPoint(int(pos.x() + 10), int(pos.y() - 10))
                    
                    # Draw background
                    painter.fillRect(
                        text_pos.x() - 2,
                        text_pos.y() - text_rect.height(),
                        text_rect.width() + 4,
                        text_rect.height() + 4,
                        QColor(0, 0, 0, 180)
                    )
                    
                    # Draw text
                    painter.drawText(text_pos, label)
        
        painter.restore()
    
    def _paint_info_overlay(self, painter: QPainter) -> None:
        """Paint information overlay in corner."""
        painter.save()
        
        # Setup text
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        # Build info text
        info_lines = []
        
        if self.curve_data:
            info_lines.append(f"Points: {len(self.curve_data)}")
        
        if self.selected_indices:
            info_lines.append(f"Selected: {len(self.selected_indices)}")
        
        info_lines.append(f"Zoom: {self.zoom_factor:.1f}x")
        
        if self.hover_index >= 0 and self.hover_index < len(self.curve_data):
            point = self.curve_data[self.hover_index]
            frame, x, y, _ = safe_extract_point(point)
            info_lines.append(f"Hover: F{frame} ({x:.1f}, {y:.1f})")
        
        # Draw background box
        metrics = QFontMetrics(font)
        max_width = max(metrics.horizontalAdvance(line) for line in info_lines) if info_lines else 0
        total_height = len(info_lines) * (metrics.height() + 2)
        
        painter.fillRect(10, 10, max_width + 20, total_height + 10, QColor(0, 0, 0, 180))
        
        # Draw text
        y = 25
        for line in info_lines:
            painter.drawText(20, y, line)
            y += metrics.height() + 2
        
        painter.restore()
    
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
    
    # Mouse Events
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events.
        
        Args:
            event: Mouse event
        """
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
                    self._select_point(idx, modifiers & Qt.KeyboardModifier.ControlModifier)
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
            # Context menu will be handled by main window
            pass
        
        self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse move events.
        
        Args:
            event: Mouse event
        """
        pos = event.position()
        
        # Update hover
        old_hover = self.hover_index
        self.hover_index = self._find_point_at(pos)
        if self.hover_index != old_hover:
            self.update()
        
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
            self.pan_offset_y += delta.y()
            self.last_mouse_pos = pos
            self._invalidate_caches()
            self.update()
            self.view_changed.emit()
    
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
                if self.main_window and hasattr(self.main_window, "add_to_history"):
                    self.main_window.add_to_history()
        
        elif button == Qt.MouseButton.MiddleButton:
            self.pan_active = False
            self.last_mouse_pos = None
            self.unsetCursor()
        
        self.update()
    
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
            self._invalidate_caches()
            new_screen_pos = self.data_to_screen(data_x, data_y)
            
            offset = pos - new_screen_pos
            self.pan_offset_x += offset.x()
            self.pan_offset_y += offset.y()
            
            # Invalidate caches again after pan adjustment
            self._invalidate_caches()
            
            self.update()
            self.zoom_changed.emit(self.zoom_factor)
            self.view_changed.emit()
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handle keyboard events.
        
        Args:
            event: Key event
        """
        key = event.key()
        modifiers = event.modifiers()
        
        # Delete selected points
        if key == Qt.Key.Key_Delete and self.selected_indices:
            self._delete_selected_points()
        
        # Select all
        elif key == Qt.Key.Key_A and modifiers & Qt.KeyboardModifier.ControlModifier:
            self._select_all()
        
        # Deselect all
        elif key == Qt.Key.Key_Escape:
            self._clear_selection()
        
        # Nudge selected points
        elif self.selected_indices:
            nudge_amount = 1.0
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                nudge_amount = 10.0
            elif modifiers & Qt.KeyboardModifier.ControlModifier:
                nudge_amount = 0.1
            
            if key == Qt.Key.Key_Left:
                self._nudge_selected(-nudge_amount, 0)
            elif key == Qt.Key.Key_Right:
                self._nudge_selected(nudge_amount, 0)
            elif key == Qt.Key.Key_Up:
                self._nudge_selected(0, -nudge_amount)
            elif key == Qt.Key.Key_Down:
                self._nudge_selected(0, nudge_amount)
        
        self.update()
    
    # View Operations
    
    def reset_view(self) -> None:
        """Reset view to default state."""
        self.zoom_factor = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.manual_offset_x = 0.0
        self.manual_offset_y = 0.0
        
        self._invalidate_caches()
        self.update()
        self.view_changed.emit()
        self.zoom_changed.emit(self.zoom_factor)
    
    def fit_to_view(self) -> None:
        """Fit all points in view."""
        if not self.curve_data:
            return
        
        # Get bounds of all points
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
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
            
            self._invalidate_caches()
            
            # Calculate center position
            screen_center = self.data_to_screen(center_x, center_y)
            widget_center = QPointF(self.width() / 2, self.height() / 2)
            
            # Adjust pan to center
            offset = widget_center - screen_center
            self.pan_offset_x = offset.x()
            self.pan_offset_y = offset.y()
            
            self._invalidate_caches()
            self.update()
            self.view_changed.emit()
            self.zoom_changed.emit(self.zoom_factor)
    
    def center_on_selection(self) -> None:
        """Center view on selected points."""
        if not self.selected_indices:
            return
        
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
            
            # Get screen position of center
            screen_pos = self.data_to_screen(center_x, center_y)
            widget_center = QPointF(self.width() / 2, self.height() / 2)
            
            # Adjust pan
            offset = widget_center - screen_pos
            self.pan_offset_x += offset.x()
            self.pan_offset_y += offset.y()
            
            self._invalidate_caches()
            self.update()
            self.view_changed.emit()
    
    # Selection Operations
    
    def _find_point_at(self, pos: QPointF) -> int:
        """
        Find point at given screen position.
        
        Args:
            pos: Screen position
            
        Returns:
            Point index or -1 if not found
        """
        # Update screen cache
        self._update_screen_points_cache()
        
        # Search radius
        threshold = self.point_radius + 3
        threshold_sq = threshold * threshold
        
        # Find closest point within threshold
        closest_idx = -1
        closest_dist_sq = threshold_sq
        
        for idx, screen_pos in self._screen_points_cache.items():
            dx = pos.x() - screen_pos.x()
            dy = pos.y() - screen_pos.y()
            dist_sq = dx * dx + dy * dy
            
            if dist_sq < closest_dist_sq:
                closest_dist_sq = dist_sq
                closest_idx = idx
        
        return closest_idx
    
    def _select_point(self, index: int, add_to_selection: bool = False) -> None:
        """
        Select a point.
        
        Args:
            index: Point index
            add_to_selection: Whether to add to existing selection
        """
        if not add_to_selection:
            self.selected_indices.clear()
        
        self.selected_indices.add(index)
        
        # Emit signals
        self.point_selected.emit(index)
        self.selection_changed.emit(list(self.selected_indices))
        
        # Update curve service if available
        if self.curve_service and self.main_window:
            self.curve_service.on_point_selected(self, self.main_window, index)
    
    def _clear_selection(self) -> None:
        """Clear all selection."""
        self.selected_indices.clear()
        self.selection_changed.emit([])
    
    def _select_all(self) -> None:
        """Select all points."""
        self.selected_indices = set(range(len(self.curve_data)))
        self.selection_changed.emit(list(self.selected_indices))
    
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
        self.selected_indices.clear()
        
        # Update screen cache
        self._update_screen_points_cache()
        
        # Check each point
        for idx, screen_pos in self._screen_points_cache.items():
            if rect.contains(screen_pos.toPoint()):
                self.selected_indices.add(idx)
    
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
            scale = transform.get_parameters()["scale"]
            
            if scale > 0:
                dx = delta.x() / scale
                dy = delta.y() / scale
                
                # Get current position
                _, x, y, _ = safe_extract_point(self.curve_data[index])
                
                # Update position
                new_x = x + dx
                new_y = y + dy
                
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
        
        if self.main_window and hasattr(self.main_window, "add_to_history"):
            self.main_window.add_to_history()
    
    def _delete_selected_points(self) -> None:
        """Delete selected points."""
        # Sort indices in reverse to delete from end first
        indices = sorted(self.selected_indices, reverse=True)
        
        for idx in indices:
            self.remove_point(idx)
        
        self.selected_indices.clear()
        self.selection_changed.emit([])
        
        if self.main_window and hasattr(self.main_window, "add_to_history"):
            self.main_window.add_to_history()
    
    # Cache Management
    
    def _invalidate_caches(self) -> None:
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
            region = QRectF(
                pos.x() - margin,
                pos.y() - margin,
                margin * 2,
                margin * 2
            )
            
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
        expanded = rect.adjusted(-self.point_radius, -self.point_radius,
                                self.point_radius, self.point_radius)
        
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
        self.curve_service = CurveService()
    
    def set_background_image(self, pixmap: QPixmap | None) -> None:
        """
        Set background image.
        
        Args:
            pixmap: Background image pixmap or None
        """
        self.background_image = pixmap
        self._invalidate_caches()
        self.update()
    
    def get_view_state(self) -> ViewState:
        """
        Get current view state.
        
        Returns:
            ViewState object with current parameters
        """
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


# Example usage and testing
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout
    
    app = QApplication(sys.argv)
    
    # Create main window
    main_window = QMainWindow()
    main_window.setWindowTitle("CurveViewWidget Test")
    main_window.resize(1200, 800)
    
    # Create curve widget
    curve_widget = CurveViewWidget()
    
    # Set some test data
    test_data = [
        (0, 100, 100),
        (10, 200, 150, "keyframe"),
        (20, 300, 200),
        (30, 400, 180, "interpolated"),
        (40, 500, 220),
        (50, 600, 250, "keyframe"),
    ]
    curve_widget.set_curve_data(test_data)
    
    # Enable features
    curve_widget.show_grid = True
    curve_widget.show_labels = True
    curve_widget.show_all_frame_numbers = True
    
    # Set as central widget
    main_window.setCentralWidget(curve_widget)
    
    # Connect signals for testing
    curve_widget.point_selected.connect(lambda idx: print(f"Selected point {idx}"))
    curve_widget.point_moved.connect(lambda idx, x, y: print(f"Moved point {idx} to ({x:.1f}, {y:.1f})"))
    curve_widget.zoom_changed.connect(lambda z: print(f"Zoom: {z:.1f}x"))
    
    main_window.show()
    sys.exit(app.exec())