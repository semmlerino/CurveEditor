#!/usr/bin/env python
"""
Tests for data preservation and restoration during endframe ↔ keyframe conversion.

Tests the complete data preservation workflow:
- Converting keyframes with tracked data to endframes preserves the data
- Converting endframes back to keyframes restores the original tracked data
- Interpolation works correctly when no tracked data exists
- Complex scenarios with multiple conversions work correctly
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

from core.curve_segments import SegmentedCurve
from core.models import PointStatus
from core.type_aliases import CurveDataList
from services.data_service import DataService


class TestDataPreservation:
    """Test data preservation during keyframe → endframe conversion."""

    def test_preserve_tracked_data_on_endframe_conversion(self):
        """Test that tracked data is preserved when converting keyframe to endframe."""
        # Create curve with tracked data between keyframes
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 105.0, "tracked"),  # Tracked data
            (3, 120.0, 110.0, "tracked"),  # Tracked data
            (4, 130.0, 115.0, "tracked"),  # Tracked data
            (5, 140.0, 120.0, "keyframe"),  # Will convert to endframe
            (8, 200.0, 200.0, "keyframe"),
        ]

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)

        # Initially there's 1 segment with all points (no endframes yet)
        assert len(segmented_curve.segments) == 1
        initial_segment = segmented_curve.segments[0]  # frames 1-8
        assert initial_segment.is_active is True

        # Convert frame 5 to endframe (simulating E key press)
        segmented_curve.update_segment_activity(4, PointStatus.ENDFRAME)  # 0-indexed

        # After conversion, should have 2 segments
        assert len(segmented_curve.segments) == 2
        first_segment = segmented_curve.segments[0]  # frames 1-5 (ending with endframe)
        second_segment = segmented_curve.segments[1]  # frames 8-8 (startframe)

        # First segment (ending with endframe) should remain active
        # The endframe itself is visible/active on the timeline
        assert first_segment.originally_active is True
        assert first_segment.is_active is True  # Segment with endframe remains active

        # Second segment should be a startframe segment and remain active
        assert second_segment.is_active is True

        # Verify tracked data is preserved in the deactivated segment
        preserved_points = first_segment.points
        assert len(preserved_points) == 5  # All points from 1-5
        assert preserved_points[1].status == PointStatus.TRACKED  # frame 2
        assert preserved_points[2].status == PointStatus.TRACKED  # frame 3
        assert preserved_points[3].status == PointStatus.TRACKED  # frame 4
        assert preserved_points[4].status == PointStatus.ENDFRAME  # frame 5

    def test_preserve_multiple_segments_data(self):
        """Test preserving data from multiple segments with endframe conversions."""
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 105.0, "tracked"),
            (3, 120.0, 110.0, "keyframe"),  # Will convert to endframe
            (4, 130.0, 115.0, "tracked"),
            (5, 140.0, 120.0, "tracked"),
            (6, 150.0, 125.0, "keyframe"),  # Will convert to endframe
            (10, 200.0, 200.0, "keyframe"),
        ]

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)

        # Convert frame 3 to endframe
        segmented_curve.update_segment_activity(2, PointStatus.ENDFRAME)  # 0-indexed

        # Convert frame 6 to endframe
        segmented_curve.update_segment_activity(5, PointStatus.ENDFRAME)  # 0-indexed

        # Check preservation metadata for segments
        # After conversion:
        # - Segment 0: frames 1-3 (ending with endframe), ACTIVE
        # - Segment 1: frames 4-6 (in gap between endframe 3 and keyframe 10), INACTIVE
        # - Segment 2: frame 10 (startframe after gap), ACTIVE

        assert len(segmented_curve.segments) == 3
        first_segment = segmented_curve.segments[0]  # frames 1-3 (ending with endframe)
        second_segment = segmented_curve.segments[1]  # frames 4-6 (in gap, even though ends with endframe)
        third_segment = segmented_curve.segments[2]  # frame 10 (startframe)

        # First segment ends with endframe, remains active
        assert first_segment.originally_active is True
        assert first_segment.is_active is True  # Segment ending with first endframe is active
        assert first_segment.end_frame == 3
        assert first_segment.points[-1].status == PointStatus.ENDFRAME

        # Second segment is in the gap (after endframe 3, before keyframe 10), should be INACTIVE
        # even though it ends with another endframe
        assert second_segment.originally_active is True
        assert second_segment.is_active is False  # Segment in gap is inactive
        assert second_segment.start_frame == 4
        assert second_segment.end_frame == 6
        assert second_segment.points[-1].status == PointStatus.ENDFRAME

        # Third segment starts with keyframe (startframe), ends the gap, is ACTIVE
        assert third_segment.is_active is True
        assert third_segment.start_frame == 10


class TestDataRestoration:
    """Test data restoration during endframe → keyframe conversion."""

    def test_restore_tracked_data_on_keyframe_conversion(self):
        """Test that tracked data is restored when converting endframe back to keyframe."""
        # Start with preserved data scenario
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 105.0, "tracked"),
            (3, 120.0, 110.0, "tracked"),
            (4, 130.0, 115.0, "tracked"),
            (5, 140.0, 120.0, "endframe"),  # Already converted
            (8, 200.0, 200.0, "keyframe"),
        ]

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)

        # Initially there are 2 segments due to endframe
        assert len(segmented_curve.segments) == 2
        assert segmented_curve.segments[0].end_frame == 5  # ends with endframe
        assert segmented_curve.segments[1].start_frame == 8  # startframe segment

        # Convert frame 5 back to keyframe (simulating E key press again)
        segmented_curve.update_segment_activity(4, PointStatus.KEYFRAME)  # 0-indexed

        # After restoration, segments merge back into one continuous segment
        assert len(segmented_curve.segments) == 1
        restored_segment = segmented_curve.segments[0]
        assert restored_segment.start_frame == 1
        assert restored_segment.end_frame == 8
        assert restored_segment.is_active is True

        # Verify tracked data is still intact and point status updated
        restored_points = restored_segment.points
        assert len(restored_points) == 6  # All points from 1-8
        assert restored_points[1].status == PointStatus.TRACKED  # frame 2
        assert restored_points[2].status == PointStatus.TRACKED  # frame 3
        assert restored_points[3].status == PointStatus.TRACKED  # frame 4
        assert restored_points[4].status == PointStatus.KEYFRAME  # frame 5 (now keyframe)
        assert restored_points[5].status == PointStatus.KEYFRAME  # frame 8

    def test_restoration_with_interpolation_fallback(self):
        """Test that interpolation works when no tracked data exists to restore."""
        # Curve with no tracked data between keyframes
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 140.0, 120.0, "keyframe"),  # No tracked data between 1-5
            (8, 200.0, 200.0, "keyframe"),
        ]

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)

        # Convert frame 5 to endframe
        segmented_curve.update_segment_activity(1, PointStatus.ENDFRAME)  # 0-indexed

        # Verify segment with endframe remains active (endframe itself is visible)
        # The gap AFTER the endframe would be inactive, not the segment with the endframe
        first_segment = segmented_curve.segments[0]
        assert first_segment.is_active is True  # Endframe segment stays active
        assert len(first_segment.points) == 2  # Only keyframes at 1 and 5

        # Convert frame 5 back to keyframe
        segmented_curve.update_segment_activity(1, PointStatus.KEYFRAME)  # 0-indexed

        # Verify segment is restored and interpolation can work
        assert first_segment.is_active is True

        # Test interpolation works between the keyframes
        position = segmented_curve.get_position_at_frame(3)  # Halfway between 1 and 5
        assert position is not None
        x, y = position
        assert x == 120.0  # 100 + (140-100) * 0.5
        assert y == 110.0  # 100 + (120-100) * 0.5

    def test_multiple_restoration_cycles(self):
        """Test multiple endframe/keyframe conversion cycles preserve data correctly."""
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 105.0, "tracked"),
            (3, 120.0, 110.0, "tracked"),
            (4, 130.0, 115.0, "keyframe"),
            (6, 200.0, 200.0, "keyframe"),
        ]

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)
        original_points = segmented_curve.segments[0].points.copy()

        # First conversion: keyframe → endframe
        segmented_curve.update_segment_activity(3, PointStatus.ENDFRAME)  # frame 4 to endframe
        assert segmented_curve.segments[0].is_active is True  # Segment with endframe remains active

        # First restoration: endframe → keyframe
        segmented_curve.update_segment_activity(3, PointStatus.KEYFRAME)  # frame 4 back to keyframe
        assert segmented_curve.segments[0].is_active is True

        # Second conversion: keyframe → endframe
        segmented_curve.update_segment_activity(3, PointStatus.ENDFRAME)  # frame 4 to endframe again
        assert segmented_curve.segments[0].is_active is True  # Segment with endframe remains active

        # Second restoration: endframe → keyframe
        segmented_curve.update_segment_activity(3, PointStatus.KEYFRAME)  # frame 4 back to keyframe again
        assert segmented_curve.segments[0].is_active is True

        # Verify tracked data survived multiple cycles
        final_points = segmented_curve.segments[0].points
        assert len(final_points) == len(original_points)
        assert final_points[1].status == PointStatus.TRACKED  # frame 2
        assert final_points[2].status == PointStatus.TRACKED  # frame 3


class TestDataServiceIntegration:
    """Test DataService integration with preservation/restoration."""

    def test_data_service_preservation_workflow(self):
        """Test complete workflow through DataService."""
        data_service = DataService()

        # Initial curve data with tracked points
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 105.0, "tracked"),
            (3, 120.0, 110.0, "tracked"),
            (4, 130.0, 115.0, "keyframe"),
            (8, 200.0, 200.0, "keyframe"),
        ]

        # Initialize data service with curve data
        data_service.update_curve_data(curve_data)

        # Test that positions work correctly before conversion
        assert data_service.get_position_at_frame(curve_data, 2) == (110.0, 105.0)
        assert data_service.get_position_at_frame(curve_data, 3) == (120.0, 110.0)

        # Convert frame 4 to endframe via data service
        data_service.handle_point_status_change(3, "endframe")  # 0-indexed

        # Test gap behavior (positions held after endframe)
        assert data_service.get_position_at_frame(curve_data, 5) == (130.0, 115.0)  # Held
        assert data_service.get_position_at_frame(curve_data, 6) == (130.0, 115.0)  # Held
        assert data_service.get_position_at_frame(curve_data, 7) == (130.0, 115.0)  # Held

        # Convert frame 4 back to keyframe
        data_service.handle_point_status_change(3, "keyframe")  # 0-indexed

        # Test that tracked data is restored and interpolation works again
        position = data_service.get_position_at_frame(curve_data, 6)  # Halfway between 4 and 8
        assert position is not None
        x, y = position
        assert x == 165.0  # 130 + (200-130) * 0.5
        assert y == 157.5  # 115 + (200-115) * 0.5

    def test_data_service_handles_point_status_enum(self):
        """Test DataService handles PointStatus enum correctly."""
        data_service = DataService()

        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 105.0, "tracked"),
            (5, 140.0, 120.0, "keyframe"),
        ]

        data_service.update_curve_data(curve_data)

        # Test with PointStatus enum (not just string)
        data_service.handle_point_status_change(2, PointStatus.ENDFRAME)  # 0-indexed

        # Verify gap behavior works
        assert data_service.get_position_at_frame(curve_data, 6) == (140.0, 120.0)  # Held

        # Convert back using enum
        data_service.handle_point_status_change(2, PointStatus.KEYFRAME)  # 0-indexed

        # Verify restoration works
        position = data_service.get_position_at_frame(curve_data, 3)  # Should interpolate
        assert position is not None


class TestEdgeCasesRestoration:
    """Test edge cases for data preservation and restoration."""

    def test_restoration_with_adjacent_endframes(self):
        """Test restoration when there are adjacent endframes."""
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 105.0, "tracked"),
            (3, 120.0, 110.0, "endframe"),  # Adjacent endframes
            (4, 130.0, 115.0, "endframe"),
            (7, 200.0, 200.0, "keyframe"),
        ]

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)

        # Initially there are 3 segments due to adjacent endframes
        assert len(segmented_curve.segments) == 3
        # Segments should be: 1-3, 4-4, 7-7

        # Convert frame 3 back to keyframe
        segmented_curve.update_segment_activity(2, PointStatus.KEYFRAME)  # 0-indexed

        # After converting frame 3 to keyframe, segments should be reconstructed
        # Should have: 1-4 (merged due to no gap at frame 3), 7-7
        assert len(segmented_curve.segments) == 2

        first_segment = segmented_curve.segments[0]  # Should now be frames 1-4
        second_segment = segmented_curve.segments[1]  # Should be frames 7-7

        # First segment contains frames 1-4
        assert first_segment.start_frame == 1
        assert first_segment.end_frame == 4
        # Note: Frame 4 is still endframe, but segments with endframes remain active
        assert first_segment.is_active is True  # Segment with endframe at 4 remains active

        # Second segment should be active (startframe)
        assert second_segment.start_frame == 7
        assert second_segment.end_frame == 7
        assert second_segment.is_active is True

    def test_restoration_with_single_point_segments(self):
        """Test restoration with single-point segments."""
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 140.0, 120.0, "endframe"),  # Single point segment
            (8, 200.0, 200.0, "keyframe"),
        ]

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)

        # Manually set preservation metadata
        first_segment = segmented_curve.segments[0]
        first_segment.originally_active = True
        first_segment.deactivated_by_frame = 5
        first_segment.is_active = False

        # Convert frame 5 back to keyframe
        segmented_curve.update_segment_activity(1, PointStatus.KEYFRAME)  # 0-indexed

        # Verify restoration works even with single-point segment
        assert first_segment.is_active is True
        assert len(first_segment.points) == 2  # frames 1 and 5

    def test_restoration_preserves_segment_boundaries(self):
        """Test that restoration preserves proper segment boundaries."""
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 105.0, "tracked"),
            (3, 120.0, 110.0, "tracked"),
            (4, 130.0, 115.0, "endframe"),
            (5, 140.0, 120.0, "tracked"),  # This should NOT be in first segment
            (6, 150.0, 125.0, "keyframe"),
        ]

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)

        # Manually set preservation for first segment
        first_segment = segmented_curve.segments[0]  # Should be frames 1-4 only
        first_segment.originally_active = True
        first_segment.deactivated_by_frame = 4
        first_segment.is_active = False

        # Verify first segment doesn't include frame 5 data
        assert len(first_segment.points) == 4  # frames 1, 2, 3, 4 only
        assert first_segment.points[-1].frame == 4

        # Convert frame 4 back to keyframe
        segmented_curve.update_segment_activity(3, PointStatus.KEYFRAME)  # 0-indexed

        # Verify restoration maintains proper boundaries
        assert first_segment.is_active is True
        assert len(first_segment.points) == 4  # Still only frames 1-4
        assert first_segment.points[-1].frame == 4  # Boundary preserved


class TestTrackedEndframeGapBehavior:
    """Test correct 3DEqualizer gap behavior with tracked frames."""

    def test_tracked_to_endframe_creates_proper_gap(self):
        """Test user's specific scenario: tracked→endframe should create gap until next keyframe.

        The issue was that TRACKED frames were incorrectly becoming startframes after endframes,
        but in 3DEqualizer behavior, only KEYFRAME points should end gaps.
        """
        # User's scenario: convert tracked frame to endframe, with tracked frames after
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "tracked"),  # Will convert to endframe
            (6, 160.0, 160.0, "tracked"),  # Should stay in gap (not become startframe)
            (7, 170.0, 170.0, "tracked"),  # Should stay in gap
            (8, 180.0, 180.0, "tracked"),  # Should stay in gap
            (10, 200.0, 200.0, "keyframe"),  # Should be the actual startframe
        ]

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)

        # Initially one active segment
        assert len(segmented_curve.segments) == 1
        assert segmented_curve.segments[0].is_active is True

        # Convert frame 5 (tracked) to endframe
        segmented_curve.update_segment_activity(1, PointStatus.ENDFRAME)  # 0-indexed

        # Should now have segments properly divided (3DEqualizer gap behavior)
        assert len(segmented_curve.segments) == 3

        first_segment = segmented_curve.segments[0]  # frames 1-5 (ends with endframe)
        second_segment = segmented_curve.segments[1]  # frames 6-8 (tracked points in gap)
        third_segment = segmented_curve.segments[2]  # frames 10-10 (keyframe ends gap)

        # First segment contains the endframe and remains active
        assert first_segment.start_frame == 1
        assert first_segment.end_frame == 5
        assert first_segment.is_active is True  # Segment with endframe remains active
        assert first_segment.points[-1].status == PointStatus.ENDFRAME  # frame 5

        # Second segment should contain only tracked frames (gap)
        assert second_segment.start_frame == 6
        assert second_segment.end_frame == 8
        assert second_segment.is_active is False  # Gap continues through tracked frames

        # Verify the tracked frames are in the gap (inactive segment)
        tracked_points = [p for p in second_segment.points if p.status == PointStatus.TRACKED]
        assert len(tracked_points) == 3  # frames 6, 7, 8

        # Third segment should contain only the keyframe (ends gap)
        assert third_segment.start_frame == 10
        assert third_segment.end_frame == 10
        assert third_segment.is_active is True  # Active segment starts with keyframe

        # Only frame 10 (keyframe) should end the gap
        keyframe_points = [p for p in third_segment.points if p.status == PointStatus.KEYFRAME]
        assert len(keyframe_points) == 1  # frame 10
        assert keyframe_points[0].frame == 10

        # Test position behavior during gap
        # Frames 6-8 have actual tracked data points, so they return their actual positions
        # even though they're in an inactive segment (gap)
        assert segmented_curve.get_position_at_frame(6) == (160.0, 160.0)  # actual tracked position
        assert segmented_curve.get_position_at_frame(7) == (170.0, 170.0)  # actual tracked position
        assert segmented_curve.get_position_at_frame(8) == (180.0, 180.0)  # actual tracked position

        # Frame 9 has no actual data point, so it returns held position from endframe at frame 5
        held_position = (150.0, 150.0)  # position from frame 5
        assert segmented_curve.get_position_at_frame(9) == held_position

        # Frame 10 should have its actual keyframe position
        assert segmented_curve.get_position_at_frame(10) == (200.0, 200.0)

    def test_keyframe_properly_ends_gap_after_tracked_endframe(self):
        """Test that converting tracked endframe back to keyframe properly restores segments."""
        # Start with tracked frame, convert to endframe, then back to keyframe
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "tracked"),  # Will convert to endframe, then back
            (6, 160.0, 160.0, "tracked"),  # In gap
            (7, 170.0, 170.0, "tracked"),  # In gap
            (10, 200.0, 200.0, "keyframe"),  # Ends gap
        ]

        segmented_curve = SegmentedCurve.from_curve_data(curve_data)

        # Convert frame 5 to endframe first
        segmented_curve.update_segment_activity(1, PointStatus.ENDFRAME)  # 0-indexed

        # Should have proper gap structure (3DEqualizer behavior creates 3 segments)
        assert len(segmented_curve.segments) == 3
        assert segmented_curve.segments[0].is_active is True  # segment with endframe remains active
        assert segmented_curve.segments[1].is_active is False  # tracked points in gap
        assert segmented_curve.segments[2].is_active is True  # keyframe ends gap

        # Convert endframe back to keyframe to test restoration
        segmented_curve.update_segment_activity(1, PointStatus.KEYFRAME)  # frame 5 back to keyframe

        # Should merge back into one active segment
        assert len(segmented_curve.segments) == 1
        restored_segment = segmented_curve.segments[0]
        assert restored_segment.is_active is True
        assert restored_segment.start_frame == 1
        assert restored_segment.end_frame == 10

        # All frames should now be accessible for interpolation
        # Test interpolation works between frames 5 and 10
        position = segmented_curve.get_position_at_frame(7)  # Should interpolate
        assert position is not None
        # Should be interpolated between frame 5 (150, 150) and frame 10 (200, 200)
        # Frame 7 is 2/5 of the way from 5 to 10
        expected_x = 150.0 + (200.0 - 150.0) * 0.4  # 170.0
        expected_y = 150.0 + (200.0 - 150.0) * 0.4  # 170.0
        assert position == (expected_x, expected_y)
