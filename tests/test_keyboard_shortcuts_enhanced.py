#!/usr/bin/env python
"""
Enhanced tests for keyboard shortcuts, including tracking direction and endframe shortcuts.
"""

from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from core.commands.shortcut_command import ShortcutContext
from core.commands.shortcut_commands import (
    SetEndframeCommand,
    SetTrackingDirectionCommand,
)
from core.models import PointStatus, TrackingDirection
from ui.curve_view_widget import CurveViewWidget
from ui.tracking_points_panel import TrackingPointsPanel


@pytest.fixture
def curve_widget_with_data(qtbot):
    """Create a curve widget with test data."""
    widget = CurveViewWidget()
    qtbot.addWidget(widget)

    # Add test curve data
    test_data = [
        (1, 100.0, 100.0, PointStatus.NORMAL.value),
        (2, 150.0, 120.0, PointStatus.KEYFRAME.value),
        (3, 200.0, 130.0, PointStatus.NORMAL.value),
        (4, 250.0, 140.0, PointStatus.NORMAL.value),
        (5, 300.0, 150.0, PointStatus.KEYFRAME.value),
    ]
    widget.set_curve_data(test_data)

    return widget


@pytest.fixture
def tracking_panel_with_data(qtbot):
    """Create a tracking points panel with test data."""
    panel = TrackingPointsPanel()
    qtbot.addWidget(panel)

    # Add test points using tracked data format
    tracked_data = {
        "Point_1": [(i, float(i * 10), float(i * 5), PointStatus.NORMAL.value) for i in range(1, 11)],
        "Point_2": [(i, float(i * 12), float(i * 6), PointStatus.NORMAL.value) for i in range(5, 15)],
        "Point_3": [(i, float(i * 15), float(i * 7), PointStatus.NORMAL.value) for i in range(10, 20)],
    }
    panel.set_tracked_data(tracked_data)

    return panel


class TestEndframeKeyboardShortcut:
    """Test E key for converting points to ENDFRAME status."""

    def test_e_key_converts_selected_points_to_endframe(self, curve_widget_with_data, qtbot):
        """Test that E key converts selected points to ENDFRAME status."""
        widget = curve_widget_with_data

        # Select some points using the proper method
        widget._select_point(0, add_to_selection=False)
        widget._select_point(2, add_to_selection=True)

        # Create mock main window
        mock_window = Mock()
        mock_window.curve_widget = widget

        # Create the command directly for testing
        cmd = SetEndframeCommand()
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)
        context = ShortcutContext(
            main_window=mock_window,
            focused_widget=widget,
            key_event=event,
            selected_curve_points=widget.selected_indices,
            selected_tracking_points=[],
            current_frame=None,
        )

        # Execute the command
        assert cmd.can_execute(context)
        assert cmd.execute(context)

        # Verify points were converted to ENDFRAME
        point0 = widget._curve_store.get_point(0)
        assert point0 and len(point0) >= 4 and point0[3] == PointStatus.ENDFRAME.value
        point2 = widget._curve_store.get_point(2)
        assert point2 and len(point2) >= 4 and point2[3] == PointStatus.ENDFRAME.value
        # Other points should remain unchanged
        point1 = widget._curve_store.get_point(1)
        assert point1 and len(point1) >= 4 and point1[3] == PointStatus.KEYFRAME.value
        point3 = widget._curve_store.get_point(3)
        assert point3 and len(point3) >= 4 and point3[3] == PointStatus.NORMAL.value

    def test_e_key_converts_current_frame_point_when_none_selected(self, curve_widget_with_data, qtbot):
        """Test that E key converts point at current frame when no points are selected."""
        widget = curve_widget_with_data

        # Clear selection to ensure no points are selected
        widget.clear_selection()

        # Create mock main window
        mock_window = Mock()
        mock_window.curve_widget = widget
        mock_window.current_frame = 3

        # Create the command directly for testing
        cmd = SetEndframeCommand()
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)
        context = ShortcutContext(
            main_window=mock_window,
            focused_widget=widget,
            key_event=event,
            selected_curve_points=widget.selected_indices,
            selected_tracking_points=[],
            current_frame=3,
        )

        # Execute the command
        assert cmd.can_execute(context)
        assert cmd.execute(context)

        # Verify point at frame 3 (index 2) was converted to ENDFRAME
        point2 = widget._curve_store.get_point(2)
        assert point2 and len(point2) >= 4 and point2[3] == PointStatus.ENDFRAME.value
        # Other points should remain unchanged
        point0 = widget._curve_store.get_point(0)
        assert point0 and len(point0) >= 4 and point0[3] == PointStatus.NORMAL.value
        point1 = widget._curve_store.get_point(1)
        assert point1 and len(point1) >= 4 and point1[3] == PointStatus.KEYFRAME.value

    def test_e_key_with_modifiers_does_nothing(self, curve_widget_with_data, qtbot):
        """Test that E key with modifiers doesn't trigger ENDFRAME conversion."""
        widget = curve_widget_with_data

        # Select a point using the proper method
        widget._select_point(0, add_to_selection=False)
        point0 = widget._curve_store.get_point(0)
        original_status = point0[3] if point0 and len(point0) >= 4 else None

        # Create mock main window
        mock_window = Mock()
        mock_window.curve_widget = widget

        # Test Shift+E (should not trigger)
        cmd = SetEndframeCommand()
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.ShiftModifier)
        context = ShortcutContext(
            main_window=mock_window,
            focused_widget=widget,
            key_event=event,
            selected_curve_points=widget.selected_indices,
            selected_tracking_points=[],
            current_frame=None,
        )

        # Should not be able to execute with modifiers
        assert not cmd.can_execute(context)

        # Status should remain unchanged
        point0 = widget._curve_store.get_point(0)
        assert point0 and len(point0) >= 4 and point0[3] == original_status


class TestTrackingDirectionKeyboardShortcuts:
    """Test keyboard shortcuts for changing tracking direction."""

    def test_shift_1_sets_backward_tracking(self, tracking_panel_with_data, qtbot):
        """Test that Shift+1 sets selected points to backward tracking."""
        panel = tracking_panel_with_data

        # Select first two rows
        from PySide6.QtWidgets import QTableWidgetSelectionRange

        selection = QTableWidgetSelectionRange(0, 0, 1, panel.table.columnCount() - 1)
        panel.table.setRangeSelected(selection, True)

        # Create mock main window
        mock_window = Mock()
        mock_window.tracking_panel = panel

        # Create the command directly for testing
        cmd = SetTrackingDirectionCommand(TrackingDirection.TRACKING_BW, "Shift+1")
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_1, Qt.KeyboardModifier.ShiftModifier)
        context = ShortcutContext(
            main_window=mock_window,
            focused_widget=panel,
            key_event=event,
            selected_curve_points=set(),
            selected_tracking_points=["Point_1", "Point_2"],
            current_frame=None,
        )

        # Execute the command
        assert cmd.can_execute(context)
        assert cmd.execute(context)

        # Verify tracking direction was updated
        assert panel._point_metadata["Point_1"]["tracking_direction"] == TrackingDirection.TRACKING_BW
        assert panel._point_metadata["Point_2"]["tracking_direction"] == TrackingDirection.TRACKING_BW
        # Third point should remain unchanged
        assert panel._point_metadata["Point_3"]["tracking_direction"] == TrackingDirection.TRACKING_FW_BW

    def test_shift_2_sets_forward_tracking(self, tracking_panel_with_data, qtbot):
        """Test that Shift+2 sets selected points to forward tracking."""
        panel = tracking_panel_with_data

        # Select middle row
        panel.table.setCurrentCell(1, 0)

        # Create mock main window
        mock_window = Mock()
        mock_window.tracking_panel = panel

        # Create the command directly for testing
        cmd = SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW, "Shift+2")
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_2, Qt.KeyboardModifier.ShiftModifier)
        context = ShortcutContext(
            main_window=mock_window,
            focused_widget=panel,
            key_event=event,
            selected_curve_points=set(),
            selected_tracking_points=["Point_2"],
            current_frame=None,
        )

        # Execute the command
        assert cmd.can_execute(context)
        assert cmd.execute(context)

        # Verify tracking direction was updated
        assert panel._point_metadata["Point_2"]["tracking_direction"] == TrackingDirection.TRACKING_FW
        # Other points should remain unchanged
        assert panel._point_metadata["Point_1"]["tracking_direction"] == TrackingDirection.TRACKING_FW_BW
        assert panel._point_metadata["Point_3"]["tracking_direction"] == TrackingDirection.TRACKING_FW_BW

    def test_shift_f3_sets_bidirectional_tracking(self, tracking_panel_with_data, qtbot):
        """Test that Shift+F3 sets selected points to bidirectional tracking."""
        panel = tracking_panel_with_data

        # First set a point to forward tracking
        panel._point_metadata["Point_1"]["tracking_direction"] = TrackingDirection.TRACKING_FW

        # Select first row
        panel.table.setCurrentCell(0, 0)

        # Create mock main window
        mock_window = Mock()
        mock_window.tracking_panel = panel

        # Create the command directly for testing
        cmd = SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW_BW, "Shift+F3")
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_F3, Qt.KeyboardModifier.ShiftModifier)
        context = ShortcutContext(
            main_window=mock_window,
            focused_widget=panel,
            key_event=event,
            selected_curve_points=set(),
            selected_tracking_points=["Point_1"],
            current_frame=None,
        )

        # Execute the command
        assert cmd.can_execute(context)
        assert cmd.execute(context)

        # Verify tracking direction was updated to bidirectional
        assert panel._point_metadata["Point_1"]["tracking_direction"] == TrackingDirection.TRACKING_FW_BW

    def test_tracking_shortcuts_without_selection_apply_to_all_visible(self, tracking_panel_with_data, qtbot):
        """Test that tracking shortcuts without selection apply to all visible points."""
        panel = tracking_panel_with_data

        # Clear selection
        panel.table.clearSelection()

        # Store original directions (for reference, not used in test)
        # original_directions = {name: metadata["tracking_direction"] for name, metadata in panel._point_metadata.items()}

        # Create mock main window
        mock_window = Mock()
        mock_window.tracking_panel = panel

        # Test that commands CAN execute without selection when there are visible points
        cmd = SetTrackingDirectionCommand(TrackingDirection.TRACKING_BW, "Test")
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_1, Qt.KeyboardModifier.ShiftModifier)
        context = ShortcutContext(
            main_window=mock_window,
            focused_widget=panel,
            key_event=event,
            selected_curve_points=set(),
            selected_tracking_points=[],  # No selection
            current_frame=None,
        )

        # Should be able to execute when there are visible points
        assert cmd.can_execute(context)

        # Execute the command
        success = cmd.execute(context)
        assert success

        # Verify all visible points got the new direction
        visible_points = panel.get_visible_points()
        for point_name in visible_points:
            assert panel._point_metadata[point_name]["tracking_direction"] == TrackingDirection.TRACKING_BW

    def test_tracking_shortcuts_without_shift_do_nothing(self, tracking_panel_with_data, qtbot):
        """Test that number keys without Shift don't change tracking direction."""
        panel = tracking_panel_with_data

        # Select a row
        panel.table.setCurrentCell(0, 0)

        # Store original direction
        original_direction = panel._point_metadata["Point_1"]["tracking_direction"]

        # Create mock main window
        mock_window = Mock()
        mock_window.tracking_panel = panel

        # Test that commands can't execute without Shift modifier
        for direction, key in [
            (TrackingDirection.TRACKING_BW, Qt.Key.Key_1),
            (TrackingDirection.TRACKING_FW, Qt.Key.Key_2),
        ]:
            cmd = SetTrackingDirectionCommand(direction, f"Shift+{key}")
            event = QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)  # No Shift
            context = ShortcutContext(
                main_window=mock_window,
                focused_widget=panel,
                key_event=event,
                selected_curve_points=set(),
                selected_tracking_points=["Point_1"],
                current_frame=None,
            )

            # Should not be able to execute without Shift modifier
            assert not cmd.can_execute(context)

        # Verify nothing changed
        assert panel._point_metadata["Point_1"]["tracking_direction"] == original_direction


class TestVisualStyling:
    """Test visual styling of smoothing controls."""

    def test_smoothing_frame_has_distinct_styling(self, qtbot):
        """Test that smoothing controls frame has distinct styling."""
        from ui.dark_theme_stylesheet import get_dark_theme_stylesheet

        stylesheet = get_dark_theme_stylesheet()

        # Check that smoothingControlsFrame styling is defined
        assert "QFrame#smoothingControlsFrame" in stylesheet
        assert "background-color: #3a3a3a" in stylesheet
        assert "border-radius: 4px" in stylesheet

        # Check label styling within frame
        assert "QFrame#smoothingControlsFrame QLabel" in stylesheet
        assert "font-weight: bold" in stylesheet

        # Check combo box and spinbox styling within frame
        assert "QFrame#smoothingControlsFrame QComboBox" in stylesheet
        assert "QFrame#smoothingControlsFrame QSpinBox" in stylesheet


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
