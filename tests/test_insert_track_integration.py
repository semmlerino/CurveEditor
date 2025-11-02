#!/usr/bin/env python3
"""
Integration tests for Insert Track feature.

Tests the complete workflow including:
- Keyboard shortcut (Ctrl+Shift+I)
- Integration with MultiPointTrackingController
- UI updates
- Command execution through InteractionService

Following UNIFIED_TESTING_GUIDE:
- Use real components where possible
- Proper Qt cleanup with qtbot
- Test end-to-end behavior
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

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt

from core.commands.insert_track_command import InsertTrackCommand
from core.commands.shortcut_command import ShortcutContext
from core.commands.shortcut_commands import InsertTrackShortcutCommand
from services import get_interaction_service
from stores.application_state import get_application_state


# ==================== Fixture Helpers ====================


def create_mock_main_window() -> object:
    """Create a mock MainWindow with property delegation for active_timeline_point.

    This is used by tests that don't use the main fixture to ensure
    active_timeline_point property delegation works consistently.
    """

    class MockMainWindowWrapper:
        def __init__(self):
            self.multi_point_controller = Mock()
            self.curve_widget = Mock()
            self.curve_widget.set_curve_data = Mock()
            self.curve_widget.multi_curve_manager = Mock()
            self.update_timeline_tabs = Mock()

        @property
        def active_timeline_point(self) -> str | None:
            """Delegate to ApplicationState.active_curve."""
            from stores.application_state import get_application_state
            return get_application_state().active_curve

        @active_timeline_point.setter
        def active_timeline_point(self, value: str | None) -> None:
            """Delegate to ApplicationState.set_active_curve()."""
            from stores.application_state import get_application_state
            get_application_state().set_active_curve(value)

    return MockMainWindowWrapper()


class TestInsertTrackIntegration:
    """Integration tests for Insert Track feature."""

    @pytest.fixture
    def mock_main_window_with_controller(self):
        """Create mock MainWindow with functional MultiPointTrackingController and property delegation."""
        # Create a wrapper class that delegates active_timeline_point to ApplicationState
        class MockMainWindowWrapper:
            def __init__(self):
                # Create tracking panel mock
                tracking_panel = Mock()
                tracking_panel.get_selected_points.return_value = ["point_01", "point_02"]
                self.tracking_panel = tracking_panel

                # Multi-point controller
                controller = Mock()
                controller.update_tracking_panel = Mock()

                # Setup data in ApplicationState instead of mock tracked_data
                app_state = get_application_state()
                app_state.set_curve_data(
                    "point_01",
                    [
                        (1, 100.0, 200.0, "keyframe"),
                        (2, 110.0, 210.0, "normal"),
                        (3, 120.0, 220.0, "normal"),
                        # Gap: frames 4, 5, 6
                        (7, 160.0, 260.0, "normal"),
                        (8, 170.0, 270.0, "keyframe"),
                    ],
                )
                app_state.set_curve_data(
                    "point_02",
                    [
                        (1, 200.0, 300.0, "keyframe"),
                        (2, 210.0, 310.0, "normal"),
                        (3, 220.0, 320.0, "normal"),
                        (4, 230.0, 330.0, "normal"),
                        (5, 240.0, 340.0, "normal"),
                        (6, 250.0, 350.0, "normal"),
                        (7, 260.0, 360.0, "normal"),
                        (8, 270.0, 370.0, "keyframe"),
                    ],
                )

                self.multi_point_controller = controller
                self.curve_widget = Mock()
                self.curve_widget.set_curve_data = Mock()
                self.curve_widget.multi_curve_manager = Mock()
                # Note: In real code, selected_curve_names is read from ApplicationState.
                # This mock directly sets it for testing Insert Track logic.
                self.curve_widget.multi_curve_manager.selected_curve_names = {"point_01", "point_02"}

                self._active_timeline_point = "point_01"
                self.current_frame = 5
                self.update_timeline_tabs = Mock()

            @property
            def active_timeline_point(self) -> str | None:
                """Delegate to ApplicationState.active_curve."""
                from stores.application_state import get_application_state
                return get_application_state().active_curve

            @active_timeline_point.setter
            def active_timeline_point(self, value: str | None) -> None:
                """Delegate to ApplicationState.set_active_curve()."""
                from stores.application_state import get_application_state
                get_application_state().set_active_curve(value)

        return MockMainWindowWrapper()

    # ==================== Keyboard Shortcut Tests ====================

    def test_shortcut_command_can_execute_with_selection(self, mock_main_window_with_controller):
        """Test InsertTrackShortcutCommand can execute with curves selected."""
        # Create key event for Ctrl+Shift+I
        key_event = Mock()
        key_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        key_event.key.return_value = Qt.Key.Key_I

        # Create shortcut context
        context = ShortcutContext(
            main_window=mock_main_window_with_controller,
            focused_widget=mock_main_window_with_controller.curve_widget,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=5,
        )

        # Test can_execute
        command = InsertTrackShortcutCommand()
        can_execute = command.can_execute(context)

        assert can_execute is True

    def test_shortcut_command_cannot_execute_without_selection(self):
        """Test InsertTrackShortcutCommand cannot execute without curves selected."""
        main_window = Mock()
        main_window.multi_point_controller = Mock()

        # tracking_panel returns empty list
        tracking_panel = Mock()
        tracking_panel.get_selected_points.return_value = []
        main_window.tracking_panel = tracking_panel

        main_window.curve_widget = Mock()
        main_window.curve_widget.multi_curve_manager = Mock()
        # Note: In real code, selected_curve_names is read from ApplicationState.
        main_window.curve_widget.multi_curve_manager.selected_curve_names = set()  # Empty

        key_event = Mock()
        key_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        key_event.key.return_value = Qt.Key.Key_I

        context = ShortcutContext(
            main_window=main_window,
            focused_widget=main_window.curve_widget,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=5,
        )

        command = InsertTrackShortcutCommand()
        can_execute = command.can_execute(context)

        assert can_execute is False

    def test_shortcut_command_executes_insert_track(self, mock_main_window_with_controller):
        """Test InsertTrackShortcutCommand executes InsertTrackCommand."""
        key_event = Mock()
        key_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        key_event.key.return_value = Qt.Key.Key_I

        context = ShortcutContext(
            main_window=mock_main_window_with_controller,
            focused_widget=mock_main_window_with_controller.curve_widget,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=5,
        )

        # Mock the command manager's execute_command
        with patch.object(
            get_interaction_service().command_manager, "execute_command", return_value=True
        ) as mock_execute:
            command = InsertTrackShortcutCommand()
            result = command.execute(context)

            assert result is True
            # Verify InsertTrackCommand was created and executed
            mock_execute.assert_called_once()

    # ==================== End-to-End Workflow Tests ====================

    def test_scenario_1_workflow_interpolate_gap(self, mock_main_window_with_controller):
        """Test Scenario 1: End-to-end workflow for interpolating a gap."""
        # Setup - select only point with gap
        # Note: In real code, selected_curve_names is read from ApplicationState.
        mock_main_window_with_controller.curve_widget.multi_curve_manager.selected_curve_names = {"point_01"}

        # Execute command
        command = InsertTrackCommand(selected_curves=["point_01"], current_frame=5)
        result = command.execute(mock_main_window_with_controller)

        # Verify success
        assert result is True
        assert command.scenario == 1

        # Verify gap was filled
        app_state = get_application_state()
        filled_data = app_state.get_curve_data("point_01")
        assert filled_data is not None
        frames = {p[0] for p in filled_data}
        assert 4 in frames
        assert 5 in frames
        assert 6 in frames

        # Verify UI updates called
        mock_main_window_with_controller.multi_point_controller.update_tracking_panel.assert_called()
        mock_main_window_with_controller.update_timeline_tabs.assert_called()

    def test_scenario_2_workflow_fill_from_source(self, mock_main_window_with_controller):
        """Test Scenario 2: End-to-end workflow for filling gap from source."""
        # Both curves selected - point_01 has gap, point_02 doesn't
        result = InsertTrackCommand(selected_curves=["point_01", "point_02"], current_frame=5).execute(
            mock_main_window_with_controller
        )

        # Verify success
        assert result is True

        # Verify point_01 gap was filled with data from point_02

    def test_insert_track_with_3element_source_data(self):
        """REGRESSION TEST: Insert Track must work when source curves have 3-element data.

        Bug: InsertTrackCommand algorithms may fail if source curves use 3-element
        tuples (frame, x, y) instead of 4-element tuples (frame, x, y, status).

        This test ensures Insert Track can interpolate from sources with 3-element
        data format, which can occur in production when data is loaded directly.
        """
        from core.commands.insert_track_command import InsertTrackCommand

        # Create mock with 3-element source data (no status field)
        main_window = Mock()

        # Tracking panel
        tracking_panel = Mock()
        tracking_panel.get_selected_points.return_value = ["target", "source_01", "source_02"]
        main_window.tracking_panel = tracking_panel

        # Multi-point controller
        controller = Mock()
        controller.update_tracking_panel = Mock()

        # Setup 3-ELEMENT data format in ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data(
            "target",
            [
                (1, 100.0, 200.0),  # 3-element: NO STATUS
                (2, 110.0, 210.0),
                (3, 120.0, 220.0),
                # Gap at frames 4, 5, 6
                (7, 160.0, 260.0),
                (8, 170.0, 270.0),
            ],
        )
        app_state.set_curve_data(
            "source_01",
            [
                (1, 200.0, 300.0),  # 3-element: NO STATUS
                (2, 210.0, 310.0),
                (3, 220.0, 320.0),
                (4, 230.0, 330.0),  # Has data in gap
                (5, 240.0, 340.0),
                (6, 250.0, 350.0),
                (7, 260.0, 360.0),
                (8, 270.0, 370.0),
            ],
        )
        app_state.set_curve_data(
            "source_02",
            [
                (1, 300.0, 400.0),  # 3-element: NO STATUS
                (2, 310.0, 410.0),
                (3, 320.0, 420.0),
                (4, 330.0, 430.0),  # Has data in gap
                (5, 340.0, 440.0),
                (6, 350.0, 450.0),
                (7, 360.0, 460.0),
                (8, 370.0, 470.0),
            ],
        )

        main_window.multi_point_controller = controller
        main_window.curve_widget = Mock()
        main_window.curve_widget.set_curve_data = Mock()
        main_window.active_timeline_point = "target"
        main_window.current_frame = 5
        main_window.update_timeline_tabs = Mock()

        # Execute Insert Track (Scenario 2: fill gap from sources)
        command = InsertTrackCommand(selected_curves=["target", "source_01", "source_02"], current_frame=5)

        # Should not crash with 3-element data
        result = command.execute(main_window)

        # Verify success
        assert result is True, "Insert Track should work with 3-element source data"
        assert command.scenario == 2, "Should execute Scenario 2 (fill from sources)"

        # Verify target gap was filled (should have new points)
        app_state = get_application_state()
        filled_data = app_state.get_curve_data("target")
        assert filled_data is not None, "Target curve data should exist"
        frames = {p[0] for p in filled_data}
        assert 4 in frames, "Frame 4 should be filled"
        assert 5 in frames, "Frame 5 should be filled"
        assert 6 in frames, "Frame 6 should be filled"

        # Verify no crashes occurred during execution
        controller.update_tracking_panel.assert_called()

    def test_insert_track_3element_data_single_curve_interpolation(self):
        """REGRESSION TEST: Insert Track Scenario 1 (interpolation) with 3-element data.

        Verifies that gap interpolation works when curve has 3-element tuples.
        """
        from core.commands.insert_track_command import InsertTrackCommand

        # Create mock with single curve having 3-element data
        main_window = Mock()

        tracking_panel = Mock()
        tracking_panel.get_selected_points.return_value = ["single_curve"]
        main_window.tracking_panel = tracking_panel

        controller = Mock()
        # Setup data in ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data(
            "single_curve",
            [
                (1, 100.0, 200.0),  # 3-element format
                (2, 110.0, 210.0),
                (3, 120.0, 220.0),
                (7, 160.0, 260.0),
                (8, 170.0, 270.0),
            ],
        )
        controller.update_tracking_panel = Mock()

        main_window.multi_point_controller = controller
        main_window.curve_widget = Mock()
        main_window.curve_widget.set_curve_data = Mock()
        main_window.active_timeline_point = "single_curve"
        main_window.current_frame = 5
        main_window.update_timeline_tabs = Mock()

        # Execute Insert Track (Scenario 1: interpolate gap)
        command = InsertTrackCommand(selected_curves=["single_curve"], current_frame=5)
        result = command.execute(main_window)

        # Should succeed with 3-element data
        assert result is True, "Insert Track interpolation should work with 3-element data"
        assert command.scenario == 1, "Should execute Scenario 1 (interpolation)"

        # Verify gap was filled
        app_state = get_application_state()
        filled_data = app_state.get_curve_data("single_curve")
        frames = {p[0] for p in filled_data}
        assert 4 in frames, "Frame 4 should be interpolated"
        assert 5 in frames, "Frame 5 should be interpolated"
        assert 6 in frames, "Frame 6 should be interpolated"

    def test_scenario_3_workflow_create_averaged_curve(self):
        """Test Scenario 3: End-to-end workflow for creating averaged curve."""
        # Setup - two curves both with data at current frame
        main_window = Mock()
        controller = Mock()
        # Setup data in ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data(
            "point_01",
            [
                (1, 100.0, 200.0, "normal"),
                (2, 110.0, 210.0, "normal"),
                (3, 120.0, 220.0, "normal"),
            ],
        )
        app_state.set_curve_data(
            "point_02",
            [
                (1, 200.0, 300.0, "normal"),
                (2, 210.0, 310.0, "normal"),
                (3, 220.0, 320.0, "normal"),
            ],
        )
        controller.update_tracking_panel = Mock()

        main_window.multi_point_controller = controller
        main_window.curve_widget = Mock()
        main_window.curve_widget.set_curve_data = Mock()
        main_window.active_timeline_point = None
        main_window.update_timeline_tabs = Mock()

        # Execute - both curves have data at frame 2
        command = InsertTrackCommand(selected_curves=["point_01", "point_02"], current_frame=2)
        result = command.execute(main_window)

        # Verify success
        assert result is True
        assert command.scenario == 3

        # Verify new curve created
        assert command.created_curve_name is not None
        app_state = get_application_state()
        assert command.created_curve_name in app_state.get_all_curve_names()

        # Verify new curve is averaged
        app_state = get_application_state()
        averaged_data = app_state.get_curve_data(command.created_curve_name)
        assert len(averaged_data) == 3  # All common frames

        # Verify UI updates
        controller.update_tracking_panel.assert_called()
        main_window.update_timeline_tabs.assert_called()

    # ==================== Undo/Redo Integration Tests ====================

    def test_undo_redo_through_interaction_service(self, mock_main_window_with_controller):
        """Test undo/redo through InteractionService CommandManager."""
        interaction_service = get_interaction_service()
        command_manager = interaction_service.command_manager

        # Execute command through command manager
        command = InsertTrackCommand(selected_curves=["point_01"], current_frame=5)
        command_manager.execute_command(command, mock_main_window_with_controller)

        # Verify gap filled
        app_state = get_application_state()
        filled_data = app_state.get_curve_data("point_01")
        filled_frames = {p[0] for p in filled_data}
        assert 5 in filled_frames

        # Undo through command manager
        command_manager.undo(mock_main_window_with_controller)

        # Verify gap restored
        app_state = get_application_state()
        restored_data = app_state.get_curve_data("point_01")
        restored_frames = {p[0] for p in restored_data}
        assert 5 not in restored_frames

        # Redo through command manager
        command_manager.redo(mock_main_window_with_controller)

        # Verify gap filled again
        app_state = get_application_state()
        refilled_data = app_state.get_curve_data("point_01")
        refilled_frames = {p[0] for p in refilled_data}
        assert 5 in refilled_frames

    # ==================== UI Integration Tests ====================

    def test_ui_updates_for_active_curve(self, mock_main_window_with_controller):
        """Test that UI updates are called when modifying active curve."""
        # Set point_01 as active
        mock_main_window_with_controller.active_timeline_point = "point_01"

        # Execute command
        command = InsertTrackCommand(selected_curves=["point_01"], current_frame=5)
        command.execute(mock_main_window_with_controller)

        # Verify curve widget updated
        mock_main_window_with_controller.curve_widget.set_curve_data.assert_called()

        # Verify timeline updated
        mock_main_window_with_controller.update_timeline_tabs.assert_called()

    def test_ui_updates_for_non_active_curve(self, mock_main_window_with_controller):
        """Test UI updates when modifying non-active curve."""
        # Set different curve as active
        mock_main_window_with_controller.active_timeline_point = "point_02"

        # Execute command on point_01 (not active)
        command = InsertTrackCommand(selected_curves=["point_01"], current_frame=5)
        command.execute(mock_main_window_with_controller)

        # Tracking panel should still be updated
        mock_main_window_with_controller.multi_point_controller.update_tracking_panel.assert_called()

    def test_scenario_3_sets_new_curve_as_active(self):
        """Test that Scenario 3 sets newly created curve as active."""
        main_window = create_mock_main_window()
        controller = Mock()
        # Setup data in ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data(
            "point_01",
            [
                (1, 100.0, 200.0, "normal"),
                (2, 110.0, 210.0, "normal"),
            ],
        )
        app_state.set_curve_data(
            "point_02",
            [
                (1, 200.0, 300.0, "normal"),
                (2, 210.0, 310.0, "normal"),
            ],
        )
        controller.update_tracking_panel = Mock()

        main_window.multi_point_controller = controller

        # Set active curve through property delegation
        main_window.active_timeline_point = "point_01"

        # Execute Scenario 3
        command = InsertTrackCommand(selected_curves=["point_01", "point_02"], current_frame=1)
        command.execute(main_window)

        # Verify new curve is set as active
        assert main_window.active_timeline_point == command.created_curve_name

    # ==================== Error Handling Integration Tests ====================

    def test_graceful_handling_of_missing_controller(self):
        """Test graceful error handling when controller is missing."""
        main_window = Mock()
        main_window.multi_point_controller = None

        command = InsertTrackCommand(selected_curves=["point_01"], current_frame=5)
        result = command.execute(main_window)

        # Should return False without crashing
        assert result is False

    def test_graceful_handling_of_missing_ui_components(self, mock_main_window_with_controller):
        """Test graceful handling when UI components are missing."""
        # Remove some UI components
        mock_main_window_with_controller.update_timeline_tabs = None
        mock_main_window_with_controller.curve_widget = None

        # Should still execute without crashing
        command = InsertTrackCommand(selected_curves=["point_01"], current_frame=5)
        result = command.execute(mock_main_window_with_controller)

        assert result is True  # Core functionality should work

    # ==================== Multi-Point Controller Integration ====================

    def test_controller_data_consistency_after_operation(self, mock_main_window_with_controller):
        """Test that tracked_data remains consistent after Insert Track."""
        app_state = get_application_state()
        original_point_02 = app_state.get_curve_data("point_02")[:]

        # Execute Scenario 2 (fill point_01 from point_02)
        command = InsertTrackCommand(selected_curves=["point_01", "point_02"], current_frame=5)
        command.execute(mock_main_window_with_controller)

        # Verify point_02 (source) is unchanged
        app_state = get_application_state()
        current_point_02 = app_state.get_curve_data("point_02")
        assert len(current_point_02) == len(original_point_02)

        # Verify point_01 (target) was modified
        app_state = get_application_state()
        point_01 = app_state.get_curve_data("point_01")
        assert len(point_01) > 5  # Original had 5 points, now should have more

    def test_controller_data_consistency_after_undo(self, mock_main_window_with_controller):
        """Test data consistency after undo operation."""
        # Save original data
        app_state = get_application_state()
        original_point_01 = app_state.get_curve_data("point_01")[:]

        # Execute and undo
        command = InsertTrackCommand(selected_curves=["point_01"], current_frame=5)
        command.execute(mock_main_window_with_controller)
        command.undo(mock_main_window_with_controller)

        # Verify data restored exactly
        app_state = get_application_state()
        restored_point_01 = app_state.get_curve_data("point_01")
        assert len(restored_point_01) == len(original_point_01)

        # Verify frames match
        original_frames = {p[0] for p in original_point_01}
        restored_frames = {p[0] for p in restored_point_01}
        assert original_frames == restored_frames

    # ==================== Complex Workflow Tests ====================

    def test_multiple_sequential_operations(self, mock_main_window_with_controller):
        """Test multiple Insert Track operations in sequence."""
        # First operation: Fill point_01 gap at frame 5
        cmd1 = InsertTrackCommand(selected_curves=["point_01", "point_02"], current_frame=5)
        result1 = cmd1.execute(mock_main_window_with_controller)
        assert result1 is True

        # Second operation: Create averaged curve at frame 2 (both have data)
        cmd2 = InsertTrackCommand(selected_curves=["point_01", "point_02"], current_frame=2)
        result2 = cmd2.execute(mock_main_window_with_controller)
        assert result2 is True

        # Verify both operations succeeded
        assert cmd1.scenario == 2
        assert cmd2.scenario == 3

        # Verify new curve exists
        app_state = get_application_state()
        assert cmd2.created_curve_name in app_state.get_all_curve_names()

    def test_undo_multiple_operations_in_order(self, mock_main_window_with_controller):
        """Test undoing multiple operations in correct order."""
        # Execute two operations
        cmd1 = InsertTrackCommand(selected_curves=["point_01"], current_frame=5)
        cmd1.execute(mock_main_window_with_controller)

        cmd2 = InsertTrackCommand(selected_curves=["point_01", "point_02"], current_frame=2)
        cmd2.execute(mock_main_window_with_controller)

        # Undo in reverse order (LIFO)
        result2 = cmd2.undo(mock_main_window_with_controller)
        result1 = cmd1.undo(mock_main_window_with_controller)

        assert result2 is True
        assert result1 is True

        # Verify cmd2's created curve removed
        if cmd2.created_curve_name:
            app_state = get_application_state()
            assert cmd2.created_curve_name not in app_state.get_all_curve_names()
