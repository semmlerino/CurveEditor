#!/usr/bin/env python
"""
View Options Controller for CurveEditor.

This controller manages all view-related options including checkboxes for
background/grid/info display, sliders for point size and line width, and
tooltip management.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.logger_utils import get_logger

logger = get_logger("view_options_controller")


class ViewOptionsController:
    """
    Controller for managing view options and visual settings.

    Extracted from MainWindow to centralize all view configuration logic
    including display toggles, size adjustments, and tooltip management.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the view options controller.

        Args:
            main_window: Reference to the main window for UI access
        """
        self.main_window = main_window
        self._stored_tooltips: dict[QWidget, str] = {}
        logger.info("ViewOptionsController initialized")

    @Slot()
    def update_curve_view_options(self) -> None:
        """Update curve view display options from checkboxes."""
        if not self.main_window.curve_widget:
            return

        # Update view options from checkboxes
        if self.main_window.show_background_cb:
            self.main_window.curve_widget.show_background = self.main_window.show_background_cb.isChecked()
        if self.main_window.show_grid_cb:
            self.main_window.curve_widget.show_grid = self.main_window.show_grid_cb.isChecked()
        if self.main_window.show_info_cb:
            self.main_window.curve_widget.show_info = self.main_window.show_info_cb.isChecked()

        # Trigger repaint
        self.main_window.curve_widget.update()
        logger.debug("Updated curve view options")

    @Slot(int)
    def update_curve_point_size(self, value: int) -> None:
        """
        Update curve point size from slider.

        Args:
            value: New point size value
        """
        if not self.main_window.curve_widget:
            return

        self.main_window.curve_widget.point_radius = value
        self.main_window.curve_widget.selected_point_radius = value + 2  # Selected points slightly larger

        # Trigger repaint
        self.main_window.curve_widget.update()
        logger.debug(f"Updated point size to {value}")

    @Slot(int)
    def update_curve_line_width(self, value: int) -> None:
        """
        Update curve line width from slider.

        Args:
            value: New line width value
        """
        if not self.main_window.curve_widget:
            return

        self.main_window.curve_widget.line_width = value
        # Trigger repaint
        self.main_window.curve_widget.update()
        logger.debug(f"Updated line width to {value}")

    @Slot()
    def toggle_tooltips(self) -> None:
        """Toggle tooltips on/off for all widgets."""
        if not self.main_window.show_tooltips_cb:
            return

        enable_tooltips = self.main_window.show_tooltips_cb.isChecked()

        if enable_tooltips:
            # Restore stored tooltips
            for widget, tooltip in self._stored_tooltips.items():
                try:
                    widget.setToolTip(tooltip)
                except RuntimeError:
                    # Widget may have been deleted
                    pass
            self._stored_tooltips.clear()
            logger.info("Tooltips enabled")
        else:
            # Store and clear all tooltips
            for widget in self.main_window.findChildren(QWidget):
                tooltip = widget.toolTip()
                if tooltip:
                    self._stored_tooltips[widget] = tooltip
                    widget.setToolTip("")
            logger.info("Tooltips disabled")

    def get_view_options(self) -> dict[str, object]:
        """
        Get current view options as a dictionary.

        Returns:
            Dictionary of view option settings
        """
        options = {}

        if self.main_window.show_background_cb:
            options["show_background"] = self.main_window.show_background_cb.isChecked()
        if self.main_window.show_grid_cb:
            options["show_grid"] = self.main_window.show_grid_cb.isChecked()
        if self.main_window.show_info_cb:
            options["show_info"] = self.main_window.show_info_cb.isChecked()
        if self.main_window.show_tooltips_cb:
            options["show_tooltips"] = self.main_window.show_tooltips_cb.isChecked()
        if self.main_window.point_size_slider:
            options["point_size"] = self.main_window.point_size_slider.value()
        if self.main_window.line_width_slider:
            options["line_width"] = self.main_window.line_width_slider.value()

        return options

    def set_view_options(self, options: dict[str, object]) -> None:
        """
        Set view options from a dictionary.

        Args:
            options: Dictionary of view option settings to apply
        """
        if "show_background" in options and self.main_window.show_background_cb:
            self.main_window.show_background_cb.setChecked(bool(options["show_background"]))
        if "show_grid" in options and self.main_window.show_grid_cb:
            self.main_window.show_grid_cb.setChecked(bool(options["show_grid"]))
        if "show_info" in options and self.main_window.show_info_cb:
            self.main_window.show_info_cb.setChecked(bool(options["show_info"]))
        if "show_tooltips" in options and self.main_window.show_tooltips_cb:
            self.main_window.show_tooltips_cb.setChecked(bool(options["show_tooltips"]))
        if "point_size" in options and self.main_window.point_size_slider:
            self.main_window.point_size_slider.setValue(int(options["point_size"]))
        if "line_width" in options and self.main_window.line_width_slider:
            self.main_window.line_width_slider.setValue(int(options["line_width"]))

        # Apply the options
        self.update_curve_view_options()
        self.toggle_tooltips()
