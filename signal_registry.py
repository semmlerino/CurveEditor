#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Signal Registry for 3DE4 Curve Editor.

This module provides a centralized registry for managing signal connections
throughout the application. It ensures consistent connection patterns and
error handling for all UI signals.
"""

from PySide6.QtCore import Qt
from curve_view_operations import CurveViewOperations
from visualization_operations import VisualizationOperations
from image_operations import ImageOperations
from dialog_operations import DialogOperations
from error_handling import show_error


class SignalRegistry:
    """Centralized registry for managing signal connections."""
    
    @staticmethod
    def connect_main_signals(main_window):
        """Connect all main window signals to their handlers.
        
        Args:
            main_window: The main application window
            
        This method serves as the central point for connecting all signals
        in the application. It organizes connections into logical groups
        and provides proper error handling for each connection.
        """
        # Store connections for potential cleanup
        main_window._signal_connections = []
        
        # Define connection groups with error handling
        signal_groups = {
            "curve_view": SignalRegistry._connect_curve_view_signals,
            "point_editing": SignalRegistry._connect_point_editing_signals,
            "file_operations": SignalRegistry._connect_file_operations_signals,
            "visualization": SignalRegistry._connect_visualization_signals,
            "timeline": SignalRegistry._connect_timeline_signals,
            "batch_edit": SignalRegistry._connect_batch_edit_signals,
            "dialogs": SignalRegistry._connect_dialog_signals
        }
        
        # Connect each group with proper error handling
        for group_name, connection_func in signal_groups.items():
            try:
                connection_func(main_window)
                print(f"Successfully connected {group_name} signals")
            except Exception as e:
                print(f"Error connecting {group_name} signals: {str(e)}")
                import traceback
                traceback.print_exc()
    
    @staticmethod
    def _connect_curve_view_signals(main_window):
        """Connect curve view signals for point selection and manipulation."""
        if hasattr(main_window, 'curve_view'):
            cv = main_window.curve_view
            
            # Use consistent connection pattern for all signals
            connections = [
                (cv.point_selected, lambda idx: CurveViewOperations.on_point_selected(main_window, idx)),
                (cv.point_moved, lambda idx, x, y: CurveViewOperations.on_point_moved(main_window, idx, x, y)),
                (cv.image_changed, main_window.on_image_changed)
            ]
            
            # Apply all connections with error checking
            for signal, slot in connections:
                try:
                    if hasattr(signal, 'connect'):  # Make sure signal exists
                        signal.connect(slot)
                        main_window._signal_connections.append((signal, slot))
                except Exception as e:
                    print(f"Error connecting signal {signal} to {slot}: {str(e)}")
    
    @staticmethod
    def _connect_point_editing_signals(main_window):
        """Connect signals for point editing controls."""
        try:
            # Point info update button
            if hasattr(main_window, 'update_point_button'):
                main_window.update_point_button.clicked.connect(
                    lambda: CurveViewOperations.update_point_from_edit(main_window)
                )
                
            # Enhanced point size control if available
            if hasattr(main_window, 'point_size_spin'):
                main_window.point_size_spin.valueChanged.connect(
                    lambda value: CurveViewOperations.set_point_size(main_window, value)
                )
        except Exception as e:
            print(f"Error connecting point editing signals: {str(e)}")
    
    @staticmethod
    def _connect_file_operations_signals(main_window):
        """Connect signals for file operations."""
        try:
            # Load/save/add buttons
            if hasattr(main_window, 'load_button'):
                main_window.load_button.clicked.connect(lambda: FileOperations.load_track_data(main_window))
                
            if hasattr(main_window, 'save_button'):
                main_window.save_button.clicked.connect(lambda: FileOperations.save_track_data(main_window))
                
            if hasattr(main_window, 'add_point_button'):
                main_window.add_point_button.clicked.connect(lambda: FileOperations.add_track_data(main_window))
        except Exception as e:
            print(f"Error connecting file operation signals: {str(e)}")
    
    @staticmethod
    def _connect_visualization_signals(main_window):
        """Connect signals for visualization controls."""
        try:
            # Basic view controls
            if hasattr(main_window, 'reset_view_button'):
                main_window.reset_view_button.clicked.connect(
                    lambda: CurveViewOperations.reset_view(main_window)
                )
                
            # Enhanced visualization controls if available
            if hasattr(main_window, 'toggle_grid_button'):
                main_window.toggle_grid_button.clicked.connect(
                    lambda checked: VisualizationOperations.toggle_grid(main_window, checked)
                )
                
            if hasattr(main_window, 'toggle_vectors_button'):
                main_window.toggle_vectors_button.clicked.connect(
                    lambda checked: VisualizationOperations.toggle_velocity_vectors(main_window, checked)
                )
                
            if hasattr(main_window, 'toggle_frame_numbers_button'):
                main_window.toggle_frame_numbers_button.clicked.connect(
                    lambda checked: VisualizationOperations.toggle_all_frame_numbers(main_window, checked)
                )
                
            if hasattr(main_window, 'toggle_crosshair_button'):
                main_window.toggle_crosshair_button.clicked.connect(
                    lambda checked: VisualizationOperations.toggle_crosshair(main_window, checked)
                )
                
            if hasattr(main_window, 'center_on_point_button'):
                main_window.center_on_point_button.clicked.connect(
                    lambda: VisualizationOperations.center_on_selected_point_from_main_window(main_window)
                )
                
            # Background controls
            if hasattr(main_window, 'toggle_bg_button'):
                main_window.toggle_bg_button.clicked.connect(
                    lambda: ImageOperations.toggle_background(main_window)
                )
                
            if hasattr(main_window, 'opacity_slider'):
                main_window.opacity_slider.valueChanged.connect(
                    lambda value: ImageOperations.opacity_changed(main_window, value)
                )
                
            if hasattr(main_window, 'load_images_button'):
                main_window.load_images_button.clicked.connect(
                    lambda: ImageOperations.load_image_sequence(main_window)
                )
        except Exception as e:
            print(f"Error connecting visualization signals: {str(e)}")
    
    @staticmethod
    def _connect_timeline_signals(main_window):
        """Connect signals for timeline and frame navigation."""
        from ui_components import UIComponents
        
        try:
            # Timeline slider
            if hasattr(main_window, 'timeline_slider'):
                main_window.timeline_slider.valueChanged.connect(
                    lambda value: UIComponents.on_timeline_changed(main_window, value)
                )
                
            # Frame controls
            if hasattr(main_window, 'frame_edit') and hasattr(main_window, 'go_button'):
                main_window.frame_edit.returnPressed.connect(
                    lambda: UIComponents.on_frame_edit_changed(main_window)
                )
                main_window.go_button.clicked.connect(
                    lambda: UIComponents.on_frame_edit_changed(main_window)
                )
                
            # Navigation buttons
            if hasattr(main_window, 'next_frame_button'):
                main_window.next_frame_button.clicked.connect(
                    lambda: UIComponents.next_frame(main_window)
                )
                
            if hasattr(main_window, 'prev_frame_button'):
                main_window.prev_frame_button.clicked.connect(
                    lambda: UIComponents.prev_frame(main_window)
                )
                
            if hasattr(main_window, 'play_button'):
                main_window.play_button.clicked.connect(
                    lambda: UIComponents.toggle_playback(main_window)
                )
                
            # Image navigation
            if hasattr(main_window, 'next_image_button'):
                main_window.next_image_button.clicked.connect(
                    lambda: ImageOperations.next_image(main_window)
                )
                
            if hasattr(main_window, 'prev_image_button'):
                main_window.prev_image_button.clicked.connect(
                    lambda: ImageOperations.previous_image(main_window)
                )
        except Exception as e:
            print(f"Error connecting timeline signals: {str(e)}")
    
    @staticmethod
    def _connect_batch_edit_signals(main_window):
        """Connect signals for batch editing operations."""
        try:
            # Batch edit buttons if they exist
            if hasattr(main_window, 'batch_edit_ui'):
                # These connections are already handled in batch_edit.py
                pass
                
            # History buttons
            if hasattr(main_window, 'undo_button'):
                main_window.undo_button.clicked.connect(main_window.undo_action)
                
            if hasattr(main_window, 'redo_button'):
                main_window.redo_button.clicked.connect(main_window.redo_action)
        except Exception as e:
            print(f"Error connecting batch edit signals: {str(e)}")
    
    @staticmethod
    def _connect_dialog_signals(main_window):
        """Connect signals for dialog operations."""
        try:
            # Tool dialog buttons
            if hasattr(main_window, 'smooth_button'):
                main_window.smooth_button.clicked.connect(
                    lambda: DialogOperations.show_smooth_dialog(main_window)
                )
                
            if hasattr(main_window, 'filter_button'):
                main_window.filter_button.clicked.connect(
                    lambda: DialogOperations.show_filter_dialog(main_window)
                )
                
            if hasattr(main_window, 'fill_gaps_button'):
                main_window.fill_gaps_button.clicked.connect(
                    lambda: DialogOperations.show_fill_gaps_dialog(main_window)
                )
                
            if hasattr(main_window, 'extrapolate_button'):
                main_window.extrapolate_button.clicked.connect(
                    lambda: DialogOperations.show_extrapolate_dialog(main_window)
                )
                
            if hasattr(main_window, 'detect_problems_button'):
                main_window.detect_problems_button.clicked.connect(
                    lambda: DialogOperations.show_problem_detection_dialog(
                        main_window, 
                        CurveOperations.detect_problems(main_window)
                    )
                )
        except Exception as e:
            print(f"Error connecting dialog signals: {str(e)}")