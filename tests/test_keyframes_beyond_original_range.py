"""Test interpolation between keyframes beyond original curve range.

User scenario: Load curve with 37 frames, image sequence with 62 frames.
Create KEYFRAMEs at frames 44 and 47 (beyond original range).
Frames 45-46 should interpolate between them, not be inactive.

Related issue: When original curve ends with ENDFRAME, consecutive KEYFRAMEs
beyond that range were being split into separate segments, preventing interpolation.
"""

from core.curve_segments import SegmentedCurve
from core.models import CurvePoint, PointStatus


def test_two_keyframes_beyond_original_range_with_endframe():
    """Two KEYFRAMEs beyond an ENDFRAME should form one active segment with interpolation.

    This is the exact user scenario:
    - Original curve: frames 1-37 (last point is ENDFRAME)
    - User presses E at frame 44 → creates KEYFRAME, then converts to ENDFRAME, then back to KEYFRAME
    - User presses E at frame 47 → creates KEYFRAME, then converts to ENDFRAME, then back to KEYFRAME
    - Frames 45-46 should interpolate between 44 and 47

    Before fix: Frames 44 and 47 were in separate segments
    After fix: Frames 44 and 47 are in the same segment, frames 45-46 interpolate
    """
    # Original curve with 37 tracked points, ending with ENDFRAME
    original_points = [
        CurvePoint(frame=i, x=float(i * 10), y=float(i * 10), status=PointStatus.TRACKED)
        for i in range(1, 37)
    ]
    original_points.append(
        CurvePoint(frame=37, x=370.0, y=370.0, status=PointStatus.ENDFRAME)
    )

    # User creates KEYFRAMEs at frames 44 and 47
    keyframe_44 = CurvePoint(frame=44, x=440.0, y=440.0, status=PointStatus.KEYFRAME)
    keyframe_47 = CurvePoint(frame=47, x=470.0, y=470.0, status=PointStatus.KEYFRAME)

    all_points = original_points + [keyframe_44, keyframe_47]
    curve = SegmentedCurve.from_points(all_points)

    # Verify segment structure
    assert len(curve.segments) == 2, f"Expected 2 segments, got {len(curve.segments)}"

    # Segment 0: frames 1-37 (ends with ENDFRAME)
    assert curve.segments[0].start_frame == 1
    assert curve.segments[0].end_frame == 37
    assert curve.segments[0].is_active is True

    # Segment 1: frames 44-47 (both KEYFRAMEs in SAME segment)
    assert curve.segments[1].start_frame == 44
    assert curve.segments[1].end_frame == 47
    assert curve.segments[1].is_active is True
    assert len(curve.segments[1].points) == 2  # Both KEYFRAMEs in same segment

    # Verify positions
    assert curve.get_position_at_frame(44) == (440.0, 440.0)
    assert curve.get_position_at_frame(47) == (470.0, 470.0)

    # THE CRITICAL TEST: Interpolation between KEYFRAMEs
    pos_45 = curve.get_position_at_frame(45)
    pos_46 = curve.get_position_at_frame(46)

    # Linear interpolation: frame_ratio = (45 - 44) / (47 - 44) = 1/3
    # x = 440 + (470 - 440) * (1/3) = 450
    assert pos_45 == (450.0, 450.0), f"Frame 45: expected interpolated (450, 450), got {pos_45}"

    # frame_ratio = (46 - 44) / (47 - 44) = 2/3
    # x = 440 + (470 - 440) * (2/3) = 460
    assert pos_46 == (460.0, 460.0), f"Frame 46: expected interpolated (460, 460), got {pos_46}"

    # Verify frames between ENDFRAME and first KEYFRAME hold ENDFRAME position
    for frame in range(38, 44):
        pos = curve.get_position_at_frame(frame)
        assert pos == (370.0, 370.0), f"Frame {frame}: expected held (370, 370), got {pos}"


def test_two_keyframes_beyond_range_without_endframe():
    """Two KEYFRAMEs beyond original range (no ENDFRAME) should also interpolate.

    Control test: Even without an ENDFRAME, two KEYFRAMEs beyond the original
    range should form one segment with interpolation.
    """
    # Original curve: frames 1-37 (all TRACKED, no ENDFRAME)
    original_points = [
        CurvePoint(frame=i, x=float(i * 10), y=float(i * 10), status=PointStatus.TRACKED)
        for i in range(1, 38)
    ]

    # User creates KEYFRAMEs at frames 44 and 47
    keyframe_44 = CurvePoint(frame=44, x=440.0, y=440.0, status=PointStatus.KEYFRAME)
    keyframe_47 = CurvePoint(frame=47, x=470.0, y=470.0, status=PointStatus.KEYFRAME)

    all_points = original_points + [keyframe_44, keyframe_47]
    curve = SegmentedCurve.from_points(all_points)

    # Verify: all points in ONE segment (no ENDFRAME to split them)
    assert len(curve.segments) == 1
    assert curve.segments[0].start_frame == 1
    assert curve.segments[0].end_frame == 47

    # Verify interpolation works
    pos_45 = curve.get_position_at_frame(45)
    pos_46 = curve.get_position_at_frame(46)

    assert pos_45 == (450.0, 450.0)
    assert pos_46 == (460.0, 460.0)


def test_three_keyframes_beyond_endframe():
    """Multiple KEYFRAMEs beyond ENDFRAME should all be in same segment."""
    original_points = [
        CurvePoint(frame=10, x=100.0, y=100.0, status=PointStatus.KEYFRAME),
        CurvePoint(frame=20, x=200.0, y=200.0, status=PointStatus.ENDFRAME),
    ]

    # Three KEYFRAMEs after the ENDFRAME
    kf_30 = CurvePoint(frame=30, x=300.0, y=300.0, status=PointStatus.KEYFRAME)
    kf_40 = CurvePoint(frame=40, x=400.0, y=400.0, status=PointStatus.KEYFRAME)
    kf_50 = CurvePoint(frame=50, x=500.0, y=500.0, status=PointStatus.KEYFRAME)

    all_points = original_points + [kf_30, kf_40, kf_50]
    curve = SegmentedCurve.from_points(all_points)

    # Verify segment structure
    assert len(curve.segments) == 2

    # Segment 1: all three KEYFRAMEs in same segment
    assert curve.segments[1].start_frame == 30
    assert curve.segments[1].end_frame == 50
    assert len(curve.segments[1].points) == 3

    # Verify interpolation between all KEYFRAMEs
    # Between 30 and 40: frame 35 should interpolate
    pos_35 = curve.get_position_at_frame(35)
    assert pos_35 == (350.0, 350.0)

    # Between 40 and 50: frame 45 should interpolate
    pos_45 = curve.get_position_at_frame(45)
    assert pos_45 == (450.0, 450.0)
