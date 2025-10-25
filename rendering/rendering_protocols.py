#!/usr/bin/env python3
"""
Protocols for the rendering module.

This module defines Protocol classes used for type checking in the rendering subsystem.
Keeping protocols separate from implementations helps avoid circular imports.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PySide6.QtGui import QImage, QPixmap

    from services.transform_service import Transform
    from ui.state_manager import StateManager


class CurveViewProtocol(Protocol):
    """Protocol for curve view objects used by the renderer."""

    # Required attributes
    points: list[tuple[int, float, float] | tuple[int, float, float, str] | tuple[int, float, float, str | bool]]
    show_background: bool
    background_image: "QImage | QPixmap | None"
    show_grid: bool
    zoom_factor: float
    pan_offset_x: float
    pan_offset_y: float
    manual_offset_x: float
    manual_offset_y: float
    image_width: int
    image_height: int
    background_opacity: float
    selected_points: set[int]
    point_radius: int
    main_window: "MainWindowProtocol | None"
    current_frame: int

    # Optional attributes for debugging
    debug_mode: bool
    show_all_frame_numbers: bool
    flip_y_axis: bool

    def width(self) -> int:
        """Get widget width in pixels."""
        ...

    def height(self) -> int:
        """Get widget height in pixels."""
        ...

    def get_transform(self) -> "Transform":
        """Get coordinate transformation for data-to-screen conversions."""
        ...


class MainWindowProtocol(Protocol):
    """Protocol for main window objects."""

    state_manager: "StateManager"  # Has current_frame attribute
