#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for all tests.

This module provides common test fixtures and configurations, including
proper Qt application initialization for tests that require Qt components.
"""

from collections.abc import Generator

import pytest
from PySide6.QtWidgets import QApplication

# Global variable to track QApplication instance
_qapp_instance: QApplication | None = None


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """
    Create a QApplication instance for the entire test session.

    This fixture ensures that only one QApplication instance exists
    throughout the test session, preventing Qt crashes when running
    multiple tests that use Qt components.

    The fixture has session scope, meaning it's created once at the
    beginning of the test session and destroyed at the end.

    Yields:
        QApplication: The Qt application instance
    """
    global _qapp_instance

    # Check if QApplication instance already exists
    app = QApplication.instance()

    if app is None:
        # Create new QApplication instance
        app = QApplication([])
        _qapp_instance = app

    yield app

    # Cleanup is handled automatically by Qt when Python exits


@pytest.fixture(autouse=True)
def qt_cleanup(qapp: QApplication) -> Generator[None, None, None]:
    """
    Automatically clean up Qt resources after each test.

    This fixture runs automatically for every test (autouse=True) and
    ensures that Qt resources are properly cleaned up between tests.
    It depends on the qapp fixture to ensure QApplication exists.

    Args:
        qapp: The QApplication instance from the qapp fixture

    Yields:
        None
    """
    # Let the test run
    yield

    # Process any pending Qt events after the test
    qapp.processEvents()

    # Clean up singleton services to prevent test interference
    try:
        from services.logging_service import LoggingService

        LoggingService.close()
    except ImportError:
        pass  # LoggingService might not be available in all tests

    # Clear transformation service caches to prevent test contamination
    try:
        from services.transformation_service import TransformationService

        TransformationService.clear_cache()
    except ImportError:
        pass  # TransformationService might not be available in all tests

    # Clear any other service caches that might cause test contamination
    try:
        from ui.ui_scaling import UIScaling

        if hasattr(UIScaling, "clear_cache"):
            UIScaling.clear_cache()
    except (ImportError, AttributeError):
        pass  # UIScaling cache might not exist or be available

    # Force garbage collection of Qt objects
    import gc

    gc.collect()


def pytest_configure(config: pytest.Config) -> None:
    """
    Configure pytest with custom markers and settings.

    Args:
        config: The pytest configuration object
    """
    # Add custom markers
    config.addinivalue_line("markers", "qt_required: mark test as requiring Qt (QApplication)")
    config.addinivalue_line("markers", "skip_qt_cleanup: mark test to skip automatic Qt cleanup")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """
    Modify test items during collection phase.

    This hook automatically marks tests that import Qt modules as requiring Qt.

    Args:
        config: The pytest configuration object
        items: list of collected test items
    """
    for item in items:
        # Check if the test module imports Qt
        test_module = item.module
        if hasattr(test_module, "__file__"):
            # Read the test file to check for Qt imports
            try:
                with open(test_module.__file__) as f:
                    content = f.read()
                    if "QFileDialog" in content or "QApplication" in content or "from PySide6" in content:
                        # Mark test as requiring Qt
                        item.add_marker(pytest.mark.qt_required)
            except Exception:
                pass


# Common fixture types used across tests
try:
    from data.curve_view import CurveView
    PointsList = list[tuple[int, float, float]]
except ImportError:
    PointsList = list


@pytest.fixture
def curve_view(qapp) -> "CurveView":
    """Create a CurveView instance for testing."""
    from data.curve_view import CurveView
    return CurveView()


@pytest.fixture
def sample_points() -> PointsList:
    """Sample point data for testing."""
    return [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]


@pytest.fixture
def large_sample_points() -> PointsList:
    """Larger sample point data for testing."""
    return [
        (1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0),
        (4, 250.0, 350.0), (5, 300.0, 400.0), (6, 350.0, 450.0)
    ]
