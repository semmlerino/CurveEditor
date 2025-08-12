#!/usr/bin/env python
"""
Migration utilities for transitioning from legacy point formats to unified data models.

This module provides comprehensive migration tools to gradually transition the
codebase from scattered tuple-based point representations to the unified
CurvePoint and PointCollection models.

Key Features:
- Gradual migration path with backward compatibility
- Performance-optimized bulk operations
- Type-safe conversion with validation
- Integration with existing service methods
- Comprehensive testing utilities

Migration Phases:
1. Phase 1: Install utilities alongside existing code
2. Phase 2: Gradually replace tuple operations with model operations
3. Phase 3: Update service interfaces to accept both formats
4. Phase 4: Migrate rendering and UI systems
5. Phase 5: Remove legacy tuple support (future)

Usage Examples:
    # Basic conversion
    legacy_points = [(100, 1920.0, 1080.0), (101, 1921.0, 1081.0, "interpolated")]
    collection = migrate_points_list(legacy_points)

    # Service integration
    @accept_both_formats
    def process_points(points):
        # Works with both legacy tuples and PointCollection
        collection = ensure_point_collection(points)
        # ... process collection ...
        return collection.to_tuples()  # Return legacy format for compatibility
"""

import functools
import warnings
from collections.abc import Callable

from core.models import CurvePoint, PointCollection, PointStatus, bulk_convert_from_tuples, bulk_convert_to_tuples

# Type definitions for migration
LegacyPointTuple = Union[tuple[int, float, float], tuple[int, float, float, str], tuple[int, float, float, bool]]
AnyPointFormat = Union["PointsList", PointCollection, list[CurvePoint]]
F = TypeVar("F", bound=Callable[..., Any])

class MigrationError(Exception):
    """Exception raised during point format migration."""

    pass

class MigrationWarning(UserWarning):
    """Warning issued for deprecated point format usage."""

    pass

# Type guards for runtime format detection

def is_legacy_point_tuple(obj: Any) -> TypeGuard[LegacyPointTuple]:
    """Type guard for legacy point tuple formats.

    Args:
        obj: Object to check

    Returns:
        True if obj is a legacy point tuple
    """
    if not isinstance(obj, tuple):
        return False

    if len(obj) < 3 or len(obj) > 4:
        return False

    # Check frame (int), x (float), y (float)
    try:
        frame, x, y = obj[:3]
        if not isinstance(frame, int):
            return False
        if not isinstance(x, int | float):
            return False
        if not isinstance(y, int | float):
            return False

        # Check status if present
        if len(obj) == 4:
            status = obj[3]
            if not isinstance(status, str | bool):
                return False

        return True
    except (ValueError, TypeError):
        return False

def is_legacy_points_list(obj: Any) -> TypeGuard["PointsList"]:
    """Type guard for legacy PointsList format.

    Args:
        obj: Object to check

    Returns:
        True if obj is a legacy PointsList
    """
    if not isinstance(obj, list):
        return False

    if not obj:  # Empty list is valid
        return True

    return all(is_legacy_point_tuple(item) for item in obj)

def is_point_collection(obj: Any) -> TypeGuard[PointCollection]:
    """Type guard for PointCollection format.

    Args:
        obj: Object to check

    Returns:
        True if obj is a PointCollection
    """
    return isinstance(obj, PointCollection)

def is_curve_point_list(obj: Any) -> TypeGuard[list[CurvePoint]]:
    """Type guard for list of CurvePoint objects.

    Args:
        obj: Object to check

    Returns:
        True if obj is a list of CurvePoint objects
    """
    if not isinstance(obj, list):
        return False

    if not obj:  # Empty list is valid
        return True

    return all(isinstance(item, CurvePoint) for item in obj)

# Core migration functions

@overload
def migrate_points_list(points: "PointsList") -> PointCollection: ...

@overload
def migrate_points_list(points: PointCollection) -> PointCollection: ...

@overload
def migrate_points_list(points: list[CurvePoint]) -> PointCollection: ...

def migrate_points_list(points: AnyPointFormat) -> PointCollection:
    """Migrate any point format to PointCollection.

    Args:
        points: Points in any supported format

    Returns:
        PointCollection with migrated data

    Raises:
        MigrationError: If input format is not supported

    Examples:
        >>> legacy = [(100, 1920.0, 1080.0), (101, 1921.0, 1081.0)]
        >>> collection = migrate_points_list(legacy)
        >>> len(collection)
        2
    """
    if is_point_collection(points):
        return points
    elif is_curve_point_list(points):
        return PointCollection(points)
    elif is_legacy_points_list(points):
        return PointCollection.from_tuples(points)
    else:
        raise MigrationError(f"Unsupported point format: {type(points)}")

@overload
def ensure_point_collection(points: "PointsList") -> PointCollection: ...

@overload
def ensure_point_collection(points: PointCollection) -> PointCollection: ...

@overload
def ensure_point_collection(points: list[CurvePoint]) -> PointCollection: ...

def ensure_point_collection(points: AnyPointFormat) -> PointCollection:
    """Ensure input is a PointCollection, converting if necessary.

    This is the primary utility function for service methods that need to work
    with both legacy and new formats during the migration period.

    Args:
        points: Points in any supported format

    Returns:
        PointCollection instance

    Examples:
        >>> # Works with legacy format
        >>> legacy = [(100, 1920.0, 1080.0)]
        >>> collection = ensure_point_collection(legacy)
        >>> isinstance(collection, PointCollection)
        True

        >>> # Works with new format
        >>> new_collection = PointCollection([CurvePoint(100, 1920.0, 1080.0)])
        >>> same_collection = ensure_point_collection(new_collection)
        >>> new_collection is same_collection
        True
    """
    return migrate_points_list(points)

def ensure_legacy_format(points: AnyPointFormat) -> "PointsList":
    """Ensure output is in legacy PointsList format.

    Used when functions need to return legacy format for compatibility
    with existing code that hasn't been migrated yet.

    Args:
        points: Points in any supported format

    Returns:
        PointsList in legacy tuple format

    Examples:
        >>> collection = PointCollection([CurvePoint(100, 1920.0, 1080.0)])
        >>> legacy = ensure_legacy_format(collection)
        >>> legacy
        [(100, 1920.0, 1080.0)]
    """
    if is_legacy_points_list(points):
        return points
    else:
        collection = ensure_point_collection(points)
        return collection.to_tuples()

# Performance-optimized migration for large datasets

def bulk_migrate_points(points: "PointsList", chunk_size: int = 10000) -> PointCollection:
    """High-performance migration for large point datasets.

    Uses chunked processing to minimize memory usage and provide progress
    feedback for very large datasets (>100k points).

    Args:
        points: Large PointsList to migrate
        chunk_size: Number of points to process at once

    Returns:
        PointCollection with migrated data
    """
    if len(points) <= chunk_size:
        return PointCollection.from_tuples(points)

    # Process in chunks for better memory management
    all_curve_points = []
    for i in range(0, len(points), chunk_size):
        chunk = points[i : i + chunk_size]
        curve_points = bulk_convert_from_tuples(chunk)
        all_curve_points.extend(curve_points)

    return PointCollection(all_curve_points)

def bulk_export_to_legacy(collection: PointCollection, chunk_size: int = 10000) -> "PointsList":
    """High-performance export to legacy format for large datasets.

    Args:
        collection: PointCollection to export
        chunk_size: Number of points to process at once

    Returns:
        PointsList in legacy format
    """
    if len(collection) <= chunk_size:
        return collection.to_tuples()

    # Process in chunks for better memory management
    all_tuples = []
    for i in range(0, len(collection), chunk_size):
        chunk_points = collection.points[i : i + chunk_size]
        chunk_tuples = bulk_convert_to_tuples(chunk_points)
        all_tuples.extend(chunk_tuples)

    return all_tuples

# Service integration decorators

def accept_both_formats[F: Callable[..., Any]](func: F) -> F:
    """Decorator to make service methods accept both legacy and new point formats.

    Automatically converts the first point-like argument to PointCollection,
    processes it, then converts back to legacy format for return value.

    Args:
        func: Service method to decorate

    Returns:
        Decorated function that accepts both formats

    Examples:
        @accept_both_formats
        def process_curve_points(points, some_param):
            # points is guaranteed to be PointCollection here
            # ... process points ...
            return points  # Auto-converted back to legacy format
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Convert first argument if it looks like points data
        new_args = list(args)
        if args and _looks_like_points_data(args[0]):
            new_args[0] = ensure_point_collection(args[0])

        # Call original function
        result = func(*new_args, **kwargs)

        # Convert result back to legacy format if it's a PointCollection
        if is_point_collection(result):
            return result.to_tuples()
        elif is_curve_point_list(result):
            return bulk_convert_to_tuples(result)
        else:
            return result

    return cast(F, wrapper)

def deprecate_legacy_format[F: Callable[..., Any]](func: F) -> F:
    """Decorator to issue deprecation warnings for legacy point format usage.

    Args:
        func: Function to decorate

    Returns:
        Decorated function that issues warnings for legacy usage
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Check if any arguments are legacy format
        for i, arg in enumerate(args):
            if is_legacy_points_list(arg):
                warnings.warn(
                    f"Legacy point format detected in {func.__name__}() argument {i}. "
                    f"Consider migrating to PointCollection for better performance and type safety.",
                    MigrationWarning,
                    stacklevel=2,
                )
                break

        return func(*args, **kwargs)

    return cast(F, wrapper)

def require_new_format[F: Callable[..., Any]](func: F) -> F:
    """Decorator to require new point format, converting legacy automatically.

    Args:
        func: Function to decorate

    Returns:
        Decorated function that only works with new formats
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Convert all point-like arguments to new format
        new_args = []
        for arg in args:
            if _looks_like_points_data(arg):
                new_args.append(ensure_point_collection(arg))
            else:
                new_args.append(arg)

        return func(*new_args, **kwargs)

    return cast(F, wrapper)

# Compatibility layer for existing service methods

class LegacyPointOperations:
    """Compatibility layer providing legacy point operations using new models.

    This class provides static methods that replicate the functionality of
    existing point manipulation functions but using the new data models
    internally for better performance and type safety.
    """

    @staticmethod
    def normalize_point(point: LegacyPointTuple) -> tuple[int, float, float, str]:
        """Legacy-compatible normalize_point using new models.

        Args:
            point: Point tuple in legacy format

        Returns:
            Normalized 4-tuple (frame, x, y, status)
        """
        curve_point = CurvePoint.from_tuple(point)
        return curve_point.to_tuple4()

    @staticmethod
    def set_point_status(point: LegacyPointTuple, status: str) -> LegacyPointTuple:
        """Legacy-compatible set_point_status using new models.

        Args:
            point: Point tuple in legacy format
            status: New status string

        Returns:
            Updated point tuple
        """
        curve_point = CurvePoint.from_tuple(point)
        new_status = PointStatus.from_legacy(status)
        updated_point = curve_point.with_status(new_status)
        return updated_point.to_legacy_tuple()

    @staticmethod
    def update_point_coords(point: LegacyPointTuple, x: float, y: float) -> LegacyPointTuple:
        """Legacy-compatible update_point_coords using new models.

        Args:
            point: Point tuple in legacy format
            x: New X coordinate
            y: New Y coordinate

        Returns:
            Updated point tuple
        """
        curve_point = CurvePoint.from_tuple(point)
        updated_point = curve_point.with_coordinates(x, y)
        return updated_point.to_legacy_tuple()

# Testing and validation utilities

def validate_migration_consistency(legacy_points: "PointsList", migrated_collection: PointCollection) -> bool:
    """Validate that migration preserved data integrity.

    Args:
        legacy_points: Original legacy format points
        migrated_collection: Migrated PointCollection

    Returns:
        True if migration was consistent

    Raises:
        MigrationError: If inconsistencies are found
    """
    if len(legacy_points) != len(migrated_collection):
        raise MigrationError(f"Length mismatch: {len(legacy_points)} vs {len(migrated_collection)}")

    # Convert back to legacy and compare
    round_trip = migrated_collection.to_tuples()

    for i, (original, round_trip_point) in enumerate(zip(legacy_points, round_trip)):
        # Normalize both for comparison
        orig_normalized = LegacyPointOperations.normalize_point(original)
        rt_normalized = LegacyPointOperations.normalize_point(round_trip_point)

        if orig_normalized != rt_normalized:
            raise MigrationError(f"Point {i} mismatch: {orig_normalized} vs {rt_normalized}")

    return True

def benchmark_migration_performance(points: "PointsList", iterations: int = 10) -> dict[str, float]:
    """Benchmark migration performance for optimization.

    Args:
        points: Points to benchmark migration with
        iterations: Number of iterations for timing

    Returns:
        Dict with timing results
    """
    import time

    results = {}

    # Benchmark standard migration
    start_time = time.perf_counter()
    for _ in range(iterations):
        collection = migrate_points_list(points)
    end_time = time.perf_counter()
    results["standard_migration"] = (end_time - start_time) / iterations

    # Benchmark bulk migration if dataset is large
    if len(points) > 1000:
        start_time = time.perf_counter()
        for _ in range(iterations):
            collection = bulk_migrate_points(points)
        end_time = time.perf_counter()
        results["bulk_migration"] = (end_time - start_time) / iterations

    # Benchmark round-trip conversion
    collection = migrate_points_list(points)
    start_time = time.perf_counter()
    for _ in range(iterations):
        _legacy = ensure_legacy_format(collection)  # Result unused, timing only
    end_time = time.perf_counter()
    results["export_to_legacy"] = (end_time - start_time) / iterations

    return results

# Helper functions

def _looks_like_points_data(obj: Any) -> bool:
    """Check if object looks like points data (heuristic).

    Args:
        obj: Object to check

    Returns:
        True if object appears to be points data
    """
    return is_legacy_points_list(obj) or is_point_collection(obj) or is_curve_point_list(obj)

# Migration status tracking

class MigrationTracker:
    """Track migration progress across the codebase.

    This utility helps track which parts of the codebase have been migrated
    to the new point format and which still use legacy formats.
    """

    def __init__(self):
        self.legacy_usage_count = 0
        self.new_format_usage_count = 0
        self.migration_warnings = []

    def record_legacy_usage(self, location: str, details: str = "") -> None:
        """Record usage of legacy format.

        Args:
            location: Where legacy format was used
            details: Additional details about the usage
        """
        self.legacy_usage_count += 1
        self.migration_warnings.append(f"Legacy format used at {location}: {details}")

    def record_new_format_usage(self, location: str) -> None:
        """Record usage of new format.

        Args:
            location: Where new format was used
        """
        self.new_format_usage_count += 1

    def get_migration_report(self) -> dict[str, Any]:
        """Get migration status report.

        Returns:
            Dict with migration statistics
        """
        total_usage = self.legacy_usage_count + self.new_format_usage_count
        if total_usage == 0:
            migration_percentage = 0.0
        else:
            migration_percentage = (self.new_format_usage_count / total_usage) * 100

        return {
            "legacy_usage": self.legacy_usage_count,
            "new_format_usage": self.new_format_usage_count,
            "total_usage": total_usage,
            "migration_percentage": migration_percentage,
            "warnings": self.migration_warnings,
        }

# Global migration tracker instance
migration_tracker = MigrationTracker()
