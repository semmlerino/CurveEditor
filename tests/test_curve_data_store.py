"""
Tests for the reactive CurveDataStore.

Verifies that the store correctly manages data and emits signals for all changes.
"""

import pytest
from PySide6.QtTest import QSignalSpy

from core.models import PointStatus
from stores.curve_data_store import CurveDataStore
from stores.store_manager import StoreManager


class TestCurveDataStore:
    """Test the reactive curve data store."""

    @pytest.fixture
    def store(self):
        """Create a fresh store for each test."""
        return CurveDataStore()

    @pytest.fixture
    def sample_data(self):
        """Sample curve data for testing."""
        return [
            (1, 100.0, 200.0, "keyframe"),
            (5, 150.0, 250.0, "keyframe"),
            (10, 200.0, 300.0, "interpolated"),
        ]

    def test_initial_state(self, store):
        """Test store initializes with empty data."""
        assert store.get_data() == []
        assert store.get_selection() == set()
        assert store.point_count() == 0

    def test_set_data(self, store, sample_data):
        """Test setting curve data."""
        store.set_data(sample_data)

        assert store.point_count() == 3
        assert store.get_data() == sample_data
        assert store.get_selection() == set()  # Selection cleared on data change

    def test_set_data_emits_signal(self, store, sample_data, qtbot):
        """Test that set_data emits data_changed signal."""
        with qtbot.waitSignal(store.data_changed, timeout=100):
            store.set_data(sample_data)

    def test_add_point(self, store):
        """Test adding a point."""
        index = store.add_point((1, 100.0, 200.0, "keyframe"))

        assert index == 0
        assert store.point_count() == 1
        assert store.get_point(0) == (1, 100.0, 200.0, "keyframe")

    def test_add_point_without_status(self, store):
        """Test adding a point without status defaults to keyframe."""
        index = store.add_point((1, 100.0, 200.0))

        assert store.get_point(index)[3] == "keyframe"

    def test_add_point_emits_signal(self, store, qtbot):
        """Test that add_point emits point_added signal."""
        with qtbot.waitSignal(store.point_added, timeout=100) as blocker:
            store.add_point((1, 100.0, 200.0))

        assert blocker.args[0] == 0  # Index
        assert blocker.args[1] == (1, 100.0, 200.0, "keyframe")  # Point data

    def test_update_point(self, store, sample_data):
        """Test updating a point's coordinates."""
        store.set_data(sample_data)
        result = store.update_point(1, 175.0, 275.0)

        assert result is True
        point = store.get_point(1)
        assert point[1] == 175.0
        assert point[2] == 275.0
        assert point[0] == 5  # Frame unchanged
        assert point[3] == "keyframe"  # Status unchanged

    def test_update_point_invalid_index(self, store):
        """Test updating with invalid index returns False."""
        result = store.update_point(10, 100.0, 200.0)
        assert result is False

    def test_update_point_emits_signal(self, store, sample_data, qtbot):
        """Test that update_point emits point_updated signal."""
        store.set_data(sample_data)

        with qtbot.waitSignal(store.point_updated, timeout=100) as blocker:
            store.update_point(1, 175.0, 275.0)

        assert blocker.args == [1, 175.0, 275.0]

    def test_remove_point(self, store, sample_data):
        """Test removing a point."""
        store.set_data(sample_data)
        result = store.remove_point(1)

        assert result is True
        assert store.point_count() == 2
        assert store.get_point(1)[0] == 10  # Third point moved to index 1

    def test_remove_point_invalid_index(self, store):
        """Test removing with invalid index returns False."""
        result = store.remove_point(10)
        assert result is False

    def test_remove_point_emits_signal(self, store, sample_data, qtbot):
        """Test that remove_point emits point_removed signal."""
        store.set_data(sample_data)

        with qtbot.waitSignal(store.point_removed, timeout=100) as blocker:
            store.remove_point(1)

        assert blocker.args[0] == 1

    def test_remove_point_updates_selection(self, store, sample_data):
        """Test that removing a point updates selection indices."""
        store.set_data(sample_data)
        store.select(1)
        store.select(2, add_to_selection=True)

        store.remove_point(0)

        # Indices should shift down
        selection = store.get_selection()
        assert selection == {0, 1}

    def test_set_point_status(self, store, sample_data):
        """Test changing a point's status."""
        store.set_data(sample_data)
        result = store.set_point_status(1, "tracked")

        assert result is True
        assert store.get_point(1)[3] == "tracked"

    def test_set_point_status_with_enum(self, store, sample_data):
        """Test changing status with PointStatus enum."""
        store.set_data(sample_data)
        result = store.set_point_status(1, PointStatus.ENDFRAME)

        assert result is True
        assert store.get_point(1)[3] == "endframe"

    def test_set_point_status_emits_signal(self, store, sample_data, qtbot):
        """Test that set_point_status emits signal."""
        store.set_data(sample_data)

        with qtbot.waitSignal(store.point_status_changed, timeout=100) as blocker:
            store.set_point_status(1, "tracked")

        assert blocker.args == [1, "tracked"]

    def test_selection_operations(self, store, sample_data):
        """Test selection management."""
        store.set_data(sample_data)

        # Single selection
        store.select(1)
        assert store.get_selection() == {1}

        # Add to selection
        store.select(2, add_to_selection=True)
        assert store.get_selection() == {1, 2}

        # Replace selection
        store.select(0)
        assert store.get_selection() == {0}

        # Deselect
        store.deselect(0)
        assert store.get_selection() == set()

    def test_select_range(self, store):
        """Test selecting a range of points."""
        store.set_data([(i, i * 10.0, i * 20.0) for i in range(10)])
        store.select_range(2, 5)

        assert store.get_selection() == {2, 3, 4, 5}

    def test_select_all(self, store, sample_data):
        """Test selecting all points."""
        store.set_data(sample_data)
        store.select_all()

        assert store.get_selection() == {0, 1, 2}

    def test_selection_emits_signal(self, store, sample_data, qtbot):
        """Test that selection changes emit signal."""
        store.set_data(sample_data)

        with qtbot.waitSignal(store.selection_changed, timeout=100) as blocker:
            store.select(1)

        assert blocker.args[0] == {1}

    def test_batch_operations(self, store, qtbot):
        """Test batch operations suspend signals using QSignalSpy."""
        # Use QSignalSpy for real Qt signals
        point_added_spy = QSignalSpy(store.point_added)
        data_changed_spy = QSignalSpy(store.data_changed)

        store.begin_batch_operation()

        # These shouldn't emit individual signals
        store.add_point((1, 100.0, 200.0))
        store.add_point((2, 150.0, 250.0))
        store.add_point((3, 200.0, 300.0))

        assert point_added_spy.count() == 0  # No signals during batch

        # End batch should emit one data_changed signal
        with qtbot.waitSignal(store.data_changed, timeout=100):
            store.end_batch_operation()

        assert store.point_count() == 3
        assert data_changed_spy.count() == 1  # Single update signal

    def test_undo_redo(self, store):
        """Test undo/redo functionality."""
        # Initial state
        store.add_point((1, 100.0, 200.0))
        original_data = store.get_data()

        # Make change
        store.add_point((2, 150.0, 250.0))
        assert store.point_count() == 2

        # Undo
        result = store.undo()
        assert result is True
        assert store.get_data() == original_data

        # Redo
        result = store.redo()
        assert result is True
        assert store.point_count() == 2

        # Can't redo again
        assert store.can_redo() is False
        assert store.redo() is False

    def test_get_frame_range(self, store, sample_data):
        """Test getting frame range."""
        store.set_data(sample_data)
        range_result = store.get_frame_range()

        assert range_result == (1, 10)

    def test_get_frame_range_empty(self, store):
        """Test frame range with no data."""
        assert store.get_frame_range() is None

    def test_get_points_at_frame(self, store):
        """Test getting points at specific frame."""
        data = [
            (1, 100.0, 200.0),
            (1, 110.0, 210.0),
            (5, 150.0, 250.0),
            (1, 120.0, 220.0),
        ]
        store.set_data(data)

        indices = store.get_points_at_frame(1)
        assert indices == [0, 1, 3]

        indices = store.get_points_at_frame(5)
        assert indices == [2]

        indices = store.get_points_at_frame(10)
        assert indices == []

    def test_clear(self, store, sample_data):
        """Test clearing all data."""
        store.set_data(sample_data)
        store.select_all()

        store.clear()

        assert store.point_count() == 0
        assert store.get_selection() == set()


class TestStoreManager:
    """Test the singleton StoreManager."""

    def test_singleton_pattern(self):
        """Test that StoreManager is a singleton."""
        manager1 = StoreManager.get_instance()
        manager2 = StoreManager.get_instance()

        assert manager1 is manager2

    def test_get_curve_store(self):
        """Test getting the curve store."""
        manager = StoreManager.get_instance()
        store = manager.get_curve_store()

        assert isinstance(store, CurveDataStore)

    def test_store_persistence(self):
        """Test that store data persists across manager access."""
        manager1 = StoreManager.get_instance()
        manager1.get_curve_store().add_point((1, 100.0, 200.0))

        manager2 = StoreManager.get_instance()
        assert manager2.get_curve_store().point_count() == 1

    def test_save_restore_state(self):
        """Test saving and restoring state."""
        manager = StoreManager.get_instance()
        store = manager.get_curve_store()

        # Set up some data
        store.set_data(
            [
                (1, 100.0, 200.0, "keyframe"),
                (5, 150.0, 250.0, "tracked"),
            ]
        )
        store.select(1)

        # Save state
        state = manager.save_state()

        # Clear and verify cleared
        store.clear()
        assert store.point_count() == 0

        # Restore state
        manager.restore_state(state)

        # Verify restored
        assert store.point_count() == 2
        point = store.get_point(1)
        assert point is not None and len(point) > 3 and point[3] == "tracked"
        assert store.get_selection() == {1}

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton after each test."""
        yield
        StoreManager.reset()
