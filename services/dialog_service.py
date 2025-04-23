#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DialogService: facade for legacy DialogOperations (phase 1).
Dynamically attaches all static methods from the legacy DialogOperations class.
"""

from dialog_operations import DialogOperations as LegacyDialogOps
from typing import Any, Optional # Added Optional

class DialogService:
    """Facade for dialog operations (phase 1)."""
    @staticmethod
    def show_smooth_dialog(
        parent_widget: Any, # Use Any temporarily due to potential PySide6 import issues
        curve_data: Any,    # Use Any temporarily
        selected_indices: Any, # Use Any temporarily
        selected_point_idx: int
    ) -> Optional[Any]: # Use Any temporarily
        """Facade stub matching the refactored signature in dialog_operations.py"""
        # The actual implementation is dynamically attached below.
        # This stub primarily helps with static analysis and type hinting.
        pass

    @staticmethod
    def show_fill_gaps_dialog(main_window: Any) -> None:
        """Stub for show_fill_gaps_dialog to satisfy UI typing."""
        pass

    @staticmethod
    def show_filter_dialog(main_window: Any) -> None:
        """Stub for show_filter_dialog to satisfy UI typing."""
        pass

    @staticmethod
    def show_extrapolate_dialog(main_window: Any) -> None:
        """Stub for show_extrapolate_dialog to satisfy UI typing."""
        pass

    @staticmethod
    def show_shortcuts_dialog(main_window: Any) -> None:
        """Stub for show_shortcuts_dialog to satisfy static analysis."""
        pass

# Attach legacy static methods (excluding private)
for name, fn in LegacyDialogOps.__dict__.items():
    if callable(fn) and not name.startswith("_"):
        setattr(DialogService, name, staticmethod(fn))
