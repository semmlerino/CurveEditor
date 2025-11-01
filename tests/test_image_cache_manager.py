#!/usr/bin/env python
"""
Comprehensive tests for SafeImageCacheManager - Phase 2A.

Tests cover:
- Cache initialization and configuration
- Image sequence management
- LRU eviction policy
- Cache hit/miss behavior
- Image loading (EXR and standard formats)
- Thread safety
- Error handling
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none

import threading
from unittest.mock import Mock, patch

import pytest
from PySide6.QtGui import QImage

from services.image_cache_manager import SafeImageCacheManager


class TestCacheInitialization:
    """Test cache manager initialization and configuration."""

    def test_default_cache_size(self):
        """Test that default max_cache_size is 100."""
        cache = SafeImageCacheManager()
        assert cache.max_cache_size == 100

    def test_custom_cache_size(self):
        """Test that custom cache size is respected."""
        cache = SafeImageCacheManager(max_cache_size=50)
        assert cache.max_cache_size == 50

    def test_initial_empty_state(self):
        """Test that cache starts empty."""
        cache = SafeImageCacheManager()

        assert cache.cache_size == 0
        assert cache._cache == {}
        assert cache._lru_order == []
        assert cache._image_files == []

    def test_qobject_inheritance(self):
        """Test that cache manager inherits from QObject (required for Phase 2B signals)."""
        cache = SafeImageCacheManager()
        from PySide6.QtCore import QObject

        assert isinstance(cache, QObject)

    def test_zero_cache_size_raises_error(self):
        """Test that zero cache size is rejected."""
        with pytest.raises(ValueError, match="max_cache_size must be positive"):
            SafeImageCacheManager(max_cache_size=0)

    def test_negative_cache_size_raises_error(self):
        """Test that negative cache size is rejected."""
        with pytest.raises(ValueError, match="max_cache_size must be positive"):
            SafeImageCacheManager(max_cache_size=-10)


class TestImageSequenceManagement:
    """Test image sequence loading and management."""

    def test_set_image_sequence_stores_files(self):
        """Test that set_image_sequence stores file list."""
        cache = SafeImageCacheManager()
        files = ["/path/to/frame_0001.png", "/path/to/frame_0002.png", "/path/to/frame_0003.png"]

        cache.set_image_sequence(files)

        assert cache._image_files == files

    def test_set_image_sequence_clears_cache(self):
        """Test that setting new sequence clears existing cache."""
        cache = SafeImageCacheManager()

        # Setup: Populate cache with mock data
        cache._cache[0] = Mock(spec=QImage)
        cache._cache[1] = Mock(spec=QImage)
        cache._lru_order = [0, 1]

        # Set new sequence
        files = ["/path/to/new_frame_0001.png"]
        cache.set_image_sequence(files)

        # Verify cache cleared
        assert cache._cache == {}
        assert cache._lru_order == []
        assert cache._image_files == files

    def test_set_empty_sequence(self):
        """Test that empty sequence is handled correctly."""
        cache = SafeImageCacheManager()
        cache.set_image_sequence([])

        assert cache._image_files == []
        assert cache.cache_size == 0

    def test_clear_cache_method(self):
        """Test public clear_cache method."""
        cache = SafeImageCacheManager()

        # Populate cache
        cache._cache[0] = Mock(spec=QImage)
        cache._lru_order = [0]

        cache.clear_cache()

        assert cache._cache == {}
        assert cache._lru_order == []


class TestLRUEviction:
    """Test LRU eviction policy."""

    def test_lru_eviction_basic(self):
        """Test that adding 101 frames to 100-frame cache evicts frame 0."""
        cache = SafeImageCacheManager(max_cache_size=100)

        # Setup: Create mock image files
        files = [f"/path/frame_{i:04d}.png" for i in range(101)]
        cache.set_image_sequence(files)

        # Mock image loading to return valid QImage objects
        with patch.object(cache, "_load_image_from_disk") as mock_load:
            mock_image = Mock(spec=QImage)
            mock_load.return_value = mock_image

            # Load frames 0-100 (101 total)
            for frame in range(101):
                cache.get_image(frame)

            # Verify frame 0 was evicted (oldest)
            assert 0 not in cache._cache
            assert 0 not in cache._lru_order

            # Verify frames 1-100 are cached
            assert all(frame in cache._cache for frame in range(1, 101))
            assert cache.cache_size == 100

    def test_lru_eviction_order(self):
        """Test that oldest frames are evicted first (FIFO for new frames)."""
        cache = SafeImageCacheManager(max_cache_size=3)

        files = [f"/path/frame_{i:04d}.png" for i in range(5)]
        cache.set_image_sequence(files)

        with patch.object(cache, "_load_image_from_disk") as mock_load:
            mock_load.return_value = Mock(spec=QImage)

            # Load frames 0, 1, 2 (cache full)
            cache.get_image(0)
            cache.get_image(1)
            cache.get_image(2)

            assert cache._lru_order == [0, 1, 2]

            # Load frame 3 (evicts frame 0)
            cache.get_image(3)
            assert cache._lru_order == [1, 2, 3]
            assert 0 not in cache._cache

            # Load frame 4 (evicts frame 1)
            cache.get_image(4)
            assert cache._lru_order == [2, 3, 4]
            assert 1 not in cache._cache

    def test_cache_size_never_exceeds_max(self):
        """Test invariant: cache size never exceeds max_cache_size."""
        cache = SafeImageCacheManager(max_cache_size=10)

        files = [f"/path/frame_{i:04d}.png" for i in range(100)]
        cache.set_image_sequence(files)

        with patch.object(cache, "_load_image_from_disk") as mock_load:
            mock_load.return_value = Mock(spec=QImage)

            # Load 100 frames
            for frame in range(100):
                cache.get_image(frame)
                # Invariant check after every operation
                assert cache.cache_size <= 10

    def test_multiple_evictions_when_cache_full(self):
        """Test that multiple evictions occur correctly when cache is full."""
        cache = SafeImageCacheManager(max_cache_size=2)

        files = [f"/path/frame_{i:04d}.png" for i in range(5)]
        cache.set_image_sequence(files)

        with patch.object(cache, "_load_image_from_disk") as mock_load:
            mock_load.return_value = Mock(spec=QImage)

            # Fill cache (frames 0, 1)
            cache.get_image(0)
            cache.get_image(1)

            # Load frame 2 (evicts 0)
            cache.get_image(2)
            assert cache._lru_order == [1, 2]

            # Load frame 3 (evicts 1)
            cache.get_image(3)
            assert cache._lru_order == [2, 3]

            # Load frame 4 (evicts 2)
            cache.get_image(4)
            assert cache._lru_order == [3, 4]


class TestCacheHits:
    """Test cache hit behavior and LRU updates."""

    def test_cache_hit_updates_lru(self):
        """Test that accessing cached frame moves it to end of LRU order."""
        cache = SafeImageCacheManager(max_cache_size=10)

        files = [f"/path/frame_{i:04d}.png" for i in range(5)]
        cache.set_image_sequence(files)

        with patch.object(cache, "_load_image_from_disk") as mock_load:
            mock_load.return_value = Mock(spec=QImage)

            # Load frames 0, 1, 2
            cache.get_image(0)
            cache.get_image(1)
            cache.get_image(2)

            assert cache._lru_order == [0, 1, 2]

            # Access frame 0 (cache hit - should move to end)
            cache.get_image(0)
            assert cache._lru_order == [1, 2, 0]

            # Access frame 1 (cache hit - should move to end)
            cache.get_image(1)
            assert cache._lru_order == [2, 0, 1]

    def test_cache_hit_returns_same_image(self):
        """Test that cache hit returns the same QImage object."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        mock_image = Mock(spec=QImage)
        with patch.object(cache, "_load_image_from_disk") as mock_load:
            mock_load.return_value = mock_image

            # First access (cache miss - loads from disk)
            image1 = cache.get_image(0)
            assert image1 is mock_image

            # Second access (cache hit - should return same object)
            image2 = cache.get_image(0)
            assert image2 is mock_image
            assert image2 is image1

    def test_multiple_hits_update_order_correctly(self):
        """Test complex LRU scenario with multiple hits."""
        cache = SafeImageCacheManager(max_cache_size=5)

        files = [f"/path/frame_{i:04d}.png" for i in range(5)]
        cache.set_image_sequence(files)

        with patch.object(cache, "_load_image_from_disk") as mock_load:
            mock_load.return_value = Mock(spec=QImage)

            # Load all frames (0-4)
            for i in range(5):
                cache.get_image(i)

            assert cache._lru_order == [0, 1, 2, 3, 4]

            # Access pattern: 2, 0, 4 (cache hits)
            cache.get_image(2)
            assert cache._lru_order == [0, 1, 3, 4, 2]

            cache.get_image(0)
            assert cache._lru_order == [1, 3, 4, 2, 0]

            cache.get_image(4)
            assert cache._lru_order == [1, 3, 2, 0, 4]

    def test_cache_hit_prevents_reload(self):
        """Test that cache hit doesn't trigger disk load."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        with patch.object(cache, "_load_image_from_disk") as mock_load:
            mock_load.return_value = Mock(spec=QImage)

            # First access (cache miss)
            cache.get_image(0)
            assert mock_load.call_count == 1

            # Second access (cache hit - should not call _load_image_from_disk)
            cache.get_image(0)
            assert mock_load.call_count == 1  # Still 1 (not called again)


class TestImageLoading:
    """Test image loading from disk (EXR and standard formats)."""

    def test_get_image_loads_on_demand(self):
        """Test that get_image triggers disk load on cache miss."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        with patch.object(cache, "_load_image_from_disk") as mock_load:
            mock_image = Mock(spec=QImage)
            mock_load.return_value = mock_image

            result = cache.get_image(0)

            assert result is mock_image
            mock_load.assert_called_once_with("/path/frame_0001.png")

    def test_get_image_negative_frame_returns_none(self):
        """Test that negative frame number returns None."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        result = cache.get_image(-1)

        assert result is None

    def test_get_image_frame_out_of_bounds_returns_none(self):
        """Test that frame >= len(image_files) returns None."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png", "/path/frame_0002.png"]
        cache.set_image_sequence(files)

        # Frame 2 is out of bounds (only 0, 1 valid)
        result = cache.get_image(2)

        assert result is None

    def test_get_image_empty_sequence_returns_none(self):
        """Test that get_image returns None when no sequence loaded."""
        cache = SafeImageCacheManager()

        # No sequence set
        result = cache.get_image(0)

        assert result is None

    def test_get_image_missing_file_returns_none(self):
        """Test that missing file returns None."""
        cache = SafeImageCacheManager()

        files = ["/nonexistent/frame_0001.png"]
        cache.set_image_sequence(files)

        # Real file system - file doesn't exist
        result = cache.get_image(0)

        assert result is None

    def test_load_image_exr_format(self):
        """Test that EXR files use special loader."""
        cache = SafeImageCacheManager()

        with patch("io_utils.exr_loader.load_exr_as_qimage") as mock_exr_load:
            mock_image = Mock(spec=QImage)
            mock_exr_load.return_value = mock_image

            # Mock Path.exists() to return True
            with patch("services.image_cache_manager.Path.exists", return_value=True):
                result = cache._load_image_from_disk("/path/frame_0001.exr")

            assert result is mock_image
            mock_exr_load.assert_called_once_with("/path/frame_0001.exr")

    def test_load_image_exr_failure_returns_none(self):
        """Test that EXR loading failure returns None."""
        cache = SafeImageCacheManager()

        with patch("io_utils.exr_loader.load_exr_as_qimage") as mock_exr_load:
            mock_exr_load.return_value = None

            with patch("services.image_cache_manager.Path.exists", return_value=True):
                result = cache._load_image_from_disk("/path/frame_0001.exr")

            assert result is None

    def test_load_image_standard_format(self):
        """Test that standard formats use QImage constructor."""
        cache = SafeImageCacheManager()

        with patch("PySide6.QtGui.QImage") as mock_qimage_class:
            mock_image = Mock(spec=QImage)
            mock_image.isNull.return_value = False
            mock_qimage_class.return_value = mock_image

            # Mock Path.exists() to return True
            with patch("services.image_cache_manager.Path.exists", return_value=True):
                result = cache._load_image_from_disk("/path/frame_0001.png")

            assert result is mock_image
            mock_qimage_class.assert_called_once_with("/path/frame_0001.png")

    def test_load_image_null_qimage_returns_none(self):
        """Test that null QImage (loading failure) returns None."""
        cache = SafeImageCacheManager()

        with patch("PySide6.QtGui.QImage") as mock_qimage_class:
            mock_image = Mock(spec=QImage)
            mock_image.isNull.return_value = True  # Loading failed
            mock_qimage_class.return_value = mock_image

            with patch("services.image_cache_manager.Path.exists", return_value=True):
                result = cache._load_image_from_disk("/path/frame_0001.png")

            assert result is None

    def test_load_image_exception_returns_none(self):
        """Test that exceptions during loading return None."""
        cache = SafeImageCacheManager()

        with patch("PySide6.QtGui.QImage") as mock_qimage_class:
            mock_qimage_class.side_effect = Exception("Test exception")

            with patch("services.image_cache_manager.Path.exists", return_value=True):
                result = cache._load_image_from_disk("/path/frame_0001.png")

            assert result is None


class TestThreadSafety:
    """Test thread safety of cache operations."""

    def test_lock_acquisition(self):
        """Test that lock is acquired during cache operations."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        # Test that lock is held during get_image operation
        # We verify this by checking that the lock is locked during execution
        lock_was_held = False


        def check_lock_held(file_path: str):
            nonlocal lock_was_held
            # Lock should be held at this point
            lock_was_held = not cache._lock.acquire(blocking=False)
            if not lock_was_held:
                cache._lock.release()  # Release if we acquired it
            return Mock(spec=QImage)

        with patch.object(cache, "_load_image_from_disk", side_effect=check_lock_held):
            cache.get_image(0)

        # Verify lock was held during operation
        assert lock_was_held

    def test_concurrent_get_image_access(self):
        """Test that concurrent access doesn't corrupt cache."""
        cache = SafeImageCacheManager(max_cache_size=10)

        files = [f"/path/frame_{i:04d}.png" for i in range(20)]
        cache.set_image_sequence(files)

        results: list[QImage | None] = []
        errors: list[Exception] = []

        def load_frames(start: int, end: int) -> None:
            """Worker function to load frames in separate thread."""
            try:
                for frame in range(start, end):
                    with patch.object(cache, "_load_image_from_disk", return_value=Mock(spec=QImage)):
                        result = cache.get_image(frame)
                        results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [
            threading.Thread(target=load_frames, args=(0, 10)),
            threading.Thread(target=load_frames, args=(10, 20)),
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0

        # Verify cache size invariant (never exceeds max)
        assert cache.cache_size <= 10

    def test_clear_cache_thread_safe(self):
        """Test that clear_cache clears both cache and LRU order."""
        cache = SafeImageCacheManager()

        # Populate cache
        cache._cache[0] = Mock(spec=QImage)
        cache._cache[1] = Mock(spec=QImage)
        cache._lru_order = [0, 1]

        # Clear cache
        cache.clear_cache()

        # Verify cache cleared
        assert cache.cache_size == 0
        assert len(cache._lru_order) == 0
        assert len(cache._cache) == 0


class TestErrorHandling:
    """Test error handling and logging."""

    def test_logging_on_cache_miss(self):
        """Test that cache miss is logged."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        with patch("services.image_cache_manager.logger") as mock_logger:
            with patch.object(cache, "_load_image_from_disk", return_value=Mock(spec=QImage)):
                cache.get_image(0)

            # Verify debug log for cache miss
            assert any("MISS" in str(call) for call in mock_logger.debug.call_args_list)

    def test_logging_on_cache_hit(self):
        """Test that cache hit is logged."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        with patch("services.image_cache_manager.logger") as mock_logger:
            with patch.object(cache, "_load_image_from_disk", return_value=Mock(spec=QImage)):
                # First access (miss)
                cache.get_image(0)

                # Clear previous calls
                mock_logger.reset_mock()

                # Second access (hit)
                cache.get_image(0)

            # Verify debug log for cache hit
            assert any("HIT" in str(call) for call in mock_logger.debug.call_args_list)

    def test_logging_on_eviction(self):
        """Test that eviction is logged."""
        cache = SafeImageCacheManager(max_cache_size=2)

        files = [f"/path/frame_{i:04d}.png" for i in range(3)]
        cache.set_image_sequence(files)

        with patch("services.image_cache_manager.logger") as mock_logger:
            with patch.object(cache, "_load_image_from_disk", return_value=Mock(spec=QImage)):
                # Fill cache
                cache.get_image(0)
                cache.get_image(1)

                # Clear previous calls
                mock_logger.reset_mock()

                # Trigger eviction
                cache.get_image(2)

            # Verify debug log for eviction
            assert any("EVICT" in str(call) for call in mock_logger.debug.call_args_list)

    def test_logging_on_load_failure(self):
        """Test that load failure is logged."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        with patch("services.image_cache_manager.logger") as mock_logger:
            with patch.object(cache, "_load_image_from_disk", return_value=None):
                cache.get_image(0)

            # Verify error log
            assert mock_logger.error.call_count >= 1

    def test_frame_out_of_bounds_logged(self):
        """Test that out-of-bounds frame access is logged."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        with patch("services.image_cache_manager.logger") as mock_logger:
            cache.get_image(99)

            # Verify debug log for out of bounds
            assert any("out of bounds" in str(call) for call in mock_logger.debug.call_args_list)


class TestCacheProperties:
    """Test cache property accessors."""

    def test_cache_size_property(self):
        """Test that cache_size property returns correct count."""
        cache = SafeImageCacheManager()

        assert cache.cache_size == 0

        # Add frames manually (simulate loading)
        cache._cache[0] = Mock(spec=QImage)
        cache._cache[1] = Mock(spec=QImage)

        assert cache.cache_size == 2

    def test_max_cache_size_property(self):
        """Test that max_cache_size property is accessible."""
        cache = SafeImageCacheManager(max_cache_size=150)

        assert cache.max_cache_size == 150

    def test_cache_size_thread_safe(self):
        """Test that cache_size property returns correct count."""
        cache = SafeImageCacheManager()

        # Initially empty
        assert cache.cache_size == 0

        # Add frames manually (simulate loading)
        cache._cache[0] = Mock(spec=QImage)
        assert cache.cache_size == 1

        cache._cache[1] = Mock(spec=QImage)
        cache._cache[2] = Mock(spec=QImage)
        assert cache.cache_size == 3

        # Clear and verify
        cache._cache.clear()
        assert cache.cache_size == 0


class TestImagePreloading:
    """Test background image preloading (Phase 2B)."""

    def test_preload_range_starts_worker(self):
        """Test that preload_range creates and starts worker thread."""
        cache = SafeImageCacheManager(max_cache_size=100)

        files = [f"/path/frame_{i:04d}.png" for i in range(100)]
        cache.set_image_sequence(files)

        # Mock worker to prevent actual loading
        with patch("services.image_cache_manager.SafeImagePreloadWorker") as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker

            cache.preload_range(10, 20)

            # Verify worker created with correct frames
            mock_worker_class.assert_called_once()
            call_args = mock_worker_class.call_args
            assert call_args[0][0] == files  # image_files
            assert call_args[0][1] == list(range(10, 21))  # frames_to_load (inclusive)

            # Verify worker started
            mock_worker.start.assert_called_once()

    def test_preload_around_frame_calculates_range(self):
        """Test that preload_around_frame calculates correct frame range."""
        cache = SafeImageCacheManager()

        files = [f"/path/frame_{i:04d}.png" for i in range(200)]
        cache.set_image_sequence(files)

        with patch("services.image_cache_manager.SafeImagePreloadWorker") as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker

            # Test window_size=20 (±20 frames)
            cache.preload_around_frame(100, window_size=20)

            call_args = mock_worker_class.call_args
            frames_to_load = call_args[0][1]
            assert frames_to_load == list(range(80, 121))  # 100±20 (inclusive)

    def test_preload_around_frame_clamps_to_bounds(self):
        """Test that frame range is clamped to sequence bounds."""
        cache = SafeImageCacheManager()

        files = [f"/path/frame_{i:04d}.png" for i in range(50)]
        cache.set_image_sequence(files)

        with patch("services.image_cache_manager.SafeImagePreloadWorker") as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker

            # Test near start (would go negative)
            cache.preload_around_frame(10, window_size=20)
            call_args = mock_worker_class.call_args
            frames_to_load = call_args[0][1]
            assert frames_to_load[0] == 0  # Clamped to 0 (not -10)
            assert frames_to_load[-1] == 30  # 10+20

            # Test near end (would exceed length)
            cache.preload_around_frame(45, window_size=20)
            call_args = mock_worker_class.call_args
            frames_to_load = call_args[0][1]
            assert frames_to_load[0] == 25  # 45-20
            assert frames_to_load[-1] == 49  # Clamped to len-1 (not 65)

    def test_preload_filters_cached_frames(self):
        """Test that preload doesn't reload frames already in cache."""
        cache = SafeImageCacheManager()

        files = [f"/path/frame_{i:04d}.png" for i in range(20)]
        cache.set_image_sequence(files)

        # Manually populate cache with frames 5-9
        for i in range(5, 10):
            cache._cache[i] = Mock(spec=QImage)
            cache._lru_order.append(i)

        with patch("services.image_cache_manager.SafeImagePreloadWorker") as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker

            # Request preload of frames 0-14
            cache.preload_range(0, 14)

            # Verify only non-cached frames passed to worker
            call_args = mock_worker_class.call_args
            frames_to_load = call_args[0][1]

            # Should exclude 5-9 (already cached)
            expected = list(range(5)) + list(range(10, 15))
            assert frames_to_load == expected

    def test_preload_with_all_frames_cached(self):
        """Test that preload with all frames cached doesn't start worker."""
        cache = SafeImageCacheManager()

        files = [f"/path/frame_{i:04d}.png" for i in range(10)]
        cache.set_image_sequence(files)

        # Cache all frames 0-4
        for i in range(5):
            cache._cache[i] = Mock(spec=QImage)
            cache._lru_order.append(i)

        with patch("services.image_cache_manager.SafeImagePreloadWorker") as mock_worker_class:
            # Request preload of already-cached frames
            cache.preload_range(0, 4)

            # Worker should not be created (all frames cached)
            mock_worker_class.assert_not_called()

    def test_preload_stops_existing_worker(self):
        """Test that starting new preload stops existing worker."""
        cache = SafeImageCacheManager()

        files = [f"/path/frame_{i:04d}.png" for i in range(100)]
        cache.set_image_sequence(files)

        with patch("services.image_cache_manager.SafeImagePreloadWorker") as mock_worker_class:
            # Create first worker
            mock_worker1 = Mock()
            mock_worker1.isRunning.return_value = True
            mock_worker_class.return_value = mock_worker1

            cache.preload_range(0, 10)

            # Start second preload (should stop first worker)
            mock_worker2 = Mock()
            mock_worker_class.return_value = mock_worker2

            cache.preload_range(50, 60)

            # Verify first worker stopped
            mock_worker1.stop.assert_called_once()
            mock_worker1.wait.assert_called_once()

    def test_set_image_sequence_stops_worker(self):
        """Test that setting new sequence stops preload worker."""
        cache = SafeImageCacheManager()

        files1 = [f"/path/frame_{i:04d}.png" for i in range(50)]
        cache.set_image_sequence(files1)

        with patch("services.image_cache_manager.SafeImagePreloadWorker") as mock_worker_class:
            mock_worker = Mock()
            mock_worker.isRunning.return_value = True
            mock_worker_class.return_value = mock_worker

            # Start preload
            cache.preload_range(0, 10)

            # Set new sequence (should stop worker)
            files2 = [f"/path/other_{i:04d}.png" for i in range(50)]
            cache.set_image_sequence(files2)

            # Verify worker stopped
            mock_worker.stop.assert_called_once()
            mock_worker.wait.assert_called_once()

    def test_preload_no_sequence_loaded(self):
        """Test that preload without sequence loaded is no-op."""
        cache = SafeImageCacheManager()

        # No sequence set
        with patch("services.image_cache_manager.SafeImagePreloadWorker") as mock_worker_class:
            cache.preload_range(0, 10)

            # Worker should not be created
            mock_worker_class.assert_not_called()

    def test_preload_invalid_range(self):
        """Test that invalid range (start > end) is handled."""
        cache = SafeImageCacheManager()

        files = [f"/path/frame_{i:04d}.png" for i in range(50)]
        cache.set_image_sequence(files)

        with patch("services.image_cache_manager.SafeImagePreloadWorker") as mock_worker_class:
            # Invalid range
            cache.preload_range(20, 10)

            # Worker should not be created
            mock_worker_class.assert_not_called()


class TestWorkerThreadSafety:
    """Test worker thread safety and signal handling (Phase 2B)."""

    def test_worker_emits_image_loaded_signal(self):
        """Test that worker emits image_loaded signal with QImage."""
        from services.image_cache_manager import SafeImagePreloadWorker

        files = ["/path/frame_0001.png", "/path/frame_0002.png"]
        frames = [0, 1]

        worker = SafeImagePreloadWorker(files, frames)

        # Collect emitted signals
        signals_received: list[tuple[int, object]] = []

        def capture_signal(frame: int, image: object) -> None:
            signals_received.append((frame, image))

        worker.image_loaded.connect(capture_signal)

        # Mock image loading
        with patch.object(worker, "_load_image") as mock_load:
            mock_image = Mock(spec=QImage)
            mock_load.return_value = mock_image

            worker.run()

            # Verify signals emitted for both frames
            assert len(signals_received) == 2
            assert signals_received[0][0] == 0
            assert signals_received[1][0] == 1

            # Verify QImage objects passed
            assert isinstance(signals_received[0][1], Mock)
            assert isinstance(signals_received[1][1], Mock)

    def test_worker_emits_progress_signal(self):
        """Test that worker emits progress signals."""
        from services.image_cache_manager import SafeImagePreloadWorker

        files = [f"/path/frame_{i:04d}.png" for i in range(5)]
        frames = list(range(5))

        worker = SafeImagePreloadWorker(files, frames)

        # Collect progress signals
        progress_signals: list[tuple[int, int]] = []

        def capture_progress(loaded: int, total: int) -> None:
            progress_signals.append((loaded, total))

        worker.progress.connect(capture_progress)

        # Mock image loading
        with patch.object(worker, "_load_image") as mock_load:
            mock_load.return_value = Mock(spec=QImage)

            worker.run()

            # Verify progress signals emitted
            assert len(progress_signals) == 5
            assert progress_signals[0] == (1, 5)
            assert progress_signals[4] == (5, 5)

    def test_worker_no_qpixmap_created(self):
        """CRITICAL: Verify worker never creates QPixmap (main-thread-only)."""
        from services.image_cache_manager import SafeImagePreloadWorker

        files = ["/path/frame_0001.png"]
        frames = [0]

        worker = SafeImagePreloadWorker(files, frames)

        # Mock QImage to succeed
        with patch("PySide6.QtGui.QImage") as mock_qimage_class:
            mock_image = Mock(spec=QImage)
            mock_image.isNull.return_value = False
            mock_qimage_class.return_value = mock_image

            with (
                patch("services.image_cache_manager.Path.exists", return_value=True),
                patch("PySide6.QtGui.QPixmap") as mock_qpixmap_class,
            ):
                result = worker._load_image("/path/frame_0001.png")

                # Verify QPixmap never created
                mock_qpixmap_class.assert_not_called()

                # Verify QImage was created
                assert result is mock_image

    def test_worker_handles_missing_file(self):
        """Test that worker handles missing files gracefully."""
        from services.image_cache_manager import SafeImagePreloadWorker

        files = ["/nonexistent/frame_0001.png"]
        frames = [0]

        worker = SafeImagePreloadWorker(files, frames)

        # Collect signals
        signals_received: list[tuple[int, object]] = []
        worker.image_loaded.connect(lambda f, img: signals_received.append((f, img)))

        # Run worker (file doesn't exist)
        worker.run()

        # Verify no signal emitted for missing file
        assert len(signals_received) == 0

    def test_worker_handles_exr_format(self):
        """Test that worker uses EXR loader for .exr files."""
        from services.image_cache_manager import SafeImagePreloadWorker

        files = ["/path/frame_0001.exr"]
        frames = [0]

        worker = SafeImagePreloadWorker(files, frames)

        with patch("io_utils.exr_loader.load_exr_as_qimage") as mock_exr_load:
            mock_image = Mock(spec=QImage)
            mock_exr_load.return_value = mock_image

            with patch("services.image_cache_manager.Path.exists", return_value=True):
                result = worker._load_image("/path/frame_0001.exr")

            # Verify EXR loader used
            mock_exr_load.assert_called_once_with("/path/frame_0001.exr")
            assert result is mock_image

    def test_worker_graceful_stop(self):
        """Test that worker stops gracefully when requested."""
        from services.image_cache_manager import SafeImagePreloadWorker

        files = [f"/path/frame_{i:04d}.png" for i in range(100)]
        frames = list(range(100))

        worker = SafeImagePreloadWorker(files, frames)

        # Collect loaded frames
        loaded_frames: list[int] = []

        def capture_frame(frame: int, image: object) -> None:
            loaded_frames.append(frame)
            # Request stop after first frame
            if len(loaded_frames) == 1:
                worker.stop()

        worker.image_loaded.connect(capture_frame)

        # Mock image loading
        with patch.object(worker, "_load_image") as mock_load:
            mock_load.return_value = Mock(spec=QImage)

            worker.run()

            # Verify worker stopped early (not all 100 frames loaded)
            assert len(loaded_frames) < 100

    def test_worker_skips_out_of_bounds_frames(self):
        """Test that worker skips frames outside valid range."""
        from services.image_cache_manager import SafeImagePreloadWorker

        files = [f"/path/frame_{i:04d}.png" for i in range(10)]
        frames = [-1, 0, 5, 10, 15]  # -1 and 10, 15 are out of bounds

        worker = SafeImagePreloadWorker(files, frames)

        # Collect loaded frames
        loaded_frames: list[int] = []
        worker.image_loaded.connect(lambda f, img: loaded_frames.append(f))

        # Mock image loading
        with patch.object(worker, "_load_image") as mock_load:
            mock_load.return_value = Mock(spec=QImage)

            worker.run()

            # Verify only valid frames loaded (0, 5)
            assert loaded_frames == [0, 5]

    def test_on_image_preloaded_adds_to_cache(self):
        """Test that _on_image_preloaded adds image to cache."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        mock_image = Mock(spec=QImage)

        # Call slot directly (simulates signal from worker)
        cache._on_image_preloaded(0, mock_image)

        # Verify image added to cache
        assert 0 in cache._cache
        assert cache._cache[0] is mock_image

    def test_on_image_preloaded_skips_cached_frame(self):
        """Test that _on_image_preloaded doesn't overwrite cached frames."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        # Pre-cache frame 0
        original_image = Mock(spec=QImage)
        cache._cache[0] = original_image
        cache._lru_order.append(0)

        # Try to overwrite with preloaded image
        preloaded_image = Mock(spec=QImage)
        cache._on_image_preloaded(0, preloaded_image)

        # Verify original image retained (not overwritten)
        assert cache._cache[0] is original_image

    def test_on_image_preloaded_rejects_invalid_type(self):
        """Test that _on_image_preloaded rejects non-QImage objects."""
        cache = SafeImageCacheManager()

        files = ["/path/frame_0001.png"]
        cache.set_image_sequence(files)

        # Pass invalid type (string instead of QImage)
        cache._on_image_preloaded(0, "not_an_image")

        # Verify not added to cache
        assert 0 not in cache._cache


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
