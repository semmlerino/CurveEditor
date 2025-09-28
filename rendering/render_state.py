#!/usr/bin/env python3
"""
RenderState dataclass for decoupled rendering.

This module provides the RenderState dataclass that contains all state
needed for rendering, enabling the renderer to be fully decoupled from
the CurveViewWidget and other UI components.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QImage, QPixmap

from core.type_aliases import CurveDataList

if TYPE_CHECKING:
    from rendering.rendering_protocols import CurveViewProtocol


@dataclass
class RenderState:
    """
    State needed for rendering, passed explicitly to the renderer.

    This dataclass contains all the information the renderer needs to draw
    the curve visualization, eliminating the need for the renderer to access
    UI component properties directly.
    """

    # Core data
    points: CurveDataList
    current_frame: int
    selected_points: set[int]

    # Widget dimensions
    widget_width: int
    widget_height: int

    # View transform settings
    zoom_factor: float
    pan_offset_x: float
    pan_offset_y: float
    manual_offset_x: float
    manual_offset_y: float
    flip_y_axis: bool

    # Background settings
    show_background: bool
    background_image: QImage | QPixmap | None = None
    background_opacity: float = 1.0

    # Image dimensions (for background scaling)
    image_width: int = 0
    image_height: int = 0

    # Grid and visual settings
    show_grid: bool = True
    point_radius: int = 3

    # Multi-curve support (for future extensibility)
    curves_data: dict[str, CurveDataList] | None = None
    show_all_curves: bool = False
    selected_curve_names: set[str] | None = None
    curve_metadata: dict[str, dict[str, Any]] | None = None
    active_curve_name: str | None = None

    def __post_init__(self) -> None:
        """Validate render state after initialization."""
        # Ensure widget dimensions are positive
        if self.widget_width <= 0 or self.widget_height <= 0:
            raise ValueError(f"Widget dimensions must be positive: {self.widget_width}x{self.widget_height}")

        # Ensure zoom factor is positive
        if self.zoom_factor <= 0:
            raise ValueError(f"Zoom factor must be positive: {self.zoom_factor}")

        # Ensure point radius is positive
        if self.point_radius <= 0:
            raise ValueError(f"Point radius must be positive: {self.point_radius}")

        # Ensure background opacity is in valid range
        if not 0.0 <= self.background_opacity <= 1.0:
            raise ValueError(f"Background opacity must be between 0.0 and 1.0: {self.background_opacity}")

    @classmethod
    def from_curve_view(
        cls, curve_view: "CurveViewProtocol", current_frame: int, selected_points: set[int]
    ) -> "RenderState":
        """
        Create RenderState from a CurveViewWidget.

        This is a convenience method for the transition period while we're
        migrating from direct curve_view access to explicit state passing.

        Args:
            curve_view: CurveViewWidget instance
            current_frame: Current frame from StateManager
            selected_points: Selected points from StateManager

        Returns:
            RenderState instance with all necessary state
        """
        return cls(
            # Core data
            points=curve_view.points,
            current_frame=current_frame,
            selected_points=selected_points,
            # Widget dimensions
            widget_width=curve_view.width(),
            widget_height=curve_view.height(),
            # View transform settings
            zoom_factor=curve_view.zoom_factor,
            pan_offset_x=curve_view.pan_offset_x,
            pan_offset_y=curve_view.pan_offset_y,
            manual_offset_x=curve_view.manual_offset_x,
            manual_offset_y=curve_view.manual_offset_y,
            flip_y_axis=curve_view.flip_y_axis,
            # Background settings
            show_background=curve_view.show_background,
            background_image=curve_view.background_image,
            background_opacity=curve_view.background_opacity,
            # Image dimensions
            image_width=curve_view.image_width,
            image_height=curve_view.image_height,
            # Grid and visual settings
            show_grid=curve_view.show_grid,
            point_radius=curve_view.point_radius,
            # Multi-curve support
            curves_data=getattr(curve_view, "curves_data", None),
            show_all_curves=getattr(curve_view, "show_all_curves", False),
            selected_curve_names=getattr(curve_view, "selected_curve_names", None),
        )
