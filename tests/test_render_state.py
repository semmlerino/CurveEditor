#!/usr/bin/env python3
"""
Tests for RenderState dataclass - validation and structure.

This test module provides comprehensive coverage of the RenderState dataclass,
testing validation logic, field assignments, defaults, and data integrity.
Follows the testing guide patterns for dataclass and validation testing.
"""

import pytest
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication

from rendering.render_state import RenderState


@pytest.fixture(scope="session")
def qapp():
    """Shared QApplication for all tests."""
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


class TestRenderStateCreation:
    """Test RenderState creation and basic functionality."""

    def test_minimal_valid_creation(self):
        """Test RenderState can be created with minimal valid parameters."""
        points = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        selected_points = {0, 1}

        state = RenderState(
            points=points,
            current_frame=1,
            selected_points=selected_points,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        # Verify core fields
        assert state.points == points
        assert state.current_frame == 1
        assert state.selected_points == selected_points
        assert state.widget_width == 800
        assert state.widget_height == 600
        assert state.zoom_factor == 1.0
        assert state.pan_offset_x == 0.0
        assert state.pan_offset_y == 0.0
        assert state.manual_offset_x == 0.0
        assert state.manual_offset_y == 0.0
        assert state.flip_y_axis is False
        assert state.show_background is True

        # Verify defaults
        assert state.background_image is None
        assert state.background_opacity == 1.0
        assert state.image_width == 0
        assert state.image_height == 0
        assert state.show_grid is True
        assert state.point_radius == 3
        assert state.curves_data is None
        assert state.show_all_curves is False
        assert state.selected_curve_names is None
        assert state.curve_metadata is None
        assert state.active_curve_name is None

    def test_full_creation_with_all_fields(self):
        """Test RenderState creation with all fields specified."""
        points = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        selected_points = {0}
        background_image = QImage(100, 100, QImage.Format.Format_RGB32)
        curves_data = {"curve1": [(1, 10.0, 20.0)], "curve2": [(2, 30.0, 40.0)]}
        selected_curve_names = {"curve1"}
        curve_metadata = {"curve1": {"color": "red"}, "curve2": {"color": "blue"}}

        state = RenderState(
            points=points,
            current_frame=5,
            selected_points=selected_points,
            widget_width=1920,
            widget_height=1080,
            zoom_factor=2.5,
            pan_offset_x=100.0,
            pan_offset_y=200.0,
            manual_offset_x=50.0,
            manual_offset_y=75.0,
            flip_y_axis=True,
            show_background=False,
            background_image=background_image,
            background_opacity=0.7,
            image_width=1920,
            image_height=1080,
            show_grid=False,
            point_radius=5,
            curves_data=curves_data,
            show_all_curves=True,
            selected_curve_names=selected_curve_names,
            curve_metadata=curve_metadata,
            active_curve_name="curve1",
        )

        # Verify all fields are set correctly
        assert state.points == points
        assert state.current_frame == 5
        assert state.selected_points == selected_points
        assert state.widget_width == 1920
        assert state.widget_height == 1080
        assert state.zoom_factor == 2.5
        assert state.pan_offset_x == 100.0
        assert state.pan_offset_y == 200.0
        assert state.manual_offset_x == 50.0
        assert state.manual_offset_y == 75.0
        assert state.flip_y_axis is True
        assert state.show_background is False
        assert state.background_image is background_image
        assert state.background_opacity == 0.7
        assert state.image_width == 1920
        assert state.image_height == 1080
        assert state.show_grid is False
        assert state.point_radius == 5
        assert state.curves_data == curves_data
        assert state.show_all_curves is True
        assert state.selected_curve_names == selected_curve_names
        assert state.curve_metadata == curve_metadata
        assert state.active_curve_name == "curve1"

    def test_creation_with_qpixmap_background(self, qapp):
        """Test RenderState creation with QPixmap background."""
        points = [(1, 100.0, 200.0)]
        selected_points = set()
        background_image = QPixmap(100, 100)

        state = RenderState(
            points=points,
            current_frame=1,
            selected_points=selected_points,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
            background_image=background_image,
        )

        assert state.background_image is background_image
        assert isinstance(state.background_image, QPixmap)


class TestRenderStateValidation:
    """Test RenderState validation logic."""

    def get_valid_base_params(self) -> dict:
        """Get base parameters for valid RenderState creation."""
        return {
            "points": [(1, 100.0, 200.0)],
            "current_frame": 1,
            "selected_points": set(),
            "widget_width": 800,
            "widget_height": 600,
            "zoom_factor": 1.0,
            "pan_offset_x": 0.0,
            "pan_offset_y": 0.0,
            "manual_offset_x": 0.0,
            "manual_offset_y": 0.0,
            "flip_y_axis": False,
            "show_background": True,
        }

    def test_validation_zero_widget_width(self):
        """Test validation fails for zero widget width."""
        params = self.get_valid_base_params()
        params["widget_width"] = 0

        with pytest.raises(ValueError, match="Widget dimensions must be positive"):
            RenderState(**params)

    def test_validation_negative_widget_width(self):
        """Test validation fails for negative widget width."""
        params = self.get_valid_base_params()
        params["widget_width"] = -100

        with pytest.raises(ValueError, match="Widget dimensions must be positive"):
            RenderState(**params)

    def test_validation_zero_widget_height(self):
        """Test validation fails for zero widget height."""
        params = self.get_valid_base_params()
        params["widget_height"] = 0

        with pytest.raises(ValueError, match="Widget dimensions must be positive"):
            RenderState(**params)

    def test_validation_negative_widget_height(self):
        """Test validation fails for negative widget height."""
        params = self.get_valid_base_params()
        params["widget_height"] = -200

        with pytest.raises(ValueError, match="Widget dimensions must be positive"):
            RenderState(**params)

    def test_validation_zero_zoom_factor(self):
        """Test validation fails for zero zoom factor."""
        params = self.get_valid_base_params()
        params["zoom_factor"] = 0.0

        with pytest.raises(ValueError, match="Zoom factor must be positive"):
            RenderState(**params)

    def test_validation_negative_zoom_factor(self):
        """Test validation fails for negative zoom factor."""
        params = self.get_valid_base_params()
        params["zoom_factor"] = -1.5

        with pytest.raises(ValueError, match="Zoom factor must be positive"):
            RenderState(**params)

    def test_validation_zero_point_radius(self):
        """Test validation fails for zero point radius."""
        params = self.get_valid_base_params()
        params["point_radius"] = 0

        with pytest.raises(ValueError, match="Point radius must be positive"):
            RenderState(**params)

    def test_validation_negative_point_radius(self):
        """Test validation fails for negative point radius."""
        params = self.get_valid_base_params()
        params["point_radius"] = -3

        with pytest.raises(ValueError, match="Point radius must be positive"):
            RenderState(**params)

    def test_validation_background_opacity_below_range(self):
        """Test validation fails for background opacity below 0.0."""
        params = self.get_valid_base_params()
        params["background_opacity"] = -0.1

        with pytest.raises(ValueError, match="Background opacity must be between 0.0 and 1.0"):
            RenderState(**params)

    def test_validation_background_opacity_above_range(self):
        """Test validation fails for background opacity above 1.0."""
        params = self.get_valid_base_params()
        params["background_opacity"] = 1.1

        with pytest.raises(ValueError, match="Background opacity must be between 0.0 and 1.0"):
            RenderState(**params)

    def test_validation_boundary_values(self):
        """Test validation passes for boundary values."""
        params = self.get_valid_base_params()

        # Test minimum valid dimensions
        params.update(
            {
                "widget_width": 1,
                "widget_height": 1,
                "zoom_factor": 0.001,  # Very small but positive
                "point_radius": 1,
                "background_opacity": 0.0,  # Minimum opacity
            }
        )

        state = RenderState(**params)
        assert state.widget_width == 1
        assert state.widget_height == 1
        assert state.zoom_factor == 0.001
        assert state.point_radius == 1
        assert state.background_opacity == 0.0

        # Test maximum opacity
        params["background_opacity"] = 1.0
        state = RenderState(**params)
        assert state.background_opacity == 1.0


class TestRenderStateDataTypes:
    """Test RenderState handles various data types correctly."""

    def test_empty_points_list(self):
        """Test RenderState with empty points list."""
        state = RenderState(
            points=[],
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        assert state.points == []
        assert len(state.points) == 0

    def test_empty_selected_points(self):
        """Test RenderState with empty selected points set."""
        state = RenderState(
            points=[(1, 100.0, 200.0)],
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        assert state.selected_points == set()
        assert len(state.selected_points) == 0

    def test_large_selected_points_set(self):
        """Test RenderState with large selected points set."""
        large_selection = set(range(1000))

        state = RenderState(
            points=[(i, float(i), float(i * 2)) for i in range(1000)],
            current_frame=1,
            selected_points=large_selection,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        assert state.selected_points == large_selection
        assert len(state.selected_points) == 1000

    def test_various_point_formats(self):
        """Test RenderState with different point tuple formats."""
        points = [
            (1, 100.0, 200.0),  # 3-tuple
            (2, 150.0, 250.0, "KEYFRAME"),  # 4-tuple with status
            (3, 200.0, 300.0, True),  # 4-tuple with boolean
        ]

        state = RenderState(
            points=points,
            current_frame=1,
            selected_points={0, 2},
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        assert state.points == points
        assert len(state.points) == 3

    def test_floating_point_precision(self):
        """Test RenderState handles floating point values correctly."""
        state = RenderState(
            points=[(1, 3.14159265359, 2.71828182846)],
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.23456789,
            pan_offset_x=-123.456,
            pan_offset_y=987.654,
            manual_offset_x=0.00001,
            manual_offset_y=-0.00001,
            flip_y_axis=False,
            show_background=True,
            background_opacity=0.123456,
        )

        assert state.zoom_factor == 1.23456789
        assert state.pan_offset_x == -123.456
        assert state.pan_offset_y == 987.654
        assert state.manual_offset_x == 0.00001
        assert state.manual_offset_y == -0.00001
        assert state.background_opacity == 0.123456


class TestRenderStateReferenceSharing:
    """Test RenderState reference behavior (dataclass shares references by default)."""

    def test_points_reference_sharing(self):
        """Test that RenderState shares references with input data (current behavior)."""
        original_points = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        points_list = list(original_points)

        state = RenderState(
            points=points_list,
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        # Verify RenderState stores the same reference
        assert state.points is points_list

        # Modify the original list
        points_list.append((3, 300.0, 400.0))

        # RenderState reflects the change (shared reference)
        assert len(state.points) == 3
        assert state.points == points_list

    def test_selected_points_reference_sharing(self):
        """Test that RenderState shares references with input selected points."""
        selection_set = {0, 1, 2}

        state = RenderState(
            points=[(1, 100.0, 200.0)],
            current_frame=1,
            selected_points=selection_set,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        # Verify RenderState stores the same reference
        assert state.selected_points is selection_set

        # Modify the original set
        selection_set.add(5)

        # RenderState reflects the change (shared reference)
        assert len(state.selected_points) == 4
        assert 5 in state.selected_points

    def test_safe_data_passing(self):
        """Test safe way to pass data to RenderState (using copies)."""
        original_points = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        original_selection = {0, 1}

        # Create copies before passing to RenderState
        state = RenderState(
            points=list(original_points),  # Copy the list
            current_frame=1,
            selected_points=set(original_selection),  # Copy the set
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        # Verify data is correct
        assert state.points == original_points
        assert state.selected_points == original_selection

        # Verify independence (different objects)
        assert state.points is not original_points
        assert state.selected_points is not original_selection


class TestRenderStateEquality:
    """Test RenderState equality and comparison behavior."""

    def test_equality_same_values(self):
        """Test that RenderStates with same values are equal."""
        params = {
            "points": [(1, 100.0, 200.0)],
            "current_frame": 1,
            "selected_points": {0},
            "widget_width": 800,
            "widget_height": 600,
            "zoom_factor": 1.0,
            "pan_offset_x": 0.0,
            "pan_offset_y": 0.0,
            "manual_offset_x": 0.0,
            "manual_offset_y": 0.0,
            "flip_y_axis": False,
            "show_background": True,
        }

        state1 = RenderState(**params)
        state2 = RenderState(**params)

        assert state1 == state2

    def test_inequality_different_values(self):
        """Test that RenderStates with different values are not equal."""
        base_params = {
            "points": [(1, 100.0, 200.0)],
            "current_frame": 1,
            "selected_points": {0},
            "widget_width": 800,
            "widget_height": 600,
            "zoom_factor": 1.0,
            "pan_offset_x": 0.0,
            "pan_offset_y": 0.0,
            "manual_offset_x": 0.0,
            "manual_offset_y": 0.0,
            "flip_y_axis": False,
            "show_background": True,
        }

        state1 = RenderState(**base_params)

        # Different zoom factor
        different_params = dict(base_params)
        different_params["zoom_factor"] = 2.0
        state2 = RenderState(**different_params)

        assert state1 != state2


class TestRenderStateEdgeCases:
    """Test RenderState edge cases and unusual inputs."""

    def test_very_large_dimensions(self):
        """Test RenderState with very large widget dimensions."""
        state = RenderState(
            points=[(1, 100.0, 200.0)],
            current_frame=1,
            selected_points=set(),
            widget_width=999999,
            widget_height=999999,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        assert state.widget_width == 999999
        assert state.widget_height == 999999

    def test_very_large_zoom_factor(self):
        """Test RenderState with very large zoom factor."""
        state = RenderState(
            points=[(1, 100.0, 200.0)],
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1000000.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        assert state.zoom_factor == 1000000.0

    def test_negative_current_frame(self):
        """Test RenderState with negative current frame (should be allowed)."""
        state = RenderState(
            points=[(1, 100.0, 200.0)],
            current_frame=-10,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=False,
            show_background=True,
        )

        assert state.current_frame == -10

    def test_negative_offsets(self):
        """Test RenderState with negative pan and manual offsets."""
        state = RenderState(
            points=[(1, 100.0, 200.0)],
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=-1000.0,
            pan_offset_y=-2000.0,
            manual_offset_x=-500.0,
            manual_offset_y=-750.0,
            flip_y_axis=False,
            show_background=True,
        )

        assert state.pan_offset_x == -1000.0
        assert state.pan_offset_y == -2000.0
        assert state.manual_offset_x == -500.0
        assert state.manual_offset_y == -750.0
