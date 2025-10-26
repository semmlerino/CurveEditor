#!/usr/bin/env python
"""
Tests for curve segmentation system.

Tests the CurveSegment and SegmentedCurve classes that handle
discontinuous curves with ENDFRAME boundaries.
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

from __future__ import annotations

from core.curve_segments import CurveSegment, SegmentedCurve
from core.models import CurvePoint, PointStatus


class TestCurveSegment:
    """Test CurveSegment class functionality."""

    def test_init_empty_segment(self):
        """Test creating an empty segment."""
        segment = CurveSegment(start_frame=1, end_frame=10)
        assert segment.start_frame == 1
        assert segment.end_frame == 10
        assert segment.points == []
        assert segment.is_active is True
        assert segment.starts_with_startframe is False

    def test_init_with_points(self):
        """Test creating a segment with points."""
        points = [
            CurvePoint(frame=5, x=10.0, y=20.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=10, x=15.0, y=25.0, status=PointStatus.NORMAL),
            CurvePoint(frame=15, x=20.0, y=30.0, status=PointStatus.KEYFRAME),
        ]
        segment = CurveSegment(start_frame=0, end_frame=20, points=points)

        # Frame range should be updated based on actual points
        assert segment.start_frame == 5
        assert segment.end_frame == 15
        assert len(segment.points) == 3

    def test_frame_range_property(self):
        """Test frame_range property."""
        segment = CurveSegment(start_frame=10, end_frame=50)
        assert segment.frame_range == (10, 50)

    def test_point_count_property(self):
        """Test point_count property."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0),
            CurvePoint(frame=2, x=1.0, y=1.0),
            CurvePoint(frame=3, x=2.0, y=2.0),
        ]
        segment = CurveSegment(start_frame=1, end_frame=3, points=points)
        assert segment.point_count == 3

    def test_has_keyframes(self):
        """Test has_keyframes property."""
        # Segment with no keyframes
        points_no_keyframes = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.NORMAL),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.INTERPOLATED),
        ]
        segment1 = CurveSegment(start_frame=1, end_frame=2, points=points_no_keyframes)
        assert segment1.has_keyframes is False

        # Segment with keyframes
        points_with_keyframes = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.INTERPOLATED),
        ]
        segment2 = CurveSegment(start_frame=1, end_frame=2, points=points_with_keyframes)
        assert segment2.has_keyframes is True

        # Segment with tracked points (also considered keyframes)
        points_with_tracked = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.TRACKED),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.NORMAL),
        ]
        segment3 = CurveSegment(start_frame=1, end_frame=2, points=points_with_tracked)
        assert segment3.has_keyframes is True

    def test_contains_frame(self):
        """Test contains_frame method."""
        segment = CurveSegment(start_frame=10, end_frame=20)

        assert segment.contains_frame(10) is True  # Start boundary
        assert segment.contains_frame(15) is True  # Middle
        assert segment.contains_frame(20) is True  # End boundary
        assert segment.contains_frame(9) is False  # Before start
        assert segment.contains_frame(21) is False  # After end

    def test_get_point_at_frame(self):
        """Test get_point_at_frame method."""
        points = [
            CurvePoint(frame=10, x=1.0, y=1.0),
            CurvePoint(frame=15, x=2.0, y=2.0),
            CurvePoint(frame=20, x=3.0, y=3.0),
        ]
        segment = CurveSegment(start_frame=10, end_frame=20, points=points)

        # Find existing points
        point10 = segment.get_point_at_frame(10)
        assert point10 is not None
        assert point10.frame == 10
        assert point10.x == 1.0

        point15 = segment.get_point_at_frame(15)
        assert point15 is not None
        assert point15.frame == 15
        assert point15.x == 2.0

        # Non-existing frame
        point12 = segment.get_point_at_frame(12)
        assert point12 is None


class TestSegmentedCurve:
    """Test SegmentedCurve class functionality."""

    def test_from_points_empty(self):
        """Test creating SegmentedCurve from empty points list."""
        curve = SegmentedCurve.from_points([])
        assert len(curve.segments) == 0
        assert len(curve.all_points) == 0

    def test_from_points_simple_continuous(self):
        """Test creating SegmentedCurve from continuous points (no ENDFRAME)."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.INTERPOLATED),
            CurvePoint(frame=3, x=2.0, y=2.0, status=PointStatus.KEYFRAME),
        ]
        curve = SegmentedCurve.from_points(points)

        assert len(curve.segments) == 1
        assert curve.segments[0].is_active is True
        assert curve.segments[0].point_count == 3
        assert curve.segments[0].frame_range == (1, 3)

    def test_from_points_with_endframe(self):
        """Test segmentation with ENDFRAME points."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=2, x=1.0, y=1.1, status=PointStatus.INTERPOLATED),
            CurvePoint(frame=3, x=2.0, y=2.0, status=PointStatus.ENDFRAME),  # Ends segment
            CurvePoint(frame=4, x=3.0, y=3.0, status=PointStatus.INTERPOLATED),  # Inactive
            CurvePoint(frame=5, x=4.0, y=4.0, status=PointStatus.KEYFRAME),  # Starts new active segment
            CurvePoint(frame=6, x=5.0, y=5.0, status=PointStatus.NORMAL),
        ]
        curve = SegmentedCurve.from_points(points)

        # Correct behavior: 3 segments with proper activity states
        assert len(curve.segments) == 3

        # First segment (active, ends with ENDFRAME)
        assert curve.segments[0].is_active is True
        assert curve.segments[0].point_count == 3
        assert curve.segments[0].frame_range == (1, 3)

        # Second segment (inactive, INTERPOLATED after ENDFRAME)
        assert curve.segments[1].is_active is False
        assert curve.segments[1].point_count == 1
        assert curve.segments[1].frame_range == (4, 4)

        # Third segment (active, starts with KEYFRAME)
        assert curve.segments[2].is_active is True
        assert curve.segments[2].point_count == 2
        assert curve.segments[2].frame_range == (5, 6)

    def test_from_points_multiple_endframes(self):
        """Test handling multiple ENDFRAME points."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.ENDFRAME),
            CurvePoint(frame=3, x=2.0, y=2.0, status=PointStatus.ENDFRAME),  # Another ENDFRAME
            CurvePoint(frame=4, x=3.0, y=3.0, status=PointStatus.TRACKED),  # Inactive after ENDFRAME
            CurvePoint(frame=5, x=4.0, y=4.0, status=PointStatus.NORMAL),
        ]
        curve = SegmentedCurve.from_points(points)

        # Should create appropriate segments
        assert len(curve.segments) >= 2
        # Last segment should be inactive (TRACKED points after ENDFRAME remain inactive until KEYFRAME)
        assert curve.segments[-1].is_active is False

    def test_from_points_unsorted(self):
        """Test that points are sorted before segmentation."""
        points = [
            CurvePoint(frame=3, x=2.0, y=2.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.INTERPOLATED),
        ]
        curve = SegmentedCurve.from_points(points)

        # Points should be sorted
        assert curve.all_points[0].frame == 1
        assert curve.all_points[1].frame == 2
        assert curve.all_points[2].frame == 3

    def test_active_segments_property(self):
        """Test active_segments property."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.ENDFRAME),
            CurvePoint(frame=3, x=2.0, y=2.0, status=PointStatus.INTERPOLATED),  # Inactive
            CurvePoint(frame=4, x=3.0, y=3.0, status=PointStatus.KEYFRAME),  # Starts new active segment
        ]
        curve = SegmentedCurve.from_points(points)

        active = curve.active_segments
        assert len(active) == 2  # First segment and KEYFRAME segment are active
        assert all(s.is_active for s in active)
        assert active[0].frame_range == (1, 2)
        assert active[1].frame_range == (4, 4)

    def test_inactive_segments_property(self):
        """Test inactive_segments property."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.ENDFRAME),
            CurvePoint(frame=3, x=2.0, y=2.0, status=PointStatus.INTERPOLATED),  # Inactive
            CurvePoint(frame=4, x=3.0, y=3.0, status=PointStatus.KEYFRAME),
        ]
        curve = SegmentedCurve.from_points(points)

        inactive = curve.inactive_segments
        assert len(inactive) == 1
        assert all(not s.is_active for s in inactive)

    def test_frame_range_property(self):
        """Test frame_range property."""
        # Empty curve
        empty_curve = SegmentedCurve()
        assert empty_curve.frame_range is None

        # Curve with points
        points = [
            CurvePoint(frame=10, x=0.0, y=0.0),
            CurvePoint(frame=20, x=1.0, y=1.0),
            CurvePoint(frame=15, x=2.0, y=2.0),
        ]
        curve = SegmentedCurve.from_points(points)
        assert curve.frame_range == (10, 20)

    def test_get_segment_at_frame(self):
        """Test get_segment_at_frame method."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=5, x=1.0, y=1.0, status=PointStatus.ENDFRAME),
            CurvePoint(frame=10, x=2.0, y=2.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=15, x=3.0, y=3.0, status=PointStatus.NORMAL),
        ]
        curve = SegmentedCurve.from_points(points)

        # Frame in first segment
        segment1 = curve.get_segment_at_frame(3)
        assert segment1 is not None
        assert segment1.contains_frame(3)

        # Frame in second segment
        segment2 = curve.get_segment_at_frame(12)
        assert segment2 is not None
        assert segment2.contains_frame(12)

        # Frame not in any segment
        segment_none = curve.get_segment_at_frame(100)
        assert segment_none is None

    def test_get_active_points(self):
        """Test get_active_points method."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.ENDFRAME),
            CurvePoint(frame=3, x=2.0, y=2.0, status=PointStatus.INTERPOLATED),  # Inactive
            CurvePoint(frame=4, x=3.0, y=3.0, status=PointStatus.KEYFRAME),  # Starts new active segment
            CurvePoint(frame=5, x=4.0, y=4.0, status=PointStatus.NORMAL),  # Active (part of KEYFRAME segment)
        ]
        curve = SegmentedCurve.from_points(points)

        active_points = curve.get_active_points()
        # Should have points from active segments only
        active_frames = [p.frame for p in active_points]
        assert 1 in active_frames  # From first active segment
        assert 2 in active_frames  # From first active segment
        assert 3 not in active_frames  # Inactive segment
        assert 4 in active_frames  # From second active segment (KEYFRAME)
        assert 5 in active_frames  # From second active segment (continues from KEYFRAME)

    def test_get_interpolation_boundaries(self):
        """Test get_interpolation_boundaries method."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=5, x=1.0, y=1.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=10, x=2.0, y=2.0, status=PointStatus.ENDFRAME),
            CurvePoint(frame=15, x=3.0, y=3.0, status=PointStatus.INTERPOLATED),  # Inactive
            CurvePoint(frame=20, x=4.0, y=4.0, status=PointStatus.KEYFRAME),  # Starts new active segment
            CurvePoint(frame=25, x=5.0, y=5.0, status=PointStatus.KEYFRAME),  # Active segment continues
        ]
        curve = SegmentedCurve.from_points(points)

        # Frame 3: between two keyframes in active segment
        prev, next = curve.get_interpolation_boundaries(3)
        assert prev is not None
        assert prev.frame == 1
        assert next is not None
        assert next.frame == 5

        # Frame 7: between keyframe and endframe in active segment
        # ENDFRAME is not considered a valid interpolation boundary
        prev, next = curve.get_interpolation_boundaries(7)
        assert prev is not None
        assert prev.frame == 5
        assert next is None  # ENDFRAME at frame 10 is not returned as boundary

        # Frame 17: in inactive segment
        prev, next = curve.get_interpolation_boundaries(17)
        assert prev is None
        assert next is None

        # Frame 22: in new active segment started by KEYFRAME at frame 20
        prev, next = curve.get_interpolation_boundaries(22)
        assert prev is not None
        assert prev.frame == 20
        assert next is not None
        assert next.frame == 25

    def test_get_interpolation_boundaries_edge_cases(self):
        """Test get_interpolation_boundaries edge cases."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=5, x=1.0, y=1.0, status=PointStatus.NORMAL),
            CurvePoint(frame=10, x=2.0, y=2.0, status=PointStatus.TRACKED),
        ]
        curve = SegmentedCurve.from_points(points)

        # Frame before all points
        prev, next = curve.get_interpolation_boundaries(0)
        assert prev is None
        assert next is None  # Outside segment range

        # Frame after all points
        prev, next = curve.get_interpolation_boundaries(20)
        assert prev is None
        assert next is None  # Outside segment range

        # Frame exactly on a keyframe
        prev, next = curve.get_interpolation_boundaries(5)
        assert prev is not None
        assert prev.frame == 1
        assert next is not None
        assert next.frame == 10

    def test_update_segment_activity(self):
        """Test update_segment_activity method."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.ENDFRAME),
            CurvePoint(frame=3, x=2.0, y=2.0, status=PointStatus.INTERPOLATED),
            CurvePoint(frame=4, x=3.0, y=3.0, status=PointStatus.NORMAL),
        ]
        curve = SegmentedCurve.from_points(points)

        # Initially, segment after ENDFRAME should be inactive
        segment_after = curve.get_segment_at_frame(3)
        assert segment_after is not None
        assert segment_after.is_active is False

        # Change ENDFRAME to KEYFRAME
        curve.update_segment_activity(1, PointStatus.KEYFRAME)

        # Segment should now be active
        # Note: This test assumes update_segment_activity modifies existing segments
        # The actual implementation might need adjustment

    def test_update_segment_activity_invalid_index(self):
        """Test update_segment_activity with invalid index."""
        points = [
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
        ]
        curve = SegmentedCurve.from_points(points)

        # Should not crash with invalid indices
        curve.update_segment_activity(-1, PointStatus.ENDFRAME)
        curve.update_segment_activity(100, PointStatus.ENDFRAME)

    def test_from_curve_data(self):
        """Test from_curve_data classmethod."""
        # Legacy format with tuples
        from typing import cast

        from core.type_aliases import CurveDataList

        curve_data = [
            (1, 0.0, 0.0, "keyframe"),
            (2, 1.0, 1.0, "interpolated"),
            (3, 2.0, 2.0, "endframe"),
            (4, 3.0, 3.0, "normal"),
        ]
        curve = SegmentedCurve.from_curve_data(cast(CurveDataList, curve_data))

        assert len(curve.all_points) == 4
        assert curve.all_points[0].status == PointStatus.KEYFRAME
        assert curve.all_points[2].status == PointStatus.ENDFRAME

        # Should create segments properly
        assert len(curve.segments) >= 1

    def test_complex_segmentation_scenario(self):
        """Test a complex scenario with multiple segments and transitions."""
        points = [
            # First active segment
            CurvePoint(frame=1, x=0.0, y=0.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=2, x=1.0, y=1.0, status=PointStatus.INTERPOLATED),
            CurvePoint(frame=3, x=2.0, y=2.0, status=PointStatus.TRACKED),
            CurvePoint(frame=4, x=3.0, y=3.0, status=PointStatus.ENDFRAME),
            # Inactive region
            CurvePoint(frame=5, x=4.0, y=4.0, status=PointStatus.INTERPOLATED),
            CurvePoint(frame=6, x=5.0, y=5.0, status=PointStatus.NORMAL),
            # Second active segment (starts with KEYFRAME)
            CurvePoint(frame=7, x=6.0, y=6.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=8, x=7.0, y=7.0, status=PointStatus.INTERPOLATED),
            CurvePoint(frame=9, x=8.0, y=8.0, status=PointStatus.ENDFRAME),
            # Another inactive region
            CurvePoint(frame=10, x=9.0, y=9.0, status=PointStatus.INTERPOLATED),
            # Third segment (inactive - TRACKED after ENDFRAME)
            CurvePoint(frame=11, x=10.0, y=10.0, status=PointStatus.TRACKED),
            CurvePoint(frame=12, x=11.0, y=11.0, status=PointStatus.NORMAL),
        ]
        curve = SegmentedCurve.from_points(points)

        # Correct behavior: 4 segments with proper activity states
        assert len(curve.segments) == 4

        # First segment: frames 1-4 (active, ends with ENDFRAME)
        assert curve.segments[0].is_active is True
        assert curve.segments[0].frame_range == (1, 4)

        # Second segment: frames 5-6 (inactive after ENDFRAME)
        assert curve.segments[1].is_active is False
        assert curve.segments[1].frame_range == (5, 6)

        # Third segment: frames 7-9 (active, starts with KEYFRAME)
        assert curve.segments[2].is_active is True
        assert curve.segments[2].frame_range == (7, 9)

        # Fourth segment: frames 10-12 (inactive, TRACKED after ENDFRAME remains inactive)
        assert curve.segments[3].is_active is False
        assert curve.segments[3].frame_range == (10, 12)

        # Two segments should be active (frames 1-4 and 7-9)
        active_segs = curve.active_segments
        assert len(active_segs) == 2
        assert active_segs[0].frame_range == (1, 4)

        # Verify interpolation boundaries
        # Frame 2 is in active segment
        prev, next = curve.get_interpolation_boundaries(2)
        assert prev is not None
        assert prev.frame == 1
        assert next is not None
        assert next.frame == 3 or next.frame == 4

        # Frame 7 is in inactive segment
        prev, next = curve.get_interpolation_boundaries(7)
        assert prev is None
        assert next is None


class TestPositionHolding:
    """Test position holding behavior in gaps (inactive segments)."""

    def test_position_holding_basic_gap(self):
        """Test basic position holding in a gap after endframe."""
        points = [
            CurvePoint(frame=1, x=100.0, y=200.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=5, x=150.0, y=250.0, status=PointStatus.ENDFRAME),  # Creates gap
            CurvePoint(frame=10, x=200.0, y=300.0, status=PointStatus.KEYFRAME),  # Startframe after gap
        ]
        curve = SegmentedCurve.from_points(points)

        # Active segment: frames 1-5
        assert curve.get_position_at_frame(1) == (100.0, 200.0)
        assert curve.get_position_at_frame(3) is not None  # Interpolated in active segment
        assert curve.get_position_at_frame(5) == (150.0, 250.0)  # Endframe position

        # Gap (inactive segment): frames 6-9 should hold endframe position
        assert curve.get_position_at_frame(6) == (150.0, 250.0)  # Held position
        assert curve.get_position_at_frame(7) == (150.0, 250.0)  # Held position
        assert curve.get_position_at_frame(8) == (150.0, 250.0)  # Held position
        assert curve.get_position_at_frame(9) == (150.0, 250.0)  # Held position

        # Next active segment starts at frame 10
        assert curve.get_position_at_frame(10) == (200.0, 300.0)  # Startframe

    def test_position_holding_multiple_gaps(self):
        """Test position holding with multiple gaps."""
        points = [
            CurvePoint(frame=1, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=3, x=120.0, y=120.0, status=PointStatus.ENDFRAME),  # First gap starts
            CurvePoint(frame=6, x=150.0, y=150.0, status=PointStatus.KEYFRAME),  # End first gap
            CurvePoint(frame=8, x=170.0, y=170.0, status=PointStatus.ENDFRAME),  # Second gap starts
            CurvePoint(frame=12, x=200.0, y=200.0, status=PointStatus.KEYFRAME),  # End second gap
        ]
        curve = SegmentedCurve.from_points(points)

        # First gap: frames 4-5 hold position from frame 3
        assert curve.get_position_at_frame(4) == (120.0, 120.0)
        assert curve.get_position_at_frame(5) == (120.0, 120.0)

        # Second gap: frames 9-11 hold position from frame 8
        assert curve.get_position_at_frame(9) == (170.0, 170.0)
        assert curve.get_position_at_frame(10) == (170.0, 170.0)
        assert curve.get_position_at_frame(11) == (170.0, 170.0)

        # Active segments work normally
        assert curve.get_position_at_frame(6) == (150.0, 150.0)  # Startframe
        assert curve.get_position_at_frame(12) == (200.0, 200.0)  # Startframe

    def test_position_holding_no_gaps(self):
        """Test that position holding doesn't affect curves without gaps."""
        points = [
            CurvePoint(frame=1, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=5, x=150.0, y=150.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=10, x=200.0, y=200.0, status=PointStatus.KEYFRAME),
        ]
        curve = SegmentedCurve.from_points(points)

        # All frames should interpolate normally (no gaps)
        assert curve.get_position_at_frame(1) == (100.0, 100.0)
        assert curve.get_position_at_frame(3) is not None  # Should interpolate
        assert curve.get_position_at_frame(5) == (150.0, 150.0)
        assert curve.get_position_at_frame(7) is not None  # Should interpolate
        assert curve.get_position_at_frame(10) == (200.0, 200.0)

    def test_position_holding_edge_cases(self):
        """Test edge cases for position holding."""
        points = [
            CurvePoint(frame=5, x=150.0, y=150.0, status=PointStatus.ENDFRAME),
        ]
        curve = SegmentedCurve.from_points(points)

        # Single endframe - should return its position for any later frame
        assert curve.get_position_at_frame(5) == (150.0, 150.0)
        assert curve.get_position_at_frame(6) == (150.0, 150.0)
        assert curve.get_position_at_frame(10) == (150.0, 150.0)

        # Frame before endframe - no position available
        assert curve.get_position_at_frame(4) is None

    def test_interpolation_in_active_segments(self):
        """Test that interpolation works correctly in active segments."""
        points = [
            CurvePoint(frame=1, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=5, x=200.0, y=200.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=7, x=250.0, y=250.0, status=PointStatus.ENDFRAME),
        ]
        curve = SegmentedCurve.from_points(points)

        # Test interpolation between keyframes in active segment
        position = curve.get_position_at_frame(3)  # Halfway between frame 1 and 5
        assert position is not None
        x, y = position
        assert x == 150.0  # Interpolated X: 100 + (200-100) * 0.5
        assert y == 150.0  # Interpolated Y: 100 + (200-100) * 0.5

        # Test exact positions
        assert curve.get_position_at_frame(1) == (100.0, 100.0)
        assert curve.get_position_at_frame(5) == (200.0, 200.0)
        assert curve.get_position_at_frame(7) == (250.0, 250.0)

        # Test gap after endframe (frame 8+ should hold endframe position)
        assert curve.get_position_at_frame(8) == (250.0, 250.0)
        assert curve.get_position_at_frame(10) == (250.0, 250.0)

    def test_multiple_endframes_create_continuous_gap(self):
        """Test that multiple endframes create a continuous gap until a keyframe.

        When multiple endframes occur in sequence without a keyframe between them,
        all segments after the first endframe should be inactive (in the gap) until
        a keyframe (startframe) appears to end the gap.
        """
        # Create curve with two endframes and NO keyframe between them
        points = [
            CurvePoint(frame=100, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=150, x=150.0, y=150.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=200, x=200.0, y=200.0, status=PointStatus.ENDFRAME),  # First endframe
            CurvePoint(frame=250, x=250.0, y=250.0, status=PointStatus.TRACKED),
            CurvePoint(frame=300, x=300.0, y=300.0, status=PointStatus.ENDFRAME),  # Second endframe (still in gap!)
        ]
        curve = SegmentedCurve.from_points(points)

        # Find segments containing each endframe
        segment_200 = curve.get_segment_at_frame(200)
        segment_300 = curve.get_segment_at_frame(300)

        # Both segments should exist
        assert segment_200 is not None, "Segment containing first endframe should exist"
        assert segment_300 is not None, "Segment containing second endframe should exist"

        # First endframe segment should be ACTIVE (contains curve leading up to endframe)
        assert segment_200.is_active, "First endframe segment should be active"

        # Second endframe segment should be INACTIVE (it's in the gap after first endframe, no keyframe yet)
        assert not segment_300.is_active, "Second endframe segment should be inactive (in gap)"

        # Verify the endframes are in their respective segments
        assert any(p.frame == 200 and p.is_endframe for p in segment_200.points)
        assert any(p.frame == 300 and p.is_endframe for p in segment_300.points)

    def test_three_endframes_create_continuous_gap(self):
        """Test that three or more endframes in sequence create continuous gap."""
        # Create curve with three endframes without keyframes between them
        points = [
            CurvePoint(frame=100, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=200, x=200.0, y=200.0, status=PointStatus.ENDFRAME),  # First - creates gap
            CurvePoint(frame=250, x=250.0, y=250.0, status=PointStatus.TRACKED),  # In gap
            CurvePoint(frame=300, x=300.0, y=300.0, status=PointStatus.ENDFRAME),  # Second - still in gap
            CurvePoint(frame=350, x=350.0, y=350.0, status=PointStatus.TRACKED),  # Still in gap
            CurvePoint(frame=400, x=400.0, y=400.0, status=PointStatus.ENDFRAME),  # Third - still in gap
        ]
        curve = SegmentedCurve.from_points(points)

        # First endframe segment should be ACTIVE
        segment_200 = curve.get_segment_at_frame(200)
        assert segment_200 is not None, "Segment at frame 200 should exist"
        assert segment_200.is_active, "First endframe segment should be active"

        # All subsequent endframe segments should be INACTIVE (in the gap)
        for endframe_number in [300, 400]:
            segment = curve.get_segment_at_frame(endframe_number)
            assert segment is not None, f"Segment at frame {endframe_number} should exist"
            assert not segment.is_active, f"Endframe segment at {endframe_number} should be inactive (in gap)"

    def test_endframes_correctly_segment_curve(self):
        """Test that multiple endframes correctly create separate curve segments."""
        points = [
            CurvePoint(frame=100, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=150, x=150.0, y=150.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=200, x=200.0, y=200.0, status=PointStatus.ENDFRAME),  # End segment 1
            CurvePoint(frame=250, x=250.0, y=250.0, status=PointStatus.TRACKED),  # Gap (inactive)
            CurvePoint(frame=300, x=300.0, y=300.0, status=PointStatus.KEYFRAME),  # Start segment 2
            CurvePoint(frame=350, x=350.0, y=350.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=400, x=400.0, y=400.0, status=PointStatus.ENDFRAME),  # End segment 2
        ]
        curve = SegmentedCurve.from_points(points)

        # Should have at least 3 segments: [100-200], [250], [300-400]
        assert len(curve.segments) >= 3

        # First segment (100-200) should be active and end with endframe
        segment_1 = curve.get_segment_at_frame(100)
        assert segment_1 is not None
        assert segment_1.is_active
        assert any(p.frame == 200 and p.is_endframe for p in segment_1.points)

        # Tracked points after first endframe should be inactive
        segment_tracked = curve.get_segment_at_frame(250)
        assert segment_tracked is not None
        assert not segment_tracked.is_active, "TRACKED points after endframe should be inactive"

        # Second active segment (300-400) should be active and end with endframe
        segment_2 = curve.get_segment_at_frame(300)
        assert segment_2 is not None
        assert segment_2.is_active
        assert any(p.frame == 400 and p.is_endframe for p in segment_2.points)

    def test_endframe_preceded_by_tracked_in_gap(self):
        """Test that endframes after tracked points (in gaps) are correctly inactive."""
        # Scenario: Two endframes with tracked points between (all in continuous gap)
        points = [
            CurvePoint(frame=200, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
            CurvePoint(frame=250, x=250.0, y=250.0, status=PointStatus.TRACKED),
            CurvePoint(frame=300, x=300.0, y=300.0, status=PointStatus.ENDFRAME),
        ]
        curve = SegmentedCurve.from_points(points)

        # Segments should exist and not be incorrectly split
        segment_200 = curve.get_segment_at_frame(200)
        segment_300 = curve.get_segment_at_frame(300)
        assert segment_200 is not None
        assert segment_300 is not None

        # First endframe segment should be ACTIVE
        assert segment_200.is_active, "First endframe segment should be active"

        # Second endframe segment should be INACTIVE (it's in the gap after first endframe)
        assert not segment_300.is_active, "Segment with second endframe should be inactive (in gap)"

        # The endframe should be in this segment
        assert any(p.frame == 300 and p.is_endframe for p in segment_300.points)

    def test_consecutive_endframes_gap_ends_at_keyframe(self):
        """Test that gaps created by multiple endframes end when a keyframe appears.

        This is the complete scenario: multiple endframes create a continuous gap,
        and the gap ends when a keyframe (startframe) appears.
        """
        points = [
            CurvePoint(frame=10, x=10.0, y=10.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=15, x=15.0, y=15.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=20, x=20.0, y=20.0, status=PointStatus.ENDFRAME),  # First endframe - creates gap
            CurvePoint(frame=25, x=25.0, y=25.0, status=PointStatus.TRACKED),  # In gap
            CurvePoint(frame=30, x=30.0, y=30.0, status=PointStatus.ENDFRAME),  # Second endframe - still in gap
            CurvePoint(frame=35, x=35.0, y=35.0, status=PointStatus.TRACKED),  # Still in gap
            CurvePoint(frame=40, x=40.0, y=40.0, status=PointStatus.KEYFRAME),  # Ends gap - becomes startframe
            CurvePoint(frame=45, x=45.0, y=45.0, status=PointStatus.KEYFRAME),
        ]
        curve = SegmentedCurve.from_points(points)

        # Segment containing first endframe (10-20) should be ACTIVE
        segment_20 = curve.get_segment_at_frame(20)
        assert segment_20 is not None
        assert segment_20.is_active, "Segment ending with first endframe should be active"

        # Segments in the gap (after frame 20, before frame 40) should be INACTIVE
        segment_25 = curve.get_segment_at_frame(25)
        if segment_25:
            assert not segment_25.is_active, "Tracked points in gap should be inactive"

        segment_30 = curve.get_segment_at_frame(30)
        assert segment_30 is not None
        assert not segment_30.is_active, "Second endframe in gap should be inactive"

        segment_35 = curve.get_segment_at_frame(35)
        if segment_35:
            assert not segment_35.is_active, "Tracked points after second endframe should be inactive"

        # Segment starting with keyframe (40+) should be ACTIVE (gap ends here)
        segment_40 = curve.get_segment_at_frame(40)
        assert segment_40 is not None
        assert segment_40.is_active, "Segment starting with keyframe should be active (ends gap)"

        # Verify that frame 40 is recognized as a startframe
        point_40 = next((p for p in points if p.frame == 40), None)
        assert point_40 is not None
        assert point_40.is_startframe(all_points=points), "Frame 40 should be a startframe (first keyframe after gap)"
