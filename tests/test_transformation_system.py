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
from services.unified_transform import Transform
from services.unified_transformation_service import UnifiedTransformationService
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
        transform = UnifiedTransformationService.from_view_state(view_state)

        # Verify transform parameters
        params = transform.get_parameters()
        self.assertIsNotNone(params['scale'])
        self.assertIsNotNone(params['center_offset_x'])
        self.assertIsNotNone(params['center_offset_y'])
        self.assertIsNotNone(params['pan_offset_x'])
        self.assertIsNotNone(params['pan_offset_y'])
        self.assertIsNotNone(params['manual_offset_x'])
        self.assertIsNotNone(params['manual_offset_y'])
        self.assertEqual(params['flip_y'], False)

    def test_transform_application(self):
        """Test application of Transform to points."""
        view_state = ViewState.from_curve_view(self.curve_view)
        transform = UnifiedTransformationService.from_view_state(view_state)

        # Test application to point
        tx, ty = transform.apply(1.0, 2.0)
        
        # Verify transformation results are valid
        self.assertIsNotNone(tx)
        self.assertIsNotNone(ty)
        
        # Test application to another point
        tx2, ty2 = transform.apply(3.0, 4.0)
        self.assertNotEqual(tx, tx2)
        self.assertNotEqual(ty, ty2)

    def test_transform_stability(self):
        """Test that transform remains stable with same view state."""
        view_state1 = ViewState.from_curve_view(self.curve_view)
        transform1 = UnifiedTransformationService.from_view_state(view_state1)

        # Create a second transform with the same view state
        view_state2 = ViewState.from_curve_view(self.curve_view)
        transform2 = UnifiedTransformationService.from_view_state(view_state2)

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
        UnifiedTransformationService.clear_cache()

        # Create two transforms with the same view state
        view_state = ViewState.from_curve_view(self.curve_view)

        # First transform should be calculated and cached
        first_transform = UnifiedTransformationService.from_view_state(view_state)
        # Verify the first transform is valid
        self.assertIsNotNone(first_transform)

        # Second transform should use cache
        with patch.object(Transform, '__init__', return_value=None) as mock_init:
            second_transform = UnifiedTransformationService.from_view_state(view_state)
            # Verify the second transform is valid
            self.assertIsNotNone(second_transform)
            # Verify Transform constructor wasn't called again
            mock_init.assert_not_called()

    def test_transformation_drift(self):
        """Test detecting transformation drift between points."""
        view_state = ViewState.from_curve_view(self.curve_view)
        transform = UnifiedTransformationService.from_view_state(view_state)

        # Create before and after points
        before_points = self.curve_data.copy()
        after_points = self.curve_data.copy()
        after_points[0] = (0, 120.0, 220.0)  # Significant change to first point
        
        # Detect drift
        drift_report = UnifiedTransformationService.detect_transformation_drift(
            before_points, after_points, transform, transform
        )
        
        # Verify drift detection
        self.assertGreater(len(drift_report), 0)  # Should detect drift
        self.assertIn(0, drift_report)  # Should identify first point
        self.assertGreater(drift_report[0], 1.0)  # Drift should be significant
        
    def test_stable_transformation_context(self):
        """Test the stable transformation context manager."""
        # Create a transform through the context manager
        with UnifiedTransformationService.stable_transformation_context(self.curve_view) as transform:
            # Verify we got a valid transform
            self.assertIsNotNone(transform)
            
            # Test that the transform works properly
            tx, ty = transform.apply(100.0, 200.0)
            self.assertIsNotNone(tx)
            self.assertIsNotNone(ty)


if __name__ == '__main__':
    unittest.main()
