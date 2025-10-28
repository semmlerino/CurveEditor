#!/usr/bin/env python
"""
Standardized error handling utilities for CurveEditor.

This module provides reusable error handling patterns extracted from the
CurveDataCommand._safe_execute() pattern. Supports both boolean returns
(success/failure) and optional returns (T | None).

Phase 1.4: Error Handling Pattern Consolidation
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from core.logger_utils import get_logger

logger = get_logger("error_handling")

# Type variable for generic return types
T = TypeVar("T")


def safe_execute(
    operation_name: str,
    operation: Callable[[], bool],
    context: str = "",
) -> bool:
    """Execute operation with standardized error handling (boolean return).

    This function wraps operations that return bool (success/failure) and provides
    consistent error logging and exception handling.

    Args:
        operation_name: Name of operation (e.g., "filtering data", "loading file")
        operation: Callable that performs the operation and returns success bool
        context: Optional context string (e.g., class name, file path) for logging

    Returns:
        True if operation succeeded, False if failed or raised exception

    Example:
        >>> def do_work() -> bool:
        ...     # Perform operation
        ...     return True
        >>> success = safe_execute("doing work", do_work, "MyClass")
    """
    try:
        return operation()
    except Exception as e:
        if context:
            logger.error(f"Error {operation_name} in {context}: {e}")
        else:
            logger.error(f"Error {operation_name}: {e}")
        return False


def safe_execute_optional[T](
    operation_name: str,
    operation: Callable[[], T | None],
    context: str = "",
) -> T | None:
    """Execute operation with standardized error handling (optional return).

    This function wraps operations that return T | None and provides
    consistent error logging and exception handling.

    Args:
        operation_name: Name of operation (e.g., "loading data", "parsing file")
        operation: Callable that performs the operation and returns T | None
        context: Optional context string (e.g., class name, file path) for logging

    Returns:
        Result of operation if succeeded, None if failed or raised exception

    Example:
        >>> def load_data() -> dict | None:
        ...     # Load and return data
        ...     return {"key": "value"}
        >>> data = safe_execute_optional("loading data", load_data, "DataLoader")
    """
    try:
        return operation()
    except Exception as e:
        if context:
            logger.error(f"Error {operation_name} in {context}: {e}")
        else:
            logger.error(f"Error {operation_name}: {e}")
        return None


def safe_operation(operation_name: str = "", context: str = "") -> Callable[[Callable[..., bool]], Callable[..., bool]]:
    """Decorator for methods that return bool with standardized error handling.

    This decorator wraps methods that return bool (success/failure) and provides
    consistent error logging and exception handling. The operation name can be
    inferred from the method name if not provided.

    Args:
        operation_name: Name of operation (defaults to method name)
        context: Optional context string (defaults to class name)

    Returns:
        Decorator function that wraps the method

    Example:
        >>> class DataProcessor:
        ...     @safe_operation("processing data")
        ...     def process(self) -> bool:
        ...         # Perform operation
        ...         return True
    """

    def decorator(func: Callable[..., bool]) -> Callable[..., bool]:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> bool:
            # Infer operation name from function name if not provided
            op_name = operation_name or func.__name__.replace("_", " ")

            # Infer context from self if available and context not provided
            ctx = context
            if not ctx and args:
                # Try to get class name from first argument (self)
                with contextlib.suppress(AttributeError, IndexError):
                    ctx = args[0].__class__.__name__

            try:
                return func(*args, **kwargs)
            except Exception as e:
                if ctx:
                    logger.error(f"Error {op_name} in {ctx}: {e}")
                else:
                    logger.error(f"Error {op_name}: {e}")
                return False

        return wrapper

    return decorator


def safe_operation_optional(operation_name: str = "", context: str = "") -> Callable[[Callable[..., T | None]], Callable[..., T | None]]:
    """Decorator for methods that return T | None with standardized error handling.

    This decorator wraps methods that return T | None and provides
    consistent error logging and exception handling. The operation name can be
    inferred from the method name if not provided.

    Args:
        operation_name: Name of operation (defaults to method name)
        context: Optional context string (defaults to class name)

    Returns:
        Decorator function that wraps the method

    Example:
        >>> class DataLoader:
        ...     @safe_operation_optional("loading data")
        ...     def load(self) -> dict | None:
        ...         # Load and return data
        ...         return {"key": "value"}
    """

    def decorator(func: Callable[..., T | None]) -> Callable[..., T | None]:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> T | None:
            # Infer operation name from function name if not provided
            op_name = operation_name or func.__name__.replace("_", " ")

            # Infer context from self if available and context not provided
            ctx = context
            if not ctx and args:
                # Try to get class name from first argument (self)
                with contextlib.suppress(AttributeError, IndexError):
                    ctx = args[0].__class__.__name__

            try:
                return func(*args, **kwargs)
            except Exception as e:
                if ctx:
                    logger.error(f"Error {op_name} in {ctx}: {e}")
                else:
                    logger.error(f"Error {op_name}: {e}")
                return None

        return wrapper

    return decorator
