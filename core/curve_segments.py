#!/usr/bin/env python
"""
Curve Segmentation System for 3DEqualizer-style tracking.

This module provides segment management for curves with gaps, where ENDFRAME
points mark segment boundaries and create discontinuous curves.

Key concepts:
- A curve segment is a continuous series of points between gaps
- ENDFRAME points mark the end of a segment
- The next KEYFRAME/TRACKED point after an ENDFRAME is a STARTFRAME
- Points between an ENDFRAME and the next STARTFRAME are inactive
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.models import CurvePoint, PointStatus

if TYPE_CHECKING:
    from core.type_aliases import CurveDataInput


@dataclass
class CurveSegment:
    """Represents a continuous curve segment between gaps.

    A segment is a series of points that should be rendered as a continuous curve.
    Segments are separated by ENDFRAME points which create gaps in the curve.

    Attributes:
        start_frame: Frame number where this segment starts
        end_frame: Frame number where this segment ends
        points: List of CurvePoints in this segment
        is_active: Whether this segment should be rendered/interpolated
        starts_with_startframe: True if this segment begins with a startframe
        originally_active: Whether this segment was originally active (for restoration)
        deactivated_by_frame: Frame number of endframe that deactivated this segment (if any)
    """

    start_frame: int
    end_frame: int
    points: list[CurvePoint] = field(default_factory=list)
    is_active: bool = True
    starts_with_startframe: bool = False
    originally_active: bool = True
    deactivated_by_frame: int | None = None

    def __post_init__(self) -> None:
        """Validate segment after initialization."""
        if self.points:
            # Update frame range based on actual points
            frames = [p.frame for p in self.points]
            self.start_frame = min(frames)
            self.end_frame = max(frames)

    @property
    def frame_range(self) -> tuple[int, int]:
        """Get the frame range of this segment."""
        return (self.start_frame, self.end_frame)

    @property
    def point_count(self) -> int:
        """Get the number of points in this segment."""
        return len(self.points)

    @property
    def has_keyframes(self) -> bool:
        """Check if this segment contains any keyframes."""
        return any(p.status in (PointStatus.KEYFRAME, PointStatus.TRACKED) for p in self.points)

    def contains_frame(self, frame: int) -> bool:
        """Check if a frame number is within this segment's range.

        Args:
            frame: Frame number to check

        Returns:
            True if the frame is within this segment
        """
        return self.start_frame <= frame <= self.end_frame

    def get_point_at_frame(self, frame: int) -> CurvePoint | None:
        """Get the point at a specific frame.

        Args:
            frame: Frame number to search for

        Returns:
            CurvePoint at that frame or None
        """
        for point in self.points:
            if point.frame == frame:
                return point
        return None

    def can_be_restored(self) -> bool:
        """Check if this segment can be restored to active state.

        Returns:
            True if segment was originally active and is currently inactive
        """
        return self.originally_active and not self.is_active

    def restore_to_original_state(self) -> None:
        """Restore segment to its original active state."""
        if self.originally_active:
            self.is_active = True
            self.deactivated_by_frame = None

    def deactivate_by_endframe(self, endframe_number: int) -> None:
        """Deactivate segment due to an endframe conversion.

        Args:
            endframe_number: Frame number of the endframe that caused deactivation
        """
        self.is_active = False
        self.deactivated_by_frame = endframe_number


@dataclass
class SegmentedCurve:
    """Manages a curve with multiple segments separated by gaps.

    This class handles the segmentation of curves based on ENDFRAME points,
    tracking which segments are active and managing the relationships between
    segments.

    Attributes:
        segments: List of CurveSegments
        all_points: Complete list of all points (for reference)
    """

    segments: list[CurveSegment] = field(default_factory=list)
    all_points: list[CurvePoint] = field(default_factory=list)

    @classmethod
    def from_points(cls, points: list[CurvePoint]) -> SegmentedCurve:
        """Create a SegmentedCurve from a list of points.

        Analyzes the points to identify segment boundaries based on ENDFRAME
        points and creates appropriate segments.

        Args:
            points: List of CurvePoints (should be sorted by frame)

        Returns:
            New SegmentedCurve instance with segments
        """
        if not points:
            return cls()

        # Sort points by frame to ensure proper segmentation
        sorted_points = sorted(points, key=lambda p: p.frame)

        segments: list[CurveSegment] = []
        current_segment_points: list[CurvePoint] = []

        # Find all endframes for reference (not currently used but may be needed later)
        # endframe_frames = set(p.frame for p in sorted_points if p.is_endframe)

        # Track if we're in a gap (after an endframe)
        in_gap_after_endframe = False

        for i, point in enumerate(sorted_points):
            # Determine if we need to start a new segment
            should_start_new_segment = False

            if i > 0:
                prev_point = sorted_points[i - 1]

                # Start new segment after an endframe
                if prev_point.is_endframe:
                    should_start_new_segment = True
                    in_gap_after_endframe = True  # We're now in a gap

                # Start new segment if this is a keyframe after being in a gap
                elif in_gap_after_endframe and point.status == PointStatus.KEYFRAME:
                    should_start_new_segment = True
                    in_gap_after_endframe = False  # Gap ends at keyframe

            if should_start_new_segment and current_segment_points:
                # Save the current segment
                # Determine if it should be active
                # Segments containing only tracked/interpolated points in a gap are inactive
                is_active = not (
                    in_gap_after_endframe
                    and all(p.status in (PointStatus.TRACKED, PointStatus.INTERPOLATED) for p in current_segment_points)
                )

                segment = CurveSegment(
                    start_frame=current_segment_points[0].frame,
                    end_frame=current_segment_points[-1].frame,
                    points=current_segment_points,
                    is_active=is_active,
                    originally_active=is_active,
                )
                segments.append(segment)
                current_segment_points = []

            # Add point to current segment
            current_segment_points.append(point)

            # If this is an endframe, close the segment
            if point.is_endframe and current_segment_points:
                segment = CurveSegment(
                    start_frame=current_segment_points[0].frame,
                    end_frame=current_segment_points[-1].frame,
                    points=current_segment_points,
                    is_active=True,  # Segments with endframes are active
                    originally_active=True,
                )
                segments.append(segment)
                current_segment_points = []

        # Add any remaining points as a final segment
        if current_segment_points:
            # Determine if this segment should be active
            # It's inactive if we're in a gap and it only contains tracked/interpolated points
            is_segment_active = not (
                in_gap_after_endframe
                and all(p.status in (PointStatus.TRACKED, PointStatus.INTERPOLATED) for p in current_segment_points)
            )

            segment = CurveSegment(
                start_frame=current_segment_points[0].frame,
                end_frame=current_segment_points[-1].frame,
                points=current_segment_points,
                is_active=is_segment_active,
                originally_active=is_segment_active,
            )
            segments.append(segment)

        # Create the segmented curve
        curve = cls(segments=segments, all_points=sorted_points)

        # Apply 3DEqualizer gap behavior automatically when there are any points after endframes
        # All points after ENDFRAME should be in inactive segments until a KEYFRAME starts a new active segment
        needs_gap_splitting = False
        for i, point in enumerate(sorted_points[:-1]):  # Check all but last point
            if point.is_endframe:
                # Any point after ENDFRAME requires gap behavior (except if it's immediately a KEYFRAME)
                next_point = sorted_points[i + 1]
                if next_point.status != PointStatus.KEYFRAME:
                    needs_gap_splitting = True
                    break

        if needs_gap_splitting:
            curve._reapply_endframe_deactivation()

        return curve

    @property
    def active_segments(self) -> list[CurveSegment]:
        """Get only the active segments for rendering."""
        return [s for s in self.segments if s.is_active]

    @property
    def inactive_segments(self) -> list[CurveSegment]:
        """Get only the inactive segments."""
        return [s for s in self.segments if not s.is_active]

    @property
    def frame_range(self) -> tuple[int, int] | None:
        """Get the overall frame range across all segments."""
        if not self.all_points:
            return None
        frames = [p.frame for p in self.all_points]
        return (min(frames), max(frames))

    def get_segment_at_frame(self, frame: int) -> CurveSegment | None:
        """Find the segment containing a specific frame.

        Args:
            frame: Frame number to search for

        Returns:
            CurveSegment containing that frame or None
        """
        for segment in self.segments:
            if segment.contains_frame(frame):
                return segment
        return None

    def get_active_points(self) -> list[CurvePoint]:
        """Get all points from active segments only."""
        points: list[CurvePoint] = []
        for segment in self.active_segments:
            points.extend(segment.points)
        return points

    def get_interpolation_boundaries(self, frame: int) -> tuple[CurvePoint | None, CurvePoint | None]:
        """Get the valid interpolation boundaries for a frame.

        Returns the previous and next keyframes that can be used for interpolation,
        respecting segment boundaries. Will not cross ENDFRAME points.

        Args:
            frame: Frame number to find boundaries for

        Returns:
            Tuple of (prev_keyframe, next_keyframe) or (None, None) if in inactive region
        """
        segment = self.get_segment_at_frame(frame)

        if not segment or not segment.is_active:
            # Frame is in an inactive region
            return (None, None)

        # Find boundaries within the segment only
        prev_keyframe: CurvePoint | None = None
        next_keyframe: CurvePoint | None = None

        for point in segment.points:
            if point.frame < frame and point.status in (PointStatus.KEYFRAME, PointStatus.TRACKED, PointStatus.NORMAL):
                prev_keyframe = point
            elif point.frame > frame and point.status in (
                PointStatus.KEYFRAME,
                PointStatus.TRACKED,
                PointStatus.NORMAL,
            ):
                if next_keyframe is None:
                    next_keyframe = point
                break

        return (prev_keyframe, next_keyframe)

    def get_position_at_frame(self, frame: int) -> tuple[float, float] | None:
        """Get the position at a specific frame, respecting gap behavior.

        For active segments: Uses normal interpolation between keyframes.
        For inactive segments (gaps): Returns the held position from the preceding endframe.

        Args:
            frame: Frame number to get position for

        Returns:
            Tuple of (x, y) coordinates or None if no position available
        """
        segment = self.get_segment_at_frame(frame)

        if segment and segment.is_active:
            # Frame is in an active segment - use normal interpolation
            return self._interpolate_in_active_segment(segment, frame)
        elif segment and not segment.is_active:
            # Frame is in an inactive segment - check if it has an actual point first
            actual_point = segment.get_point_at_frame(frame)
            if actual_point:
                # Frame has an actual point (e.g., endframe) - return its position
                return (actual_point.x, actual_point.y)
            else:
                # Frame is in gap - return held position
                return self._get_held_position_for_gap(frame)
        else:
            # Frame is not in any segment - check if it's in a gap or beyond all segments
            # If there are segments after this frame, it's in a gap
            segments_after = [s for s in self.segments if s.start_frame > frame]
            if segments_after:
                # Frame is in a gap between segments
                return self._get_held_position_for_gap(frame)
            else:
                # Frame is beyond all segments
                return self._get_position_beyond_segments(frame)

    def _interpolate_in_active_segment(self, segment: CurveSegment, frame: int) -> tuple[float, float] | None:
        """Interpolate position within an active segment.

        Args:
            segment: The active segment containing the frame
            frame: Frame number to interpolate

        Returns:
            Interpolated (x, y) coordinates or None
        """
        # Check if frame has an exact point
        exact_point = segment.get_point_at_frame(frame)
        if exact_point:
            return (exact_point.x, exact_point.y)

        # Find interpolation boundaries within this segment
        prev_point: CurvePoint | None = None
        next_point: CurvePoint | None = None

        for point in segment.points:
            if point.frame < frame and point.status in (PointStatus.KEYFRAME, PointStatus.TRACKED, PointStatus.NORMAL):
                prev_point = point
            elif point.frame > frame and point.status in (
                PointStatus.KEYFRAME,
                PointStatus.TRACKED,
                PointStatus.NORMAL,
            ):
                if next_point is None:
                    next_point = point
                break

        # Linear interpolation between boundaries
        if prev_point and next_point:
            # Interpolate between prev and next
            frame_ratio = (frame - prev_point.frame) / (next_point.frame - prev_point.frame)
            x = prev_point.x + (next_point.x - prev_point.x) * frame_ratio
            y = prev_point.y + (next_point.y - prev_point.y) * frame_ratio
            return (x, y)
        elif prev_point:
            # Only have previous point - use its position
            return (prev_point.x, prev_point.y)
        elif next_point:
            # Only have next point - use its position
            return (next_point.x, next_point.y)
        else:
            # No valid interpolation points in segment
            return None

    def _get_held_position_for_gap(self, frame: int) -> tuple[float, float] | None:
        """Get the held position for a frame in a gap (inactive segment).

        Finds the preceding endframe and returns its position.

        Args:
            frame: Frame number in the gap

        Returns:
            Held position (x, y) from preceding endframe or None
        """
        # Find the most recent endframe before this frame
        preceding_endframe: CurvePoint | None = None

        for point in self.all_points:
            if point.frame < frame and point.is_endframe:
                if preceding_endframe is None or point.frame > preceding_endframe.frame:
                    preceding_endframe = point

        if preceding_endframe:
            return (preceding_endframe.x, preceding_endframe.y)

        # If no preceding endframe found, check if we're in an inactive segment
        # and try to find the last point of the previous active segment
        for segment in self.segments:
            if segment.is_active and segment.end_frame < frame:
                # This active segment ends before our frame
                if segment.points:
                    last_point = segment.points[-1]
                    return (last_point.x, last_point.y)

        return None

    def _get_position_beyond_segments(self, frame: int) -> tuple[float, float] | None:
        """Get position for a frame beyond all segments.

        Only returns a held position if the last point is an endframe,
        otherwise returns None (no position available beyond data).

        Args:
            frame: Frame number beyond all segments

        Returns:
            Held position from last endframe or None
        """
        if not self.all_points:
            return None

        # Find the last point in the curve
        last_point = max(self.all_points, key=lambda p: p.frame)

        # Only return held position if the last point is an endframe
        # and the frame is after it
        if last_point.is_endframe and frame > last_point.frame:
            return (last_point.x, last_point.y)

        return None

    def rebuild_segments_from_points(self) -> None:
        """Rebuild segments from current point list, preserving restoration metadata.

        This method reconstructs the segment structure while preserving information
        about which segments were originally active for proper restoration.
        """
        if not self.all_points:
            self.segments.clear()
            return

        # Store current restoration metadata before rebuilding
        restoration_data = {}
        for segment in self.segments:
            # Key by frame range to match segments after rebuild
            key = (segment.start_frame, segment.end_frame)
            restoration_data[key] = {
                "originally_active": segment.originally_active,
                "deactivated_by_frame": segment.deactivated_by_frame,
                "is_active": segment.is_active,  # Preserve current active state
            }

        # Rebuild segments using the existing logic
        rebuilt_curve = self.from_points(self.all_points)
        self.segments = rebuilt_curve.segments

        # Restore metadata for matching segments
        for segment in self.segments:
            key = (segment.start_frame, segment.end_frame)
            if key in restoration_data:
                segment.originally_active = restoration_data[key]["originally_active"]
                segment.deactivated_by_frame = restoration_data[key]["deactivated_by_frame"]
                segment.is_active = restoration_data[key]["is_active"]  # Restore active state

    def restore_segments_after_endframe(self, endframe_number: int) -> None:
        """Restore segments that were deactivated by a specific endframe.

        When an endframe is converted back to a keyframe, this method restores
        all segments that were deactivated by that endframe.

        Args:
            endframe_number: Frame number of the endframe being converted to keyframe
        """
        for segment in self.segments:
            if segment.deactivated_by_frame == endframe_number and segment.can_be_restored():
                segment.restore_to_original_state()

    def deactivate_segments_after_endframe(self, endframe_number: int) -> None:
        """Deactivate segments after a newly created endframe.

        When a keyframe is converted to an endframe, this method deactivates
        subsequent segments until the next startframe.

        Args:
            endframe_number: Frame number of the newly created endframe
        """
        deactivating = False
        for segment in self.segments:
            if segment.contains_frame(endframe_number):
                # Found the segment containing the endframe
                # This segment should remain active, but segments after it should be deactivated
                deactivating = True
                # Don't deactivate the segment containing the endframe itself
                continue
            elif deactivating:
                # We're now in segments after the endframe
                # Only stop deactivating when we find a segment that starts with a keyframe (startframe)
                if segment.points and segment.points[0].status == PointStatus.KEYFRAME:
                    # Stop deactivating - this segment starts with a keyframe/startframe
                    break
                else:
                    # This segment is after the endframe and doesn't start with a keyframe
                    # Deactivate it (including segments that contain other endframes in the gap)
                    segment.deactivate_by_endframe(endframe_number)

    def update_segment_activity(self, point_index: int, new_status: PointStatus) -> None:
        """Update segment activity when a point's status changes with data preservation.

        When an ENDFRAME becomes a KEYFRAME, restore all segments deactivated by that endframe.
        When a KEYFRAME becomes an ENDFRAME, deactivate subsequent segments but preserve data.

        Args:
            point_index: Index of the point being changed
            new_status: New status for the point
        """
        if point_index < 0 or point_index >= len(self.all_points):
            return

        old_point = self.all_points[point_index]
        old_status = old_point.status

        # Update the point status in our data
        updated_point = old_point.with_status(new_status)
        self.all_points[point_index] = updated_point

        # Handle conversion from ENDFRAME to KEYFRAME/TRACKED (restoration)
        if old_status == PointStatus.ENDFRAME and new_status in (PointStatus.KEYFRAME, PointStatus.TRACKED):
            # Restore all segments that were deactivated by this endframe
            self.restore_segments_after_endframe(old_point.frame)

            # Rebuild segments to ensure proper structure after status change
            self.rebuild_segments_from_points()

            # Re-evaluate all remaining endframes to ensure proper deactivation
            self._reapply_endframe_deactivation()

        # Handle conversion to ENDFRAME (deactivation with preservation)
        elif old_status != PointStatus.ENDFRAME and new_status == PointStatus.ENDFRAME:
            # Rebuild segments first to ensure proper structure after status change
            self.rebuild_segments_from_points()

            # Then deactivate segments that end with this endframe
            self.deactivate_segments_after_endframe(old_point.frame)

            # Apply 3DEqualizer gap behavior for segments starting with tracked frames
            self._reapply_endframe_deactivation()

    def _reapply_endframe_deactivation(self) -> None:
        """Re-evaluate all endframes in the data and apply 3DEqualizer gap behavior.

        This is used after restoration to ensure that segments ending with remaining
        endframes are properly deactivated, and that segments starting with tracked
        frames after endframes remain inactive until a keyframe is reached.
        """
        # Find all endframes in the data
        endframes = [point.frame for point in self.all_points if point.status == PointStatus.ENDFRAME]

        # Apply deactivation for each endframe
        for endframe_number in endframes:
            self.deactivate_segments_after_endframe(endframe_number)

        # Apply 3DEqualizer gap behavior: segments starting with TRACKED points
        # after endframes should be split so tracked points are in inactive segments
        segments_to_split: list[tuple[int, int]] = []
        for i, segment in enumerate(self.segments):
            if segment.points and segment.is_active:
                # Skip segments that contain endframes - they should remain active as-is
                if any(p.is_endframe for p in segment.points):
                    continue

                # Check if this segment starts with tracked points after an endframe
                first_point = segment.points[0]
                if first_point.status == PointStatus.TRACKED:
                    # Find the previous point to check if it's an endframe
                    prev_point = None
                    for point in self.all_points:
                        if point.frame < first_point.frame:
                            if prev_point is None or point.frame > prev_point.frame:
                                prev_point = point

                    # If previous point is endframe, split this segment at first keyframe
                    if prev_point and prev_point.is_endframe:
                        # Find first keyframe in segment
                        keyframe_index = None
                        for j, point in enumerate(segment.points):
                            if point.status == PointStatus.KEYFRAME:
                                keyframe_index = j
                                break

                        if keyframe_index is not None and keyframe_index > 0:
                            # Split segment: tracked points become inactive, keyframe starts new active segment
                            segments_to_split.append((i, keyframe_index))

        # Apply splits (in reverse order to preserve indices)
        for segment_idx, split_idx in reversed(segments_to_split):
            segment = self.segments[segment_idx]

            # Create inactive segment for tracked points
            tracked_points = segment.points[:split_idx]
            inactive_segment = CurveSegment(
                start_frame=tracked_points[0].frame,
                end_frame=tracked_points[-1].frame,
                points=tracked_points,
                is_active=False,
                originally_active=segment.originally_active,
                deactivated_by_frame=segment.deactivated_by_frame,
            )

            # Create active segment for keyframe and after
            keyframe_points = segment.points[split_idx:]
            active_segment = CurveSegment(
                start_frame=keyframe_points[0].frame,
                end_frame=keyframe_points[-1].frame,
                points=keyframe_points,
                is_active=True,
                originally_active=segment.originally_active,
                starts_with_startframe=True,  # Keyframe after gap is startframe
            )

            # Replace original segment with split segments
            self.segments[segment_idx : segment_idx + 1] = [inactive_segment, active_segment]

    @classmethod
    def from_curve_data(cls, curve_data: CurveDataInput) -> SegmentedCurve:
        """Create SegmentedCurve from legacy curve data format.

        Args:
            curve_data: List of point tuples in legacy format

        Returns:
            New SegmentedCurve instance
        """
        from core.models import CurvePoint

        points = [CurvePoint.from_tuple(pt) for pt in curve_data]
        return cls.from_points(points)
