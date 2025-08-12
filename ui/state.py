#!/usr/bin/env python
"""Simple application state management."""

import os
import logging

logger = logging.getLogger("state")

class ApplicationState:
    """Single consolidated state container for the application."""
    
    def __init__(self):
        """Initialize application state."""
        # Track data
        self.curve_data = []
        self.point_name = "Default"
        self.point_color = "#FF0000"
        
        # Image data
        self.image_width = 1920
        self.image_height = 1080
        self.image_sequence_path = ""
        self.image_filenames = []
        
        # File paths
        self.current_file = None
        self.last_save_dir = os.path.expanduser("~")
        self.last_load_dir = os.path.expanduser("~")
        
        # UI state
        self.unsaved_changes = False
        self.ui_update_pending = False
        
        # Services (will be set by MainWindow)
        self.curve_view = None
        self.track_quality_ui = None
        
    def mark_changed(self):
        """Mark that data has changed."""
        self.unsaved_changes = True
        
    def mark_saved(self):
        """Mark that data has been saved."""
        self.unsaved_changes = False
        
    def reset(self):
        """Reset state to defaults."""
        self.curve_data = []
        self.current_file = None
        self.unsaved_changes = False