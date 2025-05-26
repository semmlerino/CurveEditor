#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File operations signal connector for CurveEditor.

This module handles all signal connections related to file operations including
loading, saving, adding, and exporting track data.
"""

from typing import Any

from services.file_service import FileService as FileOperations


class FileSignalConnector:
    """Handles signal connections for file operations."""

    @staticmethod
    def connect_signals(main_window: Any, registry: Any) -> None:
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
        # Load button
        if hasattr(main_window, 'load_button'):
            registry._connect_signal(
                main_window,
                main_window.load_button.clicked,
                lambda: FileOperations.load_track_data(main_window),
                "load_button.clicked"
            )

        # Save button
        if hasattr(main_window, 'save_button'):
            registry._connect_signal(
                main_window,
                main_window.save_button.clicked,
                lambda: FileOperations.save_track_data(main_window),
                "save_button.clicked"
            )

        # Add point button (file operation related)
        if hasattr(main_window, 'add_point_button'):
            registry._connect_signal(
                main_window,
                main_window.add_point_button.clicked,
                lambda: FileOperations.add_track_data(main_window),
                "add_point_button.clicked"
            )

    @staticmethod
    def _connect_export_signals(main_window: Any, registry: Any) -> None:
        """Connect export related signals.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        # Export CSV button
        if hasattr(main_window, 'export_csv_button'):
            registry._connect_signal(
                main_window,
                main_window.export_csv_button.clicked,
                lambda: FileOperations.export_to_csv(main_window),
                "export_csv_button.clicked"
            )
