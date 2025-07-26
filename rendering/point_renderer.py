#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Point rendering component for CurveView.

This module contains the PointRenderer class responsible for rendering
curve points with proper transformation, selection highlighting, and labels.
"""

from typing import List, Set, Tuple, Union, TYPE_CHECKING

from PySide6.QtGui import QPainter, QColor, QPen

from ui_scaling import UIScaling
from services.logging_service import LoggingService
import ui_constants

if TYPE_CHECKING:
    from services.unified_transform import Transform
    from core.protocols import PointsList

logger = LoggingService.get_logger("point_renderer")


class PointRenderer:
    """
    Handles point rendering for CurveView.
    
    This class is responsible for rendering curve points with proper transformation,
    selection highlighting, interpolation status, and frame number labels.
    Maintains identical functionality to the original paintEvent point rendering logic.
    """
    
    def render_points(self, painter: QPainter, transform: 'Transform', 
                     curve_view: 'CurveViewProtocol') -> None:
        """
        Render all curve points with transformation and styling.
        
        Args:
            painter: QPainter instance for drawing
            transform: Transform object for coordinate mapping
            curve_view: CurveView instance providing context and data
        """
        if not curve_view.points:
            return
            
        # Transform all points first
        transformed_points = self._transform_points(curve_view.points, transform)
        
        if not transformed_points:
            return
            
        # Render each point with appropriate styling
        for item in transformed_points:
            i, frame, tx, ty, point, is_interpolated = item
            
            # Render point with appropriate color and style based on state
            if i in curve_view.selected_points:
                self._render_selected_point(painter, i, tx, ty, curve_view.selected_point_idx)
            elif is_interpolated:
                self._render_interpolated_point(painter, tx, ty)
            else:
                self._render_normal_point(painter, tx, ty)
                
            # Draw labels for selected points and every 10th point
            self._render_point_labels(painter, i, frame, tx, ty, point, curve_view.selected_points)
    
    def _transform_points(self, points: 'PointsList', transform: 'Transform') -> List[Tuple[int, int, float, float, Union[Tuple[int, float, float], Tuple[int, float, float, bool]], bool]]:
        """
        Transform all points from data coordinates to screen coordinates.
        
        Args:
            points: List of curve points
            transform: Transform object for coordinate mapping
            
        Returns:
            List of transformed points with metadata
        """
        transformed_points = []
        
        for i, point in enumerate(points):
            frame: int
            x: float
            y: float
            is_interpolated: bool = False
            
            if len(point) == 3:
                frame, x, y = point
            elif len(point) == 4:
                frame, x, y, is_interpolated = point  # type: ignore
            else:
                continue
                
            # Transform the point coordinates
            tx, ty = transform.apply(x, y)
            
            # Store transformed point with metadata
            # Use type ignore here since we know the runtime type compatibility is maintained
            # but the static type checker can't verify the complex union types
            transformed_points.append((i, frame, tx, ty, point, is_interpolated))  # type: ignore[arg-type]
            
        return transformed_points
    
    def _render_selected_point(self, painter: QPainter, point_index: int, 
                             tx: float, ty: float, selected_point_idx: int) -> None:
        """
        Render a selected point with selection highlighting.
        
        Args:
            painter: QPainter instance for drawing
            point_index: Index of the point
            tx, ty: Transformed screen coordinates
            selected_point_idx: Index of the primary selected point
        """
        selected_color = ui_constants.CURVE_COLORS["point_selected"]
        color = QColor(selected_color)
        painter.setPen(QPen(color, 6))
        painter.drawPoint(int(tx), int(ty))
        
        # Draw additional highlight for the primary selected point
        if point_index == selected_point_idx:
            painter.setPen(QPen(color.darker(120), 10))
            painter.drawPoint(int(tx), int(ty))
    
    def _render_interpolated_point(self, painter: QPainter, tx: float, ty: float) -> None:
        """
        Render an interpolated point with interpolation styling.
        
        Args:
            painter: QPainter instance for drawing
            tx, ty: Transformed screen coordinates
        """
        interpolated_color = ui_constants.CURVE_COLORS["point_interpolated"]
        color = QColor(interpolated_color)
        painter.setPen(QPen(color, 6))
        painter.drawPoint(int(tx), int(ty))
    
    def _render_normal_point(self, painter: QPainter, tx: float, ty: float) -> None:
        """
        Render a normal point with standard styling.
        
        Args:
            painter: QPainter instance for drawing
            tx, ty: Transformed screen coordinates
        """
        normal_color = ui_constants.CURVE_COLORS["point_normal"]
        color = QColor(normal_color)
        painter.setPen(QPen(color, 6))
        painter.drawPoint(int(tx), int(ty))
    
    def _render_point_labels(self, painter: QPainter, point_index: int, frame: int,
                           tx: float, ty: float, point: Union[Tuple[int, float, float], Tuple[int, float, float, bool]],
                           selected_points: Set[int]) -> None:
        """
        Render frame numbers and type information for points.
        
        Args:
            painter: QPainter instance for drawing
            point_index: Index of the point
            frame: Frame number of the point
            tx, ty: Transformed screen coordinates
            point: Original point data
            selected_points: Set of selected point indices
        """
        # Draw frame number or type/status for selected points
        if point_index in selected_points:
            info_font = UIScaling.get_font("tiny")
            painter.setFont(info_font)
            label_color = UIScaling.get_color('text_warning')
            painter.setPen(QPen(QColor(label_color), 1))
            
            # Determine point type
            point_type = 'normal'
            if len(point) >= 4:
                point_type = str(point[3])
                
            painter.drawText(int(tx) + 10, int(ty) - 10, f"{frame}, {point_type}")
        elif point_index % 10 == 0:
            # Draw frame number for every 10th point
            label_color = UIScaling.get_color('text_warning')
            painter.setPen(QPen(QColor(label_color), 1))
            font = UIScaling.get_font("tiny")
            painter.setFont(font)
            painter.drawText(int(tx) + 10, int(ty) - 10, str(frame))


# Protocol for type checking
try:
    from typing import Protocol
    
    class CurveViewProtocol(Protocol):
        points: 'PointsList'
        selected_points: Set[int]
        selected_point_idx: int
        
except ImportError:
    # Fallback for older Python versions
    CurveViewProtocol = object