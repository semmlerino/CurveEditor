#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
State Manager for 3DE4 Curve Editor.

This module contains the StateManager class which provides centralized state
management with proper data flow patterns. It eliminates the need for sync
methods and provides a single source of truth for application state.
"""

# Standard library imports
from typing import TYPE_CHECKING, Any, Dict, List

# Import protocols and types
from core.protocols import PointsList

# Import local modules
from application_state import ApplicationState
from services.logging_service import LoggingService

if TYPE_CHECKING:
    from main_window import MainWindow

# Configure logger for this module
logger = LoggingService.get_logger("state_manager")


class StateManager:
    """
    State Manager for centralized application state management.
    
    This class provides a single source of truth for application state
    and eliminates the need for sync methods between MainWindow and
    ApplicationState.
    """
    
    def __init__(self, main_window: 'MainWindow') -> None:
        """Initialize the state manager with reference to main window."""
        self.main_window = main_window
        self.state = ApplicationState()
        
    def initialize_protocol_compliance(self) -> None:
        """Initialize MainWindow to comply with TrackQualityUIProtocol.
        
        This method sets up direct attribute access to state data, providing
        a simpler and more reliable approach than dynamic properties.
        """
        # Set up direct attribute access to state data
        self._setup_direct_attributes()
        
    def _setup_direct_attributes(self) -> None:
        """Set up direct attribute access to state data."""
        # Create direct references to state attributes for protocol compliance
        # This approach is simpler and more reliable than dynamic properties
        
        # Track data attributes
        self.main_window.image_sequence_path = self.state.image_sequence_path
        self.main_window.image_filenames = self.state.image_filenames
        self.main_window.curve_data = self.state.curve_data
        self.main_window.point_name = self.state.point_name
        self.main_window.point_color = self.state.point_color
        self.main_window.track_data_loaded = self.state.track_data_loaded
        
        # History attributes
        self.main_window.history = self.state.history
        self.main_window.history_index = self.state.history_index
        self.main_window.max_history_size = self.state.max_history_size
        
        # Other attributes
        self.main_window.image_width = self.state.image_width
        self.main_window.image_height = self.state.image_height
        self.main_window.default_directory = self.state.default_directory
        self.main_window.last_opened_file = self.state.last_opened_file
        self.main_window.selected_indices = self.state.selected_indices
        self.main_window.current_frame = self.state.current_frame
        self.main_window.auto_center_enabled = self.state.auto_center_enabled
        
    def sync_attributes_to_state(self) -> None:
        """Sync MainWindow attributes back to state when needed."""
        # This method can be called when we need to ensure state is up to date
        # from MainWindow attributes (for backward compatibility)
        if hasattr(self.main_window, 'curve_data'):
            self.state.curve_data = self.main_window.curve_data
        if hasattr(self.main_window, 'image_sequence_path'):
            self.state.image_sequence_path = self.main_window.image_sequence_path
        if hasattr(self.main_window, 'image_filenames'):
            self.state.image_filenames = self.main_window.image_filenames
        if hasattr(self.main_window, 'track_data_loaded'):
            self.state.track_data_loaded = self.main_window.track_data_loaded
        if hasattr(self.main_window, 'auto_center_enabled'):
            self.state.auto_center_enabled = self.main_window.auto_center_enabled
        
    def get_state_dict(self) -> Dict[str, Any]:
        """Get a dictionary representation of the current state."""
        return self.state.get_state_dict()
        
    def restore_from_dict(self, state_dict: Dict[str, Any]) -> None:
        """Restore state from a dictionary."""
        self.state.restore_from_dict(state_dict)
        
    def reset(self) -> None:
        """Reset all state to default values."""
        self.state.reset()
        
        # Update status using centralized StatusManager
        from services.status_manager import StatusManager
        StatusManager.on_data_cleared(self.main_window)
        
    # Convenience methods for common state operations
    def update_curve_data(self, curve_data: PointsList) -> None:
        """Update curve data and related state."""
        self.state.curve_data = curve_data
        logger.debug(f"Updated curve data with {len(curve_data)} points")
        
        # Update status using centralized StatusManager
        from services.status_manager import StatusManager
        StatusManager.on_curve_data_loaded(self.main_window)
        
    def update_image_sequence(self, path: str, filenames: List[str]) -> None:
        """Update image sequence information."""
        self.state.image_sequence_path = path
        self.state.image_filenames = filenames
        logger.debug(f"Updated image sequence: {path} with {len(filenames)} files")
        
    def update_selection(self, indices: List[int]) -> None:
        """Update selected point indices."""
        self.state.selected_indices = indices
        logger.debug(f"Updated selection: {len(indices)} points selected")
        
    def update_current_frame(self, frame: int) -> None:
        """Update current frame."""
        self.state.current_frame = frame
        logger.debug(f"Updated current frame to: {frame}")
        
    def is_data_loaded(self) -> bool:
        """Check if track data is loaded."""
        return self.state.track_data_loaded
        
    def mark_data_loaded(self, loaded: bool = True) -> None:
        """Mark track data as loaded or unloaded."""
        self.state.track_data_loaded = loaded
        logger.debug(f"Track data loaded state: {loaded}")