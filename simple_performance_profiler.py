#!/usr/bin/env python3
"""
Simple performance profiler for CurveEditor - focuses on core operations without GUI.
"""

import tempfile
import time
import tracemalloc
from pathlib import Path

import psutil


def profile_transforms():
    """Profile coordinate transformation performance."""
    print("Profiling transform operations...")

    from services import get_transform_service
    from services.transform_service import ViewState

    transform_service = get_transform_service()

    # Test with different sizes
    test_sizes = [100, 1000, 10000]
    results = {}

    for num_points in test_sizes:
        # Create test data
        test_points = [(i, float(i * 10), float(i * 20)) for i in range(num_points)]

        # Create view state
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=1920,
            widget_height=1080,
            zoom_factor=2.0,
            offset_x=100,
            offset_y=50,
        )

        # Profile transform creation
        create_start = time.perf_counter()
        transform = transform_service.create_transform(view_state)
        create_time = time.perf_counter() - create_start

        # Profile data to screen transformations
        to_screen_start = time.perf_counter()
        for _, x, y in test_points:
            transform.data_to_screen(x, y)
        to_screen_time = time.perf_counter() - to_screen_start

        results[num_points] = {
            "transform_creation_ms": create_time * 1000,
            "total_transform_ms": to_screen_time * 1000,
            "per_point_ms": (to_screen_time / num_points) * 1000,
            "points_per_second": num_points / to_screen_time if to_screen_time > 0 else float("inf"),
        }

    return results


def profile_file_io():
    """Profile file I/O operations."""
    print("Profiling file I/O operations...")

    from services import get_data_service

    data_service = get_data_service()

    # Test different sizes
    test_sizes = [100, 1000, 10000]
    results = {}

    for size in test_sizes:
        # Create test data
        test_data = [
            (i, float(i * 10), float(i * 20), "keyframe" if i % 10 == 0 else "interpolated") for i in range(size)
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            # Profile save
            save_start = time.perf_counter()
            data_service._save_json(temp_path, test_data, "Test", "#FF0000")
            save_time = time.perf_counter() - save_start

            # Get file size
            file_size = Path(temp_path).stat().st_size / 1024  # KB

            # Profile load
            load_start = time.perf_counter()
            loaded_data = data_service._load_json(temp_path)
            load_time = time.perf_counter() - load_start

            results[size] = {
                "save_time_ms": save_time * 1000,
                "load_time_ms": load_time * 1000,
                "file_size_kb": file_size,
                "verified": len(loaded_data) == size,
                "throughput_save_mbps": (file_size / 1024) / save_time if save_time > 0 else 0,
                "throughput_load_mbps": (file_size / 1024) / load_time if load_time > 0 else 0,
            }

        finally:
            Path(temp_path).unlink(missing_ok=True)

    return results


def profile_service_operations():
    """Profile service operations."""
    print("Profiling service operations...")

    from services import get_data_service, get_interaction_service, get_transform_service
    from tests.test_utilities import TestCurveView, TestMainWindow

    # Initialize services
    data_service = get_data_service()
    interaction_service = get_interaction_service()
    get_transform_service()

    # Create test views
    view = TestCurveView()
    window = TestMainWindow()

    # Test data
    test_data = [(i, float(i * 10), float(i * 20), "keyframe") for i in range(1000)]
    view.curve_data = test_data
    view.points = test_data

    results = {}

    # Profile point selection
    select_start = time.perf_counter()
    for i in range(100):
        interaction_service.select_point_by_index(view, window, i)
    select_time = time.perf_counter() - select_start

    results["point_selection"] = {
        "total_ms": select_time * 1000,
        "per_selection_ms": (select_time / 100) * 1000,
    }

    # Profile point finding
    find_start = time.perf_counter()
    for i in range(100):
        x = float(i * 10)
        y = float(i * 20)
        interaction_service.find_point_at(view, x, y)
    find_time = time.perf_counter() - find_start

    results["point_finding"] = {
        "total_ms": find_time * 1000,
        "per_find_ms": (find_time / 100) * 1000,
    }

    # Profile data filtering
    filter_start = time.perf_counter()
    data_service.smooth_moving_average(test_data, window_size=5)
    filter_time = time.perf_counter() - filter_start

    results["data_filtering"] = {
        "smooth_1000_points_ms": filter_time * 1000,
        "points_per_second": 1000 / filter_time if filter_time > 0 else float("inf"),
    }

    return results


def profile_memory():
    """Profile memory usage."""
    print("Profiling memory usage...")

    process = psutil.Process()

    # Start memory tracking
    tracemalloc.start()

    # Baseline memory
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Import and initialize services
    from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service

    get_data_service()
    get_interaction_service()
    get_transform_service()
    get_ui_service()

    services_memory = process.memory_info().rss / 1024 / 1024

    # Create large dataset
    [(i, float(i * 10), float(i * 20), "keyframe") for i in range(10000)]

    large_data_memory = process.memory_info().rss / 1024 / 1024

    # Get memory snapshot
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics("lineno")

    # Get top memory users
    top_memory = []
    for stat in top_stats[:10]:
        top_memory.append(
            {
                "location": str(stat.traceback),
                "size_mb": stat.size / 1024 / 1024,
            }
        )

    tracemalloc.stop()

    return {
        "baseline_mb": baseline_memory,
        "after_services_mb": services_memory,
        "after_large_data_mb": large_data_memory,
        "services_overhead_mb": services_memory - baseline_memory,
        "large_data_overhead_mb": large_data_memory - services_memory,
        "top_allocations": top_memory[:5],
    }


def generate_report():
    """Generate performance report."""
    print("\n" + "=" * 60)
    print("CURVEEDITOR PERFORMANCE BASELINE REPORT")
    print("=" * 60 + "\n")

    # Run all profiles
    transforms = profile_transforms()
    file_io = profile_file_io()
    services = profile_service_operations()
    memory = profile_memory()

    # Transform Performance
    print("## TRANSFORM PERFORMANCE")
    print("-" * 40)
    for size, metrics in transforms.items():
        print(f"\n{size} Points:")
        print(f"  Transform Creation: {metrics['transform_creation_ms']:.3f}ms")
        print(f"  Total Transform Time: {metrics['total_transform_ms']:.2f}ms")
        print(f"  Per Point: {metrics['per_point_ms']:.4f}ms")
        print(f"  Throughput: {metrics['points_per_second']:.0f} points/sec")

    # Assessment
    if transforms[1000]["total_transform_ms"] < 10:
        print("\n✅ Transform performance is EXCELLENT (<10ms for 1000 points)")
    elif transforms[1000]["total_transform_ms"] < 20:
        print("\n⚠️ Transform performance is ACCEPTABLE (10-20ms)")
    else:
        print("\n❌ Transform performance NEEDS OPTIMIZATION (>20ms)")

    # File I/O Performance
    print("\n## FILE I/O PERFORMANCE")
    print("-" * 40)
    for size, metrics in file_io.items():
        print(f"\n{size} Points:")
        print(f"  Save Time: {metrics['save_time_ms']:.2f}ms")
        print(f"  Load Time: {metrics['load_time_ms']:.2f}ms")
        print(f"  File Size: {metrics['file_size_kb']:.1f}KB")
        print(f"  Save Throughput: {metrics['throughput_save_mbps']:.2f}MB/s")
        print(f"  Load Throughput: {metrics['throughput_load_mbps']:.2f}MB/s")

    # Assessment
    if file_io[10000]["load_time_ms"] < 1000:
        print("\n✅ File I/O is EXCELLENT (<1s for 10k points)")
    elif file_io[10000]["load_time_ms"] < 2000:
        print("\n⚠️ File I/O is ACCEPTABLE (1-2s)")
    else:
        print("\n❌ File I/O NEEDS OPTIMIZATION (>2s)")

    # Service Operations
    print("\n## SERVICE OPERATIONS")
    print("-" * 40)
    print("\nPoint Selection (100 operations):")
    print(f"  Total: {services['point_selection']['total_ms']:.2f}ms")
    print(f"  Per Selection: {services['point_selection']['per_selection_ms']:.3f}ms")

    print("\nPoint Finding (100 operations):")
    print(f"  Total: {services['point_finding']['total_ms']:.2f}ms")
    print(f"  Per Find: {services['point_finding']['per_find_ms']:.3f}ms")

    print("\nData Filtering (1000 points):")
    print(f"  Smoothing Time: {services['data_filtering']['smooth_1000_points_ms']:.2f}ms")
    print(f"  Throughput: {services['data_filtering']['points_per_second']:.0f} points/sec")

    # Memory Usage
    print("\n## MEMORY USAGE")
    print("-" * 40)
    print(f"Baseline: {memory['baseline_mb']:.1f}MB")
    print(f"After Services: {memory['after_services_mb']:.1f}MB (+{memory['services_overhead_mb']:.1f}MB)")
    print(f"After 10k Points: {memory['after_large_data_mb']:.1f}MB (+{memory['large_data_overhead_mb']:.1f}MB)")

    # Assessment
    if memory["after_large_data_mb"] < 100:
        print("\n✅ Memory usage is EXCELLENT (<100MB)")
    elif memory["after_large_data_mb"] < 200:
        print("\n⚠️ Memory usage is ACCEPTABLE (100-200MB)")
    else:
        print("\n❌ Memory usage NEEDS OPTIMIZATION (>200MB)")

    # Bottleneck Analysis
    print("\n## BOTTLENECK ANALYSIS")
    print("-" * 40)

    bottlenecks = []

    if transforms[10000]["total_transform_ms"] > 100:
        bottlenecks.append(
            f"Transform operations slow for large datasets ({transforms[10000]['total_transform_ms']:.0f}ms for 10k points)"
        )

    if file_io[10000]["load_time_ms"] > 2000:
        bottlenecks.append(f"File loading slow ({file_io[10000]['load_time_ms']:.0f}ms for 10k points)")

    if services["point_finding"]["per_find_ms"] > 1:
        bottlenecks.append(
            f"Point finding inefficient ({services['point_finding']['per_find_ms']:.2f}ms per operation)"
        )

    if memory["after_large_data_mb"] > 200:
        bottlenecks.append(f"High memory usage ({memory['after_large_data_mb']:.0f}MB)")

    if bottlenecks:
        print("Priority optimization targets:")
        for i, bottleneck in enumerate(bottlenecks, 1):
            print(f"  {i}. {bottleneck}")
    else:
        print("✅ No major bottlenecks detected!")

    # Optimization Recommendations
    print("\n## OPTIMIZATION RECOMMENDATIONS")
    print("-" * 40)

    recommendations = []

    if transforms[1000]["per_point_ms"] > 0.01:
        recommendations.append("- Implement transform result caching")
        recommendations.append("- Consider numpy vectorization for batch transforms")

    if file_io[10000]["load_time_ms"] > 1000:
        recommendations.append("- Implement lazy loading for large files")
        recommendations.append("- Consider binary format (e.g., HDF5) for large datasets")

    if services["point_finding"]["per_find_ms"] > 0.5:
        recommendations.append("- Implement spatial indexing (e.g., R-tree) for point queries")

    if memory["large_data_overhead_mb"] > 50:
        recommendations.append("- Optimize data structures (use numpy arrays)")
        recommendations.append("- Implement data compression for memory efficiency")

    if recommendations:
        for rec in recommendations:
            print(rec)
    else:
        print("Performance is already well optimized!")

    print("\n" + "=" * 60)
    print("END OF PERFORMANCE BASELINE REPORT")
    print("=" * 60)


def main():
    """Run performance profiling."""
    try:
        generate_report()

        # Save results
        with open("PERFORMANCE_BASELINE_REPORT.txt", "w") as f:
            # Redirect print to file
            import sys

            old_stdout = sys.stdout
            sys.stdout = f
            generate_report()
            sys.stdout = old_stdout

        print("\nReport saved to: PERFORMANCE_BASELINE_REPORT.txt")

    except Exception as e:
        print(f"\nError during profiling: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
