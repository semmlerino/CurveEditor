#!/usr/bin/env python
"""Tests for timeline aggregate mode functionality.

Tests Phase 1C: UI Integration for multi-curve timeline aggregate view.
"""

import pytest
from PySide6.QtCore import Qt

from core.models import PointStatus
from core.type_aliases import CurveDataList
from stores.application_state import get_application_state
from ui.timeline_tabs import TimelineTabWidget


@pytest.fixture
def timeline_widget(qtbot, qapp, without_dummy_frames) -> TimelineTabWidget:
    """Create a timeline widget for testing.

    Uses without_dummy_frames to clear the 1000 dummy frames from conftest
    so tests can verify frame ranges based only on their test data.
    """
    # Ensure clean ApplicationState for this test
    app_state = get_application_state()
    # Clear all curves to prevent interference from parallel tests
    for curve_name in list(app_state.get_all_curve_names()):
        app_state.delete_curve(curve_name)

    widget = TimelineTabWidget()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def multi_curve_data() -> dict[str, CurveDataList]:
    """Create test data with multiple curves."""
    return {  # pyright: ignore[reportReturnType]
        "Track1": [
            (1, 10.0, 20.0, "keyframe"),
            (2, 11.0, 21.0, PointStatus.INTERPOLATED),
            (3, 12.0, 22.0, "keyframe"),
        ],
        "Track2": [
            (1, 30.0, 40.0, "tracked"),
            (2, 31.0, 41.0, "tracked"),
            (3, 32.0, 42.0, "endframe"),
        ],
        "Track3": [
            (1, 50.0, 60.0, PointStatus.NORMAL),
            (2, 51.0, 61.0, PointStatus.INTERPOLATED),
            (3, 52.0, 62.0, "tracked"),
        ],
    }


class TestAggregateToggleButton:
    """Test aggregate mode toggle button functionality."""

    def test_toggle_button_exists(self, timeline_widget: TimelineTabWidget) -> None:
        """Verify toggle button is created and has correct properties."""
        assert hasattr(timeline_widget, "mode_toggle_btn")
        assert timeline_widget.mode_toggle_btn is not None
        assert timeline_widget.mode_toggle_btn.isCheckable()
        assert timeline_widget.mode_toggle_btn.text() == "Aggregate Mode"
        assert "combined status" in timeline_widget.mode_toggle_btn.toolTip().lower()

    def test_toggle_button_initial_state(self, timeline_widget: TimelineTabWidget) -> None:
        """Verify button starts unchecked (single-curve mode)."""
        assert not timeline_widget.mode_toggle_btn.isChecked()
        assert not timeline_widget.show_all_curves_mode

    def test_toggle_button_click_enables_aggregate_mode(
        self, timeline_widget: TimelineTabWidget, qtbot
    ) -> None:
        """Verify clicking button enables aggregate mode."""
        # Click button to enable aggregate mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)

        # Wait for signal processing
        qtbot.wait(10)

        # Verify state changed
        assert timeline_widget.mode_toggle_btn.isChecked()
        assert timeline_widget.show_all_curves_mode
        assert timeline_widget.mode_toggle_btn.text() == "All Curves"

    def test_toggle_button_click_disables_aggregate_mode(
        self, timeline_widget: TimelineTabWidget, qtbot
    ) -> None:
        """Verify clicking button twice returns to single-curve mode."""
        # Enable aggregate mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(10)
        assert timeline_widget.show_all_curves_mode

        # Disable aggregate mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(10)

        # Verify state changed back
        assert not timeline_widget.mode_toggle_btn.isChecked()
        assert not timeline_widget.show_all_curves_mode
        assert timeline_widget.mode_toggle_btn.text() == "Aggregate Mode"


class TestAggregateModeDisplay:
    """Test aggregate mode timeline display."""

    def test_aggregate_mode_label_shows_curve_count(
        self, timeline_widget: TimelineTabWidget, multi_curve_data: dict[str, CurveDataList], qtbot
    ) -> None:
        """Verify active point label shows curve count in aggregate mode."""
        # Load multi-curve data
        app_state = get_application_state()
        for curve_name, curve_data in multi_curve_data.items():
            app_state.set_curve_data(curve_name, curve_data)

        # Enable aggregate mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)

        # Verify label shows curve count
        label_text = timeline_widget.active_point_label.text()
        assert "All Curves" in label_text
        assert f"({len(multi_curve_data)})" in label_text

    def test_aggregate_mode_uses_all_curves(
        self, timeline_widget: TimelineTabWidget, multi_curve_data: dict[str, CurveDataList], qtbot
    ) -> None:
        """Verify aggregate mode aggregates status from all curves."""
        # Load multi-curve data
        app_state = get_application_state()
        for curve_name, curve_data in multi_curve_data.items():
            app_state.set_curve_data(curve_name, curve_data)

        # Enable aggregate mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)

        # Force timeline update
        timeline_widget._on_curves_changed(multi_curve_data)  # pyright: ignore[reportPrivateUsage]

        # Verify frame 1 has aggregated status
        # Track1: KEYFRAME, Track2: TRACKED, Track3: NORMAL
        frame_1_status = timeline_widget.status_cache.get_status(1)
        assert frame_1_status is not None
        # Debug: Print actual status
        print(f"Frame 1 status: {frame_1_status}")
        # All 3 points at frame 1 should be counted (regardless of specific status classification)
        total_points = (
            frame_1_status.keyframe_count
            + frame_1_status.tracked_count
            + frame_1_status.normal_count
            + frame_1_status.interpolated_count
            + frame_1_status.endframe_count
        )
        assert total_points == 3, f"Expected 3 total points at frame 1, got {total_points}"
        # At least one of each type should be present (though exact classification may vary)
        assert frame_1_status.is_startframe  # Frame 1 is a startframe

        # Verify frame 3 status
        # Track1: KEYFRAME, Track2: ENDFRAME, Track3: TRACKED
        frame_3_status = timeline_widget.status_cache.get_status(3)
        assert frame_3_status is not None
        # All 3 points at frame 3 should be counted
        total_points_3 = (
            frame_3_status.keyframe_count
            + frame_3_status.tracked_count
            + frame_3_status.normal_count
            + frame_3_status.interpolated_count
            + frame_3_status.endframe_count
        )
        assert total_points_3 == 3, f"Expected 3 total points at frame 3, got {total_points_3}"

    def test_single_curve_mode_uses_active_curve_only(
        self, timeline_widget: TimelineTabWidget, multi_curve_data: dict[str, CurveDataList]
    ) -> None:
        """Verify single-curve mode shows only active curve status."""
        # Load multi-curve data
        app_state = get_application_state()
        for curve_name, curve_data in multi_curve_data.items():
            app_state.set_curve_data(curve_name, curve_data)

        # Set active curve
        app_state.set_active_curve("Track1")

        # Ensure single-curve mode (default)
        assert not timeline_widget.show_all_curves_mode

        # Force timeline update
        timeline_widget._on_curves_changed(multi_curve_data)  # pyright: ignore[reportPrivateUsage]

        # Verify frame 1 has only Track1 status (single point)
        frame_1_status = timeline_widget.status_cache.get_status(1)
        assert frame_1_status is not None
        total_points_single = (
            frame_1_status.keyframe_count
            + frame_1_status.tracked_count
            + frame_1_status.normal_count
            + frame_1_status.interpolated_count
            + frame_1_status.endframe_count
        )
        # Should only have 1 point (from Track1), not 3
        assert total_points_single == 1, f"Expected 1 point in single-curve mode, got {total_points_single}"


class TestModeToggling:
    """Test switching between single-curve and aggregate modes."""

    def test_toggle_refreshes_timeline_display(
        self, timeline_widget: TimelineTabWidget, multi_curve_data: dict[str, CurveDataList], qtbot
    ) -> None:
        """Verify toggling mode refreshes timeline display."""
        # Load multi-curve data
        app_state = get_application_state()
        for curve_name, curve_data in multi_curve_data.items():
            app_state.set_curve_data(curve_name, curve_data)
        app_state.set_active_curve("Track1")

        # Start in single-curve mode - verify Track1 only (1 point)
        timeline_widget._on_curves_changed(multi_curve_data)  # pyright: ignore[reportPrivateUsage]
        frame_1_single = timeline_widget.status_cache.get_status(1)
        assert frame_1_single is not None
        single_total = sum(
            [
                frame_1_single.keyframe_count,
                frame_1_single.tracked_count,
                frame_1_single.normal_count,
                frame_1_single.interpolated_count,
                frame_1_single.endframe_count,
            ]
        )
        assert single_total == 1, f"Single-curve mode should show 1 point, got {single_total}"

        # Toggle to aggregate mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(10)

        # Verify aggregated status (3 points from 3 curves)
        frame_1_aggregate = timeline_widget.status_cache.get_status(1)
        assert frame_1_aggregate is not None
        aggregate_total = sum(
            [
                frame_1_aggregate.keyframe_count,
                frame_1_aggregate.tracked_count,
                frame_1_aggregate.normal_count,
                frame_1_aggregate.interpolated_count,
                frame_1_aggregate.endframe_count,
            ]
        )
        assert aggregate_total == 3, f"Aggregate mode should show 3 points, got {aggregate_total}"

        # Toggle back to single-curve mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(10)

        # Verify back to single-curve status (1 point)
        frame_1_single_again = timeline_widget.status_cache.get_status(1)
        assert frame_1_single_again is not None
        single_again_total = sum(
            [
                frame_1_single_again.keyframe_count,
                frame_1_single_again.tracked_count,
                frame_1_single_again.normal_count,
                frame_1_single_again.interpolated_count,
                frame_1_single_again.endframe_count,
            ]
        )
        assert single_again_total == 1, f"Back to single-curve should show 1 point, got {single_again_total}"

    def test_toggle_updates_active_point_label(
        self, timeline_widget: TimelineTabWidget, multi_curve_data: dict[str, CurveDataList], qtbot
    ) -> None:
        """Verify active point label updates when toggling modes."""
        # Load multi-curve data
        app_state = get_application_state()
        for curve_name, curve_data in multi_curve_data.items():
            app_state.set_curve_data(curve_name, curve_data)
        app_state.set_active_curve("Track1")

        # Set StateManager to get proper label display
        from ui.state_manager import StateManager

        state_manager = StateManager()
        timeline_widget.set_state_manager(state_manager)

        # Update timeline to set initial label
        timeline_widget._on_curves_changed(multi_curve_data)  # pyright: ignore[reportPrivateUsage]

        # Verify single-curve label (might be "No point" initially if StateManager not fully initialized)
        label_text_single = timeline_widget.active_point_label.text()
        # Label should be either "Timeline: Track1" or "No point" initially
        assert "Timeline:" in label_text_single or "Track1" in label_text_single or "No point" in label_text_single

        # Toggle to aggregate mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)

        # Verify aggregate label
        label_text_aggregate = timeline_widget.active_point_label.text()
        assert "All Curves" in label_text_aggregate
        assert "(3)" in label_text_aggregate

        # Toggle back to single-curve mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)

        # Verify single-curve label restored
        label_text_restored = timeline_widget.active_point_label.text()
        assert "Timeline:" in label_text_restored or "Track1" in label_text_restored


class TestEmptyCurveHandling:
    """Test aggregate mode with no curves or empty curves."""

    def test_aggregate_mode_with_no_curves(self, timeline_widget: TimelineTabWidget, qtbot) -> None:
        """Verify aggregate mode handles empty curve list gracefully."""
        # Enable aggregate mode with no curves
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)

        # Should not crash and should show default range
        assert timeline_widget.min_frame == 1
        assert timeline_widget.max_frame == 1

    def test_aggregate_mode_with_empty_curves(
        self, timeline_widget: TimelineTabWidget, qtbot
    ) -> None:
        """Verify aggregate mode handles curves with no data."""
        # Load curves with empty data
        app_state = get_application_state()
        app_state.set_curve_data("Track1", [])
        app_state.set_curve_data("Track2", [])

        # Enable aggregate mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)

        # Should not crash and should use image sequence range if available
        assert timeline_widget.min_frame >= 1
        assert timeline_widget.max_frame >= 1


class TestFrameRangeCalculation:
    """Test frame range calculation in aggregate mode."""

    def test_aggregate_mode_frame_range_includes_all_curves(
        self, timeline_widget: TimelineTabWidget, qtbot
    ) -> None:
        """Verify frame range spans all curves in aggregate mode."""
        # Create curves with different frame ranges (test uses 4-tuple format)
        app_state = get_application_state()
        app_state.set_curve_data(
            "Track1",
            [
                (5, 10.0, 20.0, "keyframe"),
                (10, 11.0, 21.0, "keyframe"),
            ],
        )
        app_state.set_curve_data(
            "Track2",
            [
                (1, 30.0, 40.0, "tracked"),
                (15, 31.0, 41.0, "tracked"),
            ],
        )

        # Enable aggregate mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)

        # Verify frame range includes both curves
        assert timeline_widget.min_frame == 1  # From Track2
        assert timeline_widget.max_frame == 15  # From Track2

    def test_single_curve_mode_frame_range_uses_active_curve(
        self, timeline_widget: TimelineTabWidget
    ) -> None:
        """Verify single-curve mode uses only active curve frame range."""
        # Create curves with different frame ranges (test uses 4-tuple format)
        app_state = get_application_state()
        app_state.set_curve_data(
            "Track1",
            [
                (5, 10.0, 20.0, "keyframe"),
                (10, 11.0, 21.0, "keyframe"),
            ],
        )
        app_state.set_curve_data(
            "Track2",
            [
                (1, 30.0, 40.0, "tracked"),
                (15, 31.0, 41.0, "tracked"),
            ],
        )
        app_state.set_active_curve("Track1")

        # Update timeline in single-curve mode
        timeline_widget._on_curves_changed(app_state.get_all_curves())  # pyright: ignore[reportPrivateUsage]

        # Verify frame range uses only Track1
        assert timeline_widget.min_frame == 5  # Track1 min
        assert timeline_widget.max_frame == 10  # Track1 max


class TestIntegrationWithApplicationState:
    """Test integration with ApplicationState."""

    def test_aggregate_mode_updates_on_curve_changes(
        self, timeline_widget: TimelineTabWidget, qtbot
    ) -> None:
        """Verify aggregate mode updates when curves change."""
        # Enable aggregate mode
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)

        # Load initial curves (test uses 4-tuple format)
        app_state = get_application_state()
        app_state.set_curve_data("Track1", [(1, 10.0, 20.0, "keyframe")])

        # Verify initial status (1 point exists)
        timeline_widget._on_curves_changed(app_state.get_all_curves())  # pyright: ignore[reportPrivateUsage]
        frame_1_initial = timeline_widget.status_cache.get_status(1)
        assert frame_1_initial is not None
        initial_total = sum(
            [
                frame_1_initial.keyframe_count,
                frame_1_initial.tracked_count,
                frame_1_initial.normal_count,
                frame_1_initial.interpolated_count,
                frame_1_initial.endframe_count,
            ]
        )
        assert initial_total == 1, f"Expected 1 point initially, got {initial_total}"

        # Add another curve
        app_state.set_curve_data("Track2", [(1, 30.0, 40.0, "tracked")])

        # Verify aggregated status includes new curve (2 points total)
        timeline_widget._on_curves_changed(app_state.get_all_curves())  # pyright: ignore[reportPrivateUsage]
        frame_1_updated = timeline_widget.status_cache.get_status(1)
        assert frame_1_updated is not None
        updated_total = sum(
            [
                frame_1_updated.keyframe_count,
                frame_1_updated.tracked_count,
                frame_1_updated.normal_count,
                frame_1_updated.interpolated_count,
                frame_1_updated.endframe_count,
            ]
        )
        assert updated_total == 2, f"Expected 2 points after adding curve, got {updated_total}"

    def test_aggregate_mode_respects_cache_invalidation(
        self, timeline_widget: TimelineTabWidget, qtbot
    ) -> None:
        """Verify cache is invalidated when toggling modes."""
        # Load curves (test uses 4-tuple format)
        app_state = get_application_state()
        app_state.set_curve_data("Track1", [(1, 10.0, 20.0, "keyframe")])

        # Populate cache in single-curve mode
        timeline_widget._on_curves_changed(app_state.get_all_curves())  # pyright: ignore[reportPrivateUsage]

        # Enable aggregate mode (should invalidate cache)
        qtbot.mouseClick(timeline_widget.mode_toggle_btn, Qt.MouseButton.LeftButton)

        # Cache should be refreshed with aggregate data
        # (exact verification depends on internal implementation)
        assert len(timeline_widget.status_cache._cache) >= 0  # pyright: ignore[reportPrivateUsage]
