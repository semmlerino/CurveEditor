#!/usr/bin/env python
"""
Keyboard Shortcuts Manager for CurveEditor.

This module provides a centralized way to manage keyboard shortcuts for the
application, creating and managing all QActions with their shortcuts.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction, QKeyEvent, QKeySequence
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from ui.curve_view_widget import CurveViewWidget

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
        self.action_export_data.setShortcut("Ctrl+E")
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
        self.action_reset_view.setShortcut("Ctrl+R")
        self.action_reset_view.setStatusTip("Reset the view to default")

        self.action_toggle_grid = QAction("Toggle &Grid", self.parent_widget)
        self.action_toggle_grid.setShortcut("Ctrl+Shift+G")
        self.action_toggle_grid.setStatusTip("Show/hide the grid overlay")

    def _create_curve_actions(self) -> None:
        """Create curve manipulation QActions."""
        self.action_smooth_curve = QAction("S&mooth Curve", self.parent_widget)
        self.action_smooth_curve.setShortcut("Ctrl+M")
        self.action_smooth_curve.setStatusTip("Apply smoothing to the curve")

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

    def connect_to_main_window(self, main_window) -> None:
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

        # Navigation actions (now handled by FrameNavigationController)
        _ = self.action_next_frame.triggered.connect(main_window.frame_nav_controller._on_next_frame)
        _ = self.action_prev_frame.triggered.connect(main_window.frame_nav_controller._on_prev_frame)
        _ = self.action_first_frame.triggered.connect(main_window.frame_nav_controller._on_first_frame)
        _ = self.action_last_frame.triggered.connect(main_window.frame_nav_controller._on_last_frame)

        # Playback actions (now handled by PlaybackController)
        _ = self.action_oscillate_playback.triggered.connect(main_window.playback_controller.toggle_playback)

        logger.info("Connected all shortcuts to MainWindow")


class CurveViewKeyboardHandler:
    """
    Handles direct keyboard events for the CurveViewWidget.

    This class processes keypress events that are handled directly in the widget,
    separate from the QAction-based shortcuts managed by ShortcutManager.
    """

    def __init__(self, curve_widget: "CurveViewWidget") -> None:
        """
        Initialize the keyboard handler.

        Args:
            curve_widget: The CurveViewWidget instance to handle events for
        """
        self.curve_widget: CurveViewWidget = curve_widget
        logger.info("CurveViewKeyboardHandler initialized")

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """
        Process a key press event.

        Args:
            event: QKeyEvent to process

        Returns:
            True if the event was handled, False otherwise
        """
        key = event.key()
        modifiers = event.modifiers()

        # Debug logging
        logger.info(
            f"[HANDLER] Key: {key}, Modifiers: {modifiers}, Selected: {len(self.curve_widget.selected_indices)} points"
        )

        # Clean modifiers by removing KeypadModifier for consistent checks
        clean_modifiers = modifiers & ~Qt.KeyboardModifier.KeypadModifier

        # Delete selected points
        if key == Qt.Key.Key_Delete and self.curve_widget.selected_indices:
            self._delete_selected_points()
            return True

        # Select all (Ctrl+A)
        elif key == Qt.Key.Key_A and clean_modifiers & Qt.KeyboardModifier.ControlModifier:
            self.curve_widget.select_all()
            return True

        # Deselect all (Escape)
        elif key == Qt.Key.Key_Escape:
            self._clear_selection()
            return True

        # Toggle centering mode (C key)
        elif key == Qt.Key.Key_C and not clean_modifiers:
            self._toggle_centering_mode()
            return True

        # Fit background image to view (F key)
        elif key == Qt.Key.Key_F and not clean_modifiers:
            if self.curve_widget.background_image:
                self.curve_widget.fit_to_background_image()
                logger.debug("[VIEW] Fitted background image to view")
                return True

        # Nudge points using number keys 2/4/6/8
        # Works with both numpad and regular number keys
        # Nudges selected points if any, otherwise nudges point at current frame
        elif key in (Qt.Key.Key_2, Qt.Key.Key_4, Qt.Key.Key_6, Qt.Key.Key_8):
            # Check if we have selected points or a current frame to work with
            has_selection = bool(self.curve_widget.selected_indices)
            current_frame = self.curve_widget.get_current_frame()
            has_current_frame = current_frame is not None and 0 <= (current_frame - 1) < len(
                self.curve_widget.curve_data
            )

            if has_selection or has_current_frame:
                logger.info(
                    f"[NUDGE] Handling nudge for key {key} - Selected: {len(self.curve_widget.selected_indices)} points, Current frame: {current_frame}"
                )
                # Accept both regular number keys and numpad keys (which have KeypadModifier)
                # Use clean_modifiers for modifier checks (Shift/Ctrl) but accept the key regardless of KeypadModifier
                return self._handle_nudging(key, clean_modifiers)
            else:
                logger.info(f"[NUDGE] Cannot nudge - no selection and no valid point at frame {current_frame}")
                return False

        # Arrow keys - pass through to parent for frame navigation
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            return False  # Let parent handle

        return False

    def _handle_nudging(self, key: int, modifiers: Qt.KeyboardModifier) -> bool:
        """
        Handle point nudging with number keys.

        Args:
            key: The key pressed (2/4/6/8)
            modifiers: Keyboard modifiers (cleaned, without KeypadModifier)

        Returns:
            True if nudging was performed
        """
        from ui.ui_constants import DEFAULT_NUDGE_AMOUNT

        # Calculate nudge amount based on modifiers
        nudge_amount = DEFAULT_NUDGE_AMOUNT
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            nudge_amount = 10.0
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            nudge_amount = 0.1

        logger.info(f"[NUDGE] Nudge amount: {nudge_amount}, Key: {key}")

        # Apply nudging based on key
        # Both regular number keys and numpad keys use the same key codes
        if key == Qt.Key.Key_4:  # Left
            logger.info(f"[NUDGE] Moving left by {-nudge_amount}")
            self._nudge_selected(-nudge_amount, 0)
        elif key == Qt.Key.Key_6:  # Right
            logger.info(f"[NUDGE] Moving right by {nudge_amount}")
            self._nudge_selected(nudge_amount, 0)
        elif key == Qt.Key.Key_8:  # Up
            logger.info(f"[NUDGE] Moving up by {-nudge_amount}")
            self._nudge_selected(0, -nudge_amount)
        elif key == Qt.Key.Key_2:  # Down
            logger.info(f"[NUDGE] Moving down by {nudge_amount}")
            self._nudge_selected(0, nudge_amount)

        self.curve_widget.update()
        logger.info("[NUDGE] Update called on curve widget")
        return True

    def _nudge_selected(self, dx: float, dy: float) -> None:
        """
        Nudge selected points or current frame point by the given offset.

        Args:
            dx: X offset in data units
            dy: Y offset in data units
        """
        # If points are selected, nudge them
        if self.curve_widget.selected_indices:
            logger.info(f"[NUDGE] Nudging {len(self.curve_widget.selected_indices)} selected points")
            self.curve_widget.nudge_selected(dx, dy)
        else:
            # Otherwise, nudge the point at the current frame
            current_frame = self.curve_widget.get_current_frame()
            if current_frame is not None:
                frame_index = current_frame - 1  # Convert to 0-based index
                if 0 <= frame_index < len(self.curve_widget.curve_data):
                    logger.info(f"[NUDGE] Nudging point at frame {current_frame} (index {frame_index})")
                    # Temporarily select the point, nudge it, then clear selection
                    self.curve_widget._select_point(frame_index, add_to_selection=False)
                    self.curve_widget.nudge_selected(dx, dy)
                    # The nudge_selected method already sets KEYFRAME status
                    self.curve_widget.clear_selection()
                else:
                    logger.warning(
                        f"[NUDGE] Frame {current_frame} out of range (0-{len(self.curve_widget.curve_data)-1})"
                    )

    def _delete_selected_points(self) -> None:
        """Delete all selected points."""
        self.curve_widget.delete_selected_points()

    def _clear_selection(self) -> None:
        """Clear the current selection."""
        self.curve_widget.clear_selection()

    def _toggle_centering_mode(self) -> None:
        """Toggle centering mode on/off."""
        self.curve_widget.centering_mode = not self.curve_widget.centering_mode
        logger.info(f"[KEY_C] Centering mode {'enabled' if self.curve_widget.centering_mode else 'disabled'}")

        # If enabling centering mode, immediately center on selection or current frame
        if self.curve_widget.centering_mode:
            if self.curve_widget.selected_indices:
                logger.info(f"[KEY_C] Centering view on {len(self.curve_widget.selected_indices)} selected points...")
                self.curve_widget.center_on_selection()
                logger.info("[KEY_C] View centering completed")
            else:
                current_frame = self.curve_widget.get_current_frame()
                if current_frame is not None:
                    logger.info(f"[KEY_C] No points selected, centering on current frame {current_frame}")
                    self.curve_widget.center_on_frame(current_frame)
                    logger.info("[KEY_C] View centered on current frame")

        # Update status bar to show centering mode state
        status_msg = "Centering: ON" if self.curve_widget.centering_mode else "Centering: OFF"
        self.curve_widget.update_status(status_msg, 2000)
