#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FileService: Service class for file operations.
Provides functionality for loading, saving, and exporting track data.
"""

# Standard library imports
import logging
import os
from types import ModuleType
from typing import Optional, Any, Tuple

# Third-party imports
from PySide6.QtWidgets import QMessageBox, QFileDialog

# Local imports
from services.logging_service import LoggingService
from services.protocols import MainWindowProtocol, PointsList

# Safe module imports with fallbacks
# We'll define utility functions that provide safe access to modules that might not be available
utils_module: Optional[Any] = None
config_module: Optional[Any] = None

curve_utils_module: Optional[ModuleType] = None
track_exporter_module: Optional[ModuleType] = None
track_importer_module: Optional[ModuleType] = None

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
            if func_name == "estimate_image_dimensions":
                # Fallback implementation for estimate_image_dimensions
                return cls._fallback_estimate_image_dimensions(*args, **kwargs)
            return safe_call(curve_utils_module, func_name, *args, **kwargs)
        elif module_name == "track_importer":
            if func_name == "load_3de_track":
                # If the module is not available, provide a fallback implementation
                return cls._fallback_load_3de_track(*args, **kwargs)
            return safe_call(track_importer_module, func_name, *args, **kwargs)
        elif module_name == "track_exporter":
            if func_name == "export_to_csv":
                # If the module is not available, provide a fallback implementation
                return cls._fallback_export_to_csv(*args, **kwargs)
            return safe_call(track_exporter_module, func_name, *args, **kwargs)
        else:
            logger.error(f"Unknown or unavailable module: {module_name}")
            return None

    @staticmethod
    def export_to_csv(main_window: MainWindowProtocol) -> None:
        """Export curve data to CSV file."""
        if not main_window.curve_data:
            QMessageBox.warning(main_window.qwidget, "Warning", "No curve data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            main_window.qwidget, "Export to CSV", main_window.default_directory, "CSV Files (*.csv);;All Files (*)"
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
                QMessageBox.information(main_window.qwidget, "Success", f"Data exported to {file_path}")
                # Save the directory path to config
                folder_path = os.path.dirname(file_path)
                FileService.set_config_value("set_last_folder_path", folder_path)
            else:
                QMessageBox.critical(main_window.qwidget, "Error", f"Failed to export data to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            QMessageBox.critical(main_window.qwidget, "Error", f"Error exporting data: {str(e)}")

    @classmethod
    def _fallback_estimate_image_dimensions(cls, curve_data: PointsList) -> Tuple[int, int]:
        """Fallback implementation for estimating image dimensions from curve data.

        This function estimates a reasonable image size based on the coordinates in the tracking data.

        Args:
            curve_data: List of tracking points

        Returns:
            A tuple (width, height) representing the estimated image dimensions
        """
        logger.info("Using fallback image dimension estimation")

        # Default dimensions if we can't estimate from data
        default_width, default_height = 1920, 1080

        if not curve_data or len(curve_data) < 2:
            return default_width, default_height

        try:
            # Get min and max x/y values from the curve data
            x_values = [float(point[1]) for point in curve_data]
            y_values = [float(point[2]) for point in curve_data]

            if not x_values or not y_values:
                return default_width, default_height

            max_x = max(x_values)
            max_y = max(y_values)

            # Estimate dimensions with some padding
            width = max(int(max_x * 1.2), default_width)
            height = max(int(max_y * 1.2), default_height)

            return width, height

        except (ValueError, IndexError) as e:
            logger.error(f"Error in fallback image dimension estimation: {e}")
            return default_width, default_height

    @classmethod
    def _fallback_load_3de_track(cls, file_path: str) -> Optional[Tuple[str, str, int, PointsList]]:
        """Fallback implementation for loading 3DE track data when the track_importer module is not available.

        Args:
            file_path: Path to the track data file

        Returns:
            A tuple containing (point_name, point_color, num_frames, curve_data) or None if loading fails
        """
        logger.info(f"Using fallback track importer for file: {file_path}")
        try:
            # Basic implementation to parse text file containing tracking data
            curve_data: PointsList = []

            with open(file_path, 'r') as f:
                lines = f.readlines()

            # Get file name without path and extension as the point name
            point_name: str = os.path.splitext(os.path.basename(file_path))[0]
            point_color: str = "#FF0000"  # Default red color

            # Check if this is a 2DTrackData format file with header
            # Expected format:
            # Line 1: number of tracks (e.g., "1")
            # Line 2: track identifier (e.g., "07")
            # Line 3: offset (e.g., "0")
            # Line 4: number of points (e.g., "37")
            # Line 5+: frame_num x_coord y_coord

            line_index = 0
            num_points = 0

            # Try to parse header
            if len(lines) >= 4:
                try:
                    # Check if first 4 lines are header values
                    num_tracks = int(lines[0].strip())
                    track_id = lines[1].strip()
                    offset = int(lines[2].strip())
                    num_points = int(lines[3].strip())

                    # If parsing succeeded, we have a header, start from line 5
                    line_index = 4
                    logger.info(f"Detected 2DTrackData format: {num_tracks} tracks, ID: {track_id}, offset: {offset}, points: {num_points}")
                except (ValueError, IndexError):
                    # Not a header format, process all lines as data
                    line_index = 0
                    logger.info("No header detected, processing as simple track data")

            # Process tracking data lines
            for i in range(line_index, len(lines)):
                line = lines[i].strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Try to parse the line as tracking data
                parts = line.split()
                if len(parts) >= 3:  # At minimum: frame, x, y
                    try:
                        frame_num = int(float(parts[0]))
                        x_coord = float(parts[1])
                        y_coord = float(parts[2])

                        # Optional status value (convert to string as per PointTupleWithStatus)
                        # PointTupleWithStatus expects a bool or str as the fourth element
                        status = str(parts[3]) if len(parts) > 3 else "valid"

                        # Add point to curve data as PointTupleWithStatus
                        curve_data.append((frame_num, x_coord, y_coord, status))
                    except (ValueError, IndexError):
                        # Skip lines that can't be parsed
                        logger.debug(f"Skipping unparseable line: {line}")
                        continue

            # Sort by frame number
            curve_data.sort(key=lambda point: int(point[0]))

            if not curve_data:
                logger.error("No valid tracking data found in file")
                return None

            # Verify we loaded the expected number of points if header was present
            if num_points > 0 and len(curve_data) != num_points:
                logger.warning(f"Expected {num_points} points but loaded {len(curve_data)} points")

            num_frames = len(curve_data)
            logger.info(f"Successfully loaded {num_frames} tracking points")
            return (point_name, point_color, num_frames, curve_data)

        except Exception as e:
            logger.error(f"Error in fallback track importer: {e}")
            return None

    @classmethod
    def _load_track_from_file(cls, main_window: MainWindowProtocol, file_path: str) -> bool:
        """Load track data from a specific file path without showing a dialog.

        Args:
            main_window: The main window protocol
            file_path: Path to the track file

        Returns:
            True if successfully loaded, False otherwise
        """
        try:
            # Load track data from file using safe function calls
            result = cls.call_utils("track_importer", "load_3de_track", file_path)

            # Check if result is valid
            if not result or len(result) < 4 or not result[3]:  # result[3] is curve_data
                logger.error("Failed to load track data: Invalid data format")
                return False

            # Unpack the result
            point_name, point_color, _, curve_data = result  # num_frames is unused

            # Set the data with safe type conversion
            main_window.point_name = str(point_name) if point_name is not None else "Unknown"
            main_window.point_color = str(point_color) if point_color is not None else "red"
            main_window.curve_data = curve_data

            # Determine image dimensions from the data
            dimensions = cls.call_utils("curve_utils", "estimate_image_dimensions", curve_data)
            if dimensions and len(dimensions) == 2:
                main_window.image_width, main_window.image_height = dimensions
            else:
                # Default values if estimation fails
                main_window.image_width, main_window.image_height = 1920, 1080
                logger.warning("Using default image dimensions 1920x1080")

            # Update view
            main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height)

            # Enable controls - only enable buttons that exist
            # Note: export_button is not in MainWindowProtocol, we need to use dynamic attribute access
            if hasattr(main_window, 'export_button'):
                # Use getattr with Any type to avoid type checking issues
                export_button = getattr(main_window, 'export_button')
                if hasattr(export_button, 'setEnabled'):
                    export_button.setEnabled(True)
            if hasattr(main_window, 'add_point_button'):
                main_window.add_point_button.setEnabled(True)
            if hasattr(main_window, 'smooth_button'):
                main_window.smooth_button.setEnabled(True)
            if hasattr(main_window, 'fill_gaps_button'):
                main_window.fill_gaps_button.setEnabled(True)
            if hasattr(main_window, 'filter_button'):
                main_window.filter_button.setEnabled(True)
            if hasattr(main_window, 'detect_problems_button'):
                main_window.detect_problems_button.setEnabled(True)
            if hasattr(main_window, 'extrapolate_button'):
                main_window.extrapolate_button.setEnabled(True)

            # Update info
            main_window.info_label.setText(f"Loaded: {main_window.point_name} ({len(main_window.curve_data)} frames)")

            # Setup timeline - let the UI components calculate the frame range from curve_data
            main_window.setup_timeline()

            # Enable timeline controls if they exist
            if hasattr(main_window, 'timeline_slider'):
                main_window.timeline_slider.setEnabled(True)
            if hasattr(main_window, 'frame_edit'):
                main_window.frame_edit.setEnabled(True)
            if hasattr(main_window, 'go_button'):
                main_window.go_button.setEnabled(True)

            # Save the file path to config - fixed config keys to use the correct names
            folder_path = os.path.dirname(file_path)

            # Update last_file_path instead of set_last_file_path (the config key, not the function name)
            cls.set_config_value("last_file_path", file_path)
            cls.set_config_value("last_folder_path", folder_path)

            # Store as last_opened_file to avoid reopening in load_previous_file
            main_window.last_opened_file = file_path

            return True

        except Exception as e:
            logger.error(f"Error loading track data from file: {e}")
            return False

    @classmethod
    def _fallback_export_to_csv(cls, file_path: str, point_name: str, curve_data: PointsList,
                                image_width: int, image_height: int) -> bool:
        """Fallback implementation for exporting track data to CSV.

        Args:
            file_path: Path to save the CSV file
            point_name: Name of the tracking point
            curve_data: List of tracking points
            image_width: Image width (for metadata)
            image_height: Image height (for metadata)

        Returns:
            True if export was successful, False otherwise
        """
        logger.info(f"Using fallback CSV exporter for file: {file_path}")

        if not curve_data:
            logger.warning("No curve data to export")
            return False

        try:
            with open(file_path, 'w') as f:
                # Write metadata as comments
                f.write(f"# Point Name: {point_name}\n")
                f.write(f"# Image Dimensions: {image_width} x {image_height}\n")
                f.write(f"# Number of Points: {len(curve_data)}\n")
                f.write("#\n")

                # Write header
                f.write("Frame,X,Y,Status\n")

                # Write data
                for point in sorted(curve_data, key=lambda p: int(p[0])):
                    frame = point[0]
                    x = point[1]
                    y = point[2]
                    status = point[3] if len(point) > 3 else "valid"
                    f.write(f"{frame},{x},{y},{status}\n")

            logger.info(f"Successfully exported {len(curve_data)} points to CSV: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error in fallback CSV export: {e}")
            return False

    @staticmethod
    def load_track_data(main_window: MainWindowProtocol) -> None:
        """Load 2D track data from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            main_window.qwidget, "Load 2D Track Data", main_window.default_directory, "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Load track data from file using safe function calls
            result = FileService.call_utils("track_importer", "load_3de_track", file_path)

            # Check if result is valid
            if not result or len(result) < 4 or not result[3]:  # result[3] is curve_data
                logger.error("Failed to load track data: Invalid data format")
                QMessageBox.critical(main_window.qwidget, "Error", "Failed to load track data: Invalid format")
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

            # Enable controls - only enable buttons that exist
            # Note: export_button is not in MainWindowProtocol, we need to use dynamic attribute access
            if hasattr(main_window, 'export_button'):
                # Use getattr with Any type to avoid type checking issues
                export_button = getattr(main_window, 'export_button')
                if hasattr(export_button, 'setEnabled'):
                    export_button.setEnabled(True)
            if hasattr(main_window, 'add_point_button'):
                main_window.add_point_button.setEnabled(True)
            if hasattr(main_window, 'smooth_button'):
                main_window.smooth_button.setEnabled(True)
            if hasattr(main_window, 'fill_gaps_button'):
                main_window.fill_gaps_button.setEnabled(True)
            if hasattr(main_window, 'filter_button'):
                main_window.filter_button.setEnabled(True)
            if hasattr(main_window, 'detect_problems_button'):
                main_window.detect_problems_button.setEnabled(True)
            if hasattr(main_window, 'extrapolate_button'):
                main_window.extrapolate_button.setEnabled(True)

            # Update info
            main_window.info_label.setText(f"Loaded: {main_window.point_name} ({len(main_window.curve_data)} frames)")

            # Setup timeline - let the UI components calculate the frame range from curve_data
            main_window.setup_timeline()

            # Enable timeline controls if they exist
            if hasattr(main_window, 'timeline_slider'):
                main_window.timeline_slider.setEnabled(True)
            if hasattr(main_window, 'frame_edit'):
                main_window.frame_edit.setEnabled(True)
            if hasattr(main_window, 'go_button'):
                main_window.go_button.setEnabled(True)

            # Save the file path to config - fixed config keys to use the correct names
            folder_path = os.path.dirname(file_path)

            # Update last_file_path instead of set_last_file_path (the config key, not the function name)
            FileService.set_config_value("last_file_path", file_path)
            FileService.set_config_value("last_folder_path", folder_path)

            # Store as last_opened_file to avoid reopening in load_previous_file
            main_window.last_opened_file = file_path

        except Exception as e:
            logger.error(f"Error loading track data: {e}")
            QMessageBox.critical(main_window.qwidget, "Error", f"Failed to load track data: {e}")
            return

    @staticmethod
    def load_previous_file(main_window: MainWindowProtocol) -> None:
        """Load the previously used file and folder if they exist.

        This method is called during application initialization to restore
        the previously opened file (if any).
        """
        try:
            # Check if there's a default directory saved in configuration
            default_dir = FileService.get_config_value("last_folder_path", "")
            if default_dir and os.path.isdir(default_dir):
                main_window.default_directory = default_dir
                logger.info(f"Restored previous working directory: {default_dir}")

            # Check if there's a previously opened file saved in configuration
            last_file = FileService.get_config_value("last_file_path", "")
            if last_file and os.path.isfile(last_file):
                logger.info(f"Loading previously opened file: {last_file}")
                # Set the file path but don't load it yet
                main_window.last_opened_file = last_file

                # Auto-load the file if it's a track file
                if last_file.endswith(".txt"):
                    # Check if we have a track data loading flag (added to MainWindow)
                    # to prevent duplicate loading
                    if hasattr(main_window, 'track_data_loaded') and not main_window.track_data_loaded:
                        logger.info(f"Automatically loading track data from: {last_file}")
                        # Use the new method to load without showing dialog
                        if FileService._load_track_from_file(main_window, last_file):
                            # Mark as loaded to prevent duplicate loading
                            if hasattr(main_window, 'track_data_loaded'):
                                main_window.track_data_loaded = True
                            logger.info(f"Successfully auto-loaded track data from {last_file}")
                        else:
                            logger.warning(f"Failed to auto-load track data from {last_file}")
        except Exception as e:
            logger.error(f"Error loading previous file settings: {e}")
            # Don't show error dialog as this is called during initialization
            # and failures here shouldn't interrupt startup

    @staticmethod
    def save_track_data(main_window: MainWindowProtocol) -> None:
        """Stub for saving 2D track data to a file."""
        # TODO: Implement actual save logic
        logger.info("Called save_track_data (stub). No action performed.")

    @staticmethod
    def load_previous_image_sequence(main_window: MainWindowProtocol) -> None:
        """Load the previously used image sequence if it exists.

        This method is called during application initialization to restore
        the previously loaded image sequence (if any). If no previous sequence
        is found, it will attempt to load the default Burger sequence from
        C:/footage/Burger.
        """
        try:
            # Check if there's a previously used image sequence path saved in config
            last_image_path = FileService.get_config_value("last_image_sequence_path", "")
            # Path to default Burger sequence
            default_burger_path = "C:/footage/Burger"

            # If no previous path or it doesn't exist, try the default Burger sequence
            if not last_image_path or not os.path.isdir(last_image_path):
                logger.info("No previous image sequence path found or path doesn't exist")
                if os.path.isdir(default_burger_path):
                    logger.info(f"Attempting to load default Burger sequence from: {default_burger_path}")
                    last_image_path = default_burger_path
                    # Save this as the last used path
                    FileService.set_config_value("last_image_sequence_path", default_burger_path)
                else:
                    logger.warning(f"Default Burger sequence path {default_burger_path} not found")
                    return
            else:
                logger.info(f"Attempting to load previous image sequence from: {last_image_path}")

            # Look for image files in the directory
            image_files: list[str] = []
            valid_extensions: list[str] = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".exr"]

            try:
                for file in os.listdir(last_image_path):
                    if any(file.lower().endswith(ext) for ext in valid_extensions):
                        image_files.append(file)

                if not image_files:
                    logger.warning(f"No valid image files found in {last_image_path}")
                    # If no images were found in the previous path, try the default Burger sequence
                    if last_image_path != default_burger_path and os.path.isdir(default_burger_path):
                        logger.info(f"Trying default Burger sequence as fallback")
                        last_image_path = default_burger_path
                        for file in os.listdir(default_burger_path):
                            if any(file.lower().endswith(ext) for ext in valid_extensions):
                                image_files.append(file)
                        if not image_files:
                            logger.warning(f"No valid image files found in default path {default_burger_path}")
                            return
                        # Update the config with the default path
                        FileService.set_config_value("last_image_sequence_path", default_burger_path)
                    else:
                        return

                # Sort filenames for consistent ordering
                image_files.sort()

                # Filter for Burger sequence pattern if we're using the default path
                if last_image_path == default_burger_path:
                    burger_files: list[str] = [f for f in image_files if f.startswith("Burger.") and f.endswith(".png")]
                    if burger_files:
                        image_files = burger_files

                # Set image sequence path and filenames
                main_window.image_sequence_path = last_image_path
                main_window.image_filenames = image_files

                # Configure the curve view to display the images
                if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'setImageSequence'):
                    main_window.curve_view.setImageSequence(
                        last_image_path,
                        image_files
                    )

                    # Update UI elements
                    if hasattr(main_window, 'update_image_label'):
                        main_window.update_image_label()
                    if hasattr(main_window, 'toggle_bg_button') and hasattr(main_window.toggle_bg_button, 'setEnabled'):
                        main_window.toggle_bg_button.setEnabled(True)

                    logger.info(f"Successfully loaded {len(image_files)} images from sequence at {last_image_path}")
                else:
                    logger.warning("Curve view not available or missing setImageSequence method")
            except Exception as e:
                logger.error(f"Error loading image files from directory: {e}")

        except Exception as e:
            logger.error(f"Error loading previous image sequence: {e}")
            # Don't show error dialog as this is called during initialization

    @staticmethod
    def add_track_data(main_window: MainWindowProtocol) -> None:
        """Add an additional 2D track to the current data."""
        from typing import cast, Any
        if not main_window.curve_data:
            return

        file_path: str
        _filter: str
        file_path, _filter = QFileDialog.getOpenFileName(
            main_window.qwidget, "Add 2D Track Data", main_window.default_directory, "Text Files (*.txt);;All Files (*)"
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
                    main_window.qwidget, "Frame Conflict",
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
