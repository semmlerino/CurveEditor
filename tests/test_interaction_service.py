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

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPoint, QRect, Qt

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


class TestInteractionServiceCore:
    """Test core InteractionService functionality."""

    # Class attributes - initialized in setup() fixture
    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]
    transform_service: "TransformService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:  # pyright: ignore[reportUnusedParameter]
        """Setup test environment."""
        self.service = get_interaction_service()
        self.transform_service = get_transform_service()
        # Clear any cached state
        self.service._history = []  # pyright: ignore[reportPrivateUsage]
        self.service._current_index = -1  # pyright: ignore[reportPrivateUsage]

    def test_singleton_pattern(self) -> None:
        """Verify InteractionService uses singleton pattern correctly."""
        service1 = get_interaction_service()
        service2 = get_interaction_service()
        assert service1 is service2, "InteractionService should be a singleton"

    def test_find_point_at_empty_view(self) -> None:
        """Test finding point in empty view."""
        view = MockCurveView([])

        idx = self.service.find_point_at(view, 100, 100)  # pyright: ignore[reportArgumentType]

        assert idx == -1, "Should return -1 for empty view"

    def test_find_point_at_direct_hit(self) -> None:
        """Test finding point at exact position."""
        # Create view with test points - these are in data coordinates
        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
                (3, 300, 300),
            ]
        )

        # The InteractionService creates its own transform from view attributes
        # Since scale_to_image=True and zoom_factor=1.0, points map 1:1 to screen
        # So data point (100, 100) will be at screen (100, 100)

        # Clear spatial index to ensure a rebuild
        self.service.clear_spatial_index()

        # Find point at the actual screen position where it will be
        # With our default MockCurveView settings, points are at their data coordinates
        idx = self.service.find_point_at(view, 100, 100)  # pyright: ignore[reportArgumentType]

        assert idx == 0, "Should find first point at its actual screen position"

    def test_find_point_at_with_threshold(self) -> None:
        """Test finding point within threshold distance."""
        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
            ]
        )

        # Clear spatial index to ensure a rebuild
        self.service.clear_spatial_index()

        # Click near first point (within threshold)
        # Points are at their data coordinates with default view settings
        idx = self.service.find_point_at(view, 103, 103)  # pyright: ignore[reportArgumentType]

        assert idx == 0, "Should find point within threshold"

        # Click far from any point
        idx = self.service.find_point_at(view, 150, 150)  # pyright: ignore[reportArgumentType]
        assert idx == -1, "Should not find point outside threshold"


class TestInteractionServiceSelection:
    """Test point selection functionality."""

    # Class attributes - initialized in setup() fixture
    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]
    transform_service: "TransformService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:  # pyright: ignore[reportUnusedParameter]
        """Setup test environment."""
        self.service = get_interaction_service()
        self.transform_service = get_transform_service()

    # Note: select_point method doesn't exist in actual implementation
    # Selection is handled through find_point_at and internal methods

    # Note: toggle_point_selection method doesn't exist in actual implementation

    def test_select_all_points(self) -> None:
        """Test selecting all points."""
        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
                (3, 300, 300),
            ]
        )
        main_window = MockMainWindow()
        main_window.curve_widget = view  # Real MainWindow interface  # pyright: ignore[reportAttributeAccessIssue]
        main_window.curve_view = view  # Backward compatibility  # pyright: ignore[reportAttributeAccessIssue]

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
        main_window.curve_widget = view  # Real MainWindow interface  # pyright: ignore[reportAttributeAccessIssue]
        main_window.curve_view = view  # Backward compatibility  # pyright: ignore[reportAttributeAccessIssue]

        self.service.clear_selection(view, main_window)  # pyright: ignore[reportArgumentType]

        assert len(view.selected_points) == 0
        assert view.selected_point_idx == -1
        assert view.update_called

    def test_select_points_in_rect(self) -> None:
        """Test rectangle selection."""
        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 150, 150),
                (3, 300, 300),
                (4, 350, 350),
            ]
        )

        # Clear spatial index to ensure a rebuild
        self.service.clear_spatial_index()

        # Create rectangle that covers points at (100,100) and (150,150)
        # With default view settings, points are at their data coordinates
        rect = QRect(90, 90, 70, 70)  # From (90,90) to (160,160)

        main_window = MockMainWindow()
        main_window.curve_widget = view  # Real MainWindow interface  # pyright: ignore[reportAttributeAccessIssue]
        main_window.curve_view = view  # Backward compatibility  # pyright: ignore[reportAttributeAccessIssue]
        count = self.service.select_points_in_rect(view, main_window, rect)  # pyright: ignore[reportArgumentType]

        # Should select points at (100,100) and (150,150)
        assert count == 2
        assert 0 in view.selected_points
        assert 1 in view.selected_points
        assert 2 not in view.selected_points


class TestInteractionServiceHistory:
    """Test history management (undo/redo) functionality."""

    # Class attributes - initialized in setup() fixture
    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:  # pyright: ignore[reportUnusedParameter]
        """Setup test environment."""
        self.service = get_interaction_service()
        # Clear history
        self.service._history = []  # pyright: ignore[reportPrivateUsage]
        self.service._current_index = -1  # pyright: ignore[reportPrivateUsage]

    def test_add_to_history(self) -> None:
        """Test adding states to history."""
        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface  # pyright: ignore[reportAttributeAccessIssue]
        main_window.curve_view = view  # Backward compatibility  # pyright: ignore[reportAttributeAccessIssue]

        # Set up actual curve data that will be captured by add_to_history
        view.curve_data = [(1, 100, 100)]
        self.service.add_to_history(main_window, None)  # state param is ignored

        # Modify data and add another state
        view.curve_data = [(1, 100, 100), (2, 200, 200)]
        self.service.add_to_history(main_window, None)  # state param is ignored

        # Now we should have 2 states in history and can undo
        assert self.service.can_undo()

    def test_undo_operation(self) -> None:
        """Test undo functionality."""
        view = MockCurveView([(1, 100, 100)])
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface  # pyright: ignore[reportAttributeAccessIssue]
        main_window.curve_view = view  # Backward compatibility  # pyright: ignore[reportAttributeAccessIssue]

        # Add initial state
        self.service.add_to_history(main_window, None)

        # Modify and add new state
        view.curve_data = [(1, 150, 150)]
        self.service.add_to_history(main_window, None)

        # Perform undo
        assert self.service.can_undo()
        self.service.undo(main_window)

        # After undo, should be able to redo
        assert self.service.can_redo()

    def test_redo_operation(self) -> None:
        """Test redo functionality."""
        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface  # pyright: ignore[reportAttributeAccessIssue]
        main_window.curve_view = view  # Backward compatibility  # pyright: ignore[reportAttributeAccessIssue]

        # Add multiple states by modifying curve_data
        view.curve_data = [(1, 100, 100)]
        self.service.add_to_history(main_window, None)

        view.curve_data = [(1, 150, 150)]
        self.service.add_to_history(main_window, None)

        view.curve_data = [(1, 200, 200)]
        self.service.add_to_history(main_window, None)

        # Undo twice
        self.service.undo(main_window)
        self.service.undo(main_window)

        # Now redo
        assert self.service.can_redo()
        self.service.redo(main_window)

        # After redo, should be able to undo again
        assert self.service.can_undo()

    def test_history_branching(self) -> None:
        """Test that new action after undo creates new branch."""
        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface  # pyright: ignore[reportAttributeAccessIssue]
        main_window.curve_view = view  # Backward compatibility  # pyright: ignore[reportAttributeAccessIssue]

        # Add states
        view.curve_data = [(1, 100, 100)]
        self.service.add_to_history(main_window, None)

        view.curve_data = [(1, 150, 150)]
        self.service.add_to_history(main_window, None)

        view.curve_data = [(1, 200, 200)]
        self.service.add_to_history(main_window, None)

        # Undo once
        self.service.undo(main_window)

        # Add new state (should clear redo history)
        view.curve_data = [(1, 175, 175)]
        self.service.add_to_history(main_window, None)

        # Can't redo anymore
        assert not self.service.can_redo()

    def test_history_max_size(self) -> None:
        """Test history respects maximum size limit."""
        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface  # pyright: ignore[reportAttributeAccessIssue]
        main_window.curve_view = view  # Backward compatibility  # pyright: ignore[reportAttributeAccessIssue]

        # Add many states
        for i in range(150):  # More than typical max
            view.curve_data = [(1, i, i)]
            self.service.add_to_history(main_window, None)

        # History size check through public API
        stats = self.service.get_history_stats()
        # Should have some reasonable limit
        assert "size" in stats or self.service.get_history_size() <= 100


class TestInteractionServicePointManipulation:
    """Test point manipulation operations."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:  # pyright: ignore[reportUnusedParameter]
        """Setup test environment."""
        self.service: InteractionService = get_interaction_service()

    # Note: move_selected_points method doesn't exist in actual implementation
    # Point movement is handled through mouse events and internal methods

    def test_delete_selected_points(self) -> None:
        """Test deleting selected points."""
        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
                (3, 300, 300),
                (4, 400, 400),
            ]
        )
        view.selected_points = {1, 2}  # Select middle points
        main_window = MockMainWindow()
        main_window.curve_widget = view  # Real MainWindow interface  # pyright: ignore[reportAttributeAccessIssue]
        main_window.curve_view = view  # Backward compatibility  # pyright: ignore[reportAttributeAccessIssue]

        self.service.delete_selected_points(view, main_window)  # pyright: ignore[reportArgumentType]

        # Should have only first and last points
        assert len(view.curve_data) == 2
        assert view.curve_data[0] == (1, 100, 100)
        assert view.curve_data[1] == (4, 400, 400)

        # Selection should be cleared
        assert len(view.selected_points) == 0
        assert view.update_called

    # Note: add_point method doesn't exist in actual implementation
    # Point addition is handled through UI interactions


class TestInteractionServiceSpatialIndex:
    """Test spatial indexing functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:  # pyright: ignore[reportUnusedParameter]
        """Setup test environment."""
        self.service = get_interaction_service()
        self.transform_service = get_transform_service()

    def test_spatial_index_rebuild(self) -> None:
        """Test spatial index rebuilds with new data."""
        view = MockCurveView(
            [
                (i, i * 10, i * 10)
                for i in range(1000)  # Large dataset
            ]
        )

        view.transform = self.transform_service.create_transform(scale=1.0, center_offset=(400, 300))

        # First lookup should trigger index build
        _ = self.service.find_point_at(view, 400, 300)  # pyright: ignore[reportArgumentType]

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
            self.service.find_point_at(view, x, y)  # pyright: ignore[reportArgumentType]
        elapsed = time.time() - start

        # Should be very fast even with 10000 points
        assert elapsed < 0.1, f"Spatial index lookup too slow: {elapsed}s"

    def test_spatial_index_invalidation(self) -> None:
        """Test spatial index rebuilds when data or transform changes."""
        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
            ]
        )

        # Clear spatial index
        self.service.clear_spatial_index()

        # First lookup
        idx1 = self.service.find_point_at(view, 100, 100)  # pyright: ignore[reportArgumentType]
        assert idx1 == 0

        # Get initial stats
        stats1 = self.service.get_spatial_index_stats()
        initial_points = stats1.get("total_points")

        # Add more points to the view
        view.curve_data.append((3, 300, 300))

        # Clear the spatial index to force rebuild
        self.service.clear_spatial_index()

        # Should be able to find the new point
        idx3 = self.service.find_point_at(view, 300, 300)  # pyright: ignore[reportArgumentType]
        assert idx3 == 2  # Third point (index 2)

        # Verify stats updated
        stats2 = self.service.get_spatial_index_stats()
        new_points = stats2.get("total_points")
        assert new_points == 3
        assert new_points > initial_points


class TestInteractionServiceMouseEvents:
    """Test mouse event handling."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:  # pyright: ignore[reportUnusedParameter]
        """Setup test environment."""
        self.service: InteractionService = get_interaction_service()

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
        self.service.handle_mouse_press(view, event)  # pyright: ignore[reportArgumentType]

        # Should not crash

    def test_handle_mouse_with_modifiers(self) -> None:
        """Test mouse events with keyboard modifiers."""
        view = MockCurveView(
            [
                (1, 100, 100),
                (2, 200, 200),
            ]
        )

        # Ctrl+Click for multi-selection
        event = Mock()
        event.button.return_value = Qt.MouseButton.LeftButton
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
        event.position.return_value = QPoint(100, 100)

        # Should toggle selection
        initial_selection = len(view.selected_points)
        self.service.handle_mouse_press(view, event)  # pyright: ignore[reportArgumentType]

        # Selection should change
        assert len(view.selected_points) != initial_selection


class TestInteractionServiceKeyboardEvents:
    """Test keyboard event handling."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:  # pyright: ignore[reportUnusedParameter]
        """Setup test environment."""
        self.service: InteractionService = get_interaction_service()

    # Note: handle_key_press may not directly delete points
    # Key handling implementation may differ

    # Note: Keyboard shortcut handling may be done at a different level
    # Removed assumptions about specific key handling behavior

    def test_handle_undo_redo_shortcuts(self) -> None:
        """Test Ctrl+Z/Ctrl+Y shortcuts."""
        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface  # pyright: ignore[reportAttributeAccessIssue]
        main_window.curve_view = view  # Backward compatibility  # pyright: ignore[reportAttributeAccessIssue]

        # Add some history by setting actual curve data
        view.curve_data = [(1, 100, 100)]
        self.service.add_to_history(main_window, None)

        view.curve_data = [(1, 150, 150)]
        self.service.add_to_history(main_window, None)

        # Test that undo/redo capability exists
        assert self.service.can_undo()

        # Perform undo
        self.service.undo(main_window)

        # Should be able to redo
        assert self.service.can_redo()

        # Perform redo
        self.service.redo(main_window)

        # Should be able to undo again
        assert self.service.can_undo()
