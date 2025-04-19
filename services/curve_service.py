#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CurveService: extracted business logic placeholder for CurveViewOperations.
For Phase 1, this module re-exports all of the static methods from the legacy CurveViewOperations.
Further refactoring will move implementations here.
"""

import math
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt, QRect
from centering_zoom_operations import ZoomOperations
from error_handling import safe_operation

# Import legacy class to re-export its static methods
from curve_view_operations import CurveViewOperations as LegacyCurveOps

class CurveService:
    """Facade for curve operations (phase 1)."""
    pass

# Dynamically attach all static methods from the legacy module
for name, fn in LegacyCurveOps.__dict__.items():
    if callable(fn):
        setattr(CurveService, name, staticmethod(fn))
