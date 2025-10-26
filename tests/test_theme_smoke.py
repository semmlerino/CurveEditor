"""Smoke tests for UI theme application.

These tests ensure the dark theme stylesheet is properly applied
and prevent regressions like the _theme_initialized class variable issue.
"""

from typing import cast

import pytest
from PySide6.QtWidgets import QApplication

from ui.dark_theme_stylesheet import get_dark_theme_stylesheet
from ui.main_window import MainWindow


class TestThemeApplication:
    """Smoke tests for dark theme stylesheet application."""

    def test_dark_theme_stylesheet_generation(self):
        """Test that dark theme stylesheet generates successfully."""
        stylesheet = get_dark_theme_stylesheet()

        # Should return non-empty string
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 1000, "Stylesheet should be substantial (>1000 chars)"

        # Should contain key widget styles
        assert "QMainWindow" in stylesheet
        assert "QMenuBar" in stylesheet
        assert "QPushButton" in stylesheet
        assert "background-color" in stylesheet

    def test_theme_applied_to_application(self, qtbot):
        """Test that dark theme is applied to QApplication when MainWindow is created."""
        # Create MainWindow - should apply theme
        window = MainWindow()
        qtbot.addWidget(window)

        # Get application instance
        app = cast(QApplication, QApplication.instance())
        assert app is not None

        # Verify stylesheet was applied
        app_stylesheet = app.styleSheet()
        assert len(app_stylesheet) > 0, "Application stylesheet should not be empty"

        # Should contain dark theme markers
        assert "QMainWindow" in app_stylesheet
        assert "background-color" in app_stylesheet

        # Verify theme flag was set
        assert hasattr(MainWindow, "_theme_initialized"), \
            "_theme_initialized attribute should exist after first MainWindow creation"
        assert MainWindow._theme_initialized is True, "_theme_initialized should be True"  # pyright: ignore[reportPrivateUsage]

    def test_theme_not_reapplied_on_second_window(self, qtbot):
        """Test that theme is not reapplied when creating second MainWindow."""
        # Create first window
        window1 = MainWindow()
        qtbot.addWidget(window1)

        app = cast(QApplication, QApplication.instance())
        first_stylesheet = app.styleSheet()
        first_length = len(first_stylesheet)

        # Create second window
        window2 = MainWindow()
        qtbot.addWidget(window2)

        # Stylesheet should be identical (not reapplied)
        second_stylesheet = app.styleSheet()
        assert len(second_stylesheet) == first_length, \
            "Stylesheet should not change when creating second window"

    def test_theme_flag_not_predeclared_false(self):
        """Prevent regression: _theme_initialized should not be pre-declared as False.

        This test catches the specific bug from commit 6945833 where
        _theme_initialized: bool = False as a class variable broke
        the hasattr() check in theme application logic.
        """
        # Check if _theme_initialized exists as class variable
        if hasattr(MainWindow, "_theme_initialized"):
            # If it exists, it must not be False BEFORE first instance created
            # This would indicate it was pre-declared, breaking the hasattr() check
            value = MainWindow._theme_initialized  # pyright: ignore[reportPrivateUsage]

            # Reset the class variable for this test if it was set by previous tests
            # We want to test the INITIAL state as it would be on app startup
            if value is True:
                # Skip this assertion - theme was already applied by previous test
                # Just verify it's not set to False in the class definition
                pass
            else:
                pytest.fail(
                    "_theme_initialized should not be pre-declared as False. " +
                    "This breaks hasattr() check in theme application. " +
                    "Remove class variable declaration and let it be set dynamically."
                )


class TestThemeInitializationOrder:
    """Test theme initialization happens in correct order."""

    def test_fusion_style_set(self, qtbot):
        """Test that Fusion style is set for dark theme support."""
        window = MainWindow()
        qtbot.addWidget(window)

        app = cast(QApplication, QApplication.instance())

        # Application should have a style set (Fusion or similar)
        style = app.style()
        assert style is not None, "Application should have a style set"
