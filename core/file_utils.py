#!/usr/bin/env python
"""
File operation utilities with comprehensive error handling and validation.

This module provides decorators, context managers, and utility functions
for safe file operations with consistent error handling across the application.
"""

import csv
import json
from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any

from core.logger_factory import get_logger
from core.message_utils import MessageFormatter
from core.path_security import PathSecurityError, validate_file_path

logger = get_logger()


# Decorators for file operations
def with_file_validation(
    operation_type: str = "data_files",
    require_exists: bool = True,
    allow_create: bool = False
):
    """
    Decorator for file operations with automatic path validation.

    Args:
        operation_type: Type of file operation for validation.
        require_exists: Whether file must exist.
        allow_create: Whether creating new files is allowed.

    Example:
        ```python
        @with_file_validation(operation_type="export_files", allow_create=True)
        def save_data(self, file_path: str, data: dict) -> bool:
            # file_path is automatically validated before this runs
            with open(file_path, 'w') as f:
                json.dump(data, f)
            return True
        ```
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self, file_path: str | Path, *args, **kwargs):
            try:
                validated_path = validate_file_path(
                    file_path,
                    operation_type=operation_type,
                    require_exists=require_exists,
                    allow_create=allow_create
                )
                # Replace file_path with validated version
                return func(self, str(validated_path), *args, **kwargs)
            except PathSecurityError as e:
                error_msg = MessageFormatter.security_error(str(e))
                logger.error(error_msg)

                # Try to call service's error handler if it exists
                if hasattr(self, '_handle_security_error'):
                    self._handle_security_error(e)
                elif hasattr(self, '_status') and self._status:
                    self._status.show_error(error_msg)

                return None
        return wrapper
    return decorator


def with_error_handling(
    operation: str,
    default_return: Any = None,
    log_errors: bool = True
):
    """
    Decorator for automatic error handling and logging.

    Args:
        operation: Name of the operation for error messages.
        default_return: Value to return on error.
        log_errors: Whether to log errors.

    Example:
        ```python
        @with_error_handling("load configuration", default_return={})
        def load_config(self, path: str) -> dict:
            with open(path) as f:
                return json.load(f)
        ```
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    error_msg = MessageFormatter.error(operation, e)
                    logger.error(error_msg)
                return default_return
        return wrapper
    return decorator


# Context managers for safe file operations
@contextmanager
def safe_file_read(
    file_path: str | Path,
    mode: str = 'r',
    encoding: str = 'utf-8'
) -> Generator[Any | None, None, None]:
    """
    Context manager for safe file reading with error handling.

    Args:
        file_path: Path to file to read.
        mode: File open mode.
        encoding: Text encoding (for text mode).

    Yields:
        File handle or None if error occurred.

    Example:
        ```python
        with safe_file_read('data.json') as f:
            if f is not None:
                data = json.load(f)
            else:
                data = {}  # Use default
        ```
    """
    try:
        if 'b' in mode:
            with open(file_path, mode) as f:
                yield f
        else:
            with open(file_path, mode, encoding=encoding) as f:
                yield f
    except FileNotFoundError:
        logger.error(MessageFormatter.error_with_file("reading", file_path, "File not found"))
        yield None
    except PermissionError:
        logger.error(MessageFormatter.error_with_file("reading", file_path, "Permission denied"))
        yield None
    except Exception as e:
        logger.error(MessageFormatter.error_with_file("reading", file_path, e))
        yield None


@contextmanager
def safe_file_write(
    file_path: str | Path,
    mode: str = 'w',
    encoding: str = 'utf-8',
    create_parents: bool = True
) -> Generator[Any | None, None, None]:
    """
    Context manager for safe file writing with error handling.

    Args:
        file_path: Path to file to write.
        mode: File open mode.
        encoding: Text encoding (for text mode).
        create_parents: Whether to create parent directories.

    Yields:
        File handle or None if error occurred.

    Example:
        ```python
        with safe_file_write('output.json') as f:
            if f is not None:
                json.dump(data, f)
                success = True
            else:
                success = False
        ```
    """
    try:
        file_path = Path(file_path)

        # Create parent directories if needed
        if create_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        if 'b' in mode:
            with open(file_path, mode) as f:
                yield f
        else:
            with open(file_path, mode, encoding=encoding) as f:
                yield f

    except PermissionError:
        logger.error(MessageFormatter.error_with_file("writing", file_path, "Permission denied"))
        yield None
    except Exception as e:
        logger.error(MessageFormatter.error_with_file("writing", file_path, e))
        yield None


# JSON operations
def load_json_safe(
    file_path: str | Path,
    default: Any = None,
    validate_fn: Callable[[dict[str, Any]], bool] | None = None
) -> Any:
    """
    Load JSON file with comprehensive error handling.

    Args:
        file_path: Path to JSON file.
        default: Default value to return on error.
        validate_fn: Optional validation function.

    Returns:
        Loaded data or default value.

    Example:
        ```python
        config = load_json_safe('config.json', default={})
        # or with validation
        config = load_json_safe(
            'config.json',
            default={},
            validate_fn=lambda d: 'version' in d
        )
        ```
    """
    with safe_file_read(file_path) as f:
        if f is None:
            return default

        try:
            data = json.load(f)

            # Validate if function provided
            if validate_fn and not validate_fn(data):
                logger.error(MessageFormatter.validation_error("JSON data", file_path, "validation failed"))
                return default

            return data

        except json.JSONDecodeError as e:
            logger.error(MessageFormatter.error_with_file("parsing JSON", file_path, e))
            return default


def save_json_safe(
    file_path: str | Path,
    data: Any,
    indent: int = 2,
    ensure_ascii: bool = False
) -> bool:
    """
    Save data to JSON file with error handling.

    Args:
        file_path: Path to save to.
        data: Data to save.
        indent: JSON indentation.
        ensure_ascii: Whether to escape non-ASCII characters.

    Returns:
        True if successful, False otherwise.

    Example:
        ```python
        success = save_json_safe('output.json', my_data)
        if success:
            logger.info("Data saved successfully")
        ```
    """
    with safe_file_write(file_path) as f:
        if f is None:
            return False

        try:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            return True
        except (TypeError, ValueError) as e:
            logger.error(MessageFormatter.error("serializing to JSON", e))
            return False


# CSV operations
def load_csv_safe(
    file_path: str | Path,
    default: list[list[str]] | None = None,
    delimiter: str = ',',
    has_header: bool = True
) -> list[list[str]]:
    """
    Load CSV file with error handling.

    Args:
        file_path: Path to CSV file.
        default: Default value to return on error.
        delimiter: CSV delimiter.
        has_header: Whether first row is header.

    Returns:
        List of rows or default value.
    """
    if default is None:
        default = []

    with safe_file_read(file_path) as f:
        if f is None:
            return default

        try:
            reader = csv.reader(f, delimiter=delimiter)

            if has_header:
                next(reader, None)  # Skip header

            return list(reader)

        except csv.Error as e:
            logger.error(MessageFormatter.error_with_file("parsing CSV", file_path, e))
            return default


def save_csv_safe(
    file_path: str | Path,
    data: list,
    delimiter: str = ',',
    header: list | None = None
) -> bool:
    """
    Save data to CSV file with error handling.

    Args:
        file_path: Path to save to.
        data: Data rows to save.
        delimiter: CSV delimiter.
        header: Optional header row.

    Returns:
        True if successful, False otherwise.
    """
    with safe_file_write(file_path) as f:
        if f is None:
            return False

        try:
            writer = csv.writer(f, delimiter=delimiter)

            if header:
                writer.writerow(header)

            writer.writerows(data)
            return True

        except csv.Error as e:
            logger.error(MessageFormatter.error("writing CSV", e))
            return False


# Utility functions
def ensure_file_extension(
    file_path: str | Path,
    extension: str,
    force: bool = False
) -> Path:
    """
    Ensure file has the specified extension.

    Args:
        file_path: Original file path.
        extension: Desired extension (with or without dot).
        force: Whether to replace existing extension.

    Returns:
        Path with correct extension.

    Example:
        ```python
        path = ensure_file_extension("data", ".json")  # Returns "data.json"
        path = ensure_file_extension("data.txt", ".json", force=True)  # Returns "data.json"
        ```
    """
    path = Path(file_path)

    # Ensure extension starts with dot
    if not extension.startswith('.'):
        extension = '.' + extension

    if not path.suffix or force:
        return path.with_suffix(extension)

    return path


def get_unique_filename(
    base_path: str | Path,
    suffix: str = ""
) -> Path:
    """
    Generate a unique filename by appending numbers if file exists.

    Args:
        base_path: Base file path.
        suffix: Optional suffix to add.

    Returns:
        Unique file path.

    Example:
        ```python
        # If "output.json" exists, returns "output_1.json", etc.
        unique = get_unique_filename("output.json")
        ```
    """
    path = Path(base_path)

    if not path.exists():
        return path

    stem = path.stem
    extension = path.suffix
    parent = path.parent

    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}{extension}"
        new_path = parent / new_name

        if not new_path.exists():
            return new_path

        counter += 1
