"""MainWindow initialization handler.

This module extracts the initialization logic from MainWindow to reduce its size
and improve maintainability. All initialization happens in the same order as before,
just organized into logical methods.
"""

import logging
import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer

from .ui_components import UIComponents
from .ui_constants import MAX_HISTORY_SIZE
from .ui_scaling import UIScaling

if TYPE_CHECKING:
    from .main_window import MainWindow

logger = logging.getLogger(__name__)


class MainWindowInitializer:
    """Handles all MainWindow initialization logic."""

    def __init__(self, main_window: "MainWindow"):
        """Initialize the initializer with a reference to MainWindow.

        Args:
            main_window: The MainWindow instance to initialize
        """
        self.main_window = main_window

    def setup_window_properties(self) -> None:
        """Set basic window properties."""
        self.main_window.setWindowTitle("CurveEditor")
        self.main_window.setMinimumSize(1024, 768)
        self.main_window.resize(1400, 900)
        logger.debug("Window properties configured")

    def setup_managers(self) -> None:
        """Initialize core managers."""
        from .keyboard_shortcuts import ShortcutManager
        from .service_facade import get_service_facade
        from .session_manager import SessionManager
        from .state_manager import StateManager

        # Initialize managers
        self.main_window.state_manager = StateManager(self.main_window)
        self.main_window.shortcut_manager = ShortcutManager(self.main_window)
        self.main_window.session_manager = SessionManager()

        # Initialize service facade
        self.main_window.services = get_service_facade(self.main_window)

        # Initialize UI scaling
        self.main_window.ui_scaling = UIScaling()

        logger.debug("Managers initialized")

    def setup_ui_components(self) -> None:
        """Initialize UI components and build the interface."""
        # Initialize UI components container
        self.main_window.ui = UIComponents(self.main_window)
        self.main_window.ui_components = self.main_window.ui  # Protocol compatibility alias

        # Build UI components using builder pattern
        from .main_window_builder import MainWindowBuilder

        builder = MainWindowBuilder()
        builder.build(self.main_window)

        logger.debug("UI components built")

    def setup_state_variables(self) -> None:
        """Initialize all state tracking variables."""
        # Multi-point tracking data
        self.main_window.tracked_data = {}  # All tracking points
        self.main_window.active_points = []  # Currently selected points

        # Thread synchronization for shared state
        self.main_window._state_lock = threading.RLock()

        # Protocol-required attributes
        self.main_window.selected_indices = []  # Currently selected point indices
        self.main_window.curve_data = []  # Current curve data
        self.main_window.point_name = "Point"  # Default point name
        self.main_window.point_color = "#FF6464"  # Default point color (red)

        # UI button references for protocol compatibility
        self.main_window.undo_button = None
        self.main_window.redo_button = None
        self.main_window.save_button = None
        self.main_window.ui_components = None  # Will be set to UIComponents instance

        # Initialize legacy curve view and track quality UI
        self.main_window.curve_view = None  # Legacy curve view - no longer used
        self.main_window.track_quality_ui = None  # Legacy track quality UI

        # Initialize history tracking
        self.main_window.history = []  # Each history entry is a dict with curve data
        self.main_window.history_index = -1
        self.main_window.max_history_size = MAX_HISTORY_SIZE

        # Initialize centering state
        self.main_window.auto_center_enabled = False

        # Initialize image sequence state
        self.main_window.image_filenames = []
        self.main_window.current_image_idx = 0

        # Initialize playback timer
        self.main_window.playback_timer = QTimer(self.main_window)

        # Initialize dynamic instance variables
        self.main_window._point_spinbox_connected = False
        self.main_window._stored_tooltips = {}
        self.main_window._pending_session_data = None  # Session data to restore after files load
        self.main_window._file_loading = False  # Track file loading state

        logger.debug("State variables initialized")

    def setup_controllers(self) -> None:
        """Initialize all controllers."""
        # Import controllers locally to avoid circular imports
        from commands.base import CommandManager
        from controllers import (
            EventCoordinator,
            EventFilterController,
            FileOperationsManager,
            FrameNavigationController,
            PlaybackController,
            PointEditController,
            SmoothingController,
            StateChangeController,
            TimelineController,
            TrackingPanelController,
            ViewUpdateManager,
            ZoomController,
        )

        # Initialize original controllers (reverted from Phase 4 consolidation)
        self.main_window.event_coordinator = EventCoordinator(self.main_window, parent=self.main_window)
        self.main_window.event_filter_controller = EventFilterController(self.main_window)
        self.main_window.file_operations_manager = FileOperationsManager(self.main_window, parent=self.main_window)
        self.main_window.frame_navigation_controller = FrameNavigationController(
            self.main_window, parent=self.main_window
        )
        self.main_window.playback_controller = PlaybackController(self.main_window, parent=self.main_window)
        self.main_window.point_edit_controller = PointEditController(self.main_window)
        self.main_window.smoothing_controller = SmoothingController(self.main_window)
        self.main_window.state_change_controller = StateChangeController(self.main_window)
        self.main_window.timeline_controller = TimelineController(self.main_window)
        self.main_window.tracking_panel_controller = TrackingPanelController(self.main_window)
        self.main_window.view_update_manager = ViewUpdateManager(self.main_window)
        self.main_window.zoom_controller = ZoomController(self.main_window)

        # Initialize command manager
        self.main_window.command_manager = CommandManager(max_history=100)

        # Link command manager to point edit controller (handles editing operations)
        if hasattr(self.main_window.point_edit_controller, "set_command_manager"):
            self.main_window.point_edit_controller.set_command_manager(self.main_window.command_manager)

        logger.debug("Controllers initialized")

    def connect_signals(self) -> None:
        """Connect all signals and slots."""
        # Connect signals directly to controllers
        self._connect_signals_direct()

        # Connect curve widget signals (after all UI components are created)
        if self.main_window.curve_widget:
            self._connect_curve_widget_signals_direct()

        logger.debug("Signals connected directly to controllers")

    def _connect_signals_direct(self) -> None:
        """Connect signals directly to controller methods, bypassing wrappers."""
        mw = self.main_window

        # Connect action signals to appropriate controllers
        if mw.file_operations_manager:
            # File actions
            if hasattr(mw, "action_new"):
                mw.action_new.triggered.connect(mw.file_operations_manager.new_file)
            if hasattr(mw, "action_open"):
                mw.action_open.triggered.connect(mw.file_operations_manager.open_file)
            if hasattr(mw, "action_save"):
                mw.action_save.triggered.connect(mw.file_operations_manager.save_file)
            if hasattr(mw, "action_save_as"):
                mw.action_save_as.triggered.connect(mw.file_operations_manager.save_file_as)
            if hasattr(mw, "action_load_images"):
                mw.action_load_images.triggered.connect(mw.file_operations_manager.load_image_sequence)

        # Edit actions - still use wrappers for command manager integration
        if hasattr(mw, "action_undo") and hasattr(mw, "_on_action_undo"):
            mw.action_undo.triggered.connect(mw._on_action_undo)
        if hasattr(mw, "action_redo") and hasattr(mw, "_on_action_redo"):
            mw.action_redo.triggered.connect(mw._on_action_redo)

        # View actions - connect to zoom_controller
        if mw.zoom_controller:
            if hasattr(mw, "action_zoom_in"):
                mw.action_zoom_in.triggered.connect(mw.zoom_controller.zoom_in)
            if hasattr(mw, "action_zoom_out"):
                mw.action_zoom_out.triggered.connect(mw.zoom_controller.zoom_out)
            if hasattr(mw, "action_reset_view"):
                mw.action_reset_view.triggered.connect(mw.zoom_controller.reset_view)

        # Frame navigation actions
        if mw.frame_navigation_controller:
            if hasattr(mw, "action_first_frame"):
                mw.action_first_frame.triggered.connect(mw.frame_navigation_controller.go_to_first_frame)
            if hasattr(mw, "action_prev_frame"):
                mw.action_prev_frame.triggered.connect(mw.frame_navigation_controller.go_to_previous_frame)
            if hasattr(mw, "action_next_frame"):
                mw.action_next_frame.triggered.connect(mw.frame_navigation_controller.go_to_next_frame)
            if hasattr(mw, "action_last_frame"):
                mw.action_last_frame.triggered.connect(mw.frame_navigation_controller.go_to_last_frame)

        # Connect state manager signals (some still need wrappers for complex logic)
        if mw.state_manager:
            mw.state_manager.file_changed.connect(mw._on_file_changed)
            mw.state_manager.modified_changed.connect(mw._on_modified_changed)
            mw.state_manager.frame_changed.connect(mw._on_state_frame_changed)
            mw.state_manager.selection_changed.connect(mw._on_selection_changed)
            mw.state_manager.view_state_changed.connect(mw._on_view_state_changed)

        # Connect shortcut signals
        if mw.shortcut_manager:
            mw.shortcut_manager.shortcut_activated.connect(mw._on_shortcut_activated)

        # Connect frame controls directly to frame_navigation_controller
        if mw.frame_spinbox and mw.frame_navigation_controller:
            mw.frame_spinbox.valueChanged.connect(mw.frame_navigation_controller.on_frame_spinbox_changed)
        if mw.frame_slider and mw.frame_navigation_controller:
            mw.frame_slider.valueChanged.connect(mw.frame_navigation_controller.on_frame_slider_changed)

        # Connect view option checkboxes
        if mw.show_background_cb:
            mw.show_background_cb.stateChanged.connect(mw.update_curve_view_options)
        if mw.show_grid_cb:
            mw.show_grid_cb.stateChanged.connect(mw.update_curve_view_options)
        if mw.show_info_cb:
            mw.show_info_cb.stateChanged.connect(mw.update_curve_view_options)

        # Connect timeline tabs
        if mw.timeline_tabs:
            mw.timeline_tabs.frame_changed.connect(mw._on_timeline_tab_clicked)
            mw.timeline_tabs.frame_hovered.connect(mw._on_timeline_tab_hovered)

        logger.debug("Direct signal connections established")

    def _connect_curve_widget_signals_direct(self) -> None:
        """Connect curve widget signals directly to controllers."""
        mw = self.main_window
        if not mw.curve_widget:
            return

        # Connect curve widget signals (some still need wrappers for complex logic)
        mw.curve_widget.point_selected.connect(mw._on_point_selected)
        mw.curve_widget.point_moved.connect(mw._on_point_moved)
        mw.curve_widget.selection_changed.connect(mw._on_curve_selection_changed)
        mw.curve_widget.view_changed.connect(mw._on_curve_view_changed)
        mw.curve_widget.zoom_changed.connect(mw._on_curve_zoom_changed)

        logger.debug("Direct curve widget signal connections established")

    def setup_tab_order(self) -> None:
        """Set up proper tab order for keyboard navigation."""
        mw = self.main_window
        # Only set tab order for widgets that are actually in the UI
        # Toolbar controls - check for None values
        if mw.frame_spinbox and mw.show_background_cb:
            mw.setTabOrder(mw.frame_spinbox, mw.show_background_cb)
        if mw.show_background_cb and mw.show_grid_cb:
            mw.setTabOrder(mw.show_background_cb, mw.show_grid_cb)
        # show_info_cb is Optional[QCheckBox]
        if mw.show_grid_cb and mw.show_info_cb is not None:
            mw.setTabOrder(mw.show_grid_cb, mw.show_info_cb)

        # Curve view widget (main area)
        # show_info_cb is Optional[QCheckBox]
        if mw.curve_widget and mw.show_info_cb is not None:
            mw.setTabOrder(mw.show_info_cb, mw.curve_widget)

        logger.debug("Tab order configured for keyboard navigation")

    def finalize_setup(self) -> None:
        """Perform final setup steps."""
        # Setup initial state
        self.main_window.update_ui_state()

        # Setup tab order for keyboard navigation
        self.setup_tab_order()

        # Auto-load from session or fallback to burger footage and tracking data
        self.main_window._load_session_or_fallback()

        # Initialize tooltips as disabled by default
        self.main_window.toggle_tooltips()

        # Load initial data file if provided via command line
        if hasattr(self.main_window, "_initial_data_file") and self.main_window._initial_data_file:
            self.main_window._load_initial_data_file()

        logger.debug("Setup finalized")

    def perform_full_initialization(self, initial_data_file: str | None = None) -> None:
        """Perform complete initialization in the correct order.

        Args:
            initial_data_file: Optional initial data file to load
        """
        # Store initial data file for later loading
        self.main_window._initial_data_file = initial_data_file

        # Execute initialization in proper order
        self.setup_window_properties()
        self.setup_managers()
        self.setup_state_variables()
        self.setup_ui_components()
        self.setup_controllers()

        # NOTE: QAction attributes are created by MainWindowBuilder.build() above
        # They are properly initialized in _build_actions() method
        # DO NOT reset them to None here as that would overwrite the created actions!

        self.connect_signals()
        self.finalize_setup()

        logger.info("MainWindow initialized successfully via MainWindowInitializer")
