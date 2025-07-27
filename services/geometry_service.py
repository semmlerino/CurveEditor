#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Geometry service for curve data transformations.

This service handles geometric operations on curve data including:
- Rotation around a point
- Offsetting points by delta values
- Velocity normalization

Extracted from AnalysisService to follow Single Responsibility Principle.
"""

import copy
import math
from typing import Optional

from services.logging_service import LoggingService
from core.protocols.protocols import PointsList, GeometryServiceProtocol

logger = LoggingService.get_logger("geometry_service")


class GeometryService(GeometryServiceProtocol):
    """Service for geometric transformations on curve data."""
    
    @staticmethod
    def rotate_curve(
        data: PointsList, 
        angle_degrees: float, 
        center_x: Optional[float] = None, 
        center_y: Optional[float] = None
    ) -> PointsList:
        """
        Rotate curve data around a center point.

        Args:
            data: List of points in format [(frame, x, y), ...]
            angle_degrees: Rotation angle in degrees
            center_x: X coordinate of rotation center (None for centroid)
            center_y: Y coordinate of rotation center (None for centroid)

        Returns:
            Rotated curve data
        """
        if not data:
            return []
            
        # Create a copy of the curve data
        result = copy.deepcopy(data)
        
        # Convert angle to radians
        angle_rad = math.radians(angle_degrees)
        
        # If no center provided, use centroid of points
        if center_x is None or center_y is None:
            sum_x = 0.0
            sum_y = 0.0
            count = 0
            
            for point in data:
                sum_x += point[1]
                sum_y += point[2]
                count += 1
                
            if count > 0:
                center_x = sum_x / count
                center_y = sum_y / count
            else:
                return result
                
        logger.debug(f"Rotating {len(data)} points by {angle_degrees}° around ({center_x:.2f}, {center_y:.2f})")
        
        # Apply rotation transform to each point
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        
        for i, point in enumerate(data):
            frame = point[0]
            x = point[1]
            y = point[2]
            
            # Translate to origin (center point)
            tx = x - center_x
            ty = y - center_y
            
            # Apply rotation
            rx = tx * cos_angle - ty * sin_angle
            ry = tx * sin_angle + ty * cos_angle
            
            # Translate back
            new_x = rx + center_x
            new_y = ry + center_y
            
            # Preserve frame and status if present
            if len(point) > 3:
                result[i] = (frame, new_x, new_y, point[3])
            else:
                result[i] = (frame, new_x, new_y)
                
        return result
    
    @staticmethod
    def offset_points(data: PointsList, indices: list[int], dx: float, dy: float) -> PointsList:
        """
        Offset specified points by given delta values.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            indices: Indices of points to offset
            dx: X offset amount
            dy: Y offset amount
            
        Returns:
            Curve data with offset points
        """
        if not data or not indices:
            return data
            
        logger.info(f"Offsetting {len(indices)} points by dx={dx}, dy={dy}")
        
        # Create a copy of the data
        result = copy.deepcopy(data)
        
        # Apply offset to each specified point
        for idx in indices:
            if 0 <= idx < len(result):
                point = result[idx]
                # Create a new point with offset coordinates
                if len(point) > 3:
                    result[idx] = (point[0], point[1] + dx, point[2] + dy, point[3])
                else:
                    result[idx] = (point[0], point[1] + dx, point[2] + dy)
                    
        return result
    
    @staticmethod
    def normalize_velocity(data: PointsList, target_velocity: float) -> PointsList:
        """
        Normalize velocity between points to target value.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            target_velocity: Target velocity in pixels per frame
            
        Returns:
            Curve data with normalized velocity
        """
        if len(data) < 2 or target_velocity <= 0:
            return data
            
        logger.info(f"Normalizing velocity to {target_velocity} pixels/frame")
        
        # Keep first point fixed
        result = [copy.deepcopy(data[0])]
        
        # Adjust subsequent points
        for i in range(1, len(data)):
            prev = result[-1]
            curr = data[i]
            
            frame_diff = curr[0] - prev[0]
            if frame_diff <= 0:
                # Same frame, keep as is
                result.append(copy.deepcopy(curr))
                continue
                
            # Calculate current vector
            dx = curr[1] - prev[1]
            dy = curr[2] - prev[2]
            current_dist = math.sqrt(dx*dx + dy*dy)
            
            if current_dist == 0:
                # No movement, keep as is
                result.append(copy.deepcopy(curr))
                continue
                
            # Calculate target distance
            target_dist = target_velocity * frame_diff
            
            # Scale vector to target distance
            scale = target_dist / current_dist
            new_x = prev[1] + dx * scale
            new_y = prev[2] + dy * scale
            
            # Preserve frame and status
            if len(curr) > 3:
                result.append((curr[0], new_x, new_y, curr[3]))
            else:
                result.append((curr[0], new_x, new_y))
                
        return result