#!/usr/bin/env python3
"""
Test for Ctrl+click multi-selection behavior.

Bug Fixed: Ctrl+click now properly toggles point selection:
- If point is not selected → adds to selection
- If point is already selected → removes from selection (toggle)

Following UNIFIED_TESTING_GUIDE:
- Test behavior, not implementation
- Use real Qt widgets with qtbot
- Verify user-facing functionality
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from ui.curve_view_widget import CurveViewWidget


class TestCtrlClickToggleSelection:
    """Test suite for Ctrl+click toggle selection behavior."""

    @pytest.fixture
    def curve_widget(self, qtbot):
        """Create CurveViewWidget with test data."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Set test data
        test_data = [
            (1, 100.0, 200.0, "normal"),
            (2, 200.0, 300.0, "normal"),
            (3, 300.0, 400.0, "normal"),
        ]
        widget.set_curve_data(test_data)

        widget.show()
        qtbot.waitExposed(widget)

        return widget

    def test_ctrl_click_adds_to_selection(self, curve_widget, qtbot):
        """Test that Ctrl+click adds to selection instead of replacing it."""
        # Update screen points cache so we can find points
        curve_widget._update_screen_points_cache()

        # Get screen positions of first two points
        screen_pos_0 = curve_widget._screen_points_cache.get(0)
        screen_pos_1 = curve_widget._screen_points_cache.get(1)

        assert screen_pos_0 is not None, "Point 0 should have screen position"
        assert screen_pos_1 is not None, "Point 1 should have screen position"

        # Select first point (normal click)
        QTest.mouseClick(
            curve_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, screen_pos_0.toPoint()
        )
        qtbot.wait(10)

        # Verify only first point selected
        selection = curve_widget.selected_indices
        assert selection == {0}, f"Expected {{0}}, got {selection}"

        # Ctrl+click second point
        QTest.mouseClick(
            curve_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, screen_pos_1.toPoint()
        )
        qtbot.wait(10)

        # Verify both points are now selected
        selection = curve_widget.selected_indices
        assert selection == {0, 1}, f"Expected {{0, 1}}, got {selection}"

    def test_ctrl_click_deselects_already_selected_point(self, curve_widget, qtbot):
        """Test that Ctrl+clicking an already-selected point deselects it."""
        # Update screen points cache
        curve_widget._update_screen_points_cache()

        # Get screen positions
        screen_pos_0 = curve_widget._screen_points_cache.get(0)
        screen_pos_1 = curve_widget._screen_points_cache.get(1)

        # Select both points
        QTest.mouseClick(
            curve_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, screen_pos_0.toPoint()
        )
        qtbot.wait(10)

        QTest.mouseClick(
            curve_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, screen_pos_1.toPoint()
        )
        qtbot.wait(10)

        # Verify both selected
        assert curve_widget.selected_indices == {0, 1}

        # Ctrl+click first point again to deselect it
        QTest.mouseClick(
            curve_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, screen_pos_0.toPoint()
        )
        qtbot.wait(10)

        # Verify only second point remains selected
        selection = curve_widget.selected_indices
        assert selection == {1}, f"Expected {{1}}, got {selection}"

    def test_normal_click_replaces_selection(self, curve_widget, qtbot):
        """Test that normal click (without Ctrl) replaces selection."""
        # Update screen points cache
        curve_widget._update_screen_points_cache()

        screen_pos_0 = curve_widget._screen_points_cache.get(0)
        screen_pos_1 = curve_widget._screen_points_cache.get(1)

        # Select first point
        QTest.mouseClick(
            curve_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, screen_pos_0.toPoint()
        )
        qtbot.wait(10)

        # Ctrl+click second point to have both selected
        QTest.mouseClick(
            curve_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, screen_pos_1.toPoint()
        )
        qtbot.wait(10)

        assert curve_widget.selected_indices == {0, 1}

        # Normal click on second point should deselect first
        QTest.mouseClick(
            curve_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, screen_pos_1.toPoint()
        )
        qtbot.wait(10)

        selection = curve_widget.selected_indices
        assert selection == {1}, f"Expected {{1}}, got {selection}"
