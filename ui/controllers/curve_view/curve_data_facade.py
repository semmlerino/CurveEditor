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
        self._curve_store = widget._curve_store
        self._app_state = get_application_state()

        logger.debug("CurveDataFacade initialized")

    # ==================== Single-Curve Operations ====================

    def set_curve_data(self, data: CurveDataInput) -> None:
        """
        Set the curve data to display.

        Maintains backward compatibility by updating both CurveDataStore and ApplicationState.
        The "__default__" curve name is used for single-curve operations.

        Args:
            data: List of point tuples (frame, x, y, [status])
        """
        # Delegate to store - it will emit signals that trigger widget updates
        self._curve_store.set_data(data)
        logger.debug(f"Set curve data with {len(data)} points via CurveDataStore")

        # BACKWARD COMPATIBILITY: Also update ApplicationState with default curve name
        # This ensures single-curve tests/code work with ApplicationState-based features
        default_curve_name = "__default__"
        self._app_state.set_curve_data(default_curve_name, data)
        if not self._app_state.active_curve:
            self._app_state.set_active_curve(default_curve_name)
        logger.debug(f"Synced single-curve data to ApplicationState as '{default_curve_name}'")

    def add_point(self, point: tuple[int, float, float] | tuple[int, float, float, str]) -> None:
        """
        Add a single point to the curve.

        Args:
            point: Point tuple (frame, x, y, [status])
        """
        # Delegate to store - it will emit signals that trigger widget updates
        self._curve_store.add_point(point)

    def update_point(self, index: int, x: float, y: float) -> None:
        """
        Update coordinates of a point.

        Args:
            index: Point index
            x: New X coordinate
            y: New Y coordinate
        """
        # Delegate to store - it will emit signals that trigger widget updates
        self._curve_store.update_point(index, x, y)

    def remove_point(self, index: int) -> None:
        """
        Remove a point from the curve.

        Args:
            index: Point index to remove
        """
        # Delegate to store - it will emit signals that trigger widget updates
        # Store handles selection updates automatically
        self._curve_store.remove_point(index)

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

        Args:
            name: Name of the curve to make active
        """
        # Check if curve exists in ApplicationState
        all_curves = self._app_state.get_all_curve_names()
        if name in all_curves:
            self._app_state.set_active_curve(name)
            # Update the single curve store for backward compatibility
            curve_data = self._app_state.get_curve_data(name)
            self._curve_store.set_data(curve_data)
            logger.debug(f"Set active curve to '{name}' in ApplicationState")

            # Auto-center on the current frame if centering mode is active
            if self.widget.centering_mode:
                if self.widget.main_window and getattr(self.widget.main_window, "current_frame", None) is not None:
                    current_frame = self.widget.main_window.current_frame  # pyright: ignore[reportAttributeAccessIssue]
                    logger.debug(
                        f"[CENTERING] Auto-centering on frame {current_frame} for newly selected curve '{name}'"
                    )
                    self.widget.center_on_frame(current_frame)
