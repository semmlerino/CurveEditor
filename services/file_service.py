#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FileService: Service class for file operations.
Provides functionality for loading, saving, and exporting track data.
"""

import os
from PySide6.QtWidgets import QFileDialog, QMessageBox
import utils
import config
import csv_export
from typing import TYPE_CHECKING
from services.logging_service import LoggingService
from services.protocols import MainWindowProtocol, FileServiceProtocol

# Configure logger for this module
logger = LoggingService.get_logger("file_service")

if TYPE_CHECKING:
    from main_window import MainWindow

class FileService:
    """Service class for file operations in the 3DE4 Curve Editor."""

    @staticmethod
    def export_to_csv(main_window: MainWindowProtocol) -> None:
        """Export tracking data to CSV format."""
        if not main_window.curve_data:
            QMessageBox.information(main_window, "Info", "No data to export.")
            return

        # Get output file path
        file_path, _ = QFileDialog.getSaveFileName(
            main_window, "Export to CSV",
            os.path.join(main_window.default_directory, "track_data.csv"),
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        # Call export function
        if csv_export.export_to_csv(file_path, main_window.curve_data):
            QMessageBox.information(main_window, "Success", "Data exported to CSV successfully.")
            main_window.status_bar.showMessage(f"Exported data to {file_path}", 3000)
        else:
            QMessageBox.critical(main_window, "Error", "Failed to export data.")

    @staticmethod
    def load_track_data(main_window: MainWindowProtocol) -> None:
        """Load 2D track data from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            main_window, "Load 2D Track Data", main_window.default_directory, "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        # Load track data from file
        point_name, point_color, num_frames, curve_data = utils.load_3de_track(file_path)

        if curve_data:
            # Set the data
            main_window.point_name = point_name
            main_window.point_color = point_color
            main_window.curve_data = curve_data

            # Determine image dimensions from the data
            main_window.image_width, main_window.image_height = utils.estimate_image_dimensions(curve_data)

            # Update view
            main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height)

            # Enable controls
            main_window.save_button.setEnabled(True)
            main_window.add_point_button.setEnabled(True)
            main_window.smooth_button.setEnabled(True)
            main_window.fill_gaps_button.setEnabled(True)
            main_window.filter_button.setEnabled(True)
            main_window.detect_problems_button.setEnabled(True)
            main_window.extrapolate_button.setEnabled(True)

            # Update info
            main_window.info_label.setText(f"Loaded: {main_window.point_name} ({len(main_window.curve_data)} frames)")

            # Setup timeline
            main_window.setup_timeline()

            # Enable timeline controls
            main_window.timeline_slider.setEnabled(True)
            main_window.frame_edit.setEnabled(True)
            main_window.go_button.setEnabled(True)

            # Save the file path to config
            config.set_last_file_path(file_path)

            # Save the directory path to config
            directory = os.path.dirname(file_path)
            config.set_last_folder_path(directory)

            # Add to history
            main_window.add_to_history()
        else:
            QMessageBox.critical(main_window, "Error", "Failed to load track data.")

    @staticmethod
    def add_track_data(main_window: MainWindowProtocol) -> None:
        """Add an additional 2D track to the current data."""
        if not main_window.curve_data:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            main_window, "Add 2D Track Data", main_window.default_directory, "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        # Load track data from file
        _, _, _, additional_data = utils.load_3de_track(file_path)

        if additional_data:
            # Check frame compatibility
            existing_frames = {frame for frame, _, _ in main_window.curve_data}
            new_frames = {frame for frame, _, _ in additional_data}

            if existing_frames != new_frames:
                if QMessageBox.question(main_window, "Frame Mismatch",
                                       "The frames in the new track don't exactly match the current data. Continue anyway?",
                                       QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
                    return

            # Merge data - replace points with same frame, add new ones
            # Convert coordinates to normalized space before merging
            current_width, current_height = main_window.image_width, main_window.image_height

            # Get original dimensions from additional data
            orig_width, orig_height = utils.estimate_image_dimensions(additional_data)

            # Merge data with coordinate conversion
            merged_data = {}
            for frame, x, y in main_window.curve_data:
                merged_data[frame] = (x, y)

            for frame, x, y in additional_data:
                # Normalize to original image space
                logger.debug(f"Original coordinates - Frame {frame}: X={x}, Y={y}")
                logger.debug(f"Original image dimensions: {orig_width}x{orig_height}")

                norm_x = x / orig_width
                norm_y = y / orig_height
                logger.debug(f"Normalized coordinates: X={norm_x:.4f}, Y={norm_y:.4f}")

                # Convert to current image space
                scaled_x = norm_x * current_width
                scaled_y = norm_y * current_height
                logger.debug(f"Scaled coordinates: X={scaled_x:.1f}, Y={scaled_y:.1f} (Current dimensions: {current_width}x{current_height})")

                merged_data[frame] = (scaled_x, scaled_y)

            # Convert back to list and sort by frame
            main_window.curve_data = [(frame, x, y) for frame, (x, y) in sorted(merged_data.items())]

            # Update view
            main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height)

            # Update info
            main_window.info_label.setText(f"Loaded: {main_window.point_name} ({len(main_window.curve_data)} frames)")

            # Update timeline
            main_window.setup_timeline()

            # Add to history
            main_window.add_to_history()
        else:
            QMessageBox.critical(main_window, "Error", "Failed to load additional track data.")

    @staticmethod
    def save_track_data(main_window: MainWindowProtocol) -> None:
        """Save modified 2D track data to a file."""
        if not main_window.curve_data:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            main_window, "Save 2D Track Data", main_window.default_directory, "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        # Save track data to file
        if utils.save_3de_track(file_path, main_window.point_name, main_window.point_color, main_window.curve_data):
            QMessageBox.information(main_window, "Success", "Track data saved successfully.")

            # Save the directory path to config
            directory = os.path.dirname(file_path)
            config.set_last_folder_path(directory)
        else:
            QMessageBox.critical(main_window, "Error", "Failed to save track data.")

    @staticmethod
    def load_image_sequence(main_window: MainWindowProtocol) -> None:
        """Load an image sequence to use as background."""
        directory = QFileDialog.getExistingDirectory(
            main_window, "Select Image Sequence Directory", main_window.default_directory
        )

        if not directory:
            return

        # Look for image files in the directory
        filenames = utils.get_image_files(directory)

        if not filenames:
            QMessageBox.warning(main_window, "Warning", "No image files found in the selected directory.")
            return

        # Set the image sequence
        main_window.image_sequence_path = directory
        main_window.image_filenames = filenames

        # Setup the curve view with images
        main_window.curve_view.setImageSequence(directory, filenames)

        # Enable image controls
        main_window.toggle_bg_button.setEnabled(True)
        main_window.prev_image_button.setEnabled(True)
        main_window.next_image_button.setEnabled(True)
        main_window.opacity_slider.setEnabled(True)

        # Update label
        main_window.update_image_label()
        
        # Save the directory path to config
        config.set_last_image_sequence_path(directory)

    @staticmethod
    def load_previous_file(main_window: MainWindowProtocol) -> None:
        """Load the previously used file and folder if they exist."""
        # Check for last folder path and update default directory
        folder_path = config.get_last_folder_path()
        if folder_path and os.path.exists(folder_path):
            main_window.default_directory = folder_path

        # Load last file if it exists
        file_path = config.get_last_file_path()
        if file_path and os.path.exists(file_path):
            # Load track data from file
            point_name, point_color, _num_frames, curve_data = utils.load_3de_track(file_path)

            if curve_data:
                # Set the data
                main_window.point_name = point_name if isinstance(point_name, str) else ""
                main_window.point_color = str(point_color) if point_color is not None else config.DEFAULT_POINT_COLOR
                main_window.curve_data = curve_data

                # Determine image dimensions from the data
                main_window.image_width, main_window.image_height = utils.estimate_image_dimensions(curve_data)

                # Update view
                main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height)

                # Enable controls (guarded for robustness)
                if hasattr(main_window, "save_button"):
                    main_window.save_button.setEnabled(True)
                if hasattr(main_window, "add_point_button"):
                    main_window.add_point_button.setEnabled(True)
                if hasattr(main_window, "smooth_button"):
                    main_window.smooth_button.setEnabled(True)
                if hasattr(main_window, "fill_gaps_button"):
                    main_window.fill_gaps_button.setEnabled(True)
                if hasattr(main_window, "filter_button"):
                    main_window.filter_button.setEnabled(True)
                if hasattr(main_window, "detect_problems_button"):
                    main_window.detect_problems_button.setEnabled(True)
                if hasattr(main_window, "extrapolate_button"):
                    main_window.extrapolate_button.setEnabled(True)

                # Update info
                main_window.info_label.setText(f"Loaded: {main_window.point_name} ({len(main_window.curve_data)} frames)")

                # Setup timeline
                main_window.setup_timeline()

                # Enable timeline controls
                main_window.timeline_slider.setEnabled(True)
                main_window.frame_edit.setEnabled(True)
                main_window.go_button.setEnabled(True)

                # Add to history
                main_window.add_to_history()

        # Load last image sequence if it exists
        FileService.load_previous_image_sequence(main_window)

    @staticmethod
    def load_previous_image_sequence(main_window: MainWindowProtocol) -> None:
        """Load the previously used image sequence if it exists."""
        # Check for last image sequence path
        sequence_path = config.get_last_image_sequence_path()
        if sequence_path and os.path.exists(sequence_path):
            # Find all image files in the directory
            image_files = utils.get_image_files(sequence_path)

            if image_files:
                # Set the image sequence
                main_window.image_sequence_path = sequence_path
                main_window.image_filenames = image_files

                # Setup the curve view with images
                main_window.curve_view.setImageSequence(sequence_path, image_files)

                # Update the UI
                main_window.update_image_label()
                main_window.toggle_bg_button.setEnabled(True)
