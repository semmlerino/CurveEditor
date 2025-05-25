#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Timeline components for the Curve Editor.

This module contains all timeline-related UI components including the timeline slider,
frame controls, playback controls, and frame marker visualization.
"""

from typing import Optional, Any, Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPaintEvent, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QLineEdit
)


class TimelineFrameMarker(QWidget):
    """Custom widget to show the current frame position marker in the timeline."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super(TimelineFrameMarker, self).__init__(parent)
        self.position: float = 0.0
        self.setFixedHeight(10)
        self.setMinimumWidth(100)

    def setPosition(self, position: float) -> None:
        """Set the relative position of the marker (0.0 to 1.0)."""
        self.position = max(0.0, min(1.0, position))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the frame marker."""
        painter = QPainter(self)  # type: ignore[arg-type]
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate marker position
        width = self.width()
        x_pos = int(width * self.position)

        # Draw the triangle marker
        path = QPainterPath()
        path.moveTo(x_pos, 0)
        path.lineTo(x_pos - 5, 10)
        path.lineTo(x_pos + 5, 10)
        path.closeSubpath()

        painter.fillPath(path, QColor(255, 0, 0))


class TimelineComponents:
    """Static utility class for timeline-related UI components."""

    @staticmethod
    def create_timeline_widget(
        main_window: Any,
        on_timeline_changed: Callable[[Any, int], None],
        on_timeline_press: Callable[[Any, QMouseEvent], None],
        toggle_playback: Callable[[Any], None],
        prev_frame: Callable[[Any], None],
        next_frame: Callable[[Any], None],
        go_to_first_frame: Callable[[Any], None],
        go_to_last_frame: Callable[[Any], None],
        on_frame_edit_changed: Callable[[Any], None]
    ) -> QWidget:
        """
        Create the timeline control widget with playback controls.

        Args:
            main_window: The main application window instance
            on_timeline_changed: Callback for timeline slider changes
            on_timeline_press: Callback for timeline mouse press events
            toggle_playback: Callback for play/pause toggle
            prev_frame: Callback for previous frame navigation
            next_frame: Callback for next frame navigation
            go_to_first_frame: Callback for jumping to first frame
            go_to_last_frame: Callback for jumping to last frame
            on_frame_edit_changed: Callback for frame edit field changes

        Returns:
            QWidget: The complete timeline widget
        """
        timeline_widget = QWidget()
        timeline_layout = QVBoxLayout(timeline_widget)

        # Timeline controls
        timeline_controls = QHBoxLayout()

        # Playback controls
        main_window.play_button = QPushButton("Play")
        main_window.play_button.setCheckable(True)
        main_window.play_button.clicked.connect(lambda: toggle_playback(main_window))
        main_window.play_button.setToolTip("Play/Pause (Space)")
        main_window.play_button.setEnabled(False)

        main_window.prev_frame_button = QPushButton("<")
        main_window.prev_frame_button.clicked.connect(lambda: prev_frame(main_window))
        main_window.prev_frame_button.setToolTip("Previous Frame (,)")
        main_window.prev_frame_button.setEnabled(False)

        main_window.next_frame_button = QPushButton(">")
        main_window.next_frame_button.clicked.connect(lambda: next_frame(main_window))
        main_window.next_frame_button.setToolTip("Next Frame (.)")
        main_window.next_frame_button.setEnabled(False)

        timeline_controls.addWidget(main_window.prev_frame_button)
        timeline_controls.addWidget(main_window.play_button)
        timeline_controls.addWidget(main_window.next_frame_button)

        # Add frame jump buttons
        main_window.first_frame_button = QPushButton("<<")
        main_window.first_frame_button.clicked.connect(lambda: go_to_first_frame(main_window))
        main_window.first_frame_button.setToolTip("Go to First Frame (Home)")
        main_window.first_frame_button.setEnabled(False)

        main_window.last_frame_button = QPushButton(">>")
        main_window.last_frame_button.clicked.connect(lambda: go_to_last_frame(main_window))
        main_window.last_frame_button.setToolTip("Go to Last Frame (End)")
        main_window.last_frame_button.setEnabled(False)

        timeline_controls.addWidget(main_window.first_frame_button)

        # Frame controls
        main_window.frame_label = QLabel("Frame: N/A")
        main_window.frame_edit = QLineEdit()
        main_window.frame_edit.setMaximumWidth(60)
        main_window.frame_edit.returnPressed.connect(lambda: on_frame_edit_changed(main_window))
        main_window.go_button = QPushButton("Go")
        main_window.go_button.clicked.connect(lambda: on_frame_edit_changed(main_window))
        main_window.go_button.setMaximumWidth(50)

        timeline_controls.addWidget(main_window.frame_label)
        timeline_controls.addWidget(main_window.frame_edit)
        timeline_controls.addWidget(main_window.go_button)
        timeline_controls.addWidget(main_window.last_frame_button)
        timeline_controls.addStretch()

        timeline_layout.addLayout(timeline_controls)

        # Enhanced Timeline slider with individual frame ticks
        main_window.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        main_window.timeline_slider.setMinimum(0)
        main_window.timeline_slider.setMaximum(100)  # Will be updated when data is loaded

        # Configure slider to show individual frames
        main_window.timeline_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        main_window.timeline_slider.setSingleStep(1)    # Move by 1 frame at a time
        main_window.timeline_slider.setPageStep(1)      # Page step is also 1 frame

        # Determine a reasonable tick interval based on frame count
        frame_count = 100  # Default to 100 frames
        tick_interval = max(1, frame_count // 100)  # Prevent too many ticks on large frame ranges
        main_window.timeline_slider.setTickInterval(tick_interval)

        # Add frame tracking tooltip
        main_window.timeline_slider.setToolTip("Frame: 0")

        # Typed slot for timeline slider
        def on_slider_value_changed(value: int) -> None:
            on_timeline_changed(main_window, value)
        main_window.timeline_slider.valueChanged.connect(on_slider_value_changed)

        # Create frame marker for better visual indication
        main_window.frame_marker = TimelineFrameMarker()

        # Create a layout for the slider with the marker
        slider_layout = QVBoxLayout()
        slider_layout.addWidget(main_window.frame_marker)
        slider_layout.addWidget(main_window.timeline_slider)
        slider_layout.setSpacing(0)

        timeline_layout.addLayout(slider_layout)

        # Set up mouse event handling
        TimelineComponents._setup_timeline_press_handler(main_window, on_timeline_press)

        return timeline_widget

    @staticmethod
    def _setup_timeline_press_handler(
        main_window: Any,
        on_timeline_press: Callable[[QMouseEvent], None]
    ) -> None:
        """
        Set up mouse press event handler for the timeline slider.

        Args:
            main_window: The main application window instance
            on_timeline_press: Callback function for mouse press events
        """
        if hasattr(main_window, 'timeline_slider'):
            # Override the mousePressEvent for the slider
            original_press_event = main_window.timeline_slider.mousePressEvent

            def custom_press_event(event: QMouseEvent) -> None:
                on_timeline_press(event)
                original_press_event(event)

            main_window.timeline_slider.mousePressEvent = custom_press_event

    @staticmethod
    def setup_playback_timer(main_window: Any, update_callback: Callable[[], None]) -> None:
        """
        Set up the playback timer for animation.

        Args:
            main_window: The main application window instance
            update_callback: Callback function to update the timeline during playback
        """
        if not hasattr(main_window, 'playback_timer'):
            main_window.playback_timer = QTimer()
            main_window.playback_timer.timeout.connect(update_callback)
            main_window.playback_timer.setInterval(40)  # ~25 fps

    @staticmethod
    def update_timeline_range(main_window: Any, min_frame: int, max_frame: int) -> None:
        """
        Update the timeline slider range.

        Args:
            main_window: The main application window instance
            min_frame: Minimum frame number
            max_frame: Maximum frame number
        """
        if hasattr(main_window, 'timeline_slider'):
            main_window.timeline_slider.setMinimum(min_frame)
            main_window.timeline_slider.setMaximum(max_frame)

            # Update tick interval for reasonable display
            frame_count = max_frame - min_frame + 1
            tick_interval = max(1, frame_count // 100)
            main_window.timeline_slider.setTickInterval(tick_interval)

    @staticmethod
    def update_frame_marker_position(main_window: Any, position: float) -> None:
        """
        Update the position of the frame marker.

        Args:
            main_window: The main application window instance
            position: Relative position (0.0 to 1.0)
        """
        if hasattr(main_window, 'frame_marker'):
            main_window.frame_marker.setPosition(position)

    @staticmethod
    def setup_timeline(main_window: Any) -> None:
        """Setup timeline slider based on frame range."""
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

        print(f"TimelineComponents: Timeline setup complete with {frame_count} discrete frames from {min_frame} to {max_frame}")

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
            position_ratio = TimelineComponents._calculate_marker_position(slider_min, slider_max, value)
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
                # Import here to avoid circular imports
                from services.centering_zoom_service import CenteringZoomService
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
        main_window.curve_view.update()  # Ensure view updates

    @staticmethod
    def on_frame_edit_changed(main_window: Any) -> None:
        """Handle frame edit text changed."""
        try:
            value = int(main_window.frame_edit.text())
            min_val = main_window.timeline_slider.minimum()
            max_val = main_window.timeline_slider.maximum()

            if min_val <= value <= max_val:
                # Directly call go_to_frame to ensure consistent handling including centering
                TimelineComponents.go_to_frame(main_window, value)
            else:
                main_window.statusBar().showMessage(f"Frame {value} out of range ({min_val}-{max_val})", 2000)
        except ValueError:
            main_window.statusBar().showMessage("Invalid frame number entered", 2000)

    @staticmethod
    def toggle_playback(main_window: Any) -> None:
        """Toggle timeline playback on/off."""
        # If playback is already active, stop it
        if hasattr(main_window, 'playback_timer') and main_window.playback_timer.isActive():
            main_window.playback_timer.stop()
            main_window.play_button.setChecked(False)
            main_window.statusBar().showMessage("Playback stopped", 2000)
            return

        # Create timer if it doesn't exist
        if not hasattr(main_window, 'playback_timer'):
            main_window.playback_timer = QTimer(main_window)
            main_window.playback_timer.timeout.connect(lambda: TimelineComponents.advance_playback(main_window))

        # Start playback
        # TODO: Add FPS setting
        fps = 24  # Default FPS
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
        TimelineComponents.advance_frames(main_window, 1)

    @staticmethod
    def prev_frame(main_window: Any) -> None:
        """Go to the previous frame in the timeline."""
        TimelineComponents.advance_frames(main_window, -1)

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
                # Import here to avoid circular imports
                from services.centering_zoom_service import CenteringZoomService
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
        TimelineComponents._apply_auto_centering(main_window, "advance_frames")
        main_window.curve_view.update()  # Ensure view updates
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
            TimelineComponents._apply_auto_centering(main_window, "go_to_frame")
            main_window.curve_view.update()  # Ensure view updates

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
        TimelineComponents.go_to_frame(main_window, min_frame)

    @staticmethod
    def go_to_last_frame(main_window: Any) -> None:
        """Go to the last frame in the timeline."""
        if not main_window.curve_data:
            return

        max_frame = main_window.timeline_slider.maximum()
        TimelineComponents.go_to_frame(main_window, max_frame)

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
            position = TimelineComponents._calculate_marker_position(min_frame, max_frame, current_frame)
            main_window.frame_marker.setPosition(position)
            main_window.frame_marker.update()

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
