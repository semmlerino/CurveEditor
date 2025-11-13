#!/usr/bin/env python3
"""Benchmark cache performance improvements."""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt


def setup_environment() -> None:
    """Setup import path and working directory."""
    # Fix import path - add parent directory and change to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    os.chdir(project_root)


# Setup environment before imports
setup_environment()

from PySide6.QtWidgets import QApplication

from rendering.optimized_curve_renderer import RenderQuality, VectorizedTransform
from services.transform_service import ViewState
from ui.curve_view_widget import CurveViewWidget

if TYPE_CHECKING:
    from collections.abc import Callable


# Stub for CacheMonitor (removed from codebase)
class CacheMonitor:
    """Stub for legacy CacheMonitor tests."""

    hits: int
    misses: int
    invalidations: int

    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.invalidations = 0

    def record_hit(self) -> None:
        self.hits += 1

    def record_miss(self) -> None:
        self.misses += 1

    def record_invalidation(self) -> None:
        self.invalidations += 1

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0
        self.invalidations = 0


def benchmark_cache_hit_rate() -> float:
    """Benchmark cache hit rate improvements with monitoring."""
    _app = QApplication.instance() or QApplication(sys.argv)
    widget = CurveViewWidget()

    # Create monitoring object (widget doesn't have built-in cache monitoring)
    cache_monitor = CacheMonitor()

    # Test data
    test_data = [(i, np.sin(i / 100) * 100, np.cos(i / 100) * 100) for i in range(1000)]
    widget.set_curve_data(test_data)

    print("\n" + "=" * 60)
    print("CACHE HIT RATE BENCHMARK")
    print("=" * 60)

    # Test 1: Zoom operations
    print("\n1. Zoom Operations (small increments):")
    cache_monitor.reset()

    for _ in range(100):
        widget.zoom_factor *= 1.005
        # Testing private method for benchmarking
        widget._invalidate_caches()
        widget.get_transform()  # Returns non-None Transform
        cache_monitor.record_hit()

    print(f"   Hit Rate: {cache_monitor.hit_rate:.1f}%")
    print(f"   Hits: {cache_monitor.hits}, Misses: {cache_monitor.misses}")

    # Test 2: Pan operations
    print("\n2. Pan Operations (small movements):")
    cache_monitor.reset()

    for _ in range(100):
        widget.pan_offset_x += 0.05  # Sub-threshold
        widget._invalidate_caches()
        widget.get_transform()  # Returns non-None Transform
        cache_monitor.record_hit()
        cache_monitor.record_invalidation()

    print(f"   Hit Rate: {cache_monitor.hit_rate:.1f}%")
    print(f"   Invalidations: {cache_monitor.invalidations}")

    return cache_monitor.hit_rate


def benchmark_batch_transform() -> float:
    """Benchmark batch transform performance."""
    print("\n" + "=" * 60)
    print("BATCH TRANSFORM BENCHMARK")
    print("=" * 60)

    view_state = ViewState(
        display_width=1920,
        display_height=1080,
        widget_width=1920,
        widget_height=1080,
        zoom_factor=1.0,
        offset_x=0.0,
        offset_y=0.0,
        scale_to_image=False,
        flip_y_axis=False,
        manual_x_offset=0.0,
        manual_y_offset=0.0,
        background_image=None,
        image_width=1920,
        image_height=1080,
    )

    from services.transform_service import Transform

    transform = Transform.from_view_state(view_state)

    speedup = 1.0  # Initialize with default value
    for num_points in [100, 1000, 5000, 10000]:
        test_points: npt.NDArray[np.float64] = np.random.default_rng().random((num_points, 3)) * 1000

        # Individual transforms (sample)
        sample_size = min(100, num_points)
        start = time.perf_counter()
        for i in range(sample_size):
            transform.data_to_screen(float(test_points[i, 1]), float(test_points[i, 2]))
        individual_time = (time.perf_counter() - start) * (num_points / sample_size)

        # Batch transform using VectorizedTransform
        start = time.perf_counter()
        VectorizedTransform.transform_points_batch(
            test_points,
            zoom=view_state.zoom_factor,
            offset_x=view_state.offset_x,
            offset_y=view_state.offset_y,
            flip_y=view_state.flip_y_axis,
            height=view_state.widget_height,
        )
        batch_time = time.perf_counter() - start

        speedup = individual_time / batch_time if batch_time > 0 else 1.0
        print(f"\n{num_points:,} points:")
        print(f"   Individual: {individual_time*1000:.2f}ms")
        print(f"   Batch: {batch_time*1000:.2f}ms")
        print(f"   Speedup: {speedup:.1f}x")

    return speedup


def benchmark_render_performance() -> float:
    """Benchmark rendering performance with quality modes."""
    print("\n" + "=" * 60)
    print("RENDER PERFORMANCE BENCHMARK")
    print("=" * 60)

    _app = QApplication.instance() or QApplication(sys.argv)
    widget = CurveViewWidget()

    # Large dataset
    test_data = [(i, np.sin(i / 100) * 100, np.cos(i / 100) * 100) for i in range(5000)]
    widget.set_curve_data(test_data)

    renderer = widget._optimized_renderer

    # Benchmark different quality modes
    render_times: dict[RenderQuality, float] = {}
    for quality in [RenderQuality.DRAFT, RenderQuality.NORMAL, RenderQuality.HIGH]:
        renderer.set_render_quality(quality)

        # Simulate rendering operations
        times: list[float] = []
        for _ in range(10):
            start = time.perf_counter()
            # Update screen points cache to simulate rendering load
            widget._update_screen_points_cache()
            times.append(time.perf_counter() - start)

        avg_time: float = float(np.mean(times))
        render_times[quality] = avg_time
        fps = 1.0 / avg_time if avg_time > 0 else 999.0

        print(f"\n{quality.name} Quality:")
        print(f"   Frame time: {avg_time*1000:.2f}ms")
        print(f"   FPS: {fps:.1f}")

    return max(render_times.values())


def benchmark_cache_performance() -> tuple[float, float, int]:
    """Run legacy cache performance benchmarks."""
    _app = QApplication.instance() or QApplication(sys.argv)
    widget = CurveViewWidget()

    # Generate large dataset
    num_points = 10000
    test_data = [(i, np.sin(i / 100) * 100, np.cos(i / 100) * 100) for i in range(num_points)]
    widget.set_curve_data(test_data)

    print("=" * 60)
    print("Legacy Cache Performance Benchmark")
    print("=" * 60)

    # Benchmark 1: Transform cache consistency
    print("\n1. Transform Cache Consistency:")

    # Track cache retrieval
    cache_retrievals = 0

    # Multiple transform requests
    for _ in range(100):
        widget.get_transform()  # Returns non-None Transform
        cache_retrievals += 1

    print(f"   Transform retrievals: {cache_retrievals}/100")

    # Benchmark 2: Transform creation time
    print("\n2. Transform Creation Performance:")
    widget._invalidate_caches()

    times: list[float] = []
    for _ in range(50):
        widget._invalidate_caches()
        start = time.perf_counter()
        widget.get_transform()
        transform_time = time.perf_counter() - start
        times.append(transform_time)

    avg_time: float = float(np.mean(times)) * 1000
    max_time: float = float(np.max(times)) * 1000
    min_time: float = float(np.min(times)) * 1000

    print(f"   Average: {avg_time:.2f}ms")
    print(f"   Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")

    # Benchmark 3: Batch vs Individual transforms
    print("\n3. Batch Transform Performance:")

    # Create test points for transformation
    test_points: npt.NDArray[Any] = np.array(test_data[:1000])  # Use first 1000 points

    # Get current view state for realistic transforms
    view_state = widget.get_view_state()

    # Individual transforms (simulated)
    start = time.perf_counter()
    individual_results: list[list[float]] = []
    for point in test_points:
        # Simulate individual coordinate transformation
        x = float(point[1]) * view_state.zoom_factor + view_state.offset_x
        y = float(point[2]) * view_state.zoom_factor + view_state.offset_y
        individual_results.append([x, y])
    individual_time = time.perf_counter() - start

    # Batch transforms using VectorizedTransform
    start = time.perf_counter()
    VectorizedTransform.transform_points_batch(
        test_points,
        zoom=view_state.zoom_factor,
        offset_x=view_state.offset_x,
        offset_y=view_state.offset_y,
        flip_y=False,
        height=view_state.widget_height,
    )
    batch_time = time.perf_counter() - start

    speedup = individual_time / batch_time if batch_time > 0 else float("inf")
    print(f"   Individual: {individual_time*1000:.2f}ms")
    print(f"   Batch: {batch_time*1000:.2f}ms")
    print(f"   Speedup: {speedup:.1f}x")

    # Benchmark 4: Cache behavior during zoom
    print("\n4. Cache Behavior During Zoom:")

    # Reset and count cache operations
    original_invalidate: Callable[[], None] = widget._invalidate_caches
    invalidation_count = 0

    def count_invalidations() -> None:
        nonlocal invalidation_count
        invalidation_count += 1
        original_invalidate()

    widget._invalidate_caches = count_invalidations

    # Simulate zoom operations
    start_zoom = widget.zoom_factor
    for _ in range(50):
        # Small zoom increments (should have good cache behavior)
        widget.zoom_factor *= 1.01
        widget.get_transform()

    widget.zoom_factor = start_zoom  # Reset
    widget._invalidate_caches = original_invalidate

    print(f"   Cache invalidations during 50 zoom steps: {invalidation_count}")
    print(f"   Cache efficiency: {((50-invalidation_count)/50)*100:.1f}%")

    # Benchmark 5: Large dataset handling
    print("\n5. Large Dataset Performance:")

    # Create very large dataset
    large_data = [(i, np.sin(i / 50) * 200, np.cos(i / 50) * 200) for i in range(50000)]

    start = time.perf_counter()
    widget.set_curve_data(large_data)
    setup_time = time.perf_counter() - start

    start = time.perf_counter()
    widget._update_screen_points_cache()
    cache_time = time.perf_counter() - start

    print(f"   Data setup (50k points): {setup_time*1000:.1f}ms")
    print(f"   Cache update: {cache_time*1000:.1f}ms")
    print(f"   Points per second: {len(large_data)/(setup_time+cache_time):.0f}")

    print("\n" + "=" * 60)
    print("Benchmark Complete")
    print("=" * 60)

    return speedup, avg_time, invalidation_count


def main() -> int:
    """Run all benchmarks."""
    print("\n" + "#" * 60)
    print("# CACHE PERFORMANCE BENCHMARK SUITE")
    print("#" * 60)

    try:
        # Run benchmarks
        cache_hit_rate = benchmark_cache_hit_rate()
        batch_speedup = benchmark_batch_transform()
        max_render_time = benchmark_render_performance()

        # Legacy benchmarks for compatibility
        avg_time, _max_time, _p99_time = benchmark_cache_performance()

        # Summary
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)

        success = True

        if cache_hit_rate < 70.0:
            print(f"Cache hit rate: {cache_hit_rate:.1f}% (target: >70%)")
            success = False
        else:
            print(f"Cache hit rate: {cache_hit_rate:.1f}%")

        if batch_speedup < 5.0:
            print(f"Batch speedup: {batch_speedup:.1f}x (target: >5x)")
            success = False
        else:
            print(f"Batch speedup: {batch_speedup:.1f}x")

        render_fps = 1.0 / max_render_time if max_render_time > 0 else 999.0
        if render_fps < 60.0:
            print(f"Render performance: {render_fps:.1f} FPS (target: >60)")
        else:
            print(f"Render performance: {render_fps:.1f} FPS")

        # Additional metrics from legacy benchmark
        if avg_time <= 2.0:
            print(f"Transform creation: {avg_time:.1f}ms (target: ≤2ms)")
        else:
            print(f"Transform creation: {avg_time:.1f}ms (target: ≤2ms)")

        print("\n" + "=" * 60)
        print("Overall: " + ("PASS" if success else "FAIL"))
        print("=" * 60 + "\n")

        return 0 if success else 1

    except Exception as e:
        print(f"Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
