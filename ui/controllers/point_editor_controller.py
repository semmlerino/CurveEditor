#!/usr/bin/env python
"""
Point Editor Controller for CurveEditor.

This controller manages the point coordinate editor spinboxes and their
interaction with the curve data. It handles updating the spinbox values when
points are selected and applying changes when spinbox values are edited.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Slot  # pyright: ignore[reportUnknownVariableType]

if TYPE_CHECKING:
    from ui.main_window import MainWindow
    from ui.state_manager import StateManager

from core.logger_utils import get_logger
from core.point_types import safe_extract_point

logger = get_logger("point_editor_controller")


class PointEditorController:
    """
    Controller for managing point coordinate editing via spinboxes.

    Extracted from MainWindow to centralize all point editing logic,
    including updating spinbox values on selection changes and applying
    coordinate changes back to the curve.
    """

    main_window: "MainWindow"
    state_manager: "StateManager"
    _spinbox_connected: bool

    def __init__(self, main_window: "MainWindow", state_manager: "StateManager"):
        """
        Initialize the point editor controller.

        Args:
            main_window: Reference to the main window for UI access
            state_manager: Reference to the state manager for selection state
        """
        self.main_window = main_window
        self.state_manager = state_manager

        # Track if spinbox connections have been made
        self._spinbox_connected = False

        logger.info("PointEditorController initialized")

    def __del__(self) -> None:
        """Disconnect all signals to prevent memory leaks.

        PointEditorController creates 2 signal connections to point editor spinboxes.
        These connections are made conditionally via the _spinbox_connected flag.
        Without cleanup, these connections would keep objects alive, causing memory leaks.
        """
        # Disconnect point editor spinbox signals (2 connections, if connected)
        try:
            if hasattr(self, "_spinbox_connected") and self._spinbox_connected:
                if hasattr(self, "main_window"):
                    if self.main_window.point_x_spinbox:
                        _ = self.main_window.point_x_spinbox.valueChanged.disconnect(self._on_point_x_changed)
                    if self.main_window.point_y_spinbox:
                        _ = self.main_window.point_y_spinbox.valueChanged.disconnect(self._on_point_y_changed)
        except (RuntimeError, AttributeError):
            pass  # Already disconnected or objects destroyed

    @Slot(list)
    def on_selection_changed(self, indices: list[int]) -> None:
        """
        Handle selection change from state manager.

        Updates the point editor spinboxes to show the coordinates of
        the selected point when a single point is selected.

        Args:
            indices: List of selected point indices
        """
        count = len(indices)

        # Update selected count label
        if self.main_window.selected_count_label:
            self.main_window.selected_count_label.setText(f"Selected: {count}")

        if count == 1:
            # Show single point properties
            self._update_for_single_selection(indices[0])
        elif count > 1:
            # Multiple points selected
            self._update_for_multiple_selection(count)
        else:
            # No selection
            self._update_for_no_selection()

    @Slot(set, str)
    def on_store_selection_changed(self, selection: set[int], _curve_name: str | None = None) -> None:
        """Handle selection changes from the reactive store.

        Phase 4: Removed __default__ - curve_name is now optional.

        Args:
            selection: Set of selected point indices from the store
            _curve_name: Curve with selection change (currently unused)
        """
        if selection:
            # Update point editor with first selected point
            min_idx = min(selection)
            self._update_point_editor(min_idx)
        else:
            # Clear the point editor
            self._clear_point_editor()

        logger.debug(f"Store selection changed: {len(selection)} points")

    def _update_for_single_selection(self, idx: int) -> None:
        """
        Update UI for single point selection.

        Args:
            idx: Index of the selected point
        """
        # Update label
        if self.main_window.selected_point_label:
            self.main_window.selected_point_label.setText(f"Point #{idx}")

        # Get point data from curve widget
        curve_data = self.main_window.curve_widget.curve_data if self.main_window.curve_widget else []
        if idx < len(curve_data):
            point_data = curve_data[idx]
            _frame, x, y, _ = safe_extract_point(point_data)

            # Update spinboxes with actual values
            if self.main_window.point_x_spinbox and self.main_window.point_y_spinbox:
                # Block signals to prevent triggering value changed handlers
                _ = self.main_window.point_x_spinbox.blockSignals(True)
                _ = self.main_window.point_y_spinbox.blockSignals(True)

                self.main_window.point_x_spinbox.setValue(x)
                self.main_window.point_y_spinbox.setValue(y)

                _ = self.main_window.point_x_spinbox.blockSignals(False)
                _ = self.main_window.point_y_spinbox.blockSignals(False)

                # Connect spinbox changes if not already connected
                if not self._spinbox_connected:
                    _ = self.main_window.point_x_spinbox.valueChanged.connect(self._on_point_x_changed)
                    _ = self.main_window.point_y_spinbox.valueChanged.connect(self._on_point_y_changed)
                    self._spinbox_connected = True

                logger.debug(f"Updated point editor for point {idx}: ({x:.3f}, {y:.3f})")

        # Enable spinboxes
        self._set_spinboxes_enabled(True)

    def _update_for_multiple_selection(self, count: int) -> None:
        """
        Update UI for multiple point selection.

        Args:
            count: Number of selected points
        """
        if self.main_window.selected_point_label:
            self.main_window.selected_point_label.setText(f"{count} points selected")

        # Disable spinboxes for multiple selection
        self._set_spinboxes_enabled(False)

    def _update_for_no_selection(self) -> None:
        """Update UI when no points are selected."""
        if self.main_window.selected_point_label:
            self.main_window.selected_point_label.setText("No point selected")

        # Disable spinboxes
        self._set_spinboxes_enabled(False)

    def _update_point_editor(self, idx: int) -> None:
        """
        Update the point editor spinboxes for a specific point.

        Args:
            idx: Index of the point to display
        """
        curve_data = self.main_window.curve_widget.curve_data if self.main_window.curve_widget else []
        if idx < len(curve_data) and self.main_window.point_x_spinbox and self.main_window.point_y_spinbox:
            point_data = curve_data[idx]
            _frame, x, y, _ = safe_extract_point(point_data)

            # Block signals while updating
            _ = self.main_window.point_x_spinbox.blockSignals(True)
            _ = self.main_window.point_y_spinbox.blockSignals(True)

            self.main_window.point_x_spinbox.setValue(x)
            self.main_window.point_y_spinbox.setValue(y)

            _ = self.main_window.point_x_spinbox.blockSignals(False)
            _ = self.main_window.point_y_spinbox.blockSignals(False)

            # Enable spinboxes
            self._set_spinboxes_enabled(True)

            logger.debug(f"Point editor updated for point {idx}")

    def _clear_point_editor(self) -> None:
        """Clear and disable the point editor spinboxes."""
        self._set_spinboxes_enabled(False)

        if self.main_window.selected_point_label:
            self.main_window.selected_point_label.setText("No point selected")

    def _set_spinboxes_enabled(self, enabled: bool) -> None:
        """
        Enable or disable the coordinate spinboxes.

        Args:
            enabled: Whether to enable the spinboxes
        """
        if self.main_window.point_x_spinbox:
            self.main_window.point_x_spinbox.setEnabled(enabled)
        if self.main_window.point_y_spinbox:
            self.main_window.point_y_spinbox.setEnabled(enabled)

    @Slot(float)
    def _on_point_x_changed(self, value: float) -> None:
        """
        Handle X coordinate change in properties panel.

        Args:
            value: New X coordinate value
        """
        selected_indices = self.state_manager.selected_points
        if len(selected_indices) == 1 and self.main_window.curve_widget:
            idx = selected_indices[0]
            curve_data = self.main_window.curve_widget.curve_data
            if idx < len(curve_data):
                _, _, y, _ = safe_extract_point(curve_data[idx])
                self.main_window.curve_widget.update_point(idx, value, y)
                self.state_manager.is_modified = True
                logger.debug(f"Updated point {idx} X coordinate to {value:.3f}")

    @Slot(float)
    def _on_point_y_changed(self, value: float) -> None:
        """
        Handle Y coordinate change in properties panel.

        Args:
            value: New Y coordinate value
        """
        selected_indices = self.state_manager.selected_points
        if len(selected_indices) == 1 and self.main_window.curve_widget:
            idx = selected_indices[0]
            curve_data = self.main_window.curve_widget.curve_data
            if idx < len(curve_data):
                _, x, _, _ = safe_extract_point(curve_data[idx])
                self.main_window.curve_widget.update_point(idx, x, value)
                self.state_manager.is_modified = True
                logger.debug(f"Updated point {idx} Y coordinate to {value:.3f}")

    def connect_signals(self) -> None:
        """
        Connect point editor spinbox signals.

        This should be called after the UI is fully initialized.
        """
        if self.main_window.point_x_spinbox and self.main_window.point_y_spinbox:
            if not self._spinbox_connected:
                _ = self.main_window.point_x_spinbox.valueChanged.connect(self._on_point_x_changed)
                _ = self.main_window.point_y_spinbox.valueChanged.connect(self._on_point_y_changed)
                self._spinbox_connected = True
                logger.info("Point editor spinbox signals connected")

    # Protocol compliance methods
    @Slot(float)
    def on_point_x_changed(self, value: float) -> None:
        """Handle X coordinate change (Protocol API)."""
        self._on_point_x_changed(value)

    @Slot(float)
    def on_point_y_changed(self, value: float) -> None:
        """Handle Y coordinate change (Protocol API)."""
        self._on_point_y_changed(value)
