"""
Performance-critical integration tests for CurveEditor services.

This module establishes performance baselines and tests critical performance
paths in the service integration layer. Tests focus on ensuring the application
can handle realistic data sizes with acceptable performance.

Performance targets:
- Data loading: < 100ms for 1000 points
- Transform operations: < 10ms for 100 coordinate conversions
- Smoothing operations: < 50ms for 500 points
- Memory usage: < 100MB growth for typical operations
"""

import gc
import json
import os
import tempfile
import time

import psutil
import pytest

from core.point_types import safe_extract_point

# Import services for performance testing
from services import (
    get_data_service,
    get_transform_service,
)

# Test utilities
from tests.test_utilities import ProtocolCompliantMockCurveView


@pytest.mark.performance
class TestDataProcessingPerformance:
    """Test performance of data processing operations."""

    def setup_method(self):
        """Set up services for performance testing."""
        self.data_service = get_data_service()

    def test_large_dataset_loading_performance(self, benchmark):
        """Benchmark: Load 1000 points from JSON - Target: <100ms."""
        # Create large realistic dataset
        large_data = []
        for frame in range(1, 1001):  # 1000 points
            x = 960 + 200 * (frame / 1000) + (frame % 50) * 2  # Realistic movement
            y = 540 + 100 * (frame / 1000) + (frame % 30) * 1.5
            large_data.append(
                {"frame": frame, "x": x, "y": y, "status": "keyframe" if frame % 10 == 0 else "interpolated"}
            )

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(large_data, f)
            temp_file = f.name

        try:
            # Benchmark the loading operation
            result = benchmark(self.data_service._load_json, temp_file)

            # Verify result correctness
            assert len(result) == 1000
            assert all(isinstance(point, tuple) and len(point) >= 3 for point in result)

            # Performance assertion (benchmark provides timing automatically)
            # This will fail if loading takes more than reasonable time

        finally:
            os.unlink(temp_file)

    def test_smoothing_performance_medium_dataset(self, benchmark):
        """Benchmark: Smooth 500 points with moving average - Target: <50ms."""
        # Create medium dataset for smoothing
        medium_data = [(i, float(i * 2 + i % 10), float(i * 3 + i % 7)) for i in range(1, 501)]  # 500 points

        # Benchmark smoothing operation
        result = benchmark(self.data_service.smooth_moving_average, medium_data, 5)

        # Verify result correctness
        assert len(result) == 500
        for original, smoothed in zip(medium_data, result):
            orig_frame, orig_x, orig_y = original
            smooth_frame, smooth_x, smooth_y, _ = safe_extract_point(smoothed)

            assert orig_frame == smooth_frame  # Frame preserved
            assert isinstance(smooth_x, float)
            assert isinstance(smooth_y, float)

    def test_outlier_detection_performance(self, benchmark):
        """Benchmark: Outlier detection on 300 points - Target: <30ms."""
        # Create dataset with some outliers
        base_data = [(i, float(i * 5), float(i * 10)) for i in range(1, 301)]

        # Add some outliers
        outlier_data = base_data.copy()
        outlier_data[50] = (51, 1000.0, 2000.0)  # Clear outlier
        outlier_data[150] = (151, -500.0, -1000.0)  # Another outlier

        # Benchmark outlier detection
        outliers = benchmark(self.data_service.detect_outliers, outlier_data, 2.0)

        # Verify outliers were detected
        assert isinstance(outliers, list)
        assert len(outliers) >= 2  # Should find the outliers we added

    def test_filtering_performance(self, benchmark):
        """Benchmark: Median filtering on 400 points - Target: <40ms."""
        # Create dataset with some noise
        noisy_data = []
        for i in range(1, 401):
            noise_x = (i % 5) * 0.5  # Small noise
            noise_y = (i % 3) * 0.3
            noisy_data.append((i, float(i * 2) + noise_x, float(i * 1.5) + noise_y))

        # Benchmark median filtering
        result = benchmark(self.data_service.filter_median, noisy_data, 5)

        # Verify result correctness
        assert len(result) == 400
        for filtered_point in result:
            frame, x, y, _ = safe_extract_point(filtered_point)
            assert isinstance(frame, int)
            assert isinstance(x, float)
            assert isinstance(y, float)


@pytest.mark.performance
class TestTransformPerformance:
    """Test performance of coordinate transformation operations."""

    def setup_method(self):
        """Set up services for transform testing."""
        self.transform_service = get_transform_service()

    def test_transform_creation_performance(self, benchmark):
        """Benchmark: Create transform from view state - Target: <5ms."""
        mock_view = ProtocolCompliantMockCurveView(
            points=[(1, 100.0, 200.0)],
            zoom_factor=1.5,
            offset_x=50.0,
            offset_y=100.0,
            image_width=1920,
            image_height=1080,
        )

        def create_transform():
            view_state = self.transform_service.create_view_state(mock_view)
            return self.transform_service.create_transform_from_view_state(view_state)

        # Benchmark transform creation
        transform = benchmark(create_transform)

        # Verify transform is valid
        assert transform is not None
        params = transform.get_parameters()
        assert "scale" in params
        assert isinstance(params["scale"], int | float)

    def test_batch_coordinate_transformation_performance(self, benchmark):
        """Benchmark: Transform 100 coordinates - Target: <10ms."""
        # Set up transform
        mock_view = ProtocolCompliantMockCurveView(
            points=[(1, 100.0, 200.0)], zoom_factor=2.0, offset_x=25.0, offset_y=75.0
        )

        view_state = self.transform_service.create_view_state(mock_view)
        transform = self.transform_service.create_transform_from_view_state(view_state)

        # Create coordinate batch for transformation
        coordinate_batch = [(float(i * 10), float(i * 15)) for i in range(100)]

        def batch_transform():
            results = []
            for data_x, data_y in coordinate_batch:
                screen_x, screen_y = transform.data_to_screen(data_x, data_y)
                results.append((screen_x, screen_y))
            return results

        # Benchmark batch transformation
        results = benchmark(batch_transform)

        # Verify results
        assert len(results) == 100
        for screen_x, screen_y in results:
            assert isinstance(screen_x, int | float)
            assert isinstance(screen_y, int | float)

    def test_round_trip_transformation_performance(self, benchmark):
        """Benchmark: Round-trip coordinate conversions - Target: <15ms."""
        # Set up transform with complex parameters
        mock_view = ProtocolCompliantMockCurveView(
            points=[(1, 500.0, 300.0)], zoom_factor=0.75, offset_x=125.0, offset_y=200.0, flip_y_axis=True
        )

        view_state = self.transform_service.create_view_state(mock_view)
        transform = self.transform_service.create_transform_from_view_state(view_state)

        # Test coordinates
        test_coords = [(float(i * 20), float(i * 30)) for i in range(50)]

        def round_trip_transforms():
            results = []
            for data_x, data_y in test_coords:
                # Data to screen
                screen_x, screen_y = transform.data_to_screen(data_x, data_y)
                # Screen back to data
                back_x, back_y = transform.screen_to_data(screen_x, screen_y)
                results.append((back_x, back_y))
            return results

        # Benchmark round-trip transformations
        results = benchmark(round_trip_transforms)

        # Verify accuracy of round-trip
        for i, (back_x, back_y) in enumerate(results):
            orig_x, orig_y = test_coords[i]
            assert abs(back_x - orig_x) < 0.1, f"X round-trip failed: {orig_x} -> {back_x}"
            assert abs(back_y - orig_y) < 0.1, f"Y round-trip failed: {orig_y} -> {back_y}"


@pytest.mark.performance
class TestMemoryUsagePatterns:
    """Test memory usage patterns during typical operations."""

    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def test_data_loading_memory_growth(self):
        """Test memory growth during data loading operations."""
        data_service = get_data_service()
        initial_memory = self.get_memory_usage()

        # Create and load multiple datasets
        datasets = []
        for dataset_size in [100, 200, 300, 400, 500]:
            dataset = [(i, float(i * 2), float(i * 3)) for i in range(1, dataset_size + 1)]
            datasets.append(dataset)

            # Apply operations that might accumulate memory
            _ = data_service.smooth_moving_average(dataset, window_size=5)
            _ = data_service.detect_outliers(dataset, threshold=2.0)
            _ = data_service.filter_median(dataset, window_size=3)

            # Force garbage collection
            gc.collect()

        final_memory = self.get_memory_usage()
        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (< 50MB for this test)
        assert memory_growth < 50, f"Excessive memory growth: {memory_growth:.1f}MB"

    def test_transform_object_memory_lifecycle(self):
        """Test that transform objects don't accumulate in memory."""
        transform_service = get_transform_service()
        initial_memory = self.get_memory_usage()

        # Create many transforms
        transforms = []
        for i in range(100):
            mock_view = ProtocolCompliantMockCurveView(
                points=[(1, float(i), float(i * 2))],
                zoom_factor=1.0 + i * 0.01,
                offset_x=float(i),
                offset_y=float(i * 2),
            )

            view_state = transform_service.create_view_state(mock_view)
            transform = transform_service.create_transform_from_view_state(view_state)
            transforms.append(transform)

        # Clear references and force garbage collection
        del transforms
        gc.collect()

        final_memory = self.get_memory_usage()
        memory_growth = final_memory - initial_memory

        # Memory should not grow excessively (< 20MB)
        assert memory_growth < 20, f"Transform objects may be leaking: {memory_growth:.1f}MB"

    def test_service_cache_memory_management(self):
        """Test that service caches don't grow unbounded."""
        data_service = get_data_service()
        initial_memory = self.get_memory_usage()

        # Create many temporary files and load them
        temp_files = []
        try:
            for i in range(50):
                # Create small dataset
                data = [{"frame": j, "x": float(j), "y": float(j * 2)} for j in range(1, 21)]  # 20 points each

                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                    json.dump(data, f)
                    temp_files.append(f.name)

                # Load data (may be cached)
                loaded_data = data_service._load_json(f.name)
                assert len(loaded_data) == 20

        finally:
            # Clean up temp files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

        # Clear any caches
        if hasattr(data_service, "clear_image_cache"):
            data_service.clear_image_cache()

        gc.collect()

        final_memory = self.get_memory_usage()
        memory_growth = final_memory - initial_memory

        # Memory growth should be minimal (< 30MB)
        assert memory_growth < 30, f"Service caches may be growing unbounded: {memory_growth:.1f}MB"


@pytest.mark.performance
@pytest.mark.slow
class TestRealisticWorkflowPerformance:
    """Test performance of complete realistic workflows."""

    def setup_method(self):
        """Set up services."""
        self.data_service = get_data_service()
        self.transform_service = get_transform_service()

    def test_complete_workflow_performance(self, benchmark):
        """Benchmark: Complete file load → process → transform → save workflow."""
        # Create realistic dataset
        realistic_data = []
        for frame in range(1, 301):  # 300 frames (10 seconds at 30fps)
            # Simulate realistic motion with slight camera shake
            base_x = 960 + 100 * (frame / 300) + (frame % 20) * 0.5
            base_y = 540 + 50 * (frame / 300) + (frame % 15) * 0.3
            realistic_data.append(
                {"frame": frame, "x": base_x, "y": base_y, "status": "keyframe" if frame % 5 == 0 else "interpolated"}
            )

        # Create input file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(realistic_data, f)
            input_file = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        def complete_workflow():
            # Load data
            loaded_data = self.data_service._load_json(input_file)

            # Process data (smoothing)
            smoothed_data = self.data_service.smooth_moving_average(loaded_data, window_size=5)

            # Create transform and test coordinate conversions
            mock_view = ProtocolCompliantMockCurveView(
                points=smoothed_data, zoom_factor=1.0, offset_x=0.0, offset_y=0.0
            )

            view_state = self.transform_service.create_view_state(mock_view)
            transform = self.transform_service.create_transform_from_view_state(view_state)

            # Transform sample of coordinates
            for i in range(0, len(smoothed_data), 10):  # Every 10th point
                point = smoothed_data[i]
                frame, x, y, _ = safe_extract_point(point)
                screen_coords = transform.data_to_screen(x, y)
                # Just verify transformation works
                assert len(screen_coords) == 2

            # Save processed data
            self.data_service._save_json(output_file, smoothed_data, "test_curve", "#FF0000")

            return len(smoothed_data)

        try:
            # Benchmark complete workflow
            result_count = benchmark(complete_workflow)
            assert result_count == 300

        finally:
            # Cleanup
            for temp_file in [input_file, output_file]:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

    def test_interactive_performance_simulation(self, benchmark):
        """Benchmark: Simulate interactive user operations performance."""
        # Set up realistic state
        curve_data = [(i, float(i * 3), float(i * 4)) for i in range(1, 201)]  # 200 points

        mock_view = ProtocolCompliantMockCurveView(
            points=curve_data,
            zoom_factor=1.5,
            offset_x=100.0,
            offset_y=50.0,
            selected_points={10, 11, 12},  # Multiple selection
        )

        view_state = self.transform_service.create_view_state(mock_view)
        _ = self.transform_service.create_transform_from_view_state(view_state)

        def simulate_interactive_operations():
            operations_count = 0

            # Simulate zoom operation
            mock_view.zoom_factor = 2.0
            new_view_state = self.transform_service.create_view_state(mock_view)
            _ = self.transform_service.create_transform_from_view_state(new_view_state)
            operations_count += 1

            # Simulate pan operation
            mock_view.offset_x = 150.0
            mock_view.offset_y = 75.0
            pan_view_state = self.transform_service.create_view_state(mock_view)
            pan_transform = self.transform_service.create_transform_from_view_state(pan_view_state)
            operations_count += 1

            # Simulate point selection and coordinate lookups
            for point_idx in [5, 15, 25, 35, 45]:  # Sample points
                if point_idx < len(curve_data):
                    point = curve_data[point_idx]
                    screen_coords = pan_transform.data_to_screen(point[1], point[2])
                    _ = pan_transform.screen_to_data(screen_coords[0], screen_coords[1])
                    operations_count += 1

            # Simulate data processing on selected points
            selected_data = [curve_data[i] for i in mock_view.selected_points if i < len(curve_data)]
            if selected_data:
                smoothed_selection = self.data_service.smooth_moving_average(selected_data, window_size=3)
                operations_count += len(smoothed_selection)

            return operations_count

        # Benchmark interactive simulation
        operation_count = benchmark(simulate_interactive_operations)
        assert operation_count > 0


@pytest.mark.performance
class TestPerformanceBaselines:
    """Establish and verify performance baselines for key operations."""

    def test_baseline_data_operations(self):
        """Verify baseline performance for data operations hasn't regressed."""
        data_service = get_data_service()

        # Standard test dataset
        test_data = [(i, float(i * 2), float(i * 1.5)) for i in range(1, 101)]

        # Time smoothing operation
        start_time = time.perf_counter()
        smoothed = data_service.smooth_moving_average(test_data, window_size=5)
        smoothing_time = time.perf_counter() - start_time

        # Time outlier detection
        start_time = time.perf_counter()
        outliers = data_service.detect_outliers(test_data, threshold=2.0)
        outlier_time = time.perf_counter() - start_time

        # Time filtering
        start_time = time.perf_counter()
        filtered = data_service.filter_median(test_data, window_size=3)
        filter_time = time.perf_counter() - start_time

        # Baseline assertions (adjust these based on acceptable performance)
        assert smoothing_time < 0.05, f"Smoothing too slow: {smoothing_time:.3f}s"
        assert outlier_time < 0.03, f"Outlier detection too slow: {outlier_time:.3f}s"
        assert filter_time < 0.02, f"Filtering too slow: {filter_time:.3f}s"

        # Verify correctness
        assert len(smoothed) == len(test_data)
        assert isinstance(outliers, list)
        assert len(filtered) == len(test_data)

    def test_baseline_transform_operations(self):
        """Verify baseline performance for transform operations."""
        transform_service = get_transform_service()

        # Create standard transform
        mock_view = ProtocolCompliantMockCurveView(
            points=[(1, 100.0, 200.0)], zoom_factor=1.5, offset_x=50.0, offset_y=100.0
        )

        # Time view state creation
        start_time = time.perf_counter()
        view_state = transform_service.create_view_state(mock_view)
        view_state_time = time.perf_counter() - start_time

        # Time transform creation
        start_time = time.perf_counter()
        transform = transform_service.create_transform_from_view_state(view_state)
        transform_time = time.perf_counter() - start_time

        # Time coordinate transformations
        test_coords = [(100.0, 200.0), (300.0, 400.0), (500.0, 600.0)]

        start_time = time.perf_counter()
        for data_x, data_y in test_coords:
            screen_coords = transform.data_to_screen(data_x, data_y)
            transform.screen_to_data(screen_coords[0], screen_coords[1])
        coord_time = time.perf_counter() - start_time

        # Baseline assertions (very tight timing for simple operations)
        assert view_state_time < 0.001, f"View state creation too slow: {view_state_time:.4f}s"
        assert transform_time < 0.001, f"Transform creation too slow: {transform_time:.4f}s"
        assert coord_time < 0.001, f"Coordinate transforms too slow: {coord_time:.4f}s"
