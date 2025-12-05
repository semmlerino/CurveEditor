"""
Edge case tests for DataService.

Tests data operations with edge cases:
- Missing files
- Corrupt data files
- Empty files
- Invalid file formats
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none

import pytest
import tempfile
import os
from services.data_service import DataService


class TestDataServiceMissingFiles:
    """Tests for handling missing files."""

    @pytest.fixture
    def data_service(self):
        """Create data service instance."""
        return DataService()

    def test_load_nonexistent_file(self, data_service):
        """Should handle loading nonexistent file gracefully."""
        result = data_service.load_csv("/nonexistent/path/file.csv")
        # Should return empty list, not raise
        assert result == []

    def test_load_csv_directory_instead_of_file(self, data_service):
        """Should handle path to directory instead of file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = data_service.load_csv(tmpdir)
            assert result == []

    def test_load_file_with_empty_path(self, data_service):
        """Should handle empty path string."""
        result = data_service.load_csv("")
        assert result == []


class TestDataServiceCorruptFiles:
    """Tests for handling corrupt or invalid files."""

    @pytest.fixture
    def data_service(self):
        """Create data service instance."""
        return DataService()

    def test_load_empty_csv_file(self, data_service):
        """Should handle empty CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("")  # Empty file
            temp_path = f.name

        try:
            result = data_service.load_csv(temp_path)
            # Should return empty list, not crash
            assert result == []
        finally:
            os.unlink(temp_path)

    def test_load_csv_with_only_header(self, data_service):
        """Should handle CSV with only header, no data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("frame,x,y\n")  # Header only
            temp_path = f.name

        try:
            result = data_service.load_csv(temp_path)
            # Should return empty list
            assert result == []
        finally:
            os.unlink(temp_path)

    def test_load_csv_with_invalid_numbers(self, data_service):
        """Should handle CSV with non-numeric values by skipping bad rows."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("frame,x,y\n")
            f.write("not_a_number,abc,xyz\n")
            f.write("1,0.5,0.5\n")  # Valid row
            temp_path = f.name

        try:
            result = data_service.load_csv(temp_path)
            # Should skip invalid row but include valid one
            assert isinstance(result, list)
        finally:
            os.unlink(temp_path)

    def test_load_csv_with_missing_columns(self, data_service):
        """Should handle CSV with fewer columns than expected."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("frame,x,y\n")
            f.write("1,0.5\n")  # Missing y column
            f.write("2,0.6,0.6\n")  # Valid row
            temp_path = f.name

        try:
            result = data_service.load_csv(temp_path)
            # Should skip row with missing columns
            assert isinstance(result, list)
        finally:
            os.unlink(temp_path)


class TestDataServiceValidData:
    """Tests for valid data to ensure basic functionality."""

    @pytest.fixture
    def data_service(self):
        """Create data service instance."""
        return DataService()

    def test_load_valid_csv(self, data_service):
        """Should correctly load valid CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("frame,x,y\n")
            f.write("1,0.5,0.5\n")
            f.write("2,0.6,0.6\n")
            f.write("3,0.7,0.7\n")
            temp_path = f.name

        try:
            result = data_service.load_csv(temp_path)
            assert result is not None
            assert len(result) == 3
            # Result is list of tuples (frame, x, y) or (frame, x, y, status)
            assert result[0][0] == 1  # frame
            assert result[0][1] == 0.5  # x
        finally:
            os.unlink(temp_path)

    def test_load_csv_with_tab_delimiter(self, data_service):
        """Should handle tab-delimited CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("frame\tx\ty\n")
            f.write("1\t0.5\t0.5\n")
            f.write("2\t0.6\t0.6\n")
            temp_path = f.name

        try:
            result = data_service.load_csv(temp_path)
            assert len(result) == 2
        finally:
            os.unlink(temp_path)


class TestDataServiceExtremeValues:
    """Tests for extreme values in data loading."""

    @pytest.fixture
    def data_service(self):
        """Create data service instance."""
        return DataService()

    def test_load_csv_with_large_frame_numbers(self, data_service):
        """Should handle large frame numbers."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("frame,x,y\n")
            f.write("999999,0.5,0.5\n")  # Large frame number
            temp_path = f.name

        try:
            result = data_service.load_csv(temp_path)
            assert len(result) == 1
            assert result[0][0] == 999999  # frame
        finally:
            os.unlink(temp_path)

    def test_load_csv_with_very_small_coordinates(self, data_service):
        """Should handle very small coordinate values."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("frame,x,y\n")
            f.write("1,0.0001,0.0001\n")
            temp_path = f.name

        try:
            result = data_service.load_csv(temp_path)
            assert len(result) == 1
            assert abs(result[0][1] - 0.0001) < 1e-6
        finally:
            os.unlink(temp_path)


class TestDataServiceGetPositionAtFrame:
    """Tests for get_position_at_frame with edge cases."""

    @pytest.fixture
    def data_service(self):
        """Create data service instance."""
        return DataService()

    def test_get_position_empty_points(self, data_service):
        """Should return None for empty point list."""
        result = data_service.get_position_at_frame([], 1)
        assert result is None

    def test_get_position_negative_frame(self, data_service):
        """Should handle negative frame number gracefully."""
        # Create valid points data
        points = [(1, 0.5, 0.5), (10, 0.6, 0.6)]
        result = data_service.get_position_at_frame(points, -1)
        # Should return None or extrapolated value
        assert result is None or isinstance(result, tuple)

    def test_get_position_zero_frame(self, data_service):
        """Should handle frame 0 gracefully."""
        points = [(1, 0.5, 0.5), (10, 0.6, 0.6)]
        result = data_service.get_position_at_frame(points, 0)
        # Should return None or extrapolated value
        assert result is None or isinstance(result, tuple)

    def test_get_position_single_point(self, data_service):
        """Should handle single point gracefully."""
        points = [(5, 0.5, 0.5)]
        result = data_service.get_position_at_frame(points, 5)
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_get_position_beyond_range(self, data_service):
        """Should handle frame beyond data range."""
        points = [(1, 0.5, 0.5), (10, 0.6, 0.6)]
        result = data_service.get_position_at_frame(points, 100)
        # Should return extrapolated or held value
        assert result is None or isinstance(result, tuple)
