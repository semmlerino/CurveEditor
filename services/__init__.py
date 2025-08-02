#!/usr/bin/env python

"""
Services package for CurveEditor.

This package contains service classes that implement the core functionality
of the CurveEditor application. Each service class follows the single
responsibility principle and provides a specific set of related operations.

The __init__ module provides convenient imports and utilities that improve
code organization and reduce duplication across the application.
"""

import inspect
from typing import Any, Protocol, TypeVar, cast

from core.protocols import PointsList

# AnalysisService removed - using CurveAnalysisService directly
from services.curve_service import CurveService
from services.dialog_service import DialogService
from services.file_service import FileService

# New specialized analysis services
from services.history_service import HistoryService
from services.image_service import ImageService
from services.input_service import InputService
from services.logging_service import LoggingService
from services.models import Point, PointsCollection
from services.settings_service import SettingsService
from services.status_manager import StatusManager
from services.unified_transform import Transform

# UnifiedTransformationService removed - using TransformationService directly
from services.view_state import ViewState
from services.visualization_service import VisualizationService

__all__ = [
    # Core models and protocols
    "Point",
    "ViewState",
    "PointsCollection",
    "PointsList",
    # Core services
    # "AnalysisService", # Removed - using CurveAnalysisService directly
    "CurveService",
    "DialogService",
    "FileService",
    "HistoryService",
    "ImageService",
    "InputService",
    "LoggingService",
    "SettingsService",
    "StatusManager",
    "VisualizationService",
    "TrackQualityAnalysisService",
    # Specialized analysis services (consolidated into CurveAnalysisService)
    # Unified transformation system
    "Transform",
    # "UnifiedTransformationService", # Removed - using TransformationService directly
    # Utility functions
    "get_module_logger",
    "get_service",
]


# Utility function for getting a logger for the calling module
def get_module_logger() -> Any:
    """
    Get a logger named after the calling module.

    This utility function reduces boilerplate by automatically determining
    the module name from the calling context.

    Returns:
        Logger: A logger configured for the calling module
    """
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    if module is None:
        return LoggingService.get_logger("unknown")

    module_name = module.__name__.split(".")[-1]
    return LoggingService.get_logger(module_name)


# Cache for commonly used services
_service_cache = {}


T = TypeVar("T")


def get_service[T](service_class: type[T]) -> T:
    """
    Get or create a singleton instance of a service class.

    This utility reduces redundant service instantiations by caching
    service instances by class.

    Args:
        service_class: The service class to instantiate

    Returns:
        An instance of the requested service
    """
    if service_class not in _service_cache:
        _service_cache[service_class] = service_class()
    return cast(T, _service_cache[service_class])


# Protocol for track quality analyzers (kept for backward compatibility)
class TrackQualityAnalyzerProtocol(Protocol):
    def analyze_track(self, points: PointsList) -> dict[str, float]: ...
