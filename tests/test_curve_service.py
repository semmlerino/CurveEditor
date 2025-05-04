"""
Unit tests for the CurveService class.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtCore import QRect, QPointF
from services.curve_service import CurveService


class TestCurveService(unittest.TestCase):
    """Test cases for the CurveService class."""

    def setUp(self):
        """Set up test fixtures for each test."""
        # Create mock objects for CurveView and MainWindow
        self.mock_curve_view = MagicMock()
        self.mock_main_window = MagicMock()

        # Configure curve view mock with basic properties
        self.mock_curve_view.points = [(1, 100, 200), (2, 150, 250), (3, 200, 300)]
        self.mock_curve_view.selected_points = set()
        self.mock_curve_view.selected_point_idx = -1
        self.mock_curve_view.zoom_factor = 1.0
        self.mock_curve_view.offset_x = 0
        self.mock_curve_view.offset_y = 0
        self.mock_curve_view.x_offset = 0
        self.mock_curve_view.y_offset = 0
        self.mock_curve_view.image_width = 1920
        self.mock_curve_view.image_height = 1080
        self.mock_curve_view.width.return_value = 800
        self.mock_curve_view.height.return_value = 600
        self.mock_curve_view.point_radius = 5

        # Configure main window mock
        self.mock_main_window.curve_data = [(1, 100, 200), (2, 150, 250), (3, 200, 300)]
        self.mock_main_window.statusBar.return_value = MagicMock()

    def test_select_point_by_index(self):
        """Test selecting a point by its index."""
        # Act
        result = CurveService.select_point_by_index(
            self.mock_curve_view, self.mock_main_window, 1)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_curve_view.selected_point_idx, 1)
        self.assertEqual(self.mock_curve_view.selected_points, {1})
        self.mock_curve_view.update.assert_called_once()

    def test_select_point_by_index_invalid(self):
        """Test selecting a point with invalid index."""
        # Act
        result = CurveService.select_point_by_index(
            self.mock_curve_view, self.mock_main_window, 10)  # Out of range

        # Assert
        self.assertFalse(result)
        self.mock_curve_view.update.assert_not_called()

    def test_select_all_points(self):
        """Test selecting all points."""
        # Act
        count = CurveService.select_all_points(
            self.mock_curve_view, self.mock_main_window)

        # Assert
        self.assertEqual(count, 3)
        self.assertEqual(self.mock_curve_view.selected_points, {0, 1, 2})
        self.assertEqual(self.mock_curve_view.selected_point_idx, 0)
        self.mock_curve_view.update.assert_called_once()

    def test_clear_selection(self):
        """Test clearing the selection."""
        # Arrange
        self.mock_curve_view.selected_points = {0, 1}
        self.mock_curve_view.selected_point_idx = 0

        # Act
        CurveService.clear_selection(self.mock_curve_view, self.mock_main_window)

        # Assert
        self.assertEqual(self.mock_curve_view.selected_points, set())
        self.assertEqual(self.mock_curve_view.selected_point_idx, -1)
        self.mock_curve_view.update.assert_called_once()

    def test_select_points_in_rect(self):
        """Test selecting points within a rectangle."""
        # Mock the transform_point method to return known coordinates
        with patch.object(CurveService, 'transform_point', side_effect=[
            (100, 100),  # First point
            (150, 150),  # Second point - inside selection
            (300, 300)   # Third point
        ]):
            # Create a selection rectangle
            selection_rect = QRect(140, 140, 20, 20)  # Should only contain the second point

            # Act
            count = CurveService.select_points_in_rect(
                self.mock_curve_view, self.mock_main_window, selection_rect)

            # Assert
            self.assertEqual(count, 1)
            self.assertEqual(self.mock_curve_view.selected_points, {1})
            self.assertEqual(self.mock_curve_view.selected_point_idx, 1)
            self.mock_curve_view.update.assert_called_once()

    @patch('services.centering_zoom_service.CenteringZoomService.calculate_centering_offsets')
    def test_transform_point(self, mock_calculate_offsets):
        """Test transforming a point from data coordinates to widget coordinates."""
        # Arrange
        mock_calculate_offsets.return_value = (10, 10)  # Mock offset calculation

        # Act
        tx, ty = CurveService.transform_point(
            self.mock_curve_view, 100, 200, 1920, 1080, 10, 10, 0.5)

        # Assert
        # Expected calculation: base_x + (x * scale) = 10 + (100 * 0.5) = 60
        # Expected calculation: base_y + (y * scale) = 10 + (200 * 0.5) = 110
        self.assertEqual(tx, 60)
        self.assertEqual(ty, 110)

    def test_update_point_position(self):
        """Test updating a point's position."""
        # Act
        result = CurveService.update_point_position(
            self.mock_curve_view, self.mock_main_window, 1, 160, 260)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_main_window.curve_data[1], (2, 160, 260))

    def test_update_point_position_invalid_index(self):
        """Test updating a point with invalid index."""
        # Act
        result = CurveService.update_point_position(
            self.mock_curve_view, self.mock_main_window, 10, 160, 260)  # Out of range

        # Assert
        self.assertFalse(result)
        # Ensure data wasn't modified
        self.assertEqual(self.mock_main_window.curve_data[1], (2, 150, 250))

    def test_find_point_at(self):
        """Test finding a point at specific widget coordinates."""
        # Mock the transform_point method to return known coordinates
        with patch.object(CurveService, 'transform_point', side_effect=[
            (100, 100),  # First point
            (150, 150),  # Second point
            (200, 200)   # Third point
        ]):
            # Act - This should find the second point which is closest
            idx = CurveService.find_point_at(self.mock_curve_view, 155, 155)

            # Assert
            self.assertEqual(idx, 1)

    def test_find_point_at_no_points_found(self):
        """Test finding a point when no points are close enough."""
        # Mock the transform_point method to return coordinates far from search point
        with patch.object(CurveService, 'transform_point', side_effect=[
            (100, 100),  # Far from target
            (200, 200),  # Far from target
            (300, 300)   # Far from target
        ]):
            # Act - This should not find any points since none are close enough
            idx = CurveService.find_point_at(self.mock_curve_view, 150, 150)

            # Assert
            self.assertEqual(idx, -1)

    def test_reset_view(self):
        """Test resetting the view to default settings."""
        # Arrange
        self.mock_curve_view.zoom_factor = 2.0
        self.mock_curve_view.offset_x = 10
        self.mock_curve_view.offset_y = 20

        # Act
        CurveService.reset_view(self.mock_curve_view)

        # Assert
        # Verify ZoomOperations.reset_view was called
        self.mock_curve_view.zoom_factor = 1.0  # This would be set by ZoomOperations
        self.mock_curve_view.update.assert_called_once()

    def test_nudge_selected_points(self):
        """Test nudging selected points."""
        # Arrange
        self.mock_curve_view.selected_points = {0, 1}
        self.mock_curve_view.selected_point_idx = 0
        self.mock_curve_view.nudge_increment = 2.0
        self.mock_curve_view.main_window = self.mock_main_window

        # Act
        result = CurveService.nudge_selected_points(self.mock_curve_view, dx=1, dy=-1)

        # Assert
        self.assertTrue(result)
        # First point should be moved by (2, -2) - due to nudge_increment=2.0
        self.assertEqual(self.mock_main_window.curve_data[0],
                         (1, 102, 198))
        # Second point should also be moved
        self.assertEqual(self.mock_main_window.curve_data[1],
                         (2, 152, 248))


if __name__ == '__main__':
    unittest.main()
