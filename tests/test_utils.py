"""
Shared test utilities for the CurveEditor test suite.

This module contains common utilities to reduce duplication across test files,
following DRY principles.
"""

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
                f"Test uses anti-pattern(s) that create test-production mismatch:\n{errors}\n\n"
                f"See docs/testing/UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md section "
                f"'Test-Production State Alignment' for correct patterns."
            )

        return test_func(*args, **kwargs)

    return wrapper
