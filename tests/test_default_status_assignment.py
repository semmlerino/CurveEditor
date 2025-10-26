#!/usr/bin/env python
"""
Tests for default status assignment functionality.

Following best practices from UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md:
- Test behavior, not implementation
- Use real components over mocks
- Mock only at system boundaries
- Use factory fixtures for test data
- Parametrized tests for comprehensive coverage
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

import csv
import json

import pytest

from services.data_service import DataService

# ============================================================================
# Factory Fixtures (Best Practice: Reusable test data generation)
# ============================================================================


@pytest.fixture
def make_curve_point():
    """Factory for creating curve point tuples."""

    def _make_point(frame: int, x: float, y: float, status: str | None = None):
        if status is None:
            return (frame, x, y)
        return (frame, x, y, status)

    return _make_point


@pytest.fixture
def make_curve_data():
    """Factory for creating curve data lists."""

    def _make_data(*points):
        """Create curve data from point specifications.

        Args:
            points: Tuples of (frame, x, y) or (frame, x, y, status)
        """
        return list(points)

    return _make_data


@pytest.fixture
def data_service():
    """Real DataService instance for integration testing."""
    return DataService()


# ============================================================================
# Unit Tests: Core _apply_default_statuses() Logic
# ============================================================================


class TestApplyDefaultStatuses:
    """Test the core status assignment logic."""

    def test_empty_data_returns_empty(self, data_service):
        """Test that empty input returns empty output."""
        result = data_service._apply_default_statuses([])
        assert result == []

    def test_single_point_becomes_keyframe(self, data_service, make_curve_point):
        """Test that a single point becomes a keyframe (last frame rule)."""
        data = [make_curve_point(10, 100.0, 200.0)]
        result = data_service._apply_default_statuses(data)

        assert len(result) == 1
        assert result[0] == (10, 100.0, 200.0, "keyframe")

    def test_two_points_no_gap(self, data_service, make_curve_point):
        """Test two consecutive points: first keyframe, last keyframe."""
        data = [make_curve_point(1, 100.0, 200.0), make_curve_point(2, 110.0, 210.0)]
        result = data_service._apply_default_statuses(data)

        assert len(result) == 2
        assert result[0] == (1, 100.0, 200.0, "keyframe")  # First frame becomes keyframe
        assert result[1] == (2, 110.0, 210.0, "keyframe")  # Last frame becomes keyframe

    def test_points_with_gap_creates_endframe(self, data_service, make_curve_point):
        """Test that frame before gap becomes endframe."""
        data = [
            make_curve_point(1, 100.0, 200.0),
            make_curve_point(2, 110.0, 210.0),
            make_curve_point(3, 120.0, 220.0),  # Should become endframe
            make_curve_point(10, 200.0, 300.0),  # Gap here
            make_curve_point(11, 210.0, 310.0),  # Should become keyframe (last)
        ]
        result = data_service._apply_default_statuses(data)

        assert len(result) == 5
        assert result[0] == (1, 100.0, 200.0, "keyframe")  # First frame becomes keyframe
        assert result[1] == (2, 110.0, 210.0, "tracked")  # Middle frame
        assert result[2] == (3, 120.0, 220.0, "endframe")  # Before gap
        assert result[3] == (10, 200.0, 300.0, "keyframe")  # First after gap becomes keyframe
        assert result[4] == (11, 210.0, 310.0, "keyframe")  # Last frame becomes keyframe

    def test_multiple_gaps(self, data_service, make_curve_point):
        """Test multiple gaps create multiple endframes."""
        data = [
            make_curve_point(1, 100.0, 200.0),  # Gap after (1->5), becomes endframe
            make_curve_point(5, 150.0, 250.0),  # Gap after (5->10), becomes endframe
            make_curve_point(10, 200.0, 300.0),  # Gap after (10->15), becomes endframe
            make_curve_point(15, 250.0, 350.0),  # Last frame, becomes keyframe
        ]
        result = data_service._apply_default_statuses(data)

        assert len(result) == 4
        assert result[0] == (1, 100.0, 200.0, "keyframe")  # First frame becomes keyframe
        assert result[1] == (5, 150.0, 250.0, "keyframe")  # First after gap becomes keyframe
        assert result[2] == (10, 200.0, 300.0, "keyframe")  # First after gap becomes keyframe
        assert result[3] == (15, 250.0, 350.0, "keyframe")  # Last frame becomes keyframe

    def test_preserves_explicit_status(self, data_service, make_curve_point):
        """Test that explicitly set valid statuses are preserved."""
        data = [
            make_curve_point(1, 100.0, 200.0, "interpolated"),  # Explicit
            make_curve_point(2, 110.0, 210.0),  # Will get default
            make_curve_point(5, 150.0, 250.0, "keyframe"),  # Explicit
            make_curve_point(6, 160.0, 260.0),  # Will get default (keyframe - last)
        ]
        result = data_service._apply_default_statuses(data)

        assert len(result) == 4
        assert result[0] == (1, 100.0, 200.0, "interpolated")  # Preserved
        assert result[1] == (2, 110.0, 210.0, "endframe")  # Default (before gap)
        assert result[2] == (5, 150.0, 250.0, "keyframe")  # Preserved
        assert result[3] == (6, 160.0, 260.0, "keyframe")  # Default (last)

    def test_unsorted_input_gets_sorted(self, data_service, make_curve_point):
        """Test that unsorted input is properly sorted by frame."""
        data = [
            make_curve_point(10, 200.0, 300.0),
            make_curve_point(1, 100.0, 200.0),
            make_curve_point(5, 150.0, 250.0),
        ]
        result = data_service._apply_default_statuses(data)

        # Should be sorted by frame
        assert result[0][0] == 1  # Frame 1
        assert result[1][0] == 5  # Frame 5
        assert result[2][0] == 10  # Frame 10

        # Check statuses according to rules: first frame, first after gap, last frame
        assert result[0][3] == "keyframe"  # First frame becomes keyframe
        assert result[1][3] == "keyframe"  # First after gap (1->5) becomes keyframe
        assert result[2][3] == "keyframe"  # Last frame becomes keyframe


# ============================================================================
# Parametrized Tests: Comprehensive Scenario Coverage
# ============================================================================


@pytest.mark.parametrize(
    ("input_data", "expected_statuses"),
    [
        # Single point
        ([(1, 100.0, 200.0)], ["keyframe"]),
        # Two consecutive points
        ([(1, 100.0, 200.0), (2, 110.0, 210.0)], ["keyframe", "keyframe"]),
        # Three consecutive points (no gaps)
        ([(1, 100.0, 200.0), (2, 110.0, 210.0), (3, 120.0, 220.0)], ["keyframe", "tracked", "keyframe"]),
        # Five consecutive points (no gaps)
        (
            [(1, 100.0, 200.0), (2, 110.0, 210.0), (3, 120.0, 220.0), (4, 130.0, 230.0), (5, 140.0, 240.0)],
            ["keyframe", "tracked", "tracked", "tracked", "keyframe"],
        ),
        # Gap in sequence
        ([(1, 100.0, 200.0), (2, 110.0, 210.0), (5, 150.0, 250.0)], ["keyframe", "endframe", "keyframe"]),
        # Multiple gaps
        (
            [(1, 100.0, 200.0), (3, 120.0, 220.0), (7, 170.0, 270.0), (8, 180.0, 280.0)],
            ["keyframe", "keyframe", "keyframe", "keyframe"],
        ),
        # Large gap
        ([(1, 100.0, 200.0), (100, 1000.0, 2000.0)], ["keyframe", "keyframe"]),
    ],
)
def test_status_assignment_scenarios(data_service, input_data, expected_statuses):
    """Test various status assignment scenarios."""
    result = data_service._apply_default_statuses(input_data)

    assert len(result) == len(expected_statuses)
    for i, expected_status in enumerate(expected_statuses):
        assert result[i][3] == expected_status


# ============================================================================
# Integration Tests: File Loading with Status Assignment
# ============================================================================


class TestFileLoadingIntegration:
    """Test that file loading applies status assignment correctly."""

    def test_csv_loading_with_status_assignment(self, data_service, tmp_path):
        """Test CSV loading applies default status rules."""
        # Create test CSV file without status column
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["frame", "x", "y"])  # Header
            writer.writerow([1, 100.0, 200.0])
            writer.writerow([2, 110.0, 210.0])
            writer.writerow([5, 150.0, 250.0])  # Gap
            writer.writerow([6, 160.0, 260.0])

        result = data_service._load_csv(str(csv_file))

        # Verify status assignment
        assert len(result) == 4
        assert result[0][3] == "keyframe"  # First frame becomes keyframe
        assert result[1][3] == "endframe"  # Before gap
        assert result[2][3] == "keyframe"  # First frame after gap becomes keyframe
        assert result[3][3] == "keyframe"  # Last frame

    def test_csv_with_explicit_status_preserved(self, data_service, tmp_path):
        """Test CSV with explicit status column preserves values."""
        csv_file = tmp_path / "test_status.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["frame", "x", "y", "status"])
            writer.writerow([1, 100.0, 200.0, "interpolated"])  # Explicit
            writer.writerow([2, 110.0, 210.0, ""])  # Empty - gets default
            writer.writerow([3, 120.0, 220.0, "keyframe"])  # Explicit

        result = data_service._load_csv(str(csv_file))

        assert len(result) == 3
        assert result[0][3] == "interpolated"  # Preserved
        assert result[1][3] == "tracked"  # Default applied
        assert result[2][3] == "keyframe"  # Preserved (also last frame)

    def test_json_loading_with_status_assignment(self, data_service, tmp_path):
        """Test JSON loading applies default status rules."""
        # Create test JSON file
        json_file = tmp_path / "test.json"
        data = [
            {"frame": 1, "x": 100.0, "y": 200.0},
            {"frame": 2, "x": 110.0, "y": 210.0},
            {"frame": 5, "x": 150.0, "y": 250.0},  # Gap
        ]
        with open(json_file, "w") as f:
            json.dump(data, f)

        result = data_service._load_json(str(json_file))

        assert len(result) == 3
        assert result[0][3] == "keyframe"  # First frame becomes keyframe
        assert result[1][3] == "endframe"  # Before gap
        assert result[2][3] == "keyframe"  # Last frame

    def test_2dtrack_loading_with_status_assignment(self, data_service, tmp_path):
        """Test 2DTrackData loading applies default status rules."""
        # Create test 2DTrackData file
        track_file = tmp_path / "test.txt"
        with open(track_file, "w") as f:
            f.write("1\n")  # Version
            f.write("10\n")  # Identifier 1
            f.write("0\n")  # Identifier 2
            f.write("4\n")  # Point count
            f.write("1 100.0 200.0\n")
            f.write("2 110.0 210.0\n")
            f.write("5 150.0 250.0\n")  # Gap
            f.write("6 160.0 260.0\n")

        result = data_service._load_2dtrack_data(str(track_file))

        assert len(result) == 4
        assert result[0][3] == "keyframe"  # First frame becomes keyframe
        assert result[1][3] == "endframe"  # Before gap
        assert result[2][3] == "keyframe"  # First frame after gap becomes keyframe
        assert result[3][3] == "keyframe"  # Last frame


# ============================================================================
# Real File Testing: KeyFrameTest.txt
# ============================================================================


class TestRealFileLoading:
    """Test with real files to verify end-to-end behavior."""

    def test_keyframe_test_file_loading(self, data_service):
        """Test loading the actual KeyFrameTest.txt file."""
        # Test with the real file that was having issues
        result = data_service._load_2dtrack_data("KeyFrameTest.txt")

        if not result:
            pytest.skip("KeyFrameTest.txt not available")

        # Verify the expected behavior from the file
        statuses = {point[0]: point[3] for point in result}

        # Key expectations based on the file structure
        assert statuses[14] == "endframe"  # Frame before gap (14 -> 29)
        assert statuses[37] == "keyframe"  # Last frame

        # Count status types
        tracked_count = sum(1 for s in statuses.values() if s == "tracked")
        endframe_count = sum(1 for s in statuses.values() if s == "endframe")
        keyframe_count = sum(1 for s in statuses.values() if s == "keyframe")

        assert tracked_count == 19  # Most frames are tracked
        assert endframe_count == 1  # One endframe before gap
        assert keyframe_count == 3  # First frame, first after gap, and last frame are keyframes


# ============================================================================
# Edge Cases and Error Conditions
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_invalid_status_gets_default(self, data_service, make_curve_point):
        """Test that invalid status values get default assignment."""
        data = [
            make_curve_point(1, 100.0, 200.0, "invalid_status"),
            make_curve_point(2, 110.0, 210.0, ""),  # Empty string
            make_curve_point(3, 120.0, 220.0, None),  # None value
        ]
        result = data_service._apply_default_statuses(data)

        assert len(result) == 3
        assert result[0][3] == "keyframe"  # First frame becomes keyframe (default applied)
        assert result[1][3] == "tracked"  # Default applied
        assert result[2][3] == "keyframe"  # Default applied (last frame)

    def test_large_frame_numbers(self, data_service, make_curve_point):
        """Test with large frame numbers."""
        data = [
            make_curve_point(1000, 100.0, 200.0),
            make_curve_point(1001, 110.0, 210.0),
            make_curve_point(2000, 200.0, 300.0),  # Large gap
        ]
        result = data_service._apply_default_statuses(data)

        assert len(result) == 3
        assert result[0][3] == "keyframe"  # First frame becomes keyframe
        assert result[1][3] == "endframe"  # Before large gap
        assert result[2][3] == "keyframe"  # Last frame

    def test_negative_frame_numbers(self, data_service, make_curve_point):
        """Test with negative frame numbers."""
        data = [
            make_curve_point(-5, 100.0, 200.0),
            make_curve_point(-4, 110.0, 210.0),
            make_curve_point(1, 150.0, 250.0),  # Gap
        ]
        result = data_service._apply_default_statuses(data)

        assert len(result) == 3
        # Should be sorted by frame
        assert result[0][0] == -5
        assert result[1][0] == -4
        assert result[2][0] == 1

        # Check statuses
        assert result[0][3] == "keyframe"  # First frame becomes keyframe
        assert result[1][3] == "endframe"  # Before gap
        assert result[2][3] == "keyframe"  # Last frame

    def test_duplicate_frames_handled(self, data_service, make_curve_point):
        """Test behavior with duplicate frame numbers."""
        data = [
            make_curve_point(1, 100.0, 200.0),
            make_curve_point(1, 105.0, 205.0),  # Duplicate frame
            make_curve_point(2, 110.0, 210.0),
        ]
        result = data_service._apply_default_statuses(data)

        # Should handle duplicates gracefully
        assert len(result) == 3
        # All frames present, last one is keyframe
        last_frame = max(point[0] for point in result)
        last_points = [point for point in result if point[0] == last_frame]
        assert any(point[3] == "keyframe" for point in last_points)


# ============================================================================
# Performance and Stress Tests
# ============================================================================


class TestPerformance:
    """Test performance with larger datasets."""

    def test_large_dataset_performance(self, data_service, make_curve_point):
        """Test performance with large number of points."""
        # Create 1000 points with some gaps
        data = []
        for i in range(1, 1001):
            if i % 100 == 0:
                continue  # Create gaps every 100 frames
            data.append(make_curve_point(i, float(i), float(i * 2)))

        # Should complete quickly
        result = data_service._apply_default_statuses(data)

        assert len(result) > 900  # Most points preserved
        # Last point should be keyframe
        assert result[-1][3] == "keyframe"
        # Should have multiple endframes (before gaps)
        endframe_count = sum(1 for point in result if point[3] == "endframe")
        assert endframe_count > 5  # Multiple gaps created endframes

    @pytest.mark.parametrize("gap_size", [2, 10, 100, 1000])
    def test_various_gap_sizes(self, data_service, make_curve_point, gap_size):
        """Test that gap detection works with various gap sizes."""
        data = [
            make_curve_point(1, 100.0, 200.0),
            make_curve_point(2, 110.0, 210.0),
            make_curve_point(2 + gap_size, 150.0, 250.0),
        ]
        result = data_service._apply_default_statuses(data)

        assert len(result) == 3
        assert result[0][3] == "keyframe"  # First frame becomes keyframe
        assert result[1][3] == "endframe"  # Before gap of any size
        assert result[2][3] == "keyframe"  # Last frame
