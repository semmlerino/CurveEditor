#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Custom exception hierarchy for the CurveEditor application.

This module defines a structured hierarchy of exceptions to enable more
precise error handling, better logging, and improved error recovery mechanisms.
Specific exception types allow for targeted error handling instead of catching
generic Exception instances.
"""

from typing import Optional


class CurveEditorError(Exception):
    """Base exception for all CurveEditor-specific errors."""
    def __init__(self, message: str = "An error occurred in CurveEditor", 
                 details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)


# File operation exceptions
class FileError(CurveEditorError):
    """Base class for file operation errors."""
    def __init__(self, message: str = "File operation error", 
                 details: Optional[str] = None, 
                 file_path: Optional[str] = None):
        self.file_path = file_path
        super().__init__(message, details)


class FileReadError(FileError):
    """Error when reading a file."""
    def __init__(self, message: str = "Error reading file", 
                 details: Optional[str] = None, 
                 file_path: Optional[str] = None):
        super().__init__(message, details, file_path)


class FileWriteError(FileError):
    """Error when writing to a file."""
    def __init__(self, message: str = "Error writing to file", 
                 details: Optional[str] = None, 
                 file_path: Optional[str] = None):
        super().__init__(message, details, file_path)


class FileFormatError(FileError):
    """Error when file format is invalid."""
    def __init__(self, message: str = "Invalid file format", 
                 details: Optional[str] = None, 
                 file_path: Optional[str] = None):
        super().__init__(message, details, file_path)


class FileNotFoundError(FileError):
    """Error when a file doesn't exist."""
    def __init__(self, message: str = "File not found", 
                 details: Optional[str] = None, 
                 file_path: Optional[str] = None):
        super().__init__(message, details, file_path)


# Data operation exceptions
class DataError(CurveEditorError):
    """Base class for data operation errors."""
    pass


class DataValidationError(DataError):
    """Error when data validation fails."""
    def __init__(self, message: str = "Data validation failed", 
                 details: Optional[str] = None):
        super().__init__(message, details)


class DataProcessingError(DataError):
    """Error during data processing."""
    def __init__(self, message: str = "Error processing data", 
                 details: Optional[str] = None):
        super().__init__(message, details)


class DataNotFoundError(DataError):
    """Error when required data is missing."""
    def __init__(self, message: str = "Required data not found", 
                 details: Optional[str] = None):
        super().__init__(message, details)


# UI operation exceptions
class UIError(CurveEditorError):
    """Base class for UI operation errors."""
    pass


class ViewError(UIError):
    """Error in view operations."""
    def __init__(self, message: str = "Error in view operation", 
                 details: Optional[str] = None,
                 component: Optional[str] = None):
        self.component = component
        super().__init__(message, details)


class DialogError(UIError):
    """Error in dialog operations."""
    def __init__(self, message: str = "Error in dialog operation", 
                 details: Optional[str] = None,
                 dialog_name: Optional[str] = None):
        self.dialog_name = dialog_name
        super().__init__(message, details)


# Image operation exceptions
class ImageError(CurveEditorError):
    """Base class for image operation errors."""
    pass


class ImageLoadError(ImageError):
    """Error when loading an image."""
    def __init__(self, message: str = "Error loading image", 
                 details: Optional[str] = None,
                 image_path: Optional[str] = None):
        self.image_path = image_path
        super().__init__(message, details)


class ImageProcessingError(ImageError):
    """Error when processing an image."""
    def __init__(self, message: str = "Error processing image", 
                 details: Optional[str] = None):
        super().__init__(message, details)


# Configuration exceptions
class ConfigError(CurveEditorError):
    """Base class for configuration errors."""
    pass


class SettingsError(ConfigError):
    """Error in settings operations."""
    def __init__(self, message: str = "Error in settings operation", 
                 details: Optional[str] = None,
                 setting_key: Optional[str] = None):
        self.setting_key = setting_key
        super().__init__(message, details)


# Transformation exceptions
class TransformationError(CurveEditorError):
    """Base class for transformation errors."""
    pass


class TransformationApplyError(TransformationError):
    """Error when applying a transformation."""
    def __init__(self, message: str = "Error applying transformation", 
                 details: Optional[str] = None,
                 transform_name: Optional[str] = None):
        self.transform_name = transform_name
        super().__init__(message, details)


# Recovery mechanisms
class RecoveryError(CurveEditorError):
    """Error during recovery process."""
    def __init__(self, message: str = "Error during recovery process", 
                 details: Optional[str] = None,
                 original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(message, details)
