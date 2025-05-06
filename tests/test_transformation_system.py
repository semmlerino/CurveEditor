"""
Tests for the transformation system to validate curve shifting fix.

This module contains tests to verify that the transformation system correctly
prevents curve shifting during operations.
"""

import unittest
import sys
import os
import logging
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.view_state import ViewState
from services.transform import Transform
from services.transformation_service import TransformationService
from services.transform_stabilizer import TransformStabilizer
from services.logging_service import LoggingService

# Configure logging
LoggingService.configure_logging(level=logging.INFO)
logger = LoggingService.get_logger("test_transformation_system")


class TestTransformationSystem(unittest.TestCase):
    """Test cases for the transformation system."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock curve view with necessary properties
        self.curve_view = MagicMock()
        self.curve_view.width.return_value = 800
        self.curve_view.height.return_value = 600
        self.curve_view.zoom_factor = 1.0
        self.curve_view.offset_x = 0
        self.curve_view.offset_y = 0
        self.curve_view.x_offset = 0
        self.curve_view.y_offset = 0
        self.curve_view.flip_y_axis = False
        self.curve_view.image_width = 1920
        self.curve_view.image_height = 1080
        self.curve_view.scale_to_image = True

        # Sample curve data
        self.curve_data = [
            (0, 100.0, 200.0),   # (frame, x, y)
            (1, 110.0, 210.0),
            (2, 120.0, 205.0),
            (3, 130.0, 215.0),
            (4, 140.0, 210.0)
        ]

        # Mock background image
        self.curve_view.background_image = MagicMock()
        self.curve_view.background_image.width.return_value = 1920
        self.curve_view.background_image.height.return_value = 1080

    def test_view_state_creation(self):
        """Test creation of ViewState from curve_view."""
        view_state = ViewState.from_curve_view(self.curve_view)

        # Verify properties were correctly extracted
        self.assertEqual(view_state.widget_width, 800)
        self.assertEqual(view_state.widget_height, 600)
        self.assertEqual(view_state.zoom_factor, 1.0)
        self.assertEqual(view_state.offset_x, 0)
        self.assertEqual(view_state.offset_y, 0)
        self.assertEqual(view_state.manual_x_offset, 0)
        self.assertEqual(view_state.manual_y_offset, 0)
        self.assertEqual(view_state.flip_y_axis, False)
        self.assertEqual(view_state.display_width, 1920)
        self.assertEqual(view_state.display_height, 1080)
        self.assertEqual(view_state.scale_to_image, True)

    def test_transform_creation(self):
        """Test creation of Transform from ViewState."""
        view_state = ViewState.from_curve_view(self.curve_view)
        transform = TransformationService.calculate_transform(view_state)

        # Verify transform parameters
        params = transform.get_parameters()
        self.assertIsNotNone(params['scale'])
        self.assertIsNotNone(params['center_offset'])
        self.assertIsNotNone(params['pan_offset'])
        self.assertIsNotNone(params['manual_offset'])
        self.assertEqual(params['flip_y'], False)

    def test_transform_point_application(self):
        """Test applying a transform to a point."""
        view_state = ViewState.from_curve_view(self.curve_view)
        transform = TransformationService.calculate_transform(view_state)

        # Transform a sample point
        x, y = 100.0, 200.0
        tx, ty = transform.apply(x, y)

        # Verify transformed point is not None
        self.assertIsNotNone(tx)
        self.assertIsNotNone(ty)

        # Transform the point again to verify consistency
        tx2, ty2 = transform.apply(x, y)
        self.assertEqual(tx, tx2)
        self.assertEqual(ty, ty2)

    def test_transform_stability(self):
        """Test that transform remains stable with same view state."""
        view_state1 = ViewState.from_curve_view(self.curve_view)
        transform1 = TransformationService.calculate_transform(view_state1)

        # Create a second transform with the same view state
        view_state2 = ViewState.from_curve_view(self.curve_view)
        transform2 = TransformationService.calculate_transform(view_state2)

        # Apply both transforms to the same point
        x, y = 100.0, 200.0
        tx1, ty1 = transform1.apply(x, y)
        tx2, ty2 = transform2.apply(x, y)

        # Verify both transforms yield the same result
        self.assertEqual(tx1, tx2)
        self.assertEqual(ty1, ty2)

    def test_transform_caching(self):
        """Test that transform caching works."""
        # Clear cache first
        TransformationService.clear_cache()

        # Create two transforms with the same view state
        view_state = ViewState.from_curve_view(self.curve_view)

        # First transform should be calculated and cached
        transform1 = TransformationService.calculate_transform(view_state)

        # Second transform should use cache
        with patch.object(Transform, '__init__', return_value=None) as mock_init:
            transform2 = TransformationService.calculate_transform(view_state)
            # Verify Transform constructor wasn't called again
            mock_init.assert_not_called()

    def test_track_reference_points(self):
        """Test tracking reference points."""
        view_state = ViewState.from_curve_view(self.curve_view)
        transform = TransformationService.calculate_transform(view_state)

        # Track reference points
        reference_points = TransformStabilizer.track_reference_points(self.curve_data, transform)

        # Verify reference points were tracked
        self.assertIn(0, reference_points)  # First point
        self.assertIn(len(self.curve_data)-1, reference_points)  # Last point

    def test_verify_reference_points(self):
        """Test verifying reference points for stability."""
        view_state = ViewState.from_curve_view(self.curve_view)
        transform = TransformationService.calculate_transform(view_state)

        # Track original points
        reference_points = TransformStabilizer.track_reference_points(self.curve_data, transform)

        # Verify with same data (should be stable)
        is_stable = TransformStabilizer.verify_reference_points(
            self.curve_data, reference_points, transform
        )
        self.assertTrue(is_stable)

        # Modify data slightly
        modified_data = self.curve_data.copy()
        modified_data[0] = (0, 100.5, 200.5)  # Small change

        # Verify with modified data and small threshold (should detect change)
        is_stable = TransformStabilizer.verify_reference_points(
            modified_data, reference_points, transform, threshold=0.1
        )
        self.assertFalse(is_stable)

        # Verify with modified data and large threshold (should ignore small change)
        is_stable = TransformStabilizer.verify_reference_points(
            modified_data, reference_points, transform, threshold=10.0
        )
        self.assertTrue(is_stable)

    def test_detect_curve_shifting(self):
        """Test the curve shifting detection method."""
        view_state = ViewState.from_curve_view(self.curve_view)
        transform = TransformationService.calculate_transform(view_state)

        # Modify data to simulate a shift
        modified_data = self.curve_data.copy()
        modified_data[0] = (0, 120.0, 220.0)  # Significant change

        # Detect shifts
        shifted, shifts = TransformationService.detect_curve_shifting(
            self.curve_data, modified_data, transform, transform, threshold=1.0
        )

        # Verify shift detection
        self.assertTrue(shifted)
        self.assertIn(0, shifts)  # First point should be detected as shifted


if __name__ == '__main__':
    unittest.main()
