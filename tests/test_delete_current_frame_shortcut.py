#!/usr/bin/env python
"""
Tests for Ctrl+R delete current frame keyframe shortcut.
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

from core.commands.shortcut_command import ShortcutContext
from core.commands.shortcut_commands import DeleteCurrentFrameKeyframeCommand


class TestDeleteCurrentFrameKeyframeShortcut:
    """Test the Ctrl+R shortcut for converting keyframe to interpolated point."""

    def test_shortcut_key_sequence(self):
        """Test that the command has the correct key sequence."""
        command = DeleteCurrentFrameKeyframeCommand()
        assert command.key_sequence == "Ctrl+R"
        assert command.description == "Convert keyframe to interpolated point"

    def test_can_execute_with_point_at_current_frame(self, main_window_with_data):
        """Test that command can execute when there's a point at current frame."""
        main_window = main_window_with_data
        command = DeleteCurrentFrameKeyframeCommand()

        # Set current frame to frame 1 (which has a point)
        main_window.current_frame = 1

        # Create key event
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)

        # Create context
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=1,
        )

        # Should be able to execute
        assert command.can_execute(context)

    def test_cannot_execute_without_point_at_current_frame(self, main_window_with_data):
        """Test that command cannot execute when there's no point at current frame."""
        main_window = main_window_with_data
        command = DeleteCurrentFrameKeyframeCommand()

        # Set current frame to frame 999 (no point at this frame)
        main_window.current_frame = 999

        # Create key event
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)

        # Create context
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=999,
        )

        # Should NOT be able to execute
        assert not command.can_execute(context)

    def test_execute_converts_point_to_interpolated(self, main_window_with_data):
        """Test that executing the command converts the point to interpolated."""
        main_window = main_window_with_data
        command = DeleteCurrentFrameKeyframeCommand()

        # Get initial curve data
        initial_data = list(main_window.curve_widget.curve_data)
        initial_count = len(initial_data)

        # Set current frame to frame 2 (which has a point between frames 1 and 3)
        main_window.current_frame = 2

        # Verify frame 2 exists
        frame_2_point = None
        for p in initial_data:
            if p[0] == 2:
                frame_2_point = p
                break
        assert frame_2_point is not None, "Frame 2 should exist in initial data"

        # Create key event
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)

        # Create context
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=2,
        )

        # Execute the command
        success = command.execute(context)
        assert success, "Command should execute successfully"

        # Verify the point still exists but is now interpolated
        new_data = list(main_window.curve_widget.curve_data)
        assert len(new_data) == initial_count, "Should have same number of points"

        # Find frame 2 in new data
        new_frame_2 = None
        for p in new_data:
            if p[0] == 2:
                new_frame_2 = p
                break

        assert new_frame_2 is not None, "Frame 2 should still exist"
        assert new_frame_2[3] == "interpolated", "Frame 2 should have interpolated status"

        # Verify coordinates were interpolated (should be between frame 1 and frame 3)
        frame_1 = next(p for p in initial_data if p[0] == 1)
        frame_3 = next(p for p in initial_data if p[0] == 3)

        # Linear interpolation: frame 2 is halfway between frames 1 and 3
        expected_x = (frame_1[1] + frame_3[1]) / 2
        expected_y = (frame_1[2] + frame_3[2]) / 2

        assert abs(new_frame_2[1] - expected_x) < 0.01, "X coordinate should be interpolated"
        assert abs(new_frame_2[2] - expected_y) < 0.01, "Y coordinate should be interpolated"

    def test_shortcut_is_registered_in_main_window(self, main_window_with_data):
        """Test that Ctrl+R is properly registered in the main window."""
        main_window = main_window_with_data

        # Check that the shortcut is in the registry
        shortcuts = main_window.shortcut_registry.list_shortcuts()
        assert "Ctrl+R" in shortcuts, "Ctrl+R should be registered"
        assert shortcuts["Ctrl+R"] == "Convert keyframe to interpolated point"

    def test_shortcut_supports_undo(self, main_window_with_data):
        """Test that converting with Ctrl+R can be undone."""
        from services import get_interaction_service

        main_window = main_window_with_data
        command = DeleteCurrentFrameKeyframeCommand()

        # Get initial curve data and frame 2 point
        initial_data = list(main_window.curve_widget.curve_data)
        initial_frame_2 = next(p for p in initial_data if p[0] == 2)

        # Set current frame to frame 2
        main_window.current_frame = 2

        # Create key event and context
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
        context = ShortcutContext(
            main_window=main_window,
            focused_widget=None,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=2,
        )

        # Execute the convert command
        success = command.execute(context)
        assert success, "Convert command should succeed"

        # Verify point was converted to interpolated
        after_convert = list(main_window.curve_widget.curve_data)
        converted_frame_2 = next(p for p in after_convert if p[0] == 2)
        assert converted_frame_2[3] == "interpolated", "Should be interpolated"

        # Undo the conversion
        interaction_service = get_interaction_service()
        undo_success = interaction_service.command_manager.undo(main_window)
        assert undo_success, "Undo should succeed"

        # Verify point was restored to original state
        after_undo = list(main_window.curve_widget.curve_data)
        restored_frame_2 = next(p for p in after_undo if p[0] == 2)
        assert restored_frame_2 == initial_frame_2, "Point should be fully restored"
        assert restored_frame_2[3] == "keyframe", "Status should be restored to keyframe"


@pytest.fixture
def main_window_with_data(qapp, qtbot):
    """Create a main window with some test curve data."""
    from unittest.mock import patch

    from ui.file_operations import FileOperations
    from ui.main_window import MainWindow

    with patch.object(FileOperations, "load_burger_data_async"):
        main_window = MainWindow()
        qtbot.addWidget(main_window)

        # Add some test curve data
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "keyframe"),
            (3, 120.0, 120.0, "keyframe"),
            (5, 140.0, 140.0, "keyframe"),
        ]

        if main_window.curve_widget is not None:
            main_window.curve_widget.set_curve_data(test_data)
            main_window.current_frame = 1

        return main_window
