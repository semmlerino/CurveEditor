#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SettingsService: Manages application settings including saving and loading window state,
preferences, and other configuration data.
"""

import os
from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent
from typing import Any, Optional, TYPE_CHECKING, cast
from services.logging_service import LoggingService

# Configure logger for this module
logger = LoggingService.get_logger("settings_service")

if TYPE_CHECKING:
    from main_window import MainWindow

class SettingsService:
    """Service for managing application settings."""

    # Constants for settings keys
    APP_NAME = "3DE4"
    APP_ORGANIZATION = "CurveEditor"

    # Settings keys
    KEY_GEOMETRY = "geometry"
    KEY_WINDOW_STATE = "windowState"
    KEY_LAST_DIRECTORY = "lastDirectory"
    KEY_HISTORY_SIZE = "historySize"
    KEY_AUTO_CENTER = "view/autoCenterOnFrameChange"

    @staticmethod
    def load_settings(main_window: 'MainWindow') -> None:
        """
        Load application settings.

        Args:
            main_window: The main application window
        """
        try:
            settings = QSettings(SettingsService.APP_NAME, SettingsService.APP_ORGANIZATION)

            # Window geometry and state
            geometry = settings.value(SettingsService.KEY_GEOMETRY, b"", type=bytes)
            if isinstance(geometry, (bytes, bytearray, memoryview)) and geometry:
                main_window.restoreGeometry(geometry)

            window_state = settings.value(SettingsService.KEY_WINDOW_STATE, b"", type=bytes)
            if isinstance(window_state, (bytes, bytearray, memoryview)) and window_state:
                main_window.restoreState(window_state)

            # Last used directory
            last_dir = settings.value(SettingsService.KEY_LAST_DIRECTORY, "", type=str)
            if isinstance(last_dir, str) and os.path.isdir(last_dir):
                main_window.default_directory = last_dir

            # History size
            history_size = settings.value(SettingsService.KEY_HISTORY_SIZE, 50, type=int)
            if isinstance(history_size, int) and history_size > 0:
                main_window.max_history_size = history_size

            # Auto-center toggle state
            main_window.auto_center_enabled = bool(settings.value(
                SettingsService.KEY_AUTO_CENTER, False, type=bool
            ))

        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            # Use defaults if settings can't be loaded

    @staticmethod
    def save_settings(main_window: 'MainWindow') -> None:
        """
        Save application settings on exit.

        Args:
            main_window: The main application window
        """
        try:
            settings = QSettings(SettingsService.APP_NAME, SettingsService.APP_ORGANIZATION)

            # Window geometry and state
            settings.setValue(SettingsService.KEY_GEOMETRY, main_window.saveGeometry())
            settings.setValue(SettingsService.KEY_WINDOW_STATE, main_window.saveState())

            # Last used directory
            settings.setValue(SettingsService.KEY_LAST_DIRECTORY, main_window.default_directory)

            # History size
            settings.setValue(SettingsService.KEY_HISTORY_SIZE, main_window.max_history_size)

            # Auto-center toggle state
            settings.setValue(
                SettingsService.KEY_AUTO_CENTER,
                getattr(main_window, 'auto_center_enabled', False)
            )

        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    @staticmethod
    def handle_close_event(main_window: 'MainWindow', event: QCloseEvent) -> None:
        """
        Handle window close event.

        Args:
            main_window: The main application window
            event: The close event
        """
        # Save settings before closing
        SettingsService.save_settings(main_window)
        # Accept the close event
        event.accept()

    @staticmethod
    def get_setting(key: str, default_value: Any = None, value_type: Any = None) -> Any:
        """
        Get a setting value by key.

        Args:
            key: The settings key
            default_value: Default value if the key doesn't exist
            value_type: Type to convert the value to

        Returns:
            The setting value or default if not found
        """
        settings = QSettings(SettingsService.APP_NAME, SettingsService.APP_ORGANIZATION)
        return settings.value(key, default_value, type=value_type)

    @staticmethod
    def set_setting(key: str, value: Any) -> None:
        """
        Set a setting value.

        Args:
            key: The settings key
            value: The value to set
        """
        settings = QSettings(SettingsService.APP_NAME, SettingsService.APP_ORGANIZATION)
        settings.setValue(key, value)
