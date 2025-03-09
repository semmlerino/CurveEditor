#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from PySide6.QtWidgets import QMessageBox, QFileDialog
from PySide6.QtGui import QImage
import config


class ImageOperations:
    """Image operations for the 3DE4 Curve Editor."""
    
    @staticmethod
    def set_current_image_by_frame(curve_view, frame):
        """Set the current background image based on frame number.
        
        Args:
            curve_view: The curve view instance
            frame: Frame number to find the closest image for
        """
        if not curve_view.image_filenames:
            return
            
        # Find the closest image index to the requested frame
        closest_idx = -1
        min_diff = float('inf')
        
        for i, filename in enumerate(curve_view.image_filenames):
            # Try to extract frame number from filename
            try:
                # Common formats: name.####.ext or name_####.ext
                parts = os.path.basename(filename).split('.')
                if len(parts) >= 2 and parts[-2].isdigit():
                    img_frame = int(parts[-2])
                else:
                    # Try underscore format
                    name_parts = parts[0].split('_')
                    if name_parts[-1].isdigit():
                        img_frame = int(name_parts[-1])
                    else:
                        # Just use sequential index if can't parse frame
                        img_frame = i
            except:
                img_frame = i
                
            diff = abs(img_frame - frame)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
                
        if closest_idx >= 0 and closest_idx < len(curve_view.image_filenames):
            curve_view.current_image_idx = closest_idx
            ImageOperations.load_current_image(curve_view)
            curve_view.update()
    
    @staticmethod
    def load_current_image(curve_view):
        """Load the current image in the sequence.
        
        Args:
            curve_view: The curve view instance containing image properties
        """
        if curve_view.current_image_idx < 0 or not curve_view.image_filenames:
            curve_view.background_image = None
            return
            
        try:
            # Get path to current image
            image_path = os.path.join(curve_view.image_sequence_path, curve_view.image_filenames[curve_view.current_image_idx])
            print(f"ImageOperations: Loading image: {image_path}")
            
            # Load image using PySide6.QtGui.QImage
            image = QImage(image_path)
            
            # Make sure we have focus to receive keyboard events
            curve_view.setFocus()
            
            if image.isNull():
                print(f"ImageOperations: Failed to load image: {image_path}")
                curve_view.background_image = None
            else:
                print(f"ImageOperations: Successfully loaded image from: {image_path}")
                curve_view.background_image = image
                
                # Update track dimensions to match image dimensions
                if curve_view.scale_to_image:
                    curve_view.image_width = image.width()
                    curve_view.image_height = image.height()
                    
                # Emit the image_changed signal
                print(f"ImageOperations: Emitting image_changed signal for idx={curve_view.current_image_idx}")
                curve_view.image_changed.emit(curve_view.current_image_idx)
        except Exception as e:
            print(f"ImageOperations: Error loading image: {str(e)}")
            curve_view.background_image = None
    
    @staticmethod
    def set_current_image_by_index(curve_view, idx):
        """Set current image by index and update the view.
        
        Args:
            curve_view: The curve view instance
            idx: Index of the image to display
        """
        if idx < 0 or idx >= len(curve_view.image_filenames):
            print(f"ImageOperations: Invalid image index: {idx}")
            return
            
        # Store current zoom factor and view offsets
        current_zoom = curve_view.zoom_factor
        current_offset_x = curve_view.offset_x
        current_offset_y = curve_view.offset_y
        
        # Store current center position before changing the image
        center_pos = None
        if curve_view.selected_point_idx >= 0 and hasattr(curve_view, 'main_window') and curve_view.main_window.curve_data:
            # Remember center point if we have a selected point
            try:
                point = curve_view.main_window.curve_data[curve_view.selected_point_idx]
                center_pos = (point[1], point[2])  # x, y coordinates
                print(f"ImageOperations: Storing center position at {center_pos}")
            except (IndexError, AttributeError) as e:
                print(f"ImageOperations: Could not store center position: {str(e)}")
        
        # Update image index and load the image
        curve_view.current_image_idx = idx
        ImageOperations.load_current_image(curve_view)
        
        # Restore the zoom factor that was in effect before switching images
        print(f"ImageOperations: Preserving zoom factor of {current_zoom}")
        curve_view.zoom_factor = current_zoom
        
        # After changing the image, center on the selected point using our improved function
        if curve_view.selected_point_idx >= 0:
            success = curve_view.centerOnSelectedPoint(preserve_zoom=True)
            if success:
                print(f"ImageOperations: Successfully centered on point {curve_view.selected_point_idx}")
            else:
                print(f"ImageOperations: Could not center on point {curve_view.selected_point_idx}")
                # If centering fails, restore previous view position
                curve_view.offset_x = current_offset_x
                curve_view.offset_y = current_offset_y
        else:
            # If no point is selected, at least maintain the zoom level
            curve_view.offset_x = current_offset_x
            curve_view.offset_y = current_offset_y
        
        curve_view.update()
        curve_view.setFocus()
    
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
    
    @staticmethod
    def set_image_sequence(curve_view, path, filenames):
        """Set the image sequence to display as background.
        
        Args:
            curve_view: The curve view instance
            path: Path to the directory containing the image sequence
            filenames: List of image filenames in the sequence
        """
        curve_view.image_sequence_path = path
        curve_view.image_filenames = filenames
        curve_view.current_image_idx = 0 if filenames else -1
        ImageOperations.load_current_image(curve_view)
        curve_view.update()