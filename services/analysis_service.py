#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AnalysisService: Service for curve data analysis and manipulation.
Provides methods for smoothing, filtering, filling gaps, and extrapolation.
"""

from typing import List, Tuple, Optional, Sequence, Any, Union
import math
import copy
from curve_data_operations import CurveDataOperations as LegacyCurveDataOps

class AnalysisService:
    """
    Service for curve data analysis and mathematical operations.

    This service provides methods for:
    1. Smoothing curves (moving average, Gaussian, Savitzky-Golay)
    2. Filtering data (median, Butterworth)
    3. Filling gaps in tracking data (linear, cubic spline, constant velocity)
    4. Extrapolating curves (forward and backward)
    5. Batch transformations (scale, offset, rotation)

    Phase 1 implementation forwards to LegacyCurveDataOps internally
    while providing a service-based interface.
    """

    @classmethod
    def smooth_curve(cls, curve_data: List[Tuple[int, float, float]], indices: List[int],
                     method: str = 'gaussian', window_size: int = 5, sigma: float = 1.0) -> List[Tuple[int, float, float]]:
        """
        Apply smoothing to the specified points in curve data.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]
            indices: List of indices to smooth
            method: Smoothing method ('moving_average', 'gaussian', 'savitzky_golay')
            window_size: Size of the smoothing window (odd number >= 3)
            sigma: Sigma value for Gaussian smoothing

        Returns:
            List[Tuple[int, float, float]]: Smoothed curve data
        """
        # Create a CurveDataOperations instance for processing
        ops = LegacyCurveDataOps(curve_data)

        # Apply appropriate smoothing method
        if method == 'moving_average':
            ops.smooth_moving_average(indices, window_size)
        elif method == 'gaussian':
            ops.smooth_gaussian(indices, window_size, sigma)
        elif method == 'savitzky_golay':
            ops.smooth_savitzky_golay(indices, window_size)
        else:
            return curve_data  # Return original if method not recognized

        # Return smoothed data
        return ops.get_data()

    @classmethod
    def filter_curve(cls, curve_data: List[Tuple[int, float, float]], indices: List[int],
                     method: str = 'median', window_size: int = 5, cutoff: float = 0.1,
                     order: int = 2) -> List[Tuple[int, float, float]]:
        """
        Apply filtering to the specified points in curve data.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]
            indices: List of indices to filter
            method: Filtering method ('median', 'butterworth')
            window_size: Size of the filtering window (for median filter)
            cutoff: Cutoff frequency for Butterworth filter (0.0-1.0)
            order: Order of the Butterworth filter

        Returns:
            List[Tuple[int, float, float]]: Filtered curve data
        """
        # Create a CurveDataOperations instance for processing
        ops = LegacyCurveDataOps(curve_data)

        # Apply appropriate filtering method
        if method == 'median':
            ops.filter_median(indices, window_size)
        elif method == 'butterworth':
            ops.filter_butterworth(indices, cutoff, order)
        else:
            return curve_data  # Return original if method not recognized

        # Return filtered data
        return ops.get_data()

    @classmethod
    def fill_gap(cls, curve_data: List[Tuple[int, float, float]], start_frame: int, end_frame: int,
                 method: str = 'linear', preserve_endpoints: bool = True, **kwargs) -> List[Tuple[int, float, float]]:
        """
        Fill a gap in curve data between start_frame and end_frame.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]
            start_frame: First frame of the gap
            end_frame: Last frame of the gap
            method: Filling method ('linear', 'cubic_spline', 'constant_velocity', 'accelerated_motion', 'average')
            preserve_endpoints: Whether to preserve existing points at endpoints
            **kwargs: Additional parameters for specific fill methods:
                - tension: Tension for cubic spline (float)
                - window_size: Number of points to use for velocity calculation
                - accel_weight: Weight of acceleration for accelerated motion

        Returns:
            List[Tuple[int, float, float]]: Curve data with filled gap
        """
        # Create a CurveDataOperations instance for processing
        ops = LegacyCurveDataOps(curve_data)

        # Apply appropriate fill method
        if method == 'linear':
            ops.fill_linear(start_frame, end_frame, preserve_endpoints)
        elif method == 'cubic_spline':
            tension = kwargs.get('tension', 0.5)
            ops.fill_cubic_spline(start_frame, end_frame, tension, preserve_endpoints)
        elif method == 'constant_velocity':
            window_size = kwargs.get('window_size', 3)
            ops.fill_constant_velocity(start_frame, end_frame, window_size, preserve_endpoints)
        elif method == 'accelerated_motion':
            window_size = kwargs.get('window_size', 3)
            accel_weight = kwargs.get('accel_weight', 0.5)
            ops.fill_accelerated_motion(start_frame, end_frame, window_size, accel_weight, preserve_endpoints)
        elif method == 'average':
            window_size = kwargs.get('window_size', 3)
            ops.fill_average(start_frame, end_frame, window_size, preserve_endpoints)
        else:
            return curve_data  # Return original if method not recognized

        # Return data with filled gap
        return ops.get_data()

    @classmethod
    def extrapolate_curve(cls, curve_data: List[Tuple[int, float, float]], num_frames: int,
                          direction: str = 'forward', method: int = 0,
                          fit_points: int = 5) -> List[Tuple[int, float, float]]:
        """
        Extrapolate curve data forward or backward by num_frames.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]
            num_frames: Number of frames to extrapolate
            direction: Direction to extrapolate ('forward' or 'backward')
            method: Extrapolation method (0=linear, 1=velocity, 2=quadratic)
            fit_points: Number of points to use for extrapolation calculation

        Returns:
            List[Tuple[int, float, float]]: Extrapolated curve data
        """
        # Create a CurveDataOperations instance for processing
        ops = LegacyCurveDataOps(curve_data)

        # Apply extrapolation in appropriate direction
        if direction == 'forward':
            ops.extrapolate_forward(num_frames, method, fit_points)
        elif direction == 'backward':
            ops.extrapolate_backward(num_frames, method, fit_points)
        else:
            return curve_data  # Return original if direction not recognized

        # Return extrapolated data
        return ops.get_data()

    # Phase 2: Add transform methods for batch operations (will be implemented later)
    # @classmethod
    # def transform_points(cls, curve_data, indices, transform_type, **kwargs)

    # ---- Helper methods for direct access to legacy functionality ----

    @classmethod
    def create_processor(cls, curve_data: List[Tuple[int, float, float]]) -> LegacyCurveDataOps:
        """
        Create a CurveDataOperations processor instance.
        This is a convenience method for direct access to legacy operations.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]

        Returns:
            CurveDataOperations: A processor instance to perform operations
        """
        return LegacyCurveDataOps(curve_data)
