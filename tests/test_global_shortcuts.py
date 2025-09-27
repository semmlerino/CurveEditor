#!/usr/bin/env python
"""
Tests for the global keyboard shortcut system.

Verifies that shortcuts work regardless of which widget has focus.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.commands.shortcut_command import ShortcutContext
from core.commands.shortcut_commands import (
    CenterViewCommand,
    SetEndframeCommand,
    SetTrackingDirectionCommand,
)
from core.models import PointStatus, TrackingDirection
from ui.main_window import MainWindow
from ui.shortcut_registry import ShortcutRegistry


@pytest.fixture
def main_window_with_shortcuts(qtbot):
    """Create a main window with global shortcuts initialized."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Add test curve data
    if window.curve_widget:
        test_data = [
            (1, 100.0, 100.0, PointStatus.NORMAL.value),
            (2, 150.0, 120.0, PointStatus.KEYFRAME.value),
            (3, 200.0, 130.0, PointStatus.NORMAL.value),
            (4, 250.0, 140.0, PointStatus.NORMAL.value),
            (5, 300.0, 150.0, PointStatus.KEYFRAME.value),
        ]
        window.curve_widget.set_curve_data(test_data)

    # Add test tracking data
    if window.tracking_panel:
        tracked_data = {
            "Point_1": [(i, float(i * 10), float(i * 5), PointStatus.NORMAL.value) for i in range(1, 11)],
            "Point_2": [(i, float(i * 12), float(i * 6), PointStatus.NORMAL.value) for i in range(5, 15)],
        }
        window.tracking_panel.set_tracked_data(tracked_data)

    return window


class TestGlobalShortcuts:
    """Test that shortcuts work globally regardless of focus."""

    def test_e_key_works_when_timeline_has_focus(self, main_window_with_shortcuts, qtbot):
        """Test that E key works even when timeline has focus."""
        window = main_window_with_shortcuts

        # Select some points in curve widget
        if window.curve_widget:
            window.curve_widget._select_point(0, add_to_selection=False)
            window.curve_widget._select_point(2, add_to_selection=True)

        # Set focus to timeline tabs
        if hasattr(window, "timeline_tabs") and window.timeline_tabs:
            window.timeline_tabs.setFocus()
            assert window.timeline_tabs.hasFocus()

            # Press E key
            QTest.keyClick(window.timeline_tabs, Qt.Key.Key_E)

            # Verify points were converted to ENDFRAME
            point0 = window.curve_widget._curve_store.get_point(0)
            assert point0 and len(point0) >= 4 and point0[3] == PointStatus.ENDFRAME.value
            point2 = window.curve_widget._curve_store.get_point(2)
            assert point2 and len(point2) >= 4 and point2[3] == PointStatus.ENDFRAME.value

    def test_tracking_shortcuts_work_when_curve_has_focus(self, main_window_with_shortcuts, qtbot):
        """Test that tracking direction shortcuts work when curve widget has focus."""
        window = main_window_with_shortcuts

        if not window.tracking_panel or not window.curve_widget:
            pytest.skip("Tracking panel or curve widget not available")

        # Select tracking points
        from PySide6.QtWidgets import QTableWidgetSelectionRange

        selection = QTableWidgetSelectionRange(0, 0, 1, window.tracking_panel.table.columnCount() - 1)
        window.tracking_panel.table.setRangeSelected(selection, True)

        # Set focus to curve widget
        window.curve_widget.setFocus()
        assert window.curve_widget.hasFocus()

        # Press Shift+1 for backward tracking
        QTest.keyClick(window.curve_widget, Qt.Key.Key_1, Qt.KeyboardModifier.ShiftModifier)

        # Verify tracking direction was updated
        assert window.tracking_panel._point_metadata["Point_1"]["tracking_direction"] == TrackingDirection.TRACKING_BW
        assert window.tracking_panel._point_metadata["Point_2"]["tracking_direction"] == TrackingDirection.TRACKING_BW

    def test_c_key_centers_view_from_any_widget(self, main_window_with_shortcuts, qtbot):
        """Test that C key centers view regardless of focus."""
        window = main_window_with_shortcuts

        if not window.curve_widget:
            pytest.skip("Curve widget not available")

        # Select a point
        window.curve_widget._select_point(2, add_to_selection=False)

        # Test from different widgets
        test_widgets = []
        if hasattr(window, "timeline_tabs") and window.timeline_tabs:
            test_widgets.append(window.timeline_tabs)
        if window.tracking_panel:
            test_widgets.append(window.tracking_panel)

        for widget in test_widgets:
            # Reset centering mode
            window.curve_widget.centering_mode = False

            # Set focus to widget
            widget.setFocus()
            assert widget.hasFocus()

            # Press C key
            QTest.keyClick(widget, Qt.Key.Key_C)

            # Verify centering mode was toggled
            assert window.curve_widget.centering_mode is True

    def test_delete_works_for_appropriate_widget(self, main_window_with_shortcuts, qtbot):
        """Test that Delete key works contextually based on selection."""
        window = main_window_with_shortcuts

        if not window.curve_widget:
            pytest.skip("Curve widget not available")

        # Select curve points
        window.curve_widget._select_point(0, add_to_selection=False)
        initial_count = len(window.curve_widget.curve_data)

        # Press Delete from timeline
        if hasattr(window, "timeline_tabs") and window.timeline_tabs:
            window.timeline_tabs.setFocus()
            QTest.keyClick(window.timeline_tabs, Qt.Key.Key_Delete)

            # Verify point was deleted
            assert len(window.curve_widget.curve_data) == initial_count - 1


class TestShortcutRegistry:
    """Test the shortcut registry functionality."""

    def test_register_and_lookup_shortcuts(self):
        """Test registering and looking up shortcuts."""
        registry = ShortcutRegistry()

        # Register a shortcut
        cmd = SetEndframeCommand()
        registry.register(cmd)

        # Create a mock key event for E key
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)

        # Look up the command
        found_cmd = registry.get_command(event)
        assert found_cmd is not None
        assert found_cmd.key_sequence == "E"
        assert found_cmd.description == "Set point(s) to end frame"

    def test_list_shortcuts(self):
        """Test listing all registered shortcuts."""
        registry = ShortcutRegistry()

        # Register multiple shortcuts
        registry.register(SetEndframeCommand())
        registry.register(CenterViewCommand())
        registry.register(SetTrackingDirectionCommand(TrackingDirection.TRACKING_BW, "Shift+1"))

        # List shortcuts
        shortcuts = registry.list_shortcuts()
        assert len(shortcuts) == 3
        assert "E" in shortcuts
        assert "C" in shortcuts
        assert "Shift+1" in shortcuts

    def test_categorize_shortcuts(self):
        """Test shortcut categorization."""
        registry = ShortcutRegistry()

        # Register shortcuts from different categories
        registry.register(SetEndframeCommand())  # Editing
        registry.register(CenterViewCommand())  # View
        registry.register(SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW, "Shift+2"))  # Tracking

        # Get categorized shortcuts
        categories = registry.get_shortcuts_by_category()

        assert "Editing" in categories
        assert "View" in categories
        assert "Tracking" in categories

        # Check correct categorization
        editing = dict(categories["Editing"])
        assert "E" in editing

        view = dict(categories["View"])
        assert "C" in view

        tracking = dict(categories["Tracking"])
        assert "Shift+2" in tracking


class TestShortcutContext:
    """Test the shortcut context functionality."""

    def test_context_properties(self, main_window_with_shortcuts):
        """Test that context properties work correctly."""
        window = main_window_with_shortcuts

        # Create a mock key event
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)

        # Build a context
        context = ShortcutContext(
            main_window=window,
            focused_widget=window.curve_widget,
            key_event=event,
            selected_curve_points={0, 1, 2},
            selected_tracking_points=["Point_1"],
            current_frame=5,
        )

        # Test properties
        assert context.has_curve_selection is True
        assert context.has_tracking_selection is True
        assert context.widget_type == "CurveViewWidget"
        assert len(context.selected_curve_points) == 3
        assert len(context.selected_tracking_points) == 1
        assert context.current_frame == 5


class TestEventFilterIntegration:
    """Test the global event filter integration."""

    def test_event_filter_delegates_to_commands(self, main_window_with_shortcuts, monkeypatch):
        """Test that event filter properly delegates to commands."""
        window = main_window_with_shortcuts

        if not window.curve_widget:
            pytest.skip("Curve widget not available")

        # Track if command was executed
        executed = []

        def mock_execute(self, context):
            executed.append(self.key_sequence)
            return True

        # Patch the execute method
        monkeypatch.setattr(SetEndframeCommand, "execute", mock_execute)

        # Select a point
        window.curve_widget._select_point(0, add_to_selection=False)

        # Simulate key press through the application
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.curve_widget, event)

        # Verify command was executed
        assert "E" in executed

    def test_event_filter_skips_text_input_widgets(self, main_window_with_shortcuts, qtbot):
        """Test that event filter skips text input widgets."""
        window = main_window_with_shortcuts

        # Create a QLineEdit for testing
        from PySide6.QtWidgets import QLineEdit

        line_edit = QLineEdit(window)
        line_edit.show()
        qtbot.addWidget(line_edit)

        # Set focus to line edit
        line_edit.setFocus()
        assert line_edit.hasFocus()

        # Type E key - should go to line edit, not trigger shortcut
        QTest.keyClick(line_edit, Qt.Key.Key_E)

        # Verify text was entered
        assert line_edit.text() == "e"

        # Verify no points were changed to ENDFRAME
        if window.curve_widget:
            for i in range(len(window.curve_widget.curve_data)):
                point = window.curve_widget._curve_store.get_point(i)
                if point and len(point) >= 4:
                    assert point[3] != PointStatus.ENDFRAME.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
