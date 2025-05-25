#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FileService: Service class for file operations.
Provides functionality for loading, saving, and exporting track data.
"""

import os
import logging
from typing import Optional, Any, Tuple
from services.logging_service import LoggingService
from services.protocols import MainWindowProtocol, PointsList
from PySide6.QtWidgets import QMessageBox, QFileDialog


# Safe module imports with fallbacks
# We'll define utility functions that provide safe access to modules that might not be available
utils_module: Optional[Any] = None
config_module: Optional[Any] = None

from types import ModuleType
curve_utils_module: Optional[ModuleType] = None
# track_exporter_module: Optional[ModuleType] = None
# track_importer_module: Optional[ModuleType] = None

try:
    import config as config_module
except ImportError:
    config_module = None

# Configure logger for this module
logger: logging.Logger = LoggingService.get_logger("file_service")

# Helper functions to safely access modules
def safe_call(module: Optional[Any], attr_name: str, *args: Any, **kwargs: Any) -> Any:
    """Safely call a function from a module that might not be available."""
    if module is None:
        logger.error(f"Module not available for {attr_name}")
        return None
    
    func = getattr(module, attr_name, None)
    if func is None:
        logger.error(f"Function {attr_name} not available in module")
        return None
        
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error calling {attr_name}: {e}")
        return None

class FileService:
    """Service class for file operations in the 3DE4 Curve Editor."""
    
    @staticmethod
    def get_config_value(attr_name: str, default: Any = None) -> Any:
        """Safely get a value from the config module."""
        if config_module is None:
            logger.error(f"Config module not available for {attr_name}")
            return default
        attr = getattr(config_module, attr_name, None)
        if callable(attr):
            return attr()
        return default

    @staticmethod
    def set_config_value(attr_name: str, value: Any) -> None:
        """Safely set a config value."""
        if config_module is None:
            logger.error(f"Config module not available for {attr_name}")
            return
        setattr(config_module, attr_name, value)

    @classmethod
    def call_utils(cls, module_name: str, func_name: str, *args: Any, **kwargs: Any) -> Any:
        """Safely call a utils function from the specified module."""
        if module_name == "curve_utils":
            return safe_call(curve_utils_module, func_name, *args, **kwargs)
        else:
            logger.error(f"Unknown or unavailable module: {module_name}")
            return None

    @staticmethod
    def export_to_csv(main_window: MainWindowProtocol) -> None:
        """Export curve data to CSV file."""
        if not main_window.curve_data:
            QMessageBox.warning(main_window.qwidget(), "Warning", "No curve data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            main_window.qwidget(), "Export to CSV", main_window.default_directory, "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        # Ensure file has .csv extension
        if not file_path.lower().endswith(".csv"):
            file_path += ".csv"

        try:
            # Export data to CSV using safe function calling
            success = FileService.call_utils(
                "track_exporter", 
                "export_to_csv",
                file_path, 
                main_window.point_name, 
                main_window.curve_data, 
                main_window.image_width, 
                main_window.image_height
            )

            if success:
                QMessageBox.information(main_window.qwidget(), "Success", f"Data exported to {file_path}")
                # Save the directory path to config
                folder_path = os.path.dirname(file_path)
                FileService.set_config_value("set_last_folder_path", folder_path)
            else:
                QMessageBox.critical(main_window.qwidget(), "Error", f"Failed to export data to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            QMessageBox.critical(main_window.qwidget(), "Error", f"Error exporting data: {str(e)}")

    @staticmethod
    def load_track_data(main_window: MainWindowProtocol) -> None:
        """Load 2D track data from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            main_window.qwidget(), "Load 2D Track Data", main_window.default_directory, "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Load track data from file using safe function calls
            result = FileService.call_utils("track_importer", "load_3de_track", file_path)
            
            # Check if result is valid
            if not result or len(result) < 4 or not result[3]:  # result[3] is curve_data
                logger.error("Failed to load track data: Invalid data format")
                QMessageBox.critical(main_window.qwidget(), "Error", "Failed to load track data: Invalid format")
                return
                
            # Unpack the result
            point_name, point_color, _, curve_data = result  # num_frames is unused
            
            # Set the data with safe type conversion
            main_window.point_name = str(point_name) if point_name is not None else "Unknown"
            main_window.point_color = str(point_color) if point_color is not None else "red"
            main_window.curve_data = curve_data

            # Determine image dimensions from the data
            dimensions = FileService.call_utils("curve_utils", "estimate_image_dimensions", curve_data)
            if dimensions and len(dimensions) == 2:
                main_window.image_width, main_window.image_height = dimensions
            else:
                # Default values if estimation fails
                main_window.image_width, main_window.image_height = 1920, 1080
                logger.warning("Using default image dimensions 1920x1080")

            # Update view
            main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height)

            # Enable controls
            main_window.save_button.setEnabled(True)
            main_window.add_point_button.setEnabled(True)
            main_window.smooth_button.setEnabled(True)
            main_window.fill_gaps_button.setEnabled(True)
            main_window.filter_button.setEnabled(True)
            main_window.detect_problems_button.setEnabled(True)
            main_window.extrapolate_button.setEnabled(True)

            # Update info
            main_window.info_label.setText(f"Loaded: {main_window.point_name} ({len(main_window.curve_data)} frames)")

            # Setup timeline
            # Get min and max frame numbers from curve data
            frame_numbers = [int(point[0]) for point in main_window.curve_data]
            min_frame = min(frame_numbers) if frame_numbers else 1
            max_frame = max(frame_numbers) if frame_numbers else 100
            main_window.setup_timeline(min_frame, max_frame)

            # Enable timeline controls
            main_window.timeline_slider.setEnabled(True)
            main_window.frame_edit.setEnabled(True)
            main_window.go_button.setEnabled(True)

            # Save the file path to config
            folder_path = os.path.dirname(file_path)
            FileService.set_config_value("set_last_file_path", file_path)
            FileService.set_config_value("set_last_folder_path", folder_path)
            
        except Exception as e:
            logger.error(f"Error loading track data: {e}")
            QMessageBox.critical(main_window.qwidget(), "Error", f"Failed to load track data: {e}")
            return

    @staticmethod
    def add_track_data(main_window: MainWindowProtocol) -> None:
        """Add an additional 2D track to the current data."""
        from typing import cast, Any
        if not main_window.curve_data:
            return

        file_path: str
        _filter: str
        file_path, _filter = QFileDialog.getOpenFileName(
            main_window.qwidget(), "Add 2D Track Data", main_window.default_directory, "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Load track data from file
            # track_importer_module is unavailable, so this is currently a stub.
            # Replace with actual importer logic if/when available.
            additional_data: PointsList = []

            if not additional_data:
                # No data to add, exit early
                return
                
            # Check frame compatibility
            # Extract frame numbers, handling both 3-tuple and 4-tuple formats
            existing_frames: set[int] = set()
            for point in main_window.curve_data:
                frame = int(point[0])
                existing_frames.add(frame)
            new_frames: set[int] = set(int(point[0]) for point in additional_data)

            # Check for frame conflicts
            frame_overlap: set[int] = existing_frames.intersection(new_frames)
            if frame_overlap:
                response = QMessageBox.question(
                    main_window.qwidget(), "Frame Conflict",
                    "Some frames already exist. What would you like to do?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                    QMessageBox.StandardButton.No
                )
                if response == QMessageBox.StandardButton.No:
                    return

            current_width: float = float(main_window.image_width)
            current_height: float = float(main_window.image_height)
            orig_width: int
            orig_height: int
            orig_width, orig_height = cast(Tuple[int, int], curve_utils_module.estimate_image_dimensions(additional_data)) if curve_utils_module else (0, 0)  

            merged_data: dict[int, Tuple[float, float, *Tuple[Any, ...]]] = {}
            for main_point in main_window.curve_data:
                main_frame: int = int(main_point[0])  # type: ignore
                main_x: float = float(main_point[1])  # type: ignore
                main_y: float = float(main_point[2])  # type: ignore
                main_rest: Tuple[Any, ...] = tuple(main_point[3:]) if len(main_point) > 3 else ()  # type: ignore
                merged_data[main_frame] = (main_x, main_y, *main_rest)

            # Assume additional_data is a PointsList
            for add_point in additional_data:
                add_frame: int = int(add_point[0])
                add_x: float = float(add_point[1])
                add_y: float = float(add_point[2])
                add_rest: Tuple[Any, ...] = tuple(add_point[3:]) if len(add_point) > 3 else ()
                if add_frame not in merged_data:
                    norm_x: float = add_x / orig_width if orig_width else add_x
                    norm_y: float = add_y / orig_height if orig_height else add_y
                    scaled_x: float = norm_x * current_width
                    scaled_y: float = norm_y * current_height
                    merged_data[add_frame] = (scaled_x, scaled_y, *add_rest)

            merged_points: PointsList = [
                (frame, *merged_data[frame][:-1], merged_data[frame][-1])  # type: ignore[misc]
                for frame in sorted(merged_data.keys())
            ]
            main_window.curve_data = merged_points

            main_window.add_to_history()

        except Exception as e:
            logger.error(f"Error adding track data: {e}")
            return
