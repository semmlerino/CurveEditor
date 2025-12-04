#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for all tests.

This module imports fixtures from the organized fixtures package
to make them available to all tests.
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

from collections.abc import Generator

import pytest

# Import all fixtures from the fixtures package
from tests.fixtures import (
    all_services,
    curve_view_widget,
    file_load_signals,
    file_load_worker,
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
    # Production fixtures
    production_widget_factory,
    protocol_compliant_mock_curve_view,
    protocol_compliant_mock_main_window,
    # Qt fixtures
    qapp,
    qt_cleanup,
    reset_all_test_state,
    safe_test_data_factory,
    # Data fixtures
    sample_curve_data,
    sample_points,
    ui_file_load_signals,
    ui_file_load_worker,
    user_interaction,
)


@pytest.fixture(autouse=True)
def reset_services() -> Generator[None, None, None]:
    """Reset ALL service state between tests to ensure complete isolation.

    This fixture is auto-used for all tests to prevent state leakage.

    Sets up a minimal frame range (100 frames) to allow basic frame
    navigation in most tests. For tests requiring larger ranges,
    use `with_large_frame_range`. For tests requiring NO frames,
    use `without_dummy_frames`.
    """
    # Set up minimal frames BEFORE test (reduced from 10000 to 1000 for speed)
    # 1000 covers most test scenarios while being 10x faster than 10000
    from stores.application_state import get_application_state

    app_state = get_application_state()
    app_state.set_image_files(["dummy.png"] * 1000)

    yield  # Run the test

    # After test completes, reset everything using centralized helper
    # This provides proper error logging instead of silent exception swallowing
    reset_all_test_state(log_warnings=True)


@pytest.fixture
def with_large_frame_range():
    """Fixture for tests needing large frame range (10000 frames).

    Use this when your test needs to navigate to high frame numbers
    or test behavior with large datasets.

    Usage:
        def test_large_range_navigation(with_large_frame_range):
            app_state = get_application_state()
            app_state.set_frame(5000)  # Works with 10000 frames
            ...

    Yields:
        ApplicationState: The application state with large frame range
    """
    from stores.application_state import get_application_state

    app_state = get_application_state()
    app_state.set_image_files(["dummy.png"] * 10000)
    yield app_state


@pytest.fixture
def without_dummy_frames():
    """Fixture for tests that need clean state with NO images loaded.

    Use this when testing behavior with no images, empty state scenarios,
    or initial application state.

    Usage:
        def test_no_images_loaded(without_dummy_frames):
            app_state = get_application_state()
            assert app_state.get_image_files() == []
            ...

    Yields:
        ApplicationState: The application state with no images
    """
    from stores.application_state import get_application_state

    app_state = get_application_state()
    app_state.set_image_files([])  # Clear any pre-set images
    yield app_state


def pytest_collection_modifyitems(items):
    """Auto-tag tests based on fixtures used.

    Implements pytest collection hook to automatically mark tests:
    - 'production': Tests using production workflow fixtures
    - 'unit': Tests without Qt dependencies (fast unit tests)

    This enables filtering tests by type without manual markers.
    """
    for item in items:
        # Auto-tag production workflow tests
        production_fixtures = {"production_widget_factory", "user_interaction"}
        if any(f in item.fixturenames for f in production_fixtures):
            item.add_marker(pytest.mark.production)

        # Auto-tag unit tests (no Qt widgets)
        elif "qtbot" not in item.fixturenames and "qapp" not in item.fixturenames:
            item.add_marker(pytest.mark.unit)


# Re-export all fixtures so pytest can find them
__all__ = [
    "all_services",
    "curve_view_widget",
    "file_load_signals",
    "file_load_worker",
    "isolated_services",
    "keyframe_curve_data",
    "large_sample_points",
    "lazy_mock_main_window",
    "memory_monitor",
    "mock_curve_view",
    "mock_curve_view_with_selection",
    "mock_main_window",
    "mock_main_window_with_data",
    "production_widget_factory",
    "protocol_compliant_mock_curve_view",
    "protocol_compliant_mock_main_window",
    "qapp",
    "qt_cleanup",
    "reset_all_test_state",
    "safe_test_data_factory",
    "sample_curve_data",
    "sample_points",
    "ui_file_load_signals",
    "ui_file_load_worker",
    "user_interaction",
    "with_large_frame_range",
    "without_dummy_frames",
]
