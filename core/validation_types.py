#!/usr/bin/env python
"""Validation types for error handling."""

from dataclasses import dataclass, field
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    CRITICAL = "critical"  # Must be fixed, will cause crashes
    WARNING = "warning"  # Should be fixed, may cause incorrect behavior
    INFO = "info"  # Informational, minor issues


@dataclass
class ValidationIssue:
    """Structured error reporting for validation failures."""

    field_name: str
    value: object
    severity: ValidationSeverity
    message: str
    suggestion: str | None = None
    context: dict[str, object] = field(default_factory=dict)  # Additional metadata for debugging

    def format(self) -> str:
        """Format the validation issue as a user-friendly message."""
        base_msg = f"[{self.severity.value.upper()}] {self.field_name}: {self.message}"
        if self.suggestion:
            base_msg += f" → {self.suggestion}"
        return base_msg

    def to_exception(self) -> ValueError:
        """Convert to an exception for critical issues."""
        return ValueError(self.format())
