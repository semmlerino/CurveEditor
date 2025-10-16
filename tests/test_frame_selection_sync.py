#!/usr/bin/env python
"""
Test to verify that frame indicator updates correctly after point selection and timeline navigation.

This test ensures that the synchronization issue between point selection and timeline
navigation has been fixed - when selecting points and then navigating the timeline,
the current frame indicator should update properly on the selected points.
"""

import pytest

from core.models import PointStatus
from stores.application_state import get_application_state
from ui.main_window import MainWindow


class TestFrameSelectionSync:
    """Test frame indicator synchronization after point selection."""

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
            (20, 300.0, 400.0, PointStatus.NORMAL.value),
        ]

        # Set the data via the curve widget
        if window.curve_widget is not None:
            window.curve_widget.set_curve_data(test_data)
        qtbot.wait(100)  # Allow signals to process

        return window

    def test_frame_indicator_updates_after_point_selection(self, qtbot, main_window):
        """Test that frame indicators update correctly after selecting points and navigating timeline."""
        curve_widget = main_window.curve_widget

        # Initial state: point at frame 1 is auto-selected (application behavior)
        # The fixture sets curve data, which triggers auto-selection of point at current frame
        assert curve_widget.current_frame == 1
        # Clear auto-selection to start fresh
        from stores.application_state import get_application_state

        state = get_application_state()
        active = state.active_curve
        if active:
            state.set_selection(active, set())
        qtbot.wait(20)
        assert len(curve_widget.selected_indices) == 0

        # Step 1: Select a point (index 0 at frame 1)
        print("=== Selecting point at frame 1 ===")
        curve_widget._select_point(0, add_to_selection=False)
        qtbot.wait(50)

        # Verify point is selected
        assert 0 in curve_widget.selected_indices
        assert curve_widget.current_frame == 1

        # Step 2: Navigate to frame 5 via timeline controller
        print("=== Navigating to frame 5 ===")
        main_window.timeline_controller.set_frame(5)
        qtbot.wait(50)

        # Verify frame has been updated in the curve widget
        assert curve_widget.current_frame == 5, f"Expected frame 5, got {curve_widget.current_frame}"
        assert get_application_state().current_frame == 5

        # Step 3: Navigate to frame 10
        print("=== Navigating to frame 10 ===")
        main_window.timeline_controller.set_frame(10)
        qtbot.wait(50)

        # Verify frame has been updated
        assert curve_widget.current_frame == 10, f"Expected frame 10, got {curve_widget.current_frame}"
        assert get_application_state().current_frame == 10

        # Step 4: Select another point (index 1 at frame 5) while at frame 10
        print("=== Selecting another point while at frame 10 ===")
        curve_widget._select_point(1, add_to_selection=True)
        qtbot.wait(50)

        # Verify both points are selected and frame is still 10
        assert {0, 1} == set(curve_widget.selected_indices)
        assert curve_widget.current_frame == 10

        # Step 5: Navigate back to frame 1
        print("=== Navigating back to frame 1 ===")
        main_window.timeline_controller.set_frame(1)
        qtbot.wait(50)

        # Verify frame has been updated despite having selected points
        assert curve_widget.current_frame == 1, f"Expected frame 1, got {curve_widget.current_frame}"
        assert get_application_state().current_frame == 1
        assert {0, 1} == set(curve_widget.selected_indices)  # Selection should be preserved

        print("✓ Frame indicator synchronization test passed!")

    def test_frame_property_consistency(self, qtbot, main_window):
        """Test that different ways of accessing current frame are consistent."""
        curve_widget = main_window.curve_widget

        # Test initial state
        assert curve_widget.current_frame == 1
        assert curve_widget.get_current_frame() == 1

        # Navigate to different frames and verify consistency
        for frame in [5, 10, 15, 20, 1]:
            main_window.timeline_controller.set_frame(frame)
            qtbot.wait(20)

            assert curve_widget.current_frame == frame, f"current_frame property mismatch at frame {frame}"
            assert curve_widget.get_current_frame() == frame, f"get_current_frame() mismatch at frame {frame}"
            assert get_application_state().current_frame == frame, f"ApplicationState mismatch at frame {frame}"

        print("✓ Frame property consistency test passed!")

    def test_renderer_frame_access(self, qtbot, main_window):
        """Test that the renderer can access the current frame from the curve view."""
        curve_widget = main_window.curve_widget

        # Verify the renderer can access current_frame via the protocol
        assert hasattr(curve_widget, "current_frame")
        assert curve_widget.current_frame == 1

        # Navigate to a different frame
        main_window.timeline_controller.set_frame(15)
        qtbot.wait(50)

        # Verify renderer would get the correct frame
        assert curve_widget.current_frame == 15

        # Mock a render call to verify the frame is accessible

        # Verify curve_widget satisfies the protocol
        assert isinstance(curve_widget.current_frame, int)
        assert curve_widget.current_frame == 15

        print("✓ Renderer frame access test passed!")

    def test_frame_update_with_multiple_selections(self, qtbot, main_window):
        """Test frame updates work correctly with multiple point selections."""
        curve_widget = main_window.curve_widget

        # Select multiple points
        curve_widget._select_point(0, add_to_selection=False)  # Frame 1
        curve_widget._select_point(2, add_to_selection=True)  # Frame 10
        curve_widget._select_point(3, add_to_selection=True)  # Frame 15
        qtbot.wait(50)

        # Verify all points are selected
        assert {0, 2, 3} == set(curve_widget.selected_indices)
        assert curve_widget.current_frame == 1

        # Navigate through frames and verify frame updates regardless of selection
        test_frames = [5, 10, 15, 20, 1]
        for frame in test_frames:
            main_window.timeline_controller.set_frame(frame)
            qtbot.wait(20)

            assert curve_widget.current_frame == frame, f"Frame sync failed at {frame} with multiple selections"
            assert {0, 2, 3} == set(curve_widget.selected_indices), f"Selection lost at frame {frame}"

        print("✓ Frame update with multiple selections test passed!")

    def test_selection_after_frame_navigation(self, qtbot, main_window):
        """Test that point selection works correctly after frame navigation."""
        curve_widget = main_window.curve_widget

        # Navigate to frame 10 first
        main_window.timeline_controller.set_frame(10)
        qtbot.wait(50)
        assert curve_widget.current_frame == 10

        # Now select a point
        curve_widget._select_point(2, add_to_selection=False)  # Point at frame 10
        qtbot.wait(50)

        # Verify selection and frame are both correct
        assert 2 in curve_widget.selected_indices
        assert curve_widget.current_frame == 10

        # Navigate to another frame
        main_window.timeline_controller.set_frame(15)
        qtbot.wait(50)

        # Verify frame updated but selection preserved
        assert curve_widget.current_frame == 15
        assert 2 in curve_widget.selected_indices

        print("✓ Selection after frame navigation test passed!")
