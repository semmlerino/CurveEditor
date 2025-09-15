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
import threading

from services.data_service import DataService
from services.interaction_service import InteractionService  # type: ignore[import]
from services.service_protocols import (
    BatchEditableProtocol,
    CurveViewProtocol,
    HistoryCommandProtocol,
    HistoryContainerProtocol,
    LoggingServiceProtocol,
    MainWindowProtocol,
    ServiceProtocol,
    StateManagerProtocol,
    StatusServiceProtocol,
)
from services.transform_service import Transform, TransformService, ViewState
from services.ui_service import UIService

# Sprint 8 services have been removed in favor of the consolidated 4-service architecture

# Service instances (singleton pattern)
_data_service: DataService | None = None
_interaction_service: InteractionService | None = None
_transform_service: TransformService | None = None
_ui_service: UIService | None = None

# Thread lock for service initialization
_service_lock = threading.Lock()

# History is now fully integrated into InteractionService
# Legacy service getters removed - use core services directly:
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
    # Service Protocols for type safety
    "BatchEditableProtocol",
    "CurveViewProtocol",
    "HistoryCommandProtocol",
    "HistoryContainerProtocol",
    "LoggingServiceProtocol",
    "MainWindowProtocol",
    "ServiceProtocol",
    "StateManagerProtocol",
    "StatusServiceProtocol",
    # Service getters (4 core)
    "get_transform_service",
    "get_data_service",
    "get_interaction_service",
    "get_ui_service",
    # Utility
    "get_module_logger",
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
