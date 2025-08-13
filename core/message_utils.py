#!/usr/bin/env python
"""
Message formatting utilities for consistent messaging across the application.

This module provides standardized message formatting for logging, status updates,
and user notifications.
"""

from pathlib import Path
from typing import Any


class MessageFormatter:
    """Provides consistent message formatting across the application."""

    # Error messages
    @staticmethod
    def error(operation: str, error: Exception | str) -> str:
        """Format error message with operation context."""
        return f"Error in {operation}: {error}"

    @staticmethod
    def error_with_file(operation: str, file_path: str | Path, error: Exception | str) -> str:
        """Format error message with file context."""
        return f"Error {operation} '{file_path}': {error}"

    @staticmethod
    def security_error(violation: str) -> str:
        """Format security violation message."""
        return f"Security violation: {violation}"

    @staticmethod
    def validation_error(field: str, value: Any, reason: str) -> str:
        """Format validation error message."""
        return f"Invalid {field} '{value}': {reason}"

    # Success messages
    @staticmethod
    def success_load(count: int, source: str | Path) -> str:
        """Format successful load message."""
        return f"Successfully loaded {count} points from {source}"

    @staticmethod
    def success_save(count: int, destination: str | Path) -> str:
        """Format successful save message."""
        return f"Successfully saved {count} points to {destination}"

    @staticmethod
    def success_operation(operation: str, details: str | None = None) -> str:
        """Format generic success message."""
        if details:
            return f"{operation} completed successfully: {details}"
        return f"{operation} completed successfully"

    # Progress messages
    @staticmethod
    def progress(message: str, percentage: float) -> str:
        """Format progress message with percentage."""
        return f"{message} ({percentage:.0f}%)"

    @staticmethod
    def progress_items(current: int, total: int, item_name: str = "items") -> str:
        """Format progress message with item count."""
        percentage = (current / total * 100) if total > 0 else 0
        return f"Processing {item_name}: {current}/{total} ({percentage:.0f}%)"

    # Status messages
    @staticmethod
    def status_ready() -> str:
        """Format ready status message."""
        return "Ready"

    @staticmethod
    def status_loading(what: str = "data") -> str:
        """Format loading status message."""
        return f"Loading {what}..."

    @staticmethod
    def status_saving(what: str = "data") -> str:
        """Format saving status message."""
        return f"Saving {what}..."

    @staticmethod
    def status_processing(what: str = "data") -> str:
        """Format processing status message."""
        return f"Processing {what}..."

    # Info messages
    @staticmethod
    def info_points(total: int, selected: int | None = None) -> str:
        """Format point count information."""
        if selected is not None and selected > 0:
            return f"Points: {total} | Selected: {selected}"
        return f"Points: {total}"

    @staticmethod
    def info_fps(fps: float, quality: str | None = None) -> str:
        """Format FPS information."""
        if quality:
            return f"{fps:.1f} FPS | Quality: {quality.upper()}"
        return f"{fps:.1f} FPS"

    @staticmethod
    def info_zoom(zoom: float) -> str:
        """Format zoom level information."""
        return f"Zoom: {zoom:.1f}x"

    @staticmethod
    def info_position(x: float, y: float, precision: int = 3) -> str:
        """Format position information."""
        format_str = f"X: {{:.{precision}f}}, Y: {{:.{precision}f}}"
        return format_str.format(x, y)

    # Warning messages
    @staticmethod
    def warning_deprecated(old_method: str, new_method: str) -> str:
        """Format deprecation warning."""
        return f"'{old_method}' is deprecated, use '{new_method}' instead"

    @staticmethod
    def warning_performance(operation: str, time_ms: float, threshold_ms: float = 100) -> str:
        """Format performance warning."""
        return f"{operation} took {time_ms:.1f}ms (threshold: {threshold_ms:.1f}ms)"

    @staticmethod
    def warning_fallback(expected: str, fallback: str) -> str:
        """Format fallback warning."""
        return f"{expected} not available, using {fallback}"


class LogMessageBuilder:
    """Builder pattern for complex log messages."""

    def __init__(self, operation: str):
        """Initialize with operation name."""
        self.parts = [operation]

    def add_count(self, label: str, count: int) -> "LogMessageBuilder":
        """Add a count to the message."""
        self.parts.append(f"{label}={count}")
        return self

    def add_value(self, label: str, value: Any) -> "LogMessageBuilder":
        """Add a labeled value to the message."""
        self.parts.append(f"{label}={value}")
        return self

    def add_time(self, time_ms: float) -> "LogMessageBuilder":
        """Add execution time to the message."""
        self.parts.append(f"time={time_ms:.1f}ms")
        return self

    def add_result(self, success: bool) -> "LogMessageBuilder":
        """Add success/failure to the message."""
        self.parts.append("success" if success else "failed")
        return self

    def build(self) -> str:
        """Build the final message."""
        return " | ".join(self.parts)


# Convenience functions for common patterns
def format_error(operation: str, error: Exception | str) -> str:
    """Convenience function for error formatting."""
    return MessageFormatter.error(operation, error)


def format_success(operation: str, count: int | None = None) -> str:
    """Convenience function for success formatting."""
    if count is not None:
        return f"{operation} completed successfully ({count} items)"
    return MessageFormatter.success_operation(operation)


def format_progress(current: int, total: int) -> str:
    """Convenience function for progress formatting."""
    return MessageFormatter.progress_items(current, total)
