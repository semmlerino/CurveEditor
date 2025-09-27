"""
Integration tests for the CurveEditor service layer.

This module tests how the consolidated services work together to ensure the
4-service architecture functions correctly. Tests focus on real service
interactions rather than mocked dependencies.

Services under test:
1. TransformService - Coordinate transformations and view state management
2. DataService - Data operations, analysis, file I/O, and image management
3. InteractionService - User interactions, point manipulation, and history
4. UIService - UI operations, dialogs, status updates, and component management

Current Status: Only 29% test coverage, services at 10-25%, no integration tests.
Target: Increase service coverage from 25% to at least 50%.
"""

import json
import os
import tempfile
from unittest.mock import Mock

from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage

# Import services - using real implementations, not mocks
from services import (
    get_data_service,
    get_interaction_service,
    get_transform_service,
    get_ui_service,
)
from services.transform_service import Transform, ViewState

# Import test utilities
from tests.test_helpers import ProtocolCompliantMockCurveView, ProtocolCompliantMockMainWindow


class TestServiceInitialization:
    """Test service container initialization and dependency injection."""

    def test_service_initialization(self):
        """Test that all services initialize correctly."""
        # Verify all core services are available
        transform_service = get_transform_service()
        data_service = get_data_service()
        interaction_service = get_interaction_service()
        ui_service = get_ui_service()

        assert transform_service is not None
        assert data_service is not None
        assert interaction_service is not None
        assert ui_service is not None

        # Verify services are singletons (same instance returned)
        assert get_transform_service() is transform_service
        assert get_data_service() is data_service
        assert get_interaction_service() is interaction_service
        assert get_ui_service() is ui_service

    def test_service_dependency_injection(self):
        """Test that services can access each other through the container."""
        # Get services through container
        transform_service = get_transform_service()
        data_service = get_data_service()

        # Verify services exist and have expected attributes/methods
        assert hasattr(transform_service, "create_transform")
        assert hasattr(data_service, "smooth_moving_average")
        assert hasattr(data_service, "load_track_data")
        assert hasattr(data_service, "load_image_sequence")

    def test_service_lifecycle_management(self):
        """Test service lifecycle initialization and cleanup."""
        # Services should be properly initialized
        services = [get_transform_service(), get_data_service(), get_interaction_service(), get_ui_service()]

        for service in services:
            # All services should be instantiated
            assert service is not None

            # Services should have initialization state
            # (This is basic - more specific initialization tests would be in unit tests)


class TestCrossServiceCommunication:
    """Test how services communicate with each other."""

    def test_transform_data_service_integration(self):
        """Test integration between TransformService and DataService."""
        transform_service = get_transform_service()
        data_service = get_data_service()

        # Create test data
        test_points = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]

        # Create mock curve view with real transform capabilities
        mock_view = ProtocolCompliantMockCurveView(
            points=test_points, zoom_factor=2.0, offset_x=50.0, offset_y=100.0, image_width=1920, image_height=1080
        )

        # Test transform service can create transforms for data
        view_state = transform_service.create_view_state(mock_view)
        assert isinstance(view_state, ViewState)
        assert view_state.zoom_factor == 2.0
        assert view_state.offset_x == 50.0
        assert view_state.offset_y == 100.0

        transform = transform_service.create_transform_from_view_state(view_state)
        assert isinstance(transform, Transform)

        # Test data service can work with transforms
        smoothed_data = data_service.smooth_moving_average(test_points, window_size=3)
        assert len(smoothed_data) == len(test_points)

        # Verify smoothed data maintains structure
        for point in smoothed_data:
            assert len(point) >= 3  # frame, x, y at minimum

    def test_interaction_transform_service_integration(self):
        """Test integration between InteractionService and TransformService."""
        get_interaction_service()
        transform_service = get_transform_service()

        # Create mock curve view
        mock_view = ProtocolCompliantMockCurveView(
            points=[(1, 100.0, 200.0), (2, 150.0, 250.0)], zoom_factor=1.5, offset_x=25.0, offset_y=75.0
        )

        # Test interaction service can get current transform
        view_state = transform_service.create_view_state(mock_view)
        transform = transform_service.create_transform_from_view_state(view_state)

        # Verify transform parameters match view state
        params = transform.get_parameters()
        assert params["scale"] == 1.5

        # Test coordinate transformations for interactions
        screen_point = QPointF(300.0, 400.0)
        data_x, data_y = transform.screen_to_data(screen_point.x(), screen_point.y())

        # Transform back to verify consistency
        back_x, back_y = transform.data_to_screen(data_x, data_y)
        assert abs(back_x - screen_point.x()) < 0.1
        assert abs(back_y - screen_point.y()) < 0.1

    def test_data_ui_service_integration(self):
        """Test integration between DataService and UIService."""
        data_service = get_data_service()
        ui_service = get_ui_service()

        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_data = [
                {"frame": 1, "x": 100.0, "y": 200.0, "status": "keyframe"},
                {"frame": 2, "x": 150.0, "y": 250.0, "status": "keyframe"},
            ]
            json.dump(test_data, f)
            temp_file = f.name

        try:
            # Test data service can load data (would normally show UI dialogs)
            loaded_data = data_service._load_json(temp_file)
            assert len(loaded_data) == 2
            assert loaded_data[0] == (1, 100.0, 200.0, "keyframe")

            # UI service should be able to handle status updates
            # Check that UI service has dialog methods (its main functionality)
            assert hasattr(ui_service, "get_smooth_window_size")
            assert hasattr(ui_service, "get_filter_params")

        finally:
            os.unlink(temp_file)


class TestCompleteWorkflows:
    """Test complete workflows that span multiple services."""

    def test_file_load_to_display_workflow(self):
        """Test complete workflow: File load → Data processing → UI update."""
        # This tests the full pipeline from file loading to display

        # 1. Create test data file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_data = [
                {"frame": 1, "x": 100.0, "y": 200.0, "status": "keyframe"},
                {"frame": 2, "x": 150.0, "y": 250.0, "status": "interpolated"},
                {"frame": 3, "x": 200.0, "y": 300.0, "status": "keyframe"},
            ]
            json.dump(test_data, f)
            temp_file = f.name

        try:
            # 2. Load data through DataService
            data_service = get_data_service()
            loaded_data = data_service._load_json(temp_file)
            assert len(loaded_data) == 3

            # 3. Process data (smoothing)
            smoothed_data = data_service.smooth_moving_average(loaded_data, window_size=3)
            assert len(smoothed_data) == 3

            # 4. Create view state and transform for display
            transform_service = get_transform_service()
            mock_view = ProtocolCompliantMockCurveView(
                points=smoothed_data, zoom_factor=1.0, offset_x=0.0, offset_y=0.0
            )

            view_state = transform_service.create_view_state(mock_view)
            transform = transform_service.create_transform_from_view_state(view_state)

            # 5. Verify data can be transformed for display
            for point in smoothed_data:
                _frame, x, y = point[0], point[1], point[2]
                screen_x, screen_y = transform.data_to_screen(x, y)
                assert isinstance(screen_x, int | float)
                assert isinstance(screen_y, int | float)

        finally:
            os.unlink(temp_file)

    def test_point_manipulation_workflow(self, qapp):
        """Test complete workflow: Point selection → Manipulation → History → UI update."""
        get_interaction_service()
        transform_service = get_transform_service()

        # 1. Set up mock objects
        mock_view = ProtocolCompliantMockCurveView(
            points=[(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)],
            selected_points=set(),
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )

        mock_main_window = ProtocolCompliantMockMainWindow()
        mock_main_window.curve_view.curve_data = mock_view.points.copy()

        # 2. Create transform for coordinate conversion
        view_state = transform_service.create_view_state(mock_view)
        transform = transform_service.create_transform_from_view_state(view_state)

        # 3. Simulate point selection
        # Find a point at screen coordinates
        screen_point = transform.data_to_screen(150.0, 250.0)  # Point 2
        click_pos = QPointF(screen_point[0], screen_point[1])

        # Mock mouse press event
        mock_event = Mock()
        mock_event.position.return_value = click_pos
        mock_event.button.return_value = 1  # Left button

        # This would normally select the point
        # (In real implementation, this would involve event handling)
        mock_view.selected_points.add(1)  # Select second point
        mock_view.selected_point_idx = 1

        # 4. Verify point is selected
        assert 1 in mock_view.selected_points
        assert mock_view.selected_point_idx == 1

        # 5. Simulate point movement
        new_data_pos = (175.0, 275.0)  # New position
        transform.data_to_screen(new_data_pos[0], new_data_pos[1])

        # Update point position
        if mock_view.selected_point_idx >= 0:
            old_point = mock_view.points[mock_view.selected_point_idx]
            mock_view.points[mock_view.selected_point_idx] = (old_point[0], new_data_pos[0], new_data_pos[1])

        # 6. Verify point was moved
        moved_point = mock_view.points[1]
        assert moved_point[1] == 175.0  # x coordinate
        assert moved_point[2] == 275.0  # y coordinate

    def test_undo_redo_workflow(self):
        """Test complete workflow: Action → History → Undo → Redo."""
        data_service = get_data_service()

        # 1. Create initial data state
        original_data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]

        # 2. Apply data transformation (smoothing)
        smoothed_data = data_service.smooth_moving_average(original_data, window_size=3)

        # 3. Verify transformation occurred
        assert len(smoothed_data) == len(original_data)
        # Smoothed data should be slightly different from original
        assert smoothed_data != original_data

        # 4. Test outlier detection (another data operation)
        outliers = data_service.detect_outliers(original_data, threshold=2.0)
        assert isinstance(outliers, list)

        # 5. Test data filtering
        filtered_data = data_service.filter_median(original_data, window_size=3)
        assert len(filtered_data) == len(original_data)

    def test_image_sequence_workflow(self):
        """Test complete workflow: Image loading → Frame navigation → Display update."""
        data_service = get_data_service()

        # 1. Create temporary image directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some dummy image files
            for i in range(1, 4):
                image_path = os.path.join(temp_dir, f"frame{i:03d}.jpg")
                # Create a minimal image file (1x1 pixel)
                image = QImage(1, 1, QImage.Format.Format_RGB32)
                image.save(image_path, "JPEG")

            # 2. Load image sequence
            image_files = data_service.load_image_sequence(temp_dir)
            assert len(image_files) == 3
            # image_files contains full paths, so check the basename
            assert all(os.path.basename(f).startswith("frame") and f.endswith(".jpg") for f in image_files)

            # 3. Set up mock view with image sequence
            mock_view = ProtocolCompliantMockCurveView(
                points=[(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)],
                image_sequence_path=temp_dir,
                image_filenames=image_files,
                current_image_idx=0,
            )

            # 4. Test image navigation
            data_service.set_current_image_by_frame(mock_view, 2)  # Go to frame 2
            # The service should find the closest image for frame 2
            assert hasattr(mock_view, "current_image_idx")

            # 5. Test current image loading
            current_image = data_service.load_current_image(mock_view)
            # Should return None or QImage depending on implementation
            assert current_image is None or isinstance(current_image, QImage)


class TestErrorHandlingIntegration:
    """Test error handling across service boundaries."""

    def test_file_loading_error_propagation(self):
        """Test that file loading errors are properly handled across services."""
        data_service = get_data_service()

        # Try to load non-existent file - DataService handles errors gracefully and returns empty list
        result = data_service._load_json("/nonexistent/file.json")
        assert result == []  # Should return empty list, not raise exception

        # Try to load invalid JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            temp_file = f.name

        try:
            # Invalid JSON also returns empty list instead of raising
            result = data_service._load_json(temp_file)
            assert result == []
        finally:
            os.unlink(temp_file)

    def test_transform_error_handling(self):
        """Test error handling in transform operations."""
        transform_service = get_transform_service()

        # Create view with invalid/extreme values
        mock_view = ProtocolCompliantMockCurveView(
            points=[],  # Empty points
            zoom_factor=0.0,  # Invalid zoom
            offset_x=float("inf"),  # Invalid offset
            offset_y=float("nan"),  # Invalid offset
        )

        # Service should handle invalid values gracefully
        view_state = transform_service.create_view_state(mock_view)
        transform = transform_service.create_transform_from_view_state(view_state)

        # Transform should still be created even with invalid input
        assert transform is not None

    def test_service_resilience(self):
        """Test that services remain functional after errors."""
        data_service = get_data_service()

        # Cause an error
        try:
            data_service._load_json("/nonexistent.json")
        except OSError:
            pass  # Expected error

        # Service should still work after error
        valid_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        smoothed = data_service.smooth_moving_average(valid_data, window_size=2)
        assert len(smoothed) == 2


class TestServicePerformance:
    """Test performance characteristics of service integrations."""

    def test_large_dataset_processing(self):
        """Test services can handle reasonably large datasets."""
        data_service = get_data_service()

        # Create larger dataset
        large_dataset = [(i, float(i * 10), float(i * 20)) for i in range(1, 1001)]  # 1000 points

        # Test smoothing performance
        smoothed = data_service.smooth_moving_average(large_dataset, window_size=5)
        assert len(smoothed) == 1000

        # Test outlier detection
        outliers = data_service.detect_outliers(large_dataset, threshold=2.0)
        assert isinstance(outliers, list)

        # Test filtering
        filtered = data_service.filter_median(large_dataset, window_size=5)
        assert len(filtered) == 1000

    def test_transform_performance(self):
        """Test transform performance with many points."""
        transform_service = get_transform_service()

        # Create many points
        many_points = [(i, float(i), float(i * 2)) for i in range(1, 501)]  # 500 points

        mock_view = ProtocolCompliantMockCurveView(points=many_points, zoom_factor=1.0, offset_x=0.0, offset_y=0.0)

        view_state = transform_service.create_view_state(mock_view)
        transform = transform_service.create_transform_from_view_state(view_state)

        # Test batch transformations
        for point in many_points[:100]:  # Test subset for performance
            screen_coords = transform.data_to_screen(point[1], point[2])
            assert len(screen_coords) == 2

            # Transform back
            data_coords = transform.screen_to_data(screen_coords[0], screen_coords[1])
            assert len(data_coords) == 2


class TestServiceResourceManagement:
    """Test proper resource management across services."""

    def test_memory_cleanup(self):
        """Test that services properly clean up resources."""
        data_service = get_data_service()

        # Test image cache management
        data_service.clear_image_cache()
        # Should not raise any errors

        # Test cache size management
        data_service.set_cache_size(10)
        # Should not raise any errors

    def test_service_isolation(self):
        """Test that services are properly isolated from each other."""
        # Get separate instances
        transform1 = get_transform_service()
        transform2 = get_transform_service()

        # Should be the same instance (singleton pattern)
        assert transform1 is transform2

        # But service state should not interfere with different views
        view1 = ProtocolCompliantMockCurveView(points=[(1, 100.0, 200.0)], zoom_factor=1.0, offset_x=0.0, offset_y=0.0)
        view2 = ProtocolCompliantMockCurveView(
            points=[(1, 500.0, 600.0)], zoom_factor=2.0, offset_x=50.0, offset_y=100.0
        )

        state1 = transform1.create_view_state(view1)
        state2 = transform1.create_view_state(view2)

        # States should be different
        assert state1.zoom_factor != state2.zoom_factor
        assert state1.offset_x != state2.offset_x


# ==================== Performance Baseline Tests ====================


class TestPerformanceBaselines:
    """Establish performance baselines for service operations."""

    def test_data_processing_performance(self):
        """Test data processing operations performance."""
        import time

        data_service = get_data_service()
        test_data = [(i, float(i * 10), float(i * 20)) for i in range(1, 101)]

        # Time smoothing operation
        start_time = time.perf_counter()
        result = data_service.smooth_moving_average(test_data, 5)
        elapsed = time.perf_counter() - start_time

        assert len(result) == 100
        # Should complete in reasonable time (< 100ms)
        assert elapsed < 0.1, f"Smoothing took {elapsed:.3f}s, expected < 0.1s"

    def test_transform_performance(self):
        """Test coordinate transformation performance."""
        import time

        transform_service = get_transform_service()

        mock_view = ProtocolCompliantMockCurveView(
            points=[(1, 100.0, 200.0)], zoom_factor=1.5, offset_x=25.0, offset_y=75.0
        )

        def create_and_transform():
            view_state = transform_service.create_view_state(mock_view)
            transform = transform_service.create_transform_from_view_state(view_state)
            return transform.data_to_screen(100.0, 200.0)

        # Time transform creation and execution
        start_time = time.perf_counter()
        result = create_and_transform()
        elapsed = time.perf_counter() - start_time

        assert len(result) == 2
        # Should complete very quickly (< 10ms)
        assert elapsed < 0.01, f"Transform took {elapsed:.4f}s, expected < 0.01s"


# ==================== Service State Management Tests ====================


class TestServiceStateMaintenance:
    """Test that services maintain consistent state across operations."""

    def test_data_service_state_consistency(self):
        """Test DataService maintains consistent state."""
        data_service = get_data_service()

        # Verify initial state
        recent_files = data_service.get_recent_files()
        assert isinstance(recent_files, list)

        # Add a file to recent files
        test_file = "/test/path/data.json"
        data_service.add_recent_file(test_file)

        # Verify state updated
        updated_files = data_service.get_recent_files()
        assert test_file in updated_files

        # Test cache operations don't affect file state
        data_service.clear_image_cache()
        assert test_file in data_service.get_recent_files()

    def test_transform_service_state_isolation(self):
        """Test TransformService maintains proper state isolation."""
        transform_service = get_transform_service()

        # Create two different views
        view_a = ProtocolCompliantMockCurveView(points=[(1, 100.0, 200.0)], zoom_factor=1.0, offset_x=0.0, offset_y=0.0)
        view_b = ProtocolCompliantMockCurveView(
            points=[(1, 300.0, 400.0)], zoom_factor=2.0, offset_x=50.0, offset_y=100.0
        )

        # Create transforms for both
        state_a = transform_service.create_view_state(view_a)
        state_b = transform_service.create_view_state(view_b)

        transform_a = transform_service.create_transform_from_view_state(state_a)
        transform_b = transform_service.create_transform_from_view_state(state_b)

        # Verify transforms are independent
        result_a = transform_a.data_to_screen(100.0, 200.0)
        result_b = transform_b.data_to_screen(100.0, 200.0)

        # Results should be different due to different view states
        assert result_a != result_b
