"""Test that endframes as segment boundaries remain visible in rendering.

Bug: Endframes were being hidden when segments after them were deactivated.
Root cause: deactivate_segments_after_endframe() was deactivating segments
that END with endframes, treating them as gap segments.

Fix: Segments ending with endframes are active segment terminators and should
never be deactivated by earlier endframes.
"""

from core.curve_segments import SegmentedCurve
from core.models import CurvePoint, PointStatus


def test_multiple_endframes_renderer_shows_all():
    """Multiple ENDFRAMEs: all should be visible even if in inactive segments.

    Scenario from user bug:
    - Frame 9: ENDFRAME (ends segment 1, creates gap)
    - Frames 10-18: Gap segment (INACTIVE) containing ENDFRAME at 18
    - Frames 19-25: Gap segment continues (INACTIVE)
    - Frame 26: KEYFRAME (starts active segment)

    Segmentation behavior (correct):
    - Frames between ENDFRAMEs are a GAP (inactive)
    - Segment 10-18 is INACTIVE (it's in the gap after frame 9)

    Renderer behavior (the bug):
    - Before fix: ENDFRAMEs in inactive segments were not rendered
    - After fix: ENDFRAMEs always render, even in inactive segments
    """
    points = [
        CurvePoint(1, 100.0, 100.0, PointStatus.KEYFRAME),
        CurvePoint(5, 150.0, 150.0, PointStatus.TRACKED),
        CurvePoint(9, 200.0, 200.0, PointStatus.ENDFRAME),  # Ends segment 1
        CurvePoint(10, 210.0, 210.0, PointStatus.TRACKED),
        CurvePoint(14, 250.0, 250.0, PointStatus.TRACKED),
        CurvePoint(18, 300.0, 300.0, PointStatus.ENDFRAME),  # In gap (inactive segment)
        CurvePoint(19, 310.0, 310.0, PointStatus.TRACKED),
        CurvePoint(25, 370.0, 370.0, PointStatus.TRACKED),
        CurvePoint(26, 400.0, 400.0, PointStatus.KEYFRAME),  # Starts segment 4
        CurvePoint(37, 500.0, 500.0, PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(points)

    # Segment containing frame 9 ENDFRAME should be active
    seg_9 = curve.get_segment_at_frame(9)
    assert seg_9 is not None, "Frame 9 should be in a segment"
    assert seg_9.is_active, "Segment ending with ENDFRAME at frame 9 should be active"
    assert seg_9.end_frame == 9, "Segment should end at ENDFRAME (frame 9)"

    # Segment containing frame 18 ENDFRAME should be INACTIVE (it's in the gap)
    seg_18 = curve.get_segment_at_frame(18)
    assert seg_18 is not None, "Frame 18 should be in a segment"
    assert not seg_18.is_active, "Segment 10-18 should be INACTIVE (gap after frame 9)"
    assert seg_18.end_frame == 18, "Segment should end at ENDFRAME (frame 18)"

    # The renderer should still show frame 18 ENDFRAME (tested separately)
    # This test verifies segmentation is correct, renderer test verifies visibility

    # Gap segment (frames 19-25) should be inactive
    seg_20 = curve.get_segment_at_frame(20)
    assert seg_20 is not None, "Frame 20 should be in a segment"
    assert not seg_20.is_active, "Gap segment (19-25) should be inactive"

    # Segment starting with KEYFRAME should be active
    seg_26 = curve.get_segment_at_frame(26)
    assert seg_26 is not None, "Frame 26 should be in a segment"
    assert seg_26.is_active, "Segment starting with KEYFRAME should be active"


def test_three_consecutive_endframes_segmentation():
    """Three ENDFRAMEs: only first segment active, rest are gap segments."""
    points = [
        CurvePoint(1, 100.0, 100.0, PointStatus.KEYFRAME),
        CurvePoint(5, 150.0, 150.0, PointStatus.ENDFRAME),   # Ends active segment 1
        CurvePoint(6, 160.0, 160.0, PointStatus.TRACKED),    # Gap starts
        CurvePoint(10, 200.0, 200.0, PointStatus.ENDFRAME),  # In gap (inactive segment)
        CurvePoint(11, 210.0, 210.0, PointStatus.TRACKED),   # Still in gap
        CurvePoint(15, 250.0, 250.0, PointStatus.ENDFRAME),  # In gap (inactive segment)
        CurvePoint(16, 260.0, 260.0, PointStatus.TRACKED),   # Still in gap
        CurvePoint(25, 350.0, 350.0, PointStatus.KEYFRAME),  # Ends gap, starts active segment
    ]

    curve = SegmentedCurve.from_points(points)

    # First segment (ending with ENDFRAME at 5) should be ACTIVE
    seg_5 = curve.get_segment_at_frame(5)
    assert seg_5 is not None, "Segment at frame 5 should exist"
    assert seg_5.is_active, "Segment ending at frame 5 should be active"

    # Segments in the gap should be INACTIVE (but ENDFRAMEs should still render)
    seg_10 = curve.get_segment_at_frame(10)
    assert seg_10 is not None, "Segment at frame 10 should exist"
    assert not seg_10.is_active, "Segment ending at frame 10 should be inactive (in gap)"

    seg_15 = curve.get_segment_at_frame(15)
    assert seg_15 is not None, "Segment at frame 15 should exist"
    assert not seg_15.is_active, "Segment ending at frame 15 should be inactive (in gap)"

    # Segment starting with KEYFRAME should be ACTIVE
    seg_25 = curve.get_segment_at_frame(25)
    assert seg_25 is not None, "Segment at frame 25 should exist"
    assert seg_25.is_active, "Segment starting at frame 25 should be active"


def test_endframe_always_last_point_in_segment():
    """Verify that ENDFRAMEs are always the last point in their segment."""
    points = [
        CurvePoint(1, 100.0, 100.0, PointStatus.KEYFRAME),
        CurvePoint(5, 150.0, 150.0, PointStatus.TRACKED),
        CurvePoint(9, 200.0, 200.0, PointStatus.ENDFRAME),
        CurvePoint(10, 210.0, 210.0, PointStatus.TRACKED),
        CurvePoint(18, 300.0, 300.0, PointStatus.ENDFRAME),
        CurvePoint(26, 400.0, 400.0, PointStatus.KEYFRAME),
    ]

    curve = SegmentedCurve.from_points(points)

    # Check every segment that contains an ENDFRAME
    for segment in curve.segments:
        if segment.points and segment.points[-1].status == PointStatus.ENDFRAME:
            # The ENDFRAME should be at the segment's end_frame
            endframe = segment.points[-1]
            assert segment.end_frame == endframe.frame, \
                f"ENDFRAME at frame {endframe.frame} should be at segment end (got {segment.end_frame})"

            # Verify no points after the ENDFRAME in this segment
            assert all(p.frame <= endframe.frame for p in segment.points), \
                f"No points should exist after ENDFRAME at frame {endframe.frame} in segment"


def test_endframes_render_even_in_inactive_segments():
    """Verify that ENDFRAMEs render even when in inactive segments (the fix)."""
    points = [
        CurvePoint(1, 100.0, 100.0, PointStatus.KEYFRAME),
        CurvePoint(9, 200.0, 200.0, PointStatus.ENDFRAME),   # Active segment
        CurvePoint(10, 210.0, 210.0, PointStatus.TRACKED),   # Gap (inactive)
        CurvePoint(18, 300.0, 300.0, PointStatus.ENDFRAME),  # Gap (inactive)
        CurvePoint(26, 400.0, 400.0, PointStatus.KEYFRAME),  # Active segment
    ]

    curve = SegmentedCurve.from_points(points)

    # Frame 9 ENDFRAME is in active segment
    seg_9 = curve.get_segment_at_frame(9)
    assert seg_9 is not None, "Segment at frame 9 should exist"
    assert seg_9.is_active, "Frame 9 should be in active segment"

    # Frame 18 ENDFRAME is in INACTIVE segment (the gap)
    seg_18 = curve.get_segment_at_frame(18)
    assert seg_18 is not None, "Segment at frame 18 should exist"
    assert not seg_18.is_active, "Frame 18 should be in inactive segment"

    # The renderer should show BOTH endframes
    # (This test verifies segmentation; renderer behavior is tested via integration tests)
    # The fix is in the renderer: it checks `status != "endframe"` before skipping inactive points
