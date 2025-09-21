"""
Qt-related test fixtures.

Contains fixtures for Qt application management, widget cleanup,
and Qt-specific test utilities.
"""

import os
import sys
from collections.abc import Generator

import pytest
from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtWidgets import QApplication, QWidget

from ui.curve_view_widget import CurveViewWidget


@pytest.fixture(scope="function")
def qapp() -> Generator[QApplication, None, None]:
    """Create or retrieve the QApplication instance for testing.

    This fixture ensures a QApplication exists for Qt widget testing.
    It's function-scoped to prevent test interference.

    Yields:
        QApplication: The application instance
    """
    # Set environment for headless testing
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    # Check if an application already exists
    app = QCoreApplication.instance()

    if app is None:
        # Create new application
        app = QApplication(sys.argv)
        app.setApplicationName("CurveEditor_Tests")
        app.setOrganizationName("TestOrg")
        created = True
    elif not isinstance(app, QApplication):
        # If a QCoreApplication exists but not QApplication, we need to recreate
        app.quit()
        app.deleteLater()
        app = QApplication(sys.argv)
        app.setApplicationName("CurveEditor_Tests")
        app.setOrganizationName("TestOrg")
        created = True
    else:
        created = False

    yield app

    # Clean up if we created the app
    if created:
        # Process any pending events before cleanup
        app.processEvents()
        # Note: We don't quit() the app as it causes issues with pytest-qt


@pytest.fixture
def qt_cleanup(qapp: QApplication) -> Generator[None, None, None]:
    """Ensure proper cleanup after each test.

    This fixture runs after each test to clean up Qt resources and
    prevent test interference.

    Args:
        qapp: The QApplication instance
    """
    yield

    # Process any pending events
    qapp.processEvents()

    # Clean up any remaining widgets
    for widget in qapp.topLevelWidgets():
        if widget and not widget.isHidden():
            widget.close()
            widget.deleteLater()

    # Process deletion events
    qapp.processEvents()

    # Clear any remaining timers
    for timer in qapp.findChildren(QTimer):
        timer.stop()
        timer.deleteLater()

    # Final event processing
    qapp.processEvents()


@pytest.fixture
def qt_widget_cleanup(qapp: QApplication):
    """Explicit widget cleanup fixture for tests that create many widgets.

    Use this fixture when your test creates multiple widgets to ensure
    they are properly cleaned up.

    Args:
        qapp: The QApplication instance

    Yields:
        Cleanup function that can be called to clean widgets
    """
    widgets_to_clean = []

    def register_widget(widget: QWidget):
        """Register a widget for cleanup."""
        widgets_to_clean.append(widget)

    yield register_widget

    # Cleanup registered widgets
    for widget in widgets_to_clean:
        if widget and not widget.isHidden():
            widget.close()
            widget.deleteLater()

    qapp.processEvents()


@pytest.fixture
def curve_view(qapp: QApplication) -> CurveViewWidget:
    """Create a CurveViewWidget instance for testing.

    Args:
        qapp: The QApplication instance

    Returns:
        CurveViewWidget: A fresh curve view widget
    """
    widget = CurveViewWidget()
    widget.resize(800, 600)

    # Ensure widget is properly initialized
    qapp.processEvents()

    return widget


@pytest.fixture
def curve_view_widget(qapp: QApplication):
    """Create a curve view widget with cleanup.

    This fixture ensures the widget is properly cleaned up after the test.

    Args:
        qapp: The QApplication instance

    Yields:
        CurveViewWidget: The widget instance
    """
    widget = CurveViewWidget()
    widget.resize(800, 600)

    yield widget

    # Cleanup
    widget.close()
    widget.deleteLater()
    qapp.processEvents()
