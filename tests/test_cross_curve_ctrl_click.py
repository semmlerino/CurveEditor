#!/usr/bin/env python3
"""
Test for cross-curve Ctrl+click point selection visibility.

This test verifies that when a user selects points on different curves using Ctrl+click,
all curves with selected points become visible without requiring "Show all curves" to be enabled.
"""

from typing import cast

import pytest
from PySide6.QtTest import QTest

from core.type_aliases import CurveDataList
from services import get_interaction_service
from stores.application_state import get_application_state
from ui.curve_view_widget import CurveViewWidget


@pytest.fixture
def curve_widget(qtbot):
    """Create a CurveViewWidget with test data."""
    widget = CurveViewWidget()
    qtbot.addWidget(widget)

    # Set up multiple curves
    curves_data = cast(
        dict[str, CurveDataList],
        {
            "curve_a": [
                (1, 10.0, 20.0, "normal"),  # frame, x, y, status
                (2, 15.0, 25.0, "normal"),
                (3, 20.0, 30.0, "normal"),
            ],
            "curve_b": [
                (1, 50.0, 60.0, "normal"),
                (2, 55.0, 65.0, "normal"),
                (3, 60.0, 70.0, "normal"),
            ],
            "curve_c": [
                (1, 100.0, 110.0, "normal"),
                (2, 105.0, 115.0, "normal"),
                (3, 110.0, 120.0, "normal"),
            ],
        },
    )

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
        app_state = get_application_state()

        # Verify initial state
        assert app_state.active_curve == "curve_a"
        assert curve_widget.show_all_curves is False

        # Get screen position of first point on curve_a
        point_a = app_state.get_curve_data("curve_a")[0]
        screen_pos_a = curve_widget.data_to_screen(float(point_a[1]), float(point_a[2]))

        # Click point on curve_a
        interaction_service = get_interaction_service()
        result_a = interaction_service.find_point_at(
            curve_widget, screen_pos_a.x(), screen_pos_a.y(), mode="all_visible"
        )
        assert result_a.index >= 0, "Should find point on curve_a"
        assert result_a.curve_name == "curve_a", "Should identify curve_a"

        # Select the point (simulates mouse click)
        curve_widget._select_point(result_a.index, add_to_selection=False, curve_name=result_a.curve_name)

        # Verify curve_a is in selected_curve_names
        assert "curve_a" in curve_widget.selected_curve_names

        # Get screen position of first point on curve_b
        point_b = app_state.get_curve_data("curve_b")[0]
        screen_pos_b = curve_widget.data_to_screen(float(point_b[1]), float(point_b[2]))

        # Ctrl+click point on curve_b
        result_b = interaction_service.find_point_at(
            curve_widget, screen_pos_b.x(), screen_pos_b.y(), mode="all_visible"
        )
        assert result_b.index >= 0, "Should find point on curve_b"
        assert result_b.curve_name == "curve_b", "Should identify curve_b"

        # Select the point with add_to_selection=True (simulates Ctrl+click)
        curve_widget._select_point(result_b.index, add_to_selection=True, curve_name=result_b.curve_name)

        # Verify both curves are in selected_curve_names
        assert "curve_a" in curve_widget.selected_curve_names, "curve_a should still be selected"
        assert "curve_b" in curve_widget.selected_curve_names, "curve_b should now be selected"

        # Verify active curve switched to curve_b (last selected)
        assert app_state.active_curve == "curve_b"

        # Verify show_all_curves is still False
        assert curve_widget.show_all_curves is False

        # Both curves should be visible according to rendering logic
        # (renderer shows curves in selected_curve_names when show_all_curves is False)

    def test_find_point_at_multi_curve_searches_all_curves(self, curve_widget):
        """Test that find_point_at with mode='all_visible' can find points on any visible curve."""
        app_state = get_application_state()
        interaction_service = get_interaction_service()

        # Get points from different curves
        point_a = app_state.get_curve_data("curve_a")[1]
        point_b = app_state.get_curve_data("curve_b")[1]

        # Get screen positions
        screen_a = curve_widget.data_to_screen(float(point_a[1]), float(point_a[2]))
        screen_b = curve_widget.data_to_screen(float(point_b[1]), float(point_b[2]))

        # Should find points on different curves (verifies cross-curve search works)
        result_a = interaction_service.find_point_at(curve_widget, screen_a.x(), screen_a.y(), mode="all_visible")
        assert (
            result_a.index >= 0 and result_a.curve_name == "curve_a"
        ), f"Should find curve_a, got idx={result_a.index}, name={result_a.curve_name}"

        result_b = interaction_service.find_point_at(curve_widget, screen_b.x(), screen_b.y(), mode="all_visible")
        assert (
            result_b.index >= 0 and result_b.curve_name == "curve_b"
        ), f"Should find curve_b, got idx={result_b.index}, name={result_b.curve_name}"

    def test_selecting_from_different_curve_switches_active(self, curve_widget):
        """Test that selecting a point on a different curve makes it active."""
        app_state = get_application_state()
        interaction_service = get_interaction_service()

        assert app_state.active_curve == "curve_a"

        # Select a point on curve_b
        point_b = app_state.get_curve_data("curve_b")[0]
        screen_pos = curve_widget.data_to_screen(float(point_b[1]), float(point_b[2]))
        result = interaction_service.find_point_at(curve_widget, screen_pos.x(), screen_pos.y(), mode="all_visible")

        curve_widget._select_point(result.index, add_to_selection=False, curve_name=result.curve_name)

        # Active curve should switch to curve_b
        assert app_state.active_curve == "curve_b"

    def test_ctrl_click_on_same_curve_does_not_duplicate(self, curve_widget):
        """Test that Ctrl+clicking another point on the same curve doesn't duplicate in selected_curve_names."""
        app_state = get_application_state()
        interaction_service = get_interaction_service()

        # Select first point on curve_a
        point_a1 = app_state.get_curve_data("curve_a")[0]
        screen_pos_1 = curve_widget.data_to_screen(float(point_a1[1]), float(point_a1[2]))
        result_1 = interaction_service.find_point_at(
            curve_widget, screen_pos_1.x(), screen_pos_1.y(), mode="all_visible"
        )
        curve_widget._select_point(result_1.index, add_to_selection=False, curve_name=result_1.curve_name)

        assert "curve_a" in curve_widget.selected_curve_names
        initial_count = len([c for c in curve_widget.selected_curve_names if c == "curve_a"])

        # Ctrl+click second point on curve_a
        point_a2 = app_state.get_curve_data("curve_a")[1]
        screen_pos_2 = curve_widget.data_to_screen(float(point_a2[1]), float(point_a2[2]))
        result_2 = interaction_service.find_point_at(
            curve_widget, screen_pos_2.x(), screen_pos_2.y(), mode="all_visible"
        )
        curve_widget._select_point(result_2.index, add_to_selection=True, curve_name=result_2.curve_name)

        # Should still only have one entry for curve_a (set prevents duplicates)
        final_count = len([c for c in curve_widget.selected_curve_names if c == "curve_a"])
        assert final_count == initial_count == 1
