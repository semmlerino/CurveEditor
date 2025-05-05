# CurveEditor Protocol System

This document describes the protocol system implemented in the CurveEditor application to enforce consistent interfaces between components and improve type safety.

## Overview

Protocols in Python provide a way to define interfaces that classes should implement, similar to interfaces in other programming languages. The CurveEditor application uses protocols to define the expected structure and behavior of key components, ensuring type safety and better IDE support without relying on inheritance.

## Central Protocol Definitions

All protocol definitions are centralized in `services/protocols.py` to maintain a single source of truth for interface definitions. This file contains:

1. **Structural Protocols**: Define the required attributes and methods of components
2. **Type Aliases**: Define common type patterns for reuse throughout the application
3. **Generic Types**: Define generic type variables for flexible typing

## Key Protocols

### CurveViewProtocol

Defines the interface for curve view components:

```python
class CurveViewProtocol(Protocol):
    """Protocol defining the interface for curve view components."""

    # Required attributes
    x_offset: float
    y_offset: float
    flip_y_axis: bool
    scale_to_image: bool
    background_image: Optional[Any]
    image_width: int
    image_height: int
    zoom_factor: float

    # Required methods
    def update(self) -> None: ...
    def setPoints(self, points: List[Tuple[int, float, float]]) -> None: ...
    def get_selected_points(self) -> List[int]: ...
```

### MainWindowProtocol

Defines the interface for the main window:

```python
class MainWindowProtocol(Protocol):
    """Protocol defining the interface for the main window."""

    # Required attributes
    curve_view: CurveViewProtocol

    # Required methods
    def update_status_message(self, message: str) -> None: ...
    def refresh_point_edit_controls(self) -> None: ...
```

### Common Type Aliases

```python
PointTuple = Tuple[int, float, float]  # frame, x, y
PointTupleWithStatus = Tuple[int, float, float, bool]  # frame, x, y, interpolated
PointsList = List[Union[PointTuple, PointTupleWithStatus]]
```

## Usage in Services

Services use these protocols to define parameter types:

```python
@staticmethod
def transform_point_to_widget(
    curve_view: CurveViewProtocol,
    x: float,
    y: float,
    display_width: float,
    display_height: float,
    offset_x: float,
    offset_y: float,
    scale: float
) -> Tuple[float, float]:
    # Implementation...
```

## Benefits

1. **Improved Type Safety**: Static type checkers can verify correct usage of components
2. **Better IDE Support**: IDEs can provide completion and documentation based on protocols
3. **Consistent Interfaces**: Ensures components implement required methods and attributes
4. **Decoupled Components**: Reduces dependencies on concrete implementations
5. **Self-Documenting Code**: The protocol definitions serve as documentation of expected interfaces

## Extending the Protocol System

When adding new functionality that spans multiple components:

1. Add new protocol definitions to `services/protocols.py`
2. Update existing protocols with new required methods or attributes
3. Update service method signatures to use the protocols
4. Use property access through protocol interfaces instead of getattr calls

## Type Checking Considerations

For runtime type checking or when using protocols in concrete implementations:

```python
from typing import cast
from services.protocols import CurveViewProtocol

# Cast a component to a protocol type
curve_view = cast(CurveViewProtocol, some_component)
```

## Protocol vs. Abstract Base Classes

The protocol system is preferred over abstract base classes because:

1. Protocols support structural typing (duck typing) rather than nominal typing
2. No inheritance required, which allows for more flexible component designs
3. Better compatibility with existing components that weren't designed with inheritance in mind
4. Easier to evolve interfaces over time without breaking existing implementations
