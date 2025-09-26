"""
Qt-related test fixtures.

Contains fixtures for Qt application management, widget cleanup,
and Qt-specific test utilities.
"""

import os
import sys
from collections.abc import Generator

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from tests.test_utils import cleanup_qt_widgets
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

    # Use unified cleanup function
    cleanup_qt_widgets(qapp)


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

    # Ensure widget is properly initialized
    qapp.processEvents()

    yield widget

    # Use unified cleanup for single widget
    from tests.test_utils import safe_cleanup_widget

    safe_cleanup_widget(widget)
    qapp.processEvents()


@pytest.fixture
def main_window(qapp: QApplication):
    """Create a fully initialized MainWindow with all UI components.

    This fixture creates a MainWindow with properly initialized UI components
    including timeline_tabs, frame_spinbox, etc. to prevent "not available"
    errors in integration tests.

    Args:
        qapp: The QApplication instance

    Yields:
        MainWindow: Fully initialized main window
    """
    from PySide6.QtWidgets import QSpinBox

    from ui.main_window import MainWindow
    from ui.timeline_tabs import TimelineTabWidget

    window = MainWindow()

    # Initialize commonly needed UI components that tests expect
    # These would normally be created by UIInitializationController
    if window.timeline_tabs is None:
        window.timeline_tabs = TimelineTabWidget()

    # Initialize frame spinbox if not present
    if not hasattr(window, "frame_spinbox") or window.frame_spinbox is None:
        window.frame_spinbox = QSpinBox()
        window.frame_spinbox.setMinimum(1)
        window.frame_spinbox.setMaximum(9999)

    # Process events to ensure widgets are ready
    qapp.processEvents()

    yield window

    # Cleanup
    from tests.test_utils import safe_cleanup_widget

    safe_cleanup_widget(window)
    qapp.processEvents()
