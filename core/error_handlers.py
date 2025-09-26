#!/usr/bin/env python3
"""
Error handling utilities for consistent error management across the application.

This module provides decorators and context managers for common error handling
patterns, reducing code duplication and ensuring consistent error reporting.
"""

import functools
import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import ParamSpec, TypeVar

from core.logger_utils import get_logger

# Type variables for generic typing
T = TypeVar("T")
P = ParamSpec("P")

# Module logger
logger = get_logger(__name__)


def handle_service_error(
    operation: str = "operation", default: T | None = None, log_level: int = logging.ERROR, reraise: bool = False
) -> Callable[[Callable[P, T]], Callable[P, T | None]]:
    """
    Decorator for consistent service-level error handling.

    Args:
        operation: Description of the operation being performed
        default: Default value to return on error
        log_level: Logging level for the error (default: ERROR)
        reraise: Whether to re-raise the exception after logging

    Returns:
        Decorated function with error handling

    Example:
        @handle_service_error("load data", default=[], log_level=logging.WARNING)
        def load_data(self, filepath: str) -> list:
            # implementation
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T | None]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get the logger from the instance if available (for methods)
                error_logger = logger
                if args:
                    instance = args[0]
                    # Type-safe logger access without hasattr
                    instance_logger = getattr(instance, "_logger", None)
                    if instance_logger is not None and isinstance(instance_logger, logging.Logger):
                        error_logger = instance_logger

                error_logger.log(log_level, f"Failed to {operation}: {e}")

                if reraise:
                    raise
                return default

        return wrapper

    return decorator


@contextmanager
def suppress_and_log(
    operation: str = "operation", default: object | None = None, logger_instance: logging.Logger | None = None
) -> Generator[dict[str, object | None], None, None]:
    """
    Context manager for suppressing exceptions with logging.

    Args:
        operation: Description of the operation being performed
        default: Default value to provide if error occurs
        logger_instance: Logger to use (defaults to module logger)

    Yields:
        Dictionary that can be used to store the result

    Example:
        with suppress_and_log("parse file", default=[], logger_instance=self._logger) as result:
            result['value'] = parse_file(filepath)
        data = result.get('value', [])
    """
    result = {"value": default}
    log = logger_instance or logger

    try:
        yield result
    except Exception as e:
        log.error(f"Failed to {operation}: {e}")
        result["value"] = default


def safe_file_operation(func: Callable[P, T]) -> Callable[P, T | None]:
    """
    Decorator for safe file operations with automatic resource cleanup.

    Automatically handles file I/O exceptions and ensures proper cleanup.

    Args:
        func: Function performing file operations

    Returns:
        Decorated function with file error handling

    Example:
        @safe_file_operation
        def read_config(filepath: str) -> dict:
            with open(filepath, 'r') as f:
                return json.load(f)
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logger.warning(f"File not found: {e}")
            return None
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return None
        except OSError as e:
            logger.error(f"I/O error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in file operation: {e}")
            return None

    return wrapper


def retry_on_failure(
    max_attempts: int = 3, delay: float = 0.0, exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to retry operations on failure.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between attempts in seconds
        exceptions: Tuple of exception types to catch

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_failure(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
        def fetch_data(url: str) -> dict:
            # implementation
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}")
                        if delay > 0:
                            import time

                            time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed: {e}")

            if last_exception:
                raise last_exception

            # This should never be reached, but satisfies type checker
            raise RuntimeError("Retry logic failed unexpectedly")

        return wrapper

    return decorator


class ErrorAccumulator:
    """
    Accumulate errors for batch operations without stopping execution.

    Useful for operations that should continue even if some items fail.

    Example:
        accumulator = ErrorAccumulator()

        for item in items:
            with accumulator.capture(f"process {item.name}"):
                process_item(item)

        if accumulator.has_errors():
            logger.error(f"Failed to process {accumulator.error_count} items")
            for error in accumulator.get_errors():
                logger.error(f"  - {error}")
    """

    def __init__(self):
        """Initialize the error accumulator."""
        self.errors: list[tuple[str, Exception]] = []

    @contextmanager
    def capture(self, operation: str) -> Generator[None, None, None]:
        """
        Capture errors for a specific operation.

        Args:
            operation: Description of the operation
        """
        try:
            yield
        except Exception as e:
            self.errors.append((operation, e))
            logger.debug(f"Error captured for {operation}: {e}")

    def has_errors(self) -> bool:
        """Check if any errors were accumulated."""
        return len(self.errors) > 0

    @property
    def error_count(self) -> int:
        """Get the number of accumulated errors."""
        return len(self.errors)

    def get_errors(self) -> list[str]:
        """
        Get formatted error messages.

        Returns:
            List of formatted error messages
        """
        return [f"{op}: {err}" for op, err in self.errors]

    def clear(self) -> None:
        """Clear all accumulated errors."""
        self.errors.clear()


def validate_not_none(value: T | None, name: str = "value", message: str | None = None) -> T:
    """
    Validate that a value is not None, with descriptive error.

    Args:
        value: Value to check
        name: Name of the value for error message
        message: Custom error message

    Returns:
        The value if not None

    Raises:
        ValueError: If value is None

    Example:
        config = validate_not_none(get_config(), "configuration")
    """
    if value is None:
        error_msg = message or f"{name} cannot be None"
        logger.error(error_msg)
        raise ValueError(error_msg)
    return value


def safe_getattr(obj: object, attr: str, default: object | None = None, log_missing: bool = False) -> object | None:
    """
    Safely get an attribute with optional logging.

    Args:
        obj: Object to get attribute from
        attr: Attribute name
        default: Default value if attribute doesn't exist
        log_missing: Whether to log missing attributes

    Returns:
        Attribute value or default

    Example:
        value = safe_getattr(config, 'timeout', default=30, log_missing=True)
    """
    try:
        return getattr(obj, attr, default)
    except AttributeError as e:
        if log_missing:
            logger.debug(f"Attribute '{attr}' not found on {type(obj).__name__}: {e}")
        return default
    except Exception as e:
        logger.warning(f"Error accessing attribute '{attr}': {e}")
        return default
