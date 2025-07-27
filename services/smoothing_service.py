#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Smoothing service for curve data.

This service handles various smoothing operations on curve data including:
- Moving average smoothing
- Gaussian smoothing
- Spline smoothing

Extracted from AnalysisService to follow Single Responsibility Principle.
"""

import copy
from typing import Optional

from services.logging_service import LoggingService
from core.protocols.protocols import PointsList, SmoothingServiceProtocol

logger = LoggingService.get_logger("smoothing_service")


class SmoothingService(SmoothingServiceProtocol):
    """Service for smoothing curve data."""
    
    @staticmethod
    def smooth_moving_average(data: PointsList, indices: list[int], window_size: int) -> PointsList:
        """
        Apply moving average smoothing to specified points.
        
        This implementation applies a proper moving average filter where each point
        is smoothed based on its neighboring points within the window, not all selected points.
        This prevents the curve from shifting and only smooths local noise.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            indices: List of indices to smooth
            window_size: Size of the smoothing window (will be made odd if even)
            
        Returns:
            Smoothed curve data
        """
        logger.info(f"Starting smooth_moving_average with {len(indices)} indices and window_size={window_size}")
        
        if not data or not indices:
            logger.warning(f"Smoothing skipped: data={bool(data)}, indices={bool(indices)}")
            return data
            
        # Ensure window size is odd
        if window_size % 2 == 0:
            window_size += 1
            
        # Sort indices to maintain data structure
        sorted_indices = sorted([idx for idx in indices if 0 <= idx < len(data)])
        if not sorted_indices:
            logger.warning("No valid indices to smooth")
            return data
            
        logger.info(f"Valid indices: first={sorted_indices[0]}, last={sorted_indices[-1]}, count={len(sorted_indices)}")
        
        # Create a copy of the data for results
        result = copy.deepcopy(data)
        
        # Calculate half window for easier indexing
        half_window = window_size // 2
        
        # Apply moving average to each selected point
        for idx in sorted_indices:
            if idx >= len(data):
                continue
                
            point = data[idx]
            frame_num = point[0]
            
            # Collect neighboring points within the window
            window_x_values: list[float] = []
            window_y_values: list[float] = []
            
            # Collect values in the window
            for window_idx in range(max(0, idx - half_window), min(len(data), idx + half_window + 1)):
                window_x_values.append(data[window_idx][1])
                window_y_values.append(data[window_idx][2])
                
            # Calculate average values
            avg_x = sum(window_x_values) / len(window_x_values) if window_x_values else 0.0
            avg_y = sum(window_y_values) / len(window_y_values) if window_y_values else 0.0
            
            # Apply smoothing with a blend factor to preserve some original character
            blend_factor = min(0.8, window_size / 20.0)
            new_x = point[1] * (1 - blend_factor) + avg_x * blend_factor
            new_y = point[2] * (1 - blend_factor) + avg_y * blend_factor
            
            # Preserve status if available
            if len(point) > 3:
                result[idx] = (frame_num, new_x, new_y, point[3])
            else:
                result[idx] = (frame_num, new_x, new_y)
                
        # Log sample results
        sample_indices = sorted_indices[:2] + [sorted_indices[-1]] if len(sorted_indices) > 2 else sorted_indices
        for idx in sample_indices:
            if idx < len(data) and idx < len(result):
                before = data[idx]
                after = result[idx]
                logger.info(f"Point {idx}: ({before[1]:.2f}, {before[2]:.2f}) -> ({after[1]:.2f}, {after[2]:.2f})")
                
        logger.info(f"Smoothing complete, updated {len(sorted_indices)} points")
        return result
    
    @staticmethod
    def smooth_gaussian(data: PointsList, indices: list[int], window_size: int, sigma: float) -> PointsList:
        """
        Apply Gaussian smoothing to specified points.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            indices: List of indices to smooth
            window_size: Size of the smoothing window
            sigma: Standard deviation for Gaussian kernel
            
        Returns:
            Smoothed curve data
        """
        logger.info(f"Applying Gaussian smoothing with window_size={window_size}, sigma={sigma} to {len(indices)} points")
        
        # For now, use moving average as a fallback
        # In a real implementation, this would calculate Gaussian weights
        return SmoothingService.smooth_moving_average(data, indices, window_size)
    
    @staticmethod
    def apply_spline(data: PointsList, control_indices: list[int]) -> PointsList:
        """
        Apply spline interpolation using control points.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            control_indices: Indices of control points for the spline
            
        Returns:
            Curve data with spline interpolation applied
        """
        if len(control_indices) < 2:
            return data
            
        try:
            # Try to import scipy
            try:
                from scipy.interpolate import CubicSpline  # type: ignore[import-not-found]
            except ImportError:
                logger.warning("scipy not available, using linear interpolation instead")
                return SmoothingService._linear_interpolate(data, control_indices)
                
            # Extract control points
            control_points = [data[i] for i in control_indices if i < len(data)]
            if len(control_points) < 2:
                return data
                
            # Sort control points by frame
            control_points.sort(key=lambda p: p[0])
            
            # Extract frames and coordinates
            frames = [p[0] for p in control_points]
            x_coords = [p[1] for p in control_points]
            y_coords = [p[2] for p in control_points]
            
            # Create splines
            spline_x = CubicSpline(frames, x_coords)
            spline_y = CubicSpline(frames, y_coords)
            
            # Apply spline to all points between first and last control point
            result = copy.deepcopy(data)
            min_frame = frames[0]
            max_frame = frames[-1]
            
            for i, point in enumerate(data):
                frame = point[0]
                if min_frame <= frame <= max_frame:
                    new_x = float(spline_x(frame))
                    new_y = float(spline_y(frame))
                    # Preserve status if present
                    if len(point) > 3:
                        result[i] = (frame, new_x, new_y, point[3])
                    else:
                        result[i] = (frame, new_x, new_y)
                        
            return result
            
        except ImportError:
            # Fall back to linear interpolation
            logger.warning("SciPy not available, using linear interpolation")
            return SmoothingService._linear_interpolate(data, control_indices)
    
    @staticmethod
    def _linear_interpolate(data: PointsList, control_indices: list[int]) -> PointsList:
        """
        Simple linear interpolation fallback.
        
        Args:
            data: Curve data
            control_indices: Indices of control points
            
        Returns:
            Linearly interpolated curve data
        """
        # Extract and sort control points
        control_points = [data[i] for i in control_indices if i < len(data)]
        control_points.sort(key=lambda p: p[0])
        
        if len(control_points) < 2:
            return data
            
        result = copy.deepcopy(data)
        
        # For each segment between control points
        for i in range(len(control_points) - 1):
            p1 = control_points[i]
            p2 = control_points[i + 1]
            
            # Find all points in this segment
            for j, point in enumerate(data):
                frame = point[0]
                if p1[0] < frame < p2[0]:
                    # Interpolate
                    t = (frame - p1[0]) / (p2[0] - p1[0])
                    new_x = p1[1] * (1 - t) + p2[1] * t
                    new_y = p1[2] * (1 - t) + p2[2] * t
                    
                    # Preserve status if present
                    if len(point) > 3:
                        result[j] = (frame, new_x, new_y, point[3])
                    else:
                        result[j] = (frame, new_x, new_y)
                        
        return result