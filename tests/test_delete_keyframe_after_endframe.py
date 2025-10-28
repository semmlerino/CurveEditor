"""Test that deleting a keyframe after an endframe extends the gap."""

from core.curve_segments import SegmentedCurve
from core.models import CurvePoint, PointStatus


def test_delete_keyframe_after_endframe_extends_gap():
    """Deleting a keyframe after an endframe should extend the gap to all subsequent frames.

    Scenario:
    1. Start: frame 10 (KEYFRAME), 20 (ENDFRAME), 30 (KEYFRAME), 40 (TRACKED)
    2. Frames 21-29 are in gap (hold position from frame 20)
    3. Frames 30-40 are active (KEYFRAME at 30 reactivates)
    4. Delete the point at frame 30 (the KEYFRAME)
    5. Now frames 21-40+ should ALL be in the gap (hold position from frame 20)
    """
    # Initial state with keyframe after endframe
    initial_points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=40, x=400.0, y=400.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(initial_points)

    # Before deletion: frames 21-29 hold, frames 30-40 are active
    assert curve.get_position_at_frame(25) == (200.0, 200.0), "Frame 25 should hold from ENDFRAME"
    assert curve.get_position_at_frame(30) == (300.0, 300.0), "Frame 30 is KEYFRAME"

    # Frame 35 should interpolate between 30 and 40
    pos_35 = curve.get_position_at_frame(35)
    assert pos_35 is not None
    assert pos_35 != (200.0, 200.0), "Frame 35 should interpolate, not hold"

    # Now delete the keyframe at frame 30 (simulate user deletion)
    updated_points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
        # Frame 30 DELETED
        CurvePoint(frame=40, x=400.0, y=400.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(updated_points)

    # After deletion: frames WITHOUT points hold position, frames WITH points return actual positions
    assert curve.get_position_at_frame(25) == (200.0, 200.0), "Frame 25 (no point) should hold from ENDFRAME"
    assert curve.get_position_at_frame(30) == (200.0, 200.0), "Frame 30 (no point) should hold from ENDFRAME"
    assert curve.get_position_at_frame(35) == (200.0, 200.0), "Frame 35 (no point) should hold from ENDFRAME"
    assert curve.get_position_at_frame(40) == (400.0, 400.0), "Frame 40 has TRACKED point, returns actual position"
    assert curve.get_position_at_frame(50) == (200.0, 200.0), "Frame 50 (beyond data, no point) should hold from ENDFRAME"


def test_delete_endframe_reactivates_subsequent_frames():
    """Deleting an endframe should reactivate subsequent frames.

    Scenario:
    1. Start: frame 10 (KEYFRAME), 20 (ENDFRAME), 30 (TRACKED)
    2. Frames 21-30+ hold position from frame 20
    3. Delete the ENDFRAME at frame 20
    4. All frames should now be active and interpolate
    """
    # Initial state with endframe
    initial_points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(initial_points)

    # Before deletion: frames without points hold, frames with points return actual positions
    assert curve.get_position_at_frame(25) == (200.0, 200.0), "Frame 25 (no point) should hold from ENDFRAME"
    assert curve.get_position_at_frame(30) == (300.0, 300.0), "Frame 30 has TRACKED point, returns actual position"

    # Delete the endframe at frame 20
    updated_points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        # Frame 20 DELETED
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(updated_points)

    # After deletion: frames should interpolate
    pos_20 = curve.get_position_at_frame(20)
    assert pos_20 is not None
    assert pos_20 == (200.0, 200.0), "Frame 20 should interpolate to (200, 200)"

    pos_25 = curve.get_position_at_frame(25)
    assert pos_25 is not None
    assert pos_25 == (250.0, 250.0), "Frame 25 should interpolate to midpoint (250, 250)"
