#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SettingsService: facade for legacy SettingsOperations.
Dynamically attaches all static methods from the legacy SettingsOperations class.
"""

from settings_operations import SettingsOperations as LegacySettingsOps

class SettingsService:
    """Facade for settings operations (phase 1)."""
    pass

# Attach legacy static methods
for name, fn in LegacySettingsOps.__dict__.items():
    if callable(fn) and not name.startswith("_"):
        setattr(SettingsService, name, staticmethod(fn))
