#!/usr/bin/env python
"""
Validation strategy pattern for CurveEditor.

This module provides a flexible validation framework using the strategy pattern,
allowing different validation levels based on runtime requirements (debug vs production).
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, override, runtime_checkable

from core.validation_utils import ensure_valid_scale as validate_scale
from core.validation_utils import validate_finite, validate_point


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    CRITICAL = "critical"  # Must be fixed, will cause crashes
    WARNING = "warning"  # Should be fixed, may cause incorrect behavior
    INFO = "info"  # Informational, minor issues


@dataclass
class ValidationIssue:
    """Structured error reporting for validation failures."""

    field_name: str
    value: Any
    severity: ValidationSeverity
    message: str
    suggestion: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def format(self) -> str:
        """Format the validation issue as a user-friendly message."""
        base_msg = f"[{self.severity.value.upper()}] {self.field_name}: {self.message}"
        if self.suggestion:
            base_msg += f" → {self.suggestion}"
        return base_msg

    def to_exception(self) -> ValueError:
        """Convert to an exception for critical issues."""
        return ValueError(self.format())


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    validated_value: Any = None

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue to the result."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.CRITICAL:
            self.is_valid = False

    def get_critical_issues(self) -> list[ValidationIssue]:
        """Get only critical issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.CRITICAL]

    def get_warnings(self) -> list[ValidationIssue]:
        """Get warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def raise_if_invalid(self) -> None:
        """Raise an exception if there are critical issues."""
        if not self.is_valid:
            critical = self.get_critical_issues()
            if critical:
                raise critical[0].to_exception()


@runtime_checkable
class ValidationStrategy(Protocol):
    """Protocol for validation strategies."""

    def validate_coordinate(self, x: float, y: float, context: str = "") -> ValidationResult:
        """Validate a coordinate pair."""
        ...

    def validate_scale_factor(self, scale: float, context: str = "") -> ValidationResult:
        """Validate a scale factor."""
        ...

    def validate_dimensions(self, width: float, height: float, context: str = "") -> ValidationResult:
        """Validate dimensions."""
        ...

    def validate_transform_params(self, params: dict[str, Any]) -> ValidationResult:
        """Validate transform parameters."""
        ...

    @property
    def name(self) -> str:
        """Get strategy name."""
        ...


class BaseValidationStrategy(ABC):
    """Base class for validation strategies."""

    @abstractmethod
    def validate_coordinate(self, x: float, y: float, context: str = "") -> ValidationResult:
        """Validate a coordinate pair."""
        pass

    @abstractmethod
    def validate_scale_factor(self, scale: float, context: str = "") -> ValidationResult:
        """Validate a scale factor."""
        pass

    @abstractmethod
    def validate_dimensions(self, width: float, height: float, context: str = "") -> ValidationResult:
        """Validate dimensions."""
        pass

    @abstractmethod
    def validate_transform_params(self, params: dict[str, Any]) -> ValidationResult:
        """Validate transform parameters."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get strategy name."""
        pass


class MinimalValidationStrategy(BaseValidationStrategy):
    """
    Minimal validation for production mode.

    Only checks for critical issues that would cause crashes:
    - NaN/infinity values
    - Zero dimensions
    - Extreme values that exceed system limits
    """

    @override
    def validate_coordinate(self, x: float, y: float, context: str = "") -> ValidationResult:
        """Validate coordinates with minimal checks."""
        result = ValidationResult(is_valid=True)

        # Only check for NaN/infinity
        x_valid = validate_finite(x, name=f"{context}_x")
        y_valid = validate_finite(y, name=f"{context}_y")

        if x_valid != x or y_valid != y:
            result.validated_value = (x_valid, y_valid)
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_coordinates",
                    value=(x, y),
                    severity=ValidationSeverity.WARNING,
                    message="Non-finite coordinates replaced with defaults",
                    suggestion="Check input data for NaN/infinity values",
                )
            )
        # else: validated_value remains None when no changes needed

        return result

    @override
    def validate_scale_factor(self, scale: float, context: str = "") -> ValidationResult:
        """Validate scale with minimal checks."""
        result = ValidationResult(is_valid=True)

        # Basic sanity check
        if scale <= 0 or scale != scale:  # NaN check
            # Use minimum scale for zero/negative, take absolute value for negative
            if scale < 0:
                result.validated_value = abs(scale) if abs(scale) > 1e-10 else 1e-10
            else:
                result.validated_value = 1e-10  # Minimum scale for zero/NaN
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_scale",
                    value=scale,
                    severity=ValidationSeverity.WARNING,  # Minimal strategy is lenient
                    message="Invalid scale factor corrected",
                    suggestion="Scale must be positive and finite",
                )
            )
        # else: validated_value remains None when no changes needed

        return result

    @override
    def validate_dimensions(self, width: float, height: float, context: str = "") -> ValidationResult:
        """Validate dimensions with minimal checks."""
        result = ValidationResult(is_valid=True)

        if width <= 0 or height <= 0:
            # For negative, use absolute value; for zero, use 1
            fixed_width = abs(width) if width != 0 else 1
            fixed_height = abs(height) if height != 0 else 1
            result.validated_value = (fixed_width, fixed_height)
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_dimensions",
                    value=(width, height),
                    severity=ValidationSeverity.WARNING,  # Minimal strategy is lenient
                    message="Invalid dimensions corrected",
                    suggestion="Width and height must be positive",
                )
            )
        # else: validated_value remains None when no changes needed

        return result

    @override
    def validate_transform_params(self, params: dict[str, Any]) -> ValidationResult:
        """Validate transform parameters with minimal checks."""
        result = ValidationResult(is_valid=True)
        validated = {}

        # Only validate critical parameters
        if "scale" in params:
            scale_result = self.validate_scale_factor(params["scale"], "transform")
            validated["scale"] = scale_result.validated_value
            result.issues.extend(scale_result.issues)

        if "width" in params and "height" in params:
            dim_result = self.validate_dimensions(params["width"], params["height"], "transform")
            validated["width"], validated["height"] = dim_result.validated_value
            result.issues.extend(dim_result.issues)

        # Pass through other parameters
        for key, value in params.items():
            if key not in validated:
                validated[key] = value

        result.validated_value = validated
        result.is_valid = all(i.severity != ValidationSeverity.CRITICAL for i in result.issues)
        return result

    @property
    @override
    def name(self) -> str:
        """Get strategy name."""
        return "minimal"


class ComprehensiveValidationStrategy(BaseValidationStrategy):
    """
    Comprehensive validation for debug mode.

    Performs extensive validation including:
    - All minimal validation checks
    - Range validation with configurable limits
    - Type checking
    - Precision validation
    - Cross-parameter consistency checks
    """

    def __init__(
        self,
        max_coordinate: float = 1e12,
        min_scale: float = 1e-10,
        max_scale: float = 1e10,
        precision: float = 1e-10,
    ):
        """Initialize with configurable limits."""
        self.max_coordinate = max_coordinate
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.precision = precision

    @override
    def validate_coordinate(self, x: float, y: float, context: str = "") -> ValidationResult:
        """Validate coordinates with comprehensive checks."""
        result = ValidationResult(is_valid=True)

        # Check types
        if not isinstance(x, int | float) or not isinstance(y, int | float):
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_coordinates",
                    value=(x, y),
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Invalid coordinate types: {type(x).__name__}, {type(y).__name__}",
                    suggestion="Coordinates must be numeric",
                )
            )
            result.validated_value = (0.0, 0.0)
            return result

        # Check for NaN/inf BEFORE calling validate_point
        if math.isnan(x) or math.isinf(x) or math.isnan(y) or math.isinf(y):
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_coordinates",
                    value=(x, y),
                    severity=ValidationSeverity.CRITICAL,
                    message="Coordinates contain NaN or infinity values",
                    suggestion="Use finite numeric values",
                )
            )
            result.validated_value = (0.0, 0.0)
            return result

        # Validate with utilities (checks for NaN/inf)
        x_valid, y_valid = validate_point(x, y)

        # Check range
        if abs(x) > self.max_coordinate:
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_x",
                    value=x,
                    severity=ValidationSeverity.WARNING,
                    message=f"X coordinate exceeds maximum ({self.max_coordinate})",
                    suggestion=f"Consider using values between -{self.max_coordinate} and {self.max_coordinate}",
                )
            )

        if abs(y) > self.max_coordinate:
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_y",
                    value=y,
                    severity=ValidationSeverity.WARNING,
                    message=f"Y coordinate exceeds maximum ({self.max_coordinate})",
                    suggestion=f"Consider using values between -{self.max_coordinate} and {self.max_coordinate}",
                )
            )

        # Check precision
        if x != 0 and abs(x) < self.precision:
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_x",
                    value=x,
                    severity=ValidationSeverity.INFO,
                    message=f"X coordinate below precision threshold ({self.precision})",
                    suggestion="Very small values may be rounded to zero",
                )
            )

        result.validated_value = (x_valid, y_valid)
        return result

    @override
    def validate_scale_factor(self, scale: float, context: str = "") -> ValidationResult:
        """Validate scale with comprehensive checks."""
        result = ValidationResult(is_valid=True)

        # Type check
        if not isinstance(scale, int | float):
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_scale",
                    value=scale,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Invalid scale type: {type(scale).__name__}",
                    suggestion="Scale must be numeric",
                )
            )
            result.validated_value = 1.0
            return result

        # Check for NaN/inf/zero BEFORE calling validate_scale
        if math.isnan(scale) or math.isinf(scale) or scale == 0:
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_scale",
                    value=scale,
                    severity=ValidationSeverity.CRITICAL,
                    message="Scale factor is NaN, infinity, or zero",
                    suggestion="Scale must be a positive finite number",
                )
            )
            result.validated_value = 1.0
            return result

        # Validate with utilities
        scale_valid = validate_scale(scale, self.min_scale)

        # Range checks
        if scale < self.min_scale:
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_scale",
                    value=scale,
                    severity=ValidationSeverity.WARNING,
                    message=f"Scale below minimum ({self.min_scale})",
                    suggestion=f"Scale will be clamped to {self.min_scale}",
                )
            )
        elif scale > self.max_scale:
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_scale",
                    value=scale,
                    severity=ValidationSeverity.WARNING,
                    message=f"Scale above maximum ({self.max_scale})",
                    suggestion=f"Scale will be clamped to {self.max_scale}",
                )
            )

        # Only set validated_value if we made it this far (no critical issues)
        result.validated_value = scale_valid
        return result

    @override
    def validate_dimensions(self, width: float, height: float, context: str = "") -> ValidationResult:
        """Validate dimensions with comprehensive checks."""
        result = ValidationResult(is_valid=True)

        # Type checks
        if not isinstance(width, int | float) or not isinstance(height, int | float):
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_dimensions",
                    value=(width, height),
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Invalid dimension types: {type(width).__name__}, {type(height).__name__}",
                    suggestion="Dimensions must be numeric",
                )
            )
            result.validated_value = (100, 100)
            return result

        # Range checks
        if width <= 0:
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_width",
                    value=width,
                    severity=ValidationSeverity.CRITICAL,
                    message="Width must be positive",
                    suggestion="Using minimum width of 1",
                )
            )
            width = 1

        if height <= 0:
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_height",
                    value=height,
                    severity=ValidationSeverity.CRITICAL,
                    message="Height must be positive",
                    suggestion="Using minimum height of 1",
                )
            )
            height = 1

        # Aspect ratio check
        aspect = width / height if height > 0 else 0
        if aspect < 0.1 or aspect > 10:
            result.add_issue(
                ValidationIssue(
                    field_name=f"{context}_aspect_ratio",
                    value=aspect,
                    severity=ValidationSeverity.INFO,
                    message=f"Unusual aspect ratio: {aspect:.2f}",
                    suggestion="Consider standard aspect ratios like 16:9 or 4:3",
                )
            )

        result.validated_value = (width, height)
        return result

    @override
    def validate_transform_params(self, params: dict[str, Any]) -> ValidationResult:
        """Validate transform parameters with comprehensive checks."""
        result = ValidationResult(is_valid=True)
        validated = {}

        # Required parameters
        required = ["scale", "center_x", "center_y", "offset_x", "offset_y"]
        missing = [p for p in required if p not in params]
        if missing:
            result.add_issue(
                ValidationIssue(
                    field_name="transform_params",
                    value=params.keys(),
                    severity=ValidationSeverity.WARNING,
                    message=f"Missing required parameters: {missing}",
                    suggestion="Using defaults for missing parameters",
                )
            )

        # Validate each parameter
        if "scale" in params:
            scale_result = self.validate_scale_factor(params["scale"], "transform")
            validated["scale"] = scale_result.validated_value
            result.issues.extend(scale_result.issues)

        if "center_x" in params and "center_y" in params:
            coord_result = self.validate_coordinate(params["center_x"], params["center_y"], "center")
            validated["center_x"], validated["center_y"] = coord_result.validated_value
            result.issues.extend(coord_result.issues)

        if "offset_x" in params and "offset_y" in params:
            offset_result = self.validate_coordinate(params["offset_x"], params["offset_y"], "offset")
            validated["offset_x"], validated["offset_y"] = offset_result.validated_value
            result.issues.extend(offset_result.issues)

        if "width" in params and "height" in params:
            dim_result = self.validate_dimensions(params["width"], params["height"], "viewport")
            validated["width"], validated["height"] = dim_result.validated_value
            result.issues.extend(dim_result.issues)

        # Cross-parameter validation
        if "scale" in validated and "precision" in params:
            quantized_scale = round(validated["scale"] / params["precision"]) * params["precision"]
            if abs(quantized_scale - validated["scale"]) > params["precision"] * 0.1:
                result.add_issue(
                    ValidationIssue(
                        field_name="scale_quantization",
                        value=validated["scale"],
                        severity=ValidationSeverity.INFO,
                        message=f"Scale will be quantized to {quantized_scale}",
                        suggestion="This is normal for cache optimization",
                    )
                )

        # Pass through validated parameters
        for key, value in params.items():
            if key not in validated:
                validated[key] = value

        result.validated_value = validated
        result.is_valid = all(i.severity != ValidationSeverity.CRITICAL for i in result.issues)
        return result

    @property
    @override
    def name(self) -> str:
        """Get strategy name."""
        return "comprehensive"


class AdaptiveValidationStrategy(BaseValidationStrategy):
    """
    Adaptive validation that switches between strategies based on context.

    Uses comprehensive validation for user input and minimal validation
    for internal operations and rendering loops.
    """

    def __init__(self):
        """Initialize with both strategies."""
        self.minimal = MinimalValidationStrategy()
        self.comprehensive = ComprehensiveValidationStrategy()
        self._use_comprehensive = __debug__  # Default based on debug mode

    def set_context(
        self,
        is_user_input: bool = False,
        is_render_loop: bool = False,
        is_batch_operation: bool = False,
        is_debug: bool = False,
    ) -> None:
        """
        Set the validation context.

        Args:
            is_user_input: Use comprehensive validation for user input
            is_render_loop: Use minimal validation for performance-critical rendering
            is_batch_operation: Use minimal validation for bulk operations
            is_debug: Force comprehensive validation for debugging

        Priority order (highest to lowest):
        1. is_render_loop -> minimal (performance critical)
        2. is_debug -> comprehensive (debugging needs)
        3. is_user_input -> comprehensive (data quality)
        4. is_batch_operation -> minimal (bulk performance)
        5. default -> based on __debug__
        """
        if is_render_loop:
            # Performance critical - always use minimal
            self._use_comprehensive = False
        elif is_debug:
            # Debug mode - always use comprehensive for detailed validation
            self._use_comprehensive = True
        elif is_user_input:
            # User input - use comprehensive for data quality
            self._use_comprehensive = True
        elif is_batch_operation:
            # Batch operations - use minimal for performance
            self._use_comprehensive = False
        # Otherwise use default (__debug__ setting)

    @property
    def current_strategy(self) -> BaseValidationStrategy:
        """Get the current active strategy."""
        return self.comprehensive if self._use_comprehensive else self.minimal

    @override
    def validate_coordinate(self, x: float, y: float, context: str = "") -> ValidationResult:
        """Validate using current strategy."""
        return self.current_strategy.validate_coordinate(x, y, context)

    @override
    def validate_scale_factor(self, scale: float, context: str = "") -> ValidationResult:
        """Validate using current strategy."""
        return self.current_strategy.validate_scale_factor(scale, context)

    @override
    def validate_dimensions(self, width: float, height: float, context: str = "") -> ValidationResult:
        """Validate using current strategy."""
        return self.current_strategy.validate_dimensions(width, height, context)

    @override
    def validate_transform_params(self, params: dict[str, Any]) -> ValidationResult:
        """Validate using current strategy."""
        return self.current_strategy.validate_transform_params(params)

    @property
    @override
    def name(self) -> str:
        """Get strategy name."""
        return f"adaptive_{self.current_strategy.name}"


# Factory functions
def create_validation_strategy(mode: str = "auto") -> BaseValidationStrategy:
    """
    Create a validation strategy based on mode.

    Args:
        mode: "minimal", "comprehensive", "adaptive", or "auto" (default)

    Returns:
        Appropriate validation strategy
    """
    if mode == "minimal":
        return MinimalValidationStrategy()
    elif mode == "comprehensive":
        return ComprehensiveValidationStrategy()
    elif mode == "adaptive":
        return AdaptiveValidationStrategy()
    else:  # auto
        return AdaptiveValidationStrategy()


# Singleton instances for common use
_minimal_strategy = MinimalValidationStrategy()
_comprehensive_strategy = ComprehensiveValidationStrategy()
_adaptive_strategy = AdaptiveValidationStrategy()


def get_validation_strategy(mode: str = "current") -> BaseValidationStrategy:
    """
    Get a singleton validation strategy.

    Args:
        mode: "minimal", "comprehensive", "adaptive", "auto", or "current"

    Returns:
        Singleton strategy instance
    """
    if mode == "minimal":
        return _minimal_strategy
    elif mode == "comprehensive":
        return _comprehensive_strategy
    elif mode == "adaptive" or mode == "current" or mode == "auto":
        return _adaptive_strategy
    else:
        raise ValueError(f"Unknown validation mode: {mode}")
