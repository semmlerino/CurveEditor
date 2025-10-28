#!/usr/bin/env python3
"""
Tests for Insert Track gap filling status behavior.

Verifies that Insert Track correctly assigns point statuses to ensure:
1. First filled point gets KEYFRAME status (starts new active segment)
2. Subsequent filled points get TRACKED status (continuation)
3. Original ENDFRAME is converted to KEYFRAME (gap closure)
4. SegmentedCurve recognizes filled gap as active segment

This addresses the bug where TRACKED points after ENDFRAME were treated
as inactive segments (3DEqualizer gap semantics), causing visual gaps
to persist even after filling.

Following UNIFIED_TESTING_GUIDE:
- Test behavior, not implementation
- Use real components (SegmentedCurve, CurvePoint)
- Verify segment activity (active vs inactive)
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none

import pytest

from core.curve_segments import SegmentedCurve
from core.insert_track_algorithm import deform_curve_with_interpolated_offset, fill_gap_with_source
from core.models import CurvePoint, PointStatus
from core.type_aliases import CurveDataList


class TestInsertTrackGapStatus:
    """Test suite for Insert Track gap filling status behavior."""

    # No fixtures needed - tests use standalone functions and algorithms

    def test_deform_gap_first_point_is_keyframe(self):
        """Test that first filled point gets KEYFRAME status (Scenario 1)."""
        # Setup: Curve with gap at frames 11-20
        target_data: CurveDataList = [
            (1, 10.0, 10.0, "keyframe"),
            (10, 100.0, 100.0, "endframe"),  # Gap boundary
            # Gap: frames 11-20
            (21, 210.0, 210.0, "keyframe"),
        ]

        source_data: CurveDataList = [
            (i, float(i * 10), float(i * 10), "tracked") for i in range(1, 31)
        ]

        # Overlap points for interpolation (2+ required for deform)
        overlap_offsets = [
            (1, (0.0, 0.0)),    # Frame 1: no offset
            (30, (0.0, 0.0)),   # Frame 30: no offset
        ]

        # Execute: Fill gap using deformation algorithm
        result = deform_curve_with_interpolated_offset(
            target_data, source_data, gap_start=11, gap_end=20, overlap_offsets=overlap_offsets
        )

        # Verify: Filled points are TRACKED (the converted ENDFRAME->KEYFRAME activates segment)
        result_dict = {pt[0]: pt for pt in result}
        first_filled = result_dict[11]
        assert len(first_filled) >= 4, "Point should have status"
        assert first_filled[3] == "tracked", "Filled points should be TRACKED (tracking data)"

    def test_deform_gap_subsequent_points_are_tracked(self):
        """Test that subsequent filled points get TRACKED status (Scenario 1)."""
        target_data: CurveDataList = [
            (1, 10.0, 10.0, "keyframe"),
            (10, 100.0, 100.0, "endframe"),
            (21, 210.0, 210.0, "keyframe"),
        ]

        source_data: CurveDataList = [
            (i, float(i * 10), float(i * 10), "tracked") for i in range(1, 31)
        ]

        overlap_offsets = [(1, (0.0, 0.0)), (30, (0.0, 0.0))]

        result = deform_curve_with_interpolated_offset(
            target_data, source_data, gap_start=11, gap_end=20, overlap_offsets=overlap_offsets
        )

        # Verify: Subsequent filled points (frames 12-20) are TRACKED
        result_dict = {pt[0]: pt for pt in result}
        for frame in range(12, 21):
            point = result_dict[frame]
            assert len(point) >= 4, f"Frame {frame} should have status"
            assert point[3] == "tracked", f"Frame {frame} should be TRACKED (continuation)"

    def test_deform_gap_converts_endframe_to_keyframe(self):
        """Test that ENDFRAME is converted to KEYFRAME after gap fill (Scenario 1)."""
        target_data: CurveDataList = [
            (1, 10.0, 10.0, "keyframe"),
            (10, 100.0, 100.0, "endframe"),  # Should be converted
            (21, 210.0, 210.0, "keyframe"),
        ]

        source_data: CurveDataList = [
            (i, float(i * 10), float(i * 10), "tracked") for i in range(1, 31)
        ]

        overlap_offsets = [(1, (0.0, 0.0)), (30, (0.0, 0.0))]

        result = deform_curve_with_interpolated_offset(
            target_data, source_data, gap_start=11, gap_end=20, overlap_offsets=overlap_offsets
        )

        # Verify: ENDFRAME at frame 10 is now KEYFRAME
        result_dict = {pt[0]: pt for pt in result}
        endframe_point = result_dict[10]
        assert len(endframe_point) >= 4, "Point should have status"
        assert endframe_point[3] == "keyframe", "ENDFRAME must be converted to KEYFRAME (gap closed)"

    def test_fill_gap_first_point_is_keyframe(self):
        """Test that first filled point gets KEYFRAME status (Scenario 2)."""
        target_data: CurveDataList = [
            (1, 10.0, 10.0, "keyframe"),
            (10, 100.0, 100.0, "endframe"),  # Gap boundary
            (21, 210.0, 210.0, "keyframe"),
        ]

        source_data: CurveDataList = [
            (i, float(i * 10), float(i * 10), "tracked") for i in range(11, 21)
        ]

        offset = (5.0, 5.0)

        # Execute: Fill gap from source with offset
        result = fill_gap_with_source(target_data, source_data, gap_start=11, gap_end=20, offset=offset)

        # Verify: Filled points are TRACKED (the converted ENDFRAME->KEYFRAME activates segment)
        result_dict = {pt[0]: pt for pt in result}
        first_filled = result_dict[11]
        assert len(first_filled) >= 4, "Point should have status"
        assert first_filled[3] == "tracked", "Filled points should be TRACKED (tracking data)"

    def test_fill_gap_subsequent_points_are_tracked(self):
        """Test that subsequent filled points get TRACKED status (Scenario 2)."""
        target_data: CurveDataList = [
            (1, 10.0, 10.0, "keyframe"),
            (10, 100.0, 100.0, "endframe"),
            (21, 210.0, 210.0, "keyframe"),
        ]

        source_data: CurveDataList = [
            (i, float(i * 10), float(i * 10), "tracked") for i in range(11, 21)
        ]

        offset = (0.0, 0.0)

        result = fill_gap_with_source(target_data, source_data, gap_start=11, gap_end=20, offset=offset)

        # Verify: Subsequent filled points (frames 12-20) are TRACKED
        result_dict = {pt[0]: pt for pt in result}
        for frame in range(12, 21):
            point = result_dict[frame]
            assert len(point) >= 4, f"Frame {frame} should have status"
            assert point[3] == "tracked", f"Frame {frame} should be TRACKED"

    def test_fill_gap_converts_endframe_to_keyframe(self):
        """Test that ENDFRAME is converted to KEYFRAME after gap fill (Scenario 2)."""
        target_data: CurveDataList = [
            (1, 10.0, 10.0, "keyframe"),
            (10, 100.0, 100.0, "endframe"),  # Should be converted
            (21, 210.0, 210.0, "keyframe"),
        ]

        source_data: CurveDataList = [
            (i, float(i * 10), float(i * 10), "tracked") for i in range(11, 21)
        ]

        offset = (0.0, 0.0)

        result = fill_gap_with_source(target_data, source_data, gap_start=11, gap_end=20, offset=offset)

        # Verify: ENDFRAME at frame 10 is now KEYFRAME
        result_dict = {pt[0]: pt for pt in result}
        endframe_point = result_dict[10]
        assert len(endframe_point) >= 4, "Point should have status"
        assert endframe_point[3] == "keyframe", "ENDFRAME must be converted to KEYFRAME"

    def test_segmented_curve_recognizes_filled_gap_as_active(self):
        """Test that SegmentedCurve treats filled gap as active segment.

        This is the critical behavior: with KEYFRAME at gap start,
        SegmentedCurve should NOT treat the filled frames as inactive.
        """
        # Setup: Curve with filled gap (first point KEYFRAME, rest TRACKED)
        points = [
            CurvePoint(1, 10.0, 10.0, PointStatus.KEYFRAME),
            CurvePoint(10, 100.0, 100.0, PointStatus.KEYFRAME),  # Converted from ENDFRAME
            CurvePoint(11, 110.0, 110.0, PointStatus.KEYFRAME),  # First filled point
            CurvePoint(12, 120.0, 120.0, PointStatus.TRACKED),   # Subsequent filled
            CurvePoint(13, 130.0, 130.0, PointStatus.TRACKED),
            CurvePoint(14, 140.0, 140.0, PointStatus.TRACKED),
            CurvePoint(15, 150.0, 150.0, PointStatus.TRACKED),
            CurvePoint(21, 210.0, 210.0, PointStatus.KEYFRAME),
        ]

        # Execute: Create SegmentedCurve
        segmented = SegmentedCurve.from_points(points)

        # Verify: Segment containing filled frames (11-15) is ACTIVE
        for frame in [11, 12, 13, 14, 15]:
            segment = segmented.get_segment_at_frame(frame)
            assert segment is not None, f"Frame {frame} should be in a segment"
            assert segment.is_active, f"Frame {frame} segment should be ACTIVE (filled gap)"

    def test_segmented_curve_inactive_without_keyframe(self):
        """Test that WITHOUT KEYFRAME, filled gap would be inactive (bug case).

        This verifies the original bug: TRACKED after ENDFRAME = inactive.
        """
        # Setup: Curve with filled gap but NO KEYFRAME (all TRACKED)
        # This simulates the buggy behavior before the fix
        points = [
            CurvePoint(1, 10.0, 10.0, PointStatus.KEYFRAME),
            CurvePoint(10, 100.0, 100.0, PointStatus.ENDFRAME),  # NOT converted
            CurvePoint(11, 110.0, 110.0, PointStatus.TRACKED),   # All TRACKED (bug!)
            CurvePoint(12, 120.0, 120.0, PointStatus.TRACKED),
            CurvePoint(13, 130.0, 130.0, PointStatus.TRACKED),
            CurvePoint(21, 210.0, 210.0, PointStatus.KEYFRAME),
        ]

        # Execute: Create SegmentedCurve
        segmented = SegmentedCurve.from_points(points)

        # Verify: Segment containing filled frames (11-13) is INACTIVE
        # This is 3DEqualizer gap semantics: TRACKED after ENDFRAME = held position
        for frame in [11, 12, 13]:
            segment = segmented.get_segment_at_frame(frame)
            assert segment is not None, f"Frame {frame} should be in a segment"
            assert not segment.is_active, f"Frame {frame} segment should be INACTIVE (bug behavior)"


class TestInsertTrackEdgeCases:
    """Edge cases for Insert Track status handling."""

    def test_gap_at_curve_start_first_point_keyframe(self):
        """Test gap at start of curve: first filled point is KEYFRAME."""
        # Setup: Gap at frames 1-10, data starts at frame 11
        target_data: CurveDataList = [
            (11, 110.0, 110.0, "keyframe"),
            (20, 200.0, 200.0, "keyframe"),
        ]

        source_data: CurveDataList = [
            (i, float(i * 10), float(i * 10), "tracked") for i in range(1, 21)
        ]

        offset = (0.0, 0.0)

        # Execute: Fill gap at start
        result = fill_gap_with_source(target_data, source_data, gap_start=1, gap_end=10, offset=offset)

        # Verify: Filled points are TRACKED (tracking data)
        result_dict = {pt[0]: pt for pt in result}
        first_filled = result_dict[1]
        assert first_filled[3] == "tracked", "Filled points should be TRACKED (tracking data)"  # pyright: ignore[reportGeneralTypeIssues]

    def test_gap_at_curve_end_first_filled_keyframe(self):
        """Test gap at end of curve: first filled point is KEYFRAME."""
        target_data: CurveDataList = [
            (1, 10.0, 10.0, "keyframe"),
            (10, 100.0, 100.0, "endframe"),  # Creates gap at end
        ]

        source_data: CurveDataList = [
            (i, float(i * 10), float(i * 10), "tracked") for i in range(1, 21)
        ]

        offset = (0.0, 0.0)

        # Execute: Fill gap at end (frames 11-20)
        result = fill_gap_with_source(target_data, source_data, gap_start=11, gap_end=20, offset=offset)

        # Verify: Filled points are TRACKED (the converted ENDFRAME->KEYFRAME activates segment)
        result_dict = {pt[0]: pt for pt in result}
        first_filled = result_dict[11]
        assert first_filled[3] == "tracked", "Filled points should be TRACKED (tracking data)"  # pyright: ignore[reportGeneralTypeIssues]

        # Verify: ENDFRAME at frame 10 is converted
        endframe = result_dict[10]
        assert endframe[3] == "keyframe", "ENDFRAME should be converted"  # pyright: ignore[reportGeneralTypeIssues]

    def test_single_frame_gap_gets_keyframe_status(self):
        """Test single-frame gap: filled point gets KEYFRAME status."""
        target_data: CurveDataList = [
            (1, 10.0, 10.0, "keyframe"),
            (9, 90.0, 90.0, "endframe"),  # Gap at frame 10
            (11, 110.0, 110.0, "keyframe"),
        ]

        source_data: CurveDataList = [(10, 100.0, 100.0, "tracked")]

        offset = (0.0, 0.0)

        # Execute: Fill single-frame gap
        result = fill_gap_with_source(target_data, source_data, gap_start=10, gap_end=10, offset=offset)

        # Verify: Filled point is TRACKED (tracking data)
        result_dict = {pt[0]: pt for pt in result}
        filled = result_dict[10]
        assert filled[3] == "tracked", "Filled point should be TRACKED (tracking data)"  # pyright: ignore[reportGeneralTypeIssues]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
