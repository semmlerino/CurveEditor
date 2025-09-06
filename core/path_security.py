# \!/usr/bin/env python
"""
Path Security Module for CurveEditor.

This module provides comprehensive path validation and sanitization to prevent:
- Path traversal attacks (../../../etc/passwd)
- Directory traversal outside allowed directories
- Symlink following to unauthorized locations
- Invalid file extensions
- Other file system security issues

All file operations in CurveEditor should use these validation functions.
"""

import logging
import os
from pathlib import Path
from typing import final

logger = logging.getLogger("path_security")


class PathSecurityError(Exception):
    """Exception raised for path security violations."""

    pass


@final
class PathSecurityConfig:
    """Configuration for path security validation."""

    def __init__(self) -> None:
        """Initialize path security configuration."""
        # Get the application's base directory
        app_root = Path(__file__).parent.parent.resolve()

        # Define allowed base directories for file operations
        self.allowed_directories: list[Path] = [
            app_root,  # Application directory and subdirectories
            Path.home(),  # User's home directory and subdirectories
            Path("/tmp"),  # Temporary files (Linux/macOS)
            Path("/var/tmp"),  # Alternative temp directory
        ]

        # Add Windows temp directories if on Windows
        if os.name == "nt":
            import tempfile

            self.allowed_directories.extend(
                [
                    Path(tempfile.gettempdir()),
                    Path.home() / "Documents",
                    Path.home() / "Desktop",
                ]
            )

        # Allowed file extensions for different operation types
        self.allowed_extensions = {
            "data_files": {".json", ".csv", ".txt"},
            "image_files": {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"},
            "export_files": {".json", ".csv", ".xlsx", ".txt"},
            "all_files": set(),  # Empty set means allow all extensions
        }

        # Maximum path length to prevent buffer overflow attacks
        self.max_path_length = 4096

        # Whether to allow symlinks (disabled by default for security)
        self.allow_symlinks = False


# Global configuration instance
_config = PathSecurityConfig()


def get_path_security_config() -> PathSecurityConfig:
    """Get the global path security configuration.

    Returns:
        PathSecurityConfig instance
    """
    return _config


def validate_file_path(
    file_path: str | Path, operation_type: str = "data_files", allow_create: bool = False, require_exists: bool = True
) -> Path:
    """Validate and sanitize a file path for security.

    Args:
        file_path: The file path to validate
        operation_type: Type of operation ('data_files', 'image_files', 'export_files', 'all_files')
        allow_create: Whether to allow creation of non-existent files
        require_exists: Whether the file must exist (ignored if allow_create=True)

    Returns:
        Validated and normalized Path object

    Raises:
        PathSecurityError: If path validation fails
        ValueError: If arguments are invalid
    """
    if not file_path:
        raise PathSecurityError("Empty file path provided")

    # Convert to Path object (but don't resolve yet to preserve symlink detection)
    try:
        path = Path(file_path)

        # Check symlink policy BEFORE resolving (which follows symlinks)
        _validate_symlink_policy(path)

        # Now resolve the path
        path = path.resolve()
    except (OSError, ValueError) as e:
        raise PathSecurityError(f"Invalid path format: {e}")

    # Basic path sanity checks
    _validate_path_basic(path)

    # Check if path is within allowed directories
    _validate_path_directory(path)

    # Validate file extension
    _validate_file_extension(path, operation_type)

    # Check file existence requirements
    _validate_file_existence(path, allow_create, require_exists)

    logger.debug(f"Path validation successful: {path}")
    return path


def validate_directory_path(directory_path: str | Path, allow_create: bool = False) -> Path:
    """Validate a directory path for security.

    Args:
        directory_path: The directory path to validate
        allow_create: Whether to allow creation of non-existent directories

    Returns:
        Validated and normalized Path object

    Raises:
        PathSecurityError: If path validation fails
    """
    if not directory_path:
        raise PathSecurityError("Empty directory path provided")

    try:
        path = Path(directory_path)

        # Check symlink policy BEFORE resolving
        _validate_symlink_policy(path)

        # Now resolve the path
        path = path.resolve()
    except (OSError, ValueError) as e:
        raise PathSecurityError(f"Invalid directory path format: {e}")

    # Basic path sanity checks
    _validate_path_basic(path)

    # Check if path is within allowed directories
    _validate_path_directory(path)

    # Check directory existence
    if path.exists():
        if not path.is_dir():
            raise PathSecurityError(f"Path exists but is not a directory: {path}")
    elif not allow_create:
        raise PathSecurityError(f"Directory does not exist: {path}")

    logger.debug(f"Directory validation successful: {path}")
    return path


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to remove dangerous characters.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename

    Raises:
        ValueError: If filename is empty after sanitization
    """
    if not filename:
        raise ValueError("Empty filename provided")

    # Remove null bytes and other dangerous characters
    sanitized = filename.replace("\x00", "").replace("\n", "").replace("\r", "")

    # Remove path separators
    sanitized = sanitized.replace("/", "").replace("\\", "")

    # Remove relative path components (but preserve file extension)
    # Split the filename and extension first
    path_obj = Path(sanitized)
    name_part = path_obj.stem
    ext_part = path_obj.suffix

    # Remove dots from name part (except the extension separator)
    name_part = name_part.replace("..", "")
    while ".." in name_part:
        name_part = name_part.replace("..", ".")

    # Recombine with extension
    sanitized = name_part + ext_part

    # Limit length
    if len(sanitized) > 255:
        path_obj = Path(sanitized)
        name_part = path_obj.stem
        ext_part = path_obj.suffix
        max_name_len = 255 - len(ext_part)
        sanitized = name_part[:max_name_len] + ext_part

    # Ensure we still have a valid filename
    if not sanitized or sanitized.isspace():
        raise ValueError("Filename becomes empty after sanitization")

    return sanitized


def is_safe_to_write(file_path: str | Path) -> bool:
    """Check if a file path is safe for write operations.

    This performs a non-raising validation check.

    Args:
        file_path: The file path to check

    Returns:
        True if safe to write, False otherwise
    """
    try:
        _ = validate_file_path(file_path, operation_type="export_files", allow_create=True, require_exists=False)
        return True
    except PathSecurityError:
        return False


def is_safe_to_read(file_path: str | Path, operation_type: str = "data_files") -> bool:
    """Check if a file path is safe for read operations.

    This performs a non-raising validation check.

    Args:
        file_path: The file path to check
        operation_type: Type of operation for extension validation

    Returns:
        True if safe to read, False otherwise
    """
    try:
        _ = validate_file_path(file_path, operation_type=operation_type, allow_create=False, require_exists=True)
        return True
    except PathSecurityError:
        return False


def _validate_path_basic(path: Path) -> None:
    """Perform basic path validation checks.

    Args:
        path: Path to validate

    Raises:
        PathSecurityError: If basic validation fails
    """
    # Check path length
    if len(str(path)) > _config.max_path_length:
        raise PathSecurityError(f"Path too long (max {_config.max_path_length}): {len(str(path))}")

    # Check for null bytes (should be caught by Path.resolve() but double-check)
    if "\x00" in str(path):
        raise PathSecurityError("Path contains null bytes")

    # Check for suspicious patterns
    path_str = str(path).lower()
    suspicious_patterns = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/hosts",
        "\\windows\\system32",
        "\\windows\\system",
        "/proc/",
        "/sys/",
        "/dev/",
    ]

    for pattern in suspicious_patterns:
        if pattern in path_str:
            raise PathSecurityError(f"Path contains suspicious pattern: {pattern}")


def _validate_path_directory(path: Path) -> None:
    """Validate that path is within allowed directories.

    Args:
        path: Path to validate

    Raises:
        PathSecurityError: If path is outside allowed directories
    """
    # Check if path is within any allowed directory
    for allowed_dir in _config.allowed_directories:
        try:
            # Check if path is under allowed directory
            allowed_dir_resolved = allowed_dir.resolve()
            if path == allowed_dir_resolved or allowed_dir_resolved in path.parents:
                return
        except (OSError, ValueError):
            # Skip this allowed directory if it can't be resolved
            continue

    # Path is not within any allowed directory
    raise PathSecurityError(f"Path outside allowed directories: {path}")


def _validate_file_extension(path: Path, operation_type: str) -> None:
    """Validate file extension against allowed extensions.

    Args:
        path: Path to validate
        operation_type: Type of operation for extension validation

    Raises:
        PathSecurityError: If extension is not allowed
    """
    allowed_extensions = _config.allowed_extensions.get(operation_type, set())

    # If allowed_extensions is empty, allow all extensions
    if not allowed_extensions:
        return

    file_extension = path.suffix.lower()

    if file_extension not in allowed_extensions:
        raise PathSecurityError(
            f"File extension '{file_extension}' not allowed for {operation_type}. Allowed: {sorted(allowed_extensions)}"
        )


def _validate_symlink_policy(path: Path) -> None:
    """Validate symlink policy.

    Args:
        path: Path to validate

    Raises:
        PathSecurityError: If symlinks are not allowed
    """
    # Check if path itself is a symlink (use lstat to detect symlinks even if target doesn't exist)
    if not _config.allow_symlinks:
        try:
            if path.lstat() and path.is_symlink():
                raise PathSecurityError(f"Symlinks not allowed: {path}")
        except FileNotFoundError:
            # Path doesn't exist yet, which is OK for files we're creating
            pass

    # Check if any parent directories are symlinks
    if not _config.allow_symlinks:
        for parent in path.parents:
            try:
                if parent.lstat() and parent.is_symlink():
                    raise PathSecurityError(f"Path contains symlinked directory: {parent}")
            except FileNotFoundError:
                # Parent doesn't exist, skip
                continue


def _validate_file_existence(path: Path, allow_create: bool, require_exists: bool) -> None:
    """Validate file existence requirements.

    Args:
        path: Path to validate
        allow_create: Whether to allow creation of non-existent files
        require_exists: Whether the file must exist

    Raises:
        PathSecurityError: If existence requirements are not met
    """
    file_exists = path.exists()

    if require_exists and not allow_create and not file_exists:
        raise PathSecurityError(f"File does not exist: {path}")

    if file_exists and path.is_dir():
        raise PathSecurityError(f"Path is a directory, not a file: {path}")


# Configuration helper functions
def add_allowed_directory(directory: str | Path) -> None:
    """Add a directory to the allowed directories list.

    Args:
        directory: Directory path to add
    """
    try:
        dir_path = Path(directory).resolve()
        if dir_path not in _config.allowed_directories:
            _config.allowed_directories.append(dir_path)
            logger.info(f"Added allowed directory: {dir_path}")
    except (OSError, ValueError) as e:
        logger.warning(f"Failed to add allowed directory {directory}: {e}")


def remove_allowed_directory(directory: str | Path) -> None:
    """Remove a directory from the allowed directories list.

    Args:
        directory: Directory path to remove
    """
    try:
        dir_path = Path(directory).resolve()
        if dir_path in _config.allowed_directories:
            _config.allowed_directories.remove(dir_path)
            logger.info(f"Removed allowed directory: {dir_path}")
    except (OSError, ValueError) as e:
        logger.warning(f"Failed to remove allowed directory {directory}: {e}")


def set_allow_symlinks(allow: bool) -> None:
    """Set whether to allow symlinks.

    Args:
        allow: Whether to allow symlinks
    """
    _config.allow_symlinks = allow
    logger.info(f"Set allow_symlinks to: {allow}")


def add_allowed_extension(operation_type: str, extension: str) -> None:
    """Add an allowed file extension for an operation type.

    Args:
        operation_type: Operation type to add extension for
        extension: File extension (with dot, e.g., '.txt')
    """
    if operation_type not in _config.allowed_extensions:
        _config.allowed_extensions[operation_type] = set()

    extension = extension.lower()
    if not extension.startswith("."):
        extension = "." + extension

    _config.allowed_extensions[operation_type].add(extension)
    logger.info(f"Added allowed extension {extension} for {operation_type}")
