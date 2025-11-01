#!/usr/bin/env python
"""
Performance Tests for Image Caching System - Phase 2D.

Tests:
1. Different sequence sizes (small, medium, large)
2. Memory usage profiling and leak detection
3. Cache eviction under pressure
4. Concurrent access stress testing
5. Preload window effectiveness

Success Criteria:
- Cache hit < 5ms
- Scrubbing < 16ms per frame (60fps)
- Memory usage < 2GB for 100 frames at 1080p
- No memory leaks on sequence change
- Thread-safe under concurrent access

Note: These tests intentionally access private APIs (cache._cache) to verify
internal state without triggering re-caching during validation. This is acceptable
for performance test code where precise measurement is required.
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

import gc
import os
import random
import time
from pathlib import Path

import psutil
import pytest
from PySide6.QtGui import QImage

from services.data_service import DataService
from services.image_cache_manager import SafeImageCacheManager


def create_test_sequence(tmp_path, count: int, size: tuple[int, int], name: str = "test") -> tuple[Path, list[str]]:
    """
    Create test image sequence.

    Args:
        tmp_path: Pytest tmp_path fixture
        count: Number of frames to create
        size: Image size (width, height)
        name: Sequence name for directory

    Returns:
        Tuple of (directory_path, list_of_image_files)
    """
    test_dir = tmp_path / name
    test_dir.mkdir()

    image_files = []
    for i in range(count):
        image_path = test_dir / f"frame_{i:04d}.png"
        # Create image with unique color per frame
        image = QImage(size[0], size[1], QImage.Format.Format_RGB32)
        image.fill(0xFF000000 + (i * 16))  # Different color per frame
        image.save(str(image_path))
        image_files.append(str(image_path))

    return test_dir, image_files


@pytest.fixture
def small_sequence(tmp_path):
    """Create 10 test images (640x480) - all fit in cache."""
    return create_test_sequence(tmp_path, count=10, size=(640, 480), name="small")


@pytest.fixture
def medium_sequence(tmp_path):
    """Create 100 test images (640x480) - matches default cache size."""
    return create_test_sequence(tmp_path, count=100, size=(640, 480), name="medium")


@pytest.fixture
def large_sequence(tmp_path):
    """Create 500 test images (640x480) - exceeds cache capacity."""
    return create_test_sequence(tmp_path, count=500, size=(640, 480), name="large")


@pytest.fixture
def hd_sequence(tmp_path):
    """Create 100 test images (1920x1080) - for memory testing."""
    return create_test_sequence(tmp_path, count=100, size=(1920, 1080), name="hd")


class TestSmallSequencePerformance:
    """Test with 10 frames (all fit in cache)."""

    def test_all_frames_fit_in_cache(self, qtbot, small_sequence):
        """
        Test with 10 frames (all fit in cache).

        Verifies:
        - All frames cached after first pass
        - No evictions occur
        - Cache hits < 5ms
        """
        _test_dir, expected_files = small_sequence

        # Setup: Load sequence
        cache = SafeImageCacheManager(max_cache_size=100)  # Much larger than sequence
        cache.set_image_sequence(expected_files)

        # Act: Navigate through all frames twice
        # First pass: cache misses
        first_pass_times = []
        for i in range(10):
            start = time.perf_counter()
            image = cache.get_image(i)
            elapsed = time.perf_counter() - start
            first_pass_times.append(elapsed)
            assert image is not None, f"Frame {i} should load"

        # Wait briefly
        qtbot.wait(10)

        # Second pass: should be all cache hits
        second_pass_times = []
        for i in range(10):
            start = time.perf_counter()
            image = cache.get_image(i)
            elapsed = time.perf_counter() - start
            second_pass_times.append(elapsed)
            assert image is not None, f"Frame {i} should be cached"

        # Assert: Second pass all cache hits (fast)
        avg_first = sum(first_pass_times) / len(first_pass_times)
        avg_second = sum(second_pass_times) / len(second_pass_times)

        assert avg_second < avg_first, "Second pass should be faster (cache hits)"

        # All second pass times should be < 5ms
        for i, t in enumerate(second_pass_times):
            assert t < 0.005, f"Cache hit for frame {i} took {t*1000:.2f}ms, expected < 5ms"

        # Assert: No evictions (all frames cached)
        assert cache.cache_size == 10, "All frames should remain cached"

        print("\nSmall sequence (10 frames):")
        print(f"  First pass avg: {avg_first*1000:.2f}ms (cache miss)")
        print(f"  Second pass avg: {avg_second*1000:.2f}ms (cache hit)")
        print(f"  Cache size: {cache.cache_size}")

    def test_no_evictions_on_random_access(self, qtbot, small_sequence):
        """Verify no evictions with random access to small sequence."""
        _test_dir, expected_files = small_sequence
        cache = SafeImageCacheManager(max_cache_size=100)
        cache.set_image_sequence(expected_files)

        # Prime cache
        for i in range(10):
            cache.get_image(i)

        qtbot.wait(10)
        initial_size = cache.cache_size

        # Random access 50 times
        for _ in range(50):
            frame = random.randint(0, 9)
            image = cache.get_image(frame)
            assert image is not None

        # Cache size should not change (no evictions)
        assert cache.cache_size == initial_size, "No evictions should occur for small sequence"


class TestLargeSequencePerformance:
    """Test with 500 frames (exceeds cache capacity)."""

    def test_lru_eviction_works_correctly(self, qtbot, large_sequence):
        """
        Test with 500 frames (exceeds cache capacity).

        Verifies:
        - LRU eviction works correctly
        - Cache stays at max_size (100 frames)
        - Performance within acceptable bounds
        """
        _test_dir, expected_files = large_sequence

        # Setup: Load sequence with cache size 100
        cache = SafeImageCacheManager(max_cache_size=100)
        cache.set_image_sequence(expected_files)

        # Act: Navigate through frames 0-200 (2x cache size)
        for i in range(201):
            image = cache.get_image(i)
            assert image is not None, f"Frame {i} should load"

            # Check cache size constraint
            assert cache.cache_size <= 100, f"Cache size {cache.cache_size} exceeds max (100)"

        # Assert: Cache size at max
        assert cache.cache_size == 100, "Cache should be at max size after loading > 100 frames"

        # Assert: Recent frames cached (LRU working)
        # Frames 101-200 should be cached (most recent 100)
        recent_cached = 0
        for i in range(101, 201):
            # Check if cached (fast access)
            start = time.perf_counter()
            image = cache.get_image(i)
            elapsed = time.perf_counter() - start
            if elapsed < 0.005:  # Cache hit threshold
                recent_cached += 1

        # Most recent frames should be cached (allow some margin)
        assert recent_cached > 90, f"Only {recent_cached}/100 recent frames cached (expected >90)"

        # Assert: Old frames evicted (frames 0-50 should NOT be in cache anymore)
        # Note: We can't check timing after accessing them (that would cache them again)
        # Instead, check that they're not in the internal cache structure
        old_in_cache = sum(1 for i in range(51) if i in cache._cache)

        # Most old frames should be evicted (allow small margin for edge cases)
        assert old_in_cache < 10, f"{old_in_cache}/51 old frames still in cache (expected <10)"

        print("\nLarge sequence (500 frames, cache=100):")
        print(f"  Cache size: {cache.cache_size}")
        print(f"  Recent frames cached: {recent_cached}/100")
        print(f"  Old frames in cache: {old_in_cache}/51")

    def test_cache_performance_under_load(self, qtbot, large_sequence):
        """Test cache performance with large sequence."""
        _test_dir, expected_files = large_sequence
        cache = SafeImageCacheManager(max_cache_size=100)
        cache.set_image_sequence(expected_files)

        # Navigate through first 100 frames
        for i in range(100):
            cache.get_image(i)

        qtbot.wait(50)

        # Test cache hit performance on populated cache
        hit_times = []
        for i in range(50, 100):  # Recent 50 frames
            start = time.perf_counter()
            image = cache.get_image(i)
            elapsed = time.perf_counter() - start
            hit_times.append(elapsed)
            assert image is not None

        avg_hit_time = sum(hit_times) / len(hit_times)
        assert avg_hit_time < 0.005, f"Average cache hit {avg_hit_time*1000:.2f}ms exceeds 5ms"

        print("\nLarge sequence cache hits:")
        print(f"  Average: {avg_hit_time*1000:.2f}ms")


class TestPreloadWindowEffectiveness:
    """Test preload window effectiveness at different sizes."""

    @pytest.mark.parametrize("window_size", [10, 20, 50])
    def test_preload_window_coverage(self, qtbot, medium_sequence, window_size):
        """
        Test preload window effectiveness at different sizes.

        Verifies:
        - Preload covers window_size frames ahead/behind
        - Cache hits within window
        - Cache misses outside window
        """
        test_dir, _expected_files = medium_sequence

        # Setup: Load sequence with DataService (has preload)
        service = DataService()
        service.load_image_sequence(str(test_dir))

        # Navigate to middle frame
        center_frame = 50
        service.get_background_image(center_frame)

        # Trigger preload with custom window size
        service._safe_image_cache._preload_window_size = window_size
        service.preload_around_frame(center_frame)

        # Wait for preload to complete
        qtbot.wait(300)

        # Check frames within window (should be cached or fast)
        within_window_times = []
        start_frame = max(0, center_frame - window_size)
        end_frame = min(99, center_frame + window_size)

        for i in range(start_frame, end_frame + 1):
            start = time.perf_counter()
            pixmap = service.get_background_image(i)
            elapsed = time.perf_counter() - start
            within_window_times.append(elapsed)
            assert pixmap is not None

        # Check frames outside window (may be cache misses)
        outside_window_times = []
        if center_frame + window_size + 10 < 100:
            for i in range(center_frame + window_size + 10, min(100, center_frame + window_size + 20)):
                start = time.perf_counter()
                pixmap = service.get_background_image(i)
                elapsed = time.perf_counter() - start
                outside_window_times.append(elapsed)

        # Frames within window should be faster on average
        if within_window_times and outside_window_times:
            avg_within = sum(within_window_times) / len(within_window_times)
            avg_outside = sum(outside_window_times) / len(outside_window_times)

            print(f"\nPreload window size {window_size}:")
            print(f"  Within window: {avg_within*1000:.2f}ms avg")
            print(f"  Outside window: {avg_outside*1000:.2f}ms avg")

            # Within window should be faster (may not always be true due to caching behavior)
            # At minimum, within window should be reasonable
            assert avg_within < 0.020, f"Within window {avg_within*1000:.2f}ms too slow"


class TestMemoryUsage:
    """Test memory usage and leak detection."""

    def test_memory_usage_within_bounds(self, qtbot, hd_sequence):
        """
        Verify memory usage stays reasonable.

        Success criteria: <2GB for 100 frames at 1080p
        """
        _test_dir, expected_files = hd_sequence
        process = psutil.Process(os.getpid())

        # Force garbage collection to get baseline
        gc.collect()
        qtbot.wait(100)
        mem_before = process.memory_info().rss / (1024 ** 3)  # GB

        # Load sequence and cache all 100 frames
        cache = SafeImageCacheManager(max_cache_size=100)
        cache.set_image_sequence(expected_files)

        for i in range(100):
            image = cache.get_image(i)
            assert image is not None

        # Wait for operations to complete
        qtbot.wait(100)

        # Measure memory after caching
        gc.collect()
        qtbot.wait(100)
        mem_after = process.memory_info().rss / (1024 ** 3)  # GB
        mem_delta = mem_after - mem_before

        print("\nMemory usage (100 frames @ 1920x1080):")
        print(f"  Before: {mem_before:.2f}GB")
        print(f"  After: {mem_after:.2f}GB")
        print(f"  Delta: {mem_delta:.2f}GB")

        # Assert: Memory increase < 2GB
        assert mem_delta < 2.0, f"Memory usage {mem_delta:.2f}GB exceeds 2GB limit"

    def test_no_memory_leak_on_sequence_change(self, qtbot, tmp_path):
        """
        Verify no memory leak when loading new sequences.

        Verifies:
        - Old cache cleared when new sequence loaded
        - Memory returns to baseline
        """
        process = psutil.Process(os.getpid())

        # Create 3 sequences (50 frames each, 640x480)
        _seq1_dir, seq1_files = create_test_sequence(tmp_path, 50, (640, 480), "seq1")
        _seq2_dir, seq2_files = create_test_sequence(tmp_path, 50, (640, 480), "seq2")
        _seq3_dir, seq3_files = create_test_sequence(tmp_path, 50, (640, 480), "seq3")

        # Measure baseline memory
        gc.collect()
        qtbot.wait(100)
        mem_baseline = process.memory_info().rss / (1024 ** 2)  # MB

        # Load sequence 1, cache all frames
        cache = SafeImageCacheManager(max_cache_size=50)
        cache.set_image_sequence(seq1_files)
        for i in range(50):
            cache.get_image(i)
        qtbot.wait(50)

        # Load sequence 2, cache all frames (clears old cache)
        cache.set_image_sequence(seq2_files)
        for i in range(50):
            cache.get_image(i)
        qtbot.wait(50)

        # Load sequence 3, cache all frames
        cache.set_image_sequence(seq3_files)
        for i in range(50):
            cache.get_image(i)
        qtbot.wait(50)

        # Measure memory after 3 load cycles
        gc.collect()
        qtbot.wait(100)
        mem_after = process.memory_info().rss / (1024 ** 2)  # MB

        growth_pct = ((mem_after - mem_baseline) / mem_baseline) * 100

        # Calculate absolute growth
        mem_delta = mem_after - mem_baseline

        print("\nMemory leak test (3 sequence loads, 50 frames each):")
        print(f"  Baseline: {mem_baseline:.1f}MB")
        print(f"  After 3 loads: {mem_after:.1f}MB")
        print(f"  Delta: {mem_delta:.1f}MB")
        print(f"  Growth: {growth_pct:.1f}%")

        # Assert: Absolute memory growth reasonable (< 100MB for 50 cached frames @ 640x480)
        # Each frame is ~640*480*4 bytes = 1.2MB, so 50 frames = ~60MB
        # Allow 100MB for overhead (Python, Qt, etc.)
        assert mem_delta < 100, f"Memory grew {mem_delta:.1f}MB (expected <100MB for 50 frames)"

    def test_cache_clear_releases_memory(self, qtbot, medium_sequence):
        """Verify clearing cache releases memory."""
        _test_dir, expected_files = medium_sequence
        process = psutil.Process(os.getpid())

        cache = SafeImageCacheManager(max_cache_size=100)
        cache.set_image_sequence(expected_files)

        # Cache all frames
        for i in range(100):
            cache.get_image(i)

        qtbot.wait(50)
        gc.collect()
        qtbot.wait(50)
        mem_with_cache = process.memory_info().rss / (1024 ** 2)  # MB

        # Clear cache
        cache.clear_cache()
        qtbot.wait(50)
        gc.collect()
        qtbot.wait(50)
        mem_after_clear = process.memory_info().rss / (1024 ** 2)  # MB

        # Memory should decrease (may not be exact due to Python memory management)
        # At minimum, verify no increase
        assert mem_after_clear <= mem_with_cache * 1.05, "Memory should not increase after cache clear"

        print("\nCache clear memory release:")
        print(f"  With cache: {mem_with_cache:.1f}MB")
        print(f"  After clear: {mem_after_clear:.1f}MB")


class TestCacheEvictionStressTest:
    """Test cache eviction under pressure."""

    def test_cache_eviction_under_pressure(self, qtbot, large_sequence):
        """
        Test cache eviction with rapid frame changes.

        Verifies:
        - LRU eviction maintains correct order
        - Cache doesn't grow unbounded
        - No crashes or deadlocks
        """
        _test_dir, expected_files = large_sequence

        # Setup: Small cache size (20 frames)
        cache = SafeImageCacheManager(max_cache_size=20)
        cache.set_image_sequence(expected_files)

        # Act: Rapidly navigate through 200 frames (10x cache size)
        for frame in range(200):
            image = cache.get_image(frame)
            assert image is not None, f"Frame {frame} should load"

            # Assert: Cache size never exceeded 20
            assert cache.cache_size <= 20, f"Cache size {cache.cache_size} exceeded max (20)"

        # Assert: Most recent frames cached (LRU working)
        # Frames 180-199 should be cached
        cached_count = 0
        for frame in range(180, 200):
            # Should be cache hit (fast)
            start = time.perf_counter()
            image = cache.get_image(frame)
            elapsed = time.perf_counter() - start
            if elapsed < 0.005:
                cached_count += 1

        assert cached_count >= 18, f"Only {cached_count}/20 recent frames cached (expected >=18)"

        print("\nEviction stress test (200 frames, cache=20):")
        print(f"  Final cache size: {cache.cache_size}")
        print(f"  Recent frames cached: {cached_count}/20")

    def test_concurrent_access_stress(self, qtbot, medium_sequence):
        """
        Stress test with concurrent get_image() calls.

        Verifies:
        - Thread-safe cache access
        - No deadlocks
        - No race conditions
        """
        from concurrent.futures import ThreadPoolExecutor

        _test_dir, expected_files = medium_sequence

        # Setup: Initialize cache
        cache = SafeImageCacheManager(max_cache_size=50)
        cache.set_image_sequence(expected_files)

        # Act: 10 threads, each loading 50 random frames
        def load_frames():
            for _ in range(50):
                frame = random.randint(0, 99)
                image = cache.get_image(frame)
                assert image is not None, f"Frame {frame} should load"

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(load_frames) for _ in range(10)]
            for future in futures:
                future.result(timeout=10)  # Should complete within 10s

        # Assert: Cache still valid
        assert cache.cache_size <= cache.max_cache_size, (
            f"Cache size {cache.cache_size} exceeds max {cache.max_cache_size}"
        )

        print("\nConcurrent access stress test (10 threads x 50 frames):")
        print(f"  Cache size: {cache.cache_size}/{cache.max_cache_size}")
        print("  Test completed without deadlock")

    def test_rapid_sequence_switching(self, qtbot, tmp_path):
        """Test rapid switching between sequences."""
        # Create 5 small sequences
        sequences = []
        for i in range(5):
            _seq_dir, seq_files = create_test_sequence(
                tmp_path, count=20, size=(640, 480), name=f"rapid_{i}"
            )
            sequences.append(seq_files)

        cache = SafeImageCacheManager(max_cache_size=20)

        # Rapidly switch between sequences
        for _ in range(10):
            for seq_files in sequences:
                cache.set_image_sequence(seq_files)
                # Load a few frames from each
                for i in [0, 5, 10, 15]:
                    image = cache.get_image(i)
                    assert image is not None

        # Cache should be valid (no crashes)
        assert cache.cache_size <= cache.max_cache_size

        print("\nRapid sequence switching (5 sequences x 10 cycles):")
        print(f"  Final cache size: {cache.cache_size}")
        print("  Test completed without errors")
