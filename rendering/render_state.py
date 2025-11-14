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
from rendering.visual_settings import VisualSettings

if TYPE_CHECKING:
    from core.display_mode import DisplayMode


@dataclass(frozen=True)
class RenderState:
    """
    State needed for rendering, passed explicitly to the renderer.

    This dataclass contains all the information the renderer needs to draw
    the curve visualization, eliminating the need for the renderer to access
    UI component properties directly.

    Performance Optimization:
        The visible_curves set is pre-computed during RenderState creation,
        eliminating redundant visibility checks during rendering. Instead of
        checking metadata and display mode for each curve N times during
        rendering, we compute the visible set once and do simple O(1) lookups.
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
    background_image: QImage | None = None  # QImage preserves color space metadata

    # Image dimensions (for background scaling)
    image_width: int = 0
    image_height: int = 0

    # Visual settings (single source of truth)
    visual: VisualSettings | None = None

    # Multi-curve support (for future extensibility)
    curves_data: dict[str, CurveDataList] | None = None
    display_mode: "DisplayMode | None" = None
    selected_curve_names: set[str] | None = None
    selected_curves_ordered: list[str] | None = None  # Ordered list for visual differentiation
    curve_metadata: dict[str, dict[str, object]] | None = None
    active_curve_name: str | None = None

    # Pre-computed visibility (performance optimization)
    visible_curves: frozenset[str] | None = None  # Pre-computed set of curves that should render

    # Display mode options
    show_current_point_only: bool = False  # 3DEqualizer-style: show only point at current frame

    def __post_init__(self) -> None:
        """Validate render state after initialization."""
        # Ensure widget dimensions are positive
        if self.widget_width <= 0 or self.widget_height <= 0:
            raise ValueError(f"Widget dimensions must be positive: {self.widget_width}x{self.widget_height}")

        # Ensure zoom factor is positive
        if self.zoom_factor <= 0:
            raise ValueError(f"Zoom factor must be positive: {self.zoom_factor}")

        # Visual settings validation is now handled in VisualSettings.__post_init__

    @classmethod
    def compute(cls, widget: Any) -> "RenderState":  # CurveViewWidget - Any to avoid import cycle
        """
        Compute RenderState from CurveViewWidget with pre-computed visibility.

        This factory method creates a RenderState by extracting all necessary
        state from the widget and pre-computing the set of visible curves.
        This eliminates redundant visibility checks during rendering.

        Performance Benefits:
            - Single visibility computation instead of N checks per render
            - O(1) set lookup instead of O(1) metadata lookup + display mode logic
            - Cleaner separation: widget computes state, renderer just uses it

        Args:
            widget: CurveViewWidget instance to extract state from

        Returns:
            RenderState with all fields populated and visible_curves pre-computed

        Example:
            >>> # In paintEvent()
            >>> render_state = RenderState.compute(self)
            >>> self._renderer.render(painter, event, render_state)
        """
        # Import here to avoid circular dependency
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Get current frame from ApplicationState
        current_frame = app_state.current_frame

        # Get selected points from ApplicationState for active curve
        selected_points: set[int] = set()
        active_curve = app_state.active_curve
        if active_curve:
            selected_points = app_state.get_selection(active_curve)

        # Pre-compute visible curves based on display mode and metadata visibility
        visible_curves: set[str] = set()
        curves_data = widget._get_live_curves_data() if hasattr(widget, "_get_live_curves_data") else {}
        curve_metadata: dict[str, dict[str, object]] = {}

        # Use widget.curves_data as authoritative source (filters out "__default__")
        all_curve_names = widget.curves_data.keys() if hasattr(widget, "curves_data") else curves_data.keys()

        # Build metadata dict and visible_curves set
        if all_curve_names:
            for curve_name in all_curve_names:
                # Get metadata for this curve
                metadata = app_state.get_curve_metadata(curve_name)
                curve_metadata[curve_name] = metadata

                # Filter 1: Check metadata visibility flag
                if not metadata.get("visible", True):
                    continue

                # Filter 2: Check display mode (three-branch decision)
                from core.display_mode import DisplayMode

                if widget.display_mode == DisplayMode.ALL_VISIBLE:
                    # ALL_VISIBLE mode: render all visible curves
                    visible_curves.add(curve_name)
                elif widget.display_mode == DisplayMode.SELECTED:
                    # SELECTED mode: render only selected curves
                    if curve_name in widget.selected_curve_names:
                        visible_curves.add(curve_name)
                # ACTIVE_ONLY mode: render only active curve
                elif curve_name == app_state.active_curve:
                    visible_curves.add(curve_name)

        # Create RenderState with all necessary data
        return cls(
            # Core data
            points=widget.points,
            current_frame=current_frame,
            selected_points=selected_points,
            # Widget dimensions
            widget_width=widget.width(),
            widget_height=widget.height(),
            # View transform settings
            zoom_factor=widget.zoom_factor,
            pan_offset_x=widget.pan_offset_x,
            pan_offset_y=widget.pan_offset_y,
            manual_offset_x=widget.manual_offset_x,
            manual_offset_y=widget.manual_offset_y,
            flip_y_axis=widget.flip_y_axis,
            show_current_point_only=widget._state_manager.show_current_point_only if widget._state_manager else False,
            # Background settings
            show_background=widget.show_background,
            background_image=widget.background_image,
            # Image dimensions
            image_width=widget.image_width,
            image_height=widget.image_height,
            # Visual settings (single source of truth)
            visual=widget.visual,
            # Multi-curve support
            curves_data=curves_data,
            display_mode=widget.display_mode,
            selected_curve_names=widget.selected_curve_names,
            selected_curves_ordered=widget.selected_curves_ordered,
            curve_metadata=curve_metadata,
            active_curve_name=app_state.active_curve,
            # Pre-computed visibility
            visible_curves=frozenset(visible_curves),
        )

    def should_render(self, curve_name: str) -> bool:
        """
        Check if a curve should be rendered.

        Args:
            curve_name: Name of curve to check

        Returns:
            True if curve should be rendered, False otherwise
        """
        if self.visible_curves is None:
            return False
        return curve_name in self.visible_curves

    def __contains__(self, curve_name: str) -> bool:
        """
        Support 'in' operator for membership checking.

        Args:
            curve_name: Name of curve to check

        Returns:
            True if curve is in visible set, False otherwise
        """
        if self.visible_curves is None:
            return False
        return curve_name in self.visible_curves

    def __len__(self) -> int:
        """
        Return number of visible curves.

        Returns:
            Count of curves that should be rendered
        """
        if self.visible_curves is None:
            return 0
        return len(self.visible_curves)

    def __bool__(self) -> bool:
        """
        Check if any curves are visible.

        Returns:
            True if at least one curve should be rendered, False if none
        """
        if self.visible_curves is None:
            return False
        return bool(self.visible_curves)

    @property
    def active_curve(self) -> str | None:
        """
        Alias for active_curve_name to match test expectations.

        Returns:
            Name of active curve or None
        """
        return self.active_curve_name

    def __repr__(self) -> str:  # pyright: ignore[reportImplicitOverride]
        """
        Return concise representation showing display mode and visible curves.

        Returns:
            Compact string representation for debugging
        """
        return (
            f"RenderState("
            f"mode={self.display_mode.name if self.display_mode else None}, "
            f"curves={len(self.visible_curves) if self.visible_curves else 0}, "
            f"active={self.active_curve_name!r}"
            f")"
        )
