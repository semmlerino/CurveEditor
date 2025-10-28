#!/usr/bin/env python3
"""Tests for multiple endframes in a curve.

Verifies that when multiple endframes exist in a curve, all ENDFRAME points
are displayed as active on the timeline (not marked as "inactive"), even if
they're in segments that were deactivated by earlier endframes.
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

from core.models import CurvePoint, PointStatus
from services import get_data_service


class TestMultipleEndframes:
    """Test suite for curves with multiple endframes."""

    def test_multiple_endframes_all_display_as_active(self):
        """Test that all ENDFRAME points display as active on the timeline."""
        # Setup: Curve with endframes at frames 9, 14, and 17 (as CurvePoint objects)
        curve_points = [
            CurvePoint(1, 10.0, 10.0, PointStatus.KEYFRAME),
            CurvePoint(5, 50.0, 50.0, PointStatus.TRACKED),
            CurvePoint(9, 90.0, 90.0, PointStatus.ENDFRAME),      # First endframe
            CurvePoint(10, 100.0, 100.0, PointStatus.TRACKED),    # After first endframe
            CurvePoint(14, 140.0, 140.0, PointStatus.ENDFRAME),   # Second endframe
            CurvePoint(15, 150.0, 150.0, PointStatus.TRACKED),    # After second endframe
            CurvePoint(17, 170.0, 170.0, PointStatus.ENDFRAME),   # Third endframe
            CurvePoint(18, 180.0, 180.0, PointStatus.TRACKED),    # After third endframe
            CurvePoint(20, 200.0, 200.0, PointStatus.KEYFRAME),   # Resume active segment
        ]

        # Execute: Get display status from DataService
        data_service = get_data_service()
        frame_status = data_service.get_frame_range_point_status(curve_points)

        # Verify: ALL ENDFRAME points (9, 14, 17) display as ACTIVE (not inactive)
        assert not frame_status[9].is_inactive, "ENDFRAME at 9 MUST display as active"
        assert not frame_status[14].is_inactive, "ENDFRAME at 14 MUST display as active"
        assert not frame_status[17].is_inactive, "ENDFRAME at 17 MUST display as active"

        # Verify: Tracked points AFTER endframes display as INACTIVE (in gap)
        assert frame_status[10].is_inactive, "Frame 10 (after endframe 9) should display as inactive"
        assert frame_status[15].is_inactive, "Frame 15 (after endframe 14) should display as inactive"
        assert frame_status[18].is_inactive, "Frame 18 (after endframe 17) should display as inactive"

        # Verify: Frame 20 (keyframe) displays as ACTIVE
        assert not frame_status[20].is_inactive, "Frame 20 (keyframe) should display as active"

    def test_consecutive_endframes(self):
        """Test consecutive endframes with no points between them."""
        # Setup: Two endframes with no frames between
        curve_points = [
            CurvePoint(1, 10.0, 10.0, PointStatus.KEYFRAME),
            CurvePoint(5, 50.0, 50.0, PointStatus.ENDFRAME),
            CurvePoint(6, 60.0, 60.0, PointStatus.ENDFRAME),  # Consecutive endframe
            CurvePoint(7, 70.0, 70.0, PointStatus.TRACKED),
            CurvePoint(10, 100.0, 100.0, PointStatus.KEYFRAME),
        ]

        # Execute: Get display status
        data_service = get_data_service()
        frame_status = data_service.get_frame_range_point_status(curve_points)

        # Verify: Both endframes display as active
        assert not frame_status[5].is_inactive, "ENDFRAME at 5 MUST display as active"
        assert not frame_status[6].is_inactive, "ENDFRAME at 6 MUST display as active"

        # Verify: Frame 7 (after endframe 6) displays as inactive
        assert frame_status[7].is_inactive, "Frame 7 (after endframe 6) should display as inactive"

    def test_endframe_followed_by_keyframe(self):
        """Test endframe immediately followed by keyframe (gap of zero frames)."""
        # Setup: Endframe immediately followed by keyframe
        curve_points = [
            CurvePoint(1, 10.0, 10.0, PointStatus.KEYFRAME),
            CurvePoint(5, 50.0, 50.0, PointStatus.ENDFRAME),
            CurvePoint(6, 60.0, 60.0, PointStatus.KEYFRAME),  # Immediately after endframe
            CurvePoint(10, 100.0, 100.0, PointStatus.TRACKED),
        ]

        # Execute: Get display status
        data_service = get_data_service()
        frame_status = data_service.get_frame_range_point_status(curve_points)

        # Verify: Endframe displays as active
        assert not frame_status[5].is_inactive, "ENDFRAME at 5 MUST display as active"

        # Verify: Keyframe displays as active (no inactive gap)
        assert not frame_status[6].is_inactive, "Keyframe at 6 should display as active"

    def test_endframe_at_end_of_curve(self):
        """Test endframe at the very end of the curve."""
        # Setup: Curve ending with endframe
        curve_points = [
            CurvePoint(1, 10.0, 10.0, PointStatus.KEYFRAME),
            CurvePoint(5, 50.0, 50.0, PointStatus.TRACKED),
            CurvePoint(10, 100.0, 100.0, PointStatus.ENDFRAME),  # Ends with endframe
        ]

        # Execute: Get display status
        data_service = get_data_service()
        frame_status = data_service.get_frame_range_point_status(curve_points)

        # Verify: Endframe displays as active (last active frame)
        assert not frame_status[10].is_inactive, "ENDFRAME at 10 MUST display as active"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
