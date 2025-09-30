#!/usr/bin/env python
"""
Data Analysis Service for CurveEditor.

This service handles curve data analysis operations including:
- Smoothing (moving average)
- Filtering (median, Butterworth)
- Gap filling with linear interpolation
- Outlier detection based on velocity deviation
- Statistical analysis of curve data

Extracted from DataService during Phase 3 modularization.
"""

import logging
import statistics
from typing import TYPE_CHECKING

# Third-party imports with type stubs handling
try:
    from scipy import signal  # type: ignore[import-untyped]
except ImportError:
    signal = None  # type: ignore[assignment]

from core.type_aliases import CurveDataList
from protocols.services import LoggingServiceProtocol, StatusServiceProtocol

if TYPE_CHECKING:
    pass

logger = logging.getLogger("data_analysis")


class DataAnalysisService:
    """Service for curve data analysis and processing operations."""

    def __init__(
        self,
        logging_service: LoggingServiceProtocol | None = None,
        status_service: StatusServiceProtocol | None = None,
    ) -> None:
        """Initialize DataAnalysisService with optional dependencies."""
        self._logger: LoggingServiceProtocol | None = logging_service
        self._status: StatusServiceProtocol | None = status_service

    def smooth_moving_average(self, data: CurveDataList, window_size: int = 5) -> CurveDataList:
        """Apply moving average smoothing to curve data."""
        if len(data) < window_size:
            return data

        result: CurveDataList = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]

            avg_x = sum(p[1] for p in window) / len(window)
            avg_y = sum(p[2] for p in window) / len(window)

            # Preserve frame and additional data
            if len(data[i]) > 3:
                result.append((data[i][0], avg_x, avg_y) + data[i][3:])  # type: ignore[arg-type]
            else:
                result.append((data[i][0], avg_x, avg_y))

        if self._status:
            self._status.set_status(f"Applied moving average (window={window_size})")
        return result

    def filter_median(self, data: CurveDataList, window_size: int = 5) -> CurveDataList:
        """Apply median filter to curve data."""
        if len(data) < window_size:
            return data

        result: CurveDataList = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]

            med_x = statistics.median(p[1] for p in window)
            med_y = statistics.median(p[2] for p in window)

            if len(data[i]) > 3:
                result.append((data[i][0], med_x, med_y) + data[i][3:])  # type: ignore[arg-type]
            else:
                result.append((data[i][0], med_x, med_y))

        if self._status:
            self._status.set_status(f"Applied median filter (window={window_size})")
        return result

    def filter_butterworth(self, data: CurveDataList, cutoff: float = 0.1, order: int = 2) -> CurveDataList:
        """Apply Butterworth low-pass filter using scipy."""
        if signal is None:
            if self._logger:
                self._logger.log_error("scipy not available")
            return data

        try:
            if len(data) < 4:
                return data

            frames = [p[0] for p in data]
            x_coords = [p[1] for p in data]
            y_coords = [p[2] for p in data]

            # Design and apply filter - properly handle scipy return types
            assert signal is not None  # Type guard for mypy/basedpyright
            filter_result = signal.butter(order, cutoff, btype="low")  # type: ignore[attr-defined]

            # scipy.signal.butter always returns a 2-tuple (b, a) when output='ba' (default)
            if not isinstance(filter_result, tuple) or len(filter_result) != 2:
                raise ValueError("Unexpected return type from signal.butter")

            b, a = filter_result
            filtered_x = signal.filtfilt(b, a, x_coords)  # type: ignore[attr-defined,arg-type]
            filtered_y = signal.filtfilt(b, a, y_coords)  # type: ignore[attr-defined,arg-type]

            # Reconstruct data
            result: CurveDataList = []
            for i, frame in enumerate(frames):
                if len(data[i]) > 3:
                    result.append((frame, filtered_x[i], filtered_y[i]) + data[i][3:])  # type: ignore[arg-type]
                else:
                    result.append((frame, filtered_x[i], filtered_y[i]))

            if self._status:
                self._status.set_status("Applied Butterworth filter")
            return result

        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Butterworth filter failed: {e}")
            return data

    def fill_gaps(self, data: CurveDataList, max_gap: int = 5) -> CurveDataList:
        """Fill gaps in curve data using linear interpolation."""
        if len(data) < 2:
            return data

        result = []
        filled_count = 0

        for i in range(len(data) - 1):
            result.append(data[i])
            gap = data[i + 1][0] - data[i][0] - 1

            if 0 < gap <= max_gap:
                # Linear interpolation for gap filling
                for j in range(1, gap + 1):
                    t = j / (gap + 1)
                    frame = data[i][0] + j
                    x = data[i][1] + t * (data[i + 1][1] - data[i][1])
                    y = data[i][2] + t * (data[i + 1][2] - data[i][2])
                    result.append((frame, x, y, False))  # Mark as interpolated
                    filled_count += 1

        result.append(data[-1])

        if filled_count > 0:
            logger.info(f"Filled {filled_count} gap points")
        return result

    def detect_outliers(self, data: CurveDataList, threshold: float = 2.0) -> list[int]:
        """Detect outliers based on velocity deviation."""
        if len(data) < 3:
            return []

        # Calculate velocities
        velocities = []
        for i in range(1, len(data)):
            dx = data[i][1] - data[i - 1][1]
            dy = data[i][2] - data[i - 1][2]
            dt = data[i][0] - data[i - 1][0]
            if dt > 0:
                velocities.append((dx / dt, dy / dt))

        if len(velocities) < 2:
            return []

        # Calculate statistics
        mean_vx = sum(v[0] for v in velocities) / len(velocities)
        mean_vy = sum(v[1] for v in velocities) / len(velocities)

        outliers = []
        if len(velocities) > 1:
            std_vx = statistics.stdev(v[0] for v in velocities)
            std_vy = statistics.stdev(v[1] for v in velocities)

            # Detect outliers
            for i, (vx, vy) in enumerate(velocities):
                if (std_vx > 0 and abs(vx - mean_vx) > threshold * std_vx) or (
                    std_vy > 0 and abs(vy - mean_vy) > threshold * std_vy
                ):
                    outliers.append(i + 1)

        if self._logger and outliers:
            self._logger.log_info(f"Detected {len(outliers)} outliers")
        return outliers

    def analyze_points(self, points: CurveDataList) -> dict[str, object]:
        """Analyze curve points and return statistics."""
        if not points:
            return {
                "count": 0,
                "min_frame": 0,
                "max_frame": 0,
                "bounds": {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0},
            }

        # Extract data from points (handle both CurvePoint objects and tuples)
        frames = []
        x_coords = []
        y_coords = []

        for point in points:
            # Check if point is a CurvePoint object by looking for frame attribute
            if isinstance(point, tuple | list) and len(point) >= 3:  # Tuple format
                frames.append(point[0])
                x_coords.append(point[1])
                y_coords.append(point[2])
            elif getattr(point, "frame", None) is not None:  # CurvePoint object
                frames.append(point.frame)
                x_coords.append(point.x)
                y_coords.append(point.y)

        return {
            "count": len(points),
            "min_frame": min(frames) if frames else 0,
            "max_frame": max(frames) if frames else 0,
            "bounds": {
                "min_x": min(x_coords) if x_coords else 0,
                "max_x": max(x_coords) if x_coords else 0,
                "min_y": min(y_coords) if y_coords else 0,
                "max_y": max(y_coords) if y_coords else 0,
            },
        }

    def get_frame_point_status(self, points: CurveDataList, frame: int) -> tuple[int, int, bool]:
        """Get point status information for a specific frame.

        Args:
            points: List of curve data points to analyze
            frame: Frame number to query

        Returns:
            Tuple of (keyframe_count, interpolated_count, has_selected)
            where has_selected is always False (reserved for future selection tracking)
        """
        if not points:
            return (0, 0, False)

        keyframe_count = 0
        interpolated_count = 0

        for point in points:
            # Handle both tuple format and CurvePoint objects
            if isinstance(point, list | tuple) and len(point) >= 3:  # Tuple format
                point_frame = point[0]
                if point_frame == frame:
                    # Check status if available
                    status = point[3] if len(point) > 3 else "keyframe"
                    if isinstance(status, bool):
                        # Legacy boolean format: True = interpolated, False = keyframe
                        if status:
                            interpolated_count += 1
                        else:
                            keyframe_count += 1
                    elif isinstance(status, str):
                        if status == "interpolated":
                            interpolated_count += 1
                        else:
                            keyframe_count += 1
                    else:
                        keyframe_count += 1
            elif getattr(point, "frame", None) is not None:  # CurvePoint object
                if getattr(point, "frame") == frame:
                    if getattr(getattr(point, "status"), "value", None) == "interpolated":
                        interpolated_count += 1
                    else:
                        keyframe_count += 1

        return (keyframe_count, interpolated_count, False)

    def get_frame_range_point_status(self, points: CurveDataList) -> dict[int, tuple[int, int, bool]]:
        """Get point status for all frames that have points.

        Args:
            points: List of curve data points to analyze

        Returns:
            Dictionary mapping frame numbers to (keyframe_count, interpolated_count, has_selected) tuples
        """
        if not points:
            return {}

        frame_status = {}

        for point in points:
            # Handle both tuple format and CurvePoint objects
            if isinstance(point, list | tuple) and len(point) >= 3:  # Tuple format
                frame = point[0]
                if frame not in frame_status:
                    frame_status[frame] = [0, 0, False]  # [keyframe, interpolated, selected]

                # Check status if available
                status = point[3] if len(point) > 3 else "keyframe"
                if isinstance(status, bool):
                    # Legacy boolean format: True = interpolated, False = keyframe
                    if status:
                        frame_status[frame][1] += 1
                    else:
                        frame_status[frame][0] += 1
                elif isinstance(status, str):
                    if status == "interpolated":
                        frame_status[frame][1] += 1
                    else:
                        frame_status[frame][0] += 1
                else:
                    frame_status[frame][0] += 1
            elif getattr(point, "frame", None) is not None:  # CurvePoint object
                frame = getattr(point, "frame")
                if frame not in frame_status:
                    frame_status[frame] = [0, 0, False]  # [keyframe, interpolated, selected]

                if getattr(getattr(point, "status"), "value", None) == "interpolated":
                    frame_status[frame][1] += 1
                else:
                    frame_status[frame][0] += 1

        # Convert to tuple format
        return {frame: tuple(counts) for frame, counts in frame_status.items()}
