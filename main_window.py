#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main Window for 3DE4 Curve Editor.

This module contains the MainWindow class which serves as the main entry point
for the Curve Editor application. It initializes the UI components, creates the
main application window, and manages the application lifecycle.

Key architecture principles:
1. Separation of UI components into the UIComponents class
2. Centralized signal connections managed through UIComponents.connect_all_signals
3. Operation-specific logic in dedicated utility classes:
   - CurveViewOperations - For curve view manipulation
   - VisualizationOperations - For visualization features
   - ImageOperations - For image sequence handling
   - DialogOperations - For dialog management
   - CurveOperations - For curve data manipulation

This architecture ensures:
- Clear separation of concerns
- Improved code organization and maintainability
- Consistent signal connection patterns
- Better error handling and defensive programming
"""

import os
import sys
import math
import copy
import re

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox, QSlider, QLineEdit,
    QGroupBox, QSplitter, QDialog, QComboBox, QToolBar, QMenu,
    QGridLayout, QApplication, QStatusBar
)
from PySide6.QtCore import (
    Qt, QTimer, QSettings, QSize, QPoint, Signal, QEvent
)
from PySide6.QtGui import (
    QFont, QKeySequence, QAction, QShortcut
)

from curve_view import CurveView
from dialogs import (SmoothingDialog, FilterDialog, FillGapsDialog, 
                     ExtrapolateDialog, ProblemDetectionDialog)
from curve_operations import CurveOperations
from file_operations import FileOperations
from image_operations import ImageOperations
import utils
import config
from visualization_operations import VisualizationOperations
from dialog_operations import DialogOperations
from settings_operations import SettingsOperations
from curve_view_operations import CurveViewOperations
from enhanced_curve_view import EnhancedCurveView
from keyboard_shortcuts import ShortcutManager
from ui_components import UIComponents
from history_operations import HistoryOperations
from track_quality import TrackQualityAnalyzer, TrackQualityUI
import csv_export
import batch_edit
import quick_filter_presets as presets

# Import the separated modules
from menu_bar import MenuBar


class MainWindow(QMainWindow):
    """Main application window for 3DE4 Curve Editor.
    
    This class implements the main window of the curve editor application,
    providing a UI for editing and analyzing 2D tracking data. It uses a 
    utility-class based architecture where most functionality is delegated
    to specialized utility classes:
    
    - CurveViewOperations: Operations related to the curve view (point selection, editing)
    - VisualizationOperations: Operations for visualization (toggles, visual settings)
    - FileOperations: File handling (loading, saving tracks)
    - ImageOperations: Image sequence handling
    - DialogOperations: Management of various dialogs
    - SettingsOperations: Application settings management
    - UIComponents: Common UI operations
    - HistoryOperations: Undo/redo functionality
    - CurveOperations: Mathematical operations on curves
    
    This architecture reduces code duplication and improves maintainability
    by centralizing specific functionality in dedicated utility classes.
    
    Attributes:
        curve_data (list): List of tracking points in format [(frame, x, y), ...]
        point_name (str): Name of the current tracking point
        point_color (int): Color ID for the tracking point
        image_width (int): Width of the background image/workspace
        image_height (int): Height of the background image/workspace
        curve_view (CurveView): The main curve editing view
        default_directory (str): Default directory for file operations
        image_sequence_path (str): Path to the loaded image sequence
        image_filenames (list): List of image filenames in the sequence
        current_frame (int): Current frame number in the timeline
        history (list): Undo/redo history stack
        history_index (int): Current position in the history stack
    """
    
    def __init__(self):
        """Initialize the main window."""
        super(MainWindow, self).__init__()
        
        self.setWindowTitle("3DE4 2D Curve Editor")
        # Set a nice default size
        self.resize(1200, 800)
        
        # Data storage
        self.curve_data = []
        self.point_name = ""
        self.point_color = 0
        self.image_width = 1920
        self.image_height = 1080
        
        # Set the curve view class
        self.curve_view_class = CurveView
        
        # Default directory for 3DE points
        self.default_directory = "/home/gabriel-ha/3DEpoints"
        if not os.path.exists(self.default_directory):
            # Fallback to home directory if the specified path doesn't exist
            self.default_directory = os.path.expanduser("~")
            
        # Image sequence
        self.image_sequence_path = ""
        self.image_filenames = []
            
        # Selection and editing state
        self.selected_indices = []
        self.current_frame = 0
        
        # History for undo/redo
        self.history = []
        self.history_index = -1
        self.max_history_size = 50
        
        # Initialize the supporting modules
        # Note: FileOperations, ImageOperations, and UIComponents use static methods
        # and don't need to be instantiated
        
        # Track quality analyzer
        self.quality_ui = TrackQualityUI(self)
        
        # Init UI
        self.setup_ui()
        SettingsOperations.load_settings(self)  # Use the utility class
        
        # Install event filter for key navigation
        self.installEventFilter(self)
        
        # Set up keyboard shortcuts
        self.shortcuts = {}
        ShortcutManager.setup_shortcuts(self)
        self.connect_shortcuts()
        
        # First create view and timeline with standard curve view
        # This ensures we have a valid curve_view_container
        
        # Then try to integrate enhanced curve view if possible
        try:
            # Use the UIComponents centralized method for setting up enhanced curve view
            success = UIComponents.setup_enhanced_curve_view(self)
            if success:
                print("Enhanced curve view loaded successfully")
            else:
                print("Failed to initialize enhanced curve view")
        except Exception as e:
            print(f"Error loading enhanced curve view: {str(e)}")
            print("Using standard curve view")
            
        # Load previously used file if it exists
        self.load_previous_file()
        
        # Initialize batch editing UI
        self.batch_edit_ui = batch_edit.BatchEditUI(self)
        self.batch_edit_ui.setup_batch_editing_ui()
        
        # Use the SignalRegistry instead of UIComponents.connect_all_signals
        from signal_registry import SignalRegistry
        SignalRegistry.connect_main_signals(self)
    
    def setup_ui(self):
        """Create and arrange UI elements."""
        # Create menu bar
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Create toolbar
        toolbar_widget = UIComponents.create_toolbar(self)
        main_layout.addWidget(toolbar_widget)
        
        # Create splitter for main view and controls
        splitter = QSplitter(Qt.Vertical)
        
        # Create curve view and timeline with individual frames
        view_container = UIComponents.create_view_and_timeline(self)
        splitter.addWidget(view_container)
        
        # Create control panel
        controls_widget = UIComponents.create_control_panel(self)
        splitter.addWidget(controls_widget)
        
        # Set relative sizes
        splitter.setSizes([600, 200])
        
        main_layout.addWidget(splitter)
        
        self.setCentralWidget(main_widget)
        
        # Set up status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")
        
    def create_toolbar(self):
        """Create the toolbar with action buttons.
        
        Sets up the main toolbar with buttons for common operations:
        - Load/save/add track data
        - Load image sequence
        - Tool operations (smoothing, filtering, etc.)
        
        All button actions are connected directly to operations in utility classes
        where appropriate, avoiding redundant wrapper methods.
        """
        return UIComponents.create_toolbar(self)
        
    def create_view_and_timeline(self):
        """Create the curve view widget and timeline controls.
        
        Sets up:
        1. The CurveView widget for visualizing and editing tracking data
        2. Timeline slider and controls for frame navigation
        3. Playback controls for animation
        
        Timeline and playback controls are connected directly to UIComponents methods.
        """
        # Create the view container using UIComponents
        view_container = UIComponents.create_view_and_timeline(self)
        
        # All signals are now connected in the UIComponents class
        # No need for duplicate connections here
        
        return view_container

    def create_control_panel(self):
        """Create the control panel for point editing.
        
        Sets up the right-side panel with:
        1. Point information display (coordinates, frame)
        2. Point editing controls (selection, deletion)
        3. View controls (background, opacity)
        4. Quick filter presets
        5. Track quality analysis panel
        
        Operations are connected directly to utility class methods where appropriate.
        """
        controls_widget = UIComponents.create_control_panel(self)
        
        # Disable controls initially
        self.enable_point_controls(False)
        
        return controls_widget

    def enable_point_controls(self, enabled):
        """Enable or disable point editing controls.
        
        Args:
            enabled (bool): Whether to enable or disable controls
            
        Enables or disables the point editing controls based on whether
        there is tracking data loaded and available for editing.
        """
        self.x_edit.setEnabled(enabled)
        self.y_edit.setEnabled(enabled)
        self.update_point_button.setEnabled(enabled)

    def keyPressEvent(self, event):
        """Enhanced key handling for frame-by-frame timeline navigation."""
        # Call the base event filter first for standard shortcuts
        result = super(MainWindow, self).keyPressEvent(event)
        
        # Add extra frame navigation shortcuts
        if event.key() == Qt.Key_Period:  # Period key for next frame
            UIComponents.next_frame(self)
            return True
        elif event.key() == Qt.Key_Comma:  # Comma key for previous frame
            UIComponents.prev_frame(self)
            return True
        elif event.key() == Qt.Key_Home:  # Home key for first frame
            UIComponents.go_to_first_frame(self)
            return True
        elif event.key() == Qt.Key_End:  # End key for last frame
            UIComponents.go_to_last_frame(self)
            return True
        elif event.key() == Qt.Key_Shift and (event.key() == Qt.Key_Period):  # Shift+Period for 10 frames forward
            UIComponents.advance_frames(self, 10)
            return True
        elif event.key() == Qt.Key_Shift and (event.key() == Qt.Key_Comma):  # Shift+Comma for 10 frames backward
            UIComponents.advance_frames(self, -10)
            return True
        
        return result

    def eventFilter(self, obj, event):
        """Global event filter for keyboard navigation.
        
        Args:
            obj: The object that generated the event
            event: The event that was generated
            
        Returns:
            bool: True if the event was handled, False otherwise
            
        Handles keyboard navigation (shortcuts not in menus) and delegates
        many visual operations to the VisualizationOperations utility class.
        """
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Left:
                # Previous image
                ImageOperations.previous_image(self)
                return True
            elif event.key() == Qt.Key_Right:
                # Next image
                ImageOperations.next_image(self)
                return True
            elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
                # Delete selected points
                CurveViewOperations.delete_selected_points(self)
                return True
            elif event.key() == Qt.Key_C:
                # Center on selected point
                VisualizationOperations.center_on_selected_point_from_main_window(self)
                return True
            elif event.key() == Qt.Key_G:
                # Toggle grid
                checked = not self.toggle_grid_button.isChecked()
                self.toggle_grid_button.setChecked(checked)
                VisualizationOperations.toggle_grid(self, checked)
                return True
            elif event.key() == Qt.Key_V:
                # Toggle velocity vectors
                checked = not self.toggle_vectors_button.isChecked()
                self.toggle_vectors_button.setChecked(checked)
                VisualizationOperations.toggle_velocity_vectors(self, checked)
                return True
            elif event.key() == Qt.Key_F:
                # Toggle frame numbers
                checked = not self.toggle_frame_numbers_button.isChecked()
                self.toggle_frame_numbers_button.setChecked(checked)
                VisualizationOperations.toggle_all_frame_numbers(self, checked)
                return True
                
        return super(MainWindow, self).eventFilter(obj, event)
    
    # File Operations
    def load_track_data(self):
        """Load 2D track data from a file."""
        FileOperations.load_track_data(self)

    def add_track_data(self):
        """Add an additional 2D track to the current data."""
        FileOperations.add_track_data(self)

    def save_track_data(self):
        """Save modified 2D track data to a file."""
        FileOperations.save_track_data(self)
    
    # Image Sequence Operations
    def load_image_sequence(self):
        """Load an image sequence to use as background."""
        ImageOperations.load_image_sequence(self)

    def update_image_label(self):
        """Update the image label with current image info."""
        ImageOperations.update_image_label(self)

    def on_image_changed(self, index):
        """
        Handle image changes with improved reliability.
        
        This method is called when the image is changed through user interaction
        or programmatically. It updates the timeline position, frame display,
        and point selection to match the current image.
        
        Args:
            index: Index of the new current image in image_filenames list
        """
        try:
            # Validate index and image filenames
            if not hasattr(self, 'image_filenames') or not self.image_filenames:
                return
            if index < 0 or index >= len(self.image_filenames):
                return

            # Extract frame number using regex for reliability
            import re
            filename = os.path.basename(self.image_filenames[index])
            frame_match = re.search(r'(\d+)', filename)
            if not frame_match:
                return
            frame_num = int(frame_match.group(1))
            
            # Update timeline with signal blocking to prevent recursion
            if hasattr(self, 'timeline_slider'):
                self.timeline_slider.blockSignals(True)
                self.timeline_slider.setValue(frame_num)
                self.timeline_slider.blockSignals(False)
            
            # Update frame display consistently
            if hasattr(self, 'frame_label'):
                self.frame_label.setText(f"Frame: {frame_num}")
            if hasattr(self, 'frame_edit'):
                self.frame_edit.setText(str(frame_num))
            
            # Find and select closest point
            self._select_point_for_frame(frame_num)
            
            # Update frame marker position if available
            if hasattr(self, 'frame_marker'):
                UIComponents.update_frame_marker(self)
        
        except Exception as e:
            print(f"Error handling image change: {str(e)}")
            import traceback
            traceback.print_exc()

    def _select_point_for_frame(self, frame_num):
        """
        Helper to select the point closest to a frame number.
        
        Args:
            frame_num: Target frame number to find the closest point for
        """
        if not self.curve_data:
            return
        
        # Find closest point by frame number
        closest_idx = -1
        min_distance = float('inf')
        
        for i, point in enumerate(self.curve_data):
            distance = abs(point[0] - frame_num)
            if distance < min_distance:
                min_distance = distance
                closest_idx = i
        
        # Update selection if found
        if closest_idx >= 0:
            # Use curve_view operations for consistency
            from curve_view_operations import CurveViewOperations
            CurveViewOperations.select_point_by_index(self.curve_view, closest_idx)
    
    def load_previous_file(self):
        """Load the previously used file and folder if they exist."""
        # Check for last folder path and update default directory
        folder_path = config.get_last_folder_path()
        if folder_path and os.path.exists(folder_path):
            self.default_directory = folder_path
            
        # Load last file if it exists
        file_path = config.get_last_file_path()
        if file_path and os.path.exists(file_path):
            # Load track data from file
            point_name, point_color, num_frames, curve_data = utils.load_3de_track(file_path)
            
            if curve_data:
                # Set the data
                self.point_name = point_name
                self.point_color = point_color
                self.curve_data = curve_data
                
                # Determine image dimensions from the data
                self.image_width, self.image_height = utils.estimate_image_dimensions(curve_data)
                
                # Update view
                self.curve_view.setPoints(self.curve_data, self.image_width, self.image_height)
                
                # Enable controls
                self.save_button.setEnabled(True)
                self.add_point_button.setEnabled(True)
                self.smooth_button.setEnabled(True)
                self.fill_gaps_button.setEnabled(True)
                self.filter_button.setEnabled(True)
                self.detect_problems_button.setEnabled(True)
                self.extrapolate_button.setEnabled(True)
                
                # Update info
                self.info_label.setText(f"Loaded: {self.point_name} ({len(self.curve_data)} frames)")
                
                # Setup timeline
                self.setup_timeline()
                
                # Enable timeline controls
                self.timeline_slider.setEnabled(True)
                self.frame_edit.setEnabled(True)
                self.go_button.setEnabled(True)
                
                # Add to history
                self.add_to_history()
        
        # Load last image sequence if it exists
        self.load_previous_image_sequence()
    
    def load_previous_image_sequence(self):
        """Load the previously used image sequence if it exists."""
        # Check for last image sequence path
        sequence_path = config.get_last_image_sequence_path()
        if sequence_path and os.path.exists(sequence_path):
            # Find all image files in the directory
            image_files = utils.get_image_files(sequence_path)
            
            if image_files:
                # Set the image sequence
                self.image_sequence_path = sequence_path
                self.image_filenames = image_files
                
                # Setup the curve view with images
                self.curve_view.setImageSequence(sequence_path, image_files)
                
                # Update the UI
                self.update_image_label()
                self.toggle_bg_button.setEnabled(True)
                self.opacity_slider.setEnabled(True)

    # Timeline Operations
    def setup_timeline(self):
        """Setup timeline slider based on frame range."""
        UIComponents.setup_timeline(self)

    # Point Editing Operations
    def on_point_selected(self, idx):
        """Handle point selection in the view."""
        CurveViewOperations.on_point_selected(self, idx)

    def on_point_moved(self, idx, x, y):
        """Handle point moved in the view."""
        CurveViewOperations.on_point_moved(self, idx, x, y)

    def connect_shortcuts(self):
        """Connect keyboard shortcuts to actions."""
        # File operations
        ShortcutManager.connect_shortcut(self, "open_file", self.load_track_data)
        ShortcutManager.connect_shortcut(self, "save_file", self.save_track_data)
        ShortcutManager.connect_shortcut(self, "export_csv", lambda: FileOperations.export_to_csv(self))
        ShortcutManager.connect_shortcut(self, "export_excel", lambda: FileOperations.export_to_excel(self))
        
        # Edit operations
        ShortcutManager.connect_shortcut(self, "undo", self.undo_action)
        ShortcutManager.connect_shortcut(self, "redo", self.redo_action)
        ShortcutManager.connect_shortcut(self, "select_all", lambda: CurveViewOperations.select_all_points(self.curve_view))
        ShortcutManager.connect_shortcut(self, "deselect_all", lambda: CurveViewOperations.deselect_all_points(self.curve_view))
        ShortcutManager.connect_shortcut(self, "delete_selected", lambda: CurveViewOperations.delete_selected_points(self))
        ShortcutManager.connect_shortcut(self, "delete_selected_alt", lambda: CurveViewOperations.delete_selected_points(self))
        
        # View operations - FIXED
        ShortcutManager.connect_shortcut(self, "reset_view", lambda: CurveViewOperations.reset_view(self.curve_view))
        ShortcutManager.connect_shortcut(self, "toggle_grid", lambda: VisualizationOperations.toggle_grid(self, not self.toggle_grid_button.isChecked()))
        ShortcutManager.connect_shortcut(self, "toggle_velocity", lambda: VisualizationOperations.toggle_velocity_vectors(self, not self.toggle_vectors_button.isChecked()))
        ShortcutManager.connect_shortcut(self, "toggle_frame_numbers", lambda: VisualizationOperations.toggle_all_frame_numbers(self, not self.toggle_frame_numbers_button.isChecked()))
        
        # FIXED: Use center_on_selected_point_from_main_window instead of center_on_selected_point
        ShortcutManager.connect_shortcut(self, "center_on_point", lambda: VisualizationOperations.center_on_selected_point_from_main_window(self))
        
        ShortcutManager.connect_shortcut(self, "toggle_background", lambda: ImageOperations.toggle_background(self))
        ShortcutManager.connect_shortcut(self, "toggle_fullscreen", lambda: VisualizationOperations.toggle_fullscreen(self))
        
        # FIXED: Use VisualizationOperations.zoom_view instead of CurveViewOperations.zoom_in/out
        ShortcutManager.connect_shortcut(self, "zoom_in", lambda: VisualizationOperations.zoom_view(self.curve_view, 1.1))
        ShortcutManager.connect_shortcut(self, "zoom_out", lambda: VisualizationOperations.zoom_view(self.curve_view, 0.9))
        
        # Timeline operations
        ShortcutManager.connect_shortcut(self, "next_frame", lambda: UIComponents.next_frame(self))
        ShortcutManager.connect_shortcut(self, "prev_frame", lambda: UIComponents.prev_frame(self))
        ShortcutManager.connect_shortcut(self, "play_pause", lambda: UIComponents.toggle_playback(self))
        ShortcutManager.connect_shortcut(self, "first_frame", lambda: UIComponents.go_to_first_frame(self))
        ShortcutManager.connect_shortcut(self, "last_frame", lambda: UIComponents.go_to_last_frame(self))
        
        # Enhanced frame navigation shortcuts
        frame_advance_shortcuts = {
            "forward_10": {"key": "Shift+.", "func": lambda: UIComponents.advance_frames(self, 10)},
            "backward_10": {"key": "Shift+,", "func": lambda: UIComponents.advance_frames(self, -10)},
        }
        
        for shortcut_id, data in frame_advance_shortcuts.items():
            shortcut = QShortcut(QKeySequence(data["key"]), self)
            shortcut.activated.connect(data["func"])
        
        # Navigation
        ShortcutManager.connect_shortcut(self, "next_image", lambda: ImageOperations.next_image(self))
        ShortcutManager.connect_shortcut(self, "prev_image", lambda: ImageOperations.previous_image(self))
        
        # Tools
        ShortcutManager.connect_shortcut(self, "smooth_selected", lambda: DialogOperations.show_smooth_dialog(self))
        ShortcutManager.connect_shortcut(self, "filter_selected", lambda: DialogOperations.show_filter_dialog(self))
        ShortcutManager.connect_shortcut(self, "fill_gaps", lambda: DialogOperations.show_fill_gaps_dialog(self))
        ShortcutManager.connect_shortcut(self, "extrapolate", lambda: DialogOperations.show_extrapolate_dialog(self))
        ShortcutManager.connect_shortcut(self, "detect_problems", lambda: DialogOperations.show_problem_detection_dialog(self, CurveOperations.detect_problems(self)))
        ShortcutManager.connect_shortcut(self, "show_shortcuts", lambda: DialogOperations.show_shortcuts_dialog(self))

    def show_shortcuts_dialog(self):
        """Show dialog with keyboard shortcuts."""
        DialogOperations.show_shortcuts_dialog(self)

    def update_point_info(self, idx, x, y):
        """Update the point information panel."""
        CurveViewOperations.update_point_info(self, idx, x, y)

    # History Operations
    def add_to_history(self):
        """Add current state to history."""
        HistoryOperations.add_to_history(self)
            
    def update_history_buttons(self):
        """Update the state of undo/redo buttons."""
        HistoryOperations.update_history_buttons(self)

    def undo_action(self):
        """Undo the last action."""
        HistoryOperations.undo_action(self)

    def redo_action(self):
        """Redo the previously undone action."""
        HistoryOperations.redo_action(self)

    def restore_state(self, state):
        """Restore application state from history."""
        HistoryOperations.restore_state(self, state)

    # Quality Check Operations
    def check_tracking_quality(self):
        """Run quality checks on the tracking data."""
        if not self.curve_data:
            return
            
        # Initialize quality UI if not already done
        if not hasattr(self, 'quality_ui'):
            self.quality_ui = TrackQualityUI(self)
            
        # Run analysis
        self.quality_ui.analyze_and_update_ui(self.curve_data)

    # Dialog Operations
    def show_smooth_dialog(self):
        DialogOperations.show_smooth_dialog(self)

    def show_filter_dialog(self):
        DialogOperations.show_filter_dialog(self)

    def show_fill_gaps_dialog(self):
        DialogOperations.show_fill_gaps_dialog(self)

    def fill_gap(self, start_frame, end_frame, method, preserve_endpoints=True):
        DialogOperations.fill_gap(self, start_frame, end_frame, method, preserve_endpoints)

    def show_extrapolate_dialog(self):
        DialogOperations.show_extrapolate_dialog(self)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())