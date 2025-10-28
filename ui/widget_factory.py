"""
Widget Factory for CurveEditor.

Consolidates repetitive widget initialization patterns across controllers.
Provides helper methods for creating common widget types with consistent
configuration, reducing boilerplate code by ~150 lines.
"""

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
)


def create_label(text: str) -> QLabel:
    """
    Create a simple QLabel with text.

    Args:
        text: Label text content

    Returns:
        Configured QLabel instance
    """
    return QLabel(text)


def create_button_with_icon(
    icon: QIcon,
    tooltip: str = "",
    checkable: bool = False,
) -> QPushButton:
    """
    Create a QPushButton with icon and tooltip.

    Commonly used for navigation/playback buttons in timeline controls.

    Args:
        icon: Button icon
        tooltip: Tooltip text (optional)
        checkable: Whether button is checkable/toggleable (default: False)

    Returns:
        Configured QPushButton instance
    """
    button = QPushButton()
    button.setIcon(icon)
    if tooltip:
        button.setToolTip(tooltip)
    if checkable:
        button.setCheckable(True)
    return button


def create_spinbox(
    minimum: int = 0,
    maximum: int = 100,
    value: int = 0,
    tooltip: str = "",
    suffix: str = "",
) -> QSpinBox:
    """
    Create a QSpinBox with range, value, and optional suffix/tooltip.

    Args:
        minimum: Minimum value (default: 0)
        maximum: Maximum value (default: 100)
        value: Initial value (default: 0)
        tooltip: Tooltip text (optional)
        suffix: Value suffix text (optional, e.g., " fps")

    Returns:
        Configured QSpinBox instance
    """
    spinbox = QSpinBox()
    spinbox.setMinimum(minimum)
    spinbox.setMaximum(maximum)
    spinbox.setValue(value)
    if tooltip:
        spinbox.setToolTip(tooltip)
    if suffix:
        spinbox.setSuffix(suffix)
    return spinbox


def create_double_spinbox(
    minimum: float = -10000.0,
    maximum: float = 10000.0,
    decimals: int = 3,
    enabled: bool = True,
) -> QDoubleSpinBox:
    """
    Create a QDoubleSpinBox with range, precision, and enabled state.

    Commonly used for point coordinate editing (x/y values).

    Args:
        minimum: Minimum value (default: -10000.0)
        maximum: Maximum value (default: 10000.0)
        decimals: Number of decimal places (default: 3)
        enabled: Whether spinbox is enabled (default: True)

    Returns:
        Configured QDoubleSpinBox instance
    """
    spinbox = QDoubleSpinBox()
    spinbox.setRange(minimum, maximum)
    spinbox.setDecimals(decimals)
    spinbox.setEnabled(enabled)
    return spinbox


def create_slider(
    minimum: int = 0,
    maximum: int = 100,
    value: int = 0,
    orientation: Qt.Orientation = Qt.Orientation.Horizontal,
    tooltip: str = "",
) -> QSlider:
    """
    Create a QSlider with range, value, and orientation.

    Args:
        minimum: Minimum value (default: 0)
        maximum: Maximum value (default: 100)
        value: Initial value (default: 0)
        orientation: Slider orientation (default: Horizontal)
        tooltip: Tooltip text (optional)

    Returns:
        Configured QSlider instance
    """
    slider = QSlider(orientation)
    slider.setMinimum(minimum)
    slider.setMaximum(maximum)
    slider.setValue(value)
    if tooltip:
        slider.setToolTip(tooltip)
    return slider


def create_checkbox(label: str, checked: bool = False) -> QCheckBox:
    """
    Create a QCheckBox with label and checked state.

    Args:
        label: Checkbox label text
        checked: Initial checked state (default: False)

    Returns:
        Configured QCheckBox instance
    """
    checkbox = QCheckBox(label)
    checkbox.setChecked(checked)
    return checkbox


def create_combobox(
    items: Sequence[str],
    current_index: int = 0,
    tooltip: str = "",
) -> QComboBox:
    """
    Create a QComboBox with items and tooltip.

    Args:
        items: List of item strings to populate combobox
        current_index: Initially selected item index (default: 0)
        tooltip: Tooltip text (optional)

    Returns:
        Configured QComboBox instance
    """
    combobox = QComboBox()
    combobox.addItems(list(items))
    combobox.setCurrentIndex(current_index)
    if tooltip:
        combobox.setToolTip(tooltip)
    return combobox
