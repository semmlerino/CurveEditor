#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from PyQt5.QtGui import QImage
import config


class ImageOperations:
    """Image operations for the 3DE4 Curve Editor."""
    
    @staticmethod
    def load_image_sequence(main_window):
        """Load an image sequence to use as background."""
        # Open file dialog to select the first image in a sequence
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            main_window,
            "Select First Image in Sequence",
            main_window.default_directory,
            "Image Files (*.jpg *.jpeg *.png *.tif *.tiff *.exr)",
            options=options
        )
        
        if not file_path:
            return  # User canceled
            
        # Get the directory and base filename
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        
        # Save the directory path to config
        config.set_last_folder_path(directory)
        
        # Save the image sequence path to config
        config.set_last_image_sequence_path(directory)
        
        # Try to determine the frame number format
        # Look for patterns like name.1234.ext or name_1234.ext
        base_name, frame_num, ext = ImageOperations._parse_filename(filename)
        if frame_num is None:
            QMessageBox.warning(
                main_window,
                "Invalid Sequence",
                "Could not determine frame numbering pattern in the selected file."
            )
            return
            
        # Find all matching files in the directory
        main_window.image_sequence_path = directory
        main_window.image_filenames = []
        
        # List all files in the directory
        all_files = os.listdir(directory)
        
        # Filter for files that match our pattern
        for file in all_files:
            if file.startswith(base_name) and file.endswith(ext):
                main_window.image_filenames.append(os.path.join(directory, file))
                
        # Sort the filenames
        main_window.image_filenames.sort()
        
        if not main_window.image_filenames:
            QMessageBox.warning(
                main_window,
                "No Images Found",
                "No image sequence found matching the selected file pattern."
            )
            return
            
        # Load the first image to get dimensions
        first_image = QImage(main_window.image_filenames[0])
        if not first_image.isNull():
            main_window.image_width = first_image.width()
            main_window.image_height = first_image.height()
            
        # Set the images in the curve view
        main_window.curve_view.setImageSequence(
            directory,
            main_window.image_filenames
        )
        
        # Update the UI
        main_window.update_image_label()
        main_window.toggle_bg_button.setEnabled(True)
        main_window.opacity_slider.setEnabled(True)
        
        # Show a success message
        QMessageBox.information(
            main_window,
            "Image Sequence Loaded",
            f"Loaded {len(main_window.image_filenames)} images from sequence."
        )
    
    @staticmethod
    def _parse_filename(filename):
        """Parse an image filename to extract base name, frame number, and extension."""
        # Split extension
        name_parts = filename.split('.')
        if len(name_parts) < 2:
            return None, None, None
            
        ext = '.' + name_parts[-1]
        
        # Try to find frame number
        # First check for name.1234.ext pattern
        if len(name_parts) > 2 and name_parts[-2].isdigit():
            frame_num = name_parts[-2]
            base_name = '.'.join(name_parts[:-2]) + '.'
            return base_name, frame_num, ext
            
        # Check for name_1234.ext pattern
        base_without_ext = '.'.join(name_parts[:-1])
        parts = base_without_ext.split('_')
        
        if len(parts) > 1 and parts[-1].isdigit():
            frame_num = parts[-1]
            base_name = '_'.join(parts[:-1]) + '_'
            return base_name, frame_num, ext
            
        return None, None, None
    
    @staticmethod
    def previous_image(main_window):
        """Show the previous image in the sequence."""
        if not main_window.image_filenames or main_window.curve_view.current_image_idx <= 0:
            return
            
        main_window.curve_view.setCurrentImageByIndex(main_window.curve_view.current_image_idx - 1)
        main_window.update_image_label()

    @staticmethod
    def next_image(main_window):
        """Show the next image in the sequence."""
        if not main_window.image_filenames or main_window.curve_view.current_image_idx >= len(main_window.image_filenames) - 1:
            return
            
        main_window.curve_view.setCurrentImageByIndex(main_window.curve_view.current_image_idx + 1)
        main_window.update_image_label()

    @staticmethod
    def update_image_label(main_window):
        """Update the image label with current image info."""
        if not main_window.image_filenames:
            main_window.image_label.setText("No images loaded")
            return
            
        idx = main_window.curve_view.current_image_idx
        if 0 <= idx < len(main_window.image_filenames):
            filename = os.path.basename(main_window.image_filenames[idx])
            main_window.image_label.setText(f"Image: {idx + 1}/{len(main_window.image_filenames)} - {filename}")
        else:
            main_window.image_label.setText("Invalid image index")

    @staticmethod
    def toggle_background(main_window):
        """Toggle background image visibility."""
        if not main_window.image_filenames:
            return
            
        visible = not main_window.curve_view.show_background
        main_window.curve_view.toggleBackgroundVisible(visible)
        main_window.toggle_bg_button.setText("Hide Background" if visible else "Show Background")

    @staticmethod
    def opacity_changed(main_window, value):
        """Handle opacity slider value changed."""
        opacity = value / 100.0  # Convert from 0-100 to 0.0-1.0
        main_window.curve_view.setBackgroundOpacity(opacity)

    @staticmethod
    def on_image_changed(main_window, index):
        """Handle image changed via keyboard navigation."""
        main_window.update_image_label()