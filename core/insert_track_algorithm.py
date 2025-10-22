#!/usr/bin/env python
"""
Insert Track Algorithm - Core logic for 3DEqualizer-style gap filling.

This module implements the core algorithms for the Insert Track feature,
which fills gaps in tracking trajectories by:
1. Interpolating gaps (single point scenario)
2. Copying data from source curves with offset correction (multi-point scenario)
3. Creating averaged curves from multiple sources

Based on 3DEqualizer's Insert Track functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.type_aliases import CurveDataList

from core.logger_utils import get_logger
from core.models import CurvePoint, PointStatus

logger = get_logger("insert_track_algorithm")


def find_gap_around_frame(curve_data: CurveDataList, current_frame: int) -> tuple[int, int] | None:
    """Find gap containing current_frame (missing frames OR status-based).

    Detects two types of gaps:
    1. Missing-frame gaps: Continuous sequence of frames with no data
    2. Status-based gaps: Frames between endframe markers (3DEqualizer style)

    Args:
        curve_data: Trajectory data to search
        current_frame: Frame that should be within the gap

    Returns:
        Tuple of (gap_start, gap_end) frame numbers, or None if no gap at current_frame

    Example (missing-frame gap):
        curve_data = [(1, 10, 10), (2, 11, 11), (10, 20, 20), (11, 21, 21)]
        find_gap_around_frame(curve_data, 5) -> (3, 9)  # Gap from frame 3 to 9

    Example (status-based gap):
        curve_data = [(1, 10, 10, "keyframe"), (5, 20, 20, "endframe"),
                      (10, 30, 30, "tracked"), (15, 40, 40, "keyframe")]
        find_gap_around_frame(curve_data, 10) -> (6, 14)  # Gap from ENDFRAME to KEYFRAME
    """
    # Convert to CurvePoint objects
    points = [CurvePoint.from_tuple(p) for p in curve_data]

    if not points:
        return None

    # Sort points by frame
    points.sort(key=lambda p: p.frame)
    frames_with_data = {p.frame for p in points}

    # TYPE 1: Missing-frame gap detection
    if current_frame not in frames_with_data:
        # Find the gap boundaries
        gap_start = None
        gap_end = None

        # Find last frame with data before current_frame
        for point in reversed(points):
            if point.frame < current_frame:
                gap_start = point.frame + 1
                break

        # Find first frame with data after current_frame
        for point in points:
            if point.frame > current_frame:
                gap_end = point.frame - 1
                break

        # Handle edge cases
        if gap_start is None:
            # No data before current_frame - gap starts from first possible frame
            gap_start = 1 if points else current_frame

        if gap_end is None:
            # No data after current_frame - gap extends to infinity (or practical limit)
            # Return None as we can't fill an open-ended gap
            return None

        # Verify current_frame is actually in the gap
        if gap_start <= current_frame <= gap_end:
            return (gap_start, gap_end)

        return None

    # TYPE 2: Status-based gap detection (3DEqualizer endframe markers)
    # Gap = frames after ENDFRAME until next KEYFRAME (STARTFRAME)
    # Find the most recent ENDFRAME before or at current_frame
    prev_endframe = None
    for p in reversed(points):
        if p.frame < current_frame and p.status == PointStatus.ENDFRAME:
            prev_endframe = p
            break

    if prev_endframe:
        # Find the next KEYFRAME after the ENDFRAME (this is the STARTFRAME)
        next_keyframe = None
        for p in points:
            if p.frame > prev_endframe.frame and p.status == PointStatus.KEYFRAME:
                next_keyframe = p
                break

        if next_keyframe:
            # Gap is from frame after ENDFRAME to frame before KEYFRAME
            gap_start = prev_endframe.frame + 1
            gap_end = next_keyframe.frame - 1

            # Check if current_frame is in this gap
            if gap_start <= current_frame <= gap_end:
                logger.debug(
                    f"Status-based gap detected: frames {gap_start}-{gap_end} "
                    + f"(between ENDFRAME at {prev_endframe.frame} and KEYFRAME at {next_keyframe.frame})"
                )
                return (gap_start, gap_end)
        else:
            # ENDFRAME exists but no KEYFRAME after it - open-ended gap
            # Check if current frame is after the ENDFRAME
            if current_frame > prev_endframe.frame:
                # Can't fill open-ended gap
                logger.debug(
                    f"Open-ended gap detected after ENDFRAME at {prev_endframe.frame} "
                    + "(no KEYFRAME found to close gap)"
                )
                return None

    # No gap detected
    return None


def find_overlap_frames(
    target_data: CurveDataList, source_data: CurveDataList, gap_start: int, gap_end: int
) -> tuple[list[int], list[int]]:
    """Find frames where both target and source have data, before and after gap.

    Args:
        target_data: Target trajectory (with gap)
        source_data: Source trajectory (to copy from)
        gap_start: First frame of the gap
        gap_end: Last frame of the gap

    Returns:
        Tuple of (before_overlap_frames, after_overlap_frames)
        Each list contains frame numbers where both curves have data

    Example:
        target: frames [1, 2, 10, 11]  (gap 3-9)
        source: frames [1, 2, 3, 4, 10, 11]
        Result: ([1, 2], [10, 11])  # Overlap before and after gap
    """
    # Convert to CurvePoint objects
    target_points = [CurvePoint.from_tuple(p) for p in target_data]
    source_points = [CurvePoint.from_tuple(p) for p in source_data]

    # Get frames with data for each curve
    target_frames = {p.frame for p in target_points}
    source_frames = {p.frame for p in source_points}

    # Find overlap before gap
    before_overlap = sorted([f for f in target_frames & source_frames if f < gap_start])

    # Find overlap after gap
    after_overlap = sorted([f for f in target_frames & source_frames if f > gap_end])

    return (before_overlap, after_overlap)


def calculate_offset(
    target_data: CurveDataList, source_data: CurveDataList, overlap_frames: list[int]
) -> tuple[float, float]:
    """Calculate average offset between target and source at overlap frames.

    Args:
        target_data: Target trajectory
        source_data: Source trajectory
        overlap_frames: Frames where both have data (used for offset calculation)

    Returns:
        Tuple of (offset_x, offset_y) to apply to source data

    Note:
        Offset = target_position - source_position (averaged over overlap frames)
        This offset makes source data align with target data
    """
    if not overlap_frames:
        logger.warning("No overlap frames provided for offset calculation")
        return (0.0, 0.0)

    # Convert to CurvePoint objects first, then create dict
    target_points_list = [CurvePoint.from_tuple(p) for p in target_data]
    source_points_list = [CurvePoint.from_tuple(p) for p in source_data]

    target_points = {p.frame: p for p in target_points_list}
    source_points = {p.frame: p for p in source_points_list}

    # Calculate offset at each overlap frame
    offsets_x: list[float] = []
    offsets_y: list[float] = []

    for frame in overlap_frames:
        if frame in target_points and frame in source_points:
            target = target_points[frame]
            source = source_points[frame]

            offset_x = target.x - source.x
            offset_y = target.y - source.y

            offsets_x.append(offset_x)
            offsets_y.append(offset_y)

    if not offsets_x:
        logger.warning("No valid offset points found at overlap frames")
        return (0.0, 0.0)

    # Average the offsets
    avg_offset_x = sum(offsets_x) / len(offsets_x)
    avg_offset_y = sum(offsets_y) / len(offsets_y)

    logger.debug(f"Calculated offset: ({avg_offset_x:.2f}, {avg_offset_y:.2f}) from {len(offsets_x)} overlap frames")

    return (avg_offset_x, avg_offset_y)


def fill_gap_with_source(
    target_data: CurveDataList, source_data: CurveDataList, gap_start: int, gap_end: int, offset: tuple[float, float]
) -> CurveDataList:
    """Fill target's gap with source data, applying offset correction.

    Args:
        target_data: Target trajectory (with gap to fill)
        source_data: Source trajectory (to copy from)
        gap_start: First frame of gap
        gap_end: Last frame of gap
        offset: (offset_x, offset_y) to apply to source data

    Returns:
        New curve data with gap filled and boundaries marked as keyframes

    Note:
        - Preserves all existing target data
        - Adds source data (with offset) for gap frames where source has data
        - Marks gap boundaries as keyframes
    """
    # Convert to CurvePoint objects
    target_points = [CurvePoint.from_tuple(p) for p in target_data]
    source_points_list = [CurvePoint.from_tuple(p) for p in source_data]
    source_points = {p.frame: p for p in source_points_list}

    offset_x, offset_y = offset

    # Create result with all existing target points
    result_points = list(target_points)

    # Add source data for gap frames
    gap_frames_filled = 0
    for frame in range(gap_start, gap_end + 1):
        if frame in source_points:
            source_point = source_points[frame]
            # Apply offset
            new_x = source_point.x + offset_x
            new_y = source_point.y + offset_y

            # Create new point with TRACKED status (copied data)
            new_point = CurvePoint(frame=frame, x=new_x, y=new_y, status=PointStatus.TRACKED)
            result_points.append(new_point)
            gap_frames_filled += 1

    logger.info(f"Filled {gap_frames_filled} frames in gap [{gap_start}, {gap_end}]")

    # Mark overlap frames (frames OUTSIDE gap boundaries) as keyframes
    # Find the ACTUAL existing frames before and after the gap
    # (not just gap_start-1 and gap_end+1, which might not exist)
    target_frames = {p.frame for p in target_points}
    overlap_before = max((f for f in target_frames if f < gap_start), default=None)
    overlap_after = min((f for f in target_frames if f > gap_end), default=None)

    final_points: list[CurvePoint] = []
    for point in result_points:
        should_mark_keyframe = False
        if overlap_before is not None and point.frame == overlap_before:
            should_mark_keyframe = True
        if overlap_after is not None and point.frame == overlap_after:
            should_mark_keyframe = True

        if should_mark_keyframe:
            # Mark overlap frame as keyframe (original data connecting to fill)
            final_points.append(point.with_status(PointStatus.KEYFRAME))
        else:
            final_points.append(point)

    # Sort by frame
    final_points.sort(key=lambda p: p.frame)

    # Convert back to tuple format
    return [p.to_tuple4() for p in final_points]


def average_multiple_sources(
    source_data_list: list[CurveDataList], gap_frames: list[int], offset_list: list[tuple[float, float]]
) -> list[CurvePoint]:
    """Average positions from multiple source curves at each gap frame.

    Args:
        source_data_list: List of source trajectories
        gap_frames: Frames to fill
        offset_list: Offset for each source curve (same length as source_data_list)

    Returns:
        List of CurvePoint objects with averaged positions

    Note:
        Per 3DEqualizer spec: "averaged result will only cover the frameranges where
        ALL input points have tracking information. This behaviour also applies when
        multiple tracks are used to fill the gap of another track."

        Only includes frames where ALL sources have data (not just any available sources)
    """
    if len(source_data_list) != len(offset_list):
        raise ValueError("source_data_list and offset_list must have same length")

    # Convert source data to frame-indexed dictionaries
    source_points_list: list[dict[int, CurvePoint]] = []
    for source_data in source_data_list:
        points_list = [CurvePoint.from_tuple(p) for p in source_data]
        points_dict = {p.frame: p for p in points_list}
        source_points_list.append(points_dict)

    # Find frames where ALL sources have data (within gap range)
    # This matches 3DEqualizer's behavior
    gap_frames_set = set(gap_frames)
    all_source_frames: list[set[int]] = [set(points.keys()) & gap_frames_set for points in source_points_list]

    if all_source_frames:
        common_frames: set[int] = all_source_frames[0].intersection(*all_source_frames[1:])
    else:
        common_frames = set()

    averaged_points: list[CurvePoint] = []

    # Only average frames where ALL sources have data
    for frame in sorted(common_frames):
        positions_x: list[float] = []
        positions_y: list[float] = []

        # Collect positions from ALL sources (we know all have data at this frame)
        for i, source_points in enumerate(source_points_list):
            source_point = source_points[frame]
            offset_x, offset_y = offset_list[i]

            # Apply offset
            positions_x.append(source_point.x + offset_x)
            positions_y.append(source_point.y + offset_y)

        # Average all sources
        avg_x = sum(positions_x) / len(positions_x)
        avg_y = sum(positions_y) / len(positions_y)

        avg_point = CurvePoint(frame=frame, x=avg_x, y=avg_y, status=PointStatus.TRACKED)
        averaged_points.append(avg_point)

    logger.info(
        f"Averaged {len(averaged_points)} points from {len(source_data_list)} sources "
        + "(only frames where ALL sources have data)"
    )

    return averaged_points


def interpolate_gap(curve_data: CurveDataList, gap_start: int, gap_end: int) -> CurveDataList:
    """Fill gap using spline interpolation between surrounding keyframes.

    Args:
        curve_data: Trajectory with gap
        gap_start: First frame of gap
        gap_end: Last frame of gap

    Returns:
        New curve data with gap filled by interpolated points

    Note:
        Uses cubic spline interpolation between last point before gap
        and first point after gap. Marks gap boundaries as keyframes.
    """
    # Convert to CurvePoint objects
    points = [CurvePoint.from_tuple(p) for p in curve_data]
    points.sort(key=lambda p: p.frame)

    # Find boundary points
    before_point = None
    after_point = None

    for point in reversed(points):
        if point.frame < gap_start:
            before_point = point
            break

    for point in points:
        if point.frame > gap_end:
            after_point = point
            break

    if before_point is None or after_point is None:
        logger.warning("Cannot interpolate: missing boundary points")
        return [p.to_tuple4() for p in points]

    # Simple linear interpolation between boundaries
    # (Could be enhanced with cubic spline for smoother curves)
    frame_range = after_point.frame - before_point.frame
    if frame_range <= 0:
        return [p.to_tuple4() for p in points]

    result_points: list[CurvePoint] = list(points)

    for frame in range(gap_start, gap_end + 1):
        # Linear interpolation
        t = (frame - before_point.frame) / frame_range
        interp_x = before_point.x + t * (after_point.x - before_point.x)
        interp_y = before_point.y + t * (after_point.y - before_point.y)

        interp_point = CurvePoint(frame=frame, x=interp_x, y=interp_y, status=PointStatus.INTERPOLATED)
        result_points.append(interp_point)

    # Mark overlap frames (frames OUTSIDE gap boundaries) as keyframes
    # These are the before_point and after_point frames where original data exists
    final_points: list[CurvePoint] = []
    for point in result_points:
        if point.frame == before_point.frame or point.frame == after_point.frame:
            # Mark overlap frame as keyframe (original data connecting to interpolation)
            final_points.append(point.with_status(PointStatus.KEYFRAME))
        else:
            final_points.append(point)

    # Sort and convert
    final_points.sort(key=lambda p: p.frame)

    logger.info(f"Interpolated {gap_end - gap_start + 1} frames between {before_point.frame} and {after_point.frame}")

    return [p.to_tuple4() for p in final_points]


def create_averaged_curve(source_curves: dict[str, CurveDataList]) -> tuple[str, CurveDataList]:
    """Create new curve averaging all source curves (Scenario 3).

    Args:
        source_curves: Dictionary of curve name to curve data

    Returns:
        Tuple of (new_curve_name, averaged_curve_data)

    Note:
        Only includes frames where ALL source curves have data.
        This ensures the averaged curve is complete and reliable.
    """
    if not source_curves:
        raise ValueError("No source curves provided")

    # Convert all curves to frame-indexed dictionaries
    curve_points_dict: dict[str, dict[int, CurvePoint]] = {}
    for curve_name, curve_data in source_curves.items():
        points_list = [CurvePoint.from_tuple(p) for p in curve_data]
        points_dict = {p.frame: p for p in points_list}
        curve_points_dict[curve_name] = points_dict

    # Find frames where ALL curves have data
    all_frames: list[set[int]] = [set(points.keys()) for points in curve_points_dict.values()]
    if all_frames:
        common_frames: set[int] = all_frames[0].intersection(*all_frames[1:])
    else:
        common_frames = set()

    if not common_frames:
        logger.warning("No common frames found across all source curves")
        return ("avrg_01", [])

    # Average positions at each common frame
    averaged_points: list[CurvePoint] = []
    for frame in sorted(common_frames):
        positions_x: list[float] = []
        positions_y: list[float] = []

        for points in curve_points_dict.values():
            point = points[frame]
            positions_x.append(point.x)
            positions_y.append(point.y)

        avg_x = sum(positions_x) / len(positions_x)
        avg_y = sum(positions_y) / len(positions_y)

        avg_point = CurvePoint(frame=frame, x=avg_x, y=avg_y, status=PointStatus.NORMAL)
        averaged_points.append(avg_point)

    # Generate unique name
    curve_name = "avrg_01"

    logger.info(
        f"Created averaged curve '{curve_name}' with {len(averaged_points)} points from {len(source_curves)} sources"
    )

    return (curve_name, [p.to_tuple4() for p in averaged_points])
