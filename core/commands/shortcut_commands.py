#!/usr/bin/env python
"""
Concrete implementations of keyboard shortcut commands.

This module provides specific shortcut command implementations for all
keyboard shortcuts in the application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, override

from PySide6.QtCore import Qt

if TYPE_CHECKING:
    from core.models import TrackingDirection
    from protocols.ui import MainWindowProtocol

from core.commands.shortcut_command import ShortcutCommand, ShortcutContext
from core.logger_utils import get_logger
from core.models import PointStatus, TrackingDirection
from stores.application_state import get_application_state

logger = get_logger("shortcut_commands")


class InsertTrackShortcutCommand(ShortcutCommand):
    """Command to execute Insert Track operation (3DEqualizer-style gap filling)."""

    def __init__(self) -> None:
        """Initialize the Insert Track shortcut command."""
        super().__init__("Ctrl+Shift+I", "Insert Track - Fill gaps from other tracking points")

    @override
    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if Insert Track can be executed.

        Requires:
        - At least one tracking curve selected
        - MultiPointTrackingController available
        """
        # Check for Ctrl+Shift+I modifiers
        modifiers = context.key_event.modifiers()
        expected = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        if (modifiers & expected) != expected:
            return False

        # Check for multi-point controller
        main_window = context.main_window
        if main_window.multi_point_controller is None:
            return False

        # Check for selected curves (via tracking panel)
        if main_window.tracking_panel is not None:
            selected = main_window.tracking_panel.get_selected_points()
            return len(selected) > 0

        return False

    @override
    def execute(self, context: ShortcutContext) -> bool:
        """Execute Insert Track operation.

        Creates an InsertTrackCommand and executes it through the command manager.
        """
        try:
            from core.commands.insert_track_command import InsertTrackCommand
            from services import get_interaction_service

            main_window = context.main_window

            # Get selected curves
            selected_curves = []
            if main_window.tracking_panel is not None:
                selected_curves = main_window.tracking_panel.get_selected_points()

            if not selected_curves:
                logger.warning("No curves selected for Insert Track")
                return False

            # Get current frame
            current_frame = context.current_frame
            if current_frame is None:
                logger.warning("No current frame for Insert Track")
                return False

            # Create and execute Insert Track command
            command = InsertTrackCommand(selected_curves, current_frame)

            # Execute through command manager for undo/redo support
            interaction_service = get_interaction_service()
            if interaction_service:
                success = interaction_service.command_manager.execute_command(
                    command, cast("MainWindowProtocol", cast(object, main_window))
                )
                if success:
                    logger.info(f"Insert Track executed for {len(selected_curves)} curves at frame {current_frame}")
                return success
            else:
                # Fallback: execute directly
                return command.execute(cast("MainWindowProtocol", cast(object, main_window)))

        except Exception as e:
            logger.error(f"Error executing Insert Track shortcut: {e}")
            return False


class SetEndframeCommand(ShortcutCommand):
    """Command to toggle between KEYFRAME and ENDFRAME status for selected points."""

    def __init__(self) -> None:
        """Initialize the endframe toggle command."""
        super().__init__("E", "Toggle between keyframe and end frame")

    @override
    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can toggle endframe status.

        This is a FRAME-BASED operation - can execute for any frame in the valid range.
        Valid range is defined as [1, max_frame] where max_frame is the maximum of:
        - Image sequence length (if loaded)
        - Maximum frame in existing curve data

        If no point exists at the current frame, one will be auto-created at the interpolated position.
        Selection is ignored.
        """
        # No modifiers should be pressed
        modifiers = context.key_event.modifiers()
        clean_modifiers = modifiers & ~Qt.KeyboardModifier.KeypadModifier
        if clean_modifiers != Qt.KeyboardModifier.NoModifier:
            return False

        # Can execute if we have a current frame
        if context.current_frame is None:
            return False

        try:
            app_state = get_application_state()
            # Must have an active curve
            if (cd := app_state.active_curve_data) is None:
                return False
            _, curve_data = cd

            # Determine valid frame range: max of image sequence or curve data range
            total_frames = app_state.get_total_frames()
            if curve_data:
                max_curve_frame = max(point[0] for point in curve_data)
                total_frames = max(total_frames, max_curve_frame)

            return 1 <= context.current_frame <= total_frames

        except ValueError:
            # No active curve set
            return False

    @override
    def execute(self, context: ShortcutContext) -> bool:
        """Execute the endframe toggle command.

        This is a FRAME-BASED operation - it operates on the point at the current frame,
        NOT on selected points. If no point exists at the current frame, one is auto-created
        at the interpolated/held position (3DEqualizer behavior).
        """
        curve_widget = self._get_curve_widget(context)
        if curve_widget is None:
            return False

        try:
            from core.commands.curve_commands import AddPointCommand, SetPointStatusCommand
            from services import get_data_service, get_interaction_service

            # FRAME-BASED OPERATION: Always operate on current frame, ignore selection
            if context.current_frame is None:
                return False

            # Get active curve data using ApplicationState
            app_state = get_application_state()
            if (cd := app_state.active_curve_data) is None:
                logger.warning("No active curve set, cannot toggle endframe")
                return False
            _curve_name, curve_data = cd
            curve_data = list(curve_data)  # Mutable copy

            # Find the point at the current frame
            point_index = self._find_point_index_at_frame(curve_data, context.current_frame)

            # If no point exists at current frame, create one at interpolated position
            if point_index is None:
                data_service = get_data_service()
                position = data_service.get_position_at_frame(curve_data, context.current_frame)

                if position is None:
                    # No curve data to interpolate from - create at origin
                    x, y = 0.0, 0.0
                else:
                    x, y = position

                # Find insertion index (keep frames sorted)
                insert_index = 0
                for i, point in enumerate(curve_data):
                    if point[0] < context.current_frame:
                        insert_index = i + 1
                    else:
                        break

                # Create new KEYFRAME at interpolated position
                new_point = (context.current_frame, x, y, PointStatus.KEYFRAME.value)

                # Add the point via command (for undo support)
                add_command = AddPointCommand(
                    description=f"Auto-create keyframe at frame {context.current_frame}",
                    index=insert_index,
                    point=new_point,
                )

                interaction_service = get_interaction_service()
                if not interaction_service:
                    return False

                success = interaction_service.command_manager.execute_command(
                    add_command, cast("MainWindowProtocol", cast(object, context.main_window))
                )

                if not success:
                    logger.error("Failed to auto-create point")
                    return False

                # Update our local copy and find the new point
                curve_data.insert(insert_index, new_point)
                point_index = insert_index
                logger.info(f"Auto-created keyframe at frame {context.current_frame}, position ({x:.2f}, {y:.2f})")

            # Now we have a point at the current frame - toggle its status
            if point_index < 0 or point_index >= len(curve_data):
                return False

            point = curve_data[point_index]
            if not point or len(point) < 3:
                return False

            # Handle both 3-element (frame, x, y) and 4-element (frame, x, y, status) formats
            if len(point) >= 4:
                current_status = PointStatus.from_legacy(point[3]).to_legacy_string()
            else:
                current_status = PointStatus.KEYFRAME.value

            # Toggle logic
            if current_status == PointStatus.ENDFRAME.value:
                new_status = PointStatus.KEYFRAME.value
                status_text = "KEYFRAME"
            else:
                new_status = PointStatus.ENDFRAME.value
                status_text = "ENDFRAME"

            # Create status message
            msg = f"Set frame {context.current_frame} to {status_text}"

            # Create command with proper description
            command = SetPointStatusCommand(
                description=msg,
                changes=[(point_index, current_status, new_status)],
            )

            # Execute through command manager
            interaction_service = get_interaction_service()
            if not interaction_service:
                return False

            success = interaction_service.command_manager.execute_command(
                command, cast("MainWindowProtocol", cast(object, context.main_window))
            )

            if success:
                curve_widget.update_status(msg, 2000)
                logger.info(msg)
                return True
            return False

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
        self.direction: TrackingDirection = direction
        description = f"Set tracking direction to {direction.value}"
        super().__init__(key_sequence, description)

    @override
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
        if tracking_panel is None:
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

    @override
    def execute(self, context: ShortcutContext) -> bool:
        """Execute the tracking direction command."""
        tracking_panel = context.main_window.tracking_panel
        if tracking_panel is None:
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
            tracking_panel.set_direction_for_points(selected_points, self.direction)
            return True

        except Exception as e:
            logger.error(f"Failed to set tracking direction: {e}")
            return False


class DeletePointsCommand(ShortcutCommand):
    """Command to delete selected points."""

    def __init__(self) -> None:
        """Initialize the delete command."""
        super().__init__("Delete", "Delete selected points")

    @override
    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can delete points.

        Can execute if there are selected curve or tracking points.
        """
        return context.has_curve_selection or context.has_tracking_selection

    @override
    def execute(self, context: ShortcutContext) -> bool:
        """Execute the delete command."""
        success = False

        # Delete curve points if selected
        if context.has_curve_selection:
            curve_widget = self._get_curve_widget(context)
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
                    tracking_panel.delete_points(context.selected_tracking_points)
                    success = True
                except Exception as e:
                    logger.error(f"Failed to delete tracking points: {e}")

        return success


class DeleteCurrentFrameKeyframeCommand(ShortcutCommand):
    """Command to convert the keyframe at the current frame to an interpolated point."""

    def __init__(self) -> None:
        """Initialize the delete current frame keyframe command."""
        super().__init__("Ctrl+R", "Convert keyframe to interpolated point")

    @override
    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can delete the keyframe at the current frame.

        Can execute if there's a point at the current frame.
        """
        # Can execute if we have a current frame with a point
        if context.current_frame is not None:
            try:
                app_state = get_application_state()
                if (cd := app_state.active_curve_data) is None:
                    return False
                _, curve_data = cd
                # Check if any point exists at the current frame
                for point in curve_data:
                    if point[0] == context.current_frame:  # point[0] is the frame number
                        return True
            except ValueError:
                return False

        return False

    @override
    def execute(self, context: ShortcutContext) -> bool:
        """Execute the convert keyframe to interpolated command.

        This is a FRAME-BASED operation - it converts the point at the current frame
        to an interpolated point with coordinates calculated from surrounding keyframes.
        """
        curve_widget = self._get_curve_widget(context)
        if curve_widget is None:
            return False

        try:
            from core.commands.curve_commands import ConvertToInterpolatedCommand
            from core.curve_segments import SegmentedCurve
            from core.models import CurvePoint, PointStatus
            from services import get_interaction_service

            # FRAME-BASED OPERATION: Find and convert point at current frame
            if context.current_frame is not None:
                # Find the point index at the current frame using ApplicationState
                app_state = get_application_state()
                if (cd := app_state.active_curve_data) is None:
                    logger.warning("No active curve set, cannot delete keyframe")
                    return False
                _, curve_data = cd
                point_index = self._find_point_index_at_frame(curve_data, context.current_frame)
                current_point = curve_data[point_index] if point_index is not None else None

                if point_index is not None and current_point is not None:
                    # Get the current point data
                    frame = current_point[0]
                    old_x = current_point[1]
                    old_y = current_point[2]
                    # Ensure status is always a string
                    if len(current_point) >= 4:
                        old_status_raw = current_point[3]
                        if isinstance(old_status_raw, bool):
                            old_status = "interpolated" if old_status_raw else "normal"
                        else:
                            old_status = old_status_raw
                    else:
                        old_status = "normal"

                    # Convert curve data tuples to CurvePoint objects for segmented curve
                    curve_points = [CurvePoint.from_tuple(p) for p in curve_data]

                    # Calculate interpolated position using segmented curve
                    segmented_curve = SegmentedCurve.from_points(curve_points)
                    prev_kf, next_kf = segmented_curve.get_interpolation_boundaries(frame)

                    # Calculate interpolated coordinates
                    if prev_kf and next_kf:
                        # Linear interpolation between boundaries
                        frame_ratio = (frame - prev_kf.frame) / (next_kf.frame - prev_kf.frame)
                        new_x = prev_kf.x + (next_kf.x - prev_kf.x) * frame_ratio
                        new_y = prev_kf.y + (next_kf.y - prev_kf.y) * frame_ratio
                    elif prev_kf:
                        # Only have previous - use its position
                        new_x = prev_kf.x
                        new_y = prev_kf.y
                    elif next_kf:
                        # Only have next - use its position
                        new_x = next_kf.x
                        new_y = next_kf.y
                    else:
                        # No boundaries - keep original position
                        new_x = old_x
                        new_y = old_y

                    # Create old and new point tuples
                    old_point = (frame, old_x, old_y, old_status)
                    new_point = (frame, new_x, new_y, PointStatus.INTERPOLATED.value)

                    # Create convert command
                    command = ConvertToInterpolatedCommand(
                        description=f"Convert frame {context.current_frame} to interpolated",
                        index=point_index,
                        old_point=old_point,
                        new_point=new_point,
                    )

                    # Execute through command manager for undo support
                    interaction_service = get_interaction_service()
                    if interaction_service:
                        success = interaction_service.command_manager.execute_command(
                            command, cast("MainWindowProtocol", cast(object, context.main_window))
                        )
                        if success:
                            msg = f"Converted frame {context.current_frame} to interpolated"
                            curve_widget.update_status(msg, 2000)
                            logger.info(msg)
                            return True
                    return False

        except Exception as e:
            logger.error(f"Failed to convert keyframe to interpolated: {e}")

        return False


class CenterViewCommand(ShortcutCommand):
    """Command to center view on selection or current frame."""

    def __init__(self) -> None:
        """Initialize the center view command."""
        super().__init__("C", "Center view on selection")

    @override
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
        return self._get_curve_widget(context) is not None

    @override
    def execute(self, context: ShortcutContext) -> bool:
        """Execute the center view command."""
        curve_widget = self._get_curve_widget(context)
        if curve_widget is None:
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

    @override
    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can select all.

        Can execute if curve widget is available.
        """
        return self._get_curve_widget(context) is not None

    @override
    def execute(self, context: ShortcutContext) -> bool:
        """Execute the select all command."""
        curve_widget = self._get_curve_widget(context)
        if curve_widget is None:
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

    @override
    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can deselect all.

        Can execute if there are selected points.
        """
        return context.has_curve_selection

    @override
    def execute(self, context: ShortcutContext) -> bool:
        """Execute the deselect command."""
        curve_widget = self._get_curve_widget(context)
        if curve_widget is None:
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

    @override
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
        curve_widget = self._get_curve_widget(context)
        return curve_widget is not None and curve_widget.background_image is not None

    @override
    def execute(self, context: ShortcutContext) -> bool:
        """Execute the fit background command."""
        curve_widget = self._get_curve_widget(context)
        if curve_widget is None or curve_widget.background_image is None:
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
        self.base_dx: float = dx
        self.base_dy: float = dy
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

    @override
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
            try:
                app_state = get_application_state()
                if (cd := app_state.active_curve_data) is None:
                    return False
                _, curve_data = cd
                # Check if any point exists at the current frame
                for point in curve_data:
                    if point[0] == context.current_frame:  # point[0] is the frame number
                        return True
            except ValueError:
                return False

        return False

    @override
    def execute(self, context: ShortcutContext) -> bool:
        """Execute the nudge command."""
        curve_widget = self._get_curve_widget(context)
        if curve_widget is None:
            return False

        try:
            # Calculate nudge amount based on modifiers
            from core.defaults import DEFAULT_NUDGE_AMOUNT

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
                # Center view on selection after nudging
                curve_widget.view_camera.center_on_selection()
            elif context.current_frame is not None:
                # Find the point at the current frame using ApplicationState
                app_state = get_application_state()
                if (cd := app_state.active_curve_data) is None:
                    logger.warning("No active curve set, cannot nudge point")
                    return False
                _, curve_data = cd
                point_index = self._find_point_index_at_frame(curve_data, context.current_frame)

                if point_index is not None:
                    logger.info(f"Nudging point at frame {context.current_frame} by ({dx}, {dy})")
                    # Temporarily select the point, nudge it, then clear
                    curve_widget.select_point(point_index, add_to_selection=False)
                    curve_widget.nudge_selected(dx, dy)
                    # Center view on selection before clearing it
                    curve_widget.view_camera.center_on_selection()
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

    @override
    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can undo.

        Can execute if there's an action to undo.
        """
        # Check if we have undo available
        if context.main_window and context.main_window.action_undo:
            return context.main_window.action_undo.isEnabled()
        return False

    @override
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

    @override
    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if we can redo.

        Can execute if there's an action to redo.
        """
        # Check if we have redo available
        if context.main_window and context.main_window.action_redo:
            return context.main_window.action_redo.isEnabled()
        return False

    @override
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
