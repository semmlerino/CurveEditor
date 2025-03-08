#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QMessageBox


class TimelineOperations:
    """Timeline operations for the 3DE4 Curve Editor."""
    
    @staticmethod
    def setup_timeline(main_window):
        """Setup timeline slider based on frame range."""
        if not main_window.curve_data:
            return
            
        # Get frame range
        frames = [frame for frame, _, _ in main_window.curve_data]
        min_frame = min(frames)
        max_frame = max(frames)
        
        # Set slider range
        main_window.timeline_slider.setMinimum(min_frame)
        main_window.timeline_slider.setMaximum(max_frame)
        
        # Update frame label
        main_window.frame_label.setText(f"Frame range: {min_frame}-{max_frame}")
        
        # Initialize to first frame
        main_window.timeline_slider.setValue(min_frame)
        main_window.frame_edit.setText(str(min_frame))

    @staticmethod
    def on_timeline_changed(main_window, value):
        """Handle timeline slider value changed."""
        # Update frame edit
        main_window.frame_edit.setText(str(value))
        
        # Find the point with the closest frame
        closest_idx = -1
        closest_diff = float('inf')
        
        for i, (frame, _, _) in enumerate(main_window.curve_data):
            diff = abs(frame - value)
            if diff < closest_diff:
                closest_diff = diff
                closest_idx = i
                # Exit early if exact match
                if diff == 0:
                    break
        
        # Select the point if found
        if closest_idx >= 0:
            main_window.curve_view.selected_point_idx = closest_idx
            main_window.curve_view.update()
            
            # Update point info
            frame, x, y = main_window.curve_data[closest_idx]
            main_window.update_point_info(closest_idx, x, y)
            
            # Update the image if available
            if main_window.image_filenames:
                main_window.curve_view.setCurrentImageByFrame(frame)
                main_window.update_image_label()

    @staticmethod
    def on_frame_edit_changed(main_window):
        """Handle frame edit text changed."""
        try:
            frame = int(main_window.frame_edit.text())
            main_window.timeline_slider.setValue(frame)
        except ValueError:
            pass