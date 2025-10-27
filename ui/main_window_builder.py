"""MainWindow builder for initialization and widget creation.

Extracts initialization logic from MainWindow using the Builder pattern.
Part of Phase 2 refactoring to reduce MainWindow complexity.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from .main_window import MainWindow

from ui.curve_view_widget import CurveViewWidget
from ui.tracking_points_panel import TrackingPointsPanel

logger = logging.getLogger(__name__)


class MainWindowBuilder:
    """Builds and initializes MainWindow components.

    This builder extracts ~400 lines of initialization code from MainWindow,
    creating all widgets, actions, toolbars, and UI components while maintaining
    the exact initialization order and references.
    """

    def build(self, window: MainWindow) -> None:
        """Build all MainWindow components in the correct order.

        Args:
            window: The MainWindow instance to build components for
        """
        # Initialize in exact order as original
        self._build_actions(window)
        self._build_toolbar(window)
        self._build_central_widget(window)
        self._build_dock_widgets(window)
        self._build_status_bar(window)
        self._build_persistent_worker(window)

        logger.info("MainWindow components built successfully")

    def _build_persistent_worker(self, window: MainWindow) -> None:
        """Initialize worker with Python threading (no QThread).

        Args:
            window: The MainWindow instance
        """
        logger.info("[PYTHON-THREAD] Initializing file loader with Python threading")

        # Import here to avoid circular dependency
        from io_utils.file_load_worker import FileLoadWorker

        # Create FileLoadWorker (QThread with signals as class attributes)
        # No longer needs separate FileLoadSignals - signals are part of the worker
        window.file_load_worker = FileLoadWorker()  # pyright: ignore[reportAttributeAccessIssue]

        # Connect signals (Qt automatically handles cross-thread signal emission)
        # Note: Handler names match the public API in MainWindow (without underscore prefix)
        # Type warnings about Unknown in list types are from PySide6 Signal stubs - handlers have proper types
        _ = window.file_load_worker.tracking_data_loaded.connect(window.on_tracking_data_loaded)
        _ = window.file_load_worker.image_sequence_loaded.connect(window.on_image_sequence_loaded)
        _ = window.file_load_worker.progress_updated.connect(window.on_file_load_progress)
        _ = window.file_load_worker.error_occurred.connect(window.on_file_load_error)
        _ = window.file_load_worker.finished.connect(window.on_file_load_finished)

        logger.info("[QTHREAD] File loader initialized with Qt threading (QThread)")

    def _build_actions(self, window: MainWindow) -> None:
        """Initialize all QActions for menus and toolbars.

        Args:
            window: The MainWindow instance
        """
        # File actions
        window.action_new = QAction("New", window)
        window.action_new.setShortcut(QKeySequence.StandardKey.New)
        window.action_new.setStatusTip("Create a new curve")
        window.action_new.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        window.action_new.setToolTip("New Curve (Ctrl+N)")

        window.action_open = QAction("Open", window)
        window.action_open.setShortcut(QKeySequence.StandardKey.Open)
        window.action_open.setStatusTip("Open an existing curve file")
        window.action_open.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        window.action_open.setToolTip("Open Curve File (Ctrl+O)")

        window.action_save = QAction("Save", window)
        window.action_save.setShortcut(QKeySequence.StandardKey.Save)
        window.action_save.setStatusTip("Save the current curve")
        window.action_save.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        window.action_save.setToolTip("Save Curve (Ctrl+S)")

        window.action_save_as = QAction("Save As...", window)
        window.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        window.action_save_as.setStatusTip("Save the curve with a new name")
        window.action_save_as.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        window.action_save_as.setToolTip("Save As... (Ctrl+Shift+S)")

        window.action_load_images = QAction("Load Images", window)
        window.action_load_images.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        window.action_load_images.setShortcut("Ctrl+I")
        window.action_load_images.setToolTip("Load Background Image Sequence (Ctrl+I)")
        window.action_load_images.setStatusTip("Load an image sequence from a directory")

        # Edit actions
        window.action_undo = QAction("Undo", window)
        window.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        window.action_undo.setStatusTip("Undo the last action")
        window.action_undo.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        window.action_undo.setToolTip("Undo Last Action (Ctrl+Z)")
        window.action_undo.setEnabled(False)

        window.action_redo = QAction("Redo", window)
        window.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        window.action_redo.setStatusTip("Redo the previously undone action")
        window.action_redo.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        window.action_redo.setToolTip("Redo Action (Ctrl+Y)")
        window.action_redo.setEnabled(False)

        # View actions - Use custom text icons since Qt doesn't have good zoom icons
        window.action_zoom_in = QAction("Zoom In", window)
        window.action_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        window.action_zoom_in.setStatusTip("Zoom in the view")
        # Create a text-based icon for zoom in
        window.action_zoom_in.setText("🔍+")
        window.action_zoom_in.setToolTip("Zoom In (Ctrl++)")

        window.action_zoom_out = QAction("Zoom Out", window)
        window.action_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        window.action_zoom_out.setStatusTip("Zoom out the view")
        # Create a text-based icon for zoom out
        window.action_zoom_out.setText("🔍-")
        window.action_zoom_out.setToolTip("Zoom Out (Ctrl+-)")

        window.action_reset_view = QAction("Reset View", window)
        window.action_reset_view.setShortcut("Ctrl+0")
        window.action_reset_view.setStatusTip("Reset the view to default")
        window.action_reset_view.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        window.action_reset_view.setToolTip("Reset View to Default (Ctrl+0)")

        # Connect actions after creating them
        self._connect_actions(window)

    def _build_toolbar(self, window: MainWindow) -> None:
        """Initialize the main toolbar with all controls.

        Args:
            window: The MainWindow instance
        """
        toolbar = QToolBar("Main Toolbar", window)
        toolbar.setObjectName("mainToolBar")
        toolbar.setMovable(False)
        # Set toolbar to show both icons and text
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        window.addToolBar(toolbar)

        # File operations group
        file_label = QLabel(" File ")
        file_label.setStyleSheet("font-weight: bold; color: #666;")
        _ = toolbar.addWidget(file_label)

        # Assert actions are not None after creation (type narrowing)
        assert window.action_new is not None
        assert window.action_open is not None
        assert window.action_save is not None
        assert window.action_load_images is not None
        assert window.action_undo is not None
        assert window.action_redo is not None
        assert window.action_zoom_in is not None
        assert window.action_zoom_out is not None
        assert window.action_reset_view is not None

        _ = toolbar.addAction(window.action_new)
        _ = toolbar.addAction(window.action_open)
        _ = toolbar.addAction(window.action_save)
        _ = toolbar.addSeparator()

        # Images group
        _ = toolbar.addAction(window.action_load_images)
        _ = toolbar.addSeparator()

        # Edit operations group
        edit_label = QLabel(" Edit ")
        edit_label.setStyleSheet("font-weight: bold; color: #666;")
        _ = toolbar.addWidget(edit_label)
        _ = toolbar.addAction(window.action_undo)
        _ = toolbar.addAction(window.action_redo)
        _ = toolbar.addSeparator()

        # View operations group
        view_label = QLabel(" View ")
        view_label.setStyleSheet("font-weight: bold; color: #666;")
        _ = toolbar.addWidget(view_label)
        _ = toolbar.addAction(window.action_zoom_in)
        _ = toolbar.addAction(window.action_zoom_out)
        _ = toolbar.addAction(window.action_reset_view)
        _ = toolbar.addSeparator()

        # Add frame control to toolbar
        _ = toolbar.addWidget(QLabel("Frame:"))
        window.frame_spinbox = QSpinBox()
        window.frame_spinbox.setMinimum(1)
        window.frame_spinbox.setMaximum(1000)
        window.frame_spinbox.setValue(1)
        _ = toolbar.addWidget(window.frame_spinbox)
        window.ui.timeline.frame_spinbox = window.frame_spinbox  # Map to timeline group
        _ = toolbar.addSeparator()

        # Add view option checkboxes to toolbar
        window.show_background_cb = QCheckBox("Background")
        window.show_background_cb.setChecked(True)
        _ = toolbar.addWidget(window.show_background_cb)

        window.show_grid_cb = QCheckBox("Grid")
        window.show_grid_cb.setChecked(False)
        _ = toolbar.addWidget(window.show_grid_cb)

        window.show_info_cb = QCheckBox("Info")
        window.show_info_cb.setChecked(True)
        _ = toolbar.addWidget(window.show_info_cb)

        # Add tooltip toggle checkbox
        window.show_tooltips_cb = QCheckBox("Tooltips")
        window.show_tooltips_cb.setChecked(False)  # Off by default
        _ = toolbar.addWidget(window.show_tooltips_cb)

        # Create widgets needed for UIComponents compatibility
        self._create_ui_component_widgets(window)

        # Add stretch to push remaining items to the right
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
        _ = toolbar.addWidget(spacer)

    def _create_ui_component_widgets(self, window: MainWindow) -> None:
        """Create widgets required for UIComponents compatibility.

        These widgets are required for the Component Container Pattern to work correctly,
        even though not all are added to the toolbar.

        Args:
            window: The MainWindow instance
        """
        # Point editing widgets (used in properties panel if it exists)
        window.point_x_spinbox = QDoubleSpinBox()
        window.point_x_spinbox.setRange(-10000, 10000)
        window.point_x_spinbox.setDecimals(3)
        window.point_x_spinbox.setEnabled(False)
        window.ui.point_edit.x_edit = window.point_x_spinbox

        window.point_y_spinbox = QDoubleSpinBox()
        window.point_y_spinbox.setRange(-10000, 10000)
        window.point_y_spinbox.setDecimals(3)
        window.point_y_spinbox.setEnabled(False)
        window.ui.point_edit.y_edit = window.point_y_spinbox

        # Visualization sliders (used in properties panel if it exists)
        # Slider range 1-20 maps to point radius 0.25-5.0 (each tick = 0.25)
        window.point_size_slider = QSlider(Qt.Orientation.Horizontal)
        window.point_size_slider.setMinimum(1)
        window.point_size_slider.setMaximum(20)
        window.point_size_slider.setValue(10)  # Default 2.5 (10 * 0.25)
        window.ui.visualization.point_size_slider = window.point_size_slider

        window.line_width_slider = QSlider(Qt.Orientation.Horizontal)
        window.line_width_slider.setMinimum(1)
        window.line_width_slider.setMaximum(10)
        window.line_width_slider.setValue(2)
        window.ui.visualization.line_width_slider = window.line_width_slider

        # Keep btn_play_pause as it's used for playback functionality (though not visible)
        window.btn_play_pause = QPushButton()
        window.btn_play_pause.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        window.btn_play_pause.setCheckable(True)
        window.ui.timeline.play_button = window.btn_play_pause  # Map to timeline group

        window.fps_spinbox = QSpinBox()
        window.fps_spinbox.setMinimum(1)
        window.fps_spinbox.setMaximum(120)
        window.fps_spinbox.setValue(24)
        window.fps_spinbox.setSuffix(" fps")
        window.ui.timeline.fps_spinbox = window.fps_spinbox  # Map to timeline group

        window.frame_slider = QSlider(Qt.Orientation.Horizontal)
        window.frame_slider.setMinimum(1)
        window.frame_slider.setMaximum(1000)
        window.frame_slider.setValue(1)
        window.ui.timeline.timeline_slider = window.frame_slider  # Map to timeline group

        window.total_frames_label = QLabel("1")
        window.ui.status.info_label = window.total_frames_label  # Map to status group
        window.point_count_label = QLabel("Points: 0")
        window.ui.status.quality_score_label = window.point_count_label  # Map to status group
        window.selected_count_label = QLabel("Selected: 0")
        window.ui.status.quality_coverage_label = window.selected_count_label  # Map to status group
        window.bounds_label = QLabel("Bounds: N/A")
        window.ui.status.quality_consistency_label = window.bounds_label  # Map to status group

    def _build_central_widget(self, window: MainWindow) -> None:
        """Initialize the central widget with full-width curve view and bottom timeline.

        Args:
            window: The MainWindow instance
        """
        # Create main central widget with vertical layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create the main curve view area (full width, no side panels)
        window.curve_container = self._create_curve_view_container(window)

        # Add curve container with stretch factor so it expands
        main_layout.addWidget(window.curve_container, stretch=1)  # Takes all available space

        # Create timeline tabs widget here where it's actually used
        window.timeline_tabs = None  # Initialize to None first
        try:
            from ui.timeline_tabs import TimelineTabWidget

            window.timeline_tabs = TimelineTabWidget()
            # Connections will be set up later when handlers are available
            logger.info("Timeline tabs widget created successfully")
        except Exception as e:
            logger.warning(f"Could not create timeline tabs widget: {e}")
            window.timeline_tabs = None

        # Add timeline tabs widget if available - no stretch so it stays fixed height
        if window.timeline_tabs:
            window.timeline_tabs.setMinimumHeight(60)  # Ensure timeline gets its minimum space
            window.timeline_tabs.setFixedHeight(60)  # Force exact height
            main_layout.addWidget(window.timeline_tabs, stretch=0)  # Fixed height, no expansion
            logger.info("Timeline tabs added to main layout")

        # Set the central widget
        window.setCentralWidget(central_widget)

    def _create_curve_view_container(self, window: MainWindow) -> QWidget:
        """Create the container for the curve view.

        Args:
            window: The MainWindow instance

        Returns:
            The curve view container widget
        """
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.Box)
        container.setLineWidth(1)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create the actual CurveViewWidget
        window.curve_widget = CurveViewWidget(container)
        window.curve_widget.set_main_window(window)  # pyright: ignore[reportArgumentType]

        # Ensure the curve widget can receive keyboard focus
        window.curve_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout.addWidget(window.curve_widget)

        # Set focus to curve widget after creation
        def set_focus_safe() -> None:
            try:
                if window.curve_widget is not None:
                    window.curve_widget.setFocus()
            except RuntimeError:
                # Widget was deleted (C++ object destroyed)
                pass

        QTimer.singleShot(100, set_focus_safe)

        logger.info("CurveViewWidget created and integrated")

        return container

    def _build_dock_widgets(self, window: MainWindow) -> None:
        """Initialize dock widgets (optional, for future expansion).

        Args:
            window: The MainWindow instance
        """
        # Create tracking points panel dock widget
        window.tracking_panel_dock = QDockWidget("Tracking Points", window)
        window.tracking_panel = TrackingPointsPanel()
        window.tracking_panel_dock.setWidget(window.tracking_panel)

        # Set dock widget properties
        window.tracking_panel_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, window.tracking_panel_dock)
        window.tracking_panel_dock.setVisible(True)  # Make visible by default

        # TODO: Connect signals for tracking point management when handlers are implemented
        # window.tracking_panel.points_selected.connect(window._on_tracking_points_selected)
        # window.tracking_panel.point_visibility_changed.connect(window._on_point_visibility_changed)
        # window.tracking_panel.point_color_changed.connect(window._on_point_color_changed)
        # window.tracking_panel.point_deleted.connect(window._on_point_deleted)
        # window.tracking_panel.point_renamed.connect(window._on_point_renamed)

        logger.info("Tracking points panel dock widget initialized")

        # Create visualization panel dock widget
        window.visualization_panel_dock = QDockWidget("Visualization", window)

        # Ensure sliders exist (they're created in _create_ui_component_widgets)
        assert window.point_size_slider is not None, "point_size_slider must be initialized"
        assert window.line_width_slider is not None, "line_width_slider must be initialized"

        # Create container widget with layout
        viz_widget = QWidget()
        viz_layout = QGridLayout(viz_widget)
        viz_layout.setContentsMargins(10, 10, 10, 10)
        viz_layout.setSpacing(10)

        # Point Size slider
        point_size_label = QLabel("Point Size:")
        viz_layout.addWidget(point_size_label, 0, 0)
        viz_layout.addWidget(window.point_size_slider, 0, 1)

        point_size_value = QLabel(str(window.point_size_slider.value()))
        viz_layout.addWidget(point_size_value, 0, 2)
        window.point_size_slider.valueChanged.connect(lambda v: point_size_value.setText(str(v)))

        # Line Width slider
        line_width_label = QLabel("Line Width:")
        viz_layout.addWidget(line_width_label, 1, 0)
        viz_layout.addWidget(window.line_width_slider, 1, 1)

        line_width_value = QLabel(str(window.line_width_slider.value()))
        viz_layout.addWidget(line_width_value, 1, 2)
        window.line_width_slider.valueChanged.connect(lambda v: line_width_value.setText(str(v)))

        # Set the widget
        window.visualization_panel_dock.setWidget(viz_widget)

        # Set dock widget properties
        window.visualization_panel_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window.visualization_panel_dock)
        window.visualization_panel_dock.setVisible(True)  # Make visible by default

        logger.info("Visualization panel dock widget initialized")

    def _build_status_bar(self, window: MainWindow) -> None:
        """Initialize the status bar with additional widgets.

        Args:
            window: The MainWindow instance
        """
        window.status_bar = QStatusBar(window)
        window.setStatusBar(window.status_bar)

        # Add primary status label (left side) for thread-safe status messages
        window.status_label = QLabel("Ready")
        window.status_bar.addWidget(window.status_label)  # Regular widget goes on left

        # Add permanent widgets to status bar (right side)
        window.zoom_label = QLabel("Zoom: 100%")
        window.status_bar.addPermanentWidget(window.zoom_label)

        window.position_label = QLabel("X: 0.000, Y: 0.000")
        window.status_bar.addPermanentWidget(window.position_label)

    def _connect_actions(self, _window: MainWindow) -> None:
        """Connect actions to their handlers.

        Args:
            _window: The MainWindow instance (unused - connections handled later)
        """
        # Action connections are handled in MainWindowInitializer.connect_signals()
        # after controllers are created, so we skip them here
