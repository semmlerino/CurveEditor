from __future__ import annotations
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DEPRECATED: This module has been migrated to services/visualization_service.py
Please update your imports to use:
    from services.visualization_service import VisualizationService as VisualizationOperations

This file is kept only for backward compatibility and will be removed in a future version.
"""

import warnings
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from curve_view import CurveView

import os

# Issue deprecation warning
warnings.warn(
    "The visualization_operations module is deprecated. "
    "Please use 'from services.visualization_service import VisualizationService as VisualizationOperations' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Directly import the service version
from services.visualization_service import VisualizationService

# Re-export VisualizationService as VisualizationOperations for backward compatibility
class VisualizationOperations:
    """
    DEPRECATED: Static utility methods for visualization operations in the curve editor.
    All methods are forwarded to VisualizationService for backward compatibility.
    """
    # Forward all static method calls to the service implementation
    def __new__(cls, *args, **kwargs):
        return VisualizationService(*args, **kwargs)

    # Dynamically forward all static methods
    for name, fn in VisualizationService.__dict__.items():
        if callable(fn) and not name.startswith('__'):
            locals()[name] = staticmethod(getattr(VisualizationService, name))
