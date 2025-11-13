"""
Global pytest configuration and fixtures.

Sets up Qt testing environment to run in offscreen mode to prevent
popup windows during testing.
"""

import os

import pytest

# Import all fixtures to make them globally available
from tests.fixtures import *


def pytest_configure(config: object) -> None:  # pyright: ignore[reportUnusedParameter]
    """Configure pytest environment before tests run."""
    # Set Qt to run in offscreen mode to prevent popup windows
    # Note: Some tests need actual window exposure for keyboard events
    # but offscreen mode will prevent them from appearing on screen
    _ = os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    # Additional Qt test environment settings
    _ = os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;qt.qpa.*=false")


# qapp fixture is imported from tests.fixtures.qt_fixtures
# No need to redefine it here


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

    try:
        # Reset service facade singleton
        from ui.service_facade import reset_service_facade

        reset_service_facade()
    except ImportError:
        pass  # Service facade might not exist in all test contexts

    # Force event processing to clear any pending operations
    try:
        from PySide6.QtCore import QCoreApplication

        app = QCoreApplication.instance()
        if app:
            for _ in range(10):
                app.processEvents()
                app.sendPostedEvents(None, 0)
    except ImportError:
        pass
