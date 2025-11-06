#!/usr/bin/env python
"""
Consolidated DataService for CurveEditor.

This service handles:
- Data analysis operations (smoothing, filtering, gap filling, outlier detection)
- File I/O operations (load/save CSV and JSON files)
- Image sequence operations (loading and caching)
- Recent files tracking
"""

import csv
import json
import statistics
import threading
from pathlib import Path
from typing import TYPE_CHECKING, cast

from core.curve_data import CurveDataWithMetadata
from core.curve_segments import SegmentedCurve
from core.error_handling import safe_execute, safe_execute_optional
from core.logger_utils import get_logger
from core.models import FrameStatus, PointStatus
from core.type_aliases import CurveDataInput, CurveDataList, LegacyPointData
from services.service_protocols import LoggingServiceProtocol, StatusServiceProtocol

if TYPE_CHECKING:
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import QWidget

# Simple filter import (replaces scipy dependency)
from core.simple_filters import simple_lowpass_filter

logger = get_logger("data_service")


class DataService:
    """
    Consolidated service for data analysis and file operations.

    This service handles:
    - Curve data analysis (smoothing, filtering, gap filling, outlier detection)
    - File I/O operations (load/save CSV and JSON files)
    - Image sequence operations (loading and caching)
    - Recent files tracking
    """

    def __init__(
        self,
        logging_service: LoggingServiceProtocol | None = None,
        status_service: StatusServiceProtocol | None = None,
    ) -> None:
        """Initialize DataService with optional dependencies."""
        from services.image_cache_manager import SafeImageCacheManager

        self._lock: threading.RLock = threading.RLock()
        self._logger: LoggingServiceProtocol | None = logging_service
        self._status: StatusServiceProtocol | None = status_service

        # Initialize state for file I/O and image operations
        self._recent_files: list[str] = []
        self._max_recent_files: int = 10  # Maximum number of recent files to keep
        self._last_directory: str = ""
        self._image_cache: dict[str, object] = {}
        self._max_cache_size: int = 100  # Maximum number of cached images

        # SegmentedCurve cache for performance (keyed by object ID)
        # Using object ID allows caching when the same list instance is reused
        self._segmented_curves: dict[int, SegmentedCurve] = {}
        self._max_segmented_cache_size: int = 10  # Limit cache size

        # Persistent SegmentedCurve for restoration functionality (separate from cache)
        self._segmented_curve: SegmentedCurve | None = None
        self._current_curve_data: CurveDataList | None = None

        # Phase 2C: Image cache manager for efficient background image loading
        self._safe_image_cache: SafeImageCacheManager = SafeImageCacheManager(max_cache_size=100)

    @property
    def segmented_curve(self) -> SegmentedCurve | None:
        """Get the current SegmentedCurve for active curve data.

        Returns:
            SegmentedCurve instance for current curve, or None if no curve loaded
        """
        return self._segmented_curve

    # ==================== Public File I/O Methods (Sprint 11.5) ====================

    def load_csv(self, filepath: str) -> CurveDataList:
        """
        Public method to load CSV file programmatically.

        SPRINT 11.5 FIX: Added public method for programmatic file loading.

        Args:
            filepath: Path to CSV file

        Returns:
            List of curve data points
        """
        return self._load_csv(filepath)

    def load_json(self, filepath: str) -> CurveDataList:
        """
        Public method to load JSON file programmatically.

        SPRINT 11.5 FIX: Added public method for programmatic file loading.

        Args:
            filepath: Path to JSON file

        Returns:
            List of curve data points
        """
        return self._load_json(filepath)

    def load_2dtrack_data(self, filepath: str) -> CurveDataList | CurveDataWithMetadata:
        """
        Public method to load 2D track data file programmatically.

        Args:
            filepath: Path to 2D track data file

        Returns:
            List of curve data points or metadata-wrapped curve data
        """
        return self._load_2dtrack_data(filepath)

    def save_json(self, filepath: str, data: CurveDataList) -> bool:
        """
        Public method to save data as JSON programmatically.

        SPRINT 11.5 FIX: Added public method for programmatic file saving.

        Args:
            filepath: Path to save JSON file
            data: Curve data to save

        Returns:
            True if successful
        """
        return self._save_json(filepath, data, label="", color="")

    # ==================== Core Analysis Methods ====================

    def smooth_moving_average(self, data: CurveDataInput, window_size: int = 5) -> CurveDataList:
        """Apply moving average smoothing to curve data."""
        if len(data) < window_size:
            return list(data)

        result: CurveDataList = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]

            avg_x = sum(p[1] for p in window) / len(window)
            avg_y = sum(p[2] for p in window) / len(window)

            # Preserve frame and additional data
            if len(data[i]) > 3:
                combined = (data[i][0], avg_x, avg_y, *data[i][3:])
                result.append(cast(LegacyPointData, combined))
            else:
                result.append((data[i][0], avg_x, avg_y))

        if self._status:
            self._status.set_status(f"Applied moving average (window={window_size})")
        return result

    def filter_median(self, data: CurveDataInput, window_size: int = 5) -> CurveDataList:
        """Apply median filter to curve data."""
        if len(data) < window_size:
            return list(data)

        result: CurveDataList = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]

            med_x = statistics.median(p[1] for p in window)
            med_y = statistics.median(p[2] for p in window)

            if len(data[i]) > 3:
                combined = (data[i][0], med_x, med_y, *data[i][3:])
                result.append(cast(LegacyPointData, combined))
            else:
                result.append((data[i][0], med_x, med_y))

        if self._status:
            self._status.set_status(f"Applied median filter (window={window_size})")
        return result

    def filter_butterworth(self, data: CurveDataList, _cutoff: float = 0.1, order: int = 2) -> CurveDataList:
        """Apply lowpass filter to curve data.

        Now uses simple moving average instead of scipy.

        Args:
            data: Curve data to filter
            cutoff: Not used (kept for compatibility)
            order: Used as window size factor (default 2)

        Returns:
            Filtered curve data
        """
        if not data:
            return []

        # Use order as window size factor, ensure odd number for symmetry
        window_size = order * 2 + 1 if order < 10 else 5

        def _apply_filter() -> CurveDataList | None:
            result = simple_lowpass_filter(data, window_size)
            if self._status:
                self._status.set_status("Applied lowpass filter")
            return result

        # Try to apply filter, return original data if it fails
        result = safe_execute_optional("applying lowpass filter", _apply_filter, "DataService")
        if result is None:
            if self._logger:
                self._logger.log_error("Filtering failed. Returning original data.")
            return data
        return result

    def fill_gaps(self, data: CurveDataList, max_gap: int = 5) -> CurveDataList:
        """Fill gaps in curve data using linear interpolation."""
        if len(data) < 2:
            return data

        result: CurveDataList = []
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

    def detect_outliers(self, data: CurveDataInput, threshold: float = 2.0) -> list[int]:
        """Detect outliers based on velocity deviation."""
        if len(data) < 3:
            return []

        # Calculate velocities
        velocities: list[tuple[float, float]] = []
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

        outliers: list[int] = []
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

    def analyze_points(self, points: CurveDataInput) -> dict[str, object]:
        """Analyze curve points and return statistics."""
        if not points:
            return {
                "count": 0,
                "min_frame": 0,
                "max_frame": 0,
                "bounds": {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0},
            }

        # Extract data from points (handle both CurvePoint objects and tuples)
        frames: list[int] = []
        x_coords: list[float] = []
        y_coords: list[float] = []

        for point in points:
            # Handle CurvePoint object (check for frame attribute first)
            if hasattr(point, "frame"):
                frames.append(point.frame)  # pyright: ignore[reportAttributeAccessIssue]
                x_coords.append(point.x)  # pyright: ignore[reportAttributeAccessIssue]
                y_coords.append(point.y)  # pyright: ignore[reportAttributeAccessIssue]
            # Handle tuple/list format
            elif len(point) >= 3:
                frames.append(point[0])
                x_coords.append(point[1])
                y_coords.append(point[2])

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
            if len(point) >= 3:  # Tuple format (point is always list | tuple)
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
                    # Treat as string or other type
                    elif status == "interpolated":
                        interpolated_count += 1
                    else:
                        keyframe_count += 1
            elif getattr(point, "frame", None) is not None:  # CurvePoint object
                if point.frame == frame:
                    if getattr(point.status, "value", None) == "interpolated":
                        interpolated_count += 1
                    else:
                        keyframe_count += 1

        return (keyframe_count, interpolated_count, False)

    def get_position_at_frame(self, points: CurveDataList, frame: int) -> tuple[float, float] | None:
        """Get position at a specific frame using gap-aware interpolation.

        Uses SegmentedCurve logic to handle gaps properly:
        - Active segments: Normal interpolation between keyframes
        - Inactive segments (gaps): Returns held position from preceding endframe

        Performance: Caches SegmentedCurve instances by object ID for ~5-20x speedup.
        Priority: Uses persistent curve if available (for restoration logic), then cache, then creates new.

        Args:
            points: List of curve data points
            frame: Frame number to get position for

        Returns:
            Tuple of (x, y) coordinates or None if no position available
        """
        if not points:
            return None

        # Priority 1: Use persistent curve if points match (for restoration logic)
        if self._current_curve_data is points and self._segmented_curve:
            return self._segmented_curve.get_position_at_frame(frame)

        # Priority 2: Check cache using object ID
        points_id = id(points)
        if points_id in self._segmented_curves:
            return self._segmented_curves[points_id].get_position_at_frame(frame)

        # Priority 3: Create new segmented curve for gap-aware position lookup
        segmented_curve = SegmentedCurve.from_curve_data(points)

        # Add to cache with LRU eviction
        if len(self._segmented_curves) >= self._max_segmented_cache_size:
            # Remove oldest entry (first key)
            first_key = next(iter(self._segmented_curves))
            del self._segmented_curves[first_key]

        self._segmented_curves[points_id] = segmented_curve
        return segmented_curve.get_position_at_frame(frame)

    def update_curve_data(self, points: CurveDataList) -> None:
        """Update persistent SegmentedCurve and invalidate cache.

        This should be called whenever curve data is modified to ensure:
        1. The restoration system has the latest data structure
        2. The performance cache is invalidated

        Args:
            points: Updated curve data points
        """
        # Update persistent SegmentedCurve for restoration functionality
        self._current_curve_data = points
        if points:
            self._segmented_curve = SegmentedCurve.from_curve_data(points)
        else:
            self._segmented_curve = None

        # Invalidate cache entry for this data object
        points_id = id(points)
        if points_id in self._segmented_curves:
            del self._segmented_curves[points_id]

    def clear_segmented_curve_cache(self) -> None:
        """Clear all cached SegmentedCurve instances.

        Call this when curve data is replaced (e.g., new file loaded).
        """
        self._segmented_curves.clear()

    def handle_point_status_change(self, point_index: int, new_status: str | PointStatus) -> None:
        """Handle point status changes with restoration logic.

        This method should be called when a point's status is changed (e.g., via the E key)
        to ensure proper restoration of tracked data when endframes are converted back to keyframes.

        Args:
            point_index: Index of the point whose status changed
            new_status: New status for the point
        """
        if not self._segmented_curve or not self._current_curve_data:
            logger.warning("Cannot handle status change: no current curve data")
            return

        # Convert status to PointStatus enum if needed
        if isinstance(new_status, str):
            try:
                # Try exact match first, then case-insensitive
                status_enum = PointStatus(new_status)
            except ValueError:
                # Try case-insensitive match
                try:
                    status_enum = PointStatus(new_status.lower())
                except ValueError:
                    logger.warning(f"Invalid status value: {new_status}")
                    return
        else:
            status_enum = new_status

        # Update the persistent SegmentedCurve with restoration logic
        def _update_activity() -> bool:
            if self._segmented_curve is None:
                return False
            self._segmented_curve.update_segment_activity(point_index, status_enum)
            logger.debug(f"Updated segment activity for point {point_index} to {status_enum.value}")
            return True

        safe_execute_optional("updating segment activity", _update_activity, "DataService")

    def aggregate_frame_statuses_for_curves(
        self,
        curve_names: list[str],
    ) -> dict[int, FrameStatus]:
        """Aggregate frame statuses across multiple curves.

        Uses aggregate_frame_statuses() from core.frame_status_aggregator to combine
        status information from multiple curves, following 3DEqualizer's multi-point
        timeline behavior (sum counts, AND for is_inactive, OR for flags).

        Args:
            curve_names: List of curve names to aggregate. Empty list returns empty dict.

        Returns:
            Dict mapping frame numbers to aggregated FrameStatus. Each FrameStatus
            contains summed counts and combined boolean flags across all curves.

        Example:
            >>> service = get_data_service()
            >>> # Aggregate timeline status for all visible curves
            >>> agg_status = service.aggregate_frame_statuses_for_curves(["Track1", "Track2"])
            >>> # agg_status[42] shows combined status at frame 42 across both curves
        """
        from core.frame_status_aggregator import aggregate_frame_statuses
        from stores.application_state import get_application_state

        if not curve_names:
            return {}

        app_state = get_application_state()

        # Collect status data from each curve
        # Structure: frame_statuses[frame][curve_idx] = FrameStatus
        frame_statuses: dict[int, list[FrameStatus]] = {}

        for curve_name in curve_names:
            curve_data = app_state.get_curve_data(curve_name)
            if not curve_data:
                continue

            # Get status for this curve using existing method
            curve_status = self.get_frame_range_point_status(curve_data)

            # Group by frame number
            for frame, status in curve_status.items():
                if frame not in frame_statuses:
                    frame_statuses[frame] = []
                frame_statuses[frame].append(status)

        # Aggregate statuses for each frame
        aggregated: dict[int, FrameStatus] = {}
        for frame, statuses in frame_statuses.items():
            aggregated[frame] = aggregate_frame_statuses(statuses)

        return aggregated

    def get_frame_range_point_status(self, points: CurveDataList) -> dict[int, FrameStatus]:
        """Get comprehensive point status for all frames that have points.

        Args:
            points: List of curve data points to analyze

        Returns:
            Dictionary mapping frame numbers to FrameStatus namedtuples containing:
            (keyframe_count, interpolated_count, tracked_count, endframe_count, normal_count,
             is_startframe, is_inactive, has_selected)
        """
        if not points:
            return {}

        # First pass: collect basic status counts
        frame_status = {}
        endframe_frames: set[int] = set()  # Track which frames have endframes
        # Sort by frame number - handle both tuple and CurvePoint formats
        sorted_points = sorted(points, key=lambda p: (p[0] if isinstance(p, (tuple, list)) and len(p) >= 3 else getattr(p, "frame", 0)))  # pyright: ignore[reportUnnecessaryIsInstance]

        for _i, point in enumerate(sorted_points):
            # Handle both tuple format and CurvePoint objects
            if hasattr(point, "frame"):  # CurvePoint object
                frame = point.frame  # pyright: ignore[reportAttributeAccessIssue]
                if frame not in frame_status:
                    frame_status[frame] = [0, 0, 0, 0, 0, False, False, False]

                status = getattr(point, "status", "normal")
                status_value = status.value if isinstance(status, PointStatus) else str(status)

                if status_value == "interpolated":
                    frame_status[frame][1] += 1
                elif status_value == "keyframe":
                    frame_status[frame][0] += 1
                elif status_value == "tracked":
                    frame_status[frame][2] += 1
                elif status_value == "endframe":
                    frame_status[frame][3] += 1
                    endframe_frames.add(frame)
                else:  # normal
                    frame_status[frame][4] += 1
            elif len(point) >= 3:  # Tuple format (already know it's not CurvePoint from above)
                frame = point[0]
                if frame not in frame_status:
                    # [keyframe, interpolated, tracked, endframe, normal, is_startframe, is_inactive, selected]
                    frame_status[frame] = [0, 0, 0, 0, 0, False, False, False]

                # Check status if available
                # Default to "normal" when status field missing (not "keyframe")
                # This ensures points without explicit status display correctly
                status = point[3] if len(point) > 3 else "normal"
                if isinstance(status, bool):
                    # Legacy boolean format: True = interpolated, False = keyframe
                    if status:
                        frame_status[frame][1] += 1  # interpolated
                    else:
                        frame_status[frame][0] += 1  # keyframe
                # Treat as string or other status type
                elif status == "interpolated":
                    frame_status[frame][1] += 1
                elif status == "keyframe":
                    frame_status[frame][0] += 1
                elif status == "tracked":
                    frame_status[frame][2] += 1
                elif status == "endframe":
                    frame_status[frame][3] += 1
                    endframe_frames.add(frame)
                else:  # normal or unknown
                    frame_status[frame][4] += 1

        # Second pass: detect startframes and inactive regions using SegmentedCurve
        # This provides accurate gap detection and startframe identification
        # Use cached SegmentedCurve if available (single source of truth)
        if self._segmented_curve and self._current_curve_data == points:
            segmented_curve = self._segmented_curve
        else:
            segmented_curve = SegmentedCurve.from_curve_data(points)

        # Get all frame numbers that need to be checked (including gaps)
        if sorted_points:
            min_frame = min(frame_status.keys())
            max_frame = max(frame_status.keys())

            # Check all frames in the range for inactive status
            for frame in range(min_frame, max_frame + 1):
                segment = segmented_curve.get_segment_at_frame(frame)

                # If frame exists in our data, update startframe and inactive status
                if frame in frame_status:
                    # Check if this is a startframe using SegmentedCurve logic
                    if segment and segment.points:
                        # Find the point at this frame
                        frame_point = None
                        for point in segment.points:
                            if point.frame == frame:
                                frame_point = point
                                break

                        if frame_point:
                            # Find previous point for startframe detection
                            prev_point = None
                            for pt in segmented_curve.all_points:
                                if pt.frame < frame and (prev_point is None or pt.frame > prev_point.frame):
                                    prev_point = pt

                            # Use CurvePoint's startframe detection
                            if frame_point.is_startframe(prev_point, segmented_curve.all_points):
                                frame_status[frame][5] = True

                    # Update inactive status based on segment activity
                    # A frame is inactive ONLY if it's in an inactive segment (e.g., tracked points after endframe)
                    # Gaps (segment is None) are NOT inactive, they just have no data
                    is_inactive = segment is not None and not segment.is_active
                    # ENDFRAMES are ALWAYS displayed as active (they're the last active frame before a gap)
                    # Only override if THIS specific frame is an endframe, not just in a segment containing one
                    if frame in endframe_frames and frame_status[frame][3] > 0:  # Has endframe count > 0
                        is_inactive = False
                    frame_status[frame][6] = is_inactive
                else:
                    # Frame has no data at this frame
                    # Check if this frame is in a gap after an endframe
                    is_gap_after_endframe = False

                    # Find the last endframe before this frame
                    last_endframe_frame = None
                    for ef_frame in sorted(endframe_frames, reverse=True):
                        if ef_frame < frame:
                            last_endframe_frame = ef_frame
                            break

                    if last_endframe_frame is not None:
                        # Check if there's any keyframe between the endframe and this frame
                        has_keyframe_between = False
                        for pt in sorted_points:
                            pt_frame = pt[0] if isinstance(pt, (tuple, list)) and len(pt) >= 3 else getattr(pt, "frame", 0)  # pyright: ignore[reportUnnecessaryIsInstance]
                            if last_endframe_frame < pt_frame < frame:
                                pt_status = getattr(pt, "status", "keyframe") if hasattr(pt, "status") else (pt[3] if len(pt) > 3 else "keyframe")
                                if pt_status == "keyframe" or getattr(pt_status, "value", None) == "keyframe":
                                    has_keyframe_between = True
                                    break

                        # Frame is in gap after endframe only if there's no keyframe between endframe and this frame
                        if not has_keyframe_between:
                            is_gap_after_endframe = True

                    if segment and not segment.is_active:
                        # Frame is in an inactive segment
                        frame_status[frame] = [0, 0, 0, 0, 0, False, True, False]
                    elif is_gap_after_endframe:
                        # Frame is in gap after endframe (should be inactive)
                        frame_status[frame] = [0, 0, 0, 0, 0, False, True, False]
                    elif segment and segment.is_active:
                        # Frame is in ACTIVE segment but has no explicit point
                        # This means position is interpolated between keyframes
                        # Set interpolated_count=1 so timeline shows interpolated color
                        frame_status[frame] = [0, 1, 0, 0, 0, False, False, False]
                    else:
                        # Frame is outside all segments (gap between segments)
                        frame_status[frame] = [0, 0, 0, 0, 0, False, False, False]

        # Convert lists to FrameStatus namedtuples
        return {
            frame: FrameStatus(
                keyframe_count=counts[0],
                interpolated_count=counts[1],
                tracked_count=counts[2],
                endframe_count=counts[3],
                normal_count=counts[4],
                is_startframe=counts[5],
                is_inactive=counts[6],
                has_selected=counts[7],
            )
            for frame, counts in frame_status.items()
        }

    def add_track_data(self, data: CurveDataList, label: str = "Track", _color: str = "#FF0000") -> None:
        """Add track data (for compatibility)."""
        if self._status:
            self._status.set_status(f"Added {len(data)} points for '{label}'")

    # ==================== File I/O Delegation ====================

    def load_track_data(self, parent_widget: "QWidget") -> CurveDataList | CurveDataWithMetadata | None:
        """Load track data from file."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Load Track Data",
            self._last_directory,
            "JSON Files (*.json);;CSV Files (*.csv);;Text Files (*.txt);;All Files (*.*)",
        )

        if not file_path:
            return None

        # Update last directory
        self._last_directory = str(Path(file_path).parent)

        if file_path.endswith(".json"):
            return self._load_json(file_path)
        if file_path.endswith(".csv"):
            return self._load_csv(file_path)
        if file_path.endswith(".txt"):
            return self._load_2dtrack_data(file_path)
        # Try to detect format by content - try loaders in sequence
        result = safe_execute_optional(
            "loading as JSON", lambda: self._load_json(file_path), "DataService"
        )
        if result is not None:
            return result

        result = safe_execute_optional(
            "loading as 2D track", lambda: self._load_2dtrack_data(file_path), "DataService"
        )
        if result is not None:
            return result

        # Last resort: try CSV
        return self._load_csv(file_path)

    def save_track_data(
        self, parent_widget: "QWidget", data: CurveDataList, label: str = "Track", color: str = "#FF0000"
    ) -> bool:
        """Save track data to file."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Save Track Data",
            self._last_directory,
            "JSON Files (*.json);;CSV Files (*.csv)",
        )

        if not file_path:
            return False

        # Update last directory
        self._last_directory = str(Path(file_path).parent)

        if file_path.endswith(".json"):
            return self._save_json(file_path, data, label, color)
        return self._save_csv(file_path, data, include_header=True)

    def add_recent_file(self, file_path: str) -> None:
        """Add file to recent files list."""
        # Remove file if it already exists (to move it to front)
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        # Add file to front of list
        self._recent_files.insert(0, file_path)
        self._recent_files = self._recent_files[: self._max_recent_files]

    def get_recent_files(self) -> list[str]:
        """Get list of recent files."""
        return self._recent_files

    # ==================== Image Operation Delegation ====================

    def load_image_sequence(self, directory: str) -> list[str]:
        """Load image sequence from directory and initialize cache.

        Phase 2C: Initializes SafeImageCacheManager with loaded image files
        for efficient on-demand loading with background preloading support.

        Args:
            directory: Path to directory containing image sequence

        Returns:
            List of absolute paths to image files in sequence order
        """

        def _load_sequence() -> list[str] | None:
            path = Path(directory)
            if not path.exists() or not path.is_dir():
                if self._logger:
                    self._logger.log_error(f"Directory does not exist: {directory}")
                return []

            # Common image extensions
            image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".exr"}
            image_files = [
                str(file_path)
                for file_path in sorted(path.iterdir())
                if file_path.is_file() and file_path.suffix.lower() in image_extensions
            ]

            if self._logger and image_files:
                self._logger.log_info(f"Loaded {len(image_files)} images from {directory}")

            # Phase 2C: Initialize cache with image files
            if image_files:
                self._safe_image_cache.set_image_sequence(image_files)
                logger.debug(f"Initialized image cache with {len(image_files)} files")

            return image_files

        result = safe_execute_optional("loading image sequence", _load_sequence, "DataService")
        return result if result is not None else []

    def get_background_image(self, frame: int) -> "QPixmap | None":
        """
        Get background image for frame (cached).

        Phase 2C: Returns QPixmap for direct display use.
        Cache stores QImage; conversion happens here in main thread.

        Args:
            frame: Frame number (0-indexed)

        Returns:
            QPixmap ready for display, or None if frame invalid or load fails

        Note:
            Thread-safe: QImage → QPixmap conversion happens in main thread only.
            This method should be called from main thread.
        """
        from PySide6.QtGui import QPixmap

        qimage = self._safe_image_cache.get_image(frame)
        if qimage:
            # ✅ SAFE: Convert QImage → QPixmap in main thread
            return QPixmap.fromImage(qimage)
        return None

    def preload_around_frame(self, frame: int, window_size: int = 20) -> None:
        """
        Preload frames around current frame (background operation).

        Phase 2C: Triggers background preloading of adjacent frames to
        eliminate first-pass lag during playback.

        Args:
            frame: Center frame for preloading window
            window_size: Number of frames to load before and after (default 20)

        Note:
            Non-blocking operation. Frames load in background QThread.
            Safe to call from main thread during frame changes.
        """
        self._safe_image_cache.preload_around_frame(frame, window_size=window_size)

    def set_current_image_by_frame(self, _view: object, _frame: int) -> None:
        """Set current image by frame number."""
        # No-op implementation for consolidated service

    def load_current_image(self, _view: object) -> "QImage | None":
        """Load current image for view."""
        return None

    def clear_image_cache(self) -> None:
        """Clear the image cache."""
        self._image_cache.clear()

    def _add_to_cache(self, key: str, value: object) -> None:
        """Add an item to the image cache (thread-safe)."""
        with self._lock:
            # Trim cache if it exceeds max size
            if len(self._image_cache) >= self._max_cache_size and self._image_cache:
                # Remove oldest item (first key)
                oldest_key = next(iter(self._image_cache))
                del self._image_cache[oldest_key]
            self._image_cache[key] = value

    def set_cache_size(self, size: int) -> None:
        """Set maximum cache size."""
        self._max_cache_size = size

    def set_image_sequence(self, image_paths: list[str]) -> None:
        """Set the image sequence for the cache manager.

        Args:
            image_paths: List of full paths to image files
        """
        self._safe_image_cache.set_image_sequence(image_paths)

    # ==================== Legacy Methods (Minimal) ====================

    # Keep these minimal legacy methods for compatibility
    def _load_json(self, file_path: str) -> CurveDataList:
        """Load JSON file implementation."""

        def _load() -> CurveDataList | None:
            # FileNotFoundError and JSONDecodeError handled specially
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                if self._logger:
                    self._logger.log_error(f"File not found: {file_path}")
                return []
            except json.JSONDecodeError as e:
                if self._logger:
                    self._logger.log_error(f"Invalid JSON in {file_path}: {e}")
                return []

            # Convert to CurveDataList format
            curve_data: CurveDataList = []

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # Handle different JSON formats
                        frame = item.get("frame", item.get("f", 0))
                        x = item.get("x", item.get("X", 0.0))
                        y = item.get("y", item.get("Y", 0.0))
                        # Only include status if explicitly provided
                        status = item.get("status", item.get("type"))
                        if status:
                            curve_data.append((frame, x, y, status))
                        else:
                            curve_data.append((frame, x, y))
                    elif isinstance(item, list | tuple) and len(item) >= 3:
                        # Handle array format [frame, x, y, ...]
                        frame = item[0]
                        x = float(item[1])
                        y = float(item[2])
                        # Only include status if explicitly provided
                        if len(item) > 3:
                            status = item[3]
                            curve_data.append((frame, x, y, status))
                        else:
                            curve_data.append((frame, x, y))
            elif isinstance(data, dict) and "points" in data:
                # Handle wrapped format {"points": [...], "metadata": {...}}
                points = data["points"]
                for point in points:
                    if isinstance(point, dict):
                        frame = point.get("frame", 0)
                        x = point.get("x", 0.0)
                        y = point.get("y", 0.0)
                        # Only include status if explicitly provided
                        status = point.get("status")
                        if status:
                            curve_data.append((frame, x, y, status))
                        else:
                            curve_data.append((frame, x, y))

            if self._logger:
                self._logger.log_info(f"Loaded {len(curve_data)} points from {file_path}")

            # Apply default status rules
            return self._apply_default_statuses(curve_data)

        result = safe_execute_optional(f"loading JSON from {file_path}", _load, "DataService")
        return result if result is not None else []

    def _save_json(self, file_path: str, data: CurveDataList, label: str, color: str) -> bool:
        """Save JSON file implementation."""

        def _save() -> bool:
            # Convert CurveDataList to JSON format
            points_list: list[dict[str, object]] = []
            json_data: dict[str, object] = {
                "metadata": {"label": label, "color": color, "version": "1.0", "point_count": len(data)},
                "points": points_list,
            }

            for point in data:
                if len(point) >= 3:
                    point_data: dict[str, object] = {"frame": point[0], "x": float(point[1]), "y": float(point[2])}
                    # Add status if available
                    if len(point) > 3:
                        point_data["status"] = point[3]
                    else:
                        point_data["status"] = "keyframe"

                    points_list.append(point_data)

            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)

            if self._logger:
                self._logger.log_info(f"Saved {len(data)} points to {file_path}")

            # Add to recent files
            self.add_recent_file(file_path)

            return True

        return safe_execute(f"saving JSON to {file_path}", _save, "DataService")

    def load_tracked_data(self, file_path: str) -> dict[str, CurveDataList]:
        """Load 2DTrackDatav2 format with multiple tracking points.

        Returns a dictionary where keys are point names and values are trajectories.

        Format for each point:
        - Version number line (e.g., "12")
        - Point name line (e.g., "Point1" or "Point02")
        - Identifier line (e.g., "0")
        - Point count line (e.g., "37")
        - Data lines: frame_number x_coordinate y_coordinate
        """

        def _load() -> dict[str, CurveDataList] | None:
            tracked_data = {}

            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            i = 0
            while i < len(lines):
                # Look for point name lines (e.g., "Point1", "Point02")
                line = lines[i].strip()

                if line.startswith("Point"):
                    # Found a point name
                    point_name = line

                    # Check if we have the required header lines after it
                    if i - 1 >= 0 and i + 2 < len(lines):
                        try:
                            # The format is:
                            # version (line before point name)
                            # point_name (current line)
                            # identifier (next line)
                            # count (line after identifier)
                            _ = lines[i + 1].strip()  # identifier - not used
                            point_count = int(lines[i + 2].strip())

                            # Read the trajectory data starting from i+3
                            trajectory: CurveDataList = []
                            data_start = i + 3

                            for j in range(data_start, min(data_start + point_count, len(lines))):
                                data_line = lines[j].strip()
                                if not data_line:
                                    continue

                                parts = data_line.split()
                                if len(parts) >= 3:
                                    try:
                                        frame = int(parts[0])
                                        x = float(parts[1])
                                        y = float(parts[2])
                                        # Apply Y-flip for 3DEqualizer coordinates (bottom-origin to top-origin)
                                        y = 720 - y
                                        trajectory.append((frame, x, y))
                                    except (ValueError, IndexError):
                                        continue

                            # Store the trajectory with post-processing
                            if trajectory:
                                tracked_data[point_name] = self._apply_default_statuses(trajectory)

                            # Move past this point's data
                            i = data_start + point_count
                            continue

                        except (ValueError, IndexError):
                            pass

                i += 1

            if self._logger:
                self._logger.log_info(f"Loaded {len(tracked_data)} tracking points from {file_path}")

            return tracked_data

        result = safe_execute_optional(f"loading tracked data from {file_path}", _load, "DataService")
        return result if result is not None else {}

    def _load_2dtrack_data(self, file_path: str) -> "CurveDataList | CurveDataWithMetadata":
        """Load 2DTrackData.txt format file (single curve).

        Format:
        Line 1: Version (e.g., "1")
        Line 2: Identifier 1 (e.g., "07")
        Line 3: Identifier 2 (e.g., "0")
        Line 4: Number of points (e.g., "37")
        Lines 5+: frame_number x_coordinate y_coordinate
        """
        from core.coordinate_system import CoordinateMetadata, CoordinateOrigin, CoordinateSystem
        from core.curve_data import CurveDataWithMetadata

        def _create_empty_result() -> CurveDataWithMetadata:
            """Create empty metadata-aware result."""
            metadata = CoordinateMetadata(
                system=CoordinateSystem.THREE_DE_EQUALIZER,
                origin=CoordinateOrigin.BOTTOM_LEFT,
                width=1280,
                height=720,
            )
            return CurveDataWithMetadata(data=[], metadata=metadata)

        def _load() -> CurveDataWithMetadata | None:
            # Handle FileNotFoundError specially
            try:
                with open(file_path, encoding="utf-8") as f:
                    lines = f.readlines()
            except FileNotFoundError:
                if self._logger:
                    self._logger.log_error(f"File not found: {file_path}")
                return _create_empty_result()

            curve_data: CurveDataList = []

            # Skip the 4-line header
            if len(lines) > 4:
                # Parse data lines starting from line 5 (index 4)
                for line_num, line in enumerate(lines[4:], start=5):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            frame = int(parts[0])
                            x = float(parts[1])
                            y = float(parts[2])
                            # Store raw coordinates - metadata system handles Y-flip

                            # Optional status field - only include if explicitly provided
                            if len(parts) >= 4:
                                status = parts[3]
                                curve_data.append((frame, x, y, status))
                            else:
                                curve_data.append((frame, x, y))

                        except (ValueError, IndexError) as e:
                            if self._logger:
                                self._logger.log_error(f"Invalid data at line {line_num}: {e}")
                            continue

            # Apply default status rules
            result = self._apply_default_statuses(curve_data)

            if self._logger:
                self._logger.log_info(f"Loaded {len(result)} points from {file_path}")

            # Wrap with 3DEqualizer metadata for coordinate system awareness
            metadata = CoordinateMetadata(
                system=CoordinateSystem.THREE_DE_EQUALIZER,
                origin=CoordinateOrigin.BOTTOM_LEFT,
                width=1280,  # 3DE default
                height=720,  # 3DE default
            )

            return CurveDataWithMetadata(data=result, metadata=metadata)

        result = safe_execute_optional(f"loading 2DTrackData from {file_path}", _load, "DataService")
        return result if result is not None else _create_empty_result()

    def _load_csv(self, file_path: str) -> CurveDataList:
        """Load CSV file implementation."""

        def _load() -> CurveDataList | None:
            # Handle FileNotFoundError specially
            try:
                with open(file_path, encoding="utf-8", newline="") as f:
                    # Try to detect delimiter
                    sample = f.read(1024)
                    _ = f.seek(0)

                    delimiter = ","
                    if "\t" in sample and sample.count("\t") > sample.count(","):
                        delimiter = "\t"
                    elif ";" in sample and sample.count(";") > sample.count(","):
                        delimiter = ";"

                    reader = csv.reader(f, delimiter=delimiter)

                    # Skip header if present
                    first_row = next(reader, None)
                    if first_row:
                        # Check if first row looks like a header
                        try:
                            # Try to convert first column to number
                            _ = float(first_row[0])
                            # If successful, this is data, not header
                            _ = f.seek(0)
                            reader = csv.reader(f, delimiter=delimiter)
                        except (ValueError, IndexError):
                            # First row is likely a header, continue from next row
                            pass

                    curve_data: CurveDataList = []
                    for row_num, row in enumerate(reader, 1):
                        if len(row) < 3:
                            continue

                        try:
                            frame = int(float(row[0]))  # Allow float input, convert to int
                            x = float(row[1])
                            y = float(row[2])

                            # Optional status column - only include if explicitly provided
                            if len(row) > 3 and row[3].strip():
                                status = row[3].strip()
                                curve_data.append((frame, x, y, status))
                            else:
                                curve_data.append((frame, x, y))

                        except (ValueError, IndexError) as e:
                            if self._logger:
                                self._logger.log_error(f"Invalid data at row {row_num}: {e}")
                            continue

            except FileNotFoundError:
                if self._logger:
                    self._logger.log_error(f"File not found: {file_path}")
                return []

            if self._logger:
                self._logger.log_info(f"Loaded {len(curve_data)} points from {file_path}")

            # Apply default status rules
            return self._apply_default_statuses(curve_data)

        result = safe_execute_optional(f"loading CSV from {file_path}", _load, "DataService")
        return result if result is not None else []

    def _save_csv(self, file_path: str, data: CurveDataList, include_header: bool = True) -> bool:
        """Save CSV file implementation."""

        def _save() -> bool:
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)

                # Write header if requested
                if include_header:
                    writer.writerow(["frame", "x", "y", "status"])

                # Write data
                for point in data:
                    if len(point) >= 3:
                        row: list[object] = [point[0], point[1], point[2]]
                        # Add status if available
                        if len(point) > 3:
                            row.append(point[3])
                        else:
                            row.append("keyframe")

                        writer.writerow(row)

            if self._logger:
                self._logger.log_info(f"Saved {len(data)} points to {file_path}")

            # Add to recent files
            self.add_recent_file(file_path)

            return True

        return safe_execute(f"saving CSV to {file_path}", _save, "DataService")

    def _apply_default_statuses(self, curve_data: CurveDataList) -> CurveDataList:
        """Apply default status rules to loaded curve data.

        Rules:
        1. First frame becomes "keyframe"
        2. First frame after a gap becomes "keyframe" (startframe)
        3. Last frame becomes "keyframe"
        4. Frames before gaps (>1 frame jump) become "endframe"
        5. All other frames default to "tracked" status

        Args:
            curve_data: Raw curve data with potentially inconsistent statuses

        Returns:
            Processed curve data with consistent default statuses
        """
        if not curve_data:
            return curve_data

        # Convert to list and sort by frame
        processed_data: CurveDataList = []
        sorted_data = sorted(curve_data, key=lambda p: p[0])

        for i, point in enumerate(sorted_data):
            frame, x, y = point[0], point[1], point[2]

            # Check if status was explicitly provided and is valid
            explicit_status = None
            if len(point) > 3 and point[3] in ["normal", "interpolated", "keyframe", "tracked", "endframe"]:
                explicit_status = point[3]

            # Apply default rules if no explicit status
            if explicit_status is None:
                # Check if this is the first frame
                if i == 0:
                    status = "keyframe"
                # Check if this is the first frame after a gap
                elif i > 0:
                    prev_frame = sorted_data[i - 1][0]
                    if frame - prev_frame > 1 or i == len(sorted_data) - 1:  # Gap detected before this frame
                        status = "keyframe"
                    # Check if this is the last frame before a gap
                    elif i < len(sorted_data) - 1:
                        next_frame = sorted_data[i + 1][0]
                        status = "endframe" if next_frame - frame > 1 else "tracked"
                    else:
                        status = "tracked"
                else:
                    status = "tracked"
            else:
                # Use the explicit status
                status = explicit_status

            processed_data.append((frame, x, y, status))

        if self._logger:
            self._logger.log_info(f"Applied default statuses to {len(processed_data)} points")

        return processed_data


# Singleton instance is managed by services/__init__.py
# Removed duplicate get_data_service() to avoid multiple singleton instances
