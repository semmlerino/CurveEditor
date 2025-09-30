#!/usr/bin/env python
"""
Test to reproduce and profile the zoom floating bug in CurveEditor.

This test simulates the exact conditions that cause curves to float during
zoom operations by analyzing cache behavior and transform precision.
"""

import logging
import math
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.transform_service import TransformService, ViewState
from tools.profiling.cache_profiler import cache_profiler, profile_zoom_operation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zoom_cache_test")


def create_test_view_state(zoom_factor=1.0, base_scale=0.5, pan_x=0.0, pan_y=0.0):
    """Create a test ViewState for zoom operations."""
    return ViewState(
        display_width=1920,
        display_height=1080,
        widget_width=800,
        widget_height=600,
        zoom_factor=zoom_factor,
        base_scale=base_scale,
        offset_x=pan_x,
        offset_y=pan_y,
        scale_to_image=True,
        flip_y_axis=False,
        manual_x_offset=0.0,
        manual_y_offset=0.0,
        background_image=None,
        image_width=1920,
        image_height=1080,
    )


def test_quantization_precision():
    """Test quantization precision effects on cache keys."""
    logger.info("Testing quantization precision effects...")

    # Create base view state
    create_test_view_state(zoom_factor=1.0)

    # Test small zoom changes that might cause precision issues
    zoom_values = [1.0, 1.001, 1.002, 1.003, 1.01, 1.02, 1.05, 1.1]

    quantized_states = []
    for zoom in zoom_values:
        state = create_test_view_state(zoom_factor=zoom)
        quantized = state.quantized_for_cache()
        quantized_states.append((zoom, quantized.zoom_factor))

        # Record precision analysis
        cache_profiler.analyze_precision_loss(zoom, quantized.zoom_factor, "zoom_factor")

    logger.info("Quantization results:")
    for original, quantized in quantized_states:
        loss = abs(original - quantized)
        logger.info(f"  {original:.4f} -> {quantized:.4f} (loss: {loss:.6f})")

    # Check if small changes are being quantized to same value
    unique_quantized = set(q for _, q in quantized_states)
    logger.info(f"  Unique quantized values: {len(unique_quantized)}/{len(zoom_values)}")

    if len(unique_quantized) < len(zoom_values):
        logger.warning("⚠ Quantization is merging distinct zoom values!")


def test_cache_key_stability():
    """Test cache key stability with identical transformations."""
    logger.info("Testing cache key stability...")

    # Create identical view states
    state1 = create_test_view_state(zoom_factor=1.5, base_scale=0.8)
    state2 = create_test_view_state(zoom_factor=1.5, base_scale=0.8)

    # Quantize both
    q1 = state1.quantized_for_cache()
    q2 = state2.quantized_for_cache()

    # Check if they produce identical hashes
    hash1 = hash(q1)
    hash2 = hash(q2)

    logger.info(f"State 1 hash: {hash1}")
    logger.info(f"State 2 hash: {hash2}")
    logger.info(f"Hashes match: {hash1 == hash2}")

    if hash1 != hash2:
        logger.error("🐛 Identical view states produce different hashes!")

    # Test with floating point variations
    state3 = create_test_view_state(zoom_factor=1.500001, base_scale=0.800001)
    q3 = state3.quantized_for_cache()
    hash3 = hash(q3)

    logger.info(f"Similar state hash: {hash3}")
    logger.info(f"Similar quantized to same: {hash1 == hash3}")


def simulate_zoom_sequence():
    """Simulate a realistic zoom operation sequence."""
    logger.info("Simulating zoom sequence...")

    # Start with base zoom
    initial_zoom = 1.0
    base_scale = 0.5

    # Zoom sequence: zoom in, then out, then in again
    zoom_sequence = [1.0, 1.2, 1.5, 2.0, 2.5, 2.0, 1.5, 1.2, 1.0, 1.5, 2.0]

    transform_service = TransformService()
    transform_hashes = []

    with profile_zoom_operation(initial_zoom, zoom_sequence[-1]):
        for i, zoom in enumerate(zoom_sequence):
            logger.info(f"Zoom step {i+1}: {zoom}x")

            # Create view state for this zoom level
            view_state = create_test_view_state(zoom_factor=zoom, base_scale=base_scale)

            # Get transform (this will use caching)
            start_time = time.time()
            transform = transform_service.create_transform_from_view_state(view_state)
            elapsed = time.time() - start_time

            # Track transform stability
            transform_hash = getattr(transform, "stability_hash", "unknown")
            transform_hashes.append(transform_hash)

            cache_profiler.track_transform_stability(transform_hash, f"zoom={zoom},base={base_scale}")

            # Log performance
            logger.info(f"  Transform time: {elapsed*1000:.3f}ms")
            logger.info(f"  Transform hash: {transform_hash[:12]}")

            # Simulate some data transformations to stress the cache
            test_points = [(100, 200), (500, 400), (1000, 800)]
            for x, y in test_points:
                screen_x, screen_y = transform.data_to_screen(x, y)
                data_x, data_y = transform.screen_to_data(screen_x, screen_y)

                # Check for precision loss in round-trip
                loss = math.sqrt((x - data_x) ** 2 + (y - data_y) ** 2)
                if loss > 0.01:  # More than 0.01 pixel error
                    logger.warning(f"    Round-trip precision loss: {loss:.4f} pixels")

    # Analyze transform stability
    unique_transforms = set(transform_hashes)
    logger.info(f"Unique transforms in sequence: {len(unique_transforms)}/{len(zoom_sequence)}")

    # Check for repeated zoom levels
    zoom_to_hash = {}
    for zoom, transform_hash in zip(zoom_sequence, transform_hashes):
        if zoom in zoom_to_hash:
            if zoom_to_hash[zoom] != transform_hash:
                logger.error(f"🐛 Same zoom level ({zoom}) produced different transforms!")
                logger.error(f"    First: {zoom_to_hash[zoom][:12]}")
                logger.error(f"    Second: {transform_hash[:12]}")
        else:
            zoom_to_hash[zoom] = transform_hash


def test_base_scale_vs_zoom_factor():
    """Test the interaction between base_scale and zoom_factor in caching."""
    logger.info("Testing base_scale vs zoom_factor interaction...")

    transform_service = TransformService()

    # Test scenarios where base_scale and zoom_factor change independently
    scenarios = [
        # (zoom_factor, base_scale, scenario_name)
        (1.0, 0.5, "baseline"),
        (2.0, 0.5, "zoom_only_change"),
        (1.0, 1.0, "base_scale_only_change"),
        (2.0, 1.0, "both_change"),
        (2.0, 0.5, "back_to_zoom_only"),  # Should match scenario 2
    ]

    transforms = []
    for zoom_factor, base_scale, name in scenarios:
        logger.info(f"Scenario: {name} (zoom={zoom_factor}, base_scale={base_scale})")

        view_state = create_test_view_state(zoom_factor=zoom_factor, base_scale=base_scale)

        start_time = time.time()
        transform = transform_service.create_transform_from_view_state(view_state)
        elapsed = time.time() - start_time

        transforms.append((name, transform, elapsed))

        # Calculate total scale
        total_scale = zoom_factor * base_scale
        logger.info(f"  Total scale: {total_scale}")
        logger.info(f"  Transform time: {elapsed*1000:.3f}ms")
        logger.info(f"  Transform hash: {getattr(transform, 'stability_hash', 'unknown')[:12]}")

        # Test a sample transformation
        screen_x, screen_y = transform.data_to_screen(100, 100)
        logger.info(f"  (100,100) -> ({screen_x:.2f},{screen_y:.2f})")

    # Check if identical total scales produce identical transforms
    scenario2_transform = next(t for name, t, _ in transforms if name == "zoom_only_change")
    scenario5_transform = next(t for name, t, _ in transforms if name == "back_to_zoom_only")

    hash2 = getattr(scenario2_transform, "stability_hash", "unknown")
    hash5 = getattr(scenario5_transform, "stability_hash", "unknown")

    if hash2 == hash5:
        logger.info("✓ Identical zoom scenarios produce identical transforms")
    else:
        logger.error("🐛 Identical zoom scenarios produce different transforms!")
        logger.error(f"    Scenario 2 hash: {hash2}")
        logger.error(f"    Scenario 5 hash: {hash5}")


def test_cache_invalidation_impact():
    """Test impact of cache invalidation on performance."""
    logger.info("Testing cache invalidation impact...")

    transform_service = TransformService()

    # Get baseline performance with warm cache
    view_state = create_test_view_state(zoom_factor=1.5)

    # Warm up the cache
    transform_service.create_transform_from_view_state(view_state)

    # Measure cached access time
    start_time = time.time()
    for _ in range(100):
        transform_service.create_transform_from_view_state(view_state)
    cached_time = time.time() - start_time

    logger.info(f"100 cached accesses: {cached_time*1000:.3f}ms")

    # Clear cache and measure cold access
    cache_profiler.record_cache_operation("invalidate", "manual_test")
    transform_service.clear_cache()

    start_time = time.time()
    for _ in range(100):
        # Create slightly different states to prevent caching
        zoom = 1.5 + (0.001 * (_ % 10))  # Small variations
        test_state = create_test_view_state(zoom_factor=zoom)
        transform_service.create_transform_from_view_state(test_state)
    cold_time = time.time() - start_time

    logger.info(f"100 cold accesses: {cold_time*1000:.3f}ms")
    logger.info(f"Cache speedup: {cold_time/cached_time:.1f}x")

    if cold_time / cached_time < 5:  # Less than 5x speedup
        logger.warning("⚠ Cache providing less benefit than expected")


def test_floating_detection():
    """Test conditions that cause floating behavior."""
    logger.info("Testing floating detection conditions...")

    transform_service = TransformService()

    # Create a sequence that might cause floating
    base_zoom = 1.0
    micro_changes = [base_zoom + 0.0001 * i for i in range(100)]

    prev_screen_pos = None
    floating_detected = False

    with profile_zoom_operation(micro_changes[0], micro_changes[-1]):
        for i, zoom in enumerate(micro_changes):
            view_state = create_test_view_state(zoom_factor=zoom)
            transform = transform_service.create_transform_from_view_state(view_state)

            # Transform a fixed data point
            data_x, data_y = 100, 100
            screen_x, screen_y = transform.data_to_screen(data_x, data_y)

            if prev_screen_pos:
                # Check if the point position is stable for small zoom changes
                dx = abs(screen_x - prev_screen_pos[0])
                dy = abs(screen_y - prev_screen_pos[1])
                movement = math.sqrt(dx * dx + dy * dy)

                # For micro changes, movement should be tiny
                if movement > 0.1 and i > 0:  # More than 0.1 pixel movement
                    expected_movement = abs(zoom - micro_changes[i - 1]) * 100  # Rough estimate
                    if movement > expected_movement * 2:  # More than twice expected
                        logger.warning(f"  Step {i}: Unexpected movement {movement:.3f} pixels")
                        floating_detected = True

            prev_screen_pos = (screen_x, screen_y)

            if i % 20 == 0:  # Log every 20th step
                logger.info(f"  Step {i}: zoom={zoom:.6f}, pos=({screen_x:.2f},{screen_y:.2f})")

    if floating_detected:
        logger.error("🐛 FLOATING BEHAVIOR DETECTED!")
    else:
        logger.info("✓ No floating behavior detected")


def run_comprehensive_test():
    """Run comprehensive cache profiling test."""
    logger.info("Starting comprehensive zoom cache profiling test...")

    # Enable profiling
    cache_profiler.enable()

    try:
        # Run individual tests
        test_quantization_precision()
        print("-" * 40)

        test_cache_key_stability()
        print("-" * 40)

        simulate_zoom_sequence()
        print("-" * 40)

        test_base_scale_vs_zoom_factor()
        print("-" * 40)

        test_cache_invalidation_impact()
        print("-" * 40)

        test_floating_detection()
        print("-" * 40)

        # Get transform service cache info
        from services import get_transform_service

        transform_service = get_transform_service()
        cache_info = transform_service.get_cache_info()

        logger.info("TransformService Cache Statistics:")
        logger.info(f"  Hit Rate: {cache_info['hit_rate']:.1%}")
        logger.info(f"  Total Hits: {cache_info['hits']}")
        logger.info(f"  Total Misses: {cache_info['misses']}")
        logger.info(f"  Cache Size: {cache_info['current_size']}/{cache_info['max_size']}")

        print("\n" + "=" * 80)
        print("FINAL PROFILING REPORT")
        print("=" * 80)
        print(cache_profiler.generate_report())

    finally:
        # Disable profiling
        cache_profiler.disable()


if __name__ == "__main__":
    run_comprehensive_test()
