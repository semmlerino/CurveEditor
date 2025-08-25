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
import logging
import sys
import threading
from typing import Any

# Import PySide6 modules
from PySide6.QtCore import QEvent, QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QKeySequence,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

# Import local modules
# CurveView removed - using CurveViewWidget
from .curve_view_widget import CurveViewWidget
from .keyboard_shortcuts import ShortcutManager
from .state_manager import StateManager
from .ui_constants import MAX_HISTORY_SIZE

# Import refactored components
from .ui_scaling import UIScaling

# Configure logger for this module
logger = logging.getLogger("main_window")


class FileLoadWorker(QObject):
    """Worker class for loading files in a background thread."""

    # Signals for communicating with main thread
    tracking_data_loaded: Signal = Signal(list)  # Emits list of tracking data points
    image_sequence_loaded: Signal = Signal(str, list)  # Emits directory path and list of filenames
    progress_updated: Signal = Signal(int, str)  # Emits progress percentage and status message
    error_occurred: Signal = Signal(str)  # Emits error message
    finished: Signal = Signal()  # Emits when all loading is complete

    def __init__(self, tracking_file_path: str | None = None, image_dir_path: str | None = None):
        """Initialize worker with file paths to load."""
        super().__init__()
        self.tracking_file_path = tracking_file_path
        self.image_dir_path = image_dir_path
        self._should_stop = False
        self._stop_lock = threading.Lock()

    def stop(self) -> None:
        """Request the worker to stop processing."""
        with self._stop_lock:
            self._should_stop = True

    def _check_should_stop(self) -> bool:
        """Thread-safe check of stop flag."""
        with self._stop_lock:
            return self._should_stop

    def run(self) -> None:
        """Main worker method that runs in background thread."""
        try:
            total_tasks = 0
            current_task = 0

            # Count tasks to do
            if self.tracking_file_path:
                total_tasks += 1
            if self.image_dir_path:
                total_tasks += 1

            if total_tasks == 0:
                self.finished.emit()
                return

            # Load tracking data if requested
            if self.tracking_file_path and not self._check_should_stop():
                self.progress_updated.emit(0, "Loading tracking data...")
                try:
                    # Directly load the file without creating DataService in worker thread
                    data = self._load_2dtrack_data_direct(self.tracking_file_path)
                    if data:
                        self.tracking_data_loaded.emit(data)
                    current_task += 1
                    progress = int((current_task / total_tasks) * 100)
                    self.progress_updated.emit(progress, f"Loaded {len(data) if data else 0} tracking points")
                except Exception as e:
                    self.error_occurred.emit(f"Failed to load tracking data: {str(e)}")

            # Load image sequence if requested
            if self.image_dir_path and not self._check_should_stop():
                self.progress_updated.emit(int((current_task / total_tasks) * 100), "Loading image sequence...")
                try:
                    # Directly scan for image files without creating DataService
                    image_files = self._scan_image_directory(self.image_dir_path)
                    if image_files:
                        self.image_sequence_loaded.emit(self.image_dir_path, image_files)
                    current_task += 1
                    self.progress_updated.emit(100, f"Loaded {len(image_files) if image_files else 0} images")
                except Exception as e:
                    self.error_occurred.emit(f"Failed to load image sequence: {str(e)}")

        except Exception as e:
            self.error_occurred.emit(f"Unexpected error in file loading: {str(e)}")
        finally:
            self.finished.emit()

    def _load_2dtrack_data_direct(
        self, file_path: str
    ) -> list[tuple[int, float, float]] | list[tuple[int, float, float, str]]:
        """Load 2D tracking data directly without using DataService."""
        data = []
        try:
            with open(file_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) >= 3:
                        frame = int(parts[0])
                        x = float(parts[1])
                        y = float(parts[2])
                        # Handle optional status field
                        if len(parts) >= 4:
                            status = parts[3]
                            data.append((frame, x, y, status))
                        else:
                            data.append((frame, x, y))
        except Exception as e:
            logger.error(f"Error loading tracking data: {e}")
            raise
        return data

    def _scan_image_directory(self, dir_path: str) -> list[str]:
        """Scan directory for image files without using DataService."""
        from pathlib import Path

        supported_formats = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]
        image_files = []

        try:
            path = Path(dir_path)
            if path.exists() and path.is_dir():
                # Get all image files
                for file_path in sorted(path.iterdir()):
                    if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                        image_files.append(file_path.name)
        except Exception as e:
            logger.error(f"Error scanning image directory: {e}")
            raise

        return sorted(image_files)  # Return sorted list of filenames


class MainWindow(QMainWindow):  # Implements MainWindowProtocol (structural typing)
    """Main application window for the Curve Editor."""

    # Custom signals for internal communication
    play_toggled = Signal(bool)
    frame_rate_changed = Signal(int)

    # Widget type annotations - initialized in init methods
    frame_spinbox: QSpinBox | None = None
    total_frames_label: QLabel | None = None
    frame_slider: QSlider | None = None
    btn_first_frame: QPushButton | None = None
    btn_prev_frame: QPushButton | None = None
    btn_play_pause: QPushButton | None = None
    btn_next_frame: QPushButton | None = None
    btn_last_frame: QPushButton | None = None
    fps_spinbox: QSpinBox | None = None
    playback_timer: QTimer | None = None
    curve_widget: Any = None  # CurveViewWidget
    selected_point_label: QLabel | None = None
    point_x_spinbox: QDoubleSpinBox | None = None
    point_y_spinbox: QDoubleSpinBox | None = None
    show_background_cb: QCheckBox | None = None
    show_grid_cb: QCheckBox | None = None

    def __init__(self, parent: QWidget | None = None):
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

        # Initialize history tracking
        self.history: list[Any] = []
        self.history_index: int = -1
        self.max_history_size: int = MAX_HISTORY_SIZE

        # Initialize background thread management
        self.file_load_thread: QThread | None = None
        self.file_load_worker: FileLoadWorker | None = None

        # Connect state manager signals
        self._connect_signals()

        # Connect curve widget signals (after all UI components are created)
        if self.curve_widget:
            self._connect_curve_widget_signals()

        # Setup initial state
        self._update_ui_state()

        # Setup tab order for keyboard navigation
        self._setup_tab_order()

        # Auto-load burger footage and tracking data if available
        self._load_burger_tracking_data()

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
        toolbar.addSeparator()

        # Add frame control to toolbar
        toolbar.addWidget(QLabel("Frame:"))
        self.frame_spinbox = QSpinBox()
        self.frame_spinbox.setMinimum(1)
        self.frame_spinbox.setMaximum(1000)
        self.frame_spinbox.setValue(1)
        toolbar.addWidget(self.frame_spinbox)
        toolbar.addSeparator()

        # Add view option checkboxes to toolbar
        self.show_background_cb = QCheckBox("Background")
        self.show_background_cb.setChecked(True)
        toolbar.addWidget(self.show_background_cb)

        self.show_grid_cb = QCheckBox("Grid")
        self.show_grid_cb.setChecked(False)
        toolbar.addWidget(self.show_grid_cb)

        self.show_info_cb = QCheckBox("Info")
        self.show_info_cb.setChecked(True)
        toolbar.addWidget(self.show_info_cb)

        # Create UI elements that were in side panels (not added to UI, but needed for compatibility)
        self.point_x_spinbox = QDoubleSpinBox()
        self.point_x_spinbox.setRange(-10000, 10000)
        self.point_x_spinbox.setDecimals(3)
        self.point_x_spinbox.setEnabled(False)

        self.point_y_spinbox = QDoubleSpinBox()
        self.point_y_spinbox.setRange(-10000, 10000)
        self.point_y_spinbox.setDecimals(3)
        self.point_y_spinbox.setEnabled(False)

        self.point_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.point_size_slider.setMinimum(2)
        self.point_size_slider.setMaximum(20)
        self.point_size_slider.setValue(6)

        self.line_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.line_width_slider.setMinimum(1)
        self.line_width_slider.setMaximum(10)
        self.line_width_slider.setValue(2)

        # Create playback controls (not added to UI, but needed for compatibility)
        self.btn_first_frame = QPushButton()
        self.btn_first_frame.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))

        self.btn_prev_frame = QPushButton()
        self.btn_prev_frame.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))

        self.btn_play_pause = QPushButton()
        self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play_pause.setCheckable(True)

        self.btn_next_frame = QPushButton()
        self.btn_next_frame.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))

        self.btn_last_frame = QPushButton()
        self.btn_last_frame.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))

        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setMinimum(1)
        self.fps_spinbox.setMaximum(120)
        self.fps_spinbox.setValue(24)
        self.fps_spinbox.setSuffix(" fps")

        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(1)
        self.frame_slider.setMaximum(1000)
        self.frame_slider.setValue(1)

        self.total_frames_label = QLabel("1")
        self.point_count_label = QLabel("Points: 0")
        self.selected_count_label = QLabel("Selected: 0")
        self.bounds_label = QLabel("Bounds: N/A")

        # Add stretch to push remaining items to the right
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
        toolbar.addWidget(spacer)

    def _init_central_widget(self) -> None:
        """Initialize the central widget with full-width curve view and bottom timeline."""
        # Create main central widget with vertical layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create the main curve view area (full width, no side panels)
        self.curve_container = self._create_curve_view_container()

        # Add curve container directly to main layout (no splitter needed)
        main_layout.addWidget(self.curve_container)

        # Set the central widget
        self.setCentralWidget(central_widget)

    def _create_timeline_panel(self) -> QWidget:
        """Create the timeline control panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Timeline group - use ModernCard if available
        try:
            from ui.modern_widgets import ModernCard

            timeline_group = ModernCard("Timeline")
            timeline_layout = timeline_group.content_layout
        except ImportError:
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

        if not hasattr(timeline_group, "content_layout"):
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

        # Ensure the curve widget can receive keyboard focus
        self.curve_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout.addWidget(self.curve_widget)

        # Set focus to curve widget after creation
        QTimer.singleShot(100, lambda: self.curve_widget.setFocus())

        logger.info("CurveViewWidget created and integrated")

        return container

    def _create_properties_panel(self) -> QWidget:
        """Create the properties/info panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Point Properties group - use ModernCard if available
        try:
            from ui.modern_widgets import ModernCard

            point_group = ModernCard("Point Properties")
            point_layout = point_group.content_layout
        except ImportError:
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

        if not hasattr(point_group, "content_layout"):
            point_group.setLayout(point_layout)
        layout.addWidget(point_group)

        # View Settings group - use ModernCard if available
        try:
            from ui.modern_widgets import ModernCard

            view_group = ModernCard("View Settings")
            view_layout = view_group.content_layout
        except ImportError:
            view_group = QGroupBox("View Settings")
            view_layout = QVBoxLayout()

        # Display options
        self.show_background_cb = QCheckBox("Show Background")
        self.show_background_cb.setChecked(True)
        self.show_background_cb.stateChanged.connect(self._on_view_option_changed)
        view_layout.addWidget(self.show_background_cb)

        self.show_grid_cb = QCheckBox("Show Grid")
        self.show_grid_cb.setChecked(False)
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

        if not hasattr(view_group, "content_layout"):
            view_group.setLayout(view_layout)
        layout.addWidget(view_group)

        # Curve Info group - use ModernCard if available
        try:
            from ui.modern_widgets import ModernCard

            info_group = ModernCard("Curve Information")
            info_layout = info_group.content_layout
        except ImportError:
            info_group = QGroupBox("Curve Information")
            info_layout = QVBoxLayout()

        self.point_count_label = QLabel("Points: 0")
        info_layout.addWidget(self.point_count_label)

        self.selected_count_label = QLabel("Selected: 0")
        info_layout.addWidget(self.selected_count_label)

        self.bounds_label = QLabel("Bounds: N/A")
        self.bounds_label.setWordWrap(True)
        info_layout.addWidget(self.bounds_label)

        if not hasattr(info_group, "content_layout"):
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

    def _setup_tab_order(self) -> None:
        """Set up proper tab order for keyboard navigation."""
        # Only set tab order for widgets that are actually in the UI
        # Toolbar controls
        self.setTabOrder(self.frame_spinbox, self.show_background_cb)
        self.setTabOrder(self.show_background_cb, self.show_grid_cb)
        self.setTabOrder(self.show_grid_cb, self.show_info_cb)

        # Curve view widget (main area)
        if self.curve_widget:
            self.setTabOrder(self.show_info_cb, self.curve_widget)

        logger.debug("Tab order configured for keyboard navigation")

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

    @Slot(int)
    def _on_frame_changed(self, value: int) -> None:
        """Handle frame spinbox value change."""
        logger.debug(f"[FRAME] Frame changed to: {value}")
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(value)
        self.frame_slider.blockSignals(False)
        self.state_manager.current_frame = value
        logger.debug(f"[FRAME] State manager current_frame set to: {self.state_manager.current_frame}")

        # Update background image if image sequence is loaded
        self._update_background_image_for_frame(value)

        # Update curve widget to highlight current frame's point
        if self.curve_widget:
            # Invalidate caches to ensure proper repainting with new frame highlight
            self.curve_widget._invalidate_caches()
            self.curve_widget.update()

    @Slot(int)
    def _on_slider_changed(self, value: int) -> None:
        """Handle frame slider value change."""
        self.frame_spinbox.blockSignals(True)
        self.frame_spinbox.setValue(value)
        self.frame_spinbox.blockSignals(False)
        self.state_manager.current_frame = value

        # Update background image if image sequence is loaded
        self._update_background_image_for_frame(value)

        # Update curve widget to highlight current frame's point
        if self.curve_widget:
            # Invalidate caches to ensure proper repainting with new frame highlight
            self.curve_widget._invalidate_caches()
            self.curve_widget.update()

    @Slot()
    def _on_first_frame(self) -> None:
        """Go to first frame."""
        self.frame_spinbox.setValue(1)

    @Slot()
    def _on_prev_frame(self) -> None:
        """Go to previous frame."""
        current = self.frame_spinbox.value()
        if current > 1:
            self.frame_spinbox.setValue(current - 1)

    @Slot()
    def _on_next_frame(self) -> None:
        """Go to next frame."""
        current = self.frame_spinbox.value()
        if current < self.frame_spinbox.maximum():
            self.frame_spinbox.setValue(current + 1)

    @Slot()
    def _on_last_frame(self) -> None:
        """Go to last frame."""
        self.frame_spinbox.setValue(self.frame_spinbox.maximum())

    @Slot(bool)
    def _on_play_pause(self, checked: bool) -> None:
        """Handle play/pause toggle."""
        if checked:
            # Start playback
            fps = self.fps_spinbox.value()
            interval = int(1000 / fps)  # Convert FPS to milliseconds
            self.playback_timer.start(interval)
            self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.play_toggled.emit(True)
        else:
            # Stop playback
            self.playback_timer.stop()
            self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.play_toggled.emit(False)

    @Slot()
    def _on_playback_timer(self) -> None:
        """Handle playback timer tick."""
        current = self.frame_spinbox.value()
        if current >= self.frame_spinbox.maximum():
            # Loop back to start
            self.frame_spinbox.setValue(1)
        else:
            self.frame_spinbox.setValue(current + 1)

    @Slot(int)
    def _on_fps_changed(self, value: int) -> None:
        """Handle FPS change."""
        if self.playback_timer.isActive():
            interval = int(1000 / value)
            self.playback_timer.setInterval(interval)
        self.frame_rate_changed.emit(value)

    # ==================== View Control Handlers ====================

    @Slot()
    def _on_view_option_changed(self) -> None:
        """Handle view option checkbox changes."""
        # Now handled by dedicated curve widget handlers
        self._update_curve_view_options()
        logger.debug(
            f"View options changed - Background: {self.show_background_cb.isChecked()}, "
            f"Grid: {self.show_grid_cb.isChecked()}, "
            f"Info: {self.show_info_cb.isChecked()}"
        )

    @Slot(int)
    def _on_point_size_changed(self, value: int) -> None:
        """Handle point size slider change."""
        # Now handled by dedicated curve widget handler
        self._update_curve_point_size(value)
        logger.debug(f"Point size changed to: {value}")

    @Slot(int)
    def _on_line_width_changed(self, value: int) -> None:
        """Handle line width slider change."""
        # Now handled by dedicated curve widget handler
        self._update_curve_line_width(value)
        logger.debug(f"Line width changed to: {value}")

    # ==================== Action Handlers ====================

    @Slot()
    def _on_action_new(self) -> None:
        """Handle new file action."""
        if self.state_manager.is_modified:
            if not self.services.confirm_action("Current curve has unsaved changes. Continue?", self):
                return

        # Clear curve widget data
        if self.curve_widget:
            self.curve_widget.set_curve_data([])

        self.state_manager.reset_to_defaults()
        self._update_ui_state()
        self.status_bar.showMessage("New curve created", 2000)

    @Slot()
    def _on_action_open(self) -> None:
        """Handle open file action."""
        # Check for unsaved changes
        if self.state_manager.is_modified:
            if not self.services.confirm_action("Current curve has unsaved changes. Continue?", self):
                return

        # Load data using service facade
        data = self.services.load_track_data(self)
        if data:
            # Update curve widget with new data
            if self.curve_widget:
                self.curve_widget.set_curve_data(data)

            # Update state manager
            self.state_manager.set_track_data(data, mark_modified=False)

            # Update frame range based on loaded data
            if data:
                max_frame = max(point[0] for point in data)
                self.frame_slider.setMaximum(max_frame)
                self.frame_spinbox.setMaximum(max_frame)
                self.total_frames_label.setText(str(max_frame))
                # CRITICAL: Update state manager's total frames!
                self.state_manager.total_frames = max_frame

            self._update_ui_state()
            self.status_bar.showMessage("File loaded successfully", 2000)

    @Slot()
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

    @Slot()
    def _on_action_save_as(self) -> None:
        """Handle save as action."""
        # Get current data from curve widget
        data = self._get_current_curve_data()
        if self.services.save_track_data(data, self):
            self.state_manager.is_modified = False
            self.status_bar.showMessage("File saved successfully", 2000)

    def _load_burger_tracking_data(self) -> None:
        """Auto-load burger footage and tracking data if available using background thread."""
        from pathlib import Path

        # Get the current working directory
        base_dir = Path(__file__).parent.parent

        # Check for tracking data file
        tracking_file = base_dir / "2DTrackData.txt"
        if not tracking_file.exists():
            # Also check in footage directory
            tracking_file = base_dir / "footage" / "Burger" / "2DTrackData.txt"

        # Check for burger footage directory
        footage_dir = base_dir / "footage" / "Burger"

        # Determine what files need to be loaded
        tracking_file_path = str(tracking_file) if tracking_file.exists() else None
        image_dir_path = str(footage_dir) if footage_dir.exists() else None

        if not tracking_file_path and not image_dir_path:
            logger.debug("No burger tracking data or footage found")
            return

        # Clean up any existing thread
        self._cleanup_file_load_thread()

        # Create worker and thread
        self.file_load_worker = FileLoadWorker(tracking_file_path, image_dir_path)
        self.file_load_thread = QThread()

        # Move worker to thread
        self.file_load_worker.moveToThread(self.file_load_thread)

        # Connect worker signals
        self.file_load_worker.tracking_data_loaded.connect(self._on_tracking_data_loaded)
        self.file_load_worker.image_sequence_loaded.connect(self._on_image_sequence_loaded)
        self.file_load_worker.progress_updated.connect(self._on_file_load_progress)
        self.file_load_worker.error_occurred.connect(self._on_file_load_error)
        self.file_load_worker.finished.connect(self._on_file_load_finished)

        # Connect thread signals with proper cleanup chain
        self.file_load_thread.started.connect(self.file_load_worker.run)
        # Ensure proper cleanup sequence
        self.file_load_worker.finished.connect(self.file_load_thread.quit)
        self.file_load_worker.finished.connect(self.file_load_worker.deleteLater)
        if self.file_load_thread is not None:
            self.file_load_thread.finished.connect(self.file_load_thread.deleteLater)

        # Start the background loading
        self.status_bar.showMessage("Loading files in background...", 0)
        self.file_load_thread.start()
        logger.info("Started background file loading thread")

    def _cleanup_file_load_thread(self) -> None:
        """Clean up existing file load thread and worker."""
        if self.file_load_worker:
            self.file_load_worker.stop()
            self.file_load_worker = None

        if self.file_load_thread and self.file_load_thread.isRunning():
            self.file_load_thread.quit()
            # Wait longer for graceful shutdown
            if not self.file_load_thread.wait(5000):  # Wait up to 5 seconds
                # Don't terminate - log warning and let it finish naturally
                logger.warning("File load thread did not quit gracefully within 5 seconds")
                # Still set to None to avoid memory leak, thread will clean itself up
            self.file_load_thread = None

    def _on_tracking_data_loaded(self, data: list) -> None:
        """Handle tracking data loaded in background thread."""
        if data and self.curve_widget:
            logger.debug(f"[DATA] Loaded {len(data)} points from background thread")
            # Log first few points for debugging
            for i in range(min(3, len(data))):
                logger.debug(f"[DATA] Point {i}: {data[i]}")

            self.curve_widget.set_curve_data(data)
            self.state_manager.set_track_data(data, mark_modified=False)
            logger.info(f"Loaded {len(data)} tracking points from background thread")

            # Update frame range based on data
            if data:
                max_frame = max(point[0] for point in data)
                self.frame_slider.setMaximum(max_frame)
                self.frame_spinbox.setMaximum(max_frame)
                self.total_frames_label.setText(str(max_frame))
                # Update state manager's total frames
                self.state_manager.total_frames = max_frame

    def _on_image_sequence_loaded(self, image_dir: str, image_files: list[str]) -> None:
        """Handle image sequence loaded in background thread."""
        if image_files and self.curve_widget:
            # Store image sequence info
            self.image_directory = image_dir
            self.image_filenames = image_files
            self.current_image_idx = 0

            # Load the first image as background
            if image_files:
                from pathlib import Path

                first_image_path = Path(image_dir) / image_files[0]
                pixmap = QPixmap(str(first_image_path))

                if not pixmap.isNull():
                    self.curve_widget.background_image = pixmap
                    self.curve_widget.image_width = pixmap.width()
                    self.curve_widget.image_height = pixmap.height()
                    self.curve_widget.show_background = True

                    # Fit the image to view
                    self.curve_widget.fit_to_background_image()

                    logger.info(f"Loaded background image: {image_files[0]} ({pixmap.width()}x{pixmap.height()})")

            logger.info(f"Loaded {len(image_files)} images from background thread")

    def _on_file_load_progress(self, progress: int, message: str) -> None:
        """Handle file loading progress updates."""
        self.status_bar.showMessage(f"{message} ({progress}%)", 0)
        logger.debug(f"File load progress: {progress}% - {message}")

    def _on_file_load_error(self, error_message: str) -> None:
        """Handle file loading errors."""
        logger.error(f"File loading error: {error_message}")
        self.status_bar.showMessage(f"Error: {error_message}", 5000)

    def _on_file_load_finished(self) -> None:
        """Handle file loading completion."""
        self.status_bar.showMessage("File loading completed", 2000)
        logger.info("Background file loading finished")

        # Properly clean up thread resources
        if self.file_load_thread:
            self.file_load_thread.quit()
            # Don't set to None yet - let deleteLater handle it
        # Worker will be deleted by deleteLater connection

    def _update_background_image_for_frame(self, frame: int) -> None:
        """Update the background image based on the current frame."""
        if not hasattr(self, "image_filenames") or not self.image_filenames:
            return

        if not self.curve_widget:
            return

        # Find the appropriate image for this frame (1-based indexing)
        image_idx = frame - 1  # Convert to 0-based index

        # Clamp to valid range
        if image_idx < 0:
            image_idx = 0
        elif image_idx >= len(self.image_filenames):
            image_idx = len(self.image_filenames) - 1

        # Load the corresponding image
        if 0 <= image_idx < len(self.image_filenames):
            from pathlib import Path

            from PySide6.QtGui import QPixmap

            image_path = Path(self.image_directory) / self.image_filenames[image_idx]
            pixmap = QPixmap(str(image_path))

            if not pixmap.isNull():
                self.curve_widget.background_image = pixmap
                self.curve_widget.update()
                logger.debug(f"Updated background to frame {frame}: {self.image_filenames[image_idx]}")

    @Slot()
    def _on_action_undo(self) -> None:
        """Handle undo action."""
        self.services.undo()
        self.status_bar.showMessage("Undo", 1000)

    @Slot()
    def _on_action_redo(self) -> None:
        """Handle redo action."""
        self.services.redo()
        self.status_bar.showMessage("Redo", 1000)

    @Slot()
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

    @Slot()
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

    @Slot()
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
                if not hasattr(self, "_point_spinbox_connected"):
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
                    self.bounds_label.setText(f"Bounds:\nX: [{min_x:.2f}, {max_x:.2f}]\nY: [{min_y:.2f}, {max_y:.2f}]")
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
                    f"Bounds:\nX: [{bounds[0]:.2f}, {bounds[2]:.2f}]\nY: [{bounds[1]:.2f}, {bounds[3]:.2f}]"
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

    def eventFilter(self, obj, event) -> bool:
        """Event filter to handle key event redirection."""
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            logger.debug(f"[EVENT_FILTER] KeyPress detected: key={key}, object={obj.__class__.__name__}")

            # Handle C key specifically without modifiers
            if key == Qt.Key.Key_C and not event.modifiers():
                # If C key pressed on curve widget, let it handle normally
                if obj == self.curve_widget:
                    logger.debug("[EVENT_FILTER] C key on curve_widget, passing through")
                    return super().eventFilter(obj, event)  # Proper delegation

                # If C key pressed elsewhere, redirect to curve widget
                elif obj != self.curve_widget and self.curve_widget:
                    logger.debug("[EVENT_FILTER] Redirecting C key to curve_widget")
                    self.curve_widget.setFocus()
                    QApplication.sendEvent(self.curve_widget, event)
                    return True  # Consume original event to prevent double handling

        return super().eventFilter(obj, event)  # Proper delegation to parent

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

    @Slot(int)
    def _update_curve_point_size(self, value: int) -> None:
        """Update curve widget point size."""
        if self.curve_widget:
            self.curve_widget.point_radius = value
            self.curve_widget.selected_point_radius = value + 2
            self.curve_widget.update()
        self.point_size_label.setText(str(value))

    @Slot(int)
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

    def _get_current_curve_data(self) -> list[tuple[int, float, float]] | list[tuple[int, float, float, str]]:
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

    def set_curve_view(self, curve_view: CurveViewWidget | None) -> None:
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

    def set_centering_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-centering on frame change.

        Args:
            enabled: Whether to enable auto-centering
        """
        # Store the centering state
        if hasattr(self, "state_manager"):
            self.state_manager.auto_center_enabled = enabled

        # Update the curve widget if available
        if hasattr(self, "curve_widget") and self.curve_widget:
            if hasattr(self.curve_widget, "set_auto_center"):
                self.curve_widget.set_auto_center(enabled)

        # Log the state change
        logger.info(f"Auto-centering {'enabled' if enabled else 'disabled'}")

        # Update status bar
        if hasattr(self, "statusBar"):
            self.statusBar().showMessage(f"Auto-center on frame change: {'ON' if enabled else 'OFF'}", 3000)

    def apply_smooth_operation(self) -> None:
        """Apply smoothing operation to selected points in the curve.

        Shows a dialog to get smoothing parameters and applies smoothing
        to the currently selected points or all points if none selected.
        """
        if not hasattr(self, "curve_widget") or not self.curve_widget:
            logger.warning("No curve widget available for smoothing")
            return

        # Get the current curve data
        curve_data = getattr(self.curve_widget, "curve_data", [])
        if not curve_data:
            QMessageBox.information(self, "No Data", "No curve data to smooth.")
            return

        # Get selected points or use all points
        selected_indices = getattr(self.curve_widget, "selected_indices", [])
        if not selected_indices:
            # Ask if user wants to smooth all points
            reply = QMessageBox.question(
                self,
                "No Selection",
                "No points selected. Apply smoothing to all points?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            selected_indices = list(range(len(curve_data)))

        # Get smoothing window size from user
        from services.ui_service import get_ui_service

        ui_service = get_ui_service()
        if ui_service:
            window_size = ui_service.get_smooth_window_size(self)
            if window_size is None:
                return  # User cancelled
        else:
            # Fallback to simple input dialog
            window_size, ok = QInputDialog.getInt(self, "Smoothing Window Size", "Enter window size (3-15):", 5, 3, 15)
            if not ok:
                return

        # Apply smoothing using DataService
        from services.data_service import get_data_service

        data_service = get_data_service()
        if data_service:
            # Extract points to smooth
            points_to_smooth = [curve_data[i] for i in selected_indices]

            # Apply smoothing
            smoothed_points = data_service.smooth_moving_average(points_to_smooth, window_size)

            # Update the curve data
            new_curve_data = list(curve_data)
            for i, idx in enumerate(selected_indices):
                if i < len(smoothed_points):
                    new_curve_data[idx] = smoothed_points[i]

            # Set the new data
            self.curve_widget.set_curve_data(new_curve_data)

            # Mark as modified
            if hasattr(self, "state_manager"):
                self.state_manager.is_modified = True

            # Update status
            self.statusBar().showMessage(
                f"Applied smoothing to {len(selected_indices)} points (window size: {window_size})", 3000
            )
            logger.info(f"Smoothing applied to {len(selected_indices)} points")
        else:
            QMessageBox.warning(self, "Service Error", "Data service not available for smoothing.")

    def closeEvent(self, event) -> None:
        """Handle window close event with proper thread cleanup."""
        # Clean up any running background threads
        self._cleanup_file_load_thread()

        # Accept the close event
        event.accept()
        logger.info("MainWindow closed with proper cleanup")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
