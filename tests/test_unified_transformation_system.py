"""
Comprehensive Tests for Unified Transformation System

This module provides thorough testing of the unified transformation system,
validating both functionality and backward compatibility.
"""

import unittest
from unittest.mock import Mock, patch
import math
from typing import List, Tuple

from services.unified_transform import Transform
from services.unified_transformation_service import UnifiedTransformationService
from services.transformation_integration import (
    TransformationIntegration, get_transform, transform_point, transform_points
)
from services.view_state import ViewState


class TestUnifiedTransform(unittest.TestCase):
    """Test the core Transform class functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.basic_transform = Transform(
            scale=1.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y=False,
            display_height=1080,
            image_scale_x=1.0,
            image_scale_y=1.0,
            scale_to_image=False
        )

    def test_basic_transformation(self):
        """Test basic coordinate transformation."""
        # Identity transform should return same coordinates
        result = self.basic_transform.apply(100, 200)
        self.assertEqual(result, (100.0, 200.0))

    def test_scaling_transformation(self):
        """Test scaling transformation."""
        scaled_transform = Transform(
            scale=2.0,
            center_offset_x=0.0,
            center_offset_y=0.0
        )

        result = scaled_transform.apply(100, 200)
        self.assertEqual(result, (200.0, 400.0))

    def test_offset_transformation(self):
        """Test offset transformations."""
        offset_transform = Transform(
            scale=1.0,
            center_offset_x=10.0,
            center_offset_y=20.0,
            pan_offset_x=5.0,
            pan_offset_y=10.0,
            manual_offset_x=2.0,
            manual_offset_y=3.0
        )

        result = offset_transform.apply(100, 200)
        # 100 + 10 + 5 + 2 = 117
        # 200 + 20 + 10 + 3 = 233
        self.assertEqual(result, (117.0, 233.0))

    def test_y_flip_transformation(self):
        """Test Y-axis flipping."""
        flip_transform = Transform(
            scale=1.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            flip_y=True,
            display_height=1080
        )

        result = flip_transform.apply(100, 200)
        # Y should be flipped: 1080 - 200 = 880
        self.assertEqual(result, (100.0, 880.0))

    def test_image_scaling_transformation(self):
        """Test image scaling transformation."""
        image_scale_transform = Transform(
            scale=1.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=2.0,
            image_scale_y=1.5,
            scale_to_image=True
        )

        result = image_scale_transform.apply(100, 200)
        # Image scaling applied first: (100*2, 200*1.5) = (200, 300)
        self.assertEqual(result, (200.0, 300.0))

    def test_complex_transformation_pipeline(self):
        """Test the complete transformation pipeline."""
        complex_transform = Transform(
            scale=0.5,
            center_offset_x=10.0,
            center_offset_y=20.0,
            pan_offset_x=5.0,
            pan_offset_y=10.0,
            manual_offset_x=2.0,
            manual_offset_y=3.0,
            flip_y=True,
            display_height=1080,
            image_scale_x=2.0,
            image_scale_y=1.5,
            scale_to_image=True
        )

        result = complex_transform.apply(100, 200)

        # Manual calculation:
        # 1. Image scaling: (100*2, 200*1.5) = (200, 300)
        # 2. Y-flip: (200, 1080-300) = (200, 780)
        # 3. Main scaling: (200*0.5, 780*0.5) = (100, 390)
        # 4. Center offset: (100+10, 390+20) = (110, 410)
        # 5. Pan offset: (110+5, 410+10) = (115, 420)
        # 6. Manual offset: (115+2, 420+3) = (117, 423)

        self.assertEqual(result, (117.0, 423.0))

    def test_inverse_transformation(self):
        """Test inverse transformation accuracy."""
        transform = Transform(
            scale=1.5,
            center_offset_x=10.0,
            center_offset_y=20.0,
            pan_offset_x=5.0,
            pan_offset_y=10.0
        )

        # Transform and then inverse transform
        original = (100, 200)
        forward = transform.apply(original[0], original[1])
        inverse = transform.apply_inverse(forward[0], forward[1])

        # Should be very close to original (within floating point precision)
        self.assertAlmostEqual(inverse[0], original[0], places=10)
        self.assertAlmostEqual(inverse[1], original[1], places=10)

    def test_inverse_transformation_with_image_scaling(self):
        """Test inverse transformation with image scaling."""
        transform = Transform(
            scale=2.0,
            center_offset_x=50.0,
            center_offset_y=100.0,
            image_scale_x=1.5,
            image_scale_y=2.0,
            scale_to_image=True
        )

        original = (200, 300)
        forward = transform.apply(original[0], original[1])
        inverse = transform.apply_inverse(forward[0], forward[1])

        self.assertAlmostEqual(inverse[0], original[0], places=10)
        self.assertAlmostEqual(inverse[1], original[1], places=10)

    def test_transform_immutability(self):
        """Test that transforms are immutable."""
        transform1 = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        transform2 = transform1.with_updates(scale=2.0)

        # Original should be unchanged
        self.assertEqual(transform1.get_parameters()['scale'], 1.0)
        self.assertEqual(transform2.get_parameters()['scale'], 2.0)
        self.assertNotEqual(transform1, transform2)

    def test_parameter_updates(self):
        """Test parameter updates create correct new instances."""
        original = Transform(
            scale=1.0,
            center_offset_x=10.0,
            center_offset_y=20.0
        )

        updated = original.with_updates(
            scale=2.0,
            center_offset_x=30.0
        )

        params = updated.get_parameters()
        self.assertEqual(params['scale'], 2.0)
        self.assertEqual(params['center_offset_x'], 30.0)
        self.assertEqual(params['center_offset_y'], 20.0)  # Unchanged

    def test_qt_point_transformation(self):
        """Test QPointF transformation."""
        transform = Transform(
            scale=2.0,
            center_offset_x=10.0,
            center_offset_y=20.0
        )

        qt_point = transform.apply_qt_point(100, 200)

        # Should be same as regular apply
        regular_result = transform.apply(100, 200)
        self.assertEqual(qt_point.x(), regular_result[0])
        self.assertEqual(qt_point.y(), regular_result[1])

    def test_image_position_calculation(self):
        """Test background image position calculation."""
        transform = Transform(
            scale=2.0,
            center_offset_x=10.0,
            center_offset_y=20.0,
            pan_offset_x=5.0,
            pan_offset_y=10.0
        )

        img_pos = transform.apply_for_image_position()

        # Should be transformation of (0,0)
        expected = transform.apply(0, 0)
        self.assertEqual(img_pos, expected)

    def test_transform_equality_and_hashing(self):
        """Test transform equality and hash functions."""
        transform1 = Transform(scale=1.0, center_offset_x=10.0, center_offset_y=20.0)
        transform2 = Transform(scale=1.0, center_offset_x=10.0, center_offset_y=20.0)
        transform3 = Transform(scale=2.0, center_offset_x=10.0, center_offset_y=20.0)

        # Equal transforms
        self.assertEqual(transform1, transform2)
        self.assertEqual(hash(transform1), hash(transform2))

        # Different transforms
        self.assertNotEqual(transform1, transform3)
        self.assertNotEqual(hash(transform1), hash(transform3))


class TestUnifiedTransformationService(unittest.TestCase):
    """Test the UnifiedTransformationService functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear cache before each test
        UnifiedTransformationService.clear_cache()

        # Create test view state
        self.test_view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
            scale_to_image=False,
            flip_y_axis=False,
            manual_x_offset=0.0,
            manual_y_offset=0.0
        )

        # Create mock curve view
        self.mock_curve_view = Mock()
        self.mock_curve_view.width.return_value = 800
        self.mock_curve_view.height.return_value = 600
        self.mock_curve_view.zoom_factor = 1.0
        self.mock_curve_view.offset_x = 0.0
        self.mock_curve_view.offset_y = 0.0
        self.mock_curve_view.flip_y_axis = False
        self.mock_curve_view.scale_to_image = False
        self.mock_curve_view.x_offset = 0.0
        self.mock_curve_view.y_offset = 0.0
        self.mock_curve_view.background_image = None
        self.mock_curve_view.image_width = 1920
        self.mock_curve_view.image_height = 1080

    def test_transform_from_view_state(self):
        """Test creating transform from ViewState."""
        transform = UnifiedTransformationService.from_view_state(self.test_view_state)

        self.assertIsInstance(transform, Transform)

        # Test basic transformation
        result = transform.apply(100, 200)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_transform_from_curve_view(self):
        """Test creating transform from curve view."""
        transform = UnifiedTransformationService.from_curve_view(self.mock_curve_view)

        self.assertIsInstance(transform, Transform)

    def test_transform_caching(self):
        """Test transform caching functionality."""
        # First call should create and cache the transform
        transform1 = UnifiedTransformationService.from_view_state(self.test_view_state)

        # Second call should return cached transform
        transform2 = UnifiedTransformationService.from_view_state(self.test_view_state)

        # Should be the same object (cached)
        self.assertIs(transform1, transform2)

        # Cache stats should show one item
        cache_stats = UnifiedTransformationService.get_cache_stats()
        self.assertEqual(cache_stats['cache_size'], 1)

    def test_transform_point(self):
        """Test single point transformation."""
        transform = UnifiedTransformationService.from_view_state(self.test_view_state)
        result = UnifiedTransformationService.transform_point(transform, 100, 200)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_transform_multiple_points(self):
        """Test multiple point transformation."""
        transform = UnifiedTransformationService.from_view_state(self.test_view_state)

        test_points = [
            (0, 100, 200),
            (1, 300, 400),
            (2, 500, 600)
        ]

        results = UnifiedTransformationService.transform_points(transform, test_points)

        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)

    def test_transform_points_qt(self):
        """Test Qt point transformation."""
        transform = UnifiedTransformationService.from_view_state(self.test_view_state)

        test_points = [
            (0, 100, 200),
            (1, 300, 400)
        ]

        qt_results = UnifiedTransformationService.transform_points_qt(transform, test_points)

        self.assertEqual(len(qt_results), 2)
        for qt_point in qt_results:
            self.assertIsInstance(qt_point, type(qt_results[0]))  # QPointF type

    def test_create_stable_transform(self):
        """Test stable transform creation."""
        stable_transform = UnifiedTransformationService.create_stable_transform(
            self.mock_curve_view
        )

        self.assertIsInstance(stable_transform, Transform)

    def test_transformation_drift_detection(self):
        """Test transformation drift detection."""
        transform1 = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        transform2 = Transform(scale=1.0, center_offset_x=5.0, center_offset_y=5.0)

        points_before = [(0, 100, 200), (1, 300, 400)]
        points_after = [(0, 100, 200), (1, 300, 400)]

        drift_detected, drift_details = UnifiedTransformationService.detect_transformation_drift(
            points_before, points_after, transform1, transform2, threshold=1.0
        )

        # Should detect drift due to different transforms
        self.assertTrue(drift_detected)
        self.assertGreater(len(drift_details), 0)

    def test_cache_size_management(self):
        """Test cache size management."""
        # Create many different view states to test cache management
        for i in range(25):  # More than max cache size
            view_state = ViewState(
                display_width=1920 + i,  # Make each unique
                display_height=1080,
                widget_width=800,
                widget_height=600
            )
            UnifiedTransformationService.from_view_state(view_state)

        # Cache should not exceed max size
        cache_stats = UnifiedTransformationService.get_cache_stats()
        self.assertLessEqual(cache_stats['cache_size'], cache_stats['max_cache_size'])

    def test_clear_cache(self):
        """Test cache clearing."""
        # Create a transform to populate cache
        UnifiedTransformationService.from_view_state(self.test_view_state)

        # Verify cache has items
        cache_stats = UnifiedTransformationService.get_cache_stats()
        self.assertGreater(cache_stats['cache_size'], 0)

        # Clear cache
        UnifiedTransformationService.clear_cache()

        # Verify cache is empty
        cache_stats = UnifiedTransformationService.get_cache_stats()
        self.assertEqual(cache_stats['cache_size'], 0)

    def test_backward_compatibility(self):
        """Test backward compatibility with legacy interface."""
        result = UnifiedTransformationService.transform_point_to_widget(
            self.mock_curve_view, 100, 200
        )

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_parameter_overrides(self):
        """Test parameter overrides in legacy compatibility method."""
        result = UnifiedTransformationService.transform_point_to_widget(
            self.mock_curve_view, 100, 200,
            display_width=1000,
            display_height=800,
            offset_x=10,
            offset_y=20,
            scale=2.0
        )

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_stable_transformation_context(self):
        """Test stable transformation context manager."""
        # Mock a curve view with points
        self.mock_curve_view.points = [
            (0, 100, 200),
            (1, 300, 400),
            (2, 500, 600)
        ]

        with UnifiedTransformationService.stable_transformation_context(
            self.mock_curve_view
        ) as stable_transform:
            self.assertIsInstance(stable_transform, Transform)

            # Modify the points slightly
            self.mock_curve_view.points[1] = (1, 305, 405)

        # Context should complete without errors


class TestTransformationIntegration(unittest.TestCase):
    """Test the transformation integration layer."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_curve_view = Mock()
        self.mock_curve_view.width.return_value = 800
        self.mock_curve_view.height.return_value = 600
        self.mock_curve_view.zoom_factor = 1.0
        self.mock_curve_view.offset_x = 0.0
        self.mock_curve_view.offset_y = 0.0
        self.mock_curve_view.flip_y_axis = False
        self.mock_curve_view.scale_to_image = False
        self.mock_curve_view.x_offset = 0.0
        self.mock_curve_view.y_offset = 0.0
        self.mock_curve_view.background_image = None
        self.mock_curve_view.image_width = 1920
        self.mock_curve_view.image_height = 1080

    def test_get_transform(self):
        """Test get_transform convenience function."""
        transform = get_transform(self.mock_curve_view)
        self.assertIsInstance(transform, Transform)

    def test_transform_point(self):
        """Test transform_point convenience function."""
        result = transform_point(self.mock_curve_view, 100, 200)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_transform_points(self):
        """Test transform_points convenience function."""
        test_points = [(0, 100, 200), (1, 300, 400)]
        results = transform_points(self.mock_curve_view, test_points)

        self.assertEqual(len(results), 2)
        # Results should be QPointF objects
        for result in results:
            self.assertTrue(hasattr(result, 'x'))
            self.assertTrue(hasattr(result, 'y'))

    def test_installation(self):
        """Test unified system installation."""
        from services.transformation_integration import install_unified_system

        # Install the system
        install_unified_system(self.mock_curve_view)

        # Check that methods were added
        self.assertTrue(hasattr(self.mock_curve_view, 'get_transform'))
        self.assertTrue(hasattr(self.mock_curve_view, 'transform_point'))
        self.assertTrue(hasattr(self.mock_curve_view, 'transform_point_qt'))
        self.assertTrue(hasattr(self.mock_curve_view, '_unified_transform_installed'))

    def test_legacy_compatibility(self):
        """Test legacy compatibility methods."""
        result = TransformationIntegration.transform_point_legacy(
            self.mock_curve_view, 100, 200
        )

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)


class TestViewStateIntegration(unittest.TestCase):
    """Test ViewState integration with the unified system."""

    def test_view_state_from_curve_view(self):
        """Test ViewState creation from curve view."""
        mock_curve_view = Mock()
        mock_curve_view.width.return_value = 800
        mock_curve_view.height.return_value = 600
        mock_curve_view.zoom_factor = 1.5
        mock_curve_view.offset_x = 10.0
        mock_curve_view.offset_y = 20.0
        mock_curve_view.flip_y_axis = True
        mock_curve_view.scale_to_image = True
        mock_curve_view.x_offset = 5.0
        mock_curve_view.y_offset = 15.0
        mock_curve_view.background_image = None
        mock_curve_view.image_width = 1920
        mock_curve_view.image_height = 1080

        view_state = ViewState.from_curve_view(mock_curve_view)

        self.assertEqual(view_state.widget_width, 800)
        self.assertEqual(view_state.widget_height, 600)
        self.assertEqual(view_state.zoom_factor, 1.5)
        self.assertEqual(view_state.offset_x, 10.0)
        self.assertEqual(view_state.offset_y, 20.0)
        self.assertEqual(view_state.flip_y_axis, True)
        self.assertEqual(view_state.scale_to_image, True)
        self.assertEqual(view_state.manual_x_offset, 5.0)
        self.assertEqual(view_state.manual_y_offset, 15.0)


if __name__ == '__main__':
    # Set up test logging
    import logging
    logging.basicConfig(level=logging.INFO)

    # Run tests
    unittest.main(verbosity=2)
