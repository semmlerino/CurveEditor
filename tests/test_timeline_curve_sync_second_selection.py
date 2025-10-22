#!/usr/bin/env python
"""
TDD test to reproduce and fix the bug where timeline-curve connection breaks
when selecting a second point.

This test follows the exact user-reported scenario:
1. Select first point - works fine
2. Select second point - connection breaks
3. Timeline no longer reflects curve changes
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

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from core.models import PointStatus
from stores.application_state import get_application_state
from ui.main_window import MainWindow


class TestTimelineCurveSyncSecondSelection:
    """Test timeline-curve synchronization when selecting multiple points."""

    @pytest.fixture
    def main_window(self, qtbot, qapp):
        """Create MainWindow with test data."""
        window = MainWindow(auto_load_data=False)  # Disable auto-loading test data
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
        app_state = get_application_state()

        # Get active curve name
        active_curve = app_state.active_curve
        assert active_curve is not None, "Active curve should be set"

        # Initial state: no selection
        assert len(curve_widget.selected_indices) == 0
        assert len(app_state.get_selection(active_curve)) == 0

        # Step 1: Select first point (index 0) - this should work fine
        print("=== Selecting first point ===")
        app_state.set_selection(active_curve, {0})
        qtbot.wait(50)

        # Verify first selection works
        assert 0 in curve_widget.selected_indices, "First point should be selected in curve"
        assert 0 in app_state.get_selection(active_curve), "First point should be selected in store"

        # Check timeline shows selection (if it has a method to check)
        if hasattr(timeline, "get_frame_status"):
            frame_1_status = timeline.get_frame_status(1)
            print(f"Timeline frame 1 status after first selection: {frame_1_status}")

        # Step 2: Select second point (index 1) - THIS IS WHERE IT BREAKS
        print("=== Selecting second point (this is where it breaks) ===")

        # Store initial state to compare
        app_state.get_selection(active_curve).copy()
        curve_widget.selected_indices.copy()

        # Add second point to selection (Ctrl+click behavior)
        app_state.add_to_selection(active_curve, 1)
        qtbot.wait(50)

        # Verify second selection state
        expected_selection = {0, 1}
        curve_selection = set(curve_widget.selected_indices)
        store_selection = app_state.get_selection(active_curve)

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
        curve_data = app_state.get_curve_data(active_curve)
        assert curve_data is not None, "Curve data should exist"

        point_0_data = curve_data[0] if len(curve_data) > 0 else None
        point_1_data = curve_data[1] if len(curve_data) > 1 else None

        print(f"Point 0 data: {point_0_data}")
        print(f"Point 1 data: {point_1_data}")

        initial_point_0_status = point_0_data[3] if point_0_data and len(point_0_data) > 3 else "unknown"
        initial_point_1_status = point_1_data[3] if point_1_data and len(point_1_data) > 3 else "unknown"

        # Simulate E key press to toggle status
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)

        # Track if signals are emitted
        signals_emitted = []

        def track_curves_changed(curves):
            signals_emitted.append(f"curves_changed: {list(curves.keys())}")

        def track_selection_changed(curve_name, selection):
            signals_emitted.append(f"selection_changed: {curve_name} -> {selection}")

        # Connect signal trackers
        app_state.curves_changed.connect(track_curves_changed)
        app_state.selection_changed.connect(track_selection_changed)

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
            new_curve_data = app_state.get_curve_data(active_curve)
            assert new_curve_data is not None

            new_point_0_data = new_curve_data[0] if len(new_curve_data) > 0 else None
            new_point_1_data = new_curve_data[1] if len(new_curve_data) > 1 else None

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
            # With the fix, we should see curves_changed signals
            curves_signal_emitted = any("curves_changed" in signal for signal in signals_emitted)
            assert (
                curves_signal_emitted
            ), f"curves_changed signal should be emitted after status toggle, got signals: {signals_emitted}"

            # Critical fix verification: selections should be preserved after status change
            final_curve_selection = set(curve_widget.selected_indices)
            final_store_selection = app_state.get_selection(active_curve)

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
            app_state.curves_changed.disconnect(track_curves_changed)
            app_state.selection_changed.disconnect(track_selection_changed)

    def test_signal_integrity_after_multi_selection(self, qtbot, main_window):
        """Test that signal connections remain intact after multi-point selection."""
        app_state = get_application_state()

        # Get active curve name
        active_curve = app_state.active_curve
        assert active_curve is not None, "Active curve should be set"

        # Track signal emissions to verify signals still work
        signals_received = []

        def track_curves_changed(curves):
            signals_received.append(f"curves_changed: {list(curves.keys())}")

        def track_selection_changed(curve_name, selection):
            signals_received.append(f"selection_changed: {curve_name} -> {selection}")

        # Connect signal trackers
        app_state.curves_changed.connect(track_curves_changed)
        app_state.selection_changed.connect(track_selection_changed)

        try:
            # Make multiple selections
            app_state.set_selection(active_curve, {0})
            qtbot.wait(50)
            app_state.add_to_selection(active_curve, 1)
            qtbot.wait(50)
            app_state.add_to_selection(active_curve, 2)
            qtbot.wait(50)

            # Verify selection signals were emitted
            selection_signals = [s for s in signals_received if "selection_changed" in s]
            assert (
                len(selection_signals) >= 3
            ), f"Should have received at least 3 selection_changed signals, got: {selection_signals}"

            # Trigger a data change to verify that signal still works
            app_state.set_curve_data(active_curve, [(0, 0.0, 0.0, "test")])
            qtbot.wait(50)

            # Verify curves_changed signal was emitted
            assert any(
                "curves_changed" in s for s in signals_received
            ), f"curves_changed signal should work after multi-selection, received: {signals_received}"

        finally:
            # Clean up signal connections
            app_state.curves_changed.disconnect(track_curves_changed)
            app_state.selection_changed.disconnect(track_selection_changed)

    def test_timeline_update_mechanism_after_second_selection(self, qtbot, main_window):
        """Test the specific timeline update mechanism that might be breaking."""
        timeline = main_window.timeline_tabs
        app_state = get_application_state()

        # Get active curve name
        active_curve = app_state.active_curve
        assert active_curve is not None, "Active curve should be set"

        # Track timeline update calls
        update_calls = []

        # Patch timeline update methods to track calls
        original_on_curves_changed = timeline._on_curves_changed
        original_on_selection_changed = getattr(timeline, "_on_selection_changed", None)

        def tracked_curves_changed(curves):
            update_calls.append(f"_on_curves_changed: {list(curves.keys())}")
            try:
                return original_on_curves_changed(curves)
            except Exception as e:
                update_calls.append(f"_on_curves_changed ERROR: {e}")
                raise

        def tracked_selection_changed(curve_name, selection):
            update_calls.append(f"_on_selection_changed: {curve_name} -> {selection}")
            if original_on_selection_changed:
                try:
                    return original_on_selection_changed(curve_name, selection)
                except Exception as e:
                    update_calls.append(f"_on_selection_changed ERROR: {e}")
                    raise

        # Apply patches
        timeline._on_curves_changed = tracked_curves_changed
        if hasattr(timeline, "_on_selection_changed"):
            timeline._on_selection_changed = tracked_selection_changed

        try:
            # Select first point
            print("=== First selection ===")
            app_state.set_selection(active_curve, {0})
            qtbot.wait(100)

            first_selection_calls = update_calls.copy()
            print(f"Timeline update calls after first selection: {first_selection_calls}")

            # Select second point
            print("=== Second selection ===")
            update_calls.clear()
            app_state.add_to_selection(active_curve, 1)
            qtbot.wait(100)

            second_selection_calls = update_calls.copy()
            print(f"Timeline update calls after second selection: {second_selection_calls}")

            # Trigger a data change and see if timeline responds
            print("=== Triggering data change ===")
            update_calls.clear()

            # Manually trigger curves change
            app_state.curves_changed.emit(app_state.get_all_curves())
            qtbot.wait(100)

            data_change_calls = update_calls.copy()
            print(f"Timeline update calls after manual data change: {data_change_calls}")

            # Timeline should respond to data changes
            assert "_on_curves_changed" in str(data_change_calls), "Timeline should respond to curves_changed signal"

        finally:
            # Restore original methods
            timeline._on_curves_changed = original_on_curves_changed
            if original_on_selection_changed and hasattr(timeline, "_on_selection_changed"):
                timeline._on_selection_changed = original_on_selection_changed
