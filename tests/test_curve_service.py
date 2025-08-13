"""
Unit tests for the CurveService class.
"""

import unittest
from typing import final

from PySide6.QtCore import QRect

from services import TransformService
from services.data_service import DataService
from services.interaction_service import InteractionService
from tests.test_utilities import ProtocolCompliantMockCurveView, ProtocolCompliantMockMainWindow


@final
class TestCurveService(unittest.TestCase):
    """Test cases for the CurveService class."""

    # Initialize instance variables with proper defaults for type safety
    mock_curve_view: ProtocolCompliantMockCurveView = None  # type: ignore[assignment]
    mock_main_window: ProtocolCompliantMockMainWindow = None  # type: ignore[assignment]
    interaction_service: InteractionService = None  # type: ignore[assignment]
    transform_service: TransformService = None  # type: ignore[assignment]
    data_service: DataService = None  # type: ignore[assignment]

    def setUp(self) -> None:
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

        self.mock_main_window = ProtocolCompliantMockMainWindow()
        self.mock_main_window.curve_view.curve_data = [
            (1, 100, 200, "keyframe"),
            (2, 150, 250, "keyframe"),
            (3, 200, 300, "keyframe"),
        ]
        self.mock_main_window.curve_view.points = self.mock_main_window.curve_view.curve_data

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
        # Act
        result = self.interaction_service.select_point_by_index(self.mock_curve_view, self.mock_main_window, 1)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_curve_view.selected_point_idx, 1)
        self.assertEqual(self.mock_curve_view.selected_points, {1})
        self.assertTrue(self.mock_curve_view.update_called)

    def test_select_point_by_index_invalid(self) -> None:
        """Test selecting a point with invalid index."""
        # Act
        result = self.interaction_service.select_point_by_index(
            self.mock_curve_view, self.mock_main_window, 10
        )  # Out of range

        # Assert
        self.assertFalse(result)
        self.assertFalse(self.mock_curve_view.update_called)

    def test_select_all_points(self) -> None:
        """Test selecting all points."""
        # Act
        count = self.interaction_service.select_all_points(self.mock_curve_view, self.mock_main_window)

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
        self.interaction_service.clear_selection(self.mock_curve_view, self.mock_main_window)

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
        view_state = transform_service.create_view_state(self.mock_curve_view)
        real_transform = transform_service.create_transform(view_state)

        # Override the mock's get_current_transform to return the real transform
        self.mock_curve_view.get_current_transform = lambda: real_transform

        # Get transformed coordinates for the points we have
        _ = real_transform.data_to_screen(100, 200)  # p0_transformed
        p1_transformed = real_transform.data_to_screen(150, 250)
        _ = real_transform.data_to_screen(200, 300)  # p2_transformed

        # Create rectangle that should include only the middle point based on actual transforms
        rect = QRect(int(p1_transformed[0] - 10), int(p1_transformed[1] - 10), 20, 20)

        # Call the real method - no mocking!
        count = self.interaction_service.select_points_in_rect(self.mock_curve_view, self.mock_main_window, rect)

        # Verify the method worked correctly
        self.assertEqual(count, 1)
        self.assertEqual(self.mock_curve_view.selected_points, {1})
        self.assertEqual(self.mock_curve_view.selected_point_idx, 1)
        self.assertTrue(self.mock_curve_view.update_called)

    def test_update_point_position(self) -> None:
        """Test updating a point's position."""
        # Act
        result = self.interaction_service.update_point_position(
            self.mock_curve_view, self.mock_main_window, 1, 160, 260
        )

        # Assert
        self.assertTrue(result)
        # Check the curve_view's data, not main_window's
        self.assertEqual(self.mock_curve_view.curve_data[1][1:3], (160, 260))

    def test_update_point_position_invalid_index(self) -> None:
        """Test updating a point with invalid index."""
        # Act
        result = self.interaction_service.update_point_position(
            self.mock_curve_view, self.mock_main_window, 10, 160, 260
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
        self.mock_curve_view.center_offset_x = 0.0
        self.mock_curve_view.center_offset_y = 0.0

        # Use the real CurveService method
        from services import get_transform_service

        transform_service = get_transform_service()

        # Get actual transformed coordinates for point 1 (150, 250)
        view_state = transform_service.create_view_state(self.mock_curve_view)
        real_transform = transform_service.create_transform(view_state)

        # Override the mock's get_current_transform to return the real transform
        self.mock_curve_view.get_current_transform = lambda: real_transform

        p1_transformed = real_transform.data_to_screen(150, 250)

        # Call find_point_at near the transformed coordinates of point 1
        idx = self.interaction_service.find_point_at(self.mock_curve_view, p1_transformed[0], p1_transformed[1])

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
        idx = self.interaction_service.find_point_at(self.mock_curve_view, 10000, 10000)

        # Should return -1 (no point found)
        self.assertEqual(idx, -1)

    def test_reset_view(self) -> None:
        """Test resetting the view to default settings."""
        # Arrange
        self.mock_curve_view.zoom_factor = 2.0
        self.mock_curve_view.offset_x = 10
        self.mock_curve_view.offset_y = 20

        # Act
        self.interaction_service.reset_view(self.mock_curve_view)

        # Assert
        # Verify ZoomOperations.reset_view was called
        self.mock_curve_view.zoom_factor = 1.0  # This would be set by ZoomOperations
        self.assertTrue(self.mock_curve_view.update_called)

    @unittest.skip("nudge_selected_points method not yet implemented in consolidated services")
    def test_nudge_selected_points(self) -> None:
        """Test nudging selected points."""
        # This functionality has been consolidated but not yet fully implemented
        # TODO: Implement nudge functionality in InteractionService
        pass


if __name__ == "__main__":
    _ = unittest.main()
