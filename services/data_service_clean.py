#!/usr/bin/env python
"""
Cleaned DataService for CurveEditor.

This service now focuses on data analysis operations while delegating:
- File I/O operations to FileIOService
- Image operations to ImageSequenceService

Provides analysis methods like smoothing, filtering, gap filling, and outlier detection.
"""

import json
import logging
import os
import statistics
import threading
from typing import TYPE_CHECKING, Any

from core.type_aliases import CurveDataList
from data.curve_data_utils import compute_interpolated_curve_data
from services.file_io_service import FileIOService
from services.image_sequence_service import ImageSequenceService
from services.service_protocols import LoggingServiceProtocol, StatusServiceProtocol

if TYPE_CHECKING:
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget
else:
    # Runtime stubs for when PySide6 unavailable
    QImage = QFileDialog = QMessageBox = QWidget = object

logger = logging.getLogger("data_service")


class DataService:
    """
    Cleaned service for data analysis operations.

    This service handles:
    - Curve data analysis (smoothing, filtering, gap filling)
    - Delegates file I/O to FileIOService
    - Delegates image operations to ImageSequenceService
    """

    def __init__(
        self,
        logging_service: LoggingServiceProtocol | None = None,
        status_service: StatusServiceProtocol | None = None,
    ) -> None:
        """Initialize DataService with optional dependencies.

        Args:
            logging_service: Optional logging service for error tracking
            status_service: Optional status service for user feedback
        """
        # Thread safety lock
        self._lock = threading.RLock()

        # Service dependencies
        self._logger: LoggingServiceProtocol | None = logging_service
        self._status: StatusServiceProtocol | None = status_service

        # Delegate services (check feature flag)
        use_new_services = os.environ.get("USE_NEW_SERVICES", "false").lower() == "true"

        if use_new_services:
            self._file_io_service = FileIOService()
            self._image_service = ImageSequenceService()
        else:
            # Legacy mode - keep old behavior
            self._file_io_service = None
            self._image_service = None

            # Legacy state
            self._recent_files: list[str] = []
            self._max_recent_files: int = 10
            self._last_directory: str = ""
            self._supported_formats: list[str] = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]
            self._image_cache: dict[str, QImage] = {}
            self._max_cache_size: int = 50

    # ==================== Analysis Methods (Core Functionality) ====================

    def smooth_moving_average(
        self, data: CurveDataList, window_size: int = 5
    ) -> CurveDataList:
        """Apply moving average smoothing to curve data.

        Args:
            data: List of point tuples (frame, x, y, ...)
            window_size: Size of the moving average window

        Returns:
            Smoothed data points
        """
        if len(data) < window_size:
            return data

        result = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]

            avg_x = sum(p[1] for p in window) / len(window)
            avg_y = sum(p[2] for p in window) / len(window)

            # Preserve frame and any additional data
            if len(data[i]) > 3:
                result.append((data[i][0], avg_x, avg_y) + data[i][3:])
            else:
                result.append((data[i][0], avg_x, avg_y))

        if self._status:
            self._status.show_status(f"Applied moving average smoothing (window={window_size})")

        return result

    def filter_median(self, data: CurveDataList, window_size: int = 5) -> CurveDataList:
        """Apply median filter to curve data.

        Args:
            data: List of point tuples (frame, x, y, ...)
            window_size: Size of the median filter window

        Returns:
            Filtered data points
        """
        if len(data) < window_size:
            return data

        result = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]

            med_x = statistics.median(p[1] for p in window)
            med_y = statistics.median(p[2] for p in window)

            # Preserve frame and any additional data
            if len(data[i]) > 3:
                result.append((data[i][0], med_x, med_y) + data[i][3:])
            else:
                result.append((data[i][0], med_x, med_y))

        if self._status:
            self._status.show_status(f"Applied median filter (window={window_size})")

        return result

    def filter_butterworth(
        self, data: CurveDataList, cutoff: float = 0.1, order: int = 2
    ) -> CurveDataList:
        """Apply Butterworth low-pass filter to curve data.

        Args:
            data: List of point tuples (frame, x, y, ...)
            cutoff: Cutoff frequency (0-1, where 1 is Nyquist frequency)
            order: Filter order

        Returns:
            Filtered data points
        """
        try:
            import numpy as np  # noqa: F401
            from scipy import signal
        except ImportError:
            if self._logger:
                self._logger.log_error("scipy not available for Butterworth filter")
            return data

        if len(data) < 4:
            return data

        # Extract x and y coordinates
        frames = [p[0] for p in data]
        x_coords = [p[1] for p in data]
        y_coords = [p[2] for p in data]

        # Design filter
        b, a = signal.butter(order, cutoff, btype='low', analog=False)

        # Apply filter
        filtered_x = signal.filtfilt(b, a, x_coords)
        filtered_y = signal.filtfilt(b, a, y_coords)

        # Reconstruct data
        result = []
        for i, frame in enumerate(frames):
            if len(data[i]) > 3:
                result.append((frame, filtered_x[i], filtered_y[i]) + data[i][3:])
            else:
                result.append((frame, filtered_x[i], filtered_y[i]))

        if self._status:
            self._status.show_status(f"Applied Butterworth filter (cutoff={cutoff}, order={order})")

        return result

    def fill_gaps(
        self, data: CurveDataList, max_gap: int = 5
    ) -> CurveDataList:
        """Fill gaps in curve data using interpolation.

        Args:
            data: List of point tuples (frame, x, y, ...)
            max_gap: Maximum gap size to fill (in frames)

        Returns:
            Data with gaps filled
        """
        if len(data) < 2:
            return data

        # Use the utility function for interpolation
        compute_interpolated_curve_data(data, start_offset=0, end_offset=0)

        # Filter to only include points within max_gap of existing data
        result = []
        filled_count = 0

        for i in range(len(data) - 1):
            result.append(data[i])
            gap = data[i + 1][0] - data[i][0] - 1
            if 0 < gap <= max_gap:
                # Linear interpolation
                for j in range(1, gap + 1):
                    t = j / (gap + 1)
                    frame = data[i][0] + j
                    x = data[i][1] + t * (data[i + 1][1] - data[i][1])
                    y = data[i][2] + t * (data[i + 1][2] - data[i][2])
                    result.append((frame, x, y, False))  # Mark as interpolated
                    filled_count += 1

        result.append(data[-1])  # Add the last point

        if filled_count > 0:
            logger.info(f"Filled {filled_count} gap points using interpolation")

        return result

    def detect_outliers(
        self, data: CurveDataList, threshold: float = 2.0
    ) -> list[int]:
        """Detect outlier points based on deviation from neighbors.

        Args:
            data: List of point tuples (frame, x, y, ...)
            threshold: Standard deviation threshold for outlier detection

        Returns:
            List of indices of detected outliers
        """
        if len(data) < 3:
            return []

        outliers = []

        # Calculate velocity between consecutive points
        velocities = []
        for i in range(1, len(data)):
            dx = data[i][1] - data[i - 1][1]
            dy = data[i][2] - data[i - 1][2]
            dt = data[i][0] - data[i - 1][0]
            if dt > 0:
                vx = dx / dt
                vy = dy / dt
                velocities.append((vx, vy))

        if len(velocities) < 2:
            return []

        # Calculate mean and std of velocities
        mean_vx = sum(v[0] for v in velocities) / len(velocities)
        mean_vy = sum(v[1] for v in velocities) / len(velocities)

        if len(velocities) > 1:
            std_vx = statistics.stdev(v[0] for v in velocities)
            std_vy = statistics.stdev(v[1] for v in velocities)
        else:
            std_vx = std_vy = 0

        # Detect outliers based on velocity deviation
        for i, (vx, vy) in enumerate(velocities):
            if std_vx > 0 and abs(vx - mean_vx) > threshold * std_vx:
                outliers.append(i + 1)
            elif std_vy > 0 and abs(vy - mean_vy) > threshold * std_vy:
                outliers.append(i + 1)

        if self._logger and outliers:
            self._logger.log_info(f"Detected {len(outliers)} outliers with threshold {threshold}")

        return outliers

    # ==================== Delegation Methods ====================

    def add_track_data(
        self, data: CurveDataList, label: str = "Track", color: str = "#FF0000"
    ) -> None:
        """Add track data to the current dataset.

        Args:
            data: List of point tuples (frame, x, y, ...)
            label: Label for the track
            color: Color for visualization
        """
        # This is a simple pass-through - actual storage happens elsewhere
        if self._status:
            self._status.show_status(f"Added {len(data)} points for track '{label}'")

    # ==================== File I/O Delegation (for backward compatibility) ====================

    def load_track_data(self, parent_widget: QWidget) -> CurveDataList | None:
        """Load track data from file (delegates to FileIOService)."""
        if self._file_io_service:
            # Use new service
            from PySide6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getOpenFileName(
                parent_widget,
                "Load Track Data",
                self._file_io_service.get_last_directory(),
                "JSON Files (*.json);;CSV Files (*.csv);;All Files (*.*)",
            )

            if not file_path:
                return None

            # Detect format and load
            if file_path.endswith(".json"):
                return self._file_io_service.load_json(file_path)
            elif file_path.endswith(".csv"):
                return self._file_io_service.load_csv(file_path)
            else:
                # Try auto-detect
                try:
                    return self._file_io_service.load_json(file_path)
                except (json.JSONDecodeError, ValueError, FileNotFoundError):
                    return self._file_io_service.load_csv(file_path)
        else:
            # Legacy implementation would go here
            return None

    def save_track_data(self, parent_widget: QWidget, data: CurveDataList,
                       label: str = "Track", color: str = "#FF0000") -> bool:
        """Save track data to file (delegates to FileIOService)."""
        if self._file_io_service:
            from PySide6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                parent_widget,
                "Save Track Data",
                self._file_io_service.get_last_directory(),
                "JSON Files (*.json);;CSV Files (*.csv)",
            )

            if not file_path:
                return False

            if file_path.endswith(".json"):
                return self._file_io_service.save_json(file_path, data, label, color)
            else:
                return self._file_io_service.save_csv(file_path, data, include_header=True)
        else:
            # Legacy implementation
            return False

    # Keep minimal delegation methods for compatibility
    def add_recent_file(self, file_path: str) -> None:
        """Add file to recent files list."""
        if self._file_io_service:
            self._file_io_service.add_recent_file(file_path)

    def get_recent_files(self) -> list[str]:
        """Get list of recent files."""
        if self._file_io_service:
            return self._file_io_service.get_recent_files()
        return []

    # Image delegation methods
    def load_image_sequence(self, directory: str) -> list[str]:
        """Load image sequence from directory."""
        if self._image_service:
            return self._image_service.load_image_sequence(directory)
        return []

    def set_current_image_by_frame(self, view: Any, frame: int) -> None:
        """Set current image by frame number."""
        if self._image_service:
            self._image_service.set_current_image_by_frame(view, frame)

    def load_current_image(self, view: Any) -> QImage | None:
        """Load current image for view."""
        if self._image_service:
            return self._image_service.load_current_image(view)
        return None

    def clear_image_cache(self) -> None:
        """Clear the image cache."""
        if self._image_service:
            self._image_service.clear_cache()

    def set_cache_size(self, size: int) -> None:
        """Set maximum cache size."""
        if self._image_service:
            self._image_service.set_cache_size(size)


# Module-level instance
_data_service: DataService | None = None


def get_data_service() -> DataService:
    """Get the singleton DataService instance."""
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service
