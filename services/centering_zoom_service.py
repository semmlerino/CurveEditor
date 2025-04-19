#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CenteringZoomService: facade for legacy ZoomOperations.
Dynamically attaches all static methods from ZoomOperations.
"""

from centering_zoom_operations import ZoomOperations as LegacyZoomOps

class CenteringZoomService:
    """Facade for centering & zoom operations."""
    pass

# Attach legacy static methods
for name, fn in LegacyZoomOps.__dict__.items():
    if callable(fn) and not name.startswith("_"):
        setattr(CenteringZoomService, name, staticmethod(fn))
