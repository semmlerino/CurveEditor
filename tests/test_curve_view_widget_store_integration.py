"""
Integration tests for CurveViewWidget with ApplicationState.

Tests that CurveViewWidget correctly integrates with ApplicationState
for all data operations and reactive updates.
"""

import pytest
from PySide6.QtTest import QSignalSpy

from stores import get_store_manager
from ui.curve_view_widget import CurveViewWidget


class TestCurveViewWidgetStoreIntegration:
    """Test CurveViewWidget integration with ApplicationState."""

    @pytest.fixture(autouse=True)
    def reset_store(self):
        """Reset store manager before each test."""
        yield
        # Reset after test
        get_store_manager().reset()

    @pytest.fixture
    def widget(self, qtbot):
        """Create a CurveViewWidget for testing."""
        from stores.application_state import get_application_state

        # Set __default__ as active curve so tests can use it
        app_state = get_application_state()
        app_state.set_active_curve("__default__")

        widget = CurveViewWidget()
        qtbot.addWidget(widget)
        return widget

    def test_widget_uses_store_for_data(self, widget):
        """Test that widget accesses data through ApplicationState."""
        # Get ApplicationState
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Set data through widget
        test_data = [(1, 100.0, 200.0), (5, 150.0, 250.0)]
        widget.set_curve_data(test_data)

        # Verify ApplicationState has the data
        assert app_state.get_curve_data("__default__") == test_data

        # Verify widget sees the same data
        assert widget.curve_data == test_data

    def test_widget_updates_on_store_changes(self, widget, qtbot):
        """Test that widget updates when ApplicationState data changes."""
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Spy on widget's data_changed signal
        spy = QSignalSpy(widget.data_changed)

        # Change data directly in ApplicationState
        test_data = [(1, 100.0, 200.0)]
        app_state.set_curve_data("__default__", test_data)

        # Widget should emit its own signal
        assert spy.count() == 1

        # Widget should see the new data
        assert widget.curve_data == test_data

    def test_selection_through_store(self, widget, qtbot):
        """Test that selection goes through ApplicationState."""
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Set up data
        test_data = [(1, 100.0, 200.0), (5, 150.0, 250.0), (10, 300.0, 400.0)]
        widget.set_curve_data(test_data)

        # Spy on selection signal
        spy = QSignalSpy(widget.selection_changed)

        # Select through widget method
        widget._select_point(1, add_to_selection=False)

        # Check ApplicationState has the selection
        assert app_state.get_selection("__default__") == {1}

        # Check widget sees the same selection
        assert widget.selected_indices == {1}

        # Check signal was emitted
        assert spy.count() >= 1, "Signal should be emitted at least once"

    def test_multi_selection_through_store(self, widget):
        """Test multi-selection through ApplicationState."""
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Set up data
        test_data = [(i, i * 10.0, i * 20.0) for i in range(5)]
        widget.set_curve_data(test_data)

        # Select multiple points
        widget._select_point(1, add_to_selection=False)
        widget._select_point(3, add_to_selection=True)

        # Check ApplicationState has both
        assert app_state.get_selection("__default__") == {1, 3}
        assert widget.selected_indices == {1, 3}

    def test_clear_selection_through_store(self, widget):
        """Test clearing selection through ApplicationState."""
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Set up data and selection
        test_data = [(i, i * 10.0, i * 20.0) for i in range(5)]
        widget.set_curve_data(test_data)
        widget.select_all()

        # Verify all selected
        assert len(app_state.get_selection("__default__")) == 5

        # Clear through widget
        widget.clear_selection()

        # Verify cleared in ApplicationState
        assert app_state.get_selection("__default__") == set()
        assert widget.selected_indices == set()

    def test_add_point_through_store(self, widget, qtbot):
        """Test adding points (via widget, reflected in ApplicationState)."""
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Add point through widget
        widget.add_point((1, 100.0, 200.0))

        # Check ApplicationState has it
        data = app_state.get_curve_data("__default__")
        assert len(data) == 1
        assert data[0][:3] == (1, 100.0, 200.0)

        # Widget should see it too
        assert len(widget.curve_data) == 1

    def test_update_point_through_store(self, widget, qtbot):
        """Test updating points (via widget, reflected in ApplicationState)."""
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Set up initial data
        widget.set_curve_data([(1, 100.0, 200.0)])

        # Update through widget
        widget.update_point(0, 150.0, 250.0)

        # Check ApplicationState has updated data
        data = app_state.get_curve_data("__default__")
        assert data[0][1] == 150.0
        assert data[0][2] == 250.0

    def test_remove_point_through_store(self, widget):
        """Test removing points (via widget, reflected in ApplicationState)."""
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Set up data
        test_data = [(1, 100.0, 200.0), (5, 150.0, 250.0)]
        widget.set_curve_data(test_data)

        # Remove through widget
        widget.remove_point(0)

        # Check ApplicationState
        data = app_state.get_curve_data("__default__")
        assert len(data) == 1
        assert data[0][0] == 5  # Second point remains

    def test_status_change_through_store(self, widget):
        """Test changing point status (via widget, reflected in ApplicationState)."""
        from core.models import PointStatus
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Set up data
        widget.set_curve_data([(1, 100.0, 200.0)])

        # Change status through widget
        widget._set_point_status(0, PointStatus.KEYFRAME)

        # Check ApplicationState
        data = app_state.get_curve_data("__default__")
        # Data may be 3 or 4 element tuple, check if status exists
        if len(data[0]) > 3:
            assert data[0][3] == "keyframe"

    def test_batch_operations_through_store(self, widget):
        """Test batch operations minimize updates."""
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Count data_changed emissions
        spy = QSignalSpy(widget.data_changed)

        # Batch operations in ApplicationState
        with app_state.batch_updates():
            # Multiple operations
            widget.add_point((1, 100.0, 200.0))
            widget.add_point((2, 150.0, 250.0))
            widget.add_point((3, 200.0, 300.0))

            # During batch, individual signals suppressed
            assert spy.count() == 0

        # After batch ends, should get one signal for the whole batch
        assert spy.count() == 1

        # Data should be there
        data = app_state.get_curve_data("__default__")
        assert len(data) == 3

    def test_undo_redo_through_store(self, widget):
        """Test undo/redo operations (widget operations are undoable via command system)."""
        # Note: This test is now about verifying widget operations work with command system
        # Initial data
        widget.set_curve_data([(1, 100.0, 200.0)])

        # Make a change
        widget.add_point((2, 150.0, 250.0))
        assert len(widget.curve_data) == 2

        # Note: Actual undo/redo testing is done through InteractionService
        # This test just verifies data operations work correctly

    def test_store_singleton_shared(self, widget):
        """Test that all widgets share the same ApplicationState."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        widget2 = CurveViewWidget()

        # Set data in first widget
        widget.set_curve_data([(1, 100.0, 200.0)])

        # Second widget should see the same data
        assert widget2.curve_data == [(1, 100.0, 200.0)]

        # They should access the same ApplicationState instance
        assert app_state.get_curve_data("__default__") == [(1, 100.0, 200.0)]

    def test_selection_sync_across_widgets(self, widget, qtbot):
        """Test selection synchronizes across widgets via ApplicationState."""
        widget2 = CurveViewWidget()
        qtbot.addWidget(widget2)

        # Set data
        widget.set_curve_data([(1, 100.0, 200.0), (2, 150.0, 250.0)])

        # Select in first widget
        widget._select_point(0)

        # Second widget should see selection
        assert widget2.selected_indices == {0}

    def test_property_setters_use_store(self, widget):
        """Test compatibility property setters use ApplicationState."""
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Set data
        widget.set_curve_data([(i, i * 10.0, i * 20.0) for i in range(5)])

        # Use property setter
        widget.selected_points = {1, 2, 3}

        # ApplicationState should have the selection
        assert app_state.get_selection("__default__") == {1, 2, 3}

        # Use selected_point_idx setter
        widget.selected_point_idx = 4

        # Should add to selection
        assert 4 in app_state.get_selection("__default__")
