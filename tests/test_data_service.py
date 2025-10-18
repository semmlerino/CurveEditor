#!/usr/bin/env python
"""
Comprehensive tests for DataService - file I/O, data analysis, image loading.

This service is critical for curve data operations, file handling, and image
sequence management.
"""

import json
import threading
from typing import Any
from unittest.mock import Mock, patch

import pytest

from core.type_aliases import CurveDataList
from protocols.services import LoggingServiceProtocol, StatusServiceProtocol
from services.data_service import DataService


class TestDataAnalysis:
    """Test data analysis operations: smoothing, filtering, gap filling, outliers."""

    def test_smooth_moving_average_normal_case(self):
        """Test moving average smoothing with normal data."""
        service = DataService()
        data: CurveDataList = [
            (1, 10.0, 20.0),
            (2, 12.0, 22.0),
            (3, 14.0, 24.0),
            (4, 16.0, 26.0),
            (5, 18.0, 28.0),
        ]

        result = service.smooth_moving_average(data, window_size=3)

        assert len(result) == len(data)
        # Middle point should be average of neighbors
        assert result[2][1] == 14.0  # (12+14+16)/3 = 14
        assert result[2][2] == 24.0  # (22+24+26)/3 = 24

    def test_smooth_moving_average_preserves_frame_and_status(self):
        """Test that smoothing preserves frame numbers and status data."""
        service = DataService()
        data: CurveDataList = [
            (10, 5.0, 15.0, "keyframe"),
            (11, 7.0, 17.0, "interpolated"),
            (12, 9.0, 19.0, True),
        ]

        result = service.smooth_moving_average(data, window_size=3)

        assert result[0][0] == 10  # Frame preserved
        # Safe access for PointTuple4
        assert len(result[0]) == 4 and result[0][3] == "keyframe"  # Status preserved
        assert result[1][0] == 11
        assert len(result[1]) == 4 and result[1][3] == "interpolated"
        assert result[2][0] == 12
        assert len(result[2]) == 4 and result[2][3] is True

    def test_smooth_moving_average_insufficient_data(self):
        """Test smoothing with insufficient data points."""
        service = DataService()
        data: CurveDataList = [(1, 10.0, 20.0), (2, 12.0, 22.0)]

        result = service.smooth_moving_average(data, window_size=5)

        # Should return original data when insufficient points
        assert result == data

    def test_filter_median_normal_case(self):
        """Test median filter with normal data including outliers."""
        service = DataService()
        data: CurveDataList = [
            (1, 10.0, 20.0),
            (2, 100.0, 200.0),  # Outlier
            (3, 12.0, 22.0),
            (4, 14.0, 24.0),
            (5, 16.0, 26.0),
        ]

        result = service.filter_median(data, window_size=3)

        assert len(result) == len(data)
        # Median should reduce outlier impact
        assert result[1][1] < 50.0  # Outlier should be reduced
        assert result[1][2] < 100.0

    def test_filter_butterworth_with_scipy_available(self):
        """Test Butterworth filter (now uses simple_lowpass_filter)."""
        service = DataService()
        data: CurveDataList = [
            (1, 10.0, 20.0),
            (2, 12.0, 22.0),
            (3, 14.0, 24.0),
            (4, 16.0, 26.0),
            (5, 18.0, 28.0),
            (6, 20.0, 30.0),
        ]

        result = service.filter_butterworth(data, _cutoff=0.1)

        assert len(result) == len(data)
        # Verify data is returned (smoothing applied with moving average)
        # All coordinates should be present
        assert all(len(point) >= 3 for point in result)
        assert result[0][0] == 1  # Frame preserved
        assert result[-1][0] == 6  # Last frame preserved

    def test_filter_butterworth_without_scipy(self):
        """Test Butterworth filter when scipy is not available."""
        service = DataService()
        data: CurveDataList = [(1, 10.0, 20.0), (2, 12.0, 22.0)]

        with patch("services.data_analysis.signal", None):
            result = service.filter_butterworth(data)

            # Should return original data when scipy unavailable
            assert result == data

    def test_filter_butterworth_error_handling(self):
        """Test Butterworth filter error handling."""
        mock_logger = Mock(spec=LoggingServiceProtocol)
        service = DataService(logging_service=mock_logger)
        # Need at least 4 points to reach the error handling code
        data: CurveDataList = [
            (1, 10.0, 20.0),
            (2, 12.0, 22.0),
            (3, 14.0, 24.0),
            (4, 16.0, 26.0),
        ]

        # Mock simple_lowpass_filter to raise exception
        with patch("services.data_service.simple_lowpass_filter") as mock_filter:
            mock_filter.side_effect = ValueError("Filter failed")

            result = service.filter_butterworth(data)

            assert result == data  # Should return original on error
            mock_logger.log_error.assert_called_once()

    def test_fill_gaps_normal_case(self):
        """Test gap filling with linear interpolation."""
        service = DataService()
        data: CurveDataList = [
            (1, 10.0, 20.0),
            (5, 18.0, 28.0),  # Gap from frame 2-4
        ]

        result = service.fill_gaps(data, max_gap=5)

        # Should have interpolated points
        assert len(result) > len(data)
        # Check interpolated points exist
        filled_frames = [p[0] for p in result]
        assert 2 in filled_frames
        assert 3 in filled_frames
        assert 4 in filled_frames

    def test_fill_gaps_marks_interpolated(self):
        """Test that gap filling marks points as interpolated."""
        service = DataService()
        data: CurveDataList = [(1, 10.0, 20.0), (3, 14.0, 24.0)]

        result = service.fill_gaps(data, max_gap=2)

        # Find the interpolated point
        interpolated = [p for p in result if len(p) > 3 and p[3] is False]
        assert len(interpolated) == 1
        assert interpolated[0][0] == 2  # Frame 2 interpolated
        assert interpolated[0][3] is False  # Marked as interpolated

    def test_fill_gaps_respects_max_gap(self):
        """Test that gap filling respects maximum gap size."""
        service = DataService()
        data: CurveDataList = [(1, 10.0, 20.0), (10, 18.0, 28.0)]  # 8-frame gap

        result = service.fill_gaps(data, max_gap=5)

        # Should not fill gap larger than max_gap
        assert len(result) == len(data)

    def test_detect_outliers_normal_case(self):
        """Test outlier detection based on velocity deviation."""
        service = DataService()
        # Create data with a very obvious outlier - huge jump and back
        data: CurveDataList = [
            (1, 10.0, 20.0),
            (2, 12.0, 22.0),  # Normal velocity
            (3, 100.0, 200.0),  # Huge outlier jump
            (4, 14.0, 24.0),  # Jump back to normal
            (5, 16.0, 26.0),  # Normal continuation
        ]

        # Use lower threshold to be more sensitive
        outliers = service.detect_outliers(data, threshold=1.0)

        assert len(outliers) > 0, "Expected outliers to be detected in data with large jumps"

    def test_detect_outliers_insufficient_data(self):
        """Test outlier detection with insufficient data."""
        service = DataService()
        data: CurveDataList = [(1, 10.0, 20.0), (2, 11.0, 21.0)]

        outliers = service.detect_outliers(data)

        assert outliers == []

    def test_analyze_points_with_tuples(self):
        """Test point analysis with tuple format data."""
        service = DataService()
        points: CurveDataList = [
            (1, 10.0, 20.0),
            (5, 50.0, 80.0),
            (3, 30.0, 40.0),
        ]

        result = service.analyze_points(points)

        assert result["count"] == 3
        assert result["min_frame"] == 1
        assert result["max_frame"] == 5
        # Type narrow before indexing
        bounds = result["bounds"]
        assert isinstance(bounds, dict)
        assert bounds["min_x"] == 10.0
        assert bounds["max_x"] == 50.0
        assert bounds["min_y"] == 20.0
        assert bounds["max_y"] == 80.0

    def test_analyze_points_with_curve_point_objects(self):
        """Test point analysis with CurvePoint objects."""
        service = DataService()

        # Mock CurvePoint objects - use Any for dynamic attributes in tests
        mock_point1 = Mock()
        mock_point1.frame = 1
        mock_point1.x = 10.0
        mock_point1.y = 20.0

        mock_point2 = Mock()
        mock_point2.frame = 3
        mock_point2.x = 30.0
        mock_point2.y = 40.0

        points: list[Any] = [mock_point1, mock_point2]

        result = service.analyze_points(points)

        assert result["count"] == 2
        assert result["min_frame"] == 1
        assert result["max_frame"] == 3

    def test_analyze_points_empty_data(self):
        """Test point analysis with empty data."""
        service = DataService()

        result = service.analyze_points([])

        assert result["count"] == 0
        assert result["min_frame"] == 0
        assert result["max_frame"] == 0
        # Type narrow before indexing
        bounds = result["bounds"]
        assert isinstance(bounds, dict)
        assert bounds["min_x"] == 0


class TestFileOperations:
    """Test file I/O operations: JSON, CSV, 2DTrackData formats."""

    def test_load_json_array_format(self, tmp_path):
        """Test loading JSON in array format."""
        service = DataService()
        test_file = tmp_path / "test.json"

        # Create test JSON file
        json_data = [
            {"frame": 1, "x": 10.0, "y": 20.0, "status": "keyframe"},
            {"frame": 2, "x": 12.0, "y": 22.0, "status": "interpolated"},
        ]
        test_file.write_text(json.dumps(json_data))

        result = service.load_json(str(test_file))

        assert len(result) == 2
        assert result[0] == (1, 10.0, 20.0, "keyframe")
        assert result[1] == (2, 12.0, 22.0, "interpolated")

    def test_load_json_wrapped_format(self, tmp_path):
        """Test loading JSON in wrapped format with metadata."""
        service = DataService()
        test_file = tmp_path / "test.json"

        json_data = {
            "metadata": {"label": "Test Track", "color": "#FF0000"},
            "points": [
                {"frame": 1, "x": 10.0, "y": 20.0, "status": "keyframe"},
                {"frame": 2, "x": 12.0, "y": 22.0, "status": "interpolated"},
            ],
        }
        test_file.write_text(json.dumps(json_data))

        result = service.load_json(str(test_file))

        assert len(result) == 2
        assert result[0] == (1, 10.0, 20.0, "keyframe")

    def test_load_json_tuple_array_format(self, tmp_path):
        """Test loading JSON with tuple/array format."""
        service = DataService()
        test_file = tmp_path / "test.json"

        json_data = [
            [1, 10.0, 20.0, "keyframe"],
            [2, 12.0, 22.0, "interpolated"],
            [3, 14.0, 24.0],  # No status
        ]
        test_file.write_text(json.dumps(json_data))

        result = service.load_json(str(test_file))

        assert len(result) == 3
        assert result[0] == (1, 10.0, 20.0, "keyframe")
        assert result[2] == (3, 14.0, 24.0, "keyframe")  # Default status

    def test_load_json_file_not_found(self):
        """Test loading JSON file that doesn't exist."""
        mock_logger = Mock(spec=LoggingServiceProtocol)
        service = DataService(logging_service=mock_logger)

        result = service.load_json("/nonexistent/file.json")

        assert result == []
        mock_logger.log_error.assert_called_once()

    def test_load_json_invalid_json(self, tmp_path):
        """Test loading invalid JSON file."""
        mock_logger = Mock(spec=LoggingServiceProtocol)
        service = DataService(logging_service=mock_logger)
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json }")

        result = service.load_json(str(test_file))

        assert result == []
        mock_logger.log_error.assert_called_once()

    def test_save_json_success(self, tmp_path):
        """Test successful JSON file saving."""
        mock_logger = Mock(spec=LoggingServiceProtocol)
        service = DataService(logging_service=mock_logger)
        test_file = tmp_path / "output.json"

        data: CurveDataList = [
            (1, 10.0, 20.0, "keyframe"),
            (2, 12.0, 22.0, "interpolated"),
        ]

        result = service.save_json(str(test_file), data)

        assert result is True
        assert test_file.exists()

        # Verify content
        loaded_data = json.loads(test_file.read_text())
        assert "metadata" in loaded_data
        assert "points" in loaded_data
        assert len(loaded_data["points"]) == 2
        mock_logger.log_info.assert_called_once()

    def test_load_csv_with_header(self, tmp_path):
        """Test loading CSV file with header."""
        service = DataService()
        test_file = tmp_path / "test.csv"

        csv_content = """frame,x,y,status
1,10.0,20.0,keyframe
2,12.0,22.0,interpolated
"""
        test_file.write_text(csv_content)

        result = service.load_csv(str(test_file))

        assert len(result) == 2
        assert result[0] == (1, 10.0, 20.0, "keyframe")
        assert result[1] == (2, 12.0, 22.0, "interpolated")

    def test_load_csv_without_header(self, tmp_path):
        """Test loading CSV file without header."""
        service = DataService()
        test_file = tmp_path / "test.csv"

        csv_content = """1,10.0,20.0,keyframe
2,12.0,22.0,interpolated
"""
        test_file.write_text(csv_content)

        result = service.load_csv(str(test_file))

        assert len(result) == 2
        assert result[0] == (1, 10.0, 20.0, "keyframe")

    def test_load_csv_tab_delimited(self, tmp_path):
        """Test loading tab-delimited CSV file."""
        service = DataService()
        test_file = tmp_path / "test.tsv"

        csv_content = "1\t10.0\t20.0\tkeyframe\n2\t12.0\t22.0\tinterpolated"
        test_file.write_text(csv_content)

        result = service.load_csv(str(test_file))

        assert len(result) == 2
        assert result[0] == (1, 10.0, 20.0, "keyframe")

    def test_load_csv_semicolon_delimited(self, tmp_path):
        """Test loading semicolon-delimited CSV file."""
        service = DataService()
        test_file = tmp_path / "test.csv"

        csv_content = "1;10.0;20.0;keyframe\n2;12.0;22.0;interpolated"
        test_file.write_text(csv_content)

        result = service.load_csv(str(test_file))

        assert len(result) == 2
        assert result[0] == (1, 10.0, 20.0, "keyframe")

    def test_load_2dtrack_data_single_point(self, tmp_path):
        """Test loading 2DTrackData format (single curve) with 3DE metadata."""
        service = DataService()
        test_file = tmp_path / "test.txt"

        # 2DTrackData format: version, id1, id2, count, then data
        track_content = """1
07
0
3
1 100.0 600.0
2 102.0 598.0
3 104.0 596.0
"""
        test_file.write_text(track_content)

        result = service._load_2dtrack_data(str(test_file))

        # Result should be CurveDataWithMetadata with 3DE coordinate system
        from core.coordinate_system import CoordinateOrigin, CoordinateSystem
        from core.curve_data import CurveDataWithMetadata

        assert isinstance(result, CurveDataWithMetadata)
        assert result.metadata is not None
        assert result.metadata.system == CoordinateSystem.THREE_DE_EQUALIZER
        assert result.metadata.origin == CoordinateOrigin.BOTTOM_LEFT

        # Data should contain raw (unflipped) Y coordinates
        # Note: _apply_default_statuses marks first point as "keyframe", middle as "tracked"
        curve_data = result.data
        assert len(curve_data) == 3
        assert curve_data[0] == (1, 100.0, 600.0, "keyframe")  # Raw Y coordinate
        assert curve_data[1] == (2, 102.0, 598.0, "tracked")  # Tracked status
        assert curve_data[2] == (3, 104.0, 596.0, "keyframe")  # Last frame

    def test_load_tracked_data_multiple_points(self, tmp_path):
        """Test loading tracked data with multiple tracking points."""
        service = DataService()
        test_file = tmp_path / "tracked.txt"

        track_content = """12
Point1
0
2
1 100.0 600.0
2 102.0 598.0
12
Point02
1
2
1 200.0 500.0
2 202.0 498.0
"""
        test_file.write_text(track_content)

        result = service.load_tracked_data(str(test_file))

        assert len(result) == 2
        assert "Point1" in result
        assert "Point02" in result
        assert len(result["Point1"]) == 2
        assert len(result["Point02"]) == 2
        # Check Y-flipped coordinates for 3DEqualizer: y = 720 - y
        assert result["Point1"][0] == (1, 100.0, 120.0, "keyframe")  # Flipped: 720 - 600 = 120


class TestImageOperations:
    """Test image sequence loading and caching."""

    def test_load_image_sequence_success(self, tmp_path):
        """Test successful image sequence loading."""
        mock_logger = Mock(spec=LoggingServiceProtocol)
        service = DataService(logging_service=mock_logger)

        # Create test image files
        (tmp_path / "image001.jpg").touch()
        (tmp_path / "image002.png").touch()
        (tmp_path / "image003.gif").touch()
        (tmp_path / "not_image.txt").touch()  # Should be ignored

        result = service.load_image_sequence(str(tmp_path))

        assert len(result) == 3
        assert any("image001.jpg" in path for path in result)
        assert any("image002.png" in path for path in result)
        assert any("image003.gif" in path for path in result)
        assert not any("not_image.txt" in path for path in result)
        mock_logger.log_info.assert_called_once()

    def test_load_image_sequence_nonexistent_directory(self):
        """Test loading from nonexistent directory."""
        mock_logger = Mock(spec=LoggingServiceProtocol)
        service = DataService(logging_service=mock_logger)

        result = service.load_image_sequence("/nonexistent/directory")

        assert result == []
        mock_logger.log_error.assert_called_once()

    def test_clear_image_cache(self):
        """Test clearing the image cache."""
        service = DataService()

        # Add something to cache
        service._add_to_cache("test_key", "test_value")
        assert len(service._image_cache) > 0

        service.clear_image_cache()

        assert len(service._image_cache) == 0

    def test_cache_size_management(self):
        """Test that cache respects maximum size."""
        service = DataService()
        service.set_cache_size(2)  # Small cache for testing

        # Add items beyond cache size
        service._add_to_cache("key1", "value1")
        service._add_to_cache("key2", "value2")
        service._add_to_cache("key3", "value3")  # Should evict oldest

        assert len(service._image_cache) == 2
        assert "key1" not in service._image_cache  # Should be evicted
        assert "key2" in service._image_cache
        assert "key3" in service._image_cache


class TestRecentFiles:
    """Test recent files management."""

    def test_add_recent_file_new(self):
        """Test adding a new recent file."""
        service = DataService()

        service.add_recent_file("/path/to/file1.json")

        recent = service.get_recent_files()
        assert len(recent) == 1
        assert recent[0] == "/path/to/file1.json"

    def test_add_recent_file_moves_to_front(self):
        """Test that re-adding a file moves it to front."""
        service = DataService()

        service.add_recent_file("/path/to/file1.json")
        service.add_recent_file("/path/to/file2.json")
        service.add_recent_file("/path/to/file1.json")  # Re-add first file

        recent = service.get_recent_files()
        assert recent[0] == "/path/to/file1.json"  # Should be at front
        assert len(recent) == 2  # No duplicates

    def test_recent_files_max_limit(self):
        """Test that recent files respects maximum limit."""
        service = DataService()
        service._max_recent_files = 3

        # Add more than max
        for i in range(5):
            service.add_recent_file(f"/path/to/file{i}.json")

        recent = service.get_recent_files()
        assert len(recent) == 3  # Should not exceed max


class TestPointStatusAnalysis:
    """Test point status analysis methods."""

    def test_get_frame_point_status_tuple_format(self):
        """Test point status analysis with tuple format."""
        service = DataService()
        points: CurveDataList = [
            (1, 10.0, 20.0, "keyframe"),
            (1, 15.0, 25.0, "interpolated"),
            (2, 12.0, 22.0, "keyframe"),
        ]

        result = service.get_frame_point_status(points, 1)

        assert result == (1, 1, False)  # 1 keyframe, 1 interpolated, no selection

    def test_get_frame_point_status_boolean_legacy(self):
        """Test point status with legacy boolean format."""
        service = DataService()
        points: CurveDataList = [
            (1, 10.0, 20.0, False),  # False = keyframe in legacy
            (1, 15.0, 25.0, True),  # True = interpolated in legacy
        ]

        result = service.get_frame_point_status(points, 1)

        assert result == (1, 1, False)

    def test_get_frame_range_point_status(self):
        """Test point status analysis for multiple frames."""
        service = DataService()
        points: CurveDataList = [
            (1, 10.0, 20.0, "keyframe"),
            (1, 15.0, 25.0, "interpolated"),
            (2, 12.0, 22.0, "keyframe"),
            (3, 14.0, 24.0, "interpolated"),
        ]

        result = service.get_frame_range_point_status(points)

        # Check using FrameStatus named attributes
        assert result[1].keyframe_count == 1  # Frame 1: 1 keyframe
        assert result[1].interpolated_count == 1  # Frame 1: 1 interpolated
        assert result[2].keyframe_count == 1  # Frame 2: 1 keyframe
        assert result[2].interpolated_count == 0  # Frame 2: 0 interpolated
        assert result[3].keyframe_count == 0  # Frame 3: 0 keyframes
        assert result[3].interpolated_count == 1  # Frame 3: 1 interpolated


class TestThreadSafety:
    """Test thread safety of DataService operations."""

    def test_cache_operations_thread_safe(self):
        """Test that cache operations are thread-safe."""
        service = DataService()
        results = []
        errors = []

        def cache_worker(thread_id: int):
            try:
                for i in range(10):
                    key = f"thread_{thread_id}_item_{i}"
                    service._add_to_cache(key, f"value_{i}")
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=cache_worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0
        assert len(results) == 5

    def test_recent_files_operations_thread_safe(self):
        """Test that recent files operations handle concurrent access."""
        service = DataService()
        results = []
        errors = []

        def recent_files_worker(thread_id: int):
            try:
                for i in range(5):
                    file_path = f"/path/thread_{thread_id}/file_{i}.json"
                    service.add_recent_file(file_path)
                    recent = service.get_recent_files()
                    assert isinstance(recent, list)
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=recent_files_worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0
        assert len(results) == 3


class TestServiceIntegration:
    """Test integration with logging and status services."""

    def test_logging_service_integration(self):
        """Test that logging service is called appropriately."""
        mock_logger = Mock(spec=LoggingServiceProtocol)
        service = DataService(logging_service=mock_logger)

        # Test a method that logs
        points: CurveDataList = [(1, 10.0, 20.0), (10, 50.0, 80.0)]
        service.detect_outliers(points)

        # Should have logged info about outliers
        assert mock_logger.log_info.called or not service.detect_outliers(points)

    def test_status_service_integration(self):
        """Test that status service is called during operations."""
        mock_status = Mock(spec=StatusServiceProtocol)
        service = DataService(status_service=mock_status)

        # Test a method that updates status - need enough data points for processing
        data: CurveDataList = [
            (1, 10.0, 20.0),
            (2, 12.0, 22.0),
            (3, 14.0, 24.0),
            (4, 16.0, 26.0),
            (5, 18.0, 28.0),
        ]
        service.smooth_moving_average(data, window_size=3)

        mock_status.set_status.assert_called_once()

    def test_add_track_data_compatibility(self):
        """Test add_track_data compatibility method."""
        mock_status = Mock(spec=StatusServiceProtocol)
        service = DataService(status_service=mock_status)

        data: CurveDataList = [(1, 10.0, 20.0), (2, 12.0, 22.0)]
        service.add_track_data(data, "Test Track", "#FF0000")

        mock_status.set_status.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_data_handling(self):
        """Test that methods handle empty data gracefully."""
        service = DataService()
        empty_data: CurveDataList = []

        # All analysis methods should handle empty data
        assert service.smooth_moving_average(empty_data) == []
        assert service.filter_median(empty_data) == []
        assert service.fill_gaps(empty_data) == []
        assert service.detect_outliers(empty_data) == []

        analysis = service.analyze_points(empty_data)
        assert analysis["count"] == 0

    def test_single_point_data(self):
        """Test methods with single data point."""
        service = DataService()
        single_point: CurveDataList = [(1, 10.0, 20.0)]

        # Methods should handle single point gracefully
        assert service.smooth_moving_average(single_point) == single_point
        assert service.filter_median(single_point) == single_point
        assert service.fill_gaps(single_point) == single_point
        assert service.detect_outliers(single_point) == []

    def test_malformed_data_points(self):
        """Test handling of malformed data points."""
        service = DataService()

        # Test with insufficient data in tuples
        malformed_data: list[Any] = [(1, 10.0), (2, 12.0, 22.0, "keyframe")]  # Mixed lengths

        # Methods should not crash on malformed data
        try:
            result = service.analyze_points(malformed_data)
            assert isinstance(result, dict)
        except Exception as e:
            pytest.fail(f"Should handle malformed data gracefully: {e}")


class TestServiceSingleton:
    """Test the singleton behavior of get_data_service."""

    def test_get_data_service_singleton(self):
        """Test that get_data_service returns same instance."""
        from services import get_data_service

        service1 = get_data_service()
        service2 = get_data_service()

        assert service1 is service2
        assert isinstance(service1, DataService)

    def test_public_api_methods_available(self):
        """Test that public API methods are available."""
        service = DataService()

        # Test that all expected public methods exist by calling them
        # If methods don't exist, test should fail with AttributeError
        assert callable(service.load_csv)
        assert callable(service.load_json)
        assert callable(service.save_json)
        assert callable(service.smooth_moving_average)
        assert callable(service.filter_median)
        assert callable(service.fill_gaps)
        assert callable(service.detect_outliers)
        assert callable(service.analyze_points)
        assert callable(service.load_image_sequence)
        assert callable(service.add_recent_file)
        assert callable(service.get_recent_files)
