#!/usr/bin/env python3
"""
Comprehensive tests for services/transform_core.py module.

This test suite covers the foundation of all coordinate transformations in CurveEditor:
- Validation functions (validate_finite, validate_scale, validate_point)
- ValidationConfig class and environment handling
- ViewState class (initialization, immutability, quantization)
- Transform class (data-to-screen, screen-to-data, batch operations)
- calculate_center_offset function
- Roundtrip accuracy and edge cases

Coverage Target: >95% line coverage for transform_core.py (410 lines)
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

import math
import os
from dataclasses import FrozenInstanceError
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.error_messages import ValidationError
from services.transform_core import (
    DEFAULT_PRECISION,
    MIN_SCALE_VALUE,
    ZOOM_PRECISION,
    ZOOM_PRECISION_FACTOR,
    Transform,
    ValidationConfig,
    ViewState,
    calculate_center_offset,
    validate_finite,
    validate_point,
    validate_scale,
)

# =============================================================================
# Validation Function Tests
# =============================================================================


class TestValidationFunctions:
    """Test validation helper functions."""

    def test_validate_finite_with_valid_value(self) -> None:
        """Test validate_finite with valid finite value."""
        result = validate_finite(42.5, "test_value", default=0.0)
        assert result == 42.5

    def test_validate_finite_with_nan_returns_default(self) -> None:
        """Test validate_finite with NaN returns default."""
        result = validate_finite(float("nan"), "test_value", default=99.0)
        assert result == 99.0

    def test_validate_finite_with_infinity_returns_default(self) -> None:
        """Test validate_finite with infinity returns default."""
        result = validate_finite(float("inf"), "test_value", default=42.0)
        assert result == 42.0

    def test_validate_finite_with_negative_infinity_returns_default(self) -> None:
        """Test validate_finite with -infinity returns default."""
        result = validate_finite(float("-inf"), "test_value", default=10.0)
        assert result == 10.0

    def test_validate_scale_with_valid_positive_value(self) -> None:
        """Test validate_scale with valid positive scale."""
        result = validate_scale(2.5, "test_scale", min_scale=1e-10, max_scale=1e10, default=1.0)
        assert result == 2.5

    def test_validate_scale_with_zero_returns_default(self) -> None:
        """Test validate_scale with zero returns default."""
        result = validate_scale(0.0, "test_scale", default=1.0)
        assert result == 1.0

    def test_validate_scale_with_negative_returns_default(self) -> None:
        """Test validate_scale with negative value returns default."""
        result = validate_scale(-5.0, "test_scale", default=1.0)
        assert result == 1.0

    def test_validate_scale_with_nan_returns_default(self) -> None:
        """Test validate_scale with NaN returns default."""
        result = validate_scale(float("nan"), "test_scale", default=2.0)
        assert result == 2.0

    def test_validate_scale_clamps_to_min_scale(self) -> None:
        """Test validate_scale clamps value below min_scale."""
        result = validate_scale(1e-12, "test_scale", min_scale=1e-10, default=1.0)
        assert result == 1e-10

    def test_validate_scale_clamps_to_max_scale(self) -> None:
        """Test validate_scale clamps value above max_scale."""
        result = validate_scale(1e12, "test_scale", max_scale=1e10, default=1.0)
        assert result == 1e10

    def test_validate_point_with_valid_coordinates(self) -> None:
        """Test validate_point with valid finite coordinates."""
        x, y = validate_point(100.5, 200.5, "test_context")
        assert x == 100.5
        assert y == 200.5

    def test_validate_point_with_nan_x_returns_zeros(self) -> None:
        """Test validate_point with NaN X returns (0, 0)."""
        x, y = validate_point(float("nan"), 100.0, "test_context")
        assert x == 0.0
        assert y == 0.0

    def test_validate_point_with_nan_y_returns_zeros(self) -> None:
        """Test validate_point with NaN Y returns (0, 0)."""
        x, y = validate_point(100.0, float("nan"), "test_context")
        assert x == 0.0
        assert y == 0.0

    def test_validate_point_with_infinity_returns_zeros(self) -> None:
        """Test validate_point with infinity returns (0, 0)."""
        x, y = validate_point(float("inf"), 100.0, "test_context")
        assert x == 0.0
        assert y == 0.0


# =============================================================================
# ValidationConfig Tests
# =============================================================================


class TestValidationConfig:
    """Test ValidationConfig class."""

    def test_validation_config_defaults(self) -> None:
        """Test ValidationConfig default values."""
        config = ValidationConfig()
        assert config.enable_full_validation is True
        assert config.max_coordinate == 1e12
        assert config.min_scale == 1e-10
        assert config.max_scale == 1e10

    def test_validation_config_custom_values(self) -> None:
        """Test ValidationConfig with custom values."""
        config = ValidationConfig(enable_full_validation=False, max_coordinate=1e10, min_scale=1e-8, max_scale=1e8)
        assert config.enable_full_validation is False
        assert config.max_coordinate == 1e10
        assert config.min_scale == 1e-8
        assert config.max_scale == 1e8

    def test_validation_config_for_production(self) -> None:
        """Test ValidationConfig.for_production() factory."""
        config = ValidationConfig.for_production()
        assert config.enable_full_validation is False
        assert config.max_coordinate == 1e12
        assert config.min_scale == 1e-10
        assert config.max_scale == 1e10

    def test_validation_config_for_debug(self) -> None:
        """Test ValidationConfig.for_debug() factory."""
        config = ValidationConfig.for_debug()
        assert config.enable_full_validation is True
        assert config.max_coordinate == 1e12
        assert config.min_scale == 1e-10
        assert config.max_scale == 1e10

    @patch.dict(os.environ, {"CURVE_EDITOR_FULL_VALIDATION": "1"})
    def test_validation_config_from_environment_enabled(self) -> None:
        """Test ValidationConfig.from_environment() with validation enabled."""
        config = ValidationConfig.from_environment()
        assert config.enable_full_validation is True

    @patch.dict(os.environ, {"CURVE_EDITOR_FULL_VALIDATION": "0"})
    def test_validation_config_from_environment_disabled(self) -> None:
        """Test ValidationConfig.from_environment() with validation disabled."""
        config = ValidationConfig.from_environment()
        assert config.enable_full_validation is False

    @patch.dict(os.environ, {"CURVE_EDITOR_MAX_COORDINATE": "1e9"})
    def test_validation_config_from_environment_custom_max_coord(self) -> None:
        """Test ValidationConfig.from_environment() with custom max coordinate."""
        config = ValidationConfig.from_environment()
        assert config.max_coordinate == 1e9

    @patch.dict(os.environ, {"CURVE_EDITOR_MIN_SCALE": "1e-8", "CURVE_EDITOR_MAX_SCALE": "1e8"})
    def test_validation_config_from_environment_custom_scales(self) -> None:
        """Test ValidationConfig.from_environment() with custom scale limits."""
        config = ValidationConfig.from_environment()
        assert config.min_scale == 1e-8
        assert config.max_scale == 1e8


# =============================================================================
# calculate_center_offset Tests
# =============================================================================


class TestCalculateCenterOffset:
    """Test calculate_center_offset function."""

    def test_calculate_center_offset_no_scaling(self) -> None:
        """Test center offset with 1:1 pixel mapping (no offset)."""
        center_x, center_y = calculate_center_offset(
            widget_width=800,
            widget_height=600,
            display_width=800,
            display_height=600,
            scale=1.0,
            flip_y_axis=False,
            scale_to_image=False,
        )
        assert center_x == 0.0
        assert center_y == 0.0

    def test_calculate_center_offset_with_scale(self) -> None:
        """Test center offset with scaling applied."""
        center_x, center_y = calculate_center_offset(
            widget_width=800,
            widget_height=600,
            display_width=400,
            display_height=300,
            scale=2.0,
            flip_y_axis=False,
            scale_to_image=True,
        )
        # Expected: (800 - 400*2) / 2 = 0, (600 - 300*2) / 2 = 0
        assert center_x == 0.0
        assert center_y == 0.0

    def test_calculate_center_offset_with_different_dimensions(self) -> None:
        """Test center offset with widget larger than scaled content."""
        center_x, center_y = calculate_center_offset(
            widget_width=1000,
            widget_height=800,
            display_width=400,
            display_height=300,
            scale=1.0,
            flip_y_axis=False,
            scale_to_image=True,
        )
        # Expected: (1000 - 400) / 2 = 300, (800 - 300) / 2 = 250
        assert center_x == 300.0
        assert center_y == 250.0

    def test_calculate_center_offset_with_y_flip(self) -> None:
        """Test center offset with Y-axis flip (should still calculate offset)."""
        center_x, center_y = calculate_center_offset(
            widget_width=800,
            widget_height=600,
            display_width=400,
            display_height=300,
            scale=1.5,
            flip_y_axis=True,
            scale_to_image=True,
        )
        # Expected: (800 - 400*1.5) / 2 = 100, (600 - 300*1.5) / 2 = 75
        assert center_x == 100.0
        assert center_y == 75.0


# =============================================================================
# ViewState Tests
# =============================================================================


class TestViewState:
    """Test ViewState class."""

    def test_viewstate_initialization_minimal(self) -> None:
        """Test ViewState with minimal required parameters."""
        vs = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)
        assert vs.display_width == 1920.0
        assert vs.display_height == 1080.0
        assert vs.widget_width == 800
        assert vs.widget_height == 600
        # Check defaults
        assert vs.zoom_factor == 1.0
        assert vs.fit_scale == 1.0
        assert vs.offset_x == 0.0
        assert vs.offset_y == 0.0
        assert vs.scale_to_image is True
        assert vs.flip_y_axis is False
        assert vs.manual_x_offset == 0.0
        assert vs.manual_y_offset == 0.0
        assert vs.background_image is None
        assert vs.image_width == 1920
        assert vs.image_height == 1080

    def test_viewstate_initialization_full(self) -> None:
        """Test ViewState with all parameters specified."""
        mock_image = MagicMock()
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.5,
            fit_scale=0.8,
            offset_x=100.0,
            offset_y=50.0,
            scale_to_image=False,
            flip_y_axis=True,
            manual_x_offset=25.0,
            manual_y_offset=30.0,
            background_image=mock_image,
            image_width=1280,
            image_height=720,
        )
        assert vs.zoom_factor == 2.5
        assert vs.fit_scale == 0.8
        assert vs.offset_x == 100.0
        assert vs.offset_y == 50.0
        assert vs.scale_to_image is False
        assert vs.flip_y_axis is True
        assert vs.manual_x_offset == 25.0
        assert vs.manual_y_offset == 30.0
        assert vs.background_image is mock_image
        assert vs.image_width == 1280
        assert vs.image_height == 720

    def test_viewstate_immutability(self) -> None:
        """Test that ViewState is immutable (frozen dataclass)."""
        vs = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)
        with pytest.raises(FrozenInstanceError):
            vs.zoom_factor = 2.0  # Intentional: testing immutability

    def test_viewstate_with_updates(self) -> None:
        """Test ViewState.with_updates() creates new instance."""
        vs = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)
        updated = vs.with_updates(zoom_factor=3.0, offset_x=200.0)
        assert updated.zoom_factor == 3.0
        assert updated.offset_x == 200.0
        # Original unchanged
        assert vs.zoom_factor == 1.0
        assert vs.offset_x == 0.0
        # Other fields preserved
        assert updated.display_width == 1920.0
        assert updated.widget_width == 800

    def test_viewstate_quantized_for_cache_default_precision(self) -> None:
        """Test ViewState.quantized_for_cache() with default precision."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.2345,
            offset_x=100.123,
            offset_y=200.456,
        )
        quantized = vs.quantized_for_cache()
        # Zoom should be quantized to ZOOM_PRECISION (0.001)
        assert abs(quantized.zoom_factor - round(1.2345 / ZOOM_PRECISION) * ZOOM_PRECISION) < 1e-10
        # Offsets should be quantized to DEFAULT_PRECISION (0.1)
        assert abs(quantized.offset_x - round(100.123 / DEFAULT_PRECISION) * DEFAULT_PRECISION) < 1e-10
        assert abs(quantized.offset_y - round(200.456 / DEFAULT_PRECISION) * DEFAULT_PRECISION) < 1e-10

    def test_viewstate_quantized_for_cache_custom_precision(self) -> None:
        """Test ViewState.quantized_for_cache() with custom precision."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            offset_x=123.456,
        )
        quantized = vs.quantized_for_cache(precision=1.0)
        # Should round to nearest 1.0
        assert quantized.offset_x == 123.0

    def test_viewstate_quantized_for_cache_invalid_precision(self) -> None:
        """Test ViewState.quantized_for_cache() raises on invalid precision."""
        vs = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)
        with pytest.raises(ValidationError):
            vs.quantized_for_cache(precision=0.0)
        with pytest.raises(ValidationError):
            vs.quantized_for_cache(precision=-0.1)

    def test_viewstate_quantized_handles_non_finite_values(self) -> None:
        """Test ViewState.quantized_for_cache() handles NaN/infinity gracefully."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            zoom_factor=float("nan"),
            offset_x=float("inf"),
        )
        quantized = vs.quantized_for_cache()
        # NaN zoom should become 0.0 after quantization (isfinite check)
        assert quantized.zoom_factor == 0.0
        # Infinity offset should become 0.0
        assert quantized.offset_x == 0.0

    def test_viewstate_to_dict(self) -> None:
        """Test ViewState.to_dict() serialization."""
        mock_image = MagicMock()
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            offset_x=100.0,
            offset_y=50.0,
            manual_x_offset=10.0,
            manual_y_offset=20.0,
            scale_to_image=False,
            flip_y_axis=True,
            background_image=mock_image,
            image_width=1280,
            image_height=720,
        )
        d = vs.to_dict()
        assert d["display_dimensions"] == (1920.0, 1080.0)
        assert d["widget_dimensions"] == (800, 600)
        assert d["image_dimensions"] == (1280, 720)
        assert d["zoom_factor"] == 2.0
        assert d["offset"] == (100.0, 50.0)
        assert d["manual_offset"] == (10.0, 20.0)
        assert d["scale_to_image"] is False
        assert d["flip_y_axis"] is True
        assert d["has_background_image"] is True

    def test_viewstate_from_curve_view(self, qtbot: Any) -> None:
        """Test ViewState.from_curve_view() factory method."""
        from ui.curve_view_widget import CurveViewWidget

        curve_view = CurveViewWidget()
        qtbot.addWidget(curve_view)
        curve_view.resize(800, 600)
        curve_view.image_width = 1920
        curve_view.image_height = 1080
        curve_view.zoom_factor = 1.5
        curve_view.pan_offset_x = 50.0
        curve_view.pan_offset_y = 75.0

        vs = ViewState.from_curve_view(curve_view)
        assert vs.widget_width == 800
        assert vs.widget_height == 600
        assert vs.image_width == 1920
        assert vs.image_height == 1080
        assert vs.zoom_factor == 1.5
        assert vs.offset_x == 50.0
        assert vs.offset_y == 75.0

    def test_viewstate_from_curve_view_sanitizes_invalid_zoom(self, qtbot: Any) -> None:
        """Test ViewState.from_curve_view() sanitizes invalid zoom factor."""
        from ui.curve_view_widget import CurveViewWidget

        curve_view = CurveViewWidget()
        qtbot.addWidget(curve_view)
        curve_view.zoom_factor = float("nan")

        vs = ViewState.from_curve_view(curve_view)
        # validate_scale returns 1.0 for NaN, then clamps to valid range
        # The actual zoom_factor depends on CurveViewWidget defaults
        assert math.isfinite(vs.zoom_factor)
        assert vs.zoom_factor > 0

    def test_viewstate_from_curve_view_with_background_image(self, qtbot: Any) -> None:
        """Test ViewState.from_curve_view() uses background image dimensions."""
        from ui.curve_view_widget import CurveViewWidget

        curve_view = CurveViewWidget()
        qtbot.addWidget(curve_view)
        curve_view.image_width = 1920
        curve_view.image_height = 1080

        # Mock background image with different dimensions
        mock_image = MagicMock()
        mock_image.width.return_value = 2560
        mock_image.height.return_value = 1440
        curve_view.background_image = mock_image

        vs = ViewState.from_curve_view(curve_view)
        # Display dimensions should come from background image
        assert vs.display_width == 2560
        assert vs.display_height == 1440
        # Original dimensions preserved
        assert vs.image_width == 1920
        assert vs.image_height == 1080


# =============================================================================
# Transform Tests
# =============================================================================


class TestTransform:
    """Test Transform class."""

    def test_transform_initialization_minimal(self) -> None:
        """Test Transform with minimal parameters."""
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        assert t.scale == 1.0
        assert t.center_offset == (0.0, 0.0)
        assert t.pan_offset == (0.0, 0.0)
        assert t.manual_offset == (0.0, 0.0)
        assert t.flip_y is False
        assert t.display_height == 0

    def test_transform_initialization_full(self) -> None:
        """Test Transform with all parameters."""
        t = Transform(
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
            image_scale_y=1.5,
            scale_to_image=True,
        )
        assert t.scale == 2.0
        assert t.center_offset == (100.0, 50.0)
        assert t.pan_offset == (25.0, 30.0)
        assert t.manual_offset == (10.0, 15.0)
        assert t.flip_y is True
        assert t.display_height == 1080
        assert t.image_scale == (1.5, 1.5)
        assert t.scale_to_image is True

    def test_transform_rejects_zero_scale_in_debug_mode(self) -> None:
        """Test Transform raises ValueError for zero scale in debug mode."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Scale factor too small"):
            Transform(scale=0.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

    def test_transform_clamps_zero_scale_in_production_mode(self) -> None:
        """Test Transform clamps zero scale to minimum in production mode."""
        config = ValidationConfig.for_production()
        t = Transform(scale=0.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        # Should clamp to 1e-10
        assert t.scale == 1e-10

    def test_transform_handles_nan_scale_gracefully(self) -> None:
        """Test Transform handles NaN scale gracefully."""
        config = ValidationConfig.for_production()
        t = Transform(scale=float("nan"), center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        # NaN should be replaced with default 1.0
        assert t.scale == 1.0

    def test_transform_rejects_extreme_scale_in_debug_mode(self) -> None:
        """Test Transform raises ValueError for extreme scale in debug mode."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Scale factor too large"):
            Transform(scale=1e11, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

    def test_transform_clamps_extreme_scale_in_production_mode(self) -> None:
        """Test Transform clamps extreme scale in production mode."""
        config = ValidationConfig.for_production()
        t = Transform(scale=1e11, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        # Should clamp to max 1e10
        assert t.scale == 1e10

    def test_transform_rejects_negative_display_height_in_debug_mode(self) -> None:
        """Test Transform raises ValueError for negative display height in debug mode."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Display height cannot be negative"):
            Transform(
                scale=1.0, center_offset_x=0.0, center_offset_y=0.0, display_height=-100, validation_config=config
            )

    def test_transform_corrects_negative_display_height_in_production_mode(self) -> None:
        """Test Transform corrects negative display height in production mode."""
        config = ValidationConfig.for_production()
        t = Transform(
            scale=1.0, center_offset_x=0.0, center_offset_y=0.0, display_height=-100, validation_config=config
        )
        # Should use absolute value
        assert t.display_height == 100

    def test_transform_clamps_extreme_display_height_in_production_mode(self) -> None:
        """Test Transform clamps extremely large display height in production mode."""
        config = ValidationConfig.for_production()
        t = Transform(
            scale=1.0, center_offset_x=0.0, center_offset_y=0.0, display_height=2000000, validation_config=config
        )
        # Should clamp to max 1,000,000
        assert t.display_height == 1000000

    def test_transform_rejects_large_center_offset_in_debug_mode(self) -> None:
        """Test Transform raises ValueError for large center offset in debug mode."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="too large"):
            Transform(
                scale=1.0, center_offset_x=2e9, center_offset_y=0.0, validation_config=config
            )

    def test_transform_clamps_large_center_offset_in_production_mode(self) -> None:
        """Test Transform clamps large center offset in production mode."""
        config = ValidationConfig.for_production()
        t = Transform(
            scale=1.0, center_offset_x=2e9, center_offset_y=-2e9, validation_config=config
        )
        # Should clamp to ±1e9
        assert t.center_offset == (1e9, -1e9)

    def test_transform_rejects_large_pan_offset_in_debug_mode(self) -> None:
        """Test Transform raises ValueError for large pan offset in debug mode."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="too large"):
            Transform(
                scale=1.0, center_offset_x=0.0, center_offset_y=0.0,
                pan_offset_x=1.5e9, pan_offset_y=0.0, validation_config=config
            )

    def test_transform_clamps_large_pan_offset_in_production_mode(self) -> None:
        """Test Transform clamps large pan offset in production mode."""
        config = ValidationConfig.for_production()
        t = Transform(
            scale=1.0, center_offset_x=0.0, center_offset_y=0.0,
            pan_offset_x=1.5e9, pan_offset_y=-1.5e9, validation_config=config
        )
        # Should clamp to ±1e9
        assert t.pan_offset == (1e9, -1e9)

    def test_transform_rejects_large_manual_offset_in_debug_mode(self) -> None:
        """Test Transform raises ValueError for large manual offset in debug mode."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="too large"):
            Transform(
                scale=1.0, center_offset_x=0.0, center_offset_y=0.0,
                manual_offset_x=2e9, manual_offset_y=0.0, validation_config=config
            )

    def test_transform_clamps_large_manual_offset_in_production_mode(self) -> None:
        """Test Transform clamps large manual offset in production mode."""
        config = ValidationConfig.for_production()
        t = Transform(
            scale=1.0, center_offset_x=0.0, center_offset_y=0.0,
            manual_offset_x=2e9, manual_offset_y=-2e9, validation_config=config
        )
        # Should clamp to ±1e9
        assert t.manual_offset == (1e9, -1e9)

    def test_transform_rejects_zero_image_scale_y_in_debug_mode(self) -> None:
        """Test Transform raises ValueError for zero image_scale_y in debug mode."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Image scale Y too small"):
            Transform(
                scale=1.0, center_offset_x=0.0, center_offset_y=0.0,
                image_scale_y=1e-11, validation_config=config
            )

    def test_transform_data_to_screen_basic(self) -> None:
        """Test basic data-to-screen transformation."""
        t = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        screen_x, screen_y = t.data_to_screen(10.0, 20.0)
        # Expected: (10 * 2 + 100, 20 * 2 + 50) = (120, 90)
        assert screen_x == 120.0
        assert screen_y == 90.0

    def test_transform_data_to_screen_with_pan_offset(self) -> None:
        """Test data-to-screen with pan offset."""
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, pan_offset_x=50.0, pan_offset_y=25.0)
        screen_x, screen_y = t.data_to_screen(100.0, 200.0)
        # Expected: (100 + 50, 200 + 25) = (150, 225)
        assert screen_x == 150.0
        assert screen_y == 225.0

    def test_transform_data_to_screen_with_y_flip(self) -> None:
        """Test data-to-screen with Y-axis flip."""
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, flip_y=True, display_height=1080)
        screen_x, screen_y = t.data_to_screen(100.0, 200.0)
        # Expected: X unchanged, Y = 1080 - 200 = 880
        assert screen_x == 100.0
        assert screen_y == 880.0

    def test_transform_data_to_screen_with_image_scaling(self) -> None:
        """Test data-to-screen with image scale factors."""
        t = Transform(
            scale=2.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=1.5,
            image_scale_y=1.5,
            scale_to_image=True,
        )
        screen_x, screen_y = t.data_to_screen(10.0, 20.0)
        # Combined scale = 2.0 * 1.5 = 3.0
        # Expected: (10 * 3, 20 * 3) = (30, 60)
        assert screen_x == 30.0
        assert screen_y == 60.0

    def test_transform_data_to_screen_without_image_scaling(self) -> None:
        """Test data-to-screen ignores image scale when disabled."""
        t = Transform(
            scale=2.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=1.5,
            image_scale_y=1.5,
            scale_to_image=False,
        )
        screen_x, screen_y = t.data_to_screen(10.0, 20.0)
        # Should use only main scale: (10 * 2, 20 * 2) = (20, 40)
        assert screen_x == 20.0
        assert screen_y == 40.0

    def test_transform_data_to_screen_rejects_nan_in_debug_mode(self) -> None:
        """Test data-to-screen raises on NaN input in debug mode."""
        config = ValidationConfig.for_debug()
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        with pytest.raises(ValueError, match="must be finite"):
            t.data_to_screen(float("nan"), 100.0)

    def test_transform_data_to_screen_handles_nan_in_production_mode(self) -> None:
        """Test data-to-screen corrects NaN input in production mode."""
        config = ValidationConfig.for_production()
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        screen_x, screen_y = t.data_to_screen(float("nan"), 100.0)
        # NaN should be corrected to 0.0
        assert screen_x == 0.0
        assert screen_y == 0.0

    def test_transform_data_to_screen_rejects_extreme_coords_in_debug_mode(self) -> None:
        """Test data-to-screen raises on extreme coordinates in debug mode."""
        config = ValidationConfig.for_debug()
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        with pytest.raises(ValueError, match="too large"):
            t.data_to_screen(1e13, 100.0)

    def test_transform_screen_to_data_basic(self) -> None:
        """Test basic screen-to-data transformation."""
        t = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        data_x, data_y = t.screen_to_data(120.0, 90.0)
        # Reverse: ((120 - 100) / 2, (90 - 50) / 2) = (10, 20)
        assert data_x == 10.0
        assert data_y == 20.0

    def test_transform_screen_to_data_with_y_flip(self) -> None:
        """Test screen-to-data with Y-axis flip."""
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, flip_y=True, display_height=1080)
        data_x, data_y = t.screen_to_data(100.0, 880.0)
        # Reverse Y flip: 1080 - 880 = 200
        assert data_x == 100.0
        assert data_y == 200.0

    def test_transform_screen_to_data_handles_clamped_scale(self) -> None:
        """Test screen-to-data handles clamped image scale in production mode."""
        # Create transform with very small image scale (gets clamped to 1e-10)
        config = ValidationConfig.for_production()
        t = Transform(
            scale=1.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=1e-11,  # Gets clamped to 1e-10 in production
            scale_to_image=True,
            validation_config=config,
        )
        # Combined scale is 1.0 * 1e-10 = 1e-10, which is at the threshold
        # The code checks abs(scale) < 1e-10, so 1e-10 should be valid
        data_x, data_y = t.screen_to_data(100.0, 100.0)
        # Should succeed with clamped scale
        assert math.isfinite(data_x)
        assert math.isfinite(data_y)

    def test_transform_roundtrip_preserves_coordinates(self) -> None:
        """Test data→screen→data roundtrip preserves coordinates."""
        t = Transform(
            scale=2.5,
            center_offset_x=150.0,
            center_offset_y=75.0,
            pan_offset_x=25.0,
            pan_offset_y=30.0,
            manual_offset_x=10.0,
            manual_offset_y=5.0,
        )
        original_x, original_y = 123.456, 789.012
        screen_x, screen_y = t.data_to_screen(original_x, original_y)
        data_x, data_y = t.screen_to_data(screen_x, screen_y)
        # Should match within floating-point precision
        assert abs(data_x - original_x) < 1e-10
        assert abs(data_y - original_y) < 1e-10

    def test_transform_roundtrip_with_y_flip_preserves_coordinates(self) -> None:
        """Test roundtrip with Y-flip preserves coordinates."""
        t = Transform(
            scale=1.5,
            center_offset_x=50.0,
            center_offset_y=100.0,
            flip_y=True,
            display_height=1080,
        )
        original_x, original_y = 456.789, 234.567
        screen_x, screen_y = t.data_to_screen(original_x, original_y)
        data_x, data_y = t.screen_to_data(screen_x, screen_y)
        assert abs(data_x - original_x) < 1e-10
        assert abs(data_y - original_y) < 1e-10

    def test_transform_roundtrip_with_image_scaling_preserves_coordinates(self) -> None:
        """Test roundtrip with image scaling preserves coordinates."""
        t = Transform(
            scale=2.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=1.5,
            image_scale_y=1.5,
            scale_to_image=True,
        )
        original_x, original_y = 100.0, 200.0
        screen_x, screen_y = t.data_to_screen(original_x, original_y)
        data_x, data_y = t.screen_to_data(screen_x, screen_y)
        assert abs(data_x - original_x) < 1e-10
        assert abs(data_y - original_y) < 1e-10

    def test_transform_precision_at_high_zoom(self) -> None:
        """Test coordinate precision at high zoom levels."""
        t = Transform(scale=10.0, center_offset_x=0.0, center_offset_y=0.0)
        original_x, original_y = 12.3456789, 98.7654321
        screen_x, screen_y = t.data_to_screen(original_x, original_y)
        data_x, data_y = t.screen_to_data(screen_x, screen_y)
        # Should preserve precision even at high zoom
        assert abs(data_x - original_x) < 1e-9
        assert abs(data_y - original_y) < 1e-9

    def test_transform_precision_at_low_zoom(self) -> None:
        """Test coordinate precision at low zoom levels."""
        t = Transform(scale=0.1, center_offset_x=0.0, center_offset_y=0.0)
        original_x, original_y = 1234.5678, 9876.5432
        screen_x, screen_y = t.data_to_screen(original_x, original_y)
        data_x, data_y = t.screen_to_data(screen_x, screen_y)
        # Should preserve precision even at low zoom
        assert abs(data_x - original_x) < 1e-9
        assert abs(data_y - original_y) < 1e-9

    def test_transform_data_to_screen_qpoint(self) -> None:
        """Test QPointF data-to-screen transformation."""
        from services.transform_core import QPointF

        t = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        data_point = QPointF(10.0, 20.0)
        screen_point = t.data_to_screen_qpoint(data_point)
        assert screen_point.x() == 120.0
        assert screen_point.y() == 90.0

    def test_transform_screen_to_data_qpoint(self) -> None:
        """Test QPointF screen-to-data transformation."""
        from services.transform_core import QPointF

        t = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        screen_point = QPointF(120.0, 90.0)
        data_point = t.screen_to_data_qpoint(screen_point)
        assert data_point.x() == 10.0
        assert data_point.y() == 20.0

    def test_transform_batch_data_to_screen_2_columns(self) -> None:
        """Test batch data-to-screen with Nx2 array."""
        t = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        points = np.array([[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]], dtype=np.float64)
        result = t.batch_data_to_screen(points)
        # Expected: [(10*2+100, 20*2+50), (30*2+100, 40*2+50), (50*2+100, 60*2+50)]
        assert result.shape == (3, 2)
        np.testing.assert_allclose(result[0], [120.0, 90.0])
        np.testing.assert_allclose(result[1], [160.0, 130.0])
        np.testing.assert_allclose(result[2], [200.0, 170.0])

    def test_transform_batch_data_to_screen_3_columns(self) -> None:
        """Test batch data-to-screen with Nx3 array (frame, x, y)."""
        t = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        points = np.array([[1, 10.0, 20.0], [2, 30.0, 40.0]], dtype=np.float64)
        result = t.batch_data_to_screen(points)
        # Should extract columns 1:3 and transform
        assert result.shape == (2, 2)
        np.testing.assert_allclose(result[0], [120.0, 90.0])
        np.testing.assert_allclose(result[1], [160.0, 130.0])

    def test_transform_batch_data_to_screen_empty_array(self) -> None:
        """Test batch data-to-screen with empty array."""
        t = Transform(scale=2.0, center_offset_x=0.0, center_offset_y=0.0)
        points = np.empty((0, 2), dtype=np.float64)
        result = t.batch_data_to_screen(points)
        assert result.shape == (0, 2)

    def test_transform_batch_data_to_screen_rejects_wrong_shape(self) -> None:
        """Test batch data-to-screen raises on wrong array shape."""
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        points = np.array([10.0, 20.0], dtype=np.float64)  # 1D array
        with pytest.raises(ValueError, match="Expected 2D array"):
            t.batch_data_to_screen(points)

    def test_transform_batch_data_to_screen_rejects_wrong_columns(self) -> None:
        """Test batch data-to-screen raises on wrong column count."""
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        points = np.array([[1, 2, 3, 4]], dtype=np.float64)  # 4 columns
        with pytest.raises(ValueError, match="Expected 2 or 3 columns"):
            t.batch_data_to_screen(points)

    def test_transform_batch_data_to_screen_handles_nan_in_production(self) -> None:
        """Test batch data-to-screen corrects NaN in production mode."""
        config = ValidationConfig.for_production()
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        points = np.array([[10.0, 20.0], [float("nan"), 40.0]], dtype=np.float64)
        result = t.batch_data_to_screen(points)
        # NaN should be replaced with 0.0
        np.testing.assert_allclose(result[0], [10.0, 20.0])
        np.testing.assert_allclose(result[1], [0.0, 40.0])

    def test_transform_batch_data_to_screen_rejects_nan_in_debug(self) -> None:
        """Test batch data-to-screen raises on NaN in debug mode."""
        config = ValidationConfig.for_debug()
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        points = np.array([[10.0, 20.0], [float("nan"), 40.0]], dtype=np.float64)
        with pytest.raises(ValueError, match="must be finite"):
            t.batch_data_to_screen(points)

    def test_transform_batch_screen_to_data(self) -> None:
        """Test batch screen-to-data transformation."""
        t = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        points = np.array([[120.0, 90.0], [160.0, 130.0]], dtype=np.float64)
        result = t.batch_screen_to_data(points)
        # Reverse: [((120-100)/2, (90-50)/2), ((160-100)/2, (130-50)/2)]
        assert result.shape == (2, 2)
        np.testing.assert_allclose(result[0], [10.0, 20.0])
        np.testing.assert_allclose(result[1], [30.0, 40.0])

    def test_transform_batch_screen_to_data_empty_array(self) -> None:
        """Test batch screen-to-data with empty array."""
        t = Transform(scale=2.0, center_offset_x=0.0, center_offset_y=0.0)
        points = np.empty((0, 2), dtype=np.float64)
        result = t.batch_screen_to_data(points)
        assert result.shape == (0, 2)

    def test_transform_batch_screen_to_data_rejects_wrong_shape(self) -> None:
        """Test batch screen-to-data raises on wrong array shape."""
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        points = np.array([[1, 2, 3]], dtype=np.float64)  # 3 columns
        with pytest.raises(ValueError, match="Expected Nx2 array"):
            t.batch_screen_to_data(points)

    def test_transform_with_updates(self) -> None:
        """Test Transform.with_updates() creates new instance."""
        t = Transform(scale=1.0, center_offset_x=100.0, center_offset_y=50.0)
        updated = t.with_updates(scale=2.0, pan_offset_x=25.0)
        assert updated.scale == 2.0
        assert updated.pan_offset == (25.0, 0.0)
        # Original unchanged
        assert t.scale == 1.0
        assert t.pan_offset == (0.0, 0.0)
        # Other fields preserved
        assert updated.center_offset == (100.0, 50.0)

    def test_transform_get_parameters(self) -> None:
        """Test Transform.get_parameters() returns parameter dict."""
        t = Transform(
            scale=2.0,
            center_offset_x=100.0,
            center_offset_y=50.0,
            flip_y=True,
            display_height=1080,
        )
        params = t.get_parameters()
        assert params["scale"] == 2.0
        assert params["center_offset_x"] == 100.0
        assert params["center_offset_y"] == 50.0
        assert params["flip_y"] is True
        assert params["display_height"] == 1080

    def test_transform_stability_hash_in_debug_mode(self) -> None:
        """Test Transform stability hash is computed in debug mode."""
        config = ValidationConfig.for_debug()
        t1 = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0, validation_config=config)
        t2 = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0, validation_config=config)
        # Same parameters should have same hash
        assert t1.stability_hash == t2.stability_hash
        assert len(t1.stability_hash) == 32  # MD5 hash length

    def test_transform_stability_hash_in_production_mode(self) -> None:
        """Test Transform uses simpler hash in production mode."""
        config = ValidationConfig.for_production()
        t = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0, validation_config=config)
        # Should have some hash, but simpler than MD5
        assert t.stability_hash is not None
        assert len(t.stability_hash) > 0

    def test_transform_repr(self) -> None:
        """Test Transform __repr__ for debugging."""
        t = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0, flip_y=True)
        repr_str = repr(t)
        assert "Transform" in repr_str
        assert "scale=2.00" in repr_str
        assert "center_offset=(100.0, 50.0)" in repr_str
        assert "flip_y=True" in repr_str

    def test_transform_from_view_state(self) -> None:
        """Test Transform.from_view_state() factory method."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            fit_scale=0.5,
            offset_x=100.0,
            offset_y=50.0,
            flip_y_axis=True,
            image_width=1280,
            image_height=720,
        )
        t = Transform.from_view_state(vs)
        # Scale should be fit_scale * zoom_factor = 0.5 * 2.0 = 1.0
        assert t.scale == 1.0
        assert t.flip_y is True
        assert t.display_height == 1080
        assert t.pan_offset == (100.0, 50.0)
        # Image scale should be display/image = 1920/1280 = 1.5
        assert t.image_scale[0] == pytest.approx(1.5)
        assert t.image_scale[1] == pytest.approx(1.5)

    def test_transform_from_view_state_with_invalid_image_dimensions(self) -> None:
        """Test Transform.from_view_state() handles invalid image dimensions."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            image_width=0,  # Invalid
            image_height=-10,  # Invalid
        )
        t = Transform.from_view_state(vs)
        # Should use 1.0 scale for invalid dimensions
        assert t.image_scale == (1.0, 1.0)

    def test_transform_from_view_state_raises_on_negative_display_dimensions(self) -> None:
        """Test Transform.from_view_state() raises on negative display dimensions."""
        vs = ViewState(
            display_width=-1920.0,  # Invalid
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            image_width=1920,
            image_height=1080,
        )
        with pytest.raises(ValueError, match="Display width cannot be negative"):
            Transform.from_view_state(vs)


# =============================================================================
# Edge Cases and Constants Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and extreme scenarios."""

    def test_transform_with_extreme_coordinates(self) -> None:
        """Test transform handles very large coordinates."""
        config = ValidationConfig.for_production()
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        # Large but within max_coordinate (1e12)
        large_x, large_y = 1e11, 1e11
        screen_x, screen_y = t.data_to_screen(large_x, large_y)
        data_x, data_y = t.screen_to_data(screen_x, screen_y)
        # Should roundtrip accurately
        assert abs(data_x - large_x) < 1.0  # Allow small error for large values
        assert abs(data_y - large_y) < 1.0

    def test_transform_with_very_small_coordinates(self) -> None:
        """Test transform handles very small coordinates."""
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        small_x, small_y = 1e-9, 1e-9
        screen_x, screen_y = t.data_to_screen(small_x, small_y)
        data_x, data_y = t.screen_to_data(screen_x, screen_y)
        # Should roundtrip accurately even for tiny values
        assert abs(data_x - small_x) < 1e-12
        assert abs(data_y - small_y) < 1e-12

    def test_transform_combined_all_transformations(self) -> None:
        """Test transform with all transformation types combined."""
        t = Transform(
            scale=2.5,
            center_offset_x=150.0,
            center_offset_y=100.0,
            pan_offset_x=50.0,
            pan_offset_y=25.0,
            manual_offset_x=10.0,
            manual_offset_y=5.0,
            flip_y=True,
            display_height=1080,
            image_scale_x=1.5,
            image_scale_y=1.5,
            scale_to_image=True,
        )
        original_x, original_y = 100.0, 200.0
        screen_x, screen_y = t.data_to_screen(original_x, original_y)
        data_x, data_y = t.screen_to_data(screen_x, screen_y)
        # Complex transformation should still roundtrip accurately
        assert abs(data_x - original_x) < 1e-9
        assert abs(data_y - original_y) < 1e-9

    def test_viewstate_quantization_with_min_scale_value(self) -> None:
        """Test ViewState quantization respects MIN_SCALE_VALUE for zoom."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            zoom_factor=1e-15,  # Extremely small
        )
        quantized = vs.quantized_for_cache()
        # Should be clamped to MIN_SCALE_VALUE
        assert quantized.zoom_factor >= MIN_SCALE_VALUE

    def test_batch_operations_preserve_array_dtype(self) -> None:
        """Test batch operations preserve float64 dtype."""
        t = Transform(scale=2.0, center_offset_x=0.0, center_offset_y=0.0)
        points = np.array([[10.0, 20.0]], dtype=np.float64)
        result = t.batch_data_to_screen(points)
        assert result.dtype == np.float64

    def test_transform_with_zero_display_height_and_no_flip(self) -> None:
        """Test transform with zero display height (no flip applied)."""
        t = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, flip_y=True, display_height=0)
        # With display_height=0, flip should not be applied
        screen_x, screen_y = t.data_to_screen(100.0, 200.0)
        assert screen_x == 100.0
        assert screen_y == 200.0  # Y unchanged since display_height is 0

    def test_viewstate_hash_excludes_background_image(self) -> None:
        """Test ViewState hash excludes background_image field."""
        mock_image1 = MagicMock()
        mock_image2 = MagicMock()
        vs1 = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            background_image=mock_image1,
        )
        vs2 = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            background_image=mock_image2,
        )
        # Hashes should be equal even with different background images
        assert hash(vs1) == hash(vs2)


class TestConstants:
    """Test module constants are properly defined."""

    def test_default_precision_constant(self) -> None:
        """Test DEFAULT_PRECISION constant."""
        assert DEFAULT_PRECISION == 0.1

    def test_zoom_precision_factor_constant(self) -> None:
        """Test ZOOM_PRECISION_FACTOR constant."""
        assert ZOOM_PRECISION_FACTOR == 100

    def test_zoom_precision_constant(self) -> None:
        """Test ZOOM_PRECISION constant."""
        assert ZOOM_PRECISION == 0.001
        assert ZOOM_PRECISION == DEFAULT_PRECISION / ZOOM_PRECISION_FACTOR

    def test_min_scale_value_constant(self) -> None:
        """Test MIN_SCALE_VALUE constant."""
        assert MIN_SCALE_VALUE == 1e-10
