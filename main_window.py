#!/usr/bin/env python
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownParameterType=false
# -*- coding: utf-8 -*-
from PySide6.QtGui import QCloseEvent

"""
Main Window for 3DE4 Curve Editor.

This module contains the MainWindow class which serves as the main entry point
for the Curve Editor application. It initializes the UI components, creates the
main application window, and manages the application lifecycle.

Key architecture principles:
1. Separation of UI components into the UIComponents class
2. Centralized signal connections managed through SignalRegistry.connect_all_signals
3. Operation-specific logic in dedicated service classes:
   - CurveService - For curve view manipulation
   - ImageService - For image sequence handling
   - DialogService - For dialog management
   - SettingsService - For application settings management
   - FileService - For file operations
   - HistoryService - For undo/redo functionality
   - CenteringZoomService - For view centering and zoom operations
   - CurveDataOperations - For curve data manipulation (Legacy class)

This architecture ensures:
- Clear separation of concerns
- Improved code organization and maintainability
- Consistent signal connection patterns
- Better error handling and defensive programming
"""

import sys
import os
import re
import config
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter, QApplication, QStatusBar, QLabel, QMessageBox, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton
from PySide6.QtCore import Qt
from curve_view import CurveView
from services.file_service import FileService as FileOperations

from utils import load_3de_track, estimate_image_dimensions, get_image_files

from services.history_service import HistoryService
from services.dialog_service import DialogService
from services.image_service import ImageService as ImageOperations
from services.curve_service import CurveService as CurveViewOperations
from services.settings_service import SettingsService

from keyboard_shortcuts import ShortcutManager
from ui_components import UIComponents

from track_quality import TrackQualityUI
from menu_bar import MenuBar
# import typing  # Removed unused import
from typing import Any
from services.analysis_service import AnalysisService as CurveDataOperations
from services.centering_zoom_service import CenteringZoomService as ZoomOperations

if False:
    pass

class MainWindow(QMainWindow):
    """Main application window for 3DE4 Curve Editor.

    This class implements the main window of the curve editor application,
    providing a UI for editing and analyzing 2D tracking data. It uses a
    utility-class based architecture where most functionality is delegated
    to specialized utility classes:

    - CurveService: Operations related to the curve view (point selection, editing)
    - ImageService: Operations for image sequence handling
    - FileService: File handling (loading, saving tracks)
    - DialogService: Management of various dialogs
    - SettingsService: Application settings management
    - UIComponents: Common UI operations
    - HistoryService: Undo/redo functionality
    - CurveDataOperations: Mathematical operations on curves (New consolidated class)

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
        centering_enabled (bool): Whether automatic centering on selected point is enabled
    """
    # Explicit attribute annotations for dynamic UI components
    update_point_button: Any
    type_edit: Any
    timeline_slider: Any
    frame_label: Any
    frame_edit: Any
    curve_view: Any
    save_button: Any
    add_point_button: Any
    smooth_button: Any
    fill_gaps_button: Any
    filter_button: Any
    detect_problems_button: Any
    extrapolate_button: Any
    go_button: Any
    toggle_bg_button: Any
    center_on_point_button: Any
    auto_center_action: Any

    # Inline smoothing controls declared for proper typing
    smoothing_method_combo: QComboBox
    smoothing_window_spin: QSpinBox
    smoothing_sigma_spin: QDoubleSpinBox
    smoothing_range_combo: QComboBox
    smoothing_apply_button: QPushButton

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

        # Centering state for view centering toggle
        # Auto-center state (will be loaded from settings)
        self.auto_center_enabled = False

        # Initialize the supporting modules
        # Note: FileOperations, ImageOperations, and UIComponents use static methods
        # and don't need to be instantiated

        # Track quality analyzer
        self.quality_ui = TrackQualityUI(self)

        # Load settings first to get initial state
        SettingsService.load_settings(self)  # Use the service implementation

        # Init UI (which uses loaded settings)
        self.setup_ui()

        # Install event filter for key navigation
        self.installEventFilter(self)

        # First create view and timeline with standard curve view
        # This ensures we have a valid curve_view_container

        # Then try to integrate enhanced curve view if possible
        try:
            # Use the UIComponents centralized method for creating enhanced curve view
            success = UIComponents.create_enhanced_curve_view(self)
            if success:
                print("Enhanced curve view loaded successfully")
            else:
                print("Failed to initialize enhanced curve view")
        except Exception as e:
            print(f"Error loading enhanced curve view: {str(e)}")
            print("Using standard curve view")

        # Initialize batch editing UI
        # self.batch_edit_ui = batch_edit.BatchEditUI(self)
        # self.batch_edit_ui.setup_batch_editing_ui()

        # Load previously used file if it exists
        self.load_previous_file()

        # Setup keyboard shortcuts BEFORE connecting signals
        self.shortcuts = {}
        ShortcutManager.setup_shortcuts(self)  # type: ignore

        # Use the single centralized signal connection registry
        from signal_registry import SignalRegistry
        SignalRegistry.connect_all_signals(self)

        # Set initial state for auto-center toggle menu item AFTER UI setup and settings load
        if hasattr(self.menu_bar, 'auto_center_action'):
            self.menu_bar.auto_center_action.setChecked(getattr(self, 'auto_center_enabled', False))

    def set_centering_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-centering of the view."""
        self.auto_center_enabled = enabled
        if hasattr(self, 'auto_center_action'):
            self.auto_center_action.setChecked(enabled)

        # Immediately center on selected point if available
        if enabled:
            if hasattr(self, 'curve_view') and hasattr(self.curve_view, 'selected_point_idx') and self.curve_view.selected_point_idx >= 0:
                ZoomOperations.center_on_selected_point(self.curve_view)
            # else: no selection or view not ready, do nothing

    def setup_ui(self):
        """Create and arrange UI elements."""
        # Create menu bar
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        # Expose QAction for auto-center on main_window for shortcut handling
        self.auto_center_action = self.menu_bar.auto_center_action

        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Create toolbar
        toolbar_widget = UIComponents.create_toolbar(self)
        main_layout.addWidget(toolbar_widget)

        # Create new layout to reorganize the UI components
        # This will place the splitter exactly between the image view and bottom UI elements

        # Get the curve view and timeline components separately
        curve_view_container, timeline_widget = UIComponents.create_view_and_timeline_separated(self)

        # Create control panel
        controls_widget = UIComponents.create_control_panel(self)

        # Create splitter for curve view and bottom UI (timeline + controls)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Make the splitter handle wider and more visible
        splitter.setHandleWidth(4)

        # Set the splitter stylesheet to make the handle more visible
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #c0c0c0;
                border: 1px solid #808080;
                border-radius: 1px;
            }
            QSplitter::handle:hover {
                background-color: #a0a0a0;
            }
        """)

        # Add curve view to top of splitter
        # Set minimum size for top view to prevent it from collapsing completely
        curve_view_container.setMinimumHeight(200)
        splitter.addWidget(curve_view_container)

        # Create a container for bottom UI (timeline + controls)
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        # Add timeline to bottom container
        bottom_layout.addWidget(timeline_widget)

        # Add controls to bottom container
        # Set minimum size for bottom panel to prevent it from collapsing completely
        # but small enough to allow significant resizing
        controls_widget.setMinimumHeight(120)
        bottom_layout.addWidget(controls_widget)

        # Add the bottom container to the splitter
        bottom_container.setMinimumHeight(200)
        splitter.addWidget(bottom_container)

        # Set relative sizes with more space for the top view by default
        splitter.setSizes([700, 300])

        # Store reference to splitter for later access if needed
        self.main_splitter = splitter

        main_layout.addWidget(splitter)

        self.setCentralWidget(main_widget)

        # Set up status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        # Set initial state for auto-center toggle menu item after settings load
        if hasattr(self.menu_bar, 'auto_center_action'):
            self.menu_bar.auto_center_action.setChecked(getattr(self, 'auto_center_enabled', False))


    def create_toolbar(self) -> QWidget:
        """Create the toolbar with action buttons.

        Sets up the main toolbar with buttons for common operations:
        - Load/save/add track data
        - Load image sequence
        - Tool operations (smoothing, filtering, etc.)

        All button actions are connected directly to operations in utility classes
        where appropriate, avoiding redundant wrapper methods.
        """
        return UIComponents.create_toolbar(self)

    def create_view_and_timeline(self) -> QWidget:
        """Create the curve view widget and timeline controls.

        Sets up:
        1. The CurveView widget for visualizing and editing tracking data
        2. Timeline slider and controls for frame navigation
        3. Playback controls for animation

        Timeline and playback controls are connected directly to UIComponents methods.
        """
        # Create the view container using UIComponents
        view_container = UIComponents.create_view_and_timeline(self)

        # All signals are now connected in the SignalRegistry class
        # No need for duplicate connections here

        return view_container

    def create_control_panel(self) -> QWidget:
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

    def enable_point_controls(self, enabled: bool) -> None:
        """Enable or disable point editing controls.

        Args:
            enabled (bool): Whether to enable or disable controls

        Enables or disables the point editing controls based on whether
        there is tracking data loaded and available for editing.
        """
        # Only update button and type display (no coordinate fields)
        self.update_point_button.setEnabled(enabled)
        if hasattr(self, 'type_edit'):
            self.type_edit.setEnabled(enabled)



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

    def on_image_changed(self, index: int) -> None:
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

            # Auto-center if enabled
            if getattr(self, 'auto_center_enabled', False) and hasattr(self.curve_view, 'centerOnSelectedPoint'):
                self.curve_view.centerOnSelectedPoint(-1)
                self.curve_view.update()

        except Exception as e:
            print(f"Error handling image change: {str(e)}")
            import traceback
            traceback.print_exc()

    def _select_point_for_frame(self, frame_num: int) -> None:
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
            # Pass main_window (self) to align with method signature
            CurveViewOperations.select_point_by_index(self.curve_view, self, closest_idx)

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
            point_name, point_color, _num_frames, curve_data = load_3de_track(file_path)

            if curve_data:
                # Set the data
                self.point_name = point_name
                self.point_color = point_color
                self.curve_data = curve_data

                # Determine image dimensions from the data
                self.image_width, self.image_height = estimate_image_dimensions(curve_data)

                # Update view
                self.curve_view.setPoints(self.curve_data, self.image_width, self.image_height)

                # Enable controls (guarded for robustness)
                if hasattr(self, "save_button"):
                    self.save_button.setEnabled(True)
                if hasattr(self, "add_point_button"):
                    self.add_point_button.setEnabled(True)
                if hasattr(self, "smooth_button"):
                    self.smooth_button.setEnabled(True)
                if hasattr(self, "fill_gaps_button"):
                    self.fill_gaps_button.setEnabled(True)
                if hasattr(self, "filter_button"):
                    self.filter_button.setEnabled(True)
                if hasattr(self, "detect_problems_button"):
                    self.detect_problems_button.setEnabled(True)
                if hasattr(self, "extrapolate_button"):
                    self.extrapolate_button.setEnabled(True)

                # Update info
                self.info_label: QLabel
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
            image_files = get_image_files(sequence_path)

            if image_files:
                # Set the image sequence
                self.image_sequence_path = sequence_path
                self.image_filenames = image_files

                # Setup the curve view with images
                self.curve_view.setImageSequence(sequence_path, image_files)

                # Update the UI
                self.update_image_label()
                self.toggle_bg_button.setEnabled(True)

    # Timeline Operations
    def setup_timeline(self):
        """Setup timeline slider based on frame range."""
        UIComponents.setup_timeline(self)

    # Point Editing Operations
    def on_point_selected(self, idx: int) -> None:
        """Handle point selection in the view."""
        # Pass curve_view and main_window correctly
        CurveViewOperations.on_point_selected(self.curve_view, self, idx)

    def on_point_moved(self, idx: int, x: float, y: float) -> None:
        """Handle point moved in the view."""
        CurveViewOperations.on_point_moved(self, idx, x, y)


    def show_shortcuts_dialog(self):
        """Show dialog with keyboard shortcuts."""
        DialogService.show_shortcuts_dialog(self)

    def update_point_info(self, idx: int, x: float, y: float) -> None:
        """Update the point information panel."""
        CurveViewOperations.update_point_info(self, idx, x, y)  # type: ignore[attr-defined]

    # History Operations
    def add_to_history(self):
        """Add current state to history."""
        HistoryService.add_to_history(self)

    def update_history_buttons(self):
        """Update the state of undo/redo buttons."""
        HistoryService.update_history_buttons(self)

    def undo_action(self):
        """Undo the last action."""
        HistoryService.undo_action(self)

    def redo_action(self):
        """Redo the previously undone action."""
        HistoryService.redo_action(self)

    def restore_state(self, state: Any) -> None:
        """Restore application state from history."""
        HistoryService.restore_state(self, state)  # type: ignore[attr-defined]

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

    def apply_ui_smoothing(self) -> None:
        """Apply smoothing based on inline UI controls."""
        if not self.curve_data or len(self.curve_data) < 3:
            QMessageBox.information(self, "Info", "Not enough points to smooth curve.")
            return
        method = self.smoothing_method_combo.currentIndex()
        range_type = self.smoothing_range_combo.currentIndex()
        window = self.smoothing_window_spin.value()
        sigma = self.smoothing_sigma_spin.value()
        points_to_smooth = []
        if range_type == 0:
            points_to_smooth = list(range(len(self.curve_data)))
        elif range_type == 1:
            selected = getattr(self.curve_view, 'selected_points', [])
            if selected:
                frames = sorted([self.curve_data[i][0] for i in selected])
                for i, pt in enumerate(self.curve_data):
                    if frames[0] <= pt[0] <= frames[-1]:
                        points_to_smooth.append(i)
        elif range_type == 2:
            idx = getattr(self.curve_view, 'selected_point_idx', -1)
            if idx >= 0:
                half = window // 2
                for i in range(max(0, idx-half), min(len(self.curve_data), idx+half+1)):
                    points_to_smooth.append(i)
        if not points_to_smooth:
            QMessageBox.warning(self, "Warning", "No points to smooth.")
            return
        try:
            ops = CurveDataOperations(self.curve_data)
            if method == 0:
                ops.smooth_moving_average(points_to_smooth, window)
            elif method == 1:
                ops.smooth_gaussian(points_to_smooth, window, sigma)
            elif method == 2:
                ops.smooth_savitzky_golay(points_to_smooth, window)
            else:
                QMessageBox.warning(self, "Warning", "Unknown smoothing method.")
                return
            self.curve_data = ops.get_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Smoothing failed: {e}")
            return
        self.curve_view.scale_to_image = False
        self.curve_view.setPoints(self.curve_data, self.image_width, self.image_height, preserve_view=True)
        self.add_to_history()

    # Smoothing Operations
    def apply_smooth_operation(self):
        """Entry point for smoothing operations, coordinates UI updates."""
        if not self.curve_data:
            QMessageBox.information(self, "Info", "No curve data loaded.")
            return

        # Gather necessary data
        current_data = self.curve_data
        # Get selected indices from curve view
        selected_indices: list[int] = []
        if hasattr(self.curve_view, 'get_selected_indices'):
            selected_indices = self.curve_view.get_selected_indices()
        elif hasattr(self.curve_view, 'selected_points'):
            selected_indices = list(self.curve_view.selected_points)
        selected_point_idx = getattr(self.curve_view, 'selected_point_idx', -1)

        # Call the refactored dialog operation, passing data
        modified_data = DialogService.show_smooth_dialog(
            parent_widget=self,
            curve_data=current_data,
            selected_indices=selected_indices,
            selected_point_idx=selected_point_idx
        )

        # If data was modified, update state, view, and history
        if modified_data is not None:
            print(f"[DEBUG MainWindow] Smoothing successful. Data modified.")
            sys.stdout.flush()
            # Update the curve data
            self.curve_data = modified_data

            # Disable auto-scaling to preserve current view
            self.curve_view.scale_to_image = False

            # Set points WITH preserve_view=True to maintain view position
            self.curve_view.setPoints(
                self.curve_data,
                self.image_width,
                self.image_height,
                preserve_view=True
            )

            # Add to history
            self.add_to_history()

            # Final update to ensure proper rendering
            self.curve_view.update()

            # Update status
            self.statusBar().showMessage("Smoothing applied successfully", 3000)
    def show_filter_dialog(self):
        DialogService.show_filter_dialog(self)

    def show_fill_gaps_dialog(self):
        DialogService.show_fill_gaps_dialog(self)

    def fill_gap(self, start_frame: int, end_frame: int, method: int, preserve_endpoints: bool = True) -> None:
        """Delegate gap filling to DialogService using the selected method index."""
        DialogService.fill_gap(self, start_frame, end_frame, method, preserve_endpoints)

    def show_extrapolate_dialog(self):
        DialogService.show_extrapolate_dialog(self)

    def on_frame_changed(self, frame_num: int) -> None:
        """Called when the frame changes (timeline, playback, etc)."""
        # Usual frame update logic (call existing code)
        self._select_point_for_frame(frame_num)
        if getattr(self, 'auto_center_enabled', False):
            # Center view on selected point
            if hasattr(self.curve_view, 'centerOnSelectedPoint'):
                self.curve_view.centerOnSelectedPoint(-1)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event, saving settings before exit.

        Args:
            event: The close event from Qt
        """
        # Use the SettingsService to handle the close event
        SettingsService.handle_close_event(self, event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
