#!/usr/bin/env python
"""
Signal Connection Manager for CurveEditor.

This controller handles all signal connections that were previously
handled directly in MainWindow, centralizing signal wiring.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.logger_utils import get_logger
from stores import ConnectionVerifier

logger = get_logger("signal_connection_manager")


class SignalConnectionManager:
    """
    Manager for handling all signal connections in MainWindow.

    Extracted from MainWindow to reduce complexity and centralize
    all signal wiring in one place.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the signal connection manager.

        Args:
            main_window: Reference to the main window for signal connections
        """
        self.main_window = main_window
        logger.info("SignalConnectionManager initialized")

    def connect_all_signals(self) -> None:
        """Connect all signals in the correct order."""
        self._connect_file_operations_signals()
        self._connect_signals()
        self._connect_store_signals()

        # Connect curve widget signals (after all UI components are created)
        if self.main_window.curve_widget:
            self._connect_curve_widget_signals()

        # Verify all critical connections (fail-loud mechanism)
        self._verify_connections()

        logger.info("All signal connections established")

    def _connect_file_operations_signals(self) -> None:
        """Connect signals from file operations manager."""
        # Connect file loading signals
        self.main_window.file_operations.tracking_data_loaded.connect(self.main_window.on_tracking_data_loaded)
        self.main_window.file_operations.multi_point_data_loaded.connect(self.main_window.on_multi_point_data_loaded)
        self.main_window.file_operations.image_sequence_loaded.connect(
            self.main_window.view_management_controller.on_image_sequence_loaded
        )
        self.main_window.file_operations.progress_updated.connect(self.main_window.on_file_load_progress)
        self.main_window.file_operations.error_occurred.connect(self.main_window.on_file_load_error)
        self.main_window.file_operations.finished.connect(self.main_window.on_file_load_finished)

        # Connect file operation status signals
        self.main_window.file_operations.file_loaded.connect(self.main_window.on_file_loaded)
        self.main_window.file_operations.file_saved.connect(self.main_window.on_file_saved)

        logger.info("Connected file operations signals")

    def _connect_signals(self) -> None:
        """Connect signals from state manager and shortcuts."""
        # Connect state manager signals
        _ = self.main_window.state_manager.file_changed.connect(self.main_window.on_file_changed)
        _ = self.main_window.state_manager.modified_changed.connect(self.main_window.on_modified_changed)
        _ = self.main_window.state_manager.frame_changed.connect(self.main_window.on_state_frame_changed)
        _ = self.main_window.state_manager.selection_changed.connect(self.main_window.on_selection_changed)
        _ = self.main_window.state_manager.view_state_changed.connect(self.main_window.on_view_state_changed)

        # Connect ViewManagementController to frame changes for background updates
        _ = self.main_window.state_manager.frame_changed.connect(
            self.main_window.view_management_controller.update_background_for_frame
        )

        # Connect timeline_tabs to StateManager as observer
        if self.main_window.timeline_tabs:
            self.main_window.timeline_tabs.set_state_manager(self.main_window.state_manager)

        # Connect timeline controller signals (unified playback and navigation)
        _ = self.main_window.timeline_controller.frame_changed.connect(
            self.main_window.on_frame_changed_from_controller
        )
        _ = self.main_window.timeline_controller.status_message.connect(self.main_window.update_status)

        # NOTE: timeline_tabs.frame_changed connection REMOVED to prevent circular signal flow
        # With StateManager as single source of truth, timeline_tabs delegates frame changes
        # through StateManager, eliminating need for this connection

    def _connect_store_signals(self) -> None:
        """Connect to reactive store signals for automatic updates."""
        # Timeline now connects directly to store signals - no manual updates needed
        # The timeline_tabs widget subscribes to store signals directly in its __init__
        # This ensures automatic reactive updates without going through the controller

        # Only connect selection change which MainWindow needs
        self.main_window.get_curve_store().selection_changed.connect(self.main_window.on_store_selection_changed)

        logger.info("Connected MainWindow to reactive store signals")

    def _connect_curve_widget_signals(self) -> None:
        """Connect signals from the curve widget."""
        if not self.main_window.curve_widget:
            return

        # Connect curve widget signals to handlers
        _ = self.main_window.curve_widget.point_selected.connect(self.main_window.on_point_selected)
        _ = self.main_window.curve_widget.point_moved.connect(self.main_window.on_point_moved)
        _ = self.main_window.curve_widget.selection_changed.connect(self.main_window.on_curve_selection_changed)
        _ = self.main_window.curve_widget.view_changed.connect(self.main_window.on_curve_view_changed)
        _ = self.main_window.curve_widget.zoom_changed.connect(self.main_window.on_curve_zoom_changed)
        # Timeline now updates automatically via store signals - no manual connection needed
        # _ = self.main_window.curve_widget.data_changed.connect(
        #     lambda: self.main_window.timeline_controller.update_timeline_tabs()
        # )

        # Connect view options to view options controller
        if self.main_window.show_background_cb:
            _ = self.main_window.show_background_cb.stateChanged.connect(
                self.main_window.view_management_controller.update_curve_view_options
            )
        if self.main_window.show_grid_cb:
            _ = self.main_window.show_grid_cb.stateChanged.connect(
                self.main_window.view_management_controller.update_curve_view_options
            )
        if self.main_window.show_info_cb:
            _ = self.main_window.show_info_cb.stateChanged.connect(
                self.main_window.view_management_controller.update_curve_view_options
            )
        if self.main_window.show_tooltips_cb:
            _ = self.main_window.show_tooltips_cb.stateChanged.connect(
                self.main_window.view_management_controller.toggle_tooltips
            )
        if self.main_window.point_size_slider:
            _ = self.main_window.point_size_slider.valueChanged.connect(
                self.main_window.view_management_controller.update_curve_point_size
            )
        if self.main_window.line_width_slider:
            _ = self.main_window.line_width_slider.valueChanged.connect(
                self.main_window.view_management_controller.update_curve_line_width
            )

    def _verify_connections(self) -> None:
        """Verify all critical signal connections are established."""
        verifier = ConnectionVerifier()

        # Add critical store connections to verify
        verifier.add_required_connection(
            "CurveDataStore",
            self.main_window.get_curve_store(),
            "data_changed",
            "TimelineController",
            self.main_window.timeline_controller,  # pyright: ignore[reportArgumentType]
            "update_timeline_tabs",
            critical=False,  # TimelineController doesn't extend QObject, connection handled differently
        )

        verifier.add_required_connection(
            "CurveDataStore",
            self.main_window.get_curve_store(),
            "selection_changed",
            "MainWindow",
            self.main_window,
            "on_store_selection_changed",
            critical=True,
        )

        # Add curve widget connections if available
        if self.main_window.curve_widget:
            verifier.add_required_connection(
                "CurveViewWidget",
                self.main_window.curve_widget,
                "point_selected",
                "MainWindow",
                self.main_window,
                "on_point_selected",
                critical=True,
            )

            verifier.add_required_connection(
                "CurveViewWidget",
                self.main_window.curve_widget,
                "selection_changed",
                "MainWindow",
                self.main_window,
                "on_curve_selection_changed",
                critical=True,
            )

        # Add timeline tabs connections if available
        if self.main_window.timeline_tabs:
            verifier.add_required_connection(
                "TimelineTabs",
                self.main_window.timeline_tabs,
                "frame_changed",
                "TimelineController",
                self.main_window.timeline_controller,  # pyright: ignore[reportArgumentType]
                "on_timeline_tab_clicked",
                critical=False,  # TimelineController doesn't extend QObject, connection handled differently
            )

        # Perform verification
        all_connected, reports = verifier.verify_all()

        if not all_connected:
            # Log all failures
            verifier.log_report(verbose=False)

            # Raise error for critical failures (fail loud!)
            verifier.raise_if_failed()
        else:
            logger.info(f"All {len(reports)} critical signal connections verified successfully")
