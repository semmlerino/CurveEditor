#!/usr/bin/env python
"""
TrackingSelectionController - Handles selection synchronization.

Part of the MultiPointTrackingController split (PLAN TAU Phase 3 Task 3.1).
"""

from PySide6.QtCore import QObject, QTimer, Slot

from core.logger_utils import get_logger
from protocols.ui import MainWindowProtocol
from stores.application_state import ApplicationState, get_application_state

logger = get_logger("tracking_selection_controller")


class TrackingSelectionController(QObject):
    """Handles selection synchronization between panel and view.

    Responsibilities:
        - Sync panel selection → curve view
        - Sync curve view selection → panel
        - Handle selection change events
        - Auto-select points at current frame
    """

    def __init__(self, main_window: MainWindowProtocol) -> None:
        """Initialize tracking selection controller.

        Args:
            main_window: Main window protocol interface
        """
        super().__init__()
        self.main_window = main_window
        self._app_state: ApplicationState = get_application_state()

        logger.info("TrackingSelectionController initialized")

    @Slot(str, list)
    def on_data_loaded(self, curve_name: str, _curve_data: list[object]) -> None:
        """Handle data loaded signal - auto-select point at current frame.

        Args:
            curve_name: Name of the loaded curve
            _curve_data: The loaded curve data (unused)
        """
        # AUTO-SELECT point at current frame for immediate superior selection experience
        self._auto_select_point_at_current_frame()

    def _auto_select_point_at_current_frame(self) -> None:
        """Auto-select the point at the current frame.

        If no point exists at current frame, select the first point as fallback.
        """
        if not self.main_window.curve_widget:
            return

        # Get current frame from ApplicationState
        try:
            current_frame = get_application_state().current_frame
        except AttributeError:
            current_frame = 1  # Default fallback

        # Try to find and select the point at current frame
        curve_data = self.main_window.curve_widget.curve_data
        if curve_data:
            # Look for point at current frame
            # Get active curve name
            active_curve = self._app_state.active_curve

            if not active_curve:
                return

            for i, point in enumerate(curve_data):
                frame = point[0]  # First element is frame number
                if frame == current_frame:
                    # Found point at current frame - select it via ApplicationState
                    self._app_state.set_selection(active_curve, {i})
                    logger.debug(f"Auto-selected point at frame {current_frame} (index {i})")
                    return

            # No point at current frame - select first point as fallback
            if len(curve_data) > 0:
                self._app_state.set_selection(active_curve, {0})
                logger.debug(f"No point at frame {current_frame}, auto-selected first point (index 0)")

    def _sync_tracking_selection_to_curve_store(self, point_names: list[str]) -> None:
        """Synchronize TrackingPanel selection to CurveDataStore selection state.

        This fixes the TrackingPanel→CurveDataStore gap by ensuring manual selections
        in the tracking panel are reflected in the curve store's selection state.

        Args:
            point_names: List of selected point names from TrackingPanel
        """
        if not self.main_window.curve_widget or not point_names:
            return

        # Get the active curve (last selected point)
        active_curve_name = point_names[-1] if point_names else None
        if not active_curve_name or active_curve_name not in self._app_state.get_all_curve_names():
            return

        # Get current frame to find the appropriate point to select
        try:
            current_frame = get_application_state().current_frame
        except AttributeError:
            current_frame = 1  # Default fallback

        # Find the point at the current frame in the active curve
        curve_data = self._app_state.get_curve_data(active_curve_name)
        for i, point in enumerate(curve_data):
            frame = point[0]
            if frame == current_frame:
                # Select this point via ApplicationState
                self._app_state.set_selection(active_curve_name, {i})
                logger.debug(f"Synced TrackingPanel selection to ApplicationState: point {i} at frame {frame}")
                return

        # If no point at current frame, select the first point as fallback
        if len(curve_data) > 0:
            self._app_state.set_selection(active_curve_name, {0})
            logger.debug("Synced TrackingPanel selection to ApplicationState: fallback to first point (index 0)")

    def on_tracking_points_selected(self, point_names: list[str], display_controller: object) -> None:
        """Handle selection of tracking points from panel.

        Args:
            point_names: List of selected point names (for multi-selection in panel)
            display_controller: Reference to TrackingDisplayController for updates
        """
        # Import here to avoid circular dependency at module level
        from ui.controllers.tracking_display_controller import TrackingDisplayController

        display_ctrl = display_controller
        if not isinstance(display_ctrl, TrackingDisplayController):
            logger.error("Invalid display_controller type")
            return

        # Set the last selected point as the active timeline point (last clicked becomes active)
        # Note: point_names can be multiple for visual selection, but only one is "active" for timeline
        self.main_window.active_timeline_point = point_names[-1] if point_names else None

        # REMOVED: Synchronization loop (Phase 5.1)
        # TrackingPanel already updates ApplicationState directly (Phase 2)
        # No need to call set_selected_points() back to panel (causes race condition)

        # Synchronize selection state to CurveDataStore (fix TrackingPanel→CurveDataStore gap)
        self._sync_tracking_selection_to_curve_store(point_names)

        # Update the curve display with explicit selection to preserve user selection intent
        display_ctrl.update_display_with_selection(point_names)

        # Center view on selected point at current frame
        # Small delay to ensure curve data and point selection are processed
        if self.main_window.curve_widget and point_names:
            if callable(getattr(self.main_window.curve_widget, "center_on_selection", None)):
                # Use small delay to allow widget updates to complete
                def safe_center_on_selection() -> None:
                    if self.main_window.curve_widget and not self.main_window.curve_widget.isHidden():
                        self.main_window.curve_widget.center_on_selection()

                QTimer.singleShot(10, safe_center_on_selection)  # pyright: ignore[reportUnknownMemberType]
                logger.debug("Scheduled centering on selected point after 10ms delay")

        logger.debug(f"Selected tracking points: {point_names}")

    def on_curve_selection_changed(self, selection: set[int], curve_name: str | None = None) -> None:
        """Handle selection changes from CurveDataStore (bidirectional synchronization).

        This provides visual feedback in the tracking panel when point selection changes
        in the curve view, completing the bidirectional sync between systems.

        Phase 4: Removed __default__ special handling - use curve_name or active_timeline_point.

        Args:
            selection: Set of selected point indices from CurveDataStore
            curve_name: Name of curve with selection change (None uses active_timeline_point)
        """
        if not self.main_window.tracking_panel:
            return

        # If no selection, clear TrackingPanel selection
        if not selection:
            self.main_window.tracking_panel.set_selected_points([])
            return

        # Use explicit curve_name or fallback to active_timeline_point
        active_curve_name = curve_name if curve_name else self.main_window.active_timeline_point

        if active_curve_name and active_curve_name in self._app_state.get_all_curve_names():
            # Update TrackingPanel to highlight the curve that contains the selected points
            # This bridges point-level selection (CurveDataStore) with curve-level selection (TrackingPanel)
            selected_curves = [active_curve_name]

            # Ensure active_timeline_point is set (it should already be, but verify consistency)
            if not self.main_window.active_timeline_point:
                self.main_window.active_timeline_point = active_curve_name

            # Update TrackingPanel visual state
            self.main_window.tracking_panel.set_selected_points(selected_curves)

            logger.debug(
                f"Updated tracking panel for curve selection: {len(selection)} points selected in '{active_curve_name}'"
            )
        else:
            logger.debug(f"Could not determine curve for selection: {len(selection)} points selected, no active curve")
