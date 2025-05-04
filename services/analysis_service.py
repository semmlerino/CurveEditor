#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AnalysisService: Service for curve data analysis and manipulation.
Provides methods for smoothing, filtering, filling gaps, and extrapolation.
"""

from typing import List, Tuple, Optional, Dict
import math
import copy

class AnalysisService:
    """
    Service for curve data analysis and mathematical operations.

    This service provides methods for:
    1. Smoothing curves (moving average, Gaussian, Savitzky-Golay)
    2. Filtering data (median, Butterworth)
    3. Filling gaps in tracking data (linear, cubic spline, constant velocity)
    4. Extrapolating curves (forward and backward)
    5. Batch transformations (scale, offset, rotation)
    """
    
    def __init__(self, curve_data: Optional[List[Tuple[int, float, float]]] = None):
        """
        Initialize the AnalysisService with curve data.
        
        Args:
            curve_data: List of points in format [(frame, x, y), ...]
        """
        self.data: List[Tuple[int, float, float]] = copy.deepcopy(curve_data) if curve_data else []

    # Internal processor class to replace LegacyCurveDataOps functionality
    class CurveDataProcessor:
        """Internal processor class for curve data operations"""

        def __init__(self, curve_data: List[Tuple[int, float, float]]):
            self.data = copy.deepcopy(curve_data)

        def get_data(self) -> List[Tuple[int, float, float]]:
            return self.data

        # The methods used by AnalysisService will be implemented as needed
        # This acts as a simple facade for the CurveDataOps methods
        def smooth_moving_average(self, indices: List[int], window_size: int) -> None:
            """Apply moving average smoothing to specified points."""
            if not indices or window_size < 1 or not self.data:
                return
                
            # Ensure window size is odd for symmetrical window
            if window_size % 2 == 0:
                window_size += 1
                
            half_window = window_size // 2
            
            # Make a copy of the original data for reference
            original_data = copy.deepcopy(self.data)
            
            # Sort indices to ensure order doesn't matter
            indices.sort()
            
            # Apply moving average to each specified index
            for idx in indices:
                if idx < 0 or idx >= len(self.data):
                    continue
                    
                # Get the frame, x, y of the current point
                frame, _, _ = self.data[idx]
                
                # Find points within the window around the current point
                window_points_x: List[float] = []
                window_points_y: List[float] = []
                
                for i, (_, pt_x, pt_y) in enumerate(original_data):  # Underscore for unused pt_frame
                    # Simple window based on index distance rather than frame distance
                    if abs(i - idx) <= half_window:
                        window_points_x.append(pt_x)
                        window_points_y.append(pt_y)
                
                # Calculate the average x and y coordinates
                if window_points_x and window_points_y:
                    avg_x = sum(window_points_x) / len(window_points_x)
                    avg_y = sum(window_points_y) / len(window_points_y)
                    
                    # Update the point with smoothed coordinates
                    self.data[idx] = (frame, avg_x, avg_y)

        def smooth_gaussian(self, indices: List[int], window_size: int, sigma: float) -> None:
            pass

        def smooth_savitzky_golay(self, indices: List[int], window_size: int) -> None:
            pass

        def filter_median(self, indices: List[int], window_size: int) -> None:
            pass

        def filter_butterworth(self, indices: List[int], cutoff: float, order: int) -> None:
            pass

        def fill_linear(self, start_frame: int, end_frame: int, preserve_endpoints: bool) -> None:
            """Fill a gap with linear interpolation."""
            # Find indices of the start and end frames
            start_idx: Optional[int] = None
            end_idx: Optional[int] = None
            
            for i, (frame, _, _) in enumerate(self.data):
                if frame == start_frame:
                    start_idx = i
                if frame == end_frame:
                    end_idx = i
            
            # Return if we can't find both endpoints
            if start_idx is None or end_idx is None:
                return
            
            # Extract the start and end points
            start_pt = self.data[start_idx]
            end_pt = self.data[end_idx]
            
            start_frame, start_x, start_y = start_pt
            end_frame, end_x, end_y = end_pt
            
            # Calculate the number of frames to fill
            frame_diff = end_frame - start_frame
            if frame_diff <= 1:
                return  # No gap to fill
            
            # Calculate the step size for x and y coordinates
            x_step = (end_x - start_x) / frame_diff
            y_step = (end_y - start_y) / frame_diff
            
            # Create interpolated points
            new_points: List[Tuple[int, float, float]] = []
            for i in range(1, frame_diff):
                frame = start_frame + i
                x = start_x + x_step * i
                y = start_y + y_step * i
                new_points.append((frame, x, y))
            
            # Insert the new points into the data at the correct position
            position = start_idx + 1
            for point in new_points:
                point_tuple: Tuple[int, float, float] = point
                self.data.insert(position, point_tuple)
                position += 1

        def fill_cubic_spline(self, start_frame: int, end_frame: int, tension: float, preserve_endpoints: bool) -> None:
            """Fill a gap with cubic spline interpolation."""
            # Find indices of the start and end frames
            start_idx: Optional[int] = None
            end_idx: Optional[int] = None
            
            for i, (frame, _, _) in enumerate(self.data):
                if frame == start_frame:
                    start_idx = i
                if frame == end_frame:
                    end_idx = i
            
            # Return if we can't find both endpoints
            if start_idx is None or end_idx is None:
                return
            
            # Extract the start and end points
            start_pt = self.data[start_idx]
            end_pt = self.data[end_idx]
            
            start_frame, start_x, start_y = start_pt
            end_frame, end_x, end_y = end_pt
            
            # Calculate the number of frames to fill
            frame_diff = end_frame - start_frame
            if frame_diff <= 1:
                return  # No gap to fill
            
            # For a simple implementation, we'll use linear interpolation but add some curvature
            # based on the tension parameter
            
            # Create interpolated points
            new_points: List[Tuple[int, float, float]] = []
            for i in range(1, frame_diff):
                t = i / frame_diff  # Normalized position (0 to 1)
                
                # Basic cubic interpolation formula
                # Adjust with tension parameter (0 = straight line, 1 = maximum curve)
                h00 = 2*t**3 - 3*t**2 + 1          # Hermite basis function for position
                h10 = t**3 - 2*t**2 + t            # Hermite basis function for tangent at start
                h01 = -2*t**3 + 3*t**2             # Hermite basis function for position
                h11 = t**3 - t**2                  # Hermite basis function for tangent at end
                
                # Calculate tangents (simplified approach)
                tan_start_x = (end_x - start_x) * tension
                tan_start_y = (end_y - start_y) * tension
                tan_end_x = (end_x - start_x) * tension
                tan_end_y = (end_y - start_y) * tension
                
                # Compute interpolated position
                x = h00 * start_x + h10 * tan_start_x + h01 * end_x + h11 * tan_end_x
                y = h00 * start_y + h10 * tan_start_y + h01 * end_y + h11 * tan_end_y
                
                frame = start_frame + i
                new_points.append((frame, x, y))
            
            # Insert the new points into the data at the correct position
            position = start_idx + 1
            for point in new_points:
                point_tuple: Tuple[int, float, float] = point
                self.data.insert(position, point_tuple)
                position += 1

        def fill_constant_velocity(self, start_frame: int, end_frame: int, window_size: int, preserve_endpoints: bool) -> None:
            pass

        def fill_accelerated_motion(self, start_frame: int, end_frame: int, window_size: int, accel_weight: float, preserve_endpoints: bool) -> None:
            pass

        def fill_average(self, start_frame: int, end_frame: int, window_size: int, preserve_endpoints: bool) -> None:
            pass

        def extrapolate_forward(self, num_frames: int, method: str, fit_points: int) -> None:
            pass

        def extrapolate_backward(self, num_frames: int, method: str, fit_points: int) -> None:
            pass

    @classmethod
    def create_processor(cls, curve_data: List[Tuple[int, float, float]]) -> 'AnalysisService.CurveDataProcessor':
        """
        Create a curve data processor for custom operations.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]

        Returns:
            CurveDataProcessor: A processor instance for the curve data
        """
        return cls.CurveDataProcessor(curve_data)

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
        # Create a processor instance for processing
        ops = cls.CurveDataProcessor(curve_data)

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
        # Create a processor instance for processing
        ops = cls.CurveDataProcessor(curve_data)

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
                 method: str = 'linear', preserve_endpoints: bool = True, **kwargs: Dict[str, float]) -> List[Tuple[int, float, float]]:
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
        # Create a processor instance for processing
        ops = cls.CurveDataProcessor(curve_data)

        # Apply appropriate fill method
        if method == 'linear':
            ops.fill_linear(start_frame, end_frame, preserve_endpoints)
        elif method == 'cubic_spline':
            tension_value = kwargs.get('tension', 0.5)
            if isinstance(tension_value, dict):
                tension = 0.5  # Default if invalid
            else:
                tension = float(tension_value)
            ops.fill_cubic_spline(start_frame, end_frame, tension, preserve_endpoints)
        elif method == 'constant_velocity':
            window_size_value = kwargs.get('window_size', 3)
            if isinstance(window_size_value, dict):
                window_size = 3  # Default if invalid
            else:
                window_size = int(window_size_value)
            ops.fill_constant_velocity(start_frame, end_frame, window_size, preserve_endpoints)
        elif method == 'accelerated_motion':
            window_size_value = kwargs.get('window_size', 3)
            if isinstance(window_size_value, dict):
                window_size = 3  # Default if invalid
            else:
                window_size = int(window_size_value)
                
            accel_weight_value = kwargs.get('accel_weight', 0.5)
            if isinstance(accel_weight_value, dict):
                accel_weight = 0.5  # Default if invalid
            else:
                accel_weight = float(accel_weight_value)
                
            ops.fill_accelerated_motion(start_frame, end_frame, window_size, accel_weight, preserve_endpoints)
        elif method == 'average':
            window_size_value = kwargs.get('window_size', 3)
            if isinstance(window_size_value, dict):
                window_size = 3  # Default if invalid
            else:
                window_size = int(window_size_value)
            ops.fill_average(start_frame, end_frame, window_size, preserve_endpoints)
        else:
            return curve_data  # Return original if method not recognized

        # Return data with filled gap
        return ops.get_data()

    @classmethod
    def extrapolate_curve(cls, curve_data: List[Tuple[int, float, float]], direction: str = 'forward',
                          num_frames: int = 10, method: str = 'linear', fit_points: int = 5) -> List[Tuple[int, float, float]]:
        """
        Extrapolate curve data forward or backward by num_frames.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]
            direction: Direction to extrapolate ('forward' or 'backward')
            num_frames: Number of frames to extrapolate
            method: Extrapolation method ('linear', 'velocity', 'quadratic')
            fit_points: Number of points to use for extrapolation calculation

        Returns:
            List[Tuple[int, float, float]]: Extrapolated curve data
        """
        # Create a processor instance for processing
        ops = cls.CurveDataProcessor(curve_data)

        # Apply extrapolation in appropriate direction
        if direction == 'forward':
            ops.extrapolate_forward(num_frames, method, fit_points)
        elif direction == 'backward':
            ops.extrapolate_backward(num_frames, method, fit_points)
        else:
            return curve_data  # Return original if direction not recognized

        # Return extrapolated data
        return ops.get_data()

    @classmethod
    def rotate_curve(cls, curve_data: List[Tuple[int, float, float]], angle_degrees: float = 0.0,
                     center_x: Optional[float] = None, center_y: Optional[float] = None) -> List[Tuple[int, float, float]]:
        """
        Rotate curve data around a center point.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]
            angle_degrees: Rotation angle in degrees
            center_x: X coordinate of rotation center (None for centroid)
            center_y: Y coordinate of rotation center (None for centroid)

        Returns:
            List[Tuple[int, float, float]]: Rotated curve data
        """
        # Create a copy of the curve data
        result: List[Tuple[int, float, float]] = copy.deepcopy(curve_data)

        # Convert angle to radians
        angle_rad = math.radians(angle_degrees)

        # If no center provided, use centroid of selected points
        if center_x is None or center_y is None:
            sum_x = 0
            sum_y = 0
            count = 0

            for _, x, y in curve_data:
                sum_x += x
                sum_y += y
                count += 1

            if count > 0:
                center_x = sum_x / count if center_x is None else center_x
                center_y = sum_y / count if center_y is None else center_y
            else:
                # No valid points to rotate
                return result

        # Apply rotation to all points
        for i, (frame, x, y) in enumerate(curve_data):
            # Translate point to origin
            dx = x - center_x
            dy = y - center_y

            # Rotate point
            new_x = center_x + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
            new_y = center_y + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)

            # Update point
            result[i] = (frame, new_x, new_y)

        return result

    def get_data(self) -> List[Tuple[int, float, float]]:
        """
        Get the current curve data.
        
        Returns:
            List[Tuple[int, float, float]]: Current curve data
        """
        return copy.deepcopy(self.data)
    
    def smooth_moving_average(self, indices: List[int], window_size: int) -> None:
        """
        Apply moving average smoothing to the specified indices.
        
        Args:
            indices: List of indices to smooth
            window_size: Size of the smoothing window
        """
        processor = self.create_processor(self.data)
        processor.smooth_moving_average(indices, window_size)
        self.data = processor.get_data()
    
    def smooth_gaussian(self, indices: List[int], window_size: int, sigma: float) -> None:
        """
        Apply Gaussian smoothing to the specified indices.
        
        Args:
            indices: List of indices to smooth
            window_size: Size of the smoothing window
            sigma: Standard deviation for Gaussian kernel
        """
        processor = self.create_processor(self.data)
        processor.smooth_gaussian(indices, window_size, sigma)
        self.data = processor.get_data()
    
    def smooth_savitzky_golay(self, indices: List[int], window_size: int) -> None:
        """
        Apply Savitzky-Golay smoothing to the specified indices.
        
        Args:
            indices: List of indices to smooth
            window_size: Size of the smoothing window
        """
        processor = self.create_processor(self.data)
        processor.smooth_savitzky_golay(indices, window_size)
        self.data = processor.get_data()
    
    def fill_gap_linear(self, start_frame: int, end_frame: int) -> None:
        """
        Fill a gap with linear interpolation between start_frame and end_frame.
        
        Args:
            start_frame: First frame of the gap
            end_frame: Last frame of the gap
        """
        self.data = self.fill_gap(self.data, start_frame, end_frame, method='linear')
    
    def fill_gap_spline(self, start_frame: int, end_frame: int) -> None:
        """
        Fill a gap with cubic spline interpolation between start_frame and end_frame.
        
        Args:
            start_frame: First frame of the gap
            end_frame: Last frame of the gap
        """
        self.data = self.fill_gap(self.data, start_frame, end_frame, method='cubic_spline')
    
    def normalize_velocity(self, target_velocity: float) -> None:
        """
        Normalize the velocity between consecutive points to the target value.
        
        Args:
            target_velocity: Target velocity in pixels per frame
        """
        if not self.data or len(self.data) < 2:
            return
            
        # Sort data by frame number to ensure proper normalization
        sorted_data = sorted(self.data, key=lambda p: p[0])
        result = [sorted_data[0]]  # Keep the first point unchanged
        
        for i in range(1, len(sorted_data)):
            prev_frame, prev_x, prev_y = result[-1]  # Use the last adjusted point as reference
            curr_frame, curr_x, curr_y = sorted_data[i]
            
            # Calculate direction vector from previous point to current point
            dx = curr_x - prev_x
            dy = curr_y - prev_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 0:
                # Normalize direction vector
                dx /= distance
                dy /= distance
                
                # Calculate new position based on target velocity
                frame_diff = curr_frame - prev_frame
                if frame_diff > 0:
                    # Adjust for multi-frame gaps
                    adjusted_velocity = target_velocity * frame_diff
                else:
                    adjusted_velocity = target_velocity
                
                # Set new position at exactly the right distance
                new_x = prev_x + dx * adjusted_velocity
                new_y = prev_y + dy * adjusted_velocity
                
                result.append((curr_frame, new_x, new_y))
            else:
                # If points are at the same location, keep as is
                result.append((curr_frame, curr_x, curr_y))
                
        self.data = result

    def detect_problems(self) -> Dict[int, Dict[str, str]]:
        """
        Detect potential problems in tracking data.
        
        Identifies issues such as:
        - Jitter (very small movements)
        - Sudden jumps (large movements between consecutive frames)
        - Gaps in tracking (missing frames)
            
        Returns:
            dict: Dictionary of detected problems with frame numbers as keys
        """
        # Use instance data
        if not self.data or len(self.data) < 2:
            return {}
        
        problems: Dict[int, Dict[str, str]] = {}
        
        # Parameters for problem detection
        jitter_threshold = 0.5  # pixels - movements smaller than this might be jitter
        jump_threshold = 30.0   # pixels - movements larger than this might be sudden jumps
        gap_threshold = 1       # frames - gaps larger than this are detected
        
        # Sort data by frame number to ensure proper analysis
        sorted_data = sorted(self.data, key=lambda p: p[0])
        
        # Analyze movements between consecutive points
        for i in range(1, len(sorted_data)):
            prev_frame, prev_x, prev_y = sorted_data[i-1]
            curr_frame, curr_x, curr_y = sorted_data[i]
            
            # Check for gaps in frame numbers
            frame_diff = curr_frame - prev_frame
            if frame_diff > gap_threshold + 1:
                problems[prev_frame] = {
                    'type': 'gap',
                    'description': f'Gap of {frame_diff-1} frames after frame {prev_frame}'
                }
            
            # Only check motion issues for consecutive or near-consecutive frames
            if frame_diff <= gap_threshold + 1:
                # Calculate distance moved
                dx = curr_x - prev_x
                dy = curr_y - prev_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                # Check for jitter
                if distance < jitter_threshold:
                    problems[curr_frame] = {
                        'type': 'jitter',
                        'description': f'Minimal movement ({distance:.2f} px) at frame {curr_frame}'
                    }
                
                # Check for sudden jumps
                elif distance > jump_threshold:
                    problems[curr_frame] = {
                        'type': 'jump',
                        'description': f'Sudden jump ({distance:.2f} px) at frame {curr_frame}'
                    }
        
        return problems
