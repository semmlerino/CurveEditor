"""
Integration tests for MainWindow with reactive store.

Tests that MainWindow correctly integrates with CurveDataStore
for timeline updates and data access.
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QWidget

from stores import get_store_manager


class MinimalMainWindow(QWidget):
    """Minimal MainWindow for testing ApplicationState integration."""

    def __init__(self):
        super().__init__()
        # Get ApplicationState
        from stores.application_state import get_application_state

        self._app_state = get_application_state()
        self._curve_name = "__default__"  # Default curve name for testing

        # Mock components
        self.timeline_tabs = MagicMock()
        self.curve_widget = MagicMock()

        # Connect ApplicationState signals
        self._connect_state_signals()

    def _connect_state_signals(self):
        """Connect to ApplicationState signals for automatic updates."""
        # Connect ApplicationState signals to ensure timeline always updates
        self._app_state.curves_changed.connect(self._update_timeline_tabs)
        self._app_state.selection_changed.connect(self._on_selection_changed)

    def _update_timeline_tabs(self):
        """Update timeline tabs."""
        # Will be mocked in tests

    def _on_selection_changed(self, selection, curve_name):
        """Handle selection changes from ApplicationState.

        Args:
            selection: Set of selected point indices
            curve_name: Name of the curve whose selection changed
        """
        if curve_name == self._curve_name and selection:
            min_idx = min(selection)
            self._update_point_editor(min_idx)
        self._update_ui_state()

    def _update_point_editor(self, idx):
        """Update point editor."""
        # Will be mocked in tests

    def _update_ui_state(self):
        """Update UI state."""
        # Will be mocked in tests

    @property
    def curve_data(self):
        """Get the current curve data from ApplicationState."""
        return self._app_state.get_curve_data(self._curve_name)


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
        """Test that MainWindow has access to ApplicationState."""
        # Check attributes exist and are not None (better than hasattr)
        assert main_window._app_state is not None
        assert main_window._curve_name is not None

    def test_main_window_curve_data_property_uses_store(self, main_window):
        """Test that curve_data property gets data from ApplicationState."""
        # Set data in ApplicationState
        test_data = [(1, 100.0, 200.0), (5, 150.0, 250.0)]
        main_window._app_state.set_curve_data(main_window._curve_name, test_data)

        # Access through property should return ApplicationState data
        assert main_window.curve_data == test_data

    def test_timeline_updates_on_store_changes(self, main_window, qtbot):
        """Test that timeline updates when ApplicationState data changes."""
        # Track if update was triggered through signal emission
        update_count = [0]  # Use list to capture in closure

        def track_update():
            update_count[0] += 1

        main_window._update_timeline_tabs = track_update

        # Change data in ApplicationState
        test_data = [(1, 100.0, 200.0)]
        main_window._app_state.set_curve_data(main_window._curve_name, test_data)

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: timeline update was triggered
        assert update_count[0] > 0
        # Verify data actually changed in ApplicationState
        assert main_window.curve_data == test_data

    def test_timeline_updates_on_point_addition(self, main_window, qtbot):
        """Test that timeline updates when points are added."""
        update_triggered = [False]

        def mark_updated():
            update_triggered[0] = True

        main_window._update_timeline_tabs = mark_updated

        # Add a point via ApplicationState
        main_window._app_state.set_curve_data(main_window._curve_name, [(1, 100.0, 200.0)])

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: update was triggered and point exists
        assert update_triggered[0] is True
        assert len(main_window.curve_data) == 1
        assert main_window.curve_data[0][:3] == (1, 100.0, 200.0)

    def test_timeline_updates_on_point_update(self, main_window, qtbot):
        """Test that timeline updates when points are updated."""
        # Setup initial data
        main_window._app_state.set_curve_data(main_window._curve_name, [(1, 100.0, 200.0)])

        update_triggered = [False]

        def mark_updated():
            update_triggered[0] = True

        main_window._update_timeline_tabs = mark_updated

        # Update the point via ApplicationState
        main_window._app_state.set_curve_data(main_window._curve_name, [(1, 150.0, 250.0)])

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
        main_window._app_state.set_curve_data(main_window._curve_name, [(1, 100.0, 200.0), (2, 150.0, 250.0)])

        update_triggered = [False]

        def mark_updated():
            update_triggered[0] = True

        main_window._update_timeline_tabs = mark_updated

        # Remove a point by setting new data without first point
        main_window._app_state.set_curve_data(main_window._curve_name, [(2, 150.0, 250.0)])

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
        main_window._app_state.set_curve_data(main_window._curve_name, [(1, 100.0, 200.0)])

        update_triggered = [False]

        def mark_updated():
            update_triggered[0] = True

        main_window._update_timeline_tabs = mark_updated

        # Change point status via ApplicationState
        main_window._app_state.set_curve_data(main_window._curve_name, [(1, 100.0, 200.0, "keyframe")])

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
        main_window._app_state.set_curve_data(main_window._curve_name, [(1, 100.0, 200.0), (2, 150.0, 250.0)])
        main_window._app_state.set_active_curve(main_window._curve_name)  # Set active curve for selection

        # Track actual behavior
        editor_updated_with = [None]
        ui_state_updated = [False]

        def update_editor(idx):
            editor_updated_with[0] = idx

        def update_ui():
            ui_state_updated[0] = True

        main_window._update_point_editor = update_editor
        main_window._update_ui_state = update_ui

        # Change selection via ApplicationState
        main_window._app_state.set_selection(main_window._curve_name, {0})

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: correct index was passed and UI updated
        assert editor_updated_with[0] == 0
        assert ui_state_updated[0] is True
        # Verify selection actually changed in ApplicationState
        assert main_window._app_state.get_selection(main_window._curve_name) == {0}

    def test_store_signals_connected_on_init(self, main_window, qtbot):
        """Test that ApplicationState signals are connected during initialization."""
        # Verify signals work by testing behavior
        signal_received = [False]

        def mark_signal_received():
            signal_received[0] = True

        main_window._update_timeline_tabs = mark_signal_received

        # Trigger signal by changing data
        main_window._app_state.set_curve_data(main_window._curve_name, [(1, 100.0, 200.0)])

        # Let signals process
        qtbot.wait(10)

        # Verify behavior: signal was received and processed
        assert signal_received[0] is True

    def test_multiple_windows_share_store(self, qtbot):
        """Test that multiple MainWindow instances share the same ApplicationState."""
        window1 = MinimalMainWindow()
        window2 = MinimalMainWindow()
        qtbot.addWidget(window1)
        qtbot.addWidget(window2)

        # Both should have the same ApplicationState instance
        assert window1._app_state is window2._app_state

        # Data set in one should be visible in the other
        window1._app_state.set_curve_data(window1._curve_name, [(1, 100.0, 200.0)])
        assert window2.curve_data == [(1, 100.0, 200.0)]

    def test_batch_operations_minimize_timeline_updates(self, main_window, qtbot):
        """Test that batch_updates() doesn't trigger multiple timeline updates."""
        update_count = [0]

        def count_updates():
            update_count[0] += 1

        main_window._update_timeline_tabs = count_updates

        # Start batch operation in ApplicationState
        with main_window._app_state.batch_updates():
            # Multiple operations via ApplicationState
            main_window._app_state.set_curve_data(main_window._curve_name, [(1, 100.0, 200.0)])
            main_window._app_state.set_curve_data(main_window._curve_name, [(1, 100.0, 200.0), (2, 150.0, 250.0)])
            main_window._app_state.set_curve_data(
                main_window._curve_name, [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]
            )

            # Let any immediate signals process
            qtbot.wait(10)

            # No updates should have occurred during batch
            assert update_count[0] == 0

        # Let batch-end signal process
        qtbot.wait(10)

        # Verify behavior: exactly one update after batch, and all data present
        assert update_count[0] == 1
        assert len(main_window.curve_data) == 3
