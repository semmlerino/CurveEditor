"""
Image Cache Manager for CurveEditor.

Provides thread-safe LRU caching of image sequences for efficient frame navigation.
Phase 2A: Synchronous on-demand loading with LRU eviction.
Phase 2B: Background preloading with QThread for first-pass lag elimination.

Key Design Decisions:
- Stores QImage (NOT QPixmap) for thread safety in background loading
- Uses frame numbers as keys for O(1) lookup
- LRU eviction via list tracking (matches existing codebase pattern)
- Thread-safe lock wraps all cache operations
- QObject base class enables signals for preloading progress
- Worker thread uses QImage only (QPixmap restricted to main thread)
"""

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, override

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot

if TYPE_CHECKING:
    from PySide6.QtGui import QImage

logger = logging.getLogger(__name__)


class SafeImagePreloadWorker(QThread):
    """
    Background worker thread for preloading images.

    Loads QImage objects in worker thread (thread-safe) and emits signals
    to main thread for cache storage. NEVER creates QPixmap (main-thread-only).

    Signals:
        image_loaded: Emitted when frame loaded successfully (frame: int, image: QImage)
        progress: Emitted after each load (loaded_count: int, total_count: int)

    Thread Safety:
        - Creates only QImage (thread-safe), never QPixmap
        - Signals use QueuedConnection for cross-thread communication
        - Graceful stop via _stop_requested flag
    """

    image_loaded = Signal(int, object)  # (frame, QImage) - use object for QImage type
    progress = Signal(int, int)  # (loaded_count, total_count)

    def __init__(self, image_files: list[str], frames_to_load: list[int]) -> None:
        """
        Initialize preload worker.

        Args:
            image_files: Complete list of image file paths (indexed by frame number)
            frames_to_load: Frame numbers to preload (filtered to exclude cached frames)
        """
        super().__init__()
        self._image_files = image_files
        self._frames_to_load = frames_to_load
        # Thread-safe: Python GIL ensures atomic bool assignment
        # Worker reads, main thread writes (write-once: False → True)
        self._stop_requested = False

    @override
    def run(self) -> None:
        """
        Load images in background thread.

        Emits image_loaded signal for each successfully loaded frame.
        Emits progress signal after each load attempt.
        Stops gracefully when _stop_requested is True.
        """
        total = len(self._frames_to_load)
        loaded = 0

        for frame in self._frames_to_load:
            # Check for stop request
            if self._stop_requested:
                logger.debug(f"Preload worker stopped (loaded {loaded}/{total} frames)")
                return

            # Validate frame bounds
            if frame < 0 or frame >= len(self._image_files):
                logger.debug(f"Skipping out-of-bounds frame {frame}")
                continue

            # Load image
            file_path = self._image_files[frame]
            image = self._load_image(file_path)

            if image is not None:
                # Emit signal with loaded image (QueuedConnection to main thread)
                self.image_loaded.emit(frame, image)
                loaded += 1
                self.progress.emit(loaded, total)
            else:
                logger.warning(f"Failed to preload frame {frame}: {file_path}")

        logger.debug(f"Preload worker complete: {loaded}/{total} frames loaded")

    def stop(self) -> None:
        """Request worker to stop loading frames."""
        self._stop_requested = True

    def _load_image(self, file_path: str) -> "QImage | None":
        """
        Load image from disk (handles EXR and standard formats).

        CRITICAL: Creates QImage only (thread-safe). Never creates QPixmap.

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
            # CRITICAL: QImage is thread-safe, QPixmap is NOT
            image = QImage(str(file_path))
            if image.isNull():
                logger.error(f"Failed to load image (QImage.isNull): {file_path}")
                return None

            return image

        except Exception as e:
            logger.error(f"Exception loading image {file_path}: {e}")
            return None


class SafeImageCacheManager(QObject):
    """
    Thread-safe LRU cache for image sequences with background preloading.

    Provides on-demand loading with automatic eviction when cache is full.
    Phase 2B adds background QThread-based preloading to eliminate first-pass lag.

    Key Features:
    - LRU eviction policy (oldest frames evicted first)
    - Thread-safe access using threading.Lock
    - Support for EXR and standard image formats
    - Frame-indexed lookup (O(1) access)
    - Automatic cache clearing on sequence changes
    - Background preloading with progress signals

    Signals:
        cache_progress: Emitted during background preloading (loaded: int, total: int)

    Thread Safety:
    - All public methods acquire lock before cache operations
    - Worker thread loads QImage only (never QPixmap)
    - QueuedConnection used for cross-thread signal delivery

    Example:
        cache = SafeImageCacheManager(max_cache_size=100)
        cache.set_image_sequence(image_files)
        image = cache.get_image(frame=42)  # Loads on-demand, caches result
        cache.preload_around_frame(42, window_size=20)  # Preload ±20 frames
    """

    cache_progress = Signal(int, int)  # (loaded_count, total_count)

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
        self._preload_worker: SafeImagePreloadWorker | None = None

        logger.debug(f"SafeImageCacheManager initialized with max_cache_size={max_cache_size}")

    def set_image_sequence(self, image_files: list[str]) -> None:
        """
        Set the image sequence and clear cache.

        Args:
            image_files: List of absolute paths to image files (frame 0 = index 0)

        Note:
            Clears existing cache to prevent stale data from previous sequence.
            Stops any running preload worker.
        """
        # Stop preload worker before changing sequence
        self._stop_preload()

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

    def cleanup(self) -> None:
        """
        Stop preload worker and cleanup resources.

        Call this when shutting down the cache manager to ensure
        the background worker thread terminates gracefully.
        """
        logger.debug("Cleaning up image cache manager")
        self._stop_preload()

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

    def preload_range(self, start_frame: int, end_frame: int) -> None:
        """
        Preload consecutive frames in background thread.

        Args:
            start_frame: First frame to preload (inclusive)
            end_frame: Last frame to preload (inclusive)

        Note:
            Frames already in cache are skipped.
            Stops any existing preload worker before starting new one.
        """
        if not self._image_files:
            logger.debug("preload_range: No image sequence loaded")
            return

        # Clamp to valid range
        start = max(0, start_frame)
        end = min(len(self._image_files) - 1, end_frame)

        if start > end:
            logger.debug(f"preload_range: Invalid range {start_frame}-{end_frame}")
            return

        # Build list of frames to preload
        frames_to_load = list(range(start, end + 1))
        self._start_preload_worker(frames_to_load)

    def preload_around_frame(self, current_frame: int, window_size: int = 20) -> None:
        """
        Preload frames around current frame in background thread.

        Args:
            current_frame: Center frame for preloading window
            window_size: Number of frames to load before and after current (default 20)

        Example:
            preload_around_frame(100, window_size=20)  # Preloads frames 80-120

        Note:
            Frames already in cache are skipped.
            Stops any existing preload worker before starting new one.
        """
        if not self._image_files:
            logger.debug("preload_around_frame: No image sequence loaded")
            return

        # Calculate frame range (±window_size around current)
        start_frame = max(0, current_frame - window_size)
        end_frame = min(len(self._image_files) - 1, current_frame + window_size)

        self.preload_range(start_frame, end_frame)

    def _start_preload_worker(self, frames_to_load: list[int]) -> None:
        """
        Start background preload worker for specified frames.

        Args:
            frames_to_load: List of frame numbers to preload

        Note:
            Automatically filters out frames already in cache.
            Stops existing worker before starting new one.
        """
        # Stop existing worker
        self._stop_preload()

        # Filter out frames already in cache
        with self._lock:
            frames_needed = [f for f in frames_to_load if f not in self._cache]

        if not frames_needed:
            logger.debug("_start_preload_worker: All frames already cached")
            return

        logger.debug(f"Starting preload worker for {len(frames_needed)} frames")

        # Create and start worker
        self._preload_worker = SafeImagePreloadWorker(self._image_files, frames_needed)

        # Connect signals with QueuedConnection (cross-thread safety)
        self._preload_worker.image_loaded.connect(self._on_image_preloaded, Qt.ConnectionType.QueuedConnection)
        self._preload_worker.progress.connect(self.cache_progress, Qt.ConnectionType.QueuedConnection)

        # Start worker thread
        self._preload_worker.start()

    def _stop_preload(self) -> None:
        """
        Stop background preload worker if running.

        Waits up to 1 second for worker to finish gracefully.
        """
        if self._preload_worker is None:
            return

        if self._preload_worker.isRunning():
            logger.debug("Stopping preload worker")
            self._preload_worker.stop()
            if not self._preload_worker.wait(1000):  # 1 second timeout
                logger.warning("Preload worker did not stop within timeout")

        self._preload_worker = None

    @Slot(int, object)
    def _on_image_preloaded(self, frame: int, qimage: object) -> None:
        """
        Handle preloaded image from worker thread.

        This slot runs in the main thread via QueuedConnection.
        Adds preloaded image to cache if not already present.

        Args:
            frame: Frame number
            qimage: Loaded QImage from worker thread (typed as object for Signal compatibility)

        Note:
            Skips frames already in cache (prevents overwriting recent access).
        """
        from PySide6.QtGui import QImage

        # Type guard - qimage should always be QImage from worker
        if not isinstance(qimage, QImage):
            logger.error(f"Invalid image type received: {type(qimage)}")
            return

        with self._lock:
            # Don't overwrite if frame was loaded on-demand during preload
            if frame not in self._cache:
                self._add_to_cache(frame, qimage)
                logger.debug(f"Preloaded frame {frame} added to cache")
