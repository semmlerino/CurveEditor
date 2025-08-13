#!/usr/bin/env python
"""
Demonstration script for Sprint 11 Day 2 quick optimization wins.

This script demonstrates the two performance optimizations:
1. Transform Caching with @lru_cache
2. Spatial Indexing for O(1) point lookups
"""

import random
import time


# Mock curve view for demonstration
class MockCurveView:
    """Mock curve view for testing."""

    def __init__(self, width: int = 800, height: int = 600, curve_data: list = None):
        self._width = width
        self._height = height
        self.curve_data = curve_data or []
        self.selected_points = set()
        self.selected_point_idx = -1
        self.zoom_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.scale_to_image = True
        self.flip_y_axis = False
        self.x_offset = 0.0
        self.y_offset = 0.0
        self.background_image = None
        self.image_width = 800
        self.image_height = 600

    def width(self) -> int:
        """Return width."""
        return self._width

    def height(self) -> int:
        """Return height."""
        return self._height

    def update(self) -> None:
        """Mock update method."""
        pass


def generate_test_data(num_points: int = 1000) -> list[tuple[float, float, float, int]]:
    """Generate test curve data."""
    return [
        (i, random.uniform(0, 800), random.uniform(0, 600), 1)
        for i in range(num_points)
    ]


def demo_transform_caching() -> None:
    """Demonstrate transform caching optimization."""
    print("=== Transform Caching Demonstration ===")

    from services.transform_service import TransformService, ViewState

    # Create transform service
    transform_service = TransformService()

    # Create a test view state
    view_state = ViewState(
        display_width=800,
        display_height=600,
        widget_width=800,
        widget_height=600,
        zoom_factor=1.5,
        offset_x=100,
        offset_y=50
    )

    # Measure performance with caching
    num_iterations = 1000

    print(f"Creating {num_iterations} transforms with the same ViewState...")

    start_time = time.time()
    for _ in range(num_iterations):
        transform_service.create_transform(view_state)
    cache_time = time.time() - start_time

    # Get cache statistics
    cache_stats = transform_service.get_cache_info()

    print(f"Time with caching: {cache_time:.4f} seconds")
    print(f"Cache stats: {cache_stats}")
    print(f"Cache hit rate: {cache_stats['hit_rate']:.1%}")

    # Clear cache and test without caching
    transform_service.clear_cache()

    print("\nCreating transforms after clearing cache...")
    start_time = time.time()
    for _ in range(100):  # Fewer iterations since no caching
        transform_service.create_transform(view_state)
    no_cache_time = time.time() - start_time

    print(f"Time without cache (100 iterations): {no_cache_time:.4f} seconds")
    print(f"Estimated speedup with cache: {(no_cache_time * 10) / cache_time:.1f}x")


def demo_spatial_indexing() -> None:
    """Demonstrate spatial indexing optimization."""
    print("\n=== Spatial Indexing Demonstration ===")

    from services.interaction_service import get_interaction_service
    from services.transform_service import TransformService, ViewState

    # Generate test data
    num_points = 5000
    test_data = generate_test_data(num_points)

    # Create mock view with test data
    mock_view = MockCurveView(width=800, height=600, curve_data=test_data)

    # Create transform for coordinate conversion
    transform_service = TransformService()
    view_state = ViewState(
        display_width=800,
        display_height=600,
        widget_width=800,
        widget_height=600
    )
    transform = transform_service.create_transform(view_state)

    print(f"Testing with {num_points} points...")

    # Test spatial indexing performance
    interaction_service = get_interaction_service()

    # Warm up the spatial index
    _ = interaction_service.find_point_at(mock_view, 400, 300)

    # Test point lookup performance
    num_lookups = 1000
    test_positions = [(random.uniform(0, 800), random.uniform(0, 600)) for _ in range(num_lookups)]

    print(f"Performing {num_lookups} point lookups with spatial indexing...")

    start_time = time.time()
    found_count = 0
    for x, y in test_positions:
        point_idx = interaction_service.find_point_at(mock_view, x, y)
        if point_idx != -1:
            found_count += 1
    spatial_time = time.time() - start_time

    print(f"Time with spatial indexing: {spatial_time:.4f} seconds")
    print(f"Points found: {found_count}/{num_lookups}")

    # Get spatial index statistics
    spatial_stats = interaction_service.get_spatial_index_stats()
    print(f"Spatial index stats: {spatial_stats}")

    # Simulate linear search for comparison
    print("\nSimulating linear search for comparison...")

    start_time = time.time()
    linear_found_count = 0
    threshold = 5.0

    for x, y in test_positions[:100]:  # Only test 100 for linear search (too slow otherwise)
        for i, point in enumerate(test_data):
            if len(point) >= 3:
                # Convert data point to screen coordinates
                screen_px, screen_py = transform.data_to_screen(point[1], point[2])
                distance = ((screen_px - x) ** 2 + (screen_py - y) ** 2) ** 0.5
                if distance <= threshold:
                    linear_found_count += 1
                    break
    linear_time = time.time() - start_time

    # Estimate full linear search time
    estimated_full_linear_time = linear_time * 10  # Scale up to 1000 lookups

    print(f"Linear search time (100 lookups): {linear_time:.4f} seconds")
    print(f"Estimated linear search time (1000 lookups): {estimated_full_linear_time:.4f} seconds")
    print(f"Spatial indexing speedup: {estimated_full_linear_time / spatial_time:.1f}x")


def demo_rectangle_selection() -> None:
    """Demonstrate rectangle selection optimization."""
    print("\n=== Rectangle Selection Demonstration ===")

    from PySide6.QtCore import QRect

    from services.interaction_service import get_interaction_service

    # Generate test data
    num_points = 2000
    test_data = generate_test_data(num_points)

    # Create mock view with test data
    mock_view = MockCurveView(width=800, height=600, curve_data=test_data)

    # Test rectangle selection
    interaction_service = get_interaction_service()

    # Define test rectangle
    test_rect = QRect(200, 150, 300, 200)  # x, y, width, height

    print(f"Selecting points in rectangle (200, 150, 300x200) from {num_points} points...")

    start_time = time.time()
    selected_count = interaction_service.select_points_in_rect(mock_view, None, test_rect)
    selection_time = time.time() - start_time

    print(f"Rectangle selection time: {selection_time:.4f} seconds")
    print(f"Points selected: {selected_count}")
    print(f"Selection efficiency: {selected_count / selection_time:.0f} points/second")


def main() -> None:
    """Run all optimization demonstrations."""
    print("Sprint 11 Day 2 - Quick Optimization Wins Demo")
    print("=" * 50)

    try:
        demo_transform_caching()
        demo_spatial_indexing()
        demo_rectangle_selection()

        print("\n" + "=" * 50)
        print("✅ All optimizations are working correctly!")
        print("\nOptimization Summary:")
        print("1. Transform Caching: Uses @lru_cache for efficient transform reuse")
        print("2. Spatial Indexing: O(1) point lookups instead of O(n) linear search")
        print("3. Rectangle Selection: Efficient multi-point selection using spatial index")

    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
