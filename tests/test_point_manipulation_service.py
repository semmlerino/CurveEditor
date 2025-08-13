"""
Tests for PointManipulationService from Sprint 8 refactoring.

This test module provides coverage for the previously untested PointManipulationService
that handles point modifications with undo/redo support.
"""

import unittest
from unittest.mock import Mock

from services.point_manipulation import PointChange, PointManipulationService


class TestPointManipulationService(unittest.TestCase):
    """Test suite for PointManipulationService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = PointManipulationService()

        # Create a mock view with points
        self.mock_view = Mock()
        self.mock_view.points = [
            (1, 10.0, 20.0),
            (2, 30.0, 40.0),
            (3, 50.0, 60.0),
            (4, 70.0, 80.0, "tracked"),  # Point with status
            (5, 90.0, 100.0),
        ]
        self.mock_view.selected_points = {1, 3}
        self.mock_view.update = Mock()

    def test_initialization(self):
        """Test service initialization."""
        service = PointManipulationService()
        self.assertIsNotNone(service)

    def test_update_point_position(self):
        """Test updating a point's position."""
        # Update point at index 1
        change = self.service.update_point_position(self.mock_view, 1, 35.0, 45.0)

        self.assertIsNotNone(change)
        self.assertEqual(change.index, 1)
        self.assertEqual(change.old_point, (2, 30.0, 40.0))
        self.assertEqual(change.new_point, (2, 35.0, 45.0))

        # Verify the point was updated in the view
        self.assertEqual(self.mock_view.points[1], (2, 35.0, 45.0))
        self.mock_view.update.assert_called_once()

    def test_update_point_position_with_status(self):
        """Test updating a point that has status information."""
        # Update point at index 3 which has status
        change = self.service.update_point_position(self.mock_view, 3, 75.0, 85.0)

        self.assertIsNotNone(change)
        self.assertEqual(change.old_point, (4, 70.0, 80.0, "tracked"))
        self.assertEqual(change.new_point, (4, 75.0, 85.0, "tracked"))

        # Verify status is preserved
        self.assertEqual(self.mock_view.points[3], (4, 75.0, 85.0, "tracked"))

    def test_update_point_invalid_index(self):
        """Test updating with invalid index."""
        # Negative index
        change = self.service.update_point_position(self.mock_view, -1, 0, 0)
        self.assertIsNone(change)

        # Index out of range
        change = self.service.update_point_position(self.mock_view, 10, 0, 0)
        self.assertIsNone(change)

        # View should not be updated
        self.mock_view.update.assert_not_called()

    def test_delete_point(self):
        """Test deleting a point."""
        original_length = len(self.mock_view.points)

        # Delete point at index 2
        deleted = self.service.delete_point(self.mock_view, 2)

        self.assertEqual(deleted, (3, 50.0, 60.0))
        self.assertEqual(len(self.mock_view.points), original_length - 1)

        # Verify the point was removed
        self.assertNotIn((3, 50.0, 60.0), self.mock_view.points)
        self.mock_view.update.assert_called_once()

    def test_delete_point_updates_selection(self):
        """Test that deleting a point updates selection indices."""
        # Point 3 is selected (index 3)
        self.mock_view.selected_points = {2, 3, 4}

        # Delete point at index 1
        self.service.delete_point(self.mock_view, 1)

        # Selection indices should be adjusted
        # Original indices 2,3,4 become 1,2,3 after deletion
        self.assertEqual(self.mock_view.selected_points, {1, 2, 3})

    def test_delete_selected_point(self):
        """Test deleting a selected point removes it from selection."""
        self.mock_view.selected_points = {1, 2, 3}

        # Delete the selected point at index 2
        self.service.delete_point(self.mock_view, 2)

        # Point 2 should be removed from selection, others adjusted
        self.assertEqual(self.mock_view.selected_points, {1, 2})

    def test_delete_point_invalid_index(self):
        """Test deleting with invalid index."""
        deleted = self.service.delete_point(self.mock_view, -1)
        self.assertIsNone(deleted)

        deleted = self.service.delete_point(self.mock_view, 100)
        self.assertIsNone(deleted)

        self.mock_view.update.assert_not_called()

    def test_add_point(self):
        """Test adding a new point."""
        original_length = len(self.mock_view.points)

        # Add a new point at frame 6
        result = self.service.add_point(self.mock_view, 6, 110.0, 120.0)

        self.assertTrue(result)
        self.assertEqual(len(self.mock_view.points), original_length + 1)

        # Find the new point
        new_point = next(p for p in self.mock_view.points if p[0] == 6)
        self.assertEqual(new_point, (6, 110.0, 120.0))
        self.mock_view.update.assert_called_once()

    def test_add_point_duplicate_frame(self):
        """Test adding a point at existing frame."""
        # Try to add at frame 2 which already exists
        result = self.service.add_point(self.mock_view, 2, 35.0, 45.0)

        self.assertFalse(result)
        # Length should not change
        self.assertEqual(len(self.mock_view.points), 5)
        self.mock_view.update.assert_not_called()

    def test_add_point_maintains_order(self):
        """Test that points remain sorted by frame after addition."""
        # Add point at frame 2.5 (between existing frames)
        self.mock_view.points = [(1, 10.0, 20.0), (3, 50.0, 60.0), (5, 90.0, 100.0)]

        self.service.add_point(self.mock_view, 2, 30.0, 40.0)

        # Points should be sorted by frame
        frames = [p[0] for p in self.mock_view.points]
        self.assertEqual(frames, [1, 2, 3, 5])

    def test_batch_update_points(self):
        """Test updating multiple points."""
        updates = {0: (15.0, 25.0), 2: (55.0, 65.0), 4: (95.0, 105.0)}

        changes = self.service.batch_update_points(self.mock_view, updates)

        self.assertEqual(len(changes), 3)

        # Verify all updates were applied
        self.assertEqual(self.mock_view.points[0][1:3], (15.0, 25.0))
        self.assertEqual(self.mock_view.points[2][1:3], (55.0, 65.0))
        self.assertEqual(self.mock_view.points[4][1:3], (95.0, 105.0))

        # Update should be called once
        self.mock_view.update.assert_called_once()

    def test_batch_update_with_invalid_indices(self):
        """Test batch update with some invalid indices."""
        updates = {
            0: (15.0, 25.0),  # Valid
            10: (200.0, 210.0),  # Invalid
            2: (55.0, 65.0),  # Valid
        }

        changes = self.service.batch_update_points(self.mock_view, updates)

        # Only valid updates should be in changes
        self.assertEqual(len(changes), 2)
        self.assertEqual(self.mock_view.points[0][1:3], (15.0, 25.0))
        self.assertEqual(self.mock_view.points[2][1:3], (55.0, 65.0))

    def test_delete_points_in_range(self):
        """Test deleting points within a coordinate range."""
        # Delete points with x between 30 and 80
        deleted = self.service.delete_points_in_range(self.mock_view, x_min=30.0, x_max=80.0)

        # Points at indices 1, 2, 3 should be deleted
        self.assertEqual(len(deleted), 3)
        self.assertEqual(len(self.mock_view.points), 2)

        # Remaining points should be at frames 1 and 5
        frames = [p[0] for p in self.mock_view.points]
        self.assertEqual(frames, [1, 5])

    def test_move_selected_points(self):
        """Test moving all selected points by a delta."""
        self.mock_view.selected_points = {0, 2, 4}

        # Move selected points by (5, 10)
        changes = self.service.move_selected_points(self.mock_view, 5.0, 10.0)

        self.assertEqual(len(changes), 3)

        # Check that selected points were moved
        self.assertEqual(self.mock_view.points[0][1:3], (15.0, 30.0))
        self.assertEqual(self.mock_view.points[2][1:3], (55.0, 70.0))
        self.assertEqual(self.mock_view.points[4][1:3], (95.0, 110.0))

        # Non-selected points should not change
        self.assertEqual(self.mock_view.points[1][1:3], (30.0, 40.0))
        self.assertEqual(self.mock_view.points[3][1:3], (70.0, 80.0))

    def test_undo_point_change(self):
        """Test undoing a point change."""
        # Make a change
        change = self.service.update_point_position(self.mock_view, 1, 35.0, 45.0)

        # Undo it
        self.service.undo_change(self.mock_view, change)

        # Point should be back to original
        self.assertEqual(self.mock_view.points[1], (2, 30.0, 40.0))

    def test_redo_point_change(self):
        """Test redoing a point change."""
        change = PointChange(index=1, old_point=(2, 30.0, 40.0), new_point=(2, 35.0, 45.0))

        # Redo the change
        self.service.redo_change(self.mock_view, change)

        # Point should have new values
        self.assertEqual(self.mock_view.points[1], (2, 35.0, 45.0))

    def test_view_without_points(self):
        """Test operations on view without points."""
        bad_view = Mock(spec=[])  # No points attribute

        change = self.service.update_point_position(bad_view, 0, 10, 20)
        self.assertIsNone(change)

        deleted = self.service.delete_point(bad_view, 0)
        self.assertIsNone(deleted)

        result = self.service.add_point(bad_view, 1, 10, 20)
        self.assertFalse(result)

    def test_empty_points_list(self):
        """Test operations on empty points list."""
        self.mock_view.points = []

        # Adding should work
        result = self.service.add_point(self.mock_view, 1, 10, 20)
        self.assertTrue(result)
        self.assertEqual(len(self.mock_view.points), 1)

        # Updating non-existent should fail
        change = self.service.update_point_position(self.mock_view, 1, 15, 25)
        self.assertIsNone(change)

        # Deleting non-existent should fail
        deleted = self.service.delete_point(self.mock_view, 0)
        self.assertIsNone(deleted)


if __name__ == "__main__":
    unittest.main()
