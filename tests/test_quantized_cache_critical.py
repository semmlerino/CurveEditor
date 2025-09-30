#!/usr/bin/env python3
"""
CRITICAL MISSING TESTS: ViewState.quantized_for_cache() method

These tests are essential to prevent cache misses due to floating-point precision issues
that could cause severe performance degradation.
"""

import os
import sys

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.transform_service import ViewState


class TestQuantizedCacheCritical:
    """Critical tests for ViewState.quantized_for_cache() method."""

    def test_quantized_for_cache_basic_precision(self):
        """Test basic quantization with default precision."""
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.234567,
            offset_x=50.123456,
            offset_y=25.987654,
        )

        quantized = view_state.quantized_for_cache()

        # Should round to 0.1 precision by default for offsets
        # Zoom uses finer precision (0.001 = 0.1/100) for smooth zoom performance
        assert quantized.zoom_factor == pytest.approx(1.235, abs=1e-10)  # 0.001 precision
        assert quantized.offset_x == pytest.approx(50.1, abs=1e-10)  # 0.1 precision
        assert quantized.offset_y == pytest.approx(26.0, abs=1e-10)  # 0.1 precision

        # Integer values should remain unchanged
        assert quantized.display_width == view_state.display_width
        assert quantized.display_height == view_state.display_height

    def test_quantized_for_cache_custom_precision(self):
        """Test quantization with custom precision values."""
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.23456,
            offset_x=50.6789,
            manual_x_offset=12.3456,
            manual_y_offset=98.7654,
        )

        # Test with 1.0 precision (round to integers for offsets)
        # Zoom uses 0.01 precision (1.0/100)
        quantized_1 = view_state.quantized_for_cache(precision=1.0)
        assert quantized_1.zoom_factor == pytest.approx(1.23, abs=1e-10)  # 0.01 precision
        assert quantized_1.offset_x == pytest.approx(51.0, abs=1e-10)  # 1.0 precision
        assert quantized_1.manual_x_offset == pytest.approx(12.0, abs=1e-10)  # 1.0 precision

        # Test with 0.01 precision (round to hundredths for offsets)
        # Zoom uses 0.0001 precision (0.01/100)
        quantized_01 = view_state.quantized_for_cache(precision=0.01)
        assert quantized_01.zoom_factor == pytest.approx(1.2346, abs=1e-10)  # 0.0001 precision
        assert quantized_01.offset_x == pytest.approx(50.68, abs=1e-10)  # 0.01 precision
        assert quantized_01.manual_y_offset == pytest.approx(98.77, abs=1e-10)  # 0.01 precision

    def test_quantized_cache_key_consistency(self):
        """Test that very similar values produce identical cache keys."""
        # Create two ViewStates with tiny differences
        state1 = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.23456789,
            offset_x=50.00001,
        )

        state2 = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.23456788,  # Tiny difference
            offset_x=50.00002,  # Tiny difference
        )

        # Their quantized versions should be identical
        quantized1 = state1.quantized_for_cache()
        quantized2 = state2.quantized_for_cache()

        assert quantized1.zoom_factor == quantized2.zoom_factor
        assert quantized1.offset_x == quantized2.offset_x

        # Convert to dict to compare all fields
        dict1 = quantized1.to_dict()
        dict2 = quantized2.to_dict()
        assert dict1 == dict2

    def test_quantized_boundary_values(self):
        """Test quantization with boundary and edge case values."""
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=0.05,  # Should round to 0.050 (using 0.001 precision)
            offset_x=-0.05,  # Should round to 0.0 (using 0.1 precision)
            offset_y=0.05,  # Should round to 0.0 (using 0.1 precision, banker's rounding)
            manual_x_offset=0.049,  # Should round to 0.0 (using 0.1 precision)
            manual_y_offset=0.051,  # Should round to 0.1 (using 0.1 precision)
        )

        quantized = view_state.quantized_for_cache()

        # zoom_factor uses 0.001 precision, others use 0.1 precision
        # Note: Python uses banker's rounding - round(0.5) = 0, round(1.5) = 2
        assert quantized.zoom_factor == pytest.approx(0.050, abs=1e-10)
        assert quantized.offset_x == pytest.approx(0.0, abs=1e-10)
        assert quantized.offset_y == pytest.approx(0.0, abs=1e-10)  # 0.05/0.1 = 0.5, rounds to 0
        assert quantized.manual_x_offset == pytest.approx(0.0, abs=1e-10)
        assert quantized.manual_y_offset == pytest.approx(0.1, abs=1e-10)

    def test_quantized_preserves_immutability(self):
        """Test that quantized_for_cache preserves ViewState immutability."""
        original = ViewState(
            display_width=1920, display_height=1080, widget_width=800, widget_height=600, zoom_factor=1.23456
        )

        quantized = original.quantized_for_cache()

        # Should be different instances
        assert quantized is not original

        # Original should be unchanged
        assert original.zoom_factor == pytest.approx(1.23456, abs=1e-10)

        # Should maintain dataclass frozen behavior
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            quantized.zoom_factor = 2.0  # type: ignore[misc]

    @pytest.mark.parametrize("precision", [0.001, 0.01, 0.1, 1.0, 10.0])
    def test_quantized_various_precisions(self, precision: float):
        """Test quantization with various precision values."""
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=12.3456789,
            offset_x=98.7654321,
        )

        quantized = view_state.quantized_for_cache(precision=precision)

        # Verify values are quantized to the specified precision
        # Zoom uses precision/100 for finer control (prevents cache misses)
        zoom_precision = precision / 100
        expected_zoom = round(12.3456789 / zoom_precision) * zoom_precision
        expected_offset = round(98.7654321 / precision) * precision

        assert quantized.zoom_factor == pytest.approx(expected_zoom, abs=1e-10)
        assert quantized.offset_x == pytest.approx(expected_offset, abs=1e-10)

    def test_quantized_negative_values(self):
        """Test quantization with negative floating-point values."""
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=0.8567,
            offset_x=-123.456,
            offset_y=-67.891,
            manual_x_offset=-45.123,
            manual_y_offset=-89.987,
        )

        quantized = view_state.quantized_for_cache()

        # Negative values should be quantized correctly
        assert quantized.offset_x == pytest.approx(-123.5, abs=1e-10)
        assert quantized.offset_y == pytest.approx(-67.9, abs=1e-10)
        assert quantized.manual_x_offset == pytest.approx(-45.1, abs=1e-10)
        assert quantized.manual_y_offset == pytest.approx(-90.0, abs=1e-10)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
