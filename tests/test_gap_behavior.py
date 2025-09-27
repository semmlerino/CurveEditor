#!/usr/bin/env python
"""
Tests for gap behavior implementation.

Tests the complete endframe gap behavior including:
- Position holding in gaps
- Data service integration
- Timeline inactive status detection
- Frame navigation through gaps
"""

from core.type_aliases import CurveDataList
from services.data_service import DataService


class TestDataServiceGapBehavior:
    """Test DataService integration with gap behavior."""

    def test_get_position_at_frame_with_gaps(self):
        """Test DataService position lookup with gaps."""
        data_service = DataService()

        # Create curve data with gaps
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "endframe"),  # Creates gap
            (10, 200.0, 200.0, "keyframe"),  # Startframe after gap
        ]

        # Active segment positions
        assert data_service.get_position_at_frame(curve_data, 1) == (100.0, 100.0)
        assert data_service.get_position_at_frame(curve_data, 5) == (150.0, 150.0)

        # Gap positions (should hold endframe position)
        assert data_service.get_position_at_frame(curve_data, 6) == (150.0, 150.0)
        assert data_service.get_position_at_frame(curve_data, 7) == (150.0, 150.0)
        assert data_service.get_position_at_frame(curve_data, 8) == (150.0, 150.0)
        assert data_service.get_position_at_frame(curve_data, 9) == (150.0, 150.0)

        # Next active segment
        assert data_service.get_position_at_frame(curve_data, 10) == (200.0, 200.0)

    def test_get_position_at_frame_interpolation(self):
        """Test DataService interpolation in active segments."""
        data_service = DataService()

        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 200.0, 200.0, "keyframe"),
        ]

        # Test interpolation
        position = data_service.get_position_at_frame(curve_data, 3)  # Halfway
        assert position is not None
        x, y = position
        assert x == 150.0  # 100 + (200-100) * 0.5
        assert y == 150.0

    def test_frame_range_status_with_gaps(self):
        """Test frame range status detection includes proper gap information."""
        data_service = DataService()

        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (3, 120.0, 120.0, "endframe"),  # Creates gap
            (6, 150.0, 150.0, "keyframe"),  # Startframe after gap
        ]

        status_dict = data_service.get_frame_range_point_status(curve_data)

        # Check that we have status for all frames
        assert 1 in status_dict
        assert 3 in status_dict
        assert 6 in status_dict

        # Frame 1: keyframe, not startframe (first frame)
        frame1_status = status_dict[1]
        (
            keyframe_count,
            interpolated_count,
            tracked_count,
            endframe_count,
            normal_count,
            is_startframe,
            is_inactive,
            has_selected,
        ) = frame1_status
        assert keyframe_count == 1
        assert is_startframe is True  # First frame is startframe
        assert is_inactive is False

        # Frame 3: endframe
        frame3_status = status_dict[3]
        (
            keyframe_count,
            interpolated_count,
            tracked_count,
            endframe_count,
            normal_count,
            is_startframe,
            is_inactive,
            has_selected,
        ) = frame3_status
        assert endframe_count == 1
        assert is_startframe is False
        assert is_inactive is False  # Endframe itself is not inactive

        # Frame 6: keyframe, startframe (after gap)
        frame6_status = status_dict[6]
        (
            keyframe_count,
            interpolated_count,
            tracked_count,
            endframe_count,
            normal_count,
            is_startframe,
            is_inactive,
            has_selected,
        ) = frame6_status
        assert keyframe_count == 1
        assert is_startframe is True  # This should be detected as startframe
        assert is_inactive is False

        # Gap frames (4, 5) should be marked as inactive if included
        if 4 in status_dict:
            frame4_status = status_dict[4]
            _, _, _, _, _, is_startframe, is_inactive, _ = frame4_status
            assert is_inactive is True

        if 5 in status_dict:
            frame5_status = status_dict[5]
            _, _, _, _, _, is_startframe, is_inactive, _ = frame5_status
            assert is_inactive is True


class TestGapWorkflow:
    """Test complete gap workflow scenarios."""

    def test_endframe_conversion_creates_gap(self):
        """Test that converting a keyframe to endframe creates proper gap behavior."""
        data_service = DataService()

        # Initial curve without gaps
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "keyframe"),
            (10, 200.0, 200.0, "keyframe"),
        ]

        # All frames should interpolate normally
        assert data_service.get_position_at_frame(curve_data, 3) is not None  # Interpolated
        assert data_service.get_position_at_frame(curve_data, 7) is not None  # Interpolated

        # Convert frame 5 to endframe (simulating E key press)
        curve_data_with_gap: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "endframe"),  # Now creates gap
            (10, 200.0, 200.0, "keyframe"),  # Becomes startframe
        ]

        # After conversion: gap should exist between frames 6-9
        assert data_service.get_position_at_frame(curve_data_with_gap, 6) == (150.0, 150.0)  # Held
        assert data_service.get_position_at_frame(curve_data_with_gap, 7) == (150.0, 150.0)  # Held
        assert data_service.get_position_at_frame(curve_data_with_gap, 8) == (150.0, 150.0)  # Held
        assert data_service.get_position_at_frame(curve_data_with_gap, 9) == (150.0, 150.0)  # Held

        # Frame 10 should now be a startframe
        status_dict = data_service.get_frame_range_point_status(curve_data_with_gap)
        if 10 in status_dict:
            frame10_status = status_dict[10]
            _, _, _, _, _, is_startframe, is_inactive, _ = frame10_status
            assert is_startframe is True  # Should be detected as startframe

    def test_multiple_gaps_workflow(self):
        """Test workflow with multiple gaps in sequence."""
        data_service = DataService()

        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (3, 120.0, 120.0, "endframe"),  # First gap: 4-5
            (6, 150.0, 150.0, "keyframe"),  # End first gap
            (8, 170.0, 170.0, "endframe"),  # Second gap: 9-11
            (12, 200.0, 200.0, "keyframe"),  # End second gap
        ]

        # First gap: frames 4-5 hold position from frame 3
        assert data_service.get_position_at_frame(curve_data, 4) == (120.0, 120.0)
        assert data_service.get_position_at_frame(curve_data, 5) == (120.0, 120.0)

        # Between gaps: normal operation
        assert data_service.get_position_at_frame(curve_data, 6) == (150.0, 150.0)
        assert data_service.get_position_at_frame(curve_data, 7) is not None  # Should interpolate to frame 8

        # Second gap: frames 9-11 hold position from frame 8
        assert data_service.get_position_at_frame(curve_data, 9) == (170.0, 170.0)
        assert data_service.get_position_at_frame(curve_data, 10) == (170.0, 170.0)
        assert data_service.get_position_at_frame(curve_data, 11) == (170.0, 170.0)

        # After gaps
        assert data_service.get_position_at_frame(curve_data, 12) == (200.0, 200.0)

    def test_gap_at_end_of_sequence(self):
        """Test gap behavior when endframe is at the end of sequence."""
        data_service = DataService()

        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "keyframe"),
            (10, 200.0, 200.0, "endframe"),  # Gap extends indefinitely
        ]

        # Positions before endframe work normally
        assert data_service.get_position_at_frame(curve_data, 1) == (100.0, 100.0)
        assert data_service.get_position_at_frame(curve_data, 7) is not None  # Interpolated
        assert data_service.get_position_at_frame(curve_data, 10) == (200.0, 200.0)

        # After endframe: position should be held indefinitely
        assert data_service.get_position_at_frame(curve_data, 11) == (200.0, 200.0)
        assert data_service.get_position_at_frame(curve_data, 15) == (200.0, 200.0)
        assert data_service.get_position_at_frame(curve_data, 100) == (200.0, 200.0)


class TestEdgeCases:
    """Test edge cases for gap behavior."""

    def test_empty_curve_data(self):
        """Test gap behavior with empty curve data."""
        data_service = DataService()

        assert data_service.get_position_at_frame([], 5) is None
        assert data_service.get_frame_range_point_status([]) == {}

    def test_single_point_curves(self):
        """Test gap behavior with single point curves."""
        data_service = DataService()

        # Single keyframe
        curve_data: CurveDataList = [(5, 150.0, 150.0, "keyframe")]
        assert data_service.get_position_at_frame(curve_data, 5) == (150.0, 150.0)
        assert data_service.get_position_at_frame(curve_data, 3) is None  # Before
        assert data_service.get_position_at_frame(curve_data, 7) is None  # After

        # Single endframe
        curve_data_end: CurveDataList = [(5, 150.0, 150.0, "endframe")]
        assert data_service.get_position_at_frame(curve_data_end, 5) == (150.0, 150.0)
        assert data_service.get_position_at_frame(curve_data_end, 7) == (150.0, 150.0)  # Held after

    def test_adjacent_endframes(self):
        """Test behavior with adjacent endframes."""
        data_service = DataService()

        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "endframe"),
            (3, 120.0, 120.0, "endframe"),  # Adjacent endframe
            (5, 150.0, 150.0, "keyframe"),
        ]

        # Should work correctly with adjacent endframes
        assert data_service.get_position_at_frame(curve_data, 1) == (100.0, 100.0)
        assert data_service.get_position_at_frame(curve_data, 2) == (110.0, 110.0)
        assert data_service.get_position_at_frame(curve_data, 3) == (120.0, 120.0)

        # Frame 4 should hold position from the last endframe (frame 3)
        assert data_service.get_position_at_frame(curve_data, 4) == (120.0, 120.0)

        # Frame 5 should be startframe
        assert data_service.get_position_at_frame(curve_data, 5) == (150.0, 150.0)
