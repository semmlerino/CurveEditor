#!/usr/bin/env python
"""
Investigate Qt threading issues that may cause segmentation faults.
Following UNIFIED_TESTING_GUIDE principles for Qt safety.
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

import pytest
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


class TestQtThreadingInvestigation:
    """Test Qt threading safety issues."""

    def test_single_main_window_creation(self, qtbot, qapp):
        """Test single MainWindow creation - should always work."""
        window = MainWindow()
        qtbot.addWidget(window)  # Critical: Auto cleanup

        # Verify window was created successfully
        assert window is not None
        assert hasattr(window, "curve_widget")

    def test_multiple_main_windows_sequential(self, qtbot, qapp):
        """Test multiple MainWindow creations sequentially."""
        windows = []

        for i in range(3):
            window = MainWindow()
            qtbot.addWidget(window)  # Critical: Auto cleanup
            windows.append(window)

            # Each window should be valid
            assert window is not None
            assert hasattr(window, "curve_widget")

    @pytest.mark.slow
    def test_stylesheet_setting_safety(self, qtbot, qapp):
        """Test if setting stylesheet multiple times causes issues."""
        from ui.dark_theme_stylesheet import get_dark_theme_stylesheet

        # Get the application instance
        app = QApplication.instance()
        assert app is not None
        assert isinstance(app, QApplication), "Expected QApplication instance"

        # Try setting stylesheet multiple times (this might be the issue)
        for i in range(5):
            try:
                stylesheet = get_dark_theme_stylesheet()
                app.setStyleSheet(stylesheet)
                app.processEvents()  # Process any pending events
            except Exception as e:
                pytest.fail(f"Stylesheet setting failed on iteration {i}: {e}")

    def test_main_window_with_explicit_cleanup(self, qtbot, qapp):
        """Test MainWindow with explicit cleanup following UNIFIED_TESTING_GUIDE."""
        window = None
        try:
            window = MainWindow()
            qtbot.addWidget(window)  # qtbot handles cleanup automatically

            # Test basic functionality
            assert window.curve_widget is not None

            # Show and wait for exposure (following guide patterns)
            window.show()
            qtbot.waitExposed(window)

        except RuntimeError as e:
            # Following guide: catch RuntimeError for deleted widgets
            if "Internal C++ object already deleted" in str(e):
                # This is expected during cleanup, pass
                pass
            else:
                raise

    def test_stylesheet_isolation(self, qtbot, qapp):
        """Test if stylesheet changes affect other windows."""
        # Create first window
        window1 = MainWindow()
        qtbot.addWidget(window1)

        # Store original stylesheet
        app = QApplication.instance()
        assert isinstance(app, QApplication), "Expected QApplication instance"
        app.styleSheet()

        # Create second window (this might trigger the issue)
        window2 = MainWindow()
        qtbot.addWidget(window2)

        # Verify both windows exist and are functional
        assert window1 is not None
        assert window2 is not None

        # Verify stylesheet is still set
        current_stylesheet = app.styleSheet()
        assert len(current_stylesheet) > 0  # Should have some stylesheet content
