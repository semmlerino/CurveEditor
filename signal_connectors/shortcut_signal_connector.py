#!/usr/bin/env python

"""
Shortcut Signal Connector for 3DE4 Curve Editor.

This module handles keyboard shortcut connections for the application.
It organizes shortcuts by functional area for better maintainability.
"""

# Standard library imports
from typing import TYPE_CHECKING, Any

from components.ui_components import UIComponents
from services.centering_zoom_service import CenteringZoomService as ZoomOperations
from services.curve_service import CurveService as CurveViewOperations
from services.dialog_service import DialogService
from services.file_service import FileService
from services.history_service import HistoryService as HistoryOperations
from services.image_service import ImageService as ImageOperations
from services.logging_service import LoggingService
from services.visualization_service import VisualizationService as VisualizationOperations

# Local imports
from ui.keyboard_shortcuts import ShortcutManager

# Configure logger
logger = LoggingService.get_logger("shortcut_signal_connector")

if TYPE_CHECKING:
    pass


class ShortcutSignalConnector:
    """Handles keyboard shortcut connections."""

    @staticmethod
    def _toggle_attribute_and_update(obj: object, attr_name: str) -> None:
        """Helper method to toggle a boolean attribute and update view."""
        setattr(obj, attr_name, not getattr(obj, attr_name, False))
        if hasattr(obj, "update"):
            obj.update()

    @staticmethod
    def connect_shortcuts(main_window: Any) -> None:
        """Connect all keyboard shortcuts.

        Args:
            main_window: The main application window
        """
        ShortcutSignalConnector._connect_file_shortcuts(main_window)
        ShortcutSignalConnector._connect_edit_shortcuts(main_window)
        ShortcutSignalConnector._connect_view_shortcuts(main_window)
        ShortcutSignalConnector._connect_timeline_shortcuts(main_window)
        ShortcutSignalConnector._connect_tool_shortcuts(main_window)

        logger.info("Connected keyboard shortcuts")

    @staticmethod
    def _connect_file_shortcuts(main_window: Any) -> None:
        """Connect file operation shortcuts."""
        ShortcutManager.connect_shortcut(main_window, "load", lambda: FileService.load_track_data(main_window))
        ShortcutManager.connect_shortcut(main_window, "save", lambda: FileService.save_track_data(main_window))
        ShortcutManager.connect_shortcut(main_window, "add", lambda: FileService.add_track_data(main_window))
        # CSV export functionality has been removed

    @staticmethod
    def _connect_edit_shortcuts(main_window: Any) -> None:
        """Connect edit operation shortcuts."""
        # Undo/Redo
        ShortcutManager.connect_shortcut(main_window, "undo", lambda: HistoryOperations.undo_action(main_window))
        ShortcutManager.connect_shortcut(main_window, "redo", lambda: HistoryOperations.redo_action(main_window))

        # Selection operations
        ShortcutManager.connect_shortcut(
            main_window,
            "select_all",
            lambda: CurveViewOperations.select_all_points(main_window.curve_view, main_window),
        )
        ShortcutManager.connect_shortcut(
            main_window,
            "deselect_all",
            lambda: CurveViewOperations.clear_selection(main_window.curve_view, main_window),
        )
        ShortcutManager.connect_shortcut(
            main_window,
            "delete_selected",
            lambda: CurveViewOperations.delete_selected_points(main_window.curve_view, main_window),
        )
        ShortcutManager.connect_shortcut(
            main_window,
            "clear_selection",
            lambda: CurveViewOperations.clear_selection(main_window.curve_view, main_window),
        )

        # Nudging operations
        ShortcutManager.connect_shortcut(
            main_window, "nudge_up", lambda: CurveViewOperations.nudge_selected_points(main_window.curve_view, dy=-1)
        )
        ShortcutManager.connect_shortcut(
            main_window, "nudge_down", lambda: CurveViewOperations.nudge_selected_points(main_window.curve_view, dy=1)
        )
        ShortcutManager.connect_shortcut(
            main_window, "nudge_left", lambda: CurveViewOperations.nudge_selected_points(main_window.curve_view, dx=-1)
        )
        ShortcutManager.connect_shortcut(
            main_window, "nudge_right", lambda: CurveViewOperations.nudge_selected_points(main_window.curve_view, dx=1)
        )

    @staticmethod
    def _connect_view_shortcuts(main_window: Any) -> None:
        """Connect view operation shortcuts."""
        # Basic view operations
        ShortcutManager.connect_shortcut(
            main_window, "reset_view", lambda: CurveViewOperations.reset_view(main_window.curve_view)
        )

        # Toggle operations
        ShortcutManager.connect_shortcut(
            main_window,
            "toggle_grid",
            lambda: VisualizationOperations.toggle_grid(
                main_window,
                not main_window.toggle_grid_button.isChecked() if hasattr(main_window, "toggle_grid_button") else False,
            ),
        )
        ShortcutManager.connect_shortcut(
            main_window,
            "toggle_velocity",
            lambda: VisualizationOperations.toggle_velocity_vectors(
                main_window,
                not main_window.toggle_vectors_button.isChecked()
                if hasattr(main_window, "toggle_vectors_button")
                else False,
            ),
        )
        ShortcutManager.connect_shortcut(
            main_window,
            "toggle_frame_numbers",
            lambda: VisualizationOperations.toggle_all_frame_numbers(
                main_window,
                not main_window.toggle_frame_numbers_button.isChecked()
                if hasattr(main_window, "toggle_frame_numbers_button")
                else False,
            ),
        )
        ShortcutManager.connect_shortcut(
            main_window,
            "toggle_crosshair",
            lambda: VisualizationOperations.toggle_crosshair_internal(
                main_window.curve_view, not getattr(main_window.curve_view, "show_crosshair", False)
            ),
        )
        ShortcutManager.connect_shortcut(
            main_window, "toggle_background", lambda: ImageOperations.toggle_background(main_window)
        )

        # Zoom operations
        ShortcutManager.connect_shortcut(
            main_window, "zoom_in", lambda: ZoomOperations.zoom_view(main_window.curve_view, 1.2)
        )  # Zoom in by 20%
        ShortcutManager.connect_shortcut(
            main_window, "zoom_out", lambda: ZoomOperations.zoom_view(main_window.curve_view, 1 / 1.2)
        )  # Zoom out by 20%

        # Toggle Y-axis flip
        ShortcutManager.connect_shortcut(
            main_window,
            "toggle_y_flip",
            lambda: ShortcutSignalConnector._toggle_attribute_and_update(main_window.curve_view, "flip_y_axis"),
        )

        # Toggle scale to image
        ShortcutManager.connect_shortcut(
            main_window,
            "toggle_scale_to_image",
            lambda: ShortcutSignalConnector._toggle_attribute_and_update(main_window.curve_view, "scale_to_image"),
        )

        # Toggle auto-center on selected point
        ShortcutManager.connect_shortcut(
            main_window,
            "center_on_point",  # 'C' key
            lambda: main_window.set_centering_enabled(not getattr(main_window, "auto_center_enabled", False)),
        )

        # Fullscreen toggle (commented out as method is missing in MainWindow)
        # ShortcutManager.connect_shortcut(main_window, "toggle_fullscreen",
        #                                lambda: main_window.toggle_fullscreen() if hasattr(main_window, 'toggle_fullscreen') else None)

    @staticmethod
    def _connect_timeline_shortcuts(main_window: Any) -> None:
        """Connect timeline operation shortcuts."""
        ShortcutManager.connect_shortcut(main_window, "next_frame", lambda: UIComponents.next_frame(main_window))
        ShortcutManager.connect_shortcut(main_window, "prev_frame", lambda: UIComponents.prev_frame(main_window))
        ShortcutManager.connect_shortcut(main_window, "play_pause", lambda: UIComponents.toggle_playback(main_window))
        ShortcutManager.connect_shortcut(
            main_window, "first_frame", lambda: UIComponents.go_to_first_frame(main_window)
        )
        ShortcutManager.connect_shortcut(main_window, "last_frame", lambda: UIComponents.go_to_last_frame(main_window))
        ShortcutManager.connect_shortcut(
            main_window, "frame_forward_10", lambda: UIComponents.advance_frames(main_window, 10)
        )
        ShortcutManager.connect_shortcut(
            main_window, "frame_back_10", lambda: UIComponents.advance_frames(main_window, -10)
        )

    @staticmethod
    def _connect_tool_shortcuts(main_window: Any) -> None:
        """Connect tool operation shortcuts."""
        ShortcutManager.connect_shortcut(
            main_window, "smooth_selected", main_window.apply_smooth_operation
        )  # Connect to MainWindow method
        ShortcutManager.connect_shortcut(
            main_window, "filter_selected", lambda: DialogService.show_filter_dialog(main_window)
        )
        # Problem detection is commented out as it's temporarily disabled
        # ShortcutManager.connect_shortcut(main_window, "detect_problems",
        #                                lambda: DialogService.show_problem_detection_dialog(main_window))
