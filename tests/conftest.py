#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for all tests.

This module provides common test fixtures and configurations, including
proper Qt application initialization for tests that require Qt components.
"""

import pytest
from PySide6.QtWidgets import QApplication
from typing import Generator, Optional


# Global variable to track QApplication instance
_qapp_instance: Optional[QApplication] = None


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
    config.addinivalue_line(
        "markers", 
        "qt_required: mark test as requiring Qt (QApplication)"
    )
    config.addinivalue_line(
        "markers",
        "skip_qt_cleanup: mark test to skip automatic Qt cleanup"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """
    Modify test items during collection phase.
    
    This hook automatically marks tests that import Qt modules as requiring Qt.
    
    Args:
        config: The pytest configuration object
        items: List of collected test items
    """
    for item in items:
        # Check if the test module imports Qt
        test_module = item.module
        if hasattr(test_module, '__file__'):
            # Read the test file to check for Qt imports
            try:
                with open(test_module.__file__, 'r') as f:
                    content = f.read()
                    if 'QFileDialog' in content or 'QApplication' in content or 'from PySide6' in content:
                        # Mark test as requiring Qt
                        item.add_marker(pytest.mark.qt_required)
            except Exception:
                pass