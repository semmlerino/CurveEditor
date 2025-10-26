#!/usr/bin/env python3
"""
Test suite for validation strategy pattern.

Tests the different validation strategies and their behavior under various conditions.
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
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

import pytest
from core.validation_strategy import (
    AdaptiveValidationStrategy,
    ComprehensiveValidationStrategy,
    MinimalValidationStrategy,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    get_validation_strategy,
)


class TestValidationResult:
    """Test ValidationResult functionality."""

    def test_validation_result_creation(self):
        """Test creating validation results."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert len(result.issues) == 0
        assert result.validated_value is None

    def test_add_issue(self):
        """Test adding issues to result."""
        result = ValidationResult(is_valid=True)

        # Add info issue - shouldn't affect validity
        result.add_issue(
            ValidationIssue(field_name="test", value=1.0, severity=ValidationSeverity.INFO, message="Info message")
        )
        assert result.is_valid

        # Add warning - shouldn't affect validity
        result.add_issue(
            ValidationIssue(
                field_name="test", value=2.0, severity=ValidationSeverity.WARNING, message="Warning message"
            )
        )
        assert result.is_valid

        # Add critical - should affect validity
        result.add_issue(
            ValidationIssue(
                field_name="test", value=3.0, severity=ValidationSeverity.CRITICAL, message="Critical message"
            )
        )
        assert not result.is_valid

    def test_raise_if_invalid(self):
        """Test raising exception for invalid results."""
        result = ValidationResult(is_valid=True)
        result.raise_if_invalid()  # Should not raise

        result.add_issue(
            ValidationIssue(
                field_name="test", value=float("nan"), severity=ValidationSeverity.CRITICAL, message="NaN detected"
            )
        )

        with pytest.raises(ValueError, match="NaN detected"):
            result.raise_if_invalid()


class TestMinimalValidationStrategy:
    """Test minimal validation strategy."""

    @pytest.fixture
    def strategy(self) -> MinimalValidationStrategy:
        """Create minimal validation strategy."""
        return MinimalValidationStrategy()

    def test_validate_coordinate_valid(self, strategy: MinimalValidationStrategy):
        """Test validating valid coordinates."""
        result = strategy.validate_coordinate(10.0, 20.0)
        assert result.is_valid
        assert result.validated_value is None

    def test_validate_coordinate_nan(self, strategy: MinimalValidationStrategy):
        """Test handling NaN coordinates."""
        result = strategy.validate_coordinate(float("nan"), 20.0)
        assert result.is_valid  # Minimal strategy doesn't fail
        assert result.validated_value == (0.0, 20.0)  # Replaced with default

    def test_validate_coordinate_infinity(self, strategy: MinimalValidationStrategy):
        """Test handling infinity coordinates."""
        result = strategy.validate_coordinate(float("inf"), float("-inf"))
        assert result.is_valid
        # validate_finite replaces inf with 0.0, not clamping to max
        assert result.validated_value == (0.0, 0.0)  # Replaced with defaults

    def test_validate_scale(self, strategy: MinimalValidationStrategy):
        """Test scale validation."""
        # Valid scale
        result = strategy.validate_scale_factor(2.0)
        assert result.is_valid

        # Zero scale - should be replaced
        result = strategy.validate_scale_factor(0.0)
        assert result.is_valid
        assert result.validated_value == 1e-10

        # Negative scale - should be made positive
        result = strategy.validate_scale_factor(-5.0)
        assert result.is_valid
        assert result.validated_value == 5.0

    def test_validate_dimensions(self, strategy: MinimalValidationStrategy):
        """Test dimension validation."""
        # Valid dimensions
        result = strategy.validate_dimensions(800, 600)
        assert result.is_valid

        # Zero dimension
        result = strategy.validate_dimensions(0, 600)
        assert result.is_valid
        assert result.validated_value == (1, 600)

        # Negative dimension
        result = strategy.validate_dimensions(800, -600)
        assert result.is_valid
        assert result.validated_value == (800, 600)


class TestComprehensiveValidationStrategy:
    """Test comprehensive validation strategy."""

    @pytest.fixture
    def strategy(self) -> ComprehensiveValidationStrategy:
        """Create comprehensive validation strategy."""
        return ComprehensiveValidationStrategy()

    def test_validate_coordinate_valid(self, strategy: ComprehensiveValidationStrategy):
        """Test validating valid coordinates."""
        result = strategy.validate_coordinate(10.0, 20.0)
        assert result.is_valid

    def test_validate_coordinate_nan(self, strategy: ComprehensiveValidationStrategy):
        """Test NaN detection in comprehensive mode."""
        result = strategy.validate_coordinate(float("nan"), 20.0)
        assert not result.is_valid
        assert len(result.issues) == 1
        assert result.issues[0].severity == ValidationSeverity.CRITICAL

    def test_validate_coordinate_extreme(self, strategy: ComprehensiveValidationStrategy):
        """Test extreme coordinate detection."""
        result = strategy.validate_coordinate(1e13, 20.0)
        # Extreme values generate warnings but don't invalidate the result
        assert result.is_valid
        assert len(result.issues) > 0
        assert "exceeds maximum" in result.issues[0].message

    def test_validate_transform_params(self, strategy: ComprehensiveValidationStrategy):
        """Test transform parameter validation."""
        # Valid params
        params = {"scale": 2.0, "center_x": 100.0, "center_y": 200.0, "offset_x": 10.0, "offset_y": 20.0}
        result = strategy.validate_transform_params(params)
        assert result.is_valid

        # Invalid scale
        params["scale"] = 0.0
        result = strategy.validate_transform_params(params)
        assert not result.is_valid

        # NaN in params
        params["scale"] = 2.0
        params["center_x"] = float("nan")
        result = strategy.validate_transform_params(params)
        assert not result.is_valid


class TestAdaptiveValidationStrategy:
    """Test adaptive validation strategy."""

    @pytest.fixture
    def strategy(self) -> AdaptiveValidationStrategy:
        """Create adaptive validation strategy."""
        return AdaptiveValidationStrategy()

    def test_default_mode(self, strategy: AdaptiveValidationStrategy):
        """Test default adaptive mode."""
        # Uses __debug__ setting, which is True in test environment, so uses comprehensive
        result = strategy.validate_coordinate(float("nan"), 20.0)
        assert not result.is_valid  # Comprehensive fails on NaN

    def test_user_input_mode(self, strategy: AdaptiveValidationStrategy):
        """Test user input mode switches to comprehensive."""
        strategy.set_context(is_user_input=True)

        # Should use comprehensive for user input
        result = strategy.validate_coordinate(float("nan"), 20.0)
        assert not result.is_valid  # Comprehensive fails on NaN

    def test_render_loop_mode(self, strategy: AdaptiveValidationStrategy):
        """Test render loop always uses minimal."""
        strategy.set_context(is_render_loop=True, is_user_input=True)

        # Should use minimal in render loop even with user input
        result = strategy.validate_coordinate(float("nan"), 20.0)
        assert result.is_valid  # Minimal doesn't fail

    def test_batch_operation_mode(self, strategy: AdaptiveValidationStrategy):
        """Test batch operation mode."""
        strategy.set_context(is_batch_operation=True)

        # Should use minimal for batch operations
        result = strategy.validate_coordinate(1e13, 20.0)
        assert result.is_valid  # Minimal allows extreme values

    def test_debug_mode(self, strategy: AdaptiveValidationStrategy):
        """Test debug mode forces comprehensive."""
        strategy.set_context(is_debug=True)

        # Should use comprehensive in debug, but extreme values only generate warnings
        result = strategy.validate_coordinate(1e13, 20.0)
        assert result.is_valid  # Comprehensive warns on extreme but doesn't fail
        assert len(result.issues) > 0  # But should have warnings

    def test_switching_context(self, strategy: AdaptiveValidationStrategy):
        """Test switching between contexts."""
        # Start with user input
        strategy.set_context(is_user_input=True)
        result = strategy.validate_coordinate(float("nan"), 20.0)
        assert not result.is_valid

        # Switch to render loop
        strategy.set_context(is_render_loop=True)
        result = strategy.validate_coordinate(float("nan"), 20.0)
        assert result.is_valid

        # Back to default
        strategy.set_context()
        result = strategy.validate_coordinate(float("nan"), 20.0)
        assert result.is_valid


class TestValidationStrategySingletons:
    """Test singleton strategy instances."""

    def test_get_validation_strategy(self):
        """Test getting validation strategies."""
        # Get minimal
        minimal1 = get_validation_strategy("minimal")
        minimal2 = get_validation_strategy("minimal")
        assert minimal1 is minimal2  # Same instance
        assert isinstance(minimal1, MinimalValidationStrategy)

        # Get comprehensive
        comp1 = get_validation_strategy("comprehensive")
        comp2 = get_validation_strategy("comprehensive")
        assert comp1 is comp2
        assert isinstance(comp1, ComprehensiveValidationStrategy)

        # Get adaptive
        adaptive1 = get_validation_strategy("adaptive")
        adaptive2 = get_validation_strategy("adaptive")
        assert adaptive1 is adaptive2
        assert isinstance(adaptive1, AdaptiveValidationStrategy)

        # Invalid mode
        with pytest.raises(ValueError, match="Unknown validation strategy"):
            get_validation_strategy("invalid")

    def test_auto_mode_selection(self):
        """Test auto mode selection based on debug."""
        # Auto mode should return adaptive strategy
        strategy = get_validation_strategy("auto")
        # Auto mode returns adaptive, not minimal/comprehensive
        assert isinstance(strategy, AdaptiveValidationStrategy)


class TestValidationIntegration:
    """Test validation integration scenarios."""

    def test_pipeline_validation(self):
        """Test validation through a pipeline."""
        strategy = get_validation_strategy("comprehensive")

        # Simulate a validation pipeline
        coords_result = strategy.validate_coordinate(100.0, 200.0)
        coords_result.raise_if_invalid()

        scale_result = strategy.validate_scale_factor(2.0)
        scale_result.raise_if_invalid()

        dims_result = strategy.validate_dimensions(800, 600)
        dims_result.raise_if_invalid()

        # All should pass
        assert coords_result.is_valid
        assert scale_result.is_valid
        assert dims_result.is_valid

    def test_error_accumulation(self):
        """Test accumulating errors across validations."""
        strategy = get_validation_strategy("comprehensive")

        errors = []

        # Invalid coordinate
        result = strategy.validate_coordinate(float("nan"), 20.0)
        if not result.is_valid:
            errors.extend(result.issues)

        # Invalid scale
        result = strategy.validate_scale_factor(0.0)
        if not result.is_valid:
            errors.extend(result.issues)

        # Invalid dimension
        result = strategy.validate_dimensions(0, 0)
        if not result.is_valid:
            errors.extend(result.issues)

        # Should have collected multiple errors
        assert len(errors) > 0
        critical_errors = [e for e in errors if e.severity == ValidationSeverity.CRITICAL]
        assert len(critical_errors) > 0

    def test_performance_sensitive_validation(self):
        """Test validation in performance-sensitive context."""
        strategy = get_validation_strategy("adaptive")
        assert isinstance(strategy, AdaptiveValidationStrategy)

        # Simulate render loop
        strategy.set_context(is_render_loop=True)

        # Should handle invalid values quickly without failing
        for _ in range(1000):
            result = strategy.validate_coordinate(float("nan"), float("inf"))
            assert result.is_valid  # Minimal mode, always valid
            assert result.validated_value is not None  # But values corrected
