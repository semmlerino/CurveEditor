"""
Image Cache Manager for CurveEditor.

Provides thread-safe LRU caching of image sequences for efficient frame navigation.
Phase 2A: Synchronous on-demand loading with LRU eviction.
Phase 2B+: Will add background preloading with QThread.

Key Design Decisions:
- Stores QImage (NOT QPixmap) for thread safety in future phases
- Uses frame numbers as keys for O(1) lookup
- LRU eviction via list tracking (matches existing codebase pattern)
- Thread-safe lock wraps all cache operations
- QObject base class enables signals for Phase 2B preloading
"""

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

if TYPE_CHECKING:
    from PySide6.QtGui import QImage

logger = logging.getLogger(__name__)


class SafeImageCacheManager(QObject):
    """
    Thread-safe LRU cache for image sequences.

    Provides on-demand loading with automatic eviction when cache is full.
    Designed for future extension with background preloading (Phase 2B).

    Key Features:
    - LRU eviction policy (oldest frames evicted first)
    - Thread-safe access using threading.Lock
    - Support for EXR and standard image formats
    - Frame-indexed lookup (O(1) access)
    - Automatic cache clearing on sequence changes

    Thread Safety:
    - All public methods acquire lock before cache operations
    - Safe for multi-threaded access (required for Phase 2B preloading)

    Example:
        cache = SafeImageCacheManager(max_cache_size=100)
        cache.set_image_sequence(image_files)
        image = cache.get_image(frame=42)  # Loads on-demand, caches result
    """

    def __init__(self, max_cache_size: int = 100) -> None:
        """
        Initialize image cache manager.

        Args:
            max_cache_size: Maximum number of frames to cache (default 100)
                           When exceeded, oldest frames evicted (LRU policy)

        Raises:
            ValueError: If max_cache_size <= 0
        """
        if max_cache_size <= 0:
            raise ValueError(f"max_cache_size must be positive, got {max_cache_size}")

        super().__init__()

        self._max_cache_size: int = max_cache_size
        self._cache: dict[int, "QImage"] = {}
        self._lru_order: list[int] = []
        self._image_files: list[str] = []
        self._lock: threading.Lock = threading.Lock()

        logger.debug(f"SafeImageCacheManager initialized with max_cache_size={max_cache_size}")

    def set_image_sequence(self, image_files: list[str]) -> None:
        """
        Set the image sequence and clear cache.

        Args:
            image_files: List of absolute paths to image files (frame 0 = index 0)

        Note:
            Clears existing cache to prevent stale data from previous sequence.
        """
        with self._lock:
            self._image_files = image_files
            self._cache.clear()
            self._lru_order.clear()

        logger.info(f"Image sequence set: {len(image_files)} frames")

    def get_image(self, frame: int) -> "QImage | None":
        """
        Get image for specified frame (loads on-demand if not cached).

        Thread-safe method that:
        1. Checks cache for existing image (updates LRU on hit)
        2. Loads from disk if not cached (adds to cache)
        3. Evicts oldest frames if cache exceeds max_cache_size

        Args:
            frame: Frame number (0-indexed, corresponds to image_files index)

        Returns:
            QImage object if successful, None if frame invalid or load fails

        Note:
            Returns None for:
            - Frame out of bounds (< 0 or >= len(image_files))
            - Empty image sequence
            - File loading errors (logged)
        """
        with self._lock:
            # Validate frame number
            if not self._image_files:
                logger.debug("get_image: No image sequence loaded")
                return None

            if frame < 0 or frame >= len(self._image_files):
                logger.debug(f"get_image: Frame {frame} out of bounds (0-{len(self._image_files)-1})")
                return None

            # Cache hit - update LRU and return
            if frame in self._cache:
                self._update_lru(frame)
                logger.debug(f"Cache HIT: frame {frame}")
                return self._cache[frame]

            # Cache miss - load from disk
            file_path = self._image_files[frame]
            image = self._load_image_from_disk(file_path)

            if image is None:
                logger.error(f"Failed to load image for frame {frame}: {file_path}")
                return None

            # Add to cache (triggers eviction if needed)
            self._add_to_cache(frame, image)
            logger.debug(f"Cache MISS: frame {frame} loaded and cached (size: {len(self._cache)})")

            return image

    def _load_image_from_disk(self, file_path: str) -> "QImage | None":
        """
        Load image from disk (handles EXR and standard formats).

        Args:
            file_path: Absolute path to image file

        Returns:
            QImage object or None if loading fails
        """
        from PySide6.QtGui import QImage

        try:
            path = Path(file_path)

            if not path.exists():
                logger.error(f"Image file not found: {file_path}")
                return None

            # EXR format requires special loader
            if path.suffix.lower() == ".exr":
                from io_utils.exr_loader import load_exr_as_qimage

                image = load_exr_as_qimage(str(file_path))
                if image is None:
                    logger.error(f"Failed to load EXR image: {file_path}")
                    return None
                return image

            # Standard formats (PNG, JPG, etc.)
            image = QImage(str(file_path))
            if image.isNull():
                logger.error(f"Failed to load image (QImage.isNull): {file_path}")
                return None

            return image

        except Exception as e:
            logger.error(f"Exception loading image {file_path}: {e}")
            return None

    def _add_to_cache(self, frame: int, image: "QImage") -> None:
        """
        Add image to cache with LRU eviction.

        Args:
            frame: Frame number
            image: QImage object to cache

        Note:
            Automatically evicts oldest frames if cache exceeds max_cache_size.
            Must be called with lock held.
        """
        # Add to cache
        self._cache[frame] = image
        self._lru_order.append(frame)

        # Evict oldest frames if cache too large (LRU eviction)
        while len(self._cache) > self._max_cache_size:
            oldest_frame = self._lru_order.pop(0)
            del self._cache[oldest_frame]
            logger.debug(f"Cache EVICT: frame {oldest_frame} (cache size: {len(self._cache)})")

    def _update_lru(self, frame: int) -> None:
        """
        Update LRU order on cache hit (move frame to end).

        Args:
            frame: Frame number that was accessed

        Note:
            Must be called with lock held.
        """
        # Remove from current position and append to end (most recently used)
        self._lru_order.remove(frame)
        self._lru_order.append(frame)

    def clear_cache(self) -> None:
        """
        Clear all cached images.

        Public method for manual cache clearing (e.g., memory management).
        """
        with self._lock:
            self._cache.clear()
            self._lru_order.clear()

        logger.info("Image cache cleared")

    @property
    def cache_size(self) -> int:
        """
        Get current number of cached frames.

        Returns:
            Number of frames currently in cache
        """
        with self._lock:
            return len(self._cache)

    @property
    def max_cache_size(self) -> int:
        """
        Get maximum cache size.

        Returns:
            Maximum number of frames that can be cached
        """
        return self._max_cache_size
