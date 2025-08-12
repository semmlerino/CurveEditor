#!/usr/bin/env python
"""
Services package for CurveEditor.

This package contains the consolidated service classes that implement the core
functionality of the CurveEditor application. Each service follows the single
responsibility principle and provides a specific set of related operations.

The services have been consolidated from 8 services to 4 focused services:
1. TransformService - All coordinate transformations and view state management
2. DataService - Data operations including analysis, file I/O, and image management
3. InteractionService - User interactions including point manipulation, input, and history
4. UIService - UI operations including dialogs, status updates, and component management
"""

import inspect
import logging

# Import the consolidated services
try:
    from services.transform_service import TransformService, Transform, ViewState, get_transform_service
except ImportError:
    TransformService = None
    Transform = None
    ViewState = None
    get_transform_service = None

try:
    from services.data_service import DataService, get_data_service
except ImportError:
    DataService = None
    get_data_service = None

try:
    from services.interaction_service import InteractionService, get_interaction_service
except ImportError:
    InteractionService = None
    get_interaction_service = None

try:
    from services.ui_service import UIService, get_ui_service
except ImportError:
    UIService = None
    get_ui_service = None

# Legacy imports for backward compatibility (will be deprecated)
try:
    from services.curve_service import CurveService
except ImportError:
    CurveService = None

try:
    from services.dialog_service import DialogService
except ImportError:
    DialogService = None

try:
    from services.history_service import HistoryService
except ImportError:
    HistoryService = None

try:
    from services.image_service import ImageService
except ImportError:
    ImageService = None

try:
    from services.input_service import InputService
except ImportError:
    InputService = None

try:
    from services.file_service import FileService
except ImportError:
    FileService = None

try:
    from services.unified_transform import Transform as LegacyTransform
except ImportError:
    LegacyTransform = None

try:
    from services.view_state import ViewState as LegacyViewState
except ImportError:
    LegacyViewState = None

# Build __all__ dynamically based on what's available
_available_exports = []

# Add new consolidated services
if TransformService is not None:
    _available_exports.extend(["TransformService", "Transform", "ViewState", "get_transform_service"])

if DataService is not None:
    _available_exports.extend(["DataService", "get_data_service"])

if InteractionService is not None:
    _available_exports.extend(["InteractionService", "get_interaction_service"])

if UIService is not None:
    _available_exports.extend(["UIService", "get_ui_service"])

# Add legacy services for backward compatibility
if CurveService is not None:
    _available_exports.append("CurveService")

if DialogService is not None:
    _available_exports.append("DialogService")

if FileService is not None:
    _available_exports.append("FileService")

if HistoryService is not None:
    _available_exports.append("HistoryService")

if ImageService is not None:
    _available_exports.append("ImageService")

if InputService is not None:
    _available_exports.append("InputService")

if LegacyTransform is not None and Transform is None:
    # Only export legacy if new one isn't available
    _available_exports.append("Transform")
    Transform = LegacyTransform

if LegacyViewState is not None and ViewState is None:
    # Only export legacy if new one isn't available
    _available_exports.append("ViewState")
    ViewState = LegacyViewState

# Always export utility functions
_available_exports.extend([
    "get_module_logger", 
    "get_transform_service", 
    "get_data_service", 
    "get_interaction_service", 
    "get_ui_service"
])

__all__ = _available_exports

# Service getter functions
def get_transform_service():
    """Get TransformService instance."""
    if TransformService:
        return TransformService()
    return None

def get_data_service():
    """Get DataService instance."""  
    if DataService:
        return DataService()
    return None

def get_interaction_service():
    """Get InteractionService instance."""
    if InteractionService:
        return InteractionService()
    return None

def get_ui_service():
    """Get UIService instance."""
    if UIService:
        return UIService()
    return None

# Utility function for getting a logger for the calling module
def get_module_logger(logging_service=None) -> logging.Logger:
    """
    Get a logger named after the calling module.

    This utility function reduces boilerplate by automatically determining
    the module name from the calling context.

    Args:
        logging_service: Optional service instance (not used in simplified version).

    Returns:
        Logger: A logger configured for the calling module
    """
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    if module is None:
        module_name = "unknown"
    else:
        module_name = module.__name__.split(".")[-1]

    # Use standard logging for startup
    return logging.getLogger(module_name)