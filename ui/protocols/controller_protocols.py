#!/usr/bin/env python
"""
Protocol definitions for UI controllers.

These protocols define the interfaces for all controllers in the application,
enabling type-safe programming and reducing coupling between MainWindow and controllers.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ActionHandlerProtocol(Protocol):
    """Protocol for action handler controller."""

    def _on_action_new(self) -> None:
        """Handle new file action."""
        ...

    def _on_action_open(self) -> None:
        """Handle open file action."""
        ...

    def _on_action_save(self) -> None:
        """Handle save file action."""
        ...

    def _on_action_save_as(self) -> None:
        """Handle save as action."""
        ...

    def _on_select_all(self) -> None:
        """Handle select all action."""
        ...

    def _on_add_point(self) -> None:
        """Handle add point action."""
        ...

    def _on_zoom_in(self) -> None:
        """Handle zoom in action."""
        ...

    def _on_zoom_out(self) -> None:
        """Handle zoom out action."""
        ...

    def _on_zoom_fit(self) -> None:
        """Handle zoom fit action."""
        ...

    def _on_reset_view(self) -> None:
        """Handle reset view action."""
        ...

    def update_zoom_label(self) -> None:
        """Update the zoom level label."""
        ...

    def apply_smooth_operation(self) -> None:
        """Apply smoothing operation to curve."""
        ...

    def _get_current_curve_data(self) -> object:
        """Get current curve data."""
        ...


@runtime_checkable
class ViewOptionsProtocol(Protocol):
    """Protocol for view options controller."""

    def on_show_background_changed(self, checked: bool) -> None:
        """Handle show background checkbox change."""
        ...

    def on_show_grid_changed(self, checked: bool) -> None:
        """Handle show grid checkbox change."""
        ...

    def on_point_size_changed(self, value: int) -> None:
        """Handle point size slider change."""
        ...

    def on_line_width_changed(self, value: int) -> None:
        """Handle line width slider change."""
        ...

    def toggle_tooltips(self) -> None:
        """Toggle tooltip display."""
        ...

    def update_curve_point_size(self, value: int) -> None:
        """Update curve point size from slider."""
        ...

    def update_curve_line_width(self, value: int) -> None:
        """Update curve line width from slider."""
        ...

    def update_curve_view_options(self) -> None:
        """Update curve view widget options."""
        ...

    def get_view_options(self) -> dict[str, object]:
        """Get current view options."""
        ...

    def set_view_options(self, options: dict[str, object]) -> None:
        """Set view options from dictionary."""
        ...


@runtime_checkable
class TimelineControllerProtocol(Protocol):
    """Protocol for timeline controller."""

    frame_spinbox: Any  # QSpinBox but avoiding circular imports

    def on_timeline_tab_clicked(self, frame: int) -> None:
        """Handle timeline tab click."""
        ...

    def on_timeline_tab_hovered(self, frame: int) -> None:
        """Handle timeline tab hover."""
        ...

    def update_for_tracking_data(self, num_images: int) -> None:
        """Update timeline for tracking data."""
        ...

    def update_for_current_frame(self, frame: int) -> None:
        """Update timeline to show current frame."""
        ...

    def update_timeline_tabs(self, curve_data: object | None = None) -> None:
        """Update timeline tabs with curve data."""
        ...

    def connect_signals(self) -> None:
        """Connect timeline-related signals."""
        ...

    def set_frame_range(self, min_frame: int, max_frame: int) -> None:
        """Set the timeline frame range."""
        ...

    def clear(self) -> None:
        """Clear the timeline tabs."""
        ...


@runtime_checkable
class BackgroundImageProtocol(Protocol):
    """Protocol for background image controller."""

    def on_image_sequence_loaded(self, image_dir: str, image_files: list[str]) -> None:
        """Handle image sequence loaded."""
        ...

    def update_background_for_frame(self, frame: int) -> None:
        """Update background image for frame."""
        ...

    def clear_background_images(self) -> None:
        """Clear all background images."""
        ...

    def get_image_count(self) -> int:
        """Get number of loaded images."""
        ...

    def has_images(self) -> bool:
        """Check if images are loaded."""
        ...

    def get_current_image_info(self) -> tuple[str, int] | None:
        """Get current image information."""
        ...


@runtime_checkable
class MultiPointTrackingProtocol(Protocol):
    """Protocol for multi-point tracking controller."""

    def on_tracking_data_loaded(self, data: list[object]) -> None:
        """Handle tracking data loaded."""
        ...

    def on_multi_point_data_loaded(self, multi_data: dict[str, object]) -> None:
        """Handle multi-point data loaded."""
        ...

    def on_tracking_points_selected(self, point_names: list[str]) -> None:
        """Handle tracking point selection."""
        ...

    def on_point_visibility_changed(self, point_name: str, visible: bool) -> None:
        """Handle point visibility change."""
        ...

    def on_point_color_changed(self, point_name: str, color: str) -> None:
        """Handle point color change."""
        ...

    def on_point_deleted(self, point_name: str) -> None:
        """Handle point deletion."""
        ...

    def on_point_renamed(self, old_name: str, new_name: str) -> None:
        """Handle point rename."""
        ...

    def on_tracking_direction_changed(self, point_name: str, new_direction: object) -> None:
        """Handle tracking direction change."""
        ...

    def update_tracking_panel(self) -> None:
        """Update tracking panel display."""
        ...

    def update_curve_display(self) -> None:
        """Update curve display with tracking data."""
        ...

    def clear_tracking_data(self) -> None:
        """Clear all tracking data."""
        ...

    def has_tracking_data(self) -> bool:
        """Check if tracking data exists."""
        ...

    def get_tracking_point_names(self) -> list[str]:
        """Get list of tracking point names."""
        ...


@runtime_checkable
class PointEditorProtocol(Protocol):
    """Protocol for point editor controller."""

    def on_selection_changed(self, indices: list[int]) -> None:
        """Handle selection change."""
        ...

    def on_store_selection_changed(self, selection: set[int]) -> None:
        """Handle store selection change."""
        ...

    def on_point_x_changed(self, value: float) -> None:
        """Handle X coordinate change."""
        ...

    def on_point_y_changed(self, value: float) -> None:
        """Handle Y coordinate change."""
        ...

    def connect_signals(self) -> None:
        """Connect point editor signals."""
        ...


@runtime_checkable
class SignalConnectionProtocol(Protocol):
    """Protocol for signal connection manager."""

    def connect_all_signals(self) -> None:
        """Connect all application signals."""
        ...

    def _connect_file_operations_signals(self) -> None:
        """Connect file operation signals."""
        ...

    def _connect_signals(self) -> None:
        """Connect state manager signals."""
        ...

    def _connect_store_signals(self) -> None:
        """Connect reactive store signals."""
        ...

    def _connect_curve_widget_signals(self) -> None:
        """Connect curve widget signals."""
        ...

    def _verify_connections(self) -> None:
        """Verify critical connections."""
        ...


@runtime_checkable
class UIInitializationProtocol(Protocol):
    """Protocol for UI initialization controller."""

    def initialize_ui(self) -> None:
        """Initialize all UI components."""
        ...

    def _init_actions(self) -> None:
        """Initialize menu actions."""
        ...

    def _init_menus(self) -> None:
        """Initialize menu bar."""
        ...

    def _init_curve_view(self) -> None:
        """Initialize curve view widget."""
        ...

    def _init_control_panel(self) -> None:
        """Initialize control panel."""
        ...

    def _init_properties_panel(self) -> None:
        """Initialize properties panel."""
        ...

    def _init_timeline_tabs(self) -> None:
        """Initialize timeline tabs."""
        ...

    def _init_tracking_panel(self) -> None:
        """Initialize tracking panel."""
        ...

    def _init_status_bar(self) -> None:
        """Initialize status bar."""
        ...


@runtime_checkable
class DataObserver(Protocol):
    """Protocol for components that observe store data changes."""

    def on_data_changed(self, data: object) -> None:
        """Handle curve data change."""
        ...

    def on_selection_changed(self, selection: set[int]) -> None:
        """Handle selection change."""
        ...

    def on_point_status_changed(self, frame: int, status: str) -> None:
        """Handle point status change."""
        ...


@runtime_checkable
class UIComponent(Protocol):
    """Protocol for UI components with connection requirements."""

    required_connections: list[tuple[str, str]]

    def verify_connections(self) -> bool:
        """Verify that all required connections are established."""
        ...
