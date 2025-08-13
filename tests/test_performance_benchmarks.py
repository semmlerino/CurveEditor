#!/usr/bin/env python3
"""
Performance benchmarks for the CurveEditor application.

These tests measure performance characteristics and ensure the application
scales well with different data sizes and usage patterns.

Benchmark categories:
1. Application startup time
2. Data loading and processing
3. UI rendering performance
4. Memory usage patterns
5. Service operation efficiency
"""

import gc
import os
import tempfile
import time
import tracemalloc
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow


class BenchmarkResult:
    """Container for benchmark results."""

    def __init__(self, operation: str):
        self.operation = operation
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0
        self.memory_start = 0
        self.memory_end = 0
        self.memory_peak = 0
        self.data_size = 0

    @property
    def throughput(self) -> float:
        """Calculate throughput (items per second)."""
        if self.duration > 0 and self.data_size > 0:
            return self.data_size / self.duration
        return 0.0

    def __str__(self) -> str:
        return (
            f"{self.operation}: {self.duration:.3f}s, "
            f"Memory: {self.memory_peak / 1024 / 1024:.1f}MB peak, "
            f"Throughput: {self.throughput:.0f} items/sec"
        )


@pytest.fixture
def benchmark_context() -> Generator[dict[str, Any], None, None]:
    """Provide benchmarking context with memory tracking."""
    # Start memory tracking
    tracemalloc.start()

    context = {"results": [], "baseline_memory": tracemalloc.get_traced_memory()[0]}

    yield context

    # Stop memory tracking
    tracemalloc.stop()


def create_benchmark_data(size: int) -> list[tuple[int, float, float, str]]:
    """Create synthetic benchmark data."""
    return [
        (i, float(i * 10 + i % 10), float(i * 15 + (i * 7) % 20), "keyframe" if i % 5 == 0 else "interpolated")
        for i in range(1, size + 1)
    ]


class TestApplicationStartupBenchmarks:
    """Benchmark application startup performance."""

    def test_main_window_creation_time(self, qapp: QApplication, benchmark_context: dict[str, Any]) -> None:
        """Benchmark MainWindow creation time."""
        result = BenchmarkResult("MainWindow Creation")

        # Start timing
        result.start_time = time.perf_counter()
        result.memory_start = tracemalloc.get_traced_memory()[0]

        # Create MainWindow
        window = MainWindow()
        window.show()
        qapp.processEvents()

        # End timing
        result.end_time = time.perf_counter()
        result.duration = result.end_time - result.start_time
        result.memory_end, result.memory_peak = tracemalloc.get_traced_memory()

        # Cleanup
        window.close()

        # Assert reasonable startup time (should be < 2 seconds)
        assert result.duration < 2.0, f"MainWindow startup too slow: {result.duration:.3f}s"

        # Assert reasonable memory usage (should be < 50MB for basic startup)
        memory_mb = result.memory_peak / 1024 / 1024
        assert memory_mb < 50.0, f"MainWindow uses too much memory: {memory_mb:.1f}MB"

        benchmark_context["results"].append(result)
        print(f"\n{result}")

    def test_curve_widget_creation_time(self, qapp: QApplication, benchmark_context: dict[str, Any]) -> None:
        """Benchmark CurveViewWidget creation time."""
        result = BenchmarkResult("CurveViewWidget Creation")

        # Start timing
        result.start_time = time.perf_counter()
        result.memory_start = tracemalloc.get_traced_memory()[0]

        # Create CurveViewWidget
        CurveViewWidget()

        # End timing
        result.end_time = time.perf_counter()
        result.duration = result.end_time - result.start_time
        result.memory_end, result.memory_peak = tracemalloc.get_traced_memory()

        # Assert reasonable creation time
        assert result.duration < 0.1, f"CurveViewWidget creation too slow: {result.duration:.3f}s"

        benchmark_context["results"].append(result)
        print(f"\n{result}")


class TestDataProcessingBenchmarks:
    """Benchmark data loading and processing performance."""

    @pytest.fixture
    def main_window(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create MainWindow for benchmarking."""
        window = MainWindow()
        window.show()
        qapp.processEvents()
        yield window
        window.close()

    @pytest.mark.parametrize("data_size", [100, 1000, 5000, 10000])
    def test_data_loading_performance(
        self, main_window: MainWindow, data_size: int, benchmark_context: dict[str, Any]
    ) -> None:
        """Benchmark data loading performance with various sizes."""
        result = BenchmarkResult(f"Data Loading ({data_size} points)")
        result.data_size = data_size

        # Create test data
        test_data = create_benchmark_data(data_size)

        # Start timing
        result.start_time = time.perf_counter()
        result.memory_start = tracemalloc.get_traced_memory()[0]

        # Load data
        main_window.curve_widget.set_curve_data(test_data)

        # End timing
        result.end_time = time.perf_counter()
        result.duration = result.end_time - result.start_time
        result.memory_end, result.memory_peak = tracemalloc.get_traced_memory()

        # Performance assertions
        expected_time = data_size * 0.0001  # 0.1ms per point
        assert result.duration < expected_time, f"Data loading too slow: {result.duration:.3f}s for {data_size} points"

        # Verify data was loaded correctly
        assert len(main_window.curve_widget.curve_data) == data_size

        benchmark_context["results"].append(result)
        print(f"\n{result}")

    @pytest.mark.parametrize("update_count", [10, 100, 500])
    def test_point_update_performance(
        self, main_window: MainWindow, update_count: int, benchmark_context: dict[str, Any]
    ) -> None:
        """Benchmark point update performance."""
        # Set up initial data
        initial_data = create_benchmark_data(1000)
        main_window.curve_widget.set_curve_data(initial_data)

        result = BenchmarkResult(f"Point Updates ({update_count} updates)")
        result.data_size = update_count

        # Start timing
        result.start_time = time.perf_counter()
        result.memory_start = tracemalloc.get_traced_memory()[0]

        # Perform updates
        for i in range(update_count):
            idx = i % len(initial_data)
            main_window.curve_widget.update_point(idx, float(i * 2), float(i * 3))

        # End timing
        result.end_time = time.perf_counter()
        result.duration = result.end_time - result.start_time
        result.memory_end, result.memory_peak = tracemalloc.get_traced_memory()

        # Performance assertion - should handle at least 1000 updates per second
        assert result.throughput > 1000, f"Point updates too slow: {result.throughput:.0f} updates/sec"

        benchmark_context["results"].append(result)
        print(f"\n{result}")

    def test_file_io_performance(self, main_window: MainWindow, benchmark_context: dict[str, Any]) -> None:
        """Benchmark file I/O operations."""
        data_size = 5000
        test_data = create_benchmark_data(data_size)

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for point in test_data:
                f.write(f"{point[0]} {point[1]} {point[2]}\n")
            temp_file = f.name

        try:
            result = BenchmarkResult(f"File Loading ({data_size} points)")
            result.data_size = data_size

            # Mock file service to return our data
            with patch.object(main_window.services, "load_track_data") as mock_load:
                mock_load.return_value = test_data

                # Start timing
                result.start_time = time.perf_counter()
                result.memory_start = tracemalloc.get_traced_memory()[0]

                # Load file
                loaded_data = main_window.services.load_track_data(main_window)
                main_window.curve_widget.set_curve_data(loaded_data)

                # End timing
                result.end_time = time.perf_counter()
                result.duration = result.end_time - result.start_time
                result.memory_end, result.memory_peak = tracemalloc.get_traced_memory()

            # Performance assertion - should load at least 10,000 points per second
            assert result.throughput > 10000, f"File loading too slow: {result.throughput:.0f} points/sec"

            benchmark_context["results"].append(result)
            print(f"\n{result}")

        finally:
            os.unlink(temp_file)


class TestUIRenderingBenchmarks:
    """Benchmark UI rendering and interaction performance."""

    @pytest.fixture
    def main_window_with_data(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create MainWindow with test data."""
        window = MainWindow()
        window.show()
        qapp.processEvents()

        # Load moderate amount of test data
        test_data = create_benchmark_data(1000)
        window.curve_widget.set_curve_data(test_data)

        yield window
        window.close()

    def test_zoom_operation_performance(
        self, main_window_with_data: MainWindow, benchmark_context: dict[str, Any]
    ) -> None:
        """Benchmark zoom operations."""
        result = BenchmarkResult("Zoom Operations (50 zoom steps)")
        result.data_size = 50

        # Start timing
        result.start_time = time.perf_counter()
        result.memory_start = tracemalloc.get_traced_memory()[0]

        # Perform zoom operations
        for i in range(25):
            main_window_with_data._on_action_zoom_in()
            QApplication.processEvents()

        for i in range(25):
            main_window_with_data._on_action_zoom_out()
            QApplication.processEvents()

        # End timing
        result.end_time = time.perf_counter()
        result.duration = result.end_time - result.start_time
        result.memory_end, result.memory_peak = tracemalloc.get_traced_memory()

        # Performance assertion - should handle at least 100 zoom ops per second
        assert result.throughput > 100, f"Zoom operations too slow: {result.throughput:.0f} ops/sec"

        benchmark_context["results"].append(result)
        print(f"\n{result}")

    def test_selection_performance(self, main_window_with_data: MainWindow, benchmark_context: dict[str, Any]) -> None:
        """Benchmark point selection performance."""
        curve_widget = main_window_with_data.curve_widget
        data_size = len(curve_widget.curve_data)

        result = BenchmarkResult(f"Point Selection ({data_size} selections)")
        result.data_size = data_size

        # Start timing
        result.start_time = time.perf_counter()
        result.memory_start = tracemalloc.get_traced_memory()[0]

        # Select each point
        for i in range(data_size):
            curve_widget.selected_indices.clear()
            curve_widget.selected_indices.add(i)
            curve_widget.selection_changed.emit([i])
            QApplication.processEvents()

        # End timing
        result.end_time = time.perf_counter()
        result.duration = result.end_time - result.start_time
        result.memory_end, result.memory_peak = tracemalloc.get_traced_memory()

        # Performance assertion - should handle at least 1000 selections per second
        assert result.throughput > 1000, f"Point selection too slow: {result.throughput:.0f} selections/sec"

        benchmark_context["results"].append(result)
        print(f"\n{result}")

    def test_ui_update_performance(self, main_window_with_data: MainWindow, benchmark_context: dict[str, Any]) -> None:
        """Benchmark UI state updates."""
        update_count = 100

        result = BenchmarkResult(f"UI Updates ({update_count} updates)")
        result.data_size = update_count

        # Start timing
        result.start_time = time.perf_counter()
        result.memory_start = tracemalloc.get_traced_memory()[0]

        # Perform UI updates
        for i in range(update_count):
            main_window_with_data._update_ui_state()
            QApplication.processEvents()

        # End timing
        result.end_time = time.perf_counter()
        result.duration = result.end_time - result.start_time
        result.memory_end, result.memory_peak = tracemalloc.get_traced_memory()

        # Performance assertion - should handle at least 500 UI updates per second
        assert result.throughput > 500, f"UI updates too slow: {result.throughput:.0f} updates/sec"

        benchmark_context["results"].append(result)
        print(f"\n{result}")


class TestMemoryUsageBenchmarks:
    """Benchmark memory usage patterns."""

    @pytest.fixture
    def main_window(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create MainWindow for memory testing."""
        window = MainWindow()
        window.show()
        qapp.processEvents()
        yield window
        window.close()

    def test_memory_scaling_with_data_size(self, main_window: MainWindow, benchmark_context: dict[str, Any]) -> None:
        """Test memory usage scaling with data size."""
        data_sizes = [100, 1000, 5000, 10000]
        memory_usage = []

        for size in data_sizes:
            # Force garbage collection
            gc.collect()

            # Get baseline memory
            baseline = tracemalloc.get_traced_memory()[0]

            # Load data
            test_data = create_benchmark_data(size)
            main_window.curve_widget.set_curve_data(test_data)

            # Measure memory after loading
            current, peak = tracemalloc.get_traced_memory()
            memory_used = (current - baseline) / 1024 / 1024  # MB

            memory_usage.append((size, memory_used))

            # Clean up
            main_window.curve_widget.set_curve_data([])
            gc.collect()

        # Check memory scaling - should be roughly linear
        for i in range(1, len(memory_usage)):
            prev_size, prev_memory = memory_usage[i - 1]
            curr_size, curr_memory = memory_usage[i]

            size_ratio = curr_size / prev_size
            memory_ratio = curr_memory / prev_memory if prev_memory > 0 else 0

            # Memory growth should not be more than 2x the data growth
            assert memory_ratio <= size_ratio * 2, (
                f"Memory scaling too high: {memory_ratio:.2f}x for {size_ratio:.2f}x data"
            )

        result = BenchmarkResult("Memory Scaling Test")
        result.duration = 0.0  # Not time-based
        benchmark_context["results"].append(result)

        print("\nMemory usage scaling:")
        for size, memory in memory_usage:
            print(f"  {size:,} points: {memory:.1f}MB")

    def test_memory_cleanup_after_operations(self, main_window: MainWindow, benchmark_context: dict[str, Any]) -> None:
        """Test memory cleanup after various operations."""
        # Get baseline memory
        gc.collect()
        baseline = tracemalloc.get_traced_memory()[0]

        # Perform memory-intensive operations
        large_data = create_benchmark_data(10000)

        # Load and manipulate data multiple times
        for _ in range(5):
            main_window.curve_widget.set_curve_data(large_data)

            # Perform various operations
            for i in range(0, len(large_data), 100):
                main_window.curve_widget.selected_indices.add(i)

            main_window.curve_widget.selected_indices.clear()
            main_window.curve_widget.set_curve_data([])
            gc.collect()

        # Check final memory usage
        final_memory = tracemalloc.get_traced_memory()[0]
        memory_growth = (final_memory - baseline) / 1024 / 1024  # MB

        # Memory growth should be minimal after cleanup
        assert memory_growth < 10.0, f"Memory leak detected: {memory_growth:.1f}MB growth after operations"

        result = BenchmarkResult("Memory Cleanup Test")
        result.memory_peak = int(memory_growth * 1024 * 1024)
        benchmark_context["results"].append(result)
        print(f"\nMemory growth after operations: {memory_growth:.1f}MB")


class TestServicePerformanceBenchmarks:
    """Benchmark service operation efficiency."""

    @pytest.fixture
    def main_window(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create MainWindow for service testing."""
        window = MainWindow()
        window.show()
        qapp.processEvents()
        yield window
        window.close()

    def test_service_facade_performance(self, main_window: MainWindow, benchmark_context: dict[str, Any]) -> None:
        """Benchmark service facade delegation performance."""
        operation_count = 1000

        result = BenchmarkResult(f"Service Facade ({operation_count} operations)")
        result.data_size = operation_count

        # Mock the underlying services
        with patch.object(main_window.services, "add_to_history"):
            # Start timing
            result.start_time = time.perf_counter()
            result.memory_start = tracemalloc.get_traced_memory()[0]

            # Perform service operations
            for _ in range(operation_count):
                main_window.services.add_to_history()

            # End timing
            result.end_time = time.perf_counter()
            result.duration = result.end_time - result.start_time
            result.memory_end, result.memory_peak = tracemalloc.get_traced_memory()

        # Performance assertion - should handle at least 10,000 operations per second
        assert result.throughput > 10000, f"Service facade too slow: {result.throughput:.0f} ops/sec"

        benchmark_context["results"].append(result)
        print(f"\n{result}")

    def test_state_synchronization_performance(
        self, main_window: MainWindow, benchmark_context: dict[str, Any]
    ) -> None:
        """Benchmark state synchronization between components."""
        sync_count = 500

        result = BenchmarkResult(f"State Synchronization ({sync_count} syncs)")
        result.data_size = sync_count

        # Set up test data
        test_data = create_benchmark_data(100)
        main_window.curve_widget.set_curve_data(test_data)

        # Start timing
        result.start_time = time.perf_counter()
        result.memory_start = tracemalloc.get_traced_memory()[0]

        # Perform state synchronization operations
        for i in range(sync_count):
            # Update selection
            idx = i % len(test_data)
            main_window.curve_widget.selected_indices.clear()
            main_window.curve_widget.selected_indices.add(idx)
            main_window.curve_widget.selection_changed.emit([idx])

            # Update UI state
            main_window._update_ui_state()
            QApplication.processEvents()

        # End timing
        result.end_time = time.perf_counter()
        result.duration = result.end_time - result.start_time
        result.memory_end, result.memory_peak = tracemalloc.get_traced_memory()

        # Performance assertion - should handle at least 1000 syncs per second
        assert result.throughput > 1000, f"State synchronization too slow: {result.throughput:.0f} syncs/sec"

        benchmark_context["results"].append(result)
        print(f"\n{result}")


def test_benchmark_summary(benchmark_context: dict[str, Any]) -> None:
    """Print benchmark summary."""
    results = benchmark_context.get("results", [])

    if not results:
        pytest.skip("No benchmark results available")

    print("\n" + "=" * 80)
    print("PERFORMANCE BENCHMARK SUMMARY")
    print("=" * 80)

    for result in results:
        print(result)

    print("=" * 80)

    # Check for any concerning results
    slow_operations = [r for r in results if r.duration > 1.0 and r.data_size > 0]
    if slow_operations:
        print(f"\nWARNING: {len(slow_operations)} operations took longer than 1 second:")
        for op in slow_operations:
            print(f"  - {op.operation}: {op.duration:.3f}s")

    # Check memory usage
    high_memory = [r for r in results if r.memory_peak > 100 * 1024 * 1024]  # 100MB
    if high_memory:
        print(f"\nWARNING: {len(high_memory)} operations used more than 100MB:")
        for op in high_memory:
            print(f"  - {op.operation}: {op.memory_peak / 1024 / 1024:.1f}MB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
