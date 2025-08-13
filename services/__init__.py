#!/usr/bin/env python
"""
Services package for CurveEditor.

This package contains the service classes that implement the core functionality
of the CurveEditor application following a clean architecture with dependency
injection.

Architecture:
- ServiceContainer: Central dependency injection container
- Consolidated to 4 core services
- No direct imports between services (use container instead)

Core Services (4 total):
1. TransformService - Coordinate transformations and view state management
2. DataService - ALL data operations (analysis, file I/O, images)
3. InteractionService - User interactions, point manipulation, and history (fully integrated)
4. UIService - UI operations, dialogs, and status updates
"""

import logging
import os
import threading
from typing import Any

from services.data_service import DataService
from services.interaction_service import InteractionService
from services.transform_service import Transform, TransformService, ViewState
from services.ui_service import UIService

# Import new decomposed services (Sprint 8)
if os.environ.get("USE_NEW_SERVICES", "false").lower() == "true":
    from services.event_handler import EventHandlerService
    from services.history_service import HistoryService
    from services.point_manipulation import PointManipulationService
    from services.selection_service import SelectionService

# Feature flag for gradual migration to new services
USE_NEW_SERVICES = os.environ.get("USE_NEW_SERVICES", "false").lower() == "true"

# Service instances (singleton pattern)
_data_service: DataService | None = None
_interaction_service: InteractionService | None = None
_transform_service: TransformService | None = None
_ui_service: UIService | None = None

# New decomposed service instances (Sprint 8)
_event_handler_service: Any | None = None
_selection_service: Any | None = None
_point_manipulation_service: Any | None = None
_history_service: Any | None = None

# Thread lock for service initialization
_service_lock = threading.Lock()

# History is now fully integrated into InteractionService
# Legacy service getters removed - use core services directly:
# get_history_service() -> use get_interaction_service()
# get_file_service() -> use get_data_service()
# get_curve_analysis_service() -> use get_data_service()
# get_image_management_service() -> use get_data_service()

# Export all public symbols
__all__ = [
    # Core Service types (4 services)
    "TransformService",
    "Transform",
    "ViewState",
    "DataService",
    "InteractionService",
    "UIService",

    # Service getters (4 core)
    "get_transform_service",
    "get_data_service",
    "get_interaction_service",
    "get_ui_service",

    # New decomposed service getters (Sprint 8)
    "get_event_handler_service",
    "get_selection_service",
    "get_point_manipulation_service",
    "get_history_service",

    # Utility
    "get_module_logger",

    # Feature flag
    "USE_NEW_SERVICES",
]


def get_data_service() -> DataService:
    """Get the singleton DataService instance (thread-safe)."""
    global _data_service
    with _service_lock:
        if _data_service is None:
            _data_service = DataService()
    return _data_service


def get_interaction_service() -> InteractionService:
    """Get the singleton InteractionService instance (thread-safe)."""
    global _interaction_service
    with _service_lock:
        if _interaction_service is None:
            _interaction_service = InteractionService()
    return _interaction_service


def get_transform_service() -> TransformService:
    """Get the singleton TransformService instance (thread-safe)."""
    global _transform_service
    with _service_lock:
        if _transform_service is None:
            _transform_service = TransformService()
    return _transform_service


def get_ui_service() -> UIService:
    """Get the singleton UIService instance (thread-safe)."""
    global _ui_service
    with _service_lock:
        if _ui_service is None:
            _ui_service = UIService()
    return _ui_service


# New decomposed service getters (Sprint 8)
def get_event_handler_service() -> Any:
    """Get the singleton EventHandlerService instance (thread-safe)."""
    global _event_handler_service
    if not USE_NEW_SERVICES:
        raise RuntimeError("New services not enabled. Set USE_NEW_SERVICES=true")
    with _service_lock:
        if _event_handler_service is None:
            from services.event_handler import EventHandlerService
            _event_handler_service = EventHandlerService()
    return _event_handler_service


def get_selection_service() -> Any:
    """Get the singleton SelectionService instance (thread-safe)."""
    global _selection_service
    if not USE_NEW_SERVICES:
        raise RuntimeError("New services not enabled. Set USE_NEW_SERVICES=true")
    with _service_lock:
        if _selection_service is None:
            from services.selection_service import SelectionService
            _selection_service = SelectionService()
    return _selection_service


def get_point_manipulation_service() -> Any:
    """Get the singleton PointManipulationService instance (thread-safe)."""
    global _point_manipulation_service
    if not USE_NEW_SERVICES:
        raise RuntimeError("New services not enabled. Set USE_NEW_SERVICES=true")
    with _service_lock:
        if _point_manipulation_service is None:
            from services.point_manipulation import PointManipulationService
            _point_manipulation_service = PointManipulationService()
    return _point_manipulation_service


def get_history_service() -> Any:
    """Get the singleton HistoryService instance (thread-safe)."""
    global _history_service
    if not USE_NEW_SERVICES:
        # Fall back to InteractionService for backward compatibility
        return get_interaction_service()
    with _service_lock:
        if _history_service is None:
            from services.history_service import HistoryService
            _history_service = HistoryService()
    return _history_service


def get_module_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger for the specified module name.

    Args:
        name: Module name for the logger. If None, uses calling module.

    Returns:
        Logger instance
    """
    if name is None:
        import inspect

        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        if module is None:
            name = "unknown"
        else:
            name = module.__name__.split(".")[-1]

    return logging.getLogger(name)
