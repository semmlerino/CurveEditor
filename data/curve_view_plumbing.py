#!/usr/bin/env python

"""
Plumbing module for CurveViewOperations.
Contains decorators and helper functions for state capture, data mutation, and confirmation dialogs.
"""

import functools
import inspect
from collections.abc import Callable
from typing import Protocol, TypeVar, cast

from PySide6.QtWidgets import QMessageBox, QWidget

from core.logger_utils import get_logger
from protocols.ui import CurveViewProtocol, MainWindowProtocol
from services import get_interaction_service

# Type variable for generic decorator return types
T = TypeVar("T")

logger = get_logger("curve_view_plumbing")


class ViewState(Protocol):
    """Protocol for view state objects."""

    zoom_factor: float
    offset_x: float
    offset_y: float
    selected_indices: list[int] | None
    selected_point_idx: int | None


# Union type to represent targets that could be either CurveView or MainWindow
OperationTarget = CurveViewProtocol | MainWindowProtocol


def _get_curve_view(target: OperationTarget) -> CurveViewProtocol:
    """Extract curve_view from either main_window or direct curve_view object."""
    # Check for points attribute to determine if target is a curve_view
    # Using getattr with None default for type safety
    if getattr(target, "points", None) is not None:
        # Target is already a CurveViewProtocol
        return cast(CurveViewProtocol, target)

    # Check if target has curve_view attribute (MainWindowProtocol)
    curve_view = getattr(target, "curve_view", None)
    if curve_view is not None:
        # Target is a MainWindowProtocol, return its curve_view
        return cast(CurveViewProtocol, curve_view)
    else:
        raise ValueError("Target must be CurveViewProtocol (with 'points') or MainWindowProtocol (with 'curve_view')")


def operation(action_name: str, record_history: bool = True) -> Callable[[Callable[..., T]], Callable[..., T | None]]:
    """Unified decorator: flexible injection, error handling, and finalization."""

    def decorator(func: Callable[..., T]) -> Callable[..., T | None]:
        @functools.wraps(func)
        def wrapper(target: CurveViewProtocol | MainWindowProtocol, *args: object, **kwargs: object) -> T | None:
            # Determine curve_view and main_window
            # Check if target is a main_window (has curve_data)
            # This is intentional duck-typing for flexibility - using getattr for type safety
            if getattr(target, "curve_data", None) is not None:
                main_window: MainWindowProtocol | None = cast(MainWindowProtocol, target)
                curve_view = _get_curve_view(target)
            else:
                curve_view = _get_curve_view(target)  # Assume target is curve_view
                main_window = getattr(curve_view, "main_window", None)
            # Capture state
            original_primary: int | None = getattr(curve_view, "selected_point_idx", None)
            view_state = capture_view_state(curve_view)
            # Prepare arguments based on signature
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            call_args: list[object] = []
            # Copy kwargs and consume used params to avoid duplicates
            kw = dict(kwargs)
            arg_iter = iter(args)
            for p in params:
                if p == "curve_view":
                    call_args.append(curve_view)
                elif p == "main_window":
                    call_args.append(main_window)
                else:
                    try:
                        call_args.append(next(arg_iter))
                    except StopIteration:
                        call_args.append(kw.get(p))
                        _ = kw.pop(p, None)
            # Execute with error handling
            try:
                # Call with only unconsumed kwargs
                result = func(*call_args, **kw)
                # Show default success only for history-recording operations
                # statusBar() is a QMainWindow method, always available
                if record_history and main_window and getattr(main_window, "statusBar", None) is not None:
                    main_window.statusBar().showMessage(f"{action_name} completed successfully", 2000)
            except Exception as e:
                # statusBar() is a QMainWindow method, always available
                if main_window and getattr(main_window, "statusBar", None) is not None:
                    main_window.statusBar().showMessage(f"Error in {action_name}: {e}", 5000)
                _unused_result = QMessageBox.critical(
                    cast(QWidget, cast(object, main_window)),  # MainWindow inherits from QMainWindow -> QWidget
                    f"Error in {action_name}",
                    f"An error occurred during {action_name}:\n{e}",
                )
                import traceback

                error_traceback = traceback.format_exc()
                logger.error(f"Exception in {action_name}: {e}\n{error_traceback}")
                return None
            # Determine success and message
            if isinstance(result, tuple) and len(result) == 2:  # pyright: ignore[reportUnknownArgumentType]
                success: bool = bool(result[0])  # pyright: ignore[reportUnknownArgumentType]
                msg: str = str(result[1])  # pyright: ignore[reportUnknownArgumentType]
                retval: T | None = None  # Tuple case returns status info, not the actual result
            else:
                success = bool(result)  # pyright: ignore[reportUnknownArgumentType]
                msg = action_name
                retval = cast(T, result)  # Cast to help type checker understand the return type
            # Only finalize (restore state, history) if requested
            if success and record_history:
                new_sel = sorted(getattr(curve_view, "selected_points", []))
                finalize_data_change(curve_view, main_window, view_state, new_sel, original_primary, msg)
            return retval

        return wrapper

    return decorator


def capture_view_state(curve_view: CurveViewProtocol) -> dict[str, float]:
    """Capture zoom & offset state."""
    return {
        "zoom_factor": curve_view.zoom_factor,
        "offset_x": curve_view.offset_x,
        "offset_y": curve_view.offset_y,
        "x_offset": getattr(curve_view, "x_offset", 0),
        "y_offset": getattr(curve_view, "y_offset", 0),
    }


def restore_view_state_and_selection(
    curve_view: CurveViewProtocol,
    state: dict[str, float],
    selected_indices: list[int] | None,
    original_primary: int | None,
) -> None:
    """Restore view state and selection indices."""
    curve_view.zoom_factor = state["zoom_factor"]
    curve_view.offset_x = state["offset_x"]
    curve_view.offset_y = state["offset_y"]
    # x_offset is defined in CurveViewProtocol
    if getattr(curve_view, "x_offset", None) is not None:
        curve_view.x_offset = state["x_offset"]
    # y_offset is defined in CurveViewProtocol
    if getattr(curve_view, "y_offset", None) is not None:
        curve_view.y_offset = state["y_offset"]
    # Restore selection
    if selected_indices is not None:
        if getattr(curve_view, "set_selected_indices", None) is not None:
            curve_view.set_selected_indices(selected_indices)
        else:
            curve_view.selected_points = set(selected_indices)
            if original_primary is not None and original_primary in selected_indices:
                curve_view.selected_point_idx = original_primary
            elif selected_indices:
                curve_view.selected_point_idx = selected_indices[0]
            else:
                curve_view.selected_point_idx = -1
    else:
        # No selection to restore
        if getattr(curve_view, "set_selected_indices", None) is not None:
            curve_view.set_selected_indices([])
        else:
            curve_view.selected_points = set()
            curve_view.selected_point_idx = -1
        curve_view.update()
    # Emit selection signal for single-selection only
    if getattr(curve_view, "point_selected", None) is not None and selected_indices and len(selected_indices) == 1:
        # Signal is now properly typed in CurveViewProtocol
        curve_view.point_selected.emit(curve_view.selected_point_idx)


def finalize_data_change(
    curve_view: CurveViewProtocol,
    main_window: MainWindowProtocol | None,
    view_state: dict[str, float],
    selected_indices: list[int] | None,
    original_primary: int | None,
    history_msg: str | None = None,
) -> None:
    """Restore view, selection, repaint, update UI, history, and status."""
    restore_view_state_and_selection(curve_view, view_state, selected_indices, original_primary)
    curve_view.update()
    if main_window and getattr(main_window, "selected_indices", None) is not None and selected_indices is not None:
        main_window.selected_indices = selected_indices
    if main_window and selected_indices:
        idx0 = original_primary if original_primary in selected_indices else selected_indices[0]
        fd = main_window.curve_data[idx0]
        # Update info panel using InteractionService
        interaction_service = get_interaction_service()
        interaction_service.update_point_info(main_window, idx0, fd[1], fd[2])
    if main_window and getattr(main_window, "add_to_history", None) is not None:
        main_window.add_to_history()
    # statusBar() is a QMainWindow method, always available
    if main_window and history_msg and getattr(main_window, "statusBar", None) is not None:
        main_window.statusBar().showMessage(history_msg, 3000)


def confirm_delete(main_window: MainWindowProtocol, count: int) -> bool:
    """Show confirmation dialog for deleting N points."""
    response = QMessageBox.question(
        cast(QWidget, cast(object, main_window)),  # MainWindow inherits from QMainWindow -> QWidget
        "Confirm Delete",
        f"Delete {count} selected point{'s' if count > 1 else ''}?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return response == QMessageBox.StandardButton.Yes


# Functions normalize_point, set_point_status, and update_point_coords
# have been moved to services/curve_utils.py
