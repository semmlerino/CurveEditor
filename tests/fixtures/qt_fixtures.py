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


@pytest.fixture
def widget_factory(qapp: QApplication, qtbot):
    """Factory fixture for creating and auto-managing Qt widgets.

    This fixture consolidates widget creation and cleanup patterns,
    automatically registering widgets with qtbot for proper cleanup.
    Reduces duplication of widget setup/teardown code across tests.

    Args:
        qapp: The QApplication instance
        qtbot: pytest-qt's qtbot fixture

    Yields:
        WidgetFactory: Factory object with methods to create common widgets

    Example:
        def test_main_window(widget_factory):
            window = widget_factory.create_main_window()
            assert window.curve_widget is not None
    """

    class WidgetFactory:
        def __init__(self, qtbot_instance):
            self.qtbot = qtbot_instance
            self.widgets = []

        def create_main_window(self):
            """Create and register a MainWindow instance."""
            from ui.main_window import MainWindow

            window = MainWindow()
            self.qtbot.addWidget(window)
            self.widgets.append(window)
            return window

        def create_curve_view(self, with_data=False):
            """Create and register a CurveViewWidget instance."""
            widget = CurveViewWidget()
            self.qtbot.addWidget(widget)
            if with_data:
                widget.set_curve_data([(1, 100, 100), (5, 200, 150), (10, 300, 200)])
            self.widgets.append(widget)
            return widget

        def create_timeline_tabs(self):
            """Create and register a TimelineTabWidget instance."""
            from ui.timeline_tabs import TimelineTabWidget

            widget = TimelineTabWidget()
            self.qtbot.addWidget(widget)
            self.widgets.append(widget)
            return widget

        def create_widget(self, widget_class, *args, **kwargs):
            """Generic method to create and register any widget."""
            widget = widget_class(*args, **kwargs)
            self.qtbot.addWidget(widget)
            self.widgets.append(widget)
            return widget

        def cleanup_all(self):
            """Explicitly clean up all created widgets."""
            for widget in self.widgets:
                if widget and not widget.isHidden():
                    widget.close()
            self.widgets.clear()

    factory = WidgetFactory(qtbot)
    yield factory
    # Cleanup is automatic via qtbot, but ensure everything is cleaned
    factory.cleanup_all()
