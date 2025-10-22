#!/usr/bin/env python
"""
Safe test runner for Qt tests that ensures proper resource management.

This script runs the test suite with additional safety checks for Qt resources,
preventing common issues like:
- QPaintDevice destruction while being painted
- QPixmap usage in non-GUI threads
- Event loop blocking
- Widget cleanup issues
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

import atexit
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tests.test_utils import cleanup_qt_widgets  # noqa: E402


def cleanup_qt():
    """Ensure Qt is properly cleaned up."""
    app = QApplication.instance()
    # QApplication.instance() returns QCoreApplication | None, but cleanup_qt_widgets expects QApplication | None
    qt_app = app if isinstance(app, QApplication) else None
    cleanup_qt_widgets(qt_app)
    if app:
        app.quit()
        app.deleteLater()


def signal_handler(signum, frame):
    """Handle interruption signals gracefully."""
    print(f"\nReceived signal {signum}. Cleaning up Qt resources...")
    cleanup_qt()
    sys.exit(1)


def main():
    """Run tests with Qt safety measures."""
    # Register cleanup handlers
    atexit.register(cleanup_qt)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Ensure QApplication exists for tests
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Configure Qt for testing
    app.setAttribute(Qt.ApplicationAttribute.AA_Use96Dpi, True)  # Consistent DPI
    if isinstance(app, QApplication):
        app.setQuitOnLastWindowClosed(False)  # Don't quit during tests

    # Run pytest with recommended options for Qt testing
    pytest_args = [
        "-v",  # Verbose output
        "--tb=short",  # Shorter traceback format
        "-W",
        "ignore::DeprecationWarning",  # Ignore deprecation warnings
        "--maxfail=5",  # Stop after 5 failures
        "-p",
        "no:cacheprovider",  # Disable cache to avoid stale state
    ]

    # Add any command line arguments
    pytest_args.extend(sys.argv[1:])

    # Add tests directory if no specific tests specified
    if not any(arg.startswith("tests/") or arg.endswith(".py") for arg in sys.argv[1:]):
        pytest_args.append("tests/")

    print("Running tests with Qt safety measures...")
    print(f"Arguments: {' '.join(pytest_args)}")

    # Run tests
    exit_code = pytest.main(pytest_args)

    # Clean up Qt
    cleanup_qt()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
