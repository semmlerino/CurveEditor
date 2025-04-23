#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy


class HistoryOperations:
    """History operations for the 3DE4 Curve Editor."""
    
    @staticmethod
    def add_to_history(main_window):
        """Add current state to history."""
        # If we're not at the end of the history, truncate it
        if main_window.history_index < len(main_window.history) - 1:
            main_window.history = main_window.history[:main_window.history_index + 1]
        
        # Add current state to history
        current_state = {
            'curve_data': copy.deepcopy(main_window.curve_data),
            'point_name': main_window.point_name,
            'point_color': main_window.point_color
        }
        
        main_window.history.append(current_state)
        main_window.history_index = len(main_window.history) - 1
        
        # Limit history size
        if len(main_window.history) > main_window.max_history_size:
            main_window.history = main_window.history[1:]
            main_window.history_index = len(main_window.history) - 1
        
        # Update undo/redo buttons
        HistoryOperations.update_history_buttons(main_window)

    @staticmethod
    def update_history_buttons(main_window):
        """Update the state of undo/redo buttons."""
        main_window.undo_button.setEnabled(main_window.history_index > 0)
        main_window.redo_button.setEnabled(main_window.history_index < len(main_window.history) - 1)

    @staticmethod
    def undo_action(main_window):
        """Undo the last action."""
        if main_window.history_index <= 0:
            return
        
        main_window.history_index -= 1
        HistoryOperations.restore_state(main_window, main_window.history[main_window.history_index])
        HistoryOperations.update_history_buttons(main_window)

    @staticmethod
    def redo_action(main_window):
        """Redo the previously undone action."""
        if main_window.history_index >= len(main_window.history) - 1:
            return
        
        main_window.history_index += 1
        HistoryOperations.restore_state(main_window, main_window.history[main_window.history_index])
        HistoryOperations.update_history_buttons(main_window)

    @staticmethod
    def restore_state(main_window, state):
        """Restore application state from history."""
        main_window.curve_data = copy.deepcopy(state['curve_data'])
        main_window.point_name = state['point_name']
        main_window.point_color = state['point_color']
        
        # Update view without resetting zoom/pan
        if hasattr(main_window.curve_view, 'set_curve_data'):
            main_window.curve_view.set_curve_data(main_window.curve_data)
        elif hasattr(main_window.curve_view, 'setPoints'):
            main_window.curve_view.setPoints(
                main_window.curve_data,
                main_window.image_width,
                main_window.image_height,
                preserve_view=True
            )
        else:
            main_window.curve_view.update()
        
        # Update info
        main_window.info_label.setText(f"Loaded: {main_window.point_name} ({len(main_window.curve_data)} frames)")