"""
Tests for widget_factory module.

Verifies that widget factory methods create properly configured widgets
with correct default values and properties.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyle

from ui import widget_factory


@pytest.fixture
def qt_app(qtbot):
    """Provide Qt application for widget tests."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance()


class TestWidgetFactory:
    """Test widget factory helper methods."""

    def test_create_label(self, qtbot):
        """Test create_label creates QLabel with text."""
        label = widget_factory.create_label("Test Label")
        assert label.text() == "Test Label"

    def test_create_button_with_icon(self, qtbot, qt_app):
        """Test create_button_with_icon creates QPushButton with icon and tooltip."""
        style = qt_app.style()
        icon = style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)

        button = widget_factory.create_button_with_icon(icon=icon, tooltip="Play", checkable=True)

        assert not button.icon().isNull()
        assert button.toolTip() == "Play"
        assert button.isCheckable()

    def test_create_button_without_tooltip(self, qtbot, qt_app):
        """Test create_button_with_icon without tooltip."""
        style = qt_app.style()
        icon = style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)

        button = widget_factory.create_button_with_icon(icon=icon)

        assert not button.icon().isNull()
        assert button.toolTip() == ""
        assert not button.isCheckable()

    def test_create_spinbox(self, qtbot):
        """Test create_spinbox creates QSpinBox with range and value."""
        spinbox = widget_factory.create_spinbox(minimum=1, maximum=100, value=50, tooltip="Test", suffix=" fps")

        assert spinbox.minimum() == 1
        assert spinbox.maximum() == 100
        assert spinbox.value() == 50
        assert spinbox.toolTip() == "Test"
        assert spinbox.suffix() == " fps"

    def test_create_spinbox_defaults(self, qtbot):
        """Test create_spinbox with default parameters."""
        spinbox = widget_factory.create_spinbox()

        assert spinbox.minimum() == 0
        assert spinbox.maximum() == 100
        assert spinbox.value() == 0
        assert spinbox.toolTip() == ""
        assert spinbox.suffix() == ""

    def test_create_double_spinbox(self, qtbot):
        """Test create_double_spinbox creates QDoubleSpinBox with range and precision."""
        spinbox = widget_factory.create_double_spinbox(minimum=-1000, maximum=1000, decimals=2, enabled=False)

        assert spinbox.minimum() == -1000
        assert spinbox.maximum() == 1000
        assert spinbox.decimals() == 2
        assert not spinbox.isEnabled()

    def test_create_double_spinbox_defaults(self, qtbot):
        """Test create_double_spinbox with default parameters."""
        spinbox = widget_factory.create_double_spinbox()

        assert spinbox.minimum() == -10000.0
        assert spinbox.maximum() == 10000.0
        assert spinbox.decimals() == 3
        assert spinbox.isEnabled()

    def test_create_slider(self, qtbot):
        """Test create_slider creates QSlider with range and orientation."""
        slider = widget_factory.create_slider(
            minimum=1, maximum=20, value=10, orientation=Qt.Orientation.Horizontal, tooltip="Test slider"
        )

        assert slider.minimum() == 1
        assert slider.maximum() == 20
        assert slider.value() == 10
        assert slider.orientation() == Qt.Orientation.Horizontal
        assert slider.toolTip() == "Test slider"

    def test_create_slider_vertical(self, qtbot):
        """Test create_slider with vertical orientation."""
        slider = widget_factory.create_slider(orientation=Qt.Orientation.Vertical)

        assert slider.orientation() == Qt.Orientation.Vertical

    def test_create_checkbox(self, qtbot):
        """Test create_checkbox creates QCheckBox with label and checked state."""
        checkbox = widget_factory.create_checkbox("Test Option", checked=True)

        assert checkbox.text() == "Test Option"
        assert checkbox.isChecked()

    def test_create_checkbox_unchecked(self, qtbot):
        """Test create_checkbox with unchecked default."""
        checkbox = widget_factory.create_checkbox("Another Option", checked=False)

        assert checkbox.text() == "Another Option"
        assert not checkbox.isChecked()

    def test_create_combobox(self, qtbot):
        """Test create_combobox creates QComboBox with items."""
        items = ["Option 1", "Option 2", "Option 3"]
        combobox = widget_factory.create_combobox(items=items, current_index=1, tooltip="Select option")

        assert combobox.count() == 3
        assert combobox.currentText() == "Option 2"
        assert combobox.currentIndex() == 1
        assert combobox.toolTip() == "Select option"

    def test_create_combobox_empty(self, qtbot):
        """Test create_combobox with empty items list."""
        combobox = widget_factory.create_combobox(items=[])

        assert combobox.count() == 0
        assert combobox.currentIndex() == -1  # Empty combobox has index -1

    def test_create_combobox_single_item(self, qtbot):
        """Test create_combobox with single item."""
        combobox = widget_factory.create_combobox(items=["Only Option"])

        assert combobox.count() == 1
        assert combobox.currentText() == "Only Option"
        assert combobox.currentIndex() == 0
