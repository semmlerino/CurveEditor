#!/usr/bin/env python
"""
Signal Connection Manager for CurveEditor.

This controller handles all signal connections that were previously
handled directly in MainWindow, centralizing signal wiring.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from PySide6.QtCore import Qt

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
        self.main_window: MainWindow = main_window
        logger.info("SignalConnectionManager initialized")

    def __del__(self) -> None:
        """Disconnect all signals to prevent memory leaks.

        SignalConnectionManager creates 28+ signal connections to MainWindow,
        StateManager, FileOperations, and UI components. Without cleanup,
        these connections would keep objects alive, causing memory leaks.
        """
        # Disconnect file operations signals (8 connections)
        try:
            if self.main_window.file_operations:
                file_ops = self.main_window.file_operations
                _ = file_ops.tracking_data_loaded.disconnect(self.main_window.on_tracking_data_loaded)
                _ = file_ops.multi_point_data_loaded.disconnect(self.main_window.on_multi_point_data_loaded)
                _ = file_ops.image_sequence_loaded.disconnect(
                    self.main_window.view_management_controller.on_image_sequence_loaded
                )
                _ = file_ops.progress_updated.disconnect(self.main_window.on_file_load_progress)
                _ = file_ops.error_occurred.disconnect(self.main_window.on_file_load_error)
                _ = file_ops.finished.disconnect(self.main_window.on_file_load_finished)
                _ = file_ops.file_loaded.disconnect(self.main_window.on_file_loaded)
                _ = file_ops.file_saved.disconnect(self.main_window.on_file_saved)
        except (RuntimeError, AttributeError):
            pass  # Already disconnected or objects destroyed

        # Disconnect state manager signals (5 connections)
        try:
            if self.main_window.state_manager:
                state_mgr = self.main_window.state_manager
                _ = state_mgr.file_changed.disconnect(self.main_window.on_file_changed)
                _ = state_mgr.modified_changed.disconnect(self.main_window.on_modified_changed)
                _ = state_mgr.selection_changed.disconnect(self.main_window.on_selection_changed)
                _ = state_mgr.view_state_changed.disconnect(self.main_window.on_view_state_changed)
                # Lambda connection cannot be disconnected - will be cleaned up with state_manager
        except (RuntimeError, AttributeError):
            pass  # Already disconnected or objects destroyed

        # Disconnect timeline controller signals (1 connection)
        # REMOVED: timeline.frame_changed disconnect - signal emission removed from TimelineController
        try:
            if self.main_window.timeline_controller:
                timeline = self.main_window.timeline_controller
                # TimelineController is QObject with signals at runtime
                _ = timeline.status_message.disconnect(self.main_window.update_status)
        except (RuntimeError, AttributeError):
            pass  # Already disconnected or objects destroyed

        # Disconnect curve widget signals (5 connections)
        try:
            if self.main_window.curve_widget is not None:
                widget = self.main_window.curve_widget
                _ = widget.point_selected.disconnect(self.main_window.on_point_selected)
                _ = widget.point_moved.disconnect(self.main_window.on_point_moved)
                _ = widget.selection_changed.disconnect(self.main_window.on_curve_selection_changed)
                _ = widget.view_changed.disconnect(self.main_window.on_curve_view_changed)
                _ = widget.zoom_changed.disconnect(self.main_window.on_curve_zoom_changed)
        except (RuntimeError, AttributeError):
            pass  # Already disconnected or objects destroyed

        # Disconnect view options signals (6 connections)
        try:
            mw = self.main_window
            if mw.show_background_cb is not None:
                _ = mw.show_background_cb.stateChanged.disconnect(
                    mw.view_management_controller.update_curve_view_options
                )
            if mw.show_grid_cb is not None:
                _ = mw.show_grid_cb.stateChanged.disconnect(mw.view_management_controller.update_curve_view_options)
            if mw.show_info_cb is not None:
                _ = mw.show_info_cb.stateChanged.disconnect(mw.view_management_controller.update_curve_view_options)
            if mw.show_tooltips_cb is not None:
                _ = mw.show_tooltips_cb.stateChanged.disconnect(mw.view_management_controller.toggle_tooltips)
            if mw.point_size_slider is not None:
                _ = mw.point_size_slider.valueChanged.disconnect(mw.view_management_controller.update_curve_point_size)
            if mw.line_width_slider is not None:
                _ = mw.line_width_slider.valueChanged.disconnect(mw.view_management_controller.update_curve_line_width)
        except (RuntimeError, AttributeError):
            pass  # Already disconnected or objects destroyed

    def connect_all_signals(self) -> None:
        """Connect all signals in the correct order."""
        self._connect_file_operations_signals()
        self._connect_signals()
        self._connect_store_signals()

        # Connect curve widget signals (after all UI components are created)
        if self.main_window.curve_widget:
            self._connect_curve_widget_signals()

        # Connect frame change coordinator (replaces 6 independent frame_changed connections)
        self.main_window.frame_change_coordinator.connect()
        logger.info("FrameChangeCoordinator wired")

        # Verify all critical connections (fail-loud mechanism)
        self._verify_connections()

        logger.info("All signal connections established")

    def _connect_file_operations_signals(self) -> None:
        """Connect signals from file operations manager."""
        # Connect file loading signals
        _ = self.main_window.file_operations.tracking_data_loaded.connect(self.main_window.on_tracking_data_loaded)
        _ = self.main_window.file_operations.multi_point_data_loaded.connect(
            self.main_window.on_multi_point_data_loaded
        )
        _ = self.main_window.file_operations.image_sequence_loaded.connect(
            self.main_window.view_management_controller.on_image_sequence_loaded
        )
        _ = self.main_window.file_operations.progress_updated.connect(self.main_window.on_file_load_progress)
        _ = self.main_window.file_operations.error_occurred.connect(self.main_window.on_file_load_error)
        _ = self.main_window.file_operations.finished.connect(self.main_window.on_file_load_finished)

        # Connect file operation status signals
        _ = self.main_window.file_operations.file_loaded.connect(self.main_window.on_file_loaded)
        _ = self.main_window.file_operations.file_saved.connect(self.main_window.on_file_saved)

        logger.info("Connected file operations signals")

    def _connect_signals(self) -> None:
        """Connect signals from state manager and shortcuts."""
        # Connect state manager signals
        _ = self.main_window.state_manager.file_changed.connect(self.main_window.on_file_changed)
        _ = self.main_window.state_manager.modified_changed.connect(self.main_window.on_modified_changed)
        _ = self.main_window.state_manager.selection_changed.connect(self.main_window.on_selection_changed)
        _ = self.main_window.state_manager.view_state_changed.connect(self.main_window.on_view_state_changed)

        # Connect total_frames_changed to update timeline range
        _ = self.main_window.state_manager.total_frames_changed.connect(
            lambda total: self.main_window.timeline_controller.set_frame_range(1, total)
        )

        # Connect timeline_tabs to StateManager as observer
        if self.main_window.timeline_tabs:
            self.main_window.timeline_tabs.set_state_manager(self.main_window.state_manager)

        # Connect timeline controller signals (unified playback and navigation)
        # REMOVED: timeline_controller.frame_changed connection to dead code
        # TimelineController no longer emits frame_changed (redundant with ApplicationState)
        # All frame change handling via ApplicationState → StateManager → FrameChangeCoordinator
        _ = self.main_window.timeline_controller.status_message.connect(self.main_window.update_status)

        # NOTE: timeline_tabs.frame_changed connection REMOVED to prevent circular signal flow
        # With StateManager as single source of truth, timeline_tabs delegates frame changes
        # through StateManager, eliminating need for this connection

    def _connect_store_signals(self) -> None:
        """Connect to ApplicationState signals for automatic updates."""
        # Phase 6.3: CurveDataStore removed, using ApplicationState directly
        # ApplicationState signals now handle all state synchronization
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Connect to curves_changed signal to update status label when curve data modified
        # (e.g., E key toggle ENDFRAME, smooth operations, etc.)
        _ = app_state.curves_changed.connect(
            self.main_window.update_point_status_label,
            Qt.QueuedConnection,  # pyright: ignore[reportAttributeAccessIssue]
        )

        # Connect to active_curve_changed to update status label when switching curves
        _ = app_state.active_curve_changed.connect(
            self._on_active_curve_changed_update_status,
            Qt.QueuedConnection,  # pyright: ignore[reportAttributeAccessIssue]
        )

        # Connect FrameStore.frame_range_changed to TimelineController.set_frame_range
        # This ensures timeline spinbox/slider maximums update when curve data loads
        from stores import get_store_manager

        frame_store = get_store_manager().frame_store
        _ = frame_store.frame_range_changed.connect(
            self.main_window.timeline_controller.set_frame_range
        )

        logger.info("Connected ApplicationState signals for status label updates")

    def _on_active_curve_changed_update_status(self, _curve_name: str) -> None:
        """Handle active curve change by updating status label (ignores curve name)."""
        self.main_window.update_point_status_label()

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

        # Phase 6.3: CurveDataStore connections removed (migrated to ApplicationState)

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
