#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HistoryService: facade for legacy HistoryOperations (phase 1).
Dynamically attaches all static methods from the legacy HistoryOperations class.
"""

from history_operations import HistoryOperations as LegacyHistoryOps

class HistoryService:
    """Facade for history operations (phase 1)."""
    pass

# Attach legacy static methods (excluding private)
for name, fn in LegacyHistoryOps.__dict__.items():
    if callable(fn) and not name.startswith("_"):
        setattr(HistoryService, name, staticmethod(fn))
