#!/usr/bin/env python3
"""
Comprehensive tests for all keyboard shortcut commands.

This test module provides complete coverage of all ShortcutCommand subclasses,
testing both can_execute() and execute() methods for each command.
Follows the Protocol Testing Rule: Every method in abstract/Protocol classes must be tested.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QPixmap
from PySide6.QtWidgets import QWidget

from core.commands.shortcut_command import ShortcutContext
from core.commands.shortcut_commands import (
    CenterViewCommand,
    DeletePointsCommand,
    DeselectAllCommand,
    FitBackgroundCommand,
    NudgePointsCommand,
    RedoCommand,
    SelectAllCommand,
    SetEndframeCommand,
    SetTrackingDirectionCommand,
    UndoCommand,
)
from core.models import PointStatus, TrackingDirection


@pytest.fixture
def mock_main_window():
    """Create a mock main window with proper structure."""
    window = Mock()
    window.curve_widget = Mock()
    window.tracking_panel = Mock()
    window.action_undo = Mock()
    window.action_redo = Mock()

    # Set up curve widget defaults
    window.curve_widget.curve_data = []
    window.curve_widget._curve_store = Mock()
    window.curve_widget.background_image = None
    window.curve_widget.centering_mode = False

    # Set up tracking panel defaults
    window.tracking_panel.get_visible_points.return_value = []

    # Set up action defaults
    window.action_undo.isEnabled.return_value = False
    window.action_redo.isEnabled.return_value = False

    return window


@pytest.fixture
def mock_key_event():
    """Create a mock key event."""
    event = Mock(spec=QKeyEvent)
    event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
    event.key.return_value = Qt.Key.Key_E
    return event


@pytest.fixture
def basic_context(mock_main_window, mock_key_event):
    """Create a basic shortcut context."""
    return ShortcutContext(
        main_window=mock_main_window,
        focused_widget=None,
        key_event=mock_key_event,
        selected_curve_points=set(),
        selected_tracking_points=[],
        current_frame=None,
    )


class TestShortcutContext:
    """Test ShortcutContext dataclass functionality."""

    def test_context_creation(self, mock_main_window, mock_key_event, qtbot):
        """Test ShortcutContext creation with all parameters."""
        # Create widget with proper cleanup
        widget = QWidget()
        qtbot.addWidget(widget)

        context = ShortcutContext(
            main_window=mock_main_window,
            focused_widget=widget,
            key_event=mock_key_event,
            selected_curve_points={1, 2, 3},
            selected_tracking_points=["Point_1", "Point_2"],
            current_frame=42,
        )

        assert context.main_window is mock_main_window
        assert isinstance(context.focused_widget, QWidget)
        assert context.key_event is mock_key_event
        assert context.selected_curve_points == {1, 2, 3}
        assert context.selected_tracking_points == ["Point_1", "Point_2"]
        assert context.current_frame == 42

    def test_has_curve_selection_property(self, basic_context):
        """Test has_curve_selection property."""
        # Empty selection
        assert not basic_context.has_curve_selection

        # With selection
        basic_context.selected_curve_points = {1, 2}
        assert basic_context.has_curve_selection

    def test_has_tracking_selection_property(self, basic_context):
        """Test has_tracking_selection property."""
        # Empty selection
        assert not basic_context.has_tracking_selection

        # With selection
        basic_context.selected_tracking_points = ["Point_1"]
        assert basic_context.has_tracking_selection

    def test_widget_type_property(self, basic_context, qtbot):
        """Test widget_type property."""
        # No focused widget
        assert basic_context.widget_type == "None"

        # With focused widget
        widget = QWidget()
        qtbot.addWidget(widget)
        basic_context.focused_widget = widget
        assert basic_context.widget_type == "QWidget"


class TestSetEndframeCommand:
    """Test SetEndframeCommand functionality."""

    def test_command_initialization(self):
        """Test command initialization."""
        cmd = SetEndframeCommand()
        assert cmd.key_sequence == "E"
        assert cmd.description == "Toggle between keyframe and end frame"

    def test_can_execute_with_modifiers(self, basic_context):
        """Test can_execute returns False with modifiers."""
        cmd = SetEndframeCommand()

        # With Shift modifier
        basic_context.key_event.modifiers.return_value = Qt.KeyboardModifier.ShiftModifier
        assert not cmd.can_execute(basic_context)

    def test_can_execute_requires_current_frame(self, basic_context):
        """Test can_execute requires current frame (frame-based operation)."""
        cmd = SetEndframeCommand()
        # Selection is ignored for frame-based operations
        basic_context.selected_curve_points = {1, 2}
        basic_context.current_frame = None

        # Should fail without current_frame, even with selection
        assert not cmd.can_execute(basic_context)

    def test_can_execute_with_current_frame(self, basic_context):
        """Test can_execute with current frame and point."""
        cmd = SetEndframeCommand()
        basic_context.current_frame = 1  # Frame 1 -> index 0
        basic_context.main_window.curve_widget.curve_data = [(1, 100, 100, PointStatus.NORMAL.value)]

        assert cmd.can_execute(basic_context)

    def test_can_execute_no_valid_conditions(self, basic_context):
        """Test can_execute returns False with no valid conditions."""
        cmd = SetEndframeCommand()

        # No selection, no current frame
        assert not cmd.can_execute(basic_context)

    @patch("services.get_interaction_service")
    @patch("core.commands.curve_commands.SetPointStatusCommand")
    def test_execute_with_current_frame(self, mock_command_class, mock_service, basic_context):
        """Test execute with current frame (frame-based operation)."""
        cmd = SetEndframeCommand()
        # Set current frame to 1
        basic_context.current_frame = 1
        # Set curve data with point at frame 1 (index 0)
        basic_context.main_window.curve_widget.curve_data = [(1, 100, 100, PointStatus.NORMAL.value)]

        # Set up mock curve store to return the point at current frame
        mock_store = basic_context.main_window.curve_widget._curve_store
        mock_store.get_point.return_value = (1, 100, 100, PointStatus.NORMAL.value)

        # Set up mock interaction service
        mock_interaction = Mock()
        mock_interaction.command_manager.execute_command.return_value = True
        mock_service.return_value = mock_interaction

        # Set up mock command
        mock_command_instance = Mock()
        mock_command_class.return_value = mock_command_instance

        result = cmd.execute(basic_context)

        assert result is True
        # Verify command was created with the point at current frame
        mock_command_class.assert_called_once()
        mock_interaction.command_manager.execute_command.assert_called_once()

    def test_execute_no_curve_widget(self, basic_context):
        """Test execute returns False with no curve widget."""
        cmd = SetEndframeCommand()
        basic_context.main_window.curve_widget = None

        result = cmd.execute(basic_context)
        assert result is False


class TestSetTrackingDirectionCommand:
    """Test SetTrackingDirectionCommand functionality."""

    def test_command_initialization(self):
        """Test command initialization."""
        cmd = SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW, "Shift+1")
        assert cmd.key_sequence == "Shift+1"
        assert cmd.direction == TrackingDirection.TRACKING_FW
        assert "Set tracking direction to forward" in cmd.description

    def test_can_execute_no_tracking_panel(self, basic_context):
        """Test can_execute returns False with no tracking panel."""
        cmd = SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW, "Shift+1")
        basic_context.main_window.tracking_panel = None

        assert not cmd.can_execute(basic_context)

    def test_can_execute_with_shift_modifier(self, basic_context):
        """Test can_execute with Shift modifier and tracking points."""
        cmd = SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW, "Shift+1")
        basic_context.key_event.modifiers.return_value = Qt.KeyboardModifier.ShiftModifier
        basic_context.selected_tracking_points = ["Point_1"]

        assert cmd.can_execute(basic_context)

    def test_can_execute_with_symbol_key(self, basic_context):
        """Test can_execute with symbol key (shifted number)."""
        cmd = SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW, "!")
        basic_context.key_event.key.return_value = Qt.Key.Key_Exclam
        basic_context.main_window.tracking_panel.get_visible_points.return_value = ["Point_1"]

        assert cmd.can_execute(basic_context)

    def test_execute_with_selected_points(self, basic_context):
        """Test execute with selected tracking points."""
        cmd = SetTrackingDirectionCommand(TrackingDirection.TRACKING_FW, "Shift+1")
        basic_context.selected_tracking_points = ["Point_1", "Point_2"]

        # Set up mock tracking panel
        mock_panel = basic_context.main_window.tracking_panel
        mock_panel._set_direction_for_points = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_panel._set_direction_for_points.assert_called_once_with(
            ["Point_1", "Point_2"], TrackingDirection.TRACKING_FW
        )

    def test_execute_no_selection_uses_visible(self, basic_context):
        """Test execute uses visible points when none selected."""
        cmd = SetTrackingDirectionCommand(TrackingDirection.TRACKING_BW, "Shift+2")

        # Set up visible points but no selection
        mock_panel = basic_context.main_window.tracking_panel
        mock_panel.get_visible_points.return_value = ["Point_1", "Point_2"]
        mock_panel._set_direction_for_points = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_panel._set_direction_for_points.assert_called_once_with(
            ["Point_1", "Point_2"], TrackingDirection.TRACKING_BW
        )


class TestDeletePointsCommand:
    """Test DeletePointsCommand functionality."""

    def test_command_initialization(self):
        """Test command initialization."""
        cmd = DeletePointsCommand()
        assert cmd.key_sequence == "Delete"
        assert cmd.description == "Delete selected points"

    def test_can_execute_with_curve_selection(self, basic_context):
        """Test can_execute with curve selection."""
        cmd = DeletePointsCommand()
        basic_context.selected_curve_points = {1, 2}

        assert cmd.can_execute(basic_context)

    def test_can_execute_with_tracking_selection(self, basic_context):
        """Test can_execute with tracking selection."""
        cmd = DeletePointsCommand()
        basic_context.selected_tracking_points = ["Point_1"]

        assert cmd.can_execute(basic_context)

    def test_can_execute_no_selection(self, basic_context):
        """Test can_execute returns False with no selection."""
        cmd = DeletePointsCommand()

        assert not cmd.can_execute(basic_context)

    def test_execute_curve_points(self, basic_context):
        """Test execute with curve points."""
        cmd = DeletePointsCommand()
        basic_context.selected_curve_points = {1, 2}

        # Set up mock curve widget
        mock_widget = basic_context.main_window.curve_widget
        mock_widget.delete_selected_points = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_widget.delete_selected_points.assert_called_once()

    def test_execute_tracking_points(self, basic_context):
        """Test execute with tracking points."""
        cmd = DeletePointsCommand()
        basic_context.selected_tracking_points = ["Point_1", "Point_2"]

        # Set up mock tracking panel
        mock_panel = basic_context.main_window.tracking_panel
        mock_panel._delete_points = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_panel._delete_points.assert_called_once_with(["Point_1", "Point_2"])


class TestCenterViewCommand:
    """Test CenterViewCommand functionality."""

    def test_command_initialization(self):
        """Test command initialization."""
        cmd = CenterViewCommand()
        assert cmd.key_sequence == "C"
        assert cmd.description == "Center view on selection"

    def test_can_execute_with_modifiers(self, basic_context):
        """Test can_execute returns False with modifiers."""
        cmd = CenterViewCommand()
        basic_context.key_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        assert not cmd.can_execute(basic_context)

    def test_can_execute_with_curve_widget(self, basic_context):
        """Test can_execute with curve widget."""
        cmd = CenterViewCommand()

        assert cmd.can_execute(basic_context)

    def test_can_execute_no_curve_widget(self, basic_context):
        """Test can_execute returns False with no curve widget."""
        cmd = CenterViewCommand()
        basic_context.main_window.curve_widget = None

        assert not cmd.can_execute(basic_context)

    def test_execute_toggle_centering_with_selection(self, basic_context):
        """Test execute toggles centering and centers on selection."""
        cmd = CenterViewCommand()
        basic_context.selected_curve_points = {1, 2}

        # Set up mock curve widget
        mock_widget = basic_context.main_window.curve_widget
        mock_widget.centering_mode = False
        mock_widget.center_on_selection = Mock()
        mock_widget.update_status = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        assert mock_widget.centering_mode is True
        mock_widget.center_on_selection.assert_called_once()
        mock_widget.update_status.assert_called_once()

    def test_execute_toggle_centering_with_frame(self, basic_context):
        """Test execute centers on current frame when no selection."""
        cmd = CenterViewCommand()
        basic_context.current_frame = 42

        # Set up mock curve widget
        mock_widget = basic_context.main_window.curve_widget
        mock_widget.centering_mode = False
        mock_widget.center_on_frame = Mock()
        mock_widget.update_status = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        assert mock_widget.centering_mode is True
        mock_widget.center_on_frame.assert_called_once_with(42)


class TestSelectAllCommand:
    """Test SelectAllCommand functionality."""

    def test_command_initialization(self):
        """Test command initialization."""
        cmd = SelectAllCommand()
        assert cmd.key_sequence == "Ctrl+A"
        assert cmd.description == "Select all points"

    def test_can_execute_with_curve_widget(self, basic_context):
        """Test can_execute with curve widget."""
        cmd = SelectAllCommand()

        assert cmd.can_execute(basic_context)

    def test_can_execute_no_curve_widget(self, basic_context):
        """Test can_execute returns False with no curve widget."""
        cmd = SelectAllCommand()
        basic_context.main_window.curve_widget = None

        assert not cmd.can_execute(basic_context)

    def test_execute_select_all(self, basic_context):
        """Test execute calls select_all."""
        cmd = SelectAllCommand()

        # Set up mock curve widget
        mock_widget = basic_context.main_window.curve_widget
        mock_widget.select_all = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_widget.select_all.assert_called_once()


class TestDeselectAllCommand:
    """Test DeselectAllCommand functionality."""

    def test_command_initialization(self):
        """Test command initialization."""
        cmd = DeselectAllCommand()
        assert cmd.key_sequence == "Escape"
        assert cmd.description == "Deselect all points"

    def test_can_execute_with_selection(self, basic_context):
        """Test can_execute with curve selection."""
        cmd = DeselectAllCommand()
        basic_context.selected_curve_points = {1, 2}

        assert cmd.can_execute(basic_context)

    def test_can_execute_no_selection(self, basic_context):
        """Test can_execute returns False with no selection."""
        cmd = DeselectAllCommand()

        assert not cmd.can_execute(basic_context)

    def test_execute_clear_selection(self, basic_context):
        """Test execute calls clear_selection."""
        cmd = DeselectAllCommand()
        basic_context.selected_curve_points = {1, 2}

        # Set up mock curve widget
        mock_widget = basic_context.main_window.curve_widget
        mock_widget.clear_selection = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_widget.clear_selection.assert_called_once()


class TestFitBackgroundCommand:
    """Test FitBackgroundCommand functionality."""

    def test_command_initialization(self):
        """Test command initialization."""
        cmd = FitBackgroundCommand()
        assert cmd.key_sequence == "F"
        assert cmd.description == "Fit background image to view"

    def test_can_execute_with_modifiers(self, basic_context):
        """Test can_execute returns False with modifiers."""
        cmd = FitBackgroundCommand()
        basic_context.key_event.modifiers.return_value = Qt.KeyboardModifier.AltModifier

        assert not cmd.can_execute(basic_context)

    def test_can_execute_with_background_image(self, basic_context, qapp):
        """Test can_execute with background image."""
        cmd = FitBackgroundCommand()

        # Set up mock curve widget with background image
        mock_widget = basic_context.main_window.curve_widget
        mock_widget.background_image = QPixmap(100, 100)

        assert cmd.can_execute(basic_context)

    def test_can_execute_no_background_image(self, basic_context):
        """Test can_execute returns False with no background image."""
        cmd = FitBackgroundCommand()
        basic_context.main_window.curve_widget.background_image = None

        assert not cmd.can_execute(basic_context)

    def test_execute_fit_background(self, basic_context, qapp):
        """Test execute calls fit_to_background_image."""
        cmd = FitBackgroundCommand()

        # Set up mock curve widget
        mock_widget = basic_context.main_window.curve_widget
        mock_widget.background_image = QPixmap(100, 100)
        mock_widget.fit_to_background_image = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_widget.fit_to_background_image.assert_called_once()


class TestNudgePointsCommand:
    """Test NudgePointsCommand functionality."""

    def test_command_initialization(self):
        """Test command initialization with different directions."""
        # Left nudge
        cmd_left = NudgePointsCommand("4", -1.0, 0.0)
        assert cmd_left.key_sequence == "4"
        assert "left" in cmd_left.description
        assert cmd_left.base_dx == -1.0
        assert cmd_left.base_dy == 0.0

        # Right nudge
        cmd_right = NudgePointsCommand("6", 1.0, 0.0)
        assert "right" in cmd_right.description

        # Up nudge
        cmd_up = NudgePointsCommand("8", 0.0, -1.0)
        assert "up" in cmd_up.description

        # Down nudge
        cmd_down = NudgePointsCommand("2", 0.0, 1.0)
        assert "down" in cmd_down.description

    def test_can_execute_with_selection(self, basic_context):
        """Test can_execute with curve selection."""
        cmd = NudgePointsCommand("2", 0.0, 1.0)
        basic_context.selected_curve_points = {1, 2}

        assert cmd.can_execute(basic_context)

    def test_can_execute_with_current_frame(self, basic_context):
        """Test can_execute with current frame and point."""
        cmd = NudgePointsCommand("4", -1.0, 0.0)
        basic_context.current_frame = 1
        basic_context.main_window.curve_widget.curve_data = [(1, 100, 100, PointStatus.NORMAL.value)]

        assert cmd.can_execute(basic_context)

    def test_can_execute_no_valid_conditions(self, basic_context):
        """Test can_execute returns False with no valid conditions."""
        cmd = NudgePointsCommand("6", 1.0, 0.0)

        assert not cmd.can_execute(basic_context)

    @patch("ui.ui_constants.DEFAULT_NUDGE_AMOUNT", 1.0)
    def test_execute_nudge_selected_points(self, basic_context):
        """Test execute nudges selected points."""
        cmd = NudgePointsCommand("2", 0.0, 1.0)
        basic_context.selected_curve_points = {1, 2}

        # Set up mock curve widget
        mock_widget = basic_context.main_window.curve_widget
        mock_widget.nudge_selected = Mock()
        mock_widget.update = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_widget.nudge_selected.assert_called_once_with(0.0, 1.0)  # base_dx * 1.0, base_dy * 1.0
        mock_widget.update.assert_called_once()

    @patch("ui.ui_constants.DEFAULT_NUDGE_AMOUNT", 1.0)
    def test_execute_nudge_with_shift_modifier(self, basic_context):
        """Test execute with Shift modifier (10x nudge)."""
        cmd = NudgePointsCommand("4", -1.0, 0.0)
        basic_context.selected_curve_points = {1}
        basic_context.key_event.modifiers.return_value = Qt.KeyboardModifier.ShiftModifier

        # Set up mock curve widget
        mock_widget = basic_context.main_window.curve_widget
        mock_widget.nudge_selected = Mock()
        mock_widget.update = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_widget.nudge_selected.assert_called_once_with(-10.0, 0.0)  # -1.0 * 10.0

    @patch("ui.ui_constants.DEFAULT_NUDGE_AMOUNT", 1.0)
    def test_execute_nudge_with_ctrl_modifier(self, basic_context):
        """Test execute with Ctrl modifier (0.1x nudge)."""
        cmd = NudgePointsCommand("6", 1.0, 0.0)
        basic_context.selected_curve_points = {1}
        basic_context.key_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        # Set up mock curve widget
        mock_widget = basic_context.main_window.curve_widget
        mock_widget.nudge_selected = Mock()
        mock_widget.update = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_widget.nudge_selected.assert_called_once_with(0.1, 0.0)  # 1.0 * 0.1


class TestUndoCommand:
    """Test UndoCommand functionality."""

    def test_command_initialization(self):
        """Test command initialization."""
        cmd = UndoCommand()
        assert cmd.key_sequence == "Ctrl+Z"
        assert cmd.description == "Undo last action"

    def test_can_execute_with_enabled_action(self, basic_context):
        """Test can_execute when undo action is enabled."""
        cmd = UndoCommand()
        basic_context.main_window.action_undo.isEnabled.return_value = True

        assert cmd.can_execute(basic_context)

    def test_can_execute_with_disabled_action(self, basic_context):
        """Test can_execute returns False when undo action is disabled."""
        cmd = UndoCommand()
        basic_context.main_window.action_undo.isEnabled.return_value = False

        assert not cmd.can_execute(basic_context)

    def test_can_execute_no_action(self, basic_context):
        """Test can_execute returns False with no undo action."""
        cmd = UndoCommand()
        basic_context.main_window.action_undo = None

        assert not cmd.can_execute(basic_context)

    def test_execute_trigger_undo(self, basic_context):
        """Test execute triggers undo action."""
        cmd = UndoCommand()

        # Set up mock action
        mock_action = basic_context.main_window.action_undo
        mock_action.trigger = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_action.trigger.assert_called_once()

    def test_execute_no_action(self, basic_context):
        """Test execute returns False with no action."""
        cmd = UndoCommand()
        basic_context.main_window.action_undo = None

        result = cmd.execute(basic_context)
        assert result is False


class TestRedoCommand:
    """Test RedoCommand functionality."""

    def test_command_initialization(self):
        """Test command initialization."""
        cmd = RedoCommand()
        assert cmd.key_sequence == "Ctrl+Y"
        assert cmd.description == "Redo last action"

    def test_can_execute_with_enabled_action(self, basic_context):
        """Test can_execute when redo action is enabled."""
        cmd = RedoCommand()
        basic_context.main_window.action_redo.isEnabled.return_value = True

        assert cmd.can_execute(basic_context)

    def test_can_execute_with_disabled_action(self, basic_context):
        """Test can_execute returns False when redo action is disabled."""
        cmd = RedoCommand()
        basic_context.main_window.action_redo.isEnabled.return_value = False

        assert not cmd.can_execute(basic_context)

    def test_execute_trigger_redo(self, basic_context):
        """Test execute triggers redo action."""
        cmd = RedoCommand()

        # Set up mock action
        mock_action = basic_context.main_window.action_redo
        mock_action.trigger = Mock()

        result = cmd.execute(basic_context)

        assert result is True
        mock_action.trigger.assert_called_once()


class TestShortcutCommandAbstractMethods:
    """Test that all ShortcutCommand abstract methods are properly implemented."""

    def test_all_commands_implement_abstract_methods(self):
        """Test that all command classes implement required abstract methods."""
        command_classes = [
            SetEndframeCommand,
            SetTrackingDirectionCommand,
            DeletePointsCommand,
            CenterViewCommand,
            SelectAllCommand,
            DeselectAllCommand,
            FitBackgroundCommand,
            NudgePointsCommand,
            UndoCommand,
            RedoCommand,
        ]

        for cls in command_classes:
            # Test that we can instantiate the class (abstract methods are implemented)
            if cls == SetTrackingDirectionCommand:
                # Requires special arguments
                cmd = cls(TrackingDirection.TRACKING_FW, "Shift+1")
            elif cls == NudgePointsCommand:
                # Requires special arguments
                cmd = cls("2", 0.0, 1.0)
            else:
                cmd = cls()

            # Verify abstract methods exist and are callable
            assert hasattr(cmd, "can_execute")
            assert callable(cmd.can_execute)
            assert hasattr(cmd, "execute")
            assert callable(cmd.execute)

            # Verify properties
            assert hasattr(cmd, "key_sequence")
            assert isinstance(cmd.key_sequence, str)
            assert hasattr(cmd, "description")
            assert isinstance(cmd.description, str)

    def test_command_log_execution_method(self, basic_context):
        """Test log_execution method works for all commands."""
        cmd = SetEndframeCommand()

        # Should not raise exception
        cmd.log_execution(basic_context, True)
        cmd.log_execution(basic_context, False)
