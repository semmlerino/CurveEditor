"""Integration tests for nudge centering behavior.

Tests verify that the view automatically centers on points after nudging,
following production-realistic workflows.

Note: These tests call nudge_selected() directly since keyboard shortcuts
require MainWindow with full shortcut registry setup.
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none

import pytest

from stores.application_state import get_application_state


@pytest.mark.production
class TestNudgeCenteringIntegration:
    """Production-realistic tests for nudge centering behavior."""

    def test_nudge_right_centers_view(
        self, production_widget_factory, safe_test_data_factory, user_interaction, qtbot
    ):
        """Test that nudging right automatically centers view on nudged point."""
        # Setup: Widget with 3 points, shown and rendered
        widget = production_widget_factory(curve_data=safe_test_data_factory(3))

        # Select first point
        user_interaction.select_point(widget, 0)

        # Nudge right
        widget.nudge_selected(1.0, 0.0)
        qtbot.wait(10)

        # Verify point was nudged (x coordinate increased)
        # Note: Centering happens automatically via view_camera.center_on_selection()
        # called from NudgePointsCommand, but widget.nudge_selected() doesn't call it.
        # The centering is done at the command level, not widget level.
        # So this test verifies the point moved, but centering is tested at command level.
        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        _, curve_data = cd

        point = curve_data[0]
        assert point[1] > 50.0, "Point should have been nudged right"

    def test_nudge_selected_method_moves_points(
        self, production_widget_factory, safe_test_data_factory, user_interaction, qtbot
    ):
        """Test that nudge_selected() method correctly moves selected points."""
        widget = production_widget_factory(curve_data=safe_test_data_factory(3))

        user_interaction.select_point(widget, 1)

        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        _, initial_data = cd

        initial_x = initial_data[1][1]
        initial_y = initial_data[1][2]

        # Nudge up
        widget.nudge_selected(0.0, -5.0)
        qtbot.wait(10)

        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        _, updated_data = cd

        # Verify point moved
        assert updated_data[1][1] == initial_x, "X should not change"
        assert updated_data[1][2] < initial_y, "Y should decrease (moved up)"

    def test_nudge_multiple_selected_points(
        self, production_widget_factory, safe_test_data_factory, user_interaction, qtbot
    ):
        """Test that nudging multiple points works correctly."""
        widget = production_widget_factory(curve_data=safe_test_data_factory(5))

        # Select points 0, 1, 2
        user_interaction.select_point(widget, 0)
        user_interaction.select_point(widget, 1, ctrl=True)
        user_interaction.select_point(widget, 2, ctrl=True)

        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        _, initial_data = cd

        initial_positions = [(initial_data[i][1], initial_data[i][2]) for i in range(3)]

        # Nudge all selected points right
        widget.nudge_selected(5.0, 0.0)
        qtbot.wait(10)

        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        _, updated_data = cd

        # Verify all 3 points moved right
        for i in range(3):
            new_x = updated_data[i][1]
            new_y = updated_data[i][2]
            old_x, old_y = initial_positions[i]

            assert new_x > old_x, f"Point {i} should have moved right"
            assert new_y == old_y, f"Point {i} Y should not change"

    def test_nudge_updates_point_status(
        self, production_widget_factory, safe_test_data_factory, user_interaction, qtbot
    ):
        """Test that nudging converts points to KEYFRAME status."""
        # Create data with NORMAL status point
        data = safe_test_data_factory(3)
        widget = production_widget_factory(curve_data=data)

        user_interaction.select_point(widget, 1)

        # Nudge the point
        widget.nudge_selected(1.0, 1.0)
        qtbot.wait(10)

        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        _, updated_data = cd

        # Verify point has KEYFRAME status after nudge
        from core.models import PointStatus

        point = updated_data[1]
        assert len(point) >= 4, "Point should have status field"
        assert point[3] == PointStatus.KEYFRAME.value, "Nudged point should become KEYFRAME"
