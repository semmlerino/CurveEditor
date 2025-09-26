#!/usr/bin/env python3
"""
Comprehensive tests for core data models.

This module provides complete test coverage for the unified point data models
in core/models.py and core/image_state.py, following TDD principles.

Test Coverage:
- Point Model Tests: Creation, validation, serialization
- Point Property Tests: Frame, coordinates, status handling
- PointCollection Tests: List operations, data integrity
- ImageState Tests: State management, transitions
- Property-Based Testing: Invariant validation with Hypothesis
- Edge Cases: Error conditions, boundary values
- Performance Tests: Bulk operations optimization

Testing Strategy:
- RED-GREEN-REFACTOR TDD cycle
- Comprehensive coverage with edge cases
- Type-safe test implementations
- Mock-free testing for data models
- Property-based testing for robustness
"""

import json
import math
import os
import tempfile
from typing import Any, cast
from unittest.mock import Mock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Import core models under test
from core.image_state import ImageDisplayInfo, ImageLoadingState, ImageSequenceInfo, ImageState
from core.models import (
    CurvePoint,
    PointCollection,
    PointStatus,
    bulk_convert_from_tuples,
    bulk_convert_to_tuples,
    convert_to_curve_collection,
    convert_to_curve_point,
    is_point_tuple,
    is_points_list,
    normalize_legacy_point,
)

# For Qt mocking in image state tests
try:
    from tests.qt_test_helpers import ThreadSafeTestImage as QTThreadSafeTestImage

    # Create local alias to avoid type conflicts
    ThreadSafeTestImage = QTThreadSafeTestImage  # pyright: ignore[reportAssignmentType]
except ImportError:
    # Create a mock ThreadSafeTestImage for testing when dependencies are not available
    class ThreadSafeTestImage:
        def __init__(self, width: int = 100, height: int = 100) -> None:
            self._null: bool = width == 0 and height == 0
            self._width: int = width
            self._height: int = height

        def isNull(self) -> bool:
            return self._null

        def width(self) -> int:
            return self._width

        def height(self) -> int:
            return self._height


class TestPointStatus:
    """Comprehensive tests for PointStatus enum."""

    def test_enum_values(self) -> None:
        """Test that enum has correct string values."""
        assert PointStatus.NORMAL.value == "normal"
        assert PointStatus.INTERPOLATED.value == "interpolated"
        assert PointStatus.KEYFRAME.value == "keyframe"

    def test_from_legacy_none(self) -> None:
        """Test conversion from None value."""
        result = PointStatus.from_legacy(None)
        assert result == PointStatus.NORMAL

    def test_from_legacy_bool_true(self) -> None:
        """Test conversion from boolean True."""
        result = PointStatus.from_legacy(True)
        assert result == PointStatus.INTERPOLATED

    def test_from_legacy_bool_false(self) -> None:
        """Test conversion from boolean False."""
        result = PointStatus.from_legacy(False)
        assert result == PointStatus.NORMAL

    def test_from_legacy_valid_strings(self) -> None:
        """Test conversion from valid string values."""
        assert PointStatus.from_legacy("normal") == PointStatus.NORMAL
        assert PointStatus.from_legacy("interpolated") == PointStatus.INTERPOLATED
        assert PointStatus.from_legacy("keyframe") == PointStatus.KEYFRAME

    def test_from_legacy_invalid_string(self) -> None:
        """Test conversion from invalid string falls back to NORMAL."""
        result = PointStatus.from_legacy("invalid_status")
        assert result == PointStatus.NORMAL

    def test_from_legacy_invalid_type(self) -> None:
        """Test conversion from invalid types falls back to NORMAL."""
        assert PointStatus.from_legacy(123) == PointStatus.NORMAL  # pyright: ignore[reportArgumentType]
        assert PointStatus.from_legacy([]) == PointStatus.NORMAL  # pyright: ignore[reportArgumentType]
        assert PointStatus.from_legacy({}) == PointStatus.NORMAL  # pyright: ignore[reportArgumentType]

    def test_to_legacy_string(self) -> None:
        """Test conversion to legacy string format."""
        assert PointStatus.NORMAL.to_legacy_string() == "normal"
        assert PointStatus.INTERPOLATED.to_legacy_string() == "interpolated"
        assert PointStatus.KEYFRAME.to_legacy_string() == "keyframe"

    def test_to_legacy_bool(self) -> None:
        """Test conversion to legacy boolean format."""
        assert PointStatus.NORMAL.to_legacy_bool() is False
        assert PointStatus.INTERPOLATED.to_legacy_bool() is True
        assert PointStatus.KEYFRAME.to_legacy_bool() is False


class TestCurvePoint:
    """Comprehensive tests for CurvePoint data model."""

    # === Creation and Validation Tests ===

    def test_point_creation_minimal(self) -> None:
        """Test creating point with minimal required parameters."""
        point = CurvePoint(100, 1920.0, 1080.0)
        assert point.frame == 100
        assert point.x == 1920.0
        assert point.y == 1080.0
        assert point.status == PointStatus.NORMAL

    def test_point_creation_with_status(self) -> None:
        """Test creating point with explicit status."""
        point = CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED)
        assert point.frame == 101
        assert point.x == 1921.0
        assert point.y == 1081.0
        assert point.status == PointStatus.INTERPOLATED

    def test_point_creation_integer_coordinates(self) -> None:
        """Test point creation accepts integer coordinates."""
        point = CurvePoint(100, 1920, 1080)
        assert point.frame == 100
        assert point.x == 1920
        assert point.y == 1080
        assert isinstance(point.x, int)  # Preserved as int
        assert isinstance(point.y, int)

    def test_point_validation_frame_type(self) -> None:
        """Test frame validation rejects non-integer types."""
        with pytest.raises(TypeError, match="Frame must be int"):
            _ = CurvePoint(100.5, 1920.0, 1080.0)  # pyright: ignore[reportArgumentType]

        with pytest.raises(TypeError, match="Frame must be int"):
            _ = CurvePoint("100", 1920.0, 1080.0)  # pyright: ignore[reportArgumentType]

    def test_point_validation_coordinate_types(self) -> None:
        """Test coordinate validation rejects non-numeric types."""
        with pytest.raises(TypeError, match="X coordinate must be numeric"):
            _ = CurvePoint(100, "1920", 1080.0)  # pyright: ignore[reportArgumentType]

        with pytest.raises(TypeError, match="Y coordinate must be numeric"):
            _ = CurvePoint(100, 1920.0, "1080")  # pyright: ignore[reportArgumentType]

        with pytest.raises(TypeError, match="X coordinate must be numeric"):
            _ = CurvePoint(100, None, 1080.0)  # pyright: ignore[reportArgumentType]

    def test_point_validation_status_type(self) -> None:
        """Test status validation rejects non-PointStatus types."""
        with pytest.raises(TypeError, match="Status must be PointStatus enum"):
            _ = CurvePoint(100, 1920.0, 1080.0, "invalid")  # pyright: ignore[reportArgumentType]

        with pytest.raises(TypeError, match="Status must be PointStatus enum"):
            _ = CurvePoint(100, 1920.0, 1080.0, True)  # pyright: ignore[reportArgumentType]

    # === Immutability Tests ===

    def test_point_immutability(self) -> None:
        """Test that CurvePoint is immutable (frozen dataclass)."""
        point = CurvePoint(100, 1920.0, 1080.0)

        with pytest.raises(AttributeError):
            point.frame = 101  # pyright: ignore[reportAttributeAccessIssue]

        with pytest.raises(AttributeError):
            point.x = 1921.0  # pyright: ignore[reportAttributeAccessIssue]

        with pytest.raises(AttributeError):
            point.status = PointStatus.INTERPOLATED  # pyright: ignore[reportAttributeAccessIssue]

    # === Property Tests ===

    def test_is_interpolated_property(self) -> None:
        """Test is_interpolated property."""
        normal_point = CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL)
        interp_point = CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED)
        keyframe_point = CurvePoint(102, 1922.0, 1082.0, PointStatus.KEYFRAME)

        assert not normal_point.is_interpolated
        assert interp_point.is_interpolated
        assert not keyframe_point.is_interpolated

    def test_is_keyframe_property(self) -> None:
        """Test is_keyframe property."""
        normal_point = CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL)
        interp_point = CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED)
        keyframe_point = CurvePoint(102, 1922.0, 1082.0, PointStatus.KEYFRAME)

        assert normal_point.is_keyframe
        assert not interp_point.is_keyframe
        assert keyframe_point.is_keyframe

    def test_coordinates_property(self) -> None:
        """Test coordinates property returns (x, y) tuple."""
        point = CurvePoint(100, 1920.0, 1080.0)
        coords = point.coordinates
        assert coords == (1920.0, 1080.0)
        assert isinstance(coords, tuple)

    # === Distance Calculation Tests ===

    def test_distance_to_same_point(self) -> None:
        """Test distance to identical point is zero."""
        point1 = CurvePoint(100, 1920.0, 1080.0)
        point2 = CurvePoint(100, 1920.0, 1080.0)
        assert point1.distance_to(point2) == 0.0

    def test_distance_to_different_point(self) -> None:
        """Test distance calculation between different points."""
        point1 = CurvePoint(100, 0.0, 0.0)
        point2 = CurvePoint(101, 3.0, 4.0)
        distance = point1.distance_to(point2)
        assert distance == 5.0  # 3-4-5 right triangle

    def test_distance_calculation_accuracy(self) -> None:
        """Test distance calculation with floating point coordinates."""
        point1 = CurvePoint(100, 1.5, 2.5)
        point2 = CurvePoint(101, 4.5, 6.5)
        expected = math.sqrt((4.5 - 1.5) ** 2 + (6.5 - 2.5) ** 2)
        assert abs(point1.distance_to(point2) - expected) < 1e-10

    # === Immutable Update Tests ===

    def test_with_status(self) -> None:
        """Test creating new point with different status."""
        original = CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL)
        updated = original.with_status(PointStatus.INTERPOLATED)

        assert updated.frame == original.frame
        assert updated.x == original.x
        assert updated.y == original.y
        assert updated.status == PointStatus.INTERPOLATED
        assert original.status == PointStatus.NORMAL  # Original unchanged

    def test_with_coordinates(self) -> None:
        """Test creating new point with different coordinates."""
        original = CurvePoint(100, 1920.0, 1080.0)
        updated = original.with_coordinates(1921.0, 1081.0)

        assert updated.frame == original.frame
        assert updated.x == 1921.0
        assert updated.y == 1081.0
        assert updated.status == original.status
        assert original.x == 1920.0  # Original unchanged
        assert original.y == 1080.0

    def test_with_frame(self) -> None:
        """Test creating new point with different frame."""
        original = CurvePoint(100, 1920.0, 1080.0)
        updated = original.with_frame(101)

        assert updated.frame == 101
        assert updated.x == original.x
        assert updated.y == original.y
        assert updated.status == original.status
        assert original.frame == 100  # Original unchanged

    # === Serialization Tests ===

    def test_to_tuple3(self) -> None:
        """Test conversion to 3-tuple format."""
        point = CurvePoint(100, 1920.0, 1080.0, PointStatus.KEYFRAME)
        tuple3 = point.to_tuple3()
        assert tuple3 == (100, 1920.0, 1080.0)
        assert isinstance(tuple3, tuple)
        assert len(tuple3) == 3

    def test_to_tuple4(self) -> None:
        """Test conversion to 4-tuple format."""
        point = CurvePoint(100, 1920.0, 1080.0, PointStatus.INTERPOLATED)
        tuple4 = point.to_tuple4()
        assert tuple4 == (100, 1920.0, 1080.0, "interpolated")
        assert len(tuple4) == 4

    def test_to_legacy_tuple_normal(self) -> None:
        """Test legacy tuple conversion for normal points returns 3-tuple."""
        point = CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL)
        legacy = point.to_legacy_tuple()
        assert legacy == (100, 1920.0, 1080.0)
        assert len(legacy) == 3

    def test_to_legacy_tuple_non_normal(self) -> None:
        """Test legacy tuple conversion for non-normal points returns 4-tuple."""
        interp_point = CurvePoint(100, 1920.0, 1080.0, PointStatus.INTERPOLATED)
        keyframe_point = CurvePoint(101, 1921.0, 1081.0, PointStatus.KEYFRAME)

        interp_legacy = interp_point.to_legacy_tuple()
        keyframe_legacy = keyframe_point.to_legacy_tuple()

        assert interp_legacy == (100, 1920.0, 1080.0, "interpolated")
        assert keyframe_legacy == (101, 1921.0, 1081.0, "keyframe")
        assert len(interp_legacy) == 4
        assert len(keyframe_legacy) == 4

    # === Deserialization Tests ===

    def test_from_tuple_3_elements(self) -> None:
        """Test creation from 3-tuple."""
        point = CurvePoint.from_tuple((100, 1920.0, 1080.0))
        assert point.frame == 100
        assert point.x == 1920.0
        assert point.y == 1080.0
        assert point.status == PointStatus.NORMAL

    def test_from_tuple_4_elements_string(self) -> None:
        """Test creation from 4-tuple with string status."""
        point = CurvePoint.from_tuple((100, 1920.0, 1080.0, "interpolated"))
        assert point.frame == 100
        assert point.x == 1920.0
        assert point.y == 1080.0
        assert point.status == PointStatus.INTERPOLATED

    def test_from_tuple_4_elements_bool(self) -> None:
        """Test creation from 4-tuple with boolean status."""
        point_true = CurvePoint.from_tuple((100, 1920.0, 1080.0, True))
        point_false = CurvePoint.from_tuple((101, 1921.0, 1081.0, False))

        assert point_true.status == PointStatus.INTERPOLATED
        assert point_false.status == PointStatus.NORMAL

    def test_from_tuple_invalid_length(self) -> None:
        """Test creation from invalid tuple length raises error."""
        with pytest.raises(ValueError, match="must have 3 or 4 elements"):
            CurvePoint.from_tuple((100, 1920.0))  # pyright: ignore[reportArgumentType]

        with pytest.raises(ValueError, match="must have 3 or 4 elements"):
            CurvePoint.from_tuple((100,))  # pyright: ignore[reportArgumentType]

    def test_from_tuple_extra_elements_ignored(self) -> None:
        """Test creation from tuple with extra elements ignores them."""
        point = CurvePoint.from_tuple((100, 1920.0, 1080.0, "keyframe", "extra", "data"))  # pyright: ignore[reportArgumentType]
        assert point.frame == 100
        assert point.x == 1920.0
        assert point.y == 1080.0
        assert point.status == PointStatus.KEYFRAME

    # === Boundary Value Tests ===

    def test_extreme_frame_values(self) -> None:
        """Test points with extreme frame values."""
        min_frame = CurvePoint(-(2**31), 0.0, 0.0)
        max_frame = CurvePoint(2**31 - 1, 0.0, 0.0)

        assert min_frame.frame == -(2**31)
        assert max_frame.frame == 2**31 - 1

    def test_extreme_coordinate_values(self) -> None:
        """Test points with extreme coordinate values."""
        large_coords = CurvePoint(100, 1e10, -1e10)
        small_coords = CurvePoint(101, 1e-10, -1e-10)

        assert large_coords.x == 1e10
        assert large_coords.y == -1e10
        assert small_coords.x == 1e-10
        assert small_coords.y == -1e-10

    def test_zero_coordinates(self) -> None:
        """Test points at origin."""
        origin = CurvePoint(0, 0.0, 0.0)
        assert origin.x == 0.0
        assert origin.y == 0.0
        assert origin.coordinates == (0.0, 0.0)

    # === Equality and Hashing Tests ===

    def test_point_equality(self) -> None:
        """Test point equality comparison."""
        point1 = CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL)
        point2 = CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL)
        point3 = CurvePoint(101, 1920.0, 1080.0, PointStatus.NORMAL)

        assert point1 == point2
        assert point1 != point3

    def test_point_hashable(self) -> None:
        """Test that points can be used in sets and as dict keys."""
        point1 = CurvePoint(100, 1920.0, 1080.0)
        point2 = CurvePoint(101, 1921.0, 1081.0)

        point_set = {point1, point2, point1}  # point1 added twice
        assert len(point_set) == 2  # Only unique points

        point_dict = {point1: "first", point2: "second"}
        assert point_dict[point1] == "first"


class TestPointCollection:
    """Comprehensive tests for PointCollection data structure."""

    # === Creation and Validation Tests ===

    def test_empty_collection_creation(self) -> None:
        """Test creating empty point collection."""
        collection = PointCollection([])
        assert len(collection) == 0
        assert not collection

    def test_collection_creation_with_points(self) -> None:
        """Test creating collection with initial points."""
        points = [CurvePoint(100, 1920.0, 1080.0), CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED)]
        collection = PointCollection(points)

        assert len(collection) == 2
        assert bool(collection)
        assert collection[0] == points[0]
        assert collection[1] == points[1]

    def test_collection_validation_invalid_points(self) -> None:
        """Test collection validation rejects invalid point types."""
        with pytest.raises(TypeError, match="Point 1 must be CurvePoint"):
            _ = PointCollection([CurvePoint(100, 1920.0, 1080.0), (101, 1921.0, 1081.0)])  # pyright: ignore[reportArgumentType]

        with pytest.raises(TypeError, match="Point 1 must be CurvePoint"):
            _ = PointCollection([CurvePoint(100, 1920.0, 1080.0), "invalid"])  # pyright: ignore[reportArgumentType]

    # === Collection Interface Tests ===

    def test_iteration(self) -> None:
        """Test collection iteration."""
        points = [
            CurvePoint(100, 1920.0, 1080.0),
            CurvePoint(101, 1921.0, 1081.0),
        ]
        collection = PointCollection(points)

        iterated_points = list(collection)
        assert iterated_points == points

    def test_indexing_single(self) -> None:
        """Test single item indexing."""
        points = [
            CurvePoint(100, 1920.0, 1080.0),
            CurvePoint(101, 1921.0, 1081.0),
        ]
        collection = PointCollection(points)

        assert collection[0] == points[0]
        assert collection[1] == points[1]
        assert collection[-1] == points[1]

    def test_indexing_slice(self) -> None:
        """Test slice indexing returns new collection."""
        points = [
            CurvePoint(100, 1920.0, 1080.0),
            CurvePoint(101, 1921.0, 1081.0),
            CurvePoint(102, 1922.0, 1082.0),
        ]
        collection = PointCollection(points)

        slice_result = collection[1:3]
        assert isinstance(slice_result, PointCollection)
        assert len(slice_result) == 2
        assert slice_result[0] == points[1]
        assert slice_result[1] == points[2]

    def test_boolean_evaluation(self) -> None:
        """Test boolean evaluation of collection."""
        empty_collection = PointCollection([])
        non_empty_collection = PointCollection([CurvePoint(100, 1920.0, 1080.0)])

        assert not empty_collection
        assert bool(non_empty_collection)

    # === Query Methods Tests ===

    def test_frame_range_empty(self) -> None:
        """Test frame range for empty collection."""
        collection = PointCollection([])
        assert collection.frame_range is None

    def test_frame_range_single_point(self) -> None:
        """Test frame range for single point."""
        collection = PointCollection([CurvePoint(100, 1920.0, 1080.0)])
        assert collection.frame_range == (100, 100)

    def test_frame_range_multiple_points(self) -> None:
        """Test frame range for multiple points."""
        points = [
            CurvePoint(50, 1920.0, 1080.0),
            CurvePoint(100, 1921.0, 1081.0),
            CurvePoint(75, 1922.0, 1082.0),
        ]
        collection = PointCollection(points)
        assert collection.frame_range == (50, 100)

    def test_coordinate_bounds_empty(self) -> None:
        """Test coordinate bounds for empty collection."""
        collection = PointCollection([])
        assert collection.coordinate_bounds is None

    def test_coordinate_bounds_single_point(self) -> None:
        """Test coordinate bounds for single point."""
        collection = PointCollection([CurvePoint(100, 1920.0, 1080.0)])
        assert collection.coordinate_bounds == (1920.0, 1920.0, 1080.0, 1080.0)

    def test_coordinate_bounds_multiple_points(self) -> None:
        """Test coordinate bounds for multiple points."""
        points = [
            CurvePoint(100, 1920.0, 1080.0),
            CurvePoint(101, 1800.0, 1200.0),
            CurvePoint(102, 2000.0, 1000.0),
        ]
        collection = PointCollection(points)
        bounds = collection.coordinate_bounds
        assert bounds == (1800.0, 2000.0, 1000.0, 1200.0)

    def test_get_keyframes(self) -> None:
        """Test filtering keyframe points."""
        points = [
            CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL),
            CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED),
            CurvePoint(102, 1922.0, 1082.0, PointStatus.KEYFRAME),
        ]
        collection = PointCollection(points)
        keyframes = collection.get_keyframes()

        assert len(keyframes) == 2  # NORMAL and KEYFRAME are keyframes
        first_keyframe = keyframes[0]
        second_keyframe = keyframes[1]
        assert first_keyframe.status == PointStatus.NORMAL
        assert second_keyframe.status == PointStatus.KEYFRAME

    def test_get_interpolated(self) -> None:
        """Test filtering interpolated points."""
        points = [
            CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL),
            CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED),
            CurvePoint(102, 1922.0, 1082.0, PointStatus.KEYFRAME),
        ]
        collection = PointCollection(points)
        interpolated = collection.get_interpolated()

        assert len(interpolated) == 1
        first_interp = interpolated[0]
        assert first_interp.status == PointStatus.INTERPOLATED

    def test_find_closest_to_frame_empty(self) -> None:
        """Test finding closest point in empty collection."""
        collection = PointCollection([])
        assert collection.find_closest_to_frame(100) is None

    def test_find_closest_to_frame(self) -> None:
        """Test finding point closest to target frame."""
        points = [
            CurvePoint(100, 1920.0, 1080.0),
            CurvePoint(110, 1921.0, 1081.0),
            CurvePoint(90, 1922.0, 1082.0),
        ]
        collection = PointCollection(points)

        closest = collection.find_closest_to_frame(105)
        assert closest is not None and closest.frame == 100  # Closer than 110

        closest = collection.find_closest_to_frame(95)
        assert closest is not None and closest.frame == 100  # Closer than 90

    def test_find_at_frame(self) -> None:
        """Test finding all points at specific frame."""
        points = [
            CurvePoint(100, 1920.0, 1080.0),
            CurvePoint(100, 1921.0, 1081.0),  # Same frame
            CurvePoint(101, 1922.0, 1082.0),
        ]
        collection = PointCollection(points)

        at_100 = collection.find_at_frame(100)
        assert len(at_100) == 2
        assert at_100[0].frame == 100
        assert at_100[1].frame == 100

        at_101 = collection.find_at_frame(101)
        assert len(at_101) == 1
        assert at_101[0].frame == 101

        at_102 = collection.find_at_frame(102)
        assert len(at_102) == 0

    # === Modification Methods Tests ===

    def test_with_status_updates(self) -> None:
        """Test creating collection with status updates."""
        points = [
            CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL),
            CurvePoint(101, 1921.0, 1081.0, PointStatus.NORMAL),
            CurvePoint(102, 1922.0, 1082.0, PointStatus.NORMAL),
        ]
        collection = PointCollection(points)

        updates = {0: PointStatus.INTERPOLATED, 2: PointStatus.KEYFRAME}
        updated = collection.with_status_updates(updates)

        # Original unchanged
        orig_0 = collection[0]
        orig_1 = collection[1]
        orig_2 = collection[2]
        assert orig_0.status == PointStatus.NORMAL
        assert orig_1.status == PointStatus.NORMAL
        assert orig_2.status == PointStatus.NORMAL

        # Updated collection has changes
        upd_0 = updated[0]
        upd_1 = updated[1]
        upd_2 = updated[2]
        assert upd_0.status == PointStatus.INTERPOLATED
        assert upd_1.status == PointStatus.NORMAL  # Unchanged
        assert upd_2.status == PointStatus.KEYFRAME

    def test_with_coordinate_updates(self):
        """Test creating collection with coordinate updates."""
        points = [
            CurvePoint(100, 1920.0, 1080.0),
            CurvePoint(101, 1921.0, 1081.0),
            CurvePoint(102, 1922.0, 1082.0),
        ]
        collection = PointCollection(points)

        updates = {0: (2000.0, 1200.0), 2: (1800.0, 900.0)}
        updated = collection.with_coordinate_updates(updates)

        # Original unchanged
        orig_coord_0 = collection[0]
        assert orig_coord_0.coordinates == (1920.0, 1080.0)

        # Updated collection has changes
        upd_coord_0 = updated[0]
        upd_coord_1 = updated[1]
        upd_coord_2 = updated[2]
        assert upd_coord_0.coordinates == (2000.0, 1200.0)
        assert upd_coord_1.coordinates == (1921.0, 1081.0)  # Unchanged
        assert upd_coord_2.coordinates == (1800.0, 900.0)

    def test_sorted_by_frame(self):
        """Test sorting collection by frame number."""
        points = [
            CurvePoint(102, 1922.0, 1082.0),
            CurvePoint(100, 1920.0, 1080.0),
            CurvePoint(101, 1921.0, 1081.0),
        ]
        collection = PointCollection(points)
        sorted_collection = collection.sorted_by_frame()

        # Original unchanged
        orig_frame_0 = collection[0]
        assert orig_frame_0.frame == 102

        # Sorted collection is ordered
        sorted_0 = sorted_collection[0]
        sorted_1 = sorted_collection[1]
        sorted_2 = sorted_collection[2]
        assert sorted_0.frame == 100
        assert sorted_1.frame == 101
        assert sorted_2.frame == 102

    # === Conversion Methods Tests ===

    def test_to_tuples_legacy_format(self):
        """Test conversion to legacy tuple format."""
        points = [
            CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL),
            CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED),
        ]
        collection = PointCollection(points)
        tuples = collection.to_tuples()

        assert tuples == [
            (100, 1920.0, 1080.0),  # Normal = 3-tuple
            (101, 1921.0, 1081.0, "interpolated"),  # Non-normal = 4-tuple
        ]

    def test_to_tuple3_list(self):
        """Test conversion to 3-tuple list."""
        points = [
            CurvePoint(100, 1920.0, 1080.0, PointStatus.KEYFRAME),
            CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED),
        ]
        collection = PointCollection(points)
        tuple3_list = collection.to_tuple3_list()

        assert tuple3_list == [
            (100, 1920.0, 1080.0),
            (101, 1921.0, 1081.0),
        ]

    def test_to_tuple4_list(self):
        """Test conversion to 4-tuple list."""
        points = [
            CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL),
            CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED),
        ]
        collection = PointCollection(points)
        tuple4_list = collection.to_tuple4_list()

        assert tuple4_list == [
            (100, 1920.0, 1080.0, "normal"),
            (101, 1921.0, 1081.0, "interpolated"),
        ]

    def test_from_tuples(self):
        """Test creation from legacy tuple list."""
        from core.models import LegacyPointTuple

        tuples: list[LegacyPointTuple] = [
            (100, 1920.0, 1080.0),
            (101, 1921.0, 1081.0, "interpolated"),
            (102, 1922.0, 1082.0, True),  # Boolean status
        ]
        collection = PointCollection.from_tuples(tuples)

        assert len(collection) == 3
        assert collection[0].status == PointStatus.NORMAL
        assert collection[1].status == PointStatus.INTERPOLATED
        assert collection[2].status == PointStatus.INTERPOLATED

    def test_empty_factory(self):
        """Test empty collection factory method."""
        collection = PointCollection.empty()
        assert len(collection) == 0
        assert not collection


class TestTypeGuards:
    """Tests for point validation type guards."""

    def test_is_point_tuple_valid_3_tuple(self):
        """Test type guard accepts valid 3-tuples."""
        assert is_point_tuple((100, 1920.0, 1080.0))
        assert is_point_tuple((100, 1920, 1080))  # Integer coordinates OK

    def test_is_point_tuple_valid_4_tuple(self):
        """Test type guard accepts valid 4-tuples."""
        assert is_point_tuple((100, 1920.0, 1080.0, "normal"))
        assert is_point_tuple((100, 1920.0, 1080.0, True))

    def test_is_point_tuple_invalid_length(self):
        """Test type guard rejects invalid lengths."""
        assert not is_point_tuple((100, 1920.0))
        assert not is_point_tuple((100,))
        assert not is_point_tuple((100, 1920.0, 1080.0, "status", "extra"))

    def test_is_point_tuple_invalid_types(self):
        """Test type guard rejects invalid element types."""
        assert not is_point_tuple(("100", 1920.0, 1080.0))  # Non-int frame
        assert not is_point_tuple((100, "1920", 1080.0))  # Non-numeric x
        assert not is_point_tuple((100, 1920.0, "1080"))  # Non-numeric y
        assert not is_point_tuple((100, 1920.0, 1080.0, 123))  # Invalid status type

    def test_is_point_tuple_non_tuple(self):
        """Test type guard rejects non-tuple objects."""
        assert not is_point_tuple([100, 1920.0, 1080.0])
        assert not is_point_tuple("point")
        assert not is_point_tuple(None)

    def test_is_points_list_valid(self):
        """Test type guard accepts valid point lists."""
        valid_list = [
            (100, 1920.0, 1080.0),
            (101, 1921.0, 1081.0, "interpolated"),
        ]
        assert is_points_list(valid_list)

    def test_is_points_list_empty(self):
        """Test type guard accepts empty list."""
        assert is_points_list([])

    def test_is_points_list_invalid_elements(self):
        """Test type guard rejects lists with invalid elements."""
        invalid_list = [
            (100, 1920.0, 1080.0),
            "invalid_point",
        ]
        assert not is_points_list(invalid_list)

    def test_is_points_list_non_list(self):
        """Test type guard rejects non-list objects."""
        assert not is_points_list((100, 1920.0, 1080.0))
        assert not is_points_list("not a list")


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_normalize_legacy_point_3_tuple(self):
        """Test normalizing 3-tuple to 4-tuple."""
        result = normalize_legacy_point((100, 1920.0, 1080.0))
        assert result == (100, 1920.0, 1080.0, "normal")

    def test_normalize_legacy_point_4_tuple_string(self):
        """Test normalizing 4-tuple with string status."""
        result = normalize_legacy_point((100, 1920.0, 1080.0, "keyframe"))
        assert result == (100, 1920.0, 1080.0, "keyframe")

    def test_normalize_legacy_point_4_tuple_bool(self):
        """Test normalizing 4-tuple with boolean status."""
        result_true = normalize_legacy_point((100, 1920.0, 1080.0, True))
        result_false = normalize_legacy_point((100, 1920.0, 1080.0, False))

        assert result_true == (100, 1920.0, 1080.0, "interpolated")
        assert result_false == (100, 1920.0, 1080.0, "normal")

    def test_normalize_legacy_point_invalid(self) -> None:
        """Test normalizing invalid point raises error."""
        with pytest.raises(ValueError, match="Invalid point format"):
            normalize_legacy_point((100, 1920.0))  # pyright: ignore[reportArgumentType]

    def test_convert_to_curve_point(self):
        """Test converting tuples to CurvePoint."""
        point_3 = convert_to_curve_point((100, 1920.0, 1080.0))
        point_4 = convert_to_curve_point((101, 1921.0, 1081.0, "interpolated"))

        assert isinstance(point_3, CurvePoint)
        assert point_3.frame == 100
        assert point_3.status == PointStatus.NORMAL

        assert isinstance(point_4, CurvePoint)
        assert point_4.frame == 101
        assert point_4.status == PointStatus.INTERPOLATED

    def test_convert_to_curve_collection(self):
        """Test converting tuple list to PointCollection."""
        from core.models import PointsList

        tuples: PointsList = [
            (100, 1920.0, 1080.0),
            (101, 1921.0, 1081.0, "keyframe"),
        ]
        collection = convert_to_curve_collection(tuples)

        assert isinstance(collection, PointCollection)
        assert len(collection) == 2
        assert collection[0].frame == 100
        assert collection[1].status == PointStatus.KEYFRAME


class TestBulkOperations:
    """Tests for performance-optimized bulk operations."""

    def test_bulk_convert_to_tuples(self):
        """Test bulk conversion from CurvePoints to tuples."""
        points = [
            CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL),
            CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED),
            CurvePoint(102, 1922.0, 1082.0, PointStatus.KEYFRAME),
        ]

        tuples = bulk_convert_to_tuples(points)
        expected = [
            (100, 1920.0, 1080.0),  # Normal status = 3-tuple
            (101, 1921.0, 1081.0, "interpolated"),  # Non-normal = 4-tuple
            (102, 1922.0, 1082.0, "keyframe"),
        ]

        assert tuples == expected

    def test_bulk_convert_from_tuples(self):
        """Test bulk conversion from tuples to CurvePoints."""
        from core.models import PointsList

        tuples: PointsList = [
            (100, 1920.0, 1080.0),
            (101, 1921.0, 1081.0, "interpolated"),
            (102, 1922.0, 1082.0, True),  # Boolean status
            (103, 1923.0, 1083.0, "keyframe"),
        ]

        points = bulk_convert_from_tuples(tuples)

        assert len(points) == 4
        assert all(isinstance(p, CurvePoint) for p in points)
        assert points[0].status == PointStatus.NORMAL
        assert points[1].status == PointStatus.INTERPOLATED
        assert points[2].status == PointStatus.INTERPOLATED  # True -> INTERPOLATED
        assert points[3].status == PointStatus.KEYFRAME

    def test_bulk_operations_round_trip(self):
        """Test round-trip conversion preserves data."""
        original_points = [
            CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL),
            CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED),
            CurvePoint(102, 1922.0, 1082.0, PointStatus.KEYFRAME),
        ]

        # Convert to tuples and back
        tuples = bulk_convert_to_tuples(original_points)
        recovered_points = bulk_convert_from_tuples(tuples)

        assert len(recovered_points) == len(original_points)
        for orig, recovered in zip(original_points, recovered_points):
            assert orig == recovered


class TestImageSequenceInfo:
    """Tests for ImageSequenceInfo data model."""

    def test_creation_defaults(self):
        """Test creation with default values."""
        info = ImageSequenceInfo()
        assert info.path == ""
        assert info.filenames == []
        assert info.current_index == -1
        assert info.total_count == 0

    def test_creation_with_values(self):
        """Test creation with provided values."""
        filenames = ["frame001.jpg", "frame002.jpg", "frame003.jpg"]
        info = ImageSequenceInfo(path="/test/path", filenames=filenames, current_index=1)

        assert info.path == "/test/path"
        assert info.filenames == filenames
        assert info.current_index == 1
        assert info.total_count == 3  # Auto-calculated

    def test_post_init_validation(self):
        """Test __post_init__ ensures filenames is list."""
        # Test with non-list filenames
        info = ImageSequenceInfo(filenames="not_a_list")  # pyright: ignore[reportArgumentType]
        assert info.filenames == []
        assert info.total_count == 0

    def test_is_valid_property(self):
        """Test is_valid property validation."""
        # Invalid: no path
        info1 = ImageSequenceInfo()
        assert not info1.is_valid

        # Invalid: no filenames
        info2 = ImageSequenceInfo(path="/nonexistent")
        assert not info2.is_valid

        # Test with temporary directory for valid case
        with tempfile.TemporaryDirectory() as tmpdir:
            info3 = ImageSequenceInfo(path=tmpdir, filenames=["test.jpg"])
            assert info3.is_valid

    def test_current_filename_property(self):
        """Test current_filename property."""
        filenames = ["frame001.jpg", "frame002.jpg", "frame003.jpg"]
        info = ImageSequenceInfo(filenames=filenames)

        # No current index
        assert info.current_filename is None

        # Valid index
        info.current_index = 1
        assert info.current_filename == "frame002.jpg"

        # Invalid index
        info.current_index = 10
        assert info.current_filename is None

    def test_current_filepath_property(self):
        """Test current_filepath property."""
        filenames = ["frame001.jpg", "frame002.jpg"]
        info = ImageSequenceInfo(path="/test/path", filenames=filenames, current_index=1)

        expected = os.path.join("/test/path", "frame002.jpg")
        assert info.current_filepath == expected

        # No current filename
        info.current_index = -1
        assert info.current_filepath is None


class TestImageDisplayInfo:
    """Tests for ImageDisplayInfo data model."""

    def test_creation_defaults(self):
        """Test creation with default values."""
        info = ImageDisplayInfo()
        assert info.pixmap is None
        assert info.width == 0
        assert info.height == 0
        assert info.filepath == ""
        assert info.load_error == ""

    def test_creation_with_pixmap(self):
        """Test creation with ThreadSafeTestImage."""
        pixmap = ThreadSafeTestImage(100, 200)
        info = ImageDisplayInfo(pixmap=pixmap, width=100, height=200, filepath="/test/image.jpg")  # pyright: ignore[reportArgumentType]

        assert info.pixmap == pixmap
        assert info.width == 100
        assert info.height == 200
        assert info.filepath == "/test/image.jpg"

    def test_is_loaded_property(self):
        """Test is_loaded property."""
        # No pixmap
        info1 = ImageDisplayInfo()
        assert not info1.is_loaded

        # Null pixmap
        null_pixmap = None  # Use None for null pixmap test
        info2 = ImageDisplayInfo(pixmap=null_pixmap)
        assert not info2.is_loaded

        # Valid pixmap
        valid_pixmap = ThreadSafeTestImage(100, 100)
        info3 = ImageDisplayInfo(pixmap=valid_pixmap)  # pyright: ignore[reportArgumentType]
        assert info3.is_loaded

    def test_has_error_property(self):
        """Test has_error property."""
        info1 = ImageDisplayInfo()
        assert not info1.has_error

        info2 = ImageDisplayInfo(load_error="Failed to load image")
        assert info2.has_error


class TestImageState:
    """Comprehensive tests for ImageState management."""

    def test_initialization(self):
        """Test ImageState initialization."""
        state = ImageState()
        assert state.loading_state == ImageLoadingState.NO_SEQUENCE
        assert isinstance(state.sequence_info, ImageSequenceInfo)
        assert isinstance(state.display_info, ImageDisplayInfo)

    # === State Detection Tests ===

    def test_has_sequence_loaded_initial(self):
        """Test initial state has no sequence loaded."""
        state = ImageState()
        assert not state.has_sequence_loaded()

    def test_has_image_displayed_initial(self):
        """Test initial state has no image displayed."""
        state = ImageState()
        assert not state.has_image_displayed()

    def test_has_any_image_data_initial(self):
        """Test initial state has no image data."""
        state = ImageState()
        assert not state.has_any_image_data()

    def test_is_loading_initial(self):
        """Test initial state is not loading."""
        state = ImageState()
        assert not state.is_loading()

    def test_has_loading_error_initial(self):
        """Test initial state has no loading error."""
        state = ImageState()
        assert not state.has_loading_error()

    # === Sequence Management Tests ===

    def test_set_sequence_valid(self):
        """Test setting valid image sequence."""
        state = ImageState()

        with tempfile.TemporaryDirectory() as tmpdir:
            filenames = ["frame001.jpg", "frame002.jpg"]
            state.set_sequence(tmpdir, filenames)

            assert state.has_sequence_loaded()
            assert state.loading_state == ImageLoadingState.SEQUENCE_LOADED
            assert state.sequence_info.path == tmpdir
            assert state.sequence_info.filenames == filenames
            assert state.sequence_info.total_count == 2

    def test_set_sequence_invalid_path(self):
        """Test setting sequence with invalid path."""
        state = ImageState()
        state.set_sequence("", ["frame001.jpg"])

        assert not state.has_sequence_loaded()
        assert state.loading_state == ImageLoadingState.NO_SEQUENCE

    def test_set_sequence_no_filenames(self):
        """Test setting sequence with no filenames."""
        state = ImageState()
        with tempfile.TemporaryDirectory() as tmpdir:
            state.set_sequence(tmpdir, [])

            assert not state.has_sequence_loaded()
            assert state.loading_state == ImageLoadingState.NO_SEQUENCE

    def test_set_current_image_index_valid(self):
        """Test setting valid image index."""
        state = ImageState()

        with tempfile.TemporaryDirectory() as tmpdir:
            filenames = ["frame001.jpg", "frame002.jpg", "frame003.jpg"]
            state.set_sequence(tmpdir, filenames)
            state.set_current_image_index(1)

            assert state.sequence_info.current_index == 1

    def test_set_current_image_index_no_sequence(self):
        """Test setting image index without sequence does nothing."""
        state = ImageState()
        state.set_current_image_index(1)  # Should do nothing
        assert state.sequence_info.current_index == -1

    def test_set_current_image_index_out_of_bounds(self):
        """Test setting out-of-bounds image index."""
        state = ImageState()

        with tempfile.TemporaryDirectory() as tmpdir:
            filenames = ["frame001.jpg", "frame002.jpg"]
            state.set_sequence(tmpdir, filenames)

            # Test negative index
            state.set_current_image_index(-1)
            assert state.sequence_info.current_index == -1  # Should remain unchanged

            # Test too large index
            state.set_current_image_index(10)
            assert state.sequence_info.current_index == -1  # Should remain unchanged

    # === Image Loading State Tests ===

    def test_set_image_loading(self):
        """Test setting image loading state."""
        state = ImageState()
        state.set_image_loading()

        assert state.is_loading()
        assert state.loading_state == ImageLoadingState.IMAGE_LOADING
        assert not state.display_info.has_error

    def test_set_image_loaded(self):
        """Test setting image loaded state."""
        state = ImageState()
        pixmap = ThreadSafeTestImage(100, 100)
        filepath = "/test/image.jpg"

        state.set_image_loaded(pixmap, filepath)  # pyright: ignore[reportArgumentType]

        assert state.has_image_displayed()
        assert state.loading_state == ImageLoadingState.IMAGE_LOADED
        assert state.display_info.pixmap == pixmap
        assert state.display_info.filepath == filepath
        assert state.display_info.width == 100
        assert state.display_info.height == 100

    def test_set_image_load_failed(self):
        """Test setting image load failed state."""
        state = ImageState()
        error_message = "Failed to load image"

        state.set_image_load_failed(error_message)

        assert state.has_loading_error()
        assert state.loading_state == ImageLoadingState.IMAGE_FAILED
        assert state.display_info.load_error == error_message
        assert state.display_info.pixmap is None

    # === Clear Operations Tests ===

    def test_clear_sequence(self):
        """Test clearing entire sequence."""
        state = ImageState()

        # Set up some state first
        with tempfile.TemporaryDirectory() as tmpdir:
            state.set_sequence(tmpdir, ["frame001.jpg"])
            pixmap = ThreadSafeTestImage(100, 100)
            state.set_image_loaded(cast(Any, pixmap), "/test/image.jpg")

            # Clear everything
            state.clear_sequence()

            assert not state.has_sequence_loaded()
            assert not state.has_image_displayed()
            assert state.loading_state == ImageLoadingState.NO_SEQUENCE

    def test_clear_display_with_sequence(self):
        """Test clearing display while keeping sequence."""
        state = ImageState()

        with tempfile.TemporaryDirectory() as tmpdir:
            filenames = ["frame001.jpg", "frame002.jpg"]
            state.set_sequence(tmpdir, filenames)
            pixmap = ThreadSafeTestImage(100, 100)
            state.set_image_loaded(cast(Any, pixmap), "/test/image.jpg")

            # Clear only display
            state.clear_display()

            assert state.has_sequence_loaded()  # Sequence preserved
            assert not state.has_image_displayed()  # Display cleared
            assert state.loading_state == ImageLoadingState.SEQUENCE_LOADED

    def test_clear_display_no_sequence(self):
        """Test clearing display with no sequence clears everything."""
        state = ImageState()
        pixmap = ThreadSafeTestImage(100, 100)
        state.set_image_loaded(cast(Any, pixmap), "/test/image.jpg")

        state.clear_display()

        assert not state.has_sequence_loaded()
        assert not state.has_image_displayed()
        assert state.loading_state == ImageLoadingState.NO_SEQUENCE

    # === Status Message Tests ===

    def test_get_status_message_no_images(self):
        """Test status message when no images loaded."""
        state = ImageState()
        message = state.get_status_message()
        assert message == "No images loaded"

    def test_get_status_message_loading(self):
        """Test status message during loading."""
        state = ImageState()
        state.set_image_loading()
        message = state.get_status_message()
        assert message == "Loading image..."

    def test_get_status_message_loaded(self):
        """Test status message when image loaded."""
        state = ImageState()

        with tempfile.TemporaryDirectory() as tmpdir:
            filenames = ["test_image.jpg"]
            state.set_sequence(tmpdir, filenames)
            state.set_current_image_index(0)

            pixmap = ThreadSafeTestImage(100, 100)
            state.set_image_loaded(cast(Any, pixmap), "/test/path/test_image.jpg")

            message = state.get_status_message()
            assert "Image loaded: test_image.jpg" in message

    def test_get_status_message_error(self):
        """Test status message on error."""
        state = ImageState()
        error_msg = "File not found"
        state.set_image_load_failed(error_msg)

        message = state.get_status_message()
        assert message == f"Error: {error_msg}"

    def test_get_status_message_sequence_loaded(self):
        """Test status message when sequence loaded but no image."""
        state = ImageState()

        with tempfile.TemporaryDirectory() as tmpdir:
            filenames = ["frame001.jpg", "frame002.jpg", "frame003.jpg"]
            state.set_sequence(tmpdir, filenames)

            message = state.get_status_message()
            assert message == "Sequence loaded (3 images, none displayed)"

    def test_get_timeline_message_no_sequence(self):
        """Test timeline message with no sequence."""
        state = ImageState()
        message = state.get_timeline_message()
        assert message == "No images loaded"

    def test_get_timeline_message_with_current(self):
        """Test timeline message with current image."""
        state = ImageState()

        with tempfile.TemporaryDirectory() as tmpdir:
            filenames = ["frame001.jpg", "frame002.jpg", "frame003.jpg"]
            state.set_sequence(tmpdir, filenames)
            state.set_current_image_index(1)  # Second image (0-based)

            message = state.get_timeline_message()
            assert message == "Image: 2/3 - frame002.jpg"

    # === State Change Callbacks Tests ===

    def test_state_change_callbacks(self):
        """Test state change callback system."""
        state = ImageState()
        callback_calls = []

        def callback():
            callback_calls.append("called")

        # Add callback
        state.add_state_change_callback(callback)

        # Trigger state change
        state.set_image_loading()

        assert len(callback_calls) == 1

        # Remove callback
        state.remove_state_change_callback(callback)

        # Trigger another state change
        state.clear_sequence()

        # Callback should not be called again
        assert len(callback_calls) == 1

    def test_state_change_callback_exception_handling(self):
        """Test callback exception handling doesn't break state."""
        state = ImageState()

        def failing_callback():
            raise RuntimeError("Callback failed")

        state.add_state_change_callback(failing_callback)

        # Should not raise exception
        state.set_image_loading()

        # State should still be updated
        assert state.is_loading()

    # === Debug and Inspection Tests ===

    def test_get_state_summary(self):
        """Test state summary for debugging."""
        state = ImageState()

        with tempfile.TemporaryDirectory() as tmpdir:
            filenames = ["frame001.jpg", "frame002.jpg"]
            state.set_sequence(tmpdir, filenames)
            state.set_current_image_index(1)

            pixmap = ThreadSafeTestImage(100, 200)
            state.set_image_loaded(cast(Any, pixmap), "/test/image.jpg")

            summary = state.get_state_summary()

            assert summary["loading_state"] == "IMAGE_LOADED"
            assert summary["sequence_loaded"] is True
            assert summary["image_displayed"] is True
            assert summary["sequence_count"] == 2
            assert summary["current_index"] == 1
            assert summary["display_width"] == 100
            assert summary["display_height"] == 200

    def test_string_representation(self):
        """Test string representation for debugging."""
        state = ImageState()
        string_repr = str(state)

        assert "ImageState" in string_repr
        assert "NO_SEQUENCE" in string_repr
        assert "seq=False" in string_repr
        assert "img=False" in string_repr

    # === Legacy Compatibility Tests ===

    def test_sync_from_curve_view(self):
        """Test syncing state from curve view."""
        state = ImageState()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock curve view with attributes
            mock_curve_view = Mock()
            mock_curve_view.image_sequence_path = tmpdir
            mock_curve_view.image_filenames = ["frame001.jpg", "frame002.jpg"]
            mock_curve_view.current_image_idx = 1

            # Mock background image
            mock_pixmap = ThreadSafeTestImage(100, 100)
            mock_curve_view.background_image = mock_pixmap
            mock_pixmap.isNull = Mock(return_value=False)

            # Sync state
            state.sync_from_curve_view(mock_curve_view)

            # Verify state was synced
            assert state.has_sequence_loaded()
            assert state.sequence_info.path == tmpdir
            assert state.sequence_info.current_index == 1
            assert state.has_image_displayed()

    def test_sync_from_main_window(self):
        """Test syncing state from main window."""
        state = ImageState()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock main window
            mock_main_window = Mock()
            mock_main_window.image_sequence_path = tmpdir
            mock_main_window.image_filenames = ["frame001.jpg"]
            mock_main_window.current_frame = 0
            mock_main_window.curve_view = None

            # Sync state
            state.sync_from_main_window(mock_main_window)

            # Verify state was synced
            assert state.has_sequence_loaded()
            assert state.sequence_info.path == tmpdir
            assert state.sequence_info.current_index == 0


class TestPropertyBasedTesting:
    """Property-based tests using Hypothesis for robust validation."""

    @given(
        frame=st.integers(min_value=1, max_value=10000),  # Reduced range for faster generation
        x=st.floats(allow_nan=False, allow_infinity=False, min_value=-1000, max_value=1000),  # Reduced range
        y=st.floats(allow_nan=False, allow_infinity=False, min_value=-1000, max_value=1000),  # Reduced range
    )
    @settings(max_examples=50, deadline=1000)  # Reduce examples and increase deadline
    def test_point_creation_invariants(self, frame, x, y):
        """Test that point creation invariants hold for all valid inputs."""
        point = CurvePoint(frame, x, y)

        # Basic invariants
        assert point.frame == frame
        assert point.x == x
        assert point.y == y
        assert point.status == PointStatus.NORMAL

        # Property invariants
        assert point.coordinates == (x, y)
        assert not point.is_interpolated
        assert point.is_keyframe

    @given(
        points=st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=1000),
                st.floats(allow_nan=False, allow_infinity=False, min_value=-1000, max_value=1000),
                st.floats(allow_nan=False, allow_infinity=False, min_value=-1000, max_value=1000),
            ),
            min_size=0,
            max_size=10,
        )
    )
    def test_collection_operations_invariants(self, points):
        """Test that collection operations preserve invariants."""
        # Convert tuples to CurvePoints
        curve_points = [CurvePoint(f, x, y) for f, x, y in points]
        collection = PointCollection(curve_points)

        # Length invariant
        assert len(collection) == len(points)

        # Boolean invariant
        assert bool(collection) == bool(points)

        # Frame range invariant
        if points:
            frames = [p[0] for p in points]
            min_frame, max_frame = min(frames), max(frames)
            assert collection.frame_range == (min_frame, max_frame)
        else:
            assert collection.frame_range is None

        # Coordinate bounds invariant
        if points:
            x_coords = [p[1] for p in points]
            y_coords = [p[2] for p in points]
            expected_bounds = (min(x_coords), max(x_coords), min(y_coords), max(y_coords))
            assert collection.coordinate_bounds == expected_bounds
        else:
            assert collection.coordinate_bounds is None

    @given(
        point1_data=st.tuples(
            st.integers(1, 1000),
            st.floats(-1000, 1000, allow_nan=False, allow_infinity=False),
            st.floats(-1000, 1000, allow_nan=False, allow_infinity=False),
        ),
        point2_data=st.tuples(
            st.integers(1, 1000),
            st.floats(-1000, 1000, allow_nan=False, allow_infinity=False),
            st.floats(-1000, 1000, allow_nan=False, allow_infinity=False),
        ),
    )
    def test_distance_properties(self, point1_data, point2_data):
        """Test distance calculation properties."""
        point1 = CurvePoint(*point1_data)
        point2 = CurvePoint(*point2_data)

        distance = point1.distance_to(point2)

        # Distance is non-negative
        assert distance >= 0

        # Distance is symmetric
        assert abs(distance - point2.distance_to(point1)) < 1e-10

        # Distance to self is zero
        assert point1.distance_to(point1) == 0

        # Triangle inequality (approximate due to floating point)
        origin = CurvePoint(1, 0.0, 0.0)
        d1_origin = point1.distance_to(origin)
        d2_origin = point2.distance_to(origin)
        assert distance <= d1_origin + d2_origin + 1e-10

    @given(
        status_values=st.one_of(
            st.none(),
            st.booleans(),
            st.sampled_from(["normal", "interpolated", "keyframe", "invalid"]),
            st.integers(),
            st.floats(),
        )
    )
    def test_status_from_legacy_robustness(self, status_values):
        """Test PointStatus.from_legacy handles all input types safely."""
        result = PointStatus.from_legacy(status_values)

        # Always returns valid PointStatus
        assert isinstance(result, PointStatus)
        # from_legacy can return any valid PointStatus value
        assert result in (
            PointStatus.NORMAL,
            PointStatus.INTERPOLATED,
            PointStatus.KEYFRAME,
            PointStatus.TRACKED,
            PointStatus.ENDFRAME,
        )

        # Can convert back to string and bool
        assert isinstance(result.to_legacy_string(), str)
        assert isinstance(result.to_legacy_bool(), bool)


class TestEdgeCasesAndErrorConditions:
    """Tests for edge cases and error conditions."""

    def test_point_with_extreme_values(self):
        """Test points with extreme coordinate values."""
        # Very large values
        large_point = CurvePoint(1, 1e15, -1e15)
        assert large_point.x == 1e15
        assert large_point.y == -1e15

        # Very small values
        small_point = CurvePoint(2, 1e-15, -1e-15)
        assert small_point.x == 1e-15
        assert small_point.y == -1e-15

    def test_collection_with_duplicate_frames(self):
        """Test collection behavior with duplicate frame numbers."""
        points = [
            CurvePoint(100, 1920.0, 1080.0),
            CurvePoint(100, 1921.0, 1081.0),  # Same frame
            CurvePoint(100, 1922.0, 1082.0),  # Same frame
        ]
        collection = PointCollection(points)

        # Should still work normally
        assert len(collection) == 3
        assert collection.frame_range == (100, 100)

        # Find at frame should return all matches
        at_100 = collection.find_at_frame(100)
        assert len(at_100) == 3

    def test_empty_collection_operations(self):
        """Test operations on empty collections."""
        empty = PointCollection([])

        # All query methods should handle empty gracefully
        assert empty.frame_range is None
        assert empty.coordinate_bounds is None
        assert len(empty.get_keyframes()) == 0
        assert len(empty.get_interpolated()) == 0
        assert empty.find_closest_to_frame(100) is None
        assert len(empty.find_at_frame(100)) == 0

        # Modification methods should work
        updated = empty.with_status_updates({})
        assert len(updated) == 0

        sorted_empty = empty.sorted_by_frame()
        assert len(sorted_empty) == 0

    def test_image_state_edge_cases(self):
        """Test ImageState edge cases."""
        state = ImageState()

        # Setting current index without sequence
        state.set_current_image_index(0)  # Should be ignored
        assert state.sequence_info.current_index == -1

        # Setting null pixmap
        null_pixmap = None  # Use None for null pixmap test
        state.set_image_loaded(cast(Any, null_pixmap), "")
        assert not state.has_image_displayed()  # Null pixmap not considered loaded

    def test_bulk_operations_empty_lists(self):
        """Test bulk operations with empty input."""
        # Empty points to tuples
        empty_tuples = bulk_convert_to_tuples([])
        assert empty_tuples == []

        # Empty tuples to points
        empty_points = bulk_convert_from_tuples([])
        assert empty_points == []

    def test_json_serialization_compatibility(self):
        """Test that point data can be JSON serialized."""
        point = CurvePoint(100, 1920.0, 1080.0, PointStatus.INTERPOLATED)

        # Convert to dict-like structure for JSON
        point_dict = {"frame": point.frame, "x": point.x, "y": point.y, "status": point.status.value}

        # Should be JSON serializable
        json_str = json.dumps(point_dict)
        recovered_dict = json.loads(json_str)

        # Should be able to reconstruct point
        recovered_point = CurvePoint(
            recovered_dict["frame"], recovered_dict["x"], recovered_dict["y"], PointStatus(recovered_dict["status"])
        )

        assert recovered_point == point


# === Fixtures for Test Reusability ===


@pytest.fixture
def sample_curve_points():
    """Sample CurvePoint objects for testing."""
    return [
        CurvePoint(100, 1920.0, 1080.0, PointStatus.NORMAL),
        CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED),
        CurvePoint(102, 1922.0, 1082.0, PointStatus.KEYFRAME),
    ]


@pytest.fixture
def sample_point_collection(sample_curve_points):
    """Sample PointCollection for testing."""
    return PointCollection(sample_curve_points)


@pytest.fixture
def mock_pixmap():
    """Mock ThreadSafeTestImage for testing."""
    return ThreadSafeTestImage(100, 100)


@pytest.fixture
def image_state():
    """Fresh ImageState instance for testing."""
    return ImageState()


@pytest.fixture
def temp_image_directory():
    """Temporary directory with sample image filenames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some empty files to simulate images
        filenames = ["frame001.jpg", "frame002.jpg", "frame003.jpg"]
        for filename in filenames:
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w") as f:
                f.write("")  # Empty file
        yield tmpdir, filenames
