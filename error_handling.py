#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Error handling utilities for the 3DE4 Curve Editor application.

This module provides standardized error handling mechanisms to ensure consistent
user experience and proper error reporting throughout the application.
"""

import traceback
from PySide6.QtWidgets import QMessageBox
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

def safe_operation(operation_name: Optional[str] = None, record_history: bool = True) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """Decorator for safely executing operations with standardized error handling.

    Args:
        operation_name: Optional name of the operation for status messages
        record_history: Whether to record the operation in history (default True)

    Returns:
        Decorated function with error handling

    Example:
        @safe_operation("Load Track Data")
        def load_track_data(main_window):
            # Implementation

        @safe_operation("Finalize Selection", record_history=False)
        def finalize_selection(main_window):
            # Implementation
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        def wrapper(main_window: Any, *args: Any, **kwargs: Any) -> Optional[T]:
            op_name = operation_name or func.__name__.replace('_', ' ').title()
            try:
                result = func(main_window, *args, **kwargs)
                # Show success in status bar if appropriate
                if hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(f"{op_name} completed successfully", 2000)

                # Add to history if appropriate and the operation was successful
                if record_history and result is not None and hasattr(main_window, 'add_to_history'):
                    main_window.add_to_history()

                return result
            except Exception as e:
                # Log error
                print(f"Error in {op_name}: {str(e)}")
                traceback.print_exc()

                # Show error to user
                if hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(f"Error in {op_name}: {str(e)}", 5000)

                QMessageBox.critical(main_window, f"Error in {op_name}",
                                   f"An error occurred during {op_name}:\n{str(e)}")
                return None
        return wrapper
    return decorator

def show_error(parent: Optional[Any], title: str, message: str, detailed_message: Optional[str] = None) -> None:
    """Display a standardized error message to the user.

    Args:
        parent: Parent widget for the message box
        title: Error dialog title
        message: Main error message
        detailed_message: Optional detailed message or traceback
    """
    error_box = QMessageBox(parent)
    icon = getattr(QMessageBox, "Critical", None)
    error_box.setIcon(icon)  # type: ignore
    error_box.setWindowTitle(title)
    error_box.setText(message)

    if detailed_message:
        error_box.setDetailedText(detailed_message)

    buttons = getattr(QMessageBox, "Ok", None)
    error_box.setStandardButtons(buttons)  # type: ignore

    error_box.exec_()

    # Also log the error
    print(f"ERROR - {title}: {message}")
    if detailed_message:
        print(f"DETAILS: {detailed_message}")
