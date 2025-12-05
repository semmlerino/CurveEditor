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

import threading
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
    memory_monitor,
    # Mock fixtures (consolidated to 2 core fixtures)
    mock_curve_view,
    mock_main_window,
    # Production fixtures
    production_widget_factory,
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


@pytest.fixture(autouse=True, scope="session")
def global_thread_sweep() -> Generator[None, None, None]:
    """Session-scoped fixture to sweep stray background threads before Qt teardown.

    CRITICAL: Tests that spawn threads outside managed fixtures (file_load_worker, etc.)
    can leave threads running. If those threads interact with Qt objects during
    session teardown, the QApplication can hang or crash.

    This fixture joins all non-daemon threads with a short timeout (10ms per thread)
    to ensure clean shutdown. Runs at session end, after all tests complete.

    Per UNIFIED_TESTING_GUIDE: Always sweep threads before Qt cleanup.
    """
    yield  # Run all tests

    # After all tests complete, sweep background threads
    main_thread = threading.main_thread()
    stray_threads = []

    for thread in threading.enumerate():
        # Skip main thread and daemon threads (they auto-terminate)
        if thread is main_thread or thread.daemon:
            continue
        # Skip threading-internal threads
        if thread.name.startswith("_"):
            continue
        # Skip pytest-managed threads (pytest-timeout, pytest-xdist, etc.)
        if thread.name.startswith("pytest"):
            continue

        stray_threads.append(thread)
        # Join with 10ms timeout per UNIFIED_TESTING_GUIDE
        thread.join(timeout=0.01)

    # Log if threads didn't terminate (useful for debugging hangs)
    still_running = [t for t in stray_threads if t.is_alive()]
    if still_running:
        import warnings

        thread_names = ", ".join(t.name for t in still_running)
        warnings.warn(
            f"Stray threads still running after session: {thread_names}",
            stacklevel=2,
        )


@pytest.fixture(autouse=True)
def thread_sweep_per_test() -> Generator[None, None, None]:
    """Per-test thread sweep to join stray threads BEFORE Qt cleanup.

    CRITICAL: This fixture runs in teardown BEFORE reset_services because:
    1. Fixture name 'thread_sweep_per_test' > 'reset_services' alphabetically
    2. Teardown runs in reverse setup order
    3. So this teardown runs FIRST, joining threads before processEvents()

    This prevents the "gc.collect() + processEvents() = SEGFAULT" scenario where
    background threads interact with Qt objects during cleanup.
    """
    yield  # Run test

    # Join non-daemon threads before Qt cleanup runs
    main_thread = threading.main_thread()
    for thread in threading.enumerate():
        if thread is main_thread or thread.daemon:
            continue
        if thread.name.startswith(("_", "pytest")):
            continue
        # 1 second timeout per thread (more generous than session sweep)
        thread.join(timeout=1.0)


@pytest.fixture(autouse=True)
def reset_services() -> Generator[None, None, None]:
    """Reset ALL service state between tests to ensure complete isolation.

    This fixture is auto-used for all tests to prevent state leakage.

    DEFAULT: Empty state - no frames seeded.
    Tests that need frame navigation must use opt-in fixtures:
    - `with_minimal_frame_range`: 100 frames (basic navigation)
    - `with_large_frame_range`: 1000 frames (stress/performance)

    This ensures tests don't silently depend on frame availability and
    allows explicit testing of empty-state scenarios.
    """
    # Start with clean state - no dummy frames
    # Tests that need frames must explicitly request them via fixtures
    yield  # Run the test

    # After test completes, reset everything using centralized helper
    # This provides proper error logging instead of silent exception swallowing
    reset_all_test_state(log_warnings=True)


@pytest.fixture
def with_minimal_frame_range():
    """Opt-in fixture: 100 frames for tests needing basic frame data.

    Use this when your test needs frame navigation, timeline display,
    or basic frame-related functionality. 100 frames is sufficient for
    most navigation and timeline tests.

    Usage:
        def test_frame_navigation(with_minimal_frame_range):
            app_state = get_application_state()
            app_state.set_frame(50)  # Works with 100 frames
            ...

    Yields:
        ApplicationState: The application state with 100 frames
    """
    from stores.application_state import get_application_state

    app_state = get_application_state()
    app_state.set_image_files(["dummy.png"] * 100)
    yield app_state


@pytest.fixture
def with_large_frame_range():
    """Opt-in fixture: 1000 frames for stress/performance tests.

    Use this when your test needs to navigate to higher frame numbers
    or test behavior with larger datasets.

    Usage:
        def test_large_range_navigation(with_large_frame_range):
            app_state = get_application_state()
            app_state.set_frame(500)  # Works with 1000 frames
            ...

    Yields:
        ApplicationState: The application state with 1000 frames
    """
    from stores.application_state import get_application_state

    app_state = get_application_state()
    app_state.set_image_files(["dummy.png"] * 1000)
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
    # Fixture sets for classification
    production_fixtures = {"production_widget_factory", "user_interaction"}
    # Broadened detection to include tests with 'app' fixture and Qt widget fixtures
    qt_fixtures = {"qtbot", "qapp", "app", "curve_view_widget", "mock_main_window"}

    for item in items:
        # Auto-tag production workflow tests
        if any(f in item.fixturenames for f in production_fixtures):
            item.add_marker(pytest.mark.production)

        # Auto-tag unit tests (no Qt widgets)
        elif not any(f in item.fixturenames for f in qt_fixtures):
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
    "memory_monitor",
    # Mock fixtures (consolidated from 7 to 2)
    "mock_curve_view",
    "mock_main_window",
    # Production fixtures
    "production_widget_factory",
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
    "with_minimal_frame_range",
    "without_dummy_frames",
]
