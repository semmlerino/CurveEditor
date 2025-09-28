#!/usr/bin/env python
"""
TDD test to reproduce and fix the bug where timeline-curve connection breaks
when selecting a second point.

This test follows the exact user-reported scenario:
1. Select first point - works fine
2. Select second point - connection breaks
3. Timeline no longer reflects curve changes
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from core.models import PointStatus
from stores import get_store_manager
from ui.main_window import MainWindow


class TestTimelineCurveSyncSecondSelection:
    """Test timeline-curve synchronization when selecting multiple points."""

    @pytest.fixture(scope="session")
    def qapp(self):
        """Shared QApplication for all tests."""
        app = QApplication.instance() or QApplication([])
        yield app
        app.processEvents()

    @pytest.fixture
    def main_window(self, qtbot, qapp):
        """Create MainWindow with test data."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)

        # Set up test curve data with multiple points using proper type
        from core.type_aliases import CurveDataList

        test_data: CurveDataList = [
            (1, 100.0, 200.0, PointStatus.KEYFRAME.value),
            (5, 150.0, 250.0, PointStatus.NORMAL.value),
            (10, 200.0, 300.0, PointStatus.ENDFRAME.value),
            (15, 250.0, 350.0, PointStatus.KEYFRAME.value),
        ]

        # Set the data via the curve widget (which should update timeline)
        if window.curve_widget is not None:
            window.curve_widget.set_curve_data(test_data)
        qtbot.wait(100)  # Allow signals to process

        return window

    def test_timeline_curve_sync_breaks_on_second_selection(self, qtbot, main_window):
        """Test that demonstrates the bug where selecting second point breaks sync."""
        curve_widget = main_window.curve_widget
        timeline = main_window.timeline_tabs
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Initial state: no selection
        assert len(curve_widget.selected_indices) == 0
        assert len(curve_store.get_selection()) == 0

        # Step 1: Select first point (index 0) - this should work fine
        print("=== Selecting first point ===")
        curve_store.select(0, add_to_selection=False)
        qtbot.wait(50)

        # Verify first selection works
        assert 0 in curve_widget.selected_indices, "First point should be selected in curve"
        assert 0 in curve_store.get_selection(), "First point should be selected in store"

        # Check timeline shows selection (if it has a method to check)
        if hasattr(timeline, "get_frame_status"):
            frame_1_status = timeline.get_frame_status(1)
            print(f"Timeline frame 1 status after first selection: {frame_1_status}")

        # Step 2: Select second point (index 1) - THIS IS WHERE IT BREAKS
        print("=== Selecting second point (this is where it breaks) ===")

        # Store initial state to compare
        curve_store.get_selection().copy()
        curve_widget.selected_indices.copy()

        # Add second point to selection (Ctrl+click behavior)
        curve_store.select(1, add_to_selection=True)
        qtbot.wait(50)

        # Verify second selection state
        expected_selection = {0, 1}
        curve_selection = set(curve_widget.selected_indices)
        store_selection = curve_store.get_selection()

        print("After second selection:")
        print(f"  Curve selection: {curve_selection}")
        print(f"  Store selection: {store_selection}")

        # This assertion should pass - curve widget handles multi-selection
        assert curve_selection == expected_selection, f"Curve should have both points selected, got {curve_selection}"

        # This might fail if store doesn't sync properly
        assert store_selection == expected_selection, f"Store should have both points selected, got {store_selection}"

        # Step 3: Try to toggle status - this is where user notices the break
        print("=== Testing status toggle after second selection ===")

        # Get current status of selected points
        point_0_data = curve_store.get_point(0)
        point_1_data = curve_store.get_point(1)

        print(f"Point 0 data: {point_0_data}")
        print(f"Point 1 data: {point_1_data}")

        initial_point_0_status = point_0_data[3] if point_0_data and len(point_0_data) > 3 else "unknown"
        initial_point_1_status = point_1_data[3] if point_1_data and len(point_1_data) > 3 else "unknown"

        # Simulate E key press to toggle status
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)

        # Track if signals are emitted
        signals_emitted = []

        def track_data_changed():
            signals_emitted.append("data_changed")

        def track_selection_changed(selection):
            signals_emitted.append(f"selection_changed: {selection}")

        def track_point_status_changed(index, status):
            signals_emitted.append(f"point_status_changed: {index} -> {status}")

        # Connect signal trackers
        curve_store.data_changed.connect(track_data_changed)
        curve_store.selection_changed.connect(track_selection_changed)
        curve_store.point_status_changed.connect(track_point_status_changed)

        try:
            # Debug: Check global event filter and registry
            print(f"Global event filter exists: {hasattr(main_window, 'global_event_filter')}")
            if hasattr(main_window, "global_event_filter"):
                registry = main_window.global_event_filter.registry
                print(f"Registry has commands: {len(registry.list_shortcuts())}")

                # Look for E key command
                e_command = registry.get_command(key_event)
                print(f"E key command found: {e_command}")
                if e_command:
                    print(f"Command type: {type(e_command).__name__}")

                    # Build context like the event filter does
                    try:
                        context = main_window.global_event_filter._build_context(key_event, main_window)
                        print("Context built successfully:")
                        print(f"  Selected curve points: {context.selected_curve_points}")
                        print(f"  Has curve selection: {context.has_curve_selection}")
                        print(f"  Current frame: {context.current_frame}")

                        # Test can_execute
                        can_exec = e_command.can_execute(context)
                        print(f"  Command can_execute: {can_exec}")

                        if not can_exec:
                            print("  Command cannot execute - this is likely the problem!")

                    except Exception as e:
                        print(f"Error building context: {e}")

            # Send key event to application (not just main window) to trigger global filter
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app:
                print("Sending key event to application...")
                app.sendEvent(main_window, key_event)
            else:
                print("No QApplication instance found")

            qtbot.wait(100)  # Allow command to process

            print(f"Signals emitted after E key: {signals_emitted}")

            # Check if status actually changed
            new_point_0_data = curve_store.get_point(0)
            new_point_1_data = curve_store.get_point(1)

            new_point_0_status = new_point_0_data[3] if new_point_0_data and len(new_point_0_data) > 3 else "unknown"
            new_point_1_status = new_point_1_data[3] if new_point_1_data and len(new_point_1_data) > 3 else "unknown"

            print("Status changes:")
            print(f"  Point 0: {initial_point_0_status} -> {new_point_0_status}")
            print(f"  Point 1: {initial_point_1_status} -> {new_point_1_status}")

            # At least one status should have changed (toggle behavior)
            status_changed = (new_point_0_status != initial_point_0_status) or (
                new_point_1_status != initial_point_1_status
            )

            # This assertion might fail if the connection is broken
            assert status_changed, "E key should toggle status of selected points"

            # Critical test: check if timeline reflects the changes
            # With the fix, we should see point_status_changed signals instead of data_changed
            status_signal_emitted = any("point_status_changed" in signal for signal in signals_emitted)
            assert (
                status_signal_emitted
            ), f"point_status_changed signal should be emitted after status toggle, got signals: {signals_emitted}"

            # Critical fix verification: selections should be preserved after status change
            final_curve_selection = set(curve_widget.selected_indices)
            final_store_selection = curve_store.get_selection()

            print("Final selections:")
            print(f"  Curve: {final_curve_selection}")
            print(f"  Store: {final_store_selection}")

            # FIXED: Selections should now be preserved after status changes
            assert (
                final_curve_selection == expected_selection
            ), f"Curve selection should be preserved after status change, expected {expected_selection}, got {final_curve_selection}"
            assert (
                final_store_selection == expected_selection
            ), f"Store selection should be preserved after status change, expected {expected_selection}, got {final_store_selection}"

        finally:
            # Clean up signal connections
            curve_store.data_changed.disconnect(track_data_changed)
            curve_store.selection_changed.disconnect(track_selection_changed)
            curve_store.point_status_changed.disconnect(track_point_status_changed)

    def test_signal_integrity_after_multi_selection(self, qtbot, main_window):
        """Test that signal connections remain intact after multi-point selection."""
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Track signal emissions to verify signals still work
        signals_received = []

        def track_data_changed():
            signals_received.append("data_changed")

        def track_selection_changed(selection):
            signals_received.append(f"selection_changed: {selection}")

        # Connect signal trackers
        curve_store.data_changed.connect(track_data_changed)
        curve_store.selection_changed.connect(track_selection_changed)

        try:
            # Make multiple selections
            curve_store.select(0, add_to_selection=False)
            qtbot.wait(50)
            curve_store.select(1, add_to_selection=True)
            qtbot.wait(50)
            curve_store.select(2, add_to_selection=True)
            qtbot.wait(50)

            # Verify selection signals were emitted
            selection_signals = [s for s in signals_received if "selection_changed" in s]
            assert (
                len(selection_signals) >= 3
            ), f"Should have received at least 3 selection_changed signals, got: {selection_signals}"

            # Trigger a data change to verify that signal still works
            curve_store.set_data([(0, 0.0, 0.0, "test")])
            qtbot.wait(50)

            # Verify data_changed signal was emitted
            assert (
                "data_changed" in signals_received
            ), f"data_changed signal should work after multi-selection, received: {signals_received}"

        finally:
            # Clean up signal connections
            curve_store.data_changed.disconnect(track_data_changed)
            curve_store.selection_changed.disconnect(track_selection_changed)

    def test_timeline_update_mechanism_after_second_selection(self, qtbot, main_window):
        """Test the specific timeline update mechanism that might be breaking."""
        timeline = main_window.timeline_tabs
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Track timeline update calls
        update_calls = []

        # Patch timeline update methods to track calls
        original_on_store_data_changed = timeline._on_store_data_changed
        original_on_store_selection_changed = getattr(timeline, "_on_store_selection_changed", None)

        def tracked_data_changed():
            update_calls.append("_on_store_data_changed")
            try:
                return original_on_store_data_changed()
            except Exception as e:
                update_calls.append(f"_on_store_data_changed ERROR: {e}")
                raise

        def tracked_selection_changed(selection):
            update_calls.append(f"_on_store_selection_changed: {selection}")
            if original_on_store_selection_changed:
                try:
                    return original_on_store_selection_changed(selection)
                except Exception as e:
                    update_calls.append(f"_on_store_selection_changed ERROR: {e}")
                    raise

        # Apply patches
        timeline._on_store_data_changed = tracked_data_changed
        if hasattr(timeline, "_on_store_selection_changed"):
            timeline._on_store_selection_changed = tracked_selection_changed

        try:
            # Select first point
            print("=== First selection ===")
            curve_store.select(0, add_to_selection=False)
            qtbot.wait(100)

            first_selection_calls = update_calls.copy()
            print(f"Timeline update calls after first selection: {first_selection_calls}")

            # Select second point
            print("=== Second selection ===")
            update_calls.clear()
            curve_store.select(1, add_to_selection=True)
            qtbot.wait(100)

            second_selection_calls = update_calls.copy()
            print(f"Timeline update calls after second selection: {second_selection_calls}")

            # Trigger a data change and see if timeline responds
            print("=== Triggering data change ===")
            update_calls.clear()

            # Manually trigger data change
            curve_store.data_changed.emit()
            qtbot.wait(100)

            data_change_calls = update_calls.copy()
            print(f"Timeline update calls after manual data change: {data_change_calls}")

            # Timeline should respond to data changes
            assert "_on_store_data_changed" in str(data_change_calls), "Timeline should respond to data_changed signal"

        finally:
            # Restore original methods
            timeline._on_store_data_changed = original_on_store_data_changed
            if original_on_store_selection_changed and hasattr(timeline, "_on_store_selection_changed"):
                timeline._on_store_selection_changed = original_on_store_selection_changed
