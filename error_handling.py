#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Error handling utilities for the 3DE4 Curve Editor application.

This module provides standardized error handling mechanisms to ensure consistent
user experience and proper error reporting throughout the application.
"""

import traceback
from PySide6.QtWidgets import QMessageBox

def safe_operation(operation_name=None):
    """Decorator for safely executing operations with standardized error handling.
    
    Args:
        operation_name: Optional name of the operation for status messages
        
    Returns:
        Decorated function with error handling
        
    Example:
        @safe_operation("Load Track Data")
        def load_track_data(main_window):
            # Implementation
    """
    def decorator(func):
        def wrapper(main_window, *args, **kwargs):
            op_name = operation_name or func.__name__.replace('_', ' ').title()
            try:
                result = func(main_window, *args, **kwargs)
                # Show success in status bar if appropriate
                if hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(f"{op_name} completed successfully", 2000)
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

def show_error(parent, title, message, detailed_message=None):
    """Display a standardized error message to the user.
    
    Args:
        parent: Parent widget for the message box
        title: Error dialog title
        message: Main error message
        detailed_message: Optional detailed message or traceback
    """
    error_box = QMessageBox(parent)
    error_box.setIcon(QMessageBox.Critical)
    error_box.setWindowTitle(title)
    error_box.setText(message)
    
    if detailed_message:
        error_box.setDetailedText(detailed_message)
        
    error_box.setStandardButtons(QMessageBox.Ok)
    error_box.exec_()
    
    # Also log the error
    print(f"ERROR - {title}: {message}")
    if detailed_message:
        print(f"DETAILS: {detailed_message}")