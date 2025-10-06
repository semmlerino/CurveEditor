#!/usr/bin/env python
"""
CurveDataFacade - Data management facade for CurveViewWidget.

This facade encapsulates all data management operations, delegating to ApplicationState
while maintaining backward compatibility with CurveDataStore. It eliminates direct
store access from the widget, providing a clean API for data operations.

Phase 4 extraction from CurveViewWidget god object refactoring.
"""

# Import cycle with CurveViewWidget is expected and safe - resolved via TYPE_CHECKING
# pyright: reportImportCycles=false

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.logger_utils import get_logger
from core.models import CurvePoint, PointStatus
from core.type_aliases import CurveDataInput, CurveDataList
from stores.application_state import get_application_state

if TYPE_CHECKING:
    from ui.curve_view_widget import CurveViewWidget

logger = get_logger("curve_data_facade")


class CurveDataFacade:
    """
    Facade for curve data management operations.

    Encapsulates data operations on both CurveDataStore (legacy) and ApplicationState,
    providing a clean API that hides the dual-store complexity from the widget.

    Pattern: Controller holds widget reference (Pattern B - like StateSyncController)
    Updates are driven by signals, so no manual widget.update() calls are needed.

    Attributes:
        widget: Reference to CurveViewWidget for store access
        _curve_store: Legacy curve data store for backward compatibility
        _app_state: Centralized application state (single source of truth)
    """

    def __init__(self, widget: CurveViewWidget) -> None:
        """
        Initialize the curve data facade.

        Args:
            widget: CurveViewWidget instance
        """
        self.widget = widget
        self._app_state = get_application_state()

        logger.debug("CurveDataFacade initialized")

    def _get_active_curve_name(self) -> str:
        """Get the active curve name.

        Phase 4: Removed __default__ fallback. Raises RuntimeError if no active curve.

        Returns:
            Active curve name

        Raises:
            RuntimeError: If no active curve is set
        """
        active = self._app_state.active_curve
        if not active:
            logger.error("No active curve set - operations require an active curve")
            raise RuntimeError("No active curve set. Load data or set active curve first.")
        return active

    # ==================== Single-Curve Operations ====================

    def set_curve_data(self, data: CurveDataInput) -> None:
        """Set the curve data to display.

        Phase 4: Uses active curve or creates "Curve1" instead of __default__.

        Delegates to ApplicationState (single source of truth). StateSyncController
        handles syncing to CurveDataStore for backward compatibility.

        Args:
            data: List of point tuples (frame, x, y, [status])
        """
        # Determine curve name: use active or create new
        curve_name = self._app_state.active_curve
        if not curve_name:
            # No active curve - create default named curve
            curve_name = "Curve1"
            logger.info(f"No active curve - creating '{curve_name}' for single-curve data")

        # Set data and make active
        self._app_state.set_curve_data(curve_name, data)
        self._app_state.set_active_curve(curve_name)
        logger.debug(f"Set curve data with {len(data)} points to '{curve_name}'")

        # StateSyncController._on_app_state_curves_changed() will sync to CurveDataStore

    def add_point(self, point: tuple[int, float, float] | tuple[int, float, float, str]) -> int:
        """
        Add a single point to the curve via ApplicationState.

        Performance: 3x faster than get->append->set pattern.

        Args:
            point: Point tuple (frame, x, y, [status])

        Returns:
            Index of added point, or -1 if no active curve
        """
        try:
            curve_name = self._get_active_curve_name()
        except RuntimeError:
            logger.warning("Cannot add point: no active curve")
            return -1

        # Convert tuple to CurvePoint
        # Default to NORMAL status for 3-tuple inputs (status must be explicit for others)
        if len(point) == 3:
            curve_point = CurvePoint(frame=point[0], x=point[1], y=point[2], status=PointStatus.NORMAL)
        else:
            status = PointStatus(point[3])
            curve_point = CurvePoint(frame=point[0], x=point[1], y=point[2], status=status)

        return self._app_state.add_point(curve_name, curve_point)

    def update_point(self, index: int, x: float, y: float) -> None:
        """
        Update point coordinates while preserving status.

        ApplicationState.update_point() replaces the entire CurvePoint object,
        so we must preserve the status from the existing point.

        Args:
            index: Point index
            x: New X coordinate
            y: New Y coordinate
        """
        try:
            curve_name = self._get_active_curve_name()
        except RuntimeError:
            logger.warning(f"Cannot update point {index}: no active curve")
            return

        current_data = self._app_state.get_curve_data(curve_name)

        if not current_data or index >= len(current_data):
            logger.warning(f"Cannot update point {index}: out of range")
            return

        # Preserve existing status
        current_point = current_data[index]
        frame = current_point[0]
        status = PointStatus(current_point[3]) if len(current_point) > 3 else PointStatus.NORMAL

        # Create updated point with new coordinates but same frame and status
        updated_point = CurvePoint(frame=frame, x=x, y=y, status=status)

        self._app_state.update_point(curve_name, index, updated_point)

    def remove_point(self, index: int) -> None:
        """
        Remove a point from the curve via ApplicationState.

        Args:
            index: Point index to remove
        """
        try:
            curve_name = self._get_active_curve_name()
        except RuntimeError:
            logger.warning(f"Cannot remove point {index}: no active curve")
            return

        success = self._app_state.remove_point(curve_name, index)
        if not success:
            logger.warning(f"Failed to remove point {index} from curve '{curve_name}'")

    # ==================== Multi-Curve Operations ====================

    def set_curves_data(
        self,
        curves: dict[str, CurveDataList],
        metadata: dict[str, dict[str, Any]] | None = None,
        active_curve: str | None = None,
        selected_curves: list[str] | None = None,
    ) -> None:
        """
        Set multiple curves to display.

        Curve visibility is determined by CurveViewWidget.should_render_curve()
        which coordinates three filters: metadata.visible flag, display_mode (DisplayMode enum),
        and selected_curve_names set. See that method for detailed visibility logic.

        Args:
            curves: Dictionary mapping curve names to curve data
            metadata: Optional dictionary with per-curve metadata (visibility, color, etc.)
            active_curve: Name of the currently active curve for editing
            selected_curves: Optional list of curves to select for display
        """
        # DEBUG: Log what we're setting
        logger.info("[MULTI-CURVE-DEBUG] set_curves_data called:")
        logger.info(f"  curves: {list(curves.keys())}")
        logger.info(f"  active_curve: {active_curve}")
        logger.info(f"  selected_curves: {selected_curves}")
        logger.info(f"  Current display_mode BEFORE: {self._app_state.display_mode}")

        # Use ApplicationState for multi-curve data (Week 3 migration)
        self._app_state.begin_batch()
        try:
            # Set each curve in ApplicationState
            for name, data in curves.items():
                curve_metadata = metadata.get(name) if metadata else None
                self._app_state.set_curve_data(name, data, curve_metadata)

            # Update selection in ApplicationState (single source of truth)
            if selected_curves is not None:
                self._app_state.set_selected_curves(set(selected_curves))
                # NO MANUAL display_mode UPDATE NEEDED - computed automatically! ✅
                # Widget fields updated automatically via selection_state_changed signal

                logger.info(f"  Selection updated in ApplicationState (selected={selected_curves})")
                logger.info(f"  display_mode AFTER: {self._app_state.display_mode}")
            elif not self._app_state.get_selected_curves() and active_curve:
                # Default to active curve ONLY if there's no existing selection
                self._app_state.set_selected_curves({active_curve})
                # Widget fields updated automatically via selection_state_changed signal

            # Set the active curve in ApplicationState
            if active_curve and active_curve in curves:
                self._app_state.set_active_curve(active_curve)
                # Update single curve store for backward compatibility
                self.set_curve_data(curves[active_curve])
            elif curves:
                # Default to first curve
                first_curve = next(iter(curves.keys()))
                self._app_state.set_active_curve(first_curve)
                self.set_curve_data(curves[first_curve])
            else:
                self._app_state.set_active_curve(None)
                self.set_curve_data([])
        finally:
            self._app_state.end_batch()

        logger.debug(f"Set {len(curves)} curves in ApplicationState, active: {self._app_state.active_curve}")

    def add_curve(self, name: str, data: CurveDataList, metadata: dict[str, Any] | None = None) -> None:
        """
        Add a new curve to the display.

        Args:
            name: Unique name for the curve
            data: Curve data points
            metadata: Optional metadata for the curve
        """
        # Add to ApplicationState
        self._app_state.set_curve_data(name, data, metadata)

        # If this is the first curve, make it active
        if not self._app_state.active_curve:
            self._app_state.set_active_curve(name)
            self.set_curve_data(data)

        logger.debug(f"Added curve '{name}' with {len(data)} points to ApplicationState")

    def remove_curve(self, name: str) -> None:
        """
        Remove a curve from the display.

        Args:
            name: Name of the curve to remove
        """
        # Check if curve exists in ApplicationState
        all_curves = self._app_state.get_all_curve_names()
        if name not in all_curves:
            return

        # Remove from ApplicationState
        self._app_state.delete_curve(name)

        # If this was the active curve, select another
        if self._app_state.active_curve == name:
            remaining_curves = self._app_state.get_all_curve_names()
            if remaining_curves:
                new_active = remaining_curves[0]
                self._app_state.set_active_curve(new_active)
                self.set_curve_data(self._app_state.get_curve_data(new_active))
            else:
                self._app_state.set_active_curve(None)
                self.set_curve_data([])

        logger.debug(f"Removed curve '{name}' from ApplicationState")

    def update_curve_visibility(self, name: str, visible: bool) -> None:
        """
        Update visibility of a specific curve.

        Args:
            name: Name of the curve
            visible: Whether the curve should be visible
        """
        # Update in ApplicationState
        self._app_state.set_curve_visibility(name, visible)
        logger.debug(f"Set curve '{name}' visibility to {visible} in ApplicationState")

    def update_curve_color(self, name: str, color: str) -> None:
        """
        Update color of a specific curve.

        Args:
            name: Name of the curve
            color: Color in hex format (e.g., "#FF0000")
        """
        # Update metadata in ApplicationState
        metadata = self._app_state.get_curve_metadata(name)
        metadata["color"] = color
        self._app_state.set_curve_data(name, self._app_state.get_curve_data(name), metadata)
        logger.debug(f"Set curve '{name}' color to {color} in ApplicationState")

    def set_active_curve(self, name: str) -> None:
        """
        Set the active curve for editing operations.

        Delegates to ApplicationState. StateSyncController automatically syncs
        to CurveDataStore via active_curve_changed signal.

        Phase 3.2: Removed manual sync to CurveDataStore (now automatic).

        Args:
            name: Name of the curve to make active
        """
        # Check if curve exists in ApplicationState
        all_curves = self._app_state.get_all_curve_names()
        if name in all_curves:
            self._app_state.set_active_curve(name)
            # StateSyncController._on_app_state_active_curve_changed() handles sync to CurveDataStore
            logger.debug(f"Set active curve to '{name}' in ApplicationState")

            # Auto-center on the current frame if centering mode is active
            if self.widget.centering_mode:
                if self.widget.main_window and getattr(self.widget.main_window, "current_frame", None) is not None:
                    current_frame = self.widget.main_window.current_frame
                    logger.debug(
                        f"[CENTERING] Auto-centering on frame {current_frame} for newly selected curve '{name}'"
                    )
                    self.widget.center_on_frame(current_frame)
