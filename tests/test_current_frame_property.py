#!/usr/bin/env python
"""Test current_frame property for type safety and correctness."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_main_window_has_current_frame_property():
    """Test that MainWindow has current_frame as a property."""
    from ui.main_window import MainWindow

    # Create instance
    with patch("ui.main_window.QMainWindow"):
        window = MainWindow()

        # Check property exists
        assert hasattr(window, "current_frame")

        # Check it's a property, not just an attribute
        assert isinstance(type(window).current_frame, property)


def test_current_frame_property_returns_int():
    """Test that current_frame property returns an integer."""
    from ui.main_window import MainWindow

    with patch("ui.main_window.QMainWindow"):
        window = MainWindow()

        # Mock the frame navigation controller's method
        window.frame_nav_controller.get_current_frame = Mock(return_value=42)

        # Test property access
        frame = window.current_frame
        assert isinstance(frame, int)
        assert frame == 42


def test_current_frame_property_setter():
    """Test that current_frame property setter works."""
    from ui.main_window import MainWindow

    with patch("ui.main_window.QMainWindow"):
        window = MainWindow()

        # Mock the frame navigation controller's method
        window.frame_nav_controller.set_frame = Mock()

        # Set via property
        window.current_frame = 100

        # Check that controller method was called
        window.frame_nav_controller.set_frame.assert_called_once_with(100)


def test_curve_view_can_access_current_frame():
    """Test that CurveViewWidget can access current_frame safely."""
    from ui.curve_view_widget import CurveViewWidget
    from ui.main_window import MainWindow

    with patch("ui.curve_view_widget.QWidget"), patch("ui.main_window.QMainWindow"):
        # Create instances
        widget = CurveViewWidget()
        window = MainWindow()

        # Mock frame navigation controller
        window.frame_nav_controller.get_current_frame = Mock(return_value=50)

        # Link them
        widget.main_window = window

        # Test type-safe access
        if widget.main_window is not None:
            frame = widget.main_window.current_frame
            assert frame == 50


def test_protocol_compliance():
    """Test that MainWindow has critical protocol attributes."""
    from ui.main_window import MainWindow

    # This test verifies that MainWindow has the expected interface
    with patch("ui.main_window.QMainWindow"):
        window = MainWindow()

        # Check critical protocol attributes
        assert hasattr(window, "current_frame")
        # Note: selected_indices and curve_data may be on curve_view/curve_widget
        # This is part of the duck-typing pattern in the codebase

        # Verify current_frame is accessible as property
        window.frame_nav_controller.get_current_frame = Mock(return_value=1)

        frame = window.current_frame
        assert isinstance(frame, int)

        # Test property setter
        window.frame_nav_controller.set_frame = Mock()
        window.current_frame = 42
        window.frame_nav_controller.set_frame.assert_called_with(42)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
