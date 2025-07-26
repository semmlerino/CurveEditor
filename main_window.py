#!/usr/bin/env python
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownParameterType=false
# -*- coding: utf-8 -*-

"""
Main Window for 3DE4 Curve Editor.

This module contains the MainWindow class which serves as the main entry point
for the Curve Editor application. It has been refactored to delegate most
functionality to specialized classes for better maintainability.

Key architecture components:
1. ApplicationState - Manages all application state variables
2. UIInitializer - Handles UI component initialization
3. MainWindowOperations - Contains operation methods
4. MainWindowDelegator - Delegates all operation calls
5. Service classes - Handle specific functionality
"""

# Standard library imports

import sys
from typing import Any, Optional, Dict, cast
from PySide6.QtGui import QShortcut

# Import PySide6 modules
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QApplication, QLabel, QStatusBar, QPushButton,
    QSlider, QLineEdit, QSpinBox
)
from PySide6.QtGui import QCloseEvent, QResizeEvent

# Import protocols and types
from core.protocols import TrackQualityUIProtocol, PointsList

# Import local modules
from curve_view import CurveView
from services.file_service import FileService
from services.image_service import ImageService
from services.settings_service import SettingsService
from services.unified_transformation_service import UnifiedTransformationService
from services.logging_service import LoggingService
from menu_bar import MenuBar
from ui_scaling import UIScaling
from keyboard_shortcuts import ShortcutManager
from track_quality import TrackQualityUI
from ui_components import UIComponents
from signal_registry import SignalRegistry

# Import refactored components
from application_state import ApplicationState
from ui_initializer import UIInitializer
from main_window_delegator import MainWindowDelegator

# Configure logger for this module
logger = LoggingService.get_logger("main_window")


class MainWindow(QMainWindow):
    """Main application window for the Curve Editor."""

    # Type annotation to indicate this class implements the TrackQualityUIProtocol interface
    _protocol_type: TrackQualityUIProtocol

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        # Explicit UI attributes for linting/type checking
        self.image_label: Optional[QLabel] = None
        self.status_bar: Optional[QStatusBar] = None
        self.save_button: Optional[QPushButton] = None
        self.add_point_button: Optional[QPushButton] = None
        self.smooth_button: Optional[QPushButton] = None
        self.fill_gaps_button: Optional[QPushButton] = None
        self.filter_button: Optional[QPushButton] = None
        self.detect_problems_button: Optional[QPushButton] = None
        self.extrapolate_button: Optional[QPushButton] = None
        self.timeline_slider: Optional[QSlider] = None
        self.frame_edit: Optional[QLineEdit] = None
        self.go_button: Optional[QPushButton] = None
        self.info_label: Optional[QLabel] = None
        self.prev_image_button: Optional[QPushButton] = None
        self.next_image_button: Optional[QPushButton] = None
        self.opacity_slider: Optional[QSlider] = None
        self.undo_button: Optional[QPushButton] = None
        self.redo_button: Optional[QPushButton] = None
        self.toggle_bg_button: Optional[QPushButton] = None
        self.update_point_button: Optional[QPushButton] = None
        self.type_edit: Optional[QLineEdit] = None
        self.point_size_spin: Optional[QSpinBox] = None
        self.x_edit: Optional[QLineEdit] = None
        self.y_edit: Optional[QLineEdit] = None
        # Add other UI attributes as needed for protocol/linting

        super().__init__(parent)
        
        # Apply theme-aware styling with proper DPI scaling
        UIScaling.apply_theme_stylesheet(self, "main_window")

        # Initialize application state
        self.state = ApplicationState()

        # Set protocol required attributes from state
        self._sync_protocol_attributes()

        # Initialize UI elements
        UIInitializer.initialize_ui_elements(self)

        # Initialize services
        self.file_service = FileService
        self.image_service = ImageService

        # Initialize delegator for operations
        self.delegator = MainWindowDelegator(self)

        # Initialize unified transformation system
        self._setup_transformation_system()

        # Initialize undo/redo actions
        UIInitializer.initialize_undo_redo_actions(self)

        # Set the curve view class
        self.curve_view_class = CurveView

        # Initialize track quality UI
        self.track_quality_ui = TrackQualityUI(self)  # type: ignore[arg-type]

        # Load settings first to get initial state
        SettingsService.load_settings(self)  # type: ignore[arg-type]

        # Init UI (which uses loaded settings)
        self.setup_ui()

        # Install event filter for key navigation
        self.installEventFilter(self)

        # Initialize curve view - REMOVED: curve view is already created in setup_ui()
        # self._initialize_curve_view()

        # Load previous file and image sequence
        self.load_previous_file()
        self.load_previous_image_sequence()
        self.update_image_label()

        # Setup keyboard shortcuts
        self.shortcuts: Dict[str, QShortcut] = {}
        ShortcutManager.setup_shortcuts(self)  # type: ignore

        # Connect all signals
        SignalRegistry.connect_all_signals(self)

        # Set initial state for auto-center toggle
        if hasattr(self.menu_bar, 'auto_center_action'):
            self.menu_bar.auto_center_action.setChecked(self.state.auto_center_enabled)

    def _sync_protocol_attributes(self):
        """Sync protocol required attributes with state."""
        # These attributes are required by TrackQualityUIProtocol
        self.image_sequence_path = self.state.image_sequence_path
        self.image_filenames = self.state.image_filenames
        self.curve_data = self.state.curve_data
        self.point_name = self.state.point_name
        self.point_color = self.state.point_color
        self.track_data_loaded = self.state.track_data_loaded

        # History attributes
        self.history = self.state.history
        self.history_index = self.state.history_index
        self.max_history_size = self.state.max_history_size

        # Other attributes
        self.image_width = self.state.image_width
        self.image_height = self.state.image_height
        self.default_directory = self.state.default_directory
        self.last_opened_file = self.state.last_opened_file
        self.selected_indices = self.state.selected_indices
        self.current_frame = self.state.current_frame
        self.auto_center_enabled = self.state.auto_center_enabled
        self.track_data_loaded = self.state.track_data_loaded

    def _sync_state_from_attributes(self):
        """Sync state from attributes (for backward compatibility)."""
        self.state.curve_data = self.curve_data
        self.state.image_sequence_path = self.image_sequence_path
        self.state.image_filenames = self.image_filenames
        self.state.track_data_loaded = self.track_data_loaded
        self.state.auto_center_enabled = self.auto_center_enabled

    def on_image_changed(self, index: int) -> None:
        """Slot called when the image is changed in the UI."""
        # You can expand this logic as needed
        print(f"Image changed to index: {index}")
        if hasattr(self, 'update_image_label'):
            self.update_image_label()

    def _setup_transformation_system(self):
        """Initialize the unified transformation system."""
        try:
            UnifiedTransformationService.clear_cache()
            logger.info("✅ Unified transformation system initialized")
        except (ImportError, AttributeError, RuntimeError) as e:
            logger.error(f"Failed to initialize transformation system: {e}")
            raise

    def _initialize_curve_view(self):
        """Initialize curve view with enhanced version if possible."""
        self.curve_view = CurveView(parent=self)  # type: ignore[assignment]

        try:
            success = UIComponents.create_enhanced_curve_view(self)
            if success:
                logger.info("Enhanced curve view loaded successfully")
                
                # Initialize nudge indicator with current values
                if hasattr(self, 'nudge_indicator') and hasattr(self.curve_view, 'nudge_increment'):
                    self.nudge_indicator.set_increment(
                        self.curve_view.nudge_increment,
                        self.curve_view.current_increment_index,
                        self.curve_view.available_increments
                    )
            else:
                logger.warning("Failed to initialize enhanced curve view")
        except (ImportError, AttributeError, TypeError, RuntimeError) as e:
            logger.error(f"Error loading enhanced curve view: {str(e)}")
            logger.info("Using standard curve view")

    def setup_ui(self) -> None:
        """Create and arrange UI elements."""
        UIComponents.setup_main_ui(self)

        # Create menu bar
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        # Expose auto-center action
        self.auto_center_action = self.menu_bar.auto_center_action
        
        # Adapt layout for current screen size
        UIComponents.adapt_layout_for_screen_size(self)

        logger.info("UI setup complete with unified transformation system and responsive layout")

    @property
    def qwidget(self) -> QWidget:
        """Return the underlying QWidget for this window."""
        return self
    
    @property
    def widget(self) -> QWidget:
        """Return the underlying QWidget for this window (alias for qwidget)."""
        return self

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        self._sync_state_from_attributes()
        SettingsService.handle_close_event(self, event)  # type: ignore[arg-type]
    
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle window resize event to maintain responsive layout."""
        super().resizeEvent(event)
        
        # Clear screen info cache to detect potential DPI changes
        UIScaling.clear_cache()
        
        # Get current layout mode
        layout_mode = UIScaling.get_layout_mode()
        
        # Adjust splitter proportions based on new size if splitter exists
        if hasattr(self, 'main_splitter') and self.main_splitter is not None:
            total_height = self.height()
            if total_height > 0:
                # Recalculate responsive minimums for new window size
                
                # Update curve view minimum if it exists
                if hasattr(self, 'curve_view_container') and self.curve_view_container is not None:
                    from ui_scaling import get_responsive_height
                    new_curve_min = get_responsive_height(0.6, 150, 400)
                    self.curve_view_container.setMinimumHeight(new_curve_min)
                
                # Adapt to layout mode for very small or very large screens
                if layout_mode == 'compact' and total_height < 600:
                    # On very small screens, reduce minimums further
                    logger.debug("Applying compact layout for small screen")
                elif layout_mode == 'spacious' and total_height > 1200:
                    # On large screens, allow more generous spacing
                    logger.debug("Applying spacious layout for large screen")
        
        logger.debug(f"Window resized to {event.size().width()}x{event.size().height()}, "
                    f"layout mode: {layout_mode}")

    def _select_point_for_frame(self, frame: int) -> None:
        """Select the point for the given frame."""
        # Implementation might be in another service
        pass

    def load_previous_file(self) -> None:
        """Load the previous file."""
        self.file_service.load_previous_file(self)  # type: ignore[arg-type]

    def load_previous_image_sequence(self) -> None:
        """Load the previous image sequence."""
        ImageService.load_previous_image_sequence(self)  # type: ignore[arg-type]

    # Quality check operations
    def check_tracking_quality(self):
        """Run quality checks on the tracking data."""
        if not self.curve_data:
            return

        if not hasattr(self, 'quality_ui'):
            self.quality_ui = TrackQualityUI(cast(TrackQualityUIProtocol, self))

        filtered_curve_data = [p for p in self.curve_data if len(p) == 3]
        points_list = cast(PointsList, filtered_curve_data)
        self.quality_ui.analyze_and_update_ui(points_list)

    # Delegate all operations to the delegator
    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the delegator.

        This allows the MainWindow to act as if it has all the methods
        that are actually implemented in MainWindowOperations.
        """
        if hasattr(self.delegator, name):
            return getattr(self.delegator, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
