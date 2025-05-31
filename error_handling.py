#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Error handling utilities for the 3DE4 Curve Editor application.

This module provides standardized error handling mechanisms to ensure consistent
user experience and proper error reporting throughout the application.
"""

import logging
import traceback
from typing import Any, Callable, Optional, TypeVar, Type, Union
from unittest.mock import MagicMock, Mock

from PySide6.QtWidgets import QMessageBox, QWidget

from exceptions import CurveEditorError, RecoveryError

T = TypeVar("T")

# Configure module logger
logger = logging.getLogger(__name__)

def safe_operation(operation_name: Optional[str] = None, record_history: bool = True, 
                   expected_errors: Optional[list[Type[Exception]]] = None,
                   recovery_action: Optional[Callable[..., Any]] = None) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """Decorator for safely executing operations with standardized error handling.

    Args:
        operation_name: Optional name of the operation for status messages
        record_history: Whether to record the operation in history (default True)
        expected_errors: List of expected exception types to catch specifically
        recovery_action: Optional function to call for recovery when an error occurs

    Returns:
        Decorated function with error handling

    Example:
        @safe_operation("Load Track Data", expected_errors=[FileNotFoundError, FileReadError])
        def load_track_data(main_window):
            # Implementation

        @safe_operation("Finalize Selection", record_history=False)
        def finalize_selection(main_window):
            # Implementation
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        def wrapper(main_window: Any, *args: Any, **kwargs: Any) -> Optional[T]:
            op_name = operation_name or func.__name__.replace('_', ' ').title()
            logger.debug(f"Executing operation: {op_name}")
            
            # Default to CurveEditorError if no specific errors are provided
            errors_to_catch = expected_errors or [CurveEditorError, Exception]
            
            try:
                result = func(main_window, *args, **kwargs)
                
                # Show success in status bar if appropriate
                if hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(f"{op_name} completed successfully", 2000)
                logger.info(f"Operation '{op_name}' completed successfully")

                # Add to history if appropriate and the operation was successful
                if record_history and result is not None and hasattr(main_window, 'add_to_history'):
                    main_window.add_to_history()

                return result
                
            except tuple(errors_to_catch) as e:
                error_details = traceback.format_exc()
                logger.error(f"Error in {op_name}: {str(e)}\n{error_details}")

                # Show error to user
                if hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(f"Error in {op_name}: {str(e)}", 5000)

                # Only show message box when not in test mode (testing creates mock objects)
                # Verify main_window is a valid widget by checking for certain attributes
                try:
                    if hasattr(main_window, 'isVisible') and not isinstance(main_window, (MagicMock, Mock)):
                        show_error(main_window, f"Error in {op_name}", 
                                  f"An error occurred during {op_name}:\n{str(e)}", 
                                  error_details)
                except Exception as dialog_error:
                    # Log error creating dialog but don't crash
                    logger.error(f"Error displaying error dialog: {dialog_error}")
                
                # Attempt recovery if a recovery action is provided
                if recovery_action is not None:
                    try:
                        logger.info(f"Attempting recovery for operation '{op_name}'")
                        recovery_result = recovery_action(main_window, *args, e=e, **kwargs)
                        logger.info(f"Recovery for '{op_name}' succeeded")
                        return recovery_result
                    except Exception as recovery_error:
                        logger.error(f"Recovery for '{op_name}' failed: {str(recovery_error)}")
                        # Wrap in RecoveryError to provide context
                        raise RecoveryError(f"Recovery failed for {op_name}", 
                                           f"Original error: {str(e)}\nRecovery error: {str(recovery_error)}", 
                                           original_error=e) from recovery_error
                
                return None
                
        return wrapper
    return decorator

def show_error(parent: Optional[QWidget], title: str, message: str, detailed_message: Optional[str] = None) -> None:
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

    # Log the error
    logger.error(f"{title}: {message}")
    if detailed_message:
        logger.debug(f"Error details: {detailed_message}")
