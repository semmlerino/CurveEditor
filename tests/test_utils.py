"""
Shared test utilities for the CurveEditor test suite.

This module contains common utilities to reduce duplication across test files,
following DRY principles.
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

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


def cleanup_qt_widgets(qapp: QApplication | None) -> None:
    """
    Unified widget cleanup function for Qt tests.

    Consolidates widget cleanup logic that was previously duplicated across
    multiple test files (qt_fixtures.py, test_helpers.py, run_tests_safe.py).

    Args:
        qapp: QApplication instance to clean up, or None
    """
    if qapp is None:
        return

    # Process any pending events first
    qapp.processEvents()

    # Close and delete all top-level widgets
    for widget in qapp.topLevelWidgets():
        if widget and not widget.isHidden():
            try:
                widget.close()
                widget.deleteLater()
            except RuntimeError:
                # Widget already deleted
                pass

    # Stop and clean up any remaining timers
    for timer in qapp.findChildren(QTimer):
        try:
            timer.stop()
            timer.deleteLater()
        except RuntimeError:
            # Timer already deleted
            pass

    # Final event processing to ensure deletions complete
    qapp.processEvents()


def safe_cleanup_widget(widget):
    """
    Safely cleanup a single Qt widget.

    Replaces the safe_qt_cleanup function from test_helpers.py.

    Args:
        widget: Qt widget to cleanup, or None
    """
    if widget is None:
        return

    try:
        if hasattr(widget, "close"):
            widget.close()
        if hasattr(widget, "deleteLater"):
            widget.deleteLater()
    except RuntimeError:
        # Widget already deleted
        pass


def assert_production_realistic(test_func):
    """Decorator ensuring test doesn't use anti-patterns.

    Validates test code doesn't manually call internal cache methods
    that create test-production mismatches. Tests using anti-patterns
    will fail with clear error messages.

    Anti-patterns detected:
    - _update_screen_points_cache(): Manual cache updates (production uses auto-rebuild)
    - ._spatial_index: Direct cache access (should use service methods)

    Usage:
        ```python
        @assert_production_realistic
        def test_selection(production_widget_factory):
            # Test code here - will fail if using anti-patterns
            pass
        ```

    Args:
        test_func: Test function to validate

    Returns:
        Wrapped test function that validates before running
    """
    import functools
    import inspect

    import pytest

    @functools.wraps(test_func)
    def wrapper(*args, **kwargs):
        # Check source for anti-patterns
        try:
            source = inspect.getsource(test_func)
        except (OSError, TypeError):
            # Can't get source (probably a built-in or compiled code)
            return test_func(*args, **kwargs)

        # Remove comments to avoid false positives
        import re

        # Remove single-line comments
        source_without_comments = re.sub(r"#.*$", "", source, flags=re.MULTILINE)

        anti_patterns = [
            ("_update_screen_points_cache()", "Manual cache update (use production_widget_factory instead)"),
            ("._spatial_index", "Direct cache access (use service methods instead)"),
        ]

        found = [(pattern, msg) for pattern, msg in anti_patterns if pattern in source_without_comments]

        if found:
            __tracebackhide__ = True  # Hide this frame from traceback
            errors = "\n".join(f"  - {pattern}: {msg}" for pattern, msg in found)
            pytest.fail(
                f"Test uses anti-pattern(s) that create test-production mismatch:\n{errors}\n\n" +
                "See docs/testing/UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md section " +
                "'Test-Production State Alignment' for correct patterns."
            )

        return test_func(*args, **kwargs)

    return wrapper


# =============================================================================
# Wait Utilities for Reliable Testing
# =============================================================================


def process_qt_events(iterations: int = 3) -> None:
    """Process Qt events to allow signal propagation and deleteLater() completion.

    Use this instead of qtbot.wait(N) for synchronous signal processing when you
    don't have a specific condition to wait for.

    Args:
        iterations: Number of event processing loops. Default 3 handles:
            - 1: Direct signal emissions
            - 2: Queued signals from slot handlers
            - 3: deleteLater() cleanup from destroyed objects

    Note: For tests waiting on specific conditions, prefer wait_for_condition()
    or process_qt_events_with_verification() instead.
    """
    app = QApplication.instance()
    if app:
        for _ in range(iterations):
            app.processEvents()


def process_qt_events_with_verification(condition=None, max_iterations: int = 10) -> bool:
    """Process events until condition met or max iterations reached.

    Safer alternative to process_qt_events() when you have a condition to verify.

    Args:
        condition: Optional callable returning True when done
        max_iterations: Maximum event processing loops (default 10)

    Returns:
        True if condition met (or no condition), False if max iterations
        reached without condition being satisfied
    """
    app = QApplication.instance()
    if app is None:
        return condition() if condition else True

    for _ in range(max_iterations):
        app.processEvents()
        if condition and condition():
            return True
    return condition() if condition else True


def wait_for_condition(qtbot, condition, timeout: int = 1000, message: str = "Condition not met"):
    """Wait for arbitrary condition with clear error message.

    Wrapper around qtbot.waitUntil that provides better error messages
    when the condition times out.

    Args:
        qtbot: pytest-qt qtbot fixture
        condition: Callable returning True when condition is satisfied
        timeout: Maximum time to wait in milliseconds (default 1000ms)
        message: Error message to show on timeout

    Raises:
        AssertionError: If condition not met within timeout
    """
    try:
        qtbot.waitUntil(condition, timeout=timeout)
    except Exception:
        # pytestqt raises various exceptions on timeout
        raise AssertionError(f"{message} (timeout={timeout}ms)")


def wait_for_frame(qtbot, expected_frame: int, timeout: int = 1000):
    """Wait for current frame to change to expected value.

    Convenience wrapper for the common pattern of waiting for frame changes
    after keyboard/mouse events.

    Args:
        qtbot: pytest-qt qtbot fixture
        expected_frame: Frame number to wait for
        timeout: Maximum time to wait in milliseconds (default 1000ms)

    Raises:
        AssertionError: If frame doesn't reach expected value within timeout
    """
    from stores.application_state import get_application_state

    state = get_application_state()
    wait_for_condition(
        qtbot,
        lambda: state.current_frame == expected_frame,
        timeout=timeout,
        message=f"Expected frame {expected_frame}, got {state.current_frame}",
    )


def wait_for_signal(qtbot, spy, min_count: int = 1, timeout: int = 1000):
    """Wait for signal spy to record at least min_count emissions.

    Wrapper for waiting on QSignalSpy with clear error messages.

    Args:
        qtbot: pytest-qt qtbot fixture
        spy: QSignalSpy instance to check
        min_count: Minimum number of emissions required (default 1)
        timeout: Maximum time to wait in milliseconds (default 1000ms)

    Raises:
        AssertionError: If signal count doesn't reach min_count within timeout
    """
    wait_for_condition(
        qtbot,
        lambda: spy.count() >= min_count,
        timeout=timeout,
        message=f"Expected {min_count}+ signal emissions, got {spy.count()}",
    )
