"""
Thumbnail caching system with disk and memory storage.

This module provides a two-tier caching system for thumbnails:
- Memory cache: LRU cache for fast access to recently used thumbnails
- Disk cache: Persistent storage in user temp directory

This dramatically improves performance when browsing sequences repeatedly,
especially for slow-to-decode formats like 4K EXR files.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap

# Configure logger
from core.logger_utils import get_logger

logger = get_logger("thumbnail_cache")


class ThumbnailCache:
    """
    Two-tier caching system for thumbnails.

    Features:
    - Memory cache (LRU): Fast access, limited size
    - Disk cache: Persistent storage, larger capacity
    - Automatic cleanup of old disk cache entries
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        memory_cache_size: int = 100,
        max_disk_cache_mb: int = 500,
    ):
        """
        Initialize thumbnail cache.

        Args:
            cache_dir: Directory for disk cache (default: user temp dir)
            memory_cache_size: Maximum number of thumbnails in memory
            max_disk_cache_mb: Maximum disk cache size in MB
        """
        # Memory cache (LRU)
        self._memory_cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._memory_cache_size = memory_cache_size

        # Disk cache directory
        if cache_dir is None:
            import tempfile

            cache_dir = Path(tempfile.gettempdir()) / "curveeditor_thumbnails"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_disk_cache_bytes = max_disk_cache_mb * 1024 * 1024

        logger.debug(f"Thumbnail cache initialized: {self.cache_dir}")
        logger.debug(f"Memory cache size: {memory_cache_size}, Disk cache: {max_disk_cache_mb}MB")

    def get_cache_key(self, image_path: str, size: int) -> str:
        """
        Generate cache key for an image at specific size.

        Args:
            image_path: Path to source image
            size: Thumbnail size in pixels

        Returns:
            Cache key string
        """
        # Use hash of path + size for cache key
        key_str = f"{image_path}_{size}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, image_path: str, size: int) -> QPixmap | None:
        """
        Get thumbnail from cache.

        Checks memory cache first, then disk cache.

        Args:
            image_path: Path to source image
            size: Thumbnail size in pixels

        Returns:
            Cached QPixmap or None if not in cache
        """
        cache_key = self.get_cache_key(image_path, size)

        # Check memory cache first
        if cache_key in self._memory_cache:
            # Move to end (most recently used)
            self._memory_cache.move_to_end(cache_key)
            logger.debug(f"Memory cache hit: {cache_key}")
            return self._memory_cache[cache_key]

        # Check disk cache
        disk_pixmap = self._get_from_disk(cache_key)
        if disk_pixmap is not None:
            # Store in memory cache for future access
            self._store_in_memory(cache_key, disk_pixmap)
            logger.debug(f"Disk cache hit: {cache_key}")
            return disk_pixmap

        logger.debug(f"Cache miss: {cache_key}")
        return None

    def store(self, image_path: str, size: int, pixmap: QPixmap) -> None:
        """
        Store thumbnail in cache.

        Stores in both memory and disk caches.

        Args:
            image_path: Path to source image
            size: Thumbnail size in pixels
            pixmap: Thumbnail pixmap to cache
        """
        cache_key = self.get_cache_key(image_path, size)

        # Store in memory cache
        self._store_in_memory(cache_key, pixmap)

        # Store in disk cache
        self._store_on_disk(cache_key, pixmap)

        logger.debug(f"Cached thumbnail: {cache_key}")

    def _store_in_memory(self, cache_key: str, pixmap: QPixmap) -> None:
        """
        Store pixmap in memory cache (LRU).

        Args:
            cache_key: Cache key
            pixmap: Pixmap to store
        """
        # Add to cache
        self._memory_cache[cache_key] = pixmap

        # Move to end (most recently used)
        self._memory_cache.move_to_end(cache_key)

        # Evict oldest if over limit
        if len(self._memory_cache) > self._memory_cache_size:
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
            logger.debug(f"Evicted from memory cache: {oldest_key}")

    def _get_from_disk(self, cache_key: str) -> QPixmap | None:
        """
        Load pixmap from disk cache.

        Args:
            cache_key: Cache key

        Returns:
            Cached QPixmap or None if not found
        """
        from PySide6.QtGui import QPixmap

        cache_file = self.cache_dir / f"{cache_key}.jpg"

        if cache_file.exists():
            pixmap = QPixmap(str(cache_file))
            if not pixmap.isNull():
                # Update access time
                cache_file.touch()
                return pixmap

        return None

    def _store_on_disk(self, cache_key: str, pixmap: QPixmap) -> None:
        """
        Store pixmap on disk cache.

        Args:
            cache_key: Cache key
            pixmap: Pixmap to store
        """
        cache_file = self.cache_dir / f"{cache_key}.jpg"

        try:
            # Save as JPEG with quality 85 (good balance of quality/size)
            pixmap.save(str(cache_file), "JPEG", 85)

            # Clean up old cache entries if needed
            self._cleanup_disk_cache()

        except Exception as e:
            logger.error(f"Failed to save thumbnail to disk: {e}")

    def _cleanup_disk_cache(self) -> None:
        """
        Clean up old disk cache entries if size limit exceeded.

        Removes oldest files first (by access time).
        """
        try:
            # Get all cache files with their sizes and access times
            cache_files: list[tuple[Path, float, int]] = []
            total_size = 0

            for cache_file in self.cache_dir.glob("*.jpg"):
                if cache_file.is_file():
                    stat = cache_file.stat()
                    size = stat.st_size
                    atime = stat.st_atime
                    cache_files.append((cache_file, atime, size))
                    total_size += size

            # Check if cleanup needed
            if total_size <= self.max_disk_cache_bytes:
                return

            # Sort by access time (oldest first)
            cache_files.sort(key=lambda x: x[1])

            # Remove oldest files until under limit
            removed_count = 0
            for cache_file, _, size in cache_files:
                if total_size <= self.max_disk_cache_bytes:
                    break

                try:
                    cache_file.unlink()
                    total_size -= size
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove cache file: {e}")

            if removed_count > 0:
                logger.debug(f"Cleaned up {removed_count} old cache files")

        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")

    def clear_memory_cache(self) -> None:
        """Clear all entries from memory cache."""
        self._memory_cache.clear()
        logger.debug("Memory cache cleared")

    def clear_disk_cache(self) -> None:
        """Delete all files from disk cache."""
        try:
            removed_count = 0
            for cache_file in self.cache_dir.glob("*.jpg"):
                try:
                    cache_file.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove cache file: {e}")

            logger.info(f"Disk cache cleared: {removed_count} files removed")

        except Exception as e:
            logger.error(f"Error clearing disk cache: {e}")

    def clear(self) -> None:
        """Clear both memory and disk caches."""
        self.clear_memory_cache()
        self.clear_disk_cache()

    def get_cache_stats(self) -> dict[str, int | float]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        disk_files = list(self.cache_dir.glob("*.jpg"))
        disk_size = sum(f.stat().st_size for f in disk_files if f.is_file())

        return {
            "memory_entries": len(self._memory_cache),
            "memory_limit": self._memory_cache_size,
            "disk_entries": len(disk_files),
            "disk_size_bytes": disk_size,
            "disk_size_mb": disk_size / (1024 * 1024),
            "disk_limit_mb": self.max_disk_cache_bytes / (1024 * 1024),
        }
