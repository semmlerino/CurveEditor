#!/usr/bin/env python
"""
Multi-Curve Manager for CurveViewWidget.

Extracted from CurveViewWidget to follow Single Responsibility Principle.
Manages multiple curve data, visibility, colors, and active curve selection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.display_mode import DisplayMode
from core.logger_utils import get_logger
from core.type_aliases import CurveDataList
from stores.application_state import get_application_state

if TYPE_CHECKING:
    from ui.curve_view_widget import CurveViewWidget

logger = get_logger("multi_curve_manager")


class MultiCurveManager:
    """
    Manages multiple curves for CurveViewWidget.

    Responsibilities:
    - Store and manage multiple named curves
    - Track curve metadata (visibility, color)
    - Manage active curve for editing
    - Handle curve selection for display
    """

    def __init__(self, widget: CurveViewWidget):
        """
        Initialize the multi-curve manager.

        Args:
            widget: Parent CurveViewWidget that owns this manager
        """
        self.widget = widget

        # ApplicationState integration (single source of truth)
        self._app_state = get_application_state()

        # VIEW-specific state only (not data)
        self.selected_curve_names: set[str] = set()

        logger.debug("MultiCurveManager initialized with ApplicationState")

    # ==================== Backward-Compatible Properties ====================
    # These delegate to ApplicationState for single source of truth

    @property
    def curves_data(self) -> dict[str, CurveDataList]:
        """Get all curves data from ApplicationState (backward compatibility)."""
        return {name: self._app_state.get_curve_data(name) for name in self._app_state.get_all_curve_names()}

    @property
    def curve_metadata(self) -> dict[str, dict[str, Any]]:
        """Get all curve metadata from ApplicationState (backward compatibility)."""
        return {name: self._app_state.get_curve_metadata(name) for name in self._app_state.get_all_curve_names()}

    @property
    def active_curve_name(self) -> str | None:
        """Get active curve from ApplicationState (backward compatibility)."""
        return self._app_state.active_curve

    @active_curve_name.setter
    def active_curve_name(self, value: str | None) -> None:
        """Set active curve in ApplicationState (backward compatibility)."""
        self._app_state.set_active_curve(value)

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

        Args:
            curves: Dictionary mapping curve names to curve data
            metadata: Optional dictionary with per-curve metadata (visibility, color, etc.)
            active_curve: Name of the currently active curve for editing
            selected_curves: Optional list of curves to select for display
        """
        # Use batch mode to prevent signal storms
        self._app_state.begin_batch()
        try:
            # Set all curve data in ApplicationState
            for name, data in curves.items():
                curve_metadata = metadata.get(name) if metadata else None
                self._app_state.set_curve_data(name, data, curve_metadata)

                # Set default metadata if not provided
                if not curve_metadata:
                    current_meta = self._app_state.get_curve_metadata(name)
                    if "visible" not in current_meta:
                        self._app_state.set_curve_visibility(name, True)

            # Update selected curves if specified
            if selected_curves is not None:
                self.selected_curve_names = set(selected_curves)
                # CRITICAL FIX: Update display mode to SELECTED when curves are selected
                # This fixes the bug where selecting multiple curves only shows one
                if selected_curves:
                    self.widget.display_mode = DisplayMode.SELECTED
            elif not self.selected_curve_names:
                # If no selection specified and no existing selection, default to active curve
                self.selected_curve_names = {active_curve} if active_curve else set()

            # Set the active curve
            if active_curve and active_curve in curves:
                self._app_state.set_active_curve(active_curve)
                # Update the single curve data for backward compatibility
                self.widget.set_curve_data(curves[active_curve])
            elif curves:
                # Default to first curve if no active curve specified
                first_curve = next(iter(curves.keys()))
                self._app_state.set_active_curve(first_curve)
                self.widget.set_curve_data(curves[first_curve])
            else:
                self._app_state.set_active_curve(None)
                self.widget.set_curve_data([])
        finally:
            self._app_state.end_batch()

        # Trigger repaint to show all curves
        self.widget.update()
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

        # Set default visibility if not provided
        if not metadata or "visible" not in metadata:
            self._app_state.set_curve_visibility(name, True)

        # If this is the first curve, make it active
        if not self._app_state.active_curve:
            self._app_state.set_active_curve(name)
            self.widget.set_curve_data(data)

        self.widget.update()
        logger.debug(f"Added curve '{name}' with {len(data)} points to ApplicationState")

    def remove_curve(self, name: str) -> None:
        """
        Remove a curve from the display.

        Args:
            name: Name of the curve to remove
        """
        # Check if curve exists in ApplicationState
        if name not in self._app_state.get_all_curve_names():
            return

        # Check if this is the active curve BEFORE deletion
        was_active = self._app_state.active_curve == name

        # Delete from ApplicationState (also removes metadata and selection)
        self._app_state.delete_curve(name)

        # If this was the active curve, select another
        if was_active:
            remaining_curves = self._app_state.get_all_curve_names()
            if remaining_curves:
                first_curve = remaining_curves[0]
                self._app_state.set_active_curve(first_curve)
                self.widget.set_curve_data(self._app_state.get_curve_data(first_curve))
            else:
                self._app_state.set_active_curve(None)
                self.widget.set_curve_data([])

        self.widget.update()
        logger.debug(f"Removed curve '{name}' from ApplicationState")

    def update_curve_visibility(self, name: str, visible: bool) -> None:
        """
        Update visibility of a specific curve.

        Args:
            name: Name of the curve
            visible: Whether the curve should be visible
        """
        if name in self._app_state.get_all_curve_names():
            self._app_state.set_curve_visibility(name, visible)
            self.widget.update()
            logger.debug(f"Set curve '{name}' visibility to {visible} in ApplicationState")

    def update_curve_color(self, name: str, color: str) -> None:
        """
        Update color of a specific curve.

        Args:
            name: Name of the curve
            color: Color in hex format (e.g., "#FF0000")
        """
        if name in self._app_state.get_all_curve_names():
            # Get current metadata, update color, save back
            metadata = self._app_state.get_curve_metadata(name)
            metadata["color"] = color
            # Update metadata via set_curve_data (re-set with updated metadata)
            data = self._app_state.get_curve_data(name)
            self._app_state.set_curve_data(name, data, metadata)
            self.widget.update()
            logger.debug(f"Set curve '{name}' color to {color} in ApplicationState")

    def set_active_curve(self, name: str) -> None:
        """
        Set the active curve for editing operations.

        Args:
            name: Name of the curve to make active
        """
        if name in self._app_state.get_all_curve_names():
            # Set in ApplicationState
            self._app_state.set_active_curve(name)

            # Update the single curve data for editing operations
            # This is needed for backward compatibility with editing tools
            curve_data = self._app_state.get_curve_data(name)
            self.widget._curve_store.set_data(curve_data)

            # Trigger display update to show the new active curve
            self.widget.update()
            logger.debug(f"Set active curve to '{name}' in ApplicationState")

            # Auto-center on the current frame if centering mode is active
            if self.widget.centering_mode:
                if self.widget.main_window and getattr(self.widget.main_window, "current_frame", None) is not None:
                    current_frame = self.widget.main_window.current_frame  # pyright: ignore[reportAttributeAccessIssue]
                    logger.debug(
                        f"[CENTERING] Auto-centering on frame {current_frame} for newly selected curve '{name}'"
                    )
                    self.widget.center_on_frame(current_frame)

    def set_selected_curves(self, curve_names: list[str]) -> None:
        """
        Set which curves are currently selected for display.

        In SELECTED display mode, only these selected curves will be displayed.
        The last curve in the list becomes the active curve for editing.

        Args:
            curve_names: List of curve names to select and display
        """
        self.selected_curve_names = set(curve_names)

        # Set the last selected as the active curve for editing
        if curve_names and curve_names[-1] in self._app_state.get_all_curve_names():
            self.set_active_curve(curve_names[-1])

        self.widget.update()
        logger.debug(f"Selected curves: {self.selected_curve_names}, Active: {self._app_state.active_curve}")

    def center_on_selected_curves(self) -> None:
        """
        Center the view on all selected curves.

        Calculates the bounding box of all selected curves and centers the view on it.
        """
        all_curve_names = self._app_state.get_all_curve_names()
        logger.debug(
            f"center_on_selected_curves called with selected: {self.selected_curve_names}, ApplicationState curves: {all_curve_names}"
        )
        if not self.selected_curve_names or not all_curve_names:
            logger.debug("Early return - no selected curves or no data in ApplicationState")
            return

        # Collect all points from selected curves (from ApplicationState)
        all_points: list[tuple[float, float]] = []
        for curve_name in self.selected_curve_names:
            if curve_name in all_curve_names:
                curve_data = self._app_state.get_curve_data(curve_name)
                logger.debug(f"Processing curve {curve_name} with {len(curve_data)} points from ApplicationState")
                for point in curve_data:
                    if len(point) >= 3:
                        all_points.append((float(point[1]), float(point[2])))

        if not all_points:
            logger.debug("No points found in selected curves")
            return
        logger.debug(f"Collected {len(all_points)} points for centering")

        # Calculate bounding box
        x_coords = [p[0] for p in all_points]
        y_coords = [p[1] for p in all_points]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        # Calculate center point
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Calculate required zoom to fit all points with some padding
        from ui.ui_constants import MAX_ZOOM_FACTOR, MIN_ZOOM_FACTOR

        padding_factor = 1.2
        width_needed = (max_x - min_x) * padding_factor
        height_needed = (max_y - min_y) * padding_factor

        if width_needed > 0 and height_needed > 0:
            zoom_x = self.widget.width() / width_needed
            zoom_y = self.widget.height() / height_needed
            optimal_zoom = min(zoom_x, zoom_y, MAX_ZOOM_FACTOR)

            # Apply zoom
            self.widget.zoom_factor = max(MIN_ZOOM_FACTOR, optimal_zoom)

        # Use the proper centering method that handles coordinate transformation and Y-flip
        self.widget._center_view_on_point(center_x, center_y)

        self.widget.invalidate_caches()
        self.widget.update()
        self.widget.view_changed.emit()

        logger.debug(f"Centered on {len(all_points)} points from {len(self.selected_curve_names)} curves")
        logger.debug(
            f"Center position: ({center_x:.2f}, {center_y:.2f}), Zoom: {self.widget.zoom_factor:.2f}, Pan offset: ({self.widget.pan_offset_x:.2f}, {self.widget.pan_offset_y:.2f})"
        )

    def get_live_curves_data(self) -> dict[str, CurveDataList]:
        """
        Get curves data with live status information for active curve.

        This fixes the gap visualization issue by ensuring the active curve
        uses live data from the curve store (which has current status changes)
        instead of static data from ApplicationState.

        Returns:
            Dictionary of curve data with active curve having live status data
        """
        # Get all curves from ApplicationState
        all_curve_names = self._app_state.get_all_curve_names()
        if not all_curve_names:
            return {}

        # Create dict with data from ApplicationState
        live_curves_data: dict[str, CurveDataList] = {
            name: self._app_state.get_curve_data(name) for name in all_curve_names
        }

        # If we have an active curve and live curve store data, replace with live data
        active_curve = self._app_state.active_curve
        if active_curve and active_curve in live_curves_data:
            live_data = self.widget._curve_store.get_data()
            if live_data:
                # Replace the active curve's ApplicationState data with live data from store
                live_curves_data[active_curve] = live_data
                logger.debug(f"Using live curve store data for active curve '{active_curve}' ({len(live_data)} points)")
            else:
                logger.debug(f"No live data available for active curve '{active_curve}'")

        return live_curves_data
