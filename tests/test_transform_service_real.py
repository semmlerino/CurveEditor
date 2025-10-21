#!/usr/bin/env python
"""
Real integration tests for Transform service without mocking.
Tests actual coordinate transformations and synchronization.
"""

import pytest
from PySide6.QtCore import QPointF

from services.transform_service import Transform, TransformService


class TestTransformReal:
    """Test Transform class with real calculations."""

    def test_transform_creation_with_defaults(self):
        """Test creating transform with required values."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)

        assert transform.scale == 1.0
        assert transform.pan_offset == (0.0, 0.0)
        assert transform.center_offset == (0.0, 0.0)
        assert transform.manual_offset == (0.0, 0.0)
        assert transform.flip_y is False

    def test_data_to_screen_basic(self):
        """Test basic data to screen transformation."""
        transform = Transform(scale=2.0, center_offset_x=100, center_offset_y=100, pan_offset_x=50, pan_offset_y=25)

        # Test transformation
        screen_x, screen_y = transform.data_to_screen(10, 20)

        # Expected: (10 * 2) + 100 + 50 = 170
        # Expected: (20 * 2) + 100 + 25 = 165
        assert screen_x == 170
        assert screen_y == 165

    def test_screen_to_data_inverse(self):
        """Test that screen_to_data is inverse of data_to_screen."""
        transform = Transform(
            scale=2.5,
            center_offset_x=100,
            center_offset_y=50,
            pan_offset_x=30,
            pan_offset_y=20,
            manual_offset_x=10,
            manual_offset_y=5,
        )

        # Test multiple points
        test_points = [(0, 0), (100, 100), (-50, -50), (400, 300)]

        for data_x, data_y in test_points:
            # Transform to screen
            screen_x, screen_y = transform.data_to_screen(data_x, data_y)

            # Transform back to data
            result_x, result_y = transform.screen_to_data(screen_x, screen_y)

            # Should get back original coordinates (within floating point precision)
            assert abs(result_x - data_x) < 0.001
            assert abs(result_y - data_y) < 0.001

    def test_zoom_at_point(self):
        """Test zooming at a specific point (like mouse wheel zoom)."""
        transform = Transform(scale=1.0, center_offset_x=100, center_offset_y=100)

        # Mouse position where zoom happens
        mouse_x, mouse_y = 250, 200

        # Get data position under mouse before zoom
        data_x, data_y = transform.screen_to_data(mouse_x, mouse_y)

        # Apply zoom
        new_scale = 2.0
        new_transform = transform.with_updates(scale=new_scale)

        # Get new screen position of the same data point
        new_screen_x, new_screen_y = new_transform.data_to_screen(data_x, data_y)

        # Calculate pan offset to keep point under mouse
        pan_offset_x = mouse_x - new_screen_x
        pan_offset_y = mouse_y - new_screen_y

        # Apply pan offset
        final_transform = new_transform.with_updates(
            pan_offset_x=transform.pan_offset[0] + pan_offset_x, pan_offset_y=transform.pan_offset[1] + pan_offset_y
        )

        # Verify the point is still under the mouse
        final_x, final_y = final_transform.data_to_screen(data_x, data_y)
        assert abs(final_x - mouse_x) < 0.001
        assert abs(final_y - mouse_y) < 0.001

    def test_flip_y_transformation(self):
        """Test Y-axis flipping for different coordinate systems."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, flip_y=True, display_height=600)

        # Test flipping
        screen_x, screen_y = transform.data_to_screen(100, 100)

        assert screen_x == 100
        assert screen_y == 500  # 600 - 100 = 500

    def test_image_scaling(self):
        """Test image scaling factors."""
        transform = Transform(
            scale=2.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=0.5,
            image_scale_y=0.5,
            scale_to_image=True,
        )

        # With scale_to_image=True, data is first scaled by image factors
        screen_x, screen_y = transform.data_to_screen(100, 100)

        # Expected: (100 * 0.5) * 2 = 100
        assert screen_x == 100
        assert screen_y == 100

    def test_transform_composition(self):
        """Test that all transformation components work together correctly."""
        transform = Transform(
            scale=2.0,
            center_offset_x=50,
            center_offset_y=50,
            pan_offset_x=20,
            pan_offset_y=10,
            manual_offset_x=5,
            manual_offset_y=3,
            image_scale_x=1.5,
            image_scale_y=1.5,
            scale_to_image=True,
        )

        # Test a point
        data_x, data_y = 10, 20
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # Manual calculation:
        # 1. Image scale: 10 * 1.5 = 15, 20 * 1.5 = 30
        # 2. Main scale: 15 * 2 = 30, 30 * 2 = 60
        # 3. Center offset: 30 + 50 = 80, 60 + 50 = 110
        # 4. Pan offset: 80 + 20 = 100, 110 + 10 = 120
        # 5. Manual offset: 100 + 5 = 105, 120 + 3 = 123

        assert screen_x == 105
        assert screen_y == 123


class TestTransformService:
    """Test TransformService."""

    def test_service_creation(self):
        """Test that TransformService can be created."""
        service = TransformService()
        assert service is not None

    def test_create_transform(self):
        """Test creating transforms through service."""
        from services.transform_service import ViewState

        service = TransformService()

        # Create ViewState with correct field names
        view_state = ViewState(
            display_width=800,
            display_height=600,
            widget_width=800,
            widget_height=600,
            zoom_factor=3.0,
            offset_x=150,  # Combined offset
            offset_y=275,
            manual_x_offset=0,
            manual_y_offset=0,
            flip_y_axis=False,
            scale_to_image=True,
            image_width=800,
            image_height=600,
        )

        transform = service.create_transform_from_view_state(view_state)

        # Transform will calculate center offset internally
        assert transform.scale == 3.0

    def test_transform_consistency(self):
        """Test that transform service creates consistent transforms for same parameters."""
        from services.transform_service import ViewState

        service = TransformService()

        # Create same ViewState twice
        view_state1 = ViewState(
            display_width=800,
            display_height=600,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            offset_x=0,
            offset_y=0,
            manual_x_offset=0,
            manual_y_offset=0,
            flip_y_axis=False,
            scale_to_image=True,
            image_width=800,
            image_height=600,
        )

        view_state2 = ViewState(
            display_width=800,
            display_height=600,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            offset_x=0,
            offset_y=0,
            manual_x_offset=0,
            manual_y_offset=0,
            flip_y_axis=False,
            scale_to_image=True,
            image_width=800,
            image_height=600,
        )

        transform1 = service.create_transform_from_view_state(view_state1)
        transform2 = service.create_transform_from_view_state(view_state2)

        # Should create equivalent transforms for same parameters (not cached anymore)
        assert transform1._parameters == transform2._parameters
        assert transform1.scale == transform2.scale

    def test_update_transform(self):
        """Test updating transform parameters."""
        service = TransformService()

        initial = Transform(scale=1.0, center_offset_x=0, center_offset_y=0)
        updated = service.update_transform(initial, scale=2.0, pan_offset_x=50)

        assert updated.scale == 2.0
        assert updated.pan_offset[0] == 50
        assert updated.pan_offset[1] == 0  # Unchanged

    def test_chain_transformations(self):
        """Test chaining multiple transformations."""
        service = TransformService()

        # Start with base transform
        transform = Transform(scale=1.0, center_offset_x=0, center_offset_y=0)

        # Apply a series of transformations
        transform = service.update_transform(transform, scale=2.0)
        transform = service.update_transform(transform, pan_offset_x=100)
        transform = service.update_transform(transform, center_offset_y=50)

        # Test final result
        screen_x, screen_y = service.transform_point_to_screen(transform, 10, 10)

        # Expected: (10 * 2) + 0 + 100 + 0 = 120 (x)
        # Expected: (10 * 2) + 50 + 0 + 0 = 70 (y)
        assert screen_x == 120
        assert screen_y == 70


class TestBackgroundCurveSynchronization:
    """Test that background and curve transformations stay synchronized."""

    def test_background_and_curve_use_same_transform(self):
        """Test that background corners and curve points transform identically."""
        transform = Transform(scale=2.0, center_offset_x=100, center_offset_y=100, pan_offset_x=50, pan_offset_y=25)

        # Background image corners (in data coordinates)
        bg_top_left = (0, 0)
        bg_bottom_right = (800, 600)

        # Curve points (in same data coordinates)
        curve_points = [(100, 100), (400, 300), (700, 500)]

        # Transform background corners
        bg_tl_screen = transform.data_to_screen(*bg_top_left)
        bg_br_screen = transform.data_to_screen(*bg_bottom_right)

        # Transform curve points
        curve_screen = [transform.data_to_screen(x, y) for x, y in curve_points]

        # Background dimensions
        bg_width = bg_br_screen[0] - bg_tl_screen[0]
        bg_height = bg_br_screen[1] - bg_tl_screen[1]

        # Check that background scales correctly
        assert bg_width == 1600  # 800 * 2
        assert bg_height == 1200  # 600 * 2

        # Check that curve points are within background bounds
        for screen_x, screen_y in curve_screen:
            assert bg_tl_screen[0] <= screen_x <= bg_br_screen[0]
            assert bg_tl_screen[1] <= screen_y <= bg_br_screen[1]

    def test_zoom_maintains_synchronization(self):
        """Test that zoom operations keep background and curve synchronized."""
        initial_transform = Transform(scale=1.0, center_offset_x=100, center_offset_y=100)

        # Reference point that should stay fixed during zoom
        zoom_point = (400, 300)  # Center of zoom
        mouse_pos = initial_transform.data_to_screen(*zoom_point)

        # Apply zoom
        zoom_factor = 2.0
        new_scale = initial_transform.scale * zoom_factor

        # Create zoomed transform
        zoomed = initial_transform.with_updates(scale=new_scale)

        # Calculate pan to keep zoom point fixed
        new_pos = zoomed.data_to_screen(*zoom_point)
        pan_x = mouse_pos[0] - new_pos[0]
        pan_y = mouse_pos[1] - new_pos[1]

        # Apply pan
        final = zoomed.with_updates(
            pan_offset_x=initial_transform.pan_offset[0] + pan_x, pan_offset_y=initial_transform.pan_offset[1] + pan_y
        )

        # Verify zoom point hasn't moved
        final_pos = final.data_to_screen(*zoom_point)
        assert abs(final_pos[0] - mouse_pos[0]) < 0.001
        assert abs(final_pos[1] - mouse_pos[1]) < 0.001

        # Verify background and curve scale together
        bg_initial = initial_transform.data_to_screen(800, 600)
        bg_final = final.data_to_screen(800, 600)

        # Verify that background has been transformed
        assert bg_initial != bg_final

        # The ratio won't be exactly zoom_factor due to pan adjustments,
        # but the scaling relationship should be preserved
        curve_initial = initial_transform.data_to_screen(400, 300)
        curve_final = final.data_to_screen(400, 300)

        # This specific point should remain fixed (zoom center)
        assert abs(curve_final[0] - curve_initial[0]) < 0.001
        assert abs(curve_final[1] - curve_initial[1]) < 0.001


class TestQPointFIntegration:
    """Test Transform with Qt QPointF objects."""

    def test_qpointf_transformation(self):
        """Test transforming QPointF objects."""
        transform = Transform(scale=2.0, center_offset_x=50, center_offset_y=50)

        # Create QPointF
        data_point = QPointF(100.5, 200.5)

        # Transform to screen
        screen_point = transform.data_to_screen_qpoint(data_point)

        assert isinstance(screen_point, QPointF)
        assert screen_point.x() == 251.0  # (100.5 * 2) + 50
        assert screen_point.y() == 451.0  # (200.5 * 2) + 50

        # Transform back
        result = transform.screen_to_data_qpoint(screen_point)

        assert abs(result.x() - data_point.x()) < 0.001
        assert abs(result.y() - data_point.y()) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
