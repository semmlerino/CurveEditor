#!/usr/bin/env python
"""
Instance-based ImageService with dependency injection.

This service provides image loading and manipulation functionality
using dependency injection for better testability.
"""

import os
from pathlib import Path
from typing import Any

from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from services.service_protocols import LoggingServiceProtocol, StatusServiceProtocol

class ImageService:
    """Instance-based image service with dependency injection."""

    def __init__(
        self,
        logging_service: LoggingServiceProtocol | None = None,
        status_service: StatusServiceProtocol | None = None,
    ):
        """Initialize ImageService with optional dependencies.

        Args:
            logging_service: Optional logging service
            status_service: Optional status service for user feedback
        """
        self._logger = logging_service
        self._status = status_service
        self._supported_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
        self._image_cache: dict[str, QImage] = {}
        self._max_cache_size = 50  # Maximum number of cached images

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

            if hasattr(curve_view, "update"):
                curve_view.update()

            if self._logger:
                self._logger.log_debug(f"Set image to index {closest_idx} for frame {frame}")

    def load_current_image(self, curve_view: Any) -> QImage | None:
        """Load the current image for the curve view.

        Args:
            curve_view: The curve view instance

        Returns:
            Loaded QImage or None if failed
        """
        # Check if curve view has required attributes
        if not self._has_image_attributes(curve_view):
            curve_view.background_image = None
            return None

        if curve_view.current_image_idx < 0:
            curve_view.background_image = None
            return None

        try:
            # Get path to current image
            image_path = os.path.join(
                curve_view.image_sequence_path,
                curve_view.image_filenames[curve_view.current_image_idx]
            )

            # Check cache first
            if image_path in self._image_cache:
                image = self._image_cache[image_path]
                if self._logger:
                    self._logger.log_debug(f"Loaded image from cache: {image_path}")
            else:
                # Load image
                image = QImage(image_path)

                if image.isNull():
                    raise ValueError(f"Failed to load image: {image_path}")

                # Add to cache
                self._add_to_cache(image_path, image)

                if self._logger:
                    self._logger.log_debug(f"Loaded image: {image_path}")

            # Convert to pixmap and set on curve view
            curve_view.background_image = QPixmap.fromImage(image)

            # Update status if available
            if self._status:
                filename = os.path.basename(image_path)
                self._status.show_info(f"Image: {filename}")

            # Make sure we have focus for keyboard events
            if hasattr(curve_view, "setFocus"):
                curve_view.setFocus()

            return image

        except Exception as e:
            error_msg = f"Failed to load image: {e}"

            if self._logger:
                self._logger.log_error(error_msg, e)

            curve_view.background_image = None
            return None

    def get_image_info(self, image_path: str) -> dict[str, Any]:
        """Get information about an image.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with image information
        """
        info = {
            'path': image_path,
            'exists': False,
            'width': 0,
            'height': 0,
            'format': '',
            'size_bytes': 0,
        }

        try:
            if not os.path.exists(image_path):
                return info

            info['exists'] = True
            info['size_bytes'] = os.path.getsize(image_path)

            # Load image to get dimensions
            image = QImage(image_path)
            if not image.isNull():
                info['width'] = image.width()
                info['height'] = image.height()
                info['format'] = os.path.splitext(image_path)[1].lower()

            return info

        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to get image info: {e}")
            return info

    def navigate_to_next_image(self, curve_view: Any) -> bool:
        """Navigate to next image in sequence.

        Args:
            curve_view: The curve view instance

        Returns:
            True if navigation successful, False otherwise
        """
        if not self._has_image_attributes(curve_view):
            return False

        image_filenames = getattr(curve_view, "image_filenames", [])
        if not image_filenames:
            return False

        current_idx = curve_view.current_image_idx

        if current_idx < len(image_filenames) - 1:
            curve_view.current_image_idx = current_idx + 1
            self.load_current_image(curve_view)

            if hasattr(curve_view, "update"):
                curve_view.update()

            if self._logger:
                self._logger.log_debug(f"Navigated to next image: index {curve_view.current_image_idx}")

            return True

        return False

    def navigate_to_previous_image(self, curve_view: Any) -> bool:
        """Navigate to previous image in sequence.

        Args:
            curve_view: The curve view instance

        Returns:
            True if navigation successful, False otherwise
        """
        if not self._has_image_attributes(curve_view):
            return False

        image_filenames = getattr(curve_view, "image_filenames", [])
        if not image_filenames:
            return False

        current_idx = curve_view.current_image_idx

        if current_idx > 0:
            curve_view.current_image_idx = current_idx - 1
            self.load_current_image(curve_view)

            if hasattr(curve_view, "update"):
                curve_view.update()

            if self._logger:
                self._logger.log_debug(f"Navigated to previous image: index {curve_view.current_image_idx}")

            return True

        return False

    def browse_for_image_sequence(self, parent_widget: QWidget) -> tuple[str, list[str]] | None:
        """Open dialog to browse for image sequence directory.

        Args:
            parent_widget: Parent widget for dialog

        Returns:
            Tuple of (directory_path, image_filenames) or None if cancelled
        """
        directory = QFileDialog.getExistingDirectory(
            parent_widget,
            "Select Image Sequence Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not directory:
            return None

        image_files = self.load_image_sequence(directory)

        if not image_files:
            QMessageBox.warning(
                parent_widget,
                "No Images Found",
                f"No supported image files found in:\n{directory}"
            )
            return None

        return directory, image_files

    def clear_cache(self) -> None:
        """Clear the image cache."""
        self._image_cache.clear()

        if self._logger:
            self._logger.log_debug("Cleared image cache")

    def set_cache_size(self, size: int) -> None:
        """Set maximum cache size.

        Args:
            size: Maximum number of images to cache
        """
        self._max_cache_size = max(1, size)
        self._trim_cache()

    # Private helper methods

    def _sort_by_frame_number(self, filenames: list[str]) -> list[str]:
        """Sort filenames by extracted frame number."""
        def extract_frame_number(filename: str) -> int:
            """Extract frame number from filename."""
            try:
                # Try to extract number from filename
                parts = os.path.splitext(filename)[0].split('_')
                for part in reversed(parts):
                    if part.isdigit():
                        return int(part)

                # Try to extract from extension prefix (e.g., file.0001.png)
                parts = filename.split('.')
                if len(parts) >= 2:
                    for part in parts[:-1]:
                        if part.isdigit():
                            return int(part)

                return 0
            except Exception:
                return 0

        return sorted(filenames, key=extract_frame_number)

    def _find_closest_image_index(self, image_filenames: list[str], frame: int) -> int:
        """Find index of image closest to given frame number."""
        closest_idx = -1
        min_diff = float("inf")

        for i, filename in enumerate(image_filenames):
            try:
                # Extract frame number from filename
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

        return closest_idx

    def _has_image_attributes(self, curve_view: Any) -> bool:
        """Check if curve view has required image attributes."""
        return (
            hasattr(curve_view, "current_image_idx") and
            hasattr(curve_view, "image_filenames") and
            hasattr(curve_view, "image_sequence_path")
        )

    def _add_to_cache(self, path: str, image: QImage) -> None:
        """Add image to cache with size management."""
        # Trim cache if needed
        if len(self._image_cache) >= self._max_cache_size:
            self._trim_cache()

        self._image_cache[path] = image

    def _trim_cache(self) -> None:
        """Trim cache to maximum size."""
        if len(self._image_cache) > self._max_cache_size:
            # Remove oldest entries (simple FIFO for now)
            to_remove = len(self._image_cache) - self._max_cache_size
            keys = list(self._image_cache.keys())
            for key in keys[:to_remove]:
                del self._image_cache[key]