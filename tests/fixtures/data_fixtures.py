"""
Data fixtures for testing.

Contains fixtures that provide test data, sample points, and data builders.
"""

import math
from typing import Any

import pytest

# Import the test data types
from tests.test_utilities import (
    Point4,
    PointsList,
    TestDataBuilder,
)


@pytest.fixture
def sample_points() -> PointsList:
    """Provide a small set of sample points for testing."""
    return [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]


@pytest.fixture
def large_sample_points() -> PointsList:
    """Provide a large set of sample points for performance testing."""
    return [(i, float(i * 10), float(i * 20)) for i in range(1, 101)]


@pytest.fixture
def sample_curve_data() -> list[Point4]:
    """Provide sample curve data for tests."""
    return TestDataBuilder.curve_data()


@pytest.fixture
def keyframe_curve_data() -> list[Point4]:
    """Provide curve data with keyframes for tests."""
    return TestDataBuilder.keyframe_data()


@pytest.fixture
def test_data_builder() -> TestDataBuilder:
    """Provide the test data builder for creating test data."""
    return TestDataBuilder()


@pytest.fixture
def interpolated_curve_data() -> list[Point4]:
    """Provide curve data with interpolated points."""
    return [
        (1, 0.0, 0.0, "keyframe"),
        (2, 10.0, 5.0, "interpolated"),
        (3, 20.0, 10.0, "interpolated"),
        (4, 30.0, 15.0, "keyframe"),
        (5, 25.0, 12.5, "interpolated"),
        (6, 20.0, 10.0, "keyframe"),
    ]


@pytest.fixture
def sparse_curve_data() -> list[Point4]:
    """Provide sparse curve data with gaps."""
    return [
        (1, 0.0, 0.0, "keyframe"),
        (10, 100.0, 50.0, "keyframe"),
        (20, 200.0, 100.0, "keyframe"),
        (50, 500.0, 250.0, "keyframe"),
    ]


@pytest.fixture
def invalid_curve_data() -> list[Any]:
    """Provide invalid curve data for error testing."""
    return [
        (1, "invalid", 200.0),  # Invalid x coordinate
        (2, 150.0, None),  # None y coordinate
        ("3", 200.0, 300.0),  # String frame number
        (4,),  # Incomplete tuple
        [5, 250.0, 350.0],  # List instead of tuple
    ]


@pytest.fixture
def edge_case_curve_data() -> list[Point4]:
    """Provide edge case curve data."""
    return [
        (0, 0.0, 0.0, "keyframe"),  # Zero values
        (-1, -100.0, -200.0, "keyframe"),  # Negative values
        (999999, 1e6, 1e6, "keyframe"),  # Large values
        (1, 1e-10, 1e-10, "keyframe"),  # Very small values
    ]


@pytest.fixture
def performance_test_data() -> list[Point4]:
    """Provide large dataset for performance testing."""
    import math

    data = []
    for i in range(10000):
        x = float(i)
        y = math.sin(i * 0.01) * 100
        status = "keyframe" if i % 10 == 0 else "interpolated"
        data.append((i, x, y, status))

    return data


@pytest.fixture
def animation_curve_data() -> list[Point4]:
    """Provide realistic animation curve data."""
    # Simulates a bouncing ball animation
    data = []
    for frame in range(0, 100):
        t = frame / 24.0  # Convert to seconds (24 fps)

        # Bouncing motion with decay
        height = abs(math.sin(t * 3.14159)) * 100 * math.exp(-t * 0.1)

        # Horizontal motion
        x_pos = frame * 2.0

        status = "keyframe" if frame % 5 == 0 else "interpolated"
        data.append((frame, x_pos, height, status))

    return data


@pytest.fixture
def multi_curve_data() -> dict[str, list[Point4]]:
    """Provide multiple named curves for testing."""
    return {
        "position_x": [
            (1, 0.0, 0.0, "keyframe"),
            (25, 100.0, 0.0, "keyframe"),
            (50, 200.0, 0.0, "keyframe"),
        ],
        "position_y": [
            (1, 0.0, 100.0, "keyframe"),
            (25, 0.0, 0.0, "keyframe"),
            (50, 0.0, 100.0, "keyframe"),
        ],
        "rotation": [
            (1, 0.0, 0.0, "keyframe"),
            (25, 0.0, 180.0, "keyframe"),
            (50, 0.0, 360.0, "keyframe"),
        ],
    }
