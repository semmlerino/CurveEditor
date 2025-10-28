# pyright: reportImportCycles=false
"""
FrameChangeCoordinator - Coordinates all frame change responses.

This controller ensures frame changes happen atomically:
1. All state updates complete before any paint events
2. Updates happen in deterministic order
3. Only one repaint after all updates

Design:
    The coordinator eliminates race conditions from non-deterministic Qt signal
    ordering by enforcing explicit phase ordering:

    Phase 1: Pre-paint State Updates
        - Load background image (affects viewport calculations)
        - Apply centering (updates pan_offset based on frame position)
        - Invalidate render caches (prepares for fresh render)

    Phase 2: Widget Updates (no repaints)
        - Update timeline controls (spinbox/slider display)
        - Update timeline tabs (visual state only)

    Phase 3: Single Repaint
        - Trigger one update() call with all state applied

Why This Matters:
    Without coordination, Qt may execute signal handlers in any order.
    Background loading might happen AFTER centering, causing the centering
    calculation to use old background dimensions. This manifests as visual
    jumps during playback with background images and centering mode enabled.

    The coordinator makes the order explicit and deterministic, eliminating
    timing-dependent bugs that tests can't reliably catch.

Usage:
    coordinator = FrameChangeCoordinator(main_window)
    coordinator.connect()  # Replaces 6 independent frame_changed connections
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.logger_utils import get_logger

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = get_logger("frame_change_coordinator")


class FrameChangeCoordinator:
    """
    Coordinates all responses to frame changes.

    Ensures atomic updates: all state changes complete before any paint.
    """

    def __init__(self, main_window: MainWindow):
        """
        Initialize FrameChangeCoordinator.

        Args:
            main_window: Main window instance providing access to all controllers
        """
        from ui.controllers.view_management_controller import ViewManagementController
        from ui.protocols.controller_protocols import TimelineControllerProtocol
        from ui.timeline_tabs import TimelineTabWidget

        self.main_window: MainWindow = main_window
        # NOTE: Don't cache curve_widget reference - it's created AFTER coordinator
        # Use property to access main_window.curve_widget dynamically
        self.view_management: ViewManagementController = main_window.view_management_controller  # pyright: ignore[reportAttributeAccessIssue]
        self.timeline_controller: TimelineControllerProtocol = main_window.timeline_controller
        self.timeline_tabs: TimelineTabWidget | None = main_window.timeline_tabs
        self._connected: bool = False  # Track connection state to prevent Qt warnings
        self._curve_change_connected: bool = False  # Track active_curve_changed connection

    @property
    def curve_widget(self):
        """Get curve widget from main window (created after coordinator)."""
        from ui.curve_view_widget import CurveViewWidget

        widget = self.main_window.curve_widget
        return widget if isinstance(widget, CurveViewWidget) else None

    def __del__(self) -> None:
        """Ensure signal disconnection during object destruction.

        FrameChangeCoordinator has 1 signal connection to StateManager.frame_changed.
        The disconnect() method already handles cleanup, but __del__ ensures it's
        called during object destruction to prevent memory leaks.
        """
        self.disconnect()

    def connect(self) -> None:
        """Connect to state manager signals (idempotent).

        Connects to both frame_changed and active_curve_changed for auto-centering.

        Prevents duplicate connections - disconnect first if already connected.
        Qt allows multiple connections to same slot without error, leading to
        2x-3x update() calls per frame change (existing bug in StateSyncController).

        Uses Qt.QueuedConnection to break synchronous nested execution that causes
        timeline-curve desynchronization. With deferred execution, coordinator runs
        AFTER input handler completes, preventing widget state machine confusion.
        """
        from PySide6.QtCore import Qt
        from stores.application_state import get_application_state

        # Guard: Already connected, return early for idempotency
        if self._connected:
            logger.debug("FrameChangeCoordinator.connect() called but already connected (idempotent)")
            return

        # No need to disconnect if not already connected (_connected is False here)
        # Attempting disconnect on unconnected signal causes Qt RuntimeWarning

        # Connect to frame_changed with QueuedConnection to defer execution
        # This breaks the synchronous nested execution that causes timeline desync bugs
        _ = self.main_window.state_manager.frame_changed.connect(
            self.on_frame_changed,
            Qt.QueuedConnection,  # pyright: ignore[reportAttributeAccessIssue]  # Defers coordinator execution, prevents nested calls
        )
        self._connected = True

        # Connect to active_curve_changed for centering when switching curves
        app_state = get_application_state()
        _ = app_state.active_curve_changed.connect(
            self.on_active_curve_changed,
            Qt.QueuedConnection,  # pyright: ignore[reportAttributeAccessIssue]
        )
        self._curve_change_connected = True

        logger.info("FrameChangeCoordinator connected to frame_changed and active_curve_changed")

    def disconnect(self) -> None:
        """Disconnect from state manager and ApplicationState (cleanup)."""
        from stores.application_state import get_application_state

        # Disconnect frame_changed
        if self._connected:
            try:
                _ = self.main_window.state_manager.frame_changed.disconnect(self.on_frame_changed)
                self._connected = False
                logger.debug("Disconnected from frame_changed")
            except (RuntimeError, TypeError):
                # Signal already disconnected or connection never made
                self._connected = False

        # Disconnect active_curve_changed
        if self._curve_change_connected:
            try:
                app_state = get_application_state()
                _ = app_state.active_curve_changed.disconnect(self.on_active_curve_changed)
                self._curve_change_connected = False
                logger.debug("Disconnected from active_curve_changed")
            except (RuntimeError, TypeError):
                # Signal already disconnected or connection never made
                self._curve_change_connected = False

        if not self._connected and not self._curve_change_connected:
            logger.info("FrameChangeCoordinator fully disconnected")

    def on_frame_changed(self, frame: int) -> None:
        """
        Handle frame change with coordinated updates.

        All phases execute even if individual operations fail (atomic guarantee).
        Errors are logged but don't prevent remaining phases from executing.

        Order is critical:
        1. Background image (affects rendering viewport)
        2. Centering (updates pan_offset based on frame position)
        3. Cache invalidation (prepares for render)
        4. Widget updates (no repaints)
        5. Single repaint (with all state applied)

        Args:
            frame: New frame number
        """
        errors: list[str] = []

        # Phase 1: Pre-paint state updates (all must attempt even if one fails)
        try:
            self._update_background(frame)
        except Exception as e:
            errors.append(f"background: {e}")
            logger.error(f"Background update failed for frame {frame}: {e}", exc_info=True)

        try:
            self._apply_centering(frame)
        except Exception as e:
            errors.append(f"centering: {e}")
            logger.error(f"Centering failed for frame {frame}: {e}", exc_info=True)

        try:
            self._invalidate_caches()
        except Exception as e:
            errors.append(f"cache: {e}")
            logger.error(f"Cache invalidation failed for frame {frame}: {e}", exc_info=True)

        # Phase 2: Widget updates
        try:
            self._update_timeline_widgets(frame)
        except Exception as e:
            errors.append(f"timeline: {e}")
            logger.error(f"Timeline widget update failed for frame {frame}: {e}", exc_info=True)

        # Phase 3: Single repaint (must always attempt, even if previous phases failed)
        try:
            self._trigger_repaint()
        except Exception as e:
            errors.append(f"repaint: {e}")
            logger.error(f"Repaint failed for frame {frame}: {e}", exc_info=True)

        if errors:
            logger.warning(f"Frame {frame} completed with {len(errors)} errors: {errors}")

    def _update_background(self, frame: int) -> None:
        """Update background image for frame (if images loaded)."""
        if self.view_management and self.view_management.image_filenames:
            self.view_management.update_background_for_frame(frame)

    def _apply_centering(self, frame: int) -> None:
        """Apply centering if centering mode is enabled."""
        if self.curve_widget and self.curve_widget.centering_mode:
            self.curve_widget.center_on_frame(frame)

    def on_active_curve_changed(self, curve_name: str | None) -> None:
        """
        Handle active curve change - center on current frame if centering mode enabled.

        This allows auto-centering when user clicks different curves in the tracking panel.

        Args:
            curve_name: New active curve name
        """
        # Only center if centering mode is enabled
        if not self.curve_widget or not self.curve_widget.centering_mode:
            return

        # Get current frame from state manager
        if not self.main_window.state_manager:
            return

        current_frame = self.main_window.state_manager.current_frame

        # Center on the current frame with the newly selected curve
        try:
            self._apply_centering(current_frame)
            logger.debug(f"Auto-centered on curve '{curve_name}' at frame {current_frame}")
        except Exception as e:
            logger.error(f"Failed to auto-center on curve change: {e}", exc_info=True)

    def _invalidate_caches(self) -> None:
        """Invalidate render caches to prepare for repaint."""
        if self.curve_widget:
            self.curve_widget.invalidate_caches()

    def _update_timeline_widgets(self, frame: int) -> None:
        """Update timeline widgets (spinbox, slider, tabs)."""
        # Update timeline controller (spinbox/slider)
        if self.timeline_controller:
            self.timeline_controller.update_frame_display(frame, update_state=False)

        # Update timeline tabs (visual updates only, don't set state)
        # Note: _on_frame_changed is internal to TimelineTabWidget but safe to call
        # from coordinator as it only updates visual state without triggering signals
        if self.timeline_tabs:
            self.timeline_tabs.on_frame_changed(frame)

        # Update point status label in status bar
        if self.main_window:
            self.main_window.update_point_status_label()

    def _trigger_repaint(self) -> None:
        """Trigger single repaint with all state applied."""
        if self.curve_widget:
            self.curve_widget.update()
