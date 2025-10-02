#!/usr/bin/env python3
"""
Test for cross-curve Ctrl+click point selection visibility.

This test verifies that when a user selects points on different curves using Ctrl+click,
all curves with selected points become visible without requiring "Show all curves" to be enabled.
"""

import pytest
from PySide6.QtTest import QTest

from ui.curve_view_widget import CurveViewWidget


@pytest.fixture
def curve_widget(qtbot):
    """Create a CurveViewWidget with test data."""
    widget = CurveViewWidget()
    qtbot.addWidget(widget)

    # Set up multiple curves
    curves_data = {
        "curve_a": [
            (1, 10.0, 20.0, 0),  # frame, x, y, status
            (2, 15.0, 25.0, 0),
            (3, 20.0, 30.0, 0),
        ],
        "curve_b": [
            (1, 50.0, 60.0, 0),
            (2, 55.0, 65.0, 0),
            (3, 60.0, 70.0, 0),
        ],
        "curve_c": [
            (1, 100.0, 110.0, 0),
            (2, 105.0, 115.0, 0),
            (3, 110.0, 120.0, 0),
        ],
    }

    widget.set_curves_data(curves_data, active_curve="curve_a")
    widget.show()
    QTest.qWaitForWindowExposed(widget)

    return widget


class TestCrossCurveCtrlClick:
    """Test cross-curve point selection with Ctrl+click."""

    def test_ctrl_click_different_curve_makes_both_visible(self, curve_widget):
        """
        Test that Ctrl+clicking a point on a different curve makes both curves visible.

        Scenario:
        1. Start with curve_a active
        2. Click a point on curve_a -> curve_a should be in selected_curve_names
        3. Ctrl+click a point on curve_b -> both curve_a and curve_b should be in selected_curve_names
        4. Both curves should be visible without show_all_curves enabled
        """
        # Verify initial state
        assert curve_widget.active_curve_name == "curve_a"
        assert curve_widget.show_all_curves is False

        # Get screen position of first point on curve_a
        point_a = curve_widget.curves_data["curve_a"][0]
        screen_pos_a = curve_widget.data_to_screen(float(point_a[1]), float(point_a[2]))

        # Click point on curve_a
        idx_a, curve_name_a = curve_widget._find_point_at_multi_curve(screen_pos_a)
        assert idx_a >= 0, "Should find point on curve_a"
        assert curve_name_a == "curve_a", "Should identify curve_a"

        # Select the point (simulates mouse click)
        curve_widget._select_point(idx_a, add_to_selection=False, curve_name=curve_name_a)

        # Verify curve_a is in selected_curve_names
        assert "curve_a" in curve_widget.selected_curve_names

        # Get screen position of first point on curve_b
        point_b = curve_widget.curves_data["curve_b"][0]
        screen_pos_b = curve_widget.data_to_screen(float(point_b[1]), float(point_b[2]))

        # Ctrl+click point on curve_b
        idx_b, curve_name_b = curve_widget._find_point_at_multi_curve(screen_pos_b)
        assert idx_b >= 0, "Should find point on curve_b"
        assert curve_name_b == "curve_b", "Should identify curve_b"

        # Select the point with add_to_selection=True (simulates Ctrl+click)
        curve_widget._select_point(idx_b, add_to_selection=True, curve_name=curve_name_b)

        # Verify both curves are in selected_curve_names
        assert "curve_a" in curve_widget.selected_curve_names, "curve_a should still be selected"
        assert "curve_b" in curve_widget.selected_curve_names, "curve_b should now be selected"

        # Verify active curve switched to curve_b (last selected)
        assert curve_widget.active_curve_name == "curve_b"

        # Verify show_all_curves is still False
        assert curve_widget.show_all_curves is False

        # Both curves should be visible according to rendering logic
        # (renderer shows curves in selected_curve_names when show_all_curves is False)

    def test_find_point_at_multi_curve_searches_all_curves(self, curve_widget):
        """Test that _find_point_at_multi_curve can find points on any visible curve."""
        # Get points from different curves
        point_a = curve_widget.curves_data["curve_a"][1]
        point_b = curve_widget.curves_data["curve_b"][1]

        # Get screen positions
        screen_a = curve_widget.data_to_screen(float(point_a[1]), float(point_a[2]))
        screen_b = curve_widget.data_to_screen(float(point_b[1]), float(point_b[2]))

        # Should find points on different curves (verifies cross-curve search works)
        idx_a, name_a = curve_widget._find_point_at_multi_curve(screen_a)
        assert idx_a >= 0 and name_a == "curve_a", f"Should find curve_a, got idx={idx_a}, name={name_a}"

        idx_b, name_b = curve_widget._find_point_at_multi_curve(screen_b)
        assert idx_b >= 0 and name_b == "curve_b", f"Should find curve_b, got idx={idx_b}, name={name_b}"

    def test_selecting_from_different_curve_switches_active(self, curve_widget):
        """Test that selecting a point on a different curve makes it active."""
        assert curve_widget.active_curve_name == "curve_a"

        # Select a point on curve_b
        point_b = curve_widget.curves_data["curve_b"][0]
        screen_pos = curve_widget.data_to_screen(float(point_b[1]), float(point_b[2]))
        idx, curve_name = curve_widget._find_point_at_multi_curve(screen_pos)

        curve_widget._select_point(idx, add_to_selection=False, curve_name=curve_name)

        # Active curve should switch to curve_b
        assert curve_widget.active_curve_name == "curve_b"

    def test_ctrl_click_on_same_curve_does_not_duplicate(self, curve_widget):
        """Test that Ctrl+clicking another point on the same curve doesn't duplicate in selected_curve_names."""
        # Select first point on curve_a
        point_a1 = curve_widget.curves_data["curve_a"][0]
        screen_pos_1 = curve_widget.data_to_screen(float(point_a1[1]), float(point_a1[2]))
        idx_1, curve_name_1 = curve_widget._find_point_at_multi_curve(screen_pos_1)
        curve_widget._select_point(idx_1, add_to_selection=False, curve_name=curve_name_1)

        assert "curve_a" in curve_widget.selected_curve_names
        initial_count = len([c for c in curve_widget.selected_curve_names if c == "curve_a"])

        # Ctrl+click second point on curve_a
        point_a2 = curve_widget.curves_data["curve_a"][1]
        screen_pos_2 = curve_widget.data_to_screen(float(point_a2[1]), float(point_a2[2]))
        idx_2, curve_name_2 = curve_widget._find_point_at_multi_curve(screen_pos_2)
        curve_widget._select_point(idx_2, add_to_selection=True, curve_name=curve_name_2)

        # Should still only have one entry for curve_a (set prevents duplicates)
        final_count = len([c for c in curve_widget.selected_curve_names if c == "curve_a"])
        assert final_count == initial_count == 1
