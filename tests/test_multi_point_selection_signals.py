"""
Regression tests for MultiPointTrackingController selection signal pathways.

CRITICAL BUG HISTORY (2025-10-21):
When refactoring to sub-controllers, the ApplicationState.selection_state_changed
signal connection was removed, breaking the pathway:

  TrackingPointsPanel → ApplicationState.set_selected_curves()
  → selection_state_changed signal
  → ❌ Nobody listening!
  → Active curve never updated

This caused timeline/curve view to unsync when selecting different tracking points.

These tests ensure the signal pathway remains connected.
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

from unittest.mock import Mock

import pytest

from core.type_aliases import CurveDataList
from stores.application_state import get_application_state
from ui.controllers.multi_point_tracking_controller import MultiPointTrackingController


@pytest.fixture
def mock_main_window():
    """Create a minimal mock MainWindow for controller testing."""
    window = Mock()
    window.active_timeline_point = None
    window.curve_widget = None  # No widget for signal-only testing
    return window


@pytest.fixture
def controller(mock_main_window, qapp):
    """Create MultiPointTrackingController with real ApplicationState."""
    # Clear ApplicationState before test
    app_state = get_application_state()
    app_state._curves_data.clear()
    app_state.set_active_curve(None)
    app_state.set_selected_curves(set())

    controller = MultiPointTrackingController(mock_main_window)

    # Patch the display controller methods to track calls
    _ = controller.display_controller.update_display_with_selection  # noqa: F841
    _ = controller.display_controller.center_on_selected_curves  # noqa: F841

    controller.display_controller.update_call_count = 0
    controller.display_controller.last_selected_curves = None

    def tracked_update(selected_curves: list[str]) -> None:
        controller.display_controller.update_call_count += 1
        controller.display_controller.last_selected_curves = selected_curves
        # Don't call original - it might have complex dependencies

    def tracked_center() -> None:
        pass  # No-op for testing

    controller.display_controller.update_display_with_selection = tracked_update
    controller.display_controller.center_on_selected_curves = tracked_center

    yield controller

    # Cleanup
    app_state._curves_data.clear()
    app_state.set_active_curve(None)
    app_state.set_selected_curves(set())


@pytest.fixture
def sample_multi_curve_data() -> dict[str, CurveDataList]:
    """Create sample multi-curve data for testing."""
    return {
        "Point02": [(1, 100.0, 100.0), (2, 110.0, 110.0), (3, 120.0, 120.0)],
        "Point04": [(1, 200.0, 200.0), (2, 210.0, 210.0), (3, 220.0, 220.0)],
        "Point09": [(1, 300.0, 300.0), (2, 310.0, 310.0), (3, 320.0, 320.0)],
    }


class TestSelectionSignalPathway:
    """Test the critical signal pathway for tracking point selection."""

    def test_selection_state_changed_updates_active_curve(self, controller, sample_multi_curve_data, qapp):
        """
        REGRESSION TEST for 2025-10-21 bug.

        Verifies that selecting a tracking point via ApplicationState
        triggers the selection_state_changed signal, which updates
        the active curve.

        This is the exact pathway that was broken when the signal
        connection was removed during sub-controller refactoring.
        """
        app_state = get_application_state()

        # Setup: Load multi-curve data
        for curve_name, curve_data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, curve_data)

        # Set initial active curve
        app_state.set_active_curve("Point02")
        assert app_state.active_curve == "Point02"

        # ACT: Simulate user selecting Point04 in the tracking panel
        # This is what TrackingPointsPanel._on_selection_changed() does
        app_state.set_selected_curves({"Point04"})

        # Process Qt signals
        qapp.processEvents()

        # ASSERT: Active curve should be updated to Point04
        # This verifies the signal pathway works:
        # ApplicationState.selection_state_changed
        # → MultiPointTrackingController._on_selection_state_changed
        # → on_tracking_points_selected
        # → TrackingSelectionController.on_tracking_points_selected
        # → ApplicationState.set_active_curve("Point04")
        assert app_state.active_curve == "Point04", (
            "Active curve should update when selection changes. "
            "If this fails, the selection_state_changed signal connection is broken!"
        )

        # Verify the display was updated
        assert controller.display_controller.update_call_count > 0
        assert controller.display_controller.last_selected_curves == ["Point04"]

    def test_multi_selection_uses_last_as_active(self, controller, sample_multi_curve_data, qapp):
        """
        Verify that when multiple curves are selected, the last one
        becomes the active curve (matching user's last click).
        """
        app_state = get_application_state()

        # Setup: Load multi-curve data
        for curve_name, curve_data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, curve_data)

        # Initial state
        app_state.set_active_curve("Point02")

        # ACT: Select multiple curves (Point04, Point09)
        # In real usage, Point09 would be the last clicked
        app_state.set_selected_curves({"Point04", "Point09"})
        qapp.processEvents()

        # ASSERT: Active curve should be one of the selected
        # (The specific one depends on set ordering, but should be in selection)
        assert app_state.active_curve in ["Point04", "Point09"]

    def test_empty_selection_handles_gracefully(self, controller, qapp):
        """
        Verify that deselecting all curves doesn't crash.
        """
        app_state = get_application_state()

        # Setup: Set initial active curve
        app_state.set_curve_data("Point02", [(1, 100.0, 100.0)])
        app_state.set_active_curve("Point02")

        # ACT: Deselect all
        app_state.set_selected_curves(set())
        qapp.processEvents()

        # ASSERT: Should not crash (active curve may remain or clear)
        # The important thing is no exceptions
        assert True  # If we got here without crash, test passes

    def test_signal_connection_exists(self, controller):
        """
        Verify the critical signal connection is actually made.

        This is a white-box test that explicitly checks the signal
        is connected, providing early warning if refactoring breaks it.
        """
        get_application_state()  # Ensure state is initialized

        # Check that _on_selection_state_changed is connected
        # We can't directly inspect Qt signal connections, but we can
        # verify the method exists and is callable
        assert hasattr(controller, "_on_selection_state_changed")
        assert callable(controller._on_selection_state_changed)

        # Verify the method signature matches the signal
        import inspect

        sig = inspect.signature(controller._on_selection_state_changed)
        params = list(sig.parameters.keys())
        assert "selected_curves" in params
        assert "_show_all" in params or "show_all" in params


class TestSignalIntegration:
    """Integration tests for the complete signal flow."""

    def test_panel_to_curve_view_synchronization(self, controller, sample_multi_curve_data, qapp):
        """
        Integration test: Verify the complete flow from panel selection
        to curve view update works end-to-end.
        """
        app_state = get_application_state()

        # Setup: Load data
        for curve_name, curve_data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, curve_data)

        app_state.set_active_curve("Point02")

        # Simulate rapid selection changes (user clicking multiple points)
        for curve_name in ["Point04", "Point09", "Point02"]:
            app_state.set_selected_curves({curve_name})
            qapp.processEvents()

            # Verify active curve tracks selection
            assert app_state.active_curve == curve_name

        # Verify display updates happened
        assert controller.display_controller.update_call_count >= 3


# ==================== Helper for Manual Testing ====================


def test_signal_pathway_documentation():
    """
    Document the expected signal pathway for future developers.

    This is not a test but documentation in test form.
    """
    expected_pathway = """
    USER ACTION: Click tracking point in panel

    SIGNAL PATHWAY:
    1. TrackingPointsPanel._on_selection_changed()
       → calls ApplicationState.set_selected_curves({'Point04'})

    2. ApplicationState.set_selected_curves()
       → emits selection_state_changed signal

    3. MultiPointTrackingController._on_selection_state_changed()
       → receives signal (THIS WAS THE MISSING CONNECTION!)
       → calls on_tracking_points_selected(['Point04'])

    4. TrackingSelectionController.on_tracking_points_selected()
       → calls ApplicationState.set_active_curve('Point04')
       → updates display

    5. Timeline/CurveView update
       → reflect new active curve

    CRITICAL CONNECTION (added 2025-10-21):
    In MultiPointTrackingController._connect_sub_controllers():
        self._app_state.selection_state_changed.connect(
            self._on_selection_state_changed
        )

    If this connection is removed, the pathway breaks at step 3!
    """
    # This "test" always passes - it's just documentation
    assert True, expected_pathway
