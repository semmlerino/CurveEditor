#!/usr/bin/env python3
"""Benchmark cache performance improvements."""

import os
import sys
import time

import numpy as np


def setup_environment():
    """Setup import path and working directory."""
    # Fix import path - add parent directory and change to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    os.chdir(project_root)


# Setup environment before imports
setup_environment()

from PySide6.QtWidgets import QApplication  # noqa: E402

from rendering.optimized_curve_renderer import RenderQuality, VectorizedTransform  # noqa: E402
from services.transform_service import ViewState  # noqa: E402
from ui.curve_view_widget import CacheMonitor, CurveViewWidget  # noqa: E402


def benchmark_cache_hit_rate():
    """Benchmark cache hit rate improvements with monitoring."""
    QApplication.instance() or QApplication(sys.argv)
    widget = CurveViewWidget()

    # Enable monitoring
    widget._enable_monitoring = True
    widget._cache_monitor = CacheMonitor()

    # Test data
    test_data = [(i, np.sin(i / 100) * 100, np.cos(i / 100) * 100) for i in range(1000)]
    widget.set_curve_data(test_data)

    print("\n" + "=" * 60)
    print("CACHE HIT RATE BENCHMARK")
    print("=" * 60)

    # Test 1: Zoom operations
    print("\n1. Zoom Operations (small increments):")
    widget._cache_monitor = CacheMonitor()  # Reset

    for i in range(100):
        widget.zoom_factor *= 1.005
        widget._invalidate_caches()
        widget.get_transform()

    print(f"   Hit Rate: {widget._cache_monitor.hit_rate:.1f}%")
    print(f"   Hits: {widget._cache_monitor.hits}, Misses: {widget._cache_monitor.misses}")

    # Test 2: Pan operations
    print("\n2. Pan Operations (small movements):")
    widget._cache_monitor = CacheMonitor()  # Reset

    for i in range(100):
        widget.pan_offset_x += 0.05  # Sub-threshold
        widget._invalidate_caches()
        widget.get_transform()

    print(f"   Hit Rate: {widget._cache_monitor.hit_rate:.1f}%")
    print(f"   Invalidations: {widget._cache_monitor.invalidations}")

    return widget._cache_monitor.hit_rate


def benchmark_batch_transform():
    """Benchmark batch transform performance."""
    print("\n" + "=" * 60)
    print("BATCH TRANSFORM BENCHMARK")
    print("=" * 60)

    view_state = ViewState(
        display_width=1920.0,
        display_height=1080.0,
        widget_width=1920,
        widget_height=1080,
        zoom_factor=1.0,
        fit_scale=1.0,
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

    for num_points in [100, 1000, 5000, 10000]:
        test_points = np.random.default_rng().random((num_points, 3)) * 1000  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

        # Individual transforms (sample)
        sample_size = min(100, num_points)
        start = time.perf_counter()
        for i in range(sample_size):
            transform.data_to_screen(test_points[i, 1], test_points[i, 2])
        individual_time = (time.perf_counter() - start) * (num_points / sample_size)

        # Batch transform
        start = time.perf_counter()
        transform.batch_data_to_screen(test_points)
        batch_time = time.perf_counter() - start

        speedup = individual_time / batch_time
        print(f"\n{num_points:,} points:")
        print(f"   Individual: {individual_time*1000:.2f}ms")
        print(f"   Batch: {batch_time*1000:.2f}ms")
        print(f"   Speedup: {speedup:.1f}x")

    return speedup


def benchmark_render_performance():
    """Benchmark rendering performance with quality modes."""
    print("\n" + "=" * 60)
    print("RENDER PERFORMANCE BENCHMARK")
    print("=" * 60)

    QApplication.instance() or QApplication(sys.argv)
    widget = CurveViewWidget()

    # Large dataset
    test_data = [(i, np.sin(i / 100) * 100, np.cos(i / 100) * 100) for i in range(5000)]
    widget.set_curve_data(test_data)

    renderer = widget._optimized_renderer

    # Benchmark different quality modes
    render_times = {}
    for quality in [RenderQuality.DRAFT, RenderQuality.NORMAL, RenderQuality.HIGH]:
        renderer.set_render_quality(quality)

        # Simulate rendering operations
        times = []
        for _ in range(10):
            start = time.perf_counter()
            # Update screen points cache to simulate rendering load
            widget._update_screen_points_cache()
            times.append(time.perf_counter() - start)

        avg_time = np.mean(times)
        render_times[quality] = avg_time
        fps = 1.0 / avg_time if avg_time > 0 else 999

        print(f"\n{quality.name} Quality:")
        print(f"   Frame time: {avg_time*1000:.2f}ms")
        print(f"   FPS: {fps:.1f}")

    return max(render_times.values())


def benchmark_cache_performance():
    """Run legacy cache performance benchmarks."""
    QApplication.instance() or QApplication(sys.argv)
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
    for i in range(100):
        transform = widget.get_transform()
        if transform is not None:
            cache_retrievals += 1

    print(f"   Transform retrievals: {cache_retrievals}/100")

    # Benchmark 2: Transform creation time
    print("\n2. Transform Creation Performance:")
    widget._invalidate_caches()

    times = []
    for _ in range(50):
        widget._invalidate_caches()
        start = time.perf_counter()
        widget.get_transform()
        transform_time = time.perf_counter() - start
        times.append(transform_time)

    avg_time = np.mean(times) * 1000
    max_time = np.max(times) * 1000
    min_time = np.min(times) * 1000

    print(f"   Average: {avg_time:.2f}ms")
    print(f"   Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")

    # Benchmark 3: Batch vs Individual transforms
    print("\n3. Batch Transform Performance:")

    # Create test points for transformation
    test_points = np.array(test_data[:1000])  # Use first 1000 points

    # Get current view state for realistic transforms
    view_state = widget.get_view_state()

    # Individual transforms (simulated)
    start = time.perf_counter()
    individual_results = []
    for point in test_points:
        # Simulate individual coordinate transformation
        x = point[1] * view_state.zoom_factor + view_state.offset_x
        y = point[2] * view_state.zoom_factor + view_state.offset_y
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
    original_invalidate = widget._invalidate_caches
    invalidation_count = 0

    def count_invalidations():
        nonlocal invalidation_count
        invalidation_count += 1
        original_invalidate()

    widget._invalidate_caches = count_invalidations

    # Simulate zoom operations
    start_zoom = widget.zoom_factor
    for i in range(50):
        # Small zoom increments (should have good cache behavior)
        widget.zoom_factor *= 1.01
        widget.get_transform()

    widget.zoom_factor = start_zoom  # Reset
    widget._invalidate_caches = original_invalidate  # Restore

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


def main():
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
        speedup_legacy, avg_time, invalidations = benchmark_cache_performance()

        # Summary
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)

        success = True

        if cache_hit_rate < 70:
            print(f"❌ Cache hit rate: {cache_hit_rate:.1f}% (target: >70%)")
            success = False
        else:
            print(f"✅ Cache hit rate: {cache_hit_rate:.1f}%")

        if batch_speedup < 5:
            print(f"❌ Batch speedup: {batch_speedup:.1f}x (target: >5x)")
            success = False
        else:
            print(f"✅ Batch speedup: {batch_speedup:.1f}x")

        render_fps = 1.0 / max_render_time if max_render_time > 0 else 999
        if render_fps < 60:
            print(f"⚠️  Render performance: {render_fps:.1f} FPS (target: >60)")
        else:
            print(f"✅ Render performance: {render_fps:.1f} FPS")

        # Additional metrics from legacy benchmark
        if avg_time <= 2.0:
            print(f"✅ Transform creation: {avg_time:.1f}ms (target: ≤2ms)")
        else:
            print(f"⚠️  Transform creation: {avg_time:.1f}ms (target: ≤2ms)")

        print("\n" + "=" * 60)
        print("Overall: " + ("✅ PASS" if success else "❌ FAIL"))
        print("=" * 60 + "\n")

        return 0 if success else 1

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
