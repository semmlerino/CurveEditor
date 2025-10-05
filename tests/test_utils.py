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
