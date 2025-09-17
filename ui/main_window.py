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
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, cast, override

if TYPE_CHECKING:
    from ui.timeline_tabs import TimelineTabWidget

    from .curve_view_widget import CurveViewWidget
    from .service_facade import ServiceFacade

# Import PySide6 modules
from PySide6.QtCore import QEvent, QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QKeyEvent,
    QKeySequence,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDockWidget,
    QDoubleSpinBox,
    QFrame,
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

from core.type_aliases import CurveDataList

# Import local modules
# CurveView removed - using CurveViewWidget
from .curve_view_widget import CurveViewWidget
from .dark_theme_stylesheet import get_dark_theme_stylesheet
from .keyboard_shortcuts import ShortcutManager
from .state_manager import StateManager
from .tracking_points_panel import TrackingPointsPanel

# Import refactored components
from .ui_components import UIComponents
from .ui_constants import MAX_HISTORY_SIZE

# Configure logger for this module
logger = logging.getLogger("main_window")


class PlaybackMode(Enum):
    """Enumeration for oscillating playback modes."""

    STOPPED = auto()
    PLAYING_FORWARD = auto()
    PLAYING_BACKWARD = auto()


@dataclass
class PlaybackState:
    """State management for oscillating timeline playback."""

    mode: PlaybackMode = PlaybackMode.STOPPED
    fps: int = 12
    current_frame: int = 1
    min_frame: int = 1
    max_frame: int = 100
    loop_boundaries: bool = True  # True for oscillation, False for loop-to-start


class FileLoadSignals(QObject):
    """Signal emitter for thread-safe communication from Python thread to Qt main thread."""

    # Signals for communicating with main thread
    tracking_data_loaded: Signal = Signal(list)  # Emits list of tracking data points
    multi_point_data_loaded: Signal = Signal(dict)  # Emits dict of multi-point tracking data
    image_sequence_loaded: Signal = Signal(str, list)  # Emits directory path and list of filenames
    progress_updated: Signal = Signal(int, str)  # Emits progress percentage and status message
    error_occurred: Signal = Signal(str)  # Emits error message
    finished: Signal = Signal()  # Emits when all loading is complete


class FileLoadWorker:
    """Worker class for loading files in a Python background thread (not QThread)."""

    def __init__(self, signals: FileLoadSignals):
        """Initialize worker with signal emitter."""
        self.signals: FileLoadSignals = signals  # QObject for emitting signals
        self.tracking_file_path: str | None = None
        self.image_dir_path: str | None = None
        self._should_stop: bool = False
        self._work_ready: bool = False
        self._work_ready_lock: threading.Lock = threading.Lock()
        self._stop_lock: threading.Lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def stop(self) -> None:
        """Request the worker to stop processing."""
        with self._stop_lock:
            self._should_stop = True
        # Wait for thread to finish if it's running
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def start_work(self, tracking_file_path: str | None, image_dir_path: str | None) -> None:
        """Start new file loading work in a Python thread."""
        # Stop any existing work
        self.stop()

        # Set new work parameters
        self.tracking_file_path = tracking_file_path
        self.image_dir_path = image_dir_path
        with self._work_ready_lock:
            self._work_ready = True
        self._should_stop = False

        # Start new thread
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def _check_should_stop(self) -> bool:
        """Thread-safe check of stop flag."""
        with self._stop_lock:
            return self._should_stop

    def run(self) -> None:
        """Main worker method that runs in background Python thread."""
        # Check if there's work ready
        with self._work_ready_lock:
            if not self._work_ready:
                return  # No work to do
            self._work_ready = False

        logger.info(f"[PYTHON-THREAD] Worker.run() starting in Python thread: {threading.current_thread().name}")
        try:
            total_tasks = 0
            current_task = 0

            # Count tasks to do
            if self.tracking_file_path:
                total_tasks += 1
            if self.image_dir_path:
                total_tasks += 1

            if total_tasks == 0:
                self.signals.finished.emit()
                return

            # Load tracking data if requested
            if self.tracking_file_path and not self._check_should_stop():
                self.signals.progress_updated.emit(0, "Loading tracking data...")
                try:
                    # Check if it's a multi-point file
                    is_multi_point = False
                    try:
                        with open(self.tracking_file_path) as f:
                            content = f.read(500)  # Read first 500 chars to detect format
                            # Multi-point files have "Point" followed by a name
                            is_multi_point = "Point" in content and ("Point1" in content or "Point01" in content)
                    except OSError:
                        pass

                    multi_data = {}
                    data = []

                    if is_multi_point:
                        # Load as multi-point data
                        multi_data = self._load_multi_point_data_direct(
                            self.tracking_file_path, flip_y=True, image_height=720
                        )
                        if multi_data:
                            # Emit multi-point data signal
                            self.signals.multi_point_data_loaded.emit(multi_data)

                            # Also emit first point's data for compatibility
                            first_point = list(multi_data.keys())[0] if multi_data else None
                            data = multi_data.get(first_point, []) if first_point else []

                            logger.info(
                                f"[PYTHON-THREAD] Loaded {len(multi_data)} tracking points from multi-point file"
                            )
                    else:
                        # Load as single-point data
                        data = self._load_2dtrack_data_direct(self.tracking_file_path, flip_y=True, image_height=720)
                        if data:
                            logger.info(
                                f"[PYTHON-THREAD] Emitting tracking_data_loaded from Python thread: {threading.current_thread().name}"
                            )
                            self.signals.tracking_data_loaded.emit(data)

                    current_task += 1
                    progress = int((current_task / total_tasks) * 100)

                    if is_multi_point and multi_data:
                        total_points = sum(len(traj) for traj in multi_data.values())
                        self.signals.progress_updated.emit(
                            progress, f"Loaded {len(multi_data)} trajectories, {total_points} total points"
                        )
                    else:
                        self.signals.progress_updated.emit(
                            progress, f"Loaded {len(data) if data else 0} tracking points"
                        )
                except Exception as e:
                    self.signals.error_occurred.emit(f"Failed to load tracking data: {str(e)}")

            # Load image sequence if requested
            if self.image_dir_path and not self._check_should_stop():
                self.signals.progress_updated.emit(int((current_task / total_tasks) * 100), "Loading image sequence...")
                try:
                    # Directly scan for image files without creating DataService
                    image_files = self._scan_image_directory(self.image_dir_path)
                    if image_files:
                        logger.info(
                            f"[PYTHON-THREAD] Emitting image_sequence_loaded from Python thread: {threading.current_thread().name}"
                        )
                        self.signals.image_sequence_loaded.emit(self.image_dir_path, image_files)
                    current_task += 1
                    self.signals.progress_updated.emit(100, f"Loaded {len(image_files) if image_files else 0} images")
                except Exception as e:
                    self.signals.error_occurred.emit(f"Failed to load image sequence: {str(e)}")

        except Exception as e:
            self.signals.error_occurred.emit(f"Unexpected error in file loading: {str(e)}")
        finally:
            logger.info("[PYTHON-THREAD] About to emit finished signal")
            logger.info(f"[PYTHON-THREAD] Current Python thread: {threading.current_thread().name}")
            self.signals.finished.emit()
            logger.info("[PYTHON-THREAD] finished.emit() completed")

    def _load_2dtrack_data_direct(
        self, file_path: str, flip_y: bool = False, image_height: float = 720
    ) -> list[tuple[int, float, float]] | list[tuple[int, float, float, str]]:
        """Load 2D tracking data directly without using DataService.

        Handles 2DTrackData.txt format with 4-line header:
        Line 1: Version
        Line 2: Identifier 1
        Line 3: Identifier 2
        Line 4: Number of points
        Lines 5+: frame_number x_coordinate y_coordinate [status]

        Args:
            file_path: Path to the tracking data file
            flip_y: If True, flip Y coordinates (image_height - y)
            image_height: Height of the image for Y-flip calculation
        """
        data = []
        try:
            with open(file_path) as f:
                lines = f.readlines()

                # Detect if this is a 2DTrackData.txt format file by checking first few lines
                has_header = False
                if len(lines) > 4:
                    # Check if line 4 looks like a point count and line 5 starts with data
                    try:
                        # Try to parse line 4 as a single integer (point count)
                        int(lines[3].strip())
                        # Try to parse line 5 as data (frame x y)
                        parts = lines[4].strip().split()
                        if len(parts) >= 3:
                            int(parts[0])
                            float(parts[1])
                            float(parts[2])
                            has_header = True
                    except (ValueError, IndexError):
                        pass

                # Process lines, skipping header if detected
                start_line = 4 if has_header else 0
                for line in lines[start_line:]:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            frame = int(parts[0])
                            x = float(parts[1])
                            y = float(parts[2])

                            # Flip Y coordinate if requested (3DEqualizer convention)
                            if flip_y:
                                y = image_height - y

                            # Handle optional status field
                            if len(parts) >= 4:
                                status = parts[3]
                                data.append((frame, x, y, status))
                            else:
                                data.append((frame, x, y))
                        except ValueError:
                            # Skip lines that can't be parsed as data
                            continue
        except Exception as e:
            logger.error(f"Error loading tracking data: {e}")
            raise
        return data

    def _load_multi_point_data_direct(
        self, file_path: str, flip_y: bool = False, image_height: float = 720
    ) -> dict[str, list[tuple[int, float, float]]]:
        """Load multi-point tracking data (2DTrackDatav2 format).

        Returns a dictionary where keys are point names and values are trajectories.
        """
        tracked_data = {}

        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Look for point name lines (e.g., "Point1", "Point02")
                if line.startswith("Point"):
                    point_name = line

                    # Check if we have the required header lines
                    if i - 1 >= 0 and i + 2 < len(lines):
                        try:
                            # Format: version, point_name, identifier, count
                            _ = lines[i + 1].strip()  # identifier
                            point_count = int(lines[i + 2].strip())

                            # Read trajectory data
                            trajectory = []
                            data_start = i + 3

                            for j in range(data_start, min(data_start + point_count, len(lines))):
                                data_line = lines[j].strip()
                                if not data_line:
                                    continue

                                parts = data_line.split()
                                if len(parts) >= 3:
                                    try:
                                        frame = int(parts[0])
                                        x = float(parts[1])
                                        y = float(parts[2])

                                        # Flip Y coordinate if requested
                                        if flip_y:
                                            y = image_height - y

                                        trajectory.append((frame, x, y))
                                    except ValueError:
                                        continue

                            if trajectory:
                                tracked_data[point_name] = trajectory

                            # Move to next point
                            i = data_start + point_count - 1
                        except (ValueError, IndexError):
                            pass

                i += 1

        except Exception as e:
            logger.error(f"Error loading multi-point tracking data: {e}")
            # Fall back to single point loading
            return {}

        return tracked_data

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
    play_toggled: Signal = Signal(bool)
    frame_rate_changed: Signal = Signal(int)

    # Widget type annotations - initialized in init methods
    frame_spinbox: QSpinBox | None = None
    total_frames_label: QLabel | None = None
    frame_slider: QSlider | None = None
    timeline_tabs: "TimelineTabWidget | None" = None
    # Removed orphaned playback button attributes - they were never used
    btn_play_pause: QPushButton | None = None  # Used for playback control (not visible but functional)
    fps_spinbox: QSpinBox | None = None
    playback_timer: QTimer | None = None
    curve_widget: "CurveViewWidget | None" = None
    selected_point_label: QLabel | None = None
    point_x_spinbox: QDoubleSpinBox | None = None
    point_y_spinbox: QDoubleSpinBox | None = None
    show_background_cb: QCheckBox | None = None
    show_grid_cb: QCheckBox | None = None
    show_info_cb: QCheckBox | None = None
    show_tooltips_cb: QCheckBox | None = None
    point_size_label: QLabel | None = None
    line_width_label: QLabel | None = None
    point_size_slider: QSlider | None = None
    line_width_slider: QSlider | None = None

    # MainWindowProtocol required attributes
    # Note: selected_indices and curve_data are provided as properties below
    point_name: str = "default_point"
    point_color: str = "#FF0000"
    undo_button: QPushButton | None = None  # Will be created from action
    redo_button: QPushButton | None = None  # Will be created from action
    save_button: QPushButton | None = None  # Will be created from action
    ui_components: object | None = None  # UIComponents container

    def __init__(self, parent: QWidget | None = None):
        """Initialize the MainWindow with enhanced UI functionality."""
        super().__init__(parent)

        # Setup basic window properties
        self.setWindowTitle("CurveEditor")
        self.setMinimumSize(1024, 768)
        self.resize(1400, 900)

        # Apply dark theme to entire application
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            # Use Fusion style for better dark theme support
            app.setStyle("Fusion")
            # Apply the dark theme stylesheet
            app.setStyleSheet(get_dark_theme_stylesheet())
            logger.info("Applied dark theme to application")

        # Initialize managers
        self.state_manager: StateManager = StateManager(self)
        self.shortcut_manager: ShortcutManager = ShortcutManager(self)

        # Initialize service facade
        from services.service_protocols import MainWindowProtocol

        from .service_facade import get_service_facade

        self.services: ServiceFacade = get_service_facade(cast(MainWindowProtocol, cast(object, self)))

        # Initialize UI components container for organized widget management
        self.ui: UIComponents = UIComponents(self)

        # Multi-point tracking data
        self.tracked_data: dict[str, CurveDataList] = {}  # All tracking points
        self.active_points: list[str] = []  # Currently selected points

        # Initialize UI components
        self._init_actions()
        self._init_toolbar()
        self._init_central_widget()
        self._init_dock_widgets()
        self._init_status_bar()

        # Initialize legacy curve view and track quality UI
        self.curve_view: CurveViewWidget | None = None  # Legacy curve view - no longer used
        self.track_quality_ui: QWidget | None = None  # Legacy track quality UI

        # Initialize history tracking
        self.history: list[dict[str, object]] = []  # Each history entry is a dict with curve data
        self.history_index: int = -1
        self.max_history_size: int = MAX_HISTORY_SIZE

        # Initialize background thread management
        self.file_load_worker: FileLoadWorker | None = None
        self.file_load_signals: FileLoadSignals | None = None
        self._file_loading: bool = False  # Track if file loading is in progress

        # Initialize persistent worker and thread for Keep Worker Alive strategy
        self._init_persistent_worker()

        # Initialize centering state
        self.auto_center_enabled: bool = False

        # Initialize image sequence state
        self.image_directory: str | None = None
        self.image_filenames: list[str] = []
        self.current_image_idx: int = 0

        # Initialize playback timer for oscillating timeline playback
        self.playback_timer = QTimer(self)
        _ = self.playback_timer.timeout.connect(self._on_playback_timer)

        # Initialize playback state for oscillating playback
        self.playback_state: PlaybackState = PlaybackState()

        # Initialize dynamic instance variables that will be checked later
        self._point_spinbox_connected: bool = False
        self._stored_tooltips: dict[QWidget, str] = {}

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
        _ = self._load_burger_tracking_data()

        # Initialize tooltips as disabled by default
        self._toggle_tooltips()

        logger.info("MainWindow initialized successfully")

    def _init_persistent_worker(self) -> None:
        """Initialize worker with Python threading (no QThread)."""
        logger.info("[PYTHON-THREAD] Initializing file loader with Python threading")

        # Create signal emitter (stays in main thread)
        self.file_load_signals = FileLoadSignals()

        # Create worker (plain Python class, not QObject)
        self.file_load_worker = FileLoadWorker(self.file_load_signals)

        # Connect signals (emitter is in main thread, so this is safe)
        self.file_load_signals.tracking_data_loaded.connect(self._on_tracking_data_loaded)
        self.file_load_signals.multi_point_data_loaded.connect(self._on_multi_point_data_loaded)
        self.file_load_signals.image_sequence_loaded.connect(self._on_image_sequence_loaded)
        self.file_load_signals.progress_updated.connect(self._on_file_load_progress)
        self.file_load_signals.error_occurred.connect(self._on_file_load_error)
        self.file_load_signals.finished.connect(self._on_file_load_finished)

        logger.info("[PYTHON-THREAD] File loader initialized with Python threading")

    def _init_actions(self) -> None:
        """Initialize all QActions for menus and toolbars."""
        # File actions
        self.action_new: QAction = QAction("New", self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.setStatusTip("Create a new curve")
        self.action_new.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))

        self.action_open: QAction = QAction("Open", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.setStatusTip("Open an existing curve file")
        self.action_open.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))

        self.action_save: QAction = QAction("Save", self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.setStatusTip("Save the current curve")
        self.action_save.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DriveFDIcon))

        self.action_save_as: QAction = QAction("Save As...", self)
        self.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_as.setStatusTip("Save the curve with a new name")

        # Edit actions
        self.action_undo: QAction = QAction("Undo", self)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.setStatusTip("Undo the last action")
        self.action_undo.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.action_undo.setEnabled(False)

        self.action_redo: QAction = QAction("Redo", self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.setStatusTip("Redo the previously undone action")
        self.action_redo.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.action_redo.setEnabled(False)

        # View actions
        self.action_zoom_in: QAction = QAction("Zoom In", self)
        self.action_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.action_zoom_in.setStatusTip("Zoom in the view")
        self.action_zoom_in.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))

        self.action_zoom_out: QAction = QAction("Zoom Out", self)
        self.action_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.action_zoom_out.setStatusTip("Zoom out the view")
        self.action_zoom_out.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))

        self.action_reset_view: QAction = QAction("Reset View", self)
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
        _ = toolbar.addAction(self.action_new)
        _ = toolbar.addAction(self.action_open)
        _ = toolbar.addAction(self.action_save)
        _ = toolbar.addSeparator()

        # Edit operations
        _ = toolbar.addAction(self.action_undo)
        _ = toolbar.addAction(self.action_redo)
        _ = toolbar.addSeparator()

        # View operations
        _ = toolbar.addAction(self.action_zoom_in)
        _ = toolbar.addAction(self.action_zoom_out)
        _ = toolbar.addAction(self.action_reset_view)
        _ = toolbar.addSeparator()

        # Add frame control to toolbar
        _ = toolbar.addWidget(QLabel("Frame:"))
        self.frame_spinbox = QSpinBox()
        self.frame_spinbox.setMinimum(1)
        self.frame_spinbox.setMaximum(1000)
        self.frame_spinbox.setValue(1)
        _ = toolbar.addWidget(self.frame_spinbox)
        self.ui.timeline.frame_spinbox = self.frame_spinbox  # Map to timeline group
        _ = toolbar.addSeparator()

        # Add view option checkboxes to toolbar
        self.show_background_cb = QCheckBox("Background")
        self.show_background_cb.setChecked(True)
        _ = toolbar.addWidget(self.show_background_cb)

        self.show_grid_cb = QCheckBox("Grid")
        self.show_grid_cb.setChecked(False)
        _ = toolbar.addWidget(self.show_grid_cb)

        self.show_info_cb = QCheckBox("Info")
        self.show_info_cb.setChecked(True)
        _ = toolbar.addWidget(self.show_info_cb)

        # Add tooltip toggle checkbox
        self.show_tooltips_cb = QCheckBox("Tooltips")
        self.show_tooltips_cb.setChecked(False)  # Off by default
        _ = toolbar.addWidget(self.show_tooltips_cb)

        # Create widgets needed for UIComponents compatibility (even though not all are added to toolbar)
        # These widgets are required for the Component Container Pattern to work correctly

        # Point editing widgets (used in properties panel if it exists)
        self.point_x_spinbox = QDoubleSpinBox()
        self.point_x_spinbox.setRange(-10000, 10000)
        self.point_x_spinbox.setDecimals(3)
        self.point_x_spinbox.setEnabled(False)
        self.ui.point_edit.x_edit = self.point_x_spinbox

        self.point_y_spinbox = QDoubleSpinBox()
        self.point_y_spinbox.setRange(-10000, 10000)
        self.point_y_spinbox.setDecimals(3)
        self.point_y_spinbox.setEnabled(False)
        self.ui.point_edit.y_edit = self.point_y_spinbox

        # Visualization sliders (used in properties panel if it exists)
        self.point_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.point_size_slider.setMinimum(2)
        self.point_size_slider.setMaximum(20)
        self.point_size_slider.setValue(6)
        self.ui.visualization.point_size_slider = self.point_size_slider

        self.line_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.line_width_slider.setMinimum(1)
        self.line_width_slider.setMaximum(10)
        self.line_width_slider.setValue(2)
        self.ui.visualization.line_width_slider = self.line_width_slider

        # Keep btn_play_pause as it's used for playback functionality (though not visible)
        self.btn_play_pause = QPushButton()
        self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play_pause.setCheckable(True)
        self.ui.timeline.play_button = self.btn_play_pause  # Map to timeline group

        # NOTE: Removed other playback buttons (first/prev/next/last) - they were truly orphaned

        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setMinimum(1)
        self.fps_spinbox.setMaximum(120)
        self.fps_spinbox.setValue(24)
        self.fps_spinbox.setSuffix(" fps")
        self.ui.timeline.fps_spinbox = self.fps_spinbox  # Map to timeline group

        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(1)
        self.frame_slider.setMaximum(1000)
        self.frame_slider.setValue(1)
        self.ui.timeline.timeline_slider = self.frame_slider  # Map to timeline group

        # NOTE: timeline_tabs creation moved to _init_central_widget where it's actually used

        self.total_frames_label = QLabel("1")
        self.ui.status.info_label = self.total_frames_label  # Map to status group
        self.point_count_label: QLabel = QLabel("Points: 0")
        self.ui.status.quality_score_label = self.point_count_label  # Map to status group
        self.selected_count_label: QLabel = QLabel("Selected: 0")
        self.ui.status.quality_coverage_label = self.selected_count_label  # Map to status group
        self.bounds_label: QLabel = QLabel("Bounds: N/A")
        self.ui.status.quality_consistency_label = self.bounds_label  # Map to status group

        # Add stretch to push remaining items to the right
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
        _ = toolbar.addWidget(spacer)

    def _init_central_widget(self) -> None:
        """Initialize the central widget with full-width curve view and bottom timeline."""
        # Create main central widget with vertical layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create the main curve view area (full width, no side panels)
        self.curve_container: QWidget = self._create_curve_view_container()

        # Add curve container with stretch factor so it expands
        main_layout.addWidget(self.curve_container, stretch=1)  # Takes all available space

        # Create timeline tabs widget here where it's actually used
        self.timeline_tabs = None  # Initialize to None first
        try:
            from ui.timeline_tabs import TimelineTabWidget

            self.timeline_tabs = TimelineTabWidget()
            # Connections will be set up later when handlers are available
            logger.info("Timeline tabs widget created successfully")
        except Exception as e:
            logger.warning(f"Could not create timeline tabs widget: {e}")
            self.timeline_tabs = None

        # Add timeline tabs widget if available - no stretch so it stays fixed height
        if self.timeline_tabs:
            self.timeline_tabs.setMinimumHeight(60)  # Ensure timeline gets its minimum space
            self.timeline_tabs.setFixedHeight(60)  # Force exact height
            main_layout.addWidget(self.timeline_tabs, stretch=0)  # Fixed height, no expansion
            logger.info("Timeline tabs added to main layout")

        # Set the central widget
        self.setCentralWidget(central_widget)

    def _create_curve_view_container(self) -> QWidget:
        """Create the container for the curve view."""
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.Box)
        container.setLineWidth(1)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create the actual CurveViewWidget
        self.curve_widget = CurveViewWidget(container)
        self.curve_widget.set_main_window(self)  # pyright: ignore[reportArgumentType]

        # Ensure the curve widget can receive keyboard focus
        self.curve_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout.addWidget(self.curve_widget)

        # Set focus to curve widget after creation
        def set_focus_safe():
            try:
                if self.curve_widget is not None:
                    self.curve_widget.setFocus()
            except (RuntimeError, AttributeError):
                # Widget was deleted (C++ object destroyed) or not yet initialized
                pass

        QTimer.singleShot(100, set_focus_safe)

        logger.info("CurveViewWidget created and integrated")

        return container

    def _init_dock_widgets(self) -> None:
        """Initialize dock widgets (optional, for future expansion)."""
        # Create tracking points panel dock widget
        self.tracking_panel_dock: QDockWidget = QDockWidget("Tracking Points", self)
        self.tracking_panel: TrackingPointsPanel = TrackingPointsPanel()
        self.tracking_panel_dock.setWidget(self.tracking_panel)

        # Set dock widget properties
        self.tracking_panel_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tracking_panel_dock)
        self.tracking_panel_dock.setVisible(True)  # Make visible by default

        # Connect signals for tracking point management
        self.tracking_panel.points_selected.connect(self._on_tracking_points_selected)
        self.tracking_panel.point_visibility_changed.connect(self._on_point_visibility_changed)
        self.tracking_panel.point_color_changed.connect(self._on_point_color_changed)
        self.tracking_panel.point_deleted.connect(self._on_point_deleted)
        self.tracking_panel.point_renamed.connect(self._on_point_renamed)

        logger.info("Tracking points panel dock widget initialized")

    def _init_status_bar(self) -> None:
        """Initialize the status bar with additional widgets."""
        self.status_bar: QStatusBar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        # Add primary status label (left side) for thread-safe status messages
        self.status_label: QLabel = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)  # Regular widget goes on left

        # Add permanent widgets to status bar (right side)
        self.zoom_label: QLabel = QLabel("Zoom: 100%")
        self.status_bar.addPermanentWidget(self.zoom_label)

        self.position_label: QLabel = QLabel("X: 0.000, Y: 0.000")
        self.status_bar.addPermanentWidget(self.position_label)

    def _connect_signals(self) -> None:
        """Connect signals from state manager and shortcuts."""
        # Connect state manager signals
        _ = self.state_manager.file_changed.connect(self._on_file_changed)
        _ = self.state_manager.modified_changed.connect(self._on_modified_changed)
        _ = self.state_manager.frame_changed.connect(self._on_state_frame_changed)
        _ = self.state_manager.selection_changed.connect(self._on_selection_changed)
        _ = self.state_manager.view_state_changed.connect(self._on_view_state_changed)

        # Connect shortcut signals (these will be no-ops for now)
        _ = self.shortcut_manager.shortcut_activated.connect(self._on_shortcut_activated)

        # Connect frame controls
        if self.frame_spinbox:
            _ = self.frame_spinbox.valueChanged.connect(self._on_frame_changed)
        if self.frame_slider:
            _ = self.frame_slider.valueChanged.connect(self._on_slider_changed)

        # Connect timeline tabs if available
        if self.timeline_tabs:
            _ = self.timeline_tabs.frame_changed.connect(self._on_timeline_tab_clicked)
            _ = self.timeline_tabs.frame_hovered.connect(self._on_timeline_tab_hovered)
            logger.info("Timeline tabs signals connected")

    def _connect_curve_widget_signals(self) -> None:
        """Connect signals from the curve widget."""
        if not self.curve_widget:
            return

        # Connect curve widget signals to handlers
        _ = self.curve_widget.point_selected.connect(self._on_point_selected)
        _ = self.curve_widget.point_moved.connect(self._on_point_moved)
        _ = self.curve_widget.selection_changed.connect(self._on_curve_selection_changed)
        _ = self.curve_widget.view_changed.connect(self._on_curve_view_changed)
        _ = self.curve_widget.zoom_changed.connect(self._on_curve_zoom_changed)

        # Connect view options to curve widget
        if self.show_background_cb:
            _ = self.show_background_cb.stateChanged.connect(self._update_curve_view_options)
        if self.show_grid_cb:
            _ = self.show_grid_cb.stateChanged.connect(self._update_curve_view_options)
        if self.show_info_cb:
            _ = self.show_info_cb.stateChanged.connect(self._update_curve_view_options)
        if self.show_tooltips_cb:
            _ = self.show_tooltips_cb.stateChanged.connect(self._toggle_tooltips)
        if self.point_size_slider:
            _ = self.point_size_slider.valueChanged.connect(self._update_curve_point_size)
        if self.line_width_slider:
            _ = self.line_width_slider.valueChanged.connect(self._update_curve_line_width)

    def _connect_actions(self) -> None:
        """Connect actions to their handlers."""
        # File actions
        _ = self.action_new.triggered.connect(self._on_action_new)
        _ = self.action_open.triggered.connect(self._on_action_open)
        _ = self.action_save.triggered.connect(self._on_action_save)
        _ = self.action_save_as.triggered.connect(self._on_action_save_as)

        # Edit actions
        _ = self.action_undo.triggered.connect(self._on_action_undo)
        _ = self.action_redo.triggered.connect(self._on_action_redo)

        # View actions
        _ = self.action_zoom_in.triggered.connect(self._on_action_zoom_in)
        _ = self.action_zoom_out.triggered.connect(self._on_action_zoom_out)
        _ = self.action_reset_view.triggered.connect(self._on_action_reset_view)

    def _setup_tab_order(self) -> None:
        """Set up proper tab order for keyboard navigation."""
        # Only set tab order for widgets that are actually in the UI
        # Toolbar controls - check for None values
        if self.frame_spinbox and self.show_background_cb:
            self.setTabOrder(self.frame_spinbox, self.show_background_cb)
        if self.show_background_cb and self.show_grid_cb:
            self.setTabOrder(self.show_background_cb, self.show_grid_cb)
        # show_info_cb is Optional[QCheckBox]
        if self.show_grid_cb and self.show_info_cb is not None:
            self.setTabOrder(self.show_grid_cb, self.show_info_cb)

        # Curve view widget (main area)
        # show_info_cb is Optional[QCheckBox]
        if self.curve_widget and self.show_info_cb is not None:
            self.setTabOrder(self.show_info_cb, self.curve_widget)

        logger.debug("Tab order configured for keyboard navigation")

    @Slot(str)
    def _on_file_changed(self, file_path: str) -> None:
        """Handle file path changes."""
        self.setWindowTitle(self.state_manager.get_window_title())
        if file_path:
            logger.info(f"File changed to: {file_path}")

    @Slot(bool)
    def _on_modified_changed(self, modified: bool) -> None:
        """Handle modification status changes."""
        self.setWindowTitle(self.state_manager.get_window_title())
        if modified:
            logger.debug("Document marked as modified")

    @Slot(str)
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

        self.status_label.setText(f"Shortcut: {shortcut_name}")

    # ==================== Timeline Control Handlers ====================

    @Slot(int)
    @Slot(int)
    def _on_frame_changed(self, value: int) -> None:
        """Handle frame spinbox value change."""
        logger.debug(f"[FRAME] Frame changed to: {value}")
        # Use shared frame update logic, including state manager update
        self._update_frame_display(value, update_state_manager=True)

    def _update_frame_display(self, frame: int, update_state_manager: bool = True) -> None:
        """Shared method to update frame display across all UI components."""
        # Update UI controls
        if self.frame_spinbox:
            _ = self.frame_spinbox.blockSignals(True)
            self.frame_spinbox.setValue(frame)
            _ = self.frame_spinbox.blockSignals(False)

        if self.frame_slider:
            _ = self.frame_slider.blockSignals(True)
            self.frame_slider.setValue(frame)
            _ = self.frame_slider.blockSignals(False)

        # Update timeline tabs if available
        if self.timeline_tabs:
            self.timeline_tabs.set_current_frame(frame)

        # Update state manager (only when called from user input, not state sync)
        if update_state_manager:
            self.state_manager.current_frame = frame
            logger.debug(f"[FRAME] State manager current_frame set to: {self.state_manager.current_frame}")

        # Update background image if image sequence is loaded
        self._update_background_image_for_frame(frame)

        # Update curve widget to highlight current frame's point
        if self.curve_widget:
            # Notify curve widget of frame change for centering mode
            self.curve_widget.on_frame_changed(frame)
            # Invalidate caches to ensure proper repainting with new frame highlight
            self.curve_widget._invalidate_caches()
            self.curve_widget.update()

    @Slot(int)
    @Slot(int)
    def _on_slider_changed(self, value: int) -> None:
        """Handle frame slider value change."""
        if self.frame_spinbox:
            _ = self.frame_spinbox.blockSignals(True)
            self.frame_spinbox.setValue(value)
            _ = self.frame_spinbox.blockSignals(False)

        # Update timeline tabs if available
        if self.timeline_tabs:
            self.timeline_tabs.set_current_frame(value)

        self.state_manager.current_frame = value

        # Update background image if image sequence is loaded
        self._update_background_image_for_frame(value)

        # Update curve widget to highlight current frame's point
        if self.curve_widget:
            # Notify curve widget of frame change for centering mode
            self.curve_widget.on_frame_changed(value)
            # Invalidate caches to ensure proper repainting with new frame highlight
            self.curve_widget._invalidate_caches()
            self.curve_widget.update()

    @Slot()
    @Slot()
    def _on_first_frame(self) -> None:
        """Go to first frame."""
        if self.frame_spinbox:
            self.frame_spinbox.setValue(1)

    @Slot()
    @Slot()
    def _on_prev_frame(self) -> None:
        """Go to previous frame."""
        if self.frame_spinbox:
            current = self.frame_spinbox.value()
            if current > 1:
                self.frame_spinbox.setValue(current - 1)

    @Slot()
    @Slot()
    def _on_next_frame(self) -> None:
        """Go to next frame."""
        if self.frame_spinbox:
            current = self.frame_spinbox.value()
            if current < self.frame_spinbox.maximum():
                self.frame_spinbox.setValue(current + 1)

    @Slot()
    @Slot()
    def _on_last_frame(self) -> None:
        """Go to last frame."""
        if self.frame_spinbox:
            self.frame_spinbox.setValue(self.frame_spinbox.maximum())

    @Slot(bool)
    @Slot(bool)
    def _on_play_pause(self, checked: bool) -> None:
        """Handle play/pause toggle."""
        if checked:
            # Start playback
            if self.fps_spinbox and self.playback_timer and self.btn_play_pause:
                fps = self.fps_spinbox.value()
                interval = int(1000 / fps)  # Convert FPS to milliseconds
                self.playback_timer.start(interval)
                self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.play_toggled.emit(True)
        else:
            # Stop playback
            if self.playback_timer and self.btn_play_pause:
                self.playback_timer.stop()
                self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.play_toggled.emit(False)

    @Slot()
    @Slot()
    def _on_playback_timer(self) -> None:
        """Handle oscillating playback timer tick."""
        # Only handle oscillating playback if mode is not stopped
        if self.playback_state.mode == PlaybackMode.STOPPED:
            return

        current = self._get_current_frame()

        if self.playback_state.mode == PlaybackMode.PLAYING_FORWARD:
            # Move forward
            if current >= self.playback_state.max_frame:
                # Hit upper boundary - reverse direction
                self.playback_state.mode = PlaybackMode.PLAYING_BACKWARD
                next_frame = max(current - 1, self.playback_state.min_frame)
            else:
                next_frame = current + 1

        elif self.playback_state.mode == PlaybackMode.PLAYING_BACKWARD:
            # Move backward
            if current <= self.playback_state.min_frame:
                # Hit lower boundary - reverse direction
                self.playback_state.mode = PlaybackMode.PLAYING_FORWARD
                next_frame = min(current + 1, self.playback_state.max_frame)
            else:
                next_frame = current - 1
        else:
            # Fallback - shouldn't happen
            return

        # Update frame and UI
        self._set_current_frame(next_frame)

    @Slot(int)
    @Slot(int)
    def _on_fps_changed(self, value: int) -> None:
        """Handle FPS change."""
        if self.playback_timer and self.playback_timer.isActive():
            interval = int(1000 / value)
            self.playback_timer.setInterval(interval)
        self.frame_rate_changed.emit(value)

    # ================ Oscillating Timeline Playback Methods ================

    def _toggle_oscillating_playback(self) -> None:
        """Toggle oscillating playback on spacebar press."""
        if self.playback_state.mode == PlaybackMode.STOPPED:
            self._start_oscillating_playback()
        else:
            self._stop_oscillating_playback()

    def _start_oscillating_playback(self) -> None:
        """Start oscillating timeline playback."""
        # Update frame boundaries from current data
        self._update_playback_bounds()

        # Get FPS from UI or use default
        fps = 12  # Default
        if self.fps_spinbox:
            fps = self.fps_spinbox.value()

        # Set FPS-based timer interval
        interval = int(1000 / fps)  # Convert to milliseconds

        # Start forward playback
        self.playback_state.mode = PlaybackMode.PLAYING_FORWARD
        self.playback_state.current_frame = self._get_current_frame()

        # Start the timer
        if self.playback_timer:
            self.playback_timer.start(interval)

        logger.info(
            f"Started oscillating playback at {fps} FPS (bounds: {self.playback_state.min_frame}-{self.playback_state.max_frame})"
        )

    def _stop_oscillating_playback(self) -> None:
        """Stop oscillating timeline playback."""
        if self.playback_timer:
            self.playback_timer.stop()

        self.playback_state.mode = PlaybackMode.STOPPED
        logger.info("Stopped oscillating playback")

    def _update_playback_bounds(self) -> None:
        """Update playbook frame bounds based on current data."""
        # Get bounds from data service if available
        try:
            # curve_view is initialized as None in __init__
            if (
                self.curve_view is not None
                and getattr(self.curve_view, "curve_data", None) is not None
                and self.curve_view.curve_data
            ):
                # Calculate frame bounds directly from curve data
                frames = [int(point[0]) for point in self.curve_view.curve_data]
                if frames:
                    self.playback_state.min_frame = max(1, min(frames))
                    self.playback_state.max_frame = max(frames)
                else:
                    self.playback_state.min_frame = 1
                    self.playback_state.max_frame = 100
            else:
                # Use timeline widget bounds if available
                # timeline_tabs is Optional
                if self.timeline_tabs is not None:
                    self.playback_state.min_frame = getattr(self.timeline_tabs, "min_frame", 1)
                    self.playback_state.max_frame = getattr(self.timeline_tabs, "max_frame", 100)
                else:
                    # Default bounds
                    self.playback_state.min_frame = 1
                    self.playback_state.max_frame = 100
        except Exception as e:
            # Fallback to default bounds on any error
            logger.warning(f"Error getting playback bounds, using defaults: {e}")
            self.playback_state.min_frame = 1
            self.playback_state.max_frame = 100

        # Ensure current frame is within bounds
        current = self._get_current_frame()
        if current < self.playback_state.min_frame:
            self._set_current_frame(self.playback_state.min_frame)
        elif current > self.playback_state.max_frame:
            self._set_current_frame(self.playback_state.max_frame)

    def _get_current_frame(self) -> int:
        """Get the current frame number."""
        if self.frame_spinbox:
            return self.frame_spinbox.value()
        return 1

    def _set_current_frame(self, frame: int) -> None:
        """Set the current frame with UI updates."""
        # Update internal state
        self.playback_state.current_frame = frame

        # Update spinbox which triggers other UI updates
        if self.frame_spinbox:
            self.frame_spinbox.setValue(frame)

        # Update timeline widget if available
        # timeline_tabs is Optional
        if self.timeline_tabs is not None:
            if getattr(self.timeline_tabs, "set_current_frame", None) is not None:
                self.timeline_tabs.set_current_frame(frame)
            elif getattr(self.timeline_tabs, "current_frame", None) is not None:
                self.timeline_tabs.current_frame = frame

    @property
    def current_frame(self) -> int:
        """Get the current frame number.

        Property accessor for better type safety and compatibility.
        Provides a clean interface for accessing the current frame.
        """
        return self._get_current_frame()

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        """Set the current frame number.

        Property setter for better type safety and compatibility.
        Provides a clean interface for setting the current frame.
        """
        self._set_current_frame(value)

    # MainWindowProtocol required properties
    @property
    def selected_indices(self) -> list[int]:
        """Get the currently selected point indices."""
        return self.state_manager.selected_points

    @property
    def curve_data(self) -> list[tuple[int, float, float] | tuple[int, float, float, str]]:
        """Get the current curve data."""
        if self.curve_widget is not None:
            return self.curve_widget.curve_data  # pyright: ignore[reportReturnType]
        return []

    @property
    def is_modified(self) -> bool:
        """Get the modification state."""
        return self.state_manager.is_modified

    # MainWindowProtocol required methods
    def restore_state(self, state: object) -> None:
        """Restore state from history (delegate to state manager)."""
        # This method is required by MainWindowProtocol but actual implementation
        # is handled by the state manager and services
        pass  # pyright: ignore[reportUnnecessaryPassStatement]

    def update_status(self, message: str) -> None:
        """Update status bar message."""
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage(message)

    @Slot(int)
    @Slot(int)
    def _on_timeline_tab_clicked(self, frame: int) -> None:
        """Handle timeline tab click to navigate to frame."""
        # Update spinbox and slider (which will trigger frame change)
        if self.frame_spinbox:
            self.frame_spinbox.setValue(frame)
        logger.debug(f"Timeline tab clicked: navigating to frame {frame}")

    @Slot(int)
    @Slot(int)
    def _on_timeline_tab_hovered(self, frame: int) -> None:  # pyright: ignore[reportUnusedParameter]
        """Handle timeline tab hover for preview (optional feature)."""
        # Could be used to show frame preview in the future
        pass

    # ==================== Action Handlers ====================

    @Slot()
    @Slot()
    def _on_action_new(self) -> None:
        """Handle new file action."""
        if self.state_manager.is_modified:
            if not self.services.confirm_action("Current curve has unsaved changes. Continue?", self):
                return

        # Clear curve widget data
        if self.curve_widget:
            self.curve_widget.set_curve_data([])
            self._update_tracking_panel()

        self.state_manager.reset_to_defaults()
        self._update_ui_state()
        self.status_label.setText("New curve created")

    @Slot()
    @Slot()
    def _on_action_open(self) -> None:
        """Handle open file action."""
        # Check for unsaved changes
        if self.state_manager.is_modified:
            if not self.services.confirm_action("Current curve has unsaved changes. Continue?", self):
                return

        # Try to load as multi-point tracking data first

        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Tracking Data",
            "",
            "Text Files (*.txt);;JSON Files (*.json);;CSV Files (*.csv);;All Files (*.*)",
        )

        if not file_path:
            return

        # Check if it's a multi-point file
        if file_path.endswith(".txt"):
            # Try loading as multi-point format
            from services import get_data_service

            data_service = get_data_service()
            tracked_data = data_service.load_tracked_data(file_path)

            if tracked_data:
                # Successfully loaded multi-point data
                self.tracked_data = tracked_data
                self.active_points = list(tracked_data.keys())[:1]  # Select first point

                # Set up view for pixel-coordinate tracking data BEFORE displaying
                if self.curve_widget:
                    self.curve_widget.setup_for_pixel_tracking()

                self._update_tracking_panel()
                self._update_curve_display()

                # Update frame range based on first trajectory
                if self.active_points and self.active_points[0] in self.tracked_data:
                    trajectory = self.tracked_data[self.active_points[0]]
                    if trajectory:
                        max_frame = max(point[0] for point in trajectory)
                        if self.frame_slider:
                            self.frame_slider.setMaximum(max_frame)
                        if self.frame_spinbox:
                            self.frame_spinbox.setMaximum(max_frame)
                        if self.total_frames_label:
                            self.total_frames_label.setText(str(max_frame))
                        self.state_manager.total_frames = max_frame
                return

        # Fall back to single curve loading
        # Load data using service facade
        data = self.services.load_track_data_from_file(file_path) if file_path else None

        if data:
            # Update curve widget with new data
            if self.curve_widget:
                self.curve_widget.set_curve_data(data)  # pyright: ignore[reportArgumentType]
                self._update_tracking_panel()

            # Update state manager
            self.state_manager.set_track_data(data, mark_modified=False)  # pyright: ignore[reportArgumentType]

            # Update frame range based on loaded data
            if data:
                max_frame = max(point[0] for point in data)
                if self.frame_slider:
                    self.frame_slider.setMaximum(max_frame)
                if self.frame_spinbox:
                    self.frame_spinbox.setMaximum(max_frame)
                if self.total_frames_label:
                    self.total_frames_label.setText(str(max_frame))
                # CRITICAL: Update state manager's total frames!
                self.state_manager.total_frames = max_frame

                # Update timeline tabs with frame range and point data
                self._update_timeline_tabs(data)  # pyright: ignore[reportArgumentType]

            self._update_ui_state()
            self.status_label.setText("File loaded successfully")

    @Slot()
    @Slot()
    def _on_action_save(self) -> None:
        """Handle save file action."""
        if not self.state_manager.current_file:
            self._on_action_save_as()
        else:
            # Get current data from curve widget
            data = self._get_current_curve_data()
            if self.services.save_track_data(data, self):  # pyright: ignore[reportArgumentType]
                self.state_manager.is_modified = False
                self.status_label.setText("File saved successfully")

    @Slot()
    @Slot()
    def _on_action_save_as(self) -> None:
        """Handle save as action."""
        # Get current data from curve widget
        data = self._get_current_curve_data()
        if self.services.save_track_data(data, self):  # pyright: ignore[reportArgumentType]
            self.state_manager.is_modified = False
            self.status_label.setText("File saved successfully")

    def _load_burger_tracking_data(self) -> None:
        """Auto-load burger footage and tracking data if available using background thread."""
        from pathlib import Path

        # Get the current working directory
        base_dir = Path(__file__).parent.parent

        # Check for tracking data file - try v2 first, then v1
        tracking_file = base_dir / "2DTrackDatav2.txt"
        if not tracking_file.exists():
            tracking_file = base_dir / "2DTrackData.txt"
            if not tracking_file.exists():
                # Also check in footage directory
                tracking_file = base_dir / "footage" / "Burger" / "2DTrackDatav2.txt"
                if not tracking_file.exists():
                    tracking_file = base_dir / "footage" / "Burger" / "2DTrackData.txt"

        # Check for burger footage directory
        footage_dir = base_dir / "footage" / "Burger"

        # Determine what files need to be loaded
        tracking_file_path = str(tracking_file) if tracking_file.exists() else None
        image_dir_path = str(footage_dir) if footage_dir.exists() else None

        # For debugging: Always try to load burger sequence
        if not image_dir_path:
            # Try to find it in different locations
            possible_dirs = [base_dir / "footage" / "Burger", base_dir / "Data" / "burger", base_dir / "Burger"]
            for dir_path in possible_dirs:
                if dir_path.exists() and dir_path.is_dir():
                    image_dir_path = str(dir_path)
                    logger.info(f"Found burger footage at: {image_dir_path}")
                    break

        # Always proceed with loading if we have at least the image directory
        if not image_dir_path:
            logger.warning("No burger footage found in any expected location")
            logger.debug(f"Checked: {base_dir}/footage/Burger, {base_dir}/Data/burger, {base_dir}/Burger")
            # Still continue to attempt loading from default location
            image_dir_path = str(footage_dir)  # Use default even if it doesn't exist

        # Start new work in Python thread
        if not self.file_load_worker:
            logger.error("[PYTHON-THREAD] Worker not initialized! This should not happen.")
            return

        logger.info("[PYTHON-THREAD] Starting file loading in Python thread")

        # Start work in new Python thread
        self.file_load_worker.start_work(tracking_file_path, image_dir_path)

        logger.info("[PYTHON-THREAD] File loading started in Python thread")

    def _cleanup_file_load_thread(self) -> None:
        """Clean up file loading thread - stops Python thread if running."""
        logger.info("[PYTHON-THREAD] _cleanup_file_load_thread called - stopping Python thread if running")
        if self.file_load_worker:
            self.file_load_worker.stop()
        return

        # [REMOVED: Dead code block that was part of old QThread implementation]

    # REMOVED DUPLICATE _cleanup_file_load_thread - see above for the correct implementation

    @Slot(list)
    def _on_tracking_data_loaded(self, data: list[tuple[int, float, float] | tuple[int, float, float, str]]) -> None:
        """Handle tracking data loaded in background thread."""
        current_thread = QThread.currentThread()
        app_instance = QApplication.instance()
        main_thread = app_instance.thread() if app_instance is not None else None
        logger.info(
            f"[THREAD-DEBUG] _on_tracking_data_loaded executing in thread: {current_thread} (main={current_thread == main_thread})"
        )
        if data and self.curve_widget:
            logger.debug(f"[DATA] Loaded {len(data)} points from background thread")
            # Log first few points for debugging
            for i in range(min(3, len(data))):
                logger.debug(f"[DATA] Point {i}: {data[i]}")

            # Set up view for pixel-coordinate tracking data BEFORE setting data
            self.curve_widget.setup_for_pixel_tracking()
            self.curve_widget.set_curve_data(data)  # pyright: ignore[reportArgumentType]
            # self._update_point_list_data()  # Method doesn't exist
            self.state_manager.set_track_data(data, mark_modified=False)  # pyright: ignore[reportArgumentType]
            logger.info(f"Loaded {len(data)} tracking points from background thread")

            # Update frame range based on data
            if data:
                max_frame = max(point[0] for point in data)
                try:
                    if self.frame_slider:
                        self.frame_slider.setMaximum(max_frame)
                    if self.frame_spinbox:
                        self.frame_spinbox.setMaximum(max_frame)
                    if self.total_frames_label:
                        self.total_frames_label.setText(str(max_frame))
                    # Update state manager's total frames
                    self.state_manager.total_frames = max_frame
                except RuntimeError:
                    # Widgets may have been deleted during application shutdown
                    pass

    @Slot(dict)
    def _on_multi_point_data_loaded(self, multi_data: dict[str, CurveDataList]) -> None:
        """Handle multi-point tracking data loaded in background thread."""
        current_thread = QThread.currentThread()
        app_instance = QApplication.instance()
        main_thread = app_instance.thread() if app_instance is not None else None
        logger.info(
            f"[THREAD-DEBUG] _on_multi_point_data_loaded executing in thread: {current_thread} (main={current_thread == main_thread})"
        )

        if multi_data:
            # Store the multi-point tracking data
            self.tracked_data = multi_data
            self.active_points = list(multi_data.keys())[:1]  # Select first point by default

            logger.info(f"Loaded {len(multi_data)} tracking points from multi-point file")

            # Update the tracking panel with the multi-point data
            self._update_tracking_panel()

            # Display the first point's trajectory
            if self.active_points and self.curve_widget:
                first_point = self.active_points[0]
                if first_point in self.tracked_data:
                    # Set up view for pixel-coordinate tracking data
                    self.curve_widget.setup_for_pixel_tracking()
                    trajectory = self.tracked_data[first_point]
                    self.curve_widget.set_curve_data(trajectory)  # pyright: ignore[reportArgumentType]
                    self.state_manager.set_track_data(trajectory, mark_modified=False)  # pyright: ignore[reportArgumentType]

                    # Update frame range based on all trajectories
                    max_frame = 0
                    for traj in self.tracked_data.values():
                        if traj:
                            traj_max = max(point[0] for point in traj)
                            max_frame = max(max_frame, traj_max)

                    try:
                        if self.frame_slider:
                            self.frame_slider.setMaximum(max_frame)
                        if self.frame_spinbox:
                            self.frame_spinbox.setMaximum(max_frame)
                        if self.total_frames_label:
                            self.total_frames_label.setText(str(max_frame))
                        self.state_manager.total_frames = max_frame
                    except RuntimeError:
                        # Widgets may have been deleted during application shutdown
                        pass

    @Slot(str, list)
    def _on_image_sequence_loaded(self, image_dir: str, image_files: list[str]) -> None:
        """Handle image sequence loaded in background thread."""
        current_thread = QThread.currentThread()
        app_instance = QApplication.instance()
        main_thread = app_instance.thread() if app_instance is not None else None
        logger.info(
            f"[THREAD-DEBUG] _on_image_sequence_loaded executing in thread: {current_thread} (main={current_thread == main_thread})"
        )
        if image_files and self.curve_widget:
            # Store image sequence info
            self.image_directory = image_dir
            self.image_filenames = image_files
            self.current_image_idx = 0

            # Update frame range to match image sequence exactly
            # The frame range should match the number of images, not extend beyond
            num_images = len(image_files)
            try:
                if self.frame_spinbox:
                    self.frame_spinbox.setMaximum(num_images)
                if self.frame_slider:
                    self.frame_slider.setMaximum(num_images)
                if self.total_frames_label:
                    self.total_frames_label.setText(str(num_images))
                logger.info(f"Set frame range to match {num_images} images (1-{num_images})")
            except RuntimeError:
                # Widgets may have been deleted during application shutdown
                pass

            # Update timeline tabs if available
            # timeline_tabs is Optional
            if self.timeline_tabs is not None:
                try:
                    self.timeline_tabs.set_frame_range(1, num_images)
                    logger.info(f"Updated timeline tabs frame range to 1-{num_images}")
                except (AttributeError, RuntimeError) as e:
                    logger.warning(f"Could not update timeline tabs: {e}")

            # Update state manager if available
            # state_manager is always initialized in __init__
            if self.state_manager:
                self.state_manager.set_image_files(image_files)

            # Load the first image as background
            if image_files:
                from pathlib import Path

                first_image_path = Path(image_dir) / image_files[0]
                app_instance = QApplication.instance()
                main_thread = app_instance.thread() if app_instance is not None else None
                logger.info(
                    f"[THREAD-DEBUG] Creating QPixmap in thread: {QThread.currentThread()} (main={QThread.currentThread() == main_thread})"
                )
                pixmap = QPixmap(str(first_image_path))
                logger.info("[THREAD-DEBUG] QPixmap created successfully")

                if not pixmap.isNull():
                    self.curve_widget.background_image = pixmap
                    self.curve_widget.image_width = pixmap.width()
                    self.curve_widget.image_height = pixmap.height()
                    self.curve_widget.show_background = True

                    # Fit the image to view
                    self.curve_widget.fit_to_background_image()

                    logger.info(f"Loaded background image: {image_files[0]} ({pixmap.width()}x{pixmap.height()})")

            logger.info(f"Loaded {len(image_files)} images from background thread")

            # Ensure background checkbox is checked when images are loaded
            if self.show_background_cb and image_files:
                self.show_background_cb.setChecked(True)
                logger.info("Enabled background display for loaded images")

    @Slot(int, str)
    def _on_file_load_progress(self, progress: int, message: str) -> None:
        """Handle file loading progress updates."""
        self.status_label.setText(f"{message} ({progress}%)")
        logger.debug(f"File load progress: {progress}% - {message}")

    @Slot(str)
    def _on_file_load_error(self, error_message: str) -> None:
        """Handle file loading errors."""
        logger.error(f"File loading error: {error_message}")
        self.status_label.setText(f"Error: {error_message}")

    @Slot()
    def _on_file_load_finished(self) -> None:
        """Handle file loading completion - worker ready for next load."""
        self.status_label.setText("File loading completed")
        logger.info("[PYTHON-THREAD] File loading finished - worker ready for next load")
        # Mark loading as complete but keep worker alive for reuse
        self._file_loading = False

    def _update_background_image_for_frame(self, frame: int) -> None:
        """Update the background image based on the current frame."""
        if getattr(self, "image_filenames", None) is None or not self.image_filenames:
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

            image_path = Path(self.image_directory) / self.image_filenames[image_idx]  # pyright: ignore[reportArgumentType]
            logger.info(f"[THREAD-DEBUG] Creating QPixmap for frame update in thread: {QThread.currentThread()}")
            pixmap = QPixmap(str(image_path))

            if not pixmap.isNull():
                self.curve_widget.background_image = pixmap
                self.curve_widget.update()
                logger.debug(f"Updated background to frame {frame}: {self.image_filenames[image_idx]}")

    @Slot()
    @Slot()
    def _on_action_undo(self) -> None:
        """Handle undo action."""
        self.services.undo()
        self.status_label.setText("Undo")

    @Slot()
    @Slot()
    def _on_action_redo(self) -> None:
        """Handle redo action."""
        self.services.redo()
        self.status_label.setText("Redo")

    @Slot()
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
        self.status_label.setText("View reset")

    # ==================== State Change Handlers ====================

    @Slot(list)
    def _on_selection_changed(self, indices: list[int]) -> None:
        """Handle selection change from state manager."""
        count = len(indices)
        self.selected_count_label.setText(f"Selected: {count}")

        if count == 1:
            # Show single point properties
            idx = indices[0]
            if self.selected_point_label:
                self.selected_point_label.setText(f"Point #{idx}")

            # Get actual point data from curve widget
            if self.curve_widget and idx < len(self.curve_widget.curve_data):
                point_data = self.curve_widget.curve_data[idx]
                from core.point_types import safe_extract_point

                frame, x, y, _ = safe_extract_point(point_data)

                # Update spinboxes with actual values
                if self.point_x_spinbox and self.point_y_spinbox:
                    _ = self.point_x_spinbox.blockSignals(True)
                    _ = self.point_y_spinbox.blockSignals(True)
                    self.point_x_spinbox.setValue(x)
                    self.point_y_spinbox.setValue(y)
                    _ = self.point_x_spinbox.blockSignals(False)
                    _ = self.point_y_spinbox.blockSignals(False)

                    # Connect spinbox changes to update point
                    if getattr(self, "_point_spinbox_connected", False) is False:
                        _ = self.point_x_spinbox.valueChanged.connect(self._on_point_x_changed)
                        _ = self.point_y_spinbox.valueChanged.connect(self._on_point_y_changed)
                        self._point_spinbox_connected = True

            if self.point_x_spinbox:
                self.point_x_spinbox.setEnabled(True)
            if self.point_y_spinbox:
                self.point_y_spinbox.setEnabled(True)
        elif count > 1:
            if self.selected_point_label:
                self.selected_point_label.setText(f"{count} points selected")
            if self.point_x_spinbox:
                self.point_x_spinbox.setEnabled(False)
            if self.point_y_spinbox:
                self.point_y_spinbox.setEnabled(False)
        else:
            if self.selected_point_label:
                self.selected_point_label.setText("No point selected")
            if self.point_x_spinbox:
                self.point_x_spinbox.setEnabled(False)
            if self.point_y_spinbox:
                self.point_y_spinbox.setEnabled(False)

    @Slot()
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
        if self.frame_spinbox:
            self.frame_spinbox.setMaximum(total_frames)
        if self.frame_slider:
            self.frame_slider.setMaximum(total_frames)
        if self.total_frames_label:
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

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Event filter to handle key event redirection."""
        if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            key = event.key()
            logger.debug(f"[EVENT_FILTER] KeyPress detected: key={key}, object={watched.__class__.__name__}")

            # Handle C key specifically without modifiers
            if key == Qt.Key.Key_C and not event.modifiers():
                # If C key pressed on curve widget, let it handle normally
                if watched == self.curve_widget:
                    logger.debug("[EVENT_FILTER] C key on curve_widget, passing through")
                    return super().eventFilter(watched, event)  # Proper delegation

                # If C key pressed elsewhere, redirect to curve widget
                elif watched != self.curve_widget and self.curve_widget:
                    logger.debug("[EVENT_FILTER] Redirecting C key to curve_widget")
                    self.curve_widget.setFocus()
                    _ = QApplication.sendEvent(self.curve_widget, event)
                    return True  # Consume original event to prevent double handling

        return super().eventFilter(watched, event)  # Proper delegation to parent

    def update_cursor_position(self, x: float, y: float) -> None:
        """Update cursor position in status bar."""
        self.position_label.setText(f"X: {x:.3f}, Y: {y:.3f}")

    # ==================== Curve Widget Signal Handlers ====================

    @Slot(int)
    def _on_point_selected(self, index: int) -> None:
        """Handle point selection from curve widget."""
        logger.debug(f"Point {index} selected")
        # Update properties panel will be handled by selection_changed signal

    @Slot(int, float, float)
    def _on_point_moved(self, index: int, x: float, y: float) -> None:
        """Handle point movement from curve widget."""
        self.state_manager.is_modified = True
        logger.debug(f"Point {index} moved to ({x:.3f}, {y:.3f})")

    @Slot(list)
    def _on_curve_selection_changed(self, indices: list[int]) -> None:
        """Handle selection change from curve widget."""
        # Update state manager
        self.state_manager.set_selected_points(indices)
        # Properties panel will be updated via state manager signal

    @Slot()
    def _on_curve_view_changed(self) -> None:
        """Handle view changes from curve widget."""
        # Update zoom display
        self._update_zoom_label()

    @Slot(float)
    def _on_curve_zoom_changed(self, zoom: float) -> None:
        """Handle zoom changes from curve widget."""
        # Update state manager and zoom label
        self.state_manager.zoom_level = zoom
        self._update_zoom_label()

    # ==================== Tracking Points Panel Handlers ====================

    def _on_tracking_points_selected(self, point_names: list[str]) -> None:
        """Handle selection of tracking points from panel."""
        self.active_points = point_names
        self._update_curve_display()

    def _on_point_visibility_changed(self, point_name: str, visible: bool) -> None:
        """Handle visibility change for a tracking point."""
        # Update display to show/hide the trajectory
        self._update_curve_display()

    def _on_point_color_changed(self, point_name: str, color: str) -> None:
        """Handle color change for a tracking point."""
        # Update display with new color
        self._update_curve_display()

    def _on_point_deleted(self, point_name: str) -> None:
        """Handle deletion of a tracking point."""
        if point_name in self.tracked_data:
            del self.tracked_data[point_name]
            if point_name in self.active_points:
                self.active_points.remove(point_name)
            self._update_tracking_panel()
            self._update_curve_display()

    def _on_point_renamed(self, old_name: str, new_name: str) -> None:
        """Handle renaming of a tracking point."""
        if old_name in self.tracked_data:
            self.tracked_data[new_name] = self.tracked_data.pop(old_name)
            if old_name in self.active_points:
                idx = self.active_points.index(old_name)
                self.active_points[idx] = new_name
            self._update_tracking_panel()

    def _update_tracking_panel(self) -> None:
        """Update tracking panel with current tracking data."""
        self.tracking_panel.set_tracked_data(self.tracked_data)

    def _update_curve_display(self) -> None:
        """Update curve display with selected tracking points."""
        if not self.curve_widget:
            return

        # For now, display the first selected point's trajectory
        # TODO: Support multiple trajectory display
        if self.active_points and self.active_points[0] in self.tracked_data:
            trajectory = self.tracked_data[self.active_points[0]]
            self.curve_widget.set_curve_data(trajectory)
        else:
            self.curve_widget.set_curve_data([])

    # ==================== View Options Handlers ====================

    def _update_curve_view_options(self) -> None:
        """Update curve widget view options based on checkboxes."""
        if not self.curve_widget:
            return

        if self.show_background_cb:
            self.curve_widget.show_background = self.show_background_cb.isChecked()
        if self.show_grid_cb:
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
        if self.point_size_label:
            self.point_size_label.setText(str(value))

    @Slot(int)
    def _update_curve_line_width(self, value: int) -> None:
        """Update curve widget line width."""
        if self.curve_widget:
            self.curve_widget.line_width = value
            self.curve_widget.selected_line_width = value + 1
            self.curve_widget.update()
        if self.line_width_label:
            self.line_width_label.setText(str(value))

    def _toggle_tooltips(self) -> None:
        """Toggle tooltips on/off globally."""
        if not self.show_tooltips_cb:
            return

        enabled = self.show_tooltips_cb.isChecked()

        # Store/restore tooltips for all widgets in the main window
        if enabled:
            # Restore tooltips if we have them stored
            if getattr(self, "_stored_tooltips", None) is not None:
                for widget, tooltip in self._stored_tooltips.items():
                    if widget and tooltip:
                        widget.setToolTip(tooltip)
        else:
            # Store current tooltips and clear them
            if getattr(self, "_stored_tooltips", None) is None:
                self._stored_tooltips = {}

            # Find all widgets with tooltips and store/clear them
            for widget in self.findChildren(QWidget):
                tooltip = widget.toolTip()
                if tooltip:
                    self._stored_tooltips[widget] = tooltip
                    widget.setToolTip("")

        logger.debug(f"Tooltips {'enabled' if enabled else 'disabled'}")

    # ==================== Frame Navigation Handlers ====================

    @Slot(int)
    def _on_state_frame_changed(self, frame: int) -> None:
        """Handle frame change from state manager."""
        # Use shared frame update logic, but don't update state manager to avoid loops
        self._update_frame_display(frame, update_state_manager=False)

    # ==================== Utility Methods ====================

    def _update_timeline_tabs(
        self, curve_data: list[tuple[int, float, float] | tuple[int, float, float, str]] | None = None
    ) -> None:
        """Update timeline tabs with current curve data and frame range."""
        if not self.timeline_tabs:
            return

        # Get curve data if not provided
        if curve_data is None:
            curve_data = self._get_current_curve_data()

        if not curve_data:
            return

        # Calculate frame range - validate data first
        frames: list[int] = []
        for point in curve_data:
            if len(point) >= 3:
                try:
                    # Ensure frame number is an integer
                    frame = int(point[0])
                    frames.append(frame)
                except (ValueError, TypeError):
                    # Skip invalid data
                    continue

        if not frames:
            return

        min_frame = min(frames)
        max_frame = max(frames)

        # Update timeline widget frame range
        self.timeline_tabs.set_frame_range(min_frame, max_frame)

        # Get point status for all frames using DataService
        try:
            from services import get_data_service

            data_service = get_data_service()

            # Get status for all frames that have points
            frame_status = data_service.get_frame_range_point_status(curve_data)  # pyright: ignore[reportArgumentType]

            # Update timeline tabs with point status
            for frame, (keyframe_count, interpolated_count, has_selected) in frame_status.items():
                self.timeline_tabs.update_frame_status(frame, keyframe_count, interpolated_count, has_selected)

            logger.debug(f"Updated timeline tabs with {len(frame_status)} frames of point data")

        except Exception as e:
            logger.warning(f"Could not update timeline tabs with point data: {e}")

    def _get_current_curve_data(self) -> list[tuple[int, float, float] | tuple[int, float, float, str]]:
        """Get current curve data from curve widget or state manager."""
        if self.curve_widget:
            return self.curve_widget.curve_data  # pyright: ignore[reportReturnType]
        return self.state_manager.track_data  # pyright: ignore[reportReturnType]

    def add_to_history(self) -> None:
        """Add current state to history (called by curve widget)."""
        self.services.add_to_history()

        # Update history-related UI state
        self.action_undo.setEnabled(self.state_manager.can_undo)
        self.action_redo.setEnabled(self.state_manager.can_redo)

    @Slot(float)
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

    @Slot(float)
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

    def get_view_options(self) -> dict[str, object]:
        """Get current view options."""
        return {
            "show_background": self.show_background_cb.isChecked() if self.show_background_cb else False,
            "show_grid": self.show_grid_cb.isChecked() if self.show_grid_cb else True,
            "show_info": self.show_info_cb.isChecked() if self.show_info_cb else True,
            "point_size": self.point_size_slider.value() if self.point_size_slider else 5,
            "line_width": self.line_width_slider.value() if self.line_width_slider else 2,
        }

    def set_centering_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-centering on frame change.

        Args:
            enabled: Whether to enable auto-centering
        """
        # Store the centering state
        self.auto_center_enabled = enabled

        # Update the curve widget if available
        # curve_widget is Optional
        if self.curve_widget is not None:
            if getattr(self.curve_widget, "set_auto_center", None) is not None:
                self.curve_widget.set_auto_center(enabled)  # pyright: ignore[reportAttributeAccessIssue]

        # Log the state change
        logger.info(f"Auto-centering {'enabled' if enabled else 'disabled'}")

        # Update status bar
        # statusBar() is a QMainWindow method, always available
        self.statusBar().showMessage(f"Auto-center on frame change: {'ON' if enabled else 'OFF'}", 3000)

    def apply_smooth_operation(self) -> None:
        """Apply smoothing operation to selected points in the curve.

        Shows a dialog to get smoothing parameters and applies smoothing
        to the currently selected points or all points if none selected.
        """
        # curve_widget is Optional
        if self.curve_widget is None:
            logger.warning("No curve widget available for smoothing")
            return

        # Get the current curve data
        curve_data = getattr(self.curve_widget, "curve_data", [])
        if not curve_data:
            _ = QMessageBox.information(self, "No Data", "No curve data to smooth.")
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
        from services import get_ui_service

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
            # self._update_point_list_data()  # Method doesn't exist

            # Mark as modified
            # state_manager is always initialized in __init__
            self.state_manager.is_modified = True

            # Update status
            self.statusBar().showMessage(
                f"Applied smoothing to {len(selected_indices)} points (window size: {window_size})", 3000
            )
            logger.info(f"Smoothing applied to {len(selected_indices)} points")
        else:
            _ = QMessageBox.warning(self, "Service Error", "Data service not available for smoothing.")

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events for custom shortcuts."""
        # Tab key toggles tracking panel dock visibility
        if event.key() == Qt.Key.Key_Tab:
            # TODO: Tracking panel disabled
            # if hasattr(self, "tracking_panel_dock"):
            #     self.tracking_panel_dock.setVisible(not self.tracking_panel_dock.isVisible())
            pass
            event.accept()
            return

        # Pass to parent for default handling
        super().keyPressEvent(event)

    @override
    def closeEvent(self, event: QEvent) -> None:
        """Handle window close event with proper thread cleanup."""
        logger.info("[PYTHON-THREAD] Application closing, stopping Python thread if running")

        # Stop the worker thread
        if self.file_load_worker is not None:
            self.file_load_worker.stop()

        logger.info("[KEEP-ALIVE] Worker and thread cleaned up")

        # Accept the close event
        event.accept()
        logger.info("MainWindow closed with proper cleanup")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
