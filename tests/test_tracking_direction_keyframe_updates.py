#!/usr/bin/env python
"""
Tests for tracking direction keyframe status updates.

This test suite validates that keyframe statuses are correctly updated
when tracking direction changes, following the behavior patterns from
3DEqualizer as demonstrated in the LogicExamples.
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

from core.models import PointStatus, TrackingDirection
from data.tracking_direction_utils import (
    get_point_status,
    has_valid_position,
    update_keyframe_status_for_backward_tracking,
    update_keyframe_status_for_bidirectional_tracking,
    update_keyframe_status_for_forward_tracking,
    update_keyframe_status_for_tracking_direction,
)


class TestTrackingDirectionUtils:
    """Test utilities for tracking direction updates."""

    def test_has_valid_position(self):
        """Test valid position detection."""
        # Test data with mixed valid and invalid positions
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),  # Valid position
            (2, -1.0, -1.0, "keyframe"),  # Invalid position
            (3, 150.0, 250.0, "endframe"),  # Valid position
        ]

        assert has_valid_position(curve_data, 0) is True  # Valid position
        assert has_valid_position(curve_data, 1) is False  # Invalid position
        assert has_valid_position(curve_data, 2) is True  # Valid position
        assert has_valid_position(curve_data, -1) is False  # Out of bounds
        assert has_valid_position(curve_data, 10) is False  # Out of bounds

    def test_get_point_status(self):
        """Test point status extraction."""
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 110.0, 210.0, "endframe"),
            (3, 120.0, 220.0),  # No status (should default to normal)
        ]

        assert get_point_status(curve_data, 0) == PointStatus.KEYFRAME
        assert get_point_status(curve_data, 1) == PointStatus.ENDFRAME
        assert get_point_status(curve_data, 2) == PointStatus.NORMAL
        assert get_point_status(curve_data, -1) == PointStatus.NORMAL  # Out of bounds


class TestForwardTrackingUpdates:
    """Test forward tracking direction updates."""

    def test_endframe_to_keyframe_with_valid_next(self):
        """Test ENDFRAME → KEYFRAME when next frame has valid data."""
        curve_data = [
            (1, 100.0, 200.0, "endframe"),  # Should become keyframe
            (2, 110.0, 210.0, "normal"),  # Valid next frame
            (3, -1.0, -1.0, "normal"),  # Invalid frame
        ]

        updated_data = update_keyframe_status_for_forward_tracking(curve_data)

        # First point should be converted to keyframe
        assert updated_data[0] == (1, 100.0, 200.0, "keyframe")
        # Other points unchanged
        assert updated_data[1] == curve_data[1]
        assert updated_data[2] == curve_data[2]

    def test_keyframe_to_endframe_without_valid_next(self):
        """Test KEYFRAME → ENDFRAME when next frame has no valid data."""
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),  # Should become endframe
            (2, -1.0, -1.0, "normal"),  # Invalid next frame
            (3, 120.0, 220.0, "keyframe"),  # Should also become endframe (no frame 4)
        ]

        updated_data = update_keyframe_status_for_forward_tracking(curve_data)

        # First point should be converted to endframe
        assert updated_data[0] == (1, 100.0, 200.0, "endframe")
        # Second point unchanged (not a keyframe)
        assert updated_data[1] == curve_data[1]
        # Third point should be converted to endframe (no next frame)
        assert updated_data[2] == (3, 120.0, 220.0, "endframe")

    def test_preserve_non_keyframe_points(self):
        """Test that non-keyframe points are not modified."""
        curve_data = [
            (1, 100.0, 200.0, "normal"),  # Should stay normal
            (2, 110.0, 210.0, "interpolated"),  # Should stay interpolated
            (3, 120.0, 220.0, "tracked"),  # Should stay tracked
        ]

        updated_data = update_keyframe_status_for_forward_tracking(curve_data)

        # All points should remain unchanged
        assert updated_data == curve_data


class TestBackwardTrackingUpdates:
    """Test backward tracking direction updates."""

    def test_endframe_to_keyframe_with_valid_prev(self):
        """Test ENDFRAME → KEYFRAME when previous frame has valid data."""
        curve_data = [
            (1, 100.0, 200.0, "normal"),  # Valid previous frame
            (2, 110.0, 210.0, "endframe"),  # Should become keyframe
            (3, -1.0, -1.0, "normal"),  # Invalid frame
        ]

        updated_data = update_keyframe_status_for_backward_tracking(curve_data)

        # Second point should be converted to keyframe
        assert updated_data[1] == (2, 110.0, 210.0, "keyframe")
        # Other points unchanged
        assert updated_data[0] == curve_data[0]
        assert updated_data[2] == curve_data[2]

    def test_keyframe_to_endframe_without_valid_prev(self):
        """Test KEYFRAME → ENDFRAME when previous frame has no valid data."""
        curve_data = [
            (1, -1.0, -1.0, "normal"),  # Invalid previous frame
            (2, 110.0, 210.0, "keyframe"),  # Should become endframe
            (3, 120.0, 220.0, "normal"),  # Valid but not adjacent
        ]

        updated_data = update_keyframe_status_for_backward_tracking(curve_data)

        # Second point should be converted to endframe
        assert updated_data[1] == (2, 110.0, 210.0, "endframe")
        # Other points unchanged
        assert updated_data[0] == curve_data[0]
        assert updated_data[2] == curve_data[2]


class TestBidirectionalTrackingUpdates:
    """Test bidirectional tracking direction updates."""

    def test_bidirectional_from_forward_no_changes(self):
        """Test bidirectional from forward direction preserves keyframes."""
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 110.0, 210.0, "endframe"),
            (3, 120.0, 220.0, "keyframe"),
        ]

        updated_data = update_keyframe_status_for_bidirectional_tracking(curve_data, TrackingDirection.TRACKING_FW)

        # All points should remain unchanged when transitioning from forward
        assert updated_data == curve_data

    def test_bidirectional_from_backward_applies_forward_rules(self):
        """Test bidirectional from backward applies forward-style rules."""
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),  # Should become endframe (no valid next)
            (2, -1.0, -1.0, "normal"),  # Invalid next frame
            (3, 120.0, 220.0, "endframe"),  # Should become keyframe (has valid next)
            (4, 130.0, 230.0, "normal"),  # Valid next frame
        ]

        updated_data = update_keyframe_status_for_bidirectional_tracking(curve_data, TrackingDirection.TRACKING_BW)

        # First point should become endframe
        assert updated_data[0] == (1, 100.0, 200.0, "endframe")
        # Third point should become keyframe
        assert updated_data[2] == (3, 120.0, 220.0, "keyframe")
        # Other points unchanged
        assert updated_data[1] == curve_data[1]
        assert updated_data[3] == curve_data[3]


class TestMainTrackingDirectionFunction:
    """Test the main tracking direction update function."""

    def test_forward_direction_routing(self):
        """Test that forward direction routes to forward update function."""
        curve_data = [
            (1, 100.0, 200.0, "endframe"),  # Should become keyframe
            (2, 110.0, 210.0, "normal"),  # Valid next frame
        ]

        updated_data = update_keyframe_status_for_tracking_direction(curve_data, TrackingDirection.TRACKING_FW)

        # Should have applied forward direction rules
        assert updated_data[0] == (1, 100.0, 200.0, "keyframe")

    def test_backward_direction_routing(self):
        """Test that backward direction routes to backward update function."""
        curve_data = [
            (1, 100.0, 200.0, "normal"),  # Valid previous frame
            (2, 110.0, 210.0, "endframe"),  # Should become keyframe
        ]

        updated_data = update_keyframe_status_for_tracking_direction(curve_data, TrackingDirection.TRACKING_BW)

        # Should have applied backward direction rules
        assert updated_data[1] == (2, 110.0, 210.0, "keyframe")

    def test_bidirectional_direction_routing(self):
        """Test that bidirectional direction routes to bidirectional function."""
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),  # Should become endframe
            (2, -1.0, -1.0, "normal"),  # Invalid next frame
        ]

        updated_data = update_keyframe_status_for_tracking_direction(
            curve_data, TrackingDirection.TRACKING_FW_BW, TrackingDirection.TRACKING_BW
        )

        # Should have applied bidirectional rules (from backward)
        assert updated_data[0] == (1, 100.0, 200.0, "endframe")

    def test_with_previous_direction_none(self):
        """Test bidirectional update with None previous direction."""
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 110.0, 210.0, "normal"),
        ]

        # Should default to forward as previous direction
        updated_data = update_keyframe_status_for_tracking_direction(curve_data, TrackingDirection.TRACKING_FW_BW, None)

        # Should not apply any changes (transitioning from forward)
        assert updated_data == curve_data


class TestRealWorldScenarios:
    """Test real-world tracking scenarios based on 3DEqualizer examples."""

    def test_forward_tracking_scenario(self):
        """Test scenario from SetTrackingFwd.py example."""
        # Simulate curve with keyframes and endframes
        curve_data = [
            (10, 100.0, 200.0, "keyframe"),  # Start of tracking
            (11, 105.0, 205.0, "tracked"),  # Tracked frame
            (12, 110.0, 210.0, "keyframe"),  # Manual keyframe
            (13, 115.0, 215.0, "tracked"),  # Tracked frame
            (14, 120.0, 220.0, "endframe"),  # End of segment - should become keyframe
            (15, 125.0, 225.0, "tracked"),  # More tracking data
            (16, 130.0, 230.0, "keyframe"),  # End keyframe - should stay keyframe
            (17, -1.0, -1.0, "normal"),  # No tracking data
        ]

        updated_data = update_keyframe_status_for_forward_tracking(curve_data)

        # Frame 14 should become keyframe (has valid next frame)
        assert updated_data[4] == (14, 120.0, 220.0, "keyframe")
        # Frame 16 should become endframe (no valid next frame)
        assert updated_data[6] == (16, 130.0, 230.0, "endframe")

    def test_backward_tracking_scenario(self):
        """Test scenario from SetTrackingBwd.py example."""
        # Simulate curve with tracking data going backward
        curve_data = [
            (10, -1.0, -1.0, "normal"),  # No previous data
            (11, 105.0, 205.0, "keyframe"),  # Should become endframe
            (12, 110.0, 210.0, "tracked"),  # Tracked frame
            (13, 115.0, 215.0, "endframe"),  # Should become keyframe
            (14, 120.0, 220.0, "tracked"),  # Previous tracking data
            (15, 125.0, 225.0, "keyframe"),  # Should stay keyframe
            (16, 130.0, 230.0, "tracked"),  # Previous tracking data
        ]

        updated_data = update_keyframe_status_for_backward_tracking(curve_data)

        # Frame 11 should become endframe (no valid previous frame)
        assert updated_data[1] == (11, 105.0, 205.0, "endframe")
        # Frame 13 should become keyframe (has valid previous frame)
        assert updated_data[3] == (13, 115.0, 215.0, "keyframe")

    def test_complex_bidirectional_scenario(self):
        """Test complex bidirectional tracking scenario."""
        # Simulate transition from backward to bidirectional
        curve_data = [
            (10, 100.0, 200.0, "keyframe"),  # Should become endframe
            (11, -1.0, -1.0, "normal"),  # Gap
            (12, 110.0, 210.0, "endframe"),  # Should become keyframe
            (13, 115.0, 215.0, "tracked"),  # Valid next
            (14, 120.0, 220.0, "keyframe"),  # Should stay keyframe
            (15, 125.0, 225.0, "tracked"),  # Valid next
        ]

        updated_data = update_keyframe_status_for_bidirectional_tracking(curve_data, TrackingDirection.TRACKING_BW)

        # Frame 10 should become endframe (no valid next)
        assert updated_data[0] == (10, 100.0, 200.0, "endframe")
        # Frame 12 should become keyframe (has valid next)
        assert updated_data[2] == (12, 110.0, 210.0, "keyframe")
        # Frame 14 should stay keyframe (has valid next)
        assert updated_data[4] == (14, 120.0, 220.0, "keyframe")
