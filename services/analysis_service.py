from typing import List, Tuple, Optional, Dict, TypeVar, Protocol, Any
import copy
import math

from services.logging_service import LoggingService

# Configure logger for this module
logger = LoggingService.get_logger("analysis_service")

# Track if scipy is available
has_scipy = False

# Define CubicSpline type and implementation
CubicSplineType = Any  # This avoids issues with complex type annotations


class CurveProcessor(Protocol):
    """Protocol defining the interface for curve processors"""

    def get_data(self) -> List[Tuple[int, float, float]]:
        """Get the processed curve data"""
        ...

    def smooth_moving_average(self, indices: List[int], window_size: int) -> None:
        """Apply moving average smoothing"""
        ...

    def smooth_gaussian(self, indices: List[int], window_size: int, sigma: float) -> None:
        """Apply Gaussian smoothing"""
        ...

    def smooth_savitzky_golay(self, indices: List[int], window_size: int) -> None:
        """Apply Savitzky-Golay smoothing"""
        ...


T = TypeVar('T', bound=CurveProcessor)


class ConcreteCurveProcessor:
    """Concrete implementation of CurveProcessor"""

    def __init__(self, data: List[Tuple[int, float, float]]) -> None:
        """Initialize with curve data"""
        self.data = copy.deepcopy(data)

    def get_data(self) -> List[Tuple[int, float, float]]:
        """Get the processed curve data"""
        return self.data

    def smooth_moving_average(self, indices: List[int], window_size: int) -> None:
        """Apply moving average smoothing to y-values only, preserving x-values

        Note: This implementation only smooths the y-coordinate values, keeping the x-coordinates
        unchanged. This maintains the horizontal position of points while smoothing the vertical
        component of the curve.

        For curves with interdependent x and y values (parametric curves),
        both coordinates should ideally be smoothed together.
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Starting smooth_moving_average with {len(indices)} indices and window_size={window_size}")
        if not self.data or not indices or window_size < 2:
            logger.warning(f"Smoothing skipped: data={bool(self.data)}, indices={bool(indices)}, window={window_size}")
            return

        # Log some sample points before smoothing
        if len(self.data) > 0 and len(indices) > 0:
            # Log a few sample points
            sample_indices = [indices[0]]
            if len(indices) > 1:
                sample_indices.append(indices[len(indices)//2])
            if len(indices) > 2:
                sample_indices.append(indices[-1])

            for sample_idx in sample_indices:
                if 0 <= sample_idx < len(self.data):
                    before_point = self.data[sample_idx]
                    logger.info(f"BEFORE - Sample point at idx={sample_idx}: frame={before_point[0]}, x={before_point[1]}, y={before_point[2]}")

        # Sort indices to maintain data structure
        sorted_indices = sorted(indices)
        logger.info(f"Sorted indices: first={sorted_indices[0] if sorted_indices else 'none'}, last={sorted_indices[-1] if sorted_indices else 'none'}")

        # Create a copy of the data for processing
        result = copy.deepcopy(self.data)
        logger.debug(f"Created copy of data with {len(result)} points")

        # Track changes for logging
        changes = []

        for idx in sorted_indices:
            if idx < 0 or idx >= len(self.data):
                logger.warning(f"Skipping invalid index {idx}")
                continue

            # Get the window of points centered on the current point
            half_window = window_size // 2
            window_start = max(0, idx - half_window)
            window_end = min(len(self.data) - 1, idx + half_window)

            # Collect points in the window
            window_points = self.data[window_start:window_end + 1]
            logger.debug(f"Window for idx={idx}: start={window_start}, end={window_end}, points={len(window_points)}")

            # Calculate the average y value only
            sum_y = sum(p[2] for p in window_points)
            count = len(window_points)

            if count > 0:
                avg_y = sum_y / count

                # Replace the point, but keep original frame and x-coordinate
                frame = self.data[idx][0]  # Keep original frame number
                original_x = self.data[idx][1]  # Keep original x-coordinate
                original_y = self.data[idx][2]  # Store original y for logging

                # Preserve status (keyframe, interpolated, etc.) if present
                if len(self.data[idx]) > 3:
                    status = self.data[idx][3]
                    result[idx] = (frame, original_x, avg_y, status)
                else:
                    result[idx] = (frame, original_x, avg_y)

                # Log the change
                if len(changes) < 5:  # Limit to 5 log entries to avoid spam
                    changes.append((idx, original_y, avg_y))

        # Log the changes
        for idx, old_y, new_y in changes:
            old_point = self.data[idx]
            new_point = result[idx]
            logger.debug(f"CHANGED idx={idx}: From ({old_point[0]}, {old_point[1]}, {old_y}) to ({new_point[0]}, {new_point[1]}, {new_y})")

        # Log sample points after smoothing
        if len(result) > 0 and len(indices) > 0:
            # Log the same sample points after smoothing
            sample_indices = [indices[0]]
            if len(indices) > 1:
                sample_indices.append(indices[len(indices)//2])
            if len(indices) > 2:
                sample_indices.append(indices[-1])

            for sample_idx in sample_indices:
                if 0 <= sample_idx < len(result):
                    after_point = result[sample_idx]
                    logger.info(f"AFTER - Sample point at idx={sample_idx}: frame={after_point[0]}, x={after_point[1]}, y={after_point[2]}")

                    # Also log the changes
                    if 0 <= sample_idx < len(self.data):
                        before_point = self.data[sample_idx]
                        y_diff = after_point[2] - before_point[2]
                        logger.info(f"CHANGE at idx={sample_idx}: y changed by {y_diff:.6f} ({before_point[2]:.6f} -> {after_point[2]:.6f})")

        self.data = result
        logger.info(f"Smoothing complete, updated {len(sorted_indices)} points")

    def smooth_gaussian(self, indices: List[int], window_size: int, sigma: float) -> None:
        """Apply Gaussian smoothing to both x and y coordinates

        Unlike moving_average smoothing, this method smooths both x and y coordinates,
        which may cause more significant position changes in the curve but produces
        a more coherent result for parametric curves.
        """
        if not self.data or not indices or window_size < 2:
            return

        # Gaussian weights calculation function
        def gaussian_weight(distance: float, sigma: float) -> float:
            return math.exp(-(distance ** 2) / (2 * sigma ** 2))

        # Sort indices to maintain data structure
        sorted_indices = sorted(indices)

        # Create a copy of the data for processing
        result = copy.deepcopy(self.data)

        for idx in sorted_indices:
            if idx < 0 or idx >= len(self.data):
                continue

            # Get the window of points centered on the current point
            half_window = window_size // 2
            window_start = max(0, idx - half_window)
            window_end = min(len(self.data) - 1, idx + half_window)

            # Collect points and calculate weights
            weighted_sum_x = 0.0
            weighted_sum_y = 0.0
            sum_weights = 0.0

            center_frame = self.data[idx][0]

            for i in range(window_start, window_end + 1):
                point = self.data[i]
                distance = abs(i - idx)
                weight = gaussian_weight(distance, sigma)

                weighted_sum_x += point[1] * weight
                weighted_sum_y += point[2] * weight
                sum_weights += weight

            if sum_weights > 0:
                avg_x = weighted_sum_x / sum_weights
                avg_y = weighted_sum_y / sum_weights

                # Replace the point with the smoothed one
                # Preserve status (keyframe, interpolated, etc.) if present
                if len(self.data[idx]) > 3:
                    status = self.data[idx][3]
                    result[idx] = (center_frame, avg_x, avg_y, status)
                else:
                    result[idx] = (center_frame, avg_x, avg_y)

        self.data = result

    def smooth_savitzky_golay(self, indices: List[int], window_size: int) -> None:
        """Apply Savitzky-Golay smoothing to both x and y coordinates

        This implementation smooths both x and y coordinates using a weighted moving average
        approach that prioritizes center points. Like Gaussian smoothing, it affects the
        overall position of points in the curve, not just the y values.
        """
        if not self.data or not indices or window_size < 3:
            return

        # Ensure window_size is odd
        if window_size % 2 == 0:
            window_size += 1

        # Need enough data points for the window size
        if len(self.data) < window_size:
            return

        # Sort indices to maintain data structure
        sorted_indices = sorted(indices)

        # Create a copy of the data for processing
        result = copy.deepcopy(self.data)

        # Simple polynomial fitting approach (simplified version of Savitzky-Golay)
        for idx in sorted_indices:
            if idx < 0 or idx >= len(self.data):
                continue

            # Get the window of points centered on the current point
            half_window = window_size // 2
            window_start = max(0, idx - half_window)
            window_end = min(len(self.data) - 1, idx + half_window)

            # Collect points in the window
            window_points = self.data[window_start:window_end + 1]
            window_x = [p[1] for p in window_points]
            window_y = [p[2] for p in window_points]

            # For a simplified implementation, use weighted moving average
            # where center points have higher weights
            center_frame = self.data[idx][0]  # Keep original frame number

            if len(window_points) >= 3:
                # Create weights that give higher importance to center points
                weights: List[float] = []
                center_idx = idx - window_start
                for i in range(len(window_points)):
                    # Distance from center (0 to half_window)
                    distance = abs(i - center_idx)
                    # Weight decreases as distance increases
                    weight: float = 1.0 / (1.0 + distance)
                    weights.append(weight)

                # Normalize weights
                weight_sum: float = sum(weights)
                if weight_sum > 0:
                    weights = [w / weight_sum for w in weights]  # Normalize to sum to 1.0
                else:
                    # Fallback to equal weights
                    weights = [1.0 / len(weights) for _ in range(len(weights))]

                # Calculate weighted average
                smoothed_x: float = sum(float(x) * float(w) for x, w in zip(window_x, weights))
                smoothed_y: float = sum(float(y) * float(w) for y, w in zip(window_y, weights))

                # Replace the point with the smoothed one
                # Preserve status (keyframe, interpolated, etc.) if present
                if len(self.data[idx]) > 3:
                    status = self.data[idx][3]
                    result[idx] = (center_frame, smoothed_x, smoothed_y, status)
                else:
                    result[idx] = (center_frame, smoothed_x, smoothed_y)

        self.data = result


class AnalysisService:
    """
    Service for curve data analysis and transformations
    """

    def __init__(self, data: List[Tuple[int, float, float]]) -> None:
        """
        Initialize with curve data

        Args:
            data: List of points in format [(frame, x, y), ...]
        """
        self.data: List[Tuple[int, float, float]] = data

    def create_processor(self, data: List[Tuple[int, float, float]]) -> CurveProcessor:
        """
        Create a curve processor instance for the given data

        Args:
            data: Curve data to process

        Returns:
            An instance of a curve processor
        """
        # Return an instance of ConcreteCurveProcessor instead of self
        return ConcreteCurveProcessor(data)

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

    def fill_gap(self, data: List[Tuple[int, float, float]], start_frame: int, end_frame: int, method: str = 'linear') -> List[Tuple[int, float, float]]:
        """
        Fill a gap in the curve data using the specified method.

        Args:
            data: List of tuples in format (frame, x, y)
            start_frame: First frame in the gap
            end_frame: Last frame in the gap
            method: Interpolation method ('linear' or 'cubic_spline')

        Returns:
            List of interpolated points within the gap
        """
        logger.debug(f"Filling gap from frame {start_frame} to {end_frame} using {method} method")
        if method == 'linear':
            # Find the points before and after the gap
            prev_point = next((point for point in reversed(data) if point[0] < start_frame), None)
            next_point = next((point for point in data if point[0] > end_frame), None)

            if prev_point and next_point:
                # Calculate the slope of the line
                slope_x = (next_point[1] - prev_point[1]) / (next_point[0] - prev_point[0])
                slope_y = (next_point[2] - prev_point[2]) / (next_point[0] - prev_point[0])

                # Fill the gap with linear interpolation
                for frame in range(start_frame, end_frame + 1):
                    x = prev_point[1] + slope_x * (frame - prev_point[0])
                    y = prev_point[2] + slope_y * (frame - prev_point[0])
                    data.append((frame, x, y))

        elif method == 'cubic_spline':
            # Find the points before and after the gap
            prev_points = [point for point in data if point[0] < start_frame]
            next_points = [point for point in data if point[0] > end_frame]

            logger.debug(f"Found {len(prev_points)} points before gap and {len(next_points)} points after gap")

            if prev_points and next_points:
                # Combine the points before and after the gap
                points = prev_points + next_points

                # Sort the points by frame
                points.sort(key=lambda point: point[0])

                # For fallback method if cubic spline isn't available
                if not has_scipy:
                    logger.debug("SciPy not available, falling back to linear interpolation")
                    return self.fill_gap(data, start_frame, end_frame, method='linear')

                try:
                    # Try importing here to keep the import local to this method
                    from scipy.interpolate import CubicSpline  # type: ignore

                    # Separate the x, y coordinates
                    frames_list: List[int] = []
                    xs_list: List[float] = []
                    ys_list: List[float] = []

                    for frame, x, y in points:
                        frames_list.append(frame)
                        xs_list.append(x)
                        ys_list.append(y)

                    # Create a cubic spline interpolation
                    cs_x = CubicSpline(frames_list, xs_list)
                    cs_y = CubicSpline(frames_list, ys_list)

                    # Add the interpolated points to the result
                    interpolated_points: List[Tuple[int, float, float]] = []
                    for frame in range(start_frame, end_frame + 1):
                        # Convert numpy values to Python floats
                        x_interp = float(cs_x(frame))
                        y_interp = float(cs_y(frame))
                        interpolated_points.append((frame, x_interp, y_interp))

                    logger.debug(f"Generated {len(interpolated_points)} interpolated points using cubic spline")
                    return interpolated_points
                except (ImportError, ValueError, TypeError):
                    # Fall back to linear interpolation if there's any issue
                    return self.fill_gap(data, start_frame, end_frame, method='linear')
            else:
                # Fall back to linear interpolation if scipy not available
                return self.fill_gap(data, start_frame, end_frame, method='linear')

        return data

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
            Dict[int, Dict[str, str]]: Dictionary of detected problems with frame numbers as keys
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
