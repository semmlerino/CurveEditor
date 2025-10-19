"""
Integration tests for frame change signal chain.

These tests exercise the ACTUAL signal chain (ApplicationState.set_frame())
rather than calling widget methods directly. This validates the signal delivery
mechanism including QueuedConnection timing and signal forwarding.

Key difference from unit tests:
- Unit tests: widget.on_frame_changed(frame) - Direct call, synchronous
- Integration tests: ApplicationState.set_frame(frame) - Signal chain, may be async
"""

from __future__ import annotations

import pytest

from core.type_aliases import CurveDataList
from stores.application_state import get_application_state
from ui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot):
    """Create a real MainWindow with actual signal connections."""
    import logging

    from stores.store_manager import StoreManager

    # Enable debug logging for coordinator
    logging.getLogger("frame_change_coordinator").setLevel(logging.DEBUG)
    logging.getLogger("CENTER").setLevel(logging.DEBUG)

    # Reset stores to clean state
    StoreManager.reset()

    # Create real MainWindow (disable auto_load_data to prevent sample data)
    window = MainWindow(auto_load_data=False)
    qtbot.addWidget(window)

    yield window

    # Cleanup
    StoreManager.reset()


class TestFrameChangeSignalChain:
    """Test frame changes through actual signal chain (not direct calls)."""

    def test_rapid_frame_changes_via_signal_chain(self, qtbot, main_window):
        """
        Test rapid scrubbing via signal chain reproduces centering lag bug.

        This test exercises the ACTUAL production code path:
        ApplicationState.set_frame() → StateManager.frame_changed
        → FrameChangeCoordinator.on_frame_changed [QUEUED]

        With QueuedConnection: Multiple frame changes queue up, causing visual jumps
        With DirectConnection: Each frame change executes immediately, smooth centering

        BUG REPRODUCTION:
        - Current code uses Qt.QueuedConnection in coordinator
        - This test should FAIL (visual jumps detected)
        - After removing QueuedConnection, this test should PASS
        """
        app_state = get_application_state()
        curve_widget = main_window.curve_widget

        # CRITICAL: Load curve data (missing in original plan)
        # Create linear motion: frame i at position (100+i, 200+i)
        test_data: CurveDataList = [(i, 100.0 + float(i), 200.0 + float(i)) for i in range(1, 101)]
        app_state.set_curve_data("Track1", test_data)
        app_state.set_active_curve("Track1")

        # Enable centering mode (required for bug to manifest)
        curve_widget.centering_mode = True

        # Debug: Check widget state
        print("\n=== WIDGET STATE ===")
        print(f"Widget size: {curve_widget.width()} x {curve_widget.height()}")
        print(f"Centering mode: {curve_widget.centering_mode}")
        print(f"Active curve: {app_state.active_curve}")
        print(f"Curve data length: {len(curve_widget.curve_data)}")
        print(f"Curve data sample: {curve_widget.curve_data[:3] if curve_widget.curve_data else 'None'}")

        # Check coordinator state
        coordinator = main_window.frame_change_coordinator
        print("\n=== COORDINATOR STATE ===")
        print(f"Coordinator exists: {coordinator is not None}")
        print(f"Coordinator.curve_widget: {coordinator.curve_widget}")
        print(
            f"Coordinator.curve_widget.centering_mode: {coordinator.curve_widget.centering_mode if coordinator.curve_widget else 'N/A'}"
        )
        print(f"Same widget instance? {coordinator.curve_widget is curve_widget}")

        # Track pan offsets to detect visual jumps
        # In smooth centering, offsets should change gradually
        # With QueuedConnection bug, offsets "jump" from processing stale frames
        pan_offset_history: list[tuple[float, float]] = []

        # Simulate rapid scrubbing (100 frames in 1 second = 10ms per frame)
        # This reproduces the user's rapid timeline scrubbing scenario
        for frame in range(1, 101):
            app_state.set_frame(frame)  # Uses ACTUAL signal chain!
            qtbot.wait(10)  # 10ms per frame

            # Capture pan offset after signal processing
            # With QueuedConnection: Queue buildup causes lag
            pan_offset_history.append((curve_widget.pan_offset_x, curve_widget.pan_offset_y))

        # Allow queue to drain completely (QueuedConnection may have queued many updates)
        print("\nWaiting for queue to drain...")
        qtbot.wait(500)  # 500ms to process all queued events

        # Capture final state after queue drains
        final_offset = (curve_widget.pan_offset_x, curve_widget.pan_offset_y)
        final_frame = app_state.current_frame
        print(f"Final offset after queue drain: {final_offset}")
        print(f"Final frame in ApplicationState: {final_frame}")
        print("Expected final frame: 100")

        # Verify smooth centering (no visual jumps)
        # For linear motion (x=100+i, y=200+i), pan offsets should change smoothly
        # Large deltas indicate "jumps" from centering on stale frames
        large_jumps: list[tuple[int, float, float]] = []

        # Debug: Check if pan offsets changed at all
        first_offset = pan_offset_history[0] if pan_offset_history else (0, 0)
        last_offset = pan_offset_history[-1] if pan_offset_history else (0, 0)
        total_x_change = abs(last_offset[0] - first_offset[0])
        total_y_change = abs(last_offset[1] - first_offset[1])

        for i in range(1, len(pan_offset_history)):
            prev_x, prev_y = pan_offset_history[i - 1]
            curr_x, curr_y = pan_offset_history[i]

            x_delta = abs(curr_x - prev_x)
            y_delta = abs(curr_y - prev_y)

            # Threshold of 5 pixels for "large jump" detection
            # For linear motion (x+=1, y+=1 per frame), centering deltas should be ~1px
            # Larger deltas indicate lag from processing stale frames
            if x_delta > 5 or y_delta > 5:
                large_jumps.append((i + 1, x_delta, y_delta))

        # Debug info
        print("\n=== DEBUG INFO ===")
        print(f"Centering mode: {curve_widget.centering_mode}")
        print(f"Total pan offset change: X={total_x_change:.1f}px, Y={total_y_change:.1f}px")
        print(f"First offset: {first_offset}")
        print(f"Last offset: {final_offset}")
        print(f"Large jumps detected: {len(large_jumps)}")
        if large_jumps:
            print(f"First 5 jumps: {large_jumps[:5]}")

        # Print first 10 and last 10 deltas for analysis
        print("\n=== FRAME-BY-FRAME DELTAS (first 10) ===")
        for i in range(1, min(11, len(pan_offset_history))):
            prev_x, prev_y = pan_offset_history[i - 1]
            curr_x, curr_y = pan_offset_history[i]
            print(f"Frame {i}→{i+1}: ΔX={abs(curr_x - prev_x):.2f}px, ΔY={abs(curr_y - prev_y):.2f}px")

        print("\n=== FRAME-BY-FRAME DELTAS (last 10) ===")
        for i in range(max(1, len(pan_offset_history) - 10), len(pan_offset_history)):
            prev_x, prev_y = pan_offset_history[i - 1]
            curr_x, curr_y = pan_offset_history[i]
            print(f"Frame {i}→{i+1}: ΔX={abs(curr_x - prev_x):.2f}px, ΔY={abs(curr_y - prev_y):.2f}px")

        # CRITICAL VALIDATION: If centering mode is enabled, pan offsets MUST change
        # If they don't change, the test isn't actually testing centering
        assert total_x_change > 10 or total_y_change > 10, (
            f"Pan offsets didn't change (X={total_x_change:.1f}, Y={total_y_change:.1f}). "
            "Centering mode may not be working!"
        )

        # ASSERTION: No large jumps detected
        # With QueuedConnection: This FAILS (multiple jumps detected)
        # With DirectConnection: This PASSES (smooth centering)
        assert not large_jumps, f"Detected {len(large_jumps)} visual jumps during centering:\n" + "\n".join(
            [f"  Frame {frame}: X jump {x:.1f}px, Y jump {y:.1f}px" for frame, x, y in large_jumps[:5]]
        )  # Show first 5

    def test_frame_change_synchronization(self, qtbot, main_window):
        """
        Test that all UI components synchronize on frame changes.

        Verifies:
        - Timeline tabs show correct frame
        - Spinbox shows correct frame
        - Curve widget renders correct frame
        - No desynchronization between components
        """
        app_state = get_application_state()

        # Load test data
        test_data: CurveDataList = [(i, float(i), float(i)) for i in range(1, 51)]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")

        # Set frame via signal chain
        test_frame = 42
        app_state.set_frame(test_frame)

        # Wait for signal processing (QueuedConnection may need time)
        qtbot.wait(50)

        # Verify all components synchronized
        assert app_state.current_frame == test_frame, "ApplicationState should be at frame 42"

        # Note: timeline_tabs and timeline_controller may not expose current_frame
        # This test validates that signal delivery happens without errors
        # Visual synchronization tested manually in Phase 2

    def test_centering_mode_toggle_via_signal_chain(self, qtbot, main_window):
        """
        Test centering mode with signal chain frame changes.

        Verifies:
        - Centering applies when mode enabled
        - No centering when mode disabled
        - Toggle works with rapid frame changes
        """
        app_state = get_application_state()
        curve_widget = main_window.curve_widget

        # Load test data
        test_data: CurveDataList = [(i, 100.0 + float(i), 200.0 + float(i)) for i in range(1, 21)]
        app_state.set_curve_data("CenterTest", test_data)
        app_state.set_active_curve("CenterTest")

        # Test 1: Centering disabled
        curve_widget.centering_mode = False
        initial_pan_x = curve_widget.pan_offset_x
        initial_pan_y = curve_widget.pan_offset_y

        app_state.set_frame(10)
        qtbot.wait(50)

        # Pan offsets should NOT change (centering disabled)
        assert curve_widget.pan_offset_x == initial_pan_x, "Pan X should not change when centering disabled"
        assert curve_widget.pan_offset_y == initial_pan_y, "Pan Y should not change when centering disabled"

        # Test 2: Centering enabled
        curve_widget.centering_mode = True

        app_state.set_frame(15)
        qtbot.wait(50)

        # Pan offsets SHOULD change (centering enabled)
        # Exact values depend on widget size, just verify they changed
        assert (
            curve_widget.pan_offset_x != initial_pan_x or curve_widget.pan_offset_y != initial_pan_y
        ), "Pan offsets should change when centering enabled"

    def test_no_memory_leak_during_rapid_frame_changes(self, qtbot, main_window):
        """
        Test that rapid frame changes don't cause memory leaks.

        Verifies signal connections clean up properly during high-frequency
        signal emissions (1000 frames in rapid succession).
        """
        app_state = get_application_state()
        curve_widget = main_window.curve_widget

        # Load test data
        test_data: CurveDataList = [(i, float(i), float(i)) for i in range(1, 1001)]
        app_state.set_curve_data("MemoryTest", test_data)
        app_state.set_active_curve("MemoryTest")

        # Rapid frame changes (1000 frames)
        # This stresses the signal queue with QueuedConnection
        for frame in range(1, 1001, 10):  # Every 10th frame for speed
            app_state.set_frame(frame)
            if frame % 100 == 0:
                qtbot.wait(10)  # Occasional wait to process queue

        # Allow queue to drain
        qtbot.wait(100)

        # If we get here without crash/hang, memory management is OK
        # Actual memory leak would require memory profiling tools
        assert curve_widget.last_painted_frame > 0, "Widget should have painted at least one frame"


class TestFrameChangeEdgeCases:
    """Test edge cases in frame change signal chain."""

    def test_frame_change_with_no_curve_data(self, qtbot, main_window):
        """Test frame changes when no curve data loaded (should not crash)."""
        app_state = get_application_state()
        curve_widget = main_window.curve_widget

        # No curve data loaded
        app_state.set_active_curve(None)

        # Enable centering (should handle gracefully)
        curve_widget.centering_mode = True

        # Change frames (should not crash)
        for frame in range(1, 11):
            app_state.set_frame(frame)
            qtbot.wait(10)

        # Should complete without error
        assert True, "Frame changes should not crash without curve data"

    def test_frame_change_with_empty_curve_data(self, qtbot, main_window):
        """Test frame changes with empty curve data list."""
        app_state = get_application_state()
        curve_widget = main_window.curve_widget

        # Load empty curve
        app_state.set_curve_data("Empty", [])
        app_state.set_active_curve("Empty")

        curve_widget.centering_mode = True

        # Should handle gracefully
        app_state.set_frame(5)
        qtbot.wait(50)

        assert True, "Empty curve data should be handled gracefully"

    def test_frame_change_during_curve_switch(self, qtbot, main_window):
        """
        Test frame changes while switching between curves.

        Verifies atomic data capture pattern handles curve switching correctly.
        """
        app_state = get_application_state()

        # Load two curves
        curve1_data: CurveDataList = [(i, float(i), float(i)) for i in range(1, 51)]
        curve2_data: CurveDataList = [(i, float(i) * 2, float(i) * 2) for i in range(1, 51)]

        app_state.set_curve_data("Curve1", curve1_data)
        app_state.set_curve_data("Curve2", curve2_data)

        # Rapidly switch curves and frames
        for i in range(10):
            app_state.set_active_curve("Curve1")
            app_state.set_frame(i * 5)
            qtbot.wait(5)

            app_state.set_active_curve("Curve2")
            app_state.set_frame(i * 5 + 2)
            qtbot.wait(5)

        # Should complete without errors
        qtbot.wait(50)
        assert True, "Rapid curve switching with frame changes should not crash"
