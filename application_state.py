#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Application State Management for Curve Editor.

This module manages the application state variables that were previously
stored directly in MainWindow, helping to reduce the MainWindow class size
and improve separation of concerns.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from services.protocols import PointsList

logger = logging.getLogger(__name__)

# Constants
DEFAULT_POINT_COLOR = "#FF0000"  # Default red color for points
DEFAULT_IMAGE_WIDTH = 1920
DEFAULT_IMAGE_HEIGHT = 1080
MAX_HISTORY_SIZE = 50


class ApplicationState:
    """Manages application state variables."""

    def __init__(self):
        """Initialize application state with default values."""
        # Track data state
        self.curve_data: PointsList = []
        self.point_name: str = "Default"
        self.point_color: str = DEFAULT_POINT_COLOR
        self.track_data_loaded: bool = False
        self._track_data_loaded: bool = False

        # Image sequence state
        self.image_sequence_path: str = ""
        self.image_filenames: List[str] = []
        self.image_width: int = DEFAULT_IMAGE_WIDTH
        self.image_height: int = DEFAULT_IMAGE_HEIGHT

        # History state
        self.history: List[Dict[str, Any]] = []
        self.history_index: int = -1
        self.max_history_size: int = MAX_HISTORY_SIZE

        # Selection and editing state
        self.selected_indices: List[int] = []
        self.current_frame: int = 0

        # View state
        self.auto_center_enabled: bool = False

        # File management state
        self.default_directory: str = self._get_default_directory()
        self.last_opened_file: str = ""

    def _get_default_directory(self) -> str:
        """Determine the default directory for 3DE points files."""
        home_dir = os.path.expanduser("~")
        possible_dirs = [
            os.path.join(home_dir, "3DEpoints"),
            os.path.join(home_dir, "Documents", "3DEpoints"),
            os.path.join(home_dir, "Documents"),
            home_dir
        ]

        for directory in possible_dirs:
            if os.path.exists(directory):
                logger.info(f"Using default directory: {directory}")
                return directory

        logger.info(f"Using home directory as default: {home_dir}")
        return home_dir

    def reset(self):
        """Reset all state to default values."""
        self.__init__()

    def get_state_dict(self) -> Dict[str, Any]:
        """Get a dictionary representation of the current state.

        Returns:
            Dictionary containing all state variables
        """
        return {
            'curve_data': self.curve_data,
            'point_name': self.point_name,
            'point_color': self.point_color,
            'track_data_loaded': self.track_data_loaded,
            'image_sequence_path': self.image_sequence_path,
            'image_filenames': self.image_filenames,
            'image_width': self.image_width,
            'image_height': self.image_height,
            'selected_indices': self.selected_indices,
            'current_frame': self.current_frame,
            'auto_center_enabled': self.auto_center_enabled,
            'last_opened_file': self.last_opened_file
        }

    def restore_from_dict(self, state_dict: Dict[str, Any]):
        """Restore state from a dictionary.

        Args:
            state_dict: Dictionary containing state variables
        """
        for key, value in state_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
