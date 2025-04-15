#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from PySide6.QtCore import QSettings


class SettingsOperations:
    """Settings operations for the 3DE4 Curve Editor."""
    
    APP_NAME = "3DE4"
    APP_ORGANIZATION = "CurveEditor"
    
    @staticmethod
    def load_settings(main_window):
        """Load application settings."""
        try:
            settings = QSettings(SettingsOperations.APP_NAME, SettingsOperations.APP_ORGANIZATION)
            
            # Window geometry and state
            geometry = settings.value("geometry")
            if geometry:
                main_window.restoreGeometry(geometry)
                
            window_state = settings.value("windowState")
            if window_state:
                main_window.restoreState(window_state)
                
            # Last used directory
            last_dir = settings.value("lastDirectory")
            if last_dir and os.path.isdir(last_dir):
                main_window.default_directory = last_dir
                
            # History size
            history_size = settings.value("historySize", 50, type=int)
            if history_size > 0:
                main_window.max_history_size = history_size
                
            
            # Auto-center toggle state
            main_window.auto_center_enabled = settings.value("view/autoCenterOnFrameChange", False, type=bool)

        except Exception as e:
            print(f"Error loading settings: {e}")
            # Use defaults if settings can't be loaded
            
    @staticmethod
    def save_settings(main_window):
        """Save application settings on exit."""
        try:
            settings = QSettings(SettingsOperations.APP_NAME, SettingsOperations.APP_ORGANIZATION)
            
            # Window geometry and state
            settings.setValue("geometry", main_window.saveGeometry())
            settings.setValue("windowState", main_window.saveState())
            
            # Last used directory
            settings.setValue("lastDirectory", main_window.default_directory)
            
            # History size
            settings.setValue("historySize", main_window.max_history_size)
            
            
            # Auto-center toggle state
            settings.setValue("view/autoCenterOnFrameChange", getattr(main_window, 'auto_center_enabled', False))

        except Exception as e:
            print(f"Error saving settings: {e}")
            
    @staticmethod
    def handle_close_event(main_window, event):
        """Handle window close event."""
        # Save settings before closing
        SettingsOperations.save_settings(main_window)
        # Accept the close event
        event.accept()
