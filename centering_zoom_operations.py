#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DEPRECATED: This module has been migrated to services/centering_zoom_service.py
Please update your imports to use:
    from services.centering_zoom_service import CenteringZoomService as ZoomOperations

This file is kept only for backward compatibility and will be removed in a future version.
"""

import warnings
from typing import Any, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from curve_view import CurveView
    from PySide6.QtGui import QWheelEvent

# Issue deprecation warning
warnings.warn(
    "The centering_zoom_operations module is deprecated. "
    "Please use 'from services.centering_zoom_service import CenteringZoomService as ZoomOperations' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import the service version
from services.centering_zoom_service import CenteringZoomService

# Re-export CenteringZoomService as ZoomOperations for backward compatibility
class ZoomOperations:
    """
    DEPRECATED: Static utility methods for zooming and centering.
    All methods are forwarded to CenteringZoomService for backward compatibility.
    """
    # Forward all static method calls to the service implementation
    def __new__(cls, *args, **kwargs):
        return CenteringZoomService(*args, **kwargs)

    # Dynamically forward all static methods
    for name, fn in CenteringZoomService.__dict__.items():
        if callable(fn) and not name.startswith('__'):
            locals()[name] = staticmethod(getattr(CenteringZoomService, name))
