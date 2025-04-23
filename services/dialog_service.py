#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DialogService: facade for legacy DialogOperations (phase 1).
Dynamically attaches all static methods from the legacy DialogOperations class.
"""

from dialog_operations import DialogOperations as LegacyDialogOps
from typing import Any

class DialogService:
    """Facade for dialog operations (phase 1)."""
    @staticmethod
    def show_smooth_dialog(main_window: Any) -> None:
        """Stub for show_smooth_dialog to satisfy UI typing."""
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

# Attach legacy static methods (excluding private)
for name, fn in LegacyDialogOps.__dict__.items():
    if callable(fn) and not name.startswith("_"):
        setattr(DialogService, name, staticmethod(fn))
