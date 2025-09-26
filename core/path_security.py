#!/usr/bin/env python3
"""
Simplified Path Security Module for CurveEditor.

Provides basic path validation for file operations without the complexity
of enterprise-grade security features that aren't needed for a desktop application.
"""

from pathlib import Path

from core.logger_utils import get_logger

logger = get_logger("path_security")


class PathSecurityError(Exception):
    """Exception raised for path security violations."""

    pass


def validate_file_path(
    file_path: str | Path,
    operation_type: str = "data_files",  # pylint: disable=unused-argument  # pyright: ignore[reportUnusedParameter]
    allow_create: bool = False,
    require_exists: bool = True,
) -> Path:
    """
    Validate a file path for basic security and correctness.

    Args:
        file_path: The file path to validate
        operation_type: Type of operation (unused in simplified version)
        allow_create: Whether to allow creating new files
        require_exists: Whether the file must already exist

    Returns:
        Validated Path object

    Raises:
        PathSecurityError: If path validation fails
    """
    try:
        path = Path(file_path).resolve()
    except (OSError, ValueError) as e:
        raise PathSecurityError(f"Invalid path: {e}") from e

    # Basic validation: check if path is reasonable
    if not path.name:
        raise PathSecurityError("Path must specify a filename")

    # Check parent directory exists
    if not path.parent.exists():
        raise PathSecurityError(f"Parent directory does not exist: {path.parent}")

    # Check file existence requirements
    if require_exists and not path.exists():
        raise PathSecurityError(f"File does not exist: {path}")

    if not allow_create and not path.exists():
        raise PathSecurityError(f"File creation not allowed: {path}")

    return path


def validate_directory_path(directory_path: str | Path, allow_create: bool = False) -> Path:
    """
    Validate a directory path for basic correctness.

    Args:
        directory_path: The directory path to validate
        allow_create: Whether to allow creating new directories

    Returns:
        Validated Path object

    Raises:
        PathSecurityError: If path validation fails
    """
    try:
        path = Path(directory_path).resolve()
    except (OSError, ValueError) as e:
        raise PathSecurityError(f"Invalid directory path: {e}") from e

    if not allow_create and not path.exists():
        raise PathSecurityError(f"Directory does not exist: {path}")

    if path.exists() and not path.is_dir():
        raise PathSecurityError(f"Path is not a directory: {path}")

    return path
