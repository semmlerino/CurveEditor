"""
Tests for HistoryService from Sprint 8 refactoring.

This test module provides coverage for the previously untested HistoryService
that manages undo/redo operations with memory-efficient compression.
"""

import unittest

from services.history_service import HistoryService, HistoryStats


class TestHistoryService(unittest.TestCase):
    """Test suite for Sprint 8's HistoryService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = HistoryService()

        # Sample curve data for testing
        self.sample_data1 = [(1, 10.0, 20.0), (2, 30.0, 40.0), (3, 50.0, 60.0)]

        self.sample_data2 = [(1, 15.0, 25.0), (2, 35.0, 45.0), (3, 55.0, 65.0)]

        self.sample_data3 = [(1, 20.0, 30.0), (2, 40.0, 50.0), (3, 60.0, 70.0)]

    def test_initialization(self):
        """Test service initialization."""
        service = HistoryService()
        self.assertIsNotNone(service)
        self.assertEqual(service._current_index, -1)
        self.assertEqual(len(service._history), 0)
        self.assertEqual(service._max_size, 100)

    def test_initialization_with_custom_size(self):
        """Test initialization with custom max size."""
        service = HistoryService(max_size=50)
        self.assertEqual(service._max_size, 50)

    def test_add_to_history_first_state(self):
        """Test adding the first state to history."""
        self.service.add_to_history(self.sample_data1, "Initial state")

        self.assertEqual(len(self.service._history), 1)
        self.assertEqual(self.service._current_index, 0)
        self.assertTrue(self.service.can_undo())
        self.assertFalse(self.service.can_redo())

    def test_add_to_history_multiple_states(self):
        """Test adding multiple states."""
        self.service.add_to_history(self.sample_data1, "State 1")
        self.service.add_to_history(self.sample_data2, "State 2")
        self.service.add_to_history(self.sample_data3, "State 3")

        self.assertEqual(len(self.service._history), 3)
        self.assertEqual(self.service._current_index, 2)

    def test_add_to_history_truncates_future(self):
        """Test that adding a state truncates future history."""
        # Add three states
        self.service.add_to_history(self.sample_data1, "State 1")
        self.service.add_to_history(self.sample_data2, "State 2")
        self.service.add_to_history(self.sample_data3, "State 3")

        # Undo twice
        self.service.undo()
        self.service.undo()

        # Add a new state (should truncate State 3)
        new_data = [(1, 100.0, 200.0)]
        self.service.add_to_history(new_data, "New state")

        self.assertEqual(len(self.service._history), 2)
        self.assertEqual(self.service._current_index, 1)

    def test_undo_single_action(self):
        """Test undoing a single action."""
        self.service.add_to_history(self.sample_data1, "State 1")
        self.service.add_to_history(self.sample_data2, "State 2")

        # Undo to State 1
        result = self.service.undo()

        self.assertEqual(result, self.sample_data1)
        self.assertEqual(self.service._current_index, 0)
        self.assertTrue(self.service.can_undo())
        self.assertTrue(self.service.can_redo())

    def test_undo_at_beginning(self):
        """Test undo when at the beginning of history."""
        self.service.add_to_history(self.sample_data1, "State 1")

        # Undo once (goes to before any states)
        result = self.service.undo()
        self.assertIsNone(result)
        self.assertEqual(self.service._current_index, -1)

        # Undo again (should do nothing)
        result = self.service.undo()
        self.assertIsNone(result)
        self.assertEqual(self.service._current_index, -1)

    def test_redo_single_action(self):
        """Test redoing a single action."""
        self.service.add_to_history(self.sample_data1, "State 1")
        self.service.add_to_history(self.sample_data2, "State 2")

        # Undo then redo
        self.service.undo()
        result = self.service.redo()

        self.assertEqual(result, self.sample_data2)
        self.assertEqual(self.service._current_index, 1)

    def test_redo_at_end(self):
        """Test redo when at the end of history."""
        self.service.add_to_history(self.sample_data1, "State 1")

        # Try to redo without undoing first
        result = self.service.redo()

        self.assertIsNone(result)
        self.assertEqual(self.service._current_index, 0)

    def test_can_undo_can_redo(self):
        """Test can_undo and can_redo methods."""
        # Initially, cannot undo or redo
        self.assertFalse(self.service.can_undo())
        self.assertFalse(self.service.can_redo())

        # Add a state
        self.service.add_to_history(self.sample_data1, "State 1")
        self.assertTrue(self.service.can_undo())
        self.assertFalse(self.service.can_redo())

        # Add another state
        self.service.add_to_history(self.sample_data2, "State 2")
        self.assertTrue(self.service.can_undo())
        self.assertFalse(self.service.can_redo())

        # Undo once
        self.service.undo()
        self.assertTrue(self.service.can_undo())
        self.assertTrue(self.service.can_redo())

        # Undo again
        self.service.undo()
        self.assertFalse(self.service.can_undo())
        self.assertTrue(self.service.can_redo())

    def test_clear_history(self):
        """Test clearing history."""
        self.service.add_to_history(self.sample_data1, "State 1")
        self.service.add_to_history(self.sample_data2, "State 2")

        self.service.clear_history()

        self.assertEqual(len(self.service._history), 0)
        self.assertEqual(self.service._current_index, -1)
        self.assertFalse(self.service.can_undo())
        self.assertFalse(self.service.can_redo())

    def test_get_history_stats(self):
        """Test getting history statistics."""
        self.service.add_to_history(self.sample_data1, "State 1")
        self.service.add_to_history(self.sample_data2, "State 2")
        self.service.add_to_history(self.sample_data3, "State 3")
        self.service.undo()

        stats = self.service.get_history_stats()

        self.assertIsInstance(stats, HistoryStats)
        self.assertEqual(stats.total_entries, 3)
        self.assertEqual(stats.current_position, 1)
        self.assertTrue(stats.can_undo)
        self.assertTrue(stats.can_redo)
        self.assertGreater(stats.memory_usage, 0)

    def test_get_current_state(self):
        """Test getting the current state."""
        self.service.add_to_history(self.sample_data1, "State 1")
        self.service.add_to_history(self.sample_data2, "State 2")

        current = self.service.get_current_state()
        self.assertEqual(current, self.sample_data2)

        self.service.undo()
        current = self.service.get_current_state()
        self.assertEqual(current, self.sample_data1)

    def test_get_current_state_empty_history(self):
        """Test getting current state with empty history."""
        current = self.service.get_current_state()
        self.assertIsNone(current)

    def test_history_size_limit(self):
        """Test that history respects size limit."""
        service = HistoryService(max_size=3)

        # Add more states than the limit
        service.add_to_history(self.sample_data1, "State 1")
        service.add_to_history(self.sample_data2, "State 2")
        service.add_to_history(self.sample_data3, "State 3")

        # This should remove the oldest state
        new_data = [(1, 111.0, 222.0)]
        service.add_to_history(new_data, "State 4")

        self.assertEqual(len(service._history), 3)
        # First state should be State 2 now
        service.undo()  # To State 3
        service.undo()  # To State 2
        result = service.get_current_state()
        self.assertEqual(result, self.sample_data2)

    def test_compress_and_decompress(self):
        """Test that compression and decompression work correctly."""
        # Add a large dataset
        large_data = [(i, float(i * 10), float(i * 20)) for i in range(1000)]

        self.service.add_to_history(large_data, "Large state")

        # Retrieve it
        result = self.service.get_current_state()

        self.assertEqual(result, large_data)

    def test_get_history_size(self):
        """Test getting history size."""
        self.assertEqual(self.service.get_history_size(), 0)

        self.service.add_to_history(self.sample_data1, "State 1")
        self.assertEqual(self.service.get_history_size(), 1)

        self.service.add_to_history(self.sample_data2, "State 2")
        self.assertEqual(self.service.get_history_size(), 2)

        self.service.clear_history()
        self.assertEqual(self.service.get_history_size(), 0)

    def test_identical_states_not_added(self):
        """Test that identical consecutive states are not added."""
        self.service.add_to_history(self.sample_data1, "State 1")

        # Try to add the same state again
        self.service.add_to_history(self.sample_data1, "State 1 duplicate")

        # Should still have only one state
        self.assertEqual(self.service.get_history_size(), 1)

    def test_empty_state_handling(self):
        """Test handling of empty states."""
        empty_data = []

        self.service.add_to_history(empty_data, "Empty state")

        result = self.service.get_current_state()
        self.assertEqual(result, empty_data)

    def test_none_state_handling(self):
        """Test handling of None states."""
        # Should handle None gracefully
        self.service.add_to_history(None, "None state")

        # Should not add None to history
        self.assertEqual(self.service.get_history_size(), 0)

    def test_undo_redo_sequence(self):
        """Test a complex undo/redo sequence."""
        # Add states
        self.service.add_to_history(self.sample_data1, "State 1")
        self.service.add_to_history(self.sample_data2, "State 2")
        self.service.add_to_history(self.sample_data3, "State 3")

        # Undo all
        self.service.undo()  # To State 2
        self.service.undo()  # To State 1
        self.service.undo()  # To before any state

        self.assertFalse(self.service.can_undo())
        self.assertTrue(self.service.can_redo())

        # Redo all
        self.service.redo()  # To State 1
        self.service.redo()  # To State 2
        self.service.redo()  # To State 3

        self.assertTrue(self.service.can_undo())
        self.assertFalse(self.service.can_redo())

        result = self.service.get_current_state()
        self.assertEqual(result, self.sample_data3)

    def test_memory_usage_tracking(self):
        """Test that memory usage is tracked."""
        stats = self.service.get_history_stats()
        initial_memory = stats.memory_usage

        # Add a large state
        large_data = [(i, float(i), float(i * 2)) for i in range(1000)]
        self.service.add_to_history(large_data, "Large state")

        stats = self.service.get_history_stats()
        self.assertGreater(stats.memory_usage, initial_memory)

    def test_thread_safety_considerations(self):
        """Test that service handles concurrent access safely."""
        # This is a basic test - real thread safety would need more
        import threading

        def add_states():
            for i in range(10):
                self.service.add_to_history([(i, float(i), float(i * 2))], f"State {i}")

        # Create multiple threads
        threads = [threading.Thread(target=add_states) for _ in range(3)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Should have some states (exact number may vary due to race conditions)
        self.assertGreater(self.service.get_history_size(), 0)
        self.assertLessEqual(self.service.get_history_size(), 30)


if __name__ == "__main__":
    unittest.main()
