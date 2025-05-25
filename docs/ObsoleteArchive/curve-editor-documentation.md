# Curve Editor Documentation (Legacy)

## Overview

The Curve Editor is a Python application for visualizing and editing 2D curve data with a focus on tracking coordinate manipulations. This documentation covers the recent refactoring work done to improve code quality by applying SOLID, DRY, YAGNI, and KISS principles.

## Architecture

The application follows a service-oriented architecture with the following key components:

### Services

- **CurveService**: Facade for curve manipulation operations
- **TransformationService**: Handles coordinate transformations
- **CenteringZoomService**: Manages view centering and zoom operations
- **VisualizationService**: Controls visual aspects of the curve display
- **LoggingService**: Centralized logging functionality

### Core Classes

- **ViewState**: Immutable class representing view configuration
- **Transform**: Encapsulates transformation parameters and logic

## Refactoring Improvements

### 1. Coordinate Transformation Refactoring

Removed duplicate coordinate transformation logic by centralizing transformations in `TransformationService`:

```python
# Before refactoring - transformation logic duplicated in multiple methods
def select_points_in_rect(curve_view, main_window, selection_rect):
    # Calculate transform parameters manually
    display_width = getattr(curve_view, 'image_width', 1920)
    display_height = getattr(curve_view, 'image_height', 1080)
    if hasattr(curve_view, 'background_image') and curve_view.background_image:
        display_width = curve_view.background_image.width()
        display_height = curve_view.background_image.height()
    scale_x = curve_view.width() / display_width
    scale_y = curve_view.height() / display_height
    scale = min(scale_x, scale_y) * getattr(curve_view, 'zoom_factor', 1.0)
    # ... more calculation code ...

# After refactoring - using TransformationService consistently
def select_points_in_rect(curve_view, main_window, selection_rect):
    # Create a view state from the curve view for transformation
    view_state = ViewState.from_curve_view(curve_view)
    # Use TransformationService for coordinate transformation
    tx, ty = TransformationService.transform_point(view_state, point_x, point_y)
```

### 2. Status Bar Update Standardization

Created a helper method to standardize status bar updates:

```python
@staticmethod
def _update_status_bar(main_window, message, timeout=2000):
    """Helper method to update the status bar if available."""
    if main_window and hasattr(main_window, 'statusBar'):
        try:
            status_bar = main_window.statusBar()
            if status_bar and hasattr(status_bar, 'showMessage'):
                status_bar.showMessage(message, timeout)
        except Exception as e:
            # Log but don't raise since status bar updates are non-critical
            logger.warning(f"Failed to update status bar: {e}")
```

### 3. Point Normalization Enhancement

Improved point normalization to handle diverse point formats consistently:

```python
# Added comment to clarify the purpose of normalize_point usage
frame, _, _, status = normalize_point(main_window.curve_data[index])
```

## Service API Reference

### CurveService

The `CurveService` provides operations for manipulating curve points:

```python
# Select all points in the curve
CurveService.select_all_points(curve_view, main_window)

# Clear the current selection
CurveService.clear_selection(curve_view, main_window)

# Select points within a rectangular region
CurveService.select_points_in_rect(curve_view, main_window, selection_rect)

# Select a specific point by index
CurveService.select_point_by_index(curve_view, main_window, index)

# Update a point's position
CurveService.update_point_position(curve_view, main_window, index, x, y)

# Toggle a point's interpolation status
CurveService.toggle_point_interpolation(curve_view, index)

# Reset the view to default zoom and position
CurveService.reset_view(curve_view)

# Change the nudge increment for point movement
CurveService.change_nudge_increment(curve_view, increase=True)
```

### TransformationService

The `TransformationService` handles coordinate transformations:

```python
# Create a ViewState object from a curve view
view_state = ViewState.from_curve_view(curve_view)

# Transform a point from data coordinates to widget coordinates
tx, ty = TransformationService.transform_point(view_state, x, y)

# Transform multiple points at once for better performance
transformed_points = TransformationService.transform_points(view_state, points)

# Create a stable transform for operations that modify curve data
transform = TransformationService.create_stable_transform_for_operation(curve_view)
```

### CenteringZoomService

The `CenteringZoomService` manages view positioning and zoom:

```python
# Calculate centering offsets
offset_x, offset_y = CenteringZoomService.calculate_centering_offsets(
    widget_width, widget_height, display_width, display_height, offset_x, offset_y)

# Center the view on a specific point
CenteringZoomService.center_on_point(curve_view, point_idx)

# Reset the view to default state
CenteringZoomService.reset_view(curve_view)

# Zoom in or out from the view
CenteringZoomService.zoom_in(curve_view, factor=1.2)
CenteringZoomService.zoom_out(curve_view, factor=0.8)
```

## Design Principles Applied

### SOLID Principles

- **Single Responsibility**: Each service has a clear, focused responsibility
- **Open/Closed**: Code is open for extension but closed for modification
- **Liskov Substitution**: Interfaces are consistent and substitutable
- **Interface Segregation**: Services have focused, minimal interfaces
- **Dependency Inversion**: High-level modules depend on abstractions

### DRY (Don't Repeat Yourself)

- Eliminated duplicate coordinate transformation code
- Standardized status bar updates with a helper method
- Centralized view state management

### YAGNI (You Aren't Gonna Need It)

- Removed unnecessary code and methods
- Focused on essential functionality

### KISS (Keep It Simple, Stupid)

- Simplified transformation logic
- Made code more readable and maintainable
- Improved error handling for better robustness

## Using the Refactored Code

When working with curve operations, prefer using the `CurveService` as a facade:

```python
# Example of selecting and updating a point
CurveService.select_point_by_index(curve_view, main_window, point_index)
CurveService.update_point_position(curve_view, main_window, point_index, new_x, new_y)

# Example of transforming coordinates
view_state = ViewState.from_curve_view(curve_view)
screen_x, screen_y = TransformationService.transform_point(view_state, data_x, data_y)
```

By following this API, you'll ensure consistent coordinate transformations and maintain the architectural boundaries of the application.
