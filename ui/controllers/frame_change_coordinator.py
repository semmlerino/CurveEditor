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
        from ui.curve_view_widget import CurveViewWidget
        from ui.protocols.controller_protocols import TimelineControllerProtocol
        from ui.timeline_tabs import TimelineTabWidget

        self.main_window: MainWindow = main_window
        self.curve_widget: CurveViewWidget | None = main_window.curve_widget
        self.view_management: ViewManagementController = main_window.view_management_controller  # pyright: ignore[reportAttributeAccessIssue]
        self.timeline_controller: TimelineControllerProtocol = main_window.timeline_controller
        self.timeline_tabs: TimelineTabWidget | None = main_window.timeline_tabs

    def __del__(self) -> None:
        """Ensure signal disconnection during object destruction.

        FrameChangeCoordinator has 1 signal connection to StateManager.frame_changed.
        The disconnect() method already handles cleanup, but __del__ ensures it's
        called during object destruction to prevent memory leaks.
        """
        self.disconnect()

    def connect(self) -> None:
        """Connect to state manager frame_changed signal (idempotent).

        Prevents duplicate connections - disconnect first if already connected.
        Qt allows multiple connections to same slot without error, leading to
        2x-3x update() calls per frame change (existing bug in StateSyncController).
        """
        # Prevent duplicate connections - disconnect first if already connected
        try:
            _ = self.main_window.state_manager.frame_changed.disconnect(self.on_frame_changed)
        except (RuntimeError, TypeError):
            pass  # Not connected yet, that's expected on first call

        # Now connect (guaranteed single connection)
        _ = self.main_window.state_manager.frame_changed.connect(self.on_frame_changed)
        logger.info("FrameChangeCoordinator connected")

    def disconnect(self) -> None:
        """Disconnect from state manager (cleanup)."""
        try:
            _ = self.main_window.state_manager.frame_changed.disconnect(self.on_frame_changed)
            logger.info("FrameChangeCoordinator disconnected")
        except (RuntimeError, TypeError):
            # Signal already disconnected or connection never made
            pass

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
        logger.debug(f"[FRAME-COORDINATOR] Frame changed to {frame}")

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
            logger.debug(f"[FRAME-COORDINATOR] Background updated for frame {frame}")

    def _apply_centering(self, frame: int) -> None:
        """Apply centering if centering mode is enabled."""
        if self.curve_widget and self.curve_widget.centering_mode:
            self.curve_widget.center_on_frame(frame)
            logger.debug(f"[FRAME-COORDINATOR] Centering applied for frame {frame}")

    def _invalidate_caches(self) -> None:
        """Invalidate render caches to prepare for repaint."""
        if self.curve_widget:
            self.curve_widget.invalidate_caches()
            logger.debug("[FRAME-COORDINATOR] Caches invalidated")

    def _update_timeline_widgets(self, frame: int) -> None:
        """Update timeline widgets (spinbox, slider, tabs)."""
        # Update timeline controller (spinbox/slider)
        if self.timeline_controller:
            self.timeline_controller.update_frame_display(frame, update_state=False)

        # Update timeline tabs (visual updates only, don't set state)
        # Note: _on_frame_changed is internal to TimelineTabWidget but safe to call
        # from coordinator as it only updates visual state without triggering signals
        if self.timeline_tabs:
            self.timeline_tabs._on_frame_changed(frame)  # pyright: ignore[reportPrivateUsage]

        logger.debug(f"[FRAME-COORDINATOR] Timeline widgets updated for frame {frame}")

    def _trigger_repaint(self) -> None:
        """Trigger single repaint with all state applied."""
        if self.curve_widget:
            self.curve_widget.update()
            logger.debug("[FRAME-COORDINATOR] Repaint triggered")
