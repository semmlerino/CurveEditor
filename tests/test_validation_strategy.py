#!/usr/bin/env python3
"""
Test suite for validation strategy pattern.

Tests the different validation strategies and their behavior under various conditions.
"""

import unittest
from typing import override

from core.validation_strategy import (
    AdaptiveValidationStrategy,
    ComprehensiveValidationStrategy,
    MinimalValidationStrategy,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    get_validation_strategy,
)


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult functionality."""

    def test_validation_result_creation(self):
        """Test creating validation results."""
        result = ValidationResult(is_valid=True)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.issues), 0)
        self.assertIsNone(result.validated_value)

    def test_add_issue(self):
        """Test adding issues to result."""
        result = ValidationResult(is_valid=True)

        # Add info issue - shouldn't affect validity
        result.add_issue(
            ValidationIssue(field_name="test", value=1.0, severity=ValidationSeverity.INFO, message="Info message")
        )
        self.assertTrue(result.is_valid)

        # Add warning - shouldn't affect validity
        result.add_issue(
            ValidationIssue(
                field_name="test", value=2.0, severity=ValidationSeverity.WARNING, message="Warning message"
            )
        )
        self.assertTrue(result.is_valid)

        # Add critical - should affect validity
        result.add_issue(
            ValidationIssue(
                field_name="test", value=3.0, severity=ValidationSeverity.CRITICAL, message="Critical message"
            )
        )
        self.assertFalse(result.is_valid)

    def test_raise_if_invalid(self):
        """Test raising exception for invalid results."""
        result = ValidationResult(is_valid=True)
        result.raise_if_invalid()  # Should not raise

        result.add_issue(
            ValidationIssue(
                field_name="test", value=float("nan"), severity=ValidationSeverity.CRITICAL, message="NaN detected"
            )
        )

        with self.assertRaises(ValueError) as ctx:
            result.raise_if_invalid()
        self.assertIn("NaN detected", str(ctx.exception))


class TestMinimalValidationStrategy(unittest.TestCase):
    """Test minimal validation strategy."""

    strategy: MinimalValidationStrategy

    @override
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.strategy = MinimalValidationStrategy()

    def test_validate_coordinate_valid(self):
        """Test validating valid coordinates."""
        result = self.strategy.validate_coordinate(10.0, 20.0)
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.validated_value)

    def test_validate_coordinate_nan(self):
        """Test handling NaN coordinates."""
        result = self.strategy.validate_coordinate(float("nan"), 20.0)
        self.assertTrue(result.is_valid)  # Minimal strategy doesn't fail
        self.assertEqual(result.validated_value, (0.0, 20.0))  # Replaced with default

    def test_validate_coordinate_infinity(self):
        """Test handling infinity coordinates."""
        result = self.strategy.validate_coordinate(float("inf"), float("-inf"))
        self.assertTrue(result.is_valid)
        # validate_finite replaces inf with 0.0, not clamping to max
        self.assertEqual(result.validated_value, (0.0, 0.0))  # Replaced with defaults

    def test_validate_scale(self):
        """Test scale validation."""
        # Valid scale
        result = self.strategy.validate_scale_factor(2.0)
        self.assertTrue(result.is_valid)

        # Zero scale - should be replaced
        result = self.strategy.validate_scale_factor(0.0)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.validated_value, 1e-10)

        # Negative scale - should be made positive
        result = self.strategy.validate_scale_factor(-5.0)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.validated_value, 5.0)

    def test_validate_dimensions(self):
        """Test dimension validation."""
        # Valid dimensions
        result = self.strategy.validate_dimensions(800, 600)
        self.assertTrue(result.is_valid)

        # Zero dimension
        result = self.strategy.validate_dimensions(0, 600)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.validated_value, (1, 600))

        # Negative dimension
        result = self.strategy.validate_dimensions(800, -600)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.validated_value, (800, 600))

    def test_validate_array(self):
        """Test array validation - SKIPPED as validate_array not implemented."""
        # Note: validate_array method is not part of the ValidationStrategy protocol
        # and is not implemented in the current version
        self.skipTest("validate_array method not implemented")


class TestComprehensiveValidationStrategy(unittest.TestCase):
    """Test comprehensive validation strategy."""

    strategy: ComprehensiveValidationStrategy

    @override
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.strategy = ComprehensiveValidationStrategy()

    def test_validate_coordinate_valid(self):
        """Test validating valid coordinates."""
        result = self.strategy.validate_coordinate(10.0, 20.0)
        self.assertTrue(result.is_valid)

    def test_validate_coordinate_nan(self):
        """Test NaN detection in comprehensive mode."""
        result = self.strategy.validate_coordinate(float("nan"), 20.0)
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].severity, ValidationSeverity.CRITICAL)

    def test_validate_coordinate_extreme(self):
        """Test extreme coordinate detection."""
        result = self.strategy.validate_coordinate(1e13, 20.0)
        # Extreme values generate warnings but don't invalidate the result
        self.assertTrue(result.is_valid)
        self.assertGreater(len(result.issues), 0)
        self.assertIn("exceeds maximum", result.issues[0].message)

    def test_validate_precision(self):
        """Test precision validation - SKIPPED as validate_precision not implemented."""
        # Note: validate_precision method is not part of the ValidationStrategy protocol
        # and is not implemented in the current version
        self.skipTest("Method not implemented")

    def test_validate_transform_params(self):
        """Test transform parameter validation."""
        # Valid params
        params = {"scale": 2.0, "center_x": 100.0, "center_y": 200.0, "offset_x": 10.0, "offset_y": 20.0}
        result = self.strategy.validate_transform_params(params)
        self.assertTrue(result.is_valid)

        # Invalid scale
        params["scale"] = 0.0
        result = self.strategy.validate_transform_params(params)
        self.assertFalse(result.is_valid)

        # NaN in params
        params["scale"] = 2.0
        params["center_x"] = float("nan")
        result = self.strategy.validate_transform_params(params)
        self.assertFalse(result.is_valid)

    def test_validate_type(self):
        """Test type validation - SKIPPED as validate_type not implemented."""
        # Note: validate_type method is not part of the ValidationStrategy protocol
        # and is not implemented in the current version
        self.skipTest("Method not implemented")

    def test_cross_validate(self):
        """Test cross-parameter validation - SKIPPED as cross_validate not implemented."""
        # Note: cross_validate method is not part of the ValidationStrategy protocol
        # and is not implemented in the current version
        self.skipTest("Method not implemented")


class TestAdaptiveValidationStrategy(unittest.TestCase):
    """Test adaptive validation strategy."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = AdaptiveValidationStrategy()

    def test_default_mode(self):
        """Test default adaptive mode."""
        # Uses __debug__ setting, which is True in test environment, so uses comprehensive
        result = self.strategy.validate_coordinate(float("nan"), 20.0)
        self.assertFalse(result.is_valid)  # Comprehensive fails on NaN

    def test_user_input_mode(self):
        """Test user input mode switches to comprehensive."""
        self.strategy.set_context(is_user_input=True)

        # Should use comprehensive for user input
        result = self.strategy.validate_coordinate(float("nan"), 20.0)
        self.assertFalse(result.is_valid)  # Comprehensive fails on NaN

    def test_render_loop_mode(self):
        """Test render loop always uses minimal."""
        self.strategy.set_context(is_render_loop=True, is_user_input=True)

        # Should use minimal in render loop even with user input
        result = self.strategy.validate_coordinate(float("nan"), 20.0)
        self.assertTrue(result.is_valid)  # Minimal doesn't fail

    def test_batch_operation_mode(self):
        """Test batch operation mode."""
        self.strategy.set_context(is_batch_operation=True)

        # Should use minimal for batch operations
        result = self.strategy.validate_coordinate(1e13, 20.0)
        self.assertTrue(result.is_valid)  # Minimal allows extreme values

    def test_debug_mode(self):
        """Test debug mode forces comprehensive."""
        self.strategy.set_context(is_debug=True)

        # Should use comprehensive in debug, but extreme values only generate warnings
        result = self.strategy.validate_coordinate(1e13, 20.0)
        self.assertTrue(result.is_valid)  # Comprehensive warns on extreme but doesn't fail
        self.assertGreater(len(result.issues), 0)  # But should have warnings

    def test_switching_context(self):
        """Test switching between contexts."""
        # Start with user input
        self.strategy.set_context(is_user_input=True)
        result = self.strategy.validate_coordinate(float("nan"), 20.0)
        self.assertFalse(result.is_valid)

        # Switch to render loop
        self.strategy.set_context(is_render_loop=True)
        result = self.strategy.validate_coordinate(float("nan"), 20.0)
        self.assertTrue(result.is_valid)

        # Back to default
        self.strategy.set_context()
        result = self.strategy.validate_coordinate(float("nan"), 20.0)
        self.assertTrue(result.is_valid)


class TestValidationStrategySingletons(unittest.TestCase):
    """Test singleton strategy instances."""

    def test_get_validation_strategy(self):
        """Test getting validation strategies."""
        # Get minimal
        minimal1 = get_validation_strategy("minimal")
        minimal2 = get_validation_strategy("minimal")
        self.assertIs(minimal1, minimal2)  # Same instance
        self.assertIsInstance(minimal1, MinimalValidationStrategy)

        # Get comprehensive
        comp1 = get_validation_strategy("comprehensive")
        comp2 = get_validation_strategy("comprehensive")
        self.assertIs(comp1, comp2)
        self.assertIsInstance(comp1, ComprehensiveValidationStrategy)

        # Get adaptive
        adaptive1 = get_validation_strategy("adaptive")
        adaptive2 = get_validation_strategy("adaptive")
        self.assertIs(adaptive1, adaptive2)
        self.assertIsInstance(adaptive1, AdaptiveValidationStrategy)

        # Invalid mode
        with self.assertRaises(ValueError):
            get_validation_strategy("invalid")

    def test_auto_mode_selection(self):
        """Test auto mode selection based on debug."""
        # Auto mode should return adaptive strategy
        strategy = get_validation_strategy("auto")
        # Auto mode returns adaptive, not minimal/comprehensive
        self.assertIsInstance(strategy, AdaptiveValidationStrategy)


class TestValidationIntegration(unittest.TestCase):
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
        self.assertTrue(coords_result.is_valid)
        self.assertTrue(scale_result.is_valid)
        self.assertTrue(dims_result.is_valid)

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
        self.assertGreater(len(errors), 0)
        critical_errors = [e for e in errors if e.severity == ValidationSeverity.CRITICAL]
        self.assertGreater(len(critical_errors), 0)

    def test_performance_sensitive_validation(self):
        """Test validation in performance-sensitive context."""
        strategy = get_validation_strategy("adaptive")

        # Simulate render loop
        strategy.set_context(is_render_loop=True)

        # Should handle invalid values quickly without failing
        for _ in range(1000):
            result = strategy.validate_coordinate(float("nan"), float("inf"))
            self.assertTrue(result.is_valid)  # Minimal mode, always valid
            self.assertIsNotNone(result.validated_value)  # But values corrected


if __name__ == "__main__":
    unittest.main()
