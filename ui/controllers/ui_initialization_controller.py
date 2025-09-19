#!/usr/bin/env python
"""
UI Initialization Controller for CurveEditor.

This controller handles all UI component initialization that was previously
handled directly in MainWindow, reducing MainWindow complexity.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QDoubleSpinBox,
    QFrame,
    QLabel,
    QSlider,
    QStatusBar,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.logger_utils import get_logger

logger = get_logger("ui_initialization_controller")


class UIInitializationController:
    """
    Controller for handling all UI initialization.

    Extracted from MainWindow to reduce complexity while maintaining exact
    compatibility with existing component structure.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the UI initialization controller.

        Args:
            main_window: Reference to the main window for UI component setup
        """
        self.main_window = main_window
        logger.info("UIInitializationController initialized")

    def initialize_ui(self) -> None:
        """Initialize all UI components in the correct order."""
        self._init_actions()
        self._init_menus()
        self._init_toolbar()
        self._init_central_widget()
        self._init_dock_widgets()
        self._init_status_bar()
        logger.info("UI initialization complete")

    def _init_actions(self) -> None:
        """Get all QActions from ShortcutManager and set up icons."""
        # Get actions from ShortcutManager
        self.main_window.action_new = self.main_window.shortcut_manager.action_new
        self.main_window.action_open = self.main_window.shortcut_manager.action_open
        self.main_window.action_save = self.main_window.shortcut_manager.action_save
        self.main_window.action_save_as = self.main_window.shortcut_manager.action_save_as
        self.main_window.action_load_images = self.main_window.shortcut_manager.action_load_images
        self.main_window.action_export_data = self.main_window.shortcut_manager.action_export_data
        self.main_window.action_quit = self.main_window.shortcut_manager.action_quit

        self.main_window.action_undo = self.main_window.shortcut_manager.action_undo
        self.main_window.action_redo = self.main_window.shortcut_manager.action_redo
        self.main_window.action_select_all = self.main_window.shortcut_manager.action_select_all
        self.main_window.action_add_point = self.main_window.shortcut_manager.action_add_point

        self.main_window.action_zoom_in = self.main_window.shortcut_manager.action_zoom_in
        self.main_window.action_zoom_out = self.main_window.shortcut_manager.action_zoom_out
        self.main_window.action_zoom_fit = self.main_window.shortcut_manager.action_zoom_fit
        self.main_window.action_reset_view = self.main_window.shortcut_manager.action_reset_view

        self.main_window.action_smooth_curve = self.main_window.shortcut_manager.action_smooth_curve
        self.main_window.action_filter_curve = self.main_window.shortcut_manager.action_filter_curve
        self.main_window.action_analyze_curve = self.main_window.shortcut_manager.action_analyze_curve

        self.main_window.action_next_frame = self.main_window.shortcut_manager.action_next_frame
        self.main_window.action_prev_frame = self.main_window.shortcut_manager.action_prev_frame
        self.main_window.action_first_frame = self.main_window.shortcut_manager.action_first_frame
        self.main_window.action_last_frame = self.main_window.shortcut_manager.action_last_frame

        self.main_window.action_oscillate_playback = self.main_window.shortcut_manager.action_oscillate_playback
        # Add action to window so shortcut works globally
        self.main_window.addAction(self.main_window.action_oscillate_playback)

        # Set icons for toolbar
        style = self.main_window.style()
        if style:
            self.main_window.action_new.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
            self.main_window.action_open.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
            self.main_window.action_save.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DriveFDIcon))
            self.main_window.action_undo.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
            self.main_window.action_redo.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
            self.main_window.action_zoom_in.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
            self.main_window.action_zoom_out.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
            self.main_window.action_reset_view.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))

        # Set initial enabled states
        self.main_window.action_undo.setEnabled(False)
        self.main_window.action_redo.setEnabled(False)

        # Connect actions to handlers
        self.main_window.shortcut_manager.connect_to_main_window(self.main_window)

    def _init_menus(self) -> None:
        """Create menu bar with all actions."""
        menubar = self.main_window.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        for action in self.main_window.shortcut_manager.get_file_actions():
            if action is None:
                file_menu.addSeparator()
            else:
                file_menu.addAction(action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        for action in self.main_window.shortcut_manager.get_edit_actions():
            if action is None:
                edit_menu.addSeparator()
            else:
                edit_menu.addAction(action)

        # View menu
        view_menu = menubar.addMenu("&View")
        for action in self.main_window.shortcut_manager.get_view_actions():
            if action is None:
                view_menu.addSeparator()
            else:
                view_menu.addAction(action)

        # Curve menu
        curve_menu = menubar.addMenu("&Curve")
        for action in self.main_window.shortcut_manager.get_curve_actions():
            if action is None:
                curve_menu.addSeparator()
            else:
                curve_menu.addAction(action)

        # Navigation menu
        nav_menu = menubar.addMenu("&Navigation")
        for action in self.main_window.shortcut_manager.get_navigation_actions():
            if action is None:
                nav_menu.addSeparator()
            else:
                nav_menu.addAction(action)

    def _init_toolbar(self) -> None:
        """Initialize the main toolbar."""
        toolbar = QToolBar("Main Toolbar", self.main_window)
        toolbar.setObjectName("mainToolBar")
        toolbar.setMovable(False)
        self.main_window.addToolBar(toolbar)

        # File operations
        _ = toolbar.addAction(self.main_window.action_new)
        _ = toolbar.addAction(self.main_window.action_open)
        _ = toolbar.addAction(self.main_window.action_save)
        _ = toolbar.addSeparator()

        # Edit operations
        _ = toolbar.addAction(self.main_window.action_undo)
        _ = toolbar.addAction(self.main_window.action_redo)
        _ = toolbar.addSeparator()

        # View operations
        _ = toolbar.addAction(self.main_window.action_zoom_in)
        _ = toolbar.addAction(self.main_window.action_zoom_out)
        _ = toolbar.addAction(self.main_window.action_reset_view)
        _ = toolbar.addSeparator()

        # Add frame control to toolbar (from FrameNavigationController)
        _ = toolbar.addWidget(QLabel("Frame:"))
        self.main_window.frame_spinbox = self.main_window.frame_nav_controller.frame_spinbox
        _ = toolbar.addWidget(self.main_window.frame_spinbox)
        self.main_window.ui.timeline.frame_spinbox = self.main_window.frame_spinbox  # Map to timeline group
        _ = toolbar.addSeparator()

        # Add view option checkboxes to toolbar
        self.main_window.show_background_cb = QCheckBox("Background")
        self.main_window.show_background_cb.setChecked(True)
        _ = toolbar.addWidget(self.main_window.show_background_cb)

        self.main_window.show_grid_cb = QCheckBox("Grid")
        self.main_window.show_grid_cb.setChecked(False)
        _ = toolbar.addWidget(self.main_window.show_grid_cb)

        self.main_window.show_info_cb = QCheckBox("Info")
        self.main_window.show_info_cb.setChecked(True)
        _ = toolbar.addWidget(self.main_window.show_info_cb)

        # Add tooltip toggle checkbox
        self.main_window.show_tooltips_cb = QCheckBox("Tooltips")
        self.main_window.show_tooltips_cb.setChecked(False)  # Off by default
        _ = toolbar.addWidget(self.main_window.show_tooltips_cb)

        # Create widgets needed for UIComponents compatibility
        self._create_ui_component_widgets()

        # Add stretch to push remaining items to the right
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
        _ = toolbar.addWidget(spacer)

    def _create_ui_component_widgets(self) -> None:
        """Create widgets needed for UIComponents compatibility."""
        # Point editing widgets (used in properties panel if it exists)
        self.main_window.point_x_spinbox = QDoubleSpinBox()
        self.main_window.point_x_spinbox.setRange(-10000, 10000)
        self.main_window.point_x_spinbox.setDecimals(3)
        self.main_window.point_x_spinbox.setEnabled(False)
        self.main_window.ui.point_edit.x_edit = self.main_window.point_x_spinbox

        self.main_window.point_y_spinbox = QDoubleSpinBox()
        self.main_window.point_y_spinbox.setRange(-10000, 10000)
        self.main_window.point_y_spinbox.setDecimals(3)
        self.main_window.point_y_spinbox.setEnabled(False)
        self.main_window.ui.point_edit.y_edit = self.main_window.point_y_spinbox

        # Visualization sliders (used in properties panel if it exists)
        self.main_window.point_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.main_window.point_size_slider.setMinimum(2)
        self.main_window.point_size_slider.setMaximum(20)
        self.main_window.point_size_slider.setValue(6)
        self.main_window.ui.visualization.point_size_slider = self.main_window.point_size_slider

        self.main_window.line_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.main_window.line_width_slider.setMinimum(1)
        self.main_window.line_width_slider.setMaximum(10)
        self.main_window.line_width_slider.setValue(2)
        self.main_window.ui.visualization.line_width_slider = self.main_window.line_width_slider

        # Playback controls from PlaybackController
        self.main_window.btn_play_pause = self.main_window.playback_controller.btn_play_pause
        self.main_window.ui.timeline.play_button = self.main_window.btn_play_pause

        # FPS control from PlaybackController
        self.main_window.fps_spinbox = self.main_window.playback_controller.fps_spinbox
        self.main_window.ui.timeline.fps_spinbox = self.main_window.fps_spinbox

        # Frame slider from FrameNavigationController
        self.main_window.frame_slider = self.main_window.frame_nav_controller.frame_slider
        self.main_window.ui.timeline.timeline_slider = self.main_window.frame_slider

        # Labels
        self.main_window.total_frames_label = QLabel("1")
        self.main_window.ui.status.info_label = self.main_window.total_frames_label
        self.main_window.point_count_label = QLabel("Points: 0")
        self.main_window.ui.status.quality_score_label = self.main_window.point_count_label
        self.main_window.selected_count_label = QLabel("Selected: 0")
        self.main_window.ui.status.quality_coverage_label = self.main_window.selected_count_label
        self.main_window.bounds_label = QLabel("Bounds: N/A")
        self.main_window.ui.status.quality_consistency_label = self.main_window.bounds_label

    def _init_central_widget(self) -> None:
        """Initialize the central widget with full-width curve view and bottom timeline."""
        # Create main central widget with vertical layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create the main curve view area
        self.main_window.curve_container = self._create_curve_view_container()

        # Add curve container with stretch factor so it expands
        main_layout.addWidget(self.main_window.curve_container, stretch=1)

        # Create timeline tabs widget
        self.main_window.timeline_tabs = None  # Initialize to None first
        try:
            from ui.timeline_tabs import TimelineTabWidget

            self.main_window.timeline_tabs = TimelineTabWidget()
            logger.info("Timeline tabs widget created successfully")
        except Exception as e:
            logger.warning(f"Could not create timeline tabs widget: {e}")
            self.main_window.timeline_tabs = None

        # Add timeline tabs widget if available
        if self.main_window.timeline_tabs:
            self.main_window.timeline_tabs.setMinimumHeight(60)
            self.main_window.timeline_tabs.setFixedHeight(60)
            main_layout.addWidget(self.main_window.timeline_tabs, stretch=0)
            logger.info("Timeline tabs added to main layout")

        # Set the central widget
        self.main_window.setCentralWidget(central_widget)

    def _create_curve_view_container(self) -> QWidget:
        """Create the container for the curve view."""
        from PySide6.QtCore import QTimer

        from ui.curve_view_widget import CurveViewWidget

        container = QFrame()
        container.setFrameStyle(QFrame.Shape.Box)
        container.setLineWidth(1)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create the actual CurveViewWidget
        self.main_window.curve_widget = CurveViewWidget(container)
        self.main_window.curve_widget.set_main_window(self.main_window)  # pyright: ignore[reportArgumentType]

        # Ensure the curve widget can receive keyboard focus
        self.main_window.curve_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout.addWidget(self.main_window.curve_widget)

        # Set focus to curve widget after creation
        def set_focus_safe():
            try:
                if self.main_window.curve_widget is not None:
                    self.main_window.curve_widget.setFocus()
            except (RuntimeError, AttributeError):
                # Widget was deleted or not yet initialized
                pass

        QTimer.singleShot(100, set_focus_safe)

        logger.info("CurveViewWidget created and integrated")

        return container

    def _init_dock_widgets(self) -> None:
        """Initialize dock widgets (tracking points panel)."""
        from ui.tracking_points_panel import TrackingPointsPanel

        # Create tracking points panel dock widget
        self.main_window.tracking_panel_dock = QDockWidget("Tracking Points", self.main_window)
        self.main_window.tracking_panel = TrackingPointsPanel()
        self.main_window.tracking_panel_dock.setWidget(self.main_window.tracking_panel)

        # Set dock widget properties
        self.main_window.tracking_panel_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.main_window.tracking_panel_dock)
        self.main_window.tracking_panel_dock.setVisible(True)

        # Connect signals for tracking point management
        self.main_window.tracking_panel.points_selected.connect(self.main_window._on_tracking_points_selected)
        self.main_window.tracking_panel.point_visibility_changed.connect(self.main_window._on_point_visibility_changed)
        self.main_window.tracking_panel.point_color_changed.connect(self.main_window._on_point_color_changed)
        self.main_window.tracking_panel.point_deleted.connect(self.main_window._on_point_deleted)
        self.main_window.tracking_panel.point_renamed.connect(self.main_window._on_point_renamed)

        logger.info("Tracking points panel dock widget initialized")

    def _init_status_bar(self) -> None:
        """Initialize the status bar with additional widgets."""
        self.main_window.status_bar = QStatusBar(self.main_window)
        self.main_window.setStatusBar(self.main_window.status_bar)

        # Add primary status label (left side)
        self.main_window.status_label = QLabel("Ready")
        self.main_window.status_bar.addWidget(self.main_window.status_label)

        # Add permanent widgets to status bar (right side)
        self.main_window.zoom_label = QLabel("Zoom: 100%")
        self.main_window.status_bar.addPermanentWidget(self.main_window.zoom_label)

        self.main_window.position_label = QLabel("X: 0.000, Y: 0.000")
        self.main_window.status_bar.addPermanentWidget(self.main_window.position_label)
