#!/usr/bin/env python3
"""
Tests for background image fitting functionality.

Following UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md best practices:
- Test behavior, not implementation
- Use real components with mocked boundaries
- Use ThreadSafeTestImage for Qt threading safety
- Use qtbot.addWidget() for proper cleanup
"""

import pytest
from PySide6.QtWidgets import QApplication

from tests.qt_test_helpers import ThreadSafeTestImage
from ui.curve_view_widget import CurveViewWidget


class TestBackgroundImageFitting:
    """Test suite for background image fitting functionality."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def curve_view(self, app, qtbot):
        """Create real CurveViewWidget for testing."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)  # Essential for proper cleanup per testing guide

        # Set a known widget size for consistent testing
        widget.resize(800, 600)
        return widget

    @pytest.fixture
    def test_image_1280x720(self):
        """Create test image matching common HD resolution."""
        return ThreadSafeTestImage(1280, 720)

    @pytest.fixture
    def test_image_square(self):
        """Create square test image for aspect ratio testing."""
        return ThreadSafeTestImage(400, 400)

    def test_fit_no_background_image(self, curve_view):
        """Test fitting behavior when no background image is set."""
        # Behavior: Should handle gracefully with no background image
        original_zoom = curve_view.zoom_factor

        curve_view.fit_to_background_image()

        # Should not change zoom factor when no image
        assert curve_view.zoom_factor == original_zoom

    def test_fit_calculates_correct_scale_for_landscape_image(self, curve_view, test_image_1280x720):
        """Test scale calculation for landscape image in portrait widget."""
        # Setup: Widget 800x600, Image 1280x720
        curve_view.resize(800, 600)
        curve_view.background_image = test_image_1280x720

        # Behavior: Should calculate scale to fit image with 95% margin
        curve_view.fit_to_background_image()

        # Expected scale calculation:
        # margin = 0.95
        # scale_x = (800 * 0.95) / 1280 = 0.59375
        # scale_y = (600 * 0.95) / 720 = 0.79167
        # desired_scale = min(0.59375, 0.79167) = 0.59375
        expected_scale = 0.59375

        assert abs(curve_view.zoom_factor - expected_scale) < 0.001

    def test_fit_calculates_correct_scale_for_square_image(self, curve_view, test_image_square):
        """Test scale calculation for square image."""
        # Setup: Widget 800x600, Image 400x400
        curve_view.resize(800, 600)
        curve_view.background_image = test_image_square

        # Behavior: Should use smaller dimension (height) for square image
        curve_view.fit_to_background_image()

        # Expected scale calculation:
        # margin = 0.95
        # scale_x = (800 * 0.95) / 400 = 1.9
        # scale_y = (600 * 0.95) / 400 = 1.425
        # desired_scale = min(1.9, 1.425) = 1.425
        expected_scale = 1.425

        assert abs(curve_view.zoom_factor - expected_scale) < 0.001

    def test_fit_resets_offsets(self, curve_view, test_image_1280x720):
        """Test that fitting resets manual and pan offsets."""
        # Setup: Set some offsets first
        curve_view.background_image = test_image_1280x720
        curve_view.manual_offset_x = 50.0
        curve_view.manual_offset_y = 25.0
        curve_view.pan_offset_x = 100.0
        curve_view.pan_offset_y = 75.0

        # Behavior: Should reset all offsets to 0
        curve_view.fit_to_background_image()

        assert curve_view.manual_offset_x == 0
        assert curve_view.manual_offset_y == 0
        assert curve_view.pan_offset_x == 0
        assert curve_view.pan_offset_y == 0

    def test_fit_handles_minimal_dimensions_gracefully(self, curve_view):
        """Test behavior with minimal widget dimensions."""
        # Setup: Use Qt's minimum size (which it enforces anyway)
        # We're testing that the method handles small dimensions gracefully
        curve_view.resize(100, 100)  # Small but reasonable dimensions
        curve_view.background_image = ThreadSafeTestImage(1920, 1080)  # Much larger image

        # Store initial state
        initial_zoom = curve_view.zoom_factor

        # Behavior: Should handle gracefully without crashing
        # and should scale down the large image to fit the small widget
        curve_view.fit_to_background_image()

        # Verify the image was scaled down to fit
        assert curve_view.zoom_factor < initial_zoom
        # The function should still work even with small widget dimensions

    def test_fit_handles_zero_image_dimensions_gracefully(self, curve_view):
        """Test behavior with zero image dimensions."""
        # Setup: Zero image size
        curve_view.resize(800, 600)
        curve_view.background_image = ThreadSafeTestImage(0, 0)
        original_zoom = curve_view.zoom_factor

        # Behavior: Should handle gracefully without crashing
        curve_view.fit_to_background_image()

        # Should not change zoom when image has zero dimensions
        assert curve_view.zoom_factor == original_zoom

    def test_fit_with_very_wide_image(self, curve_view):
        """Test fitting behavior with extremely wide image."""
        # Setup: Very wide image (panoramic)
        curve_view.resize(800, 600)
        curve_view.background_image = ThreadSafeTestImage(3200, 200)  # 16:1 aspect

        # Behavior: Should be constrained by height
        curve_view.fit_to_background_image()

        # Expected: height constraint dominates
        # scale_y = (600 * 0.95) / 200 = 2.85
        # scale_x = (800 * 0.95) / 3200 = 0.2375
        # desired_scale = min(2.85, 0.2375) = 0.2375
        expected_scale = 0.2375

        assert abs(curve_view.zoom_factor - expected_scale) < 0.001

    def test_fit_with_very_tall_image(self, curve_view):
        """Test fitting behavior with extremely tall image."""
        # Setup: Very tall image
        curve_view.resize(800, 600)
        curve_view.background_image = ThreadSafeTestImage(200, 2400)  # 1:12 aspect

        # Behavior: Should be constrained by width
        curve_view.fit_to_background_image()

        # Expected: width constraint dominates
        # scale_x = (800 * 0.95) / 200 = 3.8
        # scale_y = (600 * 0.95) / 2400 = 0.2375
        # desired_scale = min(3.8, 0.2375) = 0.2375
        expected_scale = 0.2375

        assert abs(curve_view.zoom_factor - expected_scale) < 0.001

    def test_fit_transform_integration(self, curve_view, test_image_1280x720):
        """Test that fitting integrates correctly with transform system."""
        # Setup
        curve_view.resize(800, 600)
        curve_view.background_image = test_image_1280x720

        # Behavior: Transform should reflect the new zoom factor
        curve_view.fit_to_background_image()

        transform = curve_view.get_transform()
        params = transform.get_parameters()

        # Transform scale should match zoom_factor
        assert abs(params["scale"] - curve_view.zoom_factor) < 0.001

        # Should have center offsets (image smaller than widget)
        assert params["center_offset_x"] > 0
        assert params["center_offset_y"] > 0

        # Pan offsets should be 0 (reset by fit operation)
        assert params["pan_offset_x"] == 0.0
        assert params["pan_offset_y"] == 0.0

    def test_fit_emits_signals(self, curve_view, test_image_1280x720, qtbot):
        """Test that fitting emits appropriate signals."""
        # Setup
        curve_view.background_image = test_image_1280x720

        # Use qtbot to wait for signals (testing guide best practice)
        with qtbot.waitSignal(curve_view.view_changed, timeout=1000):
            with qtbot.waitSignal(curve_view.zoom_changed, timeout=1000):
                curve_view.fit_to_background_image()

    def test_fit_multiple_times_is_idempotent(self, curve_view, test_image_1280x720):
        """Test that fitting multiple times produces consistent results."""
        # Setup
        curve_view.resize(800, 600)
        curve_view.background_image = test_image_1280x720

        # Behavior: Multiple fits should produce same result
        curve_view.fit_to_background_image()
        first_zoom = curve_view.zoom_factor
        first_pan_x = curve_view.pan_offset_x
        first_pan_y = curve_view.pan_offset_y

        curve_view.fit_to_background_image()
        second_zoom = curve_view.zoom_factor
        second_pan_x = curve_view.pan_offset_x
        second_pan_y = curve_view.pan_offset_y

        assert abs(first_zoom - second_zoom) < 0.001
        assert abs(first_pan_x - second_pan_x) < 0.001
        assert abs(first_pan_y - second_pan_y) < 0.001

    def test_fit_after_widget_resize(self, curve_view, test_image_1280x720):
        """Test fitting behavior after widget resize."""
        # Setup: Initial size and fit
        curve_view.resize(800, 600)
        curve_view.background_image = test_image_1280x720
        curve_view.fit_to_background_image()
        original_zoom = curve_view.zoom_factor

        # Behavior: Resize widget and fit again
        curve_view.resize(1000, 800)  # Larger widget
        curve_view.fit_to_background_image()
        new_zoom = curve_view.zoom_factor

        # Should recalculate for new widget size (larger zoom possible)
        assert new_zoom > original_zoom


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
