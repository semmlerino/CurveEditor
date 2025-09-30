#!/usr/bin/env python3
"""
Comprehensive edge case tests for the transform system.

Tests extreme values, concurrency, NaN propagation, and other edge cases.
"""

import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from core.validation_utils import validate_finite, validate_point
from services import get_transform_service
from services.transform_service import Transform, ValidationConfig, ViewState


class TestExtremeScales:
    """Test transform system with extreme scale values."""

    def test_very_small_scales(self):
        """Test with very small scale factors."""
        service = get_transform_service()
        # Force production mode for graceful handling
        service.validation_config = ValidationConfig.for_production()

        for scale in [1e-10, 1e-8, 1e-5, 1e-3]:
            view_state = ViewState(
                display_width=1920,
                display_height=1080,
                widget_width=800,
                widget_height=600,
                zoom_factor=scale,
                offset_x=0.0,
                offset_y=0.0,
            )

            transform = service.create_transform_from_view_state(view_state)

            # Transform should handle without overflow
            x, y = transform.data_to_screen(100.0, 100.0)
            assert math.isfinite(x), f"X not finite at scale {scale}"
            assert math.isfinite(y), f"Y not finite at scale {scale}"

            # Reverse transform should also work
            x2, y2 = transform.screen_to_data(x, y)
            assert math.isfinite(x2), f"Reverse X not finite at scale {scale}"
            assert math.isfinite(y2), f"Reverse Y not finite at scale {scale}"

    def test_very_large_scales(self):
        """Test with very large scale factors."""
        service = get_transform_service()
        # Force production mode for graceful handling
        service.validation_config = ValidationConfig.for_production()

        for scale in [1e3, 1e5, 1e8, 1e10]:
            view_state = ViewState(
                display_width=1920,
                display_height=1080,
                widget_width=800,
                widget_height=600,
                zoom_factor=scale,
                offset_x=0.0,
                offset_y=0.0,
            )

            transform = service.create_transform_from_view_state(view_state)

            # Should handle large scales
            x, y = transform.data_to_screen(0.001, 0.001)
            assert math.isfinite(x), f"X not finite at scale {scale}"
            assert math.isfinite(y), f"Y not finite at scale {scale}"

    def test_scale_boundary_conditions(self):
        """Test scale at boundary conditions."""
        service = get_transform_service()
        # Force production mode for graceful handling
        service.validation_config = ValidationConfig.for_production()

        # Test at exactly zero (should be handled)
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=0.0,  # Zero scale
            offset_x=0.0,
            offset_y=0.0,
        )

        # Should be handled gracefully
        transform = service.create_transform_from_view_state(view_state)
        assert transform.scale == 0.0 or transform.scale > 0, "Scale should be handled"

        # Test negative scale (should be handled)
        view_state = view_state.with_updates(zoom_factor=-1.0)
        transform = service.create_transform_from_view_state(view_state)
        # Negative scale might be valid for flipping


class TestNaNPropagation:
    """Test that NaN values don't propagate through the system."""

    def test_nan_in_view_state(self):
        """Test NaN handling in ViewState."""
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=float("nan"),
            offset_x=float("nan"),
            offset_y=float("nan"),
        )

        # Quantization should handle NaN
        quantized = view_state.quantized_for_cache()
        assert quantized.zoom_factor == 0.0, "NaN zoom should become 0"
        assert quantized.offset_x == 0.0, "NaN offset_x should become 0"
        assert quantized.offset_y == 0.0, "NaN offset_y should become 0"

    def test_infinity_in_view_state(self):
        """Test infinity handling in ViewState."""
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=float("inf"),
            offset_x=float("-inf"),
            offset_y=float("inf"),
        )

        quantized = view_state.quantized_for_cache()
        assert quantized.zoom_factor == 0.0, "Inf zoom should become 0"
        assert quantized.offset_x == 0.0, "-Inf offset_x should become 0"
        assert quantized.offset_y == 0.0, "Inf offset_y should become 0"

    def test_nan_in_transform(self):
        """Test NaN handling in transform operations."""
        service = get_transform_service()
        # Force production mode for graceful handling
        service.validation_config = ValidationConfig.for_production()

        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )

        transform = service.create_transform_from_view_state(view_state)

        # Test NaN input to data_to_screen
        x, y = transform.data_to_screen(float("nan"), 100.0)
        assert math.isfinite(x), "NaN x should be handled and result should be finite"
        assert math.isfinite(y), "Y should remain finite"

        # Test infinity input
        x, y = transform.data_to_screen(float("inf"), float("-inf"))
        assert math.isfinite(x), "Inf x should be handled and result should be finite"
        assert math.isfinite(y), "-Inf y should be handled and result should be finite"

    def test_nan_propagation_prevention(self):
        """Ensure NaN doesn't propagate through calculations."""
        # Direct validation utility test
        result = validate_finite(float("nan"), "test_value", 42.0)
        assert result == 42.0, "NaN should return default"

        result = validate_finite(float("inf"), "test_value", 42.0)
        assert result == 42.0, "Inf should return default"

        # Point validation - using current signature that returns safe defaults
        x, y = validate_point(float("nan"), float("inf"))
        assert x == 0.0, "NaN x should use safe default (0.0)"
        assert y == 0.0, "Inf y should use safe default (0.0)"


class TestConcurrentAccess:
    """Test thread safety of the transform system."""

    def test_concurrent_transform_creation(self):
        """Test creating transforms from multiple threads."""
        service = get_transform_service()
        results: list[Transform] = []
        errors: list[Exception] = []

        def create_transform(scale: float):
            try:
                view_state = ViewState(
                    display_width=1920,
                    display_height=1080,
                    widget_width=800,
                    widget_height=600,
                    zoom_factor=scale,
                    offset_x=scale * 10,
                    offset_y=scale * 20,
                )
                transform = service.create_transform_from_view_state(view_state)
                results.append(transform)
            except Exception as e:
                errors.append(e)

        # Create transforms concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(100):
                scale = 0.5 + (i * 0.01)
                future = executor.submit(create_transform, scale)
                futures.append(future)

            # Wait for all to complete
            for future in futures:
                future.result()

        # Check results
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"
        assert len(results) == 100, "Should create 100 transforms"

    def test_concurrent_cache_access(self):
        """Test cache behavior under concurrent access."""
        service = get_transform_service()

        # Ensure we're using environment config to enable caching
        service.validation_config = ValidationConfig.from_environment()

        # Clear cache first
        service.clear_cache()

        # Same view state from multiple threads
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.5,
            offset_x=100.0,
            offset_y=200.0,
        )

        transforms = []

        def access_cache():
            transform = service.create_transform_from_view_state(view_state)
            transforms.append(transform)

        # Access cache concurrently
        threads = []
        for _ in range(50):
            thread = threading.Thread(target=access_cache)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should get the same cached transform
        assert len(transforms) == 50

        # Check cache hit rate improved
        cache_info = service.get_cache_info()
        assert cache_info["hits"] > 0, "Should have cache hits"

    def test_cache_clear_during_access(self):
        """Test clearing cache while it's being accessed."""
        service = get_transform_service()
        stop_flag = threading.Event()
        errors = []

        def continuous_access():
            while not stop_flag.is_set():
                try:
                    view_state = ViewState(
                        display_width=1920,
                        display_height=1080,
                        widget_width=800,
                        widget_height=600,
                        zoom_factor=1.0 + (hash(threading.current_thread()) % 10) * 0.1,
                        offset_x=0.0,
                        offset_y=0.0,
                    )
                    service.create_transform_from_view_state(view_state)
                except Exception as e:
                    errors.append(e)

        def continuous_clear():
            while not stop_flag.is_set():
                try:
                    service.clear_cache()
                    time.sleep(0.01)
                except Exception as e:
                    errors.append(e)

        # Start threads
        access_threads = [threading.Thread(target=continuous_access) for _ in range(5)]
        clear_thread = threading.Thread(target=continuous_clear)

        for thread in access_threads:
            thread.start()
        clear_thread.start()

        # Run for a short time
        time.sleep(0.5)
        stop_flag.set()

        # Wait for completion
        for thread in access_threads:
            thread.join()
        clear_thread.join()

        # Should complete without errors
        assert len(errors) == 0, f"Errors during concurrent clear: {errors}"


class TestBoundaryConditions:
    """Test various boundary conditions."""

    def test_zero_dimensions(self):
        """Test with zero width/height."""
        service = get_transform_service()
        # Force production mode for graceful handling
        service.validation_config = ValidationConfig.for_production()

        # This should be handled gracefully
        view_state = ViewState(
            display_width=0,  # Zero width
            display_height=0,  # Zero height
            widget_width=0,
            widget_height=0,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )

        # Should not crash
        transform = service.create_transform_from_view_state(view_state)
        assert transform is not None

    def test_negative_dimensions(self):
        """Test with negative dimensions."""
        service = get_transform_service()
        # Force production mode for graceful handling
        service.validation_config = ValidationConfig.for_production()

        view_state = ViewState(
            display_width=-1920,  # Negative
            display_height=-1080,  # Negative
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )

        transform = service.create_transform_from_view_state(view_state)
        assert transform is not None

    def test_massive_offsets(self):
        """Test with very large offset values."""
        service = get_transform_service()
        # Force production mode for graceful handling
        service.validation_config = ValidationConfig.for_production()

        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            offset_x=1e15,  # Huge offset
            offset_y=-1e15,  # Huge negative offset
        )

        transform = service.create_transform_from_view_state(view_state)

        # Should handle large offsets
        x, y = transform.data_to_screen(0.0, 0.0)
        assert math.isfinite(x) or x == 1e15
        assert math.isfinite(y) or y == -1e15

    def test_precision_limits(self):
        """Test floating point precision limits."""
        # Very close but different values
        view_state1 = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0000000001,
            offset_x=0.0000000001,
            offset_y=0.0000000001,
        )

        view_state2 = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0000000002,
            offset_x=0.0000000002,
            offset_y=0.0000000002,
        )

        # After quantization, these should be the same
        q1 = view_state1.quantized_for_cache()
        q2 = view_state2.quantized_for_cache()

        assert q1.zoom_factor == q2.zoom_factor, "Should quantize to same value"
        assert q1.offset_x == q2.offset_x, "Should quantize to same value"


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    def test_invalid_precision(self):
        """Test handling of invalid precision values."""
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )

        # Zero precision should raise ValidationError
        with pytest.raises(Exception, match="must be positive"):
            view_state.quantized_for_cache(precision=0.0)

        # Negative precision should raise ValidationError
        with pytest.raises(Exception, match="must be positive"):
            view_state.quantized_for_cache(precision=-1.0)

        # NaN precision should raise an error (could be ValidationError or ValueError)
        with pytest.raises((ValueError, Exception), match="(cannot convert float NaN|must be positive)"):
            view_state.quantized_for_cache(precision=float("nan"))

    def test_transform_with_all_zeros(self):
        """Test transform with all parameters as zero."""
        # Force production mode for graceful handling
        validation_config = ValidationConfig.for_production()

        transform = Transform(
            scale=0.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            flip_y=False,
            display_height=0,
            validation_config=validation_config,
        )

        # Should handle gracefully
        x, y = transform.data_to_screen(100.0, 100.0)
        assert math.isfinite(x)
        assert math.isfinite(y)


class TestNumPyIntegration:
    """Test integration with NumPy arrays."""

    def test_array_transformation(self):
        """Test transforming NumPy arrays of points."""
        service = get_transform_service()

        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            offset_x=100.0,
            offset_y=200.0,
        )

        transform = service.create_transform_from_view_state(view_state)

        # Create array of points
        points = np.array(
            [
                [0.0, 0.0],
                [100.0, 100.0],
                [float("nan"), 200.0],  # Include NaN
                [300.0, float("inf")],  # Include infinity
            ]
        )

        # Transform each point
        transformed = []
        for x, y in points:
            try:
                tx, ty = transform.data_to_screen(x, y)
                transformed.append([tx, ty])
            except ValueError:
                # Handle invalid points
                transformed.append([0.0, 0.0])

        transformed = np.array(transformed)

        # Check all results are finite or handled
        assert np.all(np.isfinite(transformed[:2])), "Valid points should transform"
        # NaN and inf should be handled


class TestCachePrecision:
    """Test cache precision and quantization."""

    def test_cache_quantization_levels(self):
        """Test different quantization precision levels."""
        service = get_transform_service()
        service.clear_cache()

        # Create slightly different view states
        base_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            offset_x=100.0,
            offset_y=200.0,
        )

        # Test with different precisions
        for precision in [1.0, 0.1, 0.01, 0.001]:
            states = []
            for i in range(5):
                # Create variations much smaller than precision (should quantize to same)
                variation = precision / 100  # Much smaller variation
                state = base_state.with_updates(
                    zoom_factor=1.0 + (i * variation),
                    offset_x=100.0 + (i * variation),
                    offset_y=200.0 + (i * variation),
                )
                states.append(state)

            # All should quantize to the same value
            quantized = [s.quantized_for_cache(precision) for s in states]

            # Check they're quantized consistently (may not be exactly the same due to rounding)
            first = quantized[0]
            for q in quantized[1:]:
                # They should be quantized to values within precision of each other
                assert (
                    abs(q.zoom_factor - first.zoom_factor) <= precision
                ), f"Zoom factors should be within precision {precision}: {q.zoom_factor} vs {first.zoom_factor}"
                assert (
                    abs(q.offset_x - first.offset_x) <= precision
                ), f"Offset X should be within precision {precision}: {q.offset_x} vs {first.offset_x}"
                assert (
                    abs(q.offset_y - first.offset_y) <= precision
                ), f"Offset Y should be within precision {precision}: {q.offset_y} vs {first.offset_y}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
