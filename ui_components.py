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

# Standard library imports
from typing import Any

# Third-party imports
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider
)

# Local imports
from enhanced_curve_view import EnhancedCurveView  # type: ignore[attr-defined]
from point_edit_components import PointEditComponents
from services.curve_service import CurveService as CurveViewOperations
from services.image_service import ImageService as ImageOperations
from services.visualization_service import VisualizationService  # For visualization operations
from smoothing_components import SmoothingComponents
from status_components import StatusComponents
from timeline_components import TimelineComponents
from toolbar_components import ToolbarComponents
from visualization_components import VisualizationComponents


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
            on_timeline_changed=TimelineComponents.on_timeline_changed,
            on_timeline_press=lambda mw, ev: TimelineComponents._handle_timeline_press(mw, ev),
            toggle_playback=TimelineComponents.toggle_playback,
            prev_frame=TimelineComponents.prev_frame,
            next_frame=TimelineComponents.next_frame,
            go_to_first_frame=TimelineComponents.go_to_first_frame,
            go_to_last_frame=TimelineComponents.go_to_last_frame,
            on_frame_edit_changed=TimelineComponents.on_frame_edit_changed
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
