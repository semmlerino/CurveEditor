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

    # ---- Batch transformation methods ----
    @classmethod
    def transform_points(cls, curve_data: List[Tuple[int, float, float]],
                         indices: List[int],
                         transform_type: str,
                         **kwargs) -> List[Tuple[int, float, float]]:
        """
        Apply batch transformations to specified points in curve data.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]
            indices: List of indices to transform
            transform_type: Type of transformation ('scale', 'offset', 'rotate')
            **kwargs: Additional parameters specific to each transform:
                - scale: scale_x, scale_y, center_x, center_y
                - offset: offset_x, offset_y
                - rotate: angle_degrees, center_x, center_y

        Returns:
            List[Tuple[int, float, float]]: Transformed curve data
        """
        if not curve_data or not indices:
            return copy.deepcopy(curve_data)

        if transform_type == 'scale':
            return cls.scale_points(curve_data, indices,
                                    kwargs.get('scale_x', 1.0),
                                    kwargs.get('scale_y', 1.0),
                                    kwargs.get('center_x', None),
                                    kwargs.get('center_y', None))
        elif transform_type == 'offset':
            return cls.offset_points(curve_data, indices,
                                     kwargs.get('offset_x', 0.0),
                                     kwargs.get('offset_y', 0.0))
        elif transform_type == 'rotate':
            return cls.rotate_points(curve_data, indices,
                                     kwargs.get('angle_degrees', 0.0),
                                     kwargs.get('center_x', None),
                                     kwargs.get('center_y', None))
        else:
            return copy.deepcopy(curve_data)  # Return original if method not recognized

    @classmethod
    def scale_points(cls, curve_data: List[Tuple[int, float, float]],
                     indices: List[int],
                     scale_x: float,
                     scale_y: float,
                     center_x: Optional[float] = None,
                     center_y: Optional[float] = None) -> List[Tuple[int, float, float]]:
        """
        Scale multiple points around a center point.

        Args:
            curve_data: List of (frame, x, y) tuples
            indices: List of indices to scale
            scale_x: Scale factor for X coordinates
            scale_y: Scale factor for Y coordinates
            center_x: X coordinate of scaling center (None for centroid)
            center_y: Y coordinate of scaling center (None for centroid)

        Returns:
            Modified copy of curve_data
        """
        # Create a copy of the curve data
        result = copy.deepcopy(curve_data)

        # If no center provided, use centroid of selected points
        if center_x is None or center_y is None:
            sum_x = 0
            sum_y = 0
            count = 0

            for idx in indices:
                if 0 <= idx < len(curve_data):
                    _, x, y = curve_data[idx]
                    sum_x += x
                    sum_y += y
                    count += 1

            if count > 0:
                center_x = sum_x / count if center_x is None else center_x
                center_y = sum_y / count if center_y is None else center_y
            else:
                # No valid points to scale
                return result

        # Apply scaling to selected points
        for idx in indices:
            if 0 <= idx < len(curve_data):
                frame, x, y = curve_data[idx]

                # Calculate new coordinates
                new_x = center_x + (x - center_x) * scale_x
                new_y = center_y + (y - center_y) * scale_y

                # Update point
                result[idx] = (frame, new_x, new_y)

        return result

    @classmethod
    def offset_points(cls, curve_data: List[Tuple[int, float, float]],
                      indices: List[int],
                      offset_x: float,
                      offset_y: float) -> List[Tuple[int, float, float]]:
        """
        Offset multiple points by a fixed amount.

        Args:
            curve_data: List of (frame, x, y) tuples
            indices: List of indices to offset
            offset_x: Amount to offset X coordinates
            offset_y: Amount to offset Y coordinates

        Returns:
            Modified copy of curve_data
        """
        # Create a copy of the curve data
        result = copy.deepcopy(curve_data)

        # Apply offset to selected points
        for idx in indices:
            if 0 <= idx < len(curve_data):
                frame, x, y = curve_data[idx]

                # Calculate new coordinates
                new_x = x + offset_x
                new_y = y + offset_y

                # Update point
                result[idx] = (frame, new_x, new_y)

        return result

    @classmethod
    def rotate_points(cls, curve_data: List[Tuple[int, float, float]],
                      indices: List[int],
                      angle_degrees: float,
                      center_x: Optional[float] = None,
                      center_y: Optional[float] = None) -> List[Tuple[int, float, float]]:
        """
        Rotate multiple points around a center point.

        Args:
            curve_data: List of (frame, x, y) tuples
            indices: List of indices to rotate
            angle_degrees: Rotation angle in degrees
            center_x: X coordinate of rotation center (None for centroid)
            center_y: Y coordinate of rotation center (None for centroid)

        Returns:
            Modified copy of curve_data
        """
        # Create a copy of the curve data
        result = copy.deepcopy(curve_data)

        # Convert angle to radians
        angle_rad = math.radians(angle_degrees)

        # If no center provided, use centroid of selected points
        if center_x is None or center_y is None:
            sum_x = 0
            sum_y = 0
            count = 0

            for idx in indices:
                if 0 <= idx < len(curve_data):
                    _, x, y = curve_data[idx]
                    sum_x += x
                    sum_y += y
                    count += 1

            if count > 0:
                center_x = sum_x / count if center_x is None else center_x
                center_y = sum_y / count if center_y is None else center_y
            else:
                # No valid points to rotate
                return result

        # Apply rotation to selected points
        for idx in indices:
            if 0 <= idx < len(curve_data):
                frame, x, y = curve_data[idx]

                # Translate point to origin
                dx = x - center_x
                dy = y - center_y

                # Rotate point
                new_x = center_x + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
                new_y = center_y + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)

                # Update point
                result[idx] = (frame, new_x, new_y)

        return result

    @classmethod
    def normalize_velocity(cls, curve_data: List[Tuple[int, float, float]],
                          indices: List[int],
                          target_velocity: Optional[float] = None) -> List[Tuple[int, float, float]]:
        """
        Normalize the velocity of selected points to be more consistent.

        Args:
            curve_data: List of (frame, x, y) tuples
            indices: List of indices to normalize
            target_velocity: Target velocity in pixels/frame (None for average)

        Returns:
            Modified copy of curve_data
        """
        # Create a copy of the curve data
        result = copy.deepcopy(curve_data)

        # Need at least 2 points to calculate velocity
        if len(indices) < 2:
            return result

        # Sort indices
        sorted_indices = sorted(indices)

        # If we're not modifying consecutive points, return
        if sorted_indices[-1] - sorted_indices[0] + 1 != len(sorted_indices):
            return result

        # Calculate velocities between points
        velocities = []
        for i in range(1, len(sorted_indices)):
            prev_idx = sorted_indices[i-1]
            curr_idx = sorted_indices[i]

            prev_frame, prev_x, prev_y = curve_data[prev_idx]
            curr_frame, curr_x, curr_y = curve_data[curr_idx]

            frame_diff = curr_frame - prev_frame
            if frame_diff > 0:
                dx = curr_x - prev_x
                dy = curr_y - prev_y
                distance = math.sqrt(dx*dx + dy*dy)
                velocity = distance / frame_diff
                velocities.append(velocity)

        if not velocities:
            return result

        # Calculate average velocity if no target provided
        if target_velocity is None:
            target_velocity = sum(velocities) / len(velocities)

        # Adjust points to normalize velocity
        # First point stays fixed, others are adjusted
        first_idx = sorted_indices[0]
        fixed_frame, fixed_x, fixed_y = curve_data[first_idx]

        for i in range(1, len(sorted_indices)):
            curr_idx = sorted_indices[i]
            curr_frame, curr_x, curr_y = curve_data[curr_idx]

            # Get previous adjusted point
            prev_idx = sorted_indices[i-1]
            _, prev_x, prev_y = result[prev_idx]

            # Calculate frame difference
            frame_diff = curr_frame - curve_data[prev_idx][0]

            # Calculate direction vector
            orig_dx = curr_x - curve_data[prev_idx][1]
            orig_dy = curr_y - curve_data[prev_idx][2]
            orig_dist = math.sqrt(orig_dx*orig_dx + orig_dy*orig_dy)

            # Skip if points are at the same location
            if orig_dist < 0.0001:
                continue

            # Normalize direction vector
            dir_x = orig_dx / orig_dist
            dir_y = orig_dy / orig_dist

            # Calculate new position
            new_dist = target_velocity * frame_diff
            new_x = prev_x + dir_x * new_dist
            new_y = prev_y + dir_y * new_dist

            # Update point
            result[curr_idx] = (curr_frame, new_x, new_y)

        return result

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
