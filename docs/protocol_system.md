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

### UI Component Protocols

#### CurveViewProtocol

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

#### MainWindowProtocol

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

### Service Protocols

#### FileServiceProtocol

Defines the interface for file operations:

```python
class FileServiceProtocol(Protocol):
    """Protocol defining the interface for file operations."""

    def export_to_csv(self, main_window: MainWindowProtocol) -> None: ...
    def load_track_data(self, main_window: MainWindowProtocol) -> None: ...
    def add_track_data(self, main_window: MainWindowProtocol) -> None: ...
    def save_track_data(self, main_window: MainWindowProtocol) -> None: ...
    def load_image_sequence(self, main_window: MainWindowProtocol) -> None: ...
```

#### ImageServiceProtocol

Defines the interface for image operations:

```python
class ImageServiceProtocol(Protocol):
    """Protocol defining the interface for image operations."""

    def set_current_image_by_frame(self, curve_view: CurveViewProtocol, frame: int) -> None: ...
    def load_current_image(self, curve_view: ImageSequenceProtocol) -> None: ...
    def set_current_image_by_index(self, curve_view: ImageSequenceProtocol, idx: int) -> None: ...
    def load_image_sequence(self, main_window: MainWindowProtocol) -> None: ...
    def set_image_sequence(self, curve_view: ImageSequenceProtocol, path: str, filenames: List[str]) -> None: ...
```

#### HistoryServiceProtocol

Defines the interface for history operations:

```python
class HistoryServiceProtocol(Protocol):
    """Protocol defining the interface for history operations."""

    def add_to_history(self, main_window: HistoryContainerProtocol) -> None: ...
    def update_history_buttons(self, main_window: HistoryContainerProtocol) -> None: ...
    def undo_action(self, main_window: HistoryContainerProtocol) -> None: ...
    def redo_action(self, main_window: HistoryContainerProtocol) -> None: ...
    def restore_state(self, main_window: HistoryContainerProtocol, state: Dict[str, Any]) -> None: ...
```

#### DialogServiceProtocol

Defines the interface for dialog operations:

```python
class DialogServiceProtocol(Protocol):
    """Protocol defining the interface for dialog operations."""

    def show_smooth_dialog(self, parent_widget: Any, curve_data: PointsList,
                          selected_indices: List[int], selected_point_idx: int) -> Optional[PointsList]: ...
    def show_filter_dialog(self, main_window: MainWindowProtocol) -> None: ...
    def detect_gaps(self, main_window: MainWindowProtocol) -> List[Tuple[int, int]]: ...
    def show_fill_gaps_dialog(self, main_window: MainWindowProtocol) -> None: ...
    def fill_gap(self, main_window: MainWindowProtocol, start_frame: int,
                end_frame: int, method_index: int, preserve_endpoints: bool) -> None: ...
    def show_extrapolate_dialog(self, main_window: MainWindowProtocol) -> None: ...
    def show_shortcuts_dialog(self, main_window: MainWindowProtocol) -> None: ...
    def show_offset_dialog(self, main_window: MainWindowProtocol) -> Optional[PointsList]: ...
    def show_problem_detection_dialog(self, main_window: MainWindowProtocol,
                                    problems: Optional[List[Tuple[int, Any, Any, Any]]]) -> Optional[Any]: ...
```

### Data Protocols

#### ImageSequenceProtocol

```python
class ImageSequenceProtocol(Protocol):
    """Protocol defining the interface for image sequence operations."""

    image_filenames: List[str]
    image_sequence_path: str
    current_image_idx: int
    background_image: Optional[ImageProtocol]
    scale_to_image: bool

    def update(self) -> None: ...
```

#### HistoryStateProtocol

```python
class HistoryStateProtocol(Protocol):
    """Protocol defining the structure of a history state."""

    curve_data: PointsList
    point_name: str
    point_color: str
```

#### HistoryContainerProtocol

```python
class HistoryContainerProtocol(Protocol):
    """Protocol defining the interface for a component that contains history."""

    history: List[Dict[str, Any]]
    history_index: int
    max_history_size: int
    undo_button: Any
    redo_button: Any
    curve_data: PointsList
    point_name: str
    point_color: str
    curve_view: CurveViewProtocol
    info_label: Any
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

Example from the FileService:

```python
@staticmethod
def load_track_data(main_window: MainWindowProtocol) -> None:
    """Load 2D track data from a file."""
    file_path, _ = QFileDialog.getOpenFileName(
        main_window, "Load 2D Track Data", main_window.default_directory, "Text Files (*.txt);;All Files (*)"
    )
    # Implementation...
```

## Benefits

1. **Improved Type Safety**: Static type checkers can verify correct usage of components
2. **Better IDE Support**: IDEs can provide completion and documentation based on protocols
3. **Consistent Interfaces**: Ensures components implement required methods and attributes
4. **Decoupled Components**: Reduces dependencies on concrete implementations
5. **Self-Documenting Code**: The protocol definitions serve as documentation of expected interfaces
6. **Direct Property Access**: Enables direct property access instead of using `getattr()` calls

## Extending the Protocol System

When adding new functionality that spans multiple components:

1. Add new protocol definitions to `services/protocols.py`
2. Update existing protocols with new required methods or attributes
3. Update service method signatures to use the protocols
4. Use property access through protocol interfaces instead of getattr calls

## Implementation Status

The protocol system has been implemented for the following components:

- ✅ CurveView and MainWindow core interfaces
- ✅ CurveService
- ✅ TransformationService
- ✅ FileService
- ✅ ImageService
- ✅ HistoryService
- ✅ DialogService
- ⏳ AnalysisService (partially implemented)
- ⏳ VisualizationService (partially implemented)
- ⏳ SettingsService (planned)
- ⏳ InputService (planned)

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
