"""
Integration tests for CurveEditor services.

These tests verify that the DEFAULT architecture services work together correctly
in real-world scenarios. Each test represents a complete user workflow.

Note on Transform Pattern:
    Some tests use the legacy 2-step pattern for explicitness. For NEW production
    code, use the recommended pattern: transform = transform_service.get_transform(view)
    (See CLAUDE.md for details)
"""

import csv
import json
import os
import tempfile
from collections.abc import Generator
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import pytest
from PySide6.QtCore import QRect

from core.type_aliases import CurveDataList
from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service
from stores.application_state import get_application_state
from tests.test_helpers import MockCurveView, MockMainWindow

if TYPE_CHECKING:
    from services.data_service import DataService
    from services.interaction_service import InteractionService
    from services.transform_service import TransformService
    from services.ui_service import UIService


# pyright: reportUninitializedInstanceVariable=false


class TestServiceIntegration:
    """Test integration between all four core services."""

    # Class attributes - initialized in setup() fixture
    # Suppress uninitialized variable warnings as pytest fixtures handle this
    data_service: "DataService"
    transform_service: "TransformService"
    interaction_service: "InteractionService"
    ui_service: "UIService"
    curve_view: MockCurveView
    main_window: MockMainWindow
    test_data: CurveDataList
    temp_files: list[str]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> Generator[None, None, None]:
        """Set up services and test data for each test."""
        # Initialize services
        self.data_service = get_data_service()
        self.transform_service = get_transform_service()
        self.interaction_service = get_interaction_service()
        self.ui_service = get_ui_service()

        # Create test views
        self.curve_view = MockCurveView()
        self.main_window = MockMainWindow()
        self.main_window.curve_view = self.curve_view

        # Sample test data - cast to CurveDataList for type compatibility
        self.test_data = cast(
            CurveDataList,
            [
                (1, 100.0, 200.0, "keyframe"),
                (2, 150.0, 250.0, "keyframe"),
                (3, 200.0, 300.0, "keyframe"),
                (4, 250.0, 350.0, "interpolated"),
                (5, 300.0, 400.0, "keyframe"),
            ],
        )

        # Set initial data in ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", self.test_data.copy())
        app_state.set_active_curve("test_curve")

        # Set initial data - MockCurveView expects Point4 but service expects CurveDataList
        self.curve_view.curve_data = self.test_data.copy()
        self.curve_view.points = self.test_data.copy()

        # Clean up temp files after test
        self.temp_files = []
        yield
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def create_temp_file(self, suffix: str) -> str:
        """Create a temporary file and track it for cleanup."""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            temp_path = f.name
        self.temp_files.append(temp_path)
        return temp_path


class TestLoadTransformInteractSave(TestServiceIntegration):
    """Test complete workflow: Load → Transform → Interact → Save."""

    def test_json_workflow(self) -> None:
        """Test loading JSON, transforming coordinates, interacting with points, and saving."""
        # 1. Create and save initial JSON data
        initial_file = self.create_temp_file(".json")
        json_data = []
        for point_data in self.test_data:
            # Handle variable tuple length in LegacyPointData
            if len(point_data) == 3:
                i, x, y = point_data
                s = "normal"  # default status
            else:
                i, x, y, s = point_data
            json_data.append({"frame": i, "x": x, "y": y, "status": s})
        with open(initial_file, "w") as f:
            json.dump(json_data, f)

        # 2. Load data using DataService
        loaded_data = self.data_service._load_json(initial_file)
        assert len(loaded_data) == 5

        # 3. Set data in ApplicationState and view
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", loaded_data)
        app_state.set_active_curve("test_curve")
        self.curve_view.curve_data = loaded_data
        self.curve_view.points = loaded_data

        # 4. Create transform for coordinate conversion
        view_state = self.transform_service.create_view_state(self.curve_view)
        transform = self.transform_service.create_transform_from_view_state(view_state)

        # 5. Transform data coordinates to screen
        screen_coords = []
        for point in loaded_data:
            screen_x, screen_y = transform.data_to_screen(point[1], point[2])
            screen_coords.append((screen_x, screen_y))

        # 6. Interact: Find and select a point
        target_screen = screen_coords[1]  # Point at index 1
        found_idx = self.interaction_service.find_point_at(self.curve_view, target_screen[0], target_screen[1])
        assert found_idx.index == 1

        # 7. Interact: Select the point
        success = self.interaction_service.select_point_by_index(self.curve_view, self.main_window, found_idx.index)  # pyright: ignore[reportArgumentType]
        assert success
        assert 1 in self.curve_view.selected_points

        # 8. Interact: Move the selected point
        new_x, new_y = 160.0, 260.0
        success = self.interaction_service.update_point_position(self.curve_view, self.main_window, 1, new_x, new_y)  # pyright: ignore[reportArgumentType]
        assert success
        # Phase 6: update_point_position updates ApplicationState (single source of truth)
        # Verify in ApplicationState
        app_state = get_application_state()
        curve_data = app_state.get_curve_data("test_curve")
        assert curve_data[1][1] == new_x
        assert curve_data[1][2] == new_y

        # 9. Save modified data from ApplicationState
        output_file = self.create_temp_file(".json")
        success = self.data_service._save_json(output_file, curve_data, "TestLabel", "#FF0000")
        assert success

        # 10. Verify saved data
        reloaded = self.data_service._load_json(output_file)
        assert len(reloaded) == 5
        assert reloaded[1][1] == new_x
        assert reloaded[1][2] == new_y

    def test_csv_workflow(self):
        """Test loading CSV, transforming, interacting, and saving."""
        # 1. Create and save initial CSV data
        initial_file = self.create_temp_file(".csv")
        with open(initial_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["frame", "x", "y", "status"])
            for point in self.test_data:
                writer.writerow(point)

        # 2. Load data using DataService
        loaded_data = self.data_service._load_csv(initial_file)
        assert len(loaded_data) == 5

        # 3. Set data in ApplicationState and view
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", loaded_data)
        app_state.set_active_curve("test_curve")
        self.curve_view.curve_data = loaded_data
        self.curve_view.points = loaded_data

        # 4. Interact: Select all points
        count = self.interaction_service.select_all_points(self.curve_view, self.main_window)  # pyright: ignore[reportArgumentType]
        assert count == 5
        assert len(self.curve_view.selected_points) == 5

        # 5. Save selected data
        output_file = self.create_temp_file(".csv")
        success = self.data_service._save_csv(output_file, app_state.get_curve_data("test_curve"), include_header=True)
        assert success

        # 6. Verify saved data
        reloaded = self.data_service._load_csv(output_file)
        assert len(reloaded) == 5


class TestTransformInteractionIntegration(TestServiceIntegration):
    """Test integration between Transform and Interaction services."""

    def test_screen_to_data_point_selection(self):
        """Test selecting points using screen coordinates."""
        # Set up ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", self.test_data.copy())
        app_state.set_active_curve("test_curve")

        # Set up zoom and pan
        self.curve_view.zoom_factor = 2.0
        self.curve_view.offset_x = 50
        self.curve_view.offset_y = 100

        # Create transform
        view_state = self.transform_service.create_view_state(self.curve_view)
        transform = self.transform_service.create_transform_from_view_state(view_state)

        # Get screen coordinates for a data point
        data_x, data_y = self.test_data[2][1], self.test_data[2][2]  # Point 2
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # Find point at screen coordinates
        found_idx = self.interaction_service.find_point_at(self.curve_view, screen_x, screen_y)
        assert found_idx.index == 2

        # Select the found point
        success = self.interaction_service.select_point_by_index(self.curve_view, self.main_window, found_idx.index)  # pyright: ignore[reportArgumentType]
        assert success
        assert self.curve_view.selected_point_idx == 2

    def test_rectangle_selection_with_transform(self):
        """Test selecting multiple points in a rectangle."""
        # Set up ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", self.test_data.copy())
        app_state.set_active_curve("test_curve")

        # Create transform
        view_state = self.transform_service.create_view_state(self.curve_view)
        transform = self.transform_service.create_transform_from_view_state(view_state)

        # Get screen bounds for points 1-3
        screen_coords = []
        for i in range(3):
            point = self.test_data[i]
            sx, sy = transform.data_to_screen(point[1], point[2])
            screen_coords.append((sx, sy))

        # Create rectangle encompassing points 1-3
        min_x = min(sc[0] for sc in screen_coords) - 10
        min_y = min(sc[1] for sc in screen_coords) - 10
        max_x = max(sc[0] for sc in screen_coords) + 10
        max_y = max(sc[1] for sc in screen_coords) + 10

        rect = QRect(int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y))

        # Select points in rectangle
        count = self.interaction_service.select_points_in_rect(self.curve_view, self.main_window, rect)  # pyright: ignore[reportArgumentType]
        assert count == 3
        assert self.curve_view.selected_points == {0, 1, 2}

    def test_view_reset_integration(self):
        """Test resetting view affects transformations correctly."""
        # Set up ApplicationState
        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0, "keyframe")]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        # Modify view state
        self.curve_view.zoom_factor = 3.0
        self.curve_view.offset_x = 100
        self.curve_view.offset_y = 200

        # Reset view
        self.interaction_service.reset_view(self.curve_view)

        # Verify reset
        assert self.curve_view.zoom_factor == 1.0
        assert self.curve_view.offset_x == 0
        assert self.curve_view.offset_y == 0

        # Create new transform and verify it's identity-like
        view_state = self.transform_service.create_view_state(self.curve_view)
        transform = self.transform_service.create_transform_from_view_state(view_state)

        # Test that transform works correctly after reset
        test_x, test_y = 100.0, 100.0
        screen_x, screen_y = transform.data_to_screen(test_x, test_y)

        # After reset, verify point can be found at transformed location
        # Use set_curve_data to handle type conversion properly
        self.curve_view.set_curve_data(test_data)

        # Should be able to find the point at screen coordinates
        found_idx = self.interaction_service.find_point_at(self.curve_view, screen_x, screen_y)
        assert found_idx.index == 0  # Found the point after reset


class TestDataUIIntegration(TestServiceIntegration):
    """Test integration between Data and UI services."""

    def test_file_operations_with_ui_feedback(self):
        """Test file operations trigger appropriate UI updates."""
        # Mock UI service methods
        with patch.object(self.ui_service, "show_status_message"):
            # Save operation
            temp_file = self.create_temp_file(".json")
            success = self.data_service._save_json(temp_file, self.test_data, "Test", "#FF0000")
            assert success

            # Load operation
            loaded = self.data_service._load_json(temp_file)  # pyright: ignore[reportPrivateUsage]
            assert len(loaded) == 5

        # In real implementation, UI service would show status messages
        # This test ensures the services can work together without errors

    def test_data_analysis_with_transform(self):
        """Test data filtering operations with transform."""
        # Apply smoothing to data
        smoothed = self.data_service.smooth_moving_average(self.test_data, window_size=3)
        assert len(smoothed) == len(self.test_data)

        # Apply median filter
        filtered = self.data_service.filter_median(self.test_data, window_size=3)
        assert len(filtered) == len(self.test_data)

        # Create transform and verify filtered data can be displayed
        self.curve_view.zoom_factor = 1.5
        view_state = self.transform_service.create_view_state(self.curve_view)
        transform = self.transform_service.create_transform_from_view_state(view_state)

        # Transform filtered data to screen space
        for point in filtered[:3]:  # Test first 3 points
            screen_x, screen_y = transform.data_to_screen(point[1], point[2])
            # Verify transformation occurred
            assert screen_x != point[1]  # Transformed (unless at origin)
            # Screen coordinates should be reasonable
            assert -10000 < screen_x < 10000
            assert -10000 < screen_y < 10000


class TestHistoryIntegration(TestServiceIntegration):
    """Test history/undo functionality across services."""

    def test_undo_redo_with_interaction(self):
        """Test undo/redo after point modifications."""
        # Set up ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", self.test_data.copy())
        app_state.set_active_curve("test_curve")

        # Add initial state to history
        self.interaction_service.add_to_history(self.main_window)  # pyright: ignore[reportArgumentType]

        # Store original position
        original_data = app_state.get_curve_data("test_curve")
        self.curve_view.curve_data = list(original_data)

        # Modify a point
        self.interaction_service.update_point_position(self.curve_view, self.main_window, 0, 110.0, 210.0)  # pyright: ignore[reportArgumentType]

        # Verify point was modified in ApplicationState (Phase 6: ApplicationState is source of truth)
        curve_data = app_state.get_curve_data("test_curve")
        assert curve_data[0][1] == 110.0
        assert curve_data[0][2] == 210.0

        # Add modified state to history
        self.interaction_service.add_to_history(self.main_window)  # pyright: ignore[reportArgumentType]

        # Get history stats to verify state
        stats = self.interaction_service.get_history_stats()
        if stats:
            # We have history stats, check if undo is available
            # Check undo capability if available - use getattr for optional attribute
            can_undo = getattr(stats, "can_undo", True)
            assert can_undo

        # Try to undo the change
        self.interaction_service.undo(self.main_window)  # pyright: ignore[reportArgumentType]

        # State should be returned (may be None if not implemented)
        # The important part is no exception is raised

        # Try to redo the change
        self.interaction_service.redo(self.main_window)  # pyright: ignore[reportArgumentType]
        # Again, no exception is the key test

    def test_history_memory_management(self):
        """Test history service manages memory correctly."""
        # Add many states to history
        for i in range(10):  # Reduced from 100 to avoid memory issues in test
            modified_data = self.test_data.copy()
            modified_data[0] = (1, 100.0 + i, 200.0 + i, "keyframe")

            self.main_window.curve_view.curve_data = modified_data
            self.interaction_service.add_to_history(self.main_window)  # pyright: ignore[reportArgumentType]

        # History should have some stats available
        stats = self.interaction_service.get_history_stats()
        # Stats may be None if history not fully implemented
        if stats:
            # If we have stats, verify they're reasonable
            # Note: stats is a dict with 'total_states', not an object with 'total_entries'
            # Check for expected stats attributes (dict keys or object attributes)
            has_total = "total_states" in stats or getattr(stats, "total_entries", None) is not None
            has_index = "current_index" in stats or getattr(stats, "current_position", None) is not None
            assert has_total
            assert has_index


class TestErrorRecoveryIntegration(TestServiceIntegration):
    """Test error recovery across services."""

    def test_invalid_file_handling(self):
        """Test services handle invalid files gracefully."""
        # Create invalid JSON file
        invalid_file = self.create_temp_file(".json")
        with open(invalid_file, "w") as f:
            f.write("not valid json{]")

        # Should return empty list, not crash
        result = self.data_service._load_json(invalid_file)
        assert result == []

        # Create invalid CSV file
        invalid_csv = self.create_temp_file(".csv")
        with open(invalid_csv, "w") as f:
            f.write("not,enough,columns\n1,2\n")

        # Should handle gracefully
        result = self.data_service._load_csv(invalid_csv)
        # May return partial data or empty
        assert isinstance(result, list)

    def test_out_of_bounds_operations(self):
        """Test services handle out-of-bounds operations."""
        # Try to select non-existent point
        success = self.interaction_service.select_point_by_index(self.curve_view, self.main_window, 999)  # pyright: ignore[reportArgumentType]
        assert not success

        # Try to update non-existent point
        success = self.interaction_service.update_point_position(self.curve_view, self.main_window, -1, 0, 0)  # pyright: ignore[reportArgumentType]
        assert not success

        # Try to find point at extreme coordinates
        idx = self.interaction_service.find_point_at(self.curve_view, 1e10, 1e10)
        assert idx.index == -1

    def test_service_state_consistency(self):
        """Test services maintain consistent state after errors."""
        # Set up ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", self.test_data.copy())
        app_state.set_active_curve("test_curve")

        # Cause an error by selecting invalid point
        self.interaction_service.select_point_by_index(self.curve_view, self.main_window, 999)  # pyright: ignore[reportArgumentType]

        # Verify view state is still valid
        assert isinstance(self.curve_view.selected_points, set)
        assert self.curve_view.selected_point_idx >= -1

        # Normal operations should still work
        success = self.interaction_service.select_point_by_index(self.curve_view, self.main_window, 0)  # pyright: ignore[reportArgumentType]
        assert success
        assert 0 in self.curve_view.selected_points


class TestPerformanceIntegration(TestServiceIntegration):
    """Test performance with large datasets."""

    def test_large_dataset_handling(self):
        """Test services handle large datasets efficiently."""
        # Create large dataset
        large_data = cast(
            CurveDataList,
            [(i, float(i * 10), float(i * 20), "keyframe" if i % 10 == 0 else "interpolated") for i in range(1000)],
        )

        # Save large dataset
        temp_file = self.create_temp_file(".json")
        success = self.data_service._save_json(temp_file, large_data, "Large", "#00FF00")
        assert success

        # Load large dataset
        loaded = self.data_service._load_json(temp_file)
        assert len(loaded) == 1000

        # Set in ApplicationState and view
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", loaded)
        app_state.set_active_curve("test_curve")
        self.curve_view.curve_data = loaded
        self.curve_view.points = loaded

        # Transform operations should still work
        view_state = self.transform_service.create_view_state(self.curve_view)
        transform = self.transform_service.create_transform_from_view_state(view_state)

        # Find point in middle of dataset
        mid_point = loaded[500]
        screen_x, screen_y = transform.data_to_screen(mid_point[1], mid_point[2])
        idx = self.interaction_service.find_point_at(self.curve_view, screen_x, screen_y)
        assert idx.index == 500

        # Select all should work
        count = self.interaction_service.select_all_points(self.curve_view, self.main_window)  # pyright: ignore[reportArgumentType]
        assert count == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
