#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
VisualizationService: facade for legacy VisualizationOperations (phase 1).
All static methods are dynamically attached from the legacy VisualizationOperations.
"""

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
import os
from centering_zoom_operations import ZoomOperations
from typing import Any

# Import legacy class
from visualization_operations import VisualizationOperations as LegacyVisOps

class VisualizationService:
    """Facade for visualization operations (phase 1)."""
    @staticmethod
    def toggle_grid(curve_view: Any, enabled: bool) -> None:
        """Stub for static analysis."""
        pass
    @staticmethod
    def toggle_velocity_vectors(curve_view: Any, enabled: bool) -> None:
        """Stub for static analysis."""
        pass
    @staticmethod
    def toggle_all_frame_numbers(curve_view: Any, enabled: bool) -> None:
        """Stub for static analysis."""
        pass

# Dynamically attach all static methods from the legacy module
for name, fn in LegacyVisOps.__dict__.items():
    if callable(fn):
        setattr(VisualizationService, name, staticmethod(fn))
