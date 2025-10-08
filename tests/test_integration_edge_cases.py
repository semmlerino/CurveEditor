#!/usr/bin/env python
"""
Integration and edge case tests for recent features.

Tests critical scenarios:
1. CompositeCommand rollback on partial failure
2. Undo/redo composite command integrity
3. Single point conversion edge cases
4. Shortcut conflict resolution (Ctrl+Shift+R)
5. Mixed-status nudge with undo
6. Workflow: convert→nudge→undo
"""

from typing import cast
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from core.commands.base_command import CompositeCommand
from core.commands.curve_commands import (
    BatchMoveCommand,
)
from core.commands.shortcut_command import ShortcutContext
from core.commands.shortcut_commands import DeleteCurrentFrameKeyframeCommand
from core.models import PointStatus
from core.type_aliases import PointTuple4Str
from services import get_interaction_service
from stores.application_state import get_application_state


class TestCompositeCommandRollback:
    """Test CompositeCommand rollback behavior on partial failures."""

    def test_rollback_on_second_command_failure(self, main_window_with_data, qtbot):
        """If second command fails, first command should be rolled back."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget

        # Setup initial data
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "keyframe"),
        ]
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", initial_data)
        app_state.set_active_curve("test_curve")
        curve_widget.set_curve_data(initial_data)

        # Create a composite command with a failing second command
        composite = CompositeCommand(description="Test rollback")

        # First command: move point (should succeed)
        move_cmd = BatchMoveCommand(
            description="Move point",
            moves=[(0, (100.0, 100.0), (105.0, 105.0))],
        )
        composite.add_command(move_cmd)

        # Second command: Mock that will fail
        failing_cmd = Mock()
        failing_cmd.execute.return_value = False  # Simulate failure
        failing_cmd.undo.return_value = True
        failing_cmd.executed = False
        composite.add_command(failing_cmd)

        # Execute composite - should fail and rollback
        success = composite.execute(main_window)

        # Verify composite failed
        assert not success, "Composite should fail when second command fails"

        # Verify first command was rolled back
        current_data = list(curve_widget.curve_data)
        assert current_data[0][1] == 100.0, "X should be rolled back to original"
        assert current_data[0][2] == 100.0, "Y should be rolled back to original"

        # Verify undo was called on the first command
        assert not move_cmd.executed, "Move command should be marked as not executed after rollback"

    def test_rollback_on_exception(self, main_window_with_data, qtbot):
        """If command throws exception, previous commands should be rolled back."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget

        # Setup initial data
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "keyframe"),
        ]
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", initial_data)
        app_state.set_active_curve("test_curve")
        curve_widget.set_curve_data(initial_data)

        # Create composite command
        composite = CompositeCommand(description="Test exception rollback")

        # First command: move point (should succeed)
        move_cmd = BatchMoveCommand(
            description="Move point",
            moves=[(0, (100.0, 100.0), (105.0, 105.0))],
        )
        composite.add_command(move_cmd)

        # Second command: Mock that raises exception
        failing_cmd = Mock()
        failing_cmd.execute.side_effect = RuntimeError("Simulated error")
        failing_cmd.undo.return_value = True
        failing_cmd.executed = False
        composite.add_command(failing_cmd)

        # Execute composite - should catch exception and rollback
        success = composite.execute(main_window)

        # Verify composite failed
        assert not success, "Composite should fail when command raises exception"

        # Verify first command was rolled back
        current_data = list(curve_widget.curve_data)
        assert current_data[0][1] == 100.0, "X should be rolled back after exception"
        assert current_data[0][2] == 100.0, "Y should be rolled back after exception"


class TestCompositeCommandUndo:
    """Test undo/redo integrity for CompositeCommand."""

    def test_undo_restores_both_position_and_status(self, main_window_with_data, qtbot):
        """Undo after nudge should restore BOTH position and status atomically."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget
        interaction_service = get_interaction_service()

        # Setup: interpolated point
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),  # Will be nudged
            (3, 120.0, 120.0, "keyframe"),
        ]
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", initial_data)
        app_state.set_active_curve("test_curve")
        curve_widget.set_curve_data(initial_data)

        # Select the interpolated point
        app_state.set_selection("test_curve", {1})

        # Nudge the point (should move AND change status to keyframe)
        curve_widget.nudge_selected(5.0, 5.0)

        # Verify changes in ApplicationState (commands update app_state)
        after_nudge = list(app_state.get_curve_data("test_curve"))
        assert after_nudge[1][1] == 115.0, "X should be moved"
        assert after_nudge[1][2] == 115.0, "Y should be moved"
        assert cast(PointTuple4Str, after_nudge[1])[3] == PointStatus.KEYFRAME.value, "Status should be keyframe"

        # Undo
        undo_success = interaction_service.command_manager.undo(main_window)
        assert undo_success, "Undo should succeed"

        # Verify BOTH position and status restored in ApplicationState
        after_undo = list(app_state.get_curve_data("test_curve"))
        assert after_undo[1][1] == 110.0, "X should be restored"
        assert after_undo[1][2] == 110.0, "Y should be restored"
        assert cast(PointTuple4Str, after_undo[1])[3] == "interpolated", "Status should be restored to interpolated"

    def test_redo_after_undo(self, main_window_with_data, qtbot):
        """Redo after undo should restore both move and status change."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget
        interaction_service = get_interaction_service()

        # Setup
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
        ]
        # Set active curve first so set_curve_data uses it
        app_state = get_application_state()
        app_state.set_active_curve("__default__")

        # Use widget.set_curve_data which syncs to ApplicationState "__default__" curve
        # This ensures commands operate on the same curve that the widget reads from
        curve_widget.set_curve_data(initial_data)

        # Select and nudge
        app_state.set_selection("__default__", {1})
        curve_widget.nudge_selected(5.0, 5.0)

        # Undo
        interaction_service.command_manager.undo(main_window)

        # Redo
        redo_success = interaction_service.command_manager.redo(main_window)
        assert redo_success, "Redo should succeed"

        # Verify both move and status restored
        after_redo = list(curve_widget.curve_data)
        assert after_redo[1][1] == 115.0, "X should be moved again"
        assert after_redo[1][2] == 115.0, "Y should be moved again"
        assert after_redo[1][3] == PointStatus.KEYFRAME.value, "Status should be keyframe again"


class TestConvertToInterpolatedEdgeCases:
    """Test edge cases for Ctrl+R convert to interpolated."""

    def test_convert_single_point_curve(self, main_window_with_data, qtbot):
        """Converting the only point in a curve should keep its position."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget

        # Single point
        initial_data = [(5, 100.0, 200.0, "keyframe")]
        # Use widget.set_curve_data which syncs to ApplicationState "__default__" curve
        curve_widget.set_curve_data(initial_data)
        main_window.current_frame = 5

        # Create command and execute
        command = DeleteCurrentFrameKeyframeCommand()
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=5,
        )

        success = command.execute(context)
        assert success, "Should succeed even with single point"

        # Verify: position unchanged (no boundaries to interpolate from)
        result = list(curve_widget.curve_data)
        assert result[0][0] == 5, "Frame should be unchanged"
        assert result[0][1] == 100.0, "X should be unchanged (no interpolation boundaries)"
        assert result[0][2] == 200.0, "Y should be unchanged (no interpolation boundaries)"
        assert result[0][3] == PointStatus.INTERPOLATED.value, "Status should be interpolated"

    def test_convert_first_point_no_previous(self, main_window_with_data, qtbot):
        """Converting first point should use next point's boundary."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget

        # First point at frame 1, second at frame 5
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 200.0, 200.0, "keyframe"),
        ]
        # Use widget.set_curve_data which syncs to ApplicationState "__default__" curve
        curve_widget.set_curve_data(initial_data)
        main_window.current_frame = 1

        # Execute convert
        command = DeleteCurrentFrameKeyframeCommand()
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=1,
        )

        success = command.execute(context)
        assert success, "Should succeed"

        # Verify: uses next boundary position (no previous boundary)
        result = list(curve_widget.curve_data)
        assert result[0][3] == PointStatus.INTERPOLATED.value, "Status should be interpolated"
        # Should use next keyframe's position since no previous
        assert result[0][1] == 200.0, "Should use next boundary X"
        assert result[0][2] == 200.0, "Should use next boundary Y"

    def test_convert_last_point_no_next(self, main_window_with_data, qtbot):
        """Converting last point should use previous point's boundary."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget

        # Two points: frame 1 and frame 5 (converting frame 5)
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 200.0, 200.0, "keyframe"),
        ]
        # Use widget.set_curve_data which syncs to ApplicationState "__default__" curve
        curve_widget.set_curve_data(initial_data)
        main_window.current_frame = 5

        # Execute convert
        command = DeleteCurrentFrameKeyframeCommand()
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=5,
        )

        success = command.execute(context)
        assert success, "Should succeed"

        # Verify: uses previous boundary position (no next boundary)
        result = list(curve_widget.curve_data)
        assert result[1][3] == PointStatus.INTERPOLATED.value, "Status should be interpolated"
        # Should use previous keyframe's position since no next
        assert result[1][1] == 100.0, "Should use previous boundary X"
        assert result[1][2] == 100.0, "Should use previous boundary Y"

    def test_convert_with_both_boundaries(self, main_window_with_data, qtbot):
        """Converting middle point should interpolate between boundaries."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget

        # Three points: converting middle one
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "keyframe"),  # Will convert this
            (10, 200.0, 200.0, "keyframe"),
        ]
        # Use widget.set_curve_data which syncs to ApplicationState "__default__" curve
        curve_widget.set_curve_data(initial_data)
        main_window.current_frame = 5

        # Execute convert
        command = DeleteCurrentFrameKeyframeCommand()
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=5,
        )

        success = command.execute(context)
        assert success, "Should succeed"

        # Verify: linear interpolation
        result = list(curve_widget.curve_data)
        assert result[1][3] == PointStatus.INTERPOLATED.value, "Status should be interpolated"

        # Frame 5 is 4/9 of the way from frame 1 to frame 10
        # Expected X = 100 + (200-100) * 4/9 = 100 + 44.444... ≈ 144.44
        expected_x = 100.0 + (200.0 - 100.0) * (5 - 1) / (10 - 1)
        expected_y = 100.0 + (200.0 - 100.0) * (5 - 1) / (10 - 1)

        assert abs(result[1][1] - expected_x) < 0.01, f"X should be interpolated to ~{expected_x}"
        assert abs(result[1][2] - expected_y) < 0.01, f"Y should be interpolated to ~{expected_y}"


class TestShortcutConflictResolution:
    """Test that Ctrl+Shift+R now triggers reset view (conflict resolved)."""

    def test_ctrl_shift_r_triggers_reset_view(self, main_window_with_data, qtbot):
        """Verify Ctrl+Shift+R triggers reset view action."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget

        # Modify view state
        curve_widget.zoom_factor = 2.0
        curve_widget.pan_offset_x = 100.0
        curve_widget.pan_offset_y = 50.0

        # Trigger the action (simulating Ctrl+Shift+R)
        main_window.action_reset_view.trigger()

        # Verify view was reset
        assert curve_widget.zoom_factor == 1.0, "Zoom should be reset to 1.0"
        assert curve_widget.pan_offset_x == 0.0, "Pan X should be reset to 0"
        assert curve_widget.pan_offset_y == 0.0, "Pan Y should be reset to 0"

    def test_ctrl_r_does_not_reset_view(self, main_window_with_data, qtbot):
        """Verify Ctrl+R no longer triggers reset view (now converts to interpolated)."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget

        # Setup data
        initial_data = [(5, 100.0, 100.0, "keyframe")]
        # Use widget.set_curve_data which syncs to ApplicationState "__default__" curve
        curve_widget.set_curve_data(initial_data)
        main_window.current_frame = 5

        # Modify view state
        curve_widget.zoom_factor = 2.0
        curve_widget.pan_offset_x = 100.0

        # Execute Ctrl+R (should convert point, NOT reset view)
        command = DeleteCurrentFrameKeyframeCommand()
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=5,
        )

        command.execute(context)

        # Verify view state unchanged
        assert curve_widget.zoom_factor == 2.0, "Zoom should NOT be reset"
        assert curve_widget.pan_offset_x == 100.0, "Pan should NOT be reset"

        # Verify point was converted (not view reset)
        result = list(curve_widget.curve_data)
        assert result[0][3] == PointStatus.INTERPOLATED.value, "Point should be converted"


class TestMixedStatusNudgeUndo:
    """Test nudging selection with mixed statuses."""

    def test_nudge_mixed_status_selection(self, main_window_with_data, qtbot):
        """Nudge selection with keyframes + interpolated points."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget

        # Mixed status points
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),  # Already keyframe
            (2, 110.0, 110.0, "interpolated"),  # Will convert
            (3, 120.0, 120.0, "normal"),  # Will convert
        ]
        # Set active curve first so set_curve_data uses it
        app_state = get_application_state()
        app_state.set_active_curve("__default__")

        # Use widget.set_curve_data which syncs to ApplicationState "__default__" curve
        curve_widget.set_curve_data(initial_data)

        # Select all points
        app_state.set_selection("__default__", {0, 1, 2})

        # Nudge all
        curve_widget.nudge_selected(5.0, 5.0)

        # Verify all moved
        result = list(curve_widget.curve_data)
        assert result[0][1] == 105.0 and result[0][2] == 105.0, "Point 0 should move"
        assert result[1][1] == 115.0 and result[1][2] == 115.0, "Point 1 should move"
        assert result[2][1] == 125.0 and result[2][2] == 125.0, "Point 2 should move"

        # Verify all are now keyframes
        assert result[0][3] == PointStatus.KEYFRAME.value, "Point 0 should stay keyframe"
        assert result[1][3] == PointStatus.KEYFRAME.value, "Point 1 should become keyframe"
        assert result[2][3] == PointStatus.KEYFRAME.value, "Point 2 should become keyframe"

    def test_mixed_status_nudge_undo(self, main_window_with_data, qtbot):
        """Undo after mixed-status nudge should restore all statuses correctly."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget
        interaction_service = get_interaction_service()

        # Mixed status
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "normal"),
        ]
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", initial_data)
        app_state.set_active_curve("test_curve")
        curve_widget.set_curve_data(initial_data)

        # Select and nudge all
        app_state.set_selection("test_curve", {0, 1, 2})
        curve_widget.nudge_selected(5.0, 5.0)

        # Undo
        undo_success = interaction_service.command_manager.undo(main_window)
        assert undo_success, "Undo should succeed"

        # Verify all restored to original positions AND statuses
        result = list(curve_widget.curve_data)
        assert result[0] == (1, 100.0, 100.0, "keyframe"), "Point 0 fully restored"
        assert result[1] == (2, 110.0, 110.0, "interpolated"), "Point 1 fully restored"
        assert result[2] == (3, 120.0, 120.0, "normal"), "Point 2 fully restored"


class TestWorkflowConvertNudgeUndo:
    """Test realistic workflow: convert→nudge→undo."""

    def test_convert_then_nudge_then_undo_both(self, main_window_with_data, qtbot):
        """Workflow: Ctrl+R to interpolated, nudge (becomes keyframe), undo both."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget
        interaction_service = get_interaction_service()

        # Setup
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "keyframe"),  # Will convert this
            (10, 200.0, 200.0, "keyframe"),
        ]
        # Set active curve first so set_curve_data uses it
        app_state = get_application_state()
        app_state.set_active_curve("__default__")

        # Use widget.set_curve_data which syncs to ApplicationState "__default__" curve
        curve_widget.set_curve_data(initial_data)
        main_window.current_frame = 5

        # Step 1: Convert to interpolated (Ctrl+R)
        convert_cmd = DeleteCurrentFrameKeyframeCommand()
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=5,
        )
        convert_cmd.execute(context)

        # Verify converted
        after_convert = list(curve_widget.curve_data)
        assert after_convert[1][3] == PointStatus.INTERPOLATED.value, "Should be interpolated"

        # Step 2: Nudge (should convert back to keyframe)
        app_state.set_selection("__default__", {1})
        curve_widget.nudge_selected(10.0, 10.0)

        # Verify nudged and converted to keyframe
        after_nudge = list(curve_widget.curve_data)
        assert after_nudge[1][3] == PointStatus.KEYFRAME.value, "Should be keyframe after nudge"
        original_x_after_convert = after_convert[1][1]
        original_y_after_convert = after_convert[1][2]
        assert after_nudge[1][1] == original_x_after_convert + 10.0, "X should be nudged"
        assert after_nudge[1][2] == original_y_after_convert + 10.0, "Y should be nudged"

        # Step 3: Undo nudge (should restore interpolated status and position)
        undo1 = interaction_service.command_manager.undo(main_window)
        assert undo1, "First undo should succeed"

        after_undo1 = list(curve_widget.curve_data)
        assert after_undo1[1][3] == PointStatus.INTERPOLATED.value, "Should be interpolated again"
        assert abs(after_undo1[1][1] - original_x_after_convert) < 0.01, "X should be restored"
        assert abs(after_undo1[1][2] - original_y_after_convert) < 0.01, "Y should be restored"

        # Step 4: Undo convert (should restore original keyframe)
        undo2 = interaction_service.command_manager.undo(main_window)
        assert undo2, "Second undo should succeed"

        after_undo2 = list(curve_widget.curve_data)
        assert after_undo2[1] == (5, 150.0, 150.0, "keyframe"), "Should be fully restored to original"

    def test_redo_convert_and_nudge(self, main_window_with_data, qtbot):
        """After undoing convert and nudge, redo should restore both operations."""
        main_window = main_window_with_data
        curve_widget = main_window.curve_widget
        interaction_service = get_interaction_service()

        # Setup
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "keyframe"),
            (10, 200.0, 200.0, "keyframe"),
        ]
        # Set active curve first so set_curve_data uses it
        app_state = get_application_state()
        app_state.set_active_curve("__default__")

        # Use widget.set_curve_data which syncs to ApplicationState "__default__" curve
        curve_widget.set_curve_data(initial_data)
        main_window.current_frame = 5

        # Convert + nudge
        convert_cmd = DeleteCurrentFrameKeyframeCommand()
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=5,
        )
        convert_cmd.execute(context)

        after_convert = list(curve_widget.curve_data)
        converted_x = after_convert[1][1]
        converted_y = after_convert[1][2]

        app_state.set_selection("__default__", {1})
        curve_widget.nudge_selected(10.0, 10.0)

        # Undo both
        interaction_service.command_manager.undo(main_window)
        interaction_service.command_manager.undo(main_window)

        # Redo convert
        redo1 = interaction_service.command_manager.redo(main_window)
        assert redo1, "First redo should succeed"
        after_redo1 = list(curve_widget.curve_data)
        assert after_redo1[1][3] == PointStatus.INTERPOLATED.value, "Should be interpolated again"

        # Redo nudge
        redo2 = interaction_service.command_manager.redo(main_window)
        assert redo2, "Second redo should succeed"
        after_redo2 = list(curve_widget.curve_data)
        assert after_redo2[1][3] == PointStatus.KEYFRAME.value, "Should be keyframe again"
        assert after_redo2[1][1] == converted_x + 10.0, "X should be nudged again"
        assert after_redo2[1][2] == converted_y + 10.0, "Y should be nudged again"


@pytest.fixture
def main_window_with_data(qapp, qtbot):
    """Create a main window with proper cleanup."""
    from ui.file_operations import FileOperations
    from ui.main_window import MainWindow

    with patch.object(FileOperations, "load_burger_data_async"):
        main_window = MainWindow()
        qtbot.addWidget(main_window)
        main_window.current_frame = 1
        return main_window
