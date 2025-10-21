#!/usr/bin/env python3
"""
Comprehensive tests for the TransformService module.

This test suite verifies the functionality of the TransformService, ViewState, and Transform classes,
which handle all coordinate transformations and view state management in the application.
These classes are critical for mapping between data space and screen space coordinates.

Note on Transform Pattern:
    Many tests use the 2-step pattern to test view state manipulation explicitly.
    For NEW production code, use: transform = transform_service.get_transform(view)
    See CLAUDE.md "Transform Service Pattern" for guidance.
"""

import math
import os
import sys
from typing import Any

import pytest
from pytestqt.qtbot import QtBot

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import classes directly to avoid service initialization issues
from PySide6.QtCore import QPointF

from services.transform_service import Transform, TransformService, ViewState


class TestViewState:
    """Test suite for ViewState class."""

    def _create_curve_view(self, qtbot: QtBot, **overrides: Any):
        """Factory method to create curve view with custom properties."""
        from ui.curve_view_widget import CurveViewWidget

        curve_view = CurveViewWidget()
        qtbot.addWidget(curve_view)

        # Set default test properties
        defaults = {
            "width": 800,
            "height": 600,
            "image_width": 1920,
            "image_height": 1080,
            "zoom_factor": 1.0,
            "pan_offset_x": 0.0,
            "pan_offset_y": 0.0,
            "scale_to_image": True,
            "flip_y_axis": False,
            "manual_offset_x": 0.0,
            "manual_offset_y": 0.0,
            "background_image": None,
        }

        # Apply defaults and overrides
        config = {**defaults, **overrides}

        # Set widget size - ensure values are not None
        width = config["width"]
        height = config["height"]
        if width is not None and height is not None:
            curve_view.resize(int(width), int(height))

        # Set properties
        for key, value in config.items():
            if key not in ["width", "height"]:
                setattr(curve_view, key, value)

        return curve_view

    @pytest.fixture
    def basic_view_state(self) -> ViewState:
        """Create a basic ViewState for testing."""
        return ViewState(display_width=1920, display_height=1080, widget_width=800, widget_height=600)

    @pytest.fixture
    def complex_view_state(self) -> ViewState:
        """Create a ViewState with complex parameters for testing."""
        return ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            offset_x=100.0,
            offset_y=50.0,
            scale_to_image=True,
            flip_y_axis=True,
            manual_x_offset=25.0,
            manual_y_offset=30.0,
            image_width=1280,
            image_height=720,
        )

    def test_view_state_initialization_defaults(self, basic_view_state: ViewState) -> None:
        """Test ViewState initialization with default values."""
        # Check required parameters
        assert basic_view_state.display_width == 1920
        assert basic_view_state.display_height == 1080
        assert basic_view_state.widget_width == 800
        assert basic_view_state.widget_height == 600

        # Check default values
        assert basic_view_state.zoom_factor == 1.0
        assert basic_view_state.offset_x == 0.0
        assert basic_view_state.offset_y == 0.0
        assert basic_view_state.scale_to_image is True
        assert basic_view_state.flip_y_axis is False
        assert basic_view_state.manual_x_offset == 0.0
        assert basic_view_state.manual_y_offset == 0.0
        assert basic_view_state.background_image is None
        assert basic_view_state.image_width == 1920
        assert basic_view_state.image_height == 1080

    def test_view_state_initialization_custom_values(self, complex_view_state: ViewState) -> None:
        """Test ViewState initialization with custom values."""
        assert complex_view_state.zoom_factor == 2.0
        assert complex_view_state.offset_x == 100.0
        assert complex_view_state.offset_y == 50.0
        assert complex_view_state.scale_to_image is True
        assert complex_view_state.flip_y_axis is True
        assert complex_view_state.manual_x_offset == 25.0
        assert complex_view_state.manual_y_offset == 30.0
        assert complex_view_state.image_width == 1280
        assert complex_view_state.image_height == 720

    def test_view_state_immutability(self, basic_view_state: ViewState) -> None:
        """Test that ViewState is truly immutable."""
        # ViewState should be frozen (dataclass with frozen=True)
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
            basic_view_state.zoom_factor = 2.0  # pyright: ignore[reportAttributeAccessIssue]

    def test_view_state_with_updates(self, basic_view_state: ViewState) -> None:
        """Test creating a new ViewState with updated values."""
        updated_state = basic_view_state.with_updates(
            zoom_factor=2.0, offset_x=100.0, offset_y=50.0, scale_to_image=False
        )

        # Check updated values in new instance
        assert updated_state.zoom_factor == 2.0
        assert updated_state.offset_x == 100.0
        assert updated_state.offset_y == 50.0
        assert updated_state.scale_to_image is False

        # Check original is unchanged (immutability)
        assert basic_view_state.zoom_factor == 1.0
        assert basic_view_state.offset_x == 0.0
        assert basic_view_state.offset_y == 0.0
        assert basic_view_state.scale_to_image is True

        # Check unchanged values are preserved
        assert updated_state.display_width == basic_view_state.display_width
        assert updated_state.display_height == basic_view_state.display_height
        assert updated_state.widget_width == basic_view_state.widget_width
        assert updated_state.widget_height == basic_view_state.widget_height

    def test_view_state_to_dict(self, complex_view_state: ViewState) -> None:
        """Test converting ViewState to dictionary representation."""
        state_dict = complex_view_state.to_dict()

        assert state_dict["display_dimensions"] == (1920, 1080)
        assert state_dict["widget_dimensions"] == (800, 600)
        assert state_dict["image_dimensions"] == (1280, 720)
        assert state_dict["zoom_factor"] == 2.0
        assert state_dict["offset"] == (100.0, 50.0)
        assert state_dict["scale_to_image"] is True
        assert state_dict["flip_y_axis"] is True
        assert state_dict["manual_offset"] == (25.0, 30.0)
        assert state_dict["has_background_image"] is False

    def test_view_state_from_curve_view_legacy(self, qtbot) -> None:
        """Test creating ViewState from a real CurveView widget (legacy test converted)."""
        # Create a real curve view with specific test configuration
        curve_view = self._create_curve_view(
            qtbot,
            width=800,
            height=600,
            image_width=1920,
            image_height=1080,
            zoom_factor=1.5,
            pan_offset_x=75.0,
            pan_offset_y=25.0,
            scale_to_image=True,
            flip_y_axis=False,
            manual_offset_x=10.0,
            manual_offset_y=15.0,
            background_image=None,
        )

        view_state = ViewState.from_curve_view(curve_view)  # pyright: ignore[reportArgumentType]

        assert view_state.widget_width == 800
        assert view_state.widget_height == 600
        assert view_state.image_width == 1920
        assert view_state.image_height == 1080
        assert view_state.zoom_factor == 1.5
        assert view_state.offset_x == 75.0
        assert view_state.offset_y == 25.0
        assert view_state.scale_to_image is True
        assert view_state.flip_y_axis is False
        assert view_state.manual_x_offset == 10.0
        assert view_state.manual_y_offset == 15.0
        assert view_state.background_image is None

    def test_view_state_from_curve_view_with_background_image(self, qtbot) -> None:
        """Test creating ViewState from CurveView with real background image."""
        from PySide6.QtGui import QColor, QImage

        # Create a real test background image
        background_image = QImage(2560, 1440, QImage.Format.Format_RGB32)
        background_image.fill(QColor(128, 128, 128))  # Fill with gray

        # Create curve view with real background image
        curve_view = self._create_curve_view(
            qtbot, width=800, height=600, image_width=1920, image_height=1080, background_image=background_image
        )

        view_state = ViewState.from_curve_view(curve_view)  # pyright: ignore[reportArgumentType]

        # Display dimensions should match background image
        assert view_state.display_width == 2560
        assert view_state.display_height == 1440
        # Image dimensions remain unchanged
        assert view_state.image_width == 1920
        assert view_state.image_height == 1080
        # Background image should be preserved
        assert view_state.background_image is background_image

    @pytest.mark.parametrize(
        "width,height",
        [
            (0, 0),  # Zero dimensions
            (1, 1),  # Minimal dimensions
            (3840, 2160),  # 4K dimensions
            (7680, 4320),  # 8K dimensions
        ],
    )
    def test_view_state_edge_case_dimensions(self, width: int, height: int) -> None:
        """Test ViewState with edge case dimensions."""
        view_state = ViewState(display_width=width, display_height=height, widget_width=width, widget_height=height)

        assert view_state.display_width == width
        assert view_state.display_height == height
        assert view_state.widget_width == width
        assert view_state.widget_height == height


class TestTransform:
    """Test suite for Transform class."""

    @pytest.fixture
    def basic_transform(self) -> Transform:
        """Create a basic Transform for testing."""
        return Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)

    @pytest.fixture
    def complex_transform(self) -> Transform:
        """Create a complex Transform for testing."""
        return Transform(
            scale=2.0,
            center_offset_x=100.0,
            center_offset_y=50.0,
            pan_offset_x=25.0,
            pan_offset_y=30.0,
            manual_offset_x=10.0,
            manual_offset_y=15.0,
            flip_y=True,
            display_height=1080,
            image_scale_x=1.5,
            image_scale_y=1.2,
            scale_to_image=True,
        )

    def test_transform_initialization(self, basic_transform: Transform) -> None:
        """Test Transform initialization with basic parameters."""
        assert basic_transform.scale == 1.0
        assert basic_transform.center_offset == (0.0, 0.0)
        assert basic_transform.pan_offset == (0.0, 0.0)
        assert basic_transform.manual_offset == (0.0, 0.0)
        assert basic_transform.flip_y is False
        assert basic_transform.display_height == 0
        assert basic_transform.image_scale == (1.0, 1.0)
        assert basic_transform.scale_to_image is True

    def test_transform_complex_initialization(self, complex_transform: Transform) -> None:
        """Test Transform initialization with complex parameters."""
        assert complex_transform.scale == 2.0
        assert complex_transform.center_offset == (100.0, 50.0)
        assert complex_transform.pan_offset == (25.0, 30.0)
        assert complex_transform.manual_offset == (10.0, 15.0)
        assert complex_transform.flip_y is True
        assert complex_transform.display_height == 1080
        assert complex_transform.image_scale == (1.5, 1.2)
        assert complex_transform.scale_to_image is True

    def test_transform_stability_hash(self, basic_transform: Transform) -> None:
        """Test Transform stability hash for caching."""
        hash1 = basic_transform.stability_hash
        assert isinstance(hash1, str)
        assert len(hash1) == 32  # MD5 hash length

        # Create identical transform
        identical_transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        assert identical_transform.stability_hash == hash1

        # Create different transform
        different_transform = Transform(scale=2.0, center_offset_x=0.0, center_offset_y=0.0)
        assert different_transform.stability_hash != hash1

    @pytest.mark.parametrize(
        "data_x,data_y",
        [
            (0.0, 0.0),  # Origin
            (100.0, 200.0),  # Positive coordinates
            (-100.0, -200.0),  # Negative coordinates
            (1e6, 1e6),  # Large values
            (1e-6, 1e-6),  # Small values
            (math.inf, math.inf),  # Infinite values
            (-math.inf, -math.inf),  # Negative infinite values
        ],
    )
    def test_basic_coordinate_transformation(self, basic_transform: Transform, data_x: float, data_y: float) -> None:
        """Test basic coordinate transformation (data to screen and back)."""
        if math.isinf(data_x) or math.isinf(data_y):
            # Skip infinite values for roundtrip test
            screen_x, screen_y = basic_transform.data_to_screen(data_x, data_y)
            assert math.isinf(screen_x) == math.isinf(data_x)
            assert math.isinf(screen_y) == math.isinf(data_y)
        else:
            # Test roundtrip: data -> screen -> data should preserve coordinates
            screen_x, screen_y = basic_transform.data_to_screen(data_x, data_y)
            result_x, result_y = basic_transform.screen_to_data(screen_x, screen_y)

            # Use pytest.approx for floating point comparison
            assert result_x == pytest.approx(data_x, abs=1e-10)
            assert result_y == pytest.approx(data_y, abs=1e-10)

    @pytest.mark.parametrize("zoom_factor", [0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
    def test_zoom_factor_impact(self, zoom_factor: float) -> None:
        """Test that zoom factor correctly scales coordinates."""
        transform = Transform(scale=zoom_factor, center_offset_x=0.0, center_offset_y=0.0)

        data_x, data_y = 100.0, 200.0
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # Screen coordinates should be scaled by zoom factor
        expected_x = data_x * zoom_factor
        expected_y = data_y * zoom_factor

        assert screen_x == pytest.approx(expected_x)
        assert screen_y == pytest.approx(expected_y)

    def test_center_offset_impact(self) -> None:
        """Test that center offset correctly translates coordinates."""
        center_x, center_y = 50.0, 75.0
        transform = Transform(scale=1.0, center_offset_x=center_x, center_offset_y=center_y)

        data_x, data_y = 100.0, 200.0
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # Screen coordinates should include center offset
        expected_x = data_x + center_x
        expected_y = data_y + center_y

        assert screen_x == pytest.approx(expected_x)
        assert screen_y == pytest.approx(expected_y)

    def test_pan_offset_impact(self) -> None:
        """Test that pan offset correctly translates coordinates."""
        pan_x, pan_y = 25.0, 35.0
        transform = Transform(
            scale=1.0, center_offset_x=0.0, center_offset_y=0.0, pan_offset_x=pan_x, pan_offset_y=pan_y
        )

        data_x, data_y = 100.0, 200.0
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # Screen coordinates should include pan offset
        expected_x = data_x + pan_x
        expected_y = data_y + pan_y

        assert screen_x == pytest.approx(expected_x)
        assert screen_y == pytest.approx(expected_y)

    def test_manual_offset_impact(self) -> None:
        """Test that manual offset correctly translates coordinates."""
        manual_x, manual_y = 15.0, 20.0
        transform = Transform(
            scale=1.0, center_offset_x=0.0, center_offset_y=0.0, manual_offset_x=manual_x, manual_offset_y=manual_y
        )

        data_x, data_y = 100.0, 200.0
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # Screen coordinates should include manual offset
        expected_x = data_x + manual_x
        expected_y = data_y + manual_y

        assert screen_x == pytest.approx(expected_x)
        assert screen_y == pytest.approx(expected_y)

    def test_y_axis_flipping(self) -> None:
        """Test Y-axis flipping functionality."""
        display_height = 1080
        transform = Transform(
            scale=1.0, center_offset_x=0.0, center_offset_y=0.0, flip_y=True, display_height=display_height
        )

        data_x, data_y = 100.0, 200.0
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # Y coordinate should be flipped
        expected_x = data_x
        expected_y = display_height - data_y

        assert screen_x == pytest.approx(expected_x)
        assert screen_y == pytest.approx(expected_y)

        # Test roundtrip with flipping
        result_x, result_y = transform.screen_to_data(screen_x, screen_y)
        assert result_x == pytest.approx(data_x, abs=1e-10)
        assert result_y == pytest.approx(data_y, abs=1e-10)

    def test_image_scaling(self) -> None:
        """Test image scaling functionality."""
        image_scale_x, image_scale_y = 1.5, 1.2
        transform = Transform(
            scale=1.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=image_scale_x,
            image_scale_y=image_scale_y,
            scale_to_image=True,
        )

        data_x, data_y = 100.0, 200.0
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # Coordinates should be scaled by image scale factors
        expected_x = data_x * image_scale_x
        expected_y = data_y * image_scale_y

        assert screen_x == pytest.approx(expected_x)
        assert screen_y == pytest.approx(expected_y)

        # Test roundtrip with image scaling
        result_x, result_y = transform.screen_to_data(screen_x, screen_y)
        assert result_x == pytest.approx(data_x, abs=1e-10)
        assert result_y == pytest.approx(data_y, abs=1e-10)

    def test_image_scaling_disabled(self) -> None:
        """Test that image scaling can be disabled."""
        transform = Transform(
            scale=1.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=2.0,
            image_scale_y=2.0,
            scale_to_image=False,  # Disabled
        )

        data_x, data_y = 100.0, 200.0
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # Image scaling should be ignored
        assert screen_x == pytest.approx(data_x)
        assert screen_y == pytest.approx(data_y)

    def test_combined_transformations(self, complex_transform: Transform) -> None:
        """Test complex transformation with all parameters."""
        data_x, data_y = 100.0, 200.0

        # Test roundtrip with all transformations
        screen_x, screen_y = complex_transform.data_to_screen(data_x, data_y)
        result_x, result_y = complex_transform.screen_to_data(screen_x, screen_y)

        # Should preserve coordinates despite complex transformation
        assert result_x == pytest.approx(data_x, abs=1e-10)
        assert result_y == pytest.approx(data_y, abs=1e-10)

    def test_transform_with_zero_scale(self) -> None:
        """Test Transform behavior with zero scale factor."""
        transform = Transform(scale=0.0, center_offset_x=0.0, center_offset_y=0.0)

        data_x, data_y = 100.0, 200.0
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # With zero scale, screen coordinates should be zero (after scaling)
        assert screen_x == 0.0
        assert screen_y == 0.0

        # Reverse transformation should handle division by zero gracefully
        result_x, result_y = transform.screen_to_data(screen_x, screen_y)
        assert result_x == 0.0  # Since we're dividing 0 by 0
        assert result_y == 0.0

    def test_transform_with_zero_image_scale(self) -> None:
        """Test Transform behavior with zero image scale factors."""
        transform = Transform(
            scale=1.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=0.0,
            image_scale_y=0.0,
            scale_to_image=True,
        )

        data_x, data_y = 100.0, 200.0
        screen_x, screen_y = transform.data_to_screen(data_x, data_y)

        # With zero image scale, coordinates should be zero after image scaling
        assert screen_x == 0.0
        assert screen_y == 0.0

        # Reverse transformation handles division by zero
        result_x, result_y = transform.screen_to_data(screen_x, screen_y)
        assert result_x == 0.0
        assert result_y == 0.0

    def test_qpoint_transformations(self, basic_transform: Transform) -> None:
        """Test QPointF transformation methods."""
        data_point = QPointF(100.0, 200.0)

        # Transform to screen coordinates
        screen_point = basic_transform.data_to_screen_qpoint(data_point)
        assert isinstance(screen_point, QPointF)
        assert screen_point.x() == 100.0
        assert screen_point.y() == 200.0

        # Transform back to data coordinates
        result_point = basic_transform.screen_to_data_qpoint(screen_point)
        assert isinstance(result_point, QPointF)
        assert result_point.x() == pytest.approx(data_point.x(), abs=1e-10)
        assert result_point.y() == pytest.approx(data_point.y(), abs=1e-10)

    def test_transform_with_updates(self, basic_transform: Transform) -> None:
        """Test creating updated Transform instances."""
        updated_transform = basic_transform.with_updates(scale=2.0, pan_offset_x=50.0, pan_offset_y=75.0)

        # Check updated values
        assert updated_transform.scale == 2.0
        assert updated_transform.pan_offset == (50.0, 75.0)

        # Check unchanged values are preserved
        assert updated_transform.center_offset == basic_transform.center_offset
        assert updated_transform.manual_offset == basic_transform.manual_offset
        assert updated_transform.flip_y == basic_transform.flip_y

        # Original transform should be unchanged
        assert basic_transform.scale == 1.0
        assert basic_transform.pan_offset == (0.0, 0.0)

    def test_transform_from_view_state(self) -> None:
        """Test creating Transform from ViewState."""
        # Create a mock background image to trigger center offset calculation
        from unittest.mock import Mock

        mock_background = Mock()
        mock_background.width.return_value = 1920
        mock_background.height.return_value = 1080

        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            offset_x=50.0,
            offset_y=25.0,
            manual_x_offset=10.0,
            manual_y_offset=15.0,
            flip_y_axis=True,
            scale_to_image=True,
            image_width=1280,
            image_height=720,
            background_image=mock_background,
        )

        transform = Transform.from_view_state(view_state)

        # Check basic transformation parameters
        assert transform.scale == 2.0
        assert transform.pan_offset == (50.0, 25.0)
        assert transform.manual_offset == (10.0, 15.0)
        assert transform.flip_y is True
        assert transform.display_height == 1080
        assert transform.scale_to_image is True

        # Check image scale calculation
        expected_image_scale_x = 1920 / 1280  # display_width / image_width
        expected_image_scale_y = 1080 / 720  # display_height / image_height
        assert transform.image_scale == pytest.approx((expected_image_scale_x, expected_image_scale_y))

        # Check center offset calculation
        expected_center_x = (800 - 1920 * 2.0) / 2  # (widget_width - display_width * scale) / 2
        expected_center_y = (600 - 1080 * 2.0) / 2  # (widget_height - display_height * scale) / 2
        assert transform.center_offset == pytest.approx((expected_center_x, expected_center_y))

    def test_transform_repr(self, complex_transform: Transform) -> None:
        """Test Transform string representation."""
        repr_str = repr(complex_transform)
        assert "Transform(" in repr_str
        assert "scale=2.00" in repr_str
        assert "center_offset=(100.0, 50.0)" in repr_str
        assert "pan_offset=(25.0, 30.0)" in repr_str
        assert "flip_y=True" in repr_str


class TestTransformService:
    """Test suite for TransformService class."""

    @pytest.fixture
    def transform_service(self) -> TransformService:
        """Create a TransformService for testing."""
        service = TransformService()
        return service

    @pytest.fixture
    def real_curve_view(self, qtbot: QtBot):
        """Create a real CurveViewWidget for testing transformations."""
        return self._create_curve_view(qtbot)

    def _create_curve_view(self, qtbot: QtBot, **overrides: Any):
        """Factory method to create curve view with custom properties."""
        from ui.curve_view_widget import CurveViewWidget

        curve_view = CurveViewWidget()
        qtbot.addWidget(curve_view)

        # Set default test properties
        defaults = {
            "width": 800,
            "height": 600,
            "image_width": 1920,
            "image_height": 1080,
            "zoom_factor": 1.0,
            "pan_offset_x": 0.0,
            "pan_offset_y": 0.0,
            "scale_to_image": True,
            "flip_y_axis": False,
            "manual_offset_x": 0.0,
            "manual_offset_y": 0.0,
            "background_image": None,
        }

        # Apply defaults and overrides
        config = {**defaults, **overrides}

        # Set widget size - ensure values are not None
        width = config["width"]
        height = config["height"]
        if width is not None and height is not None:
            curve_view.resize(int(width), int(height))

        # Set properties
        for key, value in config.items():
            if key not in ["width", "height"]:
                setattr(curve_view, key, value)

        return curve_view

    def test_service_creation(self) -> None:
        """Test that TransformService can be created."""
        service = TransformService()
        assert service is not None

    def test_create_view_state(self, transform_service: TransformService, real_curve_view, qtbot) -> None:
        """Test creating ViewState from CurveView using real Qt widget."""
        view_state = transform_service.create_view_state(real_curve_view)

        assert isinstance(view_state, ViewState)
        assert view_state.widget_width == 800
        assert view_state.widget_height == 600
        assert view_state.image_width == 1920
        assert view_state.image_height == 1080

    def test_create_transform(self, transform_service: TransformService) -> None:
        """Test creating Transform from ViewState."""
        view_state = ViewState(display_width=1920, display_height=1080, widget_width=800, widget_height=600)

        transform = transform_service.create_transform_from_view_state(view_state)

        assert isinstance(transform, Transform)
        assert transform.scale == 1.0

    def test_transform_point_to_screen(self, transform_service: TransformService) -> None:
        """Test transforming points to screen coordinates."""
        view_state = ViewState(display_width=1920, display_height=1080, widget_width=800, widget_height=600)
        transform = transform_service.create_transform_from_view_state(view_state)

        screen_x, screen_y = transform_service.transform_point_to_screen(transform, 100.0, 200.0)

        # Should match direct transform call
        expected_x, expected_y = transform.data_to_screen(100.0, 200.0)
        assert screen_x == expected_x
        assert screen_y == expected_y

    def test_transform_point_to_data(self, transform_service: TransformService) -> None:
        """Test transforming points to data coordinates."""
        view_state = ViewState(display_width=1920, display_height=1080, widget_width=800, widget_height=600)
        transform = transform_service.create_transform_from_view_state(view_state)

        data_x, data_y = transform_service.transform_point_to_data(transform, 100.0, 200.0)

        # Should match direct transform call
        expected_x, expected_y = transform.screen_to_data(100.0, 200.0)
        assert data_x == expected_x
        assert data_y == expected_y

    def test_update_view_state(self, transform_service: TransformService) -> None:
        """Test updating ViewState through service."""
        original_state = ViewState(display_width=1920, display_height=1080, widget_width=800, widget_height=600)

        updated_state = transform_service.update_view_state(original_state, zoom_factor=2.0, offset_x=50.0)

        # Should create new ViewState with updates
        assert updated_state.zoom_factor == 2.0
        assert updated_state.offset_x == 50.0
        assert updated_state.display_width == original_state.display_width  # Unchanged

    def test_update_transform(self, transform_service: TransformService) -> None:
        """Test updating Transform through service."""
        original_transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)

        updated_transform = transform_service.update_transform(original_transform, scale=2.0, pan_offset_x=50.0)

        # Should create new Transform with updates
        assert updated_transform.scale == 2.0
        assert updated_transform.pan_offset == (50.0, 0.0)
        assert updated_transform.center_offset == original_transform.center_offset  # Unchanged


class TestTransformServiceIntegration:
    """Integration tests for TransformService with real-world scenarios."""

    def _create_curve_view(self, qtbot: QtBot, **overrides: Any):
        """Factory method to create curve view with custom properties."""
        from ui.curve_view_widget import CurveViewWidget

        curve_view = CurveViewWidget()
        qtbot.addWidget(curve_view)

        # Set default test properties
        defaults = {
            "width": 800,
            "height": 600,
            "image_width": 1920,
            "image_height": 1080,
            "zoom_factor": 1.0,
            "pan_offset_x": 0.0,
            "pan_offset_y": 0.0,
            "scale_to_image": True,
            "flip_y_axis": False,
            "manual_offset_x": 0.0,
            "manual_offset_y": 0.0,
            "background_image": None,
        }

        # Apply defaults and overrides
        config = {**defaults, **overrides}

        # Set widget size - ensure values are not None
        width = config["width"]
        height = config["height"]
        if width is not None and height is not None:
            curve_view.resize(int(width), int(height))

        # Set properties
        for key, value in config.items():
            if key not in ["width", "height"]:
                setattr(curve_view, key, value)

        return curve_view

    @pytest.fixture
    def service(self) -> TransformService:
        """Create a fresh TransformService for integration tests."""
        service = TransformService()
        return service

    def test_full_workflow_basic(self, service: TransformService, qtbot) -> None:
        """Test full workflow: CurveView -> ViewState -> Transform -> Coordinates."""
        # Create a real CurveView with test configuration
        curve_view = self._create_curve_view(
            qtbot,
            width=1200,
            height=800,
            image_width=1920,
            image_height=1080,
            zoom_factor=1.5,
            pan_offset_x=100.0,
            pan_offset_y=50.0,
            scale_to_image=True,
            flip_y_axis=False,
            manual_offset_x=25.0,
            manual_offset_y=30.0,
            background_image=None,
        )

        # Create ViewState from real CurveView
        view_state = service.create_view_state(curve_view)  # pyright: ignore[reportArgumentType]
        assert view_state.widget_width == 1200
        assert view_state.zoom_factor == 1.5

        # Create Transform from ViewState
        transform = service.create_transform_from_view_state(view_state)
        assert transform.scale == 1.5

        # Test coordinate transformation
        data_x, data_y = 500.0, 300.0
        screen_x, screen_y = service.transform_point_to_screen(transform, data_x, data_y)
        result_x, result_y = service.transform_point_to_data(transform, screen_x, screen_y)

        # Should preserve coordinates in roundtrip
        assert result_x == pytest.approx(data_x, abs=1e-10)
        assert result_y == pytest.approx(data_y, abs=1e-10)

    def test_full_workflow_with_background_image(self, service: TransformService, qtbot) -> None:
        """Test workflow with background image affecting display dimensions."""
        from PySide6.QtGui import QColor, QImage

        # Create a real test background image
        background_image = QImage(2560, 1440, QImage.Format.Format_RGB32)
        background_image.fill(QColor(128, 128, 128))  # Fill with gray

        # Create CurveView with real background image
        curve_view = self._create_curve_view(
            qtbot,
            width=1200,
            height=800,
            image_width=1920,
            image_height=1080,
            background_image=background_image,
            zoom_factor=0.8,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            scale_to_image=True,
            flip_y_axis=True,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
        )

        # Create transform and test with real components
        view_state = service.create_view_state(curve_view)  # pyright: ignore[reportArgumentType]
        transform = service.create_transform_from_view_state(view_state)

        # Display dimensions should match background image
        assert view_state.display_width == 2560
        assert view_state.display_height == 1440
        assert transform.display_height == 1440
        assert transform.flip_y is True

        # Test coordinate transformation with Y-axis flipping
        data_x, data_y = 100.0, 200.0
        screen_x, screen_y = service.transform_point_to_screen(transform, data_x, data_y)
        result_x, result_y = service.transform_point_to_data(transform, screen_x, screen_y)

        assert result_x == pytest.approx(data_x, abs=1e-10)
        assert result_y == pytest.approx(data_y, abs=1e-10)

    def test_performance_with_large_datasets(self, service: TransformService) -> None:
        """Test performance with large coordinate datasets."""
        view_state = ViewState(
            display_width=1920, display_height=1080, widget_width=800, widget_height=600, zoom_factor=1.2
        )
        transform = service.create_transform_from_view_state(view_state)

        # Test with 10,000 coordinate pairs
        import time

        start_time = time.time()

        for i in range(10000):
            data_x, data_y = float(i), float(i * 2)
            screen_x, screen_y = service.transform_point_to_screen(transform, data_x, data_y)
            result_x, result_y = service.transform_point_to_data(transform, screen_x, screen_y)

            # Verify correctness for a few samples
            if i % 1000 == 0:
                assert result_x == pytest.approx(data_x, abs=1e-10)
                assert result_y == pytest.approx(data_y, abs=1e-10)

        elapsed = time.time() - start_time
        # Should complete in reasonable time (less than 1 second)
        assert elapsed < 1.0

    @pytest.mark.parametrize("zoom_factor", [0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
    def test_zoom_factor_integration(self, service: TransformService, zoom_factor: float) -> None:
        """Test various zoom factors in full integration workflow."""
        view_state = ViewState(
            display_width=1920, display_height=1080, widget_width=800, widget_height=600, zoom_factor=zoom_factor
        )
        transform = service.create_transform_from_view_state(view_state)

        # Test multiple coordinate pairs
        test_coords = [(0.0, 0.0), (100.0, 200.0), (-50.0, -100.0), (1000.0, 2000.0)]

        for data_x, data_y in test_coords:
            screen_x, screen_y = service.transform_point_to_screen(transform, data_x, data_y)
            result_x, result_y = service.transform_point_to_data(transform, screen_x, screen_y)

            assert result_x == pytest.approx(data_x, abs=1e-10)
            assert result_y == pytest.approx(data_y, abs=1e-10)

    def test_thread_safety_simulation(self, service: TransformService) -> None:
        """Test service behavior under simulated concurrent access."""
        import threading

        results = []
        errors = []

        def worker(worker_id: int) -> None:
            try:
                for i in range(100):
                    view_state = ViewState(
                        display_width=1920,
                        display_height=1080,
                        widget_width=800,
                        widget_height=600,
                        zoom_factor=1.0 + worker_id * 0.1 + i * 0.001,
                    )
                    transform = service.create_transform_from_view_state(view_state)

                    data_x, data_y = float(worker_id * 100 + i), float(worker_id * 200 + i)
                    screen_x, screen_y = service.transform_point_to_screen(transform, data_x, data_y)
                    result_x, result_y = service.transform_point_to_data(transform, screen_x, screen_y)

                    results.append((worker_id, i, abs(result_x - data_x) < 1e-10, abs(result_y - data_y) < 1e-10))

            except Exception as e:
                errors.append((worker_id, str(e)))

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 500  # 5 threads * 100 iterations

        # All transformations should be accurate
        for worker_id, iteration, x_correct, y_correct in results:
            assert x_correct, f"X coordinate incorrect for worker {worker_id}, iteration {iteration}"
            assert y_correct, f"Y coordinate incorrect for worker {worker_id}, iteration {iteration}"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
