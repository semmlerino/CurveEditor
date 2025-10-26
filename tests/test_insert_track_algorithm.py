#!/usr/bin/env python
"""
Tests for Insert Track algorithm functions.

Tests all core functions used in the Insert Track feature for gap detection,
offset calculation, data merging, and averaging.
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

from typing import cast

import pytest

from core.insert_track_algorithm import (
    average_multiple_sources,
    calculate_offset,
    create_averaged_curve,
    fill_gap_with_source,
    find_gap_around_frame,
    find_overlap_frames,
    interpolate_gap,
)
from core.type_aliases import CurveDataList, PointTuple4Str


class TestFindGapAroundFrame:
    """Test gap detection functionality."""

    def test_gap_in_middle(self):
        """Test finding a gap in the middle of trajectory."""
        curve_data = cast(
            CurveDataList,
            [
                (1, 10.0, 10.0),
                (2, 11.0, 11.0),
                (10, 20.0, 20.0),
                (11, 21.0, 21.0),
            ],
        )

        result = find_gap_around_frame(curve_data, 5)

        assert result is not None
        assert result == (3, 9)

    def test_no_gap_at_frame(self):
        """Test that None is returned when frame has data."""
        curve_data = cast(CurveDataList, [(1, 10.0, 10.0), (2, 11.0, 11.0), (3, 12.0, 12.0)])

        result = find_gap_around_frame(curve_data, 2)

        assert result is None

    def test_gap_at_start(self):
        """Test gap at the beginning of trajectory."""
        curve_data = cast(CurveDataList, [(10, 20.0, 20.0), (11, 21.0, 21.0)])

        result = find_gap_around_frame(curve_data, 5)

        assert result is not None
        assert result[0] == 1  # Gap starts from frame 1
        assert result[1] == 9

    def test_gap_at_end(self):
        """Test gap at the end (open-ended) returns None."""
        curve_data = cast(CurveDataList, [(1, 10.0, 10.0), (2, 11.0, 11.0)])

        result = find_gap_around_frame(curve_data, 10)

        # Open-ended gaps cannot be filled
        assert result is None

    def test_empty_curve(self):
        """Test empty curve returns None."""
        result = find_gap_around_frame([], 5)
        assert result is None

    def test_single_point_curve(self):
        """Test curve with single point."""
        curve_data = cast(CurveDataList, [(5, 10.0, 10.0)])

        # Before the point
        result = find_gap_around_frame(curve_data, 3)
        assert result == (1, 4)

        # After the point (open-ended)
        result = find_gap_around_frame(curve_data, 10)
        assert result is None

    def test_status_based_gap_between_endframe_and_keyframe(self):
        """Test status-based gap detection (ENDFRAME to KEYFRAME)."""
        curve_data = cast(
            CurveDataList,
            [
                (1, 10.0, 10.0, "keyframe"),
                (5, 20.0, 20.0, "endframe"),
                (10, 30.0, 30.0, "tracked"),  # In gap
                (15, 40.0, 40.0, "tracked"),  # In gap
                (20, 50.0, 50.0, "keyframe"),  # STARTFRAME - gap ends here
                (25, 60.0, 60.0, "tracked"),
            ],
        )

        # Frame 10 is in the gap (between ENDFRAME at 5 and KEYFRAME at 20)
        result = find_gap_around_frame(curve_data, 10)
        assert result is not None
        assert result == (6, 19)  # Gap from frame after ENDFRAME to frame before KEYFRAME

        # Frame 15 is also in the gap
        result = find_gap_around_frame(curve_data, 15)
        assert result is not None
        assert result == (6, 19)

    def test_status_based_gap_frame_with_data(self):
        """Test that frames with data inside gap are still detected as gaps."""
        curve_data = cast(
            CurveDataList,
            [
                (1, 10.0, 10.0, "keyframe"),
                (5, 20.0, 20.0, "endframe"),
                (8, 25.0, 25.0, "tracked"),  # Has data but is in gap
                (12, 35.0, 35.0, "tracked"),  # Has data but is in gap
                (15, 40.0, 40.0, "keyframe"),  # STARTFRAME
            ],
        )

        # Frame 8 has data but is in the gap
        result = find_gap_around_frame(curve_data, 8)
        assert result is not None
        assert result == (6, 14)

    def test_status_based_gap_no_keyframe_after_endframe(self):
        """Test open-ended gap when no KEYFRAME after ENDFRAME."""
        curve_data = cast(
            CurveDataList,
            [
                (1, 10.0, 10.0, "keyframe"),
                (5, 20.0, 20.0, "endframe"),
                (10, 30.0, 30.0, "tracked"),  # After endframe but no keyframe follows
                (15, 40.0, 40.0, "tracked"),
            ],
        )

        # No KEYFRAME after ENDFRAME - open-ended gap, cannot fill
        result = find_gap_around_frame(curve_data, 10)
        assert result is None

    def test_status_based_gap_frame_before_endframe(self):
        """Test that frames before ENDFRAME are not considered gaps."""
        curve_data = cast(
            CurveDataList,
            [
                (1, 10.0, 10.0, "keyframe"),
                (3, 15.0, 15.0, "tracked"),
                (5, 20.0, 20.0, "endframe"),
                (10, 30.0, 30.0, "keyframe"),
            ],
        )

        # Frame 3 is before ENDFRAME - not a gap
        result = find_gap_around_frame(curve_data, 3)
        assert result is None

    def test_status_based_gap_frame_at_keyframe(self):
        """Test that frame at KEYFRAME after gap is not considered gap."""
        curve_data = cast(
            CurveDataList,
            [
                (1, 10.0, 10.0, "keyframe"),
                (5, 20.0, 20.0, "endframe"),
                (10, 30.0, 30.0, "keyframe"),  # STARTFRAME
            ],
        )

        # Frame 10 is the KEYFRAME/STARTFRAME - not in gap
        result = find_gap_around_frame(curve_data, 10)
        assert result is None


class TestFindOverlapFrames:
    """Test overlap detection between target and source curves."""

    def test_overlap_before_and_after_gap(self):
        """Test finding overlap on both sides of gap."""
        target = cast(CurveDataList, [(1, 10.0, 10.0), (2, 11.0, 11.0), (10, 20.0, 20.0), (11, 21.0, 21.0)])
        source = cast(
            CurveDataList, [(1, 15.0, 15.0), (2, 16.0, 16.0), (3, 17.0, 17.0), (10, 25.0, 25.0), (11, 26.0, 26.0)]
        )

        gap_start, gap_end = 3, 9

        before, after = find_overlap_frames(target, source, gap_start, gap_end)

        assert before == [1, 2]
        assert after == [10, 11]

    def test_overlap_before_only(self):
        """Test overlap only before gap."""
        target = cast(CurveDataList, [(1, 10.0, 10.0), (2, 11.0, 11.0), (10, 20.0, 20.0)])
        source = cast(CurveDataList, [(1, 15.0, 15.0), (2, 16.0, 16.0), (3, 17.0, 17.0)])

        gap_start, gap_end = 3, 9

        before, after = find_overlap_frames(target, source, gap_start, gap_end)

        assert before == [1, 2]
        assert after == []

    def test_overlap_after_only(self):
        """Test overlap only after gap."""
        target = cast(CurveDataList, [(1, 10.0, 10.0), (10, 20.0, 20.0), (11, 21.0, 21.0)])
        source = cast(CurveDataList, [(5, 17.0, 17.0), (10, 25.0, 25.0), (11, 26.0, 26.0)])

        gap_start, gap_end = 2, 9

        before, after = find_overlap_frames(target, source, gap_start, gap_end)

        assert before == []
        assert after == [10, 11]

    def test_no_overlap(self):
        """Test no overlap between curves."""
        target = cast(CurveDataList, [(1, 10.0, 10.0), (2, 11.0, 11.0)])
        source = cast(CurveDataList, [(10, 25.0, 25.0), (11, 26.0, 26.0)])

        gap_start, gap_end = 3, 9

        before, after = find_overlap_frames(target, source, gap_start, gap_end)

        assert before == []
        assert after == []


class TestCalculateOffset:
    """Test offset calculation between curves."""

    def test_simple_offset(self):
        """Test calculating offset with constant difference."""
        target = cast(CurveDataList, [(1, 100.0, 200.0), (2, 101.0, 201.0)])
        source = cast(CurveDataList, [(1, 50.0, 100.0), (2, 51.0, 101.0)])

        offset_x, offset_y = calculate_offset(target, source, [1, 2])

        assert offset_x == pytest.approx(50.0)
        assert offset_y == pytest.approx(100.0)

    def test_averaged_offset(self):
        """Test offset is averaged across multiple frames."""
        target = cast(CurveDataList, [(1, 100.0, 200.0), (2, 110.0, 210.0)])
        source = cast(CurveDataList, [(1, 50.0, 100.0), (2, 55.0, 105.0)])

        offset_x, offset_y = calculate_offset(target, source, [1, 2])

        # Frame 1: offset = (50, 100)
        # Frame 2: offset = (55, 105)
        # Average: (52.5, 102.5)
        assert offset_x == pytest.approx(52.5)
        assert offset_y == pytest.approx(102.5)

    def test_single_overlap_frame(self):
        """Test offset with single overlap frame."""
        target = cast(CurveDataList, [(1, 100.0, 200.0)])
        source = cast(CurveDataList, [(1, 50.0, 100.0)])

        offset_x, offset_y = calculate_offset(target, source, [1])

        assert offset_x == pytest.approx(50.0)
        assert offset_y == pytest.approx(100.0)

    def test_no_overlap_frames(self):
        """Test offset returns (0, 0) with no overlap."""
        target = cast(CurveDataList, [(1, 100.0, 200.0)])
        source = cast(CurveDataList, [(2, 50.0, 100.0)])

        offset_x, offset_y = calculate_offset(target, source, [])

        assert offset_x == 0.0
        assert offset_y == 0.0


class TestFillGapWithSource:
    """Test gap filling with source data."""

    def test_basic_gap_filling(self):
        """Test filling a simple gap with offset."""
        target = cast(CurveDataList, [(1, 100.0, 200.0), (2, 101.0, 201.0), (10, 110.0, 210.0)])
        source = cast(CurveDataList, [(1, 50.0, 100.0), (3, 51.0, 101.0), (4, 52.0, 102.0), (10, 55.0, 105.0)])

        gap_start, gap_end = 3, 9
        offset = (50.0, 100.0)

        result = fill_gap_with_source(target, source, gap_start, gap_end, offset)

        # Should have original points plus gap fills
        frames = [p[0] for p in result]
        assert 1 in frames
        assert 2 in frames
        assert 3 in frames  # Filled from source
        assert 4 in frames  # Filled from source
        assert 10 in frames

        # Check offset was applied
        frame_3_point = next(p for p in result if p[0] == 3)
        assert frame_3_point[1] == pytest.approx(101.0)  # 51 + 50
        assert frame_3_point[2] == pytest.approx(201.0)  # 101 + 100

    def test_gap_boundaries_preserve_original_status(self):
        """Test that overlap frames (outside gap) preserve their original status."""
        target = cast(CurveDataList, [(1, 100.0, 200.0), (10, 110.0, 210.0)])
        source = cast(CurveDataList, [(3, 51.0, 101.0), (4, 52.0, 102.0)])

        gap_start, gap_end = 3, 9
        offset = (0.0, 0.0)

        result = fill_gap_with_source(target, source, gap_start, gap_end, offset)

        # Find overlap frames (frames OUTSIDE gap boundaries where original data exists)
        # overlap_before = gap_start - 1 = 2, but frame 1 is the actual existing frame
        # overlap_after = gap_end + 1 = 10
        frame_1_point = next(p for p in result if p[0] == 1)
        frame_10_point = next(p for p in result if p[0] == 10)
        frame_3_point = next(p for p in result if p[0] == 3)

        # Overlap frames (1, 10) should preserve original status (normal, since input was 3-tuples)
        assert len(frame_1_point) >= 4
        assert (
            cast(PointTuple4Str, frame_1_point)[3] == "normal"
        ), "Frame 1 (before gap) should preserve original status"
        assert len(frame_10_point) >= 4
        assert (
            cast(PointTuple4Str, frame_10_point)[3] == "normal"
        ), "Frame 10 (after gap) should preserve original status"

        # Filled frames (3) should be marked as keyframe (first filled point signals gap closure)
        # Per CLAUDE.md: "First filled point: KEYFRAME status (starts new active segment after gap)"
        assert len(frame_3_point) >= 4
        assert cast(PointTuple4Str, frame_3_point)[3] == "keyframe", "Frame 3 (first filled) should be keyframe"

    def test_partial_gap_coverage(self):
        """Test filling gap when source doesn't cover all gap frames."""
        target = cast(CurveDataList, [(1, 100.0, 200.0), (10, 110.0, 210.0)])
        source = cast(CurveDataList, [(3, 51.0, 101.0)])  # Only one frame in gap

        gap_start, gap_end = 2, 9
        offset = (50.0, 100.0)

        result = fill_gap_with_source(target, source, gap_start, gap_end, offset)

        # Should only fill frame 3
        gap_frames = [p[0] for p in result if 2 <= p[0] <= 9]
        assert gap_frames == [3]


class TestAverageMultipleSources:
    """Test averaging multiple source curves."""

    def test_average_two_sources(self):
        """Test averaging positions from two sources."""
        source1 = cast(CurveDataList, [(3, 100.0, 200.0), (4, 101.0, 201.0)])
        source2 = cast(CurveDataList, [(3, 110.0, 210.0), (4, 111.0, 211.0)])

        offsets = [(0.0, 0.0), (0.0, 0.0)]
        gap_frames = [3, 4]

        result = average_multiple_sources([source1, source2], gap_frames, offsets)

        assert len(result) == 2

        # Check averaged positions
        point_3 = result[0]
        assert point_3.frame == 3
        assert point_3.x == pytest.approx(105.0)  # (100 + 110) / 2
        assert point_3.y == pytest.approx(205.0)  # (200 + 210) / 2

    def test_average_with_offsets(self):
        """Test averaging with offset correction."""
        source1 = cast(CurveDataList, [(3, 100.0, 200.0)])
        source2 = cast(CurveDataList, [(3, 50.0, 100.0)])

        offsets = [(10.0, 20.0), (60.0, 120.0)]  # Different offsets
        gap_frames = [3]

        result = average_multiple_sources([source1, source2], gap_frames, offsets)

        # source1 + offset1 = (110, 220)
        # source2 + offset2 = (110, 220)
        # Average = (110, 220)
        assert len(result) == 1
        assert result[0].x == pytest.approx(110.0)
        assert result[0].y == pytest.approx(220.0)

    def test_average_partial_coverage(self):
        """Test averaging only fills frames where ALL sources have data (3DE spec compliance)."""
        source1 = cast(CurveDataList, [(3, 100.0, 200.0), (4, 101.0, 201.0)])
        source2 = cast(CurveDataList, [(3, 110.0, 210.0)])  # Missing frame 4

        offsets = [(0.0, 0.0), (0.0, 0.0)]
        gap_frames = [3, 4]

        result = average_multiple_sources([source1, source2], gap_frames, offsets)

        # Per 3DE spec: "averaged result will only cover the frameranges where
        # ALL input points have tracking information"
        # Only frame 3 has data from ALL sources, so only frame 3 should be in result
        assert len(result) == 1, "Should only include frames where ALL sources have data"

        # Frame 3: both sources present, should be averaged
        point_3 = next(p for p in result if p.frame == 3)
        assert point_3.x == pytest.approx(105.0), "Should average both sources: (100+110)/2 = 105"
        assert point_3.y == pytest.approx(205.0), "Should average both sources: (200+210)/2 = 205"

        # Frame 4: only source1 has data, should NOT be in result
        points_at_frame_4 = [p for p in result if p.frame == 4]
        assert len(points_at_frame_4) == 0, "Frame 4 should not be included (missing from source2)"


class TestInterpolateGap:
    """Test gap interpolation."""

    def test_linear_interpolation(self):
        """Test simple linear interpolation across gap."""
        curve = cast(CurveDataList, [(1, 100.0, 200.0), (10, 190.0, 290.0)])

        gap_start, gap_end = 2, 9

        result = interpolate_gap(curve, gap_start, gap_end)

        # Check middle point (frame 5.5 conceptually)
        # Linear interpolation from (1, 100, 200) to (10, 190, 290)
        frame_5_point = next(p for p in result if p[0] == 5)

        # At frame 5: t = (5-1)/(10-1) = 4/9
        # x = 100 + 4/9 * (190-100) = 100 + 40 = 140
        # y = 200 + 4/9 * (290-200) = 200 + 40 = 240
        assert frame_5_point[1] == pytest.approx(140.0)
        assert frame_5_point[2] == pytest.approx(240.0)

    def test_interpolation_boundaries_preserve_original_status(self):
        """Test that overlap frames (outside gap) preserve their original status."""
        curve = cast(CurveDataList, [(1, 100.0, 200.0), (10, 190.0, 290.0)])

        gap_start, gap_end = 2, 9

        result = interpolate_gap(curve, gap_start, gap_end)

        # Overlap frames (before and after gap) should preserve original status (normal)
        frame_1_point = next(p for p in result if p[0] == 1)
        frame_10_point = next(p for p in result if p[0] == 10)
        # Interpolated frames should be marked as interpolated
        frame_2_point = next(p for p in result if p[0] == 2)
        frame_9_point = next(p for p in result if p[0] == 9)

        assert (
            cast(PointTuple4Str, frame_1_point)[3] == "normal"
        ), "Frame 1 (before gap) should preserve original status"
        assert (
            cast(PointTuple4Str, frame_10_point)[3] == "normal"
        ), "Frame 10 (after gap) should preserve original status"
        assert cast(PointTuple4Str, frame_2_point)[3] == "interpolated", "Frame 2 (in gap) should be interpolated"
        assert cast(PointTuple4Str, frame_9_point)[3] == "interpolated", "Frame 9 (in gap) should be interpolated"

    def test_interpolation_missing_boundaries(self):
        """Test interpolation fails gracefully without boundary points."""
        # Gap from 2-9 but no point before frame 2
        curve = cast(CurveDataList, [(10, 190.0, 290.0)])

        gap_start, gap_end = 2, 9

        result = interpolate_gap(curve, gap_start, gap_end)

        # Should return original curve unchanged
        assert len(result) == 1
        assert result[0][0] == 10


class TestCreateAveragedCurve:
    """Test creating averaged curve from multiple sources."""

    def test_create_averaged_curve_simple(self):
        """Test creating averaged curve from two sources."""
        sources = cast(
            dict[str, CurveDataList],
            {
                "curve1": [(1, 100.0, 200.0), (2, 101.0, 201.0), (3, 102.0, 202.0)],
                "curve2": [(1, 110.0, 210.0), (2, 111.0, 211.0), (3, 112.0, 212.0)],
            },
        )

        name, curve = create_averaged_curve(sources)

        assert name == "avrg_01"
        assert len(curve) == 3

        # Check averages
        point_1 = curve[0]
        assert point_1[0] == 1
        assert point_1[1] == pytest.approx(105.0)  # (100 + 110) / 2
        assert point_1[2] == pytest.approx(205.0)  # (200 + 210) / 2

    def test_only_common_frames(self):
        """Test that only frames common to all sources are included."""
        sources = cast(
            dict[str, CurveDataList],
            {
                "curve1": [(1, 100.0, 200.0), (2, 101.0, 201.0), (3, 102.0, 202.0)],
                "curve2": [(1, 110.0, 210.0), (2, 111.0, 211.0)],  # Missing frame 3
            },
        )

        _, curve = create_averaged_curve(sources)

        # Should only include frames 1 and 2 (common to both)
        assert len(curve) == 2
        frames = [p[0] for p in curve]
        assert frames == [1, 2]

    def test_three_sources(self):
        """Test averaging three sources."""
        sources = cast(
            dict[str, CurveDataList],
            {
                "curve1": [(1, 100.0, 200.0)],
                "curve2": [(1, 110.0, 210.0)],
                "curve3": [(1, 120.0, 220.0)],
            },
        )

        _, curve = create_averaged_curve(sources)

        assert len(curve) == 1
        point = curve[0]
        assert point[1] == pytest.approx(110.0)  # (100 + 110 + 120) / 3
        assert point[2] == pytest.approx(210.0)  # (200 + 210 + 220) / 3

    def test_no_common_frames(self):
        """Test behavior when sources have no common frames."""
        sources = cast(
            dict[str, CurveDataList],
            {
                "curve1": [(1, 100.0, 200.0)],
                "curve2": [(2, 110.0, 210.0)],
            },
        )

        _, curve = create_averaged_curve(sources)

        # No common frames - should return empty curve
        assert len(curve) == 0

    def test_empty_sources(self):
        """Test error handling with no sources."""
        with pytest.raises(ValueError, match=r"No source curves provided|at least one"):
            create_averaged_curve({})
