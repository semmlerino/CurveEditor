#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Plumbing module for CurveViewOperations.
Contains decorators and helper functions for state capture, data mutation, and confirmation dialogs.
"""
import functools
import inspect

from PySide6.QtWidgets import QMessageBox

from services.curve_service import CurveService as CurveViewOperations
from services.logging_service import LoggingService

logger = LoggingService.get_logger("curve_view_plumbing")


def _get_curve_view(target):
    """Extract curve_view from either main_window or direct curve_view object."""
    return target if hasattr(target, 'points') else target.curve_view


def operation(action_name, record_history=True):
    """Unified decorator: flexible injection, error handling, and finalization."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(target, *args, **kwargs):
            # Determine curve_view and main_window
            if hasattr(target, 'curve_data'):
                main_window = target
                curve_view = _get_curve_view(target)
            else:
                curve_view = target
                main_window = getattr(curve_view, 'main_window', None)
            # Capture state
            original_primary = getattr(curve_view, 'selected_point_idx', None)
            view_state = capture_view_state(curve_view)
            # Prepare arguments based on signature
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            call_args = []
            # Copy kwargs and consume used params to avoid duplicates
            kw = dict(kwargs)
            arg_iter = iter(args)
            for p in params:
                if p == 'curve_view':
                    call_args.append(curve_view)
                elif p == 'main_window':
                    call_args.append(main_window)
                else:
                    try:
                        call_args.append(next(arg_iter))
                    except StopIteration:
                        call_args.append(kw.get(p))
                        kw.pop(p, None)
            # Execute with error handling
            try:
                # Call with only unconsumed kwargs
                result = func(*call_args, **kw)
                # Show default success only for history-recording operations
                if record_history and main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(f"{action_name} completed successfully", 2000)
            except Exception as e:
                if main_window and hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage(f"Error in {action_name}: {e}", 5000)
                QMessageBox.critical(main_window, f"Error in {action_name}",
                                    f"An error occurred during {action_name}:\n{e}")
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Exception in {action_name}: {e}\n{error_traceback}")
                return None
            # Determine success and message
            if isinstance(result, tuple) and len(result) == 2:
                success, msg = result
                retval = result[0]
            else:
                success = bool(result)
                msg = action_name
                retval = result
            # Only finalize (restore state, history) if requested
            if success and record_history:
                new_sel = sorted(getattr(curve_view, 'selected_points', []))
                finalize_data_change(curve_view, main_window, view_state,
                                     new_sel, original_primary, msg)
            return retval
        return wrapper
    return decorator


def capture_view_state(curve_view):
    """Capture zoom & offset state."""
    return {
        'zoom_factor': curve_view.zoom_factor,
        'offset_x': curve_view.offset_x,
        'offset_y': curve_view.offset_y,
        'x_offset': getattr(curve_view, 'x_offset', 0),
        'y_offset': getattr(curve_view, 'y_offset', 0),
    }


def restore_view_state_and_selection(curve_view, state, selected_indices, original_primary):
    """Restore view state and selection indices."""
    curve_view.zoom_factor = state['zoom_factor']
    curve_view.offset_x = state['offset_x']
    curve_view.offset_y = state['offset_y']
    if hasattr(curve_view, 'x_offset'):
        curve_view.x_offset = state['x_offset']
    if hasattr(curve_view, 'y_offset'):
        curve_view.y_offset = state['y_offset']
    # Restore selection
    if hasattr(curve_view, 'set_selected_indices'):
        curve_view.set_selected_indices(selected_indices)
    else:
        curve_view.selected_points = set(selected_indices)
        if original_primary in selected_indices:
            curve_view.selected_point_idx = original_primary
        elif selected_indices:
            curve_view.selected_point_idx = selected_indices[0]
        else:
            curve_view.selected_point_idx = -1
        curve_view.update()
    # Emit selection signal for single-selection only
    if hasattr(curve_view, 'point_selected') and len(selected_indices) == 1:
        curve_view.point_selected.emit(curve_view.selected_point_idx)


def finalize_data_change(curve_view, main_window, view_state, selected_indices, original_primary, history_msg=None):
    """Restore view, selection, repaint, update UI, history, and status."""
    restore_view_state_and_selection(curve_view, view_state, selected_indices, original_primary)
    curve_view.update()
    if main_window and hasattr(main_window, 'selected_indices'):
        main_window.selected_indices = selected_indices
    if main_window and selected_indices:
        idx0 = original_primary if original_primary in selected_indices else selected_indices[0]
        fd = main_window.curve_data[idx0]
        # Update info panel using the imported CurveViewOperations
        CurveViewOperations.update_point_info(main_window, idx0, fd[1], fd[2])
    if main_window and hasattr(main_window, 'add_to_history'):
        main_window.add_to_history()
    if main_window and history_msg and hasattr(main_window, 'statusBar'):
        main_window.statusBar().showMessage(history_msg, 3000)


def confirm_delete(main_window, count):
    """Show confirmation dialog for deleting N points."""
    response = QMessageBox.question(
        main_window,
        "Confirm Delete",
        f"Delete {count} selected point{'s' if count > 1 else ''}?",
        QMessageBox.Yes | QMessageBox.No
    )
    return response == QMessageBox.Yes


# Functions normalize_point, set_point_status, and update_point_coords
# have been moved to services/curve_utils.py
