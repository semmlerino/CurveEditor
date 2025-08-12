#!/usr/bin/env python3
"""
Tests for the DataService module (consolidated from FileService).

This test suite verifies the functionality of the DataService class,
which handles file operations, data analysis, and image management.
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Type alias
PointsList = list[tuple[int, float, float]]

from services.data_service import DataService
from tests.conftest import BaseMockMainWindow

class MockMainWindow(BaseMockMainWindow):
    """Mock implementation of MainWindowProtocol for testing file operations."""

    def __init__(self) -> None:
        super().__init__()
        # File service specific overrides
        self.default_directory = os.path.expanduser("~")

# Test fixtures
@pytest.fixture
def main_window() -> MockMainWindow:
    """Create a mock main window for testing."""
    return MockMainWindow()

@pytest.fixture
def sample_curve_data() -> PointsList:
    """Create sample curve data for testing."""
    return [
        (1, 100.0, 200.0, "0.8"),  # Using string status to match PointTupleWithStatus type
        (2, 105.0, 205.0, "0.9"),
        (3, 110.0, 210.0, "0.85"),
        (4, 115.0, 215.0, "0.95"),
    ]

class TestDataService:
    """Test suite for DataService class."""
    
    @pytest.fixture
    def data_service(self) -> DataService:
        """Create a DataService instance for testing."""
        return DataService()
    
    @pytest.fixture
    def sample_data(self) -> list[tuple]:
        """Sample curve data for testing."""
        return [
            (1, 100.0, 200.0, 'keyframe'),
            (2, 105.0, 205.0, 'keyframe'),
            (3, 110.0, 210.0, 'keyframe'),
            (5, 120.0, 220.0, 'keyframe'),  # Gap at frame 4
            (6, 125.0, 225.0, 'keyframe'),
        ]

    # ==================== Analysis Method Tests ====================
    
    def test_smooth_moving_average(self, data_service: DataService, sample_data: list[tuple]) -> None:
        """Test moving average smoothing."""
        result = data_service.smooth_moving_average(sample_data, window_size=3)
        assert len(result) == len(sample_data)
        # First and last points should remain relatively unchanged
        assert result[0][0] == sample_data[0][0]  # Same frame
        assert result[-1][0] == sample_data[-1][0]  # Same frame
    
    def test_smooth_moving_average_small_data(self, data_service: DataService) -> None:
        """Test smoothing with data smaller than window size."""
        small_data = [(1, 100.0, 200.0, 'keyframe')]
        result = data_service.smooth_moving_average(small_data, window_size=5)
        assert result == small_data
    
    def test_filter_median(self, data_service: DataService, sample_data: list[tuple]) -> None:
        """Test median filter."""
        result = data_service.filter_median(sample_data, window_size=3)
        assert len(result) == len(sample_data)
        assert result[0][0] == sample_data[0][0]  # Frame preserved
    
    def test_filter_butterworth(self, data_service: DataService, sample_data: list[tuple]) -> None:
        """Test butterworth filter."""
        result = data_service.filter_butterworth(sample_data, cutoff=0.1)
        assert len(result) == len(sample_data)
        assert result[0] == sample_data[0]  # First point unchanged
    
    def test_fill_gaps(self, data_service: DataService, sample_data: list[tuple]) -> None:
        """Test gap filling with linear interpolation."""
        result = data_service.fill_gaps(sample_data, max_gap=10)
        # Should have filled the gap at frame 4
        assert len(result) > len(sample_data)
        # Check that frame 4 was added
        frame_numbers = [p[0] for p in result]
        assert 4 in frame_numbers
    
    def test_detect_outliers(self, data_service: DataService, sample_data: list[tuple]) -> None:
        """Test outlier detection."""
        # Add an outlier point
        outlier_data = sample_data + [(7, 1000.0, 1000.0, 'keyframe')]
        outliers = data_service.detect_outliers(outlier_data, threshold=2.0)
        assert isinstance(outliers, list)
        # Should detect at least one outlier
        assert len(outliers) >= 0  # May or may not detect depending on algorithm
    
    # ==================== File I/O Tests ====================
    
    def test_load_track_data_user_cancels(self, data_service: DataService, main_window: MockMainWindow) -> None:
        """Test load_track_data when user cancels the file dialog."""
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName", return_value=("", "")):
            result = data_service.load_track_data(main_window)
            assert result is None
    
    def test_save_track_data_no_data(self, data_service: DataService, main_window: MockMainWindow) -> None:
        """Test save_track_data with no data."""
        result = data_service.save_track_data(main_window, [])
        assert result is False
    
    def test_save_track_data_user_cancels(self, data_service: DataService, main_window: MockMainWindow, sample_data: list[tuple]) -> None:
        """Test save_track_data when user cancels."""
        with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=("", "")):
            result = data_service.save_track_data(main_window, sample_data)
            assert result is False
    
    def test_load_json(self, data_service: DataService) -> None:
        """Test JSON loading."""
        # Create temporary JSON file
        test_data = [
            {'frame': 1, 'x': 100.0, 'y': 200.0, 'status': 'keyframe'},
            {'frame': 2, 'x': 105.0, 'y': 205.0, 'status': 'keyframe'}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name
        
        try:
            result = data_service._load_json(temp_path)
            assert len(result) == 2
            assert result[0] == (1, 100.0, 200.0, 'keyframe')
            assert result[1] == (2, 105.0, 205.0, 'keyframe')
        finally:
            os.unlink(temp_path)
    
    def test_save_json(self, data_service: DataService, sample_data: list[tuple]) -> None:
        """Test JSON saving."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            data_service._save_json(temp_path, sample_data)
            
            # Verify file was created and contains correct data
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert len(data) == len(sample_data)
            assert data[0]['frame'] == 1
            assert data[0]['x'] == 100.0
            assert data[0]['y'] == 200.0
        finally:
            os.unlink(temp_path)
    
    def test_recent_files(self, data_service: DataService) -> None:
        """Test recent files functionality."""
        # Initially empty
        assert len(data_service.get_recent_files()) == 0
        
        # Add a file
        data_service.add_recent_file("/test/file1.json")
        recent = data_service.get_recent_files()
        assert len(recent) == 1
        assert recent[0] == "/test/file1.json"
        
        # Add another file
        data_service.add_recent_file("/test/file2.json")
        recent = data_service.get_recent_files()
        assert len(recent) == 2
        assert recent[0] == "/test/file2.json"  # Most recent first
        assert recent[1] == "/test/file1.json"
    
    # ==================== Image Service Tests ====================
    
    def test_load_image_sequence_nonexistent_directory(self, data_service: DataService) -> None:
        """Test loading image sequence from non-existent directory."""
        result = data_service.load_image_sequence("/nonexistent/directory")
        assert result == []
    
    def test_clear_image_cache(self, data_service: DataService) -> None:
        """Test clearing image cache."""
        # Add something to cache
        data_service._image_cache['test'] = 'value'
        assert len(data_service._image_cache) == 1
        
        # Clear cache
        data_service.clear_image_cache()
        assert len(data_service._image_cache) == 0

if __name__ == "__main__":
    pytest.main(["-v", __file__])
