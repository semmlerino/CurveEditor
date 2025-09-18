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
    from core.type_aliases import CurveDataList


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
    """

    start_frame: int
    end_frame: int
    points: list[CurvePoint] = field(default_factory=list)
    is_active: bool = True
    starts_with_startframe: bool = False

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
        prev_point: CurvePoint | None = None
        in_inactive_region = False

        for point in sorted_points:
            # Check if this point starts a new active segment
            if prev_point and prev_point.is_endframe:
                # We just passed an ENDFRAME
                if current_segment_points:
                    # Save the previous segment
                    segment = CurveSegment(
                        start_frame=current_segment_points[0].frame,
                        end_frame=current_segment_points[-1].frame,
                        points=current_segment_points,
                        is_active=not in_inactive_region,
                    )
                    segments.append(segment)
                    current_segment_points = []

                # Check if this point is a startframe (keyframe after endframe)
                if point.status in (PointStatus.KEYFRAME, PointStatus.TRACKED):
                    # This is a startframe, start a new active segment
                    in_inactive_region = False
                    current_segment_points = [point]
                else:
                    # Still in inactive region
                    in_inactive_region = True
                    current_segment_points = [point]
            else:
                # Continue current segment
                current_segment_points.append(point)

                # If this is an ENDFRAME, the segment ends here
                if point.is_endframe:
                    if current_segment_points:
                        segment = CurveSegment(
                            start_frame=current_segment_points[0].frame,
                            end_frame=current_segment_points[-1].frame,
                            points=current_segment_points,
                            is_active=not in_inactive_region,
                        )
                        # Check if segment starts with a startframe
                        if current_segment_points and current_segment_points[0].is_startframe(
                            sorted_points[sorted_points.index(current_segment_points[0]) - 1]
                            if sorted_points.index(current_segment_points[0]) > 0
                            else None
                        ):
                            segment.starts_with_startframe = True
                        segments.append(segment)
                        current_segment_points = []
                        # After an ENDFRAME, we enter an inactive region
                        in_inactive_region = True

            prev_point = point

        # Add any remaining points as a final segment
        if current_segment_points:
            segment = CurveSegment(
                start_frame=current_segment_points[0].frame,
                end_frame=current_segment_points[-1].frame,
                points=current_segment_points,
                is_active=not in_inactive_region,
            )
            segments.append(segment)

        return cls(segments=segments, all_points=sorted_points)

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

    def update_segment_activity(self, point_index: int, new_status: PointStatus) -> None:
        """Update segment activity when a point's status changes.

        When an ENDFRAME becomes a KEYFRAME, reactivate the following segment.
        When a KEYFRAME becomes an ENDFRAME, deactivate the following segment.

        Args:
            point_index: Index of the point being changed
            new_status: New status for the point
        """
        if point_index < 0 or point_index >= len(self.all_points):
            return

        old_point = self.all_points[point_index]

        # If changing from ENDFRAME to KEYFRAME/TRACKED, reactivate next segment
        if old_point.is_endframe and new_status in (PointStatus.KEYFRAME, PointStatus.TRACKED):
            # Find and reactivate the next segment
            for segment in self.segments:
                if segment.start_frame > old_point.frame:
                    segment.is_active = True
                    break

        # If changing to ENDFRAME, deactivate following segment until next startframe
        elif not old_point.is_endframe and new_status == PointStatus.ENDFRAME:
            # Find and deactivate segments until we hit a startframe
            deactivating = False
            for segment in self.segments:
                if segment.contains_frame(old_point.frame):
                    # This segment now ends with an ENDFRAME
                    deactivating = True
                elif deactivating:
                    # Check if this segment starts with a startframe
                    if segment.points and segment.points[0].status in (PointStatus.KEYFRAME, PointStatus.TRACKED):
                        # Stop deactivating after this startframe
                        break
                    segment.is_active = False

    @classmethod
    def from_curve_data(cls, curve_data: CurveDataList) -> SegmentedCurve:
        """Create SegmentedCurve from legacy curve data format.

        Args:
            curve_data: List of point tuples in legacy format

        Returns:
            New SegmentedCurve instance
        """
        from core.models import CurvePoint

        points = [CurvePoint.from_tuple(pt) for pt in curve_data]
        return cls.from_points(points)
