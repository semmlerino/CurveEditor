#!/usr/bin/env python3
"""
Test empty-state behavior throughout the application.

These tests verify graceful handling when no data is loaded:
- Frame navigation with 0 images
- Rendering with no background image
- Timeline display with empty sequence
- ApplicationState with no curves

This ensures the application handles startup and cleared states correctly.
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportPrivateUsage=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownVariableType=none

from typing import cast
from unittest.mock import patch

import pytest
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from core.type_aliases import CurveDataList
from rendering.optimized_curve_renderer import OptimizedCurveRenderer
from stores.application_state import get_application_state
from stores.store_manager import StoreManager
from tests.fixtures.state_helpers import reset_all_test_state
from tests.test_helpers import create_test_render_state


class TestFrameNavigationEmptyState:
    """Test frame navigation behavior with no images loaded."""

    def setup_method(self) -> None:
        """Reset to clean state - no images."""
        reset_all_test_state(log_warnings=False)
        StoreManager.reset()

    def teardown_method(self) -> None:
        """Clean up."""
        reset_all_test_state(log_warnings=False)
        StoreManager.reset()

    def test_set_frame_with_no_images_clamps_to_one(self) -> None:
        """Verify set_frame() behavior when no images loaded."""
        app_state = get_application_state()

        # Ensure no images are loaded
        app_state.set_image_files([])

        # Frame 1 should be the default/minimum
        assert app_state.current_frame >= 1

        # Try to set various frame values - should not crash
        app_state.set_frame(1)
        app_state.set_frame(100)
        app_state.set_frame(0)
        app_state.set_frame(-5)

        # Should always be at least 1
        assert app_state.current_frame >= 1

    def test_frame_range_with_no_images(self) -> None:
        """Verify frame properties with no images."""
        app_state = get_application_state()
        app_state.set_image_files([])

        # Current frame should still be valid (at least 1)
        assert app_state.current_frame >= 1


class TestRenderingEmptyState:
    """Test rendering behavior with no background image."""

    def setup_method(self) -> None:
        """Reset to clean state."""
        reset_all_test_state(log_warnings=False)
        StoreManager.reset()

    def teardown_method(self) -> None:
        """Clean up."""
        reset_all_test_state(log_warnings=False)
        StoreManager.reset()

    @pytest.fixture
    def renderer(self) -> OptimizedCurveRenderer:
        """Create a renderer instance."""
        return OptimizedCurveRenderer()

    @pytest.fixture
    def mock_widget(self, qtbot: QtBot) -> QWidget:
        """Create a minimal widget for render state."""
        widget = QWidget()
        widget.resize(800, 600)
        qtbot.addWidget(widget)
        return widget

    def test_render_with_no_background(self, renderer: OptimizedCurveRenderer, mock_widget: QWidget) -> None:
        """Test rendering curves with no background image."""
        # Create render state with no background using helper
        points = cast(CurveDataList, [(1, 100.0, 100.0), (2, 200.0, 200.0), (3, 300.0, 300.0)])
        render_state = create_test_render_state(
            points=points,
            current_frame=1,
            selected_points=set(),
            show_background=False,
            background_image=None,
            image_width=0,
            image_height=0,
            show_grid=True,
        )

        # Create image to paint on
        image = QImage(800, 600, QImage.Format.Format_RGB32)
        image.fill(0)

        # Render should complete without error
        painter = QPainter(image)
        try:
            renderer.render(painter, None, render_state)
        finally:
            painter.end()

        # Verify render completed
        stats = renderer.get_performance_stats()
        assert int(stats.get("render_count", 0)) > 0

    def test_render_with_no_curve_data(self, renderer: OptimizedCurveRenderer, mock_widget: QWidget) -> None:
        """Test rendering with no curve data."""
        # Create render state with empty curve data
        render_state = create_test_render_state(
            points=[],  # Empty
            current_frame=1,
            selected_points=set(),
            show_background=False,
            background_image=None,
            image_width=0,
            image_height=0,
            show_grid=True,
        )

        # Create image to paint on
        image = QImage(800, 600, QImage.Format.Format_RGB32)
        image.fill(0)

        # Render should complete without error
        painter = QPainter(image)
        try:
            renderer.render(painter, None, render_state)
        finally:
            painter.end()

        # Verify render completed without crash
        stats = renderer.get_performance_stats()
        assert int(stats.get("render_count", 0)) >= 0  # May be 0 or more


class TestTimelineEmptyState:
    """Test timeline behavior with empty sequence."""

    def setup_method(self) -> None:
        """Reset to clean state."""
        reset_all_test_state(log_warnings=False)
        StoreManager.reset()

    def teardown_method(self) -> None:
        """Clean up."""
        reset_all_test_state(log_warnings=False)
        StoreManager.reset()

    def test_timeline_with_no_data(self, qtbot: QtBot) -> None:
        """Test timeline widget with no curve data."""
        from ui.timeline_tabs import TimelineTabWidget

        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)

        # Default state should be valid
        assert timeline.min_frame == 1
        assert timeline.max_frame == 1
        assert timeline.current_frame == 1

    def test_timeline_frame_range_empty_curves(self, qtbot: QtBot) -> None:
        """Test timeline frame range with empty curves."""
        from ui.timeline_tabs import TimelineTabWidget

        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)

        # Set empty data
        timeline.set_frame_range(1, 1)

        # Should handle gracefully
        assert timeline.min_frame == 1
        assert timeline.max_frame == 1


class TestApplicationStateEmptyState:
    """Test ApplicationState with no curves."""

    def setup_method(self) -> None:
        """Reset to clean state."""
        reset_all_test_state(log_warnings=False)
        StoreManager.reset()

    def teardown_method(self) -> None:
        """Clean up."""
        reset_all_test_state(log_warnings=False)
        StoreManager.reset()

    def test_get_curve_data_no_active_curve(self) -> None:
        """Test get_curve_data with no active curve raises ValueError."""
        app_state = get_application_state()

        # No active curve set
        assert app_state.active_curve is None

        # Getting curve data without active curve should raise ValueError
        with pytest.raises(ValueError, match="No active curve set"):
            app_state.get_curve_data()

    def test_get_curve_data_explicit_nonexistent(self) -> None:
        """Test get_curve_data with explicit nonexistent curve returns empty."""
        app_state = get_application_state()

        # Getting curve data for non-existent curve should return empty list
        data = app_state.get_curve_data("nonexistent_curve")
        assert isinstance(data, list)
        assert len(data) == 0

    def test_active_curve_data_property_empty(self) -> None:
        """Test active_curve_data property with no data."""
        app_state = get_application_state()

        # No active curve
        result = app_state.active_curve_data
        assert result is None

    def test_selection_empty_state(self) -> None:
        """Test selection operations with no data."""
        app_state = get_application_state()

        # Getting selection for non-existent curve - should return empty set
        selection = app_state.get_selection("nonexistent_curve")
        assert isinstance(selection, set)

        # Setting selection for non-existent curve should not crash
        app_state.set_selection("nonexistent_curve", {0, 1, 2})

    def test_curves_data_empty(self) -> None:
        """Test _curves_data with no curves."""
        app_state = get_application_state()

        # Should have internal data structure
        assert hasattr(app_state, "_curves_data")
        # Curves data might be empty or have only default curves
        assert isinstance(app_state._curves_data, dict)


class TestMainWindowEmptyState:
    """Test MainWindow behavior on startup with no data."""

    def test_main_window_startup_empty(self, qtbot: QtBot) -> None:
        """Test MainWindow can start with no data loaded."""
        from ui.main_window import MainWindow

        # Mock file operations to prevent auto-loading
        with patch("ui.file_operations.FileOperations.load_burger_data_async"):
            window = MainWindow(auto_load_data=False)
            qtbot.addWidget(window)

            # Window should create successfully
            assert window is not None

            # Timeline should exist with default values
            if window.timeline_tabs:
                assert window.timeline_tabs.min_frame == 1
                assert window.timeline_tabs.max_frame == 1

            # Curve widget should exist
            assert window.curve_widget is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
