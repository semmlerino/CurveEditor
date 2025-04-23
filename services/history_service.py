#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HistoryService: facade for legacy HistoryOperations (phase 1).
Dynamically attaches all static methods from the legacy HistoryOperations class.
"""

from history_operations import HistoryOperations as LegacyHistoryOps
from typing import Any

class HistoryService:
    """Facade for history operations (phase 1)."""
    @staticmethod
    def undo_action(main_window: Any) -> None:
        """Stub for undo_action to satisfy UI typing."""
        pass

    @staticmethod
    def redo_action(main_window: Any) -> None:
        """Stub for redo_action to satisfy UI typing."""
        pass

# Attach legacy static methods (excluding private)
for name, fn in LegacyHistoryOps.__dict__.items():
    if callable(fn) and not name.startswith("_"):
        setattr(HistoryService, name, staticmethod(fn))
