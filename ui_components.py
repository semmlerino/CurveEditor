#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI Components for 3DE4 Curve Editor.

This module contains the UIComponents class which centralizes all UI-related functionality
for the Curve Editor application. It handles the creation, arrangement, and signal connections
for all user interface elements in a consistent and maintainable way.

The module follows these key principles:
1. All UI component creation is centralized in static methods
2. All signal connections are managed through the connect_all_signals method
3. Proper error handling and defensive programming techniques are used
4. Clear separation between UI creation and application logic

This architecture ensures that:
- UI components are created consistently
- Signal connections are managed in a single location
- The code is more maintainable and easier to extend
- Components are properly checked before signals are connected
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QLineEdit,
    QGroupBox, QToolBar, QFrame,
    QGridLayout, QComboBox, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont, QPainter, QPainterPath, QColor, QPaintEvent, QMouseEvent
from typing import Optional, Any, cast

from services.curve_service import CurveService as CurveViewOperations
from services.image_service import ImageService as ImageOperations
from services.dialog_service import DialogService as DialogOperations
# from curve_operations import CurveOperations # Removed, logic moved
from services.history_service import HistoryService as HistoryOperations # For undo/redo
from services.centering_zoom_service import CenteringZoomService  # Use service facade for auto centering
from services.visualization_service import VisualizationService  # For visualization operations

from enhanced_curve_view import EnhancedCurveView  # type: ignore[attr-defined]

# Import component modules (refactored from this file)
from timeline_components import TimelineFrameMarker, TimelineComponents
from point_edit_components import PointEditComponents
from toolbar_components import ToolbarComponents
from status_components import StatusComponents
from visualization_components import VisualizationComponents
from smoothing_components import SmoothingComponents


class UIComponents:
    """Centralized management of all UI components for the Curve Editor application.

    This class follows a utility pattern with static methods for creating, arranging,
    and connecting UI components. It serves as a single point of control for all
    UI-related operations, improving code organization and maintainability.

    Key responsibilities:
    - Creating and arranging UI widgets and layouts
    - Centralizing signal connections through connect_all_signals
    - Providing utility methods for UI operations
    - Ensuring proper error handling for UI components

    Note:
    All methods are static and take a MainWindow instance as the first parameter.
    This design allows for separation of UI component management from application logic.
    """

    @staticmethod
    def create_toolbar(main_window: Any) -> QWidget:
        """Create a more organized toolbar with action buttons grouped by function.

        This method delegates to ToolbarComponents.create_toolbar for the actual implementation.
        """
        return ToolbarComponents.create_toolbar(main_window)

    @staticmethod
    def _create_curve_view(main_window: Any) -> QWidget:
        """Create the curve view container and view widget.

        This helper method centralizes curve view creation used by multiple methods.

        Args:
            main_window: The main application window instance

        Returns:
            QWidget: The curve view container widget with curve view inside
        """
        # Create curve view container
        curve_view_container = QWidget()
        curve_view_layout = QVBoxLayout(curve_view_container)
        curve_view_layout.setContentsMargins(0, 0, 0, 0)
        main_window.curve_view_container = curve_view_container

        # Create curve view
        if hasattr(main_window, 'curve_view_class') and issubclass(main_window.curve_view_class, EnhancedCurveView):
            main_window.curve_view = main_window.curve_view_class()
            main_window.original_curve_view = main_window.curve_view  # Store reference to original view
        else:
            main_window.curve_view = EnhancedCurveView()
            main_window.original_curve_view = main_window.curve_view  # Store reference to original view

        curve_view_layout.addWidget(main_window.curve_view)

        return curve_view_container

    @staticmethod
    def create_view_and_timeline_separated(main_window: Any) -> tuple[QWidget, QWidget]:
        """Create and return the curve view and timeline controls as separate widgets.

        This method creates the curve view and timeline components separately,
        allowing the UI to place them with a splitter exactly at their boundary.

        Returns:
            tuple[QWidget, QWidget]: A tuple containing (curve_view_container, timeline_widget)
        """
        # Create curve view using the common helper method
        curve_view_container = UIComponents._create_curve_view(main_window)

        # Create timeline widget separately
        timeline_widget = UIComponents._create_timeline_widget(main_window)

        return curve_view_container, timeline_widget

    @staticmethod
    def _create_timeline_widget(main_window: Any) -> QWidget:
        """Create the timeline widget as a separate component.

        This is a helper method for create_view_and_timeline_separated.
        """
        # Timeline widget
        timeline_widget = QWidget()
        timeline_layout = QVBoxLayout(timeline_widget)
        timeline_layout.setContentsMargins(0, 0, 0, 0)

        # Image sequence controls
        image_controls = QHBoxLayout()
        main_window.prev_image_button = QPushButton("Previous")
        main_window.prev_image_button.clicked.connect(lambda: ImageOperations.previous_image(main_window))
        main_window.prev_image_button.setEnabled(False)

        main_window.next_image_button = QPushButton("Next")
        main_window.next_image_button.clicked.connect(lambda: ImageOperations.next_image(main_window))
        main_window.next_image_button.setEnabled(False)

        main_window.image_label = QLabel("No images loaded")

        # Point size slider
        main_window.point_size_slider = QSlider(Qt.Orientation.Horizontal)
        main_window.point_size_slider.setMinimum(1)
        main_window.point_size_slider.setMaximum(20)
        main_window.point_size_slider.setValue(main_window.curve_view.point_radius)
        main_window.point_size_slider.setEnabled(True)

        # Typed slot for point size slider
        def on_point_size_changed(value: int) -> None:
            main_window.curve_view.set_point_radius(value)
        main_window.point_size_slider.valueChanged.connect(on_point_size_changed)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Point Size:"))
        size_layout.addWidget(main_window.point_size_slider)

        image_controls.addWidget(main_window.prev_image_button)
        image_controls.addWidget(main_window.image_label)
        image_controls.addWidget(main_window.next_image_button)
        image_controls.addStretch()
        image_controls.addLayout(size_layout)

        timeline_layout.addLayout(image_controls)

        # Delegate timeline controls creation to TimelineComponents
        timeline_controls_widget = TimelineComponents.create_timeline_widget(
            main_window=main_window,
            on_timeline_changed=UIComponents.on_timeline_changed,
            on_timeline_press=lambda mw, ev: UIComponents._handle_timeline_press(mw, ev),
            toggle_playback=UIComponents.toggle_playback,
            prev_frame=UIComponents.prev_frame,
            next_frame=UIComponents.next_frame,
            go_to_first_frame=UIComponents.go_to_first_frame,
            go_to_last_frame=UIComponents.go_to_last_frame,
            on_frame_edit_changed=UIComponents.on_frame_edit_changed
        )

        # Extract the timeline controls from the created widget and add to our layout
        if timeline_controls_widget.layout():
            # Move all items from the timeline controls widget to our layout
            controls_layout = timeline_controls_widget.layout()
            while controls_layout.count():
                item = controls_layout.takeAt(0)
                if item.widget():
                    timeline_layout.addWidget(item.widget())
                elif item.layout():
                    timeline_layout.addLayout(item.layout())

        return timeline_widget


    @staticmethod
    def create_view_and_timeline(main_window: Any) -> QWidget:
        """Create the curve view widget and timeline controls in a single container.

        This method uses the same helper methods as create_view_and_timeline_separated
        but combines the components into a single widget for simpler integration.

        Args:
            main_window: The main application window instance

        Returns:
            QWidget: A container widget with curve view and timeline
        """
        # Container for view and timeline
        view_container = QWidget()
        view_layout = QVBoxLayout(view_container)
        view_layout.setContentsMargins(0, 0, 0, 0)

        # Create curve view using the common helper method
        curve_view_container = UIComponents._create_curve_view(main_window)
        view_layout.addWidget(curve_view_container)

        # Create timeline widget using the existing helper method
        timeline_widget = UIComponents._create_timeline_widget(main_window)
        view_layout.addWidget(timeline_widget)

        return view_container

    @staticmethod
    def create_control_panel(main_window: Any) -> QWidget:
        """
        Create the control panel for point editing and view controls.

        The control panel consists of three main sections:

        1. Left Panel - Point Info and Editing:
           - Displays current frame information.
           - Allows user input for X and Y coordinates of a point.
           - Includes buttons for updating point data and managing selection.

        2. Center Panel - Visualization Controls:
           - Provides toggles for grid, vectors, frame numbers, and crosshair visibility.
           - Includes a button to center the view on the selected point.
           - Offers a spin box to adjust point size.

        3. Right Panel - Track Quality and Presets:
           - Displays quality metrics such as overall score, smoothness, consistency, and coverage.
           - Features an analyze button to evaluate track quality.
           - Includes quick filter presets for data processing.

        All controls are initially disabled and are connected to main window operations for functionality.
        """
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)

        # Left side: Point Info and Editing
        left_panel = PointEditComponents.create_point_info_panel(main_window)

        # Center: Visualization Controls
        center_panel = VisualizationComponents.create_visualization_panel(main_window)

        # Right side: Track Quality and Presets
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Add inline smoothing controls
        smoothing_group = SmoothingComponents.create_smoothing_panel(main_window)
        right_layout.addWidget(smoothing_group)

        # Track Quality Group
        quality_group = StatusComponents.create_track_quality_panel(main_window)
        right_layout.addWidget(quality_group)

        # Quick Filter Presets Group
        presets_group = StatusComponents.create_quick_filter_presets(main_window)
        right_layout.addWidget(presets_group)

        right_layout.addStretch()

        controls_layout.addWidget(left_panel)
        controls_layout.addWidget(center_panel)
        controls_layout.addWidget(right_panel)

        main_window.enable_point_controls(False)

        # Connect smoothing signal
        main_window.smoothing_apply_button.clicked.connect(main_window.apply_ui_smoothing)

        return controls_container

    @staticmethod
    def create_enhanced_curve_view(main_window: Any) -> bool:
        """Create and set up the enhanced curve view."""
        try:
            # Create the enhanced curve view
            enhanced_view = EnhancedCurveView(main_window)

            # Replace standard view with enhanced view
            if hasattr(main_window, 'curve_view_container') and hasattr(main_window, 'curve_view'):
                main_window.curve_view_container.layout().removeWidget(main_window.curve_view)
                main_window.curve_view.deleteLater()

                # Set the new enhanced view
                main_window.curve_view = enhanced_view
                main_window.curve_view_container.layout().addWidget(main_window.curve_view)

                # Typed slots for enhanced view signals
                def on_point_selected_slot(idx: int) -> None:
                    CurveViewOperations.on_point_selected(main_window.curve_view, main_window, idx)
                def on_point_moved_slot(idx: int, x: float, y: float) -> None:
                    CurveViewOperations.on_point_moved(main_window, idx, x, y)
                def on_image_changed_slot(index: int) -> None:
                    main_window.on_image_changed(index)
                main_window.curve_view.point_selected.connect(on_point_selected_slot)
                main_window.curve_view.point_moved.connect(on_point_moved_slot)
                main_window.curve_view.image_changed.connect(on_image_changed_slot)

                # Use the visualization service for timeline updates
                # Create a wrapper method that calls the visualization service method

                def update_timeline_for_image(index: int) -> None:
                    """Wrapper method to update the timeline for the current image."""
                    VisualizationService.update_timeline_for_image(
                        index, main_window.curve_view, main_window.image_filenames
                    )

                # Attach the wrapper method to the curve view for backward compatibility
                # Assign the wrapper method to the curve view for backward compatibility
                main_window.curve_view.updateTimelineForImage = update_timeline_for_image  # type: ignore[attr-defined]

                return True
        except Exception:
            return False
        return False

    @staticmethod
    def setup_timeline(main_window: Any) -> None:
        """Setup timeline slider based on frame range."""
        # ... (Code as before) ...
        if not main_window.curve_data:
            main_window.timeline_slider.setEnabled(False)
            main_window.frame_edit.setEnabled(False)
            main_window.go_button.setEnabled(False)
            main_window.play_button.setEnabled(False)
            main_window.prev_frame_button.setEnabled(False)
            main_window.next_frame_button.setEnabled(False)
            main_window.first_frame_button.setEnabled(False)
            main_window.last_frame_button.setEnabled(False)
            return

        # Get frame range from data
        frames = [p[0] for p in main_window.curve_data]
        min_frame = min(frames) if frames else 0
        max_frame = max(frames) if frames else 0
        frame_count = max_frame - min_frame + 1

        # Update slider range
        main_window.timeline_slider.setMinimum(min_frame)
        main_window.timeline_slider.setMaximum(max_frame)

        # Update tick interval based on new range
        tick_interval = max(1, frame_count // 100)
        main_window.timeline_slider.setTickInterval(tick_interval)

        # Set current frame if not already set or out of range
        if main_window.current_frame < min_frame or main_window.current_frame > max_frame:
            main_window.current_frame = min_frame

        # Update slider value without triggering signals initially
        main_window.timeline_slider.blockSignals(True)
        main_window.timeline_slider.setValue(main_window.current_frame)
        main_window.timeline_slider.blockSignals(False)

        # Update labels and edit fields
        main_window.frame_label.setText(f"Frame: {main_window.current_frame}")
        main_window.frame_edit.setText(str(main_window.current_frame))

        # Update frame marker position
        if hasattr(main_window, 'frame_marker'):
            main_window.frame_marker.setPosition(0)  # Start at beginning

        print(f"UIComponents: Timeline setup complete with {frame_count} discrete frames from {min_frame} to {max_frame}")

    @staticmethod
    def on_timeline_changed(main_window: Any, value: int) -> None:
        """Handle timeline slider value changed with enhanced feedback."""
        main_window.current_frame = value

        # Update frame edit and label
        main_window.frame_edit.setText(str(value))
        main_window.frame_label.setText(f"Frame: {value}")

        # Update tooltip to show current frame
        main_window.timeline_slider.setToolTip(f"Frame: {value}")

        # Update the frame marker position
        if hasattr(main_window, 'frame_marker'):
            # Use extracted helper method for position calculation
            slider_min = main_window.timeline_slider.minimum()
            slider_max = main_window.timeline_slider.maximum()
            position_ratio = UIComponents._calculate_marker_position(slider_min, slider_max, value)
            main_window.frame_marker.setPosition(position_ratio)
            main_window.frame_marker.update()

        # Load the corresponding image if we have an image sequence
        if main_window.image_filenames:
            # Update the image by frame
            main_window.curve_view.setCurrentImageByFrame(value)
            main_window.update_image_label()

        # Auto-center if enabled
        if getattr(main_window, 'auto_center_enabled', False):
            try:
                CenteringZoomService.auto_center_view(main_window, preserve_zoom=True)
            except Exception as e:
                print(f"Error during auto-centering: {e}")

        # Select the closest point for highlighting
        if hasattr(main_window, 'curve_data') and main_window.curve_data:
            closest_frame = min(main_window.curve_data, key=lambda p: abs(p[0] - main_window.current_frame))[0]
            for i, pt in enumerate(main_window.curve_data):
                if pt[0] == closest_frame:
                    main_window.curve_view.selected_point_idx = i
                    main_window.curve_view.selected_points = {i}
                    break

        # Update point type(s) for selected points on current frame
        if hasattr(main_window, 'type_edit') and hasattr(main_window.curve_view, 'get_selected_indices'):
            selected = main_window.curve_view.get_selected_indices()
            statuses: list[str] = []
            for idx in selected:
                if main_window.curve_data and idx < len(main_window.curve_data) and main_window.curve_data[idx][0] == value:
                    point = main_window.curve_data[idx]
                    status = point[3] if len(point) > 3 else 'normal'
                    statuses.append(status)
            statuses = sorted(set(statuses))
            main_window.type_edit.setText(', '.join(statuses) if statuses else '')

        # Update view AFTER potential centering
        main_window.curve_view.update() # Ensure view updates

    @staticmethod
    def on_frame_edit_changed(main_window: Any) -> None:
        """Handle frame edit text changed."""
        try:
            value = int(main_window.frame_edit.text())
            min_val = main_window.timeline_slider.minimum()
            max_val = main_window.timeline_slider.maximum()

            if min_val <= value <= max_val:
                # Directly call go_to_frame to ensure consistent handling including centering
                UIComponents.go_to_frame(main_window, value)
            else:
                main_window.statusBar().showMessage(f"Frame {value} out of range ({min_val}-{max_val})", 2000)
        except ValueError:
            main_window.statusBar().showMessage("Invalid frame number entered", 2000)

    @staticmethod
    def toggle_playback(main_window: Any) -> None:
        """Toggle timeline playback on/off."""
        # ... (Code as before) ...
        # If playback is already active, stop it
        if hasattr(main_window, 'playback_timer') and main_window.playback_timer.isActive():
            main_window.playback_timer.stop()
            main_window.play_button.setChecked(False)
            main_window.statusBar().showMessage("Playback stopped", 2000)
            return

        # Create timer if it doesn't exist
        if not hasattr(main_window, 'playback_timer'):
            main_window.playback_timer = QTimer(main_window)
            main_window.playback_timer.timeout.connect(lambda: UIComponents.advance_playback(main_window))

        # Start playback
        # TODO: Add FPS setting
        fps = 24 # Default FPS
        main_window.playback_timer.start(1000 // fps)
        main_window.play_button.setChecked(True)
        main_window.statusBar().showMessage("Playback started", 2000)

    @staticmethod
    def advance_playback(main_window: Any) -> None:
        """Advance timeline by one frame during playback."""
        current_frame = main_window.timeline_slider.value()
        max_frame = main_window.timeline_slider.maximum()

        if current_frame < max_frame:
            # Use advance_frames with display_message=False to avoid cluttering status bar during playback
            # Special case: don't use advance_frames directly to avoid its status message
            main_window.timeline_slider.setValue(current_frame + 1)
            # We don't call auto-centering here as it's handled by the slider value change signal
        else:
            # Stop playback at the end
            main_window.playback_timer.stop()
            main_window.play_button.setChecked(False)
            main_window.statusBar().showMessage("Playback finished", 2000)

    @staticmethod
    def next_frame(main_window: Any) -> None:
        """Go to the next frame in the timeline."""
        UIComponents.advance_frames(main_window, 1)

    @staticmethod
    def prev_frame(main_window: Any) -> None:
        """Go to the previous frame in the timeline."""
        UIComponents.advance_frames(main_window, -1)

    @staticmethod
    def _apply_auto_centering(main_window: Any, source_func: str = "") -> None:
        """Apply auto-centering if enabled.

        This utility method centralizes the auto-centering logic used by multiple timeline methods,
        following the DRY principle.

        Args:
            main_window: The main application window instance
            source_func: Optional name of the calling function for error reporting
        """
        if getattr(main_window, 'auto_center_enabled', False):
            try:
                CenteringZoomService.auto_center_view(main_window, preserve_zoom=True)
            except Exception as e:
                print(f"Error during auto-centering in {source_func}: {e}")

    @staticmethod
    def advance_frames(main_window: Any, count: int) -> None:
        """Advance timeline by specified number of frames (positive or negative)."""
        if not main_window.curve_data:
            return

        current_frame = main_window.timeline_slider.value()
        min_frame = main_window.timeline_slider.minimum()
        max_frame = main_window.timeline_slider.maximum()

        new_frame = current_frame + count
        new_frame = max(min_frame, min(max_frame, new_frame))

        main_window.timeline_slider.setValue(new_frame)
        # Apply auto-centering using the utility method
        UIComponents._apply_auto_centering(main_window, "advance_frames")
        main_window.curve_view.update() # Ensure view updates
        main_window.statusBar().showMessage(f"Advanced {count} frames to frame {new_frame}", 2000)

    @staticmethod
    def go_to_frame(main_window: Any, frame: int, display_message: bool = True) -> None:
        """Go to a specific frame.

        Args:
            main_window: The main application window instance
            frame: The frame number to go to
            display_message: Whether to display a status message (default: True)
        """
        if not main_window.curve_data:
            return

        min_frame = main_window.timeline_slider.minimum()
        max_frame = main_window.timeline_slider.maximum()

        if min_frame <= frame <= max_frame:
            main_window.timeline_slider.setValue(frame)
            # Apply auto-centering using the utility method
            UIComponents._apply_auto_centering(main_window, "go_to_frame")
            main_window.curve_view.update() # Ensure view updates

            # Display status message if requested
            if display_message:
                if frame == min_frame:
                    main_window.statusBar().showMessage(f"Moved to first frame ({frame})", 2000)
                elif frame == max_frame:
                    main_window.statusBar().showMessage(f"Moved to last frame ({frame})", 2000)
                else:
                    main_window.statusBar().showMessage(f"Moved to frame {frame}", 2000)
        else:
            main_window.statusBar().showMessage(f"Frame {frame} is out of range ({min_frame}-{max_frame})", 2000)

    @staticmethod
    def go_to_first_frame(main_window: Any) -> None:
        """Go to the first frame in the timeline."""
        if not main_window.curve_data:
            return

        min_frame = main_window.timeline_slider.minimum()
        UIComponents.go_to_frame(main_window, min_frame)

    @staticmethod
    def go_to_last_frame(main_window: Any) -> None:
        """Go to the last frame in the timeline."""
        if not main_window.curve_data:
            return

        max_frame = main_window.timeline_slider.maximum()
        UIComponents.go_to_frame(main_window, max_frame)

    @staticmethod
    def _calculate_marker_position(min_frame: int, max_frame: int, current_frame: int) -> float:
        """Calculate the relative position of the frame marker.

        Args:
            min_frame: Minimum frame of the timeline
            max_frame: Maximum frame of the timeline
            current_frame: Current frame position

        Returns:
            float: Relative position (0.0 to 1.0) of the marker
        """
        if max_frame <= min_frame:  # Avoid division by zero
            return 0.0

        position = (current_frame - min_frame) / (max_frame - min_frame)
        return max(0.0, min(1.0, position))  # Ensure position is between 0 and 1

    @staticmethod
    def update_frame_marker(main_window: Any) -> None:
        """Update the position of the frame marker based on current frame."""
        if hasattr(main_window, 'frame_marker') and hasattr(main_window, 'timeline_slider'):
            slider = main_window.timeline_slider
            min_frame = slider.minimum()
            max_frame = slider.maximum()
            current_frame = slider.value()

            # Use extracted helper method for position calculation
            position = UIComponents._calculate_marker_position(min_frame, max_frame, current_frame)
            main_window.frame_marker.setPosition(position)
            main_window.frame_marker.update()

    @staticmethod
    def _setup_timeline_press_handler(main_window: Any, handler_func: Any) -> None:
        """Set up the timeline press event handler.

        This method attaches a custom mouse press event handler to the timeline slider,
        while preserving the original handler. This follows DRY principles by centralizing
        the mouse event handling setup logic.

        Args:
            main_window: The main application window instance
            handler_func: The handler function to call when mouse press events occur
        """
        # Store original event handler
        original_press_event = main_window.timeline_slider.mousePressEvent

        # Create a wrapper that calls our handler then the original
        def custom_press_event(ev: QMouseEvent) -> None:
            handler_func(ev)
            # Call original handler if needed
            original_press_event(ev)

        # Set the custom handler on the slider
        setattr(main_window.timeline_slider, "mousePressEvent", custom_press_event)  # type: ignore

    @staticmethod
    def _handle_timeline_press(main_window: Any, ev: QMouseEvent) -> None:
        """Handle mouse press on timeline for direct frame selection.

        This method is extracted to follow DRY principles and eliminate code duplication
        between the different timeline implementations.

        Args:
            main_window: The main application window instance
            ev: The mouse event to handle
        """
        if ev.button() == Qt.MouseButton.LeftButton:
            # Calculate the frame based on click position
            slider = main_window.timeline_slider
            width = slider.width()
            pos = ev.pos().x()

            # Get the frame range
            min_frame = slider.minimum()
            max_frame = slider.maximum()
            frame_range = max_frame - min_frame

            # Calculate the frame based on position
            if width > 0 and frame_range > 0:
                frame = min_frame + int((pos / width) * frame_range + 0.5)
                frame = max(min_frame, min(max_frame, frame))

                # Update the slider
                slider.setValue(frame)

                # Update status message
                main_window.statusBar().showMessage(f"Jumped to frame {frame}", 2000)

    @staticmethod
    def on_control_center_toggled(main_window: Any, checked: bool) -> None:
        """Handle center on point toggle.

        This method is extracted as a static method to follow DRY principles and
        allow reuse across different parts of the UI.

        Args:
            main_window: The main application window instance
            checked: Whether center is enabled or disabled
        """
        main_window.set_centering_enabled(checked)
        if checked:
            CenteringZoomService.auto_center_view(main_window, preserve_zoom=True)

    @staticmethod
    def setup_enhanced_controls(main_window: Any) -> None:
        """Set up enhanced visualization controls in the control panel."""
        # Find the existing visualization group box or create it if needed
        vis_group = None
        if hasattr(main_window, 'controls_container'):
            # Search for the QGroupBox named "Visualization"
            for child in main_window.controls_container.findChildren(QGroupBox):
                if child.title() == "Visualization":
                    vis_group = child
                    break

        if vis_group is None:
            # If not found, create it (this might indicate a UI structure issue)
            vis_group = QGroupBox("Visualization")
            # Add it to an appropriate layout (assuming center_layout exists)
            if hasattr(main_window, 'center_layout'):
                main_window.center_layout.addWidget(vis_group)
            else:
                print("Warning: Could not find layout to add Visualization group box.")
                return # Cannot proceed without a layout

        # Ensure the group box has a layout
        if vis_group.layout() is None:
            vis_layout = QGridLayout(vis_group)
        else:
            vis_layout = cast(QGridLayout, vis_group.layout())
            # Clear existing widgets if necessary (or adjust logic as needed)
            # while vis_layout.count():
            #     child = vis_layout.takeAt(0)
            #     if child.widget():
            #         child.widget().deleteLater()

        # Create and add enhanced controls
        main_window.toggle_grid_button = QPushButton("Grid")
        main_window.toggle_grid_button.setCheckable(True)
        main_window.toggle_grid_button.setToolTip("Toggle Grid Visibility (G)")

        main_window.toggle_vectors_button = QPushButton("Vectors")
        main_window.toggle_vectors_button.setCheckable(True)
        main_window.toggle_vectors_button.setToolTip("Toggle Velocity Vectors (V)")

        main_window.toggle_frame_numbers_button = QPushButton("Numbers")
        main_window.toggle_frame_numbers_button.setCheckable(True)
        main_window.toggle_frame_numbers_button.setToolTip("Toggle Frame Numbers (F)")

        main_window.toggle_crosshair_button = QPushButton("Crosshair")
        main_window.toggle_crosshair_button.setCheckable(True)
        main_window.toggle_crosshair_button.setToolTip("Toggle Crosshair (X)")

        main_window.center_on_point_button = QPushButton("Center")
        main_window.center_on_point_button.setCheckable(True)
        # Use extracted static method for the signal handler
        # Use properly typed lambda to fix linting errors
        def on_center_toggled(checked: bool) -> None:
            UIComponents.on_control_center_toggled(main_window, checked)
        main_window.center_on_point_button.toggled.connect(on_center_toggled)
        main_window.center_on_point_button.setStyleSheet("QPushButton:checked { background-color: lightblue; }")
        main_window.center_on_point_button.setToolTip("Center View on Selected Point (C)")

        main_window.point_size_label = QLabel("Point Size:")
        main_window.point_size_spin = QSpinBox()
        main_window.point_size_spin.setRange(1, 20)
        main_window.point_size_spin.setValue(5) # Default size
        main_window.point_size_spin.setToolTip("Adjust Point Size")

        # Add widgets to layout
        vis_layout.addWidget(main_window.toggle_grid_button, 0, 0)
        vis_layout.addWidget(main_window.toggle_vectors_button, 0, 1)
        vis_layout.addWidget(main_window.toggle_frame_numbers_button, 1, 0)
        vis_layout.addWidget(main_window.toggle_crosshair_button, 1, 1)
        vis_layout.addWidget(main_window.center_on_point_button, 2, 0, 1, 2)
        vis_layout.addWidget(main_window.point_size_label, 3, 0)
        vis_layout.addWidget(main_window.point_size_spin, 3, 1)

        # Connect signals (moved to SignalRegistry)
        # SignalRegistry.connect_all_signals(main_window) # Ensure signals are connected

    @staticmethod
    def connect_all_signals(main_window: Any) -> None:
        """Connect all UI signals to their respective slots.

        This method centralizes signal connections for better maintainability.
        It ensures that signals are connected only once and provides error handling.

        Args:
            main_window: The main application window instance
        """
        # Use the SignalRegistry to handle connections
        from signal_registry import SignalRegistry
        SignalRegistry.connect_all_signals(main_window)  # type: ignore[attr-defined]
