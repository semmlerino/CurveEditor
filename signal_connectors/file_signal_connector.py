#!/usr/bin/env python

"""
File operations signal connector for CurveEditor.

This module handles all signal connections related to file operations including
loading, saving, adding, and exporting track data.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main_window import MainWindow
    from signal_registry import RegistryConnector

from services.file_service import FileService


class FileSignalConnector:
    """Handles signal connections for file operations."""

    @staticmethod
    def connect_signals(main_window: "MainWindow", registry: "RegistryConnector") -> None:
        """Connect all file operation related signals.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        FileSignalConnector._connect_load_save_signals(main_window, registry)
        FileSignalConnector._connect_export_signals(main_window, registry)

    @staticmethod
    def _connect_load_save_signals(main_window: Any, registry: Any) -> None:
        """Connect load, save, and add file operation signals.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        # Load button - REMOVED to avoid duplicate file dialog
        # The menu bar already connects to FileOperations.load_track_data
        # if hasattr(main_window, 'load_button'):
        #     registry._connect_signal(
        #         main_window,
        #         main_window.load_button.clicked,
        #         lambda: FileService.load_track_data(main_window),
        #         "load_button.clicked"
        #     )

        # Save button
        if hasattr(main_window, "save_button"):
            registry._connect_signal(
                main_window,
                main_window.save_button.clicked,
                lambda: FileService.save_track_data(main_window),
                "save_button.clicked",
            )

        # Add point button (file operation related)
        if hasattr(main_window, "add_point_button"):
            registry._connect_signal(
                main_window,
                main_window.add_point_button.clicked,
                lambda: FileService.add_track_data(main_window),
                "add_point_button.clicked",
            )

    @staticmethod
    def _connect_export_signals(main_window: Any, registry: Any) -> None:
        """Connect export related signals.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        # Export signals will be connected here if needed in the future
        pass
