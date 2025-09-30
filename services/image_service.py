#!/usr/bin/env python
"""
Image Service for CurveEditor.

This service handles image-related operations including:
- Image sequence loading
- Image caching with LRU-style management
- Current image loading for views
- Image format detection and validation

Extracted from DataService during Phase 3 modularization.
"""

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from protocols.services import LoggingServiceProtocol, StatusServiceProtocol

if TYPE_CHECKING:
    from PySide6.QtGui import QImage

logger = logging.getLogger("image_service")


class ImageService:
    """Service for image sequence and caching operations."""

    def __init__(
        self,
        logging_service: LoggingServiceProtocol | None = None,
        status_service: StatusServiceProtocol | None = None,
    ) -> None:
        """Initialize ImageService with optional dependencies."""
        self._logger: LoggingServiceProtocol | None = logging_service
        self._status: StatusServiceProtocol | None = status_service

        # Initialize caching state
        self._lock: threading.RLock = threading.RLock()
        self._image_cache: dict[str, object] = {}
        self._max_cache_size: int = 100  # Maximum number of cached images

        # Common image file extensions
        self._image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif"}

    # ==================== Image Sequence Operations ====================

    def load_image_sequence(self, directory: str) -> list[str]:
        """Load image sequence from directory."""
        try:
            path = Path(directory)
            if not path.exists() or not path.is_dir():
                if self._logger:
                    self._logger.log_error(f"Directory does not exist: {directory}")
                return []

            image_files = []

            for file_path in sorted(path.iterdir()):
                if file_path.is_file() and file_path.suffix.lower() in self._image_extensions:
                    image_files.append(str(file_path))

            if self._logger and image_files:
                self._logger.log_info(f"Loaded {len(image_files)} images from {directory}")

            if self._status and image_files:
                self._status.set_status(f"Loaded {len(image_files)} image files")

            return image_files

        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Failed to load image sequence: {e}")
            return []

    def validate_image_path(self, file_path: str) -> bool:
        """Check if the file path is a valid image file."""
        try:
            path = Path(file_path)
            return path.exists() and path.is_file() and path.suffix.lower() in self._image_extensions
        except Exception:
            return False

    def get_image_info(self, file_path: str) -> dict[str, object]:
        """Get basic information about an image file."""
        try:
            path = Path(file_path)
            if not self.validate_image_path(file_path):
                return {"valid": False, "error": "Invalid image file"}

            # Basic file information
            stat = path.stat()
            return {
                "valid": True,
                "path": str(path),
                "name": path.name,
                "size_bytes": stat.st_size,
                "extension": path.suffix.lower(),
                "modified": stat.st_mtime,
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    # ==================== Image Loading Operations ====================

    def set_current_image_by_frame(self, view: object, frame: int) -> None:
        """Set current image by frame number."""
        # Placeholder implementation for interface compatibility
        # In a full implementation, this would coordinate with the view
        # to load the appropriate image for the given frame
        if self._logger:
            self._logger.log_debug(f"Set current image for frame {frame}")

    def load_current_image(self, view: object) -> "QImage | None":
        """Load current image for view."""
        # Placeholder implementation for interface compatibility
        # In a full implementation, this would load the actual image
        # based on the view's current state
        return None

    def load_image_from_path(self, file_path: str) -> "QImage | None":
        """Load a specific image from file path."""
        try:
            if not self.validate_image_path(file_path):
                return None

            # Check cache first
            cache_key = f"image:{file_path}"
            cached_image = self._get_from_cache(cache_key)
            if cached_image is not None:
                return cached_image  # type: ignore[return-value]

            # Load image using Qt
            from PySide6.QtGui import QImage

            image = QImage(file_path)
            if not image.isNull():
                # Add to cache
                self._add_to_cache(cache_key, image)
                if self._logger:
                    self._logger.log_debug(f"Loaded image: {file_path}")
                return image
            else:
                if self._logger:
                    self._logger.log_error(f"Failed to load image: {file_path}")
                return None

        except Exception as e:
            if self._logger:
                self._logger.log_error(f"Error loading image {file_path}: {e}")
            return None

    # ==================== Cache Management ====================

    def clear_image_cache(self) -> None:
        """Clear the image cache."""
        with self._lock:
            cache_size = len(self._image_cache)
            self._image_cache.clear()
            if self._logger and cache_size > 0:
                self._logger.log_info(f"Cleared image cache ({cache_size} items)")

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.clear_image_cache()

    def get_cache_stats(self) -> dict[str, object]:
        """Get cache statistics."""
        with self._lock:
            return {
                "current_size": len(self._image_cache),
                "max_size": self._max_cache_size,
                "utilization": len(self._image_cache) / self._max_cache_size if self._max_cache_size > 0 else 0,
            }

    def set_cache_size(self, size: int) -> None:
        """Set maximum cache size."""
        if size < 0:
            raise ValueError("Cache size must be non-negative")

        with self._lock:
            self._max_cache_size = size
            # Trim cache if it now exceeds the new max size
            self._trim_cache()

        if self._logger:
            self._logger.log_info(f"Set cache size to {size}")

    def _add_to_cache(self, key: str, value: object) -> None:
        """Add an item to the image cache (thread-safe)."""
        with self._lock:
            # Trim cache if it exceeds max size
            if len(self._image_cache) >= self._max_cache_size:
                self._trim_cache()
            self._image_cache[key] = value

    def _get_from_cache(self, key: str) -> object | None:
        """Get an item from the cache (thread-safe)."""
        with self._lock:
            return self._image_cache.get(key)

    def _trim_cache(self) -> None:
        """Remove oldest items from cache if it exceeds max size."""
        while len(self._image_cache) >= self._max_cache_size and self._image_cache:
            # Remove oldest item (first key in dict)
            oldest_key = next(iter(self._image_cache))
            del self._image_cache[oldest_key]

    def _remove_from_cache(self, key: str) -> bool:
        """Remove a specific item from cache."""
        with self._lock:
            if key in self._image_cache:
                del self._image_cache[key]
                return True
            return False

    # ==================== Utility Methods ====================

    def get_supported_formats(self) -> list[str]:
        """Get list of supported image file extensions."""
        return sorted(list(self._image_extensions))

    def preload_images(self, file_paths: list[str], max_preload: int = 10) -> int:
        """Preload images into cache.

        Args:
            file_paths: List of image file paths to preload
            max_preload: Maximum number of images to preload

        Returns:
            Number of images successfully preloaded
        """
        loaded_count = 0
        for file_path in file_paths[:max_preload]:
            if self.validate_image_path(file_path):
                image = self.load_image_from_path(file_path)
                if image is not None:
                    loaded_count += 1

        if self._logger and loaded_count > 0:
            self._logger.log_info(f"Preloaded {loaded_count} images into cache")

        return loaded_count

    def estimate_cache_memory_usage(self) -> int:
        """Estimate memory usage of cached images in bytes."""
        # This is a rough estimation - actual Qt image memory usage can vary
        estimated_bytes = 0

        with self._lock:
            for cached_item in self._image_cache.values():
                try:
                    # Attempt to get Qt QImage size information
                    from PySide6.QtGui import QImage

                    if isinstance(cached_item, QImage):
                        # Estimate: width * height * bytes_per_pixel
                        # Assuming 4 bytes per pixel (RGBA)
                        estimated_bytes += cached_item.width() * cached_item.height() * 4
                except Exception:
                    # Fallback estimation if Qt objects are not accessible
                    estimated_bytes += 1024 * 1024  # Assume 1MB per cached item

        return estimated_bytes
