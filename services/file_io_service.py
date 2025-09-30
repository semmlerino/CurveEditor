#!/usr/bin/env python
"""
File I/O Service for CurveEditor.

This service handles all file input/output operations including:
- CSV and JSON file loading and saving
- Track data file operations
- Recent files tracking
- Directory tracking
- 2DTrackData format support

Extracted from DataService during Phase 3 modularization.
"""

import csv
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog

from core.curve_data import CurveDataWithMetadata
from core.type_aliases import CurveDataList
from protocols.services import LoggingServiceProtocol, StatusServiceProtocol

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

logger = logging.getLogger("file_io_service")


class FileIOService:
    """Service for file input/output operations."""

    def __init__(
        self,
        logging_service: LoggingServiceProtocol | None = None,
        status_service: StatusServiceProtocol | None = None,
    ) -> None:
        """Initialize FileIOService with optional dependencies."""
        self._logger: LoggingServiceProtocol | None = logging_service
        self._status: StatusServiceProtocol | None = status_service

        # Initialize state for file I/O operations
        self._recent_files: list[str] = []
        self._max_recent_files: int = 10  # Maximum number of recent files to keep
        self._last_directory: str = ""

    # ==================== Public API Methods ====================

    def load_csv(self, filepath: str) -> CurveDataList:
        """
        Public method to load CSV file programmatically.

        Args:
            filepath: Path to CSV file

        Returns:
            List of curve data points
        """
        return self._load_csv(filepath)

    def load_json(self, filepath: str) -> CurveDataList:
        """
        Public method to load JSON file programmatically.

        Args:
            filepath: Path to JSON file

        Returns:
            List of curve data points
        """
        return self._load_json(filepath)

    def save_json(self, filepath: str, data: CurveDataList) -> bool:
        """
        Public method to save data as JSON programmatically.

        Args:
            filepath: Path to save JSON file
            data: Curve data to save

        Returns:
            True if successful
        """
        return self._save_json(filepath, data, label="", color="")

    def save_csv(self, filepath: str, data: CurveDataList, include_header: bool = True) -> bool:
        """
        Public method to save data as CSV programmatically.

        Args:
            filepath: Path to save CSV file
            data: Curve data to save
            include_header: Whether to include column headers

        Returns:
            True if successful
        """
        return self._save_csv(filepath, data, include_header)

    # ==================== Interactive File Operations ====================

    def load_track_data(self, parent_widget: "QWidget") -> CurveDataList | None:
        """Load track data from file using file dialog."""
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
        elif file_path.endswith(".csv"):
            return self._load_csv(file_path)
        elif file_path.endswith(".txt"):
            result = self._load_2dtrack_data(file_path)
            if isinstance(result, CurveDataWithMetadata):
                return result.data
            return result
        else:
            # Try to detect format by content
            try:
                return self._load_json(file_path)
            except Exception:
                try:
                    result = self._load_2dtrack_data(file_path)
                    if isinstance(result, CurveDataWithMetadata):
                        return result.data
                    return result
                except Exception:
                    return self._load_csv(file_path)

    def save_track_data(
        self, parent_widget: "QWidget", data: CurveDataList, label: str = "Track", color: str = "#FF0000"
    ) -> bool:
        """Save track data to file using file dialog."""
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
        else:
            return self._save_csv(file_path, data, include_header=True)

    # ==================== Recent Files Management ====================

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

    def get_last_directory(self) -> str:
        """Get the last used directory."""
        return self._last_directory

    def set_last_directory(self, directory: str) -> None:
        """Set the last used directory."""
        self._last_directory = directory

    # ==================== Multiple Point Data Loader ====================

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
        tracked_data = {}

        try:
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
                            trajectory = []
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
                                        # Keep original coordinates (display transform will handle Y-flip)
                                        trajectory.append((frame, x, y))
                                    except (ValueError, IndexError):
                                        continue

                            # Store the trajectory
                            if trajectory:
                                tracked_data[point_name] = trajectory

                            # Move past this point's data
                            i = data_start + point_count
                            continue

                        except (ValueError, IndexError):
                            pass

                i += 1

            if self._logger:
                self._logger.log_info(f"Loaded {len(tracked_data)} tracking points from {file_path}")

            # Check if we need to denormalize coordinates
            if tracked_data:
                from core.coordinate_detector import detect_coordinate_system

                metadata = detect_coordinate_system(file_path)

                if metadata.uses_normalized_coordinates:
                    # Denormalize all tracked data
                    denormalized_data = {}
                    for point_name, trajectory in tracked_data.items():
                        denormalized_trajectory = []
                        for frame, x, y in trajectory:
                            x_pixel, y_pixel = metadata.denormalize_coordinates(x, y)
                            denormalized_trajectory.append((frame, x_pixel, y_pixel))
                        denormalized_data[point_name] = denormalized_trajectory

                    if self._logger:
                        total_points = sum(len(traj) for traj in denormalized_data.values())
                        self._logger.log_info(f"Denormalized {total_points} points from normalized coordinates")

                    return denormalized_data

            return tracked_data

        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to load tracked data: {e}")
            return {}

    # ==================== Internal Implementation Methods ====================

    def _load_json(self, file_path: str) -> CurveDataList:
        """Load JSON file implementation."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            # Convert to CurveDataList format
            curve_data = []

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # Handle different JSON formats
                        frame = item.get("frame", item.get("f", 0))
                        x = item.get("x", item.get("X", 0.0))
                        y = item.get("y", item.get("Y", 0.0))
                        status = item.get("status", item.get("type", "keyframe"))
                        curve_data.append((frame, x, y, status))
                    elif isinstance(item, list | tuple) and len(item) >= 3:
                        # Handle array format [frame, x, y, ...]
                        frame = item[0]
                        x = float(item[1])
                        y = float(item[2])
                        status = item[3] if len(item) > 3 else "keyframe"
                        curve_data.append((frame, x, y, status))
            elif isinstance(data, dict) and "points" in data:
                # Handle wrapped format {"points": [...], "metadata": {...}}
                points = data["points"]
                for point in points:
                    if isinstance(point, dict):
                        frame = point.get("frame", 0)
                        x = point.get("x", 0.0)
                        y = point.get("y", 0.0)
                        status = point.get("status", "keyframe")
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
        """Save JSON file implementation."""
        try:
            # Convert CurveDataList to JSON format
            points_list: list[dict[str, object]] = []
            json_data = {
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

        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to save JSON file {file_path}: {e}")
            return False

    def _load_2dtrack_data(self, file_path: str) -> CurveDataList | CurveDataWithMetadata:
        """Load 2DTrackData.txt format file (single curve).

        Format:
        Line 1: Version (e.g., "1")
        Line 2: Identifier 1 (e.g., "07")
        Line 3: Identifier 2 (e.g., "0")
        Line 4: Number of points (e.g., "37")
        Lines 5+: frame_number x_coordinate y_coordinate

        Returns:
            CurveDataWithMetadata with proper coordinate system info
        """
        try:
            curve_data = []

            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

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
                                # Keep original coordinates (display transform will handle Y-flip)

                                # Optional status field
                                status = "keyframe"
                                if len(parts) >= 4:
                                    status = parts[3]

                                curve_data.append((frame, x, y, status))

                            except (ValueError, IndexError) as e:
                                if self._logger:
                                    self._logger.log_error(f"Invalid data at line {line_num}: {e}")
                                continue

            if self._logger:
                self._logger.log_info(f"Loaded {len(curve_data)} points from {file_path}")

            # Wrap with metadata for proper coordinate transformation
            from core.curve_data import wrap_legacy_data

            wrapped_data = wrap_legacy_data(curve_data, file_path)

            # Apply denormalization if coordinates are normalized
            if wrapped_data.metadata and wrapped_data.metadata.uses_normalized_coordinates:
                denormalized_data = []
                for point in curve_data:
                    frame = point[0]
                    x, y = wrapped_data.metadata.denormalize_coordinates(point[1], point[2])
                    status = point[3] if len(point) > 3 else "keyframe"
                    denormalized_data.append((frame, x, y, status))

                # Create new metadata without the normalized flag since we've denormalized
                from dataclasses import replace

                new_metadata = replace(wrapped_data.metadata, uses_normalized_coordinates=False)

                # Return new wrapper with denormalized data and updated metadata
                from core.curve_data import CurveDataWithMetadata

                if self._logger:
                    self._logger.log_info(f"Denormalized {len(denormalized_data)} points from normalized coordinates")
                return CurveDataWithMetadata(denormalized_data, new_metadata)

            return wrapped_data

        except FileNotFoundError:
            if self._logger:
                self._logger.log_error(f"File not found: {file_path}")
            # Return empty metadata-aware data
            from core.curve_data import wrap_legacy_data

            return wrap_legacy_data([], file_path)
        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to load 2DTrackData file {file_path}: {e}")
            # Return empty metadata-aware data
            from core.curve_data import wrap_legacy_data

            return wrap_legacy_data([], file_path)

    def _load_csv(self, file_path: str) -> CurveDataList:
        """Load CSV file implementation."""
        try:
            curve_data = []

            with open(file_path, encoding="utf-8", newline="") as f:
                # Try to detect delimiter
                sample = f.read(1024)
                f.seek(0)

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
                        status = "keyframe"
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
        """Save CSV file implementation."""
        try:
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

        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to save CSV file {file_path}: {e}")
            return False
