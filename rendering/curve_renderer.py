#!/usr/bin/env python
"""Consolidated rendering system for curve editor."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont

class CurveRenderer:
    """Main renderer that handles all curve visualization."""
    
    def __init__(self):
        """Initialize renderer."""
        self.background_opacity = 1.0
        
    def render(self, painter: QPainter, curve_view):
        """Render complete curve view."""
        # Save painter state
        painter.save()
        
        # Render background if available
        if curve_view.show_background and curve_view.background_image:
            self.render_background(painter, curve_view)
            
        # Render grid
        if curve_view.show_grid:
            self.render_grid(painter, curve_view)
            
        # Render curve points
        if curve_view.points:
            self.render_points(painter, curve_view)
            
        # Render info overlay
        self.render_info(painter, curve_view)
        
        # Restore painter state
        painter.restore()
        
    def render_background(self, painter: QPainter, curve_view):
        """Render background image."""
        if not curve_view.background_image:
            return
            
        painter.setOpacity(curve_view.background_opacity)
        painter.drawPixmap(0, 0, curve_view.width(), curve_view.height(), 
                          curve_view.background_image)
        painter.setOpacity(1.0)
        
    def render_grid(self, painter: QPainter, curve_view):
        """Render grid lines."""
        pen = QPen(QColor(100, 100, 100, 50))
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Vertical lines
        step = 50
        for x in range(0, curve_view.width(), step):
            painter.drawLine(x, 0, x, curve_view.height())
            
        # Horizontal lines
        for y in range(0, curve_view.height(), step):
            painter.drawLine(0, y, curve_view.width(), y)
            
    def render_points(self, painter: QPainter, curve_view):
        """Render curve points and lines."""
        if not curve_view.points:
            return
            
        # Draw lines between points
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        
        for i in range(len(curve_view.points) - 1):
            p1 = self.data_to_screen(curve_view.points[i], curve_view)
            p2 = self.data_to_screen(curve_view.points[i + 1], curve_view)
            painter.drawLine(p1, p2)
            
        # Draw points
        for i, point in enumerate(curve_view.points):
            screen_pos = self.data_to_screen(point, curve_view)
            
            # Determine point color
            if i in curve_view.selected_points:
                color = QColor(255, 255, 0)  # Yellow for selected
            else:
                color = QColor(255, 0, 0)  # Red for normal
                
            # Draw point
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.NoPen))
            painter.drawEllipse(screen_pos, 5, 5)
            
            # Draw frame number if enabled
            if curve_view.show_all_frame_numbers:
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(screen_pos.x() + 10, screen_pos.y() - 10, 
                               f"F{point[0]}")
                               
    def render_info(self, painter: QPainter, curve_view):
        """Render information overlay."""
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 10))
        
        info_text = f"Points: {len(curve_view.points)}"
        if curve_view.selected_points:
            info_text += f" | Selected: {len(curve_view.selected_points)}"
        info_text += f" | Zoom: {curve_view.zoom_factor:.1f}x"
        
        painter.drawText(10, 20, info_text)
        
    def data_to_screen(self, point: tuple, curve_view) -> QPointF:
        """Convert data coordinates to screen coordinates."""
        # Simple transformation
        x = point[1] * curve_view.zoom_factor + curve_view.offset_x
        y = point[2] * curve_view.zoom_factor + curve_view.offset_y
        
        if curve_view.flip_y_axis:
            y = curve_view.height() - y
            
        return QPointF(x, y)
        
    def screen_to_data(self, pos: QPointF, curve_view) -> tuple[float, float]:
        """Convert screen coordinates to data coordinates."""
        x = (pos.x() - curve_view.offset_x) / curve_view.zoom_factor
        y = pos.y()
        
        if curve_view.flip_y_axis:
            y = curve_view.height() - y
            
        y = (y - curve_view.offset_y) / curve_view.zoom_factor
        
        return (x, y)