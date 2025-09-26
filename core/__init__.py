"""Core architectural components for the CurveEditor.

This package contains the fundamental building blocks for the application:
- Protocol definitions for interface contracts
- Service registry for dependency management
- Event system for loose coupling between components

These components provide the architectural foundation that enables
clean separation of concerns and testable code.
"""

# Path Security Module
from .path_security import (
    PathSecurityError,
    validate_directory_path,
    validate_file_path,
)

__all__ = [
    # Path Security
    "PathSecurityError",
    "validate_file_path",
    "validate_directory_path",
]
