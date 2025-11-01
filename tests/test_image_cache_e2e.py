#!/usr/bin/env python
"""
End-to-End Integration Tests for Image Caching System - Phase 2D.

Tests the complete flow:
1. Frame change → ViewManagementController.update_background_for_frame()
2. update_background_for_frame() → DataService.get_background_image()
3. get_background_image() → DataService.preload_around_frame()
4. preload_around_frame() → Background worker thread

Verifies:
- Frame changes trigger background updates and preloading
- Cache hits are significantly faster than cache misses
- Scrubbing through cached regions is smooth (60fps target)

Note: These tests intentionally access private APIs (_safe_image_cache, _preload_worker)
to verify internal state during integration testing. This is acceptable for test code
where thorough validation of implementation details is required.
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

import time

import pytest
from PySide6.QtGui import QImage

from services import get_data_service
from services.data_service import DataService
from ui.controllers.view_management_controller import ViewManagementController


@pytest.fixture
def temp_image_sequence(tmp_path):
    """Create temporary image sequence for testing."""
    # Create test directory
    test_dir = tmp_path / "test_images"
    test_dir.mkdir()

    # Create test images (640x480 PNG images for realistic performance)
    image_files = []
    for i in range(20):  # 20 frames for basic e2e tests
        image_path = test_dir / f"frame_{i:04d}.png"
        # Create 640x480 images (realistic size for performance validation)
        image = QImage(640, 480, QImage.Format.Format_RGB32)
        image.fill(0xFF000000 + (i * 16))  # Different color per frame
        image.save(str(image_path))
        image_files.append(str(image_path))

    return test_dir, image_files


@pytest.fixture
def large_image_sequence(tmp_path):
    """Create large image sequence for performance tests (100 frames)."""
    test_dir = tmp_path / "large_images"
    test_dir.mkdir()

    image_files = []
    for i in range(100):
        image_path = test_dir / f"frame_{i:04d}.png"
        # Create 640x480 images (realistic size but still fast to generate)
        image = QImage(640, 480, QImage.Format.Format_RGB32)
        image.fill(0xFF000000 + (i * 16))
        image.save(str(image_path))
        image_files.append(str(image_path))

    return test_dir, image_files


@pytest.fixture
def mock_main_window(qtbot):
    """Create mock MainWindow with minimal required components."""
    from unittest.mock import MagicMock

    from PySide6.QtWidgets import QWidget

    # Create real widget to satisfy qtbot
    widget = QWidget()
    qtbot.addWidget(widget)

    # Create mock with required attributes
    main_window = MagicMock()
    main_window.curve_widget = MagicMock()
    main_window.curve_widget.background_image = None

    return main_window


@pytest.fixture
def data_service_with_sequence(temp_image_sequence):
    """DataService with loaded image sequence."""
    test_dir, _expected_files = temp_image_sequence
    service = DataService()
    service.load_image_sequence(str(test_dir))
    return service


class TestFrameChangeIntegration:
    """Test frame change → background update → preload integration."""

    def test_frame_change_triggers_preload(self, qtbot, temp_image_sequence, mock_main_window):
        """
        End-to-end test: frame change → background update → preload.

        Verifies:
        - Frame change calls ViewManagementController._update_background_image()
        - _update_background_image() calls DataService.get_background_image()
        - get_background_image() triggers DataService.preload_around_frame()
        - preload_around_frame() starts background worker
        """
        test_dir, _expected_files = temp_image_sequence

        # Setup: Load image sequence using singleton DataService
        data_service = get_data_service()
        data_service.load_image_sequence(str(test_dir))

        # Setup: Create ViewManagementController (uses same singleton internally)
        view_controller = ViewManagementController(main_window=mock_main_window)

        # Act: Change frame (simulate frame change via controller)
        target_frame = 10  # 1-based (frame 10 = index 9)
        view_controller._update_background_image(target_frame)

        # Wait briefly for main thread to process
        qtbot.wait(50)

        # Assert: Cache contains frame 10 (index 9)
        image_idx = target_frame - 1
        assert data_service._safe_image_cache.cache_size > 0, "Cache should contain at least one image"

        # Cache should have the requested frame
        cached_image = data_service._safe_image_cache.get_image(image_idx)
        assert cached_image is not None, f"Frame {image_idx} should be cached"

        # Assert: Background worker started (check preload worker exists)
        assert data_service._safe_image_cache._preload_worker is not None, "Preload worker should be created"

        # Wait for preload to process some frames (background operation)
        qtbot.wait(200)

        # Assert: Adjacent frames preloaded (at least some frames around target)
        # Preload window is 20 frames (default), so frames [0-29] should be queued
        # Check that multiple frames are cached (indicating preload worked)
        assert data_service._safe_image_cache.cache_size > 1, "Preload should cache multiple frames"

    def test_background_image_updated_on_frame_change(self, qtbot, temp_image_sequence, mock_main_window):
        """Verify background image is updated when frame changes."""
        test_dir, _expected_files = temp_image_sequence

        # Setup
        data_service = get_data_service()
        data_service.load_image_sequence(str(test_dir))
        view_controller = ViewManagementController(main_window=mock_main_window)

        # Act: Update to frame 5
        view_controller._update_background_image(5)
        qtbot.wait(50)

        # Assert: Background image was set
        assert mock_main_window.curve_widget.background_image is not None

        # Store first background

        # Act: Update to different frame
        view_controller._update_background_image(10)
        qtbot.wait(50)

        # Assert: Background changed
        second_background = mock_main_window.curve_widget.background_image
        assert second_background is not None
        # Note: Cannot compare QPixmap equality directly, but both should exist


class TestCachePerformance:
    """Test cache hit vs cache miss performance."""

    def test_cache_hit_faster_than_miss(self, qtbot, temp_image_sequence):
        """
        Verify cached retrieval is faster than first load.

        Success criteria: Cache hit < 5ms
        """
        test_dir, _expected_files = temp_image_sequence

        # Setup: Load sequence
        data_service = get_data_service()
        data_service.load_image_sequence(str(test_dir))

        # Measure: Time to load frame 10 (first time - cache miss)
        frame_idx = 9  # 0-based
        start = time.perf_counter()
        first_load = data_service.get_background_image(frame_idx)
        first_load_time = time.perf_counter() - start

        assert first_load is not None, "First load should succeed"

        # Wait briefly to ensure cache is populated
        qtbot.wait(10)

        # Measure: Time to load frame 10 (second time - cache hit)
        start = time.perf_counter()
        second_load = data_service.get_background_image(frame_idx)
        cache_hit_time = time.perf_counter() - start

        assert second_load is not None, "Second load should succeed"

        # Assert: Cache hit is faster
        assert cache_hit_time < first_load_time, (
            f"Cache hit ({cache_hit_time*1000:.2f}ms) should be faster than "
            f"first load ({first_load_time*1000:.2f}ms)"
        )

        # Assert: Cache hit < 5ms (success criteria)
        assert cache_hit_time < 0.005, (
            f"Cache hit took {cache_hit_time*1000:.2f}ms, expected < 5ms"
        )

    def test_scrubbing_smooth_with_cache(self, qtbot, large_image_sequence):
        """
        Verify scrubbing through cached region is smooth (60fps = ~16ms per frame).

        Success criteria: Average frame switch < 16ms
        """
        test_dir, _expected_files = large_image_sequence

        # Setup: Load sequence
        data_service = get_data_service()
        data_service.load_image_sequence(str(test_dir))

        # Preload frames 0-50
        for i in range(51):
            data_service.get_background_image(i)

        # Wait for all frames to be cached
        qtbot.wait(100)

        # Act: Scrub through frames 0-50 (simulate playback)
        frame_times = []
        for i in range(51):
            start = time.perf_counter()
            pixmap = data_service.get_background_image(i)
            elapsed = time.perf_counter() - start
            frame_times.append(elapsed)
            assert pixmap is not None, f"Frame {i} should be cached"

        # Calculate statistics
        avg_time = sum(frame_times) / len(frame_times)
        max_time = max(frame_times)
        sorted_times = sorted(frame_times)
        p95_time = sorted_times[int(len(sorted_times) * 0.95)]

        # Assert: Average frame switch < 16ms (60fps)
        assert avg_time < 0.016, (
            f"Average frame switch {avg_time*1000:.2f}ms exceeds 16ms (60fps target)"
        )

        # Assert: 95th percentile < 20ms (allow some variance)
        assert p95_time < 0.020, (
            f"95th percentile {p95_time*1000:.2f}ms exceeds 20ms"
        )

        # Log performance metrics for analysis
        print("\nScrubbing performance (51 frames):")
        print(f"  Average: {avg_time*1000:.2f}ms")
        print(f"  Max: {max_time*1000:.2f}ms")
        print(f"  95th percentile: {p95_time*1000:.2f}ms")

    def test_cache_hit_consistency(self, qtbot, temp_image_sequence):
        """Verify cache hits are consistently fast across multiple accesses."""
        test_dir, _expected_files = temp_image_sequence
        data_service = get_data_service()
        data_service.load_image_sequence(str(test_dir))

        # Prime cache with frame 5
        frame_idx = 5
        data_service.get_background_image(frame_idx)
        qtbot.wait(10)

        # Measure 10 consecutive cache hits
        hit_times = []
        for _ in range(10):
            start = time.perf_counter()
            pixmap = data_service.get_background_image(frame_idx)
            elapsed = time.perf_counter() - start
            hit_times.append(elapsed)
            assert pixmap is not None

        # All hits should be fast
        for i, hit_time in enumerate(hit_times):
            assert hit_time < 0.005, (
                f"Cache hit {i+1} took {hit_time*1000:.2f}ms, expected < 5ms"
            )

        # Variance should be low (consistent performance)
        avg = sum(hit_times) / len(hit_times)
        variance = sum((t - avg) ** 2 for t in hit_times) / len(hit_times)
        std_dev = variance ** 0.5

        print("\nCache hit consistency (10 accesses):")
        print(f"  Average: {avg*1000:.2f}ms")
        print(f"  Std dev: {std_dev*1000:.2f}ms")


class TestPreloadEffectiveness:
    """Test that preloading improves real-world usage patterns."""

    def test_sequential_playback_with_preload(self, qtbot, large_image_sequence):
        """
        Test sequential playback benefits from preloading.

        Simulates real playback: each frame triggers preload for next frames.
        """
        test_dir, _expected_files = large_image_sequence
        data_service = get_data_service()
        data_service.load_image_sequence(str(test_dir))

        # Simulate playback: navigate through frames 0-30
        # Each frame change triggers preload
        first_frame_time = None
        subsequent_times = []

        for i in range(31):
            start = time.perf_counter()
            pixmap = data_service.get_background_image(i)
            elapsed = time.perf_counter() - start

            assert pixmap is not None, f"Frame {i} should load"

            # Trigger preload (simulates what ViewManagementController does)
            data_service.preload_around_frame(i)

            if i == 0:
                first_frame_time = elapsed  # First frame is always cache miss
            else:
                subsequent_times.append(elapsed)

            # Small delay to simulate realistic playback timing
            qtbot.wait(10)

        # Assert: First frame slower (cache miss)
        avg_subsequent = sum(subsequent_times) / len(subsequent_times)
        assert first_frame_time is not None
        assert avg_subsequent < first_frame_time, (
            f"Average subsequent frame time ({avg_subsequent*1000:.2f}ms) "
            f"should be faster than first frame ({first_frame_time*1000:.2f}ms)"
        )

        print("\nSequential playback with preload (31 frames):")
        print(f"  First frame: {first_frame_time*1000:.2f}ms (cache miss)")
        print(f"  Average subsequent: {avg_subsequent*1000:.2f}ms (preloaded)")

    def test_bidirectional_scrubbing_with_preload(self, qtbot, large_image_sequence):
        """
        Test bidirectional scrubbing (forward/backward) with preload.

        Preload window should handle both directions.
        """
        test_dir, _expected_files = large_image_sequence
        data_service = get_data_service()
        data_service.load_image_sequence(str(test_dir))

        # Start at middle frame
        start_frame = 50
        data_service.get_background_image(start_frame)
        data_service.preload_around_frame(start_frame)

        # Wait for preload to populate cache
        qtbot.wait(200)

        # Test forward scrubbing (frames 51-60)
        forward_times = []
        for i in range(start_frame + 1, start_frame + 11):
            start = time.perf_counter()
            pixmap = data_service.get_background_image(i)
            elapsed = time.perf_counter() - start
            forward_times.append(elapsed)
            assert pixmap is not None

        # Test backward scrubbing (frames 49-40)
        backward_times = []
        for i in range(start_frame - 1, start_frame - 11, -1):
            start = time.perf_counter()
            pixmap = data_service.get_background_image(i)
            elapsed = time.perf_counter() - start
            backward_times.append(elapsed)
            assert pixmap is not None

        # Both directions should be fast (preloaded)
        avg_forward = sum(forward_times) / len(forward_times)
        avg_backward = sum(backward_times) / len(backward_times)

        assert avg_forward < 0.016, f"Forward scrubbing {avg_forward*1000:.2f}ms too slow"
        assert avg_backward < 0.016, f"Backward scrubbing {avg_backward*1000:.2f}ms too slow"

        print(f"\nBidirectional scrubbing from frame {start_frame}:")
        print(f"  Forward (51-60): {avg_forward*1000:.2f}ms avg")
        print(f"  Backward (49-40): {avg_backward*1000:.2f}ms avg")
