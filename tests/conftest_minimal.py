#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for all tests.

This module imports fixtures from the organized fixtures package
to make them available to all tests.
"""

# Import all fixtures from the fixtures package
from tests.fixtures import (
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
    # Component fixtures
    test_curve_view,
    test_curve_view_with_data,
    test_data_builder,
    test_main_window,
    test_main_window_with_data,
)

# Re-export all fixtures so pytest can find them
__all__ = [
    # Data fixtures
    "sample_curve_data",
    "keyframe_curve_data",
    "sample_points",
    "large_sample_points",
    "test_data_builder",
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
    # Service fixtures
    "isolated_services",
    "memory_monitor",
    # Component fixtures
    "test_curve_view",
    "test_curve_view_with_data",
    "test_main_window",
    "test_main_window_with_data",
]
