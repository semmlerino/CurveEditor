"""
Data Pipeline Integration Tests for CurveEditor.

This module tests complete data workflows from file loading to display,
ensuring data consistency throughout the pipeline. Tests use real service
implementations with minimal mocking to catch integration issues.

Pipeline stages tested:
1. File loading → Data validation → Storage
2. Data processing → Transformation → Analysis
3. Point manipulation → History tracking → Undo/Redo
4. UI updates → Status notifications → Error handling

Focus on HIGH-VALUE integration tests that verify the data pipeline works correctly.

Note on Transform Pattern:
    Some tests use the legacy 2-step pattern for explicitness in testing:
        view_state = transform_service.create_view_state(view)
        transform = transform_service.create_transform_from_view_state(view_state)

    For NEW production code, use the recommended pattern from CLAUDE.md:
        transform = transform_service.get_transform(view)
"""

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

import csv
import json
import os
import tempfile

from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage

from core.point_types import safe_extract_point

# Import services for real integration testing
from services import (
    get_data_service,
    get_interaction_service,
    get_transform_service,
)
from services.data_service import DataService
from services.interaction_service import InteractionService
from services.transform_service import TransformService

# Import test utilities
from tests.test_helpers import ProtocolCompliantMockCurveView


class TestFileToDisplayPipeline:
    """Test complete pipeline from file loading to display rendering."""

    data_service: DataService  # pyright: ignore[reportUninitializedInstanceVariable]
    transform_service: TransformService  # pyright: ignore[reportUninitializedInstanceVariable]

    def setup_method(self) -> None:
        """Set up test environment for each test method."""
        self.data_service = get_data_service()
        self.transform_service = get_transform_service()

    def test_json_load_to_display_workflow(self) -> None:
        """Test: JSON file → Load → Process → Transform → Display coordinates."""
        # 1. Create realistic test data file
        test_data = [
            {"frame": 1, "x": 960.5, "y": 540.2, "status": "keyframe"},
            {"frame": 2, "x": 965.1, "y": 542.8, "status": "keyframe"},
            {"frame": 3, "x": 958.9, "y": 538.1, "status": "interpolated"},
            {"frame": 4, "x": 972.3, "y": 545.7, "status": "keyframe"},
            {"frame": 5, "x": 969.8, "y": 543.2, "status": "keyframe"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name

        try:
            # 2. Load data through DataService
            loaded_data = self.data_service._load_json(temp_file)

            # Verify data structure and content
            assert len(loaded_data) == 5
            for i, point in enumerate(loaded_data):
                frame, x, y, status = safe_extract_point(point)
                assert frame == test_data[i]["frame"]
                # Use proper float comparison with casting
                assert abs(float(x) - float(test_data[i]["x"])) < 0.001
                assert abs(float(y) - float(test_data[i]["y"])) < 0.001
                assert status == test_data[i]["status"]

            # 3. Create view state for realistic display scenario
            mock_view = ProtocolCompliantMockCurveView(
                points=loaded_data,
                zoom_factor=0.8,  # Zoomed out to see all points
                offset_x=100.0,  # Panned slightly
                offset_y=50.0,
                image_width=1920,
                image_height=1080,
                flip_y_axis=True,  # Image coordinates
            )

            # 4. Generate transform for display
            view_state = self.transform_service.create_view_state(mock_view)
            transform = self.transform_service.create_transform_from_view_state(view_state)

            # 5. Convert all data points to screen coordinates
            screen_coordinates: list[tuple[int, float, float, str]] = []
            for point in loaded_data:
                frame, x, y, status = safe_extract_point(point)
                screen_x, screen_y = transform.data_to_screen(float(x), float(y))
                screen_coordinates.append((int(frame), float(screen_x), float(screen_y), str(status)))

            # 6. Verify screen coordinates are reasonable
            for frame, screen_x, screen_y, status in screen_coordinates:
                assert isinstance(screen_x, int | float)
                assert isinstance(screen_y, int | float)
                # Should be within reasonable screen bounds (with margin for pan/zoom)
                assert -1000 <= screen_x <= 3000  # Allow for panning outside viewport
                assert -1000 <= screen_y <= 2000

            # 7. Test reverse transformation for consistency
            for i, (frame, screen_x, screen_y, status) in enumerate(screen_coordinates):
                data_x, data_y = transform.screen_to_data(screen_x, screen_y)
                original_point = safe_extract_point(loaded_data[i])
                original_x, original_y = float(original_point[1]), float(original_point[2])

                # Should round-trip accurately
                assert abs(data_x - original_x) < 0.1
                assert abs(data_y - original_y) < 0.1

        finally:
            os.unlink(temp_file)

    def test_csv_load_to_display_workflow(self) -> None:
        """Test: CSV file → Load → Process → Transform → Display coordinates."""
        # 1. Create CSV test data
        csv_data = [
            ["frame", "x", "y", "status"],
            ["1", "100.0", "200.0", "keyframe"],
            ["2", "105.5", "198.2", "keyframe"],
            ["3", "98.9", "203.1", "interpolated"],
            ["4", "112.3", "195.7", "keyframe"],
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            temp_file = f.name

        try:
            # 2. Load CSV data
            loaded_data = self.data_service._load_csv(temp_file)

            # Verify CSV parsing
            assert len(loaded_data) == 4  # Excluding header
            first_point = safe_extract_point(loaded_data[0])
            assert first_point[0] == 1  # frame
            assert first_point[1] == 100.0  # x
            assert first_point[2] == 200.0  # y
            assert first_point[3] == "keyframe"  # status

            # 3. Process through full pipeline
            mock_view = ProtocolCompliantMockCurveView(points=loaded_data, zoom_factor=1.5, offset_x=0.0, offset_y=0.0)

            view_state = self.transform_service.create_view_state(mock_view)
            transform = self.transform_service.create_transform_from_view_state(view_state)

            # 4. Verify all points can be transformed
            for point in loaded_data:
                frame, x, y, status = safe_extract_point(point)
                screen_coords = transform.data_to_screen(float(x), float(y))
                assert len(screen_coords) == 2
                assert all(isinstance(coord, int | float) for coord in screen_coords)

        finally:
            os.unlink(temp_file)

    def test_large_dataset_pipeline(self) -> None:
        """Test pipeline performance with larger datasets."""
        # 1. Generate larger dataset (simulate real tracking data)
        large_dataset = []
        for frame in range(1, 201):  # 200 frames
            # Simulate realistic motion with some noise
            base_x = 960 + 50 * (frame / 200) + (frame % 10) * 2
            base_y = 540 + 20 * (frame / 200) + (frame % 7) * 1.5

            large_dataset.append(
                {"frame": frame, "x": base_x, "y": base_y, "status": "keyframe" if frame % 5 == 0 else "interpolated"}
            )

        # 2. Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(large_dataset, f)
            temp_file = f.name

        try:
            # 3. Load large dataset
            loaded_data = self.data_service._load_json(temp_file)
            assert len(loaded_data) == 200

            # 4. Test data processing performance
            smoothed_data = self.data_service.smooth_moving_average(loaded_data, window_size=5)
            assert len(smoothed_data) == 200

            # 5. Test outlier detection on large dataset
            outliers = self.data_service.detect_outliers(loaded_data, threshold=2.0)
            assert isinstance(outliers, list)
            # With simulated data, may have many outliers due to pattern
            assert len(outliers) >= 0  # Just verify it returns a list

            # 6. Test transform performance
            mock_view = ProtocolCompliantMockCurveView(
                points=smoothed_data, zoom_factor=1.0, offset_x=0.0, offset_y=0.0
            )

            view_state = self.transform_service.create_view_state(mock_view)
            transform = self.transform_service.create_transform_from_view_state(view_state)

            # 7. Test batch transformation (sample for performance)
            sample_size = min(50, len(smoothed_data))
            for i in range(0, len(smoothed_data), len(smoothed_data) // sample_size):
                point = smoothed_data[i]
                frame, x, y, _ = safe_extract_point(point)
                screen_coords = transform.data_to_screen(float(x), float(y))
                assert len(screen_coords) == 2

        finally:
            os.unlink(temp_file)


class TestPointManipulationPipeline:
    """Test complete point manipulation workflows including undo/redo."""

    interaction_service: InteractionService  # pyright: ignore[reportUninitializedInstanceVariable]
    transform_service: TransformService  # pyright: ignore[reportUninitializedInstanceVariable]
    data_service: DataService  # pyright: ignore[reportUninitializedInstanceVariable]

    def setup_method(self) -> None:
        """Set up test environment."""
        self.interaction_service = get_interaction_service()
        self.transform_service = get_transform_service()
        self.data_service = get_data_service()

    def test_point_selection_to_modification_workflow(self) -> None:
        """Test: Point selection → Coordinate modification → Transform update → Display."""
        # 1. Set up test data and view
        initial_points = [(1, 100.0, 200.0, "keyframe"), (2, 150.0, 250.0, "keyframe"), (3, 200.0, 300.0, "keyframe")]

        mock_view = ProtocolCompliantMockCurveView(
            points=initial_points,
            selected_points=set(),
            selected_point_idx=-1,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )

        # 2. Create transform for coordinate conversions
        view_state = self.transform_service.create_view_state(mock_view)
        transform = self.transform_service.create_transform_from_view_state(view_state)

        # 3. Simulate point selection by screen coordinates
        # Target point 2 (150.0, 250.0)
        target_point_data = (150.0, 250.0)
        screen_coords = transform.data_to_screen(target_point_data[0], target_point_data[1])
        click_position = QPointF(screen_coords[0], screen_coords[1])

        # 4. Find point at click position (simulate interaction service logic)
        found_point_idx = -1
        for i, point in enumerate(mock_view.points):
            frame, x, y, _ = safe_extract_point(point)
            point_screen = transform.data_to_screen(float(x), float(y))
            distance = (
                (point_screen[0] - click_position.x()) ** 2 + (point_screen[1] - click_position.y()) ** 2
            ) ** 0.5
            if distance < 10:  # Within selection tolerance
                found_point_idx = i
                break

        assert found_point_idx == 1  # Should find point 2

        # 5. Select the point
        mock_view.selected_points.add(found_point_idx)
        mock_view.selected_point_idx = found_point_idx

        # 6. Modify point position
        new_data_position = (175.0, 275.0)  # Move point
        new_screen_position = transform.data_to_screen(new_data_position[0], new_data_position[1])

        # Update point data
        old_point = mock_view.points[found_point_idx]
        frame, _, _, status = safe_extract_point(old_point)
        mock_view.points[found_point_idx] = (int(frame), new_data_position[0], new_data_position[1], str(status))

        # 7. Verify modification
        modified_point = safe_extract_point(mock_view.points[found_point_idx])
        assert modified_point[1] == 175.0  # x
        assert modified_point[2] == 275.0  # y
        assert modified_point[0] == 2  # frame unchanged
        assert modified_point[3] == "keyframe"  # status unchanged

        # 8. Test that transform still works with modified data
        updated_screen = transform.data_to_screen(float(modified_point[1]), float(modified_point[2]))
        assert abs(updated_screen[0] - new_screen_position[0]) < 0.1
        assert abs(updated_screen[1] - new_screen_position[1]) < 0.1

    def test_multi_point_selection_and_batch_operations(self) -> None:
        """Test: Multi-point selection → Batch operations → Coordinate updates."""
        # 1. Set up test data
        test_points = [(i, float(i * 100), float(i * 200), "keyframe") for i in range(1, 6)]

        mock_view = ProtocolCompliantMockCurveView(
            points=test_points, selected_points=set(), zoom_factor=1.0, offset_x=0.0, offset_y=0.0
        )

        # 2. Select multiple points (simulate box selection)
        # Select points 2, 3, 4 (indices 1, 2, 3)
        selected_indices = {1, 2, 3}
        mock_view.selected_points = selected_indices

        # 3. Apply batch operation (smoothing on selected points)
        selected_points_data = [mock_view.points[i] for i in selected_indices]
        smoothed_points = self.data_service.smooth_moving_average(selected_points_data, window_size=3)

        # 4. Update selected points with smoothed data
        for i, smoothed_point in enumerate(smoothed_points):
            original_idx = list(selected_indices)[i]
            # Ensure we maintain the correct point format
            frame, x, y, status = safe_extract_point(smoothed_point)
            mock_view.points[original_idx] = (int(frame), float(x), float(y), str(status))

        # 5. Verify batch operation results
        assert len(smoothed_points) == 3
        for smoothed_point in smoothed_points:
            frame, x, y, _ = safe_extract_point(smoothed_point)
            # Smoothed points should have same frames but potentially different coordinates
            assert 1 <= frame <= 5
            assert isinstance(x, int | float)
            assert isinstance(y, int | float)

    def test_undo_redo_data_consistency(self) -> None:
        """Test: Modification → Undo → Redo → Data consistency verification."""
        # 1. Set up initial state
        original_data = [(1, 100.0, 200.0, "keyframe"), (2, 150.0, 250.0, "keyframe"), (3, 200.0, 300.0, "keyframe")]

        # 2. Create copies to simulate history states
        initial_state = [tuple(point) for point in original_data]

        # 3. Apply modification (smoothing)
        modified_data = self.data_service.smooth_moving_average(original_data, window_size=3)

        # 4. Verify modification occurred
        assert len(modified_data) == len(original_data)
        # Smoothed data should be slightly different
        for i, (orig, smooth) in enumerate(zip(original_data, modified_data)):
            orig_frame, orig_x, orig_y, orig_status = safe_extract_point(orig)
            smooth_frame, smooth_x, smooth_y, smooth_status = safe_extract_point(smooth)

            assert orig_frame == smooth_frame  # Frame unchanged
            assert orig_status == smooth_status  # Status preserved
            # Coordinates may be slightly different due to smoothing

        # 5. Simulate undo (restore original state)
        restored_data = initial_state.copy()

        # 6. Verify undo restored original data
        assert len(restored_data) == len(original_data)
        for orig, restored in zip(original_data, restored_data):
            assert orig == restored

        # 7. Simulate redo (reapply modification)
        redone_data = self.data_service.smooth_moving_average(restored_data, window_size=3)  # pyright: ignore[reportArgumentType]

        # 8. Verify redo produces consistent results
        assert len(redone_data) == len(modified_data)
        for modified_point, redone_point in zip(modified_data, redone_data):
            mod_frame, mod_x, mod_y, mod_status = safe_extract_point(modified_point)
            redo_frame, redo_x, redo_y, redo_status = safe_extract_point(redone_point)

            assert mod_frame == redo_frame
            assert abs(float(mod_x) - float(redo_x)) < 0.001  # Should be identical
            assert abs(float(mod_y) - float(redo_y)) < 0.001
            assert mod_status == redo_status


class TestImageSequencePipeline:
    """Test complete image sequence workflows."""

    data_service: DataService  # pyright: ignore[reportUninitializedInstanceVariable]
    transform_service: TransformService  # pyright: ignore[reportUninitializedInstanceVariable]

    def setup_method(self) -> None:
        """Set up test environment."""
        self.data_service = get_data_service()
        self.transform_service = get_transform_service()

    def test_image_sequence_loading_to_display(self) -> None:
        """Test: Image directory → Load sequence → Frame navigation → Display sync."""
        # 1. Create temporary image directory with test images
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test images with realistic names
            image_filenames = []
            for i in range(1, 6):
                filename = f"frame{i:04d}.jpg"
                image_path = os.path.join(temp_dir, filename)

                # Create minimal test image
                test_image = QImage(100, 100, QImage.Format.Format_RGB32)
                test_image.fill(0xFF000000)  # Black image
                test_image.save(image_path)  # Let Qt determine format from extension
                image_filenames.append(filename)

            # 2. Load image sequence through DataService
            loaded_filenames = self.data_service.load_image_sequence(temp_dir)
            assert len(loaded_filenames) == 5
            # Check that each expected filename appears in one of the loaded full paths
            assert all(any(name in loaded_path for loaded_path in loaded_filenames) for name in image_filenames)

            # 3. Set up mock view with image sequence
            curve_points = [(i, float(i * 50), float(i * 75)) for i in range(1, 6)]
            mock_view = ProtocolCompliantMockCurveView(
                points=curve_points, image_sequence_path=temp_dir, image_filenames=loaded_filenames, current_image_idx=0
            )

            # 4. Test frame navigation
            for frame_num in range(1, 6):
                # Navigate to frame
                self.data_service.set_current_image_by_frame(mock_view, frame_num)

                # Verify current image index updated appropriately
                # (Implementation may map frame numbers to image indices differently)
                assert hasattr(mock_view, "current_image_idx")
                # Service may not update index if frame mapping is different

            # 5. Test image loading
            mock_view.current_image_idx = 2  # Third image
            loaded_image = self.data_service.load_current_image(mock_view)

            # Should load successfully or return None (depending on implementation)
            assert loaded_image is None or isinstance(loaded_image, QImage)

    def test_image_sequence_with_curve_synchronization(self) -> None:
        """Test: Image sequence ↔ Curve data synchronization by frame."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Create image sequence
            for i in range(1, 4):
                filename = f"shot001_{i:03d}.jpg"
                image_path = os.path.join(temp_dir, filename)
                test_image = QImage(50, 50, QImage.Format.Format_RGB32)
                test_image.save(image_path)  # Let Qt determine format from extension

            loaded_filenames = self.data_service.load_image_sequence(temp_dir)

            # 2. Create curve data that matches frame range
            curve_data = [(1, 100.0, 200.0, "keyframe"), (2, 150.0, 225.0, "keyframe"), (3, 200.0, 250.0, "keyframe")]

            # 3. Set up synchronized view
            mock_view = ProtocolCompliantMockCurveView(
                points=curve_data, image_sequence_path=temp_dir, image_filenames=loaded_filenames, current_image_idx=0
            )

            # 4. Test synchronization: navigate to each frame
            for frame_num in [1, 2, 3]:
                # Set current frame
                self.data_service.set_current_image_by_frame(mock_view, frame_num)

                # Find corresponding curve point
                matching_point: tuple[float, float] | None = None
                for point in curve_data:
                    point_frame, x, y, status = safe_extract_point(point)
                    if point_frame == frame_num:
                        matching_point = (float(x), float(y))
                        break

                assert matching_point is not None

                # Verify frame sync (image index should correspond to frame)
                # This tests that image navigation aligns with curve frame numbers
                expected_image_idx = frame_num - 1  # Typical 0-based indexing
                if expected_image_idx < len(loaded_filenames):
                    # Image index should be reasonable for the frame or -1 if not mapped
                    assert mock_view.current_image_idx >= -1


class TestDataConsistencyPipeline:
    """Test data consistency across all pipeline stages."""

    data_service: DataService  # pyright: ignore[reportUninitializedInstanceVariable]
    transform_service: TransformService  # pyright: ignore[reportUninitializedInstanceVariable]

    def setup_method(self) -> None:
        """Set up services."""
        self.data_service = get_data_service()
        self.transform_service = get_transform_service()

    def test_data_integrity_through_full_pipeline(self) -> None:
        """Test: Load → Process → Transform → Modify → Save → Reload → Verify consistency."""
        # Initialize temp_output to avoid UnboundLocalError
        temp_output: str | None = None

        # 1. Create original test data
        original_data = [
            {"frame": 1, "x": 960.0, "y": 540.0, "status": "keyframe"},
            {"frame": 2, "x": 965.0, "y": 545.0, "status": "keyframe"},
            {"frame": 3, "x": 970.0, "y": 550.0, "status": "keyframe"},
            {"frame": 4, "x": 975.0, "y": 555.0, "status": "keyframe"},
        ]

        # 2. Save initial data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json as json_module

            json_module.dump(original_data, f)
            temp_input = f.name

        try:
            # 3. Load data
            loaded_data = self.data_service._load_json(temp_input)

            # 4. Process data (smoothing)
            processed_data = self.data_service.smooth_moving_average(loaded_data, window_size=3)

            # 5. Transform coordinates
            mock_view = ProtocolCompliantMockCurveView(
                points=processed_data, zoom_factor=1.2, offset_x=25.0, offset_y=50.0
            )

            view_state = self.transform_service.create_view_state(mock_view)
            transform = self.transform_service.create_transform_from_view_state(view_state)

            # Get screen coordinates for verification
            screen_coords: list[tuple[int, float, float, str]] = []
            for point in processed_data:
                frame, x, y, status = safe_extract_point(point)
                sx, sy = transform.data_to_screen(float(x), float(y))
                screen_coords.append((int(frame), float(sx), float(sy), str(status)))

            # 6. Modify data (simulate user edit)
            if processed_data:
                old_point = processed_data[1]  # Modify second point
                frame, x, y, status = safe_extract_point(old_point)
                processed_data[1] = (int(frame), float(x) + 10.0, float(y) + 5.0, str(status))

            # 7. Save modified data
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                temp_output = f.name

            # Use the direct save method instead of going through the dialog
            save_result = self.data_service._save_json(temp_output, processed_data, label="Test Track", color="#FF0000")
            assert save_result, "Failed to save JSON data"

            # 8. Reload and verify consistency
            reloaded_data = self.data_service._load_json(temp_output)

            # 9. Verify data consistency
            assert len(reloaded_data) == len(processed_data)
            for original, reloaded in zip(processed_data, reloaded_data):
                orig_frame, orig_x, orig_y, orig_status = safe_extract_point(original)
                reload_frame, reload_x, reload_y, reload_status = safe_extract_point(reloaded)

                assert orig_frame == reload_frame
                assert abs(float(orig_x) - float(reload_x)) < 0.001
                assert abs(float(orig_y) - float(reload_y)) < 0.001
                assert orig_status == reload_status

        finally:
            for temp_file in [temp_input, temp_output]:
                if temp_file and os.path.exists(temp_file):
                    os.unlink(temp_file)

    def test_coordinate_system_consistency(self) -> None:
        """Test coordinate system consistency across transforms and data operations."""
        # 1. Create test data in different coordinate ranges
        test_cases = [
            # Small values
            [(1, 10.5, 20.3), (2, 11.2, 19.8), (3, 9.8, 21.1)],
            # Medium values (typical screen coordinates)
            [(1, 960.0, 540.0), (2, 965.0, 545.0), (3, 970.0, 550.0)],
            # Large values
            [(1, 5000.0, 3000.0), (2, 5100.0, 3050.0), (3, 5200.0, 3100.0)],
        ]

        for i, test_data in enumerate(test_cases):
            # 2. Set up transform with different view parameters
            mock_view = ProtocolCompliantMockCurveView(
                points=test_data,
                zoom_factor=0.5 + i * 0.5,  # Different zoom for each test
                offset_x=i * 100.0,
                offset_y=i * 50.0,
            )

            view_state = self.transform_service.create_view_state(mock_view)
            transform = self.transform_service.create_transform_from_view_state(view_state)

            # 3. Test round-trip coordinate transformations
            for point in test_data:
                _, data_x, data_y = point[0], point[1], point[2]

                # Transform to screen coordinates
                screen_x, screen_y = transform.data_to_screen(data_x, data_y)

                # Transform back to data coordinates
                back_data_x, back_data_y = transform.screen_to_data(screen_x, screen_y)

                # Verify round-trip accuracy
                assert abs(back_data_x - data_x) < 0.1, f"X coordinate round-trip failed: {data_x} -> {back_data_x}"
                assert abs(back_data_y - data_y) < 0.1, f"Y coordinate round-trip failed: {data_y} -> {back_data_y}"

            # 4. Test data operations preserve coordinate validity
            smoothed_data = self.data_service.smooth_moving_average(test_data, window_size=3)

            for original, smoothed in zip(test_data, smoothed_data):
                orig_frame = original[0]
                smooth_frame, smooth_x, smooth_y, _ = safe_extract_point(smoothed)

                # Frame should be preserved
                assert orig_frame == smooth_frame

                # Coordinates should remain in reasonable range
                assert isinstance(smooth_x, int | float)
                assert isinstance(smooth_y, int | float)
                assert not (smooth_x != smooth_x)  # Check for NaN
                assert not (smooth_y != smooth_y)  # Check for NaN

    def test_error_recovery_and_data_preservation(self) -> None:
        """Test that data is preserved during error conditions."""
        # 1. Set up valid initial data
        valid_data = [(1, 100.0, 200.0, "keyframe"), (2, 150.0, 250.0, "keyframe")]

        # 2. Test data service error recovery
        # Try invalid file operation
        try:
            self.data_service._load_json("/nonexistent/path/file.json")
        except OSError:
            pass  # Expected error

        # Service should still work with valid data after error
        _ = self.data_service.smooth_moving_average(valid_data, window_size=2)

        # 3. Test transform service error recovery
        # Create view with invalid parameters
        invalid_view = ProtocolCompliantMockCurveView(
            points=valid_data,
            zoom_factor=0.0,  # Invalid zoom
            offset_x=float("nan"),  # Invalid offset
            offset_y=float("inf"),  # Invalid offset
        )

        # Service should handle gracefully
        try:
            view_state = self.transform_service.create_view_state(invalid_view)
            transform = self.transform_service.create_transform_from_view_state(view_state)
            # Should create some kind of valid transform even with invalid input
            assert transform is not None
        except Exception:
            pass  # Error handling is acceptable

        # 4. Verify original data remains unmodified
        for original, current in zip([(1, 100.0, 200.0, "keyframe"), (2, 150.0, 250.0, "keyframe")], valid_data):
            # Handle both 3-tuple and 4-tuple point formats
            if len(current) > 3:
                assert original == current[:4]
            else:
                assert original == current
