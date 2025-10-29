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
    from protocols.ui import CurveViewProtocol
    from ui.timeline_tabs import TimelineTabWidget

    from .curve_view_widget import CurveViewWidget
    from .service_facade import ServiceFacade

# Import PySide6 modules
from PySide6.QtCore import QEvent, QObject, Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QKeyEvent,
)

# These widget imports are needed for type annotations of class attributes
# The actual widgets are created in UIInitializationController
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
from core.type_aliases import CurveDataInput, CurveDataList
from services import get_data_service
from stores import StoreManager, get_store_manager
from stores.application_state import get_application_state

# Import local modules
# CurveView removed - using CurveViewWidget
from .controllers import (
    ActionHandlerController,
    MultiPointTrackingController,
    PointEditorController,
    SignalConnectionManager,
    TimelineController,
    UIInitializationController,
    ViewManagementController,
)
from .curve_view_widget import CurveViewWidget
from .dark_theme_stylesheet import get_dark_theme_stylesheet
from .file_operations import FileOperations
from .global_event_filter import GlobalEventFilter
from .keyboard_shortcuts import ShortcutManager
from .protocols.controller_protocols import (
    ActionHandlerProtocol,
    MultiPointTrackingProtocol,
    PointEditorProtocol,
    SignalConnectionProtocol,
    TimelineControllerProtocol,
    UIInitializationProtocol,
    ViewManagementProtocol,
)
from .shortcut_registry import ShortcutRegistry
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

    # Class variables
    # _theme_initialized is set dynamically when theme is applied (do NOT pre-declare as False)

    # Attributes initialized in __init__ - declare for type safety
    _file_loading: bool = False  # Track file loading state
    # Note: Auto-centering state stored in curve_widget.centering_mode (single source of truth)

    # Widget type annotations - initialized by UIInitializationController
    frame_spinbox: QSpinBox | None = None
    total_frames_label: QLabel | None = None
    frame_slider: QSlider | None = None
    timeline_tabs: "TimelineTabWidget | None" = None
    # Removed orphaned playback button attributes - they were never used
    btn_play_pause: QPushButton | None = None  # Used for playback control (not visible but functional)
    fps_spinbox: QSpinBox | None = None
    # playback_timer was moved to TimelineController
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
    type_label: QLabel | None = None
    tracking_panel_dock: QDockWidget | None = None
    tracking_panel: TrackingPointsPanel | None = None
    visualization_panel_dock: QDockWidget | None = None

    # Actions initialized by UIInitializationController
    action_new: QAction | None = None
    action_open: QAction | None = None
    action_save: QAction | None = None
    action_save_as: QAction | None = None
    action_load_images: QAction | None = None
    action_export_data: QAction | None = None
    action_quit: QAction | None = None
    action_undo: QAction | None = None
    action_redo: QAction | None = None
    action_select_all: QAction | None = None
    action_add_point: QAction | None = None
    action_zoom_in: QAction | None = None
    action_zoom_out: QAction | None = None
    action_zoom_fit: QAction | None = None
    action_reset_view: QAction | None = None
    action_smooth_curve: QAction | None = None
    action_filter_curve: QAction | None = None
    action_analyze_curve: QAction | None = None
    action_next_frame: QAction | None = None
    action_prev_frame: QAction | None = None
    action_first_frame: QAction | None = None
    action_last_frame: QAction | None = None
    action_oscillate_playback: QAction | None = None

    # MainWindowProtocol required attributes
    # Note: selected_indices and curve_data are provided as properties below
    point_name: str = "default_point"
    point_color: str = "#FF0000"
    undo_button: QPushButton | None = None  # Required by protocol, created from action
    redo_button: QPushButton | None = None  # Required by protocol, created from action
    save_button: QPushButton | None = None  # Required by protocol, created from action

    # Controllers - initialized in __init__
    timeline_controller: TimelineControllerProtocol
    action_controller: ActionHandlerProtocol
    ui_init_controller: UIInitializationProtocol
    view_management_controller: ViewManagementProtocol
    point_editor_controller: PointEditorProtocol
    background_controller: ViewManagementProtocol
    tracking_controller: MultiPointTrackingProtocol
    signal_manager: SignalConnectionProtocol

    def __init__(self, parent: QWidget | None = None, auto_load_data: bool = True):
        """Initialize the MainWindow with enhanced UI functionality.

        Args:
            parent: Optional parent widget
            auto_load_data: If True, automatically load burger footage/tracking data. Set to False in tests.
        """
        super().__init__(parent)

        # Setup basic window properties
        self.setWindowTitle("CurveEditor")
        self.setMinimumSize(1024, 768)
        self.resize(1400, 900)

        # Apply dark theme to entire application
        # CRITICAL: Only apply stylesheet once to prevent timeout after 1580+ tests.
        # When stylesheet is applied at app level, Qt reprocesses ALL widgets including
        # accumulated test widgets, causing 30+ second delays (see UNIFIED_TESTING_GUIDE).
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            # Check if stylesheet already applied (avoid reapplying in tests)
            # Track application initialization state in MainWindow instead of QApplication
            # This avoids type checking issues with dynamic attributes
            if not hasattr(MainWindow, "_theme_initialized"):
                # Use Fusion style for better dark theme support
                _ = app.setStyle("Fusion")
                # Apply the dark theme stylesheet
                app.setStyleSheet(get_dark_theme_stylesheet())
                MainWindow._theme_initialized: bool = True
                logger.info("Applied dark theme to application")
            else:
                logger.debug("Dark theme already applied, skipping")

        # Initialize managers
        self.state_manager: StateManager = StateManager(self)
        self.shortcut_manager: ShortcutManager = ShortcutManager(self)

        # Initialize session manager for automatic session persistence
        from ui.session_manager import SessionManager
        self._session_manager: SessionManager = SessionManager()

        # Get store manager (CurveDataStore removed in Phase 6.3)
        self._store_manager: StoreManager = get_store_manager()

        # Connect StateManager to FrameStore for delegation
        self._store_manager.set_state_manager(self.state_manager)

        # Initialize controllers (typed as protocols for better decoupling)
        from protocols.ui import MainWindowProtocol
        from ui.controllers.frame_change_coordinator import FrameChangeCoordinator

        from .service_facade import get_service_facade

        self.timeline_controller = TimelineController(self.state_manager, self)
        self.action_controller = ActionHandlerController(
            self.state_manager,  # pyright: ignore[reportArgumentType]
            self,  # pyright: ignore[reportArgumentType]
        )
        self.ui_init_controller = UIInitializationController(self)
        self.view_management_controller = ViewManagementController(self)  # pyright: ignore[reportAttributeAccessIssue]
        self.background_controller = self.view_management_controller
        self.point_editor_controller = PointEditorController(self, self.state_manager)  # pyright: ignore[reportAttributeAccessIssue]
        self.tracking_controller = MultiPointTrackingController(self)  # pyright: ignore[reportArgumentType]

        # Frame change coordinator (replaces 6 independent frame_changed connections)
        self.frame_change_coordinator: FrameChangeCoordinator = FrameChangeCoordinator(self)

        self.signal_manager = SignalConnectionManager(self)

        # Initialize service facade
        self.services: ServiceFacade = get_service_facade(cast(MainWindowProtocol, cast(object, self)))

        # Initialize file operations manager
        self.file_operations: FileOperations = FileOperations(self, self.state_manager, self.services)

        # Initialize UI components container for organized widget management
        self.ui: UIComponents = UIComponents(self)

        # Multi-point tracking now managed by MultiPointTrackingController

        # Initialize all UI components via controller
        self.ui_init_controller.initialize_ui()

        # Legacy attributes for backward compatibility
        self._curve_view_deprecated: CurveViewWidget | None = None  # Private backing for deprecated curve_view property

        # Initialize history tracking
        self.history: list[dict[str, object]] = []  # Each history entry is a dict with curve data
        self.history_index: int = -1
        self.max_history_size: int = MAX_HISTORY_SIZE

        # File operations are now handled by FileOperations class
        # Note: _file_loading already declared at class level (line 104)

        # Initialize centering state
        # Note: Auto-centering state stored in curve_widget.centering_mode

        # Image data now managed by ViewManagementController

        # Playback and frame navigation now handled by TimelineController

        # Initialize dynamic instance variables that will be checked later
        self._point_spinbox_connected: bool = False

        # Connect all signals via manager
        self.signal_manager.connect_all_signals()

        # Initialize global keyboard shortcut system
        self._init_global_shortcuts()

        # Verify all critical connections are established
        self._verify_connections()

        # Setup initial state
        self.update_ui_state()

        # Setup tab order for keyboard navigation
        self._setup_tab_order()

        # Auto-load session data (or fallback to burger data if no session exists)
        if auto_load_data:
            self._session_manager.load_session_or_fallback(self)

        # Initialize tooltips as disabled by default
        self.view_management_controller.toggle_tooltips()

        logger.info("MainWindow initialized successfully")

    def on_store_selection_changed(self, selection: set[int], curve_name: str | None = None) -> None:
        """Handle store selection changed.

        Phase 4: Removed __default__ - curve_name is now optional.

        Args:
            selection: Selected indices
            curve_name: Curve with selection change (None uses active curve)
        """
        # Delegate to point editor controller
        self.point_editor_controller.on_store_selection_changed(selection, curve_name)
        self.update_ui_state()

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

    def _init_global_shortcuts(self) -> None:
        """Initialize the global keyboard shortcut system."""
        from core.commands.shortcut_commands import (
            CenterViewCommand,
            DeleteCurrentFrameKeyframeCommand,
            DeletePointsCommand,
            DeselectAllCommand,
            FitBackgroundCommand,
            InsertTrackShortcutCommand,
            NudgePointsCommand,
            RedoCommand,
            SelectAllCommand,
            SetEndframeCommand,
            SetTrackingDirectionCommand,
            UndoCommand,
        )
        from core.models import TrackingDirection

        # Create shortcut registry
        self.shortcut_registry: ShortcutRegistry = ShortcutRegistry()

        # Register shortcuts
        # Undo/Redo shortcuts
        self.shortcut_registry.register(UndoCommand())
        self.shortcut_registry.register(RedoCommand())

        # Editing shortcuts
        self.shortcut_registry.register(SetEndframeCommand())
        self.shortcut_registry.register(DeletePointsCommand())
        self.shortcut_registry.register(DeleteCurrentFrameKeyframeCommand())

        # Insert Track shortcut (3DEqualizer-style gap filling)
        self.shortcut_registry.register(InsertTrackShortcutCommand())

        # Tracking direction shortcuts
        self.shortcut_registry.register(SetTrackingDirectionCommand(TrackingDirection.TRACKING_BW, "Shift+1"))
        self.shortcut_registry.register(SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW, "Shift+2"))
        self.shortcut_registry.register(SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW_BW, "Shift+F3"))
        # Global registrations for international keyboard symbols (for when table doesn't have focus)
        self.shortcut_registry.register(SetTrackingDirectionCommand(TrackingDirection.TRACKING_BW, "!"))
        self.shortcut_registry.register(
            SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW, '"')  # German layout
        )
        self.shortcut_registry.register(
            SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW, "@")  # US layout
        )

        # View shortcuts
        self.shortcut_registry.register(CenterViewCommand())
        self.shortcut_registry.register(FitBackgroundCommand())

        # Nudging shortcuts (numpad 2/4/6/8)
        self.shortcut_registry.register(NudgePointsCommand("4", -1, 0))  # Left
        self.shortcut_registry.register(NudgePointsCommand("6", 1, 0))  # Right
        self.shortcut_registry.register(NudgePointsCommand("8", 0, -1))  # Up
        self.shortcut_registry.register(NudgePointsCommand("2", 0, 1))  # Down

        # Selection shortcuts
        self.shortcut_registry.register(SelectAllCommand())
        self.shortcut_registry.register(DeselectAllCommand())

        # Install global event filter
        self.global_event_filter: GlobalEventFilter = GlobalEventFilter(self, self.shortcut_registry)
        app = QApplication.instance()
        if app:
            app.installEventFilter(self.global_event_filter)
            logger.info(
                "Global keyboard shortcut system initialized with %d shortcuts",
                len(self.shortcut_registry.list_shortcuts()),
            )

    @Slot(str)
    def on_file_changed(self, file_path: str) -> None:
        """Handle file path changes."""
        self.setWindowTitle(self.state_manager.get_window_title())
        if file_path:
            logger.info(f"File changed to: {file_path}")

    @Slot(bool)
    def on_modified_changed(self, modified: bool) -> None:
        """Handle modification status changes."""
        self.setWindowTitle(self.state_manager.get_window_title())
        if modified:
            logger.debug("Document marked as modified")

    @Slot(str)
    def on_file_loaded(self, file_path: str) -> None:
        """Handle successful file loading from FileOperations."""
        logger.info(f"File loaded: {file_path}")
        self.update_ui_state()

    @Slot(str)
    def on_file_saved(self, file_path: str) -> None:
        """Handle successful file save from FileOperations."""
        logger.info(f"File saved: {file_path}")
        self.update_ui_state()

    # ==================== Timeline Control Handlers ====================

    # REMOVED: on_frame_changed_from_controller(self, frame: int) method (dead code)
    # This method did nothing except log a debug message. It was connected to
    # TimelineController.frame_changed signal which has been removed (redundant).
    # All frame change handling is now done via ApplicationState → StateManager
    # → FrameChangeCoordinator with proper QueuedConnection timing.

    def _update_frame_display(self, frame: int) -> None:
        """
        Update frame display using KISS/SOLID Observer pattern.

        Simply updates ApplicationState - all observers react automatically via signals.
        This eliminates cascade calls and tight coupling.
        """
        # Single source of truth update - observers handle the rest
        get_application_state().set_frame(frame)
        logger.debug(f"[FRAME] ApplicationState updated to frame {frame} - signals will notify observers")

    # Frame navigation and playback methods removed - now handled by TimelineController
    # The controller manages play/pause, FPS changes, and oscillating playback

    def _get_current_frame(self) -> int:
        """Get the current frame number."""
        return self.timeline_controller.get_current_frame()

    def _set_current_frame(self, frame: int) -> None:
        """Set the current frame with UI updates.

        Now delegates to TimelineController.
        """
        self.timeline_controller.set_frame(frame)

    @property
    def current_frame(self) -> int:
        """Get the current frame number.

        Property accessor for better type safety and compatibility.
        Provides a clean interface for accessing the current frame.
        """
        return self.timeline_controller.get_current_frame()

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        """Set the current frame number.

        Property setter for better type safety and compatibility.
        Provides a clean interface for setting the current frame.
        """
        self.timeline_controller.set_frame(value)

    # MainWindowProtocol required properties
    @property
    def selected_indices(self) -> list[int]:
        """Get the currently selected point indices."""
        state = get_application_state()
        active = state.active_curve
        if not active:
            return []
        return sorted(state.get_selection(active))

    @selected_indices.setter
    def selected_indices(self, value: list[int]) -> None:
        """Set the selected point indices."""
        self.state_manager.set_selected_points(value)

    @property
    def curve_data(self) -> CurveDataList:
        """Get the current curve data directly from ApplicationState.

        Uses ApplicationState as single source of truth per architectural guidelines.
        """
        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            return []
        _, curve_data = cd
        return curve_data

    @curve_data.setter
    def curve_data(self, value: CurveDataList) -> None:
        """Set the curve data via ApplicationState."""
        state = get_application_state()
        active_curve = state.active_curve
        if active_curve:
            state.set_curve_data(active_curve, value)

    @property
    def is_modified(self) -> bool:
        """Get the modification state."""
        return self.state_manager.is_modified

    @property
    def curve_view(self) -> "CurveViewProtocol | None":
        """Get the curve view widget (MainWindowProtocol requirement).

        Returns the curve_widget which implements CurveViewProtocol.
        This property exists for protocol conformance.
        """
        return cast("CurveViewProtocol | None", self.curve_widget)

    @property
    def active_timeline_point(self) -> str | None:
        """Get the active timeline point (which tracking point's timeline is displayed)."""
        return self.state_manager.active_timeline_point

    @active_timeline_point.setter
    def active_timeline_point(self, point_name: str | None) -> None:
        """Set the active timeline point (which tracking point's timeline to display)."""
        self.state_manager.active_timeline_point = point_name

    @property
    def multi_point_controller(self) -> object:  # MultiPointTrackingProtocol
        """Get multi-point tracking controller (alias for tracking_controller)."""
        return self.tracking_controller

    # Additional MainWindowProtocol required properties (for protocol conformance)
    @property
    def image_filenames(self) -> list[str]:
        """Get list of loaded image filenames."""
        # Access view controller's image state directly
        return getattr(self.view_management_controller, "image_filenames", [])

    @property
    def current_image_idx(self) -> int:
        """Get current image index."""
        # Access view controller's current image index
        return getattr(self.view_management_controller, "current_image_idx", 0)

    @property
    def file_load_worker(self) -> object | None:
        """Get file load worker instance (if active)."""
        # Access file operations worker if it exists
        return getattr(self.file_operations, "file_load_worker", None)

    @property
    def tracked_data(self) -> dict[str, CurveDataList]:
        """Get tracked data from multi-point controller."""
        return self.tracking_controller.tracked_data

    @property
    def active_points(self) -> list[str]:
        """Get list of active tracking point names."""
        return list(self.tracking_controller.tracked_data.keys())

    @property
    def session_manager(self) -> object:
        """Get session manager instance."""
        # Return session manager if it exists (may be added in future)
        return getattr(self, "_session_manager", None)

    @property
    def view_update_manager(self) -> object:
        """Get view update manager instance."""
        # Return view update manager if it exists (may be added in future)
        return getattr(self, "_view_update_manager", None)

    # MainWindowProtocol required methods
    def restore_state(self, _state: object) -> None:
        """Restore state from history (delegate to state manager)."""
        # This method is required by MainWindowProtocol but actual implementation
        # is handled by the state manager and services

    def set_tracked_data_atomic(self, data: dict[str, object]) -> None:
        """Set tracked data atomically using ApplicationState batch operations.

        Args:
            data: Dictionary mapping curve names to curve data
        """
        state = get_application_state()

        # Use batch mode to set all curves atomically
        with state.batch_updates():
            for curve_name, curve_data in data.items():
                # Convert generic object to CurveDataList if needed
                if isinstance(curve_data, list):
                    state.set_curve_data(curve_name, curve_data)

    def set_file_loading_state(self, loading: bool) -> None:
        """Set file loading state flag.

        Args:
            loading: True if file loading is in progress, False otherwise
        """
        self._file_loading = loading

    def update_status(self, message: str) -> None:
        """Update status bar message."""
        status_bar = self.statusBar()  # Returns non-None QStatusBar
        status_bar.showMessage(message)

    @Slot(int)
    @Slot(int)
    def _on_timeline_tab_clicked(self, frame: int) -> None:
        """Handle timeline tab click (delegated to TimelineController)."""
        self.timeline_controller.on_timeline_tab_clicked(frame)

    @Slot(int)
    def _on_timeline_tab_hovered(self, frame: int) -> None:
        """Handle timeline tab hover (delegated to TimelineController)."""
        self.timeline_controller.on_timeline_tab_hovered(frame)

    # ==================== Action Handlers ====================

    @Slot()
    def on_action_new(self) -> None:
        """Handle new file action (delegated to ActionHandlerController)."""
        self.action_controller.on_action_new()

    @Slot()
    def on_action_open(self) -> None:
        """Handle open file action (delegated to ActionHandlerController)."""
        self.action_controller.on_action_open()

    @Slot()
    def on_action_save(self) -> None:
        """Handle save file action (delegated to ActionHandlerController)."""
        self.action_controller.on_action_save()

    @Slot()
    def on_action_save_as(self) -> None:
        """Handle save as action (delegated to ActionHandlerController)."""
        self.action_controller.on_action_save_as()

    def _cleanup_file_load_thread(self) -> None:
        """Clean up file loading thread - delegates to FileOperations."""
        logger.info("[PYTHON-THREAD] _cleanup_file_load_thread called - delegating to FileOperations")
        # file_operations is always initialized in __init__
        self.file_operations.cleanup_threads()
        return

    @Slot(list)
    def on_tracking_data_loaded(self, data: CurveDataInput) -> None:
        """Handle tracking data loaded (delegated to MultiPointTrackingController)."""
        self.tracking_controller.on_tracking_data_loaded(data)
        # Save session after loading new data
        self._save_current_session()

    @Slot(dict)
    def on_multi_point_data_loaded(self, multi_data: dict[str, CurveDataList]) -> None:
        """Handle multi-point data loaded (delegated to MultiPointTrackingController)."""
        self.tracking_controller.on_multi_point_data_loaded(multi_data)
        # Save session after loading new data
        self._save_current_session()

    @Slot(str, list)
    def on_image_sequence_loaded(self, image_dir: str, image_files: list[str]) -> None:
        """Handle image sequence loaded (delegated to ViewManagementController)."""
        self.background_controller.on_image_sequence_loaded(image_dir, image_files)
        # Save session after loading new images
        self._save_current_session()

    @Slot(int, str)
    def on_file_load_progress(self, progress: int, message: str) -> None:
        """Handle file loading progress updates."""
        if self.status_label:
            self.status_label.setText(f"{message} ({progress}%)")
        logger.debug(f"File load progress: {progress}% - {message}")

    @Slot(str)
    def on_file_load_error(self, error_message: str) -> None:
        """Handle file loading errors."""
        logger.error(f"File loading error: {error_message}")
        if self.status_label:
            self.status_label.setText(f"Error: {error_message}")

    @Slot()
    def on_file_load_finished(self) -> None:
        """Handle file loading completion - worker ready for next load."""
        if self.status_label:
            self.status_label.setText("File loading completed")
        logger.info("[PYTHON-THREAD] File loading finished - worker ready for next load")
        # Mark loading as complete but keep worker alive for reuse
        self._file_loading = False

    @Slot()
    def on_action_undo(self) -> None:
        """Handle undo action (delegated to ActionHandlerController)."""
        logger.info("MainWindow.on_action_undo called")
        self.action_controller.on_action_undo()

    @Slot()
    def on_action_redo(self) -> None:
        """Handle redo action (delegated to ActionHandlerController)."""
        self.action_controller.on_action_redo()

    @Slot()
    def on_action_zoom_in(self) -> None:
        """Handle zoom in action (delegated to ActionHandlerController)."""
        self.action_controller.on_action_zoom_in()

    @Slot()
    def on_action_zoom_out(self) -> None:
        """Handle zoom out action (delegated to ActionHandlerController)."""
        self.action_controller.on_action_zoom_out()

    @Slot()
    def on_action_reset_view(self) -> None:
        """Handle reset view action (delegated to ActionHandlerController)."""
        self.action_controller.on_action_reset_view()

    @Slot()
    def on_toggle_grid(self) -> None:
        """Toggle the grid visibility."""
        if self.show_grid_cb:
            # Toggle the checkbox state, which will trigger the existing handler
            new_state = not self.show_grid_cb.isChecked()
            self.show_grid_cb.setChecked(new_state)

    @Slot()
    def on_increase_grid_size(self) -> None:
        """Increase the grid cell size."""
        if self.curve_view:
            current_size = self.curve_view.visual.grid_size
            # Increase by 10 pixels, max 200
            new_size = min(current_size + 10, 200)
            self.curve_view.visual.grid_size = new_size
            self.curve_view.update()
            logger.info(f"Grid size increased to {new_size}")

    @Slot()
    def on_decrease_grid_size(self) -> None:
        """Decrease the grid cell size."""
        if self.curve_view:
            current_size = self.curve_view.visual.grid_size
            # Decrease by 10 pixels, min 10
            new_size = max(current_size - 10, 10)
            self.curve_view.visual.grid_size = new_size
            self.curve_view.update()
            logger.info(f"Grid size decreased to {new_size}")

    @Slot()
    def on_load_images(self) -> None:
        """Handle load background images action (delegated to ActionHandlerController)."""
        self.action_controller.on_load_images()

    @Slot()
    def on_export_data(self) -> None:
        """Handle export curve data action (delegated to ActionHandlerController)."""
        self.action_controller.on_export_data()

    @Slot()
    def on_select_all(self) -> None:
        """Handle select all action (delegated to ActionHandlerController)."""
        self.action_controller.on_select_all()

    @Slot()
    def on_add_point(self) -> None:
        """Handle add point action (delegated to ActionHandlerController)."""
        self.action_controller.on_add_point()

    @Slot()
    def on_zoom_fit(self) -> None:
        """Handle zoom fit action (delegated to ActionHandlerController)."""
        self.action_controller.on_zoom_fit()

    @Slot()
    def on_smooth_curve(self) -> None:
        """Handle smooth curve action (delegated to ActionHandlerController)."""
        self.action_controller.on_smooth_curve()

    @Slot()
    def on_filter_curve(self) -> None:
        """Handle filter curve action (delegated to ActionHandlerController)."""
        self.action_controller.on_filter_curve()

    @Slot()
    def on_analyze_curve(self) -> None:
        """Handle analyze curve action (delegated to ActionHandlerController)."""
        self.action_controller.on_analyze_curve()

    # ==================== State Change Handlers ====================

    @Slot(set)
    def on_selection_changed(self, indices: set[int]) -> None:
        """Handle selection change from state manager (delegated to PointEditorController)."""
        # Convert set to sorted list for compatibility with PointEditorController
        self.point_editor_controller.on_selection_changed(sorted(indices))

    @Slot()
    def on_view_state_changed(self) -> None:
        """Handle view state change from state manager."""
        self.update_zoom_label()

    # ==================== UI Update Methods ====================

    def _safe_set_label(self, label: QLabel | None, text: str) -> None:
        """Set label text if label exists."""
        if label:
            label.setText(text)

    def _format_bounds_text(self, bounds: tuple[float, float, float, float] | None) -> str:
        """Format bounds tuple as display text."""
        if not bounds:
            return "Bounds: N/A"
        min_x, min_y, max_x, max_y = bounds
        return f"Bounds:\nX: [{min_x:.2f}, {max_x:.2f}]\nY: [{min_y:.2f}, {max_y:.2f}]"

    def _get_current_point_count_and_bounds(self) -> tuple[int, tuple[float, float, float, float] | None]:
        """Get current curve point count and bounds from ApplicationState.

        Uses ApplicationState as single source of truth per architectural guidelines.
        """
        app_state = get_application_state()

        # Get active curve data from single source of truth
        if (cd := app_state.active_curve_data) is None:
            return 0, None

        _, curve_data = cd

        if not curve_data:
            return 0, None

        # Calculate bounds from curve data
        x_coords = [float(point[1]) for point in curve_data]
        y_coords = [float(point[2]) for point in curve_data]
        bounds = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

        return len(curve_data), bounds

    def _update_history_actions(self) -> None:
        """Update undo/redo action states."""
        if self.action_undo:
            self.action_undo.setEnabled(self.state_manager.can_undo)
        if self.action_redo:
            self.action_redo.setEnabled(self.state_manager.can_redo)

    def _update_frame_controls(self) -> None:
        """Update frame spinbox and total frames label."""
        total_frames = get_application_state().get_total_frames()
        self.timeline_controller.set_frame_range(1, total_frames)
        self._safe_set_label(self.total_frames_label, str(total_frames))

    def _update_point_info_labels(self) -> None:
        """Update point count and bounds labels."""
        point_count, bounds = self._get_current_point_count_and_bounds()

        self._safe_set_label(self.point_count_label, f"Points: {point_count}")
        self._safe_set_label(self.bounds_label, self._format_bounds_text(bounds))

    def update_point_status_label(self) -> None:
        """Update point status label with current frame's point status."""
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Get active curve data - use active_curve_data property
        if (cd := app_state.active_curve_data) is None:
            self._safe_set_label(self.type_label, "Status: --")
            return
        _curve_name, curve_data = cd

        # Get current frame
        current_frame = app_state.current_frame

        # Check if curve has data
        if not curve_data:
            self._safe_set_label(self.type_label, "Status: --")
            return

        # Check if there's an exact point at current frame FIRST
        from core.models import CurvePoint, PointStatus

        points = [CurvePoint.from_tuple(p) for p in curve_data]
        current_point = next((p for p in points if p.frame == current_frame), None)

        # ENDFRAMES are ALWAYS displayed as active (they're the last active frame before a gap)
        # Check this BEFORE segment activity to ensure endframes always show correctly
        if current_point and current_point.status == PointStatus.ENDFRAME:
            self._safe_set_label(self.type_label, "Status: ENDFRAME")
            return

        # Now check segment activity (for non-ENDFRAME points)
        from core.curve_segments import SegmentedCurve

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)
        segment = segmented_curve.get_segment_at_frame(current_frame)

        # If in an inactive segment, show "Inactive" (tracked points after endframes)
        if segment is not None and not segment.is_active:
            self._safe_set_label(self.type_label, "Status: Inactive")
            return

        # In active segment - show point status if exists
        if current_point:
            # Display the point's status
            status_name = current_point.status.name
            self._safe_set_label(self.type_label, f"Status: {status_name}")
        else:
            # No point at current frame in active segment
            # This means position is interpolated between keyframes
            self._safe_set_label(self.type_label, "Status: INTERPOLATED")

    def update_ui_state(self) -> None:
        """Update UI elements based on current state."""
        self._update_history_actions()
        self._update_frame_controls()
        self._update_point_info_labels()
        self.update_point_status_label()

    def update_zoom_label(self) -> None:
        """Update zoom label (delegated to ActionHandlerController)."""
        self.action_controller.update_zoom_label()

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

            # Handle Page Up/Down globally for keyframe navigation
            elif key == Qt.Key.Key_PageUp:
                logger.debug("[EVENT_FILTER] Page Up pressed, navigating to previous keyframe")
                self.navigate_to_prev_keyframe()
                return True  # Consume event
            elif key == Qt.Key.Key_PageDown:
                logger.debug("[EVENT_FILTER] Page Down pressed, navigating to next keyframe")
                self.navigate_to_next_keyframe()
                return True  # Consume event

        return super().eventFilter(watched, event)  # Proper delegation to parent

    def update_cursor_position(self, x: float, y: float) -> None:
        """Update cursor position in status bar."""
        if self.position_label:
            self.position_label.setText(f"X: {x:.3f}, Y: {y:.3f}")

    # ==================== Curve Widget Signal Handlers ====================

    @Slot(int)
    def on_point_selected(self, index: int) -> None:
        """Handle point selection from curve widget."""
        logger.debug(f"Point {index} selected")

        # Auto-center on selected point if centering mode is enabled
        if self.curve_widget and self.curve_widget.centering_mode:
            curve_data = self.curve_widget.curve_data
            if curve_data and 0 <= index < len(curve_data):
                # Get frame from the selected point
                frame = curve_data[index][0]  # First element is frame number
                logger.debug(f"Auto-centering on point at frame {frame}")
                self.curve_widget.center_on_frame(frame)

        # Update properties panel will be handled by selection_changed signal

    @Slot(int, float, float)
    def on_point_moved(self, index: int, x: float, y: float) -> None:
        """Handle point movement from curve widget."""
        self.state_manager.is_modified = True
        logger.debug(f"Point {index} moved to ({x:.3f}, {y:.3f})")

    @Slot(list)
    def on_curve_selection_changed(self, indices: list[int]) -> None:
        """Handle selection change from curve widget."""
        # Update state manager
        self.state_manager.set_selected_points(indices)

        # Auto-center on selected point if centering mode is enabled and single point selected
        if self.curve_widget and self.curve_widget.centering_mode and len(indices) == 1:
            curve_data = self.curve_widget.curve_data
            index = indices[0]
            if curve_data and 0 <= index < len(curve_data):
                # Get frame from the selected point
                frame = curve_data[index][0]  # First element is frame number
                logger.debug(f"Auto-centering on selected point at frame {frame}")
                self.curve_widget.center_on_frame(frame)

        # Properties panel will be updated via state manager signal

    @Slot()
    def on_curve_view_changed(self) -> None:
        """Handle view changes from curve widget (syncs pan_offset to state_manager)."""
        # Sync pan_offset from curve_widget to state_manager for session save/restore.
        # Critical: Session persistence depends on this sync - without it, pan_offset
        # contains stale values when session is saved at application closeout.
        if self.curve_widget:
            self.state_manager.pan_offset = (
                self.curve_widget.pan_offset_x,
                self.curve_widget.pan_offset_y,
            )

        # Update zoom display
        self.update_zoom_label()

    @Slot(float)
    def on_curve_zoom_changed(self, zoom: float) -> None:
        """Handle zoom changes from curve widget."""
        # Update state manager and zoom label
        self.state_manager.zoom_level = zoom
        self.update_zoom_label()

    # ==================== Tracking Points Panel Handlers ====================

    def on_point_visibility_changed(self, point_name: str, visible: bool) -> None:
        """Handle point visibility change (delegated to MultiPointTrackingController)."""
        self.tracking_controller.on_point_visibility_changed(point_name, visible)

    def on_point_color_changed(self, point_name: str, color: str) -> None:
        """Handle point color change (delegated to MultiPointTrackingController)."""
        self.tracking_controller.on_point_color_changed(point_name, color)

    def on_point_deleted(self, point_name: str) -> None:
        """Handle point deletion (delegated to MultiPointTrackingController)."""
        self.tracking_controller.on_point_deleted(point_name)

    def on_point_renamed(self, old_name: str, new_name: str) -> None:
        """Handle point renaming (delegated to MultiPointTrackingController)."""
        self.tracking_controller.on_point_renamed(old_name, new_name)

    def update_tracking_panel(self) -> None:
        """Update tracking panel (delegated to MultiPointTrackingController)."""
        self.tracking_controller.update_tracking_panel()

    def _update_curve_display(self) -> None:
        """Update curve display (delegated to MultiPointTrackingController)."""
        self.tracking_controller.update_curve_display()

    # ==================== View Options Handlers ====================
    # View options are now handled by ViewManagementController

    # ==================== Frame Navigation Handlers ====================
    # Frame change handling now managed by FrameChangeCoordinator

    # ==================== Utility Methods ====================

    def update_timeline_tabs(self, curve_data: CurveDataInput | None = None) -> None:
        """Update timeline tabs (delegated to TimelineController)."""
        self.timeline_controller.update_timeline_tabs(curve_data)

    def get_current_curve_data(self) -> CurveDataList:
        """Get current curve data (delegated to ActionHandlerController)."""
        return self.action_controller.get_current_curve_data()

    def _verify_connections(self) -> None:
        """
        Verify all critical signal connections are established.

        Phase 6.3: CurveDataStore removed, verification simplified.
        """
        from stores import ConnectionVerifier

        verifier = ConnectionVerifier()

        # Phase 6.3: CurveDataStore connections removed (migrated to ApplicationState)
        # All state synchronization now handled through ApplicationState signals

        # Verify all connections exist
        all_connected, _ = verifier.verify_all()

        if not all_connected:
            import os

            # Only fail loud in debug mode
            if os.environ.get("DEBUG_MODE"):
                verifier.raise_if_failed()
                return

            # Guard: In production mode, log warnings instead of raising
            failures = verifier.get_failed_connections()
            if failures:
                logger.warning(f"Missing {len(failures)} connections")
                verifier.log_report()
            return

        # All critical connections verified
        logger.debug("All critical connections verified")

    def add_to_history(self) -> None:
        """Add current state to history (called by curve widget)."""
        self.services.add_to_history()

        # Update history-related UI state
        if self.action_undo:
            self.action_undo.setEnabled(self.state_manager.can_undo)
        if self.action_redo:
            self.action_redo.setEnabled(self.state_manager.can_redo)

    @Slot(float)
    def on_point_x_changed(self, value: float) -> None:
        """Handle X coordinate change in properties panel (delegated to PointEditorController)."""
        self.point_editor_controller.on_point_x_changed(value)

    @Slot(float)
    def on_point_y_changed(self, value: float) -> None:
        """Handle Y coordinate change in properties panel (delegated to PointEditorController)."""
        self.point_editor_controller.on_point_y_changed(value)

    # ==================== Public Methods for External Use ====================

    def set_curve_view(self, curve_view: CurveViewWidget | None) -> None:
        """Set the curve view widget (legacy method - now uses CurveViewWidget)."""
        self._curve_view_deprecated = curve_view
        logger.info("Legacy curve view reference set")

    def get_view_options(self) -> dict[str, object]:
        """Get current view options."""
        return self.view_management_controller.get_view_options()

    def set_centering_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-centering on frame change.

        Args:
            enabled: Whether to enable auto-centering
        """
        # Update the curve widget if available (single source of truth)
        # curve_widget is Optional
        if self.curve_widget is not None:
            # Directly set centering_mode on curve widget
            self.curve_widget.centering_mode = enabled

            # Log the state change
            logger.info(f"Auto-centering {'enabled' if enabled else 'disabled'}")

            # Update status bar
            # statusBar() is a QMainWindow method, always available
            self.statusBar().showMessage(f"Auto-center on frame change: {'ON' if enabled else 'OFF'}", 3000)

    def apply_smooth_operation(self) -> None:
        """Apply smoothing operation (delegated to ActionHandlerController)."""
        self.action_controller.apply_smooth_operation()

    def _get_navigation_frames(self) -> list[int]:
        """Collect all navigation frames (keyframes, endframes, startframes) from current curve.

        Returns:
            Sorted list of frame numbers that are navigable (keyframes, endframes, or startframes).
            Returns empty list if no curve data loaded.
        """
        # Get active curve data directly from ApplicationState
        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            return []

        _, curve_data = cd

        if not curve_data:
            return []

        # Collect keyframes and endframes from point data
        nav_frames = [int(point[0]) for point in curve_data if len(point) >= 4 and point[3] in ["keyframe", "endframe"]]

        # Add startframes from DataService analysis
        try:
            data_service = get_data_service()
            frame_status = data_service.get_frame_range_point_status(curve_data)
            for frame, status in frame_status.items():
                if status.is_startframe and frame not in nav_frames:
                    nav_frames.append(frame)
        except Exception as e:
            logger.warning(f"Could not identify startframes: {e}")

        return sorted(nav_frames)

    def _navigate_to_adjacent_frame(self, direction: int) -> None:
        """Navigate to adjacent navigation frame.

        Args:
            direction: -1 for previous, +1 for next
        """
        nav_frames = self._get_navigation_frames()
        if not nav_frames:
            self.statusBar().showMessage("No navigation frames found", 3000)
            return

        current_frame = get_application_state().current_frame

        # Find adjacent frame in specified direction
        if direction < 0:
            # Previous: find largest frame < current
            candidates = [f for f in nav_frames if f < current_frame]
            target = max(candidates) if candidates else None
            direction_name = "previous"
            boundary_msg = "first"
        else:
            # Next: find smallest frame > current
            candidates = [f for f in nav_frames if f > current_frame]
            target = min(candidates) if candidates else None
            direction_name = "next"
            boundary_msg = "last"

        if target is not None:
            self.timeline_controller.set_frame(target)
            self.statusBar().showMessage(f"Navigated to {direction_name} frame: {target}", 2000)
        else:
            self.statusBar().showMessage(f"Already at {boundary_msg} navigation frame", 2000)

    def navigate_to_prev_keyframe(self) -> None:
        """Navigate to the previous keyframe, endframe, or startframe relative to current frame."""
        self._navigate_to_adjacent_frame(-1)

    def navigate_to_next_keyframe(self) -> None:
        """Navigate to the next keyframe, endframe, or startframe relative to current frame."""
        self._navigate_to_adjacent_frame(1)

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events for custom shortcuts.

        Keyboard shortcuts:
            Tab: Toggle tracking panel dock visibility
            PageUp: Navigate to previous navigation frame (keyframes, endframes, startframes)
            PageDown: Navigate to next navigation frame (keyframes, endframes, startframes)
        """
        # Tab key toggles tracking panel dock visibility
        if event.key() == Qt.Key.Key_Tab:
            if self.tracking_panel_dock:
                self.tracking_panel_dock.setVisible(not self.tracking_panel_dock.isVisible())
            event.accept()
            return

        # PageUp: Navigate to previous keyframe
        elif event.key() == Qt.Key.Key_PageUp:
            self.navigate_to_prev_keyframe()
            event.accept()
            return

        # PageDown: Navigate to next keyframe
        elif event.key() == Qt.Key.Key_PageDown:
            self.navigate_to_next_keyframe()
            event.accept()
            return

        # Pass to parent for default handling
        super().keyPressEvent(event)

    def __del__(self) -> None:
        """Destructor to ensure event filter cleanup even if closeEvent isn't called.

        CRITICAL: Removes global event filter to prevent accumulation across tests.
        After 1580+ tests, accumulated event filters cause timeouts when
        setStyleSheet() triggers events through all filters (see UNIFIED_TESTING_GUIDE).
        """
        from contextlib import suppress

        try:
            app = QApplication.instance()
            if app and getattr(self, "global_event_filter", None) is not None:
                with suppress(RuntimeError):
                    app.removeEventFilter(self.global_event_filter)
        except Exception:
            pass  # Suppress all exceptions in destructor

    def _save_current_session(self) -> None:
        """Save current application state to session file."""
        try:
            from stores.application_state import get_application_state

            app_state = get_application_state()

            # Gather current session data
            from typing import cast

            # Get image data from ApplicationState (single source of truth)
            image_directory = app_state.get_image_directory()
            image_files = app_state.get_image_files()

            # Debug logging to see what values we're saving
            logger.debug(
                f"[SESSION-SAVE] tracking_file={self.state_manager.current_file}, " +
                f"image_directory={image_directory}, image_files={len(image_files) if image_files else 0}"
            )

            session_data = self._session_manager.create_session_data(
                tracking_file=self.state_manager.current_file,
                image_directory=image_directory,
                current_frame=self.timeline_controller.get_current_frame(),
                zoom_level=self.state_manager.zoom_level,
                pan_offset=self.state_manager.pan_offset,
                window_geometry=cast(tuple[int, int, int, int], self.geometry().getRect()),
                selected_curves=list(app_state.get_selected_curves()),
                show_all_curves=app_state.get_show_all_curves(),
            )

            # Add image files to session data (not part of create_session_data signature)
            session_data["image_files"] = image_files

            # Save session to file
            if self._session_manager.save_session(session_data):
                logger.info("Session saved successfully")
            else:
                logger.warning("Failed to save session")

        except Exception as e:
            logger.error(f"Error saving session: {e}")

    @override
    def closeEvent(self, event: QEvent) -> None:
        """Handle window close event with proper thread cleanup."""
        logger.info("[PYTHON-THREAD] Application closing, stopping Python thread if running")

        # Disconnect frame change coordinator to prevent signal warnings
        if getattr(self, "frame_change_coordinator", None) is not None:
            self.frame_change_coordinator.disconnect()
            logger.info("Disconnected frame change coordinator")

        # Remove global event filter to prevent accumulation
        app = QApplication.instance()
        if app and getattr(self, "global_event_filter", None) is not None:
            app.removeEventFilter(self.global_event_filter)
            logger.info("Removed global event filter")

        # Stop playback timer if running
        if getattr(self, "timeline_controller", None) is not None:
            self.timeline_controller.stop_playback()
            # Note: playback_timer access handled by stop_playback() method

        # Stop any file operation threads
        # file_operations is always initialized in __init__
        self.file_operations.cleanup_threads()

        logger.info("[KEEP-ALIVE] Worker and thread cleaned up")

        # Save current session before closing
        self._save_current_session()

        # Accept the close event
        event.accept()
        logger.info("MainWindow closed with proper cleanup")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
