#!/usr/bin/env python
"""
Tests for frame status aggregation engine.

Phase 1A: Core Aggregation Engine
Tests verify:
- Single curve aggregation (identity)
- Multiple curve aggregation
- Empty input handling
- is_inactive AND logic (ALL curves must be inactive)
- is_startframe OR logic (ANY curve matches)
- has_selected OR logic (ANY curve matches)
"""

from core.frame_status_aggregator import FrameStatusAccumulator, aggregate_frame_statuses
from core.models import FrameStatus


class TestFrameStatusAccumulator:
    """Tests for FrameStatusAccumulator dataclass."""

    def test_default_initialization(self) -> None:
        """Verify default values match expected aggregation initial state."""
        agg = FrameStatusAccumulator()

        # Count fields default to 0
        assert agg.keyframe_count == 0
        assert agg.interpolated_count == 0
        assert agg.tracked_count == 0
        assert agg.endframe_count == 0
        assert agg.normal_count == 0

        # Boolean flags
        assert agg.is_startframe is False  # OR logic starts with False
        assert agg.is_inactive is True     # AND logic starts with True
        assert agg.has_selected is False   # OR logic starts with False

    def test_custom_initialization(self) -> None:
        """Verify custom values can be set."""
        agg = FrameStatusAccumulator(
            keyframe_count=5,
            interpolated_count=10,
            tracked_count=3,
            endframe_count=1,
            normal_count=2,
            is_startframe=True,
            is_inactive=False,
            has_selected=True,
        )

        assert agg.keyframe_count == 5
        assert agg.interpolated_count == 10
        assert agg.tracked_count == 3
        assert agg.endframe_count == 1
        assert agg.normal_count == 2
        assert agg.is_startframe is True
        assert agg.is_inactive is False
        assert agg.has_selected is True


class TestAggregateFrameStatuses:
    """Tests for aggregate_frame_statuses() function."""

    def test_empty_input(self) -> None:
        """Empty input returns FrameStatus with all zeros and default flags."""
        result = aggregate_frame_statuses([])

        # All counts should be 0
        assert result.keyframe_count == 0
        assert result.interpolated_count == 0
        assert result.tracked_count == 0
        assert result.endframe_count == 0
        assert result.normal_count == 0

        # Default flag values
        assert result.is_startframe is False
        assert result.is_inactive is True  # AND logic with no input = True
        assert result.has_selected is False

    def test_single_curve_identity(self) -> None:
        """Single curve aggregation returns identical status (identity operation)."""
        status = FrameStatus(
            keyframe_count=3,
            interpolated_count=5,
            tracked_count=2,
            endframe_count=1,
            normal_count=4,
            is_startframe=True,
            is_inactive=False,
            has_selected=True,
        )

        result = aggregate_frame_statuses([status])

        # Should match input exactly
        assert result.keyframe_count == 3
        assert result.interpolated_count == 5
        assert result.tracked_count == 2
        assert result.endframe_count == 1
        assert result.normal_count == 4
        assert result.is_startframe is True
        assert result.is_inactive is False
        assert result.has_selected is True

    def test_multiple_curves_sum_counts(self) -> None:
        """Multiple curves sum all count fields."""
        statuses = [
            FrameStatus(
                keyframe_count=2,
                interpolated_count=3,
                tracked_count=1,
                endframe_count=0,
                normal_count=1,
                is_startframe=False,
                is_inactive=False,
                has_selected=False,
            ),
            FrameStatus(
                keyframe_count=1,
                interpolated_count=2,
                tracked_count=4,
                endframe_count=1,
                normal_count=0,
                is_startframe=False,
                is_inactive=False,
                has_selected=False,
            ),
            FrameStatus(
                keyframe_count=0,
                interpolated_count=1,
                tracked_count=0,
                endframe_count=0,
                normal_count=2,
                is_startframe=False,
                is_inactive=False,
                has_selected=False,
            ),
        ]

        result = aggregate_frame_statuses(statuses)

        # Counts should be summed (2+1+0=3, 3+2+1=6, etc.)
        assert result.keyframe_count == 3
        assert result.interpolated_count == 6
        assert result.tracked_count == 5
        assert result.endframe_count == 1
        assert result.normal_count == 3

    def test_is_inactive_and_logic_all_inactive(self) -> None:
        """is_inactive is True ONLY when ALL curves are inactive (AND logic)."""
        statuses = [
            FrameStatus(0, 0, 0, 0, 0, False, True, False),  # inactive
            FrameStatus(0, 0, 0, 0, 0, False, True, False),  # inactive
            FrameStatus(0, 0, 0, 0, 0, False, True, False),  # inactive
        ]

        result = aggregate_frame_statuses(statuses)
        assert result.is_inactive is True

    def test_is_inactive_and_logic_one_active(self) -> None:
        """is_inactive is False when ANY curve is active (AND logic)."""
        statuses = [
            FrameStatus(0, 0, 0, 0, 0, False, True, False),   # inactive
            FrameStatus(0, 0, 0, 0, 0, False, False, False),  # ACTIVE
            FrameStatus(0, 0, 0, 0, 0, False, True, False),   # inactive
        ]

        result = aggregate_frame_statuses(statuses)
        assert result.is_inactive is False  # One active curve makes frame active

    def test_is_inactive_and_logic_all_active(self) -> None:
        """is_inactive is False when ALL curves are active."""
        statuses = [
            FrameStatus(0, 0, 0, 0, 0, False, False, False),  # active
            FrameStatus(0, 0, 0, 0, 0, False, False, False),  # active
            FrameStatus(0, 0, 0, 0, 0, False, False, False),  # active
        ]

        result = aggregate_frame_statuses(statuses)
        assert result.is_inactive is False

    def test_is_startframe_or_logic_none(self) -> None:
        """is_startframe is False when NO curves have startframe (OR logic)."""
        statuses = [
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
        ]

        result = aggregate_frame_statuses(statuses)
        assert result.is_startframe is False

    def test_is_startframe_or_logic_one(self) -> None:
        """is_startframe is True when ANY curve has startframe (OR logic)."""
        statuses = [
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
            FrameStatus(0, 0, 0, 0, 0, True, False, False),   # startframe
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
        ]

        result = aggregate_frame_statuses(statuses)
        assert result.is_startframe is True

    def test_is_startframe_or_logic_multiple(self) -> None:
        """is_startframe is True when MULTIPLE curves have startframe."""
        statuses = [
            FrameStatus(0, 0, 0, 0, 0, True, False, False),   # startframe
            FrameStatus(0, 0, 0, 0, 0, True, False, False),   # startframe
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
        ]

        result = aggregate_frame_statuses(statuses)
        assert result.is_startframe is True

    def test_has_selected_or_logic_none(self) -> None:
        """has_selected is False when NO curves have selection (OR logic)."""
        statuses = [
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
        ]

        result = aggregate_frame_statuses(statuses)
        assert result.has_selected is False

    def test_has_selected_or_logic_one(self) -> None:
        """has_selected is True when ANY curve has selection (OR logic)."""
        statuses = [
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
            FrameStatus(0, 0, 0, 0, 0, False, False, True),   # selected
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
        ]

        result = aggregate_frame_statuses(statuses)
        assert result.has_selected is True

    def test_has_selected_or_logic_multiple(self) -> None:
        """has_selected is True when MULTIPLE curves have selection."""
        statuses = [
            FrameStatus(0, 0, 0, 0, 0, False, False, True),   # selected
            FrameStatus(0, 0, 0, 0, 0, False, False, True),   # selected
            FrameStatus(0, 0, 0, 0, 0, False, False, False),
        ]

        result = aggregate_frame_statuses(statuses)
        assert result.has_selected is True

    def test_comprehensive_aggregation(self) -> None:
        """Test complete aggregation with all fields varying."""
        statuses = [
            # Curve 1: Active, not startframe, keyframes and interpolated
            FrameStatus(
                keyframe_count=2,
                interpolated_count=1,
                tracked_count=0,
                endframe_count=0,
                normal_count=1,
                is_startframe=False,
                is_inactive=False,
                has_selected=True,
            ),
            # Curve 2: Inactive, startframe, tracked points
            FrameStatus(
                keyframe_count=0,
                interpolated_count=0,
                tracked_count=3,
                endframe_count=1,
                normal_count=0,
                is_startframe=True,
                is_inactive=True,
                has_selected=False,
            ),
            # Curve 3: Active, normal points
            FrameStatus(
                keyframe_count=1,
                interpolated_count=2,
                tracked_count=1,
                endframe_count=0,
                normal_count=2,
                is_startframe=False,
                is_inactive=False,
                has_selected=False,
            ),
        ]

        result = aggregate_frame_statuses(statuses)

        # Verify counts summed correctly
        assert result.keyframe_count == 3      # 2 + 0 + 1
        assert result.interpolated_count == 3  # 1 + 0 + 2
        assert result.tracked_count == 4       # 0 + 3 + 1
        assert result.endframe_count == 1      # 0 + 1 + 0
        assert result.normal_count == 3        # 1 + 0 + 2

        # Verify boolean logic
        assert result.is_startframe is True    # OR: Curve 2 has startframe
        assert result.is_inactive is False     # AND: Curves 1 and 3 are active
        assert result.has_selected is True     # OR: Curve 1 has selection

    def test_generator_input(self) -> None:
        """Verify aggregator accepts generator (Iterable interface)."""
        def status_generator():
            yield FrameStatus(1, 0, 0, 0, 0, False, False, False)
            yield FrameStatus(0, 2, 0, 0, 0, False, False, False)

        result = aggregate_frame_statuses(status_generator())

        assert result.keyframe_count == 1
        assert result.interpolated_count == 2

    def test_returns_frame_status_type(self) -> None:
        """Verify return type is FrameStatus (not FrameStatusAccumulator)."""
        statuses = [FrameStatus(1, 0, 0, 0, 0, False, False, False)]
        result = aggregate_frame_statuses(statuses)

        assert isinstance(result, FrameStatus)
        assert not isinstance(result, FrameStatusAccumulator)
