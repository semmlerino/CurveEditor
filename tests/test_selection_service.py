"""
Tests for SelectionService from Sprint 8 refactoring.

This test module provides coverage for the previously untested SelectionService
that was extracted during Sprint 8's service decomposition.
"""

import unittest
from unittest.mock import Mock

from services.selection_service import SelectionService


class TestSelectionService(unittest.TestCase):
    """Test suite for SelectionService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = SelectionService()

        # Create a mock view with required attributes
        self.mock_view = Mock()
        self.mock_view.points = [
            (1, 10.0, 20.0),
            (2, 30.0, 40.0),
            (3, 50.0, 60.0),
            (4, 70.0, 80.0),
            (5, 90.0, 100.0)
        ]
        self.mock_view.selected_points = set()
        self.mock_view.update = Mock()
        self.mock_view.transform = Mock()
        self.mock_view.transform.device_to_curve = Mock(return_value=(0, 0))

    def test_initialization(self):
        """Test service initialization."""
        service = SelectionService()
        self.assertIsNotNone(service)
        self.assertIsInstance(service._view_selections, dict)

    def test_select_point_by_index(self):
        """Test selecting a point by index."""
        # Select first point
        result = self.service.select_point_by_index(self.mock_view, 0)
        self.assertTrue(result)
        self.assertEqual(self.mock_view.selected_points, {0})

        # Select another point (replace selection)
        result = self.service.select_point_by_index(self.mock_view, 2)
        self.assertTrue(result)
        self.assertEqual(self.mock_view.selected_points, {2})

    def test_select_point_by_index_add_to_selection(self):
        """Test adding points to selection."""
        # Select first point
        self.service.select_point_by_index(self.mock_view, 0)

        # Add second point to selection
        result = self.service.select_point_by_index(self.mock_view, 2, add_to_selection=True)
        self.assertTrue(result)
        self.assertEqual(self.mock_view.selected_points, {0, 2})

        # Add third point
        result = self.service.select_point_by_index(self.mock_view, 4, add_to_selection=True)
        self.assertTrue(result)
        self.assertEqual(self.mock_view.selected_points, {0, 2, 4})

    def test_select_point_invalid_index(self):
        """Test selecting with invalid index."""
        # Negative index
        result = self.service.select_point_by_index(self.mock_view, -1)
        self.assertFalse(result)

        # Index out of range
        result = self.service.select_point_by_index(self.mock_view, 10)
        self.assertFalse(result)

    def test_toggle_selection(self):
        """Test toggling selection when adding to selection."""
        # Select a point
        self.service.select_point_by_index(self.mock_view, 1)
        self.assertEqual(self.mock_view.selected_points, {1})

        # Toggle it off by selecting again with add_to_selection
        result = self.service.select_point_by_index(self.mock_view, 1, add_to_selection=True)
        self.assertTrue(result)
        self.assertEqual(self.mock_view.selected_points, set())

        # Toggle it back on
        result = self.service.select_point_by_index(self.mock_view, 1, add_to_selection=True)
        self.assertTrue(result)
        self.assertEqual(self.mock_view.selected_points, {1})

    def test_clear_selection(self):
        """Test clearing selection."""
        # Select multiple points
        self.mock_view.selected_points = {0, 1, 2}

        # Clear selection
        self.service.clear_selection(self.mock_view)
        self.assertEqual(self.mock_view.selected_points, set())
        self.mock_view.update.assert_called_once()

    def test_select_all(self):
        """Test selecting all points."""
        self.service.select_all(self.mock_view)
        self.assertEqual(self.mock_view.selected_points, {0, 1, 2, 3, 4})
        self.mock_view.update.assert_called_once()

    def test_get_selected_indices(self):
        """Test getting selected indices."""
        self.mock_view.selected_points = {1, 3, 4}

        indices = self.service.get_selected_indices(self.mock_view)
        self.assertEqual(indices, [1, 3, 4])

    def test_get_selected_indices_empty(self):
        """Test getting indices when nothing selected."""
        indices = self.service.get_selected_indices(self.mock_view)
        self.assertEqual(indices, [])

    def test_is_point_selected(self):
        """Test checking if point is selected."""
        self.mock_view.selected_points = {1, 3}

        self.assertFalse(self.service.is_point_selected(self.mock_view, 0))
        self.assertTrue(self.service.is_point_selected(self.mock_view, 1))
        self.assertFalse(self.service.is_point_selected(self.mock_view, 2))
        self.assertTrue(self.service.is_point_selected(self.mock_view, 3))

    def test_get_selection_count(self):
        """Test getting selection count."""
        self.assertEqual(self.service.get_selection_count(self.mock_view), 0)

        self.mock_view.selected_points = {1, 2, 3}
        self.assertEqual(self.service.get_selection_count(self.mock_view), 3)

    def test_invert_selection(self):
        """Test inverting selection."""
        self.mock_view.selected_points = {0, 2, 4}

        self.service.invert_selection(self.mock_view)
        self.assertEqual(self.mock_view.selected_points, {1, 3})
        self.mock_view.update.assert_called_once()

    def test_select_range(self):
        """Test selecting a range of points."""
        self.service.select_range(self.mock_view, 1, 3)
        self.assertEqual(self.mock_view.selected_points, {1, 2, 3})
        self.mock_view.update.assert_called_once()

    def test_select_range_invalid(self):
        """Test selecting invalid range."""
        # Start > end
        self.service.select_range(self.mock_view, 3, 1)
        self.assertEqual(self.mock_view.selected_points, set())

        # Out of bounds
        self.service.select_range(self.mock_view, -1, 10)
        self.assertEqual(self.mock_view.selected_points, set())

    def test_view_without_points(self):
        """Test operations on view without points attribute."""
        bad_view = Mock(spec=[])  # No points attribute

        result = self.service.select_point_by_index(bad_view, 0)
        self.assertFalse(result)

        self.service.clear_selection(bad_view)  # Should not crash
        self.service.select_all(bad_view)  # Should not crash

        indices = self.service.get_selected_indices(bad_view)
        self.assertEqual(indices, [])

    def test_view_without_selected_points(self):
        """Test operations on view without selected_points attribute."""
        bad_view = Mock()
        bad_view.points = [(1, 10.0, 20.0)]
        # No selected_points attribute

        result = self.service.select_point_by_index(bad_view, 0)
        self.assertFalse(result)  # Should fail gracefully

    def test_multiple_views(self):
        """Test managing selections for multiple views."""
        view1 = Mock()
        view1.points = [(1, 10.0, 20.0), (2, 30.0, 40.0)]
        view1.selected_points = set()
        view1.update = Mock()

        view2 = Mock()
        view2.points = [(1, 50.0, 60.0), (2, 70.0, 80.0)]
        view2.selected_points = set()
        view2.update = Mock()

        # Select in view1
        self.service.select_point_by_index(view1, 0)
        self.assertEqual(view1.selected_points, {0})
        self.assertEqual(view2.selected_points, set())

        # Select in view2
        self.service.select_point_by_index(view2, 1)
        self.assertEqual(view1.selected_points, {0})
        self.assertEqual(view2.selected_points, {1})

        # Clear view1
        self.service.clear_selection(view1)
        self.assertEqual(view1.selected_points, set())
        self.assertEqual(view2.selected_points, {1})


if __name__ == '__main__':
    unittest.main()
