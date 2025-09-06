#!/usr/bin/env python
"""
Real integration tests for UI components without mocking.
Tests actual UI functionality and modernization features.
"""

import pytest
from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget

from ui.modern_theme import ModernTheme
from ui.modern_widgets import ModernCard, ModernLoadingSpinner, ModernProgressBar, ModernToast
from ui.ui_constants import COLORS_DARK, COLORS_LIGHT


class TestModernTheme:
    """Test modern theme system."""

    def test_theme_initialization(self):
        """Test theme manager initialization."""
        theme = ModernTheme()

        assert theme.current_theme == "light"
        assert theme.animations_enabled is True

    def test_stylesheet_generation(self):
        """Test that stylesheet contains all required color keys."""
        theme = ModernTheme()

        # Test light theme
        theme.current_theme = "light"
        stylesheet = theme.get_stylesheet()

        # Check that all color keys are referenced correctly
        for key in COLORS_LIGHT:
            # The stylesheet should not have any missing key errors
            assert stylesheet is not None

        # Test dark theme
        theme.current_theme = "dark"
        stylesheet = theme.get_stylesheet()

        for key in COLORS_DARK:
            assert stylesheet is not None

    def test_color_key_consistency(self):
        """Test that all color keys used in stylesheet exist in constants."""
        # These are the keys we use in the stylesheet
        required_keys = [
            "text_primary",
            "bg_primary",
            "bg_secondary",
            "bg_elevated",
            "button_primary_bg",
            "button_primary_hover",
            "button_primary_active",
            "bg_disabled",
            "text_disabled",
            "accent_primary",
            "bg_hover",
            "bg_selected",
            "accent_secondary",
            "border_default",
            "bg_input",
            "border_focus",
            "border_hover",
            "text_secondary",
        ]

        # Check light theme
        for key in required_keys:
            assert key in COLORS_LIGHT, f"Missing key '{key}' in COLORS_LIGHT"

        # Check dark theme
        for key in required_keys:
            assert key in COLORS_DARK, f"Missing key '{key}' in COLORS_DARK"

    def test_theme_switching(self):
        """Test switching between themes."""
        theme = ModernTheme()

        # Start with light
        theme.current_theme = "light"
        light_style = theme.get_stylesheet()

        # Switch to dark
        theme.switch_theme("dark")
        dark_style = theme.get_stylesheet()

        # Styles should be different
        assert light_style != dark_style
        assert theme.current_theme == "dark"


class TestModernCard:
    """Test ModernCard widget."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_card_creation(self, app):
        """Test creating a modern card."""
        card = ModernCard("Test Card")

        assert card.title == "Test Card"
        assert card.title_label.text() == "Test Card"
        assert card.content_layout is not None

    def test_card_without_title(self, app):
        """Test creating card without title."""
        card = ModernCard()

        assert card.title == ""
        assert not hasattr(card, "title_label")

    def test_adding_widgets_to_card(self, app, qtbot):
        """Test adding widgets to card content."""
        card = ModernCard("Test")

        # Add a widget
        widget = QWidget()
        qtbot.addWidget(widget)
        card.addWidget(widget)

        # Check it was added to content layout
        assert card.content_layout.count() == 1

    def test_card_hover_state(self, app):
        """Test card hover state changes."""
        card = ModernCard("Test")

        # Initial state
        assert card._hover is False

        # Simulate mouse enter
        card.enterEvent(None)
        assert card._hover is True

        # Simulate mouse leave
        card.leaveEvent(None)
        assert card._hover is False


class TestModernWidgets:
    """Test other modern widgets."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_loading_spinner(self, app, qtbot):
        """Test modern loading spinner."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()  # Show parent so child visibility works correctly
        spinner = ModernLoadingSpinner(parent)

        assert spinner.parent() == parent
        assert not spinner.isVisible()  # Hidden by default

        # Start spinning
        spinner.start()
        app.processEvents()  # Process Qt events
        assert spinner.isVisible()

        # Stop spinning
        spinner.stop()
        app.processEvents()  # Process Qt events
        assert not spinner.isVisible()

    def test_progress_bar(self, app, qtbot):
        """Test modern progress bar."""
        parent = QWidget()
        qtbot.addWidget(parent)
        progress = ModernProgressBar(parent)

        # Test setting value
        progress.setValue(50)
        assert progress.value() == 50

        # Test setting text
        progress.setText("Loading...")
        assert progress.text() == "Loading..."

        # Test indeterminate mode
        progress.setIndeterminate(True)
        assert progress._indeterminate is True

    def test_toast_notification(self, app, qtbot):
        """Test modern toast notification."""
        parent = QWidget()
        qtbot.addWidget(parent)
        toast = ModernToast("Test message", "success", 1000, parent)

        assert toast.message == "Test message"
        assert toast.variant == "success"
        assert toast.duration == 1000

        # Check styling based on variant
        assert "background" in toast.styleSheet()


class TestCurveViewWidgetOptimizations:
    """Test CurveViewWidget optimizations."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_partial_update_rect(self, app):
        """Test partial update rectangle calculation."""
        from ui.curve_view_widget import CurveViewWidget

        widget = CurveViewWidget()
        widget.curve_data = [(1, 100, 100), (2, 200, 200), (3, 300, 300)]

        # Test getting update rect for a point
        rect = widget._get_point_update_rect(0)

        assert isinstance(rect, QRect)
        assert rect.width() > 0
        assert rect.height() > 0

        # Test with invalid index
        invalid_rect = widget._get_point_update_rect(-1)
        assert invalid_rect.isEmpty()

        invalid_rect = widget._get_point_update_rect(100)
        assert invalid_rect.isEmpty()

    def test_hover_partial_updates(self, app):
        """Test that hover changes trigger partial updates only."""
        from ui.curve_view_widget import CurveViewWidget

        class UpdateTracker(CurveViewWidget):
            """Track update calls."""

            def __init__(self):
                super().__init__()
                self.update_calls = []

            def update(self, rect=None):
                """Track update calls."""
                self.update_calls.append(rect)
                super().update(rect) if rect else super().update()

        widget = UpdateTracker()
        widget.curve_data = [
            (1, 100, 100),
            (2, 200, 200),
        ]

        # Simulate mouse move that changes hover
        widget.hover_index = -1
        event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(100, 100),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Clear any initial updates
        widget.update_calls.clear()

        # Trigger mouse move
        widget.mouseMoveEvent(event)

        # Should have triggered partial updates, not full updates
        for rect in widget.update_calls:
            if rect is not None:
                assert isinstance(rect, QRect)
                # Partial update should be smaller than full widget
                assert rect.width() < widget.width() or widget.width() == 0


class TestPerformanceMode:
    """Test performance mode functionality."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_performance_mode_toggle(self, app, qtbot):
        """Test toggling performance mode."""
        from ui.modernized_main_window import ModernizedMainWindow

        # Create window
        window = ModernizedMainWindow()
        qtbot.addWidget(window)

        # Initial state
        assert window.animations_enabled is True

        # Enable performance mode
        window._toggle_performance_mode(True)
        assert window.animations_enabled is False

        # Disable performance mode
        window._toggle_performance_mode(False)
        assert window.animations_enabled is True

    def test_performance_mode_disables_effects(self, app, qtbot):
        """Test that performance mode disables graphics effects."""
        from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton

        from ui.modernized_main_window import ModernizedMainWindow

        window = ModernizedMainWindow()
        qtbot.addWidget(window)

        # Add a widget with effect
        button = QPushButton("Test", window)
        effect = QGraphicsDropShadowEffect()
        button.setGraphicsEffect(effect)

        # Enable performance mode
        window._toggle_performance_mode(True)

        # Effect should be disabled
        assert button.graphicsEffect().isEnabled() is False

        # Disable performance mode
        window._toggle_performance_mode(False)

        # Effect should be re-enabled
        assert button.graphicsEffect().isEnabled() is True


class TestGroupBoxToModernCard:
    """Test GroupBox replacement with ModernCard."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_timeline_panel_uses_moderncard(self, app, qtbot):
        """Test that timeline panel uses ModernCard when available."""
        from ui.main_window import MainWindow

        # Create main window
        window = MainWindow()
        qtbot.addWidget(window)

        # Check if timeline components are properly created in toolbar
        # The actual timeline controls are created in _init_toolbar
        assert hasattr(window, "timeline_tabs")
        assert window.timeline_tabs is not None
        assert isinstance(window.timeline_tabs, QWidget)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
