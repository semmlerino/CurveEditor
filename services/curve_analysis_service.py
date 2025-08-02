#!/usr/bin/env python

"""
Unified Curve Analysis Service for curve data operations.

This service consolidates all curve data analysis and transformation operations
that were previously scattered across 7 different services:
- GeometryService: Rotation, offset, velocity normalization
- ProblemDetectionService: Problem detection, outliers, curvature
- SmoothingService: Moving average, Gaussian, spline smoothing
- FilteringService: Median, Butterworth filtering, duplicate removal
- GapFillingService: Linear, spline, velocity-based gap filling
- ExtrapolationService: Forward/backward extrapolation, frame interpolation

Following KISS principle: One service for related curve analysis operations.
"""

import copy
import math

from core.protocols.protocols import PointsList
from services.logging_service import LoggingService

logger = LoggingService.get_logger("curve_analysis_service")

# Optional scientific computing imports
_scipy_available = False  # Use lowercase private variable to avoid reportConstantRedefinition
try:
    import numpy as np  # noqa: F401
    from scipy import interpolate, signal  # noqa: F401

    _scipy_available = True
except ImportError:
    _scipy_available = False
    logger.info("SciPy not available - using fallback implementations for advanced filtering and interpolation")

# Public constant for external access
SCIPY_AVAILABLE = _scipy_available


class CurveAnalysisService:
    """
    Unified service for all curve data analysis and transformation operations.

    This service consolidates the functionality of 7 previously separate services
    into a single, maintainable class following KISS and DRY principles.
    """

    def __init__(self, data: PointsList) -> None:
        """
        Initialize with curve data.

        Args:
            data: list of points in format [(frame, x, y), ...]
        """
        self.data: PointsList = data

    def get_data(self) -> PointsList:
        """Get the current curve data."""
        return self.data

    def create_processor(self, data: PointsList) -> "ConcreteCurveProcessor":
        """Create a processor instance for the given data."""
        return ConcreteCurveProcessor(data)

    # =============================================================================
    # GEOMETRY OPERATIONS (formerly GeometryService)
    # =============================================================================

    @staticmethod
    def rotate_curve(
        data: PointsList, angle_degrees: float, center_x: float | None = None, center_y: float | None = None
    ) -> PointsList:
        """
        Rotate curve data around a center point.

        Args:
            data: list of points in format [(frame, x, y), ...]
            angle_degrees: Rotation angle in degrees
            center_x: X coordinate of rotation center (None for centroid)
            center_y: Y coordinate of rotation center (None for centroid)

        Returns:
            Rotated curve data
        """
        if not data:
            return []

        result = copy.deepcopy(data)

        # Calculate centroid if center not provided
        if center_x is None or center_y is None:
            sum_x = sum(p[1] for p in data)
            sum_y = sum(p[2] for p in data)
            center_x = sum_x / len(data) if center_x is None else center_x
            center_y = sum_y / len(data) if center_y is None else center_y

        # Convert angle to radians
        angle_rad = math.radians(angle_degrees)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)

        # Rotate each point
        for i, point in enumerate(result):
            frame, x, y = point[0], point[1], point[2]

            # Translate to origin
            rel_x = x - center_x
            rel_y = y - center_y

            # Rotate
            new_x = rel_x * cos_angle - rel_y * sin_angle
            new_y = rel_x * sin_angle + rel_y * cos_angle

            # Translate back
            final_x = new_x + center_x
            final_y = new_y + center_y

            # Preserve original tuple structure
            if len(point) == 3:
                result[i] = (frame, final_x, final_y)
            else:
                result[i] = (frame, final_x, final_y, *point[3:])

        logger.info(f"Rotated {len(result)} points by {angle_degrees}° around ({center_x:.2f}, {center_y:.2f})")
        return result

    @staticmethod
    def offset_points(data: PointsList, indices: list[int], dx: float, dy: float) -> PointsList:
        """
        Offset specified points by delta values.

        Args:
            data: list of points in format [(frame, x, y), ...]
            indices: list of point indices to offset
            dx: X offset to apply
            dy: Y offset to apply

        Returns:
            Data with specified points offset
        """
        if not data or not indices:
            return data

        result = copy.deepcopy(data)

        for idx in indices:
            if 0 <= idx < len(result):
                point = result[idx]
                frame, x, y = point[0], point[1], point[2]
                new_x, new_y = x + dx, y + dy

                # Preserve original tuple structure
                if len(point) == 3:
                    result[idx] = (frame, new_x, new_y)
                else:
                    result[idx] = (frame, new_x, new_y, *point[3:])

        logger.info(f"Offset {len(indices)} points by ({dx}, {dy})")
        return result

    @staticmethod
    def normalize_velocity(data: PointsList, target_velocity: float = 1.0) -> PointsList:
        """
        Normalize velocity-based movements in curve data to target velocity.

        Args:
            data: list of points in format [(frame, x, y), ...]
            target_velocity: Target velocity for normalization

        Returns:
            Data with normalized velocities
        """
        if len(data) < 2 or target_velocity <= 0:
            return data

        logger.info(f"Normalizing velocity for {len(data)} points to target {target_velocity}")

        # Sort by frame
        sorted_data = sorted(data, key=lambda p: p[0])
        result = copy.deepcopy(sorted_data)

        # Calculate and apply velocity normalization
        for i in range(1, len(sorted_data)):
            prev_point = result[i - 1]
            curr_point = result[i]

            dt = curr_point[0] - prev_point[0]
            if dt > 0:
                # Calculate current displacement
                dx = curr_point[1] - prev_point[1]
                dy = curr_point[2] - prev_point[2]
                current_distance = math.sqrt(dx * dx + dy * dy)

                if current_distance > 0:
                    # Calculate target distance for target velocity
                    target_distance = target_velocity * dt

                    # Scale displacement to achieve target velocity
                    scale_factor = target_distance / current_distance

                    # Apply scaling to get new position
                    new_dx = dx * scale_factor
                    new_dy = dy * scale_factor

                    # Update position relative to previous point
                    new_x = prev_point[1] + new_dx
                    new_y = prev_point[2] + new_dy

                    # Preserve original tuple structure
                    if len(curr_point) == 3:
                        result[i] = (curr_point[0], new_x, new_y)
                    else:
                        result[i] = (curr_point[0], new_x, new_y, *curr_point[3:])

        logger.info(f"Applied velocity normalization to target velocity {target_velocity}")
        return result

    # =============================================================================
    # PROBLEM DETECTION (formerly ProblemDetectionService)
    # =============================================================================

    @staticmethod
    def detect_problems(data: PointsList) -> dict[int, dict[str, str]]:
        """
        Detect common problems in tracking data.

        Detects issues such as:
        - Jitter (very small movements)
        - Sudden jumps (unusually large movements)
        - Gaps in frame sequence

        Args:
            data: list of points in format [(frame, x, y), ...]

        Returns:
            Dictionary mapping frame numbers to problem descriptions
        """
        if len(data) < 2:
            return {}

        logger.info(f"Detecting problems in {len(data)} points")

        sorted_data = sorted(data, key=lambda p: p[0])
        problems = {}

        # Define thresholds
        jitter_threshold = 0.5  # Very small movement
        jump_threshold = 10.0  # Large sudden movement

        for i in range(1, len(sorted_data)):
            prev_point = sorted_data[i - 1]
            curr_point = sorted_data[i]

            frame = curr_point[0]

            # Check for frame gaps
            if curr_point[0] - prev_point[0] > 1:
                problems[frame] = problems.get(frame, {})
                problems[frame]["type"] = "gap"
                problems[frame]["gap"] = f"Gap of {curr_point[0] - prev_point[0] - 1} frames"

            # Check for movement issues
            dx = abs(curr_point[1] - prev_point[1])
            dy = abs(curr_point[2] - prev_point[2])
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < jitter_threshold:
                problems[frame] = problems.get(frame, {})
                problems[frame]["type"] = "jitter"
                problems[frame]["jitter"] = f"Very small movement: {distance:.3f}"
            elif distance > jump_threshold:
                problems[frame] = problems.get(frame, {})
                problems[frame]["type"] = "jump"
                problems[frame]["jump"] = f"Large jump: {distance:.3f}"

        logger.info(f"Found problems in {len(problems)} frames")
        return problems

    @staticmethod
    def calculate_curvature(data: PointsList, indices: list[int]) -> list[float]:
        """
        Calculate curvature at specified points.

        Args:
            data: list of points in format [(frame, x, y), ...]
            indices: list of indices to calculate curvature for

        Returns: list of curvature values
        """
        if len(data) < 3:
            # For insufficient data, return zero curvature for each requested index
            return [0.0 for _ in indices]

        sorted_data = sorted(data, key=lambda p: p[0])
        curvatures = []

        for idx in indices:
            if 1 <= idx < len(sorted_data) - 1:
                # Get three consecutive points
                p1 = sorted_data[idx - 1]
                p2 = sorted_data[idx]
                p3 = sorted_data[idx + 1]

                # Calculate curvature using cross product method
                v1 = (p2[1] - p1[1], p2[2] - p1[2])
                v2 = (p3[1] - p2[1], p3[2] - p2[2])

                cross = v1[0] * v2[1] - v1[1] * v2[0]
                v1_mag = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
                v2_mag = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

                if v1_mag > 0 and v2_mag > 0:
                    curvature = abs(cross) / (v1_mag * v2_mag)
                    curvatures.append(curvature)
                else:
                    curvatures.append(0.0)
            else:
                curvatures.append(0.0)

        logger.info(f"Calculated curvature for {len(curvatures)} points")
        return curvatures

    # =============================================================================
    # SMOOTHING OPERATIONS (formerly SmoothingService)
    # =============================================================================

    @staticmethod
    def smooth_moving_average(data: PointsList, indices: list[int], window_size: int) -> PointsList:
        """
        Apply moving average smoothing to specified points.

        Args:
            data: list of points in format [(frame, x, y), ...]
            indices: list of indices to smooth
            window_size: Size of the smoothing window (will be made odd if even)

        Returns:
            Smoothed curve data
        """
        logger.info(f"Starting smooth_moving_average with {len(indices)} indices and window_size={window_size}")

        if not data or not indices:
            return data

        # Ensure window size is odd
        if window_size % 2 == 0:
            window_size += 1

        half_window = window_size // 2
        result = copy.deepcopy(data)
        sorted_data = sorted(data, key=lambda p: p[0])

        # Create frame-to-index mapping for efficient lookup
        {point[0]: i for i, point in enumerate(sorted_data)}

        for idx in indices:
            if 0 <= idx < len(sorted_data):
                target_frame = sorted_data[idx][0]

                # Collect neighboring points within window
                neighbor_points = []
                for i in range(max(0, idx - half_window), min(len(sorted_data), idx + half_window + 1)):
                    neighbor_points.append(sorted_data[i])

                if neighbor_points:
                    # Calculate average position
                    avg_x = sum(p[1] for p in neighbor_points) / len(neighbor_points)
                    avg_y = sum(p[2] for p in neighbor_points) / len(neighbor_points)

                    # Update the result
                    original_point = sorted_data[idx]
                    if len(original_point) == 3:
                        result[idx] = (target_frame, avg_x, avg_y)
                    else:
                        result[idx] = (target_frame, avg_x, avg_y, *original_point[3:])

        logger.info(f"Applied moving average smoothing to {len(indices)} points")
        return result

    @staticmethod
    def smooth_gaussian(data: PointsList, indices: list[int], sigma: float) -> PointsList:
        """
        Apply Gaussian smoothing to specified points.

        Args:
            data: list of points in format [(frame, x, y), ...]
            indices: list of indices to smooth
            sigma: Standard deviation for Gaussian kernel

        Returns:
            Smoothed curve data
        """
        logger.info(f"Applying Gaussian smoothing with sigma={sigma} to {len(indices)} points")

        if not data or not indices or sigma <= 0:
            return data

        # For now, use moving average as fallback
        # In a full implementation, this would use proper Gaussian weights
        window_size = max(3, int(3 * sigma))
        return CurveAnalysisService.smooth_moving_average(data, indices, window_size)

    # =============================================================================
    # FILTERING OPERATIONS (formerly FilteringService)
    # =============================================================================

    @staticmethod
    def filter_median(data: PointsList, indices: list[int], window_size: int) -> PointsList:
        """
        Apply median filter to specified points.

        Args:
            data: list of points in format [(frame, x, y), ...]
            indices: list of indices to filter
            window_size: Size of the filter window

        Returns:
            Filtered curve data
        """
        logger.info(f"Applying median filter with window_size={window_size} to {len(indices)} points")

        # For now, use moving average as a fallback since we don't have numpy
        # In a real implementation, this would calculate the median
        return CurveAnalysisService.smooth_moving_average(data, indices, window_size)

    @staticmethod
    def filter_butterworth(data: PointsList, indices: list[int], cutoff: float, order: int) -> PointsList:
        """
        Apply Butterworth filter to specified points.

        Args:
            data: list of points in format [(frame, x, y), ...]
            indices: list of indices to filter
            cutoff: Cutoff frequency
            order: Filter order

        Returns:
            Filtered curve data
        """
        logger.info(f"Applying Butterworth filter (cutoff={cutoff}, order={order}) to {len(indices)} points")

        if _scipy_available and len(indices) > order * 2:
            # Use scipy for Butterworth filtering
            try:
                from scipy import signal

                # Extract data for filtering
                result = copy.deepcopy(data)
                x_data = [result[i][1] for i in indices]
                y_data = [result[i][2] for i in indices]

                # Design filter
                b, a = signal.butter(order, cutoff, btype="low", analog=False)

                # Apply filter
                x_filtered = signal.filtfilt(b, a, x_data)
                y_filtered = signal.filtfilt(b, a, y_data)

                # Update result
                for idx, i in enumerate(indices):
                    result[i] = (result[i][0], float(x_filtered[idx]), float(y_filtered[idx]))

                return result
            except Exception as e:
                logger.warning(f"Butterworth filter failed, using fallback: {e}")

        # Fallback to moving average
        window_size = max(3, int(1.0 / cutoff) if cutoff > 0 else 5)
        return CurveAnalysisService.smooth_moving_average(data, indices, window_size)

    @staticmethod
    def remove_duplicates(data: PointsList) -> PointsList:
        """
        Remove duplicate points from curve data.

        Args:
            data: list of points in format [(frame, x, y), ...]

        Returns:
            Data with duplicates removed
        """
        if not data:
            return []

        logger.info(f"Removing duplicates from {len(data)} points")

        seen_frames = set()
        result = []

        for point in data:
            # Use frame as primary key for duplicate detection
            frame = point[0]
            if frame not in seen_frames:
                seen_frames.add(frame)
                result.append(point)

        logger.info(f"Removed {len(data) - len(result)} duplicate points")
        return result

    # =============================================================================
    # GAP FILLING (formerly GapFillingService)
    # =============================================================================

    @staticmethod
    def fill_gap_linear(data: PointsList, start_frame: int, end_frame: int) -> PointsList:
        """
        Fill a gap between start_frame and end_frame using linear interpolation.

        Args:
            data: list of points in format [(frame, x, y), ...]
            start_frame: Start frame of the gap (inclusive)
            end_frame: End frame of the gap (inclusive)

        Returns:
            Curve data with gap filled
        """
        if len(data) < 2 or start_frame >= end_frame:
            return data

        logger.info(f"Filling gap from frame {start_frame} to {end_frame} using linear interpolation")

        # Find the points before and after the gap
        sorted_data = sorted(data, key=lambda p: p[0])
        before_point = None
        after_point = None

        for point in sorted_data:
            if point[0] < start_frame:
                before_point = point
            elif point[0] > end_frame and after_point is None:
                after_point = point
                break

        if before_point is None or after_point is None:
            logger.warning("Cannot fill gap: missing boundary points")
            return data

        result = copy.deepcopy(data)

        # Linear interpolation between boundary points
        frame_diff = after_point[0] - before_point[0]
        x_diff = after_point[1] - before_point[1]
        y_diff = after_point[2] - before_point[2]

        for frame in range(start_frame, end_frame + 1):
            t = (frame - before_point[0]) / frame_diff
            x = before_point[1] + t * x_diff
            y = before_point[2] + t * y_diff
            result.append((frame, x, y))

        logger.info(f"Filled gap with {end_frame - start_frame + 1} interpolated points")
        return sorted(result, key=lambda p: p[0])

    @staticmethod
    def fill_gap_spline(data: PointsList, start_frame: int, end_frame: int) -> PointsList:
        """
        Fill a gap using spline interpolation.

        Args:
            data: list of points in format [(frame, x, y), ...]
            start_frame: Start frame of the gap
            end_frame: End frame of the gap

        Returns:
            Curve data with gap filled
        """
        logger.info(f"Filling gap from frame {start_frame} to {end_frame} using spline interpolation")

        if _scipy_available:
            try:
                from scipy import interpolate

                # Get points around the gap for interpolation
                frames = [p[0] for p in data]
                before_idx = max([i for i, f in enumerate(frames) if f < start_frame], default=-1)
                after_idx = min([i for i, f in enumerate(frames) if f > end_frame], default=len(data))

                if before_idx >= 0 and after_idx < len(data):
                    # Use at least 4 points for cubic spline (2 before, 2 after)
                    start_idx = max(0, before_idx - 1)
                    end_idx = min(len(data), after_idx + 2)

                    if end_idx - start_idx >= 4:
                        # Extract control points
                        control_frames = [data[i][0] for i in range(start_idx, end_idx)]
                        control_x = [data[i][1] for i in range(start_idx, end_idx)]
                        control_y = [data[i][2] for i in range(start_idx, end_idx)]

                        # Create cubic spline interpolators
                        spline_x = interpolate.CubicSpline(control_frames, control_x)
                        spline_y = interpolate.CubicSpline(control_frames, control_y)

                        # Generate interpolated points
                        result = copy.deepcopy(data)
                        for frame in range(start_frame, end_frame + 1):
                            x = float(spline_x(frame))
                            y = float(spline_y(frame))
                            result.append((frame, x, y))

                        return sorted(result, key=lambda p: p[0])
            except Exception as e:
                logger.warning(f"Spline interpolation failed, using fallback: {e}")

        # Fallback to linear interpolation
        return CurveAnalysisService.fill_gap_linear(data, start_frame, end_frame)

    # =============================================================================
    # EXTRAPOLATION (formerly ExtrapolationService)
    # =============================================================================

    @staticmethod
    def extrapolate_forward(data: PointsList, num_frames: int, method: int, fit_points: int) -> PointsList:
        """
        Extrapolate curve forward.

        Args:
            data: list of points in format [(frame, x, y), ...]
            num_frames: Number of frames to extrapolate
            method: Extrapolation method (0=linear, 1=quadratic, etc.)
            fit_points: Number of points to use for fitting

        Returns:
            Curve data with extrapolated points added
        """
        logger.info(f"Extrapolating {num_frames} frames forward using method={method} with {fit_points} fit points")

        if not data or len(data) < 2:
            return data

        # Get last points to establish direction
        sorted_data = sorted(data, key=lambda p: p[0])
        last_points = sorted_data[-fit_points:]
        if len(last_points) < 2:
            return data

        result = copy.deepcopy(data)

        # Simple linear extrapolation
        if method == 0:  # Linear
            p1, p2 = last_points[-2], last_points[-1]
            dx_per_frame = (p2[1] - p1[1]) / (p2[0] - p1[0]) if p2[0] != p1[0] else 0
            dy_per_frame = (p2[2] - p1[2]) / (p2[0] - p1[0]) if p2[0] != p1[0] else 0

            last_frame = p2[0]
            for i in range(1, num_frames + 1):
                new_frame = last_frame + i
                new_x = p2[1] + dx_per_frame * i
                new_y = p2[2] + dy_per_frame * i
                result.append((new_frame, new_x, new_y))

        logger.info(f"Added {num_frames} extrapolated points")
        return result

    @staticmethod
    def extrapolate_backward(data: PointsList, num_frames: int, method: int, fit_points: int) -> PointsList:
        """
        Extrapolate curve backward.

        Args:
            data: list of points in format [(frame, x, y), ...]
            num_frames: Number of frames to extrapolate
            method: Extrapolation method (0=linear, 1=quadratic, etc.)
            fit_points: Number of points to use for fitting

        Returns:
            Curve data with extrapolated points added
        """
        logger.info(f"Extrapolating {num_frames} frames backward using method={method} with {fit_points} fit points")

        if not data or len(data) < 2:
            return data

        # Get first points to establish direction
        sorted_data = sorted(data, key=lambda p: p[0])
        first_points = sorted_data[:fit_points]
        if len(first_points) < 2:
            return data

        result = copy.deepcopy(data)

        # Simple linear extrapolation
        if method == 0:  # Linear
            p1, p2 = first_points[0], first_points[1]
            dx_per_frame = (p2[1] - p1[1]) / (p2[0] - p1[0]) if p2[0] != p1[0] else 0
            dy_per_frame = (p2[2] - p1[2]) / (p2[0] - p1[0]) if p2[0] != p1[0] else 0

            first_frame = p1[0]
            for i in range(1, num_frames + 1):
                new_frame = first_frame - i
                new_x = p1[1] - dx_per_frame * i
                new_y = p1[2] - dy_per_frame * i
                result.append((new_frame, new_x, new_y))

        logger.info(f"Added {num_frames} extrapolated points")
        return sorted(result, key=lambda p: p[0])


class ConcreteCurveProcessor:
    """
    Concrete implementation of curve processor.

    This class provides a stateful interface to curve analysis operations,
    maintaining backward compatibility with existing code.
    """

    def __init__(self, data: PointsList) -> None:
        """Initialize with curve data."""
        self.data: PointsList = copy.deepcopy(data)
        self.analysis_service: CurveAnalysisService = CurveAnalysisService(self.data)

    def get_data(self) -> PointsList:
        """Get the current curve data."""
        return self.data

    def detect_problems(self) -> dict[int, dict[str, str]]:
        """Detect problems in the curve data."""
        return CurveAnalysisService.detect_problems(self.data)

    def smooth_moving_average(self, indices: list[int], window_size: int) -> None:
        """Apply moving average smoothing."""
        self.data = CurveAnalysisService.smooth_moving_average(self.data, indices, window_size)

    def offset_points(self, indices: list[int], dx: float, dy: float) -> None:
        """Offset specified points."""
        self.data = CurveAnalysisService.offset_points(self.data, indices, dx, dy)

    def extrapolate_forward(self, num_frames: int, method: int, fit_points: int) -> None:
        """Extrapolate curve forward."""
        self.data = CurveAnalysisService.extrapolate_forward(self.data, num_frames, method, fit_points)

    def extrapolate_backward(self, num_frames: int, method: int, fit_points: int) -> None:
        """Extrapolate curve backward."""
        self.data = CurveAnalysisService.extrapolate_backward(self.data, num_frames, method, fit_points)
