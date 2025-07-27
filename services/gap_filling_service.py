#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gap filling service for curve data.

This service handles various gap interpolation methods including:
- Linear interpolation
- Spline interpolation
- Constant velocity filling
- Accelerated motion filling
- Average-based filling

Extracted from AnalysisService to follow Single Responsibility Principle.
"""

import copy
from typing import Optional

from services.logging_service import LoggingService
from core.protocols.protocols import PointsList, GapFillingServiceProtocol

logger = LoggingService.get_logger("gap_filling_service")


class GapFillingService(GapFillingServiceProtocol):
    """Service for filling gaps in curve data."""
    
    @staticmethod
    def fill_gap_linear(data: PointsList, start_frame: int, end_frame: int) -> PointsList:
        """
        Fill a gap between start_frame and end_frame using linear interpolation.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            start_frame: Start frame of the gap (inclusive)
            end_frame: End frame of the gap (inclusive)
            
        Returns:
            Curve data with gap filled
        """
        if len(data) < 2 or start_frame >= end_frame:
            return data
            
        logger.info(f"Filling gap from frame {start_frame} to {end_frame} using linear interpolation")
        
        # Find the points before and after the gap
        start_point = None
        end_point = None
        
        for point in data:
            if point[0] == start_frame:
                start_point = point
            elif point[0] == end_frame:
                end_point = point
                
        # If we don't have both start and end points, can't interpolate
        if not start_point or not end_point:
            logger.warning("Cannot find start or end points for gap filling")
            return data
            
        # Create interpolated points
        new_points: PointsList = []
        frame_gap = end_frame - start_frame
        
        for frame in range(start_frame + 1, end_frame):
            # Calculate interpolation factor (0.0 to 1.0)
            t = (frame - start_frame) / frame_gap
            
            # Linearly interpolate x and y coordinates
            x = start_point[1] + (end_point[1] - start_point[1]) * t
            y = start_point[2] + (end_point[2] - start_point[2]) * t
            
            new_points.append((frame, x, y))
            
        # Add new points to data
        result = copy.deepcopy(data)
        result.extend(new_points)
        
        # Sort by frame number
        result.sort(key=lambda p: p[0])
        
        return result
    
    @staticmethod
    def fill_gap_spline(data: PointsList, start_frame: int, end_frame: int) -> PointsList:
        """
        Fill a gap between start_frame and end_frame using spline interpolation.
        Uses cubic spline if scipy is available, otherwise falls back to linear interpolation.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            start_frame: Start frame of the gap (inclusive)
            end_frame: End frame of the gap (inclusive)
            
        Returns:
            Curve data with gap filled
        """
        if len(data) < 2 or start_frame >= end_frame:
            return data
            
        try:
            # Try to import scipy for spline interpolation
            try:
                from scipy.interpolate import CubicSpline  # type: ignore[import-not-found]
            except ImportError:
                # Fall back to linear interpolation if scipy not available
                logger.warning("scipy not available, using linear interpolation instead")
                return GapFillingService.fill_gap_linear(data, start_frame, end_frame)
                
            # Find context points for better spline (include neighboring points)
            context_points: PointsList = []
            
            # Get points within a window around the gap for better spline fitting
            window_size = 2  # Points before and after the gap
            
            for point in data:
                frame = point[0]
                if frame >= start_frame - window_size and frame <= end_frame + window_size:
                    context_points.append(point)
                    
            # Need at least 3 points for cubic spline
            if len(context_points) < 3:
                # Fall back to linear interpolation
                return GapFillingService.fill_gap_linear(data, start_frame, end_frame)
                
            # Sort by frame number
            context_points.sort(key=lambda p: p[0])
            
            # Extract frames and coordinates for spline fitting
            frames = [p[0] for p in context_points]
            x_coords = [p[1] for p in context_points]
            y_coords = [p[2] for p in context_points]
            
            # Create splines
            spline_x = CubicSpline(frames, x_coords)
            spline_y = CubicSpline(frames, y_coords)
            
            # Generate new points for missing frames
            new_points: PointsList = []
            
            for frame in range(start_frame + 1, end_frame):
                # Use spline to calculate coordinates
                x = float(spline_x(frame))
                y = float(spline_y(frame))
                new_points.append((frame, x, y))
                
            # Add new points to data
            result = copy.deepcopy(data)
            result.extend(new_points)
            
            # Sort by frame number
            result.sort(key=lambda p: p[0])
            
            return result
            
        except ImportError:
            # Fall back to linear interpolation if scipy is not available
            logger.warning("SciPy not available, falling back to linear interpolation")
            return GapFillingService.fill_gap_linear(data, start_frame, end_frame)
    
    @staticmethod
    def fill_constant_velocity(data: PointsList, start_frame: int, end_frame: int) -> PointsList:
        """
        Fill a gap assuming constant velocity.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            start_frame: Start frame of the gap
            end_frame: End frame of the gap
            
        Returns:
            Curve data with gap filled
        """
        logger.info(f"Filling gap from frame {start_frame} to {end_frame} with constant velocity")
        # For constant velocity, linear interpolation is appropriate
        return GapFillingService.fill_gap_linear(data, start_frame, end_frame)
    
    @staticmethod
    def fill_accelerated_motion(data: PointsList, start_frame: int, end_frame: int) -> PointsList:
        """
        Fill a gap assuming accelerated motion.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            start_frame: Start frame of the gap
            end_frame: End frame of the gap
            
        Returns:
            Curve data with gap filled
        """
        logger.info(f"Filling gap from frame {start_frame} to {end_frame} with accelerated motion")
        # Use spline as it better approximates accelerated motion
        return GapFillingService.fill_gap_spline(data, start_frame, end_frame)
    
    @staticmethod
    def fill_average(data: PointsList, start_frame: int, end_frame: int, window_size: int) -> PointsList:
        """
        Fill a gap using average of surrounding points.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            start_frame: Start frame of the gap
            end_frame: End frame of the gap
            window_size: Window size for averaging
            
        Returns:
            Curve data with gap filled
        """
        logger.info(f"Filling gap from frame {start_frame} to {end_frame} using average with window_size={window_size}")
        # For now, use linear interpolation as approximation
        return GapFillingService.fill_gap_linear(data, start_frame, end_frame)