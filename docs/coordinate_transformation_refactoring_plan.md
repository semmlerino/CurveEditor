# Coordinate Transformation System Refactoring Plan

This document outlines a comprehensive refactoring plan to address the curve shifting issue
by implementing a robust coordinate transformation system.

## 1. Core Components

### 1.1 ViewState Class

```python
from dataclasses import dataclass
from typing import Optional, Any

@dataclass(frozen=True)
class ViewState:
    """Immutable class representing the view state for coordinate transformations."""

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

    def with_updates(self, **kwargs) -> 'ViewState':
        """Create a new ViewState with updated values."""
        return ViewState(**{**self.__dict__, **kwargs})
```

### 1.2 Transform Class

```python
class Transform:
    """Immutable class representing a coordinate transformation."""

    def __init__(self, scale: float, center_offset_x: float, center_offset_y: float,
                 pan_offset_x: float, pan_offset_y: float, manual_x: float = 0,
                 manual_y: float = 0, flip_y: bool = False, display_height: int = 0):
        """Initialize the transform parameters."""
        self._scale = scale
        self._center_offset_x = center_offset_x
        self._center_offset_y = center_offset_y
        self._pan_offset_x = pan_offset_x
        self._pan_offset_y = pan_offset_y
        self._manual_x = manual_x
        self._manual_y = manual_y
        self._flip_y = flip_y
        self._display_height = display_height

    def apply(self, x: float, y: float) -> tuple[float, float]:
        """Apply this transform to a point."""
        # 1. Apply Y-flip if needed
        if self._flip_y:
            y = self._display_height - y

        # 2. Apply scale
        sx = x * self._scale
        sy = y * self._scale

        # 3. Apply centering offset
        cx = sx + self._center_offset_x
        cy = sy + self._center_offset_y

        # 4. Apply pan offset
        px = cx + self._pan_offset_x
        py = cy + self._pan_offset_y

        # 5. Apply manual offset
        fx = px + self._manual_x
        fy = py + self._manual_y

        return fx, fy

    def get_parameters(self) -> dict:
        """Get the transform parameters."""
        return {
            "scale": self._scale,
            "center_offset": (self._center_offset_x, self._center_offset_y),
            "pan_offset": (self._pan_offset_x, self._pan_offset_y),
            "manual_offset": (self._manual_x, self._manual_y),
            "flip_y": self._flip_y
        }
```

### 1.3 TransformationService

```python
class TransformationService:
    """Central service for all coordinate transformations in the application."""

    @staticmethod
    def get_view_state_from_curve_view(curve_view) -> ViewState:
        """Extract a ViewState from a CurveView instance."""
        # Get widget dimensions
        widget_width = curve_view.width()
        widget_height = curve_view.height()

        # Get display dimensions
        display_width = getattr(curve_view, 'image_width', 1920)
        display_height = getattr(curve_view, 'image_height', 1080)

        # Check for background image dimensions
        background_image = getattr(curve_view, 'background_image', None)
        if background_image:
            display_width = background_image.width()
            display_height = background_image.height()

        # Create the ViewState
        return ViewState(
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
            background_image=background_image
        )

    @staticmethod
    def calculate_transform(view_state: ViewState) -> Transform:
        """Calculate a transform object from the current view state."""
        # Calculate scale factor
        scale_x = view_state.widget_width / view_state.display_width
        scale_y = view_state.widget_height / view_state.display_height
        scale = min(scale_x, scale_y) * view_state.zoom_factor

        # Calculate centering offsets
        from services.centering_zoom_service import CenteringZoomService
        center_x, center_y = CenteringZoomService.calculate_centering_offsets(
            view_state.widget_width,
            view_state.widget_height,
            view_state.display_width * scale,
            view_state.display_height * scale,
            view_state.offset_x,
            view_state.offset_y
        )

        # Create the transform
        return Transform(
            scale=scale,
            center_offset_x=center_x,
            center_offset_y=center_y,
            pan_offset_x=view_state.offset_x,
            pan_offset_y=view_state.offset_y,
            manual_x=view_state.manual_x_offset,
            manual_y=view_state.manual_y_offset,
            flip_y=view_state.flip_y_axis,
            display_height=view_state.display_height
        )

    @staticmethod
    def transform_points(points, transform: Transform) -> list:
        """Transform multiple points using the provided transform."""
        return [transform.apply(p[1], p[2]) for p in points]
```

## 2. Integration with Existing Code

### 2.1 Modify CurveView

```python
def paintEvent(self, event: QPaintEvent) -> None:
    """Draw the curve and points using the new transformation system."""
    if not self.points and not self.background_image:
        return

    # Get the current view state
    from services.transformation_service import TransformationService, ViewState
    view_state = TransformationService.get_view_state_from_curve_view(self)

    # Calculate the transform once for all rendering
    transform = TransformationService.calculate_transform(view_state)

    # Log transform parameters for debugging
    logger.debug(f"Rendering with transform: {transform.get_parameters()}")

    # Use transform for all point conversions
    painter = QPainter(self)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.fillRect(self.rect(), QColor(40, 40, 40))

    # Draw background if available
    if self.show_background and self.background_image:
        # Calculate scaled dimensions
        display_width = self.background_image.width()
        display_height = self.background_image.height()
        scale = transform.get_parameters()["scale"]
        scaled_width = display_width * scale
        scaled_height = display_height * scale

        # Get offsets from transform
        offsets = transform.get_parameters()["center_offset"]
        img_x, img_y = offsets

        # Draw the image
        painter.setOpacity(self.background_opacity)
        painter.drawPixmap(int(img_x), int(img_y), int(scaled_width), int(scaled_height), self.background_image)
        painter.setOpacity(1.0)

    # Draw curve and points
    if self.points:
        # Use transform for all point drawing
        for i, pt in enumerate(self.points):
            # Get transformed coordinates
            frame, x, y = pt[:3]
            tx, ty = transform.apply(x, y)

            # Draw logic remains the same...
```

### 2.2 Update CurveService

```python
@staticmethod
def find_point_at(curve_view: Any, x: float, y: float) -> int:
    """Find a point at the given widget coordinates."""
    if not hasattr(curve_view, 'points') or not curve_view.points:
        return -1

    # Use the transformation service
    from services.transformation_service import TransformationService
    view_state = TransformationService.get_view_state_from_curve_view(curve_view)
    transform = TransformationService.calculate_transform(view_state)

    # Find closest point
    closest_idx = -1
    min_distance = float('inf')

    for i, point in enumerate(curve_view.points):
        _, point_x, point_y = point[:3]

        # Transform using consistent transform
        tx, ty = transform.apply(point_x, point_y)

        distance = ((x - tx) ** 2 + (y - ty) ** 2) ** 0.5
        detection_radius = getattr(curve_view, 'point_radius', 5) * 2

        if distance <= detection_radius and distance < min_distance:
            min_distance = distance
            closest_idx = i

    return closest_idx
```

## 3. Implementation Plan

### 3.1 Phase 1: Create New Components

1. Create the ViewState class in a new file `services/view_state.py`
2. Create the Transform class in a new file `services/transform.py`
3. Create the TransformationService in `services/transformation_service.py`
4. Add unit tests for these components

### 3.2 Phase 2: Integration and Testing

1. Create a temporary shim to test the new transformation system without changing existing code
2. Modify CurveView to use the new system for rendering (paintEvent)
3. Update CurveService to use the new system for point finding
4. Implement transform caching to improve performance

### 3.3 Phase 3: Migration and Cleanup

1. Update all other coordinate transformation code to use the new system
2. Remove the temporary shim and original transformation code
3. Add more comprehensive unit tests
4. Update documentation to reflect the new architecture

## 4. Benefits of the Refactoring

### 4.1 Architectural Improvements

1. **Single Source of Truth**: All transformations are calculated in one place
2. **Immutability**: ViewState and Transform objects are immutable, preventing accidental modifications
3. **Separation of Concerns**: Clear separation between view state and transformation logic
4. **Reusability**: Transform objects can be reused across operations

### 4.2 Bug Prevention

1. **Consistent Transformations**: Same transformation logic used for all operations
2. **Predictable Behavior**: Well-defined transformation pipeline
3. **No State Duplication**: Eliminates inconsistencies that cause the shifting issue

### 4.3 Developer Experience

1. **Better Debugging**: Clear logs showing exactly what transforms are applied
2. **Simplified Maintenance**: Easier to modify transformation logic in one place
3. **Enhanced Testing**: Isolated components that can be tested individually

## 5. Migration Strategy

To ensure a smooth transition while preventing regressions:

1. Implement the new system alongside the existing code
2. Add a feature flag to switch between old and new systems
3. Gradually migrate functions one by one
4. Add extensive tests for each migrated function
5. Once all functions are migrated, remove the old code and feature flag

This approach allows for incremental improvement without disrupting the current functionality, making it safer and more manageable to implement.
