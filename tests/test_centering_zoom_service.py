"""
Unit tests for the CenteringZoomService class.
"""

import unittest
from unittest.mock import MagicMock, Mock

from services.centering_zoom_service import CenteringZoomService


class TestCenteringZoomService(unittest.TestCase):
    """Test cases for the CenteringZoomService class."""

    def setUp(self):
        """Set up test fixtures for each test."""
        # Create mock objects for CurveView
        self.mock_curve_view = MagicMock()

        # Configure curve view mock with basic properties
        self.mock_curve_view.points = [(1, 100, 200), (2, 150, 250), (3, 200, 300)]
        self.mock_curve_view.selected_points = {1}
        self.mock_curve_view.selected_point_idx = 1
        self.mock_curve_view.zoom_factor = 1.0
        self.mock_curve_view.offset_x = 0
        self.mock_curve_view.offset_y = 0
        self.mock_curve_view.x_offset = 0
        self.mock_curve_view.y_offset = 0
        self.mock_curve_view.image_width = 1920
        self.mock_curve_view.image_height = 1080
        self.mock_curve_view.width.return_value = 800
        self.mock_curve_view.height.return_value = 600

        # Set up background image mock
        self.mock_background_image = MagicMock()
        self.mock_background_image.width.return_value = 1920
        self.mock_background_image.height.return_value = 1080
        self.mock_curve_view.background_image = self.mock_background_image

    def test_calculate_centering_offsets(self):
        """Test calculating centering offsets for content within a viewport."""
        # Test case: Content smaller than viewport, should be centered
        widget_width = 800
        widget_height = 600
        content_width = 400
        content_height = 300
        pan_offset_x = 0
        pan_offset_y = 0

        offset_x, offset_y = CenteringZoomService.calculate_centering_offsets(
            widget_width, widget_height, content_width, content_height, pan_offset_x, pan_offset_y
        )

        # Content should be centered in the viewport
        self.assertEqual(offset_x, 200)  # (800 - 400) / 2
        self.assertEqual(offset_y, 150)  # (600 - 300) / 2

        # Test case: Content larger than viewport, with pan offset
        content_width = 1000
        content_height = 800
        pan_offset_x = 100
        pan_offset_y = 50

        offset_x, offset_y = CenteringZoomService.calculate_centering_offsets(
            widget_width, widget_height, content_width, content_height, pan_offset_x, pan_offset_y
        )

        # Content should be positioned with pan offset
        self.assertEqual(offset_x, -100 + 100)  # -((1000 - 800) / 2) + 100
        self.assertEqual(offset_y, -100 + 50)  # -((800 - 600) / 2) + 50

    def test_reset_view(self):
        """Test resetting the view to default state."""
        # Call the method
        CenteringZoomService.reset_view(self.mock_curve_view)

        # Verify the view was reset to defaults
        self.assertEqual(self.mock_curve_view.zoom_factor, 1.0)
        self.assertEqual(self.mock_curve_view.offset_x, 0)
        self.assertEqual(self.mock_curve_view.offset_y, 0)
        self.mock_curve_view.update.assert_called_once()

    def test_zoom_in(self):
        """Test zooming in on a point."""
        # Initial state
        self.mock_curve_view.zoom_factor = 1.0

        # Call the method to zoom in (centered by default)
        CenteringZoomService.zoom_in(self.mock_curve_view)

        # Verify zoom was increased
        self.assertGreater(self.mock_curve_view.zoom_factor, 1.0)
        self.mock_curve_view.update.assert_called_once()

    def test_zoom_out(self):
        """Test zooming out."""
        # Initial state
        self.mock_curve_view.zoom_factor = 2.0

        # Call the method to zoom out
        CenteringZoomService.zoom_out(self.mock_curve_view)

        # Verify zoom was decreased
        self.assertLess(self.mock_curve_view.zoom_factor, 2.0)
        self.mock_curve_view.update.assert_called_once()

    def test_zoom_in_at_point(self):
        """Test zooming in at a specific point."""
        # Initial state
        self.mock_curve_view.zoom_factor = 1.0
        x, y = 400, 300  # Center point for zooming

        # Call the method
        CenteringZoomService.zoom_in_at_point(self.mock_curve_view, x, y)

        # Verify zoom was increased
        self.assertGreater(self.mock_curve_view.zoom_factor, 1.0)
        # Update should be called
        self.mock_curve_view.update.assert_called_once()

    def test_zoom_out_at_point(self):
        """Test zooming out at a specific point."""
        # Initial state
        self.mock_curve_view.zoom_factor = 2.0
        x, y = 400, 300  # Center point for zooming

        # Call the method
        CenteringZoomService.zoom_out_at_point(self.mock_curve_view, x, y)

        # Verify zoom was decreased
        self.assertLess(self.mock_curve_view.zoom_factor, 2.0)
        # Update should be called
        self.mock_curve_view.update.assert_called_once()

    def test_pan_view(self):
        """Test panning the view."""
        # Initial state
        self.mock_curve_view.offset_x = 0
        self.mock_curve_view.offset_y = 0

        # Call the method to pan the view
        dx, dy = 50, -30
        CenteringZoomService.pan_view(self.mock_curve_view, dx, dy)

        # Verify offsets were updated
        self.assertEqual(self.mock_curve_view.offset_x, 50)
        self.assertEqual(self.mock_curve_view.offset_y, -30)
        # Update should be called
        self.mock_curve_view.update.assert_called_once()

    def test_center_on_selected_point(self):
        """Test centering the view on a selected point."""
        # Set up transformations for the selected point
        self.mock_curve_view.transform_point = Mock(return_value=(150, 250))

        # Set a mock main_window with curve_data for the method to succeed
        mock_main_window = MagicMock()
        mock_main_window.curve_data = self.mock_curve_view.points
        self.mock_curve_view.main_window = mock_main_window

        # Reset update mock to ensure clean state
        self.mock_curve_view.update.reset_mock()

        # Call the method
        CenteringZoomService.center_on_selected_point(self.mock_curve_view)

        # Since we're mocking transform_point, we can't easily verify the exact offsets,
        # but we can verify that update was called
        self.mock_curve_view.update.assert_called_once()

    def test_center_on_point(self):
        """Test centering the view on a specific point."""
        # Call the method with a specific point index
        CenteringZoomService.center_on_point(self.mock_curve_view, 2)

        # Verify the point was centered (offsets would be calculated based on point position)
        self.mock_curve_view.update.assert_called_once()

    def test_zoom_to_fit(self):
        """Test zooming to fit all points in the view."""
        # Set up some point data with known bounds
        self.mock_curve_view.points = [(1, 100, 100), (2, 300, 100), (3, 300, 300), (4, 100, 300)]

        # Call the method
        CenteringZoomService.zoom_to_fit(self.mock_curve_view)

        # Verify zoom and update
        self.mock_curve_view.update.assert_called_once()

    def test_toggle_auto_center(self):
        """Test toggling auto-centering."""
        # Initial state
        self.mock_curve_view.auto_center_enabled = False

        # Call the method to toggle on
        result = CenteringZoomService.toggle_auto_center(self.mock_curve_view)

        # Verify auto-center was toggled on
        self.assertTrue(result)
        self.assertTrue(self.mock_curve_view.auto_center_enabled)

        # Call the method to toggle off
        result = CenteringZoomService.toggle_auto_center(self.mock_curve_view)

        # Verify auto-center was toggled off
        self.assertFalse(result)
        self.assertFalse(self.mock_curve_view.auto_center_enabled)


if __name__ == "__main__":
    unittest.main()
