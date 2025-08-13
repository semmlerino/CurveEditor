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
    PathSecurityConfig,
    PathSecurityError,
    add_allowed_directory,
    add_allowed_extension,
    get_path_security_config,
    is_safe_to_read,
    is_safe_to_write,
    remove_allowed_directory,
    sanitize_filename,
    set_allow_symlinks,
    validate_directory_path,
    validate_file_path,
)

__all__ = [
    # Path Security
    "PathSecurityError",
    "PathSecurityConfig",
    "validate_file_path",
    "validate_directory_path",
    "sanitize_filename",
    "is_safe_to_write",
    "is_safe_to_read",
    "get_path_security_config",
    "add_allowed_directory",
    "remove_allowed_directory",
    "set_allow_symlinks",
    "add_allowed_extension",
]
