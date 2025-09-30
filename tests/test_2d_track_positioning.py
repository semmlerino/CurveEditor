#!/usr/bin/env python3
"""
Tests for 2D track data positioning fix.

Following UNIFIED_TESTING_GUIDE principles:
- Test behavior, not implementation
- Real components over mocks
- Mock only at system boundaries
"""

from unittest.mock import Mock

import pytest

from core.coordinate_detector import CoordinateDetector
from core.coordinate_system import CoordinateOrigin, CoordinateSystem
from core.curve_data import CurveDataWithMetadata, wrap_legacy_data
from services.data_service import DataService


# Test Fixtures
@pytest.fixture
def sample_3de_content():
    """Sample 3DEqualizer format content from Point01_only.txt."""
    return """1
Point1
0
37
1 682.291351786175937 211.331718165415879
2 682.545189161841108 212.540183990857656
3 682.713305139502836 214.057309384797804
4 683.064889159724544 215.828024768162948
5 683.318386159606803 217.806226221166156
"""


@pytest.fixture
def sample_non_3de_content():
    """Sample non-3DEqualizer format content."""
    return """frame,x,y
1,100.5,200.3
2,101.2,201.5
3,102.0,202.8
"""


@pytest.fixture
def temp_3de_file(tmp_path, sample_3de_content):
    """Create a temporary 3DE format file."""
    file_path = tmp_path / "test_tracking.txt"
    file_path.write_text(sample_3de_content)
    return str(file_path)


@pytest.fixture
def temp_non_3de_file(tmp_path, sample_non_3de_content):
    """Create a temporary non-3DE format file."""
    file_path = tmp_path / "test_data.csv"
    file_path.write_text(sample_non_3de_content)
    return str(file_path)


@pytest.fixture
def real_data_service():
    """Real DataService instance for integration testing."""
    return DataService()


# Unit Tests for CoordinateDetector
class TestCoordinateDetector:
    """Test coordinate detection improvements."""

    def test_detects_3de_structure_from_content(self, sample_3de_content):
        """Test that 3DE structure is detected from file content."""
        # Test behavior: detection of 3DE format
        result = CoordinateDetector._has_3de_structure(sample_3de_content)

        assert result is True, "Should detect 3DEqualizer structure"

    def test_detects_3de_from_file_without_2dtrack_in_name(self, sample_3de_content):
        """Test detection of 3DE format even without '2dtrack' in filename."""
        # Test the complete detection flow
        metadata = CoordinateDetector.detect_from_file(
            "Point01_only.txt",  # No '2dtrack' in name
            sample_3de_content,
        )

        assert metadata.system == CoordinateSystem.THREE_DE_EQUALIZER
        assert metadata.origin == CoordinateOrigin.BOTTOM_LEFT
        assert metadata.needs_y_flip_for_qt is True

    def test_does_not_detect_3de_for_non_3de_content(self, sample_non_3de_content):
        """Test that non-3DE content is not misidentified."""
        result = CoordinateDetector._has_3de_structure(sample_non_3de_content)

        assert result is False, "Should not detect 3DE structure in CSV"

    def test_3de_structure_validation_edge_cases(self):
        """Test edge cases in 3DE structure detection."""
        # Too few lines
        assert CoordinateDetector._has_3de_structure("1\nPoint1") is False

        # Invalid version number
        assert CoordinateDetector._has_3de_structure("999999\nPoint1\n0\n37\n1 100 200") is False

        # Invalid frame count
        assert CoordinateDetector._has_3de_structure("1\nPoint1\n0\n-5\n1 100 200") is False

        # Valid minimal case
        valid_minimal = "1\nPoint1\n0\n1\n1 100.5 200.3"
        assert CoordinateDetector._has_3de_structure(valid_minimal) is True

    def test_filename_detection_fallback(self):
        """Test that filename detection still works as fallback."""
        # With 2dtrack in filename
        metadata = CoordinateDetector.detect_from_file(
            "test_2dtrack.txt",
            None,  # No content provided
        )
        assert metadata.system == CoordinateSystem.THREE_DE_EQUALIZER

        # With 3de in filename
        metadata = CoordinateDetector.detect_from_file("data_3de_export.txt", None)
        assert metadata.system == CoordinateSystem.THREE_DE_EQUALIZER


# Integration Tests for DataService
class TestDataServiceMetadataFlow:
    """Test metadata flow through DataService."""

    def test_load_2dtrack_returns_metadata_aware_data(self, real_data_service, temp_3de_file):
        """Test that _load_2dtrack_data returns CurveDataWithMetadata."""
        # Use real DataService to test actual behavior
        result = real_data_service._file_io_service._load_2dtrack_data(temp_3de_file)

        # Verify it returns metadata-aware data
        assert isinstance(result, CurveDataWithMetadata)
        assert result.metadata is not None
        assert result.coordinate_system == CoordinateSystem.THREE_DE_EQUALIZER
        assert result.needs_y_flip_for_display is True

    def test_empty_file_returns_metadata_aware_empty_data(self, real_data_service, tmp_path):
        """Test that empty/missing files still return metadata-aware data."""
        missing_file = str(tmp_path / "nonexistent.txt")

        result = real_data_service._file_io_service._load_2dtrack_data(missing_file)

        assert isinstance(result, CurveDataWithMetadata)
        assert result.frame_count == 0
        assert result.metadata is not None

    def test_data_coordinates_preserved(self, real_data_service, temp_3de_file):
        """Test that original coordinates are preserved in the data."""
        result = real_data_service._file_io_service._load_2dtrack_data(temp_3de_file)

        # Check first point coordinates match original
        if result.data:
            first_point = result.data[0]
            assert first_point[0] == 1  # frame
            assert abs(first_point[1] - 682.291351786175937) < 0.0001  # x
            assert abs(first_point[2] - 211.331718165415879) < 0.0001  # y

    def test_metadata_dimensions_set_correctly(self, real_data_service, temp_3de_file):
        """Test that coordinate dimensions are set from metadata."""
        result = real_data_service._file_io_service._load_2dtrack_data(temp_3de_file)

        assert result.metadata.width == 1280  # 3DE default
        assert result.metadata.height == 720  # 3DE default


# Tests for wrap_legacy_data improvements
class TestWrapLegacyData:
    """Test the enhanced wrap_legacy_data function."""

    def test_wrap_legacy_data_uses_advanced_detection(self, temp_3de_file):
        """Test that wrap_legacy_data uses content-based detection."""
        legacy_data = [
            (1, 682.29, 211.33),
            (2, 682.55, 212.54),
        ]

        # Wrap with file path for detection
        result = wrap_legacy_data(legacy_data, temp_3de_file)

        assert isinstance(result, CurveDataWithMetadata)
        assert result.coordinate_system == CoordinateSystem.THREE_DE_EQUALIZER
        assert result.needs_y_flip_for_display is True

    def test_wrap_legacy_data_without_file_path(self):
        """Test default behavior when no file path is provided."""
        legacy_data = [(1, 100, 200)]

        result = wrap_legacy_data(legacy_data)

        assert isinstance(result, CurveDataWithMetadata)
        assert result.coordinate_system == CoordinateSystem.QT_SCREEN
        assert result.needs_y_flip_for_display is False

    def test_dimension_override(self, temp_3de_file):
        """Test that provided dimensions override detected ones."""
        legacy_data = [(1, 100, 200)]

        result = wrap_legacy_data(legacy_data, temp_3de_file, width=1920, height=1080)

        assert result.metadata.width == 1920
        assert result.metadata.height == 1080
        # But system should still be detected as 3DE
        assert result.coordinate_system == CoordinateSystem.THREE_DE_EQUALIZER


# Integration test for full pipeline
class TestFullPipeline:
    """Test the complete flow from file to display coordinates."""

    def test_3de_data_flows_with_correct_metadata(self, real_data_service, temp_3de_file):
        """Test that 3DE data maintains metadata through the pipeline."""
        # Load data through DataService
        data = real_data_service._load_2dtrack_data(temp_3de_file)

        # Verify metadata at each stage
        assert data.coordinate_system == CoordinateSystem.THREE_DE_EQUALIZER
        assert data.metadata.needs_y_flip_for_qt is True

        # Simulate what CurveViewWidget would do
        legacy_format = data.to_legacy_format()
        assert len(legacy_format) == 5  # We have 5 points in sample

        # The metadata should indicate Y-flip is needed
        if data.needs_y_flip_for_display:
            # Widget would apply Y-flip using metadata.height
            test_y = data.data[0][2]  # Original Y
            flipped_y = data.metadata.height - test_y
            assert flipped_y == pytest.approx(720 - 211.331718165415879, rel=1e-4)


# Test doubles for UI components (following guide principles)
class TestCurveViewWidget:
    """Test curve view widget metadata handling."""

    @pytest.fixture
    def mock_curve_widget(self):
        """Create a test double for CurveViewWidget."""
        widget = Mock()
        widget.curve_data = []
        widget.coord_width = 1280
        widget.coord_height = 720
        widget._data_metadata = None
        widget.flip_y_axis = False

        # Add the set_curve_data behavior
        def set_curve_data(data):
            if isinstance(data, CurveDataWithMetadata):
                widget._data_metadata = data.metadata
                widget.curve_data = data.to_legacy_format()
                if data.metadata:
                    widget.coord_width = data.metadata.width
                    widget.coord_height = data.metadata.height
                    widget.flip_y_axis = data.needs_y_flip_for_display
            else:
                widget.curve_data = data
                widget._data_metadata = None

        widget.set_curve_data = set_curve_data
        return widget

    def test_widget_handles_metadata_aware_data(self, mock_curve_widget, real_data_service, temp_3de_file):
        """Test that widget correctly processes metadata-aware data."""
        # Load data with metadata
        data = real_data_service._load_2dtrack_data(temp_3de_file)

        # Set on widget
        mock_curve_widget.set_curve_data(data)

        # Verify widget state
        assert mock_curve_widget._data_metadata is not None
        assert mock_curve_widget.coord_width == 1280
        assert mock_curve_widget.coord_height == 720
        assert mock_curve_widget.flip_y_axis is True
        assert len(mock_curve_widget.curve_data) == 5

    def test_widget_handles_legacy_data(self, mock_curve_widget):
        """Test backward compatibility with legacy data."""
        legacy_data = [(1, 100, 200), (2, 101, 201)]

        mock_curve_widget.set_curve_data(legacy_data)

        assert mock_curve_widget._data_metadata is None
        assert mock_curve_widget.curve_data == legacy_data
        assert mock_curve_widget.flip_y_axis is False


# Performance test (following guide's resource management principles)
class TestPerformance:
    """Test performance characteristics of the fix."""

    def test_metadata_detection_performance(self, sample_3de_content):
        """Test that detection is fast enough for interactive use."""
        import time

        start = time.perf_counter()
        for _ in range(100):
            CoordinateDetector._has_3de_structure(sample_3de_content)
        elapsed = time.perf_counter() - start

        # Should complete 100 detections in under 100ms
        assert elapsed < 0.1, f"Detection too slow: {elapsed:.3f}s for 100 iterations"

    def test_memory_efficiency(self, real_data_service, tmp_path):
        """Test that metadata doesn't significantly increase memory usage."""
        import sys

        # Create a larger test file with more realistic data
        large_content = "1\nPoint1\n0\n1000\n"
        for i in range(1, 1001):
            large_content += f"{i} {682.0 + i*0.1} {211.0 + i*0.2}\n"

        large_file = tmp_path / "large_test.txt"
        large_file.write_text(large_content)

        # Load data
        data = real_data_service._load_2dtrack_data(str(large_file))

        # Check memory footprint
        data_size = sys.getsizeof(data.data)
        metadata_size = sys.getsizeof(data.metadata) if data.metadata else 0

        # For realistic data sizes, metadata should be small compared to data
        # Metadata is fixed size, data grows with points
        assert metadata_size < data_size * 0.05, f"Metadata ({metadata_size}B) too large vs data ({data_size}B)"

        # Also verify metadata is reasonable absolute size
        assert metadata_size < 1000, f"Metadata size {metadata_size} bytes is too large"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
