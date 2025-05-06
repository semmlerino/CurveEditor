"""
ViewState Module for CurveEditor.

This module implements an immutable ViewState class that encapsulates
all parameters needed for coordinate transformations in the application.
The ViewState serves as a complete snapshot of view configuration,
enabling consistent coordinate transformations.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict


@dataclass(frozen=True)
class ViewState:
    """
    Immutable class representing the view state for coordinate transformations.

    This class encapsulates all parameters that affect how coordinates are
    transformed between data space and screen space. By capturing all these
    parameters in a single, immutable object, we ensure consistency in
    coordinate transformations across different operations.

    Attributes:
        display_width: Width of the content being displayed (image or data)
        display_height: Height of the content being displayed (image or data)
        widget_width: Width of the widget in screen pixels
        widget_height: Height of the widget in screen pixels
        zoom_factor: Current zoom level (default: 1.0)
        offset_x: Horizontal panning offset (default: 0.0)
        offset_y: Vertical panning offset (default: 0.0)
        scale_to_image: Whether to scale coordinates to image dimensions (default: True)
        flip_y_axis: Whether to flip the Y axis (default: False)
        manual_x_offset: Manual X offset adjustment (default: 0.0)
        manual_y_offset: Manual Y offset adjustment (default: 0.0)
        background_image: Optional reference to the background image
        image_width: Width of the original data image/track (default: 1920)
        image_height: Height of the original data image/track (default: 1080)
    """

    # Core display parameters
    display_width: int
    display_height: int
    widget_width: int
    widget_height: int

    # View transformation parameters
    zoom_factor: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0

    # Configuration options
    scale_to_image: bool = True
    flip_y_axis: bool = False

    # Manual adjustments
    manual_x_offset: float = 0.0
    manual_y_offset: float = 0.0

    # Background image reference (optional)
    background_image: Optional[Any] = None

    # Original data dimensions for scaling
    image_width: int = 1920
    image_height: int = 1080

    def with_updates(self, **kwargs) -> 'ViewState':
        """
        Create a new ViewState with updated values.

        This method allows for creating a modified copy of the current
        ViewState without changing the original (immutability pattern).

        Args:
            **kwargs: New values for any attributes to update

        Returns:
            A new ViewState instance with the specified updates applied

        Example:
            new_state = current_state.with_updates(zoom_factor=2.0, offset_x=10)
        """
        return ViewState(**{**self.__dict__, **kwargs})

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ViewState to a dictionary.

        Returns:
            A dictionary containing all ViewState attributes
        """
        return {
            "display_dimensions": (self.display_width, self.display_height),
            "widget_dimensions": (self.widget_width, self.widget_height),
            "image_dimensions": (self.image_width, self.image_height),
            "zoom_factor": self.zoom_factor,
            "offset": (self.offset_x, self.offset_y),
            "scale_to_image": self.scale_to_image,
            "flip_y_axis": self.flip_y_axis,
            "manual_offset": (self.manual_x_offset, self.manual_y_offset),
            "has_background_image": self.background_image is not None
        }

    @classmethod
    def from_curve_view(cls, curve_view: Any) -> 'ViewState':
        """
        Create a ViewState from a CurveView instance.

        This factory method extracts all necessary parameters from a CurveView
        to create a complete ViewState object.

        Args:
            curve_view: The CurveView instance to extract parameters from

        Returns:
            A new ViewState instance with parameters from the CurveView
        """
        # Get widget dimensions
        widget_width = curve_view.width()
        widget_height = curve_view.height()

        # Get original data dimensions
        image_width = getattr(curve_view, 'image_width', 1920)
        image_height = getattr(curve_view, 'image_height', 1080)

        # Get display dimensions (initially same as image dimensions)
        display_width = image_width
        display_height = image_height

        # Check for background image dimensions
        background_image = getattr(curve_view, 'background_image', None)
        if background_image:
            display_width = background_image.width()
            display_height = background_image.height()

        # Create the ViewState
        return cls(
            display_width=display_width,
            display_height=display_height,
            widget_width=widget_width,
            widget_height=widget_height,
            zoom_factor=getattr(curve_view, 'zoom_factor', 1.0),
            offset_x=getattr(curve_view, 'offset_x', 0.0),
            offset_y=getattr(curve_view, 'offset_y', 0.0),
            scale_to_image=getattr(curve_view, 'scale_to_image', True),
            flip_y_axis=getattr(curve_view, 'flip_y_axis', False),
            manual_x_offset=getattr(curve_view, 'x_offset', 0.0),
            manual_y_offset=getattr(curve_view, 'y_offset', 0.0),
            background_image=background_image,
            image_width=image_width,
            image_height=image_height
        )
