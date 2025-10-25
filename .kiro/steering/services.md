# CurveEditor Service Architecture Guide

## 4-Service Architecture Overview

CurveEditor uses a consolidated 4-service architecture for clean separation of concerns:

1. **TransformService** - Coordinate transformations and view state
2. **DataService** - All data operations (analysis, file I/O, images)
3. **InteractionService** - User interactions, point manipulation, and history
4. **UIService** - UI operations, dialogs, and status updates

## Service Access Patterns

### Always Use Service Getters

Never import services directly - always use the getter functions:

```python
# ✅ CORRECT - Use service getters
from services import get_data_service, get_transform_service, get_interaction_service, get_ui_service

def some_operation(self):
    data_service = get_data_service()
    transform_service = get_transform_service()
    
    # Use services
    if data_service.has_curve_data():
        points = transform_service.transform_points(data_service.get_points())

# ❌ FORBIDDEN - Direct service imports
from services.data_service import DataService  # Creates circular dependencies
from services.transform_service import TransformService  # Breaks singleton pattern
```

### Service Getter Benefits

- **Thread Safety**: Getters use locks for safe singleton initialization
- **Lazy Loading**: Services created only when first accessed
- **Circular Dependency Prevention**: Avoids import cycles between services
- **Testability**: Easy to mock services in tests using `reset_all_services()`

## Individual Service Responsibilities

### TransformService

**Purpose**: Coordinate transformations and view state management

**Key Methods**:
```python
def data_to_screen(self, data_point: tuple[float, float]) -> QPointF:
    """Convert data coordinates to screen coordinates."""

def screen_to_data(self, screen_point: QPointF) -> tuple[float, float]:
    """Convert screen coordinates to data coordinates."""

def set_zoom_factor(self, factor: float) -> None:
    """Update zoom level and invalidate transform cache."""

def set_pan_offset(self, offset: QPointF) -> None:
    """Update pan offset and invalidate transform cache."""
```

**When to Use**:
- Converting between coordinate systems
- Managing zoom and pan state
- Calculating view bounds
- Screen-to-data hit testing

### DataService

**Purpose**: All data operations including analysis, file I/O, and image management

**Key Methods**:
```python
def load_curve_data(self, file_path: Path) -> tuple[bool, str]:
    """Load curve data from file."""

def get_curve_data(self, curve_name: str) -> list[CurvePoint] | None:
    """Get curve data by name."""

def analyze_curve_statistics(self, curve_name: str) -> dict[str, float]:
    """Calculate curve statistics (bounds, velocity, etc.)."""

def load_background_image(self, image_path: Path) -> tuple[bool, str]:
    """Load background reference image."""
```

**When to Use**:
- Loading/saving curve data files
- Managing curve data collections
- Calculating curve statistics and analysis
- Background image operations
- Data validation and processing

### InteractionService

**Purpose**: User interactions, point manipulation, and complete history management

**Key Methods**:
```python
def select_points(self, curve_name: str, point_indices: set[int]) -> None:
    """Select points and record in history."""

def move_points(self, curve_name: str, point_indices: set[int], delta: tuple[float, float]) -> None:
    """Move points and create undo command."""

def delete_points(self, curve_name: str, point_indices: set[int]) -> None:
    """Delete points with undo support."""

def undo(self) -> bool:
    """Undo last operation."""

def redo(self) -> bool:
    """Redo last undone operation."""
```

**When to Use**:
- Processing mouse/keyboard interactions
- Point selection and manipulation
- Any operation that should be undoable
- Batch editing operations
- Multi-curve interactions

### UIService

**Purpose**: UI operations, dialogs, and status updates

**Key Methods**:
```python
def show_error_dialog(self, title: str, message: str) -> None:
    """Display error dialog to user."""

def update_status_bar(self, message: str) -> None:
    """Update main window status bar."""

def show_progress_dialog(self, title: str, max_value: int) -> QProgressDialog:
    """Show progress dialog for long operations."""

def get_file_path_from_user(self, title: str, filters: str) -> Path | None:
    """Show file dialog and return selected path."""
```

**When to Use**:
- Showing dialogs and user prompts
- Updating UI status and progress
- Managing UI state coordination
- Settings persistence

## Service Interaction Patterns

### Cross-Service Communication

Services can call other services through getters:

```python
class InteractionService:
    def move_selected_points(self, delta: tuple[float, float]) -> None:
        """Move currently selected points."""
        # Get other services
        data_service = get_data_service()
        ui_service = get_ui_service()
        
        # Get current selection
        active_curve = data_service.get_active_curve_name()
        if not active_curve:
            ui_service.update_status_bar("No active curve")
            return
        
        selected_indices = self.get_selection(active_curve)
        if not selected_indices:
            ui_service.update_status_bar("No points selected")
            return
        
        # Perform the move operation
        self.move_points(active_curve, selected_indices, delta)
        ui_service.update_status_bar(f"Moved {len(selected_indices)} points")
```

### Service Coordination Example

Complex operations often involve multiple services:

```python
def load_and_display_curve_file(file_path: Path) -> None:
    """Complete workflow for loading a curve file."""
    # Get all needed services
    data_service = get_data_service()
    transform_service = get_transform_service()
    interaction_service = get_interaction_service()
    ui_service = get_ui_service()
    
    # Show progress
    progress = ui_service.show_progress_dialog("Loading", 100)
    
    try:
        # Load data
        success, error_msg = data_service.load_curve_data(file_path)
        progress.setValue(50)
        
        if not success:
            ui_service.show_error_dialog("Load Error", error_msg)
            return
        
        # Auto-fit view to data
        bounds = data_service.get_curve_bounds("main")
        transform_service.fit_to_bounds(bounds)
        progress.setValue(75)
        
        # Clear selection and history
        interaction_service.clear_selection()
        interaction_service.clear_history()
        progress.setValue(100)
        
        ui_service.update_status_bar(f"Loaded {file_path.name}")
        
    finally:
        progress.close()
```

## Thread Safety

### Service Locking

All services use `threading.RLock()` for thread safety:

```python
class DataService:
    def __init__(self):
        self._lock = threading.RLock()  # Reentrant lock
        self._data: dict[str, Any] = {}
    
    def thread_safe_operation(self) -> Any:
        """All service methods should use the lock."""
        with self._lock:
            # Safe to call other service methods here
            # RLock allows reentrant calls
            return self._perform_operation()
```

### Cross-Service Thread Safety

When services call each other, RLock prevents deadlocks:

```python
class InteractionService:
    def complex_operation(self) -> None:
        """Service methods can safely call other services."""
        with self._lock:
            # This is safe - RLock allows reentrant acquisition
            data_service = get_data_service()
            data_service.some_method()  # This also acquires its own lock
```

## Protocol Implementation

### Service Protocols

Each service implements a protocol for type safety:

```python
# Define protocol
class DataServiceProtocol(Protocol):
    def load_curve_data(self, file_path: Path) -> tuple[bool, str]: ...
    def get_curve_data(self, curve_name: str) -> list[CurvePoint] | None: ...

# Implement protocol
class DataService(DataServiceProtocol):
    """Concrete implementation must match protocol exactly."""
    
    def load_curve_data(self, file_path: Path) -> tuple[bool, str]:
        # Implementation here
        pass
```

### Using Protocols in Type Hints

Use protocols for dependency injection and testing:

```python
class CurveRenderer:
    def __init__(self, 
                 data_service: DataServiceProtocol,
                 transform_service: TransformServiceProtocol):
        self._data = data_service
        self._transform = transform_service
    
    def render(self) -> QImage:
        """Render using protocol methods."""
        points = self._data.get_curve_data("main")
        if points:
            screen_points = [self._transform.data_to_screen(p.position) for p in points]
            # Render screen_points
```

## Testing Services

### Service Mocking

Use `reset_all_services()` for clean test isolation:

```python
@pytest.fixture(autouse=True)
def reset_services():
    """Reset all services between tests."""
    yield
    from services import reset_all_services
    reset_all_services()

def test_service_interaction():
    """Test with fresh service instances."""
    data_service = get_data_service()
    interaction_service = get_interaction_service()
    
    # Test interaction
    data_service.add_curve_data("test", test_points)
    interaction_service.select_points("test", {0, 1})
    
    assert interaction_service.get_selection("test") == {0, 1}
```

### Protocol Mocking

Mock services using their protocols:

```python
def test_with_mock_service(monkeypatch):
    """Test using mocked service."""
    mock_data_service = Mock(spec=DataServiceProtocol)
    mock_data_service.get_curve_data.return_value = test_points
    
    # Replace service getter
    monkeypatch.setattr("services.get_data_service", lambda: mock_data_service)
    
    # Test code that uses get_data_service()
    result = some_function_that_uses_data_service()
    assert result is not None
```

## Service Anti-Patterns

### ❌ Don't Store Service References

```python
# ❌ BAD - Storing service references
class SomeClass:
    def __init__(self):
        self._data_service = get_data_service()  # Don't store
    
    def method(self):
        return self._data_service.get_data()  # Hard to test

# ✅ GOOD - Get services when needed
class SomeClass:
    def method(self):
        data_service = get_data_service()  # Get when needed
        return data_service.get_data()  # Easy to mock
```

### ❌ Don't Create Service Dependencies in __init__

```python
# ❌ BAD - Service dependencies in constructor
class InteractionService:
    def __init__(self):
        self._data_service = get_data_service()  # Creates circular dependency

# ✅ GOOD - Get services in methods
class InteractionService:
    def select_point(self, point_index: int):
        data_service = get_data_service()  # Get when needed
        # Use service
```

### ❌ Don't Bypass Service Getters

```python
# ❌ BAD - Direct instantiation
service = DataService()  # Bypasses singleton pattern

# ❌ BAD - Direct imports
from services.data_service import DataService  # Creates cycles

# ✅ GOOD - Use getters
service = get_data_service()  # Proper singleton access
```

## Service Extension Patterns

### Adding New Service Methods

When adding methods to existing services:

1. Add to the protocol first
2. Implement in the concrete service
3. Add tests for the new method
4. Update documentation

```python
# 1. Add to protocol
class DataServiceProtocol(Protocol):
    def new_method(self, param: str) -> bool: ...

# 2. Implement in service
class DataService(DataServiceProtocol):
    def new_method(self, param: str) -> bool:
        """New method implementation."""
        with self._lock:
            # Implementation
            return True

# 3. Test the new method
def test_new_method():
    service = get_data_service()
    result = service.new_method("test")
    assert result is True
```

### Service Composition

For complex operations, compose services rather than adding to existing ones:

```python
class CurveAnalyzer:
    """Composes multiple services for complex analysis."""
    
    def analyze_curve_motion(self, curve_name: str) -> dict[str, float]:
        """Analyze curve motion using multiple services."""
        data_service = get_data_service()
        transform_service = get_transform_service()
        
        # Get data
        points = data_service.get_curve_data(curve_name)
        if not points:
            return {}
        
        # Calculate screen-space velocities
        screen_points = [transform_service.data_to_screen(p.position) for p in points]
        
        # Analyze motion
        return self._calculate_motion_stats(screen_points)
```

This service architecture provides a clean, testable, and maintainable foundation for the CurveEditor application.