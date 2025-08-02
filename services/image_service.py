#!/usr/bin/env python

"""
ImageService: Service class for image operations.
Provides functionality for loading and manipulating image sequences.
"""

import os
from typing import Any, cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

import config
from core.protocols import CurveViewProtocol, ImageSequenceProtocol, MainWindowProtocol
from services.logging_service import LoggingService
from services.settings_service import SettingsService

# Configure logger for this module
logger = LoggingService.get_logger("image_service")


class ImageService:
    """Service class for image operations in the 3DE4 Curve Editor."""

    @staticmethod
    def set_current_image_by_frame(curve_view: CurveViewProtocol, frame: int) -> None:
        """Set the current background image based on frame number.

        Args:
            curve_view: The curve view instance
            frame: Frame number to find the closest image for
        """
        if not hasattr(curve_view, "image_filenames"):
            return

        # Find the closest image index to the requested frame
        closest_idx: int = -1
        min_diff: float = float("inf")

        image_filenames = getattr(curve_view, "image_filenames", [])
        for i, filename in enumerate(image_filenames):
            try:
                parts = os.path.basename(filename).split(".")
                if len(parts) >= 2 and parts[-2].isdigit():
                    frame_number = int(parts[-2])
                else:
                    name_parts = parts[0].split("_")
                    if len(name_parts) > 1 and name_parts[-1].isdigit():
                        frame_number = int(name_parts[-1])
                    else:
                        frame_number = i
            except (ValueError, IndexError):
                frame_number = i

            diff = abs(frame_number - frame)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i

        if 0 <= closest_idx < len(image_filenames):
            curve_view.current_image_idx = closest_idx
            ImageService.load_current_image(curve_view)
            if hasattr(curve_view, "update"):
                curve_view.update()

    @staticmethod
    def load_current_image(curve_view: ImageSequenceProtocol) -> None:
        """Load the current image in the sequence.

        Args:
            curve_view: The curve view instance containing image properties
        """
        # Defensive: do not assume curve_view has main_window, check for required attributes directly
        if not hasattr(curve_view, "current_image_idx") or not hasattr(curve_view, "image_filenames"):
            curve_view.background_image = None
            return
        if curve_view.current_image_idx < 0:
            curve_view.background_image = None
            return

        try:
            # Get path to current image
            image_path = os.path.join(
                curve_view.image_sequence_path, curve_view.image_filenames[curve_view.current_image_idx]
            )
            logger.debug(f"Loading image: {image_path}")

            # Load image using PySide6.QtGui.QImage
            image: QImage = QImage(image_path)

            # Make sure we have focus to receive keyboard events
            if hasattr(curve_view, "setFocus"):
                curve_view.setFocus()

            if image.isNull():
                logger.error(f"Failed to load image: {image_path}")
                curve_view.background_image = None
            else:
                logger.debug(f"Successfully loaded image from: {image_path}")
                # Store the QPixmap in a member variable to prevent it from being garbage collected
                # This is important to avoid the "QPaintDevice: Cannot destroy paint device that is being painted" error
                pixmap: QPixmap = QPixmap.fromImage(image)
                curve_view.background_image = pixmap

                # Update track dimensions to match image dimensions
                if curve_view.scale_to_image:
                    curve_view.image_width = image.width()
                    curve_view.image_height = image.height()

                # Emit the image_changed signal
                logger.debug(f"Emitting image_changed signal for idx={curve_view.current_image_idx}")
                curve_view.image_changed.emit(curve_view.current_image_idx)

                # Update status using centralized StatusManager
                if hasattr(curve_view, "main_window") and curve_view.main_window:
                    from services.status_manager import StatusManager

                    StatusManager.on_image_data_loaded(curve_view.main_window)

                # Mark that we need to fit content (will happen on next paint)
                if hasattr(curve_view, "_needs_initial_fit"):
                    curve_view._needs_initial_fit = True
        except FileNotFoundError as e:
            logger.error(f"Image file not found: {str(e)}")
            curve_view.background_image = None
            # Update status when image loading fails
            if hasattr(curve_view, "main_window") and curve_view.main_window:
                from services.status_manager import StatusManager

                StatusManager.update_status(curve_view.main_window)
        except OSError as e:
            logger.error(f"Error reading image file: {str(e)}")
            curve_view.background_image = None
            # Update status when image loading fails
            if hasattr(curve_view, "main_window") and curve_view.main_window:
                from services.status_manager import StatusManager

                StatusManager.update_status(curve_view.main_window)
        except Exception as e:
            # Keep generic fallback for unexpected errors
            logger.error(f"Unexpected error loading image: {e.__class__.__name__}: {str(e)}")
            curve_view.background_image = None
            # Update status when image loading fails
            if hasattr(curve_view, "main_window") and curve_view.main_window:
                from services.status_manager import StatusManager

                StatusManager.update_status(curve_view.main_window)

    @staticmethod
    def set_current_image_by_index(curve_view: ImageSequenceProtocol, idx: int) -> None:
        """Set current image by index and update the view.

        Args:
            curve_view: The curve view instance
            idx: Index of the image to display
        """
        if idx < 0 or idx >= len(curve_view.image_filenames):
            logger.warning(f"Invalid image index: {idx}")
            return

        # Store current zoom factor and view offsets
        # Update image index and load the image
        curve_view.current_image_idx = idx
        ImageService.load_current_image(curve_view)

        # After changing the image, center on the selected point using our improved function
        point: tuple[float, float, float] | None = None
        center_pos: tuple[float, float] | None = None
        curve_data: Any = None
        if hasattr(curve_view, "selected_point_idx") and hasattr(curve_view, "main_window"):
            main_window = getattr(curve_view, "main_window", None)
            selected_idx = getattr(curve_view, "selected_point_idx", -1)
            if main_window is not None and hasattr(main_window, "curve_data") and selected_idx >= 0:
                try:
                    curve_data = getattr(main_window, "curve_data", None)
                    if curve_data is not None:
                        point = curve_data[selected_idx]
                        if isinstance(point, tuple) and len(point) == 3:
                            center_pos = (point[1], point[2])  # x, y coordinates
                            logger.debug(f"Storing center position at {center_pos}")
                except (IndexError, AttributeError) as e:
                    logger.error(f"Could not store center position: {str(e)}")
        if hasattr(curve_view, "centerOnSelectedPoint"):
            center_fn = getattr(curve_view, "centerOnSelectedPoint", None)
            if callable(center_fn):
                success: bool = False
                try:
                    result = center_fn()
                    success = bool(result)
                except TypeError:
                    try:
                        result = center_fn(preserve_zoom=True)
                        success = bool(result)
                    except (TypeError, AttributeError) as e:
                        logger.debug(f"centerOnSelectedPoint with preserve_zoom failed: {e}")
                        success = False
                if success:
                    logger.debug(f"Successfully centered on point {getattr(curve_view, 'selected_point_idx', '?')}")
        if hasattr(curve_view, "setImageSequence"):
            curve_view.setImageSequence(curve_view.image_sequence_path, curve_view.image_filenames)
            if hasattr(curve_view, "current_image_idx"):
                curve_view.current_image_idx = idx
            update_fn = getattr(curve_view, "update", None)
            if callable(update_fn):
                update_fn()
            set_focus_fn = getattr(curve_view, "setFocus", None)
            if callable(set_focus_fn):
                set_focus_fn()
        if isinstance(curve_view, CurveViewProtocol):
            update_fn = getattr(curve_view, "update", None)
            if callable(update_fn):
                update_fn()
            set_focus_fn = getattr(curve_view, "setFocus", None)
            if callable(set_focus_fn):
                set_focus_fn()

    @staticmethod
    def load_image_sequence(main_window: MainWindowProtocol) -> None:
        """Load an image sequence to use as background."""
        # Open dialog to select directory containing image sequence
        options = QFileDialog.Option.DontUseNativeDialog

        directory = QFileDialog.getExistingDirectory(
            main_window.qwidget if hasattr(main_window, "qwidget") else None,
            "Select Directory Containing Image Sequence",
            main_window.default_directory,
            options,
        )

        if not directory:
            return  # User canceled

        config.set_last_folder_path(directory)
        config.set_last_image_sequence_path(directory)

        # Find all image files in the directory
        main_window.image_sequence_path = directory
        main_window.image_filenames = []

        # List all files in the directory
        all_files = os.listdir(directory)
        valid_extensions = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".exr"]

        # Filter for valid image files
        for file in all_files:
            file_lower = file.lower()
            if any(file_lower.endswith(ext) for ext in valid_extensions):
                main_window.image_filenames.append(file)

        # Sort the filenames (they should sort naturally by frame number)
        main_window.image_filenames.sort()

        if not main_window.image_filenames:
            QMessageBox.warning(
                main_window.qwidget if hasattr(main_window, "qwidget") else None,
                "No Images Found",
                "Could not find any matching images in the sequence.",
            )
            return

        # Set the image sequence in the curve view
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        # Configure curve view to use the image sequence
        if hasattr(main_window, "curve_view"):
            main_window.curve_view.setImageSequence(directory, main_window.image_filenames)

        # Update the UI
        if hasattr(main_window, "update_image_label"):
            main_window.update_image_label()
        if hasattr(main_window, "toggle_bg_button") and hasattr(main_window.toggle_bg_button, "setEnabled"):
            main_window.toggle_bg_button.setEnabled(True)

        # Update status to reflect loaded images
        from services.status_manager import StatusManager
        StatusManager.update_status(main_window)

        # Show a success message
        QMessageBox.information(
            main_window.qwidget if hasattr(main_window, "qwidget") else None,
            "Image Sequence Loaded",
            f"Loaded {len(main_window.image_filenames)} images from sequence.",
            QMessageBox.StandardButton.Ok,
        )

    @staticmethod
    def _parse_filename(filename: str) -> tuple[str | None, str | None, str]:
        """Parse a filename to extract base name, frame number and extension.

        Args:
            filename: The filename to parse

        Returns: tuple of (base_name, frame_num, ext)
        """
        # Split the filename by extension
        main_part, ext = os.path.splitext(filename)
        if not ext:
            return None, None, ""

        # Look for patterns like name.1234.ext
        dot_parts = main_part.split(".")
        if len(dot_parts) > 1 and dot_parts[-1].isdigit():
            frame_num = dot_parts[-1]
            base_name = ".".join(dot_parts[:-1]) + "."
            return base_name, frame_num, ext

        # Look for patterns like name_1234.ext
        underscore_parts = main_part.split("_")
        return ImageService._parse_filename_parts(underscore_parts, ext)

    @staticmethod
    def _parse_filename_parts(parts: list[str], ext: str) -> tuple[str | None, str | None, str]:
        """Parse filename parts to extract base name and frame number.

        Args:
            parts: Parts of the filename
            ext: File extension

        Returns: tuple of (base_name, frame_num, ext)
        """
        if len(parts) > 1 and parts[-1].isdigit():
            inner_frame_num: str = parts[-1]
            inner_base_name: str = "_".join(parts[:-1]) + "_"
            return inner_base_name, inner_frame_num, ext
        # Always return a tuple
        return None, None, ext

    @staticmethod
    def next_image(main_window: MainWindowProtocol) -> None:
        """Show the next image in the sequence."""
        curve_view: Any | None = getattr(main_window, "curve_view", None)
        if curve_view is None:
            return
        # Use stricter type guards to ensure curve_view has required attributes
        if not hasattr(curve_view, "current_image_idx") or not hasattr(curve_view, "setCurrentImageByIndex"):
            # If curve_view does not have required attributes, log an error and return
            logger.error("curve_view is missing required attributes")
            return
        # Use cast to help type checker and avoid type: ignore
        cv = cast(CurveViewProtocol, curve_view)
        if cv.current_image_idx >= len(main_window.image_filenames) - 1:
            return
        new_idx = cv.current_image_idx + 1
        cv.setCurrentImageByIndex(new_idx)
        # Update main window current_frame to match
        main_window.current_frame = new_idx

    @staticmethod
    def previous_image(main_window: MainWindowProtocol) -> None:
        """Show the previous image in the sequence."""
        curve_view: Any | None = getattr(main_window, "curve_view", None)
        if curve_view is None:
            return
        # Use stricter type guards to ensure curve_view has required attributes
        if not hasattr(curve_view, "current_image_idx") or not hasattr(curve_view, "setCurrentImageByIndex"):
            # If curve_view does not have required attributes, log an error and return
            logger.error("curve_view is missing required attributes")
            return
        # Use cast to help type checker and avoid type: ignore
        cv = cast(CurveViewProtocol, curve_view)
        if cv.current_image_idx <= 0:
            return
        new_idx = cv.current_image_idx - 1
        cv.setCurrentImageByIndex(new_idx)
        # Update main window current_frame to match
        main_window.current_frame = new_idx

    @staticmethod
    def prev_image(main_window: MainWindowProtocol) -> None:
        """Alias for previous_image to maintain API compatibility."""
        ImageService.previous_image(main_window)

    @staticmethod
    def go_to_frame(main_window: MainWindowProtocol, frame: int) -> None:
        """Go to a specific frame in the image sequence.

        Args:
            main_window: The main window instance
            frame: Target frame number (will be clamped to valid range)
        """
        if not hasattr(main_window, "image_filenames") or not main_window.image_filenames:
            return

        # Clamp frame to valid range
        max_frame = len(main_window.image_filenames) - 1
        clamped_frame = max(0, min(max_frame, frame))

        # Update current frame
        main_window.current_frame = clamped_frame

        # Set image by index if curve_view exists
        curve_view = getattr(main_window, "curve_view", None)
        if curve_view and hasattr(curve_view, "setCurrentImageByIndex"):
            curve_view.setCurrentImageByIndex(clamped_frame)

    @staticmethod
    def toggle_background_visible(main_window: MainWindowProtocol) -> None:
        """Toggle the visibility of the background image."""
        curve_view: Any | None = getattr(main_window, "curve_view", None)
        if curve_view is None:
            return
        visible: bool = not getattr(curve_view, "show_background", False)
        if hasattr(curve_view, "toggleBackgroundVisible"):
            curve_view.toggleBackgroundVisible(visible)
        main_window.toggle_bg_button.setText("Hide Background" if visible else "Show Background")

    @staticmethod
    def toggle_background(main_window: MainWindowProtocol) -> None:
        """Alias for toggle_background_visible for backward compatibility."""
        ImageService.toggle_background_visible(main_window)

    @staticmethod
    def opacity_changed(main_window: MainWindowProtocol, value: float) -> None:
        """Change the opacity of the background image.

        Args:
            main_window: The main window instance
            value: Opacity value between 0.0 and 1.0
        """
        # Ensure value is within valid range
        opacity = max(0.0, min(1.0, value))

        # Get curve view if it exists
        curve_view = getattr(main_window, "curve_view", None)
        if curve_view is None:
            return

        # Set opacity if the method exists
        if hasattr(curve_view, "setBackgroundOpacity"):
            curve_view.setBackgroundOpacity(opacity)
        # Or try alternative attribute name
        elif hasattr(curve_view, "background_opacity"):
            curve_view.background_opacity = opacity

        # Trigger update if possible
        if hasattr(curve_view, "update"):
            curve_view.update()

    @staticmethod
    def set_image_sequence(curve_view: ImageSequenceProtocol, path: str, filenames: list[str]) -> None:
        """Set the image sequence to display as background.

        Args:
            curve_view: The curve view instance
            path: Path to the directory containing the image sequence
            filenames: list of image filenames in the sequence
        """
        curve_view.image_sequence_path = path
        curve_view.image_filenames = filenames
        curve_view.current_image_idx = 0 if filenames else -1
        ImageService.load_current_image(curve_view)
        # Mark that we need to fit content (will happen on next paint)
        if hasattr(curve_view, "_needs_initial_fit"):
            curve_view._needs_initial_fit = True
        curve_view.update()

    def set_image_sequence_instance(self, curve_view: ImageSequenceProtocol, path: str, filenames: list[str]) -> None:
        """Instance method for protocol compatibility. Delegates to static method set_image_sequence."""
        ImageService.set_image_sequence(curve_view, path, filenames)

    @staticmethod
    def update_image_label(main_window: MainWindowProtocol) -> None:
        """Update the image label with current image info.

        Args:
            main_window: The main window instance containing the image label
        """
        # Check if required attributes exist
        curve_view = getattr(main_window, "curve_view", None)
        if curve_view is None or not hasattr(curve_view, "current_image_idx"):
            return

        # Get current image information
        current_idx = curve_view.current_image_idx
        total_images = len(getattr(main_window, "image_filenames", []))

        # Update label if it exists
        if hasattr(main_window, "image_label") and hasattr(main_window.image_label, "setText"):
            if current_idx >= 0 and total_images > 0 and current_idx < total_images:
                # Get image filename with proper type checking
                image_filenames: list[str] = getattr(main_window, "image_filenames", [])
                if image_filenames and 0 <= current_idx < len(image_filenames):
                    # Use cast to help type checker understand this is definitely a string
                    filename: str = cast(str, image_filenames[current_idx])
                    # Now we know filename is definitely a string
                    image_name: str = os.path.basename(filename)
                    main_window.image_label.setText(f"Image: {current_idx + 1}/{total_images} - {image_name}")
                else:
                    main_window.image_label.setText(f"Image: {current_idx + 1}/{total_images}")
            else:
                main_window.image_label.setText("No images loaded")

    @staticmethod
    def load_previous_image_sequence(main_window: MainWindowProtocol) -> None:
        """Load the previously used image sequence from settings.

        If no previous sequence is found, attempts to load the default burger sequence.

        Args:
            main_window: The main window instance
        """
        # Get curve view if it exists
        curve_view = getattr(main_window, "curve_view", None)
        if curve_view is None:
            logger.error("Cannot load previous image sequence: curve_view not found")
            return

        # Try to load from settings
        # Get previous image path from settings
        image_path = SettingsService.get_setting("last_image_path", "", str)

        if image_path and os.path.isdir(image_path):
            logger.info(f"Loading previous image sequence from: {image_path}")
            # Load all image files from the directory
            image_files: list[str] = []
            for filename in os.listdir(image_path):
                filename_str: str = str(filename)  # Ensure we have a string
                file_path: str = os.path.join(image_path, filename_str)
                if os.path.isfile(file_path) and any(
                    filename_str.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"]
                ):
                    image_files.append(filename_str)

            if image_files:
                # Sort files to ensure correct sequence order
                image_files.sort()

                # Configure curve view to use the image sequence
                if hasattr(main_window, "curve_view"):
                    ImageService.set_image_sequence(main_window.curve_view, image_path, image_files)  # type: ignore[arg-type]
                    logger.info(f"Loaded {len(image_files)} images from previous path")
            else:
                logger.warning(f"No image files found in previous path: {image_path}")
                # Fall back to default burger sequence
                ImageService._load_default_burger_sequence(main_window)
        else:
            # Try to load default burger sequence
            ImageService._load_default_burger_sequence(main_window)

    @staticmethod
    def _load_default_burger_sequence(main_window: MainWindowProtocol) -> None:
        """Load the default sample image sequence from the footage folder.

        Args:
            main_window: The main window instance
        """
        # Get curve view if it exists
        curve_view = getattr(main_window, "curve_view", None)
        if curve_view is None:
            logger.error("Cannot load sample footage: curve_view not found")
            return

        # Try to find the sample data directory in the footage/Burger folder
        default_path: str = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "footage", "Burger"
        )

        if os.path.isdir(default_path):
            logger.info(f"Loading sample footage from: {default_path}")
            # Find image files in the burger directory
            image_files: list[str] = []
            for filename in os.listdir(default_path):
                filename_str: str = str(filename)  # Ensure we have a string
                file_path: str = os.path.join(default_path, filename_str)
                if os.path.isfile(file_path) and any(
                    filename_str.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".bmp"]
                ):
                    image_files.append(filename_str)

            if image_files:
                # Sort files to ensure correct sequence order
                image_files.sort()

                # Set the image sequence
                ImageService.set_image_sequence(curve_view, default_path, image_files)  # type: ignore[arg-type]

                # Save this path as the last used path
                SettingsService.set_setting("last_image_path", default_path)

                logger.info(f"Loaded {len(image_files)} images from sample footage directory")
            else:
                logger.warning(f"No image files found in sample footage directory: {default_path}")
        else:
            logger.warning(f"Sample footage directory not found at: {default_path}")


# End of class ImageService
