"""
File I/O service for the CurveEditor.

This service handles loading and saving curve data in various formats
including JSON and CSV, and manages recent files.
"""

import csv
import json
import logging
import threading
from pathlib import Path

from core.path_security import PathSecurityError, validate_file_path
from core.type_aliases import CurveDataList

logger = logging.getLogger(__name__)


class FileIOService:
    """
    Handles file input/output operations for curve data.

    This service is responsible for:
    - Loading curve data from JSON and CSV files
    - Saving curve data to JSON and CSV files
    - Managing recent files list
    - File path validation and security
    """

    def __init__(self, max_recent_files: int = 10):
        """
        Initialize the file I/O service.

        Args:
            max_recent_files: Maximum number of recent files to track
        """
        self._lock = threading.RLock()
        self._recent_files: list[str] = []
        self._max_recent_files = max_recent_files
        self._last_directory: str = ""

        # Load recent files from config if available
        self._load_recent_files()

    def load_json(self, file_path: str) -> CurveDataList:
        """
        Load curve data from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            List of point tuples

        Raises:
            PathSecurityError: If path is invalid
            ValueError: If JSON format is invalid
        """
        # Validate path
        validated_path = validate_file_path(file_path, operation_type="data_files", require_exists=True)
        file_path = str(validated_path)

        with self._lock:
            with open(file_path) as f:
                data = json.load(f)

            # Extract curve data
            curve_data = []

            # Handle different JSON formats
            if isinstance(data, dict):
                # Format 1: {"curve_data": [...]}
                if "curve_data" in data:
                    points = data["curve_data"]
                # Format 2: {"points": [...]}
                elif "points" in data:
                    points = data["points"]
                # Format 3: {"data": [...]}
                elif "data" in data:
                    points = data["data"]
                else:
                    raise ValueError(f"Unrecognized JSON format in {file_path}")
            elif isinstance(data, list):
                # Direct list of points
                points = data
            else:
                raise ValueError(f"Invalid JSON structure in {file_path}")

            # Convert points to tuples
            for point in points:
                if isinstance(point, list | tuple) and len(point) >= 3:
                    # Basic format: [frame, x, y]
                    frame = int(point[0])
                    x = float(point[1])
                    y = float(point[2])

                    # Optional status field
                    if len(point) > 3:
                        status = str(point[3])
                        curve_data.append((frame, x, y, status))
                    else:
                        curve_data.append((frame, x, y))
                elif isinstance(point, dict):
                    # Dictionary format
                    frame = int(point.get("frame", point.get("f", 0)))
                    x = float(point.get("x", 0))
                    y = float(point.get("y", 0))
                    status = point.get("status", point.get("s", "normal"))

                    if status and status != "normal":
                        curve_data.append((frame, x, y, status))
                    else:
                        curve_data.append((frame, x, y))

            # Update recent files
            self.add_recent_file(file_path)
            self._last_directory = str(Path(file_path).parent)

            logger.debug(f"Loaded {len(curve_data)} points from JSON: {file_path}")
            return curve_data

    def save_json(
        self,
        file_path: str,
        curve_data: CurveDataList,
        point_name: str = "TrackPoint",
        point_color: str = "#FF0000"
    ) -> bool:
        """
        Save curve data to JSON file.

        Args:
            file_path: Path to save JSON file
            curve_data: List of point tuples
            point_name: Name of the point type
            point_color: Color of the points

        Returns:
            True if successful, False otherwise
        """
        # Validate path
        try:
            validated_path = validate_file_path(file_path, operation_type="data_files", require_exists=False)
            file_path = str(validated_path)
        except PathSecurityError as e:
            logger.error(f"Security violation: {e}")
            return False

        with self._lock:
            try:
                # Convert tuples to JSON-serializable format
                points = []
                for point in curve_data:
                    if len(point) >= 4:
                        # Include status
                        points.append({
                            "frame": point[0],
                            "x": point[1],
                            "y": point[2],
                            "status": point[3]
                        })
                    else:
                        # Basic format
                        points.append({
                            "frame": point[0],
                            "x": point[1],
                            "y": point[2]
                        })

                # Create JSON structure
                data = {
                    "curve_data": points,
                    "metadata": {
                        "point_name": point_name,
                        "point_color": point_color,
                        "version": "1.0"
                    }
                }

                # Write to file
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2)

                # Update recent files
                self.add_recent_file(file_path)
                self._last_directory = str(Path(file_path).parent)

                logger.debug(f"Saved {len(curve_data)} points to JSON: {file_path}")
                return True

            except Exception as e:
                logger.error(f"Failed to save JSON: {e}")
                return False

    def load_csv(self, file_path: str) -> CurveDataList:
        """
        Load curve data from CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            List of point tuples

        Raises:
            PathSecurityError: If path is invalid
            ValueError: If CSV format is invalid
        """
        # Validate path
        validated_path = validate_file_path(file_path, operation_type="data_files", require_exists=True)
        file_path = str(validated_path)

        with self._lock:
            curve_data = []

            with open(file_path, newline="") as f:
                reader = csv.reader(f)

                # Skip header if present
                first_row = next(reader, None)
                if first_row:
                    # Check if first row is header
                    try:
                        int(first_row[0])
                        # Not a header, process as data
                        if len(first_row) >= 3:
                            frame = int(first_row[0])
                            x = float(first_row[1])
                            y = float(first_row[2])

                            if len(first_row) > 3:
                                status = str(first_row[3])
                                curve_data.append((frame, x, y, status))
                            else:
                                curve_data.append((frame, x, y))
                    except ValueError:
                        # First row is header, skip it
                        pass

                # Process remaining rows
                for row in reader:
                    if len(row) >= 3:
                        try:
                            frame = int(row[0])
                            x = float(row[1])
                            y = float(row[2])

                            if len(row) > 3:
                                status = str(row[3])
                                curve_data.append((frame, x, y, status))
                            else:
                                curve_data.append((frame, x, y))
                        except (ValueError, IndexError):
                            # Skip invalid rows
                            continue

            # Update recent files
            self.add_recent_file(file_path)
            self._last_directory = str(Path(file_path).parent)

            logger.debug(f"Loaded {len(curve_data)} points from CSV: {file_path}")
            return curve_data

    def save_csv(
        self,
        file_path: str,
        curve_data: CurveDataList,
        include_header: bool = True
    ) -> bool:
        """
        Save curve data to CSV file.

        Args:
            file_path: Path to save CSV file
            curve_data: List of point tuples
            include_header: Whether to include header row

        Returns:
            True if successful, False otherwise
        """
        # Validate path
        try:
            validated_path = validate_file_path(file_path, operation_type="data_files", require_exists=False)
            file_path = str(validated_path)
        except PathSecurityError as e:
            logger.error(f"Security violation: {e}")
            return False

        with self._lock:
            try:
                with open(file_path, "w", newline="") as f:
                    writer = csv.writer(f)

                    # Write header if requested
                    if include_header:
                        writer.writerow(["frame", "x", "y", "status"])

                    # Write data
                    for point in curve_data:
                        if len(point) >= 4:
                            writer.writerow([point[0], point[1], point[2], point[3]])
                        else:
                            writer.writerow([point[0], point[1], point[2], "normal"])

                # Update recent files
                self.add_recent_file(file_path)
                self._last_directory = str(Path(file_path).parent)

                logger.debug(f"Saved {len(curve_data)} points to CSV: {file_path}")
                return True

            except Exception as e:
                logger.error(f"Failed to save CSV: {e}")
                return False

    def add_recent_file(self, file_path: str) -> None:
        """
        Add a file to the recent files list.

        Args:
            file_path: Path to add to recent files
        """
        with self._lock:
            # Remove if already in list
            if file_path in self._recent_files:
                self._recent_files.remove(file_path)

            # Add to front
            self._recent_files.insert(0, file_path)

            # Trim to max size
            self._recent_files = self._recent_files[:self._max_recent_files]

            # Save to config
            self._save_recent_files()

    def get_recent_files(self) -> list[str]:
        """
        Get list of recent files.

        Returns:
            List of recent file paths
        """
        with self._lock:
            # Filter out non-existent files
            valid_files = []
            for file_path in self._recent_files:
                if Path(file_path).exists():
                    valid_files.append(file_path)

            # Update list if any were removed
            if len(valid_files) != len(self._recent_files):
                self._recent_files = valid_files
                self._save_recent_files()

            return list(self._recent_files)

    def clear_recent_files(self) -> None:
        """Clear the recent files list."""
        with self._lock:
            self._recent_files.clear()
            self._save_recent_files()

    def get_last_directory(self) -> str:
        """
        Get the last used directory.

        Returns:
            Path to last used directory or empty string
        """
        return self._last_directory

    def set_last_directory(self, directory: str) -> None:
        """
        Set the last used directory.

        Args:
            directory: Directory path to remember
        """
        self._last_directory = directory

    def _load_recent_files(self) -> None:
        """Load recent files from configuration."""
        # This would load from a config file or settings
        # For now, just initialize empty
        pass

    def _save_recent_files(self) -> None:
        """Save recent files to configuration."""
        # This would save to a config file or settings
        # For now, just log
        logger.debug(f"Recent files updated: {len(self._recent_files)} files")
