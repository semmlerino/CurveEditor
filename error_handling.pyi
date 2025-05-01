#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Type stub file for error_handling.py"""

from typing import Any, Callable, TypeVar, Optional, cast

T = TypeVar('T')

def safe_operation(operation_name: Optional[str] = None, record_history: bool = True) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """Decorator for safely executing operations with standardized error handling.

    Args:
        operation_name: Optional name of the operation for status messages
        record_history: Whether to record the operation in history (default True)

    Returns:
        Decorated function with error handling
    """
    ...

def show_error(parent: Any, title: str, message: str, detailed_message: Optional[str] = None) -> None:
    """Display a standardized error message to the user.

    Args:
        parent: Parent widget for the message box
        title: Error dialog title
        message: Main error message
        detailed_message: Optional detailed message or traceback
    """
    ...
