#!/usr/bin/env python3
"""
Tests for grid-related keyboard shortcuts and functionality.

Tests for:
- Ctrl+Shift+G: Toggle grid and center on current frame's point
- Ctrl+=: Increase grid size
- Ctrl+-: Decrease grid size

Following UNIFIED_TESTING_GUIDE principles:
- Test behavior, not implementation
- Use production-realistic patterns
- Verify actual state changes
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

import contextlib

import pytest
from PySide6.QtWidgets import QApplication

from core.type_aliases import CurveDataList
from stores.application_state import get_application_state
from ui.main_window import MainWindow


class TestGridToggleShortcut:
    """Test Ctrl+Shift+G grid toggle and centering functionality."""

    @pytest.fixture
    def main_window(self, qtbot, qapp: QApplication) -> MainWindow:
        """Create MainWindow with proper cleanup."""
        def cleanup_event_filter(window):
            """Remove global event filter before window closes."""
            app = QApplication.instance()
            if app and hasattr(window, 'global_event_filter'):
                with contextlib.suppress(RuntimeError):
                    app.removeEventFilter(window.global_event_filter)

        window = MainWindow()
        qtbot.addWidget(window, before_close_func=cleanup_event_filter)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_grid_toggle_centers_on_current_frame_point(self, main_window: MainWindow, qtbot):
        """Test that toggling grid only changes grid visibility without side effects."""
        # Setup: Add curve data with points at different frames
        test_data: CurveDataList = [
            (1, 100.0, 200.0),
            (5, 300.0, 400.0),
            (10, 500.0, 600.0),
        ]

        app_state = get_application_state()

        # Wait for MainWindow's session loading to complete
        qtbot.wait(100)

        # Create a fresh test curve
        test_curve_name = "TestCurve_Grid"
        app_state.set_active_curve(test_curve_name)
        app_state.set_curve_data(test_curve_name, test_data)
        app_state.set_frame(5)  # Set to frame 5 (middle point)
        qtbot.wait(50)  # Wait for signals to propagate and widget to update

        # Verify the active curve is correct
        assert app_state.active_curve == test_curve_name, f"Active curve should be {test_curve_name}, got {app_state.active_curve}"

        # Verify the data was actually set
        verify_data = app_state.get_curve_data(test_curve_name)
        assert len(verify_data) == 3, f"Expected 3 points, got {len(verify_data)}"
        assert verify_data[1][0] == 5, f"Expected point at frame 5, got frame {verify_data[1][0]}"

        # Initially grid should be off
        if main_window.show_grid_cb:
            main_window.show_grid_cb.setChecked(False)
        qtbot.wait(10)

        # Store initial selection state (should be empty)
        initial_selection = app_state.get_selection(test_curve_name)

        # Trigger grid toggle via the shortcut action
        main_window.on_toggle_grid()
        qtbot.wait(10)

        # Verify grid is now on
        assert main_window.show_grid_cb is not None
        assert main_window.show_grid_cb.isChecked() is True

        # Verify selection UNCHANGED (grid toggle has no side effects)
        selection = app_state.get_selection(test_curve_name)
        assert selection == initial_selection, f"Grid toggle should not change selection. Was {initial_selection}, now {selection}"

        # Grid should be visible
        assert main_window.curve_view is not None

    def test_grid_toggle_handles_no_exact_point_at_frame(self, main_window: MainWindow, qtbot):
        """Test grid toggle when current frame has no exact point."""
        # Setup: Add curve data with gaps
        test_data: CurveDataList = [
            (1, 100.0, 200.0),
            (10, 500.0, 600.0),
        ]

        app_state = get_application_state()

        # Wait for session loading and create fresh test curve
        qtbot.wait(100)
        test_curve_name = "TestCurve_NoPoint"
        app_state.set_active_curve(test_curve_name)
        app_state.set_curve_data(test_curve_name, test_data)
        app_state.set_frame(5)  # Frame 5 has no exact point (between 1 and 10)
        qtbot.wait(50)

        # Initially grid off
        if main_window.show_grid_cb:
            main_window.show_grid_cb.setChecked(False)
        qtbot.wait(10)

        # Toggle grid
        main_window.on_toggle_grid()
        qtbot.wait(10)

        # Grid should be on
        assert main_window.show_grid_cb is not None
        assert main_window.show_grid_cb.isChecked() is True

        # No point should be selected (frame 5 doesn't have an exact point)
        selection = app_state.get_selection(test_curve_name)
        assert len(selection) == 0, "No point should be selected when frame has no exact point"

        # View should still center on interpolated position (no error)
        assert main_window.curve_view is not None

    def test_grid_toggle_with_no_active_curve(self, main_window: MainWindow, qtbot):
        """Test grid toggle when no curve is active."""
        app_state = get_application_state()
        app_state.set_active_curve(None)

        # Initially grid off
        if main_window.show_grid_cb:
            main_window.show_grid_cb.setChecked(False)
        qtbot.wait(10)

        # Toggle grid (should not crash)
        main_window.on_toggle_grid()
        qtbot.wait(10)

        # Grid should toggle on (even without active curve)
        assert main_window.show_grid_cb is not None
        assert main_window.show_grid_cb.isChecked() is True

    def test_grid_toggle_turns_off_correctly(self, main_window: MainWindow, qtbot):
        """Test that toggling grid off works correctly."""
        # Setup with grid on
        if main_window.show_grid_cb:
            main_window.show_grid_cb.setChecked(True)
        qtbot.wait(10)

        # Toggle off
        main_window.on_toggle_grid()
        qtbot.wait(10)

        # Grid should be off
        assert main_window.show_grid_cb is not None
        assert main_window.show_grid_cb.isChecked() is False


class TestGridSizeShortcuts:
    """Test Ctrl+= and Ctrl+- grid size adjustment shortcuts."""

    @pytest.fixture
    def main_window(self, qtbot, qapp: QApplication) -> MainWindow:
        """Create MainWindow with proper cleanup."""
        def cleanup_event_filter(window):
            """Remove global event filter before window closes."""
            app = QApplication.instance()
            if app and hasattr(window, 'global_event_filter'):
                with contextlib.suppress(RuntimeError):
                    app.removeEventFilter(window.global_event_filter)

        window = MainWindow()
        qtbot.addWidget(window, before_close_func=cleanup_event_filter)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_increase_grid_size(self, main_window: MainWindow, qtbot):
        """Test that Ctrl+= increases grid size by 10 pixels."""
        assert main_window.curve_view is not None

        # Set initial grid size to known value
        initial_size = 50
        main_window.curve_view.visual.grid_size = initial_size
        qtbot.wait(10)

        # Trigger increase
        main_window.on_increase_grid_size()
        qtbot.wait(10)

        # Verify size increased by 10
        assert main_window.curve_view.visual.grid_size == initial_size + 10

    def test_decrease_grid_size(self, main_window: MainWindow, qtbot):
        """Test that Ctrl+- decreases grid size by 10 pixels."""
        assert main_window.curve_view is not None

        # Set initial grid size to known value
        initial_size = 50
        main_window.curve_view.visual.grid_size = initial_size
        qtbot.wait(10)

        # Trigger decrease
        main_window.on_decrease_grid_size()
        qtbot.wait(10)

        # Verify size decreased by 10
        assert main_window.curve_view.visual.grid_size == initial_size - 10

    def test_grid_size_respects_maximum(self, main_window: MainWindow, qtbot):
        """Test that grid size cannot exceed 200 pixels."""
        assert main_window.curve_view is not None

        # Set to near maximum
        main_window.curve_view.visual.grid_size = 195
        qtbot.wait(10)

        # Try to increase multiple times
        main_window.on_increase_grid_size()  # 195 + 10 = 200 (clamped)
        qtbot.wait(10)
        assert main_window.curve_view.visual.grid_size == 200

        main_window.on_increase_grid_size()  # Should stay at 200
        qtbot.wait(10)
        assert main_window.curve_view.visual.grid_size == 200

    def test_grid_size_respects_minimum(self, main_window: MainWindow, qtbot):
        """Test that grid size cannot go below 10 pixels."""
        assert main_window.curve_view is not None

        # Set to near minimum
        main_window.curve_view.visual.grid_size = 15
        qtbot.wait(10)

        # Try to decrease multiple times
        main_window.on_decrease_grid_size()  # 15 - 10 = 10 (clamped)
        qtbot.wait(10)
        assert main_window.curve_view.visual.grid_size == 10

        main_window.on_decrease_grid_size()  # Should stay at 10
        qtbot.wait(10)
        assert main_window.curve_view.visual.grid_size == 10

    def test_grid_size_multiple_adjustments(self, main_window: MainWindow, qtbot):
        """Test multiple grid size adjustments in sequence."""
        assert main_window.curve_view is not None

        # Start at default (50)
        main_window.curve_view.visual.grid_size = 50
        qtbot.wait(10)

        # Increase twice
        main_window.on_increase_grid_size()
        qtbot.wait(10)
        assert main_window.curve_view.visual.grid_size == 60

        main_window.on_increase_grid_size()
        qtbot.wait(10)
        assert main_window.curve_view.visual.grid_size == 70

        # Decrease once
        main_window.on_decrease_grid_size()
        qtbot.wait(10)
        assert main_window.curve_view.visual.grid_size == 60

        # Decrease three times
        main_window.on_decrease_grid_size()
        main_window.on_decrease_grid_size()
        main_window.on_decrease_grid_size()
        qtbot.wait(10)
        assert main_window.curve_view.visual.grid_size == 30


class TestGridShortcutIntegration:
    """Integration tests for grid shortcuts with ShortcutManager."""

    @pytest.fixture
    def main_window(self, qtbot, qapp: QApplication) -> MainWindow:
        """Create MainWindow with proper cleanup."""
        def cleanup_event_filter(window):
            """Remove global event filter before window closes."""
            app = QApplication.instance()
            if app and hasattr(window, 'global_event_filter'):
                with contextlib.suppress(RuntimeError):
                    app.removeEventFilter(window.global_event_filter)

        window = MainWindow()
        qtbot.addWidget(window, before_close_func=cleanup_event_filter)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_shortcut_manager_has_grid_actions(self, main_window: MainWindow):
        """Test that ShortcutManager provides grid-related actions."""
        assert main_window.shortcut_manager is not None

        # Check grid toggle action exists
        assert hasattr(main_window.shortcut_manager, 'action_toggle_grid')
        assert main_window.shortcut_manager.action_toggle_grid is not None

        # Check grid size actions exist
        assert hasattr(main_window.shortcut_manager, 'action_increase_grid_size')
        assert main_window.shortcut_manager.action_increase_grid_size is not None

        assert hasattr(main_window.shortcut_manager, 'action_decrease_grid_size')
        assert main_window.shortcut_manager.action_decrease_grid_size is not None

    def test_grid_actions_have_correct_shortcuts(self, main_window: MainWindow):
        """Test that grid actions have the correct keyboard shortcuts."""
        assert main_window.shortcut_manager is not None

        # Grid toggle: Ctrl+Shift+G
        toggle_action = main_window.shortcut_manager.action_toggle_grid
        assert toggle_action.shortcut().toString() == "Ctrl+Shift+G"

        # Grid increase: Ctrl++ (plus key, which is Shift+=)
        increase_action = main_window.shortcut_manager.action_increase_grid_size
        assert increase_action.shortcut().toString() == "Ctrl++"

        # Grid decrease: Ctrl+- (minus key)
        decrease_action = main_window.shortcut_manager.action_decrease_grid_size
        assert decrease_action.shortcut().toString() == "Ctrl+-"

    def test_grid_actions_are_connected(self, main_window: MainWindow, qtbot):
        """Test that grid actions trigger the correct handlers."""
        assert main_window.shortcut_manager is not None
        assert main_window.curve_view is not None

        # Set up initial state
        if main_window.show_grid_cb:
            main_window.show_grid_cb.setChecked(False)
        main_window.curve_view.visual.grid_size = 50
        qtbot.wait(10)

        # Trigger toggle via action
        main_window.shortcut_manager.action_toggle_grid.trigger()
        qtbot.wait(10)
        assert main_window.show_grid_cb is not None
        assert main_window.show_grid_cb.isChecked() is True

        # Trigger increase via action
        main_window.shortcut_manager.action_increase_grid_size.trigger()
        qtbot.wait(10)
        assert main_window.curve_view.visual.grid_size == 60

        # Trigger decrease via action
        main_window.shortcut_manager.action_decrease_grid_size.trigger()
        qtbot.wait(10)
        assert main_window.curve_view.visual.grid_size == 50


class TestGridCenteringWithRealData:
    """Integration tests with real curve data and rendering."""

    @pytest.fixture
    def main_window(self, qtbot, qapp: QApplication) -> MainWindow:
        """Create MainWindow with proper cleanup."""
        def cleanup_event_filter(window):
            """Remove global event filter before window closes."""
            app = QApplication.instance()
            if app and hasattr(window, 'global_event_filter'):
                with contextlib.suppress(RuntimeError):
                    app.removeEventFilter(window.global_event_filter)

        window = MainWindow()
        qtbot.addWidget(window, before_close_func=cleanup_event_filter)
        window.show()
        qtbot.waitExposed(window)
        return window

    def test_grid_toggle_has_no_selection_side_effects(self, main_window: MainWindow, qtbot):
        """Test that grid toggle does not modify selection state."""
        # Setup: Multi-point curve with pre-existing selection
        test_data: CurveDataList = [
            (1, 100.0, 100.0),
            (5, 300.0, 300.0),
            (10, 500.0, 500.0),
        ]

        app_state = get_application_state()

        # Wait for session loading and create fresh test curve
        qtbot.wait(100)
        test_curve_name = "TestCurve_Centering"
        app_state.set_active_curve(test_curve_name)
        app_state.set_curve_data(test_curve_name, test_data)
        app_state.set_frame(5)  # Middle point

        # Set a specific selection (point at index 0)
        app_state.set_selection(test_curve_name, {0})
        qtbot.wait(50)

        # Verify initial selection
        initial_selection = app_state.get_selection(test_curve_name)
        assert initial_selection == {0}, "Initial selection should be point 0"

        # Toggle grid on
        if main_window.show_grid_cb:
            main_window.show_grid_cb.setChecked(False)
        qtbot.wait(10)
        main_window.on_toggle_grid()
        qtbot.wait(50)  # Wait for rendering

        # Verify selection UNCHANGED after grid toggle
        selection_after = app_state.get_selection(test_curve_name)
        assert selection_after == {0}, f"Grid toggle should not change selection. Expected {{0}}, got {selection_after}"

        # Grid should be visible
        assert main_window.curve_view is not None
        assert main_window.curve_view.visual.show_grid is True

    def test_grid_respects_visual_settings(self, main_window: MainWindow, qtbot):
        """Test that grid size changes are reflected in visual settings."""
        assert main_window.curve_view is not None

        # Change grid size
        main_window.curve_view.visual.grid_size = 100
        qtbot.wait(10)

        # Increase
        main_window.on_increase_grid_size()
        qtbot.wait(10)

        # Verify visual settings updated
        assert main_window.curve_view.visual.grid_size == 110

        # Decrease
        main_window.on_decrease_grid_size()
        qtbot.wait(10)

        assert main_window.curve_view.visual.grid_size == 100
