#!/usr/bin/env python3
"""
Tests for the FileService module.

This test suite verifies the functionality of the FileService class,
which handles file operations such as loading, saving, and exporting track data.
"""

import os
import sys
import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.file_service import FileService
from services.protocols import PointsList


class MockMainWindow:
    """Mock implementation of MainWindowProtocol for testing."""
    
    def __init__(self) -> None:
        self.curve_data: PointsList = []
        self.image_width: int = 1920
        self.image_height: int = 1080
        self.default_directory: str = os.path.expanduser("~")
        self.qwidget = MagicMock()
        self.history_added = False
    
    def add_to_history(self) -> None:
        """Mock implementation of add_to_history."""
        self.history_added = True


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


class TestFileService:
    """Test suite for FileService class."""

    def test_get_config_value_with_missing_module(self) -> None:
        """Test get_config_value when config module is missing."""
        # Save original module reference
        with patch('services.file_service.config_module', None):
            # Test with default value
            result = FileService.get_config_value("some_attr", "default_value")
            assert result == "default_value"
            
            # Test without default value
            result = FileService.get_config_value("some_attr")
            assert result is None

    def test_set_config_value_with_missing_module(self) -> None:
        """Test set_config_value when config module is missing."""
        with patch('services.file_service.config_module', None):
            # Should not raise an exception
            FileService.set_config_value("some_attr", "some_value")

    def test_fallback_estimate_image_dimensions(self) -> None:
        """Test the fallback image dimension estimation."""
        # Test with empty data
        empty_data: PointsList = []
        width, height = FileService._fallback_estimate_image_dimensions(empty_data)
        assert width == 1920
        assert height == 1080
        
        # Test with actual data
        curve_data: PointsList = [
            (1, 500.0, 300.0, 0.9),
            (2, 600.0, 400.0, 0.8),
            (3, 100.0, 100.0, 0.7),
        ]
        width, height = FileService._fallback_estimate_image_dimensions(curve_data)
        # Max X value is 600, with padding it should be larger
        assert width >= 600
        # Max Y value is 400, with padding it should be larger
        assert height >= 400

    # CSV export tests have been removed as the functionality is no longer needed

    def test_load_track_data_user_cancels(self, main_window: MockMainWindow) -> None:
        """Test load_track_data when user cancels the file dialog."""
        with patch('services.file_service.QFileDialog.getOpenFileName', return_value=("", "")):
            FileService.load_track_data(main_window)
            # Just verify it returns without exceptions

    def test_fallback_load_3de_track_invalid_file(self) -> None:
        """Test the fallback 3DE track loader with an invalid file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b"This is not a valid track file")
            temp_path = temp_file.name
        
        try:
            result = FileService._fallback_load_3de_track(temp_path)
            assert result is None
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_fallback_load_3de_track_valid_file(self) -> None:
        """Test the fallback 3DE track loader with a valid-format file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', prefix='test_track_', delete=False) as temp_file:
            # Create a simplified valid 3DE track format
            temp_file.write(b"1 100.0 200.0 0.9\n")
            temp_file.write(b"2 105.0 205.0 0.8\n")
            temp_file.write(b"3 110.0 210.0 0.95\n")
            temp_path = temp_file.name
        
        try:
            result = FileService._fallback_load_3de_track(temp_path)
            assert result is not None
            
            point_name, point_color, num_frames, curve_data = result
            
            # The point name is derived from the file name
            file_basename = os.path.basename(temp_path)
            expected_name = os.path.splitext(file_basename)[0]
            assert point_name == expected_name
            
            # Default color is "#FF0000"
            assert point_color == "#FF0000"
            assert num_frames == 3
            assert len(curve_data) == 3
            assert curve_data[0] == (1, 100.0, 200.0, "0.9")
            assert curve_data[1] == (2, 105.0, 205.0, "0.8")
            assert curve_data[2] == (3, 110.0, 210.0, "0.95")
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_add_track_data_no_current_data(self, main_window: MockMainWindow) -> None:
        """Test add_track_data when no current curve data exists."""
        main_window.curve_data = []
        FileService.add_track_data(main_window)
        # Just verify it returns without exceptions

    def test_add_track_data_user_cancels(self, main_window: MockMainWindow, sample_curve_data: PointsList) -> None:
        """Test add_track_data when user cancels the file dialog."""
        main_window.curve_data = sample_curve_data
        
        with patch('services.file_service.QFileDialog.getOpenFileName', return_value=("", "")):
            FileService.add_track_data(main_window)
            # Just verify it doesn't raise exceptions

    def test_call_utils_unknown_module(self) -> None:
        """Test call_utils with an unknown module."""
        result = FileService.call_utils("unknown_module", "some_function")
        assert result is None

    def test_safe_call_module_none(self) -> None:
        """Test safe_call when module is None."""
        from services.file_service import safe_call
        result = safe_call(None, "some_function")
        assert result is None

    def test_safe_call_attr_not_found(self) -> None:
        """Test safe_call when the attribute is not found."""
        from services.file_service import safe_call
        
        # Create a mock module
        mock_module = MagicMock()
        delattr(mock_module, "non_existent_function")
        
        result = safe_call(mock_module, "non_existent_function")
        assert result is None

    def test_safe_call_exception(self) -> None:
        """Test safe_call when the function raises an exception."""
        from services.file_service import safe_call
        
        # Create a mock module with a function that raises an exception
        mock_module = MagicMock()
        mock_module.problematic_function = MagicMock(side_effect=Exception("Test exception"))
        
        result = safe_call(mock_module, "problematic_function")
        assert result is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
