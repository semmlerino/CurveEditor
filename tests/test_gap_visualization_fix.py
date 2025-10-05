#!/usr/bin/env python3
"""
Tests for gap visualization fix in multi-curve rendering.

These tests verify that both single-curve and multi-curve rendering pathways
show gaps correctly when points have endframe status, fixing the issue where
manual selection would break gap visualization.
"""

from typing import cast
from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

# CurveEditor specific imports
from core.type_aliases import PointTuple4Str
from ui.curve_view_widget import CurveViewWidget


@pytest.fixture(scope="session")
def qapp():
    """Shared QApplication for all tests."""
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


@pytest.fixture
def curve_widget(qtbot) -> CurveViewWidget:
    """CurveViewWidget with cleanup."""
    widget = CurveViewWidget()
    qtbot.addWidget(widget)  # CRITICAL: Auto cleanup
    return widget


class TestGetLiveCurvesDataMethod:
    """Unit tests for _get_live_curves_data method - the core fix."""

    def test_get_live_curves_data_no_curves_data(self, curve_widget):
        """Test with no curves in ApplicationState - should return empty dict."""
        from stores.application_state import reset_application_state

        # Ensure ApplicationState has no curves
        reset_application_state()

        # curves_data property should return empty dict when no curves exist
        assert curve_widget.curves_data == {}

        result = curve_widget._get_live_curves_data()

        assert result == {}

    def test_get_live_curves_data_empty_curves_data(self, curve_widget):
        """Test with empty curves_data - should return empty dict."""
        from stores.application_state import reset_application_state

        # Ensure ApplicationState is empty
        reset_application_state()

        result = curve_widget._get_live_curves_data()

        assert result == {}

    def test_get_live_curves_data_no_active_curve(self, curve_widget):
        """Test with curves but no active curve - should return original data."""
        from stores.application_state import get_application_state

        test_curves_data = {
            "Track1": [(1, 10.0, 20.0, "keyframe"), (2, 30.0, 40.0, "normal")],
            "Track2": [(1, 50.0, 60.0, "normal"), (3, 70.0, 80.0, "endframe")],
        }

        # Set curves via set_curves_data method
        curve_widget.set_curves_data(test_curves_data)

        # Ensure no active curve
        app_state = get_application_state()
        app_state.set_active_curve(None)

        result = curve_widget._get_live_curves_data()

        assert result == test_curves_data
        # Ensure it's a copy, not the same object
        assert result is not test_curves_data

    def test_get_live_curves_data_active_curve_not_in_data(self, curve_widget):
        """Test with active curve that doesn't exist in curves_data."""
        from stores.application_state import get_application_state

        test_curves_data = {"Track1": [(1, 10.0, 20.0, "keyframe")], "Track2": [(2, 30.0, 40.0, "normal")]}

        # Set curves via set_curves_data method
        curve_widget.set_curves_data(test_curves_data)

        # Set active curve to nonexistent track
        app_state = get_application_state()
        app_state.set_active_curve("NonexistentTrack")

        result = curve_widget._get_live_curves_data()

        assert result == test_curves_data

    def test_get_live_curves_data_replaces_active_curve_with_live_data(self, curve_widget):
        """Test the core fix - active curve data replaced with live store data."""

        # Setup static curves data (stale)
        static_curves_data = {
            "Track1": [(1, 10.0, 20.0, "keyframe"), (2, 30.0, 40.0, "normal")],
            "Track2": [(1, 50.0, 60.0, "normal")],
        }

        # Set curves via set_curves_data method with active curve
        curve_widget.set_curves_data(static_curves_data, active_curve="Track1")

        # Setup live store data (current with status changes)
        live_store_data = [(1, 10.0, 20.0, "keyframe"), (2, 30.0, 40.0, "endframe")]  # Status changed!
        curve_widget._curve_store = Mock()
        curve_widget._curve_store.get_data.return_value = live_store_data

        result = curve_widget._get_live_curves_data()

        # Active curve should have live data, inactive curves unchanged
        expected = {
            "Track1": live_store_data,  # Replaced with live data
            "Track2": [(1, 50.0, 60.0, "normal")],  # Unchanged static data
        }
        assert result == expected

        # Verify the store was queried
        curve_widget._curve_store.get_data.assert_called_once()

    def test_get_live_curves_data_no_curve_store(self, curve_widget):
        """Test when curve store doesn't exist - should return original data."""

        test_curves_data = {
            "Track1": [(1, 10.0, 20.0, "keyframe")],
        }

        # Set curves via set_curves_data method with active curve
        curve_widget.set_curves_data(test_curves_data, active_curve="Track1")

        # Temporarily remove _curve_store to test fallback (restore after test)
        original_store = curve_widget._curve_store
        try:
            delattr(curve_widget, "_curve_store")
            result = curve_widget._get_live_curves_data()
            assert result == test_curves_data
        finally:
            # Restore _curve_store for cleanup
            curve_widget._curve_store = original_store

    def test_get_live_curves_data_empty_live_store(self, curve_widget):
        """Test when curve store returns empty data - should keep static data."""
        static_curves_data = {
            "Track1": [(1, 10.0, 20.0, "keyframe")],
        }

        # Set curves via set_curves_data method with active curve
        curve_widget.set_curves_data(static_curves_data, active_curve="Track1")

        # Store returns empty data
        curve_widget._curve_store = Mock()
        curve_widget._curve_store.get_data.return_value = []

        result = curve_widget._get_live_curves_data()

        # Should keep static data when live data is empty
        assert result == static_curves_data


class TestGapVisualizationBehavior:
    """Integration tests for gap visualization in rendering."""

    def test_single_curve_rendering_shows_gaps(self, qtbot, curve_widget):
        """Test that single-curve mode shows gaps correctly (regression test)."""
        # Create curve data with endframe point to create a gap
        curve_data = [
            (1, 10.0, 20.0, "keyframe"),
            (5, 30.0, 40.0, "endframe"),  # Creates gap after frame 5
            (10, 50.0, 60.0, "keyframe"),
        ]

        # Set single-curve data
        curve_widget.set_curve_data(curve_data)

        # Verify data was set correctly
        assert len(curve_widget.curve_data) == 3
        assert curve_widget.curve_data[1][3] == "endframe"  # Status preserved

        # Force a paint event to trigger rendering
        curve_widget.show()
        qtbot.waitExposed(curve_widget)
        qtbot.wait(100)  # Allow paint events to process

        # Verify the widget has the right data for rendering
        assert curve_widget.points == curve_data  # Points property for renderer

    def test_multi_curve_rendering_uses_live_data(self, qtbot, curve_widget):
        """Test that multi-curve mode uses live data from the fix."""
        # Setup multi-curve scenario
        static_curves_data = {
            "Track1": [(1, 10.0, 20.0, "keyframe"), (5, 30.0, 40.0, "normal")],  # Original
            "Track2": [(2, 50.0, 60.0, "normal")],
        }

        from stores.application_state import get_application_state

        # Set curves via set_curves_data method with active curve
        curve_widget.set_curves_data(static_curves_data, active_curve="Track1")

        # Set display mode via ApplicationState
        app_state = get_application_state()
        app_state.set_show_all_curves(True)

        # Live store has status change for Track1
        live_data_with_gap = [(1, 10.0, 20.0, "keyframe"), (5, 30.0, 40.0, "endframe")]  # Changed to endframe
        curve_widget._curve_store = Mock()
        curve_widget._curve_store.get_data.return_value = live_data_with_gap

        # Get the data that would be passed to renderer
        live_curves = curve_widget._get_live_curves_data()

        # Verify active curve has live data with gap-creating endframe
        assert live_curves["Track1"] == live_data_with_gap
        assert live_curves["Track1"][1][3] == "endframe"  # Gap-creating status
        assert live_curves["Track2"] == static_curves_data["Track2"]  # Unchanged

    @patch("ui.curve_view_widget.logger")
    def test_live_data_logging(self, mock_logger, curve_widget):
        """Test that live data replacement is properly logged."""
        # Set curves via set_curves_data method with active curve
        curve_widget.set_curves_data({"Track1": [(1, 10.0, 20.0)]}, active_curve="Track1")

        live_data = [(1, 10.0, 20.0, "endframe")]
        curve_widget._curve_store = Mock()
        curve_widget._curve_store.get_data.return_value = live_data

        curve_widget._get_live_curves_data()

        # Verify debug logging occurred
        mock_logger.debug.assert_called_with("Using live curve store data for active curve 'Track1' (1 points)")

    @patch("ui.curve_view_widget.logger")
    def test_empty_live_data_logging(self, mock_logger, curve_widget):
        """Test logging when no live data is available."""
        # Set curves via set_curves_data method with active curve
        curve_widget.set_curves_data({"Track1": [(1, 10.0, 20.0)]}, active_curve="Track1")

        curve_widget._curve_store = Mock()
        curve_widget._curve_store.get_data.return_value = []  # Empty

        curve_widget._get_live_curves_data()

        # Verify warning logged
        mock_logger.debug.assert_called_with("No live data available for active curve 'Track1'")


class TestOriginalBugReproduction:
    """Tests that reproduce and verify the fix for the original bug."""

    def test_original_bug_scenario_would_fail_without_fix(self, qtbot, curve_widget):
        """
        Test that reproduces the original bug scenario.

        This test would have failed before the fix and passes after the fix.
        It simulates the exact user workflow that exposed the bug.
        """
        # Step 1: Load multi-point data (triggers multi-curve mode)
        multi_curve_data = {
            "Track1": [(1, 100.0, 100.0, "keyframe"), (10, 200.0, 150.0, "normal")],
            "Track2": [(5, 150.0, 120.0, "normal"), (15, 250.0, 180.0, "keyframe")],
        }

        # Set curves via set_curves_data method with active curve and selected curves
        curve_widget.set_curves_data(multi_curve_data, active_curve="Track1", selected_curves=["Track1"])

        # Set display mode via ApplicationState (show selected only)
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_show_all_curves(False)  # Display mode will be SELECTED

        # Step 2: Simulate user setting point to endframe (superior implementation works)
        # This updates the curve store but NOT the static curves_data
        updated_live_data = [(1, 100.0, 100.0, "keyframe"), (10, 200.0, 150.0, "endframe")]
        curve_widget._curve_store = Mock()
        curve_widget._curve_store.get_data.return_value = updated_live_data

        # Step 3: Simulate manual selection in side pane (inferior implementation)
        # Before fix: This would use stale static curves_data without endframe status
        # After fix: This uses live data from _get_live_curves_data()

        live_curves = curve_widget._get_live_curves_data()

        # Step 4: Verify the fix - active curve has endframe status for gap visualization
        assert live_curves["Track1"][1][3] == "endframe"  # Gap-creating status preserved

        # This is the core of the fix: multi-curve rendering now gets live data
        # with status changes, so gaps will be visualized correctly

    def test_timeline_gap_vs_curve_gap_consistency(self, qtbot, curve_widget):
        """
        Test that ensures timeline and curve gaps are consistent.

        This was the core symptom: timeline showed gaps but curve didn't.
        """
        # Setup scenario with endframe creating a gap
        curve_widget.set_curves_data(
            {"ActiveTrack": [(1, 10.0, 10.0, "keyframe"), (5, 20.0, 20.0, "normal")]}, active_curve="ActiveTrack"
        )

        # Simulate status change that creates gap (would update timeline)
        live_data_with_gap = [(1, 10.0, 10.0, "keyframe"), (5, 20.0, 20.0, "endframe")]
        curve_widget._curve_store = Mock()
        curve_widget._curve_store.get_data.return_value = live_data_with_gap

        # Get data that multi-curve renderer would use
        renderer_data = curve_widget._get_live_curves_data()

        # Verify curve renderer gets the same gap-creating data that timeline has
        assert renderer_data["ActiveTrack"][1][3] == "endframe"

        # This ensures both timeline AND curve will show gaps consistently


class TestEdgeCasesAndRobustness:
    """Test edge cases and error conditions."""

    def test_type_safety_with_various_data_formats(self, curve_widget):
        """Test handling of different curve data tuple formats."""
        # Test with various tuple lengths (3-element and 4-element tuples)
        mixed_curves_data = {
            "Track1": [(1, 10.0, 20.0), (2, 30.0, 40.0, "keyframe")],  # Mixed formats
            "Track2": [(3, 50.0, 60.0, "normal")],
        }

        # Set curves via set_curves_data method with active curve
        curve_widget.set_curves_data(mixed_curves_data, active_curve="Track1")

        live_data = [(1, 10.0, 20.0, "endframe"), (2, 30.0, 40.0, "keyframe")]
        curve_widget._curve_store = Mock()
        curve_widget._curve_store.get_data.return_value = live_data

        result = curve_widget._get_live_curves_data()

        # Should handle mixed formats gracefully
        assert result["Track1"] == live_data
        assert result["Track2"] == mixed_curves_data["Track2"]

    def test_memory_efficiency_creates_copy(self, curve_widget):
        """Test that original curves_data is not modified."""
        from stores.application_state import get_application_state

        original_data = {"Track1": [(1, 10.0, 20.0, "keyframe")]}

        # Set curves via set_curves_data method with active curve
        curve_widget.set_curves_data(original_data, active_curve="Track1")

        live_data = [(1, 10.0, 20.0, "endframe")]  # Different status
        curve_widget._curve_store = Mock()
        curve_widget._curve_store.get_data.return_value = live_data

        result = curve_widget._get_live_curves_data()

        # ApplicationState should be unchanged
        app_state = get_application_state()
        stored_data = app_state.get_curve_data("Track1")
        assert cast(PointTuple4Str, stored_data[0])[3] == "keyframe"  # ApplicationState data preserved
        assert cast(PointTuple4Str, result["Track1"][0])[3] == "endframe"  # Result has live data
        assert result is not original_data  # Different objects


# TDD-style test that would have caught the original bug
def test_gap_visualization_tdd_style(qtbot):
    """
    TDD-style test that would have caught the gap visualization bug.

    This test follows the RED-GREEN-REFACTOR pattern from the testing guide.
    It would have failed before the fix (RED) and passes after (GREEN).
    """
    # Arrange: Setup multi-curve scenario like real usage
    widget = CurveViewWidget()
    qtbot.addWidget(widget)

    # Act: Simulate the exact bug scenario
    # 1. Multi-curve data loaded
    widget.set_curves_data(
        {"MainTrack": [(1, 100, 100, "keyframe"), (10, 200, 150, "normal")]}, active_curve="MainTrack"
    )

    # 2. User changes point status (updates curve store)
    widget._curve_store = Mock()
    widget._curve_store.get_data.return_value = [
        (1, 100, 100, "keyframe"),
        (10, 200, 150, "endframe"),  # Changed to create gap
    ]

    # 3. Manual selection triggers multi-curve rendering
    live_data = widget._get_live_curves_data()

    # Assert: The fix ensures multi-curve rendering gets live data
    # Before fix: This would have failed - static data wouldn't have endframe
    # After fix: This passes - live data has endframe for gap visualization
    assert (
        cast(PointTuple4Str, live_data["MainTrack"][1])[3] == "endframe"
    ), "Multi-curve rendering must use live data with status changes for gap visualization"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
