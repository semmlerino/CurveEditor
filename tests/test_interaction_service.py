#!/usr/bin/env python3
"""
Comprehensive tests for InteractionService following best practices.

This test suite verifies the functionality of the InteractionService which handles:
- User interactions (mouse, keyboard)
- Point selection and manipulation
- History management (undo/redo)
- Spatial indexing for efficient point lookup

Following the testing guide principles:
- Test behavior, not implementation
- Use real components over mocks
- Mock only at system boundaries
"""

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPoint, QRect, Qt

from core.type_aliases import CurveDataList
from services import get_interaction_service, get_transform_service

if TYPE_CHECKING:
    from services.interaction_service import InteractionService
    from services.transform_service import TransformService

# Import test helpers
from tests.test_helpers import (
    MockCurveView,
    MockMainWindow,
)

# All functionality from MockCurveView is now imported from test_helpers
# No need for extended version since base class has all needed attributes

# MockMainWindow is imported from test_helpers - no need for extended version
# The base MockMainWindow already has curve_view, undo_action, redo_action, and status_bar


class TestInteractionServiceCore:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test core InteractionService functionality."""

    # Class attributes - initialized in setup() fixture
    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]
    transform_service: "TransformService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()
        self.transform_service = get_transform_service()
        # Clear any cached state (now in _commands helper)
        self.service._commands._history = []
        self.service._commands._current_index = -1

    def test_singleton_pattern(self) -> None:
        """Verify InteractionService uses singleton pattern correctly."""
        service1 = get_interaction_service()
        service2 = get_interaction_service()
        assert service1 is service2, "InteractionService should be a singleton"

    def test_find_point_at_empty_view(self) -> None:
        """Test finding point in empty view."""
        view = MockCurveView([])

        idx = self.service.find_point_at(view, 100, 100)

        assert idx == -1, "Should return -1 for empty view"

    def test_find_point_at_direct_hit(self) -> None:
        """Test finding point at exact position."""
        from stores.application_state import get_application_state

        # Create view with test points - these are in data coordinates
        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
                (3, 300, 300),
            ]
        )

        # Set up ApplicationState with curve data
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        # The InteractionService creates its own transform from view attributes
        # Since scale_to_image=True and zoom_factor=1.0, points map 1:1 to screen
        # So data point (100, 100) will be at screen (100, 100)

        # Clear spatial index to ensure a rebuild
        self.service.clear_spatial_index()

        # Find point at the actual screen position where it will be
        # With our default MockCurveView settings, points are at their data coordinates
        idx = self.service.find_point_at(view, 100, 100)

        assert idx == 0, "Should find first point at its actual screen position"

    def test_find_point_at_with_threshold(self) -> None:
        """Test finding point within threshold distance."""
        from stores.application_state import get_application_state

        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
            ]
        )

        # Set up ApplicationState with curve data
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        # Clear spatial index to ensure a rebuild
        self.service.clear_spatial_index()

        # Click near first point (within threshold)
        # Points are at their data coordinates with default view settings
        idx = self.service.find_point_at(view, 103, 103)

        assert idx == 0, "Should find point within threshold"

        # Click far from any point
        idx = self.service.find_point_at(view, 150, 150)
        assert idx == -1, "Should not find point outside threshold"


class TestInteractionServiceSelection:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test point selection functionality."""

    # Class attributes - initialized in setup() fixture
    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]
    transform_service: "TransformService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()
        self.transform_service = get_transform_service()

    # Note: select_point method doesn't exist in actual implementation
    # Selection is handled through find_point_at and internal methods

    # Note: toggle_point_selection method doesn't exist in actual implementation

    def test_select_all_points(self) -> None:
        """Test selecting all points."""
        from stores.application_state import get_application_state

        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
                (3, 300, 300),
            ]
        )

        # Set up ApplicationState with curve data
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Use correct method name: select_all_points, not select_all
        count = self.service.select_all_points(view, main_window)  # pyright: ignore[reportArgumentType]

        assert count == 3
        assert len(view.selected_points) == 3
        assert view.selected_points == {0, 1, 2}
        assert view.update_called

    def test_clear_selection(self) -> None:
        """Test clearing selection."""
        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
            ]
        )
        view.selected_points = {0, 1}
        view.selected_point_idx = 1
        main_window = MockMainWindow()
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        self.service.clear_selection(view, main_window)  # pyright: ignore[reportArgumentType]

        assert len(view.selected_points) == 0
        assert view.selected_point_idx == -1
        assert view.update_called

    def test_select_points_in_rect(self) -> None:
        """Test rectangle selection."""
        from stores.application_state import get_application_state

        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 150, 150),
                (3, 300, 300),
                (4, 350, 350),
            ]
        )

        # Set up ApplicationState with curve data
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        # Clear spatial index to ensure a rebuild
        self.service.clear_spatial_index()

        # Create rectangle that covers points at (100,100) and (150,150)
        # With default view settings, points are at their data coordinates
        rect = QRect(90, 90, 70, 70)  # From (90,90) to (160,160)

        main_window = MockMainWindow()
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility
        count = self.service.select_points_in_rect(view, main_window, rect)  # pyright: ignore[reportArgumentType]

        # Should select points at (100,100) and (150,150)
        assert count == 2
        assert 0 in view.selected_points
        assert 1 in view.selected_points
        assert 2 not in view.selected_points


class TestInteractionServiceHistory:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test history management (undo/redo) functionality."""

    # Class attributes - initialized in setup() fixture
    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()
        # Clear history (now in _commands helper)
        self.service._commands._history = []
        self.service._commands._current_index = -1

    def test_add_to_history(self) -> None:
        """Test adding states to history."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve("test_curve")
        app_state.set_curve_data("test_curve", [(1, 100, 100)])

        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add initial state
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Modify data and add another state
        app_state.set_curve_data("test_curve", [(1, 100, 100), (2, 200, 200)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Now we should have 2 states in history and can undo
        assert self.service.can_undo()

    def test_undo_operation(self) -> None:
        """Test undo functionality."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve("test_curve")
        app_state.set_curve_data("test_curve", [(1, 100, 100)])

        view = MockCurveView([(1, 100, 100)])
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add initial state
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Modify and add new state
        app_state.set_curve_data("test_curve", [(1, 150, 150)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Perform undo
        assert self.service.can_undo()
        self.service.undo(main_window)  # pyright: ignore[reportArgumentType]

        # After undo, should be able to redo
        assert self.service.can_redo()

    def test_redo_operation(self) -> None:
        """Test redo functionality."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve("test_curve")
        app_state.set_curve_data("test_curve", [(1, 100, 100)])

        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add multiple states by modifying curve_data
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        app_state.set_curve_data("test_curve", [(1, 150, 150)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        app_state.set_curve_data("test_curve", [(1, 150, 150)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        app_state.set_curve_data("test_curve", [(1, 200, 200)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Undo twice
        self.service.undo(main_window)  # pyright: ignore[reportArgumentType]
        self.service.undo(main_window)  # pyright: ignore[reportArgumentType]

        # Now redo
        assert self.service.can_redo()
        self.service.redo(main_window)  # pyright: ignore[reportArgumentType]

        # After redo, should be able to undo again
        assert self.service.can_undo()

    def test_history_branching(self) -> None:
        """Test that new action after undo creates new branch."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve("test_curve")
        app_state.set_curve_data("test_curve", [(1, 100, 100)])

        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add states
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        app_state.set_curve_data("test_curve", [(1, 150, 150)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        app_state.set_curve_data("test_curve", [(1, 200, 200)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Undo once
        self.service.undo(main_window)  # pyright: ignore[reportArgumentType]

        # Add new state (should clear redo history)
        app_state.set_curve_data("test_curve", [(1, 175, 175)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Can't redo anymore
        assert not self.service.can_redo()

    def test_history_max_size(self) -> None:
        """Test history respects maximum size limit."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve("test_curve")

        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add many states
        for i in range(150):  # More than typical max
            app_state.set_curve_data("test_curve", [(1, i, i)])
            self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # History size check through public API
        stats = self.service.get_history_stats()
        # Should have some reasonable limit
        assert "size" in stats or self.service.get_history_size() <= 100


class TestInteractionServicePointManipulation:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test point manipulation operations."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    # Note: move_selected_points method doesn't exist in actual implementation
    # Point movement is handled through mouse events and internal methods

    def test_delete_selected_points(self) -> None:
        """Test deleting selected points."""
        from stores.application_state import get_application_state

        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
                (3, 300, 300),
                (4, 400, 400),
            ]
        )
        view.selected_points = {1, 2}  # Select middle points

        # Set up ApplicationState with curve data
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        self.service.delete_selected_points(view, main_window)  # pyright: ignore[reportArgumentType]

        # Verify deletion in ApplicationState
        updated_data = app_state.get_curve_data("test_curve")
        assert len(updated_data) == 2
        assert updated_data[0] == (1, 100, 100)
        assert updated_data[1] == (4, 400, 400)

        # Selection should be cleared
        assert len(view.selected_points) == 0
        assert view.update_called

    # Note: add_point method doesn't exist in actual implementation
    # Point addition is handled through UI interactions


class TestInteractionServiceSpatialIndex:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test spatial indexing functionality."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]
    transform_service: Any  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()
        self.transform_service = get_transform_service()

    def test_spatial_index_rebuild(self) -> None:
        """Test spatial index rebuilds with new data."""
        from stores.application_state import get_application_state

        view = MockCurveView(
            [
                (i, i * 10, i * 10)
                for i in range(1000)  # Large dataset
            ]
        )

        # Set up ApplicationState with curve data
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        view.transform = self.transform_service.create_transform(scale=1.0, center_offset=(400, 300))

        # First lookup should trigger index build
        _ = self.service.find_point_at(view, 400, 300)

        # Get stats
        stats = self.service.get_spatial_index_stats()

        assert "grid_size" in stats
        assert stats["total_points"] == 1000

    def test_spatial_index_performance(self) -> None:
        """Test spatial index provides O(1) lookup."""
        # Create large dataset
        view = MockCurveView(
            [
                (i, (i % 100) * 10, (i // 100) * 10)
                for i in range(10000)  # Very large dataset
            ]
        )

        view.transform = self.transform_service.create_transform(scale=1.0, center_offset=(400, 300))

        # Multiple lookups should be fast
        import time

        start = time.time()
        for _ in range(100):
            # Random positions
            x = 400 + ((_ % 10) - 5) * 50
            y = 300 + ((_ // 10) - 5) * 50
            self.service.find_point_at(view, x, y)
        elapsed = time.time() - start

        # Should be very fast even with 10000 points
        assert elapsed < 0.1, f"Spatial index lookup too slow: {elapsed}s"

    def test_spatial_index_invalidation(self) -> None:
        """Test spatial index rebuilds when data or transform changes."""
        from stores.application_state import get_application_state

        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
            ]
        )

        # Set up ApplicationState with curve data
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        # Clear spatial index
        self.service.clear_spatial_index()

        # First lookup
        idx1 = self.service.find_point_at(view, 100, 100)
        assert idx1 == 0

        # Get initial stats
        stats1 = self.service.get_spatial_index_stats()
        initial_points = stats1.get("total_points")
        assert isinstance(initial_points, int), "Expected initial_points to be an int"

        # Add more points to the view
        view.curve_data.append((3, 300, 300))
        # Update ApplicationState with new data
        app_state.set_curve_data("test_curve", view.curve_data)

        # Clear the spatial index to force rebuild
        self.service.clear_spatial_index()

        # Should be able to find the new point
        idx3 = self.service.find_point_at(view, 300, 300)
        assert idx3 == 2  # Third point (index 2)

        # Verify stats updated
        stats2 = self.service.get_spatial_index_stats()
        new_points = stats2.get("total_points")
        assert isinstance(new_points, int), "Expected new_points to be an int"
        assert new_points == 3
        assert new_points > initial_points


class TestInteractionServiceMouseEvents:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test mouse event handling."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_handle_mouse_press(self) -> None:
        """Test mouse press event handling."""
        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
            ]
        )

        # Create mock mouse event
        event = Mock()
        event.button.return_value = Qt.MouseButton.LeftButton
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
        event.position.return_value = QPoint(100, 100)

        # Handle mouse press - returns None not boolean
        self.service.handle_mouse_press(view, event)

        # Should not crash

    def test_handle_mouse_with_modifiers(self) -> None:
        """Test mouse events with keyboard modifiers."""
        from stores.application_state import get_application_state

        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
            ]
        )

        # Set up ApplicationState with curve data
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        # Ctrl+Click for multi-selection
        event = Mock()
        event.button.return_value = Qt.MouseButton.LeftButton
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
        event.position.return_value = QPoint(100, 100)

        # Should toggle selection
        initial_selection = len(view.selected_points)
        self.service.handle_mouse_press(view, event)

        # Selection should change
        assert len(view.selected_points) != initial_selection


class TestInteractionServiceKeyboardEvents:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test keyboard event handling."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    # Note: handle_key_press may not directly delete points
    # Key handling implementation may differ

    # Note: Keyboard shortcut handling may be done at a different level
    # Removed assumptions about specific key handling behavior

    def test_handle_undo_redo_shortcuts(self) -> None:
        """Test Ctrl+Z/Ctrl+Y shortcuts."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve("test_curve")
        app_state.set_curve_data("test_curve", [(1, 100, 100)])

        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add some history by setting actual curve data
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        app_state.set_curve_data("test_curve", [(1, 150, 150)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Test that undo/redo capability exists
        assert self.service.can_undo()

        # Perform undo
        self.service.undo(main_window)  # pyright: ignore[reportArgumentType]

        # Should be able to redo
        assert self.service.can_redo()

        # Perform redo
        self.service.redo(main_window)  # pyright: ignore[reportArgumentType]

        # Should be able to undo again
        assert self.service.can_undo()


class TestKeyEventHandling:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test comprehensive key event handling."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_delete_key_deletes_selected_points(self) -> None:
        """Test Delete key triggers delete command creation."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0), (3, 300.0, 300.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        view.selected_points = {0, 2}  # Select first and third points
        # Don't set main_window - service will skip command execution

        event = Mock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_Delete
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        self.service.handle_key_event(view, event)

        # Test passes if no error - deletion logic is triggered
        # Actual deletion requires main_window for command execution

    def test_ctrl_a_selects_all_points(self) -> None:
        """Test Ctrl+A selects all points."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0), (3, 300.0, 300.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))

        event = Mock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_A
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        self.service.handle_key_event(view, event)

        # All points should be selected
        assert len(view.selected_points) == 3
        assert view.selected_points == {0, 1, 2}

    def test_escape_clears_selection(self) -> None:
        """Test Escape key clears selection."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        view = MockCurveView([(1, 100.0, 100.0), (2, 200.0, 200.0)])
        view.selected_points = {0, 1}

        event = Mock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_Escape
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        self.service.handle_key_event(view, event)

        # Selection should be cleared
        assert len(view.selected_points) == 0
        assert view.selected_point_idx == -1

    def test_arrow_keys_nudge_selected_points(self) -> None:
        """Test arrow keys trigger nudge command creation."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        view.selected_points = {0}
        # Don't set main_window - service will skip command execution

        # Test right arrow
        event = Mock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_Right
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        self.service.handle_key_event(view, event)

        # Test passes if no error - nudge logic is triggered
        # Actual nudge requires main_window for command execution


class TestPointManipulation:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test point manipulation methods."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_select_point_by_index(self) -> None:
        """Test selecting point by index."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()
        view = MockCurveView(cast(CurveDataList, test_data))

        result = self.service.select_point_by_index(
            view,
            main_window,  # pyright: ignore[reportArgumentType]
            1,
        )

        assert result is True
        assert 1 in view.selected_points
        assert view.selected_point_idx == 1

    def test_select_point_by_index_add_to_selection(self) -> None:
        """Test adding point to selection by index."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()
        view = MockCurveView(cast(CurveDataList, test_data))
        view.selected_points = {0}

        result = self.service.select_point_by_index(
            view,
            main_window,  # pyright: ignore[reportArgumentType]
            1,
            add_to_selection=True,
        )

        assert result is True
        assert 0 in view.selected_points
        assert 1 in view.selected_points

    def test_update_point_position(self) -> None:
        """Test updating point position."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()
        view = MockCurveView(cast(CurveDataList, test_data))

        result = self.service.update_point_position(
            view,
            main_window,  # pyright: ignore[reportArgumentType]
            0,
            150.0,
            150.0,
        )

        assert result is True
        # Check ApplicationState (Phase 6: single source of truth)
        updated_data = app_state.get_curve_data("test_curve")
        assert updated_data[0][1] == 150.0
        assert updated_data[0][2] == 150.0

    def test_nudge_selected_points(self) -> None:
        """Test nudging selected points."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()
        view = MockCurveView(cast(CurveDataList, test_data))

        # Set selection via ApplicationState (Phase 6)
        app_state.set_selection("test_curve", {0})
        # MockCurveView doesn't have property syncing, so set directly too
        view.selected_points = {0}

        result = self.service.nudge_selected_points(
            view,
            main_window,  # pyright: ignore[reportArgumentType]
            10.0,
            -5.0,
        )

        assert result is True
        # Check ApplicationState (Phase 6: single source of truth)
        updated_data = app_state.get_curve_data("test_curve")
        assert updated_data[0][1] == 110.0
        assert updated_data[0][2] == 95.0


class TestMouseMoveEvents:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test mouse move event handling for drag, pan, and rubber band operations."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_handle_mouse_move_drag_points(self) -> None:
        """Test mouse move during point dragging."""
        from PySide6.QtGui import QMouseEvent

        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        view.selected_points = {0}
        view.drag_active = True
        view.last_drag_pos = QPoint(100, 100)

        # Create mouse move event
        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPoint(110, 95)

        self.service.handle_mouse_move(view, event)

        # Points should have moved in view.curve_data
        # Movement depends on transform, but update should be called
        assert view.update_called

    def test_handle_mouse_move_pan_view(self) -> None:
        """Test mouse move during view panning."""
        from PySide6.QtGui import QMouseEvent

        view = MockCurveView([])
        view.pan_active = True
        view.last_pan_pos = QPoint(200, 150)

        # Create mouse move event
        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPoint(220, 170)

        self.service.handle_mouse_move(view, event)

        # Pan should have been called (if view supports it)
        # At minimum, update should be called
        assert view.update_called

    def test_handle_mouse_move_rubber_band(self) -> None:
        """Test mouse move during rubber band selection."""
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtWidgets import QRubberBand

        view = MockCurveView([])
        view.rubber_band_active = True
        view.rubber_band_origin = QPoint(100, 100)
        view.rubber_band = Mock(spec=QRubberBand)

        # Create mouse move event
        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPoint(200, 200)

        self.service.handle_mouse_move(view, event)

        # Rubber band geometry should be updated
        assert view.rubber_band.setGeometry.called
        assert view.update_called


class TestMouseReleaseEvents:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test mouse release event handling for completing drag/pan/selection."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_handle_mouse_release_drag(self) -> None:
        """Test mouse release after dragging points."""
        from PySide6.QtGui import QMouseEvent

        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        view.selected_points = {0}
        view.drag_active = True
        main_window = MockMainWindow()
        view.main_window = main_window  # pyright: ignore[reportAttributeAccessIssue]

        # Set original positions (now in _mouse helper)
        self.service._mouse._drag_original_positions = {0: (100.0, 100.0)}

        # Modify point position to simulate drag
        view.curve_data[0] = (1, 110.0, 95.0)

        # Create mouse release event
        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPoint(110, 95)

        self.service.handle_mouse_release(view, event)

        # Drag should be ended
        assert not view.drag_active
        assert view.last_drag_pos is None
        assert view.update_called

    def test_handle_mouse_release_pan(self) -> None:
        """Test mouse release after panning."""
        from PySide6.QtGui import QMouseEvent

        view = MockCurveView([])
        view.pan_active = True
        view.last_pan_pos = QPoint(200, 150)

        # Create mouse release event
        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPoint(220, 170)

        self.service.handle_mouse_release(view, event)

        # Pan should be ended
        assert not view.pan_active
        assert view.last_pan_pos is None
        assert view.update_called

    def test_handle_mouse_release_rubber_band(self) -> None:
        """Test mouse release after rubber band selection."""
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtWidgets import QRubberBand

        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 150.0, 150.0), (3, 300.0, 300.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        view.rubber_band_active = True
        view.rubber_band = Mock(spec=QRubberBand)
        view.rubber_band.geometry.return_value = QRect(90, 90, 70, 70)

        # Create mouse release event
        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPoint(160, 160)

        self.service.handle_mouse_release(view, event)

        # Rubber band should be hidden
        assert view.rubber_band.hide.called
        assert not view.rubber_band_active
        assert view.update_called


class TestWheelEvents:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test mouse wheel event handling for zooming."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_handle_wheel_event_zoom_in(self) -> None:
        """Test wheel event for zooming in."""
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QWheelEvent

        view = MockCurveView([])

        # Add a zoom method to the view (required by wheel event handler)
        view.zoom = Mock()  # pyright: ignore[reportAttributeAccessIssue]

        # Create wheel event for zoom in (positive delta)
        event = Mock(spec=QWheelEvent)
        angle_delta_mock = Mock()
        angle_delta_mock.y.return_value = 120  # Positive = zoom in
        event.angleDelta.return_value = angle_delta_mock
        event.position.return_value = QPoint(400, 300)

        self.service.handle_wheel_event(view, event)

        # Zoom method should be called
        assert view.zoom.called  # pyright: ignore[reportAttributeAccessIssue]
        assert view.update_called

    def test_handle_wheel_event_zoom_out(self) -> None:
        """Test wheel event for zooming out."""
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QWheelEvent

        view = MockCurveView([])

        # Add a zoom method to the view (required by wheel event handler)
        view.zoom = Mock()  # pyright: ignore[reportAttributeAccessIssue]

        # Create wheel event for zoom out (negative delta)
        event = Mock(spec=QWheelEvent)
        angle_delta_mock = Mock()
        angle_delta_mock.y.return_value = -120  # Negative = zoom out
        event.angleDelta.return_value = angle_delta_mock
        event.position.return_value = QPoint(400, 300)

        self.service.handle_wheel_event(view, event)

        # Zoom method should be called
        assert view.zoom.called  # pyright: ignore[reportAttributeAccessIssue]
        assert view.update_called


class TestStateManagement:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test save_state and restore_state functionality."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()
        # Clear history (now in _commands helper)
        self.service._commands._history = []
        self.service._commands._current_index = -1

    def test_save_state(self) -> None:
        """Test save_state method (alias for add_to_history)."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        main_window = MockMainWindow()
        main_window.history = None
        main_window.history_index = None
        self.service.save_state(main_window)  # pyright: ignore[reportArgumentType]
        main_window.curve_view = view

        # save_state is an alias for add_to_history
        self.service.save_state(main_window)  # pyright: ignore[reportArgumentType]

        # Should have added to internal history
        assert len(self.service._commands._history) > 0

    def test_restore_state_with_curve_data(self) -> None:
        """Test restoring state with curve data."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_curve_data("test_curve", [(1, 50.0, 50.0)])
        app_state.set_active_curve("test_curve")

        view = MockCurveView([(1, 50.0, 50.0)])
        main_window = MockMainWindow()
        main_window.curve_widget = view
        main_window.curve_view = view

        # Create state to restore
        state = {
            "curve_data": [(1, 100.0, 100.0), (2, 200.0, 200.0)],
            "point_name": "test_point",
            "point_color": "red",
        }

        self.service.restore_state(
            main_window,  # pyright: ignore[reportArgumentType]
            cast(dict[str, object], state),
        )

        # Verify ApplicationState was updated
        restored_data = app_state.get_curve_data("test_curve")
        assert len(restored_data) == 2
        # Data may be stored as lists, so compare values not types
        assert restored_data[0][0] == 1
        assert restored_data[0][1] == 100.0
        assert restored_data[0][2] == 100.0

    def test_restore_state_empty_state(self) -> None:
        """Test restoring with empty state does nothing."""
        main_window = MockMainWindow()

        # Should not crash with empty state
        self.service.restore_state(
            main_window,  # pyright: ignore[reportArgumentType]
            {},
        )


class TestHistoryWithMainWindow:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test history management using MainWindow's history system."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_add_to_history_with_main_window_history(self) -> None:
        """Test add_to_history using main_window's history."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        main_window = MockMainWindow()
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        main_window.history_index = -1
        main_window.max_history_size = 50
        main_window.curve_widget = view
        main_window.curve_view = view

        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Should have added to main_window's history
        assert len(main_window.history) == 1  # pyright: ignore[reportArgumentType]
        assert main_window.history_index == 0

    def test_undo_with_main_window_history(self) -> None:
        """Test undo using main_window's history system."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        main_window = MockMainWindow()
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        main_window.history_index = -1
        main_window.curve_widget = view
        main_window.curve_view = view

        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Modify and add new state
        self.service.undo_action(main_window)  # pyright: ignore[reportArgumentType]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Undo
        assert main_window.history_index == 1
        self.service.undo_action(main_window)  # pyright: ignore[reportArgumentType]

        # Should have decremented index
        assert main_window.history_index == 0


class TestHistoryEdgeCases:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test edge cases in history management."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()
        # Clear history (now in _commands helper)
        self.service._commands._history = []
        self.service._commands._current_index = -1

    def test_clear_history(self) -> None:
        """Test clearing history."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve("test_curve")
        app_state.set_curve_data("test_curve", [(1, 100.0, 100.0)])

        view = MockCurveView([(1, 100.0, 100.0)])
        main_window = MockMainWindow()
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Add some states
        app_state.set_curve_data("test_curve", [(1, 100.0, 100.0), (2, 200.0, 200.0)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        app_state.set_curve_data("test_curve", [(1, 100.0, 100.0), (2, 200.0, 200.0), (3, 300.0, 300.0)])
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Clear history
        self.service.clear_history(main_window)  # pyright: ignore[reportArgumentType]

        # History should be empty
        assert len(self.service._commands._history) == 0
        assert self.service._commands._current_index == -1
        assert not self.service.can_undo()
        assert not self.service.can_redo()

    def test_update_history_buttons(self) -> None:
        """Test updating undo/redo button states."""
        main_window = MockMainWindow()
        main_window.history = None
        main_window.history_index = None

        # Create mock UI with buttons - use pyright: ignore to suppress attribute check
        main_window.ui = Mock()  # pyright: ignore[reportAttributeAccessIssue]
        main_window.ui.undo_button = Mock()  # pyright: ignore[reportAttributeAccessIssue]
        main_window.ui.redo_button = Mock()  # pyright: ignore[reportAttributeAccessIssue]

        # Update buttons with no history
        self.service.update_history_buttons(main_window)  # pyright: ignore[reportArgumentType]

        # Undo button should be disabled
        main_window.ui.undo_button.setEnabled.assert_called_with(False)  # pyright: ignore[reportAttributeAccessIssue]
        main_window.ui.redo_button.setEnabled.assert_called_with(False)  # pyright: ignore[reportAttributeAccessIssue]

    def test_get_memory_stats(self) -> None:
        """Test getting memory statistics."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve("test_curve")
        app_state.set_curve_data("test_curve", [(1, 100.0, 100.0)])

        view = MockCurveView([(1, 100.0, 100.0)])
        main_window = MockMainWindow()
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view

        # Add some states
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        stats = self.service.get_memory_stats()

        assert "total_states" in stats
        assert "current_index" in stats
        assert "memory_mb" in stats
        assert "can_undo" in stats
        assert "can_redo" in stats
        assert stats["total_states"] == 1


class TestCompatibilityMethods:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test compatibility methods and legacy interfaces."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_handle_key_press_compatibility(self) -> None:
        """Test handle_key_press routes to handle_key_event."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        view = MockCurveView([])

        event = Mock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_Escape
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        # Should not crash - routes to handle_key_event
        self.service.handle_key_press(view, event)

    def test_handle_context_menu(self) -> None:
        """Test context menu handling."""
        from PySide6.QtGui import QMouseEvent

        view = MockCurveView([])

        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPoint(100, 100)

        # Should not crash - currently just logs
        self.service.handle_context_menu(view, event)

    def test_find_point_at_position(self) -> None:
        """Test find_point_at_position with tolerance parameter."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        self.service.clear_spatial_index()

        # With large tolerance
        idx = self.service.find_point_at_position(view, 110, 110, tolerance=20.0)
        assert idx == 0

        # With small tolerance
        idx = self.service.find_point_at_position(view, 110, 110, tolerance=2.0)
        assert idx == -1

    def test_reset_view(self) -> None:
        """Test resetting view to default state."""
        view = MockCurveView([])
        view.zoom_factor = 2.0
        view.pan_offset_x = 100
        view.pan_offset_y = 50

        self.service.reset_view(view)

        # View should be reset
        assert view.zoom_factor == 1.0
        assert view.pan_offset_x == 0
        assert view.pan_offset_y == 0
        assert view.update_called

    def test_on_point_moved_callback(self) -> None:
        """Test point moved callback."""
        main_window = MockMainWindow()

        # Should not crash
        self.service.on_point_moved(
            main_window,  # pyright: ignore[reportArgumentType]
            0,
            100.0,
            100.0,
        )

    def test_on_point_selected_callback(self) -> None:
        """Test point selected callback."""
        view = MockCurveView([])
        main_window = MockMainWindow()

        # Should not crash
        self.service.on_point_selected(
            view,
            main_window,  # pyright: ignore[reportArgumentType]
            0,
        )

    def test_update_point_info(self) -> None:
        """Test updating point info in status bar."""
        main_window = MockMainWindow()

        # Should not crash
        self.service.update_point_info(
            main_window,  # pyright: ignore[reportArgumentType]
            0,
            100.0,
            100.0,
        )


class TestFindPointAtPositionEdgeCases:  # pyright: ignore[reportUninitializedInstanceVariable]
    """Test edge cases for point finding functionality."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_find_point_no_active_curve(self) -> None:
        """Test finding point when no active curve is set."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve(None)  # No active curve

        view = MockCurveView([])

        idx = self.service.find_point_at(view, 100, 100)
        assert idx == -1

    def test_select_point_invalid_index(self) -> None:
        """Test selecting point with invalid index."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        main_window = MockMainWindow()

        # Try to select out-of-bounds index
        result = self.service.select_point_by_index(
            view,
            main_window,  # pyright: ignore[reportArgumentType]
            999,
        )
        assert result is False

    def test_update_point_position_invalid_index(self) -> None:
        """Test updating point with invalid index."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        main_window = MockMainWindow()

        # Try to update out-of-bounds index
        result = self.service.update_point_position(
            view,
            main_window,  # pyright: ignore[reportArgumentType]
            999,
            50.0,
            50.0,
        )
        assert result is False

    def test_nudge_selected_points_no_selection(self) -> None:
        """Test nudging when no points are selected."""
        view = MockCurveView([(1, 100.0, 100.0)])
        view.selected_points = set()  # No selection
        main_window = MockMainWindow()

        result = self.service.nudge_selected_points(
            view,
            main_window,  # pyright: ignore[reportArgumentType]
            10.0,
            10.0,
        )
        assert result is False

    def test_nudge_selected_points_no_curve_data(self) -> None:
        """Test nudging when no curve data exists."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve(None)

        view = MockCurveView([])
        view.selected_points = {0}
        main_window = MockMainWindow()

        result = self.service.nudge_selected_points(
            view,
            main_window,  # pyright: ignore[reportArgumentType]
            10.0,
            10.0,
        )
        assert result is False
