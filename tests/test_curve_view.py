#!/usr/bin/env python3
"""
Updated tests for CurveViewWidget.

This test suite provides coverage of the new CurveViewWidget class that replaces
the old CurveView. Tests are organized by functional areas to match the new
widget's capabilities.

Test Categories:
- Initialization and basic setup
- Point data management (set_curve_data, selection, data retrieval)
- View state management (zoom, pan, flip, scale)
- Coordinate transformations
- Visual rendering options
"""

import os
import sys
from unittest.mock import Mock

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QWidget

from tests.test_helpers import MockCurveView, MockDataBuilder, PointsList
from ui.curve_view_widget import CurveViewWidget


class TestCurveViewWidgetInitialization:
    """Test CurveViewWidget initialization and basic setup."""

    def test_initialization_creates_widget(self, curve_view_widget: CurveViewWidget) -> None:
        """Test that CurveViewWidget initializes as a QWidget."""
        assert isinstance(curve_view_widget, QWidget)
        assert curve_view_widget is not None

    def test_default_attributes(self, curve_view_widget: CurveViewWidget) -> None:
        """Test that CurveViewWidget has expected default attributes."""
        # View state attributes
        assert curve_view_widget.zoom_factor == 1.0
        assert curve_view_widget.pan_offset_x == 0.0
        assert curve_view_widget.pan_offset_y == 0.0
        assert curve_view_widget.manual_offset_x == 0.0
        assert curve_view_widget.manual_offset_y == 0.0
        assert curve_view_widget.flip_y_axis is False
        assert curve_view_widget.scale_to_image is True

        # Display options
        assert curve_view_widget.show_grid is False
        assert curve_view_widget.show_points is True
        assert curve_view_widget.show_lines is True
        assert curve_view_widget.show_velocity_vectors is False
        assert curve_view_widget.show_all_frame_numbers is False
        assert curve_view_widget.show_background is True

        # Point management
        assert isinstance(curve_view_widget.selected_indices, set)
        assert len(curve_view_widget.selected_indices) == 0
        assert isinstance(curve_view_widget.curve_data, list)
        assert len(curve_view_widget.curve_data) == 0

    def test_initial_dimensions(self, curve_view_widget: CurveViewWidget) -> None:
        """Test initial dimensions and image properties."""
        assert curve_view_widget.image_width == 1920
        assert curve_view_widget.image_height == 1080
        assert curve_view_widget.background_image is None

    def test_rendering_settings(self, curve_view_widget: CurveViewWidget) -> None:
        """Test that rendering settings are properly initialized."""
        assert curve_view_widget.point_radius == 5
        assert curve_view_widget.selected_point_radius == 7
        assert curve_view_widget.line_width == 2
        assert curve_view_widget.selected_line_width == 3


class TestPointDataManagement:
    """Test point data management functionality."""

    def test_set_curve_data_basic(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test basic set_curve_data functionality."""
        curve_view_widget.set_curve_data(sample_points)

        assert len(curve_view_widget.curve_data) == 3
        assert curve_view_widget.curve_data[0] == (1, 100.0, 200.0)
        assert curve_view_widget.curve_data[1] == (2, 150.0, 250.0)
        assert curve_view_widget.curve_data[2] == (3, 200.0, 300.0)

    def test_add_point(self, curve_view_widget: CurveViewWidget) -> None:
        """Test adding a single point."""
        # Clear any existing data first
        curve_view_widget._curve_store.clear()

        point = (1, 100.0, 200.0, "keyframe")
        curve_view_widget.add_point(point)

        assert len(curve_view_widget.curve_data) == 1
        assert curve_view_widget.curve_data[0][:3] == point[:3]  # Compare frame, x, y

    def test_update_point(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test updating a point's coordinates."""
        curve_view_widget.set_curve_data(sample_points)

        curve_view_widget.update_point(0, 150.0, 250.0)

        # Check that point was updated
        assert curve_view_widget.curve_data[0][1] == 150.0  # X coordinate
        assert curve_view_widget.curve_data[0][2] == 250.0  # Y coordinate

    def test_remove_point(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test removing a point."""
        curve_view_widget.set_curve_data(sample_points)
        original_length = len(curve_view_widget.curve_data)

        curve_view_widget.remove_point(1)

        assert len(curve_view_widget.curve_data) == original_length - 1

    def test_get_selected_indices(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test getting selected indices."""
        curve_view_widget.set_curve_data(sample_points)
        # Use store methods to set selection
        curve_view_widget._curve_store.select(0)
        curve_view_widget._curve_store.select(2, add_to_selection=True)

        selected = curve_view_widget.get_selected_indices()
        assert set(selected) == {0, 2}

    def test_selection_operations(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test point selection operations."""
        curve_view_widget.set_curve_data(sample_points)

        # Test internal selection methods
        curve_view_widget._select_point(1)
        assert 1 in curve_view_widget.selected_indices

        curve_view_widget.clear_selection()
        assert len(curve_view_widget.selected_indices) == 0

        curve_view_widget.select_all()
        assert len(curve_view_widget.selected_indices) == len(sample_points)


class TestViewStateManagement:
    """Test view state management (zoom, pan, flip, scale)."""

    def test_zoom_operations(self, curve_view_widget: CurveViewWidget) -> None:
        """Test zoom functionality."""
        initial_zoom = curve_view_widget.zoom_factor
        curve_view_widget.zoom_factor = 2.0
        assert curve_view_widget.zoom_factor == 2.0
        assert curve_view_widget.zoom_factor != initial_zoom

    def test_pan_operations(self, curve_view_widget: CurveViewWidget) -> None:
        """Test pan functionality."""
        curve_view_widget.pan_offset_x = 100.0
        curve_view_widget.pan_offset_y = 50.0

        assert curve_view_widget.pan_offset_x == 100.0
        assert curve_view_widget.pan_offset_y == 50.0

    def test_reset_view(self, curve_view_widget: CurveViewWidget) -> None:
        """Test resetting view to defaults."""
        # Modify view state
        curve_view_widget.zoom_factor = 2.0
        curve_view_widget.pan_offset_x = 100.0
        curve_view_widget.pan_offset_y = 50.0

        curve_view_widget.reset_view()

        assert curve_view_widget.zoom_factor == 1.0
        assert curve_view_widget.pan_offset_x == 0.0
        assert curve_view_widget.pan_offset_y == 0.0

    def test_fit_to_view(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test fit to view functionality."""
        curve_view_widget.set_curve_data(sample_points)

        # Should not raise exceptions
        curve_view_widget.fit_to_view()
        assert True

    def test_center_on_selection(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test centering on selected points."""
        curve_view_widget.set_curve_data(sample_points)
        # Use store methods to set selection
        curve_view_widget._curve_store.select(0)
        curve_view_widget._curve_store.select(1, add_to_selection=True)

        # Should not raise exceptions
        curve_view_widget.center_on_selection()
        assert True

    def test_center_on_frame(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test centering on a specific frame."""
        curve_view_widget.set_curve_data(sample_points)

        # Test centering on valid frame (1-based indexing)
        frame_to_center = 2  # Second point in sample_points
        initial_pan_x = curve_view_widget.pan_offset_x
        initial_pan_y = curve_view_widget.pan_offset_y

        # Center on frame
        curve_view_widget.center_on_frame(frame_to_center)

        # Pan offsets should change (view should move)
        assert curve_view_widget.pan_offset_x != initial_pan_x or curve_view_widget.pan_offset_y != initial_pan_y

        # Test with out-of-bounds frame (should not crash)
        curve_view_widget.center_on_frame(999)  # Invalid frame
        assert True  # Should not raise exceptions

        # Test with frame 0 (invalid, should not crash)
        curve_view_widget.center_on_frame(0)
        assert True

        # Test with negative frame (invalid, should not crash)
        curve_view_widget.center_on_frame(-1)
        assert True


class TestCoordinateTransformation:
    """Test coordinate transformation functionality."""

    def test_get_transform(self, curve_view_widget: CurveViewWidget) -> None:
        """Test getting transform object."""
        transform = curve_view_widget.get_transform()
        assert transform is not None
        # Transform should have required methods
        assert callable(getattr(transform, "data_to_screen", None)), "Transform should have data_to_screen method"
        assert callable(getattr(transform, "screen_to_data", None)), "Transform should have screen_to_data method"

    def test_data_to_screen_conversion(self, curve_view_widget: CurveViewWidget) -> None:
        """Test converting data coordinates to screen coordinates."""
        screen_pos = curve_view_widget.data_to_screen(100.0, 200.0)
        assert isinstance(screen_pos, QPointF)
        # Screen coordinates can be negative for points outside the viewport
        assert isinstance(screen_pos.x(), float)
        assert isinstance(screen_pos.y(), float)

    def test_screen_to_data_conversion(self, curve_view_widget: CurveViewWidget) -> None:
        """Test converting screen coordinates to data coordinates."""
        screen_pos = QPointF(100.0, 200.0)
        data_x, data_y = curve_view_widget.screen_to_data(screen_pos)
        assert isinstance(data_x, float)
        assert isinstance(data_y, float)

    def test_coordinate_roundtrip(self, curve_view_widget: CurveViewWidget) -> None:
        """Test that coordinate conversion is consistent."""
        original_x, original_y = 100.0, 200.0

        # Convert to screen and back
        screen_pos = curve_view_widget.data_to_screen(original_x, original_y)
        converted_x, converted_y = curve_view_widget.screen_to_data(screen_pos)

        # Should be approximately equal (allowing for floating point precision)
        assert abs(converted_x - original_x) < 0.1
        assert abs(converted_y - original_y) < 0.1


class TestVisualizationOptions:
    """Test visualization options and display settings."""

    def test_toggle_grid(self, curve_view_widget: CurveViewWidget) -> None:
        """Test toggling grid display."""
        initial_state = curve_view_widget.show_grid
        curve_view_widget.show_grid = not initial_state
        assert curve_view_widget.show_grid != initial_state

    def test_toggle_points(self, curve_view_widget: CurveViewWidget) -> None:
        """Test toggling point display."""
        initial_state = curve_view_widget.show_points
        curve_view_widget.show_points = not initial_state
        assert curve_view_widget.show_points != initial_state

    def test_toggle_lines(self, curve_view_widget: CurveViewWidget) -> None:
        """Test toggling line display."""
        initial_state = curve_view_widget.show_lines
        curve_view_widget.show_lines = not initial_state
        assert curve_view_widget.show_lines != initial_state

    def test_toggle_velocity_vectors(self, curve_view_widget: CurveViewWidget) -> None:
        """Test toggling velocity vectors."""
        curve_view_widget.show_velocity_vectors = True
        assert curve_view_widget.show_velocity_vectors is True

        curve_view_widget.show_velocity_vectors = False
        assert curve_view_widget.show_velocity_vectors is False

    def test_background_settings(self, curve_view_widget: CurveViewWidget) -> None:
        """Test background display settings."""
        curve_view_widget.show_background = False
        assert curve_view_widget.show_background is False

        curve_view_widget.background_opacity = 0.5
        assert curve_view_widget.background_opacity == 0.5


class TestInteractionHandling:
    """Test mouse and keyboard interaction handling."""

    def test_find_point_at(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test finding point at screen position."""
        curve_view_widget.set_curve_data(sample_points)

        # This tests the internal method
        pos = QPointF(100.0, 200.0)
        result = curve_view_widget._find_point_at(pos)

        # Should return -1 (no point found) or valid index
        assert isinstance(result, int)
        assert result >= -1

    def test_point_deletion(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test deleting selected points."""
        curve_view_widget.set_curve_data(sample_points)
        # Use store methods to set selection
        curve_view_widget._curve_store.select(0)
        curve_view_widget._curve_store.select(2, add_to_selection=True)
        original_length = len(curve_view_widget.curve_data)

        curve_view_widget.delete_selected_points()

        # Should have removed 2 points
        assert len(curve_view_widget.curve_data) == original_length - 2
        assert len(curve_view_widget.selected_indices) == 0

    def test_nudge_selected_points(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test nudging selected points."""
        curve_view_widget.set_curve_data(sample_points)
        # Use store methods to set selection
        curve_view_widget._curve_store.select(0)

        # Get original position
        original_x = curve_view_widget.curve_data[0][1]
        original_y = curve_view_widget.curve_data[0][2]

        # Nudge point
        curve_view_widget.nudge_selected(10.0, 5.0)

        # Check that point moved
        new_x = curve_view_widget.curve_data[0][1]
        new_y = curve_view_widget.curve_data[0][2]

        assert new_x == original_x + 10.0
        assert new_y == original_y + 5.0

    def test_nudge_converts_interpolated_to_keyframe(self, curve_view_widget: CurveViewWidget) -> None:
        """Test that nudging an interpolated point converts it to a keyframe."""
        from core.models import PointStatus

        # Create test data with an interpolated point
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),  # This will be nudged
            (3, 120.0, 120.0, "keyframe"),
        ]
        curve_view_widget.set_curve_data(test_data)

        # Select the interpolated point (index 1)
        curve_view_widget._curve_store.select(1)

        # Verify it's interpolated before nudging
        point_before = curve_view_widget.curve_data[1]
        assert point_before[3] == "interpolated", "Point should be interpolated before nudge"

        # Nudge the point
        curve_view_widget.nudge_selected(5.0, 5.0)

        # Verify the point is now a keyframe
        point_after = curve_view_widget.curve_data[1]
        assert point_after[3] == PointStatus.KEYFRAME.value, "Point should be keyframe after nudge"

        # Verify position changed
        assert point_after[1] == 115.0, "X coordinate should have moved"
        assert point_after[2] == 115.0, "Y coordinate should have moved"

    def test_nudge_converts_normal_to_keyframe(self, curve_view_widget: CurveViewWidget) -> None:
        """Test that nudging a normal point converts it to a keyframe."""
        from core.models import PointStatus

        # Create test data with a normal point (3-tuple, implicit normal status)
        test_data = [
            (1, 100.0, 100.0),  # This will be nudged - implicit normal status
            (2, 110.0, 110.0, "keyframe"),
        ]
        curve_view_widget.set_curve_data(test_data)

        # Select the normal point (index 0)
        curve_view_widget._curve_store.select(0)

        # Nudge the point
        curve_view_widget.nudge_selected(5.0, 5.0)

        # Verify the point is now a keyframe
        point_after = curve_view_widget.curve_data[0]
        assert len(point_after) >= 4, "Point should have status after nudge"
        assert point_after[3] == PointStatus.KEYFRAME.value, "Point should be keyframe after nudge"

    def test_nudge_keyframe_stays_keyframe(self, curve_view_widget: CurveViewWidget) -> None:
        """Test that nudging a keyframe keeps it as a keyframe."""
        from core.models import PointStatus

        # Create test data with a keyframe
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "keyframe"),
        ]
        curve_view_widget.set_curve_data(test_data)

        # Select the keyframe (index 0)
        curve_view_widget._curve_store.select(0)

        # Nudge the point
        curve_view_widget.nudge_selected(5.0, 5.0)

        # Verify the point is still a keyframe
        point_after = curve_view_widget.curve_data[0]
        assert point_after[3] == PointStatus.KEYFRAME.value, "Point should remain keyframe after nudge"


class TestServiceIntegration:
    """Test integration with services."""

    def test_set_main_window(self, curve_view_widget: CurveViewWidget) -> None:
        """Test setting main window reference."""
        mock_main_window = Mock()
        curve_view_widget.set_main_window(mock_main_window)

        assert curve_view_widget.main_window == mock_main_window
        assert curve_view_widget.interaction_service is not None

    def test_get_view_state(self, curve_view_widget: CurveViewWidget) -> None:
        """Test getting current view state."""
        view_state = curve_view_widget.get_view_state()

        assert view_state is not None
        # Check zoom_factor exists and is accessible
        assert view_state.zoom_factor is not None, "ViewState should have zoom_factor"
        assert view_state.zoom_factor == curve_view_widget.zoom_factor

    def test_set_background_image(self, curve_view_widget: CurveViewWidget) -> None:
        """Test setting background image."""
        # Test with None (should not raise exceptions)
        curve_view_widget.set_background_image(None)
        assert curve_view_widget.background_image is None


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_empty_curve_data_handling(self, curve_view_widget: CurveViewWidget) -> None:
        """Test handling of empty curve data."""
        curve_view_widget.set_curve_data([])

        assert len(curve_view_widget.curve_data) == 0
        assert len(curve_view_widget.selected_indices) == 0

    def test_invalid_point_operations(self, curve_view_widget: CurveViewWidget) -> None:
        """Test handling of invalid point operations."""
        # Try to update non-existent point
        curve_view_widget.update_point(99, 100.0, 200.0)  # Should not crash

        # Try to remove non-existent point
        curve_view_widget.remove_point(99)  # Should not crash

    def test_selection_edge_cases(self, curve_view_widget: CurveViewWidget, sample_points: PointsList) -> None:
        """Test selection edge cases."""
        curve_view_widget.set_curve_data(sample_points)

        # Try to select invalid index
        curve_view_widget._select_point(99)  # Should not crash

        # Clear selection when already empty
        curve_view_widget.clear_selection()
        curve_view_widget.clear_selection()  # Should not crash


class TestRealComponentBenefits:
    """Demonstrate the benefits of using real components instead of mocks."""

    def test_real_vs_mock_behavior(self) -> None:
        """Show how real components provide actual behavior vs mock assumptions."""
        # Real component - actual behavior
        real_view = MockCurveView()
        test_data = MockDataBuilder().with_points(3).build()
        real_view.set_curve_data(test_data)

        # Real deletion behavior - data actually gets removed
        original_count = len(real_view.curve_data)
        real_view.selected_points = {1}
        real_view.remove_point(1)

        # Verify real deletion happened
        assert len(real_view.curve_data) == original_count - 1

        # Real coordinate transformation - actual math
        real_view.zoom_factor = 2.0
        real_view.offset_x = 100.0
        screen_point = real_view.data_to_screen(150.0, 200.0)
        data_point = real_view.screen_to_data(screen_point[0], screen_point[1])

        # Real coordinate roundtrip works
        assert abs(data_point[0] - 150.0) < 0.1
        assert abs(data_point[1] - 200.0) < 0.1

    def test_easy_test_data_creation(self) -> None:
        """Show how builder pattern makes test data creation easy."""
        # Create different types of test data easily
        simple_data = MockDataBuilder().with_points(5).build()
        keyframe_data = MockDataBuilder().with_keyframes([1, 5, 10]).build()
        mixed_data = MockDataBuilder().with_points(3).with_keyframes([7, 8]).build()

        # Builder creates proper data structures
        assert len(simple_data) == 5
        assert all(isinstance(point, tuple) and len(point) == 4 for point in simple_data)

        assert "keyframe" in [point[3] for point in keyframe_data]
        assert "normal" in [point[3] for point in mixed_data]
        assert "keyframe" in [point[3] for point in mixed_data]

        # Test builder produces both types in mixed data
        assert len(mixed_data) == 5  # 3 normal + 2 keyframes

    def test_real_component_maintenance(self) -> None:
        """Show how real components are easier to maintain than mocks."""
        # Real component automatically matches interface changes
        real_view = MockCurveView()

        # If the real CurveView interface changes, this automatically adapts
        # No need to update hundreds of mock method signatures
        # Verify attributes exist by accessing them
        assert real_view.curve_data is not None or real_view.curve_data == [], "Real view should have curve_data"
        assert (
            real_view.selected_points is not None or real_view.selected_points == set()
        ), "Real view should have selected_points"
        assert callable(getattr(real_view, "update", None)), "Real view should have update method"

        # Real behavior doesn't drift from implementation
        real_view.add_point((99, 999.0, 888.0, "test"))
        assert len(real_view.curve_data) == 1
        assert real_view.curve_data[0] == (99, 999.0, 888.0, "test")

    def test_integration_with_real_widget(self, curve_view_widget: CurveViewWidget) -> None:
        """Show how real test components can work alongside real widgets."""
        # Both provide similar interfaces but at different levels
        test_curve_view = MockCurveView()
        test_data = MockDataBuilder().with_points(3).build()

        # Real widget (PySide6 implementation)
        curve_view_widget.set_curve_data(test_data)  # pyright: ignore[reportArgumentType]
        assert len(curve_view_widget.curve_data) == 3

        # Real test component (lightweight implementation)
        test_curve_view.set_curve_data(test_data)
        assert len(test_curve_view.curve_data) == 3

        # Both can be used where appropriate:
        # - Real widget for UI integration tests
        # - Real test component for service/logic tests


if __name__ == "__main__":
    pytest.main(["-v", __file__])
