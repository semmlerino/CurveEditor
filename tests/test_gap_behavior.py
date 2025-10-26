#!/usr/bin/env python
"""
Tests for gap behavior implementation.

Tests the complete endframe gap behavior including:
- Position holding in gaps
- Data service integration
- Timeline inactive status detection
- Frame navigation through gaps
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

import pytest

from core.type_aliases import CurveDataList
from services.data_service import DataService


class TestDataServiceGapBehavior:
    """Test DataService integration with gap behavior."""

    @pytest.mark.parametrize(
        ("frame", "expected_position"),
        [
            pytest.param(1, (100.0, 100.0), id="active_start"),
            pytest.param(5, (150.0, 150.0), id="endframe"),
            pytest.param(6, (150.0, 150.0), id="gap_frame_6"),
            pytest.param(7, (150.0, 150.0), id="gap_frame_7"),
            pytest.param(8, (150.0, 150.0), id="gap_frame_8"),
            pytest.param(9, (150.0, 150.0), id="gap_frame_9"),
            pytest.param(10, (200.0, 200.0), id="next_active"),
        ],
    )
    def test_get_position_at_frame_with_gaps(self, frame: int, expected_position: tuple[float, float]):
        """Test DataService position lookup with gaps - positions held during gaps."""
        data_service = DataService()

        # Create curve data with gaps
        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "endframe"),  # Creates gap
            (10, 200.0, 200.0, "keyframe"),  # Startframe after gap
        ]

        assert data_service.get_position_at_frame(curve_data, frame) == expected_position

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
            _interpolated_count,
            _tracked_count,
            _endframe_count,
            _normal_count,
            is_startframe,
            is_inactive,
            _has_selected,
        ) = frame1_status
        assert keyframe_count == 1
        assert is_startframe is True  # First frame is startframe
        assert is_inactive is False

        # Frame 3: endframe
        frame3_status = status_dict[3]
        (
            _keyframe_count,
            _interpolated_count,
            _tracked_count,
            endframe_count,
            _normal_count,
            is_startframe,
            is_inactive,
            _has_selected,
        ) = frame3_status
        assert endframe_count == 1
        assert is_startframe is False
        assert is_inactive is False  # Endframe itself is not inactive

        # Frame 6: keyframe, startframe (after gap)
        frame6_status = status_dict[6]
        (
            keyframe_count,
            _interpolated_count,
            _tracked_count,
            _endframe_count,
            _normal_count,
            is_startframe,
            is_inactive,
            _has_selected,
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
            assert frame10_status.is_startframe is True  # Should be detected as startframe

    @pytest.mark.parametrize(
        ("frame", "expected_x", "expected_y", "description"),
        [
            pytest.param(4, 120.0, 120.0, "first_gap_start", id="gap1_frame4"),
            pytest.param(5, 120.0, 120.0, "first_gap_end", id="gap1_frame5"),
            pytest.param(6, 150.0, 150.0, "between_gaps_keyframe", id="keyframe_6"),
            pytest.param(9, 170.0, 170.0, "second_gap_start", id="gap2_frame9"),
            pytest.param(10, 170.0, 170.0, "second_gap_middle", id="gap2_frame10"),
            pytest.param(11, 170.0, 170.0, "second_gap_end", id="gap2_frame11"),
            pytest.param(12, 200.0, 200.0, "after_gaps", id="keyframe_12"),
        ],
    )
    def test_multiple_gaps_workflow(self, frame: int, expected_x: float, expected_y: float, description: str):
        """Test workflow with multiple gaps in sequence."""
        data_service = DataService()

        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (3, 120.0, 120.0, "endframe"),  # First gap: 4-5
            (6, 150.0, 150.0, "keyframe"),  # End first gap
            (8, 170.0, 170.0, "endframe"),  # Second gap: 9-11
            (12, 200.0, 200.0, "keyframe"),  # End second gap
        ]

        position = data_service.get_position_at_frame(curve_data, frame)
        if description == "between_gaps_interpolated":
            # For interpolated position, just verify it's not None
            assert position is not None
        else:
            assert position == (expected_x, expected_y)

    @pytest.mark.parametrize(
        ("frame", "expected_behavior"),
        [
            pytest.param(1, ("exact", (100.0, 100.0)), id="keyframe_1"),
            pytest.param(7, ("interpolated", None), id="interpolated_7"),
            pytest.param(10, ("exact", (200.0, 200.0)), id="endframe_10"),
            pytest.param(11, ("exact", (200.0, 200.0)), id="held_11"),
            pytest.param(15, ("exact", (200.0, 200.0)), id="held_15"),
            pytest.param(100, ("exact", (200.0, 200.0)), id="held_100"),
        ],
    )
    def test_gap_at_end_of_sequence(self, frame: int, expected_behavior: tuple[str, tuple[float, float]]):
        """Test gap behavior when endframe is at the end of sequence."""
        data_service = DataService()

        curve_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "keyframe"),
            (10, 200.0, 200.0, "endframe"),  # Gap extends indefinitely
        ]

        behavior_type, expected_value = expected_behavior
        result = data_service.get_position_at_frame(curve_data, frame)

        if behavior_type == "exact":
            assert result == expected_value
        elif behavior_type == "interpolated":
            assert result is not None  # Should interpolate between frames 5 and 10


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
