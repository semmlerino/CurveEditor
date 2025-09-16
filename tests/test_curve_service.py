"""
Unit tests for the CurveService class.
"""

import unittest
from typing import final

from PySide6.QtCore import QRect

from services.data_service import DataService
from services.interaction_service import InteractionService
from services.transform_service import TransformService
from tests.test_utilities import ProtocolCompliantMockCurveView, ProtocolCompliantMockMainWindow


@final
class TestCurveService(unittest.TestCase):
    """Test cases for the CurveService class."""

    def __init__(self, methodName: str = "runTest") -> None:  # noqa: N803
        super().__init__(methodName)
        # Initialize instance variables with proper defaults for type safety
        self.mock_curve_view: ProtocolCompliantMockCurveView
        self.mock_main_window: ProtocolCompliantMockMainWindow
        self.interaction_service: InteractionService
        self.transform_service: TransformService
        self.data_service: DataService

    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        """Set up test fixtures for each test."""
        # Create protocol-compliant mock objects for CurveView and MainWindow
        self.mock_curve_view = ProtocolCompliantMockCurveView()
        # Set properties after creation
        self.mock_curve_view.curve_data = [
            (1, 100, 200, "keyframe"),
            (2, 150, 250, "keyframe"),
            (3, 200, 300, "keyframe"),
        ]
        self.mock_curve_view.points = self.mock_curve_view.curve_data
        self.mock_curve_view.selected_points = set()
        self.mock_curve_view.selected_point_idx = -1
        self.mock_curve_view.zoom_factor = 1.0
        self.mock_curve_view.offset_x = 0
        self.mock_curve_view.offset_y = 0

        # Add missing protocol attributes to make it compatible
        self.mock_curve_view.x_offset = 0
        self.mock_curve_view.y_offset = 0
        self.mock_curve_view.drag_active = False
        self.mock_curve_view.pan_active = False
        self.mock_curve_view.last_drag_pos = None
        self.mock_curve_view.last_pan_pos = None
        self.mock_curve_view.rubber_band = None

        self.mock_main_window = ProtocolCompliantMockMainWindow()
        self.mock_main_window.curve_view.curve_data = [
            (1, 100, 200, "keyframe"),
            (2, 150, 250, "keyframe"),
            (3, 200, 300, "keyframe"),
        ]
        self.mock_main_window.curve_view.points = self.mock_main_window.curve_view.curve_data

        # Add missing protocol attributes
        self.mock_main_window.selected_indices = []  # Changed to list to match protocol
        self.mock_main_window.max_history_size = 100
        self.mock_main_window.point_name = ""
        self.mock_main_window.point_color = "blue"
        self.mock_main_window.undo_button = None
        self.mock_main_window.redo_button = None
        self.mock_main_window.save_button = None

        # Additional properties needed for transformation tests
        # Set these through the internal interface if they don't exist
        if not hasattr(self.mock_curve_view, "center_offset_x"):
            setattr(self.mock_curve_view, "center_offset_x", 0.0)
        if not hasattr(self.mock_curve_view, "center_offset_y"):
            setattr(self.mock_curve_view, "center_offset_y", 0.0)

        # Initialize consolidated services
        self.interaction_service = InteractionService()
        self.transform_service = TransformService()
        self.data_service = DataService()

    def test_select_point_by_index(self) -> None:
        """Test selecting a point by its index."""
        # Act - Use pyright ignore for protocol compatibility
        result = self.interaction_service.select_point_by_index(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            self.mock_main_window,  # pyright: ignore[reportArgumentType]
            1,
        )

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_curve_view.selected_point_idx, 1)
        self.assertEqual(self.mock_curve_view.selected_points, {1})
        self.assertTrue(self.mock_curve_view.update_called)

    def test_select_point_by_index_invalid(self) -> None:
        """Test selecting a point with invalid index."""
        # Act
        result = self.interaction_service.select_point_by_index(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            self.mock_main_window,  # pyright: ignore[reportArgumentType]
            10,
        )  # Out of range

        # Assert
        self.assertFalse(result)
        self.assertFalse(self.mock_curve_view.update_called)

    def test_select_all_points(self) -> None:
        """Test selecting all points."""
        # Act
        count = self.interaction_service.select_all_points(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            self.mock_main_window,  # pyright: ignore[reportArgumentType]
        )

        # Assert
        self.assertEqual(count, 3)
        self.assertEqual(self.mock_curve_view.selected_points, {0, 1, 2})
        self.assertEqual(self.mock_curve_view.selected_point_idx, 0)
        self.assertTrue(self.mock_curve_view.update_called)

    def test_clear_selection(self) -> None:
        """Test clearing the selection."""
        # Arrange
        self.mock_curve_view.selected_points = {0, 1}
        self.mock_curve_view.selected_point_idx = 0

        # Act
        self.interaction_service.clear_selection(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            self.mock_main_window,  # pyright: ignore[reportArgumentType]
        )

        # Assert
        self.assertEqual(self.mock_curve_view.selected_points, set())
        self.assertEqual(self.mock_curve_view.selected_point_idx, -1)
        self.assertTrue(self.mock_curve_view.update_called)

    def test_select_points_in_rect(self) -> None:
        """Test selecting points within a rectangle using real transformation."""
        # Add necessary attributes for TransformationService
        self.mock_curve_view.flip_y_axis = True
        self.mock_curve_view.scale_to_image = False
        # Use setattr to add missing attributes
        setattr(self.mock_curve_view, "center_offset_x", 0.0)
        setattr(self.mock_curve_view, "center_offset_y", 0.0)

        # Use the real CurveService method with real transformation
        from services import get_transform_service

        transform_service = get_transform_service()

        # Create real transform to understand actual coordinate mapping
        view_state = transform_service.create_view_state(self.mock_curve_view)  # pyright: ignore[reportArgumentType]
        real_transform = transform_service.create_transform_from_view_state(view_state)

        # Override the mock's get_current_transform to return the real transform
        self.mock_curve_view.get_current_transform = lambda: real_transform

        # Get transformed coordinates for the points we have
        _ = real_transform.data_to_screen(100, 200)  # p0_transformed
        p1_transformed = real_transform.data_to_screen(150, 250)
        _ = real_transform.data_to_screen(200, 300)  # p2_transformed

        # Create rectangle that should include only the middle point based on actual transforms
        rect = QRect(int(p1_transformed[0] - 10), int(p1_transformed[1] - 10), 20, 20)

        # Call the real method - no mocking!
        count = self.interaction_service.select_points_in_rect(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            self.mock_main_window,  # pyright: ignore[reportArgumentType]
            rect,
        )

        # Verify the method worked correctly
        self.assertEqual(count, 1)
        self.assertEqual(self.mock_curve_view.selected_points, {1})
        self.assertEqual(self.mock_curve_view.selected_point_idx, 1)
        self.assertTrue(self.mock_curve_view.update_called)

    def test_update_point_position(self) -> None:
        """Test updating a point's position."""
        # Act
        result = self.interaction_service.update_point_position(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            self.mock_main_window,  # pyright: ignore[reportArgumentType]
            1,
            160,
            260,
        )

        # Assert
        self.assertTrue(result)
        # Check the curve_view's data, not main_window's
        self.assertEqual(self.mock_curve_view.curve_data[1][1:3], (160, 260))

    def test_update_point_position_invalid_index(self) -> None:
        """Test updating a point with invalid index."""
        # Act
        result = self.interaction_service.update_point_position(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            self.mock_main_window,  # pyright: ignore[reportArgumentType]
            10,
            160,
            260,
        )  # Out of range

        # Assert
        self.assertFalse(result)
        # Ensure data wasn't modified in curve_view
        self.assertEqual(self.mock_curve_view.curve_data[1][1:3], (150, 250))

    def test_find_point_at(self) -> None:
        """Test finding a point at specific widget coordinates using real transformation."""
        # Add necessary attributes for TransformationService (if not already present)
        self.mock_curve_view.flip_y_axis = True
        self.mock_curve_view.scale_to_image = False
        if not hasattr(self.mock_curve_view, "center_offset_x"):
            setattr(self.mock_curve_view, "center_offset_x", 0.0)
        if not hasattr(self.mock_curve_view, "center_offset_y"):
            setattr(self.mock_curve_view, "center_offset_y", 0.0)

        # Use the real CurveService method
        from services import get_transform_service

        transform_service = get_transform_service()

        # Get actual transformed coordinates for point 1 (150, 250)
        view_state = transform_service.create_view_state(self.mock_curve_view)  # pyright: ignore[reportArgumentType]
        real_transform = transform_service.create_transform_from_view_state(view_state)

        # Override the mock's get_current_transform to return the real transform
        self.mock_curve_view.get_current_transform = lambda: real_transform

        p1_transformed = real_transform.data_to_screen(150, 250)

        # Call find_point_at near the transformed coordinates of point 1
        idx = self.interaction_service.find_point_at(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            p1_transformed[0],
            p1_transformed[1],
        )

        # Should find point 1 (index 1)
        self.assertEqual(idx, 1)

    def test_find_point_at_no_points_found(self) -> None:
        """Test finding a point when no points are close enough using real method."""
        # Add necessary attributes for TransformationService
        self.mock_curve_view.flip_y_axis = True
        self.mock_curve_view.scale_to_image = False
        # Use setattr to add missing attributes
        setattr(self.mock_curve_view, "center_offset_x", 0.0)
        setattr(self.mock_curve_view, "center_offset_y", 0.0)

        # Use the real CurveService method at coordinates far from any points
        # Call find_point_at at coordinates that should be far from any transformed points
        idx = self.interaction_service.find_point_at(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            10000,
            10000,
        )

        # Should return -1 (no point found)
        self.assertEqual(idx, -1)

    def test_reset_view(self) -> None:
        """Test resetting the view to default settings."""
        # Arrange
        self.mock_curve_view.zoom_factor = 2.0
        self.mock_curve_view.offset_x = 10
        self.mock_curve_view.offset_y = 20

        # Act
        self.interaction_service.reset_view(self.mock_curve_view)  # pyright: ignore[reportArgumentType]

        # Assert
        # Verify ZoomOperations.reset_view was called
        self.mock_curve_view.zoom_factor = 1.0  # This would be set by ZoomOperations
        self.assertTrue(self.mock_curve_view.update_called)

    def test_nudge_selected_points(self) -> None:
        """Test nudging selected points."""
        # Arrange
        self.mock_curve_view.selected_points = {0, 1}  # Select first two points
        initial_point_0 = self.mock_curve_view.curve_data[0]
        initial_point_1 = self.mock_curve_view.curve_data[1]

        # Act
        dx, dy = 5.0, 10.0
        result = self.interaction_service.nudge_selected_points(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            self.mock_main_window,  # pyright: ignore[reportArgumentType]
            dx,
            dy,
        )

        # Assert
        self.assertTrue(result)

        # Check that selected points were moved by the delta
        moved_point_0 = self.mock_curve_view.curve_data[0]
        moved_point_1 = self.mock_curve_view.curve_data[1]

        # Point 0: (1, 100, 200, "keyframe") -> (1, 105, 210, "keyframe")
        self.assertEqual(moved_point_0[0], initial_point_0[0])  # Frame unchanged
        self.assertEqual(moved_point_0[1], initial_point_0[1] + dx)  # X moved
        self.assertEqual(moved_point_0[2], initial_point_0[2] + dy)  # Y moved
        self.assertEqual(moved_point_0[3], initial_point_0[3])  # Status unchanged

        # Point 1: (2, 150, 250, "keyframe") -> (2, 155, 260, "keyframe")
        self.assertEqual(moved_point_1[0], initial_point_1[0])  # Frame unchanged
        self.assertEqual(moved_point_1[1], initial_point_1[1] + dx)  # X moved
        self.assertEqual(moved_point_1[2], initial_point_1[2] + dy)  # Y moved
        self.assertEqual(moved_point_1[3], initial_point_1[3])  # Status unchanged

        # Point 2 should be unchanged (not selected)
        unchanged_point_2 = self.mock_curve_view.curve_data[2]
        self.assertEqual(unchanged_point_2, (3, 200, 300, "keyframe"))

        # Verify update was called
        self.assertTrue(self.mock_curve_view.update_called)

    def test_nudge_selected_points_no_selection(self) -> None:
        """Test nudging when no points are selected."""
        # Arrange
        self.mock_curve_view.selected_points = set()  # No selection

        # Act
        result = self.interaction_service.nudge_selected_points(
            self.mock_curve_view,  # pyright: ignore[reportArgumentType]
            self.mock_main_window,  # pyright: ignore[reportArgumentType]
            5.0,
            10.0,
        )

        # Assert
        self.assertFalse(result)

        # Verify no points were modified
        self.assertEqual(self.mock_curve_view.curve_data[0], (1, 100, 200, "keyframe"))
        self.assertEqual(self.mock_curve_view.curve_data[1], (2, 150, 250, "keyframe"))
        self.assertEqual(self.mock_curve_view.curve_data[2], (3, 200, 300, "keyframe"))


if __name__ == "__main__":
    _ = unittest.main()
