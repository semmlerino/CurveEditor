"""Visual Settings for Curve Rendering.

This module defines VisualSettings, the single source of truth for all visual
parameters controlling curve rendering appearance. It consolidates scattered
visual settings from CurveViewWidget and RenderState into one mutable dataclass.

Design:
    - Mutable dataclass (NOT frozen) - visual settings change frequently via UI
    - Comprehensive validation in __post_init__ for all numeric fields
    - QColor fields use field(default_factory=...) for proper instance isolation
    - Defaults match current behavior from CurveViewWidget (see current_defaults.txt)

Excluded:
    - show_background: Architectural setting (belongs in RenderState - image pipeline)

Usage:
    visual = VisualSettings()
    visual.point_radius = 7  # Mutable - can change at runtime
    visual.line_color = QColor(255, 0, 0)
"""

from dataclasses import dataclass, field

from PySide6.QtGui import QColor

__all__ = ["VisualSettings"]


@dataclass
class VisualSettings:
    """Visual parameters for curve rendering (single source of truth).

    All 15 visual parameters controlling curve display appearance. This is the
    canonical source for visual settings - other classes should reference this
    instead of maintaining their own copies.

    Attributes:
        Display toggles (6):
            show_grid: Show coordinate grid
            show_points: Show curve points
            show_lines: Show curve lines
            show_labels: Show point labels
            show_velocity_vectors: Show velocity arrows
            show_all_frame_numbers: Show frame numbers for all points

        Grid settings (3):
            grid_size: Grid spacing in pixels (must be > 0)
            grid_color: Grid line color
            grid_line_width: Grid line thickness (must be > 0)

        Point rendering (2):
            point_radius: Normal point radius in pixels (must be > 0)
            selected_point_radius: Selected point radius in pixels (must be > 0)

        Line rendering (4):
            line_color: Normal curve line color
            line_width: Normal line thickness (must be > 0)
            selected_line_color: Selected curve line color
            selected_line_width: Selected line thickness (must be > 0)

    Raises:
        ValueError: If any numeric field is <= 0 during initialization or modification
    """

    # Display toggles (6 fields)
    show_grid: bool = False
    show_points: bool = True
    show_lines: bool = True
    show_labels: bool = False
    show_velocity_vectors: bool = False
    show_all_frame_numbers: bool = False

    # Grid settings (3 fields)
    grid_size: int = 50
    grid_color: QColor = field(default_factory=lambda: QColor(100, 100, 100, 50))
    grid_line_width: int = 1

    # Point rendering (2 fields)
    point_radius: int = 5
    selected_point_radius: int = 7

    # Line rendering (4 fields)
    line_color: QColor = field(default_factory=lambda: QColor(200, 200, 200))
    line_width: int = 2
    selected_line_color: QColor = field(default_factory=lambda: QColor(255, 255, 100))
    selected_line_width: int = 3

    def __post_init__(self) -> None:
        """Validate all numeric fields are positive.

        Raises:
            ValueError: If any numeric field is <= 0
        """
        # Validate all 6 numeric fields
        if self.point_radius <= 0:
            raise ValueError(f"point_radius must be > 0, got {self.point_radius}")
        if self.selected_point_radius <= 0:
            raise ValueError(f"selected_point_radius must be > 0, got {self.selected_point_radius}")
        if self.line_width <= 0:
            raise ValueError(f"line_width must be > 0, got {self.line_width}")
        if self.selected_line_width <= 0:
            raise ValueError(f"selected_line_width must be > 0, got {self.selected_line_width}")
        if self.grid_size <= 0:
            raise ValueError(f"grid_size must be > 0, got {self.grid_size}")
        if self.grid_line_width <= 0:
            raise ValueError(f"grid_line_width must be > 0, got {self.grid_line_width}")
