#!/usr/bin/env python
"""
Consolidated TransformService for CurveEditor.

This service merges functionality from:
- unified_transform.py: Immutable Transform class with coordinate transformations
- view_state.py: ViewState class for transformation parameters

Provides a unified interface for all coordinate transformations and view state management.
"""

import hashlib
import logging
import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from ui.ui_constants import DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH

if TYPE_CHECKING:
    from services.service_protocols import CurveViewProtocol

try:
    from PySide6.QtCore import QPointF
except ImportError:
    # Stub for when PySide6 is not available
    class QPointF:
        def __init__(self, x: float = 0, y: float = 0) -> None:
            self._x = x
            self._y = y

        def x(self) -> float:
            return self._x

        def y(self) -> float:
            return self._y

        def setX(self, x: float) -> None:
            self._x = x

        def setY(self, y: float) -> None:
            self._y = y


logger = logging.getLogger("transform_service")


@dataclass(frozen=True)
class ViewState:
    """
    Immutable class representing the view state for coordinate transformations.

    Encapsulates all parameters that affect coordinate transformations
    between data space and screen space.
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
    background_image: Any | None = None

    # Original data dimensions for scaling
    image_width: int = DEFAULT_IMAGE_WIDTH
    image_height: int = DEFAULT_IMAGE_HEIGHT

    def with_updates(self, **kwargs: Any) -> "ViewState":
        """Create a new ViewState with updated values."""
        # Merge current values with updates, ensuring proper types
        updated = dict(self.__dict__)
        updated.update(kwargs)
        return ViewState(**updated)

    def to_dict(self) -> dict[str, Any]:
        """Convert the ViewState to a dictionary."""
        return {
            "display_dimensions": (self.display_width, self.display_height),
            "widget_dimensions": (self.widget_width, self.widget_height),
            "image_dimensions": (self.image_width, self.image_height),
            "zoom_factor": self.zoom_factor,
            "offset": (self.offset_x, self.offset_y),
            "scale_to_image": self.scale_to_image,
            "flip_y_axis": self.flip_y_axis,
            "manual_offset": (self.manual_x_offset, self.manual_y_offset),
            "has_background_image": self.background_image is not None,
        }

    @classmethod
    def from_curve_view(cls, curve_view: "CurveViewProtocol") -> "ViewState":
        """Create a ViewState from a CurveView instance."""
        # Get widget dimensions
        widget_width = curve_view.width()
        widget_height = curve_view.height()

        # Get original data dimensions
        image_width = getattr(curve_view, "image_width", DEFAULT_IMAGE_WIDTH)
        image_height = getattr(curve_view, "image_height", DEFAULT_IMAGE_HEIGHT)

        # Get display dimensions (initially same as image dimensions)
        display_width = image_width
        display_height = image_height

        # Check for background image dimensions
        background_image = getattr(curve_view, "background_image", None)
        if background_image:
            display_width = background_image.width()
            display_height = background_image.height()

        # Create the ViewState
        return cls(
            display_width=display_width,
            display_height=display_height,
            widget_width=widget_width,
            widget_height=widget_height,
            zoom_factor=getattr(curve_view, "zoom_factor", 1.0),
            offset_x=getattr(curve_view, "offset_x", 0.0),
            offset_y=getattr(curve_view, "offset_y", 0.0),
            scale_to_image=getattr(curve_view, "scale_to_image", True),
            flip_y_axis=getattr(curve_view, "flip_y_axis", False),
            manual_x_offset=getattr(curve_view, "x_offset", 0.0),
            manual_y_offset=getattr(curve_view, "y_offset", 0.0),
            background_image=background_image,
            image_width=image_width,
            image_height=image_height,
        )


class Transform:
    """
    Unified immutable class representing a coordinate transformation.

    Consolidates all transformation logic with consistent mapping between
    data coordinates and screen coordinates.

    Transformation pipeline:
    1. Image scaling adjustment (if enabled)
    2. Y-axis flipping (optional)
    3. Main scaling
    4. Centering offset application
    5. Pan offset application
    6. Manual offset application
    """

    def __init__(
        self,
        scale: float,
        center_offset_x: float,
        center_offset_y: float,
        pan_offset_x: float = 0.0,
        pan_offset_y: float = 0.0,
        manual_offset_x: float = 0.0,
        manual_offset_y: float = 0.0,
        flip_y: bool = False,
        display_height: int = 0,
        image_scale_x: float = 1.0,
        image_scale_y: float = 1.0,
        scale_to_image: bool = True,
    ):
        """Initialize transformation parameters."""
        # Store all parameters as immutable private attributes
        self._parameters = {
            "scale": float(scale),
            "center_offset_x": float(center_offset_x),
            "center_offset_y": float(center_offset_y),
            "pan_offset_x": float(pan_offset_x),
            "pan_offset_y": float(pan_offset_y),
            "manual_offset_x": float(manual_offset_x),
            "manual_offset_y": float(manual_offset_y),
            "flip_y": bool(flip_y),
            "display_height": int(display_height),
            "image_scale_x": float(image_scale_x),
            "image_scale_y": float(image_scale_y),
            "scale_to_image": bool(scale_to_image),
        }

        # Compute stability hash for caching
        self._stability_hash = self._compute_stability_hash()

    def _compute_stability_hash(self) -> str:
        """Compute a hash of the transformation parameters for stability tracking."""
        # Create a string representation of all parameters
        param_str = "|".join(f"{k}:{v}" for k, v in sorted(self._parameters.items()))
        # Return MD5 hash for efficient comparison
        return hashlib.md5(param_str.encode()).hexdigest()

    @property
    def stability_hash(self) -> str:
        """Get the stability hash for this transformation."""
        return self._stability_hash

    @property
    def scale(self) -> float:
        """Get the main scaling factor."""
        return self._parameters["scale"]

    @property
    def center_offset(self) -> tuple[float, float]:
        """Get the centering offset as (x, y) tuple."""
        return (self._parameters["center_offset_x"], self._parameters["center_offset_y"])

    @property
    def pan_offset(self) -> tuple[float, float]:
        """Get the pan offset as (x, y) tuple."""
        return (self._parameters["pan_offset_x"], self._parameters["pan_offset_y"])

    @property
    def manual_offset(self) -> tuple[float, float]:
        """Get the manual offset as (x, y) tuple."""
        return (self._parameters["manual_offset_x"], self._parameters["manual_offset_y"])

    @property
    def flip_y(self) -> bool:
        """Check if Y-axis should be flipped."""
        return self._parameters["flip_y"]

    @property
    def display_height(self) -> int:
        """Get the display height."""
        return self._parameters["display_height"]

    @property
    def image_scale(self) -> tuple[float, float]:
        """Get the image scale factors as (x, y) tuple."""
        return (self._parameters["image_scale_x"], self._parameters["image_scale_y"])

    @property
    def scale_to_image(self) -> bool:
        """Check if scaling to image dimensions is enabled."""
        return self._parameters["scale_to_image"]

    def get_parameters(self) -> dict[str, Any]:
        """Get all transformation parameters as a dictionary."""
        return self._parameters.copy()

    def data_to_screen(self, x: float, y: float) -> tuple[float, float]:
        """
        Transform data coordinates to screen coordinates.

        Args:
            x: Data X coordinate
            y: Data Y coordinate

        Returns:
            Tuple of (screen_x, screen_y)
        """
        # Step 1: Apply image scaling if enabled
        if self.scale_to_image:
            x *= self._parameters["image_scale_x"]
            y *= self._parameters["image_scale_y"]

        # Step 2: Apply Y-axis flipping if enabled
        if self.flip_y and self.display_height > 0:
            y = self.display_height - y

        # Step 3: Apply main scaling
        x *= self.scale
        y *= self.scale

        # Step 4: Apply centering offset
        x += self._parameters["center_offset_x"]
        y += self._parameters["center_offset_y"]

        # Step 5: Apply pan offset
        x += self._parameters["pan_offset_x"]
        y += self._parameters["pan_offset_y"]

        # Step 6: Apply manual offset
        x += self._parameters["manual_offset_x"]
        y += self._parameters["manual_offset_y"]

        return (x, y)

    def screen_to_data(self, x: float, y: float) -> tuple[float, float]:
        """
        Transform screen coordinates to data coordinates.

        Args:
            x: Screen X coordinate
            y: Screen Y coordinate

        Returns:
            Tuple of (data_x, data_y)
        """
        # Reverse Step 6: Remove manual offset
        x -= self._parameters["manual_offset_x"]
        y -= self._parameters["manual_offset_y"]

        # Reverse Step 5: Remove pan offset
        x -= self._parameters["pan_offset_x"]
        y -= self._parameters["pan_offset_y"]

        # Reverse Step 4: Remove centering offset
        x -= self._parameters["center_offset_x"]
        y -= self._parameters["center_offset_y"]

        # Reverse Step 3: Remove main scaling
        if self.scale != 0:
            x /= self.scale
            y /= self.scale

        # Reverse Step 2: Reverse Y-axis flipping if enabled
        if self.flip_y and self.display_height > 0:
            y = self.display_height - y

        # Reverse Step 1: Remove image scaling if enabled
        if self.scale_to_image:
            if self._parameters["image_scale_x"] != 0:
                x /= self._parameters["image_scale_x"]
            if self._parameters["image_scale_y"] != 0:
                y /= self._parameters["image_scale_y"]

        return (x, y)

    def data_to_screen_qpoint(self, point: QPointF) -> QPointF:
        """Transform a QPointF from data to screen coordinates."""
        x, y = self.data_to_screen(point.x(), point.y())
        return QPointF(x, y)

    def screen_to_data_qpoint(self, point: QPointF) -> QPointF:
        """Transform a QPointF from screen to data coordinates."""
        x, y = self.screen_to_data(point.x(), point.y())
        return QPointF(x, y)

    def with_updates(self, **kwargs: Any) -> "Transform":
        """Create a new Transform with updated parameters."""
        # Merge current parameters with updates
        new_params = dict(self._parameters)

        # Map friendly parameter names to internal names
        param_mapping = {
            "scale": "scale",
            "center_offset_x": "center_offset_x",
            "center_offset_y": "center_offset_y",
            "pan_offset_x": "pan_offset_x",
            "pan_offset_y": "pan_offset_y",
            "manual_offset_x": "manual_offset_x",
            "manual_offset_y": "manual_offset_y",
            "flip_y": "flip_y",
            "display_height": "display_height",
            "image_scale_x": "image_scale_x",
            "image_scale_y": "image_scale_y",
            "scale_to_image": "scale_to_image",
        }

        # Update parameters
        for key, value in kwargs.items():
            if key in param_mapping:
                new_params[param_mapping[key]] = value

        # Create new Transform instance
        return Transform(
            scale=new_params["scale"],
            center_offset_x=new_params["center_offset_x"],
            center_offset_y=new_params["center_offset_y"],
            pan_offset_x=new_params["pan_offset_x"],
            pan_offset_y=new_params["pan_offset_y"],
            manual_offset_x=new_params["manual_offset_x"],
            manual_offset_y=new_params["manual_offset_y"],
            flip_y=new_params["flip_y"],
            display_height=new_params["display_height"],
            image_scale_x=new_params["image_scale_x"],
            image_scale_y=new_params["image_scale_y"],
            scale_to_image=new_params["scale_to_image"],
        )

    @classmethod
    def from_view_state(cls, view_state: ViewState) -> "Transform":
        """Create a Transform from a ViewState."""
        # Calculate scale
        scale = view_state.zoom_factor

        # Calculate center offsets
        center_offset_x = (view_state.widget_width - view_state.display_width * scale) / 2
        center_offset_y = (view_state.widget_height - view_state.display_height * scale) / 2

        # Calculate image scale factors
        image_scale_x = view_state.display_width / view_state.image_width if view_state.image_width > 0 else 1.0
        image_scale_y = view_state.display_height / view_state.image_height if view_state.image_height > 0 else 1.0

        return cls(
            scale=scale,
            center_offset_x=center_offset_x,
            center_offset_y=center_offset_y,
            pan_offset_x=view_state.offset_x,
            pan_offset_y=view_state.offset_y,
            manual_offset_x=view_state.manual_x_offset,
            manual_offset_y=view_state.manual_y_offset,
            flip_y=view_state.flip_y_axis,
            display_height=view_state.display_height,
            image_scale_x=image_scale_x,
            image_scale_y=image_scale_y,
            scale_to_image=view_state.scale_to_image,
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Transform(scale={self.scale:.2f}, "
            f"center_offset=({self._parameters['center_offset_x']:.1f}, {self._parameters['center_offset_y']:.1f}), "
            f"pan_offset=({self._parameters['pan_offset_x']:.1f}, {self._parameters['pan_offset_y']:.1f}), "
            f"flip_y={self.flip_y})"
        )


class TransformService:
    """
    Consolidated service for all coordinate transformations and view state management.

    This service merges functionality from unified_transform.py and view_state.py
    to provide a single interface for transformation operations.
    """

    def __init__(self) -> None:
        """Initialize the TransformService."""
        self._lock = threading.RLock()

    def create_view_state(self, curve_view: "CurveViewProtocol") -> ViewState:
        """Create a ViewState from a CurveView instance."""
        return ViewState.from_curve_view(curve_view)

    @staticmethod
    @lru_cache(maxsize=128)
    def _create_transform_cached(view_state: ViewState) -> Transform:
        """
        Create a Transform from a ViewState with LRU caching.

        This method uses @lru_cache for optimal performance. Since ViewState is
        a frozen dataclass, it's hashable and works perfectly as a cache key.

        Args:
            view_state: The ViewState to create a transform for

        Returns:
            Transform instance for the given view state
        """
        return Transform.from_view_state(view_state)

    def create_transform(self, view_state: ViewState) -> Transform:
        """
        Create a Transform from a ViewState with caching.

        This method uses LRU caching for optimal performance. The cache is
        automatically managed by functools.lru_cache.

        Args:
            view_state: The ViewState to create a transform for

        Returns:
            Transform instance (potentially cached)
        """
        return self._create_transform_cached(view_state)

    def clear_cache(self) -> None:
        """Clear the transform cache."""
        self._create_transform_cached.cache_clear()

    def get_cache_info(self) -> dict[str, Any]:
        """
        Get transform cache statistics.

        Returns:
            Dictionary with cache hit/miss statistics
        """
        info = self._create_transform_cached.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "current_size": info.currsize,
            "max_size": info.maxsize,
            "hit_rate": info.hits / (info.hits + info.misses) if (info.hits + info.misses) > 0 else 0.0,
        }

    def transform_point_to_screen(self, transform: Transform, x: float, y: float) -> tuple[float, float]:
        """Transform a data point to screen coordinates."""
        return transform.data_to_screen(x, y)

    def transform_point_to_data(self, transform: Transform, x: float, y: float) -> tuple[float, float]:
        """Transform a screen point to data coordinates."""
        return transform.screen_to_data(x, y)

    def update_view_state(self, view_state: ViewState, **kwargs: Any) -> ViewState:
        """Update a ViewState with new parameters."""
        return view_state.with_updates(**kwargs)

    def update_transform(self, transform: Transform, **kwargs: Any) -> Transform:
        """Update a Transform with new parameters."""
        return transform.with_updates(**kwargs)
