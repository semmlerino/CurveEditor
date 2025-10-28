"""Test endframe dynamic updates when adding/removing endframes."""

import pytest

from core.curve_segments import SegmentedCurve
from core.models import CurvePoint, PointStatus


def test_adding_earlier_endframe_deactivates_later_frames():
    """Adding an endframe should deactivate all frames after it.

    Scenario:
    1. Start with frames 10 (KEYFRAME), 20, 30, 40 (all active)
    2. Mark frame 20 as ENDFRAME
    3. All frames after 20 should become inactive and hold position from frame 20
    """
    # Initial points - all active
    points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.TRACKED),
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.TRACKED),
        CurvePoint(frame=40, x=400.0, y=400.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(points)

    # Before endframe: frames 20, 30, 40 should interpolate normally
    assert curve.get_position_at_frame(25) is not None  # Interpolates between 20 and 30
    assert curve.get_position_at_frame(35) is not None  # Interpolates between 30 and 40

    # Now mark frame 20 as ENDFRAME
    updated_points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),  # Changed!
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.TRACKED),
        CurvePoint(frame=40, x=400.0, y=400.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(updated_points)

    # After endframe at 20: frames without points hold, frames with points return actual positions
    assert curve.get_position_at_frame(25) == (200.0, 200.0), "Frame 25 (no point) should hold from ENDFRAME"
    assert curve.get_position_at_frame(30) == (300.0, 300.0), "Frame 30 has TRACKED point, returns actual position"
    assert curve.get_position_at_frame(35) == (200.0, 200.0), "Frame 35 (no point) should hold from ENDFRAME"
    assert curve.get_position_at_frame(40) == (400.0, 400.0), "Frame 40 has TRACKED point, returns actual position"


def test_deleting_later_endframe_extends_earlier_gap():
    """Deleting a later endframe should extend the gap from an earlier endframe.

    Scenario:
    1. Start with frame 10 (KEYFRAME), 20 (ENDFRAME), 30 (TRACKED), 40 (ENDFRAME)
    2. Delete the endframe at 40 (change to TRACKED)
    3. All frames after 20 should remain inactive and hold position from frame 20
    """
    # Initial: two endframes
    points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.TRACKED),
        CurvePoint(frame=40, x=400.0, y=400.0, status=PointStatus.ENDFRAME),
    ]

    curve = SegmentedCurve.from_points(points)

    # Gap from 20: frames without points hold, frames with points return actual positions
    assert curve.get_position_at_frame(25) == (200.0, 200.0), "Frame 25 (no point) holds"
    assert curve.get_position_at_frame(30) == (300.0, 300.0), "Frame 30 has TRACKED point"
    assert curve.get_position_at_frame(35) == (200.0, 200.0), "Frame 35 (no point) holds"

    # Delete the endframe at 40 (change to TRACKED)
    updated_points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.TRACKED),
        CurvePoint(frame=40, x=400.0, y=400.0, status=PointStatus.TRACKED),  # Changed from ENDFRAME!
    ]

    curve = SegmentedCurve.from_points(updated_points)

    # Gap extends: frames without points hold, frames with points return actual positions
    assert curve.get_position_at_frame(25) == (200.0, 200.0), "Frame 25 (no point) holds"
    assert curve.get_position_at_frame(30) == (300.0, 300.0), "Frame 30 has TRACKED point"
    assert curve.get_position_at_frame(35) == (200.0, 200.0), "Frame 35 (no point) holds"
    assert curve.get_position_at_frame(40) == (400.0, 400.0), "Frame 40 has TRACKED point"
    assert curve.get_position_at_frame(50) == (200.0, 200.0), "Frame 50 (no point) holds"


def test_adding_endframe_before_existing_endframe():
    """Adding an earlier endframe should create a new gap boundary.

    Scenario:
    1. Start with frame 10 (KEYFRAME), 20, 30, 40 (ENDFRAME)
    2. Add ENDFRAME at frame 15
    3. Frames 16-39 should hold position from frame 15
    4. Frame 40 is still an ENDFRAME

    Initial state (before change):
    - Frame 10: KEYFRAME
    - Frame 15: TRACKED
    - Frame 20: TRACKED
    - Frame 40: ENDFRAME
    """
    # Change frame 15 to ENDFRAME
    updated_points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=15, x=150.0, y=150.0, status=PointStatus.ENDFRAME),  # Changed!
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.TRACKED),
        CurvePoint(frame=40, x=400.0, y=400.0, status=PointStatus.ENDFRAME),
    ]

    curve = SegmentedCurve.from_points(updated_points)

    # After frame 15: frames without points hold, frames with points return actual positions
    assert curve.get_position_at_frame(17) == (150.0, 150.0), "Frame 17 (no point) holds from ENDFRAME at 15"
    assert curve.get_position_at_frame(20) == (200.0, 200.0), "Frame 20 has TRACKED point"
    assert curve.get_position_at_frame(35) == (150.0, 150.0), "Frame 35 (no point) holds from ENDFRAME at 15"
    assert curve.get_position_at_frame(40) == (400.0, 400.0), "Frame 40 has ENDFRAME point"


def test_removing_all_endframes_reactivates_curve():
    """Removing all endframes should reactivate the entire curve.

    Scenario:
    1. Start with frame 10 (KEYFRAME), 20 (ENDFRAME), 30 (TRACKED)
    2. Remove ENDFRAME at 20 (change to TRACKED)
    3. All frames should interpolate normally again
    """
    # Initial: with endframe
    initial_points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(initial_points)
    assert curve.get_position_at_frame(25) == (200.0, 200.0), "Should hold during gap"

    # Remove endframe
    updated_points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.TRACKED),  # Changed!
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(updated_points)

    # Frame 25 should now interpolate between 20 and 30
    pos = curve.get_position_at_frame(25)
    assert pos is not None, "Frame 25 should have a position (interpolated)"
    assert pos != (200.0, 200.0), "Frame 25 should interpolate, not hold at 200"
    # Should be halfway between (200, 200) and (300, 300) = (250, 250)
    assert pos == pytest.approx((250.0, 250.0)), "Frame 25 should interpolate to midpoint"
