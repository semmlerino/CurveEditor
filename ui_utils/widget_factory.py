"""
Widget factory for creating common UI widgets with consistent styling.

This module provides factory methods for creating widgets with consistent
theming, spacing, and configuration across the application.
"""

from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import ui.ui_constants as ui_constants
from ui.ui_scaling import UIScaling


class WidgetFactory:
    """Factory for creating common UI widgets with consistent styling."""

    @staticmethod
    def create_group_box(
        title: str,
        layout_type: Literal["grid", "horizontal", "vertical"] = "grid",
        spacing: str = "s",
        margins: str | None = None,
    ) -> tuple[QGroupBox, QLayout]:
        """Create a themed group box with specified layout type.

        Args:
            title: Group box title
            layout_type: Type of layout to use
            spacing: Spacing size key (xs, s, m, l)
            margins: Margin size key, None for default margins

        Returns:
            Tuple of (group_box, layout)
        """
        group = QGroupBox(title)

        # Create layout based on type
        if layout_type == "grid":
            layout = QGridLayout(group)
        elif layout_type == "horizontal":
            layout = QHBoxLayout(group)
        else:  # vertical
            layout = QVBoxLayout(group)

        # Set spacing
        layout.setSpacing(UIScaling.get_spacing(spacing))

        # Set margins if specified
        if margins is not None:
            margin = UIScaling.get_spacing(margins)
            layout.setContentsMargins(margin, margin, margin, margin)

        return group, layout

    @staticmethod
    def create_panel_widget(
        background: Literal["panel", "elevated", "surface"] = "panel",
        border: bool = True,
        rounded: bool = True,
    ) -> QWidget:
        """Create a themed panel widget with consistent styling.

        Args:
            background: Background style type
            border: Whether to show border
            rounded: Whether to use rounded corners

        Returns:
            Styled QWidget
        """
        widget = QWidget()
        WidgetFactory.apply_panel_styling(widget, background, border, rounded)
        return widget

    @staticmethod
    def apply_panel_styling(
        widget: QWidget,
        background: Literal["panel", "elevated", "surface"] = "panel",
        border: bool = True,
        rounded: bool = True,
    ) -> None:
        """Apply consistent panel styling to any widget.

        Args:
            widget: Widget to style
            background: Background style type
            border: Whether to show border
            rounded: Whether to use rounded corners
        """
        colors = ui_constants.get_theme_colors(UIScaling.get_theme())

        # Map background types to color keys
        bg_colors = {
            "panel": colors["bg_panel"],
            "elevated": colors["bg_elevated"],
            "surface": colors["bg_surface"],
        }
        bg_color = bg_colors.get(background, colors["bg_panel"])

        # Build stylesheet
        styles = [f"background-color: {bg_color};"]

        if border:
            styles.append(f"border: 1px solid {colors['border_default']};")

        if rounded:
            radius = UIScaling.get_border_radius("large")
            styles.append(f"border-radius: {radius}px;")

        widget.setStyleSheet(f"QWidget {{ {' '.join(styles)} }}")

    @staticmethod
    def create_horizontal_button_group(spacing: str = "s", margins: bool = False) -> tuple[QWidget, QHBoxLayout]:
        """Create a horizontal widget group for buttons.

        Args:
            spacing: Spacing size key
            margins: Whether to include margins

        Returns:
            Tuple of (container_widget, layout)
        """
        container = QWidget()
        layout = QHBoxLayout()

        layout.setSpacing(UIScaling.get_spacing(spacing))

        if not margins:
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            margin = UIScaling.get_spacing(spacing)
            layout.setContentsMargins(margin, margin, margin, margin)

        container.setLayout(layout)
        return container, layout

    @staticmethod
    def create_label_value_pair(
        label_text: str,
        initial_value: str = "",
        label_width: int | None = None,
    ) -> tuple[QLabel, QLabel]:
        """Create a consistent label-value pair for displaying metrics.

        Args:
            label_text: Text for the label
            initial_value: Initial value text
            label_width: Fixed width for label alignment

        Returns:
            Tuple of (label_widget, value_widget)
        """
        label = QLabel(label_text)
        value = QLabel(initial_value)

        # Style the label
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if label_width:
            label.setFixedWidth(label_width)

        # Style the value
        value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        return label, value

    @staticmethod
    def setup_standard_layout(
        layout: QLayout,
        spacing: str = "s",
        margins: str | None = None,
        zero_margins: bool = False,
    ) -> None:
        """Apply standard spacing and margin patterns to a layout.

        Args:
            layout: Layout to configure
            spacing: Spacing size key
            margins: Margin size key
            zero_margins: If True, sets margins to 0
        """
        layout.setSpacing(UIScaling.get_spacing(spacing))

        if zero_margins:
            layout.setContentsMargins(0, 0, 0, 0)
        elif margins is not None:
            margin = UIScaling.get_spacing(margins)
            layout.setContentsMargins(margin, margin, margin, margin)

    @staticmethod
    def create_spin_box(
        min_value: int = 0,
        max_value: int = 100,
        initial_value: int = 0,
        suffix: str = "",
        prefix: str = "",
        step: int = 1,
    ) -> QSpinBox:
        """Create a configured spin box with consistent styling.

        Args:
            min_value: Minimum value
            max_value: Maximum value
            initial_value: Initial value
            suffix: Text suffix (e.g., " px")
            prefix: Text prefix (e.g., "$")
            step: Step increment

        Returns:
            Configured QSpinBox
        """
        spin_box = QSpinBox()
        spin_box.setRange(min_value, max_value)
        spin_box.setValue(initial_value)
        spin_box.setSingleStep(step)

        if suffix:
            spin_box.setSuffix(suffix)
        if prefix:
            spin_box.setPrefix(prefix)

        # Apply consistent styling
        spin_box.setAlignment(Qt.AlignRight)

        return spin_box
