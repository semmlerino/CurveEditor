# Architecture Guide

## Overview

CurveEditor follows a service-oriented architecture that emphasizes separation of concerns, modularity, and maintainability. This guide explains the key architectural patterns and design decisions.

## Architectural Principles

### 1. Service-Oriented Design

The application organizes functionality into focused services:

```
services/
├── curve_service.py         # Curve manipulation operations
├── unified_transformation_service.py  # Coordinate transformations
├── centering_zoom_service.py # View positioning and zoom
├── visualization_service.py  # Visual display management
├── file_service.py          # File I/O operations
├── history_service.py       # Undo/redo functionality
├── input_service.py         # User input handling
└── settings_service.py      # Configuration management
```

### 2. Immutable Data Structures

Key classes use immutable design for consistency:

- **Transform**: Represents coordinate transformations
- **ViewState**: Captures view configuration
- **Point data**: Curve points remain immutable during operations

### 3. Dependency Injection

Services receive dependencies explicitly rather than accessing globals:

```python
class CurveService:
    @staticmethod
    def update_point_position(curve_view, main_window, index, x, y):
        # Dependencies passed as parameters
        pass
```

## Core Components

### 1. CurveView (Primary UI Component)

```
curve_view.py                 # Main widget implementation
enhanced_curve_view.py        # Enhanced features
curve_view_plumbing.py        # Internal connections
```

**Responsibilities:**
- User interaction handling
- Visual curve rendering
- Coordinate space management
- Event delegation to services

### 2. Services Layer

**CurveService**
- Point selection and manipulation
- Curve data operations
- Integration with other services

**UnifiedTransformationService**
- All coordinate transformations
- Performance optimization through caching
- Stability tracking

**VisualizationService**
- Rendering configuration
- Visual properties management
- Display updates

### 3. Models and State

```
services/
├── models.py                # Data models
├── view_state.py           # View configuration
├── unified_transform.py     # Transformation model
└── protocols.py            # Type definitions
```

### 4. UI Components

```
main_window.py              # Application window
ui_components.py            # Reusable UI elements
dialogs.py                  # Modal dialogs
menu_bar.py                 # Menu system
```

## Data Flow

### 1. User Interaction Flow

```
User Input → InputService → CurveService → ViewState Update → UI Refresh
```

Example: Moving a point

1. User drags point in CurveView
2. InputService captures mouse events
3. CurveService validates and applies changes
4. ViewState updated with new data
5. CurveView redraws with new positions

### 2. Transformation Flow

```
Data Coordinates → Transform → Screen Coordinates → UI Rendering
```

Example: Rendering points

1. CurveView requests point transformations
2. UnifiedTransformationService creates cached transform
3. Batch transformation applied to all points
4. Qt drawing operations use screen coordinates

### 3. File Operations Flow

```
UI Action → FileService → Data Validation → CurveService Update → UI Refresh
```

Example: Loading a file

1. User selects File → Open
2. FileService reads and parses file
3. Data validated and normalized
4. CurveService updates internal state
5. UI refreshes with new curve data

## Design Patterns

### 1. Facade Pattern

**CurveService** acts as a facade for curve operations:

```python
# Instead of complex direct manipulation
curve_view.selected_points.add(index)
curve_view.curve_data[index] = new_point
curve_view.update()

# Simple facade call
CurveService.select_point_by_index(curve_view, main_window, index)
```

### 2. Strategy Pattern

**TransformationService** uses strategy pattern for different coordinate systems:

```python
# Different transformation strategies
transform = Transform(scale=1.0, flip_y=False)  # Standard
transform = Transform(scale=2.0, flip_y=True)   # Flipped coordinates
```

### 3. Observer Pattern

**HistoryService** observes changes for undo/redo:

```python
# Services notify history of operations
HistoryService.record_operation("point_move", previous_state)
```

### 4. Command Pattern

User actions are encapsulated as commands for undo/redo:

```python
class MovePointCommand:
    def execute(self):
        # Apply point movement

    def undo(self):
        # Revert point movement
```

## Configuration and Settings

### 1. Settings Management

```python
# Centralized configuration
settings = SettingsService.get_settings()
settings.update('zoom_sensitivity', 1.5)
SettingsService.save_settings(settings)
```

### 2. Logging Configuration

```python
# Structured logging throughout application
from services.logging_service import LoggingService

logger = LoggingService.get_logger(__name__)
logger.info("Point moved", extra={'point_index': index})
```

## Error Handling Strategy

### 1. Layered Error Handling

- **UI Layer**: User-friendly error messages
- **Service Layer**: Business logic validation
- **Data Layer**: Input validation and sanitization

### 2. Error Recovery

```python
try:
    result = risky_operation()
except RecoverableError as e:
    logger.warning(f"Recoverable error: {e}")
    result = fallback_operation()
except FatalError as e:
    logger.error(f"Fatal error: {e}")
    raise
```

## Testing Architecture

### 1. Test Structure

```
tests/
├── test_curve_service.py            # Service-level tests
├── test_unified_transformation_system.py  # Transformation tests
├── test_main_window.py              # UI integration tests
└── test_error_handling.py          # Error handling tests
```

### 2. Testing Patterns

- **Unit Tests**: Individual service methods
- **Integration Tests**: Service interactions
- **UI Tests**: User interaction simulation
- **Performance Tests**: Transformation benchmarks

## Performance Considerations

### 1. Transformation Caching

```python
# Automatic caching in UnifiedTransformationService
transform = get_transform(curve_view)  # May be cached
qt_points = transform_points(curve_view, points)  # Batch operation
```

### 2. Lazy Loading

- Curve data loaded on demand
- Transformations calculated only when needed
- UI updates batched for efficiency

### 3. Memory Management

- Immutable objects reduce memory leaks
- Cache size limits prevent unbounded growth
- Weak references used where appropriate

## Extension Points

### 1. Adding New Services

```python
# services/new_service.py
class NewService:
    @staticmethod
    def new_operation(curve_view, parameters):
        # Implementation
        pass

# Register in services/__init__.py
from .new_service import NewService
```

### 2. Custom Transformations

```python
# Extend Transform class for specialized transformations
class CustomTransform(Transform):
    def apply_custom_operation(self, x, y):
        # Custom transformation logic
        return x, y
```

### 3. UI Extensions

```python
# Custom dialogs inherit from base classes
class CustomDialog(DialogBase):
    def setup_ui(self):
        # Custom UI setup
        pass
```

## Security Considerations

### 1. Input Validation

- All file inputs validated before processing
- User input sanitized to prevent injection
- Type checking enforced throughout

### 2. Error Information

- Sensitive information not exposed in error messages
- Debug information available in development only
- Logging configured appropriately for environment

## Future Architecture Goals

### 1. Plugin System

Enable third-party extensions through plugin architecture:

```python
# Future: Plugin registration
PluginManager.register_transformation_plugin(CustomTransformPlugin)
```

### 2. Microservices

Consider breaking larger services into focused microservices:

- Separate transformation service process
- Independent file processing service
- Distributed undo/redo service

### 3. Performance Improvements

- GPU acceleration for transformations
- Async file operations
- Background processing for large datasets

## Development Guidelines

### 1. Adding New Features

1. **Design**: Follow service-oriented principles
2. **Implement**: Use existing patterns and services
3. **Test**: Add comprehensive tests
4. **Document**: Update relevant documentation
5. **Integrate**: Ensure compatibility with existing code

### 2. Modifying Existing Code

1. **Understand**: Review related services and dependencies
2. **Plan**: Consider impact on other components
3. **Test**: Ensure no regressions
4. **Refactor**: Improve code quality when possible

### 3. Performance Optimization

1. **Profile**: Identify actual bottlenecks
2. **Optimize**: Focus on high-impact areas
3. **Measure**: Verify improvements
4. **Document**: Explain optimization decisions

The architecture is designed to be modular, maintainable, and extensible. By following these patterns and principles, new features can be added safely while maintaining the overall quality and performance of the application.
