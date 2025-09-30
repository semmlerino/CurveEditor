#!/usr/bin/env python
"""
Multi-Curve Manager for CurveViewWidget.

Extracted from CurveViewWidget to follow Single Responsibility Principle.
Manages multiple curve data, visibility, colors, and active curve selection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.logger_utils import get_logger
from core.type_aliases import CurveDataList

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

        # Multi-curve data
        self.curves_data: dict[str, CurveDataList] = {}
        self.curve_metadata: dict[str, dict[str, Any]] = {}
        self.active_curve_name: str | None = None
        self.show_all_curves: bool = False
        self.selected_curve_names: set[str] = set()

        logger.debug("MultiCurveManager initialized")

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
        self.curves_data = curves.copy()
        if metadata:
            self.curve_metadata = metadata.copy()
        else:
            # Initialize default metadata for each curve
            self.curve_metadata = {name: {"visible": True, "color": "#FFFFFF"} for name in curves.keys()}

        # Update selected curves if specified
        if selected_curves is not None:
            self.selected_curve_names = set(selected_curves)
        elif not self.selected_curve_names:
            # If no selection specified and no existing selection, default to active curve
            self.selected_curve_names = {active_curve} if active_curve else set()

        # Set the active curve
        if active_curve and active_curve in curves:
            self.active_curve_name = active_curve
            # Update the single curve data for backward compatibility
            self.widget.set_curve_data(curves[active_curve])
        elif curves:
            # Default to first curve if no active curve specified
            self.active_curve_name = next(iter(curves.keys()))
            self.widget.set_curve_data(curves[self.active_curve_name])
        else:
            self.active_curve_name = None
            self.widget.set_curve_data([])

        # Trigger repaint to show all curves
        self.widget.update()
        logger.debug(f"Set {len(curves)} curves, active: {self.active_curve_name}")

    def add_curve(self, name: str, data: CurveDataList, metadata: dict[str, Any] | None = None) -> None:
        """
        Add a new curve to the display.

        Args:
            name: Unique name for the curve
            data: Curve data points
            metadata: Optional metadata for the curve
        """
        self.curves_data[name] = data
        if metadata:
            self.curve_metadata[name] = metadata
        else:
            self.curve_metadata[name] = {"visible": True, "color": "#FFFFFF"}

        # If this is the first curve, make it active
        if not self.active_curve_name:
            self.active_curve_name = name
            self.widget.set_curve_data(data)

        self.widget.update()
        logger.debug(f"Added curve '{name}' with {len(data)} points")

    def remove_curve(self, name: str) -> None:
        """
        Remove a curve from the display.

        Args:
            name: Name of the curve to remove
        """
        if name not in self.curves_data:
            return

        del self.curves_data[name]
        if name in self.curve_metadata:
            del self.curve_metadata[name]

        # If this was the active curve, select another
        if self.active_curve_name == name:
            if self.curves_data:
                self.active_curve_name = next(iter(self.curves_data.keys()))
                self.widget.set_curve_data(self.curves_data[self.active_curve_name])
            else:
                self.active_curve_name = None
                self.widget.set_curve_data([])

        self.widget.update()
        logger.debug(f"Removed curve '{name}'")

    def update_curve_visibility(self, name: str, visible: bool) -> None:
        """
        Update visibility of a specific curve.

        Args:
            name: Name of the curve
            visible: Whether the curve should be visible
        """
        if name in self.curve_metadata:
            self.curve_metadata[name]["visible"] = visible
            self.widget.update()
            logger.debug(f"Set curve '{name}' visibility to {visible}")

    def update_curve_color(self, name: str, color: str) -> None:
        """
        Update color of a specific curve.

        Args:
            name: Name of the curve
            color: Color in hex format (e.g., "#FF0000")
        """
        if name in self.curve_metadata:
            self.curve_metadata[name]["color"] = color
            self.widget.update()
            logger.debug(f"Set curve '{name}' color to {color}")

    def set_active_curve(self, name: str) -> None:
        """
        Set the active curve for editing operations.

        Args:
            name: Name of the curve to make active
        """
        if name in self.curves_data:
            self.active_curve_name = name
            # Update the single curve data for editing operations
            # This is needed for backward compatibility with editing tools
            self.widget._curve_store.set_data(self.curves_data[name])
            # Trigger display update to show the new active curve
            self.widget.update()
            logger.debug(f"Set active curve to '{name}'")

            # Auto-center on the current frame if centering mode is active
            if self.widget.centering_mode:
                if self.widget.main_window and getattr(self.widget.main_window, "current_frame", None) is not None:
                    current_frame = self.widget.main_window.current_frame  # pyright: ignore[reportAttributeAccessIssue]
                    logger.debug(
                        f"[CENTERING] Auto-centering on frame {current_frame} for newly selected curve '{name}'"
                    )
                    self.widget.center_on_frame(current_frame)

    def toggle_show_all_curves(self, show_all: bool) -> None:
        """
        Toggle whether to show all curves or just the active one.

        Args:
            show_all: If True, show all visible curves; if False, show only active curve
        """
        self.show_all_curves = show_all
        self.widget.update()
        logger.debug(f"Show all curves: {show_all}")

    def set_selected_curves(self, curve_names: list[str]) -> None:
        """
        Set which curves are currently selected for display.

        When show_all_curves is False, only these selected curves will be displayed.
        The last curve in the list becomes the active curve for editing.

        Args:
            curve_names: List of curve names to select and display
        """
        self.selected_curve_names = set(curve_names)

        # Set the last selected as the active curve for editing
        if curve_names and curve_names[-1] in self.curves_data:
            self.set_active_curve(curve_names[-1])

        self.widget.update()
        logger.debug(f"Selected curves: {self.selected_curve_names}, Active: {self.active_curve_name}")

    def center_on_selected_curves(self) -> None:
        """
        Center the view on all selected curves.

        Calculates the bounding box of all selected curves and centers the view on it.
        """
        logger.debug(
            f"center_on_selected_curves called with selected: {self.selected_curve_names}, curves_data keys: {self.curves_data.keys() if self.curves_data else 'None'}"
        )
        if not self.selected_curve_names or not self.curves_data:
            logger.debug("Early return - no selected curves or no data")
            return

        # Collect all points from selected curves
        all_points: list[tuple[float, float]] = []
        for curve_name in self.selected_curve_names:
            if curve_name in self.curves_data:
                curve_data = self.curves_data[curve_name]
                logger.debug(f"Processing curve {curve_name} with {len(curve_data)} points")
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
        instead of static data from the tracking controller.

        Returns:
            Dictionary of curve data with active curve having live status data
        """
        # Start with static curves data as base
        if not self.curves_data:
            return {}

        # Create a copy to avoid modifying the original
        live_curves_data: dict[str, CurveDataList] = self.curves_data.copy()

        # If we have an active curve and live curve store data, replace with live data
        if self.active_curve_name and self.active_curve_name in live_curves_data:
            live_data = self.widget._curve_store.get_data()
            if live_data:
                # Replace the active curve's static data with live data from store
                live_curves_data[self.active_curve_name] = live_data
                logger.debug(
                    f"Using live curve store data for active curve '{self.active_curve_name}' ({len(live_data)} points)"
                )
            else:
                logger.debug(f"No live data available for active curve '{self.active_curve_name}'")

        return live_curves_data
