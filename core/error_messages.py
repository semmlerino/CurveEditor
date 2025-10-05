#!/usr/bin/env python3
"""
User-friendly error messages for the CurveEditor application.

Provides context-aware error messages with suggestions for resolution.
"""

import math


class TransformError(ValueError):
    """Custom exception for transformation-related errors with helpful messages."""

    def __init__(self, message: str, suggestion: str | None = None, value: str | int | float | bool | None = None):
        """
        Initialize TransformError with detailed information.

        Args:
            message: The error message
            suggestion: Optional suggestion for fixing the error
            value: Optional value that caused the error
        """
        full_message = message
        if value is not None:
            full_message += f" (received: {value})"
        if suggestion:
            full_message += f"\n  → Suggestion: {suggestion}"
        super().__init__(full_message)
        self.suggestion: str | None = suggestion
        self.value: str | int | float | bool | None = value


class ValidationError(ValueError):
    """Custom exception for validation errors with helpful context."""

    def __init__(self, field: str, value: str | int | float | bool, reason: str, suggestion: str | None = None):
        """
        Initialize ValidationError with field-specific information.

        Args:
            field: The field that failed validation
            value: The invalid value
            reason: Why the validation failed
            suggestion: Optional suggestion for fixing
        """
        message = f"Validation failed for '{field}': {reason}"
        # value is non-optional (str | int | float | bool)
        message += f" (value: {value})"
        if suggestion:
            message += f"\n  → Try: {suggestion}"
        super().__init__(message)
        self.field: str = field
        self.value: str | int | float | bool = value
        self.reason: str = reason
        self.suggestion: str | None = suggestion


def format_precision_error(precision: float) -> str:
    """Format error message for invalid precision values."""
    if precision <= 0:
        return (
            f"Precision must be a positive number, but got {precision}.\n"
            f"  → Use a value like 0.1 for coarse precision or 0.01 for fine precision."
        )
    elif not math.isfinite(precision):
        return (
            f"Precision must be a finite number, but got {precision}.\n" f"  → Use a standard value like 0.1 or 0.01."
        )
    return f"Invalid precision value: {precision}"


def format_scale_error(scale: float, context: str = "transform") -> str:
    """Format error message for invalid scale values."""
    import math

    if not math.isfinite(scale):
        return (
            f"Scale factor for {context} must be a finite number.\n"
            f"  Received: {scale}\n"
            f"  → Reset to default zoom level (1.0) or check calculation inputs."
        )
    elif scale <= 0:
        if scale == 0:
            return (
                f"Scale factor for {context} cannot be zero (would cause division by zero).\n"
                f"  → Use a small positive value like 0.001 for minimum zoom."
            )
        else:
            return (
                f"Scale factor for {context} cannot be negative ({scale}).\n"
                f"  → Use positive values only. For flipping, use the flip_y option instead."
            )
    elif scale < 1e-10:
        return (
            f"Scale factor for {context} is too small ({scale:.2e}).\n"
            f"  Minimum allowed: 1e-10\n"
            f"  → This prevents numerical instability. Use a larger zoom value."
        )
    elif scale > 1e10:
        return (
            f"Scale factor for {context} is too large ({scale:.2e}).\n"
            f"  Maximum allowed: 1e10\n"
            f"  → This prevents overflow. Use a smaller zoom value."
        )
    return f"Invalid scale factor for {context}: {scale}"


def format_dimension_error(dimension: int, name: str) -> str:
    """Format error message for invalid dimension values."""
    if dimension < 0:
        return (
            f"{name} cannot be negative ({dimension} pixels).\n" f"  → Check window initialization or resize handling."
        )
    elif dimension == 0:
        return (
            f"{name} cannot be zero (would cause division errors).\n"
            f"  → Ensure window is properly initialized before use."
        )
    elif dimension > 1_000_000:
        return (
            f"{name} is unrealistically large ({dimension:,} pixels).\n"
            f"  Maximum allowed: 1,000,000 pixels\n"
            f"  → Check for calculation errors or use reasonable display dimensions."
        )
    return f"Invalid {name}: {dimension}"


def format_coordinate_error(x: float, y: float, context: str = "coordinates") -> str:
    """Format error message for invalid coordinate values."""
    import math

    if not math.isfinite(x) or not math.isfinite(y):
        invalid: list[str] = []
        if not math.isfinite(x):
            invalid.append(f"x={x}")
        if not math.isfinite(y):
            invalid.append(f"y={y}")
        return (
            f"Invalid {context}: {', '.join(invalid)}\n"
            f"  → Coordinates must be finite numbers.\n"
            f"  → Check data source for NaN or infinity values."
        )

    max_coord = 1e10
    if abs(x) > max_coord or abs(y) > max_coord:
        return (
            f"Coordinates for {context} are too large.\n"
            f"  Received: x={x:.2e}, y={y:.2e}\n"
            f"  Maximum: ±{max_coord:.0e}\n"
            f"  → Check for accumulating transformation errors or reset view."
        )

    return f"Invalid {context}: x={x}, y={y}"


def format_offset_error(offset: float, name: str) -> str:
    """Format error message for invalid offset values."""
    import math

    if not math.isfinite(offset):
        return (
            f"{name} must be a finite number, but got {offset}.\n"
            f"  → Reset pan position or check calculation inputs."
        )

    max_offset = 1e6
    if abs(offset) > max_offset:
        return (
            f"{name} is too large ({offset:.2e}).\n"
            f"  Maximum allowed: ±{max_offset:.0e}\n"
            f"  → This may indicate runaway pan accumulation. Reset view to center."
        )

    return f"Invalid {name}: {offset}"


def format_configuration_error(config_name: str, issue: str, suggestion: str) -> str:
    """Format error message for configuration issues."""
    return f"Configuration error in '{config_name}':\n" f"  Issue: {issue}\n" f"  → {suggestion}"


def format_cache_error(operation: str, details: str) -> str:
    """Format error message for cache-related issues."""
    return (
        f"Cache {operation} failed:\n"
        f"  Details: {details}\n"
        f"  → Try clearing the cache or restarting the application."
    )


def format_type_error(expected: str, received: str | int | float | bool | object, field: str) -> str:
    """Format error message for type mismatches."""
    received_type = type(received).__name__
    return (
        f"Type mismatch for '{field}':\n"
        f"  Expected: {expected}\n"
        f"  Received: {received_type} ({received})\n"
        f"  → Ensure correct data types are passed to this function."
    )


def format_state_recovery_error(level: int, attempted: str, fallback: str) -> str:
    """Format error message for state recovery issues."""
    return (
        f"State recovery level {level} attempted:\n"
        f"  Tried: {attempted}\n"
        f"  Fallback: {fallback}\n"
        f"  → Your view settings have been adjusted to prevent errors.\n"
        f"  → Some manual adjustments may have been reset."
    )


# Common error scenarios with helpful messages
ERROR_SCENARIOS = {
    "zero_scale": "Scale factor cannot be zero as it would cause division by zero errors. Use a small positive value instead.",
    "negative_dimension": "Display dimensions must be positive. Check window initialization.",
    "nan_coordinate": "Coordinates contain NaN or infinity values. Check data source or calculations.",
    "precision_zero": "Precision must be positive for quantization to work correctly.",
    "cache_collision": "Cache key collision detected. This is an internal error that should be reported.",
    "validation_bypass": "Validation was bypassed but errors occurred. Enable debug mode for details.",
    "transform_overflow": "Transformation resulted in numeric overflow. Reset view or reduce zoom level.",
    "inverse_transform_fail": "Cannot compute inverse transformation with current parameters. Check scale factors.",
}


def get_error_help(error_code: str) -> str:
    """
    Get helpful message for common error scenarios.

    Args:
        error_code: The error scenario code

    Returns:
        Helpful error message with suggestions
    """
    return ERROR_SCENARIOS.get(
        error_code, f"Unknown error code: {error_code}. Please check documentation or report this issue."
    )
