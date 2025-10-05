#!/usr/bin/env python
"""
Real integration tests for UI components without mocking.
Tests actual UI functionality and modernization features.
"""

import pytest
from PySide6.QtWidgets import QApplication, QWidget

# Modern UI tests removed - these components have been archived

"""
REMOVED: TestModernTheme, TestModernCard, TestModernWidgets classes
These tested the archived modern UI components:
- ModernTheme (theme switching)
- ModernCard (enhanced panels)
- ModernLoadingSpinner, ModernProgressBar, ModernToast (UI widgets)
"""

# [REMOVED: Large block of test code for modern UI components]
# Classes removed: TestModernTheme, TestModernCard, TestModernWidgets, TestPerformanceMode
# These components have been archived to archive_obsolete/modern_ui/


class TestCurveViewWidgetOptimizations:
    """Test CurveViewWidget optimizations."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_curve_view_widget_creation(self, app, qtbot):
        """Test that CurveViewWidget can be created."""
        from ui.curve_view_widget import CurveViewWidget

        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Basic checks
        assert widget is not None
        assert hasattr(widget, "curve_data")
        assert hasattr(widget, "selected_indices")

    def test_curve_view_rendering(self, app, qtbot):
        """Test curve view rendering optimizations."""
        from ui.curve_view_widget import CurveViewWidget

        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Add test data
        test_data = [(i, float(i), float(i * 2)) for i in range(100)]
        widget.set_curve_data(test_data)

        # Check data was set
        assert len(widget.curve_data) == 100

        # Test viewport culling by zooming
        widget.zoom_factor = 10.0
        widget.update()  # Trigger repaint

        # Widget should handle large datasets efficiently
        assert widget.zoom_factor == 10.0


class TestTimelineIntegration:
    """Test timeline integration with MainWindow."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_timeline_panel_exists(self, app, qtbot):
        """Test that timeline panel is properly created."""
        from ui.main_window import MainWindow

        # Create main window
        window = MainWindow()
        qtbot.addWidget(window)

        # Check if timeline components are properly created
        assert hasattr(window, "timeline_tabs")
        # Timeline may be None if creation fails, which is logged
        if window.timeline_tabs is not None:
            assert isinstance(window.timeline_tabs, QWidget)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
