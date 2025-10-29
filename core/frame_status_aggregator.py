#!/usr/bin/env python
"""
Frame status aggregation engine for multi-curve timeline display.

This module provides type-safe aggregation of FrameStatus objects across multiple
curves, following 3DEqualizer's multi-point timeline behavior:
- Sum all count fields (keyframe_count, interpolated_count, etc.)
- Logical AND for is_inactive (ALL curves must be inactive)
- Logical OR for is_startframe and has_selected (ANY curve matches)

Integration:
    Used by DataService.get_frame_range_point_status() when display_mode is
    DisplayMode.ALL_VISIBLE to compute aggregate status for timeline rendering.

    Phase 1A: Core aggregation (this module)
    Phase 1B: Integration into DataService (services/data_service.py)

See Also:
    - ENHANCEMENT_PLAN_3DE_ALIGNMENT.md (Phase 1A/1B)
    - services/data_service.py: get_frame_range_point_status()
    - ui/components/frame_tab.py: StatusColorResolver

Phase 1A: Core Aggregation Engine (ENHANCEMENT_PLAN_3DE_ALIGNMENT.md lines 114-166)
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from core.models import FrameStatus


@dataclass
class FrameStatusAccumulator:
    """Internal accumulator for FrameStatus aggregation.

    Prevents type errors during aggregation by providing explicit fields
    that match FrameStatus structure. Clients should never use this directly -
    aggregate_frame_statuses() returns immutable FrameStatus.

    Attributes:
        keyframe_count: Sum of keyframe points across all curves
        interpolated_count: Sum of interpolated points across all curves
        tracked_count: Sum of tracked points across all curves
        endframe_count: Sum of endframe points across all curves
        normal_count: Sum of normal points across all curves
        is_startframe: True if ANY curve has a startframe (OR logic)
        is_inactive: True if ALL curves are inactive (AND logic)
        has_selected: True if ANY curve has selected points (OR logic)
    """

    keyframe_count: int = 0
    interpolated_count: int = 0
    tracked_count: int = 0
    endframe_count: int = 0
    normal_count: int = 0
    is_startframe: bool = False
    is_inactive: bool = True  # Initialize to True for AND logic (ALL curves must be inactive)
    has_selected: bool = False


def aggregate_frame_statuses(statuses: Iterable[FrameStatus]) -> FrameStatus:
    """Aggregate multiple FrameStatus objects into a single status.

    Implements aggregation logic for multi-curve timeline display:
    - Count fields: Sum across all curves
    - is_inactive: Logical AND (frame is inactive ONLY if ALL curves are inactive)
    - is_startframe/has_selected: Logical OR (flag if ANY curve matches)

    Args:
        statuses: Iterable of FrameStatus objects to aggregate. Can be empty.

    Returns:
        FrameStatus with aggregated values:
        - All count fields are summed
        - is_inactive uses AND logic (True only if ALL curves inactive)
        - is_startframe uses OR logic (True if ANY curve is startframe)
        - has_selected uses OR logic (True if ANY curve has selection)

    Example:
        >>> s1 = FrameStatus(1, 0, 0, 0, 0, True, False, False)
        >>> s2 = FrameStatus(0, 2, 0, 0, 0, False, False, True)
        >>> result = aggregate_frame_statuses([s1, s2])
        >>> result.keyframe_count
        1
        >>> result.interpolated_count
        2
        >>> result.is_startframe
        True
        >>> result.has_selected
        True
    """
    # Use dataclass accumulator for type safety
    agg = FrameStatusAccumulator()

    for status in statuses:
        # Sum all count fields
        agg.keyframe_count += status.keyframe_count
        agg.interpolated_count += status.interpolated_count
        agg.tracked_count += status.tracked_count
        agg.endframe_count += status.endframe_count
        agg.normal_count += status.normal_count

        # Logical OR for flags (ANY curve has these)
        agg.is_startframe |= status.is_startframe
        agg.has_selected |= status.has_selected

        # Logical AND for is_inactive (ALL curves must be inactive)
        # Why AND? If any curve is active, frame should NOT show dark gray (inactive color)
        # OR logic would incorrectly hide active curves when one is in a gap
        agg.is_inactive &= status.is_inactive

    # Convert dataclass to FrameStatus (immutable NamedTuple)
    return FrameStatus(
        keyframe_count=agg.keyframe_count,
        interpolated_count=agg.interpolated_count,
        tracked_count=agg.tracked_count,
        endframe_count=agg.endframe_count,
        normal_count=agg.normal_count,
        is_startframe=agg.is_startframe,
        is_inactive=agg.is_inactive,
        has_selected=agg.has_selected,
    )
