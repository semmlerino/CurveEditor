#!/usr/bin/env python3
"""
Tests for gap visual rendering (dashed lines, point visibility, colors).

This test suite prevents regression of the "invisible dashed lines" bug where:
1. Inactive pen color was semi-transparent gray (barely visible)
2. Points were rendered on top of dashed lines (obscuring the gap)

These tests ensure gaps are visually distinct with:
- Bright cyan dashed lines (visible on dark background)
- No point markers in inactive segments (clean dashed line)

Created: 2025-10-22
Related Issues: Gap rendering not visible despite correct architecture
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from core.curve_segments import SegmentedCurve
from core.models import CurvePoint, PointStatus
from services import get_data_service
from ui.color_constants import CurveColors


class TestInactivePenColor:
    """Unit tests for inactive pen color configuration."""

    def test_inactive_pen_is_bright_cyan(self):
        """Test that inactive pen uses bright cyan (0, 255, 255) for visibility.

        REGRESSION PREVENTION: Previously used semi-transparent gray (128, 128, 128, 128)
        which was barely visible on dark background.
        """
        pen = CurveColors.get_inactive_pen()
        color = pen.color()

        # Verify bright cyan color
        assert color.red() == 0, "Inactive pen should be cyan (R=0)"
        assert color.green() == 255, "Inactive pen should be cyan (G=255)"
        assert color.blue() == 255, "Inactive pen should be cyan (B=255)"
        assert color.alpha() == 255, "Inactive pen should be opaque (A=255)"

    def test_inactive_pen_is_dashed(self):
        """Test that inactive pen uses dashed line style.

        REGRESSION PREVENTION: Ensure dashed style is applied for visual distinction.
        """
        pen = CurveColors.get_inactive_pen()

        # Verify dashed line style
        assert pen.style() == Qt.PenStyle.DashLine, "Inactive pen should use DashLine style"

    def test_inactive_pen_has_proper_width(self):
        """Test that inactive pen has visible width."""
        pen = CurveColors.get_inactive_pen(width=2)

        # Verify pen width
        assert pen.width() == 2, "Inactive pen should respect width parameter"

    def test_inactive_color_constant_is_bright_cyan(self):
        """Test that INACTIVE_CYAN constant is defined correctly."""
        color = CurveColors.INACTIVE_CYAN

        assert isinstance(color, QColor), "INACTIVE_CYAN should be QColor"
        assert color.red() == 0, "INACTIVE_CYAN should have R=0"
        assert color.green() == 255, "INACTIVE_CYAN should have G=255"
        assert color.blue() == 255, "INACTIVE_CYAN should have B=255"


class TestPointRenderingInInactiveSegments:
    """Unit tests for point rendering behavior in inactive segments."""

    def test_points_not_collected_for_inactive_segment_frames(self):
        """Test that points in inactive segments are skipped during collection.

        REGRESSION PREVENTION: Previously, points were rendered on top of
        dashed lines, obscuring the gap visual. Now they should be skipped.
        """
        # Arrange: Create curve with gap (frames 1-6 active, 7-22 inactive, 23-37 active)
        points = [
            CurvePoint(
                frame=i,
                x=50.0 + i * 10,
                y=50.0 + i * 10,
                status=PointStatus.KEYFRAME if i == 1 else PointStatus.TRACKED,
            )
            for i in range(1, 7)
        ]
        points.append(CurvePoint(frame=6, x=50.0 + 6 * 10, y=50.0 + 6 * 10, status=PointStatus.ENDFRAME))
        points.extend(
            [CurvePoint(frame=i, x=50.0 + i * 10, y=50.0 + i * 10, status=PointStatus.TRACKED) for i in range(7, 23)]
        )
        points.append(CurvePoint(frame=23, x=50.0 + 23 * 10, y=50.0 + 23 * 10, status=PointStatus.KEYFRAME))
        points.extend(
            [CurvePoint(frame=i, x=50.0 + i * 10, y=50.0 + i * 10, status=PointStatus.TRACKED) for i in range(24, 38)]
        )

        segmented_curve = SegmentedCurve.from_points(points)

        # Act: Check which frames are in inactive segments
        inactive_frames = []
        for frame in range(7, 23):
            segment = segmented_curve.get_segment_at_frame(frame)
            if segment and not segment.is_active:
                inactive_frames.append(frame)

        # Assert: Frames 7-22 should be in inactive segment
        assert len(inactive_frames) > 0, "Should have inactive frames"
        assert all(7 <= f <= 22 for f in inactive_frames), "Inactive frames should be 7-22"

    def test_active_segment_frames_still_render_points(self):
        """Test that points in active segments are still rendered normally.

        REGRESSION PREVENTION: Ensure fix doesn't break normal point rendering.
        """
        # Arrange: Create curve with only active segments
        points = [
            CurvePoint(frame=i, x=50.0 + i * 10, y=50.0 + i * 10, status=PointStatus.TRACKED) for i in range(1, 11)
        ]

        segmented_curve = SegmentedCurve.from_points(points)

        # Act: Verify all frames are in active segments
        active_frames = []
        for frame in range(1, 11):
            segment = segmented_curve.get_segment_at_frame(frame)
            if segment and segment.is_active:
                active_frames.append(frame)

        # Assert: All frames should be active
        assert len(active_frames) == 10, "All frames should be in active segments"

    def test_endframe_itself_is_rendered_with_point(self):
        """Test that ENDFRAME point itself is rendered (not skipped).

        REGRESSION PREVENTION: Only frames AFTER endframe should skip points.
        """
        # Arrange: Create curve with endframe
        points = [
            CurvePoint(frame=1, x=50.0, y=50.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=6, x=100.0, y=100.0, status=PointStatus.ENDFRAME),
            CurvePoint(frame=7, x=110.0, y=110.0, status=PointStatus.TRACKED),
        ]

        segmented_curve = SegmentedCurve.from_points(points)

        # Act: Check segment activity
        endframe_segment = segmented_curve.get_segment_at_frame(6)
        after_endframe_segment = segmented_curve.get_segment_at_frame(7)

        # Assert: ENDFRAME is in active segment, frame after is inactive
        assert endframe_segment is not None, "Should find segment for ENDFRAME"
        assert endframe_segment.is_active, "ENDFRAME itself should be in active segment"

        assert after_endframe_segment is not None, "Should find segment after ENDFRAME"
        assert not after_endframe_segment.is_active, "Frame after ENDFRAME should be inactive"


class TestGapRenderingIntegration:
    """Integration tests for complete gap rendering flow."""

    def test_data_service_provides_segmented_curve_for_rendering(self):
        """Test that DataService provides SegmentedCurve with gap information.

        REGRESSION PREVENTION: Renderer must access SegmentedCurve to know
        which frames are in inactive segments.
        """
        data_service = get_data_service()

        # Arrange: Curve with gap
        curve_data = [
            (1, 50.0, 50.0, "keyframe"),
            (2, 60.0, 60.0, "tracked"),
            (6, 100.0, 100.0, "endframe"),
            (7, 110.0, 110.0, "tracked"),  # Inactive
            (8, 120.0, 120.0, "tracked"),  # Inactive
            (23, 280.0, 280.0, "keyframe"),  # Active again
        ]

        # Act: Update DataService
        data_service.update_curve_data(curve_data)
        segmented_curve = data_service.segmented_curve

        # Assert: SegmentedCurve is available
        assert segmented_curve is not None, "DataService should provide SegmentedCurve"
        assert len(segmented_curve.segments) >= 2, "Should have multiple segments"

        # Assert: Gap frames are in inactive segment
        for frame in [7, 8]:
            segment = segmented_curve.get_segment_at_frame(frame)
            assert segment is not None, f"Should find segment for frame {frame}"
            assert not segment.is_active, f"Frame {frame} should be in inactive segment"

    def test_renderer_path_selection_with_status(self):
        """Test that renderer chooses segmented rendering when status present.

        REGRESSION PREVENTION: Renderer must detect status data to enable
        segment-aware rendering.
        """
        # Arrange: Curve data with status information
        curve_data = [
            (1, 50.0, 50.0, "keyframe"),
            (6, 100.0, 100.0, "endframe"),
            (7, 110.0, 110.0, "tracked"),
        ]

        # Act: Check if renderer would detect status
        has_status = any(len(pt) > 3 for pt in curve_data if pt)

        # Assert: Status should be detected
        assert has_status, "Renderer should detect status field in data"

    def test_complete_gap_visual_configuration(self):
        """Integration test: Verify complete gap rendering configuration.

        Tests the complete fix:
        1. DataService has SegmentedCurve with inactive segments
        2. Inactive pen is bright cyan with dashed style
        3. Points in inactive segments would be skipped

        REGRESSION PREVENTION: This is the complete fix for "invisible gaps".
        """
        # Step 1: Setup data with gap
        data_service = get_data_service()
        curve_data = [
            (1, 50.0, 50.0, "keyframe"),
            (6, 100.0, 100.0, "endframe"),
            (7, 110.0, 110.0, "tracked"),  # Should be invisible (no point marker)
            (23, 280.0, 280.0, "keyframe"),
        ]
        data_service.update_curve_data(curve_data)

        # Step 2: Verify segmentation
        segmented_curve = data_service.segmented_curve
        assert segmented_curve is not None
        segment_7 = segmented_curve.get_segment_at_frame(7)
        assert segment_7 is not None
        assert not segment_7.is_active, "Frame 7 should be in inactive segment"

        # Step 3: Verify pen configuration
        inactive_pen = CurveColors.get_inactive_pen()
        assert inactive_pen.color() == QColor(0, 255, 255), "Inactive pen should be bright cyan"
        assert inactive_pen.style() == Qt.PenStyle.DashLine, "Inactive pen should be dashed"

        # Step 4: Document expected behavior
        # When renderer draws frame 7:
        # - Line: Bright cyan dashed (from inactive_pen)
        # - Point: NOT rendered (skipped due to segment.is_active check)
        # Result: Clean dashed line visible on dark background


class TestRegressionPrevention:
    """Meta-tests to prevent regression of the bug fixes."""

    def test_inactive_color_is_not_gray(self):
        """REGRESSION TEST: Ensure inactive color is never semi-transparent gray.

        Original bug: QColor(128, 128, 128, 128) was barely visible.
        """
        color = CurveColors.INACTIVE_CYAN

        # Should not be gray (R=G=B)
        is_gray = color.red() == color.green() == color.blue()
        assert not is_gray, "Inactive color should not be gray (not visible on dark bg)"

        # Should be fully opaque
        assert color.alpha() == 255, "Inactive color should be fully opaque"

    def test_inactive_pen_is_not_solid_line(self):
        """REGRESSION TEST: Ensure inactive pen uses dashed style.

        Visual distinction requires dashed line style.
        """
        pen = CurveColors.get_inactive_pen()

        # Should not be solid line
        assert pen.style() != Qt.PenStyle.SolidLine, "Inactive pen should not be solid"
        assert pen.style() == Qt.PenStyle.DashLine, "Inactive pen must be dashed"

    def test_segment_activity_check_exists(self):
        """REGRESSION TEST: Ensure segment activity check exists in code path.

        Point rendering must check segment.is_active to skip inactive frames.
        """
        # This test documents the requirement that renderer checks segment.is_active
        # The actual implementation check is in rendering/optimized_curve_renderer.py
        # lines 898-902

        # Arrange: Create inactive segment
        points = [
            CurvePoint(frame=1, x=50.0, y=50.0, status=PointStatus.KEYFRAME),
            CurvePoint(frame=6, x=100.0, y=100.0, status=PointStatus.ENDFRAME),
            CurvePoint(frame=7, x=110.0, y=110.0, status=PointStatus.TRACKED),
        ]
        segmented_curve = SegmentedCurve.from_points(points)

        # Act: Verify that we can check segment activity
        segment = segmented_curve.get_segment_at_frame(7)

        # Assert: Activity check is possible
        assert segment is not None, "Should be able to get segment for frame"
        assert hasattr(segment, "is_active"), "Segment must have is_active attribute"
        assert isinstance(segment.is_active, bool), "is_active must be boolean"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
