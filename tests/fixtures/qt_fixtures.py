"""
Qt-related test fixtures.

Contains fixtures for Qt application management, widget cleanup,
and Qt-specific test utilities.
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

import os
import sys
from collections.abc import Generator

import pytest
from PySide6.QtWidgets import QApplication

from tests.test_utils import cleanup_qt_widgets
from ui.curve_view_widget import CurveViewWidget


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Session-wide QApplication - created once for all tests.

    CRITICAL: Session-scope QApplication + proper QObject cleanup prevents
    resource exhaustion segfaults after 850+ tests (see UNIFIED_TESTING_GUIDE).

    Yields:
        QApplication: The shared application instance
    """
    # Set environment for headless testing
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    # Get or create QApplication instance
    # QApplication.instance() returns QCoreApplication | QApplication, need to cast
    existing_app = QApplication.instance()
    if existing_app is not None:
        # Cast to QApplication since we know it must be QApplication in test context
        app = existing_app if isinstance(existing_app, QApplication) else QApplication(sys.argv)
    else:
        app = QApplication(sys.argv)

    app.setApplicationName("CurveEditor_Tests")
    app.setOrganizationName("TestOrg")

    yield app

    # Process pending events to handle deleteLater() calls
    app.processEvents()


@pytest.fixture(autouse=True)
def qt_cleanup(qapp: QApplication) -> Generator[None, None, None]:
    """Ensure proper cleanup after each test.

    This fixture runs after each test to clean up Qt resources and
    prevent test interference. Made autouse=True to catch ALL tests.

    CRITICAL: Removes accumulated event filters to prevent timeout after 1580+ tests.
    Without this, event filters accumulate causing setStyleSheet() to timeout.

    Args:
        qapp: The QApplication instance
    """
    yield

    # CRITICAL: Aggressively clean up ALL widgets to prevent accumulation
    # Get snapshot of top-level widgets before cleanup starts
    widgets_to_clean = list(qapp.topLevelWidgets())

    for widget in widgets_to_clean:
        try:
            # Remove event filters FIRST before destroying widget
            # Use getattr() to avoid type errors with dynamic attributes
            if hasattr(widget, "global_event_filter"):
                try:
                    global_filter = getattr(widget, "global_event_filter", None)
                    if global_filter is not None:
                        qapp.removeEventFilter(global_filter)
                except (RuntimeError, AttributeError):
                    pass

            # Remove tracking panel event filters
            if hasattr(widget, "_table_event_filter") and hasattr(widget, "table"):
                try:
                    table = getattr(widget, "table", None)
                    table_filter = getattr(widget, "_table_event_filter", None)
                    if table is not None and table_filter is not None:
                        table.removeEventFilter(table_filter)
                except (RuntimeError, AttributeError):
                    pass

            # Close widget to trigger cleanup
            if hasattr(widget, "close"):
                with contextlib.suppress(RuntimeError):
                    widget.close()

            # Force immediate deletion
            with contextlib.suppress(RuntimeError):
                widget.deleteLater()
        except Exception:
            pass  # Don't let cleanup failures break tests

    # Process events to handle deleteLater calls
    for _ in range(10):
        qapp.processEvents()
        qapp.sendPostedEvents(None, 0)

    # Use unified cleanup function
    cleanup_qt_widgets(qapp)

    # Final aggressive event processing
    for _ in range(10):
        qapp.processEvents()
        qapp.sendPostedEvents(None, 0)


@pytest.fixture
def curve_view_widget(qapp: QApplication, qtbot):
    """Create a curve view widget with cleanup.

    This fixture ensures the widget is properly cleaned up after the test.

    Args:
        qapp: The QApplication instance
        qtbot: pytest-qt bot for automatic cleanup

    Yields:
        CurveViewWidget: The widget instance
    """
    # Initialize services first - needed for commands to work
    from services import get_data_service, get_interaction_service

    data_service = get_data_service()
    _ = get_interaction_service()  # Initialize but don't use

    widget = CurveViewWidget()
    widget.resize(800, 600)

    # CRITICAL: Use qtbot.addWidget for automatic cleanup (required per testing guide)
    qtbot.addWidget(widget)

    # Set up basic main window for command execution
    # This is needed for delete_selected_points and nudge_selected to work
    from tests.test_helpers import ProtocolCompliantMockMainWindow

    mock_main_window = ProtocolCompliantMockMainWindow()
    # CRITICAL: Set the mock's curve_widget to point to our actual widget
    # so that commands execute on the real widget, not the mock
    mock_main_window.curve_widget = widget
    # Mock is protocol-compatible at runtime (has properties that match protocol requirements)
    widget.set_main_window(mock_main_window)

    # Store original set_curve_data method and wrap it to sync with data service
    original_set_curve_data = widget.set_curve_data

    def synced_set_curve_data(data):
        original_set_curve_data(data)
        # Sync with data service so commands can work
        data_service.update_curve_data(data)

    widget.set_curve_data = synced_set_curve_data

    # Ensure widget is properly initialized
    qapp.processEvents()

    return widget

    # qtbot.addWidget handles cleanup automatically
    # No manual cleanup needed


def _cleanup_main_window_event_filter(window):
    """Remove MainWindow's global event filter before window closes.

    CRITICAL: Prevents event filter accumulation causing timeout after 1580+ tests.
    This callback is executed by qtbot.addWidget(before_close_func=...) before
    the window is destroyed, ensuring deterministic cleanup without relying on __del__.

    CRITICAL: Also stops background worker threads to prevent segfault during
    app.processEvents() in reset_all_services fixture (after gc.collect()).
    Daemon threads + processEvents during destruction = SEGFAULT.
    """
    try:
        # STEP 1: Stop background threads FIRST (before any processEvents)
        # This prevents segfault when reset_all_services calls app.processEvents()
        # after gc.collect() triggers __del__ with threads still running
        if hasattr(window, "file_operations"):
            with contextlib.suppress(RuntimeError, AttributeError):
                window.file_operations.cleanup_threads()

        # STEP 2: Remove event filters (original cleanup)
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app and hasattr(window, "global_event_filter"):
            with contextlib.suppress(RuntimeError):
                app.removeEventFilter(window.global_event_filter)
    except Exception:
        pass  # Suppress all exceptions in cleanup  # Suppress all exceptions in cleanup


@pytest.fixture
def main_window(qapp: QApplication, qtbot):
    """Create a fully initialized MainWindow with all UI components.

    This fixture creates a MainWindow with properly initialized UI components
    including timeline_tabs, frame_spinbox, etc. to prevent "not available"
    errors in integration tests.

    Args:
        qapp: The QApplication instance
        qtbot: pytest-qt bot for automatic cleanup

    Yields:
        MainWindow: Fully initialized main window
    """
    from PySide6.QtWidgets import QSpinBox

    from ui.main_window import MainWindow
    from ui.timeline_tabs import TimelineTabWidget

    window = MainWindow()

    # CRITICAL: Use qtbot.addWidget with before_close_func for deterministic event filter cleanup
    # This prevents accumulation of event filters across 1580+ tests causing timeout
    qtbot.addWidget(window, before_close_func=_cleanup_main_window_event_filter)

    # Initialize commonly needed UI components that tests expect
    # These would normally be created by UIInitializationController
    if window.timeline_tabs is None:
        window.timeline_tabs = TimelineTabWidget()

    # Use frame spinbox from timeline_controller if available, otherwise create one
    if not hasattr(window, "frame_spinbox") or window.frame_spinbox is None:
        # Use the frame_spinbox from timeline_controller if it exists (has signals connected)
        if hasattr(window, "timeline_controller"):
            window.frame_spinbox = window.timeline_controller.frame_spinbox
        else:
            # Fallback: create a new one (shouldn't happen in normal flow)
            window.frame_spinbox = QSpinBox()
            window.frame_spinbox.setMinimum(1)
            window.frame_spinbox.setMaximum(9999)

    # Use frame slider from timeline_controller if available
    if not hasattr(window, "frame_slider") or window.frame_slider is None:
        if hasattr(window, "timeline_controller"):
            # Access frame_slider attribute from concrete implementation
            if hasattr(window.timeline_controller, "frame_slider"):
                window.frame_slider = getattr(window.timeline_controller, "frame_slider")

    # Process events to ensure widgets are ready
    qapp.processEvents()

    return window

    # qtbot.addWidget handles cleanup automatically including before_close_func
    # No manual cleanup needed


@pytest.fixture
def file_load_signals(qtbot, qapp):
    """Create FileLoadWorker instance with proper QObject cleanup.

    NOTE: This fixture name is maintained for backward compatibility.
    It actually creates a FileLoadWorker (QThread with signals as class attributes).

    CRITICAL: QObjects must be properly cleaned up to prevent resource exhaustion.
    After 850+ tests, uncleaned QObjects cause segfaults (see UNIFIED_TESTING_GUIDE).

    This fixture implements the cleanup pattern from the testing guide:
    - Set parent to QApplication for proper Qt ownership
    - Explicit deleteLater() + processEvents() in cleanup
    - Proper thread stopping before cleanup

    Args:
        qtbot: pytest-qt bot fixture
        qapp: QApplication instance

    Yields:
        FileLoadWorker: Properly managed QThread for file loading
    """
    from io_utils.file_load_worker import FileLoadWorker

    worker = FileLoadWorker()
    # Set parent to QApplication for proper Qt ownership/cleanup
    worker.setParent(qapp)

    yield worker

    # Explicit cleanup to prevent memory leaks and segfaults
    try:
        # Stop thread first
        worker.stop()
        if worker.isRunning():
            worker.wait(2000)

        # Then clean up QObject
        worker.setParent(None)
        worker.deleteLater()
        # Process events to ensure deleteLater() is handled
        qapp.processEvents()
    except RuntimeError:
        pass  # Qt object may already be deleted


@pytest.fixture
def file_load_worker(qtbot, qapp):
    """Create FileLoadWorker instance with proper thread cleanup.

    CRITICAL: Background threads must be fully stopped to prevent segfaults.

    This fixture ensures:
    - Worker thread is stopped before fixture teardown
    - Thread.wait() with timeout is called (QThread method)
    - Cleanup happens even if test fails

    Args:
        qtbot: pytest-qt bot fixture (unused, for consistency)
        qapp: QApplication instance for Qt ownership

    Yields:
        FileLoadWorker: Worker with thread safety guarantees
    """
    from io_utils.file_load_worker import FileLoadWorker

    worker = FileLoadWorker()
    worker.setParent(qapp)  # Qt ownership for cleanup
    yield worker

    # Ensure cleanup happens even if test fails
    try:
        worker.stop()
        # stop() already calls wait(2000), but ensure it's stopped
        if worker.isRunning():
            worker.wait(2000)
            if worker.isRunning():
                # Thread didn't stop - log warning but don't fail test
                import warnings

                warnings.warn("Worker thread did not stop within timeout")

        # Clean up QObject
        worker.setParent(None)
        worker.deleteLater()
        qapp.processEvents()
    except (RuntimeError, AttributeError):
        # Worker might already be stopped, that's okay
        pass


@pytest.fixture
def ui_file_load_signals(qtbot, qapp):
    """Create FileLoadWorker from io_utils.file_load_worker with proper QObject cleanup.

    FileLoadWorker is a QThread with signals as class attributes.
    Signals are: tracking_data_loaded, image_sequence_loaded, progress_updated,
    error_occurred, and finished.

    CRITICAL: QObjects must be properly cleaned up to prevent resource exhaustion.

    Args:
        qtbot: pytest-qt bot fixture
        qapp: QApplication instance

    Yields:
        FileLoadWorker: Properly managed QThread for signal emission
    """
    from io_utils.file_load_worker import FileLoadWorker

    worker = FileLoadWorker()
    worker.setParent(qapp)

    yield worker

    try:
        # Stop thread first
        worker.stop()
        if worker.isRunning():
            worker.wait(2000)

        # Then clean up QObject
        worker.setParent(None)
        worker.deleteLater()
        qapp.processEvents()
    except RuntimeError:
        pass


@pytest.fixture
def ui_file_load_worker(ui_file_load_signals):
    """Create FileLoadWorker from io_utils.file_load_worker with proper thread cleanup.

    FileLoadWorker inherits from QThread, so it is the worker and thread combined.

    Args:
        ui_file_load_signals: FileLoadWorker fixture (used to maintain fixture pattern)

    Yields:
        FileLoadWorker: QThread worker with proper cleanup
    """
    # ui_file_load_signals is already a FileLoadWorker instance, just return it
    # This maintains the fixture pattern for backward compatibility
    yield ui_file_load_signals

    try:
        ui_file_load_signals.stop()
        if ui_file_load_signals.isRunning():
            ui_file_load_signals.wait(timeout=2000)
            if ui_file_load_signals.isRunning():
                import warnings

                warnings.warn("FileLoadWorker thread did not stop within timeout")
    except (RuntimeError, AttributeError):
        pass
