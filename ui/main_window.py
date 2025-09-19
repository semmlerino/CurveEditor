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
from typing import TYPE_CHECKING, cast, override

if TYPE_CHECKING:
    from ui.timeline_tabs import TimelineTabWidget

    from .curve_view_widget import CurveViewWidget
    from .service_facade import ServiceFacade

# Import PySide6 modules
from PySide6.QtCore import QEvent, QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import (
    QKeyEvent,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDockWidget,
    QDoubleSpinBox,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QWidget,
)

# Configure logger for this module
from core.logger_utils import get_logger
from core.type_aliases import CurveDataList
from services import get_data_service
from stores import get_store_manager

# Import local modules
# CurveView removed - using CurveViewWidget
from .controllers import (
    ActionHandlerController,
    FrameNavigationController,
    PlaybackController,
    SignalConnectionManager,
    UIInitializationController,
)
from .curve_view_widget import CurveViewWidget
from .dark_theme_stylesheet import get_dark_theme_stylesheet
from .file_operations import FileOperations
from .keyboard_shortcuts import ShortcutManager
from .state_manager import StateManager
from .tracking_points_panel import TrackingPointsPanel

# Import refactored components
from .ui_components import UIComponents
from .ui_constants import MAX_HISTORY_SIZE

logger = get_logger("main_window")


class MainWindow(QMainWindow):  # Implements MainWindowProtocol (structural typing)
    """Main application window for the Curve Editor."""

    # Custom signals for internal communication
    play_toggled: Signal = Signal(bool)
    frame_rate_changed: Signal = Signal(int)

    # Widget type annotations - initialized by UIInitializationController
    frame_spinbox: QSpinBox | None = None
    total_frames_label: QLabel | None = None
    frame_slider: QSlider | None = None
    timeline_tabs: "TimelineTabWidget | None" = None
    # Removed orphaned playback button attributes - they were never used
    btn_play_pause: QPushButton | None = None  # Used for playback control (not visible but functional)
    fps_spinbox: QSpinBox | None = None
    # playback_timer was moved to PlaybackController
    curve_widget: "CurveViewWidget | None" = None
    curve_container: QWidget | None = None
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

    # Additional widgets created by UIInitializationController
    point_count_label: QLabel | None = None
    selected_count_label: QLabel | None = None
    bounds_label: QLabel | None = None
    status_label: QLabel | None = None
    status_bar: QStatusBar | None = None
    zoom_label: QLabel | None = None
    position_label: QLabel | None = None
    tracking_panel_dock: QDockWidget | None = None
    tracking_panel: TrackingPointsPanel | None = None

    # Actions initialized by UIInitializationController
    action_new: object | None = None
    action_open: object | None = None
    action_save: object | None = None
    action_save_as: object | None = None
    action_load_images: object | None = None
    action_export_data: object | None = None
    action_quit: object | None = None
    action_undo: object | None = None
    action_redo: object | None = None
    action_select_all: object | None = None
    action_add_point: object | None = None
    action_zoom_in: object | None = None
    action_zoom_out: object | None = None
    action_zoom_fit: object | None = None
    action_reset_view: object | None = None
    action_smooth_curve: object | None = None
    action_filter_curve: object | None = None
    action_analyze_curve: object | None = None
    action_next_frame: object | None = None
    action_prev_frame: object | None = None
    action_first_frame: object | None = None
    action_last_frame: object | None = None
    action_oscillate_playback: object | None = None

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

        # Get reactive data store
        self._store_manager = get_store_manager()
        self._curve_store = self._store_manager.get_curve_store()

        # Initialize controllers
        self.playback_controller: PlaybackController = PlaybackController(self.state_manager, self)
        self.frame_nav_controller: FrameNavigationController = FrameNavigationController(self.state_manager, self)
        self.action_controller: ActionHandlerController = ActionHandlerController(self.state_manager, self)
        self.ui_init_controller: UIInitializationController = UIInitializationController(self)
        self.signal_manager: SignalConnectionManager = SignalConnectionManager(self)

        # Initialize service facade
        from services.service_protocols import MainWindowProtocol

        from .service_facade import get_service_facade

        self.services: ServiceFacade = get_service_facade(cast(MainWindowProtocol, cast(object, self)))

        # Initialize file operations manager
        self.file_operations: FileOperations = FileOperations(self, self.state_manager, self.services)

        # Initialize UI components container for organized widget management
        self.ui: UIComponents = UIComponents(self)

        # Multi-point tracking data
        self.tracked_data: dict[str, CurveDataList] = {}  # All tracking points
        self.active_points: list[str] = []  # Currently selected points

        # Initialize all UI components via controller
        self.ui_init_controller.initialize_ui()

        # Initialize legacy curve view and track quality UI
        self.curve_view: CurveViewWidget | None = None  # Legacy curve view - no longer used
        self.track_quality_ui: QWidget | None = None  # Legacy track quality UI

        # Initialize history tracking
        self.history: list[dict[str, object]] = []  # Each history entry is a dict with curve data
        self.history_index: int = -1
        self.max_history_size: int = MAX_HISTORY_SIZE

        # File operations are now handled by FileOperations class
        self._file_loading: bool = False  # Track if file loading is in progress

        # Initialize centering state
        self.auto_center_enabled: bool = False

        # Initialize image sequence state
        self.image_directory: str | None = None
        self.image_filenames: list[str] = []
        self.current_image_idx: int = 0

        # Playback functionality now handled by PlaybackController
        # Frame navigation functionality now handled by FrameNavigationController

        # Initialize dynamic instance variables that will be checked later
        self._point_spinbox_connected: bool = False
        self._stored_tooltips: dict[QWidget, str] = {}

        # Connect all signals via manager
        self.signal_manager.connect_all_signals()

        # Setup initial state
        self._update_ui_state()

        # Setup tab order for keyboard navigation
        self._setup_tab_order()

        # Auto-load burger footage and tracking data if available
        self.file_operations.load_burger_data_async()

        # Initialize tooltips as disabled by default
        self._toggle_tooltips()

        logger.info("MainWindow initialized successfully")

    def _on_store_selection_changed(self, selection: set[int]) -> None:
        """Handle selection changes from the store."""
        # Update UI to reflect new selection
        if selection:
            # Update point editor with first selected point (TODO: extract to PointEditorController)
            # min_idx = min(selection) - will be used when PointEditorController is extracted
            # _update_point_editor will be moved to PointEditorController
            pass  # For now, just update UI state
        self._update_ui_state()

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
    def _on_file_loaded(self, file_path: str) -> None:
        """Handle successful file loading from FileOperations."""
        logger.info(f"File loaded: {file_path}")
        self._update_ui_state()

    @Slot(str)
    def _on_file_saved(self, file_path: str) -> None:
        """Handle successful file save from FileOperations."""
        logger.info(f"File saved: {file_path}")
        self._update_ui_state()

    # ==================== Timeline Control Handlers ====================

    @Slot(int)
    @Slot(int)
    def _on_frame_changed_from_controller(self, frame: int) -> None:
        """Handle frame change from the navigation controller.

        The controller has already updated the spinbox/slider and state manager,
        so we just need to update other dependent components.
        """
        logger.debug(f"[FRAME] Frame changed via controller to: {frame}")
        # Update dependent components using existing logic
        self._update_frame_display(frame, update_state_manager=False)

    def _update_frame_display(self, frame: int, update_state_manager: bool = True) -> None:
        """Shared method to update frame display across all UI components.

        Note: Spinbox/slider updates are now handled by FrameNavigationController.
        """
        # Controller now handles spinbox/slider synchronization

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

    # Frame navigation methods removed - now handled by FrameNavigationController

    # Playback methods removed - now handled by PlaybackController
    # The controller manages play/pause, FPS changes, and oscillating playback

    def _get_current_frame(self) -> int:
        """Get the current frame number."""
        return self.frame_nav_controller.get_current_frame()

    def _set_current_frame(self, frame: int) -> None:
        """Set the current frame with UI updates.

        Now delegates to FrameNavigationController.
        """
        self.frame_nav_controller.set_frame(frame)

    @property
    def current_frame(self) -> int:
        """Get the current frame number.

        Property accessor for better type safety and compatibility.
        Provides a clean interface for accessing the current frame.
        """
        return self.frame_nav_controller.get_current_frame()

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        """Set the current frame number.

        Property setter for better type safety and compatibility.
        Provides a clean interface for setting the current frame.
        """
        self.frame_nav_controller.set_frame(value)

    # MainWindowProtocol required properties
    @property
    def selected_indices(self) -> list[int]:
        """Get the currently selected point indices."""
        return self.state_manager.selected_points

    @property
    def curve_data(self) -> list[tuple[int, float, float] | tuple[int, float, float, str]]:
        """Get the current curve data from the store."""
        # Always get data from the store (single source of truth)
        return self._curve_store.get_data()  # pyright: ignore[reportReturnType]

    @property
    def is_modified(self) -> bool:
        """Get the modification state."""
        return self.state_manager.is_modified

    # MainWindowProtocol required methods
    def restore_state(self, state: object) -> None:
        """Restore state from history (delegate to state manager)."""
        # This method is required by MainWindowProtocol but actual implementation
        # is handled by the state manager and services
        pass

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
    def _on_action_new(self) -> None:
        """Handle new file action (delegated to ActionHandlerController)."""
        self.action_controller._on_action_new()

    @Slot()
    def _on_action_open(self) -> None:
        """Handle open file action (delegated to ActionHandlerController)."""
        self.action_controller._on_action_open()

    @Slot()
    def _on_action_save(self) -> None:
        """Handle save file action (delegated to ActionHandlerController)."""
        self.action_controller._on_action_save()

    @Slot()
    def _on_action_save_as(self) -> None:
        """Handle save as action (delegated to ActionHandlerController)."""
        self.action_controller._on_action_save_as()

    def _cleanup_file_load_thread(self) -> None:
        """Clean up file loading thread - delegates to FileOperations."""
        logger.info("[PYTHON-THREAD] _cleanup_file_load_thread called - delegating to FileOperations")
        if hasattr(self, "file_operations"):
            self.file_operations.cleanup_threads()
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
    def _on_action_undo(self) -> None:
        """Handle undo action (delegated to ActionHandlerController)."""
        self.action_controller._on_action_undo()

    @Slot()
    def _on_action_redo(self) -> None:
        """Handle redo action (delegated to ActionHandlerController)."""
        self.action_controller._on_action_redo()

    @Slot()
    def _on_action_zoom_in(self) -> None:
        """Handle zoom in action (delegated to ActionHandlerController)."""
        self.action_controller._on_action_zoom_in()

    @Slot()
    def _on_action_zoom_out(self) -> None:
        """Handle zoom out action (delegated to ActionHandlerController)."""
        self.action_controller._on_action_zoom_out()

    @Slot()
    def _on_action_reset_view(self) -> None:
        """Handle reset view action (delegated to ActionHandlerController)."""
        self.action_controller._on_action_reset_view()

    @Slot()
    def _on_load_images(self) -> None:
        """Handle load background images action (delegated to ActionHandlerController)."""
        self.action_controller._on_load_images()

    @Slot()
    def _on_export_data(self) -> None:
        """Handle export curve data action (delegated to ActionHandlerController)."""
        self.action_controller._on_export_data()

    @Slot()
    def _on_select_all(self) -> None:
        """Handle select all action (delegated to ActionHandlerController)."""
        self.action_controller._on_select_all()

    @Slot()
    def _on_add_point(self) -> None:
        """Handle add point action (delegated to ActionHandlerController)."""
        self.action_controller._on_add_point()

    @Slot()
    def _on_zoom_fit(self) -> None:
        """Handle zoom fit action (delegated to ActionHandlerController)."""
        self.action_controller._on_zoom_fit()

    @Slot()
    def _on_smooth_curve(self) -> None:
        """Handle smooth curve action (delegated to ActionHandlerController)."""
        self.action_controller._on_smooth_curve()

    @Slot()
    def _on_filter_curve(self) -> None:
        """Handle filter curve action (delegated to ActionHandlerController)."""
        self.action_controller._on_filter_curve()

    @Slot()
    def _on_analyze_curve(self) -> None:
        """Handle analyze curve action (delegated to ActionHandlerController)."""
        self.action_controller._on_analyze_curve()

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
            curve_data = self._curve_store.get_data()
            if idx < len(curve_data):
                point_data = curve_data[idx]
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

        # Update frame controls via controller
        total_frames = self.state_manager.total_frames
        # Use controller's set_frame_range instead of direct manipulation
        self.frame_nav_controller.set_frame_range(1, max(total_frames, 1000))
        if self.total_frames_label:
            self.total_frames_label.setText(str(total_frames))

        # Update info labels - use curve widget data if available
        if self.curve_widget:
            point_count = self._curve_store.point_count()
            self.point_count_label.setText(f"Points: {point_count}")

            if point_count > 0:
                # Calculate bounds from curve data
                from core.point_types import safe_extract_point

                x_coords = []
                y_coords = []
                for point in self._curve_store.get_data():
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
        """Update zoom label (delegated to ActionHandlerController)."""
        self.action_controller._update_zoom_label()

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
            curve_data = self._get_current_curve_data()  # pyright: ignore[reportAssignmentType]

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
            data_service = get_data_service()

            # Get comprehensive status for all frames that have points
            frame_status = data_service.get_frame_range_point_status(curve_data)  # pyright: ignore[reportArgumentType]

            # Update timeline tabs with comprehensive point status
            for frame, status_data in frame_status.items():
                # Unpack all status fields from the enhanced DataService response
                (
                    keyframe_count,
                    interpolated_count,
                    tracked_count,
                    endframe_count,
                    normal_count,
                    is_startframe,
                    is_inactive,
                    has_selected,
                ) = status_data

                self.timeline_tabs.update_frame_status(
                    frame,
                    keyframe_count=keyframe_count,
                    interpolated_count=interpolated_count,
                    tracked_count=tracked_count,
                    endframe_count=endframe_count,
                    normal_count=normal_count,
                    is_startframe=is_startframe,
                    is_inactive=is_inactive,
                    has_selected=has_selected,
                )

            logger.debug(f"Updated timeline tabs with {len(frame_status)} frames of point data")

        except Exception as e:
            logger.warning(f"Could not update timeline tabs with point data: {e}")

    def _get_current_curve_data(self) -> CurveDataList:
        """Get current curve data (delegated to ActionHandlerController)."""
        return self.action_controller._get_current_curve_data()

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
            curve_data = self._curve_store.get_data()
            if idx < len(curve_data):
                from core.point_types import safe_extract_point

                _, _, y, _ = safe_extract_point(curve_data[idx])
                self.curve_widget.update_point(idx, value, y)
                self.state_manager.is_modified = True

    @Slot(float)
    def _on_point_y_changed(self, value: float) -> None:
        """Handle Y coordinate change in properties panel."""
        selected_indices = self.state_manager.selected_points
        if len(selected_indices) == 1 and self.curve_widget:
            idx = selected_indices[0]
            curve_data = self._curve_store.get_data()
            if idx < len(curve_data):
                from core.point_types import safe_extract_point

                _, x, _, _ = safe_extract_point(curve_data[idx])
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
        """Apply smoothing operation (delegated to ActionHandlerController)."""
        self.action_controller.apply_smooth_operation()

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

        # Stop any file operation threads
        if hasattr(self, "file_operations"):
            self.file_operations.cleanup_threads()

        logger.info("[KEEP-ALIVE] Worker and thread cleaned up")

        # Accept the close event
        event.accept()
        logger.info("MainWindow closed with proper cleanup")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
