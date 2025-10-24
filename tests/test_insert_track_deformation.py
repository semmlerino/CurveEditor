#!/usr/bin/env python
"""
Tests for Insert Track offset deformation (3DEqualizer _deformCurve behavior).

Tests that when 2+ overlap points exist, the offset is linearly interpolated
across the gap rather than using a constant offset.
"""

from __future__ import annotations

import pytest

from core.insert_track_algorithm import deform_curve_with_interpolated_offset
from core.type_aliases import CurveDataList


class TestInsertTrackDeformation:
    """Test suite for offset deformation behavior (2+ overlap points)."""

    def test_deformation_with_2_overlap_points(self):
        """Test deformation with 2 overlap points (before and after gap).

        Scenario:
        - Target: frame 1 at (0,0), frame 10 at (10,10)
        - Source: frame 1 at (0,0), frames 2-9 at (1,1) to (8,8), frame 10 at (10,0)
        - Gap: frames 2-9

        Expected:
        - Frame 1: offset (0,0)
        - Frame 10: offset (0,10)
        - Frame 5: offset should interpolate to (0,5)
        """
        # Target with gap
        target: CurveDataList = [
            (1, 0.0, 0.0, "keyframe"),
            (10, 10.0, 10.0, "keyframe"),
        ]

        # Source with continuous data
        source: CurveDataList = [
            (1, 0.0, 0.0, "tracked"),
            (2, 1.0, 1.0, "tracked"),
            (3, 2.0, 2.0, "tracked"),
            (4, 3.0, 3.0, "tracked"),
            (5, 4.0, 4.0, "tracked"),
            (6, 5.0, 5.0, "tracked"),
            (7, 6.0, 6.0, "tracked"),
            (8, 7.0, 7.0, "tracked"),
            (9, 8.0, 8.0, "tracked"),
            (10, 10.0, 0.0, "tracked"),
        ]

        # Overlap points: frame 1 (offset 0,0) and frame 10 (offset 0,10)
        overlap_offsets: list[tuple[int, tuple[float, float]]] = [
            (1, (0.0, 0.0)),  # Target (0,0) - Source (0,0) = (0,0)
            (10, (0.0, 10.0)),  # Target (10,10) - Source (10,0) = (0,10)
        ]

        gap_start, gap_end = 2, 9

        # Execute deformation
        result = deform_curve_with_interpolated_offset(target, source, gap_start, gap_end, overlap_offsets)

        # Verify result has target points + gap filled
        result_frames = {p[0] for p in result}
        assert 1 in result_frames  # Original target
        assert 10 in result_frames  # Original target
        assert all(f in result_frames for f in range(2, 10))  # Gap filled

        # Find filled points
        result_dict = {p[0]: p for p in result}

        # Frame 2: t=1/9, offset_y = 0 + (1/9) * 10 ≈ 1.11
        frame_2 = result_dict[2]
        expected_y_2 = 1.0 + (1.0 / 9.0) * 10.0  # Source 1.0 + interpolated offset
        assert frame_2[0] == 2
        assert frame_2[1] == pytest.approx(1.0, abs=0.01)  # X unchanged (offset 0)
        assert frame_2[2] == pytest.approx(expected_y_2, abs=0.01)

        # Frame 5: t=4/9, offset_y = 0 + (4/9) * 10 ≈ 4.44
        frame_5 = result_dict[5]
        expected_y_5 = 4.0 + (4.0 / 9.0) * 10.0
        assert frame_5[0] == 5
        assert frame_5[1] == pytest.approx(4.0, abs=0.01)  # X unchanged
        assert frame_5[2] == pytest.approx(expected_y_5, abs=0.01)

        # Frame 9: t=8/9, offset_y = 0 + (8/9) * 10 ≈ 8.89
        frame_9 = result_dict[9]
        expected_y_9 = 8.0 + (8.0 / 9.0) * 10.0
        assert frame_9[0] == 9
        assert frame_9[1] == pytest.approx(8.0, abs=0.01)  # X unchanged
        assert frame_9[2] == pytest.approx(expected_y_9, abs=0.01)

    def test_deformation_with_3_overlap_points(self):
        """Test deformation with 3 overlap points (multiple segments).

        Scenario:
        - Overlap at frames 1, 5, 10 with different offsets
        - Gap covers frames 2-9
        - Should use 2 segments: [1-5) and [5-10)
        """
        target: CurveDataList = [
            (1, 0.0, 0.0, "keyframe"),
            (5, 5.0, 10.0, "keyframe"),
            (10, 10.0, 10.0, "keyframe"),
        ]

        source: CurveDataList = [
            (1, 0.0, 0.0, "tracked"),
            (2, 1.0, 0.0, "tracked"),
            (3, 2.0, 0.0, "tracked"),
            (4, 3.0, 0.0, "tracked"),
            (5, 5.0, 5.0, "tracked"),
            (6, 6.0, 5.0, "tracked"),
            (7, 7.0, 5.0, "tracked"),
            (8, 8.0, 5.0, "tracked"),
            (9, 9.0, 5.0, "tracked"),
            (10, 10.0, 10.0, "tracked"),
        ]

        # Overlap offsets at frames 1, 5, 10
        overlap_offsets: list[tuple[int, tuple[float, float]]] = [
            (1, (0.0, 0.0)),  # No offset
            (5, (0.0, 5.0)),  # Y offset increases
            (10, (0.0, 0.0)),  # Y offset decreases back
        ]

        gap_start, gap_end = 2, 9

        result = deform_curve_with_interpolated_offset(target, source, gap_start, gap_end, overlap_offsets)
        result_dict = {p[0]: p for p in result}

        # Segment 1: frames 2-4 (between overlap 1 and 5)
        # Frame 3: t=2/4, offset_y = 0 + (2/4) * 5 = 2.5
        frame_3 = result_dict[3]
        expected_y_3 = 0.0 + 2.5  # Source 0.0 + interpolated offset
        assert frame_3[2] == pytest.approx(expected_y_3, abs=0.01)

        # Segment 2: frames 6-9 (between overlap 5 and 10)
        # Frame 7: t=2/5, offset_y = 5 + (2/5) * (-5) = 3.0
        frame_7 = result_dict[7]
        expected_y_7 = 5.0 + 3.0  # Source 5.0 + interpolated offset
        assert frame_7[2] == pytest.approx(expected_y_7, abs=0.01)

    def test_deformation_matches_3dequalizer_formula(self):
        """Test that our interpolation formula matches 3DEqualizer exactly.

        From 3DEqualizer InsertTrack.py line 243:
        xoI = (xo0 + ((f - f0) * ((xo1 - xo0) / (f1 - f0))))
        """
        # Simple test case with known values
        target: CurveDataList = [
            (10, 10.0, 10.0, "keyframe"),
            (20, 20.0, 30.0, "keyframe"),
        ]

        source: CurveDataList = [
            (10, 10.0, 10.0, "tracked"),
            (15, 15.0, 15.0, "tracked"),
            (20, 20.0, 20.0, "tracked"),
        ]

        overlap_offsets: list[tuple[int, tuple[float, float]]] = [
            (10, (0.0, 0.0)),  # offset at f0
            (20, (0.0, 10.0)),  # offset at f1
        ]

        gap_start, gap_end = 11, 19

        result = deform_curve_with_interpolated_offset(target, source, gap_start, gap_end, overlap_offsets)
        result_dict = {p[0]: p for p in result}

        # Frame 15: f=15, f0=10, f1=20, xo0=0, xo1=10
        # xoI = 0 + ((15 - 10) * ((10 - 0) / (20 - 10)))
        #     = 0 + (5 * (10 / 10))
        #     = 0 + 5 = 5
        frame_15 = result_dict[15]
        expected_y = 15.0 + 5.0  # Source Y + interpolated offset
        assert frame_15[2] == pytest.approx(expected_y, abs=0.001)

    def test_deformation_only_fills_gap_frames(self):
        """Test that deformation only fills frames within the gap range."""
        target: CurveDataList = [
            (5, 5.0, 5.0, "keyframe"),
            (15, 15.0, 15.0, "keyframe"),
        ]

        source: CurveDataList = [
            (1, 1.0, 1.0, "tracked"),  # Before gap - should not be added
            (5, 5.0, 5.0, "tracked"),
            (10, 10.0, 10.0, "tracked"),
            (15, 15.0, 15.0, "tracked"),
            (20, 20.0, 20.0, "tracked"),  # After gap - should not be added
        ]

        overlap_offsets: list[tuple[int, tuple[float, float]]] = [
            (5, (0.0, 0.0)),
            (15, (0.0, 0.0)),
        ]

        gap_start, gap_end = 6, 14

        result = deform_curve_with_interpolated_offset(target, source, gap_start, gap_end, overlap_offsets)
        result_frames = {p[0] for p in result}

        # Should have original target frames
        assert 5 in result_frames
        assert 15 in result_frames

        # Should have frame 10 (in gap)
        assert 10 in result_frames

        # Should NOT have frames outside gap
        assert 1 not in result_frames
        assert 20 not in result_frames

    def test_deformation_with_missing_source_frames(self):
        """Test deformation when source has gaps within the gap range."""
        target: CurveDataList = [
            (1, 0.0, 0.0, "keyframe"),
            (10, 10.0, 10.0, "keyframe"),
        ]

        # Source missing frames 5-7
        source: CurveDataList = [
            (1, 0.0, 0.0, "tracked"),
            (2, 1.0, 1.0, "tracked"),
            (3, 2.0, 2.0, "tracked"),
            (4, 3.0, 3.0, "tracked"),
            # Missing 5-7
            (8, 7.0, 7.0, "tracked"),
            (9, 8.0, 8.0, "tracked"),
            (10, 10.0, 0.0, "tracked"),
        ]

        overlap_offsets: list[tuple[int, tuple[float, float]]] = [
            (1, (0.0, 0.0)),
            (10, (0.0, 10.0)),
        ]

        gap_start, gap_end = 2, 9

        result = deform_curve_with_interpolated_offset(target, source, gap_start, gap_end, overlap_offsets)
        result_frames = {p[0] for p in result}

        # Should fill frames where source has data
        assert 2 in result_frames
        assert 3 in result_frames
        assert 4 in result_frames
        assert 8 in result_frames
        assert 9 in result_frames

        # Should NOT fill frames where source is missing
        assert 5 not in result_frames
        assert 6 not in result_frames
        assert 7 not in result_frames

    def test_deformation_requires_2_or_more_overlaps(self):
        """Test that deformation raises error when less than 2 overlap points."""
        target: CurveDataList = [(1, 0.0, 0.0, "keyframe"), (10, 10.0, 10.0, "keyframe")]

        source: CurveDataList = [(1, 0.0, 0.0, "tracked"), (5, 5.0, 5.0, "tracked"), (10, 10.0, 10.0, "tracked")]

        # Only 1 overlap point
        overlap_offsets: list[tuple[int, tuple[float, float]]] = [(1, (0.0, 0.0))]

        with pytest.raises(ValueError, match="deform_curve requires 2\\+ overlap points"):
            deform_curve_with_interpolated_offset(target, source, 2, 9, overlap_offsets)

    def test_deformation_with_both_x_and_y_offsets(self):
        """Test deformation when both X and Y offsets vary."""
        target: CurveDataList = [
            (1, 0.0, 0.0, "keyframe"),
            (10, 20.0, 20.0, "keyframe"),
        ]

        source: CurveDataList = [
            (1, 0.0, 0.0, "tracked"),
            (5, 5.0, 5.0, "tracked"),
            (10, 10.0, 10.0, "tracked"),
        ]

        # Both X and Y offsets change
        overlap_offsets: list[tuple[int, tuple[float, float]]] = [
            (1, (0.0, 0.0)),  # No offset
            (10, (10.0, 10.0)),  # Both X and Y offset by 10
        ]

        gap_start, gap_end = 2, 9

        result = deform_curve_with_interpolated_offset(target, source, gap_start, gap_end, overlap_offsets)
        result_dict = {p[0]: p for p in result}

        # Frame 5: halfway through, offset should be (5, 5)
        frame_5 = result_dict[5]
        # t = (5-1)/(10-1) = 4/9
        # offset_x = 0 + (4/9) * 10 ≈ 4.44
        # offset_y = 0 + (4/9) * 10 ≈ 4.44
        expected_x = 5.0 + (4.0 / 9.0) * 10.0
        expected_y = 5.0 + (4.0 / 9.0) * 10.0

        assert frame_5[1] == pytest.approx(expected_x, abs=0.01)
        assert frame_5[2] == pytest.approx(expected_y, abs=0.01)
