"""Common exception handling utilities.

This module provides reusable exception handling patterns to reduce duplication.
Previously, similar try/except blocks were repeated 45+ times across the codebase.
"""

import logging
from collections.abc import Callable
from typing import Any, TypeVar, cast

T = TypeVar("T")
R = TypeVar("R")


def safe_execute(
    func: Callable[..., T],
    *args: Any,
    default: T | None = None,
    logger: logging.Logger | None = None,
    log_message: str = "Operation failed",
    **kwargs: Any,
) -> T | None:
    """Execute a function safely, returning default value on exception.

    Args:
        func: Function to execute
        *args: Positional arguments for func
        default: Value to return on exception (default: None)
        logger: Logger to use for error reporting
        log_message: Context message for logging
        **kwargs: Keyword arguments for func

    Returns:
        Function result or default value on exception

    Example:
        result = safe_execute(
            load_file,
            filename,
            default=[],
            logger=logger,
            log_message=f"Failed to load {filename}"
        )
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if logger:
            logger.error(f"{log_message}: {e.__class__.__name__}: {e}")
        return default


def handle_file_operation(
    operation: Callable[[], T],
    file_path: str,
    logger: logging.Logger | None = None,
    default: T | None = None,
) -> T | None:
    """Handle common file operation exceptions.

    Args:
        operation: File operation to perform
        file_path: Path to file being operated on
        logger: Logger for error reporting
        default: Value to return on error

    Returns:
        Operation result or default value on exception
    """
    try:
        return operation()
    except FileNotFoundError:
        if logger:
            logger.error(f"File not found: {file_path}")
        return default
    except PermissionError:
        if logger:
            logger.error(f"Permission denied accessing: {file_path}")
        return default
    except OSError as e:
        if logger:
            logger.error(f"OS error accessing {file_path}: {e}")
        return default
    except Exception as e:
        if logger:
            logger.error(f"Unexpected error accessing {file_path}: {e.__class__.__name__}: {e}")
        return default


def with_fallback(
    primary: Callable[[], T],
    fallback: Callable[[], T],
    logger: logging.Logger | None = None,
) -> T:
    """Try primary operation, fall back to secondary on failure.

    Args:
        primary: Primary operation to attempt
        fallback: Fallback operation if primary fails
        logger: Logger for error reporting

    Returns:
        Result from primary or fallback operation

    Raises:
        Exception: If both primary and fallback fail
    """
    try:
        return primary()
    except Exception as e:
        if logger:
            logger.warning(f"Primary operation failed ({e}), trying fallback")
        return fallback()


class ErrorContext:
    """Context manager for consistent error handling and logging."""

    operation: str
    logger: logging.Logger | None
    reraise: bool
    default: Any
    result: Any
    exception: Exception | None

    def __init__(
        self,
        operation: str,
        logger: logging.Logger | None = None,
        reraise: bool = False,
        default: Any = None,
    ):
        """Initialize error context.

        Args:
            operation: Description of operation being performed
            logger: Logger for error reporting
            reraise: Whether to re-raise exceptions after logging
            default: Default value to store if exception occurs
        """
        self.operation = operation
        self.logger = logger
        self.reraise = reraise
        self.default = default
        self.result = default
        self.exception = None

    def __enter__(self) -> "ErrorContext":
        """Enter context."""
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> bool:
        """Exit context, handling any exceptions."""
        if exc_val is not None:
            self.exception = cast(Exception, exc_val)
            if self.logger:
                self.logger.error(
                    f"{self.operation} failed: {exc_type.__name__ if exc_type else 'Unknown'}: {exc_val}", exc_info=True
                )
            if not self.reraise:
                self.result = self.default
                return True  # Suppress exception
        return False  # Let exception propagate if reraise=True


def categorize_error(exception: Exception) -> str:
    """Categorize an exception for consistent error reporting.

    Args:
        exception: Exception to categorize

    Returns:
        Human-readable error category
    """
    error_categories = {
        FileNotFoundError: "File not found",
        PermissionError: "Permission denied",
        ValueError: "Invalid value",
        TypeError: "Type error",
        KeyError: "Missing key",
        IndexError: "Index out of range",
        AttributeError: "Missing attribute",
        ImportError: "Import error",
        OSError: "System error",
        RuntimeError: "Runtime error",
    }

    for exc_type, category in error_categories.items():
        if isinstance(exception, exc_type):
            return category

    return "Unexpected error"
