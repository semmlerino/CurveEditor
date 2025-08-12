#!/usr/bin/env python
"""
Consolidated DataService for CurveEditor.

This service merges functionality from:
- curve_service.py: Analysis methods (smooth, filter, fill_gaps, detect_outliers)
- file_service.py: File I/O operations (JSON/CSV load/save)
- image_service.py: Image loading and manipulation

Provides a unified interface for all data operations including analysis,
file I/O, and image management.
"""

import csv
import json
import logging
import os
import statistics
from pathlib import Path
from typing import Any

from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from services.service_protocols import LoggingServiceProtocol, StatusServiceProtocol

logger = logging.getLogger("data_service")


class DataService:
    """
    Consolidated service for all data operations.
    
    This service handles:
    - Curve data analysis (smoothing, filtering, gap filling)
    - File I/O operations (JSON/CSV loading and saving)
    - Image sequence management
    """
    
    def __init__(
        self,
        logging_service: LoggingServiceProtocol | None = None,
        status_service: StatusServiceProtocol | None = None,
    ):
        """Initialize DataService with optional dependencies.
        
        Args:
            logging_service: Optional logging service for error tracking
            status_service: Optional status service for user feedback
        """
        self._logger = logging_service
        self._status = status_service
        
        # File service state
        self._recent_files: list[str] = []
        self._max_recent_files = 10
        self._last_directory = ""
        
        # Image service state
        self._supported_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
        self._image_cache: dict[str, QImage] = {}
        self._max_cache_size = 50
        
        # Load recent files from config if available
        self._load_recent_files()
    
    # ==================== Analysis Methods (from curve_service) ====================
    
    def smooth_moving_average(self, data: list[tuple], window_size: int = 5) -> list[tuple]:
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
            result.append((data[i][0], avg_x, avg_y, *data[i][3:]))
        
        if self._logger:
            self._logger.log_info(f"Applied moving average smoothing with window size {window_size}")
        
        return result
    
    def filter_median(self, data: list[tuple], window_size: int = 5) -> list[tuple]:
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
            result.append((data[i][0], med_x, med_y, *data[i][3:]))
        
        if self._logger:
            self._logger.log_info(f"Applied median filter with window size {window_size}")
        
        return result
    
    def filter_butterworth(self, data: list[tuple], cutoff: float = 0.1) -> list[tuple]:
        """Apply simple low-pass filter (simplified butterworth).
        
        Args:
            data: List of point tuples (frame, x, y, ...)
            cutoff: Cutoff frequency (0.0 to 1.0)
        
        Returns:
            Filtered data points
        """
        if len(data) < 2:
            return data
        
        result = [data[0]]
        alpha = cutoff
        for i in range(1, len(data)):
            filtered_x = alpha * data[i][1] + (1 - alpha) * result[-1][1]
            filtered_y = alpha * data[i][2] + (1 - alpha) * result[-1][2]
            result.append((data[i][0], filtered_x, filtered_y, *data[i][3:]))
        
        if self._logger:
            self._logger.log_info(f"Applied butterworth filter with cutoff {cutoff}")
        
        return result
    
    def fill_gaps(self, data: list[tuple], max_gap: int = 10) -> list[tuple]:
        """Fill gaps in curve data with linear interpolation.
        
        Args:
            data: List of point tuples (frame, x, y, ...)
            max_gap: Maximum gap size to fill with interpolation
        
        Returns:
            Data with gaps filled
        """
        if len(data) < 2:
            return data
        
        result = []
        filled_count = 0
        
        for i in range(len(data) - 1):
            result.append(data[i])
            gap = data[i+1][0] - data[i][0] - 1
            if 0 < gap <= max_gap:
                # Linear interpolation
                for j in range(1, gap + 1):
                    t = j / (gap + 1)
                    frame = data[i][0] + j
                    x = data[i][1] + t * (data[i+1][1] - data[i][1])
                    y = data[i][2] + t * (data[i+1][2] - data[i][2])
                    result.append((frame, x, y, False))  # Mark as interpolated
                    filled_count += 1
        
        result.append(data[-1])
        
        if self._logger:
            self._logger.log_info(f"Filled {filled_count} gaps with max gap size {max_gap}")
        
        if self._status and filled_count > 0:
            self._status.show_info(f"Filled {filled_count} gaps")
        
        return result
    
    def detect_outliers(self, data: list[tuple], threshold: float = 2.0) -> list[int]:
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
            dx = data[i][1] - data[i-1][1]
            dy = data[i][2] - data[i-1][2]
            dt = data[i][0] - data[i-1][0]
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
    
    # ==================== File I/O Methods (from file_service) ====================
    
    def load_track_data(self, parent_widget: QWidget) -> list[tuple] | None:
        """Load track data from file.
        
        Args:
            parent_widget: Parent widget for dialog
        
        Returns:
            List of point tuples or None if cancelled/failed
        """
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Load Track Data",
            self._last_directory,
            "JSON Files (*.json);;CSV Files (*.csv);;All Files (*.*)"
        )
        
        if not file_path:
            return None
        
        try:
            # Update last directory
            self._last_directory = str(Path(file_path).parent)
            
            # Load based on extension
            if file_path.endswith('.json'):
                data = self._load_json(file_path)
            elif file_path.endswith('.csv'):
                data = self._load_csv(file_path)
            else:
                # Try to detect format
                data = self._auto_detect_load(file_path)
            
            # Add to recent files
            self.add_recent_file(file_path)
            
            # Log success
            if self._logger:
                self._logger.log_info(f"Successfully loaded {len(data)} points from {file_path}")
            
            # Update status
            if self._status:
                self._status.show_info(f"Loaded {len(data)} points")
            
            return data
        
        except Exception as e:
            error_msg = f"Failed to load file: {e}"
            
            if self._logger:
                self._logger.log_error(error_msg, e)
            
            if self._status:
                self._status.show_error(error_msg)
            
            QMessageBox.critical(parent_widget, "Error", error_msg)
            return None
    
    def save_track_data(self, parent_widget: QWidget, data: list[tuple]) -> bool:
        """Save track data to file.
        
        Args:
            parent_widget: Parent widget for dialog
            data: Curve data to save
        
        Returns:
            True if successful, False otherwise
        """
        if not data:
            if self._status:
                self._status.show_warning("No data to save")
            return False
        
        # Open save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Save Track Data",
            self._last_directory,
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if not file_path:
            return False
        
        try:
            # Ensure proper extension
            if not file_path.endswith(('.json', '.csv')):
                file_path += '.json'
            
            # Update last directory
            self._last_directory = str(Path(file_path).parent)
            
            # Save based on extension
            if file_path.endswith('.json'):
                self._save_json(file_path, data)
            else:
                self._save_csv(file_path, data)
            
            # Add to recent files
            self.add_recent_file(file_path)
            
            # Log success
            if self._logger:
                self._logger.log_info(f"Successfully saved {len(data)} points to {file_path}")
            
            # Update status
            if self._status:
                self._status.show_info(f"Saved {len(data)} points")
            
            return True
        
        except Exception as e:
            error_msg = f"Failed to save file: {e}"
            
            if self._logger:
                self._logger.log_error(error_msg, e)
            
            if self._status:
                self._status.show_error(error_msg)
            
            QMessageBox.critical(parent_widget, "Error", error_msg)
            return False
    
    def _load_json(self, file_path: str) -> list[tuple]:
        """Load data from JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Convert to tuple format
        points = []
        for item in data:
            if isinstance(item, dict):
                frame = item.get('frame', 0)
                x = item.get('x', 0)
                y = item.get('y', 0)
                status = item.get('status', 'keyframe')
                points.append((frame, x, y, status))
            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                # Handle list/tuple format
                frame = item[0]
                x = item[1]
                y = item[2]
                status = item[3] if len(item) > 3 else 'keyframe'
                points.append((frame, x, y, status))
        
        return points
    
    def _load_csv(self, file_path: str) -> list[tuple]:
        """Load data from CSV file."""
        points = []
        with open(file_path, 'r', newline='') as f:
            reader = csv.reader(f)
            # Skip header if present
            first_row = next(reader, None)
            if first_row and not first_row[0].isdigit():
                # Header row, skip it
                pass
            elif first_row:
                # Data row, process it
                frame = int(first_row[0])
                x = float(first_row[1])
                y = float(first_row[2])
                status = first_row[3] if len(first_row) > 3 else 'keyframe'
                points.append((frame, x, y, status))
            
            # Process remaining rows
            for row in reader:
                if len(row) >= 3:
                    frame = int(row[0])
                    x = float(row[1])
                    y = float(row[2])
                    status = row[3] if len(row) > 3 else 'keyframe'
                    points.append((frame, x, y, status))
        
        return points
    
    def _auto_detect_load(self, file_path: str) -> list[tuple]:
        """Auto-detect file format and load."""
        # Try JSON first
        try:
            return self._load_json(file_path)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Try CSV
        try:
            return self._load_csv(file_path)
        except (csv.Error, ValueError):
            pass
        
        raise ValueError("Unable to detect file format")
    
    def _save_json(self, file_path: str, data: list[tuple]) -> None:
        """Save data to JSON file."""
        json_data = []
        for point in data:
            json_data.append({
                'frame': point[0],
                'x': point[1],
                'y': point[2],
                'status': point[3] if len(point) > 3 else 'keyframe'
            })
        
        with open(file_path, 'w') as f:
            json.dump(json_data, f, indent=2)
    
    def _save_csv(self, file_path: str, data: list[tuple]) -> None:
        """Save data to CSV file."""
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(['frame', 'x', 'y', 'status'])
            # Write data
            for point in data:
                row = [point[0], point[1], point[2]]
                if len(point) > 3:
                    row.append(point[3])
                else:
                    row.append('keyframe')
                writer.writerow(row)
    
    def add_recent_file(self, file_path: str) -> None:
        """Add a file to the recent files list."""
        # Remove if already in list
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        
        # Add to beginning
        self._recent_files.insert(0, file_path)
        
        # Limit size
        if len(self._recent_files) > self._max_recent_files:
            self._recent_files = self._recent_files[:self._max_recent_files]
        
        # Save to config
        self._save_recent_files()
    
    def get_recent_files(self) -> list[str]:
        """Get the list of recent files."""
        return list(self._recent_files)
    
    def _load_recent_files(self) -> None:
        """Load recent files from config."""
        # For now, just initialize empty
        # TODO: Load from actual config file
        pass
    
    def _save_recent_files(self) -> None:
        """Save recent files to config."""
        # TODO: Save to actual config file
        pass
    
    # ==================== Image Methods (from image_service) ====================
    
    def load_image_sequence(self, directory: str) -> list[str]:
        """Load image sequence from directory.
        
        Args:
            directory: Path to directory containing images
        
        Returns:
            List of image filenames sorted by frame number
        """
        if not os.path.exists(directory):
            if self._logger:
                self._logger.log_error(f"Directory does not exist: {directory}")
            return []
        
        image_files = []
        
        try:
            # Find all image files in directory
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self._supported_formats:
                        image_files.append(file)
            
            # Sort by frame number if possible
            image_files = self._sort_by_frame_number(image_files)
            
            if self._logger:
                self._logger.log_info(f"Loaded {len(image_files)} images from {directory}")
            
            if self._status and image_files:
                self._status.show_info(f"Loaded {len(image_files)} images")
            
            return image_files
        
        except Exception as e:
            error_msg = f"Failed to load image sequence: {e}"
            if self._logger:
                self._logger.log_error(error_msg, e)
            return []
    
    def set_current_image_by_frame(self, curve_view: Any, frame: int) -> None:
        """Set current image by frame number.
        
        Args:
            curve_view: The curve view instance
            frame: Frame number to find the closest image for
        """
        if not hasattr(curve_view, "image_filenames"):
            return
        
        image_filenames = getattr(curve_view, "image_filenames", [])
        if not image_filenames:
            return
        
        # Find the closest image index to the requested frame
        closest_idx = self._find_closest_image_index(image_filenames, frame)
        
        if 0 <= closest_idx < len(image_filenames):
            curve_view.current_image_idx = closest_idx
            self.load_current_image(curve_view)
    
    def load_current_image(self, curve_view: Any) -> None:
        """Load the current image for the curve view.
        
        Args:
            curve_view: The curve view instance
        """
        if not hasattr(curve_view, "image_filenames") or not hasattr(curve_view, "current_image_idx"):
            return
        
        image_filenames = getattr(curve_view, "image_filenames", [])
        current_idx = getattr(curve_view, "current_image_idx", 0)
        
        if not image_filenames or current_idx < 0 or current_idx >= len(image_filenames):
            return
        
        image_dir = getattr(curve_view, "image_directory", "")
        if not image_dir:
            return
        
        image_path = os.path.join(image_dir, image_filenames[current_idx])
        
        # Check cache first
        if image_path in self._image_cache:
            image = self._image_cache[image_path]
        else:
            # Load image
            image = QImage(image_path)
            if image.isNull():
                if self._logger:
                    self._logger.log_error(f"Failed to load image: {image_path}")
                return
            
            # Add to cache
            if len(self._image_cache) >= self._max_cache_size:
                # Remove oldest entry
                oldest_key = next(iter(self._image_cache))
                del self._image_cache[oldest_key]
            
            self._image_cache[image_path] = image
        
        # Convert to pixmap and set as background
        pixmap = QPixmap.fromImage(image)
        curve_view.background_image = pixmap
        curve_view.update()
    
    def clear_image_cache(self) -> None:
        """Clear the image cache."""
        self._image_cache.clear()
    
    def _sort_by_frame_number(self, filenames: list[str]) -> list[str]:
        """Sort filenames by extracted frame number."""
        import re
        
        def extract_number(filename: str) -> int:
            """Extract frame number from filename."""
            # Look for numbers in the filename
            numbers = re.findall(r'\d+', filename)
            if numbers:
                # Return the last number found (usually the frame number)
                return int(numbers[-1])
            return 0
        
        return sorted(filenames, key=extract_number)
    
    def _find_closest_image_index(self, filenames: list[str], frame: int) -> int:
        """Find the index of the image closest to the given frame number."""
        import re
        
        def extract_number(filename: str) -> int:
            """Extract frame number from filename."""
            numbers = re.findall(r'\d+', filename)
            if numbers:
                return int(numbers[-1])
            return 0
        
        # Find closest frame
        min_diff = float('inf')
        closest_idx = 0
        
        for i, filename in enumerate(filenames):
            file_frame = extract_number(filename)
            diff = abs(file_frame - frame)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        
        return closest_idx


# Module-level singleton instance
_instance = DataService()

def get_data_service() -> DataService:
    """Get the singleton instance of DataService."""
    return _instance