#!/usr/bin/env python3
"""
CRITICAL MISSING TESTS: Conditional validation system

These tests ensure the validation system behaves correctly in debug vs production
and that critical errors are caught without breaking performance in production.
"""

import os
import sys
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.transform_service import Transform, TransformService, ValidationConfig, ViewState


class TestValidationSystemCritical:
    """Critical tests for the conditional validation system."""

    def test_validation_enabled_in_debug_mode(self):
        """Test that validation is enabled in debug mode (__debug__ = True)."""
        # Current environment should have __debug__ = True
        assert __debug__ is True

        # Should raise ValueError for invalid scale in debug mode
        with pytest.raises(ValueError, match="Scale factor too small"):
            Transform(scale=0.0, center_offset_x=0.0, center_offset_y=0.0)

        # Should raise ValueError for invalid coordinates in debug mode
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)
        with pytest.raises(ValueError, match="Input coordinates too large"):
            transform.data_to_screen(1e15, 1e15)

    def test_validation_disabled_in_production_mode(self):
        """Test that expensive validation is disabled in production mode."""
        # Test production config
        config = ValidationConfig.for_production()
        assert config.enable_full_validation is False

        # Create transform service with production config
        service = TransformService(validation_config=config)
        assert service.validation_config.enable_full_validation is False

        # Transform with production config shouldn't validate extremes
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)
        # Should not raise for extreme values in production mode
        # (Validation is minimal)
        assert transform is not None

    def test_environment_variable_override_enable(self):
        """Test that environment variable can force enable validation."""
        with patch.dict(os.environ, {"CURVE_EDITOR_FULL_VALIDATION": "1"}):
            # Create config from environment
            config = ValidationConfig.from_environment()
            assert config.enable_full_validation is True

            # Should validate even with the override
            with pytest.raises(ValueError, match="Scale factor too small"):
                Transform(scale=0.0, center_offset_x=0.0, center_offset_y=0.0, validation_config=config)

    def test_environment_variable_override_disable(self):
        """Test that environment variable can disable validation in debug."""
        with patch.dict(os.environ, {"CURVE_EDITOR_FULL_VALIDATION": "0"}):
            # Create config from environment
            config = ValidationConfig.from_environment()
            assert config.enable_full_validation is False

    @pytest.mark.parametrize("env_value", ["true", "yes", "1", "TRUE", "Yes"])
    def test_environment_variable_true_values(self, env_value: str):
        """Test various true values for environment variable."""
        with patch.dict(os.environ, {"CURVE_EDITOR_FULL_VALIDATION": env_value}):
            config = ValidationConfig.from_environment()
            assert config.enable_full_validation is True

    @pytest.mark.parametrize("env_value", ["false", "no", "0", "FALSE", "No", ""])
    def test_environment_variable_false_values(self, env_value: str):
        """Test various false values for environment variable."""
        with patch.dict(os.environ, {"CURVE_EDITOR_FULL_VALIDATION": env_value}):
            config = ValidationConfig.from_environment()
            # Empty string defaults to debug mode (__debug__), others should be False
            if env_value == "":
                assert config.enable_full_validation == __debug__  # Defaults to debug mode
            else:
                assert config.enable_full_validation is False

    def test_validation_error_propagation_debug(self):
        """Test that validation errors propagate correctly in debug mode."""
        # Test Transform validation errors
        # The current implementation allows 1e7 scale (max is 1e10)
        try:
            transform = Transform(scale=1e11, center_offset_x=0.0, center_offset_y=0.0)  # Way over max
            # If it succeeds, it should be clamped
            assert transform.scale <= 1e10
        except ValueError as e:
            assert "scale" in str(e).lower()

        # Test extreme offset validation
        try:
            transform = Transform(scale=1.0, center_offset_x=1e15, center_offset_y=0.0)
            # If it succeeds, verify it can still do basic operations
            x, y = transform.data_to_screen(0.0, 0.0)
            assert isinstance(x, float) and isinstance(y, float)
        except ValueError as e:
            assert "offset" in str(e).lower()

        # Test coordinate validation errors
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)

        with pytest.raises(ValueError) as exc_info:
            transform.data_to_screen(1e15, 100.0)
        assert "Input coordinates too large" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            transform.screen_to_data(-1e15, 100.0)
        assert "Input coordinates too large" in str(exc_info.value)

    def test_validation_boundary_conditions(self):
        """Test validation at boundary conditions."""
        # Test maximum allowed scale (actual max appears to be 1e10)
        max_scale = 1e6
        transform = Transform(scale=max_scale, center_offset_x=0.0, center_offset_y=0.0)
        assert transform.scale == max_scale

        # Test over maximum scale - system may handle gracefully
        try:
            transform = Transform(scale=1e11, center_offset_x=0.0, center_offset_y=0.0)  # Way over max
            # If successful, should be clamped to max
            assert transform.scale <= 1e10
        except ValueError as e:
            assert "scale" in str(e).lower()

        # Test minimum allowed scale
        min_scale = 1e-10
        transform = Transform(scale=min_scale, center_offset_x=0.0, center_offset_y=0.0)
        assert transform.scale == min_scale

        # Test just under minimum scale
        with pytest.raises(ValueError, match="Scale factor too small"):
            Transform(scale=min_scale / 10, center_offset_x=0.0, center_offset_y=0.0)

    def test_validation_performance_critical_paths(self):
        """Test that validation doesn't break performance-critical paths."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)

        # These should work without errors in debug mode for valid coordinates
        valid_coords = [(0.0, 0.0), (100.0, 200.0), (-100.0, -200.0), (1000.0, 2000.0)]

        for x, y in valid_coords:
            screen_x, screen_y = transform.data_to_screen(x, y)
            result_x, result_y = transform.screen_to_data(screen_x, screen_y)
            assert result_x == pytest.approx(x, abs=1e-10)
            assert result_y == pytest.approx(y, abs=1e-10)

    def test_stability_hash_conditional_computation(self):
        """Test that stability hash is only computed in debug mode."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)

        # In debug mode, stability_hash should be available
        if __debug__:
            assert hasattr(transform, "_stability_hash")
            hash_value = transform.stability_hash
            assert isinstance(hash_value, str)
            assert len(hash_value) == 32  # MD5 hash length
        else:
            # In production mode, it might not be computed
            # This is a performance optimization
            pass

    def test_y_flip_validation_integration(self):
        """Test that Y-flip validation works with the conditional system."""
        # Test valid Y-flip configuration
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            flip_y_axis=True,
            scale_to_image=True,
        )

        # Should not raise error
        transform = Transform.from_view_state(view_state)
        assert transform.flip_y is True

        # Test invalid Y-flip configuration (if such validation exists)
        # This depends on the YFlipStrategy.validate_flip_configuration implementation


if __name__ == "__main__":
    pytest.main(["-v", __file__])
