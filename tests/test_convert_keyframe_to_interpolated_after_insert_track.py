"""Test that converting a KEYFRAME to INTERPOLATED after Insert Track maintains gap behavior."""

from core.curve_segments import SegmentedCurve
from core.models import CurvePoint, PointStatus


def test_convert_keyframe_after_insert_track():
    """Converting KEYFRAME to INTERPOLATED after Insert Track should maintain inactive segment.

    Scenario (from user bug report):
    1. Frame 10: ENDFRAME (creates gap)
    2. Frame 11-16: TRACKED (from Insert Track, converted ENDFRAME to KEYFRAME)
    3. Frame 17: KEYFRAME (reactivates curve)
    4. Convert frame 17 to INTERPOLATED
    5. Toggle frame 10 back to ENDFRAME
    6. Result: Frames 11-37 should ALL be inactive (only INTERPOLATED points, no KEYFRAME)
    """
    # Step 5: After converting frame 17 to INTERPOLATED and toggling frame 10 to ENDFRAME
    points = [
        CurvePoint(frame=1, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=10, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
        # Frames 11-16: TRACKED (from Insert Track)
        CurvePoint(frame=11, x=210.0, y=210.0, status=PointStatus.TRACKED),
        CurvePoint(frame=12, x=220.0, y=220.0, status=PointStatus.TRACKED),
        CurvePoint(frame=13, x=230.0, y=230.0, status=PointStatus.TRACKED),
        CurvePoint(frame=14, x=240.0, y=240.0, status=PointStatus.TRACKED),
        CurvePoint(frame=15, x=250.0, y=250.0, status=PointStatus.TRACKED),
        CurvePoint(frame=16, x=260.0, y=260.0, status=PointStatus.TRACKED),
        # Frame 17: INTERPOLATED (converted from KEYFRAME)
        CurvePoint(frame=17, x=270.0, y=270.0, status=PointStatus.INTERPOLATED),
        # More TRACKED points after frame 17 (no KEYFRAME to reactivate)
        CurvePoint(frame=20, x=300.0, y=300.0, status=PointStatus.TRACKED),
        CurvePoint(frame=37, x=400.0, y=400.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(points)

    # Frames with actual points return their actual positions (Insert Track data must be visible!)
    assert curve.get_position_at_frame(11) == (210.0, 210.0), "Frame 11 has TRACKED point"
    assert curve.get_position_at_frame(12) == (220.0, 220.0), "Frame 12 has TRACKED point"
    assert curve.get_position_at_frame(16) == (260.0, 260.0), "Frame 16 has TRACKED point"
    assert curve.get_position_at_frame(17) == (270.0, 270.0), "Frame 17 has INTERPOLATED point"
    assert curve.get_position_at_frame(20) == (300.0, 300.0), "Frame 20 has TRACKED point"
    assert curve.get_position_at_frame(37) == (400.0, 400.0), "Frame 37 has TRACKED point"

    # Frames WITHOUT actual points return held position
    assert curve.get_position_at_frame(50) == (200.0, 200.0), "Frame 50 (beyond) should hold from ENDFRAME"


def test_tracked_and_interpolated_after_endframe_all_inactive():
    """TRACKED/INTERPOLATED points after ENDFRAME are in inactive segment, but return actual positions (data preservation).

    This is critical for Insert Track to work - filled frames must show their actual positions.
    Frames WITHOUT actual points return held positions.
    """
    points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
        CurvePoint(frame=25, x=250.0, y=250.0, status=PointStatus.TRACKED),
        CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.INTERPOLATED),
        CurvePoint(frame=35, x=350.0, y=350.0, status=PointStatus.TRACKED),
    ]

    curve = SegmentedCurve.from_points(points)

    # Frames with actual points return their actual positions (data preservation)
    assert curve.get_position_at_frame(25) == (250.0, 250.0), "Frame 25 (TRACKED) returns actual position"
    assert curve.get_position_at_frame(30) == (300.0, 300.0), "Frame 30 (INTERPOLATED) returns actual position"
    assert curve.get_position_at_frame(35) == (350.0, 350.0), "Frame 35 (TRACKED) returns actual position"

    # Frames WITHOUT actual points return held position
    assert curve.get_position_at_frame(22) == (200.0, 200.0), "Frame 22 (no point) should hold ENDFRAME position"
    assert curve.get_position_at_frame(40) == (200.0, 200.0), "Frame 40 (beyond) should hold ENDFRAME position"
