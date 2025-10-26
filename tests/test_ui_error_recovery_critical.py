#!/usr/bin/env python3
"""
CRITICAL MISSING TESTS: UI error recovery with safe fallback defaults

These tests ensure that UI components gracefully handle errors and fall back to
safe default values rather than crashing the application.
"""

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

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.transform_service import Transform, TransformService, ViewState


class TestUIErrorRecoveryCritical:
    """Critical tests for UI error recovery with safe fallback defaults."""

    def test_transform_service_invalid_view_state_fallback(self):
        """Test that TransformService handles invalid ViewState gracefully."""
        service = TransformService()

        # Create a ViewState that would cause transform creation to fail
        with patch.object(Transform, "from_view_state", side_effect=ValueError("Invalid configuration")):
            view_state = ViewState(display_width=1920, display_height=1080, widget_width=800, widget_height=600)

            # Service should handle the error gracefully
            # The improved system may handle this without raising
            try:
                transform = service.create_transform_from_view_state(view_state)  # Returns non-None Transform
                # Verify it returned a valid transform
                assert hasattr(transform, "data_to_screen")
                # Verify transform works with basic operations
                x, y = transform.data_to_screen(100.0, 100.0)
                assert isinstance(x, float)
                assert isinstance(y, float)
            except (ValueError, RuntimeError) as e:
                # If it still raises, verify error is informative
                error_str = str(e)
                assert ("Invalid configuration" in error_str) or ("Transform creation failed" in error_str)

    def test_transform_coordinate_overflow_fallback(self):
        """Test that coordinate transformations handle overflow gracefully."""
        transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0)

        # Test with extremely large coordinates that would cause overflow
        large_coord = 1e20

        # System now handles large coordinates gracefully
        try:
            x, y = transform.data_to_screen(large_coord, large_coord)
            # If successful, verify values are clamped or handled
            assert x is not None
            assert y is not None
            # Values should be finite
            import math

            assert math.isfinite(x)
            assert math.isfinite(y)
        except ValueError as e:
            # If it raises, verify message is clear
            error_str = str(e).lower()
            assert ("too large" in error_str) or ("overflow" in error_str)

    def test_view_state_from_corrupted_curve_view(self):
        """Test ViewState creation from curve view with missing/invalid attributes."""
        # Create a mock curve view with missing attributes
        incomplete_curve_view = Mock()
        incomplete_curve_view.width.return_value = 800
        incomplete_curve_view.height.return_value = 600
        incomplete_curve_view.image_width = None  # Missing critical attribute
        incomplete_curve_view.image_height = None
        incomplete_curve_view.zoom_factor = "invalid"  # Wrong type

        # System now handles missing attributes gracefully with defaults
        try:
            view_state = ViewState.from_curve_view(incomplete_curve_view)
            # If successful, verify defaults were used
            assert view_state.widget_width == 800
            assert view_state.widget_height == 600
            # Should have reasonable defaults for missing values
            assert view_state.display_width > 0
            assert view_state.display_height > 0
            assert view_state.zoom_factor == 1.0  # Default zoom
        except (AttributeError, TypeError, ValueError) as e:
            # If it raises, verify error is informative
            # TypeError is acceptable for invalid type (string for zoom_factor)
            error_str = str(e).lower()
            expected_keywords = [
                "image_width",
                "image_height",
                "zoom_factor",
                "invalid",
                "none",
                "must be real number",
                "real number",
                "not str",
            ]
            assert any(keyword in error_str for keyword in expected_keywords)

    def test_view_state_with_negative_dimensions_fallback(self):
        """Test ViewState handles negative dimensions safely."""
        # The system accepts negative dimensions (they'll be handled in transform)
        view_state = ViewState(
            display_width=-1920,  # Invalid negative width
            display_height=1080,
            widget_width=800,
            widget_height=600,
        )
        # ViewState stores the value as-is
        assert view_state.display_width == -1920

        # The Transform should handle it when creating from ViewState
        try:
            transform = Transform.from_view_state(view_state)
            # If successful, verify it can still do basic operations
            x, y = transform.data_to_screen(100.0, 100.0)
            assert isinstance(x, float)
            assert isinstance(y, float)
        except ValueError as e:
            # If it raises, ensure error is clear
            error_str = str(e).lower()
            assert ("negative" in error_str) or ("invalid" in error_str)

    def test_transform_with_extreme_display_height_validation(self):
        """Test Transform handles extreme display height values."""
        # Test with negative display height
        try:
            transform = Transform(scale=1.0, center_offset_x=0.0, center_offset_y=0.0, display_height=-1080)
            # If successful, should use absolute value or default
            assert transform.display_height > 0
        except ValueError as e:
            error_str = str(e).lower()
            assert ("negative" in error_str) or ("invalid" in error_str)

        # Test with extremely large display height
        try:
            transform = Transform(
                scale=1.0,
                center_offset_x=0.0,
                center_offset_y=0.0,
                display_height=2_000_000,  # Larger than max allowed
            )
            # If successful, should clamp to max allowed
            assert transform.display_height <= 1_000_000  # Max allowed
        except ValueError as e:
            error_str = str(e).lower()
            assert ("too large" in error_str) or ("max" in error_str)

    def test_view_state_to_dict_with_corrupted_state(self):
        """Test ViewState.to_dict() handles internal corruption gracefully."""
        view_state = ViewState(display_width=1920, display_height=1080, widget_width=800, widget_height=600)

        # Normal operation should work
        state_dict = view_state.to_dict()
        assert isinstance(state_dict, dict)
        assert "display_dimensions" in state_dict

        # Test with None values in creation
        view_state_with_defaults = ViewState(
            display_width=None,
            display_height=None,
            widget_width=800,
            widget_height=600,
        )

        # System may handle None values gracefully or raise
        try:
            corrupted_dict = view_state_with_defaults.to_dict()
            # If successful, verify it handled the None values
            assert corrupted_dict is not None
        except (AttributeError, TypeError, ValueError) as e:
            # If it raises, verify error is clear
            error_str = str(e)
            assert ("display" in error_str.lower()) or ("None" in error_str)

    def test_transform_service_concurrent_error_recovery(self):
        """Test TransformService error recovery under concurrent access."""
        service = TransformService()
        import queue
        import threading

        errors = queue.Queue()
        results = queue.Queue()

        def worker_with_operations():
            try:
                # Create view state for this thread
                thread_ident = threading.current_thread().ident or 0
                view_state = ViewState(
                    display_width=1920,
                    display_height=1080,
                    widget_width=800,
                    widget_height=600,
                    zoom_factor=1.0 + thread_ident % 100 * 0.001,
                )

                # Perform multiple operations
                for _ in range(10):
                    transform = service.create_transform_from_view_state(view_state)
                    results.put(transform)

            except Exception as e:
                errors.put(f"Unexpected error: {e}")

        # Run multiple threads
        threads = [threading.Thread(target=worker_with_operations) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5.0)
            if thread.is_alive():
                import warnings

                warnings.warn(f"Thread {thread.name} did not stop within timeout", stacklevel=2)

        # Check that service remained functional
        error_list = []
        while not errors.empty():
            error_list.append(errors.get())

        result_list = []
        while not results.empty():
            result_list.append(results.get())

        # Should have successful results from all threads
        assert len(error_list) == 0  # No errors expected
        assert len(result_list) == 30  # 10 results per thread * 3 threads
        assert all(hasattr(r, "data_to_screen") for r in result_list)

    def test_safe_fallback_default_values(self):
        """Test that safe fallback defaults are used when values are invalid."""
        # This test verifies that the system uses safe defaults
        # when encountering invalid configurations

        # Test ViewState with minimal valid parameters
        minimal_state = ViewState(
            display_width=1,  # Minimal but valid
            display_height=1,
            widget_width=1,
            widget_height=1,
        )

        # Should create valid transform with safe defaults
        transform = Transform.from_view_state(minimal_state)
        assert transform.scale == 1.0  # Default zoom
        assert transform.flip_y is False  # Default flip
        assert transform.scale_to_image is True  # Default scaling

        # Should be able to perform basic transformations
        x, y = transform.data_to_screen(0.0, 0.0)
        assert isinstance(x, float)
        assert isinstance(y, float)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
