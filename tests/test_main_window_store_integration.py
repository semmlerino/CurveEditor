"""
Integration tests for MainWindow with reactive store.

Tests that MainWindow correctly integrates with CurveDataStore
for timeline updates and data access.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QWidget

from stores import get_store_manager


class MinimalMainWindow(QWidget):
    """Minimal MainWindow for testing store integration."""

    def __init__(self):
        super().__init__()
        # Get reactive data store
        self._store_manager = get_store_manager()
        self._curve_store = self._store_manager.get_curve_store()

        # Mock components
        self.timeline_tabs = MagicMock()
        self.curve_widget = MagicMock()

        # Connect store signals
        self._connect_store_signals()

    def _connect_store_signals(self):
        """Connect to reactive store signals for automatic updates."""
        # Connect store signals directly to ensure timeline always updates
        self._curve_store.data_changed.connect(self._update_timeline_tabs)
        self._curve_store.point_added.connect(lambda idx, point: self._update_timeline_tabs())
        self._curve_store.point_updated.connect(lambda idx, x, y: self._update_timeline_tabs())
        self._curve_store.point_removed.connect(lambda idx: self._update_timeline_tabs())
        self._curve_store.point_status_changed.connect(lambda idx, status: self._update_timeline_tabs())
        self._curve_store.selection_changed.connect(self._on_store_selection_changed)

    def _update_timeline_tabs(self):
        """Update timeline tabs."""
        pass  # Will be mocked in tests

    def _on_store_selection_changed(self, selection):
        """Handle selection changes from the store."""
        if selection:
            min_idx = min(selection)
            self._update_point_editor(min_idx)
        self._update_ui_state()

    def _update_point_editor(self, idx):
        """Update point editor."""
        pass  # Will be mocked in tests

    def _update_ui_state(self):
        """Update UI state."""
        pass  # Will be mocked in tests

    @property
    def curve_data(self):
        """Get the current curve data from the store."""
        return self._curve_store.get_data()


class TestMainWindowStoreIntegration:
    """Test MainWindow integration with reactive store."""

    @pytest.fixture(autouse=True)
    def reset_store(self):
        """Reset store manager before each test."""
        yield
        # Reset after test
        get_store_manager().reset()

    @pytest.fixture
    def main_window(self, qtbot):
        """Create a minimal MainWindow for testing."""
        window = MinimalMainWindow()
        qtbot.addWidget(window)
        return window

    def test_main_window_has_store_access(self, main_window):
        """Test that MainWindow has access to the reactive store."""
        # Check attributes exist and are not None (better than hasattr)
        assert main_window._store_manager is not None
        assert main_window._curve_store is not None

    def test_main_window_curve_data_property_uses_store(self, main_window):
        """Test that curve_data property gets data from store."""
        # Set data in store
        test_data = [(1, 100.0, 200.0), (5, 150.0, 250.0)]
        main_window._curve_store.set_data(test_data)

        # Access through property should return store data
        assert main_window.curve_data == test_data

    def test_timeline_updates_on_store_changes(self, main_window, qtbot):
        """Test that timeline updates when store data changes."""
        # Track if update was triggered through signal emission
        update_count = [0]  # Use list to capture in closure

        def track_update():
            update_count[0] += 1

        main_window._update_timeline_tabs = track_update

        # Change data in store
        test_data = [(1, 100.0, 200.0)]
        main_window._curve_store.set_data(test_data)

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: timeline update was triggered
        assert update_count[0] > 0
        # Verify data actually changed in store
        assert main_window.curve_data == test_data

    def test_timeline_updates_on_point_addition(self, main_window, qtbot):
        """Test that timeline updates when points are added."""
        update_triggered = [False]

        def mark_updated():
            update_triggered[0] = True

        main_window._update_timeline_tabs = mark_updated

        # Add a point
        main_window._curve_store.add_point((1, 100.0, 200.0))

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: update was triggered and point exists
        assert update_triggered[0] is True
        assert len(main_window.curve_data) == 1
        assert main_window.curve_data[0][:3] == (1, 100.0, 200.0)

    def test_timeline_updates_on_point_update(self, main_window, qtbot):
        """Test that timeline updates when points are updated."""
        # Setup initial data
        main_window._curve_store.set_data([(1, 100.0, 200.0)])

        update_triggered = [False]

        def mark_updated():
            update_triggered[0] = True

        main_window._update_timeline_tabs = mark_updated

        # Update the point
        main_window._curve_store.update_point(0, 150.0, 250.0)

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: update triggered and data actually changed
        assert update_triggered[0] is True
        curve_data = main_window.curve_data
        assert len(curve_data) == 1
        # Check coordinates were updated (frame stays same, x/y changed)
        assert curve_data[0][0] == 1  # frame unchanged
        assert curve_data[0][1] == 150.0  # x updated
        assert curve_data[0][2] == 250.0  # y updated

    def test_timeline_updates_on_point_removal(self, main_window, qtbot):
        """Test that timeline updates when points are removed."""
        # Setup initial data
        main_window._curve_store.set_data([(1, 100.0, 200.0), (2, 150.0, 250.0)])

        update_triggered = [False]

        def mark_updated():
            update_triggered[0] = True

        main_window._update_timeline_tabs = mark_updated

        # Remove a point
        main_window._curve_store.remove_point(0)

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: update triggered and point was removed
        assert update_triggered[0] is True
        assert len(main_window.curve_data) == 1
        # Verify the right point remains (second point)
        assert main_window.curve_data[0][0] == 2  # frame from second point

    def test_timeline_updates_on_status_change(self, main_window, qtbot):
        """Test that timeline updates when point status changes."""
        # Setup initial data
        main_window._curve_store.set_data([(1, 100.0, 200.0)])

        update_triggered = [False]

        def mark_updated():
            update_triggered[0] = True

        main_window._update_timeline_tabs = mark_updated

        # Change point status
        main_window._curve_store.set_point_status(0, "keyframe")

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: update triggered and status changed
        assert update_triggered[0] is True
        curve_data = main_window.curve_data
        # Check if status is present (4th element if it exists)
        if len(curve_data[0]) > 3:
            assert curve_data[0][3] == "keyframe"

    def test_selection_updates_trigger_ui_update(self, main_window, qtbot):
        """Test that selection changes trigger UI updates."""
        # Setup initial data
        main_window._curve_store.set_data([(1, 100.0, 200.0), (2, 150.0, 250.0)])

        # Track actual behavior
        editor_updated_with = [None]
        ui_state_updated = [False]

        def update_editor(idx):
            editor_updated_with[0] = idx

        def update_ui():
            ui_state_updated[0] = True

        main_window._update_point_editor = update_editor
        main_window._update_ui_state = update_ui

        # Change selection
        main_window._curve_store.select(0)

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: correct index was passed and UI updated
        assert editor_updated_with[0] == 0
        assert ui_state_updated[0] is True
        # Verify selection actually changed in store (get_selection returns a set)
        assert main_window._curve_store.get_selection() == {0}

    def test_store_signals_connected_on_init(self, main_window, qtbot):
        """Test that store signals are connected during initialization."""
        # Verify signals work by testing behavior
        signal_received = [False]

        def mark_signal_received():
            signal_received[0] = True

        main_window._update_timeline_tabs = mark_signal_received

        # Trigger signal
        main_window._curve_store.data_changed.emit()

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: signal was received and processed
        assert signal_received[0] is True

    def test_multiple_windows_share_store(self, qtbot):
        """Test that multiple MainWindow instances share the same store."""
        window1 = MinimalMainWindow()
        window2 = MinimalMainWindow()
        qtbot.addWidget(window1)
        qtbot.addWidget(window2)

        # Both should have the same store instance
        assert window1._curve_store is window2._curve_store

        # Data set in one should be visible in the other
        window1._curve_store.set_data([(1, 100.0, 200.0)])
        assert window2.curve_data == [(1, 100.0, 200.0)]

    def test_batch_operations_minimize_timeline_updates(self, main_window, qtbot):
        """Test that batch operations don't trigger multiple timeline updates."""
        update_count = [0]

        def count_updates():
            update_count[0] += 1

        main_window._update_timeline_tabs = count_updates

        # Start batch operation
        main_window._curve_store.begin_batch_operation()

        # Multiple operations
        main_window._curve_store.add_point((1, 100.0, 200.0))
        main_window._curve_store.add_point((2, 150.0, 250.0))
        main_window._curve_store.add_point((3, 200.0, 300.0))

        # Let any immediate signals process
        qtbot.wait(10)

        # No updates should have occurred during batch
        assert update_count[0] == 0

        # End batch
        main_window._curve_store.end_batch_operation()

        # Let batch-end signal process
        qtbot.wait(10)

        # Verify behavior: exactly one update after batch, and all data present
        assert update_count[0] == 1
        assert len(main_window.curve_data) == 3
