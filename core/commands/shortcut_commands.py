#!/usr/bin/env python
"""
Concrete implementations of keyboard shortcut commands.

This module provides specific shortcut command implementations for all
keyboard shortcuts in the application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

if TYPE_CHECKING:
    from core.models import TrackingDirection

from core.commands.shortcut_command import ShortcutCommand, ShortcutContext
from core.logger_utils import get_logger
from core.models import PointStatus, TrackingDirection

logger = get_logger("shortcut_commands")


class SetEndframeCommand(ShortcutCommand):
    """Command to toggle between KEYFRAME and ENDFRAME status for selected points."""

    def __init__(self) -> None:
        """Initialize the endframe toggle command."""
        super().__init__("E", "Toggle between keyframe and end frame")

    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can toggle endframe status.

        Can execute if:
        - There are selected curve points, OR
        - There's a current frame with a point at that position
        """
        # No modifiers should be pressed
        modifiers = context.key_event.modifiers()
        clean_modifiers = modifiers & ~Qt.KeyboardModifier.KeypadModifier
        if clean_modifiers != Qt.KeyboardModifier.NoModifier:
            return False

        # Can execute if we have selected points
        if context.has_curve_selection:
            return True

        # Or if we have a current frame with a point
        if context.current_frame is not None:
            curve_widget = context.main_window.curve_widget
            if curve_widget:
                frame_index = context.current_frame - 1
                if 0 <= frame_index < len(curve_widget.curve_data):
                    return True

        return False

    def execute(self, context: ShortcutContext) -> bool:
        """Execute the endframe toggle command."""
        curve_widget = context.main_window.curve_widget
        if not curve_widget:
            return False

        try:
            if context.has_curve_selection:
                # Toggle status for selected points
                toggled_count = 0
                endframe_count = 0
                keyframe_count = 0

                for idx in context.selected_curve_points:
                    # Get current point status
                    point = curve_widget._curve_store.get_point(idx)
                    if point and len(point) >= 4:
                        current_status = point[3]

                        # Toggle logic
                        if current_status == PointStatus.ENDFRAME.value:
                            new_status = PointStatus.KEYFRAME.value
                            keyframe_count += 1
                        else:
                            new_status = PointStatus.ENDFRAME.value
                            endframe_count += 1

                        curve_widget._curve_store.set_point_status(idx, new_status)
                        toggled_count += 1

                if toggled_count > 0:
                    # Instead of directly modifying, create a command for undo/redo
                    from core.commands import SetPointStatusCommand
                    from services import get_interaction_service

                    # Already applied the changes, now record them for undo/redo
                    interaction_service = get_interaction_service()
                    if interaction_service and hasattr(interaction_service, "command_manager"):
                        # The changes have already been applied above
                        # We need to reverse engineer what was changed
                        changes = []
                        for idx in context.selected_curve_points:
                            point = curve_widget._curve_store.get_point(idx)
                            if point and len(point) >= 4:
                                current_status = point[3]
                                # Determine what the old status was based on what we changed to
                                if current_status == PointStatus.ENDFRAME.value:
                                    old_status = PointStatus.KEYFRAME.value
                                else:
                                    old_status = PointStatus.ENDFRAME.value
                                changes.append((idx, old_status, current_status))

                        if changes:
                            # Build description based on what was changed
                            if endframe_count > 0 and keyframe_count > 0:
                                desc = f"Toggle {toggled_count} points"
                            elif endframe_count > 0:
                                desc = f"Set {endframe_count} points to ENDFRAME"
                            else:
                                desc = f"Set {keyframe_count} points to KEYFRAME"

                            command = SetPointStatusCommand(
                                description=desc,
                                changes=changes,
                            )
                            # Mark as already executed since we already applied the changes
                            command.executed = True
                            # Add to history
                            cm = interaction_service.command_manager
                            cm._history.append(command)
                            cm._current_index = len(cm._history) - 1
                            cm._enforce_history_limit()
                            cm._update_ui_state(context.main_window)

                    curve_widget.update()

                    # Create informative status message
                    if endframe_count > 0 and keyframe_count > 0:
                        msg = f"Toggled {toggled_count} points ({endframe_count} to ENDFRAME, {keyframe_count} to KEYFRAME)"
                    elif endframe_count > 0:
                        msg = f"Set {endframe_count} points to ENDFRAME"
                    else:
                        msg = f"Set {keyframe_count} points to KEYFRAME"

                    curve_widget.update_status(msg, 2000)
                    logger.info(msg)
                    return True

            elif context.current_frame is not None:
                # Toggle point at current frame
                frame_index = context.current_frame - 1
                if 0 <= frame_index < len(curve_widget.curve_data):
                    point = curve_widget._curve_store.get_point(frame_index)
                    if point and len(point) >= 4:
                        current_status = point[3]

                        # Toggle logic
                        if current_status == PointStatus.ENDFRAME.value:
                            new_status = PointStatus.KEYFRAME.value
                            status_text = "KEYFRAME"
                        else:
                            new_status = PointStatus.ENDFRAME.value
                            status_text = "ENDFRAME"

                        curve_widget._curve_store.set_point_status(frame_index, new_status)

                        # Create command for undo/redo
                        from core.commands import SetPointStatusCommand
                        from services import get_interaction_service

                        interaction_service = get_interaction_service()
                        if interaction_service and hasattr(interaction_service, "command_manager"):
                            old_status = current_status
                            command = SetPointStatusCommand(
                                description=msg,
                                changes=[(frame_index, old_status, new_status)],
                            )
                            # Mark as already executed since we already applied the change
                            command.executed = True
                            # Add to history
                            cm = interaction_service.command_manager
                            cm._history.append(command)
                            cm._current_index = len(cm._history) - 1
                            cm._enforce_history_limit()
                            cm._update_ui_state(context.main_window)

                        curve_widget.update()

                        msg = f"Set frame {context.current_frame} to {status_text}"
                        curve_widget.update_status(msg, 2000)
                        logger.info(msg)
                        return True

        except Exception as e:
            logger.error(f"Failed to toggle endframe status: {e}")

        return False


class SetTrackingDirectionCommand(ShortcutCommand):
    """Command to set tracking direction for selected tracking points."""

    def __init__(self, direction: TrackingDirection, key_sequence: str) -> None:
        """Initialize the tracking direction command.

        Args:
            direction: The tracking direction to set
            key_sequence: The key sequence that triggers this command
        """
        self.direction = direction
        description = f"Set tracking direction to {direction.value}"
        super().__init__(key_sequence, description)

    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can set tracking direction.

        Can execute if:
        - Shift modifier is pressed (for Shift+number keys), OR
        - Key is a symbol key (!, @) that represents a shifted number
        - There are tracking points (selected or visible)
        """
        modifiers = context.key_event.modifiers()
        key = context.key_event.key()

        # Check if tracking panel exists and has points
        tracking_panel = context.main_window.tracking_panel
        if not tracking_panel:
            return False

        # Can execute if there are selected points OR any visible points
        selected_points = context.selected_tracking_points
        visible_points = tracking_panel.get_visible_points()
        has_points = bool(selected_points) or bool(visible_points)

        # Allow if Shift modifier is pressed (traditional Shift+1, Shift+2, Shift+F3)
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            return has_points

        # Allow if key is a symbol that represents a shifted number (!, ", @)
        symbol_keys = {Qt.Key.Key_Exclam, Qt.Key.Key_QuoteDbl, Qt.Key.Key_At}  # !, ", @
        if key in symbol_keys:
            return has_points
        return False

    def execute(self, context: ShortcutContext) -> bool:
        """Execute the tracking direction command."""
        tracking_panel = context.main_window.tracking_panel
        if not tracking_panel:
            return False

        try:
            selected_points = context.selected_tracking_points

            # If no points are selected, select all visible points for global operation
            if not selected_points:
                visible_points = tracking_panel.get_visible_points()
                if not visible_points:
                    logger.warning("No visible tracking points to set direction for")
                    return False

                selected_points = visible_points
                logger.info(f"No points selected, applying to all {len(selected_points)} visible points")

            logger.info(f"Setting {len(selected_points)} points to {self.direction.value}")

            # Use the panel's internal method to set direction
            tracking_panel._set_direction_for_points(selected_points, self.direction)
            return True

        except Exception as e:
            logger.error(f"Failed to set tracking direction: {e}")
            return False


class DeletePointsCommand(ShortcutCommand):
    """Command to delete selected points."""

    def __init__(self) -> None:
        """Initialize the delete command."""
        super().__init__("Delete", "Delete selected points")

    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can delete points.

        Can execute if there are selected curve or tracking points.
        """
        return context.has_curve_selection or context.has_tracking_selection

    def execute(self, context: ShortcutContext) -> bool:
        """Execute the delete command."""
        success = False

        # Delete curve points if selected
        if context.has_curve_selection:
            curve_widget = context.main_window.curve_widget
            if curve_widget:
                try:
                    curve_widget.delete_selected_points()
                    success = True
                except Exception as e:
                    logger.error(f"Failed to delete curve points: {e}")

        # Delete tracking points if selected
        if context.has_tracking_selection:
            tracking_panel = context.main_window.tracking_panel
            if tracking_panel:
                try:
                    tracking_panel._delete_points(context.selected_tracking_points)
                    success = True
                except Exception as e:
                    logger.error(f"Failed to delete tracking points: {e}")

        return success


class CenterViewCommand(ShortcutCommand):
    """Command to center view on selection or current frame."""

    def __init__(self) -> None:
        """Initialize the center view command."""
        super().__init__("C", "Center view on selection")

    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can center the view.

        Can execute if:
        - No modifiers are pressed
        - Curve widget has focus or is available
        """
        # No modifiers should be pressed
        modifiers = context.key_event.modifiers()
        clean_modifiers = modifiers & ~Qt.KeyboardModifier.KeypadModifier
        if clean_modifiers != Qt.KeyboardModifier.NoModifier:
            return False

        # Need curve widget
        return context.main_window.curve_widget is not None

    def execute(self, context: ShortcutContext) -> bool:
        """Execute the center view command."""
        curve_widget = context.main_window.curve_widget
        if not curve_widget:
            return False

        try:
            # Toggle centering mode
            curve_widget.centering_mode = not curve_widget.centering_mode
            logger.info(f"Centering mode {'enabled' if curve_widget.centering_mode else 'disabled'}")

            # If enabling, immediately center
            if curve_widget.centering_mode:
                if context.has_curve_selection:
                    curve_widget.center_on_selection()
                elif context.current_frame is not None:
                    curve_widget.center_on_frame(context.current_frame)

            # Update status
            status_msg = "Centering: ON" if curve_widget.centering_mode else "Centering: OFF"
            curve_widget.update_status(status_msg, 2000)
            return True

        except Exception as e:
            logger.error(f"Failed to toggle centering: {e}")
            return False


class SelectAllCommand(ShortcutCommand):
    """Command to select all points."""

    def __init__(self) -> None:
        """Initialize the select all command."""
        super().__init__("Ctrl+A", "Select all points")

    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can select all.

        Can execute if curve widget is available.
        """
        return context.main_window.curve_widget is not None

    def execute(self, context: ShortcutContext) -> bool:
        """Execute the select all command."""
        curve_widget = context.main_window.curve_widget
        if not curve_widget:
            return False

        try:
            curve_widget.select_all()
            return True
        except Exception as e:
            logger.error(f"Failed to select all: {e}")
            return False


class DeselectAllCommand(ShortcutCommand):
    """Command to deselect all points."""

    def __init__(self) -> None:
        """Initialize the deselect command."""
        super().__init__("Escape", "Deselect all points")

    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can deselect all.

        Can execute if there are selected points.
        """
        return context.has_curve_selection

    def execute(self, context: ShortcutContext) -> bool:
        """Execute the deselect command."""
        curve_widget = context.main_window.curve_widget
        if not curve_widget:
            return False

        try:
            curve_widget.clear_selection()
            return True
        except Exception as e:
            logger.error(f"Failed to clear selection: {e}")
            return False


class FitBackgroundCommand(ShortcutCommand):
    """Command to fit background image to view."""

    def __init__(self) -> None:
        """Initialize the fit background command."""
        super().__init__("F", "Fit background image to view")

    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can fit background.

        Can execute if:
        - No modifiers are pressed
        - Curve widget exists and has a background image
        """
        # No modifiers should be pressed
        modifiers = context.key_event.modifiers()
        clean_modifiers = modifiers & ~Qt.KeyboardModifier.KeypadModifier
        if clean_modifiers != Qt.KeyboardModifier.NoModifier:
            return False

        # Need curve widget with background image
        curve_widget = context.main_window.curve_widget
        return curve_widget is not None and curve_widget.background_image is not None

    def execute(self, context: ShortcutContext) -> bool:
        """Execute the fit background command."""
        curve_widget = context.main_window.curve_widget
        if not curve_widget or not curve_widget.background_image:
            return False

        try:
            curve_widget.fit_to_background_image()
            logger.info("Fitted background image to view")
            return True
        except Exception as e:
            logger.error(f"Failed to fit background: {e}")
            return False


class NudgePointsCommand(ShortcutCommand):
    """Command to nudge selected points with arrow keys."""

    def __init__(self, key: str, dx: float, dy: float) -> None:
        """Initialize the nudge command.

        Args:
            key: The key sequence (e.g., "2", "4", "6", "8")
            dx: X direction nudge amount
            dy: Y direction nudge amount
        """
        self.base_dx = dx
        self.base_dy = dy
        direction = ""
        if dx < 0:
            direction = "left"
        elif dx > 0:
            direction = "right"
        elif dy < 0:
            direction = "up"
        elif dy > 0:
            direction = "down"
        super().__init__(key, f"Nudge points {direction}")

    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can nudge points.

        Can execute if:
        - There are selected curve points, OR
        - There's a current frame with a point at that position
        """
        # Can execute if we have selected points
        if context.has_curve_selection:
            return True

        # Or if we have a current frame with a point
        if context.current_frame is not None:
            curve_widget = context.main_window.curve_widget
            if curve_widget:
                frame_index = context.current_frame - 1
                if 0 <= frame_index < len(curve_widget.curve_data):
                    return True

        return False

    def execute(self, context: ShortcutContext) -> bool:
        """Execute the nudge command."""
        curve_widget = context.main_window.curve_widget
        if not curve_widget:
            return False

        try:
            # Calculate nudge amount based on modifiers
            from ui.ui_constants import DEFAULT_NUDGE_AMOUNT

            modifiers = context.key_event.modifiers()
            clean_modifiers = modifiers & ~Qt.KeyboardModifier.KeypadModifier

            nudge_amount = DEFAULT_NUDGE_AMOUNT
            if clean_modifiers & Qt.KeyboardModifier.ShiftModifier:
                nudge_amount = 10.0
            elif clean_modifiers & Qt.KeyboardModifier.ControlModifier:
                nudge_amount = 0.1

            dx = self.base_dx * nudge_amount
            dy = self.base_dy * nudge_amount

            # Nudge selected points or current frame point
            if context.has_curve_selection:
                logger.info(f"Nudging {len(context.selected_curve_points)} selected points by ({dx}, {dy})")
                curve_widget.nudge_selected(dx, dy)
            elif context.current_frame is not None:
                frame_index = context.current_frame - 1
                if 0 <= frame_index < len(curve_widget.curve_data):
                    logger.info(f"Nudging point at frame {context.current_frame} by ({dx}, {dy})")
                    # Temporarily select the point, nudge it, then clear
                    curve_widget._select_point(frame_index, add_to_selection=False)
                    curve_widget.nudge_selected(dx, dy)
                    curve_widget.clear_selection()

            curve_widget.update()
            return True

        except Exception as e:
            logger.error(f"Failed to nudge points: {e}")
            return False


class UndoCommand(ShortcutCommand):
    """Command to undo the last action."""

    def __init__(self) -> None:
        """Initialize the undo command."""
        super().__init__("Ctrl+Z", "Undo last action")

    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can undo.

        Can execute if there's an action to undo.
        """
        # Check if we have undo available
        if context.main_window and context.main_window.action_undo:
            return context.main_window.action_undo.isEnabled()
        return False

    def execute(self, context: ShortcutContext) -> bool:
        """Execute the undo command."""
        if context.main_window and context.main_window.action_undo:
            try:
                context.main_window.action_undo.trigger()
                logger.info("Executed undo via shortcut")
                return True
            except Exception as e:
                logger.error(f"Failed to execute undo: {e}")
                return False
        return False


class RedoCommand(ShortcutCommand):
    """Command to redo the last undone action."""

    def __init__(self) -> None:
        """Initialize the redo command."""
        super().__init__("Ctrl+Y", "Redo last action")

    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can redo.

        Can execute if there's an action to redo.
        """
        # Check if we have redo available
        if context.main_window and context.main_window.action_redo:
            return context.main_window.action_redo.isEnabled()
        return False

    def execute(self, context: ShortcutContext) -> bool:
        """Execute the redo command."""
        if context.main_window and context.main_window.action_redo:
            try:
                context.main_window.action_redo.trigger()
                logger.info("Executed redo via shortcut")
                return True
            except Exception as e:
                logger.error(f"Failed to execute redo: {e}")
                return False
        return False
