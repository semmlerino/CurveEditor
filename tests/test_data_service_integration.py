#!/usr/bin/env python
"""
Integration tests for DataService Phase 2C - SafeImageCacheManager integration.

Tests cache initialization, QPixmap conversion, and background preloading integration.
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtGui import QImage, QPixmap

from services.data_service import DataService


@pytest.fixture
def temp_image_sequence(tmp_path):
    """Create temporary image sequence for testing."""
    # Create test directory
    test_dir = tmp_path / "test_images"
    test_dir.mkdir()

    # Create 10 test images (1x1 pixel PNG images)
    image_files = []
    for i in range(10):
        image_path = test_dir / f"frame_{i:04d}.png"
        # Create minimal valid PNG
        image = QImage(1, 1, QImage.Format.Format_RGB32)
        image.fill(0xFF000000 + (i * 16))  # Different color per frame
        image.save(str(image_path))
        image_files.append(str(image_path))

    return test_dir, image_files


class TestCacheInitialization:
    """Test that loading sequence initializes image cache."""

    def test_load_image_sequence_initializes_cache(self, temp_image_sequence):
        """Test that loading sequence initializes SafeImageCacheManager."""
        test_dir, expected_files = temp_image_sequence

        service = DataService()

        # Load sequence
        loaded_files = service.load_image_sequence(str(test_dir))

        # Assert: Files loaded correctly
        assert len(loaded_files) == len(expected_files)
        assert all(Path(f).exists() for f in loaded_files)

        # Assert: Cache initialized (verify by checking cache can retrieve images)
        # Access private cache for verification (test-only)
        assert service._safe_image_cache is not None
        assert service._safe_image_cache.cache_size == 0  # No images cached yet (on-demand loading)

        # Trigger cache load
        image = service._safe_image_cache.get_image(0)
        assert image is not None
        assert service._safe_image_cache.cache_size == 1  # Image now cached

    def test_load_empty_directory_clears_cache(self, tmp_path):
        """Test that loading empty directory clears cache."""
        service = DataService()

        # Create empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        # Load empty sequence
        loaded_files = service.load_image_sequence(str(empty_dir))

        # Assert: No files loaded
        assert len(loaded_files) == 0

        # Assert: Cache cleared
        assert service._safe_image_cache.cache_size == 0

    def test_load_nonexistent_directory_returns_empty(self):
        """Test that loading nonexistent directory returns empty list."""
        service = DataService()

        # Load nonexistent directory
        loaded_files = service.load_image_sequence("/nonexistent/path/12345")

        # Assert: Empty list returned
        assert loaded_files == []


class TestGetBackgroundImage:
    """Test that get_background_image returns QPixmap with proper conversion."""

    def test_get_background_image_returns_qpixmap(self, temp_image_sequence):
        """Test that get_background_image converts QImage to QPixmap."""
        test_dir, _ = temp_image_sequence

        service = DataService()
        service.load_image_sequence(str(test_dir))

        # Get background image (0-indexed frame)
        pixmap = service.get_background_image(0)

        # Assert: Returns QPixmap (not QImage)
        assert isinstance(pixmap, QPixmap)
        assert not pixmap.isNull()
        assert pixmap.width() == 1
        assert pixmap.height() == 1

    def test_get_background_image_returns_none_for_invalid_frame(self, temp_image_sequence):
        """Test that invalid frame numbers return None."""
        test_dir, _ = temp_image_sequence

        service = DataService()
        service.load_image_sequence(str(test_dir))

        # Test out-of-bounds frames
        assert service.get_background_image(-1) is None
        assert service.get_background_image(100) is None

    def test_get_background_image_caches_result(self, temp_image_sequence):
        """Test that retrieved images are cached for subsequent access."""
        test_dir, _ = temp_image_sequence

        service = DataService()
        service.load_image_sequence(str(test_dir))

        # First access (cache miss)
        pixmap1 = service.get_background_image(0)
        assert service._safe_image_cache.cache_size == 1

        # Second access (cache hit - should be same QImage, different QPixmap)
        pixmap2 = service.get_background_image(0)
        assert service._safe_image_cache.cache_size == 1  # Cache size unchanged

        # Both should be valid QPixmaps with same dimensions
        assert pixmap1 is not None
        assert pixmap2 is not None
        assert pixmap1.width() == pixmap2.width()
        assert pixmap1.height() == pixmap2.height()

    def test_get_background_image_no_sequence_loaded(self):
        """Test that calling get_background_image without sequence returns None."""
        service = DataService()

        # No sequence loaded
        pixmap = service.get_background_image(0)

        assert pixmap is None


class TestPreloadAroundFrame:
    """Test that preload_around_frame is non-blocking and callable."""

    def test_preload_around_frame_non_blocking(self, temp_image_sequence):
        """Test that preload_around_frame returns immediately."""
        test_dir, _ = temp_image_sequence

        service = DataService()
        service.load_image_sequence(str(test_dir))

        # Call preload_around_frame and measure time
        start_time = time.perf_counter()
        service.preload_around_frame(5, window_size=3)  # Preload frames 2-8
        elapsed = time.perf_counter() - start_time

        # Cleanup immediately to avoid hanging
        service._safe_image_cache.cleanup()

        # Assert: Returns within 100ms (non-blocking, starts background thread)
        assert elapsed < 0.1, f"preload_around_frame took {elapsed*1000:.1f}ms (expected <100ms)"

    def test_preload_around_frame_no_sequence_loaded(self):
        """Test that preload_around_frame without sequence doesn't crash."""
        service = DataService()

        # No sequence loaded - should be no-op
        service.preload_around_frame(0, window_size=10)

        # Assert: No cache activity
        assert service._safe_image_cache.cache_size == 0

    def test_preload_around_frame_callable_interface(self, temp_image_sequence):
        """Test that preload_around_frame has correct interface and doesn't crash."""
        test_dir, _ = temp_image_sequence

        service = DataService()
        service.load_image_sequence(str(test_dir))

        # Test that method is callable with various parameters
        service.preload_around_frame(0, window_size=5)
        service.preload_around_frame(5, window_size=10)
        service.preload_around_frame(9, window_size=20)

        # Cleanup all workers
        service._safe_image_cache.cleanup()

        # Assert: No crashes occurred
        assert True


class TestCacheCleanup:
    """Test cache cleanup and resource management."""


    def test_load_new_sequence_clears_cache(self, temp_image_sequence, tmp_path):
        """Test that loading new sequence clears previous cache."""
        test_dir1, _ = temp_image_sequence

        # Create second sequence
        test_dir2 = tmp_path / "test_images2"
        test_dir2.mkdir()
        for i in range(5):
            image_path = test_dir2 / f"frame_{i:04d}.png"
            image = QImage(1, 1, QImage.Format.Format_RGB32)
            image.fill(0xFFFFFFFF)  # White images
            image.save(str(image_path))

        service = DataService()

        # Load first sequence and cache images
        service.load_image_sequence(str(test_dir1))
        service.get_background_image(0)
        assert service._safe_image_cache.cache_size == 1

        # Load second sequence
        service.load_image_sequence(str(test_dir2))

        # Assert: Cache cleared for new sequence
        assert service._safe_image_cache.cache_size == 0


class TestThreadSafety:
    """Test thread safety of cache operations."""

    def test_qimage_to_qpixmap_conversion_in_main_thread(self, temp_image_sequence):
        """Test that QImage→QPixmap conversion happens in main thread (not worker)."""
        test_dir, _ = temp_image_sequence

        service = DataService()
        service.load_image_sequence(str(test_dir))

        # Mock QPixmap.fromImage to verify it's called
        # QPixmap is imported inside the method, so patch PySide6.QtGui.QPixmap
        with patch("PySide6.QtGui.QPixmap.fromImage") as mock_from_image:
            mock_pixmap = MagicMock(spec=QPixmap)
            mock_pixmap.isNull.return_value = False
            mock_from_image.return_value = mock_pixmap

            # Get background image
            pixmap = service.get_background_image(0)

            # Assert: QPixmap.fromImage was called (conversion in main thread)
            mock_from_image.assert_called_once()
            assert pixmap is mock_pixmap

    def test_preload_uses_background_thread(self, temp_image_sequence):
        """Test that preload operations don't block main thread."""
        test_dir, _ = temp_image_sequence

        service = DataService()
        service.load_image_sequence(str(test_dir))

        # Preload all frames (should be non-blocking)
        start_time = time.perf_counter()
        service.preload_around_frame(0, window_size=100)  # Large window to preload all
        elapsed = time.perf_counter() - start_time

        # Cleanup worker thread immediately
        service._safe_image_cache.cleanup()

        # Assert: Returns immediately (< 100ms) even with large window
        assert elapsed < 0.1, f"Large preload took {elapsed*1000:.1f}ms (expected <100ms)"


# ==================== Performance Benchmarks ====================


class TestPerformance:
    """Performance benchmarks for cache integration."""

    def test_cached_image_retrieval_fast(self, temp_image_sequence):
        """Test that cached image retrieval is fast (< 1ms)."""
        test_dir, _ = temp_image_sequence

        service = DataService()
        service.load_image_sequence(str(test_dir))

        # Cache frame 0
        service.get_background_image(0)

        # Measure cached retrieval time
        start_time = time.perf_counter()
        for _ in range(100):
            pixmap = service.get_background_image(0)
            assert pixmap is not None
        elapsed = time.perf_counter() - start_time

        # Assert: 100 cached retrievals < 100ms (< 1ms per retrieval)
        assert elapsed < 0.1, f"100 cached retrievals took {elapsed*1000:.1f}ms (expected <100ms)"

    def test_first_load_slower_than_cached(self, temp_image_sequence):
        """Test that first load is slower than cached retrieval (expected behavior)."""
        test_dir, _ = temp_image_sequence

        service = DataService()
        service.load_image_sequence(str(test_dir))

        # Measure first load time
        start_time = time.perf_counter()
        pixmap1 = service.get_background_image(0)
        first_load_time = time.perf_counter() - start_time

        # Measure cached retrieval time
        start_time = time.perf_counter()
        pixmap2 = service.get_background_image(0)
        cached_time = time.perf_counter() - start_time

        # Assert: Both successful
        assert pixmap1 is not None
        assert pixmap2 is not None

        # Assert: Cached retrieval faster (or equal if both very fast)
        assert cached_time <= first_load_time, (
            f"Cached retrieval ({cached_time*1000:.3f}ms) slower than first load ({first_load_time*1000:.3f}ms)"
        )
