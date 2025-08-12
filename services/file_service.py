#!/usr/bin/env python
"""
Instance-based FileService with dependency injection.

This service handles all file operations for the CurveEditor application
using dependency injection for better testability and loose coupling.
"""

import csv
import json
import os
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from services.service_protocols import LoggingServiceProtocol, StatusServiceProtocol

class FileService:
    """Instance-based file service with dependency injection."""

    def __init__(
        self,
        logging_service: LoggingServiceProtocol | None = None,
        status_service: StatusServiceProtocol | None = None,
    ):
        """Initialize FileService with injected dependencies.

        Args:
            logging_service: Optional logging service for error tracking
            status_service: Optional status service for user feedback
        """
        self._logger = logging_service
        self._status = status_service
        self._recent_files: list[str] = []
        self._max_recent_files = 10
        self._last_directory = ""

        # Load recent files from config if available
        self._load_recent_files()

    def load_track_data(self, parent_widget: QWidget) -> list[tuple] | None:
        """Load track data from file and return it.

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

    def export_to_csv(self, parent_widget: QWidget, data: list[tuple]) -> bool:
        """Export data to CSV format.

        Args:
            parent_widget: Parent widget for dialog
            data: Curve data to export

        Returns:
            True if successful, False otherwise
        """
        if not data:
            if self._status:
                self._status.show_warning("No data to export")
            QMessageBox.warning(parent_widget, "Warning", "No data to export")
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Export to CSV",
            self._last_directory,
            "CSV Files (*.csv)"
        )

        if not file_path:
            return False

        try:
            self._save_csv(file_path, data)

            if self._logger:
                self._logger.log_info(f"Exported {len(data)} points to CSV: {file_path}")

            if self._status:
                self._status.show_info("Data exported successfully")

            QMessageBox.information(parent_widget, "Success", "Data exported successfully")
            return True

        except Exception as e:
            error_msg = f"Failed to export: {e}"

            if self._logger:
                self._logger.log_error(error_msg, e)

            if self._status:
                self._status.show_error(error_msg)

            QMessageBox.critical(parent_widget, "Error", error_msg)
            return False

    def import_from_csv(self, parent_widget: QWidget) -> list[tuple] | None:
        """Import data from CSV format.

        Args:
            parent_widget: Parent widget for dialog

        Returns:
            List of point tuples or None if cancelled/failed
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Import from CSV",
            self._last_directory,
            "CSV Files (*.csv);;All Files (*.*)"
        )

        if not file_path:
            return None

        try:
            data = self._load_csv(file_path)

            if self._logger:
                self._logger.log_info(f"Imported {len(data)} points from CSV: {file_path}")

            if self._status:
                self._status.show_info(f"Imported {len(data)} points")

            return data

        except Exception as e:
            error_msg = f"Failed to import: {e}"

            if self._logger:
                self._logger.log_error(error_msg, e)

            if self._status:
                self._status.show_error(error_msg)

            QMessageBox.critical(parent_widget, "Error", error_msg)
            return None

    def get_recent_files(self) -> list[str]:
        """Get list of recently used files."""
        return self._recent_files.copy()

    def add_recent_file(self, file_path: str) -> None:
        """Add file to recent files list.

        Args:
            file_path: Path to add to recent files
        """
        # Remove if already in list
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)

        # Add to front
        self._recent_files.insert(0, file_path)

        # Limit size
        self._recent_files = self._recent_files[:self._max_recent_files]

        # Save to config
        self._save_recent_files()

    def clear_recent_files(self) -> None:
        """Clear the recent files list."""
        self._recent_files.clear()
        self._save_recent_files()

    # Private helper methods

    def _load_json(self, file_path: str) -> list[tuple]:
        """Load data from JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)

            # Handle both list and dict formats
            if isinstance(data, dict):
                if 'points' in data:
                    curve_data = data['points']
                elif 'curve_data' in data:
                    curve_data = data['curve_data']
                else:
                    # Try to find any list in the dict
                    for value in data.values():
                        if isinstance(value, list):
                            curve_data = value
                            break
                    else:
                        curve_data = []
            else:
                curve_data = data

            # Convert to tuples
            result = []
            for point in curve_data:
                if isinstance(point, (list, tuple)) and len(point) >= 3:
                    # Ensure we have at least frame, x, y
                    frame = int(point[0])
                    x = float(point[1])
                    y = float(point[2])
                    # Include additional data if present
                    if len(point) > 3:
                        result.append((frame, x, y, *point[3:]))
                    else:
                        result.append((frame, x, y))

            return result

    def _load_csv(self, file_path: str) -> list[tuple]:
        """Load data from CSV file."""
        curve_data = []

        with open(file_path, 'r') as f:
            reader = csv.reader(f)

            # Skip header if present
            first_row = next(reader, None)
            if first_row and not first_row[0].isdigit():
                # It's a header, skip it
                pass
            elif first_row:
                # It's data, process it
                if len(first_row) >= 3:
                    curve_data.append((
                        int(first_row[0]),
                        float(first_row[1]),
                        float(first_row[2]),
                        *first_row[3:]
                    ))

            # Process remaining rows
            for row in reader:
                if len(row) >= 3:
                    try:
                        curve_data.append((
                            int(row[0]),
                            float(row[1]),
                            float(row[2]),
                            *row[3:]
                        ))
                    except ValueError:
                        # Skip invalid rows
                        if self._logger:
                            self._logger.log_warning(f"Skipping invalid CSV row: {row}")

        return curve_data

    def _auto_detect_load(self, file_path: str) -> list[tuple]:
        """Try to auto-detect file format and load."""
        # Try JSON first
        try:
            return self._load_json(file_path)
        except Exception:
            pass

        # Try CSV
        try:
            return self._load_csv(file_path)
        except Exception:
            pass

        raise ValueError("Unable to detect file format")

    def _save_json(self, file_path: str, data: list[tuple]) -> None:
        """Save data to JSON file."""
        # Convert tuples to lists for JSON
        json_data = {
            'points': [list(point) for point in data],
            'version': '2.0',
            'format': 'curve_editor'
        }

        with open(file_path, 'w') as f:
            json.dump(json_data, f, indent=2)

    def _save_csv(self, file_path: str, data: list[tuple]) -> None:
        """Save data to CSV file."""
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Write header
            headers = ['Frame', 'X', 'Y']
            if data and len(data[0]) > 3:
                # Add additional column headers if needed
                for i in range(3, len(data[0])):
                    headers.append(f'Data{i-2}')
            writer.writerow(headers)

            # Write data
            for point in data:
                writer.writerow(point)

    def _load_recent_files(self) -> None:
        """Load recent files from configuration."""
        try:
            config_path = Path.home() / '.curve_editor' / 'recent_files.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self._recent_files = json.load(f)
        except Exception:
            # Ignore errors loading recent files
            pass

    def _save_recent_files(self) -> None:
        """Save recent files to configuration."""
        try:
            config_dir = Path.home() / '.curve_editor'
            config_dir.mkdir(exist_ok=True)

            config_path = config_dir / 'recent_files.json'
            with open(config_path, 'w') as f:
                json.dump(self._recent_files, f)
        except Exception as e:
            # Log but don't fail
            if self._logger:
                self._logger.log_warning(f"Could not save recent files: {e}")

# Module-level singleton instance
_instance: FileService | None = None

def get_file_service() -> FileService:
    """Get the singleton instance of FileService."""
    global _instance
    if _instance is None:
        import logging
        _instance = FileService(logging_service=None)  # Will use get_logger directly
    return _instance