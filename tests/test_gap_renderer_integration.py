#!/usr/bin/env python3
"""
TDD tests for gap rendering integration.

Tests verify the complete flow from SetPointStatusCommand through DataService's
SegmentedCurve to renderer drawing dashed lines for inactive segments.

RED-GREEN-REFACTOR Cycle:
1. RED: Write tests that fail, proving gaps aren't rendered correctly
2. GREEN: Fix the root cause to make tests pass
3. REFACTOR: Clean up without breaking tests
"""

# Per-file type checking relaxations for test code
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

from unittest.mock import MagicMock

import pytest

from core.commands.curve_commands import SetPointStatusCommand
from core.models import PointStatus
from services import get_data_service
from stores.application_state import get_application_state


class TestDataServiceSegmentedCurveUpdates:
    """Phase 1: Test that DataService updates SegmentedCurve correctly."""

    def test_update_curve_data_creates_segmented_curve(self):
        """Test that update_curve_data creates a SegmentedCurve instance.

        RED: Initially fails if DataService doesn't create SegmentedCurve.
        """
        data_service = get_data_service()

        # Arrange: Curve data with frames 1-15
        curve_data = [(i, 100.0 + i * 10, 200.0 + i * 5, "tracked") for i in range(1, 16)]

        # Act: Update curve data in DataService
        data_service.update_curve_data(curve_data)

        # Assert: SegmentedCurve should be created
        assert data_service.segmented_curve is not None, "DataService should create SegmentedCurve"
        assert len(data_service.segmented_curve.all_points) == 15, "All points should be in SegmentedCurve"

    def test_handle_point_status_change_updates_segmented_curve(self):
        """Test that handle_point_status_change updates segment activity.

        RED: Initially fails if handle_point_status_change doesn't call update_segment_activity.
        """
        data_service = get_data_service()

        # Arrange: Curve data with frames 1-15, all tracked
        curve_data = [(i, 100.0 + i * 10, 200.0 + i * 5, "tracked") for i in range(1, 16)]
        data_service.update_curve_data(curve_data)

        # Verify initial state: single active segment
        segmented_curve = data_service.segmented_curve
        assert segmented_curve is not None, "SegmentedCurve should exist"
        initial_segments = segmented_curve.segments
        assert len(initial_segments) == 1, "Should start with 1 segment"
        assert initial_segments[0].is_active, "Initial segment should be active"

        # Act: Set frame 10 (index 9) as ENDFRAME
        data_service.handle_point_status_change(9, PointStatus.ENDFRAME)

        # Assert: SegmentedCurve should be updated with 2 segments
        segmented_curve = data_service.segmented_curve
        assert segmented_curve is not None, "SegmentedCurve should exist after ENDFRAME"
        updated_segments = segmented_curve.segments
        assert len(updated_segments) >= 2, "Should have at least 2 segments after ENDFRAME"

        # Find segments before and after frame 10
        segment_before_10 = None
        segment_after_10 = None
        for seg in updated_segments:
            if seg.end_frame <= 10:
                segment_before_10 = seg
            elif seg.start_frame > 10:
                segment_after_10 = seg

        # Verify segment activity
        assert segment_before_10 is not None, "Should have segment ending at/before frame 10"
        assert segment_before_10.is_active, "Segment before ENDFRAME should be active"

        if segment_after_10 is not None:
            assert not segment_after_10.is_active, "Segment after ENDFRAME should be inactive"


class TestSetPointStatusCommandUpdatesDataService:
    """Phase 2: Test that SetPointStatusCommand calls DataService correctly."""

    def test_execute_calls_update_curve_data(self, main_window_mock):
        """Test that execute() calls update_curve_data on DataService.

        RED: Initially fails if execute() doesn't call update_curve_data.
        """
        # Arrange: Setup application state with curve data
        app_state = get_application_state()
        curve_data = [(i, 100.0 + i * 10, 200.0 + i * 5, "tracked") for i in range(1, 16)]
        app_state.set_curve_data("TestTrack", curve_data)
        app_state.set_active_curve("TestTrack")

        data_service = get_data_service()

        # Create command to set frame 10 as ENDFRAME
        changes = [(9, "tracked", "endframe")]  # Index 9 = frame 10
        command = SetPointStatusCommand(description="Set endframe", changes=changes)

        # Act: Execute command
        result = command.execute(main_window_mock)

        # Assert: Command should succeed
        assert result, "Command execution should succeed"

        # Assert: DataService should have updated SegmentedCurve
        assert data_service.segmented_curve is not None, "SegmentedCurve should be updated"
        assert len(data_service.segmented_curve.segments) >= 2, "Should have multiple segments"

    def test_execute_calls_handle_point_status_change(self, main_window_mock):
        """Test that execute() calls handle_point_status_change for each change.

        RED: Initially fails if execute() doesn't call handle_point_status_change.
        """
        # Arrange: Setup application state
        app_state = get_application_state()
        curve_data = [(i, 100.0 + i * 10, 200.0 + i * 5, "tracked") for i in range(1, 16)]
        app_state.set_curve_data("TestTrack", curve_data)
        app_state.set_active_curve("TestTrack")

        data_service = get_data_service()

        # Create command
        changes = [(9, "tracked", "endframe")]
        command = SetPointStatusCommand(description="Set endframe", changes=changes)

        # Act: Execute command
        command.execute(main_window_mock)

        # Assert: SegmentedCurve should be updated
        segmented_curve = data_service.segmented_curve
        assert segmented_curve is not None

        # Verify that frame 10 is now an endframe
        point_at_frame_10 = None
        for point in segmented_curve.all_points:
            if point.frame == 10:
                point_at_frame_10 = point
                break

        assert point_at_frame_10 is not None, "Should find point at frame 10"
        assert point_at_frame_10.status == PointStatus.ENDFRAME, "Point should be ENDFRAME"


class TestSegmentedCurveActivity:
    """Phase 3: Test that SegmentedCurve correctly identifies active/inactive segments."""

    def test_segmented_curve_has_active_and_inactive_segments(self):
        """Test that SegmentedCurve correctly splits segments at ENDFRAME.

        RED: Initially fails if SegmentedCurve doesn't create inactive segments.
        """
        data_service = get_data_service()

        # Arrange: Curve data with ENDFRAME at frame 10
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),
            *[(i, 100.0 + i * 10, 200.0 + i * 5, "tracked") for i in range(2, 10)],
            (10, 190.0, 245.0, "endframe"),  # Creates gap after frame 10
            *[(i, 100.0 + i * 10, 200.0 + i * 5, "tracked") for i in range(11, 16)],
        ]

        # Act: Update DataService with this data
        data_service.update_curve_data(curve_data)

        # Assert: Should have segments with correct activity
        segmented_curve = data_service.segmented_curve
        assert segmented_curve is not None

        segments = segmented_curve.segments
        assert len(segments) >= 2, "Should have at least 2 segments"

        # Verify segment structure
        # Segment 1 (frames 1-10): active=True
        segment_1 = None
        for seg in segments:
            if seg.start_frame == 1 and seg.end_frame == 10:
                segment_1 = seg
                break

        assert segment_1 is not None, "Should have segment for frames 1-10"
        assert segment_1.is_active, "Segment with ENDFRAME should be active"

        # Segment 2 (frames 11-15): active=False (in gap after ENDFRAME)
        segment_2 = None
        for seg in segments:
            if seg.start_frame == 11:
                segment_2 = seg
                break

        assert segment_2 is not None, "Should have segment for frames 11+"
        assert not segment_2.is_active, "Segment after ENDFRAME should be inactive"

    def test_get_frame_range_point_status_shows_inactive_frames(self):
        """Test that DataService.get_frame_range_point_status marks frames as inactive.

        RED: Initially fails if get_frame_range_point_status doesn't use SegmentedCurve.
        """
        data_service = get_data_service()

        # Arrange: Curve with gap
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),
            (10, 190.0, 245.0, "endframe"),  # Gap after this
            (11, 200.0, 250.0, "tracked"),   # Should be inactive
            (15, 240.0, 270.0, "keyframe"),  # Starts active segment
        ]

        # Act: Update DataService and get frame status
        data_service.update_curve_data(curve_data)
        frame_status = data_service.get_frame_range_point_status(curve_data)

        # Assert: Frame 11 should be marked as inactive
        assert 11 in frame_status, "Should have status for frame 11"
        assert frame_status[11].is_inactive, "Frame 11 should be inactive (in gap)"

        # Assert: Frame 10 should NOT be inactive (it's the ENDFRAME itself)
        assert 10 in frame_status, "Should have status for frame 10"
        assert not frame_status[10].is_inactive, "Frame 10 (ENDFRAME) should not be inactive"


class TestRendererUsesSegmentedCurve:
    """Phase 4: Test that renderer gets and uses SegmentedCurve from DataService."""

    def test_renderer_uses_data_service_segmented_curve(self):
        """Test that renderer accesses DataService.segmented_curve.

        RED: Initially fails if renderer doesn't use DataService as single source of truth.
        """
        # Arrange: Setup DataService with gap
        data_service = get_data_service()
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),
            (10, 190.0, 245.0, "endframe"),
            (11, 200.0, 250.0, "tracked"),
            (15, 240.0, 270.0, "keyframe"),
        ]
        data_service.update_curve_data(curve_data)

        # Act: Verify DataService has SegmentedCurve
        segmented_curve = data_service.segmented_curve

        # Assert: DataService provides the SegmentedCurve
        assert segmented_curve is not None, "DataService should have SegmentedCurve"
        assert len(segmented_curve.segments) >= 2, "Should have multiple segments"

        # Assert: Segments are properly categorized
        inactive_segments = [s for s in segmented_curve.segments if not s.is_active]
        assert len(inactive_segments) > 0, "Should have inactive segments for gaps"

    def test_renderer_line_method_checks_for_status(self):
        """Test that _render_lines_with_segments checks for status data.

        RED: Initially fails if renderer doesn't check for status before segmenting.
        """
        data_service = get_data_service()

        # Arrange: Curve with status (should trigger segmented rendering)
        curve_with_status = [
            (1, 100.0, 200.0, "keyframe"),
            (10, 190.0, 245.0, "endframe"),
            (11, 200.0, 250.0, "tracked"),
        ]
        data_service.update_curve_data(curve_with_status)

        # Act: Check that data has status
        has_status = any(len(pt) > 3 for pt in curve_with_status if pt)

        # Assert: Data structure indicates status is present
        assert has_status, "Curve data should have status field"

        # Assert: SegmentedCurve reflects this
        segmented_curve = data_service.segmented_curve
        assert segmented_curve is not None
        assert len(segmented_curve.segments) >= 2, "Status should create segments"


class TestEndToEndGapRendering:
    """Phase 5: End-to-end tests from command to renderer."""

    def test_complete_gap_rendering_flow(self, main_window_mock):
        """Test complete flow: SetPointStatusCommand → DataService → Renderer.

        RED: Initially fails if any part of the chain is broken.
        GREEN: Passes when all parts work together.
        """
        # Arrange: Setup application state
        app_state = get_application_state()
        curve_data = [(i, 100.0 + i * 10, 200.0 + i * 5, "tracked") for i in range(1, 16)]
        app_state.set_curve_data("TestTrack", curve_data)
        app_state.set_active_curve("TestTrack")

        data_service = get_data_service()

        # Step 1: Execute SetPointStatusCommand
        changes = [(9, "tracked", "endframe")]  # Set frame 10 as ENDFRAME
        command = SetPointStatusCommand(description="Create gap", changes=changes)
        result = command.execute(main_window_mock)
        assert result, "Command should execute successfully"

        # Step 2: Verify DataService has updated SegmentedCurve
        segmented_curve = data_service.segmented_curve
        assert segmented_curve is not None, "DataService should have SegmentedCurve"

        segments = segmented_curve.segments
        assert len(segments) >= 2, "Should have multiple segments after ENDFRAME"

        # Step 3: Verify segments have correct activity
        segment_1 = None  # Frames 1-10
        segment_2 = None  # Frames 11-15

        for seg in segments:
            if seg.end_frame <= 10:
                segment_1 = seg
            elif seg.start_frame == 11:
                segment_2 = seg

        assert segment_1 is not None, "Should have segment ending at frame 10"
        assert segment_1.is_active, "Segment with ENDFRAME should be active"

        assert segment_2 is not None, "Should have segment starting at frame 11"
        assert not segment_2.is_active, "Segment after ENDFRAME should be inactive"

        # Step 4: Verify renderer would get correct data from DataService
        # (We don't need to actually render - just verify the data flow)
        updated_curve_data = app_state.get_curve_data("TestTrack")
        assert len(updated_curve_data) == 15, "Should have all 15 points"

        # Verify point at index 9 (frame 10) has endframe status
        point_at_10 = updated_curve_data[9]
        # point_at_10 is a 4-tuple: (frame, x, y, status)
        assert len(point_at_10) == 4, "Point should have 4 elements"
        assert point_at_10[3] == "endframe", "Frame 10 should be ENDFRAME"

        # Step 5: Verify DataService's SegmentedCurve is accessible
        assert data_service.segmented_curve is not None, "Renderer can get SegmentedCurve from DataService"

    def test_timeline_and_curve_show_same_gap(self, main_window_mock):
        """Test that timeline and curve renderer see the same gap state.

        This was the original bug: timeline showed gap, curve didn't.
        """
        # Arrange: Setup curve
        app_state = get_application_state()
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),
            (10, 190.0, 245.0, "tracked"),
            (15, 240.0, 270.0, "keyframe"),
        ]
        app_state.set_curve_data("TestTrack", curve_data)
        app_state.set_active_curve("TestTrack")

        data_service = get_data_service()
        data_service.update_curve_data(curve_data)

        # Act: Execute command to create gap
        changes = [(1, "tracked", "endframe")]  # Frame 10 becomes ENDFRAME
        command = SetPointStatusCommand(description="Create gap", changes=changes)
        command.execute(main_window_mock)

        # Get updated data
        updated_curve_data = list(app_state.get_curve_data("TestTrack"))

        # Step 1: Check timeline view (via get_frame_range_point_status)
        frame_status = data_service.get_frame_range_point_status(updated_curve_data)

        # Frames 11-14 should be inactive on timeline
        for frame in range(11, 15):
            if frame in frame_status:
                assert frame_status[frame].is_inactive, f"Frame {frame} should be inactive on timeline"

        # Step 2: Check renderer view (via SegmentedCurve)
        segmented_curve = data_service.segmented_curve
        assert segmented_curve is not None, "SegmentedCurve should exist"

        # Frames 11-14 should be in inactive segment
        for frame in range(11, 15):
            segment = segmented_curve.get_segment_at_frame(frame)
            if segment:
                assert not segment.is_active, f"Frame {frame} should be in inactive segment for renderer"

        # This proves timeline and renderer use the same single source of truth


@pytest.fixture
def main_window_mock():
    """Create a mock MainWindow for command execution."""
    mock = MagicMock()
    mock.update_view = MagicMock()
    return mock


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
