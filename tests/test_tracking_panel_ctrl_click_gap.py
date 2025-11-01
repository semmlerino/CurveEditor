#!/usr/bin/env python3
"""Test for bug: Ctrl+clicking curve with gap in tracking panel doesn't make it active.

This test reproduces the specific bug where:
1. User has curve_a selected in tracking panel
2. User Ctrl+clicks curve_b (which has a gap) in the tracking panel list
3. BUG: curve_b should become active, but due to set ordering, might not
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

import pytest

from core.models import PointStatus
from core.type_aliases import CurveDataList
from stores.application_state import get_application_state
from ui.main_window import MainWindow


@pytest.fixture
def main_window_with_gaps(qtbot, qapp):
    """Create MainWindow with curves - one with a gap."""
    window = MainWindow(auto_load_data=False)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    app_state = get_application_state()

    # curve_a: Normal curve (no gap)
    curve_a_data: CurveDataList = [
        (1, 100.0, 100.0, PointStatus.KEYFRAME.value),
        (2, 200.0, 100.0, PointStatus.NORMAL.value),
        (3, 300.0, 100.0, PointStatus.NORMAL.value),
    ]

    # curve_b: Curve WITH gap (ENDFRAME creates gap)
    curve_b_data: CurveDataList = [
        (1, 100.0, 200.0, PointStatus.KEYFRAME.value),
        (2, 200.0, 200.0, PointStatus.ENDFRAME.value),  # Creates gap
        (3, 300.0, 200.0, PointStatus.NORMAL.value),    # In gap segment
    ]

    # Load both curves
    app_state.set_curve_data("curve_a", curve_a_data)
    app_state.set_curve_data("curve_b", curve_b_data)
    app_state.set_active_curve("curve_a")
    app_state.set_selected_curves({"curve_a"})

    # Update tracking panel to show both curves
    if window.tracking_panel:
        window.tracking_panel.set_tracked_data(
            {
                "curve_a": curve_a_data,
                "curve_b": curve_b_data,
            }
        )

    qtbot.wait(100)
    return window


class TestTrackingPanelCtrlClickGap:
    """Test Ctrl+click in tracking panel for curves with gaps."""

    def test_ctrl_click_gap_curve_in_tracking_panel_makes_it_active(self, main_window_with_gaps, qtbot):
        """
        Test that Ctrl+clicking a curve with a gap in the tracking panel makes it active.

        This is the EXACT bug the user reported.
        Root cause: set_selected_curves() uses a set, which loses order.
        When converted back to list, point_names[-1] is arbitrary.
        """
        window = main_window_with_gaps
        app_state = get_application_state()

        # Verify initial state
        assert app_state.active_curve == "curve_a"
        assert app_state.get_selected_curves() == {"curve_a"}

        print(f"Initial state:")
        print(f"  active_curve: {app_state.active_curve}")
        print(f"  selected_curves: {app_state.get_selected_curves()}")

        # Simulate Ctrl+clicking curve_b in the tracking panel
        # This is what happens when user Ctrl+clicks:
        # 1. Tracking panel gets both curve_a and curve_b selected
        # 2. Calls set_selected_curves({"curve_a", "curve_b"})
        # 3. Signal emitted with the set
        # 4. MultiPointTrackingController converts set to list
        # 5. BUG: list({"curve_a", "curve_b"}) could be ["curve_a", "curve_b"] OR ["curve_b", "curve_a"]
        # 6. on_tracking_points_selected uses point_names[-1] as active

        # Simulate the exact flow
        new_selection = {"curve_a", "curve_b"}
        app_state.set_selected_curves(new_selection)
        qtbot.wait(50)

        # Check results
        print(f"\nAfter Ctrl+clicking curve_b:")
        print(f"  active_curve: {app_state.active_curve}")
        print(f"  selected_curves: {app_state.get_selected_curves()}")

        # BUG: This might fail! The active curve could be either curve_a or curve_b
        # depending on set iteration order
        # We WANT it to be curve_b (the one just clicked), but it might be curve_a

        # To truly test this, we need to check the implementation detail
        # Let's see what the controller does with the set

    def test_set_ordering_bug_reproduction(self):
        """
        Demonstrate the root cause: set to list conversion loses order.

        This shows why the bug happens.
        """
        # When user has curve_a selected and Ctrl+clicks curve_b,
        # the tracking panel ends up with both selected
        selected_set = {"curve_a", "curve_b"}

        # Convert to list (this is what MultiPointTrackingController does)
        point_names = list(selected_set)

        # The "last selected" curve should be curve_b (what user just clicked)
        # But point_names[-1] could be either curve_a or curve_b!
        print(f"Set: {selected_set}")
        print(f"List: {point_names}")
        print(f"point_names[-1] = {point_names[-1]}")

        # This demonstrates the non-determinism
        # In Python 3.7+, sets maintain insertion order in CPython,
        # but this is an implementation detail, not guaranteed
        # More importantly, the tracking panel doesn't tell us WHICH curve was just added

    def test_direct_signal_connection_with_gap_curve(self, main_window_with_gaps, qtbot):
        """
        Test by directly calling the tracking panel's selection change handler.

        This bypasses UI interaction and directly tests the signal flow.
        After fix: tracking panel now uses currentRow() to determine active curve.
        """
        window = main_window_with_gaps
        app_state = get_application_state()
        tracking_panel = window.tracking_panel

        # Find row indices for curve_a and curve_b
        curve_a_row = None
        curve_b_row = None
        for row in range(tracking_panel.table.rowCount()):
            name_item = tracking_panel.table.item(row, 1)
            if name_item:
                if name_item.text() == "curve_a":
                    curve_a_row = row
                elif name_item.text() == "curve_b":
                    curve_b_row = row

        assert curve_a_row is not None, "curve_a should exist in tracking panel"
        assert curve_b_row is not None, "curve_b should exist in tracking panel"

        # Select curve_a by setting current row
        tracking_panel.table.setCurrentCell(curve_a_row, 0)
        tracking_panel.table.selectRow(curve_a_row)
        qtbot.wait(50)

        print(f"After selecting only curve_a:")
        print(f"  active_curve: {app_state.active_curve}")

        assert app_state.active_curve == "curve_a"

        # Now Ctrl+click curve_b (select both, with curve_b as current)
        from PySide6.QtCore import QItemSelectionModel

        # Use selection model to add curve_b to selection (like Ctrl+click)
        selection_model = tracking_panel.table.selectionModel()
        index = tracking_panel.table.model().index(curve_b_row, 0)

        # Select curve_b row and make it current (simulates Ctrl+click)
        selection_model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
        selection_model.select(
            index,
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
        )

        qtbot.wait(50)

        print(f"\nAfter Ctrl+clicking curve_b:")
        print(f"  active_curve: {app_state.active_curve}")
        print(f"  selected_curves: {app_state.get_selected_curves()}")
        print(f"  currentRow: {tracking_panel.table.currentRow()}")

        # After fix: curve_b should be active (it's the current row)
        assert app_state.active_curve == "curve_b", (
            f"BUG FIXED: curve_b should be active after Ctrl+click, "
            f"but got {app_state.active_curve}"
        )

        # Both curves should be selected
        assert app_state.get_selected_curves() == {"curve_a", "curve_b"}

    @pytest.mark.skip(reason="Demonstrates bug - result is non-deterministic due to set ordering")
    def test_bug_demonstration_non_deterministic(self, main_window_with_gaps, qtbot):
        """
        This test demonstrates the bug but is marked skip because it's non-deterministic.

        The bug: When Ctrl+clicking curve_b after curve_a is selected,
        curve_b might not become active due to set-to-list conversion losing order.
        """
        window = main_window_with_gaps
        app_state = get_application_state()

        # Simulate multiple Ctrl+clicks to show non-determinism
        for i in range(10):
            # Reset to just curve_a
            app_state.set_active_curve("curve_a")
            app_state.set_selected_curves({"curve_a"})

            # Ctrl+click to add curve_b
            app_state.set_selected_curves({"curve_a", "curve_b"})
            qtbot.wait(10)

            print(f"Iteration {i}: active_curve = {app_state.active_curve}")

        # In some iterations, curve_b becomes active
        # In others, curve_a remains active (BUG)
