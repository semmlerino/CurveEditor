"""
Integration tests for CurveViewWidget with reactive store.

Tests that CurveViewWidget correctly integrates with CurveDataStore
for all data operations and reactive updates.
"""

import pytest
from PySide6.QtTest import QSignalSpy

from stores import get_store_manager
from ui.curve_view_widget import CurveViewWidget


class TestCurveViewWidgetStoreIntegration:
    """Test CurveViewWidget integration with reactive store."""

    @pytest.fixture(autouse=True)
    def reset_store(self):
        """Reset store manager before each test."""
        yield
        # Reset after test
        get_store_manager().reset()

    @pytest.fixture
    def widget(self, qtbot):
        """Create a CurveViewWidget for testing."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)
        return widget

    def test_widget_uses_store_for_data(self, widget):
        """Test that widget accesses data through store."""
        # Get store directly
        store = widget._curve_store

        # Set data through widget
        test_data = [(1, 100.0, 200.0), (5, 150.0, 250.0)]
        widget.set_curve_data(test_data)

        # Verify store has the data
        assert store.get_data() == test_data

        # Verify widget sees the same data
        assert widget.curve_data == test_data

    def test_widget_updates_on_store_changes(self, widget, qtbot):
        """Test that widget updates when store data changes."""
        store = widget._curve_store

        # Spy on widget's data_changed signal
        spy = QSignalSpy(widget.data_changed)

        # Change data directly in store
        test_data = [(1, 100.0, 200.0)]
        store.set_data(test_data)

        # Widget should emit its own signal
        assert spy.count() == 1

        # Widget should see the new data
        assert widget.curve_data == test_data

    def test_selection_through_store(self, widget, qtbot):
        """Test that selection goes through store."""
        store = widget._curve_store

        # Set up data
        test_data = [(1, 100.0, 200.0), (5, 150.0, 250.0), (10, 300.0, 400.0)]
        widget.set_curve_data(test_data)

        # Spy on selection signal
        spy = QSignalSpy(widget.selection_changed)

        # Select through widget method
        widget._select_point(1, add_to_selection=False)

        # Check store has the selection
        assert store.get_selection() == {1}

        # Check widget sees the same selection
        assert widget.selected_indices == {1}

        # Check signal was emitted
        assert spy.count() == 1
        # For now, just verify the signal was emitted
        # The exact argument format varies by PySide6 version

    def test_multi_selection_through_store(self, widget):
        """Test multi-selection through store."""
        store = widget._curve_store

        # Set up data
        test_data = [(i, i * 10.0, i * 20.0) for i in range(5)]
        widget.set_curve_data(test_data)

        # Select multiple points
        widget._select_point(1, add_to_selection=False)
        widget._select_point(3, add_to_selection=True)

        # Check store has both
        assert store.get_selection() == {1, 3}
        assert widget.selected_indices == {1, 3}

    def test_clear_selection_through_store(self, widget):
        """Test clearing selection through store."""
        store = widget._curve_store

        # Set up data and selection
        test_data = [(i, i * 10.0, i * 20.0) for i in range(5)]
        widget.set_curve_data(test_data)
        widget.select_all()

        # Verify all selected
        assert len(store.get_selection()) == 5

        # Clear through widget
        widget._clear_selection()

        # Verify cleared in store
        assert store.get_selection() == set()
        assert widget.selected_indices == set()

    def test_add_point_through_store(self, widget, qtbot):
        """Test adding points through store."""
        store = widget._curve_store

        # Add point through widget
        widget.add_point((1, 100.0, 200.0))

        # Check store has it
        assert store.point_count() == 1
        assert store.get_point(0) == (1, 100.0, 200.0, "keyframe")

        # Widget should see it too
        assert len(widget.curve_data) == 1

    def test_update_point_through_store(self, widget, qtbot):
        """Test updating points through store."""
        store = widget._curve_store

        # Set up initial data
        widget.set_curve_data([(1, 100.0, 200.0)])

        # Update through widget
        widget.update_point(0, 150.0, 250.0)

        # Check store has updated data
        point = store.get_point(0)
        assert point[1] == 150.0
        assert point[2] == 250.0

    def test_remove_point_through_store(self, widget):
        """Test removing points through store."""
        store = widget._curve_store

        # Set up data
        test_data = [(1, 100.0, 200.0), (5, 150.0, 250.0)]
        widget.set_curve_data(test_data)

        # Remove through widget
        widget.remove_point(0)

        # Check store
        assert store.point_count() == 1
        assert store.get_point(0)[0] == 5  # Second point is now at index 0

    def test_status_change_through_store(self, widget):
        """Test changing point status through store."""
        from core.models import PointStatus

        store = widget._curve_store

        # Set up data
        widget.set_curve_data([(1, 100.0, 200.0)])

        # Change status through widget
        widget._set_point_status(0, PointStatus.KEYFRAME)

        # Check store
        point = store.get_point(0)
        assert point[3] == "keyframe"

    def test_batch_operations_through_store(self, widget):
        """Test batch operations minimize updates."""
        store = widget._curve_store

        # Count data_changed emissions
        spy = QSignalSpy(widget.data_changed)

        # Start batch
        store.begin_batch_operation()

        # Multiple operations
        widget.add_point((1, 100.0, 200.0))
        widget.add_point((2, 150.0, 250.0))
        widget.add_point((3, 200.0, 300.0))

        # During batch, individual signals suppressed
        assert spy.count() == 0

        # End batch
        store.end_batch_operation()

        # Should get one signal for the whole batch
        assert spy.count() == 1

        # Data should be there
        assert store.point_count() == 3

    def test_undo_redo_through_store(self, widget):
        """Test undo/redo operations through store."""
        store = widget._curve_store

        # Initial data
        widget.set_curve_data([(1, 100.0, 200.0)])

        # Make a change
        widget.add_point((2, 150.0, 250.0))
        assert store.point_count() == 2

        # Undo
        store.undo()
        assert store.point_count() == 1

        # Redo
        store.redo()
        assert store.point_count() == 2

    def test_store_singleton_shared(self, widget):
        """Test that all widgets share the same store."""
        widget2 = CurveViewWidget()

        # Set data in first widget
        widget.set_curve_data([(1, 100.0, 200.0)])

        # Second widget should see the same data
        assert widget2.curve_data == [(1, 100.0, 200.0)]

        # They should have the same store instance
        assert widget._curve_store is widget2._curve_store

    def test_selection_sync_across_widgets(self, widget, qtbot):
        """Test selection synchronizes across widgets."""
        widget2 = CurveViewWidget()
        qtbot.addWidget(widget2)

        # Set data
        widget.set_curve_data([(1, 100.0, 200.0), (2, 150.0, 250.0)])

        # Select in first widget
        widget._select_point(0)

        # Second widget should see selection
        assert widget2.selected_indices == {0}

    def test_property_setters_use_store(self, widget):
        """Test compatibility property setters use store."""
        store = widget._curve_store

        # Set data
        widget.set_curve_data([(i, i * 10.0, i * 20.0) for i in range(5)])

        # Use property setter
        widget.selected_points = {1, 2, 3}

        # Store should have the selection
        assert store.get_selection() == {1, 2, 3}

        # Use selected_point_idx setter
        widget.selected_point_idx = 4

        # Should add to selection
        assert 4 in store.get_selection()
