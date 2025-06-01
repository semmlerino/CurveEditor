#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""File service module for curve editor file operations.

This module provides the FileService class which handles all file-related
operations in the 3DE4 Curve Editor, including loading, saving, and exporting
tracking data.

The service implements lazy loading of dependent modules to avoid circular
imports and provides fallback implementations for core functionality.

Classes:
    FileService: Main service class for file operations.

Functions:
    safe_call: Safely calls functions from modules that might not be available.

Example:
    from services.file_service import FileService

    # Load track data
    file_service = FileService()
    file_service.load_track_data(main_window)



Note:
    This module uses lazy imports to avoid circular dependencies. Modules are
    imported only when their functionality is actually needed.

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
    """Safely call a function from a module that might not be available.

    This function provides a safe way to call functions from modules that
    might not be imported due to circular dependencies or missing dependencies.

    Args:
        module: The module containing the function to call, or None if unavailable.
        attr_name: Name of the function to call from the module.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The return value of the called function, or None if the function
        could not be called.

    Example:
        result = safe_call(utils_module, 'parse_data', filename, format='csv')

    """
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
    """Service class for file operations in the 3DE4 Curve Editor.

    This class provides static methods for handling all file-related operations
    including loading, saving, and exporting track data. It uses lazy loading
    to avoid circular imports and provides fallback implementations when
    dependencies are not available.

    The service integrates with the Qt framework for file dialogs and user
    interaction, and supports various file formats for import and export.

    Methods:
        get_config_value: Safely retrieves configuration values.
        set_config_value: Safely sets configuration values.
        call_utils: Safely calls utility functions from various modules.

        load_track_data: Loads tracking data from files.
        add_track_data: Adds additional tracking data to existing data.
        save_track_data: Saves current tracking data to a file.
        load_image_sequence: Loads a sequence of images.

    Example:
        # Export curve data to CSV
        FileService.export_to_csv(main_window)

        # Load track data from file
        FileService.load_track_data(main_window)

    Note:
        All methods are static to allow easy access without instantiation.
        The service handles missing dependencies gracefully with fallbacks.

    """

    @staticmethod
    def get_config_value(attr_name: str, default: Any = None) -> Any:
        """Safely get a value from the config module.

        Retrieves a configuration value from the config module if available.
        If the module is not loaded or the attribute doesn't exist, returns
        the default value.

        Args:
            attr_name: Name of the configuration attribute to retrieve.
            default: Default value to return if attribute is not found.
                Defaults to None.

        Returns:
            The configuration value if found, otherwise the default value.
            If the attribute is callable, returns the result of calling it.

        Example:
            # Get default directory
            directory = FileService.get_config_value('DEFAULT_DIRECTORY', '.')

            # Get a callable config value
            max_size = FileService.get_config_value('get_max_file_size', 1024)

        """
        if config_module is None:
            logger.error(f"Config module not available for {attr_name}")
            return default
        attr = getattr(config_module, attr_name, None)
        if callable(attr):
            return attr()
        return default

    @staticmethod
    def set_config_value(attr_name: str, value: Any) -> None:
        """Safely set a config value.

        Sets a configuration value in the config module if available.
        If the module is not loaded, logs an error and returns without
        setting the value.

        Args:
            attr_name: Name of the configuration attribute to set.
            value: Value to set for the configuration attribute.

        Returns:
            None

        Example:
            # Set default directory
            FileService.set_config_value('DEFAULT_DIRECTORY', '/home/user/data')

            # Set a numeric config value
            FileService.set_config_value('MAX_HISTORY_SIZE', 100)

        """
        if config_module is None:
            logger.error(f"Config module not available for {attr_name}")
            return
        setattr(config_module, attr_name, value)

    @classmethod
    def call_utils(cls, module_name: str, func_name: str, *args: Any, **kwargs: Any) -> Any:
        """Safely call a utils function from the specified module.

        Provides a centralized way to call utility functions from various
        modules with fallback implementations when modules are not available.
        This helps avoid circular imports and provides graceful degradation.

        Args:
            module_name: Name of the module containing the function.
                Supported modules: 'curve_utils', 'track_importer', 'track_exporter'.
            func_name: Name of the function to call.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The return value of the called function, or the result of a
            fallback implementation if the module is not available.

        Example:
            # Call estimate_image_dimensions from curve_utils
            dimensions = FileService.call_utils(
                'curve_utils', 'estimate_image_dimensions',
                curve_data, image_width, image_height
            )

            # Call load_3de_track from track_importer
            data = FileService.call_utils(
                'track_importer', 'load_3de_track',
                filepath
            )

        Note:
            If a module is not available, this method will attempt to use
            a fallback implementation if one exists.

        """
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

            return safe_call(track_exporter_module, func_name, *args, **kwargs)
        else:
            logger.error(f"Unknown or unavailable module: {module_name}")
            return None

    @classmethod
    def _fallback_estimate_image_dimensions(cls, curve_data: PointsList) -> Tuple[int, int]:
        """Fallback implementation for estimating image dimensions from curve data.

        This function estimates a reasonable image size based on the coordinates
        in the tracking data. It's used when the curve_utils module is not available.

        Args:
            curve_data: List of tracking points containing frame, x, y coordinates.

        Returns:
            Tuple[int, int]: A tuple (width, height) representing the estimated
                image dimensions. Returns default 1920x1080 if estimation fails.

        Example:
            dimensions = cls._fallback_estimate_image_dimensions(curve_data)
            width, height = dimensions

        Note:
            The estimation adds 20% padding to the maximum coordinates found
            in the curve data to ensure all points are visible.

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
        """Fallback implementation for loading 3DE track data.

        Provides basic parsing of 3DE track data files when the track_importer
        module is not available. Supports both headerless and 2DTrackData format files.

        Args:
            file_path: Path to the track data file to load.

        Returns:
            Optional[Tuple[str, str, int, PointsList]]: A tuple containing:
                - point_name: Name extracted from the filename
                - point_color: Default color (#FF0000)
                - num_frames: Total number of frames in the track
                - curve_data: List of tracking points
            Returns None if loading fails.

        Example:
            result = cls._fallback_load_3de_track('/path/to/track.txt')
            if result:
                name, color, frames, data = result

        Note:
            Supports two formats:
            1. Headerless: Direct frame x y data per line
            2. 2DTrackData: 4-line header followed by frame x y data

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

    @staticmethod
    def load_track_data(main_window: MainWindowProtocol) -> None:
        """Load 2D track data from a file.

        Opens a file dialog for the user to select a track data file,
        loads the data, and updates the main window with the loaded
        curve information. Automatically estimates image dimensions if
        not provided in the data.

        Args:
            main_window: The main window instance to update with loaded data.

        Returns:
            None

        Example:
            FileService.load_track_data(main_window)

        Note:
            - Supports both headerless and 2DTrackData format files
            - Enables relevant UI controls after successful loading
            - Sets up timeline based on loaded frame range
            - Updates status with loaded point name and frame count

        Side Effects:
            - Updates main_window.curve_data with loaded points
            - Updates main_window.point_name and point_color
            - Enables various UI controls
            - Calls main_window.setup_timeline()

        """
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
        except Exception as e:
            logger.exception(f"Failed to load track data: {e}")
            QMessageBox.critical(main_window.qwidget, "Error", f"Failed to load track data: {e}")

    @staticmethod
    def load_previous_file(main_window: MainWindowProtocol) -> None:
        """Load the previously used file and folder if they exist.

        This method is called during application initialization to restore
        the previously opened file path and working directory from saved
        configuration. Does not actually load the file content by default.

        Args:
            main_window: The main window instance to update with previous
                file information.

        Returns:
            None

        Example:
            # Called during initialization
            FileService.load_previous_file(main_window)

        Note:
            - Silently handles errors to avoid interrupting application startup
            - Only restores paths if they still exist on the filesystem
            - Does not automatically load file content (uncomment line 640 to enable)

        Side Effects:
            - Sets main_window.default_directory if previous directory exists
            - Sets main_window.last_opened_file if previous file exists

        """
        try:
            # Check if there's a default directory saved in configuration
            default_dir = FileService.get_config_value("default_directory", "")
            if default_dir and os.path.isdir(default_dir):
                main_window.default_directory = default_dir
                logger.info(f"Restored previous working directory: {default_dir}")

            # Check if there's a previously opened file saved in configuration
            last_file = FileService.get_config_value("last_opened_file", "")
            if last_file and os.path.isfile(last_file):
                logger.info(f"Loading previously opened file: {last_file}")
                # Set the file path but don't load it yet
                main_window.last_opened_file = last_file
                # Optional: auto-load the file (uncomment if desired)
                # FileService.load_track_data_from_path(main_window, last_file)
        except Exception as e:
            logger.error(f"Error loading previous file settings: {e}")
            # Don't show error dialog as this is called during initialization
            # and failures here shouldn't interrupt startup

    @staticmethod
    def load_previous_image_sequence(main_window: MainWindowProtocol) -> None:
        """Load the previously used image sequence if it exists.

        This method is called during application initialization to restore
        the previously loaded image sequence. Falls back to a default Burger
        sequence if no previous sequence is found or accessible.

        Args:
            main_window: The main window instance to update with the
                loaded image sequence.

        Returns:
            None

        Example:
            # Called during initialization
            FileService.load_previous_image_sequence(main_window)

        Note:
            - Checks for previously used sequence from configuration
            - Falls back to default Burger sequence at C:/footage/Burger
            - Silently handles errors to avoid interrupting startup
            - Only loads sequences with supported image formats

        Side Effects:
            - Updates main_window.image_sequence_path
            - Updates main_window.image_filenames
            - Calls main_window.setImageSequence()
            - Updates configuration with loaded path

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
        """Add an additional 2D track to the current data.

        Opens a file dialog to select additional track data and merges it
        with the existing curve data. Handles frame conflicts by prompting
        the user for resolution strategy.

        Args:
            main_window: The main window instance containing existing curve
                data to merge with.

        Returns:
            None

        Example:
            # Add more tracking data to existing curve
            FileService.add_track_data(main_window)

        Note:
            - Requires existing curve data to be loaded first
            - Prompts user when frame conflicts are detected
            - Scales additional data to match current image dimensions
            - Currently a stub implementation when track_importer is unavailable

        Side Effects:
            - Updates main_window.curve_data with merged points
            - Updates timeline if new frames extend the range
            - Adds operation to history for undo functionality

        """
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
