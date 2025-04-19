#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DialogService: facade for legacy DialogOperations (phase 1).
Dynamically attaches all static methods from the legacy DialogOperations class.
"""

from dialog_operations import DialogOperations as LegacyDialogOps

class DialogService:
    """Facade for dialog operations (phase 1)."""
    pass

# Attach legacy static methods (excluding private)
for name, fn in LegacyDialogOps.__dict__.items():
    if callable(fn) and not name.startswith("_"):
        setattr(DialogService, name, staticmethod(fn))
