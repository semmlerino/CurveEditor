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

import threading
from typing import TYPE_CHECKING

# Import protocols at module level (these are always safe)
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

# Import concrete types only for type checking to avoid cycles
if TYPE_CHECKING:
    from services.data_service import DataService
    from services.interaction_service import InteractionService
    from services.transform_service import Transform, TransformService, ViewState
    from services.ui_service import UIService
else:
    # These will be imported lazily in the getter functions
    DataService = None
    InteractionService = None
    TransformService = None
    UIService = None
    Transform = None
    ViewState = None

# Sprint 8 services have been removed in favor of the consolidated 4-service architecture

# Service instances (singleton pattern) - use Any to avoid forward reference issues
_data_service: object | None = None
_interaction_service: object | None = None
_transform_service: object | None = None
_ui_service: object | None = None

# Thread lock for service initialization
_service_lock = threading.Lock()

# History is now fully integrated into InteractionService
# Legacy service getters removed - use core services directly:
# get_file_service() -> use get_data_service()
# get_curve_analysis_service() -> use get_data_service()
# get_image_management_service() -> use get_data_service()

# Export all public symbols - include conditionally imported types
__all__ = [
    # Service Protocols for type safety (always available)
    "BatchEditableProtocol",
    "CurveViewProtocol",
    "HistoryCommandProtocol",
    "HistoryContainerProtocol",
    "LoggingServiceProtocol",
    "MainWindowProtocol",
    "ServiceProtocol",
    "StateManagerProtocol",
    "StatusServiceProtocol",
    # Service getters (4 core) - always available
    "get_transform_service",
    "get_data_service",
    "get_interaction_service",
    "get_ui_service",
    # Utility
    "get_module_logger",
    "reset_all_services",
]

# Add service types to __all__ only if TYPE_CHECKING is False (runtime)
# This ensures they're available for runtime imports but doesn't break type checking
if not TYPE_CHECKING:
    __all__.extend(
        [
            "TransformService",
            "Transform",
            "ViewState",
            "DataService",
            "InteractionService",
            "UIService",
        ]
    )


def get_data_service() -> "DataService":
    """Get the singleton DataService instance (thread-safe)."""
    global _data_service
    with _service_lock:
        if _data_service is None:
            # Lazy import to avoid circular dependency
            from services.data_service import DataService

            _data_service = DataService()
    return _data_service  # pyright: ignore[reportReturnType]


def get_interaction_service() -> "InteractionService":
    """Get the singleton InteractionService instance (thread-safe)."""
    global _interaction_service
    with _service_lock:
        if _interaction_service is None:
            # Lazy import to avoid circular dependency
            from services.interaction_service import InteractionService

            _interaction_service = InteractionService()
    return _interaction_service  # pyright: ignore[reportReturnType]


def get_transform_service() -> "TransformService":
    """Get the singleton TransformService instance (thread-safe)."""
    global _transform_service
    with _service_lock:
        if _transform_service is None:
            # Lazy import to avoid circular dependency
            from services.transform_service import TransformService

            _transform_service = TransformService()
    return _transform_service  # pyright: ignore[reportReturnType]


def get_ui_service() -> "UIService":
    """Get the singleton UIService instance (thread-safe)."""
    global _ui_service
    with _service_lock:
        if _ui_service is None:
            # Lazy import to avoid circular dependency
            from services.ui_service import UIService

            _ui_service = UIService()
    return _ui_service  # pyright: ignore[reportReturnType]


def reset_all_services() -> None:
    """
    Reset all service singletons (for testing).

    This clears all cached service instances and state, allowing tests
    to start with fresh instances.
    """
    global _data_service, _interaction_service, _transform_service, _ui_service
    with _service_lock:
        _data_service = None
        _interaction_service = None
        _transform_service = None
        _ui_service = None
