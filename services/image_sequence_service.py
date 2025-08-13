"""
Image sequence management service for the CurveEditor.

This service handles loading and managing sequences of images,
with caching and frame-based navigation.
"""

import logging
import os
import re
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.path_security import PathSecurityError, validate_directory_path, validate_file_path

if TYPE_CHECKING:
    from PySide6.QtGui import QImage, QPixmap
else:
    # Runtime stubs for when PySide6 unavailable
    QImage = QPixmap = object

logger = logging.getLogger(__name__)


class ImageSequenceService:
    """
    Manages image sequences for background display.

    This service is responsible for:
    - Loading image sequences from directories
    - Caching loaded images for performance
    - Frame-based image navigation
    - Sorting images by frame number
    """

    def __init__(self, max_cache_size: int = 50):
        """
        Initialize the image sequence service.

        Args:
            max_cache_size: Maximum number of images to cache
        """
        self._lock = threading.RLock()

        # Supported image formats
        self._supported_formats = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]

        # Image cache
        self._image_cache: dict[str, QImage] = {}
        self._cache_order: list[str] = []  # Track order for LRU
        self._max_cache_size = max_cache_size

    def load_image_sequence(self, directory: str) -> list[str]:
        """
        Load image sequence from directory.

        Args:
            directory: Path to directory containing images

        Returns:
            List of image filenames sorted by frame number
        """
        try:
            # Validate directory path for security
            validated_dir = validate_directory_path(directory, allow_create=False)
            directory = str(validated_dir)
        except PathSecurityError as e:
            logger.error(f"Security violation: {e}")
            return []

        directory_path = Path(directory)
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return []

        with self._lock:
            image_files = []

            try:
                # Find all image files in directory
                for file in os.listdir(directory):
                    file_path = Path(directory) / file
                    if file_path.is_file():
                        ext = file_path.suffix.lower()
                        if ext in self._supported_formats:
                            image_files.append(file)

                # Sort by frame number if possible
                image_files = self._sort_by_frame_number(image_files)

                logger.info(f"Loaded {len(image_files)} images from {directory}")
                return image_files

            except Exception as e:
                logger.error(f"Failed to load image sequence: {e}")
                return []

    def load_image(self, file_path: str) -> QImage | None:
        """
        Load a single image with caching.

        Args:
            file_path: Path to image file

        Returns:
            QImage object or None if failed
        """
        try:
            # Validate file path
            validated_path = validate_file_path(file_path, operation_type="images", require_exists=True)
            file_path = str(validated_path)
        except PathSecurityError as e:
            logger.error(f"Security violation: {e}")
            return None

        with self._lock:
            # Check cache first
            if file_path in self._image_cache:
                # Move to end (most recently used)
                self._cache_order.remove(file_path)
                self._cache_order.append(file_path)
                return self._image_cache[file_path]

            try:
                # Import PySide6 only when needed
                from PySide6.QtGui import QImage

                # Load image
                image = QImage(file_path)

                if image.isNull():
                    logger.error(f"Failed to load image: {file_path}")
                    return None

                # Add to cache
                self._add_to_cache(file_path, image)

                logger.debug(f"Loaded image: {file_path}")
                return image

            except Exception as e:
                logger.error(f"Error loading image {file_path}: {e}")
                return None

    def set_current_image_by_frame(self, view: Any, frame: int) -> None:
        """
        Set current image by frame number.

        Args:
            view: The curve view instance
            frame: Frame number to find the closest image for
        """
        if not hasattr(view, "image_filenames"):
            return

        image_filenames = getattr(view, "image_filenames", [])
        if not image_filenames:
            return

        # Find the closest image index to the requested frame
        closest_idx = self._find_closest_image_index(image_filenames, frame)

        if 0 <= closest_idx < len(image_filenames):
            view.current_image_idx = closest_idx
            self.load_current_image(view)

    def load_current_image(self, view: Any) -> QImage | None:
        """
        Load the current image for the curve view.

        Args:
            view: The curve view instance

        Returns:
            Loaded QImage or None
        """
        if not hasattr(view, "image_filenames") or not hasattr(view, "current_image_idx"):
            return None

        image_filenames = getattr(view, "image_filenames", [])
        current_idx = getattr(view, "current_image_idx", 0)
        image_dir = getattr(view, "image_directory", "")

        if not image_filenames or current_idx < 0 or current_idx >= len(image_filenames):
            return None

        # Construct full path
        image_path = str(Path(image_dir) / image_filenames[current_idx])

        # Load image
        image = self.load_image(image_path)

        if image and hasattr(view, "current_background_image"):
            view.current_background_image = image
            view.update()

        return image

    def clear_cache(self) -> None:
        """Clear the image cache."""
        with self._lock:
            self._image_cache.clear()
            self._cache_order.clear()
            logger.debug("Image cache cleared")

    def set_cache_size(self, size: int) -> None:
        """
        Set maximum cache size.

        Args:
            size: New maximum cache size
        """
        with self._lock:
            self._max_cache_size = max(1, size)
            self._trim_cache()

    def get_cache_info(self) -> dict[str, Any]:
        """
        Get information about the cache.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            return {"size": len(self._image_cache), "max_size": self._max_cache_size, "files": list(self._cache_order)}

    def _add_to_cache(self, path: str, image: QImage) -> None:
        """
        Add image to cache with LRU eviction.

        Args:
            path: Image file path
            image: QImage object to cache
        """
        # Add to cache
        self._image_cache[path] = image

        # Update order
        if path in self._cache_order:
            self._cache_order.remove(path)
        self._cache_order.append(path)

        # Trim if necessary
        self._trim_cache()

    def _trim_cache(self) -> None:
        """Trim cache to maximum size using LRU."""
        while len(self._image_cache) > self._max_cache_size:
            # Remove least recently used
            if self._cache_order:
                oldest = self._cache_order.pop(0)
                del self._image_cache[oldest]
                logger.debug(f"Evicted from cache: {oldest}")

    def _sort_by_frame_number(self, filenames: list[str]) -> list[str]:
        """
        Sort filenames by extracted frame number.

        Args:
            filenames: List of image filenames

        Returns:
            Sorted list of filenames
        """

        def extract_frame_number(filename: str) -> int:
            """Extract frame number from filename."""
            # Look for patterns like:
            # - frame_0001.png
            # - image.0001.jpg
            # - 0001.png
            # - frame1.png

            # Try to find any sequence of digits
            matches = re.findall(r"\d+", filename)
            if matches:
                # Use the last number found (often the frame number)
                try:
                    return int(matches[-1])
                except ValueError:
                    pass

            # If no number found, use alphabetical order
            return 0

        try:
            # Sort by extracted frame number, then by name for ties
            return sorted(filenames, key=lambda f: (extract_frame_number(f), f))
        except Exception as e:
            logger.warning(f"Error sorting filenames: {e}")
            # Fall back to simple alphabetical sort
            return sorted(filenames)

    def _find_closest_image_index(self, filenames: list[str], target_frame: int) -> int:
        """
        Find index of image closest to target frame number.

        Args:
            filenames: List of image filenames
            target_frame: Target frame number

        Returns:
            Index of closest image
        """
        if not filenames:
            return -1

        # Extract frame numbers
        frame_numbers = []
        for filename in filenames:
            matches = re.findall(r"\d+", filename)
            if matches:
                try:
                    frame_numbers.append(int(matches[-1]))
                except ValueError:
                    frame_numbers.append(0)
            else:
                frame_numbers.append(0)

        # Find closest
        closest_idx = 0
        min_diff = abs(frame_numbers[0] - target_frame)

        for i, frame_num in enumerate(frame_numbers[1:], 1):
            diff = abs(frame_num - target_frame)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i

        return closest_idx

    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported image formats.

        Returns:
            List of file extensions
        """
        return list(self._supported_formats)

    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if file has supported image format.

        Args:
            file_path: Path to check

        Returns:
            True if format is supported
        """
        ext = Path(file_path).suffix.lower()
        return ext in self._supported_formats
