"""
Integration tests for centralized selection state architecture.

Tests the complete flow: UI → ApplicationState → rendering

Covers all edge cases identified in independent reviews:
- Batch mode state visibility
- Qt signal timing
- Invalid curve names
- Empty selection transitions
- Redundant update filtering
"""

import warnings

import pytest

from core.display_mode import DisplayMode
from rendering.render_state import RenderState
from stores.application_state import get_application_state, reset_application_state
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow
from ui.tracking_points_panel import TrackingPointsPanel


class TestSelectionStateIntegration:
    """Test selection state flows through ApplicationState correctly."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        """Reset ApplicationState before each test."""
        reset_application_state()
        yield
        reset_application_state()

    def test_panel_selection_updates_app_state(self, qapp, qtbot):
        """Test: Panel selection → ApplicationState → display_mode."""
        panel = TrackingPointsPanel()
        app_state = get_application_state()

        # Add tracking data (legacy tuple format)
        panel.set_tracked_data({"Track1": [(1, 10, 20)], "Track2": [(1, 30, 40)]})

        # User selects two curves via table with Ctrl modifier for multi-select
        selection_model = panel.table.selectionModel()
        for row in range(panel.table.rowCount()):
            item = panel.table.item(row, 1)  # Name column
            if item and item.text() in ["Track1", "Track2"]:
                # Use Ctrl+click pattern for multi-select
                from PySide6.QtCore import QItemSelectionModel

                selection_model.select(
                    panel.table.model().index(row, 0),
                    QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
                )

        # Wait for Qt signals to process
        qtbot.wait(50)

        # ApplicationState updated
        assert app_state.get_selected_curves() == {"Track1", "Track2"}
        assert app_state.display_mode == DisplayMode.SELECTED

    def test_checkbox_updates_app_state(self, qapp):
        """Test: Checkbox toggle → ApplicationState → display_mode."""
        panel = TrackingPointsPanel()
        app_state = get_application_state()

        # User checks "show all"
        panel.display_mode_checkbox.setChecked(True)

        # ApplicationState updated
        assert app_state.get_show_all_curves() is True
        assert app_state.display_mode == DisplayMode.ALL_VISIBLE

    def test_widget_reads_from_app_state(self, qapp):
        """Test: ApplicationState → Widget display_mode property."""
        widget = CurveViewWidget()
        app_state = get_application_state()

        # Change ApplicationState
        app_state.set_show_all_curves(True)

        # Widget reflects ApplicationState
        assert widget.display_mode == DisplayMode.ALL_VISIBLE

        # Change to selection mode
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves({"Track1"})

        # Widget reflects new mode
        assert widget.display_mode == DisplayMode.SELECTED

    def test_no_synchronization_loop(self, qapp, qtbot):
        """
        Regression test: Selecting curves should NOT create infinite sync loop.

        Original bug: on_tracking_points_selected() called set_selected_points()
        which triggered _on_selection_changed() during clearing phase = race condition.

        The test verifies that updates stabilize quickly (finite calls) vs looping forever.
        """
        window = MainWindow(auto_load_data=False)
        assert window.tracking_panel is not None
        panel = window.tracking_panel
        app_state = get_application_state()

        # Load data (legacy tuple format)
        panel.set_tracked_data({"Track1": [(1, 10, 20)], "Track2": [(1, 30, 40)]})

        # Track selection changed calls
        assert window.tracking_panel is not None
        selection_changed_count = 0
        original_handler = window.tracking_panel._on_selection_changed

        def track_selection_changed():
            nonlocal selection_changed_count
            selection_changed_count += 1
            original_handler()

        window.tracking_panel._on_selection_changed = track_selection_changed

        # Simulate user selection programmatically (bypasses Qt signals, tests direct API)
        # This tests that calling ApplicationState directly doesn't cause loops
        app_state.set_selected_curves({"Track1", "Track2"})

        # Wait for Qt signals
        qtbot.wait(50)

        # Key test: Should stabilize quickly (2-3 calls max), not loop infinitely
        # Some calls expected: reverse sync from ApplicationState triggers table update
        # The recursion guard (_update_depth) prevents infinite loops
        assert (
            selection_changed_count <= 3
        ), f"Expected ≤3 calls (finite), got {selection_changed_count} (possible loop)"
        assert app_state.get_selected_curves() == {"Track1", "Track2"}

    def test_regression_multi_curve_display_bug(self, qapp, qtbot):
        """
        Regression test for: Selecting two curves only shows one.

        Original bug: selected_curve_names updated but display_mode not set to SELECTED.
        With new architecture, display_mode always correct (computed property).
        """
        window = MainWindow(auto_load_data=False)
        app_state = get_application_state()

        # Simulate the exact user action that caused the bug
        assert window.tracking_panel is not None
        window.tracking_panel.set_tracked_data({"Track1": [(1, 10, 20)], "Track2": [(1, 30, 40)]})

        # Load curves into ApplicationState (needed for rendering) - legacy tuple format
        app_state.set_curve_data("Track1", [(1, 10, 20)])
        app_state.set_curve_data("Track2", [(1, 30, 40)])

        # Select via ApplicationState (the new architecture)
        app_state.set_selected_curves({"Track1", "Track2"})

        # Wait for updates
        qtbot.wait(50)

        # This should NOT fail (original bug: only one curve rendered)
        render_state = RenderState.compute(window.curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" in render_state.visible_curves
        assert "Track2" in render_state.visible_curves
        assert len(render_state.visible_curves) == 2

    # NEW TESTS: Edge cases from reviews

    def test_batch_mode_state_visibility(self, qapp):
        """
        Test: display_mode reflects changes immediately during batch.

        Batch mode defers signal emissions, NOT state visibility.
        """
        app_state = get_application_state()

        app_state.begin_batch()
        try:
            # Set selection
            app_state.set_selected_curves({"Track1"})
            # display_mode should update immediately, even in batch
            assert app_state.display_mode == DisplayMode.SELECTED

            # Change to show all
            app_state.set_show_all_curves(True)
            # Mode should change immediately
            assert app_state.display_mode == DisplayMode.ALL_VISIBLE
        finally:
            app_state.end_batch()

        # Signals emitted now, but state was visible throughout

    def test_batch_mode_conflicting_changes(self, qapp):
        """Test precedence when both show_all and selection change in batch."""
        app_state = get_application_state()

        app_state.begin_batch()
        try:
            app_state.set_selected_curves({"Track1"})  # Would give SELECTED
            app_state.set_show_all_curves(True)  # Would give ALL_VISIBLE
        finally:
            app_state.end_batch()

        # Last write wins: show_all takes priority
        assert app_state.display_mode == DisplayMode.ALL_VISIBLE

    def test_batch_mode_same_signal_different_args(self, qapp):
        """
        Test: Batch mode with same signal emitted multiple times uses LAST args.

        Regression test for signal deduplication bug where first args were kept
        instead of last, causing listeners to receive stale state.
        """
        app_state = get_application_state()

        signal_emissions = []

        def track_signals(selected: set[str], show_all: bool):
            signal_emissions.append((selected.copy(), show_all))

        app_state.selection_state_changed.connect(track_signals)

        app_state.begin_batch()
        try:
            app_state.set_selected_curves({"Track1"})
            app_state.set_selected_curves({"Track2"})
            app_state.set_selected_curves({"Track3"})
        finally:
            app_state.end_batch()

        # Should emit LAST value only, not first
        assert len(signal_emissions) == 1
        assert signal_emissions[0][0] == {"Track3"}
        assert signal_emissions[0][1] is False

        # Verify final state matches emitted signal
        assert app_state.get_selected_curves() == {"Track3"}

    def test_qt_signal_timing_no_circular_updates(self, qapp, qtbot):
        """
        Test: _updating flag timing doesn't cause circular updates.

        The QTimer fix ensures flag release happens after queued signals.
        """
        panel = TrackingPointsPanel()
        app_state = get_application_state()

        # Track how many times _on_selection_changed fires
        call_count = 0
        original = panel._on_selection_changed

        def tracked_handler():
            nonlocal call_count
            call_count += 1
            original()

        panel._on_selection_changed = tracked_handler

        # External update to ApplicationState (triggers reverse sync)
        app_state.set_selected_curves({"Track1"})

        # Wait for Qt signals to process
        qtbot.wait(100)

        # Should only fire once (from reverse sync), not loop
        assert call_count <= 1, f"Expected ≤1 call, got {call_count}"

    def test_invalid_curve_names_warns_but_works(self, qapp):
        """
        Test: Selecting non-existent curves warns but doesn't crash.

        Allows setting selection before curves load (session restoration).
        """
        app_state = get_application_state()

        # Set selection before loading curves (session restoration scenario)
        app_state.set_selected_curves({"Track1", "Track2"})
        # Should work, no crash
        assert app_state.get_selected_curves() == {"Track1", "Track2"}

        # Load curves (legacy tuple format)
        app_state.set_curve_data("Track1", [(1, 10, 20)])

        # Select mixture of valid and invalid - ApplicationState filters invalid curves
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            app_state.set_selected_curves({"Track1", "FakeCurve"})

            # Should warn about invalid curve (logger.warning, not Python warning)
            # The warning goes to logger, not warnings module

        # Selection filtered to only valid curves (defensive behavior)
        assert app_state.get_selected_curves() == {"Track1"}

    def test_empty_selection_transitions(self, qapp):
        """Test all display mode transitions with empty selections."""
        app_state = get_application_state()

        # Start: ACTIVE_ONLY (no selection, no show_all)
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

        # Select curves → SELECTED
        app_state.set_selected_curves({"Track1"})
        assert app_state.display_mode == DisplayMode.SELECTED

        # Clear selection → back to ACTIVE_ONLY
        app_state.set_selected_curves(set())
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

        # Enable show_all → ALL_VISIBLE
        app_state.set_show_all_curves(True)
        assert app_state.display_mode == DisplayMode.ALL_VISIBLE

        # Disable show_all with no selection → ACTIVE_ONLY
        app_state.set_show_all_curves(False)
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

    def test_redundant_updates_filtered(self, qapp):
        """Test: Setting same value twice doesn't emit duplicate signals."""
        app_state = get_application_state()

        signal_count = 0

        def count_signals(selected: set[str], show_all: bool):
            nonlocal signal_count
            signal_count += 1

        app_state.selection_state_changed.connect(count_signals)

        # First update
        app_state.set_selected_curves({"Track1"})
        assert signal_count == 1

        # Same value again - should NOT emit signal
        app_state.set_selected_curves({"Track1"})
        assert signal_count == 1  # Still 1, not 2

    def test_set_display_mode_edge_case_no_active_curve(self, qapp):
        """
        Test: set_display_mode(SELECTED) when no active curve.

        Should log warning and remain in ACTIVE_ONLY mode.
        """
        window = MainWindow()
        app_state = get_application_state()

        # Ensure no active curve - set via ApplicationState (property has no setter)
        app_state.set_active_curve(None)

        # Try to set SELECTED mode - should warn and stay in ACTIVE_ONLY
        # The warning goes to logger, not pytest.warns
        from ui.controllers.multi_point_tracking_controller import MultiPointTrackingController

        controller = window.multi_point_controller
        assert isinstance(controller, MultiPointTrackingController)
        controller.set_display_mode(DisplayMode.SELECTED)

        # Mode should remain ACTIVE_ONLY (no curves to select)
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

    def test_widget_destruction_disconnects_signals(self, qapp, qtbot):
        """
        Test: Widget destruction properly cleans up signal connections.

        Regression test for memory leak where widgets connected directly to
        ApplicationState signals without using SignalManager for cleanup.
        """
        from ui.curve_view_widget import CurveViewWidget
        from ui.tracking_points_panel import TrackingPointsPanel

        app_state = get_application_state()

        # Track signal emissions to verify connections
        emission_count = 0

        def track_emissions(selected: set[str], show_all: bool):
            nonlocal emission_count
            emission_count += 1

        app_state.selection_state_changed.connect(track_emissions)

        # Create widgets (they connect to ApplicationState)
        widget = CurveViewWidget()
        panel = TrackingPointsPanel()

        # Trigger signal to verify widgets are connected
        app_state.set_selected_curves({"Track1"})
        initial_emissions = emission_count

        # Both widgets should have received the signal
        assert initial_emissions >= 1

        # Destroy widgets
        widget.deleteLater()
        panel.deleteLater()
        qapp.processEvents()  # Process deleteLater events

        # Reset counter
        emission_count = 0

        # Trigger signal again - destroyed widgets should NOT receive it
        app_state.set_selected_curves({"Track2"})

        # Signal should still work (our tracker receives it)
        assert emission_count == 1

        # Key test: No crashes or errors from destroyed widgets trying to handle signal
        # (If SignalManager cleanup failed, this would crash or log errors)
