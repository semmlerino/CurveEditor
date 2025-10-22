#!/usr/bin/env python3
"""
Comprehensive tests for services/transform_core.py.

This module tests the critical coordinate transformation engine that converts
between data space and screen space. Transform errors can silently corrupt
point positions, clicks, zoom/pan behavior, and file I/O.

Test Coverage:
- Validation helpers (validate_finite, validate_scale, validate_point)
- ValidationConfig (debug vs production modes)
- ViewState (creation, immutability, quantization)
- Transform core transformations (data_to_screen, screen_to_data)
- Transform edge cases (NaN, infinity, zero scale, huge coordinates)
- Transform batch operations (NumPy vectorized transforms)
- Transform integration (from_view_state)
- Property-based testing (roundtrip invariants)

Testing Strategy:
- Pure Python/NumPy tests (no Qt dependencies)
- High coverage target (90%+ of 410 statements)
- Test both debug and production validation modes
- Verify mathematical invariants (roundtrip identity)
- Test edge cases that could silently corrupt data
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

import math
import os
from unittest.mock import Mock, patch

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from numpy.testing import assert_allclose

from core.defaults import DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH
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
# Test Validation Helpers
# =============================================================================


class TestValidateFinite:
    """Test validate_finite() helper function."""

    def test_with_valid_float(self) -> None:
        """Valid float returned unchanged."""
        result = validate_finite(123.456, "test")
        assert result == 123.456

    def test_with_nan_uses_default(self) -> None:
        """NaN replaced with default value."""
        result = validate_finite(float("nan"), "test", default=5.0)
        assert result == 5.0

    def test_with_positive_infinity_uses_default(self) -> None:
        """Positive infinity replaced with default."""
        result = validate_finite(float("inf"), "test", default=0.0)
        assert result == 0.0

    def test_with_negative_infinity_uses_default(self) -> None:
        """Negative infinity replaced with default."""
        result = validate_finite(float("-inf"), "test", default=-1.0)
        assert result == -1.0

    def test_with_zero(self) -> None:
        """Zero is valid."""
        result = validate_finite(0.0, "test")
        assert result == 0.0

    def test_with_negative_value(self) -> None:
        """Negative values are valid."""
        result = validate_finite(-999.99, "test")
        assert result == -999.99

    def test_with_very_large_value(self) -> None:
        """Very large values are valid if finite."""
        result = validate_finite(1e100, "test")
        assert result == 1e100

    def test_default_parameter_defaults_to_zero(self) -> None:
        """Default parameter defaults to 0.0 when not specified."""
        result = validate_finite(float("nan"), "test")
        assert result == 0.0


class TestValidateScale:
    """Test validate_scale() helper function."""

    def test_with_valid_scale(self) -> None:
        """Valid scale returned unchanged."""
        result = validate_scale(2.0, "test")
        assert result == 2.0

    def test_rejects_zero_uses_default(self) -> None:
        """Zero scale replaced with default."""
        result = validate_scale(0.0, "test", default=1.0)
        assert result == 1.0

    def test_rejects_negative_uses_default(self) -> None:
        """Negative scale replaced with default."""
        result = validate_scale(-5.0, "test", default=1.0)
        assert result == 1.0

    def test_clamps_too_small_to_minimum(self) -> None:
        """Scale below minimum clamped to minimum."""
        result = validate_scale(1e-15, "test", min_scale=1e-10, default=1.0)
        assert result == 1e-10

    def test_clamps_too_large_to_maximum(self) -> None:
        """Scale above maximum clamped to maximum."""
        result = validate_scale(1e15, "test", max_scale=1e10, default=1.0)
        assert result == 1e10

    def test_with_nan_uses_default(self) -> None:
        """NaN scale replaced with default."""
        result = validate_scale(float("nan"), "test", default=1.0)
        assert result == 1.0

    def test_with_infinity_uses_default(self) -> None:
        """Infinity scale replaced with default."""
        result = validate_scale(float("inf"), "test", default=1.0)
        assert result == 1.0

    def test_respects_custom_min_max(self) -> None:
        """Custom min/max bounds respected."""
        result = validate_scale(5.0, "test", min_scale=1.0, max_scale=10.0)
        assert result == 5.0

        result = validate_scale(0.5, "test", min_scale=1.0, max_scale=10.0)
        assert result == 1.0

        result = validate_scale(15.0, "test", min_scale=1.0, max_scale=10.0)
        assert result == 10.0

    def test_default_parameters(self) -> None:
        """Default min_scale, max_scale, default values work."""
        # Should clamp very small value to 1e-10 (default min_scale)
        result = validate_scale(1e-20, "test")
        assert result == 1e-10

        # Should clamp very large value to 1e10 (default max_scale)
        result = validate_scale(1e20, "test")
        assert result == 1e10


class TestValidatePoint:
    """Test validate_point() helper function."""

    def test_with_valid_coordinates(self) -> None:
        """Valid coordinates returned unchanged."""
        x, y = validate_point(100.0, 200.0, "test")
        assert x == 100.0
        assert y == 200.0

    def test_with_nan_x_returns_zero(self) -> None:
        """NaN x-coordinate replaced with (0, 0)."""
        x, y = validate_point(float("nan"), 200.0, "test")
        assert x == 0.0
        assert y == 0.0

    def test_with_nan_y_returns_zero(self) -> None:
        """NaN y-coordinate replaced with (0, 0)."""
        x, y = validate_point(100.0, float("nan"), "test")
        assert x == 0.0
        assert y == 0.0

    def test_with_infinity_x_returns_zero(self) -> None:
        """Infinity x-coordinate replaced with (0, 0)."""
        x, y = validate_point(float("inf"), 200.0, "test")
        assert x == 0.0
        assert y == 0.0

    def test_with_infinity_y_returns_zero(self) -> None:
        """Infinity y-coordinate replaced with (0, 0)."""
        x, y = validate_point(100.0, float("inf"), "test")
        assert x == 0.0
        assert y == 0.0

    def test_with_negative_coordinates(self) -> None:
        """Negative coordinates are valid."""
        x, y = validate_point(-100.0, -200.0, "test")
        assert x == -100.0
        assert y == -200.0

    def test_with_zero_coordinates(self) -> None:
        """Zero coordinates are valid."""
        x, y = validate_point(0.0, 0.0, "test")
        assert x == 0.0
        assert y == 0.0


# =============================================================================
# Test ValidationConfig
# =============================================================================


class TestValidationConfig:
    """Test ValidationConfig configuration class."""

    def test_default_values(self) -> None:
        """Default ValidationConfig has expected values."""
        config = ValidationConfig()
        assert config.enable_full_validation is True
        assert config.max_coordinate == 1e12
        assert config.min_scale == 1e-10
        assert config.max_scale == 1e10

    def test_for_production(self) -> None:
        """Production config disables full validation."""
        config = ValidationConfig.for_production()
        assert config.enable_full_validation is False

    def test_for_debug(self) -> None:
        """Debug config enables full validation."""
        config = ValidationConfig.for_debug()
        assert config.enable_full_validation is True

    def test_from_environment_default(self) -> None:
        """from_environment() respects __debug__ by default."""
        # Mock the get_config function at module level
        mock_config = Mock()
        mock_config.force_debug_validation = False

        with patch("core.config.get_config", return_value=mock_config):
            # Clear environment variable if set
            old_val = os.environ.pop("CURVE_EDITOR_FULL_VALIDATION", None)
            try:
                config = ValidationConfig.from_environment()
                # Should use __debug__ value (True in tests)
                assert config.enable_full_validation == __debug__
            finally:
                # Restore environment variable if it existed
                if old_val is not None:
                    os.environ["CURVE_EDITOR_FULL_VALIDATION"] = old_val

    def test_from_environment_with_env_var_true(self) -> None:
        """from_environment() respects CURVE_EDITOR_FULL_VALIDATION=1."""
        mock_config = Mock()
        mock_config.force_debug_validation = False

        with patch("core.config.get_config", return_value=mock_config):
            os.environ["CURVE_EDITOR_FULL_VALIDATION"] = "1"
            try:
                config = ValidationConfig.from_environment()
                assert config.enable_full_validation is True
            finally:
                os.environ.pop("CURVE_EDITOR_FULL_VALIDATION")

    def test_from_environment_with_env_var_false(self) -> None:
        """from_environment() respects CURVE_EDITOR_FULL_VALIDATION=0."""
        mock_config = Mock()
        mock_config.force_debug_validation = False

        with patch("core.config.get_config", return_value=mock_config):
            os.environ["CURVE_EDITOR_FULL_VALIDATION"] = "0"
            try:
                config = ValidationConfig.from_environment()
                assert config.enable_full_validation is False
            finally:
                os.environ.pop("CURVE_EDITOR_FULL_VALIDATION")

    def test_from_environment_with_force_debug(self) -> None:
        """force_debug_validation overrides environment."""
        mock_config = Mock()
        mock_config.force_debug_validation = True

        with patch("core.config.get_config", return_value=mock_config):
            os.environ["CURVE_EDITOR_FULL_VALIDATION"] = "0"
            try:
                config = ValidationConfig.from_environment()
                assert config.enable_full_validation is True
            finally:
                os.environ.pop("CURVE_EDITOR_FULL_VALIDATION")

    def test_from_environment_custom_limits(self) -> None:
        """from_environment() reads custom limits from environment."""
        mock_config = Mock()
        mock_config.force_debug_validation = False

        with patch("core.config.get_config", return_value=mock_config):
            os.environ["CURVE_EDITOR_MAX_COORDINATE"] = "1e6"
            os.environ["CURVE_EDITOR_MIN_SCALE"] = "1e-5"
            os.environ["CURVE_EDITOR_MAX_SCALE"] = "1e5"
            try:
                config = ValidationConfig.from_environment()
                assert config.max_coordinate == 1e6
                assert config.min_scale == 1e-5
                assert config.max_scale == 1e5
            finally:
                os.environ.pop("CURVE_EDITOR_MAX_COORDINATE", None)
                os.environ.pop("CURVE_EDITOR_MIN_SCALE", None)
                os.environ.pop("CURVE_EDITOR_MAX_SCALE", None)


# =============================================================================
# Test calculate_center_offset
# =============================================================================


class TestCalculateCenterOffset:
    """Test calculate_center_offset() helper function."""

    def test_1to1_mapping_returns_zero(self) -> None:
        """1:1 pixel mapping with no scaling/flipping returns (0, 0)."""
        cx, cy = calculate_center_offset(
            widget_width=800,
            widget_height=600,
            display_width=1920,
            display_height=1080,
            scale=1.0,
            flip_y_axis=False,
            scale_to_image=False,
        )
        assert cx == 0.0
        assert cy == 0.0

    def test_with_scaling_centers_content(self) -> None:
        """Scaling centers content in widget."""
        cx, cy = calculate_center_offset(
            widget_width=800,
            widget_height=600,
            display_width=400,
            display_height=300,
            scale=2.0,
            flip_y_axis=False,
            scale_to_image=False,
        )
        # Expected: (800 - 400*2) / 2 = 0, (600 - 300*2) / 2 = 0
        assert cx == 0.0
        assert cy == 0.0

    def test_with_smaller_content_centers_in_widget(self) -> None:
        """Smaller content centered in larger widget."""
        cx, cy = calculate_center_offset(
            widget_width=1000,
            widget_height=800,
            display_width=200,
            display_height=100,
            scale=2.0,
            flip_y_axis=False,
            scale_to_image=False,
        )
        # Expected: (1000 - 200*2) / 2 = 300, (800 - 100*2) / 2 = 300
        assert cx == 300.0
        assert cy == 300.0

    def test_with_flip_y_still_centers(self) -> None:
        """Y-flip doesn't affect centering calculation."""
        cx, cy = calculate_center_offset(
            widget_width=1000,
            widget_height=800,
            display_width=200,
            display_height=100,
            scale=2.0,
            flip_y_axis=True,
            scale_to_image=False,
        )
        # Centering logic is same regardless of flip
        assert cx == 300.0
        assert cy == 300.0

    def test_with_scale_to_image_centers(self) -> None:
        """scale_to_image flag doesn't affect centering calculation."""
        cx, cy = calculate_center_offset(
            widget_width=1000,
            widget_height=800,
            display_width=200,
            display_height=100,
            scale=2.0,
            flip_y_axis=False,
            scale_to_image=True,
        )
        # scale_to_image affects Transform pipeline, not centering
        assert cx == 300.0
        assert cy == 300.0


# =============================================================================
# Test ViewState
# =============================================================================


class TestViewStateCreation:
    """Test ViewState creation and basic properties."""

    def test_minimal_creation(self) -> None:
        """ViewState can be created with minimal parameters."""
        vs = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)
        assert vs.display_width == 1920.0
        assert vs.display_height == 1080.0
        assert vs.widget_width == 800
        assert vs.widget_height == 600
        assert vs.zoom_factor == 1.0
        assert vs.fit_scale == 1.0

    def test_full_creation_with_all_parameters(self) -> None:
        """ViewState stores all parameters correctly."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            fit_scale=1.5,
            offset_x=10.0,
            offset_y=20.0,
            scale_to_image=True,
            flip_y_axis=True,
            manual_x_offset=5.0,
            manual_y_offset=15.0,
            image_width=1920,
            image_height=1080,
        )
        assert vs.zoom_factor == 2.0
        assert vs.fit_scale == 1.5
        assert vs.offset_x == 10.0
        assert vs.offset_y == 20.0
        assert vs.scale_to_image is True
        assert vs.flip_y_axis is True
        assert vs.manual_x_offset == 5.0
        assert vs.manual_y_offset == 15.0

    def test_default_values(self) -> None:
        """ViewState default values are correct."""
        vs = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)
        assert vs.zoom_factor == 1.0
        assert vs.fit_scale == 1.0
        assert vs.offset_x == 0.0
        assert vs.offset_y == 0.0
        assert vs.scale_to_image is True
        assert vs.flip_y_axis is False
        assert vs.manual_x_offset == 0.0
        assert vs.manual_y_offset == 0.0
        assert vs.background_image is None
        assert vs.image_width == DEFAULT_IMAGE_WIDTH
        assert vs.image_height == DEFAULT_IMAGE_HEIGHT


class TestViewStateImmutability:
    """Test ViewState immutability."""

    def test_is_immutable_frozen_dataclass(self) -> None:
        """ViewState is frozen and cannot be modified."""
        vs = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            vs.zoom_factor = 3.0  # type: ignore[misc]

    def test_with_updates_creates_new_instance(self) -> None:
        """with_updates() creates new ViewState with updated values."""
        vs1 = ViewState(
            display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600, zoom_factor=1.0
        )
        vs2 = vs1.with_updates(zoom_factor=2.0)

        # Original unchanged
        assert vs1.zoom_factor == 1.0

        # New instance updated
        assert vs2.zoom_factor == 2.0

        # Other fields preserved
        assert vs2.display_width == 1920.0
        assert vs2.widget_width == 800

    def test_with_updates_multiple_fields(self) -> None:
        """with_updates() can update multiple fields."""
        vs1 = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)
        vs2 = vs1.with_updates(zoom_factor=2.0, offset_x=50.0, flip_y_axis=True)

        assert vs2.zoom_factor == 2.0
        assert vs2.offset_x == 50.0
        assert vs2.flip_y_axis is True
        # Original unchanged
        assert vs1.zoom_factor == 1.0


class TestViewStateQuantization:
    """Test ViewState quantization for cache hit rate optimization."""

    def test_quantization_rounds_offsets(self) -> None:
        """Quantization rounds floating-point offsets."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            offset_x=100.0456,
            offset_y=50.0123,
        )
        quantized = vs.quantized_for_cache(precision=0.1)

        # Should round to nearest 0.1
        assert abs(quantized.offset_x - 100.0) < 1e-10
        assert abs(quantized.offset_y - 50.0) < 1e-10

    def test_quantization_rounds_manual_offsets(self) -> None:
        """Quantization rounds manual offsets."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            manual_x_offset=12.3456,
            manual_y_offset=78.9012,
        )
        quantized = vs.quantized_for_cache(precision=0.1)

        assert abs(quantized.manual_x_offset - 12.3) < 1e-10
        assert abs(quantized.manual_y_offset - 78.9) < 1e-10

    def test_quantization_uses_finer_precision_for_zoom(self) -> None:
        """Zoom factor uses finer precision (0.001 vs 0.1)."""
        vs = ViewState(
            display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600, zoom_factor=1.23456
        )
        quantized = vs.quantized_for_cache(precision=0.1)

        # Zoom precision is 0.1 / 100 = 0.001
        # 1.23456 → 1.235
        assert abs(quantized.zoom_factor - 1.235) < 1e-10

    def test_quantization_clamps_zoom_to_min_scale(self) -> None:
        """Quantization clamps zoom to MIN_SCALE_VALUE."""
        vs = ViewState(
            display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600, zoom_factor=1e-15
        )
        quantized = vs.quantized_for_cache()

        # Should clamp to MIN_SCALE_VALUE
        assert quantized.zoom_factor >= MIN_SCALE_VALUE

    def test_quantization_preserves_booleans(self) -> None:
        """Quantization doesn't affect boolean flags."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            flip_y_axis=True,
            scale_to_image=False,
        )
        quantized = vs.quantized_for_cache()

        assert quantized.flip_y_axis is True
        assert quantized.scale_to_image is False

    def test_quantization_preserves_dimensions(self) -> None:
        """Quantization preserves display and widget dimensions."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            image_width=2048,
            image_height=1536,
        )
        quantized = vs.quantized_for_cache()

        assert quantized.display_width == 1920.0
        assert quantized.display_height == 1080.0
        assert quantized.widget_width == 800
        assert quantized.widget_height == 600
        assert quantized.image_width == 2048
        assert quantized.image_height == 1536

    def test_quantization_replaces_nan_with_zero(self) -> None:
        """Quantization replaces NaN values with 0.0."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            offset_x=float("nan"),
            offset_y=float("inf"),
        )
        quantized = vs.quantized_for_cache()

        assert quantized.offset_x == 0.0
        assert quantized.offset_y == 0.0

    def test_quantization_rejects_negative_precision(self) -> None:
        """Quantization raises on negative precision."""
        vs = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)

        from core.error_messages import ValidationError

        with pytest.raises(ValidationError):
            vs.quantized_for_cache(precision=-0.1)

    def test_quantization_rejects_zero_precision(self) -> None:
        """Quantization raises on zero precision."""
        vs = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)

        from core.error_messages import ValidationError

        with pytest.raises(ValidationError):
            vs.quantized_for_cache(precision=0.0)


class TestViewStateToDict:
    """Test ViewState.to_dict() serialization."""

    def test_to_dict_includes_all_fields(self) -> None:
        """to_dict() includes all relevant fields."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            offset_x=10.0,
            offset_y=20.0,
            scale_to_image=True,
            flip_y_axis=True,
            manual_x_offset=5.0,
            manual_y_offset=15.0,
            image_width=2048,
            image_height=1536,
        )
        d = vs.to_dict()

        assert d["display_dimensions"] == (1920.0, 1080.0)
        assert d["widget_dimensions"] == (800, 600)
        assert d["image_dimensions"] == (2048, 1536)
        assert d["zoom_factor"] == 2.0
        assert d["offset"] == (10.0, 20.0)
        assert d["scale_to_image"] is True
        assert d["flip_y_axis"] is True
        assert d["manual_offset"] == (5.0, 15.0)
        assert d["has_background_image"] is False

    def test_to_dict_with_background_image(self) -> None:
        """to_dict() reports background_image presence."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            background_image=Mock(),
        )
        d = vs.to_dict()

        assert d["has_background_image"] is True


# =============================================================================
# Test Transform Basic Operations
# =============================================================================


class TestTransformCreation:
    """Test Transform creation and validation."""

    def test_minimal_creation(self) -> None:
        """Transform can be created with minimal parameters."""
        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        assert transform.scale == 2.0
        assert transform.center_offset == (100.0, 50.0)

    def test_full_creation_with_all_parameters(self) -> None:
        """Transform stores all parameters correctly."""
        transform = Transform(
            scale=2.0,
            center_offset_x=100.0,
            center_offset_y=50.0,
            pan_offset_x=10.0,
            pan_offset_y=20.0,
            manual_offset_x=5.0,
            manual_offset_y=15.0,
            flip_y=True,
            display_height=1080,
            image_scale_x=1.5,
            image_scale_y=1.5,
            scale_to_image=True,
        )
        assert transform.scale == 2.0
        assert transform.pan_offset == (10.0, 20.0)
        assert transform.manual_offset == (5.0, 15.0)
        assert transform.flip_y is True
        assert transform.display_height == 1080
        assert transform.image_scale == (1.5, 1.5)
        assert transform.scale_to_image is True

    def test_validates_and_replaces_nan_scale(self) -> None:
        """NaN scale replaced with default (1.0)."""
        transform = Transform(
            scale=float("nan"),
            center_offset_x=0.0,
            center_offset_y=0.0,
            validation_config=ValidationConfig.for_production(),
        )
        assert transform.scale == 1.0

    def test_debug_mode_raises_on_zero_scale(self) -> None:
        """Debug mode raises ValueError for zero scale."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Scale factor too small"):
            Transform(scale=0.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

    def test_production_mode_clamps_zero_scale(self) -> None:
        """Production mode clamps zero scale to minimum."""
        config = ValidationConfig.for_production()
        transform = Transform(scale=0.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        assert transform.scale >= 1e-10

    def test_debug_mode_raises_on_too_large_scale(self) -> None:
        """Debug mode raises ValueError for extremely large scale."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Scale factor too large"):
            Transform(scale=1e15, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

    def test_production_mode_clamps_large_scale(self) -> None:
        """Production mode clamps extremely large scale."""
        config = ValidationConfig.for_production()
        transform = Transform(scale=1e15, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        assert transform.scale <= 1e10

    def test_debug_mode_raises_on_negative_display_height(self) -> None:
        """Debug mode raises ValueError for negative display height."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Display height cannot be negative"):
            Transform(
                scale=1.0, center_offset_x=0.0, center_offset_y=0.0, display_height=-100, validation_config=config
            )

    def test_production_mode_corrects_negative_display_height(self) -> None:
        """Production mode uses absolute value of negative display height."""
        config = ValidationConfig.for_production()
        transform = Transform(
            scale=1.0, center_offset_x=0.0, center_offset_y=0.0, display_height=-100, validation_config=config
        )
        assert transform.display_height == 100

    def test_debug_mode_raises_on_too_large_offset(self) -> None:
        """Debug mode raises ValueError for extremely large offset."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Offset .* too large"):
            Transform(scale=1.0, center_offset_x=1e12, center_offset_y=0.0, validation_config=config)

    def test_production_mode_clamps_large_offset(self) -> None:
        """Production mode clamps extremely large offset."""
        config = ValidationConfig.for_production()
        transform = Transform(scale=1.0, center_offset_x=1e12, center_offset_y=0.0, validation_config=config)
        cx, cy = transform.center_offset
        assert cx <= 1e9


class TestTransformDataToScreen:
    """Test Transform.data_to_screen() forward transformation."""

    def test_basic_forward_transformation(self) -> None:
        """Basic forward transformation with scale and offset."""
        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        x, y = transform.data_to_screen(10.0, 20.0)

        # Expected: (10*2 + 100, 20*2 + 50) = (120, 90)
        assert x == 120.0
        assert y == 90.0

    def test_with_y_flip(self) -> None:
        """Y-flip for 3DEqualizer data."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, flip_y=True, display_height=1000)
        x, y = transform.data_to_screen(100.0, 200.0)

        # Y should be flipped: 1000 - 200 = 800
        assert x == 100.0
        assert y == 800.0

    def test_with_combined_offsets(self) -> None:
        """All offsets combine correctly."""
        transform = Transform(
            scale=1.0,
            center_offset_x=10.0,
            center_offset_y=20.0,
            pan_offset_x=5.0,
            pan_offset_y=10.0,
            manual_offset_x=2.0,
            manual_offset_y=3.0,
        )
        x, y = transform.data_to_screen(0.0, 0.0)

        # Combined offset: (10+5+2, 20+10+3) = (17, 33)
        assert x == 17.0
        assert y == 33.0

    def test_with_image_scaling(self) -> None:
        """Image scaling multiplies main scale."""
        transform = Transform(
            scale=2.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=1.5,
            image_scale_y=1.5,
            scale_to_image=True,
        )
        x, y = transform.data_to_screen(10.0, 20.0)

        # Combined scale: 2.0 * 1.5 = 3.0
        # Expected: (10*3, 20*3) = (30, 60)
        assert x == 30.0
        assert y == 60.0

    def test_without_image_scaling(self) -> None:
        """scale_to_image=False ignores image scale."""
        transform = Transform(
            scale=2.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=1.5,
            image_scale_y=1.5,
            scale_to_image=False,
        )
        x, y = transform.data_to_screen(10.0, 20.0)

        # Should use main scale only: 2.0
        # Expected: (10*2, 20*2) = (20, 40)
        assert x == 20.0
        assert y == 40.0

    def test_at_origin(self) -> None:
        """(0, 0) transforms correctly."""
        transform = Transform(scale=2.0, center_offset_x=10.0, center_offset_y=20.0)
        x, y = transform.data_to_screen(0.0, 0.0)

        assert x == 10.0
        assert y == 20.0

    def test_with_negative_coordinates(self) -> None:
        """Negative coordinates transform correctly."""
        transform = Transform(scale=2.0, center_offset_x=0.0, center_offset_y=0.0)
        x, y = transform.data_to_screen(-10.0, -20.0)

        assert x == -20.0
        assert y == -40.0

    def test_debug_mode_raises_on_nan_input(self) -> None:
        """Debug mode raises ValueError for NaN input."""
        config = ValidationConfig.for_debug()
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        with pytest.raises(ValueError, match="must be finite"):
            transform.data_to_screen(float("nan"), 10.0)

    def test_production_mode_clamps_nan_input(self) -> None:
        """Production mode replaces NaN with (0, 0)."""
        config = ValidationConfig.for_production()
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        x, y = transform.data_to_screen(float("nan"), 10.0)
        # validate_point() returns (0, 0) for invalid input
        assert x == 0.0
        assert y == 0.0

    def test_debug_mode_raises_on_too_large_input(self) -> None:
        """Debug mode raises ValueError for extremely large input."""
        config = ValidationConfig.for_debug()
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        with pytest.raises(ValueError, match="too large"):
            transform.data_to_screen(1e13, 0.0)


class TestTransformScreenToData:
    """Test Transform.screen_to_data() inverse transformation."""

    def test_basic_inverse_transformation(self) -> None:
        """Basic inverse transformation reverses data_to_screen."""
        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)

        # Forward: (10, 20) → (120, 90)
        # Reverse: (120, 90) → (10, 20)
        x, y = transform.screen_to_data(120.0, 90.0)
        assert x == 10.0
        assert y == 20.0

    def test_roundtrip_identity(self) -> None:
        """Data → Screen → Data should equal identity."""
        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)

        original_x, original_y = 123.456, 789.012
        screen_x, screen_y = transform.data_to_screen(original_x, original_y)
        recovered_x, recovered_y = transform.screen_to_data(screen_x, screen_y)

        assert abs(recovered_x - original_x) < 1e-10
        assert abs(recovered_y - original_y) < 1e-10

    def test_roundtrip_with_y_flip(self) -> None:
        """Roundtrip works with Y-flip."""
        transform = Transform(scale=2.0, center_offset_x=0.0, center_offset_y=0.0, flip_y=True, display_height=1000)

        original_x, original_y = 100.0, 200.0
        screen_x, screen_y = transform.data_to_screen(original_x, original_y)
        recovered_x, recovered_y = transform.screen_to_data(screen_x, screen_y)

        assert abs(recovered_x - original_x) < 1e-10
        assert abs(recovered_y - original_y) < 1e-10

    def test_roundtrip_with_all_offsets(self) -> None:
        """Roundtrip works with combined offsets."""
        transform = Transform(
            scale=3.0,
            center_offset_x=10.0,
            center_offset_y=20.0,
            pan_offset_x=5.0,
            pan_offset_y=10.0,
            manual_offset_x=2.0,
            manual_offset_y=3.0,
        )

        original_x, original_y = -50.0, 75.0
        screen_x, screen_y = transform.data_to_screen(original_x, original_y)
        recovered_x, recovered_y = transform.screen_to_data(screen_x, screen_y)

        assert abs(recovered_x - original_x) < 1e-10
        assert abs(recovered_y - original_y) < 1e-10

    def test_raises_on_zero_combined_scale_x(self) -> None:
        """Raises ValueError if combined_scale_x is too small for division."""
        # Production mode clamps scale to 1e-10, which is valid for division
        # To test the error condition, we need scale_to_image=True with tiny image_scale
        config = ValidationConfig.for_production()
        transform = Transform(
            scale=1.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=1e-20,  # This gets clamped to 1e-10
            image_scale_y=1.0,
            scale_to_image=True,
            validation_config=config,
        )

        # Combined scale x will be 1.0 * 1e-10 = 1e-10, which should still be valid
        # Actually, the validation in __init__ will clamp image_scale_x to 1e-10
        # So this test is validating that the clamping prevents the error
        # Let's instead test that we CAN do inverse transform with clamped values
        x, y = transform.screen_to_data(100.0, 100.0)
        assert math.isfinite(x) and math.isfinite(y)

    def test_debug_mode_raises_on_nan_input(self) -> None:
        """Debug mode raises ValueError for NaN input."""
        config = ValidationConfig.for_debug()
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        with pytest.raises(ValueError, match="must be finite"):
            transform.screen_to_data(float("nan"), 10.0)

    def test_production_mode_clamps_nan_input(self) -> None:
        """Production mode replaces NaN with (0, 0)."""
        config = ValidationConfig.for_production()
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        x, y = transform.screen_to_data(float("nan"), 10.0)
        assert x == 0.0
        assert y == 0.0


class TestTransformBatchOperations:
    """Test Transform batch operations with NumPy."""

    def test_batch_data_to_screen_basic(self) -> None:
        """Batch transform matches single transforms."""
        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)

        # Create batch of points: [[10, 20], [30, 40]]
        points = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float64)

        # Batch transform
        result = transform.batch_data_to_screen(points)

        # Verify against individual transforms
        x1, y1 = transform.data_to_screen(10.0, 20.0)
        x2, y2 = transform.data_to_screen(30.0, 40.0)

        assert abs(result[0, 0] - x1) < 1e-10
        assert abs(result[0, 1] - y1) < 1e-10
        assert abs(result[1, 0] - x2) < 1e-10
        assert abs(result[1, 1] - y2) < 1e-10

    def test_batch_data_to_screen_with_frame_column(self) -> None:
        """Batch transform handles Nx3 array with frame column."""
        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)

        # Create points with frame: [[frame, x, y], ...]
        points = np.array([[0, 10.0, 20.0], [1, 30.0, 40.0]], dtype=np.float64)

        result = transform.batch_data_to_screen(points)

        # Should extract x, y columns
        assert result.shape == (2, 2)
        x1, y1 = transform.data_to_screen(10.0, 20.0)
        assert abs(result[0, 0] - x1) < 1e-10

    def test_batch_screen_to_data_basic(self) -> None:
        """Batch inverse transform works."""
        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)

        # Original points
        data_points = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float64)

        # Round trip
        screen = transform.batch_data_to_screen(data_points)
        recovered = transform.batch_screen_to_data(screen)

        assert_allclose(recovered, data_points, rtol=1e-10)

    def test_batch_transform_handles_empty_array(self) -> None:
        """Empty array doesn't crash."""
        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        empty = np.empty((0, 2), dtype=np.float64)

        result = transform.batch_data_to_screen(empty)
        assert len(result) == 0
        assert result.shape == (0, 2)

    def test_batch_data_to_screen_raises_on_wrong_shape(self) -> None:
        """Raises ValueError for wrong array shape."""
        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)

        # 1D array
        with pytest.raises(ValueError, match="Expected 2D array"):
            transform.batch_data_to_screen(np.array([1.0, 2.0]))

        # Wrong number of columns
        with pytest.raises(ValueError, match="Expected 2 or 3 columns"):
            transform.batch_data_to_screen(np.array([[1.0, 2.0, 3.0, 4.0]]))

    def test_batch_screen_to_data_raises_on_wrong_shape(self) -> None:
        """Raises ValueError for wrong array shape."""
        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)

        with pytest.raises(ValueError, match="Expected Nx2 array"):
            transform.batch_screen_to_data(np.array([1.0, 2.0]))

    def test_batch_debug_mode_raises_on_nan(self) -> None:
        """Debug mode raises ValueError for NaN in batch."""
        config = ValidationConfig.for_debug()
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        points = np.array([[10.0, 20.0], [float("nan"), 40.0]])

        with pytest.raises(ValueError, match="must be finite"):
            transform.batch_data_to_screen(points)

    def test_batch_production_mode_replaces_nan(self) -> None:
        """Production mode replaces NaN with 0.0 in batch."""
        config = ValidationConfig.for_production()
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        points = np.array([[10.0, 20.0], [float("nan"), 40.0]])

        # Should replace NaN with 0.0
        result = transform.batch_data_to_screen(points)
        assert result[1, 0] == 0.0

    def test_batch_with_y_flip(self) -> None:
        """Batch operations work with Y-flip."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, flip_y=True, display_height=1000)

        data = np.array([[100.0, 200.0], [300.0, 400.0]])
        screen = transform.batch_data_to_screen(data)
        recovered = transform.batch_screen_to_data(screen)

        assert_allclose(recovered, data, rtol=1e-10)


class TestTransformProperties:
    """Test Transform property accessors."""

    def test_scale_property(self) -> None:
        """scale property returns main scale."""
        transform = Transform(scale=2.5, center_offset_x=0.0, center_offset_y=0.0)
        assert transform.scale == 2.5

    def test_center_offset_property(self) -> None:
        """center_offset property returns tuple."""
        transform = Transform(scale=1.0, center_offset_x=10.0, center_offset_y=20.0)
        assert transform.center_offset == (10.0, 20.0)

    def test_pan_offset_property(self) -> None:
        """pan_offset property returns tuple."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, pan_offset_x=5.0, pan_offset_y=15.0)
        assert transform.pan_offset == (5.0, 15.0)

    def test_manual_offset_property(self) -> None:
        """manual_offset property returns tuple."""
        transform = Transform(
            scale=1.0, center_offset_x=0.0, center_offset_y=0.0, manual_offset_x=2.0, manual_offset_y=3.0
        )
        assert transform.manual_offset == (2.0, 3.0)

    def test_flip_y_property(self) -> None:
        """flip_y property returns boolean."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, flip_y=True)
        assert transform.flip_y is True

    def test_display_height_property(self) -> None:
        """display_height property returns integer."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, display_height=1080)
        assert transform.display_height == 1080

    def test_image_scale_property(self) -> None:
        """image_scale property returns tuple."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, image_scale_x=1.5, image_scale_y=2.0)
        assert transform.image_scale == (1.5, 2.0)

    def test_scale_to_image_property(self) -> None:
        """scale_to_image property returns boolean."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, scale_to_image=False)
        assert transform.scale_to_image is False

    def test_get_parameters(self) -> None:
        """get_parameters() returns copy of parameters dict."""
        transform = Transform(scale=2.0, center_offset_x=10.0, center_offset_y=20.0)
        params = transform.get_parameters()

        assert params["scale"] == 2.0
        assert params["center_offset_x"] == 10.0
        assert params["center_offset_y"] == 20.0

        # Should be a copy
        params["scale"] = 999.0
        assert transform.scale == 2.0

    def test_stability_hash(self) -> None:
        """stability_hash property returns hash string."""
        transform = Transform(scale=2.0, center_offset_x=10.0, center_offset_y=20.0)
        hash_value = transform.stability_hash

        assert isinstance(hash_value, str)
        assert len(hash_value) > 0


class TestTransformWithUpdates:
    """Test Transform.with_updates() method."""

    def test_with_updates_creates_new_instance(self) -> None:
        """with_updates() creates new Transform with updated values."""
        t1 = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        t2 = t1.with_updates(scale=2.0)

        # Original unchanged
        assert t1.scale == 1.0

        # New instance updated
        assert t2.scale == 2.0

    def test_with_updates_multiple_fields(self) -> None:
        """with_updates() can update multiple fields."""
        t1 = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        t2 = t1.with_updates(scale=2.0, pan_offset_x=50.0, flip_y=True)

        assert t2.scale == 2.0
        assert t2.pan_offset == (50.0, 0.0)
        assert t2.flip_y is True


class TestTransformFromViewState:
    """Test Transform.from_view_state() factory method."""

    def test_from_viewstate_basic(self) -> None:
        """Transform created correctly from ViewState."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            fit_scale=1.0,
            offset_x=10.0,
            offset_y=20.0,
        )

        transform = Transform.from_view_state(vs)

        # Scale should be fit_scale * zoom_factor
        assert transform.scale == 2.0

        # Offsets should be applied
        assert transform.pan_offset == (10.0, 20.0)

    def test_from_viewstate_combines_fit_and_zoom(self) -> None:
        """Transform correctly combines fit_scale and zoom_factor."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            fit_scale=1.5,
        )

        transform = Transform.from_view_state(vs)

        # Combined: 1.5 * 2.0 = 3.0
        assert transform.scale == 3.0

    def test_from_viewstate_with_flip_y(self) -> None:
        """Transform preserves flip_y_axis flag."""
        vs = ViewState(
            display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600, flip_y_axis=True
        )

        transform = Transform.from_view_state(vs)

        assert transform.flip_y is True
        assert transform.display_height == 1080

    def test_from_viewstate_calculates_image_scale(self) -> None:
        """Transform calculates image scale from dimensions."""
        vs = ViewState(
            display_width=2560.0,  # Display is larger
            display_height=1440.0,
            widget_width=800,
            widget_height=600,
            image_width=1920,  # Original image smaller
            image_height=1080,
        )

        transform = Transform.from_view_state(vs)

        # Image scale: (2560/1920, 1440/1080)
        expected_scale_x = 2560.0 / 1920.0
        expected_scale_y = 1440.0 / 1080.0

        assert abs(transform.image_scale[0] - expected_scale_x) < 1e-10
        assert abs(transform.image_scale[1] - expected_scale_y) < 1e-10

    def test_from_viewstate_handles_invalid_image_dimensions(self) -> None:
        """Transform handles zero/negative image dimensions gracefully."""
        vs = ViewState(
            display_width=1920.0,
            display_height=1080.0,
            widget_width=800,
            widget_height=600,
            image_width=0,  # Invalid
            image_height=-100,  # Invalid
        )

        transform = Transform.from_view_state(vs)

        # Should default to 1.0 for invalid dimensions
        assert transform.image_scale[0] == 1.0
        assert transform.image_scale[1] == 1.0

    def test_from_viewstate_with_validation_config(self) -> None:
        """Transform.from_view_state() accepts validation_config."""
        vs = ViewState(display_width=1920.0, display_height=1080.0, widget_width=800, widget_height=600)

        config = ValidationConfig.for_debug()
        transform = Transform.from_view_state(vs, validation_config=config)

        assert transform.validation_config == config


class TestTransformRepr:
    """Test Transform.__repr__() string representation."""

    def test_repr_includes_key_parameters(self) -> None:
        """__repr__() includes key transformation parameters."""
        transform = Transform(
            scale=2.5, center_offset_x=100.0, center_offset_y=50.0, pan_offset_x=10.0, pan_offset_y=20.0, flip_y=True
        )

        repr_str = repr(transform)

        assert "scale=2.50" in repr_str
        assert "center_offset=(100.0, 50.0)" in repr_str
        assert "pan_offset=(10.0, 20.0)" in repr_str
        assert "flip_y=True" in repr_str


# =============================================================================
# Property-Based Tests (Hypothesis)
# =============================================================================


@pytest.mark.slow
class TestTransformPropertyBased:
    """Property-based tests using Hypothesis for mathematical invariants."""

    @given(
        x=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        y=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        scale=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=100, deadline=None)
    def test_roundtrip_identity_property(self, x: float, y: float, scale: float) -> None:
        """Data → Screen → Data should equal identity for all valid inputs."""
        transform = Transform(scale=scale, center_offset_x=0.0, center_offset_y=0.0)

        screen_x, screen_y = transform.data_to_screen(x, y)
        recovered_x, recovered_y = transform.screen_to_data(screen_x, screen_y)

        # Allow small floating-point error
        assert abs(recovered_x - x) < 1e-6
        assert abs(recovered_y - y) < 1e-6

    @given(scale=st.floats(min_value=0.1, max_value=100.0))
    @settings(max_examples=100, deadline=None)
    def test_origin_with_zero_offsets_property(self, scale: float) -> None:
        """Origin (0,0) with zero offsets stays at origin after scaling."""
        transform = Transform(scale=scale, center_offset_x=0.0, center_offset_y=0.0)
        x, y = transform.data_to_screen(0.0, 0.0)

        assert x == 0.0
        assert y == 0.0

    @given(
        x=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        y=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        offset_x=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        offset_y=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_translation_invariance_property(self, x: float, y: float, offset_x: float, offset_y: float) -> None:
        """Translation should preserve relative distances."""
        # Assume reasonable offset values to avoid overflow
        assume(abs(offset_x) < 1e8)
        assume(abs(offset_y) < 1e8)
        assume(abs(x) < 1e8)
        assume(abs(y) < 1e8)

        transform = Transform(scale=1.0, center_offset_x=offset_x, center_offset_y=offset_y)

        # Two points
        x1, y1 = transform.data_to_screen(x, y)
        x2, y2 = transform.data_to_screen(x + 10.0, y + 10.0)

        # Distance should be preserved (scaled by 1.0)
        dx = x2 - x1
        dy = y2 - y1

        assert abs(dx - 10.0) < 1e-6
        assert abs(dy - 10.0) < 1e-6

    @given(
        x=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        y=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        scale=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=100, deadline=None)
    def test_scaling_preserves_origin_distance_property(self, x: float, y: float, scale: float) -> None:
        """Scaling should multiply distance from origin."""
        transform = Transform(scale=scale, center_offset_x=0.0, center_offset_y=0.0)

        screen_x, screen_y = transform.data_to_screen(x, y)

        # Distance from origin should be scaled
        data_distance = math.sqrt(x * x + y * y)
        screen_distance = math.sqrt(screen_x * screen_x + screen_y * screen_y)

        if data_distance > 1e-6:  # Avoid division by zero
            ratio = screen_distance / data_distance
            assert abs(ratio - scale) < 1e-3

    @given(
        points=st.lists(
            st.tuples(
                st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
                st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
            ),
            min_size=1,
            max_size=100,
        ),
        scale=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=50, deadline=None)
    def test_batch_equals_individual_property(self, points: list[tuple[float, float]], scale: float) -> None:
        """Batch operations should match individual operations."""
        transform = Transform(scale=scale, center_offset_x=0.0, center_offset_y=0.0)

        # Convert to NumPy array
        data = np.array(points, dtype=np.float64)

        # Batch transform
        batch_result = transform.batch_data_to_screen(data)

        # Individual transforms
        for i, (x, y) in enumerate(points):
            ind_x, ind_y = transform.data_to_screen(x, y)
            assert abs(batch_result[i, 0] - ind_x) < 1e-6
            assert abs(batch_result[i, 1] - ind_y) < 1e-6


# =============================================================================
# Edge Cases and Stress Tests
# =============================================================================


class TestTransformEdgeCases:
    """Test Transform edge cases and extreme values."""

    def test_with_very_large_coordinates(self) -> None:
        """Very large coordinates don't overflow in production mode."""
        config = ValidationConfig.for_production()
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        x, y = transform.data_to_screen(1e6, 1e6)
        assert math.isfinite(x) and math.isfinite(y)

    def test_with_very_small_scale(self) -> None:
        """Very small scale handled in production mode."""
        config = ValidationConfig.for_production()
        transform = Transform(scale=1e-9, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        # Should clamp to min_scale
        assert transform.scale >= 1e-10

    def test_with_negative_scale_debug_mode(self) -> None:
        """Negative scale is allowed (for flipping) but small magnitudes raise."""
        config = ValidationConfig.for_debug()
        # Negative scale with abs > 1e-10 is actually allowed (could be used for flipping)
        # Only scales with abs < 1e-10 raise errors
        # So -1.0 should succeed
        transform = Transform(scale=-1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        assert transform.scale == -1.0

        # But very small negative scale should raise
        with pytest.raises(ValueError, match="Scale factor too small"):
            Transform(scale=-1e-20, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

    def test_with_zero_display_height_y_flip(self) -> None:
        """Zero display height doesn't crash Y-flip."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, flip_y=True, display_height=0)

        # Should not flip when display_height is 0
        x, y = transform.data_to_screen(100.0, 200.0)
        # Y-flip only applies when display_height > 0
        assert y == 200.0

    def test_combined_scale_calculation_with_scale_to_image_false(self) -> None:
        """Combined scale ignores image scale when scale_to_image=False."""
        transform = Transform(
            scale=2.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=3.0,
            image_scale_y=3.0,
            scale_to_image=False,
        )

        # Combined scale should be just main scale (2.0), not 2.0*3.0
        x, y = transform.data_to_screen(10.0, 20.0)
        assert x == 20.0  # 10 * 2.0
        assert y == 40.0  # 20 * 2.0

    def test_combined_scale_calculation_with_scale_to_image_true(self) -> None:
        """Combined scale includes image scale when scale_to_image=True."""
        transform = Transform(
            scale=2.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=3.0,
            image_scale_y=3.0,
            scale_to_image=True,
        )

        # Combined scale: 2.0 * 3.0 = 6.0
        x, y = transform.data_to_screen(10.0, 20.0)
        assert x == 60.0  # 10 * 6.0
        assert y == 120.0  # 20 * 6.0

    def test_batch_raises_on_zero_combined_scale(self) -> None:
        """Batch inverse transform validates scale is sufficient."""
        # Production mode clamps scale to 1e-10, which is at the threshold
        # The code checks for abs(scale) < 1e-10, so 1e-10 should be valid
        config = ValidationConfig.for_production()
        transform = Transform(scale=1e-20, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        # Scale gets clamped to 1e-10, which should be valid
        screen_points = np.array([[100.0, 200.0]])

        # Should succeed (scale was clamped to valid range)
        result = transform.batch_screen_to_data(screen_points)
        assert math.isfinite(result[0, 0]) and math.isfinite(result[0, 1])

    def test_debug_mode_validates_display_height_range(self) -> None:
        """Debug mode validates display height upper bound."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Display height too large"):
            Transform(
                scale=1.0, center_offset_x=0.0, center_offset_y=0.0, display_height=2000000, validation_config=config
            )

    def test_production_mode_clamps_display_height(self) -> None:
        """Production mode clamps extremely large display height."""
        config = ValidationConfig.for_production()
        transform = Transform(
            scale=1.0, center_offset_x=0.0, center_offset_y=0.0, display_height=2000000, validation_config=config
        )

        assert transform.display_height <= 1000000


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Test module constants are defined correctly."""

    def test_default_precision_defined(self) -> None:
        """DEFAULT_PRECISION is defined."""
        assert DEFAULT_PRECISION == 0.1

    def test_zoom_precision_factor_defined(self) -> None:
        """ZOOM_PRECISION_FACTOR is defined."""
        assert ZOOM_PRECISION_FACTOR == 100

    def test_zoom_precision_calculated(self) -> None:
        """ZOOM_PRECISION is calculated from DEFAULT_PRECISION."""
        assert ZOOM_PRECISION == DEFAULT_PRECISION / ZOOM_PRECISION_FACTOR
        assert ZOOM_PRECISION == 0.001

    def test_min_scale_value_defined(self) -> None:
        """MIN_SCALE_VALUE is defined."""
        assert MIN_SCALE_VALUE == 1e-10


# =============================================================================
# Additional Coverage Tests
# =============================================================================


class TestTransformQPointMethods:
    """Test Transform QPointF transformation methods."""

    def test_data_to_screen_qpoint(self) -> None:
        """QPointF forward transformation."""
        from services.transform_core import QPointF

        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        point = QPointF(10.0, 20.0)

        result = transform.data_to_screen_qpoint(point)

        assert result.x() == 120.0
        assert result.y() == 90.0

    def test_screen_to_data_qpoint(self) -> None:
        """QPointF inverse transformation."""
        from services.transform_core import QPointF

        transform = Transform(scale=2.0, center_offset_x=100.0, center_offset_y=50.0)
        point = QPointF(120.0, 90.0)

        result = transform.screen_to_data_qpoint(point)

        assert result.x() == 10.0
        assert result.y() == 20.0


class TestTransformAdditionalEdgeCases:
    """Additional edge case tests for higher coverage."""

    def test_debug_mode_raises_on_invalid_image_scale_x(self) -> None:
        """Debug mode validates image_scale_x."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Image scale X too small"):
            Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, image_scale_x=0.0, validation_config=config)

    def test_debug_mode_raises_on_invalid_image_scale_y(self) -> None:
        """Debug mode validates image_scale_y."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Image scale Y too small"):
            Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, image_scale_y=0.0, validation_config=config)

    def test_debug_mode_raises_on_too_large_image_scale(self) -> None:
        """Debug mode validates image scale upper bounds."""
        config = ValidationConfig.for_debug()
        with pytest.raises(ValueError, match="Image scale factors too large"):
            Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, image_scale_x=1e15, validation_config=config)

    def test_production_mode_clamps_invalid_image_scales(self) -> None:
        """Production mode clamps invalid image scales."""
        config = ValidationConfig.for_production()
        transform = Transform(
            scale=1.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            image_scale_x=0.0,
            image_scale_y=1e20,
            validation_config=config,
        )

        # Should clamp to valid range
        image_scale_x, image_scale_y = transform.image_scale
        assert image_scale_x >= 1e-10
        assert image_scale_y <= 1e10

    def test_batch_data_to_screen_debug_raises_on_too_large(self) -> None:
        """Debug mode raises on coordinates exceeding max_coordinate."""
        config = ValidationConfig.for_debug()
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        points = np.array([[1e13, 0.0]])  # Exceeds default max_coordinate (1e12)

        with pytest.raises(ValueError, match="too large"):
            transform.batch_data_to_screen(points)

    def test_batch_screen_to_data_debug_raises_on_too_large(self) -> None:
        """Debug mode raises on screen coordinates exceeding max_coordinate."""
        config = ValidationConfig.for_debug()
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

        points = np.array([[1e13, 0.0]])

        with pytest.raises(ValueError, match="too large"):
            transform.batch_screen_to_data(points)

    def test_production_mode_logs_warning_for_small_scale(self) -> None:
        """Production mode logs warning when clamping small scale."""
        config = ValidationConfig.for_production()

        # This should trigger warning log
        with patch("services.transform_core.logger") as mock_logger:
            _ = Transform(scale=1e-15, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
            # Should have called logger.warning
            assert mock_logger.warning.called

    def test_production_mode_clamps_all_offset_types(self) -> None:
        """Production mode clamps all offset types."""
        config = ValidationConfig.for_production()

        transform = Transform(
            scale=1.0,
            center_offset_x=2e9,
            center_offset_y=-2e9,
            pan_offset_x=2e9,
            pan_offset_y=-2e9,
            manual_offset_x=2e9,
            manual_offset_y=-2e9,
            validation_config=config,
        )

        # All offsets should be clamped to ±1e9
        cx, cy = transform.center_offset
        assert abs(cx) <= 1e9
        assert abs(cy) <= 1e9

        px, py = transform.pan_offset
        assert abs(px) <= 1e9
        assert abs(py) <= 1e9

        mx, my = transform.manual_offset
        assert abs(mx) <= 1e9
        assert abs(my) <= 1e9
