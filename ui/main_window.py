#!/usr/bin/env python
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportImportCycles=false
# -*- coding: utf-8 -*-

"""
Main Window for 3DE4 Curve Editor.

This module contains the MainWindow class which serves as the main entry point
for the Curve Editor application. It has been refactored to delegate most
functionality to specialized classes for better maintainability.

Key architecture components:
1. ApplicationState - Manages all application state variables
2. UIInitializer - Handles UI component initialization
3. Direct service access through ServiceRegistryV2
5. Service classes - Handle specific functionality
"""

# Standard library imports
import sys
import logging
from typing import Optional

# Import PySide6 modules
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QIcon,
    QKeySequence,
    QResizeEvent,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStyle,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# Import local modules
from data.curve_view import CurveView
from data.track_quality import TrackQualityUI

from .curve_view_widget import CurveViewWidget
from .keyboard_shortcuts import ShortcutManager
from .state_manager import StateManager

# Import refactored components
from .ui_scaling import UIScaling

# Configure logger for this module
logger = logging.getLogger("main_window")

class MainWindow(QMainWindow):  # Implements MainWindowProtocol (structural typing)
    """Main application window for the Curve Editor."""
    
    # Custom signals for internal communication
    play_toggled = Signal(bool)
    frame_rate_changed = Signal(int)

    def __init__(self, parent: QWidget = None):
        """Initialize the MainWindow with enhanced UI functionality."""
        super().__init__(parent)
        
        # Setup basic window properties
        self.setWindowTitle("CurveEditor")
        self.setMinimumSize(1024, 768)
        self.resize(1400, 900)
        
        # Initialize managers
        self.state_manager = StateManager(self)
        self.shortcut_manager = ShortcutManager(self)
        
        # Initialize service facade
        from .service_facade import get_service_facade
        self.services = get_service_facade(self)
        
        # Initialize UI scaling
        self.ui_scaling = UIScaling()
        
        # Initialize UI components
        self._init_actions()
        self._init_toolbar()
        self._init_central_widget()
        self._init_dock_widgets()
        self._init_status_bar()
        
        # Initialize legacy curve view and track quality UI
        self.curve_view = None
        self.track_quality_ui = None
        
        # Connect state manager signals
        self._connect_signals()
        
        # Connect curve widget signals (after all UI components are created)
        if self.curve_widget:
            self._connect_curve_widget_signals()
        
        # Setup initial state
        self._update_ui_state()
        
        logger.info("MainWindow initialized successfully")
    
    def _init_actions(self) -> None:
        """Initialize all QActions for menus and toolbars."""
        # File actions
        self.action_new = QAction("New", self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.setStatusTip("Create a new curve")
        self.action_new.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        
        self.action_open = QAction("Open", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.setStatusTip("Open an existing curve file")
        self.action_open.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        
        self.action_save = QAction("Save", self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.setStatusTip("Save the current curve")
        self.action_save.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DriveFDIcon))
        
        self.action_save_as = QAction("Save As...", self)
        self.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_as.setStatusTip("Save the curve with a new name")
        
        # Edit actions
        self.action_undo = QAction("Undo", self)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.setStatusTip("Undo the last action")
        self.action_undo.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.action_undo.setEnabled(False)
        
        self.action_redo = QAction("Redo", self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.setStatusTip("Redo the previously undone action")
        self.action_redo.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.action_redo.setEnabled(False)
        
        # View actions
        self.action_zoom_in = QAction("Zoom In", self)
        self.action_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.action_zoom_in.setStatusTip("Zoom in the view")
        self.action_zoom_in.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        
        self.action_zoom_out = QAction("Zoom Out", self)
        self.action_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.action_zoom_out.setStatusTip("Zoom out the view")
        self.action_zoom_out.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        
        self.action_reset_view = QAction("Reset View", self)
        self.action_reset_view.setShortcut("Ctrl+0")
        self.action_reset_view.setStatusTip("Reset the view to default")
        self.action_reset_view.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        
        # Connect actions to shortcut manager signals
        self._connect_actions()
    
    def _init_toolbar(self) -> None:
        """Initialize the main toolbar."""
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setObjectName("mainToolBar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # File operations
        toolbar.addAction(self.action_new)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        
        # Edit operations
        toolbar.addAction(self.action_undo)
        toolbar.addAction(self.action_redo)
        toolbar.addSeparator()
        
        # View operations
        toolbar.addAction(self.action_zoom_in)
        toolbar.addAction(self.action_zoom_out)
        toolbar.addAction(self.action_reset_view)
        
        # Add stretch to push remaining items to the right
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().horizontalPolicy(),
            spacer.sizePolicy().verticalPolicy()
        )
        toolbar.addWidget(spacer)
    
    def _init_central_widget(self) -> None:
        """Initialize the central widget with QSplitter layout."""
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.main_splitter)
        
        # Left panel - Timeline controls
        self.timeline_widget = self._create_timeline_panel()
        self.main_splitter.addWidget(self.timeline_widget)
        
        # Center - Main curve view area
        self.curve_container = self._create_curve_view_container()
        self.main_splitter.addWidget(self.curve_container)
        
        # Right panel - Properties/Info
        self.properties_widget = self._create_properties_panel()
        self.main_splitter.addWidget(self.properties_widget)
        
        # Set initial splitter sizes (left: 250, center: expandable, right: 300)
        self.main_splitter.setSizes([250, 850, 300])
        self.main_splitter.setStretchFactor(0, 0)  # Left panel doesn't stretch
        self.main_splitter.setStretchFactor(1, 1)  # Center panel stretches
        self.main_splitter.setStretchFactor(2, 0)  # Right panel doesn't stretch
    
    def _create_timeline_panel(self) -> QWidget:
        """Create the timeline control panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Timeline group
        timeline_group = QGroupBox("Timeline")
        timeline_layout = QVBoxLayout()
        
        # Frame controls
        frame_layout = QHBoxLayout()
        frame_layout.addWidget(QLabel("Frame:"))
        
        self.frame_spinbox = QSpinBox()
        self.frame_spinbox.setMinimum(1)
        self.frame_spinbox.setMaximum(1000)
        self.frame_spinbox.setValue(1)
        self.frame_spinbox.valueChanged.connect(self._on_frame_changed)
        frame_layout.addWidget(self.frame_spinbox)
        
        frame_layout.addWidget(QLabel("/"))
        
        self.total_frames_label = QLabel("1")
        frame_layout.addWidget(self.total_frames_label)
        frame_layout.addStretch()
        
        timeline_layout.addLayout(frame_layout)
        
        # Frame slider
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(1)
        self.frame_slider.setMaximum(1000)
        self.frame_slider.setValue(1)
        self.frame_slider.valueChanged.connect(self._on_slider_changed)
        timeline_layout.addWidget(self.frame_slider)
        
        # Playback controls
        playback_layout = QHBoxLayout()
        
        self.btn_first_frame = QPushButton()
        self.btn_first_frame.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.btn_first_frame.setToolTip("Go to first frame")
        self.btn_first_frame.clicked.connect(self._on_first_frame)
        playback_layout.addWidget(self.btn_first_frame)
        
        self.btn_prev_frame = QPushButton()
        self.btn_prev_frame.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))
        self.btn_prev_frame.setToolTip("Previous frame")
        self.btn_prev_frame.clicked.connect(self._on_prev_frame)
        playback_layout.addWidget(self.btn_prev_frame)
        
        self.btn_play_pause = QPushButton()
        self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play_pause.setCheckable(True)
        self.btn_play_pause.setToolTip("Play/Pause")
        self.btn_play_pause.toggled.connect(self._on_play_pause)
        playback_layout.addWidget(self.btn_play_pause)
        
        self.btn_next_frame = QPushButton()
        self.btn_next_frame.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))
        self.btn_next_frame.setToolTip("Next frame")
        self.btn_next_frame.clicked.connect(self._on_next_frame)
        playback_layout.addWidget(self.btn_next_frame)
        
        self.btn_last_frame = QPushButton()
        self.btn_last_frame.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.btn_last_frame.setToolTip("Go to last frame")
        self.btn_last_frame.clicked.connect(self._on_last_frame)
        playback_layout.addWidget(self.btn_last_frame)
        
        timeline_layout.addLayout(playback_layout)
        
        # Frame rate control
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setMinimum(1)
        self.fps_spinbox.setMaximum(120)
        self.fps_spinbox.setValue(24)
        self.fps_spinbox.setSuffix(" fps")
        self.fps_spinbox.valueChanged.connect(self._on_fps_changed)
        fps_layout.addWidget(self.fps_spinbox)
        fps_layout.addStretch()
        
        timeline_layout.addLayout(fps_layout)
        
        timeline_group.setLayout(timeline_layout)
        layout.addWidget(timeline_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Playback timer for animation
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._on_playback_timer)
        
        return widget
    
    def _create_curve_view_container(self) -> QWidget:
        """Create the container for the curve view."""
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.Box)
        container.setLineWidth(1)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the actual CurveViewWidget
        self.curve_widget = CurveViewWidget(container)
        self.curve_widget.set_main_window(self)
        layout.addWidget(self.curve_widget)
        
        logger.info("CurveViewWidget created and integrated")
        
        return container
    
    def _create_properties_panel(self) -> QWidget:
        """Create the properties/info panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Point Properties group
        point_group = QGroupBox("Point Properties")
        point_layout = QVBoxLayout()
        
        # Selected point info
        self.selected_point_label = QLabel("No point selected")
        point_layout.addWidget(self.selected_point_label)
        
        # Point position
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("X:"))
        self.point_x_spinbox = QDoubleSpinBox()
        self.point_x_spinbox.setRange(-10000, 10000)
        self.point_x_spinbox.setDecimals(3)
        self.point_x_spinbox.setEnabled(False)
        pos_layout.addWidget(self.point_x_spinbox)
        
        pos_layout.addWidget(QLabel("Y:"))
        self.point_y_spinbox = QDoubleSpinBox()
        self.point_y_spinbox.setRange(-10000, 10000)
        self.point_y_spinbox.setDecimals(3)
        self.point_y_spinbox.setEnabled(False)
        pos_layout.addWidget(self.point_y_spinbox)
        
        point_layout.addLayout(pos_layout)
        
        point_group.setLayout(point_layout)
        layout.addWidget(point_group)
        
        # View Settings group
        view_group = QGroupBox("View Settings")
        view_layout = QVBoxLayout()
        
        # Display options
        self.show_background_cb = QCheckBox("Show Background")
        self.show_background_cb.setChecked(True)
        self.show_background_cb.stateChanged.connect(self._on_view_option_changed)
        view_layout.addWidget(self.show_background_cb)
        
        self.show_grid_cb = QCheckBox("Show Grid")
        self.show_grid_cb.setChecked(True)
        self.show_grid_cb.stateChanged.connect(self._on_view_option_changed)
        view_layout.addWidget(self.show_grid_cb)
        
        self.show_info_cb = QCheckBox("Show Info Overlay")
        self.show_info_cb.setChecked(True)
        self.show_info_cb.stateChanged.connect(self._on_view_option_changed)
        view_layout.addWidget(self.show_info_cb)
        
        # Point size slider
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Point Size:"))
        
        self.point_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.point_size_slider.setMinimum(2)
        self.point_size_slider.setMaximum(20)
        self.point_size_slider.setValue(6)
        self.point_size_slider.valueChanged.connect(self._on_point_size_changed)
        size_layout.addWidget(self.point_size_slider)
        
        self.point_size_label = QLabel("6")
        size_layout.addWidget(self.point_size_label)
        
        view_layout.addLayout(size_layout)
        
        # Line width slider
        line_layout = QHBoxLayout()
        line_layout.addWidget(QLabel("Line Width:"))
        
        self.line_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.line_width_slider.setMinimum(1)
        self.line_width_slider.setMaximum(10)
        self.line_width_slider.setValue(2)
        self.line_width_slider.valueChanged.connect(self._on_line_width_changed)
        line_layout.addWidget(self.line_width_slider)
        
        self.line_width_label = QLabel("2")
        line_layout.addWidget(self.line_width_label)
        
        view_layout.addLayout(line_layout)
        
        view_group.setLayout(view_layout)
        layout.addWidget(view_group)
        
        # Curve Info group
        info_group = QGroupBox("Curve Information")
        info_layout = QVBoxLayout()
        
        self.point_count_label = QLabel("Points: 0")
        info_layout.addWidget(self.point_count_label)
        
        self.selected_count_label = QLabel("Selected: 0")
        info_layout.addWidget(self.selected_count_label)
        
        self.bounds_label = QLabel("Bounds: N/A")
        self.bounds_label.setWordWrap(True)
        info_layout.addWidget(self.bounds_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Add stretch
        layout.addStretch()
        
        return widget
    
    def _init_dock_widgets(self) -> None:
        """Initialize dock widgets (optional, for future expansion)."""
        # Can add dockable panels here if needed
        pass
    
    def _init_status_bar(self) -> None:
        """Initialize the status bar with additional widgets."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add permanent widgets to status bar
        self.zoom_label = QLabel("Zoom: 100%")
        self.status_bar.addPermanentWidget(self.zoom_label)
        
        self.position_label = QLabel("X: 0.000, Y: 0.000")
        self.status_bar.addPermanentWidget(self.position_label)
        
        self.status_bar.showMessage("Ready", 2000)
    
    def _connect_signals(self) -> None:
        """Connect signals from state manager and shortcuts."""
        # Connect state manager signals
        self.state_manager.file_changed.connect(self._on_file_changed)
        self.state_manager.modified_changed.connect(self._on_modified_changed)
        self.state_manager.frame_changed.connect(self._on_state_frame_changed)
        self.state_manager.selection_changed.connect(self._on_selection_changed)
        self.state_manager.view_state_changed.connect(self._on_view_state_changed)
        
        # Connect shortcut signals (these will be no-ops for now)
        self.shortcut_manager.shortcut_activated.connect(self._on_shortcut_activated)
    
    def _connect_curve_widget_signals(self) -> None:
        """Connect signals from the curve widget."""
        if not self.curve_widget:
            return
        
        # Connect curve widget signals to handlers
        self.curve_widget.point_selected.connect(self._on_point_selected)
        self.curve_widget.point_moved.connect(self._on_point_moved)
        self.curve_widget.selection_changed.connect(self._on_curve_selection_changed)
        self.curve_widget.view_changed.connect(self._on_curve_view_changed)
        self.curve_widget.zoom_changed.connect(self._on_curve_zoom_changed)
        
        # Connect view options to curve widget
        self.show_background_cb.stateChanged.connect(self._update_curve_view_options)
        self.show_grid_cb.stateChanged.connect(self._update_curve_view_options)
        self.show_info_cb.stateChanged.connect(self._update_curve_view_options)
        self.point_size_slider.valueChanged.connect(self._update_curve_point_size)
        self.line_width_slider.valueChanged.connect(self._update_curve_line_width)
    
    def _connect_actions(self) -> None:
        """Connect actions to their handlers."""
        # File actions
        self.action_new.triggered.connect(self._on_action_new)
        self.action_open.triggered.connect(self._on_action_open)
        self.action_save.triggered.connect(self._on_action_save)
        self.action_save_as.triggered.connect(self._on_action_save_as)
        
        # Edit actions
        self.action_undo.triggered.connect(self._on_action_undo)
        self.action_redo.triggered.connect(self._on_action_redo)
        
        # View actions
        self.action_zoom_in.triggered.connect(self._on_action_zoom_in)
        self.action_zoom_out.triggered.connect(self._on_action_zoom_out)
        self.action_reset_view.triggered.connect(self._on_action_reset_view)
    
    def _on_file_changed(self, file_path: str) -> None:
        """Handle file path changes."""
        self.setWindowTitle(self.state_manager.get_window_title())
        if file_path:
            logger.info(f"File changed to: {file_path}")
    
    def _on_modified_changed(self, modified: bool) -> None:
        """Handle modification status changes."""
        self.setWindowTitle(self.state_manager.get_window_title())
        if modified:
            logger.debug("Document marked as modified")
    
    def _on_shortcut_activated(self, shortcut_name: str) -> None:
        """Handle keyboard shortcut activation."""
        logger.debug(f"Shortcut activated: {shortcut_name}")
        # Map shortcut names to actions
        shortcut_map = {
            "new_file": self.action_new,
            "open_file": self.action_open,
            "save_file": self.action_save,
            "save_as": self.action_save_as,
            "undo": self.action_undo,
            "redo": self.action_redo,
            "zoom_in": self.action_zoom_in,
            "zoom_out": self.action_zoom_out,
            "reset_view": self.action_reset_view,
            "next_frame": lambda: self._on_next_frame(),
            "prev_frame": lambda: self._on_prev_frame(),
            "first_frame": lambda: self._on_first_frame(),
            "last_frame": lambda: self._on_last_frame(),
        }
        
        if shortcut_name in shortcut_map:
            action_or_func = shortcut_map[shortcut_name]
            if callable(action_or_func):
                action_or_func()
            else:
                action_or_func.trigger()
        
        self.status_bar.showMessage(f"Shortcut: {shortcut_name}", 1000)
    
    # ==================== Timeline Control Handlers ====================
    
    def _on_frame_changed(self, value: int) -> None:
        """Handle frame spinbox value change."""
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(value)
        self.frame_slider.blockSignals(False)
        self.state_manager.current_frame = value
    
    def _on_slider_changed(self, value: int) -> None:
        """Handle frame slider value change."""
        self.frame_spinbox.blockSignals(True)
        self.frame_spinbox.setValue(value)
        self.frame_spinbox.blockSignals(False)
        self.state_manager.current_frame = value
    
    def _on_first_frame(self) -> None:
        """Go to first frame."""
        self.frame_spinbox.setValue(1)
    
    def _on_prev_frame(self) -> None:
        """Go to previous frame."""
        current = self.frame_spinbox.value()
        if current > 1:
            self.frame_spinbox.setValue(current - 1)
    
    def _on_next_frame(self) -> None:
        """Go to next frame."""
        current = self.frame_spinbox.value()
        if current < self.frame_spinbox.maximum():
            self.frame_spinbox.setValue(current + 1)
    
    def _on_last_frame(self) -> None:
        """Go to last frame."""
        self.frame_spinbox.setValue(self.frame_spinbox.maximum())
    
    def _on_play_pause(self, checked: bool) -> None:
        """Handle play/pause toggle."""
        if checked:
            # Start playback
            fps = self.fps_spinbox.value()
            interval = int(1000 / fps)  # Convert FPS to milliseconds
            self.playback_timer.start(interval)
            self.btn_play_pause.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
            )
            self.play_toggled.emit(True)
        else:
            # Stop playback
            self.playback_timer.stop()
            self.btn_play_pause.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
            )
            self.play_toggled.emit(False)
    
    def _on_playback_timer(self) -> None:
        """Handle playback timer tick."""
        current = self.frame_spinbox.value()
        if current >= self.frame_spinbox.maximum():
            # Loop back to start
            self.frame_spinbox.setValue(1)
        else:
            self.frame_spinbox.setValue(current + 1)
    
    def _on_fps_changed(self, value: int) -> None:
        """Handle FPS change."""
        if self.playback_timer.isActive():
            interval = int(1000 / value)
            self.playback_timer.setInterval(interval)
        self.frame_rate_changed.emit(value)
    
    # ==================== View Control Handlers ====================
    
    def _on_view_option_changed(self) -> None:
        """Handle view option checkbox changes."""
        # Now handled by dedicated curve widget handlers
        self._update_curve_view_options()
        logger.debug(f"View options changed - Background: {self.show_background_cb.isChecked()}, "
                    f"Grid: {self.show_grid_cb.isChecked()}, "
                    f"Info: {self.show_info_cb.isChecked()}")
    
    def _on_point_size_changed(self, value: int) -> None:
        """Handle point size slider change."""
        # Now handled by dedicated curve widget handler
        self._update_curve_point_size(value)
        logger.debug(f"Point size changed to: {value}")
    
    def _on_line_width_changed(self, value: int) -> None:
        """Handle line width slider change."""
        # Now handled by dedicated curve widget handler
        self._update_curve_line_width(value)
        logger.debug(f"Line width changed to: {value}")
    
    # ==================== Action Handlers ====================
    
    def _on_action_new(self) -> None:
        """Handle new file action."""
        if self.state_manager.is_modified:
            if not self.services.confirm_action(
                "Current curve has unsaved changes. Continue?", self
            ):
                return
        
        # Clear curve widget data
        if self.curve_widget:
            self.curve_widget.set_curve_data([])
        
        self.state_manager.reset_to_defaults()
        self._update_ui_state()
        self.status_bar.showMessage("New curve created", 2000)
    
    def _on_action_open(self) -> None:
        """Handle open file action."""
        # Check for unsaved changes
        if self.state_manager.is_modified:
            if not self.services.confirm_action(
                "Current curve has unsaved changes. Continue?", self
            ):
                return
        
        # Load data using service facade
        data = self.services.load_track_data(self)
        if data:
            # Update curve widget with new data
            if self.curve_widget:
                self.curve_widget.set_curve_data(data)
            
            # Update state manager
            self.state_manager.set_track_data(data, mark_modified=False)
            self._update_ui_state()
            self.status_bar.showMessage("File loaded successfully", 2000)
    
    def _on_action_save(self) -> None:
        """Handle save file action."""
        if not self.state_manager.current_file:
            self._on_action_save_as()
        else:
            # Get current data from curve widget
            data = self._get_current_curve_data()
            if self.services.save_track_data(data, self):
                self.state_manager.is_modified = False
                self.status_bar.showMessage("File saved successfully", 2000)
    
    def _on_action_save_as(self) -> None:
        """Handle save as action."""
        # Get current data from curve widget
        data = self._get_current_curve_data()
        if self.services.save_track_data(data, self):
            self.state_manager.is_modified = False
            self.status_bar.showMessage("File saved successfully", 2000)
    
    def _on_action_undo(self) -> None:
        """Handle undo action."""
        self.services.undo()
        self.status_bar.showMessage("Undo", 1000)
    
    def _on_action_redo(self) -> None:
        """Handle redo action."""
        self.services.redo()
        self.status_bar.showMessage("Redo", 1000)
    
    def _on_action_zoom_in(self) -> None:
        """Handle zoom in action."""
        if self.curve_widget:
            # Let curve widget handle zooming directly
            current_zoom = self.curve_widget.zoom_factor
            new_zoom = max(0.1, min(10.0, current_zoom * 1.2))
            self.curve_widget.zoom_factor = new_zoom
            self.curve_widget._invalidate_caches()
            self.curve_widget.update()
            self.curve_widget.zoom_changed.emit(new_zoom)
        else:
            # Fallback to state manager
            current_zoom = self.state_manager.zoom_level
            self.state_manager.zoom_level = current_zoom * 1.2
        self._update_zoom_label()
    
    def _on_action_zoom_out(self) -> None:
        """Handle zoom out action."""
        if self.curve_widget:
            # Let curve widget handle zooming directly
            current_zoom = self.curve_widget.zoom_factor
            new_zoom = max(0.1, min(10.0, current_zoom / 1.2))
            self.curve_widget.zoom_factor = new_zoom
            self.curve_widget._invalidate_caches()
            self.curve_widget.update()
            self.curve_widget.zoom_changed.emit(new_zoom)
        else:
            # Fallback to state manager
            current_zoom = self.state_manager.zoom_level
            self.state_manager.zoom_level = current_zoom / 1.2
        self._update_zoom_label()
    
    def _on_action_reset_view(self) -> None:
        """Handle reset view action."""
        if self.curve_widget:
            # Reset view using curve widget's method
            self.curve_widget.reset_view()
        else:
            # Fallback to state manager
            self.state_manager.zoom_level = 1.0
            self.state_manager.pan_offset = (0.0, 0.0)
        self._update_zoom_label()
        self.status_bar.showMessage("View reset", 1000)
    
    # ==================== State Change Handlers ====================
    
    def _on_selection_changed(self, indices: list) -> None:
        """Handle selection change from state manager."""
        count = len(indices)
        self.selected_count_label.setText(f"Selected: {count}")
        
        if count == 1:
            # Show single point properties
            idx = indices[0]
            self.selected_point_label.setText(f"Point #{idx}")
            
            # Get actual point data from curve widget
            if self.curve_widget and idx < len(self.curve_widget.curve_data):
                point_data = self.curve_widget.curve_data[idx]
                from core.point_types import safe_extract_point
                frame, x, y, status = safe_extract_point(point_data)
                
                # Update spinboxes with actual values
                self.point_x_spinbox.blockSignals(True)
                self.point_y_spinbox.blockSignals(True)
                self.point_x_spinbox.setValue(x)
                self.point_y_spinbox.setValue(y)
                self.point_x_spinbox.blockSignals(False)
                self.point_y_spinbox.blockSignals(False)
                
                # Connect spinbox changes to update point
                if not hasattr(self, '_point_spinbox_connected'):
                    self.point_x_spinbox.valueChanged.connect(self._on_point_x_changed)
                    self.point_y_spinbox.valueChanged.connect(self._on_point_y_changed)
                    self._point_spinbox_connected = True
                
            self.point_x_spinbox.setEnabled(True)
            self.point_y_spinbox.setEnabled(True)
        elif count > 1:
            self.selected_point_label.setText(f"{count} points selected")
            self.point_x_spinbox.setEnabled(False)
            self.point_y_spinbox.setEnabled(False)
        else:
            self.selected_point_label.setText("No point selected")
            self.point_x_spinbox.setEnabled(False)
            self.point_y_spinbox.setEnabled(False)
    
    def _on_view_state_changed(self) -> None:
        """Handle view state change from state manager."""
        self._update_zoom_label()
    
    # ==================== UI Update Methods ====================
    
    def _update_ui_state(self) -> None:
        """Update UI elements based on current state."""
        # Update history actions
        self.action_undo.setEnabled(self.state_manager.can_undo)
        self.action_redo.setEnabled(self.state_manager.can_redo)
        
        # Update frame controls
        total_frames = self.state_manager.total_frames
        self.frame_spinbox.setMaximum(total_frames)
        self.frame_slider.setMaximum(total_frames)
        self.total_frames_label.setText(str(total_frames))
        
        # Update info labels - use curve widget data if available
        if self.curve_widget:
            point_count = len(self.curve_widget.curve_data)
            self.point_count_label.setText(f"Points: {point_count}")
            
            if point_count > 0:
                # Calculate bounds from curve data
                from core.point_types import safe_extract_point
                x_coords = []
                y_coords = []
                for point in self.curve_widget.curve_data:
                    _, x, y, _ = safe_extract_point(point)
                    x_coords.append(x)
                    y_coords.append(y)
                
                if x_coords and y_coords:
                    min_x, max_x = min(x_coords), max(x_coords)
                    min_y, max_y = min(y_coords), max(y_coords)
                    self.bounds_label.setText(
                        f"Bounds:\nX: [{min_x:.2f}, {max_x:.2f}]\n"
                        f"Y: [{min_y:.2f}, {max_y:.2f}]"
                    )
                else:
                    self.bounds_label.setText("Bounds: N/A")
            else:
                self.bounds_label.setText("Bounds: N/A")
        else:
            # Fallback to state manager
            point_count = len(self.state_manager.track_data)
            self.point_count_label.setText(f"Points: {point_count}")
            
            if point_count > 0:
                bounds = self.state_manager.data_bounds
                self.bounds_label.setText(
                    f"Bounds:\nX: [{bounds[0]:.2f}, {bounds[2]:.2f}]\n"
                    f"Y: [{bounds[1]:.2f}, {bounds[3]:.2f}]"
                )
            else:
                self.bounds_label.setText("Bounds: N/A")
    
    def _update_zoom_label(self) -> None:
        """Update the zoom level label in status bar."""
        if self.curve_widget:
            zoom_percent = int(self.curve_widget.zoom_factor * 100)
        else:
            zoom_percent = int(self.state_manager.zoom_level * 100)
        self.zoom_label.setText(f"Zoom: {zoom_percent}%")
    
    def update_cursor_position(self, x: float, y: float) -> None:
        """Update cursor position in status bar."""
        self.position_label.setText(f"X: {x:.3f}, Y: {y:.3f}")

    # ==================== Curve Widget Signal Handlers ====================
    
    def _on_point_selected(self, index: int) -> None:
        """Handle point selection from curve widget."""
        logger.debug(f"Point {index} selected")
        # Update properties panel will be handled by selection_changed signal
    
    def _on_point_moved(self, index: int, x: float, y: float) -> None:
        """Handle point movement from curve widget."""
        self.state_manager.is_modified = True
        logger.debug(f"Point {index} moved to ({x:.3f}, {y:.3f})")
    
    def _on_curve_selection_changed(self, indices: list[int]) -> None:
        """Handle selection change from curve widget."""
        # Update state manager
        self.state_manager.set_selected_points(indices)
        # Properties panel will be updated via state manager signal
    
    def _on_curve_view_changed(self) -> None:
        """Handle view changes from curve widget."""
        # Update zoom display
        self._update_zoom_label()
    
    def _on_curve_zoom_changed(self, zoom: float) -> None:
        """Handle zoom changes from curve widget."""
        # Update state manager and zoom label
        self.state_manager.zoom_level = zoom
        self._update_zoom_label()
    
    # ==================== View Options Handlers ====================
    
    def _update_curve_view_options(self) -> None:
        """Update curve widget view options based on checkboxes."""
        if not self.curve_widget:
            return
        
        self.curve_widget.show_background = self.show_background_cb.isChecked()
        self.curve_widget.show_grid = self.show_grid_cb.isChecked()
        # Note: show_info_cb controls info overlay display - might need implementation
        self.curve_widget.update()
    
    def _update_curve_point_size(self, value: int) -> None:
        """Update curve widget point size."""
        if self.curve_widget:
            self.curve_widget.point_radius = value
            self.curve_widget.selected_point_radius = value + 2
            self.curve_widget.update()
        self.point_size_label.setText(str(value))
    
    def _update_curve_line_width(self, value: int) -> None:
        """Update curve widget line width."""
        if self.curve_widget:
            self.curve_widget.line_width = value
            self.curve_widget.selected_line_width = value + 1
            self.curve_widget.update()
        self.line_width_label.setText(str(value))
    
    # ==================== Frame Navigation Handlers ====================
    
    def _on_state_frame_changed(self, frame: int) -> None:
        """Handle frame change from state manager."""
        # Update UI controls
        self.frame_spinbox.blockSignals(True)
        self.frame_slider.blockSignals(True)
        self.frame_spinbox.setValue(frame)
        self.frame_slider.setValue(frame)
        self.frame_spinbox.blockSignals(False)
        self.frame_slider.blockSignals(False)
        
        # Update curve widget if it handles frame-based display
        # This would be for showing different frames of animation data
        # For now, we'll leave this as a placeholder for future frame-based features

    # ==================== Utility Methods ====================
    
    def _get_current_curve_data(self) -> list[tuple]:
        """Get current curve data from curve widget or state manager."""
        if self.curve_widget:
            return self.curve_widget.curve_data
        return [(x, y) for x, y in self.state_manager.track_data]
    
    def add_to_history(self) -> None:
        """Add current state to history (called by curve widget)."""
        self.services.add_to_history()
        
        # Update history-related UI state
        self.action_undo.setEnabled(self.state_manager.can_undo)
        self.action_redo.setEnabled(self.state_manager.can_redo)
    
    def _on_point_x_changed(self, value: float) -> None:
        """Handle X coordinate change in properties panel."""
        selected_indices = self.state_manager.selected_points
        if len(selected_indices) == 1 and self.curve_widget:
            idx = selected_indices[0]
            if idx < len(self.curve_widget.curve_data):
                from core.point_types import safe_extract_point
                _, _, y, _ = safe_extract_point(self.curve_widget.curve_data[idx])
                self.curve_widget.update_point(idx, value, y)
                self.state_manager.is_modified = True
    
    def _on_point_y_changed(self, value: float) -> None:
        """Handle Y coordinate change in properties panel."""
        selected_indices = self.state_manager.selected_points
        if len(selected_indices) == 1 and self.curve_widget:
            idx = selected_indices[0]
            if idx < len(self.curve_widget.curve_data):
                from core.point_types import safe_extract_point
                _, x, _, _ = safe_extract_point(self.curve_widget.curve_data[idx])
                self.curve_widget.update_point(idx, x, value)
                self.state_manager.is_modified = True

    # ==================== Public Methods for External Use ====================
    
    def set_curve_view(self, curve_view: Optional[CurveView]) -> None:
        """Set the curve view widget (legacy method - now uses CurveViewWidget)."""
        self.curve_view = curve_view
        logger.info("Legacy curve view reference set")
    
    def get_view_options(self) -> dict:
        """Get current view options."""
        return {
            "show_background": self.show_background_cb.isChecked(),
            "show_grid": self.show_grid_cb.isChecked(),
            "show_info": self.show_info_cb.isChecked(),
            "point_size": self.point_size_slider.value(),
            "line_width": self.line_width_slider.value(),
        }

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
