# services/analysis_service.py

from typing import List, Tuple, Optional, Dict, TypeVar, Protocol, Any
import copy
from services.protocols import PointsList
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

    def get_data(self) -> PointsList:
        """Get the processed curve data"""
        ...

    def smooth_moving_average(self, indices: List[int], window_size: int) -> None:
        """Apply moving average smoothing"""
        ...


T = TypeVar('T', bound=CurveProcessor)


class ConcreteCurveProcessor:
    """Concrete implementation of CurveProcessor"""

    def __init__(self, data: PointsList) -> None:
        """Initialize with curve data"""
        self.data: PointsList = copy.deepcopy(data)

    def get_data(self) -> PointsList:
        """Get the processed curve data"""
        return self.data

    def smooth_moving_average(self, indices: List[int], window_size: int, real_view: Any = None) -> None:
        """Apply moving average smoothing to x and y coordinates.

        This implementation applies a proper moving average filter where each point
        is smoothed based on its neighboring points within the window, not all selected points.
        This prevents the curve from shifting and only smooths local noise.

        Args:
            indices: List of indices to smooth
            window_size: Size of the smoothing window (must be odd)
            real_view: Optional reference to the actual curve view (not used in new implementation)
        """
        logger.info(f"Starting smooth_moving_average with {len(indices)} indices and window_size={window_size}")
        if not self.data or not indices:
            logger.warning(f"Smoothing skipped: data={bool(self.data)}, indices={bool(indices)}, window={window_size}")
            return

        # Ensure window size is odd
        if window_size % 2 == 0:
            window_size += 1

        # Sort indices to maintain data structure
        sorted_indices = sorted([idx for idx in indices if 0 <= idx < len(self.data)])
        if not sorted_indices:
            logger.warning("No valid indices to smooth")
            return

        logger.info(f"Valid indices: first={sorted_indices[0]}, last={sorted_indices[-1]}, count={len(sorted_indices)}")

        # Create a copy of the data for results
        result = copy.deepcopy(self.data)

        # Create a set for fast lookup of which indices to smooth
        indices_set = set(sorted_indices)

        # Calculate half window for easier indexing
        half_window = window_size // 2

        # Apply moving average to each selected point
        for idx in sorted_indices:
            if idx >= len(self.data):
                continue

            point = self.data[idx]
            frame_num = point[0]

            # Collect neighboring points within the window
            # Only consider points that have the same or adjacent frame numbers
            neighbors_x = []
            neighbors_y = []

            # Look for neighbors within the window range
            for offset in range(-half_window, half_window + 1):
                neighbor_idx = idx + offset

                # Check if neighbor index is valid and in our data
                if 0 <= neighbor_idx < len(self.data):
                    neighbor = self.data[neighbor_idx]
                    # Only include neighbors that are close in frame number
                    # This prevents smoothing across disconnected curve segments
                    if abs(neighbor[0] - frame_num) <= half_window:
                        neighbors_x.append(neighbor[1])
                        neighbors_y.append(neighbor[2])

            # Calculate average of neighbors
            if neighbors_x and neighbors_y:
                avg_x = sum(neighbors_x) / len(neighbors_x)
                avg_y = sum(neighbors_y) / len(neighbors_y)

                # Apply smoothing with a blend factor to preserve some original character
                # Higher window sizes get stronger smoothing
                blend_factor = min(0.8, window_size / 20.0)

                new_x = point[1] * (1 - blend_factor) + avg_x * blend_factor
                new_y = point[2] * (1 - blend_factor) + avg_y * blend_factor

                # Preserve status if available
                if len(point) > 3 and isinstance(point[3], bool):
                    result[idx] = (frame_num, new_x, new_y, point[3])
                else:
                    result[idx] = (frame_num, new_x, new_y, False)

                logger.debug(f"Smoothed point {idx}: ({point[1]:.2f}, {point[2]:.2f}) -> ({new_x:.2f}, {new_y:.2f})")
            else:
                # No valid neighbors found, keep original point
                logger.debug(f"No valid neighbors for point {idx}, keeping original")

        # Log sample results
        sample_indices = sorted_indices[:2] + [sorted_indices[-1]] if len(sorted_indices) > 2 else sorted_indices
        for idx in sample_indices:
            if idx < len(self.data) and idx < len(result):
                before = self.data[idx]
                after = result[idx]
                logger.info(f"Point {idx}: ({before[1]:.2f}, {before[2]:.2f}) -> ({after[1]:.2f}, {after[2]:.2f})")

        # Update the data with smoothed values
        self.data = result
        logger.info(f"Smoothing complete, updated {len(sorted_indices)} points")


class AnalysisService:
    """
    Service for curve data analysis and transformations
    """

    def __init__(self, data: PointsList) -> None:
        """
        Initialize with curve data

        Args:
            data: List of points in format [(frame, x, y), ...]
        """
        self.data: PointsList = data

    def create_processor(self, data: PointsList) -> CurveProcessor:
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
                center_x = sum_x / count
                center_y = sum_y / count
            else:
                # No points, no rotation
                return result

        # Apply rotation transform to each point
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)

        for i, (frame, x, y) in enumerate(curve_data):
            # Translate to origin (center point)
            tx = x - center_x
            ty = y - center_y

            # Apply rotation
            rx = tx * cos_angle - ty * sin_angle
            ry = tx * sin_angle + ty * cos_angle

            # Translate back
            result[i] = (frame, rx + center_x, ry + center_y)

        return result

    @classmethod
    def find_velocity_outliers(cls, curve_data: List[Tuple[int, float, float]], threshold_factor: float = 2.0) -> List[int]:
        """
        Find points with velocity significantly different from neighbors.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]
            threshold_factor: Factor for determining outliers (default: 2.0 * mean velocity)

        Returns:
            List[int]: Indices of outlier points
        """
        if len(curve_data) < 3:
            return []

        # Calculate velocities between consecutive points
        velocities: List[float] = []
        for i in range(1, len(curve_data)):
            p1 = curve_data[i-1]
            p2 = curve_data[i]
            frame_diff = p2[0] - p1[0]
            if frame_diff > 0:
                dx = p2[1] - p1[1]
                dy = p2[2] - p1[2]
                velocity = math.sqrt(dx*dx + dy*dy) / frame_diff
                velocities.append(velocity)

        if not velocities:
            return []

        # Calculate mean and standard deviation
        mean_velocity = sum(velocities) / len(velocities)
        threshold = mean_velocity * threshold_factor

        # Find outliers
        outliers: List[int] = []

        # Check first point
        if velocities[0] > threshold:
            outliers.append(0)

        # Check middle points
        for i in range(1, len(velocities)):
            if velocities[i] > threshold:
                outliers.append(i)

        return outliers

    @classmethod
    def interpolate_missing_frames(cls, curve_data: List[Tuple[int, float, float]]) -> List[Tuple[int, float, float]]:
        """
        Interpolate points for missing frame numbers.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]

        Returns:
            List[Tuple[int, float, float]]: Curve data with interpolated points
        """
        if len(curve_data) < 2:
            return curve_data.copy()

        # Sort by frame number
        sorted_data = sorted(curve_data, key=lambda p: p[0])
        result: List[Tuple[int, float, float]] = []

        for i in range(len(sorted_data) - 1):
            p1 = sorted_data[i]
            p2 = sorted_data[i + 1]
            result.append(p1)

            # Check for gap
            frame_gap = p2[0] - p1[0]
            if frame_gap > 1:
                # Interpolate missing frames
                for j in range(1, frame_gap):
                    t = j / frame_gap
                    frame = p1[0] + j
                    x = p1[1] * (1 - t) + p2[1] * t
                    y = p1[2] * (1 - t) + p2[2] * t
                    result.append((frame, x, y))

        # Add last point
        result.append(sorted_data[-1])

        return result

    def get_data(self) -> PointsList:
        """
        Get the current curve data

        Returns:
            PointsList: Current curve data
        """
        return self.data

    def smooth_moving_average(self, indices: List[int], window_size: int) -> None:
        """
        Apply moving average smoothing to specified points

        Args:
            indices: List of point indices to smooth
            window_size: Size of the smoothing window
        """
        processor = self.create_processor(self.data)
        processor.smooth_moving_average(indices, window_size)
        self.data = processor.get_data()

    def apply_spline(self, control_indices: List[int]) -> None:
        """
        Apply spline interpolation using control points.

        Args:
            control_indices: Indices of control points for the spline
        """
        if len(control_indices) < 2:
            return

        try:
            # Try to import scipy
            from scipy.interpolate import CubicSpline

            # Extract control points
            control_points = [self.data[i] for i in control_indices if i < len(self.data)]
            if len(control_points) < 2:
                return

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
            min_frame = frames[0]
            max_frame = frames[-1]

            for i, point in enumerate(self.data):
                frame = point[0]
                if min_frame <= frame <= max_frame:
                    new_x = float(spline_x(frame))
                    new_y = float(spline_y(frame))
                    # Preserve status if present
                    if len(point) > 3:
                        self.data[i] = (frame, new_x, new_y, point[3])
                    else:
                        self.data[i] = (frame, new_x, new_y)

        except ImportError:
            # Fall back to linear interpolation
            logger.warning("SciPy not available, using linear interpolation")
            self._linear_interpolate(control_indices)

    def _linear_interpolate(self, control_indices: List[int]) -> None:
        """
        Simple linear interpolation fallback

        Args:
            control_indices: Indices of control points
        """
        # Extract and sort control points
        control_points = [self.data[i] for i in control_indices if i < len(self.data)]
        control_points.sort(key=lambda p: p[0])

        if len(control_points) < 2:
            return

        # For each segment between control points
        for i in range(len(control_points) - 1):
            p1 = control_points[i]
            p2 = control_points[i + 1]

            # Find all points in this segment
            for j, point in enumerate(self.data):
                frame = point[0]
                if p1[0] < frame < p2[0]:
                    # Interpolate
                    t = (frame - p1[0]) / (p2[0] - p1[0])
                    new_x = p1[1] * (1 - t) + p2[1] * t
                    new_y = p1[2] * (1 - t) + p2[2] * t

                    # Preserve status if present
                    if len(point) > 3:
                        self.data[j] = (frame, new_x, new_y, point[3])
                    else:
                        self.data[j] = (frame, new_x, new_y)

    def normalize_velocity(self, target_velocity: float) -> None:
        """
        Normalize velocity between points to target value.

        Args:
            target_velocity: Target velocity in pixels per frame
        """
        if len(self.data) < 2 or target_velocity <= 0:
            return

        # Keep first point fixed
        result = [self.data[0]]

        # Adjust subsequent points
        for i in range(1, len(self.data)):
            prev = result[-1]
            curr = self.data[i]

            frame_diff = curr[0] - prev[0]
            if frame_diff <= 0:
                # Same frame, keep as is
                result.append(curr)
                continue

            # Calculate current vector
            dx = curr[1] - prev[1]
            dy = curr[2] - prev[2]
            current_dist = math.sqrt(dx*dx + dy*dy)

            if current_dist == 0:
                # No movement, keep as is
                result.append(curr)
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

        self.data = result

    def calculate_curvature(self) -> List[float]:
        """
        Calculate curvature at each point.

        Returns:
            List[float]: Curvature values for each point
        """
        if len(self.data) < 3:
            return [0.0] * len(self.data)

        curvatures: List[float] = []

        # First point
        curvatures.append(0.0)

        # Middle points
        for i in range(1, len(self.data) - 1):
            p1 = self.data[i-1]
            p2 = self.data[i]
            p3 = self.data[i+1]

            # Calculate vectors
            v1_x = p2[1] - p1[1]
            v1_y = p2[2] - p1[2]
            v2_x = p3[1] - p2[1]
            v2_y = p3[2] - p2[2]

            # Calculate angle between vectors
            dot = v1_x * v2_x + v1_y * v2_y
            det = v1_x * v2_y - v1_y * v2_x
            angle = math.atan2(det, dot)

            # Curvature is change in angle over distance
            dist1 = math.sqrt(v1_x*v1_x + v1_y*v1_y)
            dist2 = math.sqrt(v2_x*v2_x + v2_y*v2_y)
            avg_dist = (dist1 + dist2) / 2

            if avg_dist > 0:
                curvature = abs(angle) / avg_dist
            else:
                curvature = 0.0

            curvatures.append(curvature)

        # Last point
        curvatures.append(0.0)

        return curvatures

    def remove_duplicates(self) -> int:
        """
        Remove duplicate points with same frame number.

        Returns:
            int: Number of duplicates removed
        """
        if not self.data:
            return 0

        seen_frames: Dict[int, int] = {}
        unique_data: PointsList = []
        removed = 0

        for i, point in enumerate(self.data):
            frame = point[0]
            if frame not in seen_frames:
                seen_frames[frame] = i
                unique_data.append(point)
            else:
                removed += 1
                # Keep the point with larger movement or newer index
                existing_idx = seen_frames[frame]
                existing = unique_data[existing_idx]

                # Compare movement from origin
                existing_dist = existing[1]**2 + existing[2]**2
                current_dist = point[1]**2 + point[2]**2

                if current_dist > existing_dist:
                    unique_data[existing_idx] = point

        self.data = unique_data
        return removed
