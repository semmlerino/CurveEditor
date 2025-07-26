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
from typing import Protocol, cast, Tuple

# Third-party imports
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QStatusBar
)

# Local imports
from enhanced_curve_view import EnhancedCurveView
from ui_scaling import UIScaling, get_responsive_height, get_content_height
import ui_constants
from point_edit_components import PointEditComponents
from services.curve_service import CurveService as CurveViewOperations
from services.image_service import ImageService as ImageOperations
from services.logging_service import LoggingService
from core.protocols import MainWindowProtocol, CurveViewProtocol
from services.visualization_service import VisualizationService  # For visualization operations
from smoothing_components import SmoothingComponents
from status_components import StatusComponents
from timeline_components import TimelineComponents
from toolbar_components import ToolbarComponents
from visualization_components import VisualizationComponents
from collapsible_panel import CollapsiblePanel

# Configure logger
logger = LoggingService.get_logger("ui_components")

class CurveViewWithTimelineProtocol(CurveViewProtocol, Protocol):
    def updateTimelineForImage(self, index: int) -> None: ...


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
    def setup_main_ui(main_window: MainWindowProtocol) -> None:
        """Set up the main UI layout for the application.

        This method creates the main layout structure with:
        - Toolbar at the top
        - Splitter containing curve view and bottom UI
        - Timeline and controls in the bottom section
        """
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter

        # Main widget and layout with theme-aware styling
        main_widget = QWidget()
        UIScaling.apply_theme_stylesheet(main_widget, "panel")
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)  # No spacing to allow background image to extend to toolbar

        # Create toolbar
        toolbar_widget = UIComponents.create_toolbar(main_window)
        main_layout.addWidget(toolbar_widget)

        # Get the curve view and timeline components separately
        curve_view_container, timeline_widget = UIComponents.create_view_and_timeline_separated(main_window)

        # Create control panel
        controls_widget = UIComponents.create_control_panel(main_window)

        # Create splitter for curve view and bottom UI
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Make the splitter handle more visible and ensure no margins
        splitter.setHandleWidth(2)
        splitter.setContentsMargins(0, 0, 0, 0)
        # Apply theme-aware splitter styling
        import ui_constants
        colors = ui_constants.get_theme_colors(UIScaling.get_theme())
        splitter.setStyleSheet(f"""
            QSplitter {{
                background-color: {colors['bg_primary']};
                margin: 0px;
                padding: 0px;
            }}
            QSplitter::handle {{
                background-color: {colors['bg_panel']};
                border: 1px solid {colors['border_default']};
                border-radius: {UIScaling.get_border_radius('small')}px;
                margin: 0px;
            }}
            QSplitter::handle:hover {{
                background-color: {colors['border_focus']};
                border-color: {colors['border_focus']};
            }}
        """)

        # Add curve view to top of splitter - let it expand to fill space
        # Use responsive minimum height (60% of screen, minimum 150px, maximum 400px)
        responsive_curve_min = get_responsive_height(0.6, 150, 400)
        curve_view_container.setMinimumHeight(responsive_curve_min)
        curve_view_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        splitter.addWidget(curve_view_container)

        # Create a compact container for bottom UI (timeline + controls)
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(UIScaling.get_spacing("xs"))

        # Add timeline to bottom container
        bottom_layout.addWidget(timeline_widget)

        # Add controls to bottom container with content-based constraints
        # Calculate height based on content requirements (approximately 3 lines of controls + padding)
        content_based_min = get_content_height(lines=3, padding=16)
        controls_widget.setMinimumHeight(content_based_min)
        # Remove maximum height constraint to allow better scaling
        bottom_layout.addWidget(controls_widget)

        # Add the bottom container to the splitter with responsive constraints
        # Timeline + controls should be roughly 15% of screen height, minimum based on content
        timeline_min_height = get_content_height(lines=2, padding=8)  # Timeline height
        bottom_responsive_min = max(
            get_responsive_height(0.15, 100, 200),  # 15% of screen, 100-200px range
            content_based_min + timeline_min_height  # Ensure content fits
        )
        bottom_container.setMinimumHeight(bottom_responsive_min)
        # Remove maximum height to allow better proportional scaling
        splitter.addWidget(bottom_container)

        # Set stretch factors to prioritize curve view expansion
        splitter.setStretchFactor(0, 1)  # Curve view gets maximum priority
        splitter.setStretchFactor(1, 0)  # Bottom controls stay minimal
        
        # Let the stretch factors and size constraints handle proportional sizing
        # Don't set hard-coded sizes - this allows proper scaling with window size

        # Store reference to splitter
        main_window.main_splitter = splitter

        main_layout.addWidget(splitter, 1)  # Add with stretch factor to take available vertical space
        main_window.setCentralWidget(main_widget)

        # Set up status bar with improved styling
        status_bar = QStatusBar()
        main_window.setStatusBar(status_bar)
        
        # Style the status bar for better visibility
        import ui_constants
        colors = ui_constants.get_theme_colors(UIScaling.get_theme())
        status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {colors['bg_panel']},
                    stop:1 {colors['bg_secondary']});
                border-top: 4px solid {colors['accent_primary']};
                color: {colors['text_primary']};
                font-size: {UIScaling.get_font_size('medium')}px;
                font-weight: 600;
                padding: {UIScaling.get_spacing('m')}px;
                min-height: {UIScaling.scale_px(44)}px;
            }}
            QStatusBar::item {{
                border: none;
            }}
            QLabel {{
                color: {colors['text_primary']};
                font-size: {UIScaling.get_font_size('medium')}px;
                font-weight: 600;
                padding: 0 {UIScaling.get_spacing('l')}px;
                background-color: transparent;
            }}
        """)
        
        # Add nudge indicator to status bar
        from nudge_indicator import NudgeIndicator
        main_window.nudge_indicator = NudgeIndicator()
        status_bar.addPermanentWidget(main_window.nudge_indicator)
        
        # Set initial message with better visibility
        status_bar.showMessage("Ready", 0)  # 0 means permanent until replaced

    @staticmethod
    def create_toolbar(main_window: MainWindowProtocol) -> QWidget:
        """Create a more organized toolbar with action buttons grouped by function.

        This method delegates to ToolbarComponents.create_toolbar for the actual implementation.
        """
        return ToolbarComponents.create_toolbar(main_window)

    @staticmethod
    def _create_curve_view(main_window: MainWindowProtocol) -> QWidget:
        """Create the curve view container and view widget.

        This helper method centralizes curve view creation used by multiple methods.

        Args:
            main_window: The main application window instance

        Returns:
            QWidget: The curve view container widget with curve view inside
        """
        # Create curve view container with enhanced visual styling
        curve_view_container = QWidget()
        # colors = ui_constants.get_theme_colors(UIScaling.get_theme())  # Not used after removing styling
        curve_view_container.setObjectName("curveViewContainer")
        # Remove all styling to allow background image to fill entire area
        curve_view_container.setStyleSheet("""
            #curveViewContainer {
                margin: 0px;
                padding: 0px;
                border: none;
            }
        """)
        curve_view_layout = QVBoxLayout(curve_view_container)
        curve_view_layout.setContentsMargins(0, 0, 0, 0)
        curve_view_layout.setSpacing(0)
        
        # Set size policy to expand and fill available space
        curve_view_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        main_window.curve_view_container = curve_view_container

        # Create curve view
        if hasattr(main_window, 'curve_view_class') and issubclass(main_window.curve_view_class, EnhancedCurveView):
            main_window.curve_view = main_window.curve_view_class(parent=main_window)
            main_window.original_curve_view = main_window.curve_view  # Store reference to original view
        else:
            main_window.curve_view = EnhancedCurveView(parent=main_window)
            main_window.original_curve_view = main_window.curve_view  # Store reference to original view

        # Ensure curve view expands to fill available space
        main_window.curve_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        curve_view_layout.addWidget(main_window.curve_view)

        # Zoom indicator removed per user request - background image should fill entire UI
        # from zoom_indicator import ZoomIndicator
        # main_window.zoom_indicator = ZoomIndicator(main_window.curve_view)  # Direct child of curve view
        # main_window.zoom_indicator.show()  # Ensure it's visible
        # main_window.zoom_indicator.raise_()  # Bring to front
        
        # # Position it in bottom-right corner to avoid content overlap
        # def reposition_zoom_indicator():
        #     if hasattr(main_window, 'zoom_indicator') and main_window.zoom_indicator:
        #         margin = UIScaling.scale_px(10)
        #         main_window.zoom_indicator.move(
        #             main_window.curve_view.width() - main_window.zoom_indicator.width() - margin,
        #             main_window.curve_view.height() - main_window.zoom_indicator.height() - margin
        #         )
        
        # # Connect resize event to reposition
        # original_resize = main_window.curve_view.resizeEvent
        # def new_resize_event(event):
        #     original_resize(event)
        #     reposition_zoom_indicator()
        # main_window.curve_view.resizeEvent = new_resize_event
        
        # # Initial positioning after a short delay to ensure layout is complete
        # from PySide6.QtCore import QTimer
        # QTimer.singleShot(100, reposition_zoom_indicator)
        
        # # Connect zoom indicator to curve view
        # main_window.zoom_indicator.zoom_changed.connect(
        #     lambda zoom: setattr(main_window.curve_view, 'zoom_factor', zoom) or main_window.curve_view.update()
        # )
        # main_window.zoom_indicator.reset_zoom.connect(
        #     lambda: main_window.curve_view.reset_view()
        # )
        
        # # Update zoom indicator when curve view zoom changes
        # def update_zoom_indicator():
        #     if hasattr(main_window, 'zoom_indicator') and hasattr(main_window.curve_view, 'zoom_factor'):
        #         main_window.zoom_indicator.set_zoom_level(main_window.curve_view.zoom_factor)
        
        # # Connect curve view updates to zoom indicator
        # main_window.curve_view.update = lambda: (
        #     super(type(main_window.curve_view), main_window.curve_view).update(),
        #     update_zoom_indicator()
        # )[-1]  # Return the result of update()

        return curve_view_container

    @staticmethod
    def create_view_and_timeline_separated(main_window: MainWindowProtocol) -> Tuple[QWidget, QWidget]:
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
    def _create_timeline_widget(main_window: MainWindowProtocol) -> QWidget:
        """Create the timeline widget as a separate component.

        This is a helper method for create_view_and_timeline_separated.
        """
        # Local helper for timeline press
        def _local_timeline_press_handler(mw_param: MainWindowProtocol, ev_param: QMouseEvent) -> None:
            TimelineComponents.handle_timeline_press(mw_param, ev_param)

        # Timeline widget with enhanced visual styling
        timeline_widget = QWidget()
        colors = ui_constants.get_theme_colors(UIScaling.get_theme())
        timeline_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {colors['bg_panel']};
                border-top: 1px solid {colors['border_default']};
            }}
        """)
        timeline_layout = QVBoxLayout(timeline_widget)
        timeline_layout.setContentsMargins(0, 0, 0, 0)

        # Image sequence controls with improved styling
        image_controls = QHBoxLayout()
        image_controls.setSpacing(UIScaling.get_spacing("s"))
        
        # Create styled image navigation buttons with icons only
        main_window.prev_image_button = QPushButton("◀")
        main_window.prev_image_button.clicked.connect(lambda: ImageOperations.previous_image(main_window))
        main_window.prev_image_button.setEnabled(False)
        main_window.prev_image_button.setFixedSize(UIScaling.scale_px(32), UIScaling.scale_px(32))
        main_window.prev_image_button.setToolTip("Previous Image")
        
        main_window.next_image_button = QPushButton("▶")
        main_window.next_image_button.clicked.connect(lambda: ImageOperations.next_image(main_window))
        main_window.next_image_button.setEnabled(False)
        main_window.next_image_button.setFixedSize(UIScaling.scale_px(32), UIScaling.scale_px(32))
        main_window.next_image_button.setToolTip("Next Image")
        
        # Create centered image label with enhanced styling
        main_window.image_label = QLabel("No images loaded")
        main_window.image_label.setAlignment(Qt.AlignCenter)
        
        # Get theme colors
        colors = ui_constants.get_theme_colors(UIScaling.get_theme())
        
        main_window.image_label.setStyleSheet(f"""
            QLabel {{
                font-size: {UIScaling.get_font_size('medium')}px;
                font-weight: 500;
                color: {colors['text_secondary']};
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 {colors['bg_secondary']},
                                          stop: 1 {colors['bg_panel']});
                border: 1px solid {colors['border_default']};
                border-radius: {UIScaling.get_border_radius('large')}px;
                padding: {UIScaling.get_spacing('s')}px {UIScaling.get_spacing('l')}px;
                min-width: {UIScaling.scale_px(250)}px;
                letter-spacing: 0.5px;
            }}
        """)
        
        # Add widgets with proper layout
        image_controls.addWidget(main_window.prev_image_button)
        image_controls.addStretch(1)
        image_controls.addWidget(main_window.image_label)
        image_controls.addStretch(1)
        image_controls.addWidget(main_window.next_image_button)
    
        timeline_layout.addLayout(image_controls)

        # Create timeline controls
        timeline_controls_widget = TimelineComponents.create_timeline_widget(
            main_window=main_window,
            on_timeline_changed=TimelineComponents.on_timeline_changed,
            on_timeline_press=_local_timeline_press_handler,
            toggle_playback=TimelineComponents.toggle_playback,
            prev_frame=TimelineComponents.prev_frame,
            next_frame=TimelineComponents.next_frame,
            go_to_first_frame=TimelineComponents.go_to_first_frame,
            go_to_last_frame=TimelineComponents.go_to_last_frame,
            on_frame_edit_changed=TimelineComponents.on_frame_edit_changed
        )
        timeline_layout.addWidget(timeline_controls_widget)

        return timeline_widget


    @staticmethod
    def create_view_and_timeline(main_window: MainWindowProtocol) -> QWidget:
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
    def create_control_panel(main_window: MainWindowProtocol) -> QWidget:
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
        control_margins = UIScaling.get_margin("control")
        controls_layout.setContentsMargins(control_margins, control_margins, control_margins, control_margins)
        controls_layout.setSpacing(UIScaling.get_spacing("xl"))  # Increased spacing between sections
        
        # Add subtle styling to controls container
        panel_color = UIScaling.get_color('bg_panel')
        border_color = UIScaling.get_color('border_default')
        controls_container.setStyleSheet(f"""
            QWidget {{
                background-color: {panel_color};
                border-top: 1px solid {border_color};
            }}
        """)

        # Left side: Point Info and Editing in collapsible panel
        left_collapsible = CollapsiblePanel("Point Info", collapsed=False)
        left_panel_content = PointEditComponents.create_point_info_panel(main_window)
        left_collapsible.set_content_widget(left_panel_content)

        # Center: Visualization Controls in collapsible panel
        center_collapsible = CollapsiblePanel("Visualization", collapsed=False)
        center_panel_content = VisualizationComponents.create_visualization_panel(main_window)
        center_collapsible.set_content_widget(center_panel_content)

        # Right side: Multiple collapsible panels
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(UIScaling.get_spacing("s"))

        # Smoothing controls in collapsible panel
        smoothing_collapsible = CollapsiblePanel("Smoothing", collapsed=False)  # Start expanded
        smoothing_content = SmoothingComponents.create_smoothing_panel(main_window)
        smoothing_collapsible.set_content_widget(smoothing_content)
        right_layout.addWidget(smoothing_collapsible)

        # Track Quality in collapsible panel
        quality_collapsible = CollapsiblePanel("Track Quality", collapsed=False)
        quality_content = StatusComponents.create_track_quality_panel(main_window)
        quality_collapsible.set_content_widget(quality_content)
        right_layout.addWidget(quality_collapsible)

        # Quick Filter Presets in collapsible panel
        presets_collapsible = CollapsiblePanel("Quick Filters", collapsed=False)  # Start expanded
        presets_content = StatusComponents.create_quick_filter_presets(main_window)
        presets_collapsible.set_content_widget(presets_content)
        right_layout.addWidget(presets_collapsible)

        right_layout.addStretch()

        controls_layout.addWidget(left_collapsible)
        controls_layout.addWidget(center_collapsible)
        controls_layout.addWidget(right_panel)

        main_window.enable_point_controls(False)

        # Connect smoothing signal
        main_window.smoothing_apply_button.clicked.connect(main_window.apply_ui_smoothing)

        return controls_container

    @staticmethod
    def create_enhanced_curve_view(main_window: MainWindowProtocol) -> bool:
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
                # Use setattr to dynamically add the method (mypy-safe approach)
                setattr(main_window.curve_view, 'updateTimelineForImage', update_timeline_for_image)
                main_window.curve_view = cast(CurveViewWithTimelineProtocol, main_window.curve_view)

                return True
        except Exception:
            return False
        return False

    @staticmethod
    def setup_timeline(main_window: MainWindowProtocol) -> None:
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

        logger.info(f"Timeline setup complete with {frame_count} discrete frames from {min_frame} to {max_frame}")







    @staticmethod
    def on_timeline_changed(main_window: MainWindowProtocol, value: int) -> None:
        """Handle timeline slider value changes by delegating to TimelineComponents.

        Args:
            main_window: The main application window instance
            value: The new slider value (frame number)
        """
        from timeline_components import TimelineComponents
        TimelineComponents.on_timeline_changed(main_window, value)

    @staticmethod
    def on_frame_edit_changed(main_window: MainWindowProtocol, text: str) -> None:
        """Handle frame edit text changes by delegating to TimelineComponents.

        Args:
            main_window: The main application window instance
            text: The new text value in the frame edit field
        """
        from timeline_components import TimelineComponents
        # The TimelineComponents method doesn't use the text parameter directly
        # but expects it to be already set in the frame_edit field
        TimelineComponents.on_frame_edit_changed(main_window)

    @staticmethod
    def go_to_frame(main_window: MainWindowProtocol, frame: int) -> None:
        """Go to a specific frame in the timeline.

        Args:
            main_window: The main application window instance
            frame: The frame number to go to
        """
        from timeline_components import TimelineComponents
        TimelineComponents.go_to_frame(main_window, frame)

    @staticmethod
    def next_frame(main_window: MainWindowProtocol) -> None:
        """Go to the next frame in the timeline.

        Args:
            main_window: The main application window instance
        """
        from timeline_components import TimelineComponents
        TimelineComponents.next_frame(main_window)

    @staticmethod
    def prev_frame(main_window: MainWindowProtocol) -> None:
        """Go to the previous frame in the timeline.

        Args:
            main_window: The main application window instance
        """
        from timeline_components import TimelineComponents
        TimelineComponents.prev_frame(main_window)

    @staticmethod
    def go_to_first_frame(main_window: MainWindowProtocol) -> None:
        """Go to the first frame in the timeline.

        Args:
            main_window: The main application window instance
        """
        from timeline_components import TimelineComponents
        TimelineComponents.go_to_first_frame(main_window)

    @staticmethod
    def go_to_last_frame(main_window: MainWindowProtocol) -> None:
        """Go to the last frame in the timeline.

        Args:
            main_window: The main application window instance
        """
        from timeline_components import TimelineComponents
        TimelineComponents.go_to_last_frame(main_window)

    @staticmethod
    def adapt_layout_for_screen_size(main_window: MainWindowProtocol) -> None:
        """Adapt the layout based on current screen size and layout mode.
        
        This method adjusts UI component sizing and spacing based on the
        current screen characteristics and layout mode (compact/normal/spacious).
        
        Args:
            main_window: The main application window instance
        """
        layout_mode = UIScaling.get_layout_mode()
        screen_info = UIScaling.get_screen_info()
        
        logger.debug(f"Adapting layout for {layout_mode} mode on "
                    f"{screen_info.width}x{screen_info.height} screen")
        
        # Adjust splitter proportions based on layout mode
        if hasattr(main_window, 'main_splitter') and main_window.main_splitter is not None:
            if layout_mode == 'compact':
                # On small screens, give more space to curve view, minimize controls
                main_window.main_splitter.setStretchFactor(0, 3)  # Curve view
                main_window.main_splitter.setStretchFactor(1, 1)  # Controls
            elif layout_mode == 'spacious':
                # On large screens, allow more generous control space
                main_window.main_splitter.setStretchFactor(0, 2)  # Curve view
                main_window.main_splitter.setStretchFactor(1, 1)  # Controls
            else:  # normal mode
                # Standard proportions
                main_window.main_splitter.setStretchFactor(0, 1)  # Curve view
                main_window.main_splitter.setStretchFactor(1, 0)  # Controls
        
        # Adjust toolbar and control panel spacing based on layout mode
        if hasattr(main_window, 'centralWidget') and main_window.centralWidget() is not None:
            central_widget = main_window.centralWidget()
            if central_widget.layout() is not None:
                if layout_mode == 'compact':
                    # Reduce margins and spacing for compact layout
                    compact_margin = UIScaling.get_spacing("xs")
                    central_widget.layout().setContentsMargins(compact_margin, compact_margin, compact_margin, compact_margin)
                    central_widget.layout().setSpacing(UIScaling.get_spacing("xs"))
                elif layout_mode == 'spacious':
                    # Increase margins and spacing for spacious layout
                    spacious_margin = UIScaling.get_spacing("l")
                    central_widget.layout().setContentsMargins(spacious_margin, spacious_margin, spacious_margin, spacious_margin)
                    central_widget.layout().setSpacing(UIScaling.get_spacing("s"))
                else:
                    # Standard margins and spacing
                    central_widget.layout().setContentsMargins(0, 0, 0, 0)
                    central_widget.layout().setSpacing(UIScaling.get_spacing("xs"))
    
    @staticmethod
    def connect_all_signals(main_window: MainWindowProtocol) -> None:
        """Connect all UI signals to their respective slots.

        This method centralizes signal connections for better maintainability.
        It ensures that signals are connected only once and provides error handling.

        Args:
            main_window: The main application window instance
        """
        # Use the SignalRegistry to handle connections
        from signal_registry import SignalRegistry
        SignalRegistry.connect_all_signals(main_window)  # main_window is dynamically extended at runtime, safe for production
