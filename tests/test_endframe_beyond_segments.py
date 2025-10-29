"""Test endframe behavior for frames beyond all segments."""

from core.curve_segments import SegmentedCurve
from core.models import CurvePoint, PointStatus


def test_endframe_makes_all_subsequent_frames_inactive_beyond_data():
    """After an endframe, all frames should be inactive if no keyframes follow.

    Test case:
    - Frame 10: KEYFRAME
    - Frame 20: ENDFRAME
    - Frame 30: TRACKED (from Insert Track)
    - Frame 40+: Should return held position from frame 20 (the ENDFRAME)

    Currently FAILS: Returns None instead of held position.
    """
    points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(points)

    # Frames beyond the last point should return held position from ENDFRAME
    # because there are no KEYFRAMES after the ENDFRAME
    position_40 = curve.get_position_at_frame(40)
    position_50 = curve.get_position_at_frame(50)
    position_100 = curve.get_position_at_frame(100)

    # Should all return the held position from frame 20 (ENDFRAME)
    assert position_40 == (200.0, 200.0), f"Expected held position (200, 200), got {position_40}"
    assert position_50 == (200.0, 200.0), f"Expected held position (200, 200), got {position_50}"
    assert position_100 == (200.0, 200.0), f"Expected held position (200, 200), got {position_100}"


def test_no_endframe_beyond_segments_returns_held_position():
    """If there's no endframe, frames beyond data should return held position from last point.

    This enables 3DEqualizer-style flexibility where the E key can work on any frame
    in the image sequence range, not just frames with existing points.
    """
    points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(points)

    # Without an endframe, frames beyond should return held position from last point
    assert curve.get_position_at_frame(30) == (200.0, 200.0)
    assert curve.get_position_at_frame(100) == (200.0, 200.0)


def test_keyframe_after_endframe_reactivates():
    """A keyframe after an endframe should start a new active segment.

    Test case:
    - Frame 10: KEYFRAME
    - Frame 20: ENDFRAME (gap starts)
    - Frame 30: KEYFRAME (starts new active segment, gap ends)
    - Frame 40: TRACKED
    - Frame 50+: Should return held position from frame 40 (last point in active segment)
    """
    points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=40, x=400.0, y=400.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(points)

    # Frames beyond should return held position from last point (frame 40)
    assert curve.get_position_at_frame(50) == (400.0, 400.0)
    assert curve.get_position_at_frame(100) == (400.0, 400.0)
