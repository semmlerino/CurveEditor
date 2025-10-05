#!/usr/bin/env python
"""
Keyboard Shortcuts Manager for CurveEditor.

This module provides a centralized way to manage keyboard shortcuts for the
application, creating and managing all QActions with their shortcuts.
"""

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    pass

from core.logger_utils import get_logger

logger = get_logger("keyboard_shortcuts")


class ShortcutManager(QObject):
    """
    Manages keyboard shortcuts and actions for the CurveEditor application.

    This class provides a centralized way to create, manage, and organize
    all QActions with their shortcuts, keeping MainWindow lean.
    """

    # Attributes - initialized in __init__
    parent_widget: QWidget | None

    # File actions
    action_new: QAction
    action_open: QAction
    action_save: QAction
    action_save_as: QAction
    action_load_images: QAction
    action_export_data: QAction
    action_quit: QAction

    # Edit actions
    action_undo: QAction
    action_redo: QAction
    action_select_all: QAction
    action_add_point: QAction

    # View actions
    action_zoom_in: QAction
    action_zoom_out: QAction
    action_zoom_fit: QAction
    action_reset_view: QAction
    action_toggle_grid: QAction

    # Curve actions
    action_smooth_curve: QAction
    action_filter_curve: QAction
    action_analyze_curve: QAction

    # Navigation actions
    action_next_frame: QAction
    action_prev_frame: QAction
    action_first_frame: QAction
    action_last_frame: QAction

    # Playback actions
    action_oscillate_playback: QAction

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the shortcut manager and create all QActions.

        Args:
            parent: Parent widget for the actions (typically MainWindow)
        """
        super().__init__(parent)
        self.parent_widget = parent
        self._create_file_actions()
        self._create_edit_actions()
        self._create_view_actions()
        self._create_curve_actions()
        self._create_navigation_actions()
        self._create_playback_actions()

        logger.info("ShortcutManager initialized with QActions")

    def _create_file_actions(self) -> None:
        """Create file-related QActions."""
        self.action_new = QAction("&New", self.parent_widget)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.setStatusTip("Create a new curve")

        self.action_open = QAction("&Open...", self.parent_widget)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.setStatusTip("Open an existing curve file")

        self.action_save = QAction("&Save", self.parent_widget)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.setStatusTip("Save the current curve")

        self.action_save_as = QAction("Save &As...", self.parent_widget)
        self.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_as.setStatusTip("Save the curve with a new name")

        self.action_load_images = QAction("&Load Images...", self.parent_widget)
        self.action_load_images.setShortcut("Ctrl+I")
        self.action_load_images.setStatusTip("Load background images")

        self.action_export_data = QAction("&Export Data...", self.parent_widget)
        self.action_export_data.setShortcut("Ctrl+Shift+E")
        self.action_export_data.setStatusTip("Export curve data")

        self.action_quit = QAction("&Quit", self.parent_widget)
        self.action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_quit.setStatusTip("Exit the application")

    def _create_edit_actions(self) -> None:
        """Create edit-related QActions."""
        self.action_undo = QAction("&Undo", self.parent_widget)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.setStatusTip("Undo the last action")

        self.action_redo = QAction("&Redo", self.parent_widget)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.setStatusTip("Redo the previously undone action")

        self.action_select_all = QAction("Select &All", self.parent_widget)
        self.action_select_all.setShortcut("Ctrl+A")
        self.action_select_all.setStatusTip("Select all points")

        # Changed from Ctrl+A to avoid conflict with select all
        self.action_add_point = QAction("Add &Point", self.parent_widget)
        self.action_add_point.setShortcut("Ctrl+Shift+N")
        self.action_add_point.setStatusTip("Add a new point to the curve")

    def _create_view_actions(self) -> None:
        """Create view-related QActions."""
        self.action_zoom_in = QAction("Zoom &In", self.parent_widget)
        self.action_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.action_zoom_in.setStatusTip("Zoom in the view")

        self.action_zoom_out = QAction("Zoom &Out", self.parent_widget)
        self.action_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.action_zoom_out.setStatusTip("Zoom out the view")

        self.action_zoom_fit = QAction("Zoom &Fit", self.parent_widget)
        self.action_zoom_fit.setShortcut("Ctrl+0")
        self.action_zoom_fit.setStatusTip("Fit curve to view")

        self.action_reset_view = QAction("&Reset View", self.parent_widget)
        self.action_reset_view.setShortcut("Ctrl+Shift+R")
        self.action_reset_view.setStatusTip("Reset the view to default")

        self.action_toggle_grid = QAction("Toggle &Grid", self.parent_widget)
        self.action_toggle_grid.setShortcut("Ctrl+Shift+G")
        self.action_toggle_grid.setStatusTip("Show/hide the grid overlay")

    def _create_curve_actions(self) -> None:
        """Create curve manipulation QActions."""
        self.action_smooth_curve = QAction("S&mooth Curve", self.parent_widget)
        self.action_smooth_curve.setShortcut("Ctrl+E")
        self.action_smooth_curve.setStatusTip("Apply smoothing to selected points")

        self.action_filter_curve = QAction("&Filter Curve", self.parent_widget)
        self.action_filter_curve.setShortcut("Ctrl+F")
        self.action_filter_curve.setStatusTip("Apply filtering to the curve")

        self.action_analyze_curve = QAction("Ana&lyze Curve", self.parent_widget)
        self.action_analyze_curve.setShortcut("Ctrl+L")
        self.action_analyze_curve.setStatusTip("Analyze curve properties")

    def _create_navigation_actions(self) -> None:
        """Create frame navigation QActions."""
        # Note: Arrow keys will be handled by focused widget
        # These actions can be triggered via menu/toolbar
        self.action_next_frame = QAction("Next Frame", self.parent_widget)
        self.action_next_frame.setShortcut("Right")
        self.action_next_frame.setStatusTip("Go to next frame")

        self.action_prev_frame = QAction("Previous Frame", self.parent_widget)
        self.action_prev_frame.setShortcut("Left")
        self.action_prev_frame.setStatusTip("Go to previous frame")

        self.action_first_frame = QAction("First Frame", self.parent_widget)
        self.action_first_frame.setShortcut("Home")
        self.action_first_frame.setStatusTip("Go to first frame")

        self.action_last_frame = QAction("Last Frame", self.parent_widget)
        self.action_last_frame.setShortcut("End")
        self.action_last_frame.setStatusTip("Go to last frame")

    def _create_playback_actions(self) -> None:
        """Create playback control QActions."""
        self.action_oscillate_playback = QAction("Toggle Playback", self.parent_widget)
        self.action_oscillate_playback.setShortcut("Space")
        self.action_oscillate_playback.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.action_oscillate_playback.setStatusTip("Toggle oscillating playback")

    def get_file_actions(self) -> list[QAction | None]:
        """
        Get all file-related actions for the File menu.
        None values indicate menu separators.

        Returns:
            List of file actions in menu order
        """
        return [
            self.action_new,
            self.action_open,
            None,  # Separator
            self.action_save,
            self.action_save_as,
            None,  # Separator
            self.action_load_images,
            self.action_export_data,
            None,  # Separator
            self.action_quit,
        ]

    def get_edit_actions(self) -> list[QAction | None]:
        """
        Get all edit-related actions for the Edit menu.
        None values indicate menu separators.

        Returns:
            List of edit actions in menu order
        """
        return [
            self.action_undo,
            self.action_redo,
            None,  # Separator
            self.action_select_all,
            self.action_add_point,
        ]

    def get_view_actions(self) -> list[QAction | None]:
        """
        Get all view-related actions for the View menu.
        None values indicate menu separators.

        Returns:
            List of view actions in menu order
        """
        return [
            self.action_zoom_in,
            self.action_zoom_out,
            self.action_zoom_fit,
            None,  # Separator
            self.action_reset_view,
            self.action_toggle_grid,
        ]

    def get_curve_actions(self) -> list[QAction | None]:
        """
        Get all curve-related actions for the Curve menu.
        None values indicate menu separators.

        Returns:
            List of curve actions in menu order
        """
        return [
            self.action_smooth_curve,
            self.action_filter_curve,
            self.action_analyze_curve,
        ]

    def get_navigation_actions(self) -> list[QAction | None]:
        """
        Get all navigation-related actions.
        None values indicate menu separators.

        Returns:
            List of navigation actions
        """
        return [
            self.action_prev_frame,
            self.action_next_frame,
            None,  # Separator
            self.action_first_frame,
            self.action_last_frame,
        ]

    def get_all_actions(self) -> dict[str, QAction]:
        """
        Get all actions as a dictionary.

        Returns:
            Dictionary mapping action names to QAction objects
        """
        return {
            "new": self.action_new,
            "open": self.action_open,
            "save": self.action_save,
            "save_as": self.action_save_as,
            "load_images": self.action_load_images,
            "export_data": self.action_export_data,
            "quit": self.action_quit,
            "undo": self.action_undo,
            "redo": self.action_redo,
            "select_all": self.action_select_all,
            "add_point": self.action_add_point,
            "zoom_in": self.action_zoom_in,
            "zoom_out": self.action_zoom_out,
            "zoom_fit": self.action_zoom_fit,
            "reset_view": self.action_reset_view,
            "toggle_grid": self.action_toggle_grid,
            "smooth_curve": self.action_smooth_curve,
            "filter_curve": self.action_filter_curve,
            "analyze_curve": self.action_analyze_curve,
            "next_frame": self.action_next_frame,
            "prev_frame": self.action_prev_frame,
            "first_frame": self.action_first_frame,
            "last_frame": self.action_last_frame,
            "oscillate_playback": self.action_oscillate_playback,
        }

    def connect_to_main_window(self, main_window: Any) -> None:
        """
        Connect actions to MainWindow slots.

        Args:
            main_window: The MainWindow instance to connect to
        """
        # File actions
        _ = self.action_new.triggered.connect(main_window._on_action_new)
        _ = self.action_open.triggered.connect(main_window._on_action_open)
        _ = self.action_save.triggered.connect(main_window._on_action_save)
        _ = self.action_save_as.triggered.connect(main_window._on_action_save_as)
        _ = self.action_load_images.triggered.connect(main_window._on_load_images)
        _ = self.action_export_data.triggered.connect(main_window._on_export_data)
        _ = self.action_quit.triggered.connect(main_window.close)

        # Edit actions
        _ = self.action_undo.triggered.connect(main_window._on_action_undo)
        _ = self.action_redo.triggered.connect(main_window._on_action_redo)
        _ = self.action_select_all.triggered.connect(main_window._on_select_all)
        _ = self.action_add_point.triggered.connect(main_window._on_add_point)

        # View actions
        _ = self.action_zoom_in.triggered.connect(main_window._on_action_zoom_in)
        _ = self.action_zoom_out.triggered.connect(main_window._on_action_zoom_out)
        _ = self.action_zoom_fit.triggered.connect(main_window._on_zoom_fit)
        _ = self.action_reset_view.triggered.connect(main_window._on_action_reset_view)
        _ = self.action_toggle_grid.triggered.connect(main_window._on_toggle_grid)

        # Curve actions
        _ = self.action_smooth_curve.triggered.connect(main_window._on_smooth_curve)
        _ = self.action_filter_curve.triggered.connect(main_window._on_filter_curve)
        _ = self.action_analyze_curve.triggered.connect(main_window._on_analyze_curve)

        # Add actions to window for keyboard shortcuts to work globally
        main_window.addAction(self.action_undo)
        main_window.addAction(self.action_redo)
        main_window.addAction(self.action_select_all)
        main_window.addAction(self.action_zoom_in)
        main_window.addAction(self.action_zoom_out)
        main_window.addAction(self.action_reset_view)

        # Navigation actions (now handled by TimelineController)
        _ = self.action_next_frame.triggered.connect(main_window.timeline_controller._on_next_frame)
        _ = self.action_prev_frame.triggered.connect(main_window.timeline_controller._on_prev_frame)
        _ = self.action_first_frame.triggered.connect(main_window.timeline_controller._on_first_frame)
        _ = self.action_last_frame.triggered.connect(main_window.timeline_controller._on_last_frame)

        # Playback actions (now handled by TimelineController)
        _ = self.action_oscillate_playback.triggered.connect(main_window.timeline_controller.toggle_playback)

        logger.info("Connected all shortcuts to MainWindow")
