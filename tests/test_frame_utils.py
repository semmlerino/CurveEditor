"""Tests for frame manipulation utilities."""

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

from core.frame_utils import (
    clamp_frame,
    get_frame_range_from_curve,
    get_frame_range_with_limits,
    is_frame_in_range,
)


class TestClampFrame:
    """Tests for clamp_frame function."""

    def test_frame_within_range(self):
        """Frame within range should be unchanged."""
        assert clamp_frame(5, 1, 10) == 5
        assert clamp_frame(1, 1, 10) == 1
        assert clamp_frame(10, 1, 10) == 10

    def test_frame_below_min(self):
        """Frame below min should be clamped to min."""
        assert clamp_frame(0, 1, 10) == 1
        assert clamp_frame(-5, 1, 10) == 1

    def test_frame_above_max(self):
        """Frame above max should be clamped to max."""
        assert clamp_frame(11, 1, 10) == 10
        assert clamp_frame(100, 1, 10) == 10

    def test_single_frame_range(self):
        """Range with min == max should return that frame."""
        assert clamp_frame(0, 5, 5) == 5
        assert clamp_frame(5, 5, 5) == 5
        assert clamp_frame(10, 5, 5) == 5

    def test_negative_range(self):
        """Negative frame ranges should work correctly."""
        assert clamp_frame(-5, -10, 0) == -5
        assert clamp_frame(-15, -10, 0) == -10
        assert clamp_frame(5, -10, 0) == 0


class TestIsFrameInRange:
    """Tests for is_frame_in_range function."""

    def test_frame_in_range(self):
        """Frame in range should return True."""
        assert is_frame_in_range(5, 1, 10) is True
        assert is_frame_in_range(1, 1, 10) is True
        assert is_frame_in_range(10, 1, 10) is True

    def test_frame_out_of_range(self):
        """Frame out of range should return False."""
        assert is_frame_in_range(0, 1, 10) is False
        assert is_frame_in_range(11, 1, 10) is False

    def test_negative_range(self):
        """Negative frame ranges should work correctly."""
        assert is_frame_in_range(-5, -10, 0) is True
        assert is_frame_in_range(-11, -10, 0) is False
        assert is_frame_in_range(1, -10, 0) is False

    def test_single_frame_range(self):
        """Single frame range should only accept that frame."""
        assert is_frame_in_range(5, 5, 5) is True
        assert is_frame_in_range(4, 5, 5) is False
        assert is_frame_in_range(6, 5, 5) is False


class TestGetFrameRangeFromCurve:
    """Tests for get_frame_range_from_curve function."""

    def test_normal_curve(self):
        """Normal curve should return min/max frames."""
        data = [(1, 10.0, 20.0), (5, 15.0, 25.0), (3, 12.0, 22.0)]
        assert get_frame_range_from_curve(data) == (1, 5)

    def test_empty_curve(self):
        """Empty curve should return None."""
        assert get_frame_range_from_curve([]) is None

    def test_single_point(self):
        """Single point should return same frame for min/max."""
        data = [(42, 10.0, 20.0)]
        assert get_frame_range_from_curve(data) == (42, 42)

    def test_unsorted_frames(self):
        """Unsorted frames should still return correct min/max."""
        data = [(10, 0, 0), (5, 0, 0), (15, 0, 0), (1, 0, 0)]
        assert get_frame_range_from_curve(data) == (1, 15)

    def test_invalid_points_filtered(self):
        """Points with insufficient data should be filtered out."""
        data = [(1, 10.0), (5, 15.0, 25.0), (10, 20.0, 30.0)]  # First point missing y
        assert get_frame_range_from_curve(data) == (5, 10)

    def test_all_invalid_points(self):
        """All invalid points should return None."""
        data = [(1,), (5,)]  # No x, y data
        assert get_frame_range_from_curve(data) is None


class TestGetFrameRangeWithLimits:
    """Tests for get_frame_range_with_limits function."""

    def test_within_limit(self):
        """Range within limit should be unchanged."""
        data = [(1, 0, 0), (50, 0, 0)]
        assert get_frame_range_with_limits(data, max_range=200) == (1, 50)

    def test_exceeds_limit(self):
        """Range exceeding limit should be truncated."""
        data = [(1, 0, 0), (1000, 0, 0)]
        assert get_frame_range_with_limits(data, max_range=200) == (1, 200)

    def test_empty_curve(self):
        """Empty curve should return None."""
        assert get_frame_range_with_limits([]) is None

    def test_exactly_at_limit(self):
        """Range exactly at limit should be unchanged."""
        data = [(1, 0, 0), (200, 0, 0)]
        assert get_frame_range_with_limits(data, max_range=200) == (1, 200)

    def test_custom_max_range(self):
        """Custom max_range should be respected."""
        data = [(1, 0, 0), (150, 0, 0)]
        assert get_frame_range_with_limits(data, max_range=100) == (1, 100)
