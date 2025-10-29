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
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

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

        original_load = cache._load_image_from_disk

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
