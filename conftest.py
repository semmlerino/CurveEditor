"""
Global pytest configuration and fixtures.

Sets up Qt testing environment to run in offscreen mode to prevent
popup windows during testing.
"""

import os

import pytest
from PySide6.QtWidgets import QApplication


def pytest_configure(config: object) -> None:  # pyright: ignore[reportUnusedParameter]
    """Configure pytest environment before tests run."""
    # Set Qt to run in offscreen mode to prevent popup windows
    # Note: Some tests need actual window exposure for keyboard events
    # but offscreen mode will prevent them from appearing on screen
    _ = os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    # Additional Qt test environment settings
    _ = os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;qt.qpa.*=false")


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    # Check if application already exists
    app = QApplication.instance()
    if app is None:
        # Create new application in offscreen mode
        app = QApplication([])

    yield app

    # Don't quit the app - let pytest-qt handle it


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singleton state between tests to prevent state pollution."""
    # This runs before each test
    yield

    # This runs after each test
    try:
        # Reset store manager singleton
        from stores.store_manager import StoreManager

        StoreManager.reset()
    except ImportError:
        pass  # Store manager might not exist in all test contexts

    try:
        # Reset service singletons
        from services import reset_all_services

        reset_all_services()
    except ImportError:
        pass  # Services might not exist in all test contexts
