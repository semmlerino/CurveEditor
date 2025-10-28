#!/usr/bin/env python
"""Test that Insert Track doesn't create duplicate frame entries."""

# Per-file type checking relaxations for test code
# pyright: reportArgumentType=none

from core.insert_track_algorithm import deform_curve_with_interpolated_offset, fill_gap_with_source
from core.models import CurvePoint, PointStatus


def test_deform_curve_no_duplicate_frames():
    """Verify deform_curve doesn't create duplicate frame entries.

    Bug scenario (from user log):
    - Gap frames 7-10 exist with NORMAL status
    - Insert Track fills gap with KEYFRAME/TRACKED
    - Bug: Both old NORMAL and new KEYFRAME points exist for same frames
    - Fix: Gap frames removed before adding filled points
    """
    # Target curve with ENDFRAME at 6, gap 7-10, KEYFRAME at 11
    target_data = [
        (1, 100.0, 100.0, "normal"),
        (2, 110.0, 110.0, "normal"),
        (3, 120.0, 120.0, "normal"),
        (4, 130.0, 130.0, "normal"),
        (5, 140.0, 140.0, "normal"),
        (6, 150.0, 150.0, "endframe"),
        (7, 160.0, 160.0, "normal"),     # In gap (NORMAL status)
        (8, 170.0, 170.0, "normal"),     # In gap (NORMAL status)
        (9, 180.0, 180.0, "normal"),     # In gap (NORMAL status)
        (10, 190.0, 190.0, "normal"),    # In gap (NORMAL status)
        (11, 200.0, 200.0, "keyframe"),
        (12, 210.0, 210.0, "normal"),
    ]

    # Source curve with data in gap range
    source_data = [
        (1, 100.0, 200.0, "normal"),
        (2, 110.0, 210.0, "normal"),
        (3, 120.0, 220.0, "normal"),
        (6, 150.0, 250.0, "normal"),
        (7, 160.0, 260.0, "normal"),
        (8, 170.0, 270.0, "normal"),
        (9, 180.0, 280.0, "normal"),
        (10, 190.0, 290.0, "normal"),
        (11, 200.0, 300.0, "normal"),
        (12, 210.0, 310.0, "normal"),
    ]

    # Overlap offsets for deformation
    overlap_offsets = [
        (6, (0.0, -100.0)),   # Before gap
        (11, (0.0, -100.0)),  # After gap
    ]

    # Fill gap
    result = deform_curve_with_interpolated_offset(
        target_data, source_data, gap_start=7, gap_end=10, overlap_offsets=overlap_offsets
    )

    # Convert result to CurvePoint objects
    result_points = [CurvePoint.from_tuple(p) for p in result]

    # Check for duplicates
    frame_counts: dict[int, int] = {}
    for point in result_points:
        frame_counts[point.frame] = frame_counts.get(point.frame, 0) + 1

    # No frame should appear more than once
    duplicates = {frame: count for frame, count in frame_counts.items() if count > 1}
    assert not duplicates, f"Found duplicate frames: {duplicates}"

    # Verify total point count is correct (12 original frames, no duplicates)
    assert len(result_points) == 12, f"Expected 12 points, got {len(result_points)}"

    # Verify gap frames now have correct status (all TRACKED)
    frames_7_to_10 = [p for p in result_points if 7 <= p.frame <= 10]
    assert len(frames_7_to_10) == 4, "Should have 4 filled gap frames"
    assert all(p.status == PointStatus.TRACKED for p in frames_7_to_10), "All filled frames should be TRACKED"

    # Verify frame 6 converted from ENDFRAME to KEYFRAME
    frame_6 = next(p for p in result_points if p.frame == 6)
    assert frame_6.status == PointStatus.KEYFRAME, "Frame 6 should be converted to KEYFRAME"


def test_fill_gap_with_source_no_duplicates():
    """Verify fill_gap_with_source doesn't create duplicate frame entries."""
    # Target curve with gap
    target_data = [
        (1, 100.0, 100.0, "normal"),
        (5, 140.0, 140.0, "endframe"),
        (6, 150.0, 150.0, "normal"),     # In gap
        (7, 160.0, 160.0, "normal"),     # In gap
        (8, 170.0, 170.0, "keyframe"),
    ]

    # Source curve with data in gap range
    source_data = [
        (1, 100.0, 200.0, "normal"),
        (5, 140.0, 240.0, "normal"),
        (6, 150.0, 250.0, "normal"),
        (7, 160.0, 260.0, "normal"),
        (8, 170.0, 270.0, "normal"),
    ]

    # Fill gap
    result = fill_gap_with_source(
        target_data, source_data, gap_start=6, gap_end=7, offset=(0.0, -100.0)
    )

    # Convert result to CurvePoint objects
    result_points = [CurvePoint.from_tuple(p) for p in result]

    # Check for duplicates
    frame_counts: dict[int, int] = {}
    for point in result_points:
        frame_counts[point.frame] = frame_counts.get(point.frame, 0) + 1

    # No frame should appear more than once
    duplicates = {frame: count for frame, count in frame_counts.items() if count > 1}
    assert not duplicates, f"Found duplicate frames: {duplicates}"

    # Verify total point count is correct (5 frames: 1, 5, 6, 7, 8)
    # Frame 5 is converted from ENDFRAME to KEYFRAME, still counts as 1 frame
    assert len(result_points) == 5, f"Expected 5 points, got {len(result_points)}"

    # Verify frame 5 converted from ENDFRAME to KEYFRAME
    frame_5 = next(p for p in result_points if p.frame == 5)
    assert frame_5.status == PointStatus.KEYFRAME, "Frame 5 should be converted to KEYFRAME"
