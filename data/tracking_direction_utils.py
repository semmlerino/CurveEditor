#!/usr/bin/env python
"""
Tracking Direction Update Utilities for CurveEditor.

This module provides utilities for updating keyframe statuses when tracking
direction changes, mirroring 3DEqualizer's behavior patterns.

Based on 3DEqualizer behavior patterns:
- Forward tracking: ENDFRAME → KEYFRAME if next frame has valid data
- Backward tracking: KEYFRAME → ENDFRAME if previous frame has no valid data
- Bidirectional: Special handling for transitions from previous direction
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import PointStatus, TrackingDirection

from core.logger_utils import get_logger
from core.models import PointStatus, TrackingDirection
from core.type_aliases import CurveDataInput, CurveDataList

logger = get_logger("tracking_direction_utils")


def has_valid_position(curve_data: CurveDataInput, frame_index: int) -> bool:
    """Check if a frame has valid position data.

    Args:
        curve_data: List of point tuples
        frame_index: 0-based index into curve_data list

    Returns:
        True if position is valid (not [-1, -1])
    """
    if frame_index < 0 or frame_index >= len(curve_data):
        return False

    point_tuple = curve_data[frame_index]
    if len(point_tuple) >= 3:
        x, y = point_tuple[1], point_tuple[2]
        return x != -1 or y != -1
    return False


def get_point_status(curve_data: CurveDataInput, frame_index: int) -> PointStatus:
    """Get the status of a point from curve data.

    Args:
        curve_data: List of point tuples
        frame_index: 0-based index into curve_data list

    Returns:
        PointStatus of the point
    """
    if frame_index < 0 or frame_index >= len(curve_data):
        return PointStatus.NORMAL

    point_tuple = curve_data[frame_index]
    if len(point_tuple) >= 4:
        return PointStatus.from_legacy(point_tuple[3])
    return PointStatus.NORMAL


def update_keyframe_status_for_forward_tracking(curve_data: CurveDataInput) -> CurveDataList:
    """Update keyframe statuses for forward tracking direction.

    Forward tracking rules (from SetTrackingFwd.py):
    - If ENDFRAME has valid tracking data after it → convert to KEYFRAME
    - If KEYFRAME has no valid tracking data after it → convert to ENDFRAME

    Args:
        curve_data: List of point tuples to update

    Returns:
        Updated curve data with modified statuses
    """
    # Normalize data to ensure all points have 4 elements (frame, x, y, status)
    normalized_data = []
    for point_tuple in curve_data:
        if len(point_tuple) == 3:
            # Add default keyframe status for 3-element tuples
            normalized_data.append((*point_tuple, "keyframe"))
        else:
            normalized_data.append(point_tuple)

    updated_data = list(normalized_data)
    changes_made = 0

    for i, point_tuple in enumerate(normalized_data):
        frame, x, y = point_tuple[:3]
        current_status = PointStatus.from_legacy(point_tuple[3])

        # Only process keyframes and endframes
        if current_status not in (PointStatus.KEYFRAME, PointStatus.ENDFRAME):
            continue

        # Check if current position is valid
        if x == -1 and y == -1:
            continue

        # Check next frame for valid data
        has_next_valid = has_valid_position(normalized_data, i + 1)

        new_status = current_status

        if current_status == PointStatus.ENDFRAME and has_next_valid:
            # ENDFRAME with valid next frame → KEYFRAME
            new_status = PointStatus.KEYFRAME
            logger.debug(f"Frame {frame}: ENDFRAME -> KEYFRAME (has valid tracking after)")
            changes_made += 1

        elif current_status == PointStatus.KEYFRAME and not has_next_valid:
            # KEYFRAME with no valid next frame → ENDFRAME
            new_status = PointStatus.ENDFRAME
            logger.debug(f"Frame {frame}: KEYFRAME -> ENDFRAME (no valid tracking after)")
            changes_made += 1

        # Update the tuple if status changed
        if new_status != current_status:
            updated_data[i] = (frame, x, y, new_status.value)

    logger.info(f"Forward tracking update: {changes_made} status changes made")
    return updated_data


def update_keyframe_status_for_backward_tracking(curve_data: CurveDataInput) -> CurveDataList:
    """Update keyframe statuses for backward tracking direction.

    Backward tracking rules (from SetTrackingBwd.py):
    - If ENDFRAME has valid tracking data before it → convert to KEYFRAME
    - If KEYFRAME has no valid tracking data before it → convert to ENDFRAME

    Args:
        curve_data: List of point tuples to update

    Returns:
        Updated curve data with modified statuses
    """
    # Normalize data to ensure all points have 4 elements (frame, x, y, status)
    normalized_data = []
    for point_tuple in curve_data:
        if len(point_tuple) == 3:
            # Add default keyframe status for 3-element tuples
            normalized_data.append((*point_tuple, "keyframe"))
        else:
            normalized_data.append(point_tuple)

    updated_data = list(normalized_data)
    changes_made = 0

    for i, point_tuple in enumerate(normalized_data):
        frame, x, y = point_tuple[:3]
        current_status = PointStatus.from_legacy(point_tuple[3])

        # Only process keyframes and endframes
        if current_status not in (PointStatus.KEYFRAME, PointStatus.ENDFRAME):
            continue

        # Check if current position is valid
        if x == -1 and y == -1:
            continue

        # Check previous frame for valid data
        has_prev_valid = has_valid_position(normalized_data, i - 1)

        new_status = current_status

        if current_status == PointStatus.ENDFRAME and has_prev_valid:
            # ENDFRAME with valid previous frame → KEYFRAME
            new_status = PointStatus.KEYFRAME
            logger.debug(f"Frame {frame}: ENDFRAME -> KEYFRAME (has valid tracking before)")
            changes_made += 1

        elif current_status == PointStatus.KEYFRAME and not has_prev_valid:
            # KEYFRAME with no valid previous frame → ENDFRAME
            new_status = PointStatus.ENDFRAME
            logger.debug(f"Frame {frame}: KEYFRAME -> ENDFRAME (no valid tracking before)")
            changes_made += 1

        # Update the tuple if status changed
        if new_status != current_status:
            updated_data[i] = (frame, x, y, new_status.value)

    logger.info(f"Backward tracking update: {changes_made} status changes made")
    return updated_data


def update_keyframe_status_for_bidirectional_tracking(
    curve_data: CurveDataInput, previous_direction: TrackingDirection
) -> CurveDataList:
    """Update keyframe statuses for bidirectional tracking direction.

    Bidirectional tracking rules (from SetTrackingFwdBwd.py):
    - When transitioning from backward tracking, apply special rules:
      - KEYFRAME with no valid next position → ENDFRAME
      - ENDFRAME with valid next position → KEYFRAME
    - Otherwise preserve existing keyframe structure

    Args:
        curve_data: List of point tuples to update
        previous_direction: The previous tracking direction before switching to bidirectional

    Returns:
        Updated curve data with modified statuses
    """
    # Normalize data to ensure all points have 4 elements (frame, x, y, status)
    normalized_data = []
    for point_tuple in curve_data:
        if len(point_tuple) == 3:
            # Add default keyframe status for 3-element tuples
            normalized_data.append((*point_tuple, "keyframe"))
        else:
            normalized_data.append(point_tuple)

    updated_data = list(normalized_data)
    changes_made = 0

    # Only apply special rules when transitioning from backward tracking
    if previous_direction != TrackingDirection.TRACKING_BW:
        logger.info("Bidirectional tracking: No special updates needed (not from backward)")
        return updated_data

    for i, point_tuple in enumerate(normalized_data):
        frame, x, y = point_tuple[:3]
        current_status = PointStatus.from_legacy(point_tuple[3])

        # Only process keyframes and endframes
        if current_status not in (PointStatus.KEYFRAME, PointStatus.ENDFRAME):
            continue

        # Check if current position is valid
        if x == -1 and y == -1:
            continue

        # Check next frame for valid data
        has_next_valid = has_valid_position(normalized_data, i + 1)

        new_status = current_status

        if current_status == PointStatus.KEYFRAME and not has_next_valid:
            # KEYFRAME with no valid next frame → ENDFRAME
            new_status = PointStatus.ENDFRAME
            logger.debug(f"Frame {frame}: KEYFRAME -> ENDFRAME (bidirectional from backward)")
            changes_made += 1

        elif current_status == PointStatus.ENDFRAME and has_next_valid:
            # ENDFRAME with valid next frame → KEYFRAME
            new_status = PointStatus.KEYFRAME
            logger.debug(f"Frame {frame}: ENDFRAME -> KEYFRAME (bidirectional from backward)")
            changes_made += 1

        # Update the tuple if status changed
        if new_status != current_status:
            updated_data[i] = (frame, x, y, new_status.value)

    logger.info(f"Bidirectional tracking update: {changes_made} status changes made")
    return updated_data


def update_keyframe_status_for_tracking_direction(
    curve_data: CurveDataInput, new_direction: TrackingDirection, previous_direction: TrackingDirection | None = None
) -> CurveDataList:
    """Update keyframe statuses based on new tracking direction.

    This is the main entry point for tracking direction updates, implementing
    the behavior patterns from 3DEqualizer.

    Args:
        curve_data: List of point tuples to update
        new_direction: New tracking direction
        previous_direction: Previous tracking direction (needed for bidirectional)

    Returns:
        Updated curve data with modified statuses
    """
    logger.info(f"Updating keyframe statuses for direction change: {previous_direction} -> {new_direction}")

    if new_direction == TrackingDirection.TRACKING_FW:
        return update_keyframe_status_for_forward_tracking(curve_data)
    elif new_direction == TrackingDirection.TRACKING_BW:
        return update_keyframe_status_for_backward_tracking(curve_data)
    elif new_direction == TrackingDirection.TRACKING_FW_BW:
        return update_keyframe_status_for_bidirectional_tracking(
            curve_data, previous_direction or TrackingDirection.TRACKING_FW
        )
    else:
        logger.warning(f"Unknown tracking direction: {new_direction}")
        return curve_data
