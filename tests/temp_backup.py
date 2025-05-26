"""
Unit tests for the VisualizationService class.
"""

from typing import cast
from unittest.mock import patch, MagicMock
import unittest

from PySide6.QtGui import QColor

from services.centering_zoom_service import CenteringZoomService
from services.protocols import PointsList
from services.visualization_service import VisualizationService, logger

class TestVisualizationService(unittest.TestCase):
    """Test cases for the VisualizationService class."""

    def setUp(self):
        """Set up test fixtures for each test."""
        # Create mock objects for CurveView
        self.mock_curve_view = MagicMock()

        # Configure curve view mock with basic properties (using float values for coordinates)
        self.mock_curve_view.points = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]
        self.mock_curve_view.curve_data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]
        self.mock_curve_view.selected_points = {1}
        self.mock_curve_view.selected_point_idx = 1
        self.mock_curve_view.zoom_factor = 1.0
        self.mock_curve_view.offset_x = 0
        self.mock_curve_view.offset_y = 0
        self.mock_curve_view.show_grid = False
        self.mock_curve_view.show_background = True
        self.mock_curve_view.show_velocity_vectors = False
        self.mock_curve_view.show_all_frame_numbers = False
        self.mock_curve_view.show_crosshair = False
        self.mock_curve_view.background_opacity = 0.5
        self.mock_curve_view.point_radius = 5
        self.mock_curve_view.grid_color = QColor(100, 100, 100)
        self.mock_curve_view.grid_line_width = 1
        self.mock_curve_view.image_width = 1920
        self.mock_curve_view.image_height = 1080
        self.mock_curve_view.width.return_value = 800
        self.mock_curve_view.height.return_value = 600

        # Set up frame marker and timeline slider mocks
        self.mock_curve_view.frame_marker_label = MagicMock()
        self.mock_curve_view.timeline_slider = MagicMock()
        self.mock_curve_view.timeline_slider.minimum.return_value = 1
        self.mock_curve_view.timeline_slider.maximum.return_value = 100

    def test_toggle_background_visible(self):
        """Test toggling background image visibility."""
        # Test turning off the background
        VisualizationService.toggle_background_visible(self.mock_curve_view, False)
        self.assertFalse(self.mock_curve_view.show_background)
        self.mock_curve_view.update.assert_called_once()

        # Reset the mock and test turning on
        self.mock_curve_view.update.reset_mock()
        VisualizationService.toggle_background_visible(self.mock_curve_view, True)
        self.assertTrue(self.mock_curve_view.show_background)
        self.mock_curve_view.update.assert_called_once()

    def test_toggle_grid(self):
        """Test toggling grid visibility."""
        # Test with explicit parameter
        VisualizationService.toggle_grid(self.mock_curve_view, True)
        self.assertTrue(self.mock_curve_view.show_grid)
        self.mock_curve_view.update.assert_called_once()

        # Reset the mock
        self.mock_curve_view.update.reset_mock()

        # Test with None parameter (toggle current state)
        VisualizationService.toggle_grid(self.mock_curve_view, None)
        self.assertFalse(self.mock_curve_view.show_grid)  # Should toggle from True to False
        self.mock_curve_view.update.assert_called_once()

    def test_toggle_velocity_vectors(self):
        """Test toggling velocity vectors."""
        VisualizationService.toggle_velocity_vectors(self.mock_curve_view, True)
        self.assertTrue(self.mock_curve_view.show_velocity_vectors)
        self.mock_curve_view.update.assert_called_once()

    def test_toggle_all_frame_numbers(self):
        """Test toggling all frame numbers."""
        VisualizationService.toggle_all_frame_numbers(self.mock_curve_view, True)
        self.assertTrue(self.mock_curve_view.show_all_frame_numbers)
        self.mock_curve_view.update.assert_called_once()

    def test_toggle_crosshair(self):
        """Test toggling crosshair."""
        VisualizationService.toggle_crosshair(self.mock_curve_view, True)
        self.assertTrue(self.mock_curve_view.show_crosshair)
        self.mock_curve_view.update.assert_called_once()

    def test_toggle_crosshair_internal(self):
        """Test the internal crosshair toggle method."""
        # This method is a wrapper, so we patch the toggle_crosshair method
        with patch.object(VisualizationService, 'toggle_crosshair') as mock_toggle:
            VisualizationService.toggle_crosshair_internal(self.mock_curve_view, True)
            mock_toggle.assert_called_once_with(self.mock_curve_view, True)

    def test_set_background_opacity(self):
        """Test setting background opacity."""
        # Test with valid value
        VisualizationService.set_background_opacity(self.mock_curve_view, 0.75)
        self.assertEqual(self.mock_curve_view.background_opacity, 0.75)
        self.mock_curve_view.update.assert_called_once()

        # Reset the mock
        self.mock_curve_view.update.reset_mock()

        # Test with value too high (should clamp to 1.0)
        VisualizationService.set_background_opacity(self.mock_curve_view, 1.5)
        self.assertEqual(self.mock_curve_view.background_opacity, 1.0)
        self.mock_curve_view.update.assert_called_once()

        # Reset the mock
        self.mock_curve_view.update.reset_mock()

        # Test with value too low (should clamp to 0.0)
        VisualizationService.set_background_opacity(self.mock_curve_view, -0.5)
        self.assertEqual(self.mock_curve_view.background_opacity, 0.0)
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
        self.mock_curve_view.update.assert_called_once()

    def test_set_point_radius(self):
        """Test setting point radius."""
        # Test with valid value
        VisualizationService.set_point_radius(self.mock_curve_view, 8)
        self.assertEqual(self.mock_curve_view.point_radius, 8)
        self.mock_curve_view.update.assert_called_once()

        # Reset the mock
        self.mock_curve_view.update.reset_mock()

        # Test with value too low (should clamp to 1)
        VisualizationService.set_point_radius(self.mock_curve_view, 0)
        self.assertEqual(self.mock_curve_view.point_radius, 1)
        self.mock_curve_view.update.assert_called_once()

    def test_set_grid_color(self):
        """Test setting grid color."""
        new_color = QColor(255, 0, 0)  # Red
        VisualizationService.set_grid_color(self.mock_curve_view, new_color)
        self.assertEqual(self.mock_curve_view.grid_color, new_color)
        self.mock_curve_view.update.assert_called_once()

    def test_set_grid_line_width(self):
        """Test setting grid line width."""
        # Test with valid value
        VisualizationService.set_grid_line_width(self.mock_curve_view, 3)
        self.assertEqual(self.mock_curve_view.grid_line_width, 3)
        self.mock_curve_view.update.assert_called_once()

        # Reset the mock
        self.mock_curve_view.update.reset_mock()

        # Test with value too low (should clamp to 1)
        VisualizationService.set_grid_line_width(self.mock_curve_view, 0)
        self.assertEqual(self.mock_curve_view.grid_line_width, 1)
        self.mock_curve_view.update.assert_called_once()

    @patch('re.search')
    @patch('os.path.basename')
    def test_update_timeline_for_image_valid(self, mock_basename: MagicMock, mock_re_search: MagicMock):
        """Test updating timeline for a valid image."""
        # Mock the basename function to return a filename
        mock_basename.return_value = "frame_042.jpg"

        # Mock the regex search to return a match
        mock_match = MagicMock()
        mock_match.group.return_value = "42"
        mock_re_search.return_value = mock_match

        # Mock methods used by the function
        with patch.object(VisualizationService, 'update_frame_marker_position') as mock_update_marker:
            # Call the method with valid data
            image_filenames = ["path/to/frame_042.jpg"]
            VisualizationService.update_timeline_for_image(0, self.mock_curve_view, image_filenames)

            # Verify it called update_frame_marker_position with the correct frame
            mock_update_marker.assert_called_once_with(self.mock_curve_view, 42)

            # Verify it updated the selected point
            self.assertIn(self.mock_curve_view.update.call_count, [1, 2])

    def test_update_timeline_for_image_empty_list(self):
        """Test updating timeline with an empty list."""
        with patch.object(logger, 'warning') as mock_logger:
            VisualizationService.update_timeline_for_image(0, self.mock_curve_view, [])
            mock_logger.assert_called_once_with("No image filenames available")

    def test_update_timeline_for_image_invalid_index(self):
        """Test updating timeline with an invalid index."""
        with patch.object(logger, 'warning') as mock_logger:
            VisualizationService.update_timeline_for_image(5, self.mock_curve_view, ["frame_001.jpg"])
            mock_logger.assert_called_once_with("Invalid index 5")

    def test_update_frame_marker_position(self):
        """Test updating the frame marker position."""
        # Call the method with a frame number
        VisualizationService.update_frame_marker_position(self.mock_curve_view, 42)

        # Verify the tooltip was set correctly
        self.mock_curve_view.frame_marker_label.setToolTip.assert_called_once_with("Frame: 42")

    def test_set_points_preserve_view(self):
        """Test setting points while preserving the view."""
        # Set initial state
        self.mock_curve_view.zoom_factor = 2.0
        self.mock_curve_view.offset_x = 100
        self.mock_curve_view.offset_y = 50

        # New points to set
        new_points = [(10, 300, 400), (20, 350, 450), (30, 400, 500)]

        # Call the method with preserve_view=True
        VisualizationService.set_points(
            self.mock_curve_view, cast(PointsList, new_points), 1920, 1080, preserve_view=True
        )

        # Verify view state was preserved
        self.assertEqual(self.mock_curve_view.zoom_factor, 2.0)
        self.assertEqual(self.mock_curve_view.offset_x, 100)
        self.assertEqual(self.mock_curve_view.offset_y, 50)

        # Verify points were updated
        self.assertEqual(self.mock_curve_view.points, new_points)
        self.assertEqual(self.mock_curve_view.image_width, 1920)
        self.assertEqual(self.mock_curve_view.image_height, 1080)

        # Verify update was called
        self.mock_curve_view.update.assert_called_once()

    def test_set_points_reset_view(self):
        """Test setting points while resetting the view."""
        # Set initial state
        self.mock_curve_view.zoom_factor = 2.0
        self.mock_curve_view.offset_x = 100
        self.mock_curve_view.offset_y = 50

        # New points to set
        new_points = [(10, 300, 400), (20, 350, 450), (30, 400, 500)]

        # Patch the reset_view method to verify it's called
        with patch.object(CenteringZoomService, 'reset_view') as mock_reset_view:
            # Call the method with preserve_view=False
            VisualizationService.set_points(
                self.mock_curve_view, cast(PointsList, new_points), 1920, 1080, preserve_view=False
            )

            # Verify reset_view was called
            mock_reset_view.assert_called_once_with(self.mock_curve_view)

            # Verify points were updated
            self.assertEqual(self.mock_curve_view.points, new_points)
            self.assertEqual(self.mock_curve_view.image_width, 1920)
            self.assertEqual(self.mock_curve_view.image_height, 1080)

            # Verify update was called
            self.mock_curve_view.update.assert_called_once()

    def test_jump_to_frame_by_click(self):
        """Test jumping to a frame by clicking (placeholder method)."""
        # This is a placeholder method in the service, so we just need to ensure it doesn't break
        VisualizationService.jump_to_frame_by_click(self.mock_curve_view, 50)

        # No assertions needed as the method is empty, just ensuring it doesn't raise exceptions

    def test_center_on_selected_point_from_main_window(self):
        """Test centering on selected point from main window."""
        # Create a mock main window
        mock_main_window = MagicMock()
        mock_main_window.curve_view = self.mock_curve_view

        # Patch the centering method to verify it's called
        with patch.object(CenteringZoomService, 'center_on_selected_point') as mock_center:
            VisualizationService.center_on_selected_point_from_main_window(mock_main_window)
            mock_center.assert_called_once_with(self.mock_curve_view)

    def test_center_on_selected_point_from_main_window_no_curve_view(self):
        """Test when no curve view is available."""
        # Create a mock main window without a curve view
        mock_main_window = MagicMock()
        mock_main_window.curve_view = None

        # Verify it handles the error gracefully
        with patch.object(logger, 'warning') as mock_logger:
            VisualizationService.center_on_selected_point_from_main_window(mock_main_window)
            mock_logger.assert_called_once_with("Cannot center: no curve view available.")


if __name__ == '__main__':
    unittest.main()
