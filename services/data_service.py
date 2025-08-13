#!/usr/bin/env python
"""
Refactored DataService for CurveEditor.

This service focuses on data analysis operations while delegating:
- File I/O operations to FileIOService
- Image operations to ImageSequenceService
"""

import csv
import json
import logging
import os
import statistics
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.type_aliases import CurveDataList
from services.file_io_service import FileIOService
from services.image_sequence_service import ImageSequenceService
from services.service_protocols import LoggingServiceProtocol, StatusServiceProtocol

if TYPE_CHECKING:
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QWidget

logger = logging.getLogger("data_service")


class DataService:
    """
    Refactored service for data analysis operations.

    This service handles:
    - Curve data analysis (smoothing, filtering, gap filling, outlier detection)
    - Delegates file I/O to FileIOService
    - Delegates image operations to ImageSequenceService
    """

    def __init__(
        self,
        logging_service: LoggingServiceProtocol | None = None,
        status_service: StatusServiceProtocol | None = None,
    ) -> None:
        """Initialize DataService with optional dependencies."""
        self._lock = threading.RLock()
        self._logger = logging_service
        self._status = status_service

        # Initialize delegate services
        use_new = os.environ.get("USE_NEW_SERVICES", "false").lower() == "true"
        self._file_io = FileIOService() if use_new else None
        self._image = ImageSequenceService() if use_new else None

        # Legacy state (only if not using new services)
        if not use_new:
            self._recent_files: list[str] = []
            self._max_recent_files: int = 10  # Maximum number of recent files to keep
            self._last_directory: str = ""
            self._image_cache: dict = {}
            self._max_cache_size: int = 100  # Maximum number of cached images

    # ==================== Core Analysis Methods ====================

    def smooth_moving_average(self, data: CurveDataList, window_size: int = 5) -> CurveDataList:
        """Apply moving average smoothing to curve data."""
        if len(data) < window_size:
            return data

        result = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]

            avg_x = sum(p[1] for p in window) / len(window)
            avg_y = sum(p[2] for p in window) / len(window)

            # Preserve frame and additional data
            if len(data[i]) > 3:
                result.append((data[i][0], avg_x, avg_y) + data[i][3:])
            else:
                result.append((data[i][0], avg_x, avg_y))

        if self._status:
            self._status.show_status(f"Applied moving average (window={window_size})")
        return result

    def filter_median(self, data: CurveDataList, window_size: int = 5) -> CurveDataList:
        """Apply median filter to curve data."""
        if len(data) < window_size:
            return data

        result = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]

            med_x = statistics.median(p[1] for p in window)
            med_y = statistics.median(p[2] for p in window)

            if len(data[i]) > 3:
                result.append((data[i][0], med_x, med_y) + data[i][3:])
            else:
                result.append((data[i][0], med_x, med_y))

        if self._status:
            self._status.show_status(f"Applied median filter (window={window_size})")
        return result

    def filter_butterworth(self, data: CurveDataList, cutoff: float = 0.1, order: int = 2) -> CurveDataList:
        """Apply Butterworth low-pass filter using scipy."""
        try:
            from scipy import signal

            if len(data) < 4:
                return data

            frames = [p[0] for p in data]
            x_coords = [p[1] for p in data]
            y_coords = [p[2] for p in data]

            # Design and apply filter
            b, a = signal.butter(order, cutoff, btype='low')
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
                self._status.show_status("Applied Butterworth filter")
            return result

        except ImportError:
            if self._logger:
                self._logger.log_error("scipy not available")
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
                if (std_vx > 0 and abs(vx - mean_vx) > threshold * std_vx) or \
                   (std_vy > 0 and abs(vy - mean_vy) > threshold * std_vy):
                    outliers.append(i + 1)

        if self._logger and outliers:
            self._logger.log_info(f"Detected {len(outliers)} outliers")
        return outliers

    def add_track_data(self, data: CurveDataList, label: str = "Track", color: str = "#FF0000") -> None:
        """Add track data (for compatibility)."""
        if self._status:
            self._status.show_status(f"Added {len(data)} points for '{label}'")

    # ==================== File I/O Delegation ====================

    def load_track_data(self, parent_widget: "QWidget") -> CurveDataList | None:
        """Load track data from file."""
        if not self._file_io:
            return self._load_track_data_legacy(parent_widget)

        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget, "Load Track Data",
            self._file_io.get_last_directory(),
            "JSON Files (*.json);;CSV Files (*.csv);;All Files (*.*)"
        )

        if not file_path:
            return None

        if file_path.endswith(".json"):
            return self._file_io.load_json(file_path)
        elif file_path.endswith(".csv"):
            return self._file_io.load_csv(file_path)
        else:
            # Try JSON first, then CSV
            try:
                return self._file_io.load_json(file_path)
            except Exception:
                return self._file_io.load_csv(file_path)

    def save_track_data(self, parent_widget: "QWidget", data: CurveDataList,
                       label: str = "Track", color: str = "#FF0000") -> bool:
        """Save track data to file."""
        if not self._file_io:
            return self._save_track_data_legacy(parent_widget, data, label, color)

        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget, "Save Track Data",
            self._file_io.get_last_directory(),
            "JSON Files (*.json);;CSV Files (*.csv)"
        )

        if not file_path:
            return False

        if file_path.endswith(".json"):
            return self._file_io.save_json(file_path, data, label, color)
        else:
            return self._file_io.save_csv(file_path, data, include_header=True)

    def add_recent_file(self, file_path: str) -> None:
        """Add file to recent files list."""
        if self._file_io:
            self._file_io.add_recent_file(file_path)
        elif hasattr(self, "_recent_files"):
            if file_path not in self._recent_files:
                self._recent_files.insert(0, file_path)
                max_files = getattr(self, "_max_recent_files", 10)
                self._recent_files = self._recent_files[:max_files]

    def get_recent_files(self) -> list[str]:
        """Get list of recent files."""
        if self._file_io:
            return self._file_io.get_recent_files()
        return getattr(self, "_recent_files", [])

    # ==================== Image Operation Delegation ====================

    def load_image_sequence(self, directory: str) -> list[str]:
        """Load image sequence from directory."""
        if self._image:
            return self._image.load_image_sequence(directory)

        # Fallback implementation
        try:
            path = Path(directory)
            if not path.exists() or not path.is_dir():
                if self._logger:
                    self._logger.log_error(f"Directory does not exist: {directory}")
                return []

            # Common image extensions
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
            image_files = []

            for file_path in sorted(path.iterdir()):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    image_files.append(str(file_path))

            if self._logger and image_files:
                self._logger.log_info(f"Loaded {len(image_files)} images from {directory}")

            return image_files

        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to load image sequence: {e}")
            return []

    def set_current_image_by_frame(self, view: Any, frame: int) -> None:
        """Set current image by frame number."""
        if self._image:
            self._image.set_current_image_by_frame(view, frame)

    def load_current_image(self, view: Any) -> "QImage | None":
        """Load current image for view."""
        if self._image:
            return self._image.load_current_image(view)
        return None

    def clear_image_cache(self) -> None:
        """Clear the image cache."""
        if self._image:
            self._image.clear_cache()
        elif hasattr(self, "_image_cache"):
            self._image_cache.clear()

    def _add_to_cache(self, key: str, value: Any) -> None:
        """Add an item to the image cache (thread-safe)."""
        with self._lock:
            if hasattr(self, "_image_cache"):
                # Trim cache if it exceeds max size
                if len(self._image_cache) >= getattr(self, "_max_cache_size", 100):
                    # Remove oldest item (first key)
                    if self._image_cache:
                        oldest_key = next(iter(self._image_cache))
                        del self._image_cache[oldest_key]
                self._image_cache[key] = value

    def set_cache_size(self, size: int) -> None:
        """Set maximum cache size."""
        if self._image:
            self._image.set_cache_size(size)

    # ==================== Legacy Methods (Minimal) ====================

    def _load_track_data_legacy(self, parent_widget: "QWidget") -> CurveDataList | None:
        """Legacy load implementation."""
        # Minimal legacy implementation
        return None

    def _save_track_data_legacy(self, parent_widget: "QWidget", data: CurveDataList,
                               label: str, color: str) -> bool:
        """Legacy save implementation."""
        # Minimal legacy implementation
        return False

    # Keep these minimal legacy methods for compatibility
    def _load_json(self, file_path: str) -> CurveDataList:
        """Legacy JSON load (delegates if possible)."""
        if self._file_io:
            return self._file_io.load_json(file_path)

        # Fallback implementation
        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)

            # Convert to CurveDataList format
            curve_data = []

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # Handle different JSON formats
                        frame = item.get('frame', item.get('f', 0))
                        x = item.get('x', item.get('X', 0.0))
                        y = item.get('y', item.get('Y', 0.0))
                        status = item.get('status', item.get('type', 'keyframe'))
                        curve_data.append((frame, x, y, status))
                    elif isinstance(item, list | tuple) and len(item) >= 3:
                        # Handle array format [frame, x, y, ...]
                        frame = item[0]
                        x = float(item[1])
                        y = float(item[2])
                        status = item[3] if len(item) > 3 else 'keyframe'
                        curve_data.append((frame, x, y, status))
            elif isinstance(data, dict) and 'points' in data:
                # Handle wrapped format {"points": [...], "metadata": {...}}
                points = data['points']
                for point in points:
                    if isinstance(point, dict):
                        frame = point.get('frame', 0)
                        x = point.get('x', 0.0)
                        y = point.get('y', 0.0)
                        status = point.get('status', 'keyframe')
                        curve_data.append((frame, x, y, status))

            if self._logger:
                self._logger.log_info(f"Loaded {len(curve_data)} points from {file_path}")

            return curve_data

        except FileNotFoundError:
            if self._logger:
                self._logger.log_error(f"File not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            if self._logger:
                self._logger.log_error(f"Invalid JSON in {file_path}: {e}")
            return []
        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to load JSON file {file_path}: {e}")
            return []

    def _save_json(self, file_path: str, data: CurveDataList, label: str, color: str) -> bool:
        """Legacy JSON save (delegates if possible)."""
        if self._file_io:
            return self._file_io.save_json(file_path, data, label, color)

        # Fallback implementation
        try:
            # Convert CurveDataList to JSON format
            json_data = {
                "metadata": {
                    "label": label,
                    "color": color,
                    "version": "1.0",
                    "point_count": len(data)
                },
                "points": []
            }

            for point in data:
                if len(point) >= 3:
                    point_data = {
                        "frame": point[0],
                        "x": float(point[1]),
                        "y": float(point[2])
                    }
                    # Add status if available
                    if len(point) > 3:
                        point_data["status"] = point[3]
                    else:
                        point_data["status"] = "keyframe"

                    json_data["points"].append(point_data)

            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2)

            if self._logger:
                self._logger.log_info(f"Saved {len(data)} points to {file_path}")

            # Add to recent files
            self.add_recent_file(file_path)

            return True

        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to save JSON file {file_path}: {e}")
            return False

    def _load_csv(self, file_path: str) -> CurveDataList:
        """Legacy CSV load (delegates if possible)."""
        if self._file_io:
            return self._file_io.load_csv(file_path)

        # Fallback implementation
        try:
            curve_data = []

            with open(file_path, encoding='utf-8', newline='') as f:
                # Try to detect delimiter
                sample = f.read(1024)
                f.seek(0)

                delimiter = ','
                if '\t' in sample and sample.count('\t') > sample.count(','):
                    delimiter = '\t'
                elif ';' in sample and sample.count(';') > sample.count(','):
                    delimiter = ';'

                reader = csv.reader(f, delimiter=delimiter)

                # Skip header if present
                first_row = next(reader, None)
                if first_row:
                    # Check if first row looks like a header
                    try:
                        # Try to convert first column to number
                        float(first_row[0])
                        # If successful, this is data, not header
                        f.seek(0)
                        reader = csv.reader(f, delimiter=delimiter)
                    except (ValueError, IndexError):
                        # First row is likely a header, continue from next row
                        pass

                for row_num, row in enumerate(reader, 1):
                    if len(row) < 3:
                        continue

                    try:
                        frame = int(float(row[0]))  # Allow float input, convert to int
                        x = float(row[1])
                        y = float(row[2])

                        # Optional status column
                        status = 'keyframe'
                        if len(row) > 3 and row[3].strip():
                            status = row[3].strip()

                        curve_data.append((frame, x, y, status))

                    except (ValueError, IndexError) as e:
                        if self._logger:
                            self._logger.log_error(f"Invalid data at row {row_num}: {e}")
                        continue

            if self._logger:
                self._logger.log_info(f"Loaded {len(curve_data)} points from {file_path}")

            return curve_data

        except FileNotFoundError:
            if self._logger:
                self._logger.log_error(f"File not found: {file_path}")
            return []
        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to load CSV file {file_path}: {e}")
            return []

    def _save_csv(self, file_path: str, data: CurveDataList, include_header: bool = True) -> bool:
        """Legacy CSV save (delegates if possible)."""
        if self._file_io:
            return self._file_io.save_csv(file_path, data, include_header)

        # Fallback implementation
        try:
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)

                # Write header if requested
                if include_header:
                    writer.writerow(['frame', 'x', 'y', 'status'])

                # Write data
                for point in data:
                    if len(point) >= 3:
                        row = [point[0], point[1], point[2]]
                        # Add status if available
                        if len(point) > 3:
                            row.append(point[3])
                        else:
                            row.append('keyframe')

                        writer.writerow(row)

            if self._logger:
                self._logger.log_info(f"Saved {len(data)} points to {file_path}")

            # Add to recent files
            self.add_recent_file(file_path)

            return True

        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to save CSV file {file_path}: {e}")
            return False


# Module-level instance
_data_service: DataService | None = None


def get_data_service() -> DataService:
    """Get the singleton DataService instance."""
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service

