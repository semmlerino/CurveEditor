#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for all tests.

This module imports fixtures from the organized fixtures package
to make them available to all tests.
"""

# Import all fixtures from the fixtures package
from tests.fixtures import (
    all_services,
    curve_view,
    curve_view_widget,
    # Service fixtures
    isolated_services,
    keyframe_curve_data,
    large_sample_points,
    lazy_mock_main_window,
    memory_monitor,
    # Mock fixtures
    mock_curve_view,
    mock_curve_view_with_selection,
    mock_main_window,
    mock_main_window_with_data,
    protocol_compliant_mock_curve_view,
    protocol_compliant_mock_main_window,
    # Qt fixtures
    qapp,
    qt_cleanup,
    qt_widget_cleanup,
    # Data fixtures
    sample_curve_data,
    sample_points,
    widget_factory,
)

# Re-export all fixtures so pytest can find them
__all__ = [
    # Data fixtures
    "sample_curve_data",
    "keyframe_curve_data",
    "sample_points",
    "large_sample_points",
    # Mock fixtures
    "mock_curve_view",
    "mock_curve_view_with_selection",
    "mock_main_window",
    "mock_main_window_with_data",
    "protocol_compliant_mock_curve_view",
    "protocol_compliant_mock_main_window",
    "lazy_mock_main_window",
    # Qt fixtures
    "qapp",
    "qt_cleanup",
    "qt_widget_cleanup",
    "curve_view",
    "curve_view_widget",
    "widget_factory",
    # Service fixtures
    "all_services",
    "isolated_services",
    "memory_monitor",
]
