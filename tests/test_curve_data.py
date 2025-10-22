"""Tests for metadata-aware curve data structures and coordinate detection."""

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

import pytest

from core.coordinate_detector import CoordinateDetector, get_system_info
from core.coordinate_system import CoordinateMetadata, CoordinateOrigin, CoordinateSystem
from core.curve_data import (
    CurveDataWithMetadata,
    create_metadata_from_file_type,
    ensure_metadata_aware,
    wrap_legacy_data,
)


class TestCurveDataWithMetadata:
    """Test the metadata-aware curve data structure."""

    def test_creation_with_metadata(self):
        """Test creating curve data with metadata."""
        data = [(1, 640.0, 360.0), (2, 650.0, 370.0)]
        metadata = CoordinateMetadata(
            system=CoordinateSystem.THREE_DE_EQUALIZER, origin=CoordinateOrigin.BOTTOM_LEFT, width=1280, height=720
        )

        curve_data = CurveDataWithMetadata(data=data, metadata=metadata)

        assert curve_data.is_metadata_aware
        assert curve_data.coordinate_system == CoordinateSystem.THREE_DE_EQUALIZER
        assert curve_data.needs_y_flip_for_display
        assert curve_data.frame_count == 2
        assert not curve_data.is_normalized

    def test_creation_without_metadata(self):
        """Test creating curve data without metadata."""
        data = [(1, 100.0, 200.0)]
        curve_data = CurveDataWithMetadata(data=data)

        assert not curve_data.is_metadata_aware
        assert curve_data.coordinate_system is None
        assert not curve_data.needs_y_flip_for_display
        assert curve_data.frame_count == 1

    def test_to_legacy_format(self):
        """Test conversion to legacy tuple format."""
        data = [(1, 640.0, 360.0), (2, 650.0, 370.0)]
        metadata = CoordinateMetadata(
            system=CoordinateSystem.QT_SCREEN, origin=CoordinateOrigin.TOP_LEFT, width=1920, height=1080
        )

        curve_data = CurveDataWithMetadata(data=data, metadata=metadata)
        legacy = curve_data.to_legacy_format()

        assert legacy == data
        assert isinstance(legacy, list)

    def test_normalization_from_3de(self):
        """Test normalizing 3DEqualizer data to internal format."""
        # 3DE data with bottom-left origin
        data = [(1, 640.0, 100.0)]  # Y=100 from bottom
        metadata = CoordinateMetadata(
            system=CoordinateSystem.THREE_DE_EQUALIZER, origin=CoordinateOrigin.BOTTOM_LEFT, width=1280, height=720
        )

        curve_data = CurveDataWithMetadata(data=data, metadata=metadata)
        normalized = curve_data.to_normalized()

        assert normalized.is_normalized
        assert normalized.coordinate_system == CoordinateSystem.CURVE_EDITOR_INTERNAL
        # Y should be flipped: 720 - 100 = 620
        assert normalized.data[0][2] == 620.0
        assert normalized.data[0][1] == 640.0  # X unchanged

    def test_normalization_from_qt(self):
        """Test normalizing Qt data (already normalized)."""
        data = [(1, 640.0, 360.0)]
        metadata = CoordinateMetadata(
            system=CoordinateSystem.QT_SCREEN, origin=CoordinateOrigin.TOP_LEFT, width=1920, height=1080
        )

        curve_data = CurveDataWithMetadata(data=data, metadata=metadata)
        normalized = curve_data.to_normalized()

        assert normalized.is_normalized
        # Data should be unchanged since Qt is already top-left
        assert normalized.data[0] == data[0]

    def test_denormalization_to_3de(self):
        """Test converting normalized data back to 3DE format."""
        # Normalized data (top-left origin)
        data = [(1, 640.0, 620.0)]  # Y=620 from top
        metadata = CoordinateMetadata(
            system=CoordinateSystem.CURVE_EDITOR_INTERNAL, origin=CoordinateOrigin.TOP_LEFT, width=1280, height=720
        )

        normalized = CurveDataWithMetadata(data=data, metadata=metadata, is_normalized=True)

        # Convert to 3DE format
        target_metadata = CoordinateMetadata(
            system=CoordinateSystem.THREE_DE_EQUALIZER, origin=CoordinateOrigin.BOTTOM_LEFT, width=1280, height=720
        )

        converted = normalized.from_normalized(target_metadata)

        assert not converted.is_normalized
        assert converted.coordinate_system == CoordinateSystem.THREE_DE_EQUALIZER
        # Y should be flipped back: 720 - 620 = 100
        assert converted.data[0][2] == 100.0
        assert converted.data[0][1] == 640.0  # X unchanged

    def test_round_trip_conversion(self):
        """Test that data survives normalization and denormalization."""
        # Original 3DE data
        original_data = [(1, 640.0, 100.0), (2, 650.0, 200.0), (3, 660.0, 300.0)]
        metadata = CoordinateMetadata(
            system=CoordinateSystem.THREE_DE_EQUALIZER, origin=CoordinateOrigin.BOTTOM_LEFT, width=1280, height=720
        )

        curve_data = CurveDataWithMetadata(data=original_data, metadata=metadata)

        # Normalize then denormalize
        normalized = curve_data.to_normalized()
        restored = normalized.from_normalized(metadata)

        # Should match original
        for i, (orig, rest) in enumerate(zip(original_data, restored.data)):
            assert orig[0] == rest[0], f"Frame mismatch at index {i}"
            assert abs(orig[1] - rest[1]) < 0.001, f"X mismatch at index {i}"
            assert abs(orig[2] - rest[2]) < 0.001, f"Y mismatch at index {i}"

    def test_preserve_extra_fields(self):
        """Test that extra fields (like status) are preserved."""
        data = [(1, 640.0, 360.0, "keyframe"), (2, 650.0, 370.0, "interpolated")]
        metadata = CoordinateMetadata(
            system=CoordinateSystem.THREE_DE_EQUALIZER, origin=CoordinateOrigin.BOTTOM_LEFT, width=1280, height=720
        )

        curve_data = CurveDataWithMetadata(data=data, metadata=metadata)
        normalized = curve_data.to_normalized()

        # Extra fields should be preserved
        assert len(normalized.data[0]) == 4
        # Safe access for PointTuple4
        point0 = normalized.data[0]
        point1 = normalized.data[1]
        if len(point0) == 4:
            assert point0[3] == "keyframe"
        if len(point1) == 4:
            assert point1[3] == "interpolated"

    def test_get_bounds(self):
        """Test getting bounding box of curve data."""
        data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 120.0, 180.0)]
        curve_data = CurveDataWithMetadata(data=data)

        min_x, min_y, max_x, max_y = curve_data.get_bounds()

        assert min_x == 100.0
        assert max_x == 150.0
        assert min_y == 180.0
        assert max_y == 250.0

    def test_get_point_at_frame(self):
        """Test retrieving point at specific frame."""
        data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 120.0, 180.0)]
        curve_data = CurveDataWithMetadata(data=data)

        point = curve_data.get_point_at_frame(2)
        assert point == (2, 150.0, 250.0)

        point = curve_data.get_point_at_frame(99)
        assert point is None


class TestCoordinateDetector:
    """Test automatic coordinate system detection."""

    def test_detect_3de_from_filename(self):
        """Test detecting 3DEqualizer from filename."""
        paths = ["data_2dtrack.txt", "tracking_3de.txt", "shot001_3DEqualizer.2dt", "track.3de"]

        for path in paths:
            # Since files don't exist, provide empty content to trigger filename detection
            metadata = CoordinateDetector.detect_from_file(path, "")
            assert metadata.system == CoordinateSystem.THREE_DE_EQUALIZER, f"Failed for {path}"
            assert metadata.origin == CoordinateOrigin.BOTTOM_LEFT

    def test_detect_from_extension(self):
        """Test detection from file extensions."""
        test_cases = [
            ("file.nk", CoordinateSystem.NUKE),
            ("file.ma", CoordinateSystem.MAYA),
            ("file.mb", CoordinateSystem.MAYA),
            ("file.txt", None),  # Unknown without content
            ("file.json", None),
        ]

        for path, expected in test_cases:
            system = CoordinateDetector._detect_system_from_extension(path)
            assert system == expected

    def test_detect_3de_from_content(self):
        """Test detecting 3DE from file content."""
        content = """# 3DEqualizer tracking data
        # IMAGE 1280x720
        1 640.5 360.2
        2 641.0 359.8
        3 641.5 359.5
        """

        metadata = CoordinateDetector.detect_from_file("unknown.txt", content)
        assert metadata.system == CoordinateSystem.THREE_DE_EQUALIZER
        assert metadata.width == 1280
        assert metadata.height == 720

    def test_extract_dimensions(self):
        """Test extracting dimensions from content."""
        test_cases = [
            ("IMAGE 1920x1080", (1920, 1080)),
            ("RESOLUTION: 1280 x 720", (1280, 720)),
            ("WIDTH: 2560 HEIGHT: 1440", (2560, 1440)),
            ("Size 3840,2160", (3840, 2160)),
        ]

        for content, expected in test_cases:
            width, height = CoordinateDetector._extract_dimensions(content)
            assert (width, height) == expected

    def test_infer_dimensions_from_data(self):
        """Test inferring dimensions from coordinate range."""
        content = """1 640.0 360.0
        2 1200.0 700.0
        3 100.0 50.0
        4 1250.0 710.0
        """

        result = CoordinateDetector._infer_dimensions_from_data(content)
        assert result is not None
        width, height = result
        assert width == 1280
        assert height == 720

    def test_looks_like_3de_data(self):
        """Test recognition of 3DE data format."""
        # Valid 3DE data
        content = """1 640.0 360.0
        2 641.0 361.0
        3 642.0 362.0
        4 643.0 363.0
        """
        assert CoordinateDetector._looks_like_3de_data(content)

        # Not 3DE data (frames don't start at 1)
        content = """100 640.0 360.0
        101 641.0 361.0
        102 642.0 362.0
        """
        assert not CoordinateDetector._looks_like_3de_data(content)


class TestHelperFunctions:
    """Test helper functions for metadata handling."""

    def test_create_metadata_from_file_type(self):
        """Test metadata creation from file type."""
        test_cases = [
            ("data_2dtrack.txt", CoordinateSystem.THREE_DE_EQUALIZER, CoordinateOrigin.BOTTOM_LEFT),
            ("shot.nuke", CoordinateSystem.NUKE, CoordinateOrigin.BOTTOM_LEFT),
            ("anim.maya", CoordinateSystem.MAYA, CoordinateOrigin.CENTER),
            ("unknown.dat", CoordinateSystem.QT_SCREEN, CoordinateOrigin.TOP_LEFT),
        ]

        for path, expected_system, expected_origin in test_cases:
            metadata = create_metadata_from_file_type(path)
            assert metadata.system == expected_system
            assert metadata.origin == expected_origin

    def test_wrap_legacy_data(self):
        """Test wrapping legacy data with metadata."""
        data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]

        # With file path for auto-detection
        wrapped = wrap_legacy_data(data, "track_3de.txt")
        assert wrapped.is_metadata_aware
        assert wrapped.coordinate_system == CoordinateSystem.THREE_DE_EQUALIZER
        assert wrapped.data == data

        # Without file path (defaults to Qt)
        wrapped = wrap_legacy_data(data)
        assert wrapped.coordinate_system == CoordinateSystem.QT_SCREEN

    def test_ensure_metadata_aware(self):
        """Test ensuring data is metadata-aware."""
        # Already metadata-aware
        data = [(1, 100.0, 200.0)]
        metadata = CoordinateMetadata(
            system=CoordinateSystem.NUKE, origin=CoordinateOrigin.BOTTOM_LEFT, width=1920, height=1080
        )
        curve_data = CurveDataWithMetadata(data=data, metadata=metadata)

        result = ensure_metadata_aware(curve_data)
        assert result is curve_data  # Should return same instance

        # Legacy data
        legacy_data = [(1, 100.0, 200.0)]
        result = ensure_metadata_aware(legacy_data, "test_3de.txt")
        assert isinstance(result, CurveDataWithMetadata)
        assert result.coordinate_system == CoordinateSystem.THREE_DE_EQUALIZER

    def test_get_system_info(self):
        """Test getting system information."""
        info = get_system_info(CoordinateSystem.THREE_DE_EQUALIZER)

        assert info["origin"] == CoordinateOrigin.BOTTOM_LEFT
        # Type narrow before using "in" operator
        description = info["description"]
        assert isinstance(description, str) and "3DEqualizer" in description
        file_extensions = info["file_extensions"]
        assert isinstance(file_extensions, list) and ".3de" in file_extensions
        assert info["default_dimensions"] == (1280, 720)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_data_format(self):
        """Test handling of invalid data format."""
        with pytest.raises(ValueError, match="Invalid curve data format"):
            CurveDataWithMetadata(data=[(1, 100)])  # Testing invalid data

    def test_empty_data(self):
        """Test handling of empty data."""
        curve_data = CurveDataWithMetadata(data=[])

        assert curve_data.frame_count == 0
        assert curve_data.get_bounds() == (0.0, 0.0, 0.0, 0.0)
        assert curve_data.get_point_at_frame(1) is None

    def test_denormalize_without_normalizing(self):
        """Test that denormalizing non-normalized data raises error."""
        data = [(1, 100.0, 200.0)]
        metadata = CoordinateMetadata(
            system=CoordinateSystem.THREE_DE_EQUALIZER, origin=CoordinateOrigin.BOTTOM_LEFT, width=1280, height=720
        )

        curve_data = CurveDataWithMetadata(data=data, metadata=metadata)

        with pytest.raises(ValueError, match="must be normalized"):
            curve_data.from_normalized(metadata)

    def test_dimension_sanity_checks(self):
        """Test that detector applies sanity checks to dimensions."""
        # Unrealistic dimensions should be rejected
        content = "IMAGE 99999x99999"
        width, height = CoordinateDetector._extract_dimensions(content)
        assert width is None
        assert height is None

        # Reasonable dimensions should be accepted
        content = "IMAGE 1920x1080"
        width, height = CoordinateDetector._extract_dimensions(content)
        assert width == 1920
        assert height == 1080
