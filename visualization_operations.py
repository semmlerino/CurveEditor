#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Visualization operations for 3DE4 Curve Editor.
Provides functionality for curve visualization features like grid, vectors, and crosshair display.
"""

from PySide6.QtWidgets import QMessageBox


class VisualizationOperations:
    """Static utility methods for visualization operations in the curve editor."""
    
    @staticmethod
    def toggle_grid(main_window, checked):
        """Toggle grid visibility.
        
        Args:
            main_window: The main application window
            checked: Boolean indicating if grid should be shown
        """
        if hasattr(main_window.curve_view, 'toggleGrid'):
            main_window.curve_view.toggleGrid(checked)
            main_window.toggle_grid_button.setChecked(checked)
    
    @staticmethod
    def toggle_velocity_vectors(main_window, checked):
        """Toggle velocity vector display.
        
        Args:
            main_window: The main application window
            checked: Boolean indicating if vectors should be shown
        """
        if hasattr(main_window.curve_view, 'toggleVelocityVectors'):
            main_window.curve_view.toggleVelocityVectors(checked)
            main_window.toggle_vectors_button.setChecked(checked)
    
    @staticmethod
    def toggle_all_frame_numbers(main_window, checked):
        """Toggle display of all frame numbers.
        
        Args:
            main_window: The main application window
            checked: Boolean indicating if frame numbers should be shown
        """
        if hasattr(main_window.curve_view, 'toggleAllFrameNumbers'):
            main_window.curve_view.toggleAllFrameNumbers(checked)
            main_window.toggle_frame_numbers_button.setChecked(checked)
    
    @staticmethod
    def toggle_crosshair(main_window, checked):
        """Toggle crosshair visibility.
        
        Args:
            main_window: The main application window
            checked: Boolean indicating if crosshair should be shown
        """
        if hasattr(main_window.curve_view, 'toggleCrosshair'):
            main_window.curve_view.toggleCrosshair(checked)
            main_window.toggle_crosshair_button.setChecked(checked)
            main_window.statusBar().showMessage(f"Crosshair {'shown' if checked else 'hidden'}", 2000)
    
    @staticmethod
    def center_on_selected_point(main_window):
        """Center the view on the currently selected point.
        
        Args:
            main_window: The main application window
        """
        if not hasattr(main_window.curve_view, 'centerOnSelectedPoint'):
            main_window.statusBar().showMessage("Center on point not supported in basic view mode", 2000)
            return
        
        # Check first if we have selected points in the curve view
        if hasattr(main_window.curve_view, 'selected_points') and main_window.curve_view.selected_points:
            # Use the first selected point from the curve view's selection
            point_idx = list(main_window.curve_view.selected_points)[0]
            main_window.curve_view.centerOnSelectedPoint(point_idx)
            main_window.statusBar().showMessage(f"Centered view on point {point_idx}", 2000)
            return
            
        # Fallback to main_window.selected_indices
        if hasattr(main_window, 'selected_indices') and main_window.selected_indices:
            # Use the first selected point if multiple are selected
            point_idx = main_window.selected_indices[0]
            main_window.curve_view.centerOnSelectedPoint(point_idx)
            main_window.statusBar().showMessage(f"Centered view on point {point_idx}", 2000)
            return
            
        # If we get here, no point is selected
        main_window.statusBar().showMessage("No point selected to center on", 2000)
