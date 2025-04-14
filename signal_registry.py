#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Signal Registry for 3DE4 Curve Editor.

This module provides a centralized registry for managing signal connections
throughout the application. It ensures consistent connection patterns and
error handling for all UI signals.

Key improvements in this refactored version:
1. Centralized all signal connections in a single class
2. Organized connections by functional area
3. Added connection tracking to prevent duplicate connections
4. Added debug logging for connection status
5. Implemented proper error handling for all connections
"""

import traceback
from curve_operations import CurveOperations
from PySide6.QtCore import Qt, Signal, QObject
from curve_view_operations import CurveViewOperations
from visualization_operations import VisualizationOperations
from image_operations import ImageOperations
from dialog_operations import DialogOperations
from file_operations import FileOperations
from history_operations import HistoryOperations
from keyboard_shortcuts import ShortcutManager
from centering_zoom_operations import ZoomOperations



class SignalRegistry:
    """Centralized registry for managing signal connections.
    
    This class consolidates all signal connections in the application, ensuring
    that each signal is connected exactly once to its appropriate handler.
    
    The class uses a registry pattern where each group of signals is handled by
    a dedicated private method, and the main connect_all_signals method orchestrates
    the connection process.
    """
    
    @staticmethod
    def connect_all_signals(main_window):
        """Connect all signals throughout the application.
        
        Args:
            main_window: The main application window instance
            
        This method serves as the single entry point for connecting all signals
        in the application. It tracks which signals have been connected to prevent
        duplicate connections and provides detailed error reporting.
        """
        # Initialize connection tracking for debugging
        if not hasattr(main_window, '_connected_signals'):
            main_window._connected_signals = set()
        
        # Print a header to make the connection process visible in logs
        print("\n" + "="*80)
        print("CONNECTING ALL APPLICATION SIGNALS")
        print("="*80)
        
        # Define all signal connection groups to process
        signal_groups = [
            # UI element signals
            ("Curve View", SignalRegistry._connect_curve_view_signals),
            ("Point Editing", SignalRegistry._connect_point_editing_signals),
            ("File Operations", SignalRegistry._connect_file_operations_signals),
            ("Visualization", SignalRegistry._connect_visualization_signals),
            ("Timeline", SignalRegistry._connect_timeline_signals),
            ("Batch Edit", SignalRegistry._connect_batch_edit_signals),
            ("Dialog Operations", SignalRegistry._connect_dialog_signals),
            ("History Operations", SignalRegistry._connect_history_signals),
            ("Enhanced View", SignalRegistry._connect_enhanced_view_signals),
            ("Image Operations", SignalRegistry._connect_image_operations_signals),
            
            # Keyboard shortcuts (handled last after all UI elements are connected)
            ("Keyboard Shortcuts", SignalRegistry._connect_keyboard_shortcuts),
        ]
        
        # Connect each group with proper error handling
        for group_name, connection_func in signal_groups:
            try:
                print(f"\nConnecting {group_name} signals...")
                connection_func(main_window)
                print(f"✓ Successfully connected {group_name} signals")
            except Exception as e:
                print(f"✗ Error connecting {group_name} signals: {str(e)}")
                traceback.print_exc()
        
        print("\n" + "="*80)
        print(f"Signal connection complete. {len(main_window._connected_signals)} total connections.")
        print("="*80 + "\n")
    
    @staticmethod
    def _connect_signal(main_window, signal, slot, signal_name=None):
        """Connect a signal to a slot with tracking and error handling.
        
        Args:
            main_window: The main application window
            signal: The signal to connect
            slot: The slot function to connect to
            signal_name: Optional name for the signal for tracking
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        if signal is None:
            print(f"  ✗ Signal '{signal_name}' is None, cannot connect")
            return False
            
        if not hasattr(signal, 'connect'):
            print(f"  ✗ Object '{signal_name}' is not a signal (no connect method)")
            return False
            
        # Create a unique identifier for this connection
        connection_id = f"{signal_name or id(signal)}-{id(slot)}"
        
        # Check if this connection already exists
        if connection_id in main_window._connected_signals:
            print(f"  ⚠ Signal '{signal_name}' already connected to this slot, skipping")
            return True
            
        try:
            # Make the connection
            signal.connect(slot)
            
            # Add to tracking set
            main_window._connected_signals.add(connection_id)
            
            # Log success
            print(f"  ✓ Connected: {signal_name or 'signal'}")
            return True
        except Exception as e:
            print(f"  ✗ Error connecting {signal_name or 'signal'}: {str(e)}")
            return False
    
    @staticmethod
    def _connect_curve_view_signals(main_window):
        """Connect signals from the curve view widget.
        
        Args:
            main_window: The main application window
        """
        if not hasattr(main_window, 'curve_view'):
            print("  ⚠ No curve_view found, skipping curve view signals")
            return
            
        cv = main_window.curve_view
        
        # Define all curve view signals to connect
        connections = [
            (getattr(cv, 'point_selected', None), 
             lambda idx: CurveViewOperations.on_point_selected(main_window, idx),
             "curve_view.point_selected"),
             
            (getattr(cv, 'point_moved', None), 
             lambda idx, x, y: CurveViewOperations.on_point_moved(main_window, idx, x, y),
             "curve_view.point_moved"),
             
            (getattr(cv, 'image_changed', None), 
             main_window.on_image_changed,
             "curve_view.image_changed"),
        ]
        
        # Connect each signal
        for signal, slot, name in connections:
            SignalRegistry._connect_signal(main_window, signal, slot, name)
    
    @staticmethod
    def _connect_point_editing_signals(main_window):
        """Connect signals for point editing controls.
        
        Args:
            main_window: The main application window
        """
        # Point info update button
        if hasattr(main_window, 'update_point_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.update_point_button.clicked,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "update_point_button.clicked"
            )
                
        # Enhanced point size control
        if hasattr(main_window, 'point_size_spin'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.point_size_spin.valueChanged,
                lambda value: CurveViewOperations.set_point_size(main_window, value),
                "point_size_spin.valueChanged"
            )
        
        # Point coordinate entry fields
        if hasattr(main_window, 'x_edit') and hasattr(main_window, 'y_edit'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.x_edit.returnPressed,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "x_edit.returnPressed"
            )
            
            SignalRegistry._connect_signal(
                main_window,
                main_window.y_edit.returnPressed,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "y_edit.returnPressed"
            )
    
    @staticmethod
    def _connect_file_operations_signals(main_window):
        """Connect signals for file operations.
        
        Args:
            main_window: The main application window
        """
        # Load/save/add buttons
        if hasattr(main_window, 'load_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.load_button.clicked,
                lambda: FileOperations.load_track_data(main_window),
                "load_button.clicked"
            )
                
        if hasattr(main_window, 'save_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.save_button.clicked,
                lambda: FileOperations.save_track_data(main_window),
                "save_button.clicked"
            )
                
        if hasattr(main_window, 'add_point_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.add_point_button.clicked,
                lambda: FileOperations.add_track_data(main_window),
                "add_point_button.clicked"
            )
            
        # Export buttons
        if hasattr(main_window, 'export_csv_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.export_csv_button.clicked,
                lambda: FileOperations.export_to_csv(main_window),
                "export_csv_button.clicked"
            )
    
    @staticmethod
    def _connect_visualization_signals(main_window):
        """Connect signals for visualization controls.
        
        Args:
            main_window: The main application window
        """
        # Basic view controls
        if hasattr(main_window, 'reset_view_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.reset_view_button.clicked,
                lambda: CurveViewOperations.reset_view(main_window),
                "reset_view_button.clicked"
            )
                
        # Enhanced visualization controls
        if hasattr(main_window, 'toggle_grid_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.toggle_grid_button.clicked,
                lambda checked: VisualizationOperations.toggle_grid(main_window, checked),
                "toggle_grid_button.clicked"
            )
                
        if hasattr(main_window, 'toggle_vectors_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.toggle_vectors_button.clicked,
                lambda checked: VisualizationOperations.toggle_velocity_vectors(main_window, checked),
                "toggle_vectors_button.clicked"
            )
                
        if hasattr(main_window, 'toggle_frame_numbers_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.toggle_frame_numbers_button.clicked,
                lambda checked: VisualizationOperations.toggle_all_frame_numbers(main_window, checked),
                "toggle_frame_numbers_button.clicked"
            )
                
                
        if hasattr(main_window, 'center_on_point_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.center_on_point_button.clicked,
                lambda: VisualizationOperations.center_on_selected_point_from_main_window(main_window),
                "center_on_point_button.clicked"
            )
    
    @staticmethod
    def _connect_timeline_signals(main_window):
        """Connect signals for timeline and frame navigation.
        
        Args:
            main_window: The main application window
        """
        from ui_components import UIComponents
        
        # Timeline slider
        if hasattr(main_window, 'timeline_slider'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.timeline_slider.valueChanged,
                lambda value: UIComponents.on_timeline_changed(main_window, value),
                "timeline_slider.valueChanged"
            )
                
        # Frame controls
        if hasattr(main_window, 'frame_edit'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.frame_edit.returnPressed,
                lambda: UIComponents.on_frame_edit_changed(main_window),
                "frame_edit.returnPressed"
            )
                
        if hasattr(main_window, 'go_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.go_button.clicked,
                lambda: UIComponents.on_frame_edit_changed(main_window),
                "go_button.clicked"
            )
                
        # Navigation buttons
        if hasattr(main_window, 'next_frame_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.next_frame_button.clicked,
                lambda: UIComponents.next_frame(main_window),
                "next_frame_button.clicked"
            )
                
        if hasattr(main_window, 'prev_frame_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.prev_frame_button.clicked,
                lambda: UIComponents.prev_frame(main_window),
                "prev_frame_button.clicked"
            )
                
        if hasattr(main_window, 'first_frame_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.first_frame_button.clicked,
                lambda: UIComponents.go_to_first_frame(main_window),
                "first_frame_button.clicked"
            )
                
        if hasattr(main_window, 'last_frame_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.last_frame_button.clicked,
                lambda: UIComponents.go_to_last_frame(main_window),
                "last_frame_button.clicked"
            )
                
        if hasattr(main_window, 'play_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.play_button.clicked,
                lambda: UIComponents.toggle_playback(main_window),
                "play_button.clicked"
            )
    
    @staticmethod
    def _connect_batch_edit_signals(main_window):
        """Connect signals for batch editing operations.
        
        Args:
            main_window: The main application window
        """
        # Batch edit buttons are typically connected in batch_edit.py
        # But we'll add some common ones here if they exist
        
        if hasattr(main_window, 'scale_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.scale_button.clicked,
                lambda: main_window.batch_edit_ui.batch_scale() if hasattr(main_window, 'batch_edit_ui') else None,
                "scale_button.clicked"
            )
            
        if hasattr(main_window, 'offset_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.offset_button.clicked,
                lambda: main_window.batch_edit_ui.batch_offset() if hasattr(main_window, 'batch_edit_ui') else None,
                "offset_button.clicked"
            )
            
        if hasattr(main_window, 'rotate_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.rotate_button.clicked,
                lambda: main_window.batch_edit_ui.batch_rotate() if hasattr(main_window, 'batch_edit_ui') else None,
                "rotate_button.clicked"
            )
            
        if hasattr(main_window, 'smooth_batch_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.smooth_batch_button.clicked,
                lambda: main_window.batch_edit_ui.batch_smooth() if hasattr(main_window, 'batch_edit_ui') else None,
                "smooth_batch_button.clicked"
            )
            
        if hasattr(main_window, 'select_all_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.select_all_button.clicked,
                lambda: CurveViewOperations.select_all_points(main_window.curve_view),
                "select_all_button.clicked"
            )
    
    @staticmethod
    def _connect_dialog_signals(main_window):
        """Connect signals for dialog operations.
        
        Args:
            main_window: The main application window
        """
        # Tool dialog buttons
        if hasattr(main_window, 'smooth_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.smooth_button.clicked,
                lambda: DialogOperations.show_smooth_dialog(main_window),
                "smooth_button.clicked"
            )
                
        if hasattr(main_window, 'filter_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.filter_button.clicked,
                lambda: DialogOperations.show_filter_dialog(main_window),
                "filter_button.clicked"
            )
                
        if hasattr(main_window, 'fill_gaps_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.fill_gaps_button.clicked,
                lambda: DialogOperations.show_fill_gaps_dialog(main_window),
                "fill_gaps_button.clicked"
            )
                
        if hasattr(main_window, 'extrapolate_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.extrapolate_button.clicked,
                lambda: DialogOperations.show_extrapolate_dialog(main_window),
                "extrapolate_button.clicked"
            )
                
        if hasattr(main_window, 'detect_problems_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.detect_problems_button.clicked,
                lambda: DialogOperations.show_problem_detection_dialog(
                    main_window, 
                    CurveOperations.detect_problems(main_window)
                ),
                "detect_problems_button.clicked"
            )
            
        if hasattr(main_window, 'shortcuts_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.shortcuts_button.clicked,
                lambda: DialogOperations.show_shortcuts_dialog(main_window),
                "shortcuts_button.clicked"
            )
    
    @staticmethod
    def _connect_history_signals(main_window):
        """Connect signals for history operations (undo/redo).
        
        Args:
            main_window: The main application window
        """
        # History buttons
        if hasattr(main_window, 'undo_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.undo_button.clicked,
                lambda: HistoryOperations.undo_action(main_window),
                "undo_button.clicked"
            )
                
        if hasattr(main_window, 'redo_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.redo_button.clicked,
                lambda: HistoryOperations.redo_action(main_window),
                "redo_button.clicked"
            )
    
    @staticmethod
    def _connect_enhanced_view_signals(main_window):
        """Connect signals specific to the enhanced curve view.
        
        Args:
            main_window: The main application window
        """
        # Only proceed if we have an enhanced curve view
        if not hasattr(main_window, 'curve_view') or not hasattr(main_window.curve_view, 'toggleGrid'):
            print("  ⚠ Enhanced curve view not detected, skipping enhanced view signals")
            return
            
        # These are typically handled in the curve_view_signals, but we'll add specific ones here
        pass  # Currently no additional signals needed
    
    @staticmethod
    def _connect_image_operations_signals(main_window):
        """Connect signals for image operations.
        
        Args:
            main_window: The main application window
        """
        # Background controls
        if hasattr(main_window, 'toggle_bg_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.toggle_bg_button.clicked,
                lambda: ImageOperations.toggle_background(main_window),
                "toggle_bg_button.clicked"
            )
                
        if hasattr(main_window, 'opacity_slider'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.opacity_slider.valueChanged,
                lambda value: ImageOperations.opacity_changed(main_window, value),
                "opacity_slider.valueChanged"
            )
                
        if hasattr(main_window, 'load_images_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.load_images_button.clicked,
                lambda: ImageOperations.load_image_sequence(main_window),
                "load_images_button.clicked"
            )
                
        # Navigation buttons
        if hasattr(main_window, 'next_image_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.next_image_button.clicked,
                lambda: ImageOperations.next_image(main_window),
                "next_image_button.clicked"
            )
                
        if hasattr(main_window, 'prev_image_button'):
            SignalRegistry._connect_signal(
                main_window,
                main_window.prev_image_button.clicked,
                lambda: ImageOperations.previous_image(main_window),
                "prev_image_button.clicked"
            )
    
    @staticmethod
    def _connect_keyboard_shortcuts(main_window):
        """Connect keyboard shortcuts to actions.
        
        Args:
            main_window: The main application window
        """
        # Check if shortcuts have already been set up
        if not hasattr(main_window, 'shortcuts') or not main_window.shortcuts:
            print("  ⚠ No shortcuts dictionary found, initializing...")
            # Initialize shortcuts if needed
            ShortcutManager.setup_shortcuts(main_window)
        
        # File operations
        ShortcutManager.connect_shortcut(main_window, "open_file", 
                                         lambda: FileOperations.load_track_data(main_window))
        ShortcutManager.connect_shortcut(main_window, "save_file", 
                                         lambda: FileOperations.save_track_data(main_window))
        ShortcutManager.connect_shortcut(main_window, "export_csv", 
                                         lambda: FileOperations.export_to_csv(main_window))
        
        # Edit operations
        ShortcutManager.connect_shortcut(main_window, "undo", 
                                         lambda: HistoryOperations.undo_action(main_window))
        ShortcutManager.connect_shortcut(main_window, "redo", 
                                         lambda: HistoryOperations.redo_action(main_window))
        ShortcutManager.connect_shortcut(main_window, "select_all", 
                                         lambda: CurveViewOperations.select_all_points(main_window.curve_view))
        ShortcutManager.connect_shortcut(main_window, "deselect_all", 
                                         lambda: CurveViewOperations.clear_selection(main_window.curve_view))
        # Only register the main Delete shortcut to avoid ambiguity
        ShortcutManager.connect_shortcut(main_window, "delete_selected",
                                         lambda: CurveViewOperations.delete_selected_points(main_window))
        # If you want Backspace as an alternative, ensure it does not conflict with QAction
        ShortcutManager.connect_shortcut(main_window, "clear_selection",
                                         lambda: CurveViewOperations.clear_selection(main_window.curve_view))
        # Nudging operations
        ShortcutManager.connect_shortcut(main_window, "nudge_up",
                                         lambda: CurveViewOperations.nudge_selected_points(main_window.curve_view, dy=-1))
        ShortcutManager.connect_shortcut(main_window, "nudge_down",
                                         lambda: CurveViewOperations.nudge_selected_points(main_window.curve_view, dy=1))
        ShortcutManager.connect_shortcut(main_window, "nudge_left",
                                         lambda: CurveViewOperations.nudge_selected_points(main_window.curve_view, dx=-1))
        ShortcutManager.connect_shortcut(main_window, "nudge_right",
                                         lambda: CurveViewOperations.nudge_selected_points(main_window.curve_view, dx=1))

        
        # View operations
        ShortcutManager.connect_shortcut(main_window, "reset_view", 
                                         lambda: CurveViewOperations.reset_view(main_window.curve_view))
        ShortcutManager.connect_shortcut(main_window, "toggle_grid", 
                                         lambda: VisualizationOperations.toggle_grid(
                                             main_window, 
                                             not main_window.toggle_grid_button.isChecked() 
                                             if hasattr(main_window, 'toggle_grid_button') else None
                                         ))
        ShortcutManager.connect_shortcut(main_window, "toggle_velocity", 
                                         lambda: VisualizationOperations.toggle_velocity_vectors(
                                             main_window, 
                                             not main_window.toggle_vectors_button.isChecked()
                                             if hasattr(main_window, 'toggle_vectors_button') else None
                                         ))
        ShortcutManager.connect_shortcut(main_window, "toggle_frame_numbers", 
                                         lambda: VisualizationOperations.toggle_all_frame_numbers(
                                             main_window, 
                                             not main_window.toggle_frame_numbers_button.isChecked()
                                             if hasattr(main_window, 'toggle_frame_numbers_button') else None
                                         ))
        ShortcutManager.connect_shortcut(main_window, "toggle_crosshair",
                                         lambda: VisualizationOperations.toggle_crosshair_internal(main_window.curve_view, not getattr(main_window.curve_view, 'show_crosshair', False)))
        ShortcutManager.connect_shortcut(main_window, "toggle_background",
                                         lambda: ImageOperations.toggle_background(main_window))
        ShortcutManager.connect_shortcut(main_window, "toggle_fullscreen",
                                         lambda: main_window.toggle_fullscreen() if hasattr(main_window, 'toggle_fullscreen') else None)
        ShortcutManager.connect_shortcut(main_window, "zoom_in",
                                         lambda: ZoomOperations.zoom_view(main_window.curve_view, 1.2)) # Zoom in by 20%
        ShortcutManager.connect_shortcut(main_window, "zoom_out",
                                         lambda: ZoomOperations.zoom_view(main_window.curve_view, 1 / 1.2)) # Zoom out by 20%
        ShortcutManager.connect_shortcut(main_window, "toggle_y_flip",
                                         lambda: setattr(main_window.curve_view, 'flip_y_axis', not getattr(main_window.curve_view, 'flip_y_axis', False)) or main_window.curve_view.update())
        ShortcutManager.connect_shortcut(main_window, "toggle_scale_to_image",
                                         lambda: setattr(main_window.curve_view, 'scale_to_image', not getattr(main_window.curve_view, 'scale_to_image', False)) or main_window.curve_view.update())
        ShortcutManager.connect_shortcut(main_window, "toggle_debug_mode",
                                         lambda: setattr(main_window.curve_view, 'debug_mode', not getattr(main_window.curve_view, 'debug_mode', False)) or main_window.curve_view.update())

        
        # Center on selected point
        ShortcutManager.connect_shortcut(main_window, "center_on_point", 
                                         lambda: VisualizationOperations.center_on_selected_point_from_main_window(main_window))
        
        # Timeline operations
        from ui_components import UIComponents
        ShortcutManager.connect_shortcut(main_window, "next_frame", 
                                         lambda: UIComponents.next_frame(main_window))
        ShortcutManager.connect_shortcut(main_window, "prev_frame", 
                                         lambda: UIComponents.prev_frame(main_window))
        ShortcutManager.connect_shortcut(main_window, "play_pause", 
                                         lambda: UIComponents.toggle_playback(main_window))
        ShortcutManager.connect_shortcut(main_window, "first_frame", 
                                         lambda: UIComponents.go_to_first_frame(main_window))
        ShortcutManager.connect_shortcut(main_window, "last_frame", 
                                         lambda: UIComponents.go_to_last_frame(main_window))
        ShortcutManager.connect_shortcut(main_window, "frame_forward_10",
                                         lambda: UIComponents.advance_frames(main_window, 10))
        ShortcutManager.connect_shortcut(main_window, "frame_back_10",
                                         lambda: UIComponents.advance_frames(main_window, -10))

        
        print("  ✓ Connected keyboard shortcuts")
        # Tools
        ShortcutManager.connect_shortcut(main_window, "smooth_selected",
                                         lambda: DialogOperations.show_smooth_dialog(main_window))
        ShortcutManager.connect_shortcut(main_window, "filter_selected",
                                         lambda: DialogOperations.show_filter_dialog(main_window))
        ShortcutManager.connect_shortcut(main_window, "detect_problems",
                                         lambda: DialogOperations.show_problem_detection_dialog(main_window, CurveOperations.detect_problems(main_window)))
