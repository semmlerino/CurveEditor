#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DEPRECATED: This module has been migrated to services/settings_service.py
Please update your imports to use:
    from services.settings_service import SettingsService as SettingsOperations

This file is kept only for backward compatibility and will be removed in a future version.
"""

import warnings
from typing import Any, TYPE_CHECKING
from PySide6.QtGui import QCloseEvent

if TYPE_CHECKING:
    from main_window import MainWindow

# Issue deprecation warning
warnings.warn(
    "The settings_operations module is deprecated. "
    "Please use 'from services.settings_service import SettingsService as SettingsOperations' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import the service version
from services.settings_service import SettingsService

# Re-export SettingsService as SettingsOperations for backward compatibility
class SettingsOperations:
    """
    DEPRECATED: Settings operations for the 3DE4 Curve Editor.
    All methods are forwarded to SettingsService for backward compatibility.
    """
    # Constants
    APP_NAME = SettingsService.APP_NAME
    APP_ORGANIZATION = SettingsService.APP_ORGANIZATION

    # Forward all static method calls to the service implementation
    def __new__(cls, *args, **kwargs):
        return SettingsService(*args, **kwargs)

    # Dynamically forward all static methods
    for name, fn in SettingsService.__dict__.items():
        if callable(fn) and not name.startswith('__'):
            locals()[name] = staticmethod(getattr(SettingsService, name))
