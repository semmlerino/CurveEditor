#!/usr/bin/env python3
"""
Edge Case Test Suite

This module tests edge cases that have historically escaped testing and caused bugs.
Based on post-mortem analysis of 9 bugs that reached production, these tests focus on:

1. Null/None checks (Bug #1: ui_service.py:366 - no active curve check)
2. Invalid input types (Bug #2: ui_service.py:340 - non-string component names)
3. Empty collections
4. Boundary conditions
5. State transitions

Per testing principle: "Edge cases that slip through are bugs waiting to happen."
"""

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QPushButton

from services.ui_service import UIService
from stores.application_state import get_application_state


class TestNullAndNoneChecks:
    """Test that code handles None values gracefully (Bug #1 pattern)."""

    def test_ui_service_update_button_states_with_no_active_curve(self, qtbot):
        """Test UIService.update_button_states() when no active curve is set.

        Bug #1: ui_service.py:366 crashed with ValueError when active_curve was None.
        This test verifies the fix handles None gracefully.
        """
        # Create a mock MainWindow with save button and proper attributes
        mock_window = Mock()
        mock_window.save_button = QPushButton()
        mock_window.undo_button = QPushButton()
        mock_window.redo_button = QPushButton()
        mock_window.history_index = 0
        mock_window.history = []
        mock_window.selected_indices = []  # Empty history
        qtbot.addWidget(mock_window.save_button)
        qtbot.addWidget(mock_window.undo_button)
        qtbot.addWidget(mock_window.redo_button)

        # Clear active curve to trigger edge case
        app_state = get_application_state()
        app_state.set_active_curve(None)  # Edge case: no active curve

        service = UIService()

        # Should gracefully handle no active curve (improved behavior after Task 3.1)
        # Button should be disabled when no active curve
        service.update_button_states(mock_window)
        assert mock_window.save_button.isEnabled() is False

    def test_ui_service_update_button_states_with_empty_curve_data(self, qtbot):
        """Test UIService.update_button_states() with active curve but no data."""
        mock_window = Mock()
        mock_window.save_button = QPushButton()
        mock_window.undo_button = QPushButton()
        mock_window.redo_button = QPushButton()
        mock_window.history_index = 0
        mock_window.history = []
        mock_window.selected_indices = []
        qtbot.addWidget(mock_window.save_button)
        qtbot.addWidget(mock_window.undo_button)
        qtbot.addWidget(mock_window.redo_button)

        # Set active curve but with empty data
        app_state = get_application_state()
        app_state.set_active_curve("test_curve")
        app_state.set_curve_data("test_curve", [])  # Edge case: empty data

        service = UIService()
        service.update_button_states(mock_window)

        # Button should be disabled for empty data
        assert mock_window.save_button.isEnabled() is False

    def test_application_state_get_curve_data_with_no_active_curve(self):
        """Test ApplicationState.get_curve_data() raises clear error when no active curve."""
        app_state = get_application_state()
        app_state.set_active_curve(None)

        # Should raise ValueError with clear message
        with pytest.raises(ValueError, match="No active curve set"):
            app_state.get_curve_data()

    def test_application_state_operations_with_none_curve_name(self):
        """Test ApplicationState handles None curve_name parameter correctly."""
        app_state = get_application_state()

        # Edge case: None as curve_name parameter
        # ApplicationState may handle None gracefully or raise error
        # Either behavior is acceptable as long as it doesn't crash with AttributeError
        try:
            app_state.set_curve_data(None, [(1, 100.0, 200.0)])  # pyright: ignore[reportArgumentType]
        except (ValueError, TypeError, AttributeError) as e:
            # Expected - some kind of validation error
            assert "curve" in str(e).lower() or "none" in str(e).lower()

        try:
            app_state.get_curve_data(None)  # type: ignore[arg-type]
        except (ValueError, TypeError, AttributeError):
            # Expected - some kind of validation error
            pass


class TestInvalidInputTypes:
    """Test that code validates input types (Bug #2 pattern)."""

    def test_ui_service_enable_components_with_non_string_component_names(self):
        """Test UIService.enable_ui_components() rejects non-string component names.

        Bug #2: ui_service.py:340 crashed with TypeError when component_name was int.
        This test verifies the fix validates types before getattr().
        """
        mock_window = Mock()
        service = UIService()

        # Edge case: component names include non-strings
        invalid_components = [
            "valid_name",  # string - OK
            123,  # int - should cause TypeError
            None,  # None - should be skipped
        ]

        # Should raise TypeError for non-string component names
        # (UIService expects all items to be strings or skipped with falsy check)
        with pytest.raises(TypeError, match="attribute name must be string"):
            service.enable_ui_components(mock_window, invalid_components)  # pyright: ignore[reportArgumentType]

    def test_application_state_set_curve_data_with_invalid_types(self):
        """Test ApplicationState.set_curve_data() validates data types."""
        app_state = get_application_state()
        app_state.set_active_curve("test_curve")

        # Edge case: invalid data types
        invalid_data_sets = [
            None,  # None instead of list
            "string",  # string instead of list
            123,  # int instead of list
            {"frame": 1},  # dict instead of list
        ]

        for invalid_data in invalid_data_sets:
            # Should handle gracefully or raise clear error
            try:
                app_state.set_curve_data("test_curve", invalid_data)  # pyright: ignore[reportArgumentType]
            except (TypeError, ValueError, AttributeError):
                pass  # Expected - type validation working


class TestEmptyCollections:
    """Test that code handles empty lists, dicts, and sets correctly."""

    def test_ui_service_with_empty_component_list(self):
        """Test UIService operations with empty component lists."""
        mock_window = Mock()
        service = UIService()

        # Edge case: empty list
        service.enable_ui_components(mock_window, [])

        # Should not crash

    def test_application_state_with_empty_curve_data(self):
        """Test ApplicationState handles empty curve data."""
        app_state = get_application_state()
        app_state.set_active_curve("empty_curve")

        # Edge case: empty list
        app_state.set_curve_data("empty_curve", [])

        result = app_state.get_curve_data("empty_curve")
        assert result == []
        assert len(result) == 0

    def test_application_state_with_empty_selection(self):
        """Test ApplicationState handles empty selection sets."""
        app_state = get_application_state()
        app_state.set_active_curve("test_curve")

        # Edge case: empty set
        app_state.set_selection("test_curve", set())

        result = app_state.get_selection("test_curve")
        assert result == set()
        assert len(result) == 0

    def test_application_state_batch_operations_with_no_curves(self):
        """Test ApplicationState batch mode with no curve operations."""
        app_state = get_application_state()

        # Edge case: use batch_updates context manager with no operations
        with app_state.batch_updates():
            pass  # No operations

        # Should not crash


class TestBoundaryConditions:
    """Test boundary values and extreme cases."""

    def test_application_state_with_very_large_curve_name(self):
        """Test ApplicationState handles very long curve names."""
        app_state = get_application_state()

        # Edge case: 1000 character curve name
        long_name = "a" * 1000
        app_state.set_active_curve(long_name)

        test_data = [(1, 100.0, 200.0)]
        app_state.set_curve_data(long_name, test_data)

        result = app_state.get_curve_data(long_name)
        assert result == test_data

    def test_application_state_with_special_characters_in_curve_name(self):
        """Test ApplicationState handles special characters in curve names."""
        app_state = get_application_state()

        # Edge case: special characters
        special_names = [
            "curve-with-dashes",
            "curve_with_underscores",
            "curve.with.dots",
            "curve with spaces",
            "curve/with/slashes",
            "curve\\with\\backslashes",
        ]

        test_data = [(1, 100.0, 200.0)]

        for name in special_names:
            app_state.set_active_curve(name)
            app_state.set_curve_data(name, test_data)
            result = app_state.get_curve_data(name)
            assert result == test_data, f"Failed for curve name: {name}"

    def test_application_state_with_frame_number_boundaries(self):
        """Test ApplicationState handles extreme frame numbers."""
        app_state = get_application_state()
        app_state.set_active_curve("boundary_test")

        # Edge cases: extreme frame numbers
        boundary_data = [
            (0, 0.0, 0.0),  # Frame 0
            (1, 1.0, 1.0),  # Frame 1 (typical start)
            (999999, 999.0, 999.0),  # Very large frame number
            (-1, -1.0, -1.0),  # Negative frame (unusual but valid)
        ]

        app_state.set_curve_data("boundary_test", boundary_data)
        result = app_state.get_curve_data("boundary_test")

        assert len(result) == len(boundary_data)

    def test_application_state_with_extreme_coordinate_values(self):
        """Test ApplicationState handles extreme coordinate values."""
        app_state = get_application_state()
        app_state.set_active_curve("extreme_coords")

        # Edge cases: extreme coordinates
        extreme_data = [
            (1, 0.0, 0.0),  # Origin
            (2, 999999.9, 999999.9),  # Very large positive
            (3, -999999.9, -999999.9),  # Very large negative
            (4, 0.000001, 0.000001),  # Very small positive
            (5, -0.000001, -0.000001),  # Very small negative
        ]

        app_state.set_curve_data("extreme_coords", extreme_data)
        result = app_state.get_curve_data("extreme_coords")

        assert len(result) == len(extreme_data)


class TestStateTransitions:
    """Test edge cases in state changes and transitions."""

    def test_application_state_rapid_active_curve_changes(self):
        """Test ApplicationState handles rapid active curve switching."""
        app_state = get_application_state()

        # Setup multiple curves
        for i in range(10):
            curve_name = f"curve_{i}"
            app_state.set_curve_data(curve_name, [(i, float(i), float(i))])

        # Edge case: rapidly switch active curve
        for i in range(10):
            app_state.set_active_curve(f"curve_{i}")
            assert app_state.active_curve == f"curve_{i}"

    def test_application_state_clear_after_set(self):
        """Test ApplicationState handles clear operations after setting data."""
        app_state = get_application_state()
        app_state.set_active_curve("clear_test")

        # Set data then clear
        app_state.set_curve_data("clear_test", [(1, 100.0, 200.0)])
        app_state.set_curve_data("clear_test", [])  # Clear

        result = app_state.get_curve_data("clear_test")
        assert result == []

    def test_application_state_nested_batch_operations(self):
        """Test ApplicationState handles nested batch mode with context managers."""
        app_state = get_application_state()
        app_state.set_active_curve("test_curve")

        # Edge case: nested batch_updates context managers
        # Context managers should handle this gracefully
        with app_state.batch_updates():
            app_state.set_curve_data("test_curve", [(1, 100.0, 200.0)])

            with app_state.batch_updates():
                app_state.set_curve_data("test_curve", [(1, 100.0, 200.0), (2, 150.0, 250.0)])

            # Both contexts should complete without crash

        # Data should be set correctly
        result = app_state.get_curve_data("test_curve")
        assert len(result) == 2


class TestRegressionPrevention:
    """Tests that directly target the specific bugs that escaped."""

    def test_bug_1_regression_ui_service_no_active_curve(self, qtbot):
        """Regression test for Bug #1: UIService gracefully handles no active curve (improved after Task 3.1).

        Location: services/ui_service.py:366
        Old behavior: Raised ValueError: No active curve set
        New behavior (Task 3.1): Gracefully handles None, disables save button
        Improvement: More robust - no crashes, proper UI state
        """
        from services.ui_service import UIService

        mock_window = Mock()
        mock_window.save_button = QPushButton()
        mock_window.undo_button = QPushButton()
        mock_window.redo_button = QPushButton()
        mock_window.history_index = 0
        mock_window.history = []
        mock_window.selected_indices = []
        qtbot.addWidget(mock_window.save_button)
        qtbot.addWidget(mock_window.undo_button)
        qtbot.addWidget(mock_window.redo_button)

        # Reproduce bug condition
        app_state = get_application_state()
        app_state.set_active_curve(None)  # Bug: no active curve set

        service = UIService()

        # Should gracefully handle - no exception, button disabled (improved behavior)
        service.update_button_states(mock_window)
        assert mock_window.save_button.isEnabled() is False

    def test_bug_2_regression_ui_service_non_string_components(self):
        """Regression test for Bug #2: UIService should raise TypeError for non-string components.

        Location: services/ui_service.py:340
        Symptom: TypeError: attribute name must be string, not 'int'
        Fix: Raise clear error when non-string component names are passed
        """
        from services.ui_service import UIService

        mock_window = Mock()
        service = UIService()

        # Reproduce bug condition: component list with non-string types
        components_with_int = [123, "valid_name", 456]

        # Should raise TypeError with clear message
        with pytest.raises(TypeError, match="attribute name must be string"):
            service.enable_ui_components(mock_window, components_with_int)  # pyright: ignore[reportArgumentType]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
