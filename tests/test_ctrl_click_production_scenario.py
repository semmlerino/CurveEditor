"""Test Ctrl+click behavior in production-like scenarios.

This test file validates that Ctrl+click works correctly WITHOUT manually
updating the screen points cache - simulating real user interactions.
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from stores.application_state import get_application_state


class TestCtrlClickProductionScenario:
    """Test Ctrl+click behavior as a user would experience it."""

    def test_ctrl_click_without_manual_cache_update(self, curve_view_widget, qtbot):
        """Test that Ctrl+click works without manually updating cache.

        This simulates the real production scenario where users just click,
        and the cache should be updated automatically through normal widget lifecycle.
        """
        # Setup: Create curve with points
        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0), (3, 300.0, 300.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")
        curve_view_widget.set_curve_data(test_data)

        # Show widget and wait for it to be rendered
        curve_view_widget.show()
        qtbot.waitExposed(curve_view_widget)
        qtbot.wait(50)  # Allow paint event to complete

        # CRITICAL: Do NOT call curve_view_widget._update_screen_points_cache()
        # This tests the real production scenario

        # Get screen positions by asking the spatial index
        # (This is what the production code does)
        from services import get_interaction_service

        interaction_service = get_interaction_service()

        # Search for first point
        result1 = interaction_service.find_point_at(curve_view_widget, 100, 100, mode="active")
        assert result1.found, "Should find first point using spatial index"
        point1_idx = result1.index

        # Click first point (normal click - should select it)
        from PySide6.QtCore import QPointF

        from services import get_transform_service

        transform = get_transform_service().get_transform(curve_view_widget)

        # Get screen coordinates for point 0
        screen_x1, screen_y1 = transform.data_to_screen(100.0, 100.0)

        QTest.mouseClick(
            curve_view_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPointF(screen_x1, screen_y1).toPoint(),
        )
        qtbot.wait(10)

        # Verify first point selected
        assert curve_view_widget.selected_indices == {
            point1_idx
        }, f"Expected {{{point1_idx}}}, got {curve_view_widget.selected_indices}"

        # Now Ctrl+click second point
        screen_x2, screen_y2 = transform.data_to_screen(200.0, 200.0)

        QTest.mouseClick(
            curve_view_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
            QPointF(screen_x2, screen_y2).toPoint(),
        )
        qtbot.wait(10)

        # Should have BOTH points selected
        result2 = interaction_service.find_point_at(curve_view_widget, screen_x2, screen_y2, mode="active")
        assert result2.found, "Should find second point"
        point2_idx = result2.index

        selection = curve_view_widget.selected_indices
        assert len(selection) == 2, f"Expected 2 points selected, got {len(selection)}: {selection}"
        assert point1_idx in selection, f"Point {point1_idx} should still be selected"
        assert point2_idx in selection, f"Point {point2_idx} should be selected after Ctrl+click"

    def test_ctrl_click_after_zoom(self, curve_view_widget, qtbot):
        """Test that Ctrl+click works correctly after zooming.

        This tests the scenario where cache might be invalidated.
        """
        # Setup
        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")
        curve_view_widget.set_curve_data(test_data)

        curve_view_widget.show()
        qtbot.waitExposed(curve_view_widget)
        qtbot.wait(50)

        # Zoom in
        curve_view_widget.zoom_factor = 2.0
        curve_view_widget.update()
        qtbot.wait(10)

        # Now try Ctrl+click selection
        from services import get_transform_service

        transform = get_transform_service().get_transform(curve_view_widget)

        screen_x1, screen_y1 = transform.data_to_screen(100.0, 100.0)
        screen_x2, screen_y2 = transform.data_to_screen(200.0, 200.0)

        # Select first point
        from PySide6.QtCore import QPointF

        QTest.mouseClick(
            curve_view_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPointF(screen_x1, screen_y1).toPoint(),
        )
        qtbot.wait(10)

        # Ctrl+click second point
        QTest.mouseClick(
            curve_view_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
            QPointF(screen_x2, screen_y2).toPoint(),
        )
        qtbot.wait(10)

        # Verify both selected
        selection = curve_view_widget.selected_indices
        assert len(selection) == 2, f"Expected 2 points after zoom+ctrl+click, got {len(selection)}"

    def test_ctrl_click_multi_curve_vs_point_selection(self, curve_view_widget, qtbot):
        """Test the distinction between curve-level and point-level selection.

        This tests what happens when a user has multiple curves and Ctrl+clicks:
        - Ctrl+click on a point in the ACTIVE curve should toggle point selection
        - Ctrl+click on a point in a DIFFERENT curve should toggle curve selection
        """
        app_state = get_application_state()

        # Create two curves
        curve1_data = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        curve2_data = [(1, 300.0, 300.0), (2, 400.0, 400.0)]

        app_state.set_curve_data("curve1", curve1_data)
        app_state.set_curve_data("curve2", curve2_data)
        app_state.set_active_curve("curve1")
        app_state.set_show_all_curves(True)  # Show all curves

        curve_view_widget.show()
        qtbot.waitExposed(curve_view_widget)
        qtbot.wait(50)

        from services import get_transform_service

        transform = get_transform_service().get_transform(curve_view_widget)

        # Get screen coordinates for points in both curves
        screen_x1, screen_y1 = transform.data_to_screen(100.0, 100.0)  # curve1, point 0
        screen_x2, screen_y2 = transform.data_to_screen(200.0, 200.0)  # curve1, point 1
        screen_x3, screen_y3 = transform.data_to_screen(300.0, 300.0)  # curve2, point 0

        from PySide6.QtCore import QPointF

        # Step 1: Click point in curve1 (should select point 0 in curve1)
        QTest.mouseClick(
            curve_view_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPointF(screen_x1, screen_y1).toPoint(),
        )
        qtbot.wait(10)

        # Should have curve1 as active with point 0 selected
        assert app_state.active_curve == "curve1"
        assert 0 in app_state.get_selection("curve1"), "Point 0 should be selected in curve1"

        # Step 2: Ctrl+click another point in the SAME curve (should add to selection)
        QTest.mouseClick(
            curve_view_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
            QPointF(screen_x2, screen_y2).toPoint(),
        )
        qtbot.wait(10)

        # Should have BOTH points selected in curve1 (point-level selection within active curve)
        selection = app_state.get_selection("curve1")
        assert len(selection) == 2, f"Expected 2 points selected in curve1, got {len(selection)}: {selection}"
        assert 0 in selection and 1 in selection, "Both points should be selected in curve1"

        # Step 3: Ctrl+click point in DIFFERENT curve (should toggle curve-level selection)
        QTest.mouseClick(
            curve_view_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
            QPointF(screen_x3, screen_y3).toPoint(),
        )
        qtbot.wait(10)

        # Should have switched to curve2 as active
        assert app_state.active_curve == "curve2", "Active curve should switch to curve2"

        # Should have curve-level selection updated (curve2 added to selected curves)
        selected_curves = app_state.get_selected_curves()
        assert "curve2" in selected_curves, f"curve2 should be in selected curves: {selected_curves}"

    def test_ctrl_click_state_persistence(self, curve_view_widget, qtbot):
        """Test that Ctrl+click selection persists correctly.

        Verify that after multiple Ctrl+clicks, the selection state is correctly
        maintained and doesn't get lost or reset unexpectedly.
        """
        app_state = get_application_state()
        # NOTE: Avoid (0,0) screen coordinates - QTest.mouseClick has boundary issues
        # Start from 50.0 to ensure all points are away from widget edges
        test_data = [(i + 1, float(50 + i * 100), float(50 + i * 100)) for i in range(5)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")
        curve_view_widget.set_curve_data(test_data)

        curve_view_widget.show()
        qtbot.waitExposed(curve_view_widget)
        qtbot.wait(50)

        from PySide6.QtCore import QPointF

        from services import get_transform_service

        transform = get_transform_service().get_transform(curve_view_widget)

        # Select points 0, 1, 2 via Ctrl+click
        for i in range(3):
            data_x = float(50 + i * 100)
            data_y = float(50 + i * 100)
            screen_x, screen_y = transform.data_to_screen(data_x, data_y)
            modifier = Qt.KeyboardModifier.NoModifier if i == 0 else Qt.KeyboardModifier.ControlModifier

            QTest.mouseClick(
                curve_view_widget, Qt.MouseButton.LeftButton, modifier, QPointF(screen_x, screen_y).toPoint()
            )
            qtbot.wait(10)

        # Verify all three points are selected
        selection = app_state.get_selection("test_curve")
        assert len(selection) == 3, f"Expected 3 points selected, got {len(selection)}: {selection}"
        assert {0, 1, 2}.issubset(selection), "Points 0, 1, 2 should all be selected"

        # Now Ctrl+click one of the already-selected points (should deselect it)
        # Click point at index 1 (data coordinates 150, 150)
        screen_x, screen_y = transform.data_to_screen(150.0, 150.0)
        QTest.mouseClick(
            curve_view_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
            QPointF(screen_x, screen_y).toPoint(),
        )
        qtbot.wait(10)

        # Point 1 should be deselected, points 0 and 2 should remain
        selection = app_state.get_selection("test_curve")
        assert len(selection) == 2, f"Expected 2 points after deselecting point 1, got {len(selection)}: {selection}"
        assert 1 not in selection, "Point 1 should be deselected"
        assert 0 in selection and 2 in selection, "Points 0 and 2 should remain selected"
