# CurveEditor Coding Standards

## Type Hints (Required)

All functions and methods must have complete type hints:

```python
# ✅ REQUIRED - Complete type annotations
def transform_point(self, point: CurvePoint, frame: int) -> tuple[float, float]:
    """Transform point to screen coordinates."""
    return (x, y)

# ✅ REQUIRED - Protocol return types
def get_selection(self, curve_name: str) -> set[int]:
    """Get selected point indices for curve."""
    return self._selections.get(curve_name, set())

# ❌ FORBIDDEN - Missing type hints
def process_data(data):  # Missing parameter and return types
    return result
```

### TYPE_CHECKING Pattern

Use TYPE_CHECKING blocks to avoid circular imports:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.data_service import DataService
    from ui.main_window import MainWindow
else:
    # Runtime imports or None assignments
    DataService = None
    MainWindow = None

def get_data_service() -> "DataService":
    """Lazy import with forward reference."""
    # Implementation with lazy import
```

### Protocol Definitions

All service interfaces must use Protocol classes:

```python
from typing import Protocol

class TransformServiceProtocol(Protocol):
    """Protocol for coordinate transformation operations."""
    
    def data_to_screen(self, data_point: tuple[float, float]) -> QPointF:
        """Convert data coordinates to screen coordinates."""
        ...
    
    def screen_to_data(self, screen_point: QPointF) -> tuple[float, float]:
        """Convert screen coordinates to data coordinates."""
        ...
```

## Import Patterns

### Service Imports

Always use service getters, never direct imports between services:

```python
# ✅ CORRECT - Use service getters
from services import get_data_service, get_transform_service

def some_method(self):
    data_service = get_data_service()
    transform_service = get_transform_service()

# ❌ FORBIDDEN - Direct service imports
from services.data_service import DataService  # Creates circular dependency
```

### Lazy Imports

Use lazy imports for heavy dependencies or circular references:

```python
def expensive_operation(self):
    """Import only when needed."""
    from heavy_module import ExpensiveClass
    return ExpensiveClass().process()
```

### Protocol Imports

Protocol imports are always safe at module level:

```python
# ✅ SAFE - Protocols never create circular dependencies
from protocols.ui import CurveViewProtocol, MainWindowProtocol
from services.service_protocols import BatchEditableProtocol
```

## Docstring Conventions

### Public Methods (Required)

All public methods must have docstrings with parameters and return values:

```python
def add_curve_data(self, curve_name: str, points: list[CurvePoint]) -> bool:
    """Add curve data to the collection.
    
    Args:
        curve_name: Unique identifier for the curve
        points: List of curve points to add
        
    Returns:
        True if data was added successfully, False if curve already exists
        
    Raises:
        ValueError: If curve_name is empty or points list is invalid
    """
```

### Private Methods (Optional)

Private methods should have brief docstrings for complex logic:

```python
def _rebuild_spatial_index(self) -> None:
    """Rebuild spatial index for efficient point lookup."""
```

### Class Docstrings

Classes should document their purpose and key responsibilities:

```python
class TransformService:
    """Manages coordinate transformations and view state.
    
    Handles conversion between data coordinates and screen coordinates,
    manages zoom/pan state, and provides thread-safe transformation
    operations for the curve editor.
    
    This service uses singleton pattern and is thread-safe.
    """
```

## Error Handling Patterns

### Service Method Error Handling

Services should handle errors gracefully and return meaningful results:

```python
def load_curve_data(self, file_path: Path) -> tuple[bool, str]:
    """Load curve data from file.
    
    Returns:
        Tuple of (success, error_message). If success is True,
        error_message is empty. If False, contains user-friendly error.
    """
    try:
        # File loading logic
        return True, ""
    except FileNotFoundError:
        return False, f"File not found: {file_path}"
    except PermissionError:
        return False, f"Permission denied: {file_path}"
    except Exception as e:
        logger.exception("Unexpected error loading file")
        return False, f"Failed to load file: {str(e)}"
```

### Qt Widget Error Handling

Handle Qt object lifecycle issues:

```python
def update_widget_safely(self, widget: QWidget, text: str) -> None:
    """Update widget text with safety checks."""
    try:
        if widget is not None and not widget.isHidden():
            widget.setText(text)
    except RuntimeError:
        # Qt object was deleted at C++ level
        logger.debug("Widget was deleted, skipping update")
```

### Validation Patterns

Use early returns for validation:

```python
def set_frame(self, frame: int) -> bool:
    """Set current frame with validation."""
    if frame < 0:
        logger.warning(f"Invalid frame number: {frame}")
        return False
    
    if not self.has_data():
        logger.debug("No data loaded, cannot set frame")
        return False
    
    # Main logic here
    self._current_frame = frame
    return True
```

## Qt-Specific Patterns

### Signal/Slot Connections

Use new-style signal connections with type safety:

```python
# ✅ CORRECT - New-style connections
self.button.clicked.connect(self.on_button_clicked)
self.data_changed.connect(self.update_display)

# ✅ CORRECT - Lambda with proper capture
self.button.clicked.connect(lambda: self.process_data(self.current_data))

# ❌ AVOID - Old-style string connections
self.connect(self.button, SIGNAL("clicked()"), self.on_button_clicked)
```

### Widget Lifecycle

Initialize data before calling super().__init__():

```python
class CurveViewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        # Initialize data first
        self._curve_data: dict[str, list[CurvePoint]] = {}
        self._selection: set[int] = set()
        
        # Then call super
        super().__init__(parent)
        
        # UI setup after super
        self._setup_ui()
```

### Thread Safety

Use proper locking for shared state:

```python
class DataService:
    def __init__(self):
        self._lock = threading.RLock()  # Reentrant lock
        self._data: dict[str, Any] = {}
    
    def get_data(self, key: str) -> Any | None:
        """Thread-safe data access."""
        with self._lock:
            return self._data.get(key)
    
    def set_data(self, key: str, value: Any) -> None:
        """Thread-safe data modification."""
        with self._lock:
            self._data[key] = value
```

## Service Implementation Patterns

### Singleton Pattern

Services use module-level singletons with thread-safe initialization:

```python
# In services/__init__.py
_data_service: DataService | None = None
_service_lock = threading.Lock()

def get_data_service() -> DataService:
    """Get singleton DataService instance (thread-safe)."""
    global _data_service
    with _service_lock:
        if _data_service is None:
            from services.data_service import DataService
            _data_service = DataService()
    return _data_service
```

### Protocol Implementation

Services should implement their protocols explicitly:

```python
class DataService(DataServiceProtocol):
    """Concrete implementation of data service protocol."""
    
    def load_file(self, path: Path) -> tuple[bool, str]:
        """Implementation matches protocol signature exactly."""
        # Implementation here
```

### Service Dependencies

Services can depend on other services through getters:

```python
class InteractionService:
    def __init__(self):
        # Don't store service references in __init__
        pass
    
    def select_point(self, point_index: int) -> None:
        """Select point using other services."""
        # Get services when needed
        data_service = get_data_service()
        transform_service = get_transform_service()
        
        # Use services
        if data_service.has_point(point_index):
            # Logic here
```

## Performance Patterns

### Lazy Evaluation

Compute expensive operations only when needed:

```python
class CurveRenderer:
    def __init__(self):
        self._screen_points_cache: dict[str, list[QPointF]] | None = None
        self._cache_dirty = True
    
    def get_screen_points(self, curve_name: str) -> list[QPointF]:
        """Get screen points with lazy cache rebuild."""
        if self._cache_dirty or self._screen_points_cache is None:
            self._rebuild_cache()
        return self._screen_points_cache.get(curve_name, [])
```

### Batch Operations

Process multiple items efficiently:

```python
def update_multiple_points(self, updates: list[tuple[int, CurvePoint]]) -> None:
    """Update multiple points in a single operation."""
    with self._lock:
        # Batch all updates
        for point_index, new_point in updates:
            self._points[point_index] = new_point
        
        # Single cache invalidation
        self._invalidate_cache()
        
        # Single signal emission
        self.points_changed.emit()
```

## Code Organization

### File Structure

Keep files focused and reasonably sized:

```python
# ✅ GOOD - Single responsibility
# ui/curve_view_widget.py - Only curve view logic
# ui/timeline_widget.py - Only timeline logic
# services/data_service.py - Only data operations

# ❌ AVOID - Mixed responsibilities
# ui/widgets.py - Multiple unrelated widgets
# services/everything_service.py - Too many responsibilities
```

### Class Organization

Organize class members logically:

```python
class CurveViewWidget(QWidget):
    # 1. Signals first
    selection_changed = Signal(set)
    
    # 2. Constructor
    def __init__(self, parent: QWidget | None = None):
        pass
    
    # 3. Public methods
    def add_curve_data(self, data: list[CurvePoint]) -> None:
        pass
    
    # 4. Qt overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        pass
    
    # 5. Event handlers
    def mousePressEvent(self, event: QMouseEvent) -> None:
        pass
    
    # 6. Private methods
    def _setup_ui(self) -> None:
        pass
```

## Naming Conventions

### Variables and Functions

Use descriptive names following Python conventions:

```python
# ✅ GOOD - Clear, descriptive names
curve_data: list[CurvePoint]
selected_point_indices: set[int]
transform_data_to_screen(point: tuple[float, float]) -> QPointF

# ❌ AVOID - Unclear abbreviations
cd: list[CurvePoint]  # What does 'cd' mean?
sel_pts: set[int]     # Unclear abbreviation
transform_d2s()       # Cryptic function name
```

### Qt Method Overrides

Qt method names are exempt from Python naming conventions:

```python
# ✅ ALLOWED - Qt override methods
def paintEvent(self, event: QPaintEvent) -> None:  # camelCase OK
def mousePressEvent(self, event: QMouseEvent) -> None:  # camelCase OK

# ✅ PREFERRED - Python methods
def update_selection(self, indices: set[int]) -> None:  # snake_case
def get_curve_data(self) -> list[CurvePoint]:  # snake_case
```

## Logging Patterns

Use structured logging with appropriate levels:

```python
import logging

logger = logging.getLogger(__name__)

class DataService:
    def load_file(self, path: Path) -> tuple[bool, str]:
        """Load file with proper logging."""
        logger.info(f"Loading curve data from {path}")
        
        try:
            # File loading logic
            logger.debug(f"Successfully loaded {len(points)} points")
            return True, ""
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return False, str(e)
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational messages
- **WARNING**: Recoverable issues
- **ERROR**: Serious problems that prevent operation
- **CRITICAL**: System-level failures

## Testing Integration

Write code that's easy to test:

```python
# ✅ TESTABLE - Dependencies injected, pure functions
def calculate_curve_bounds(points: list[CurvePoint]) -> tuple[float, float, float, float]:
    """Calculate bounding box for points."""
    # Pure function, easy to test
    
class CurveRenderer:
    def __init__(self, transform_service: TransformServiceProtocol):
        self._transform = transform_service  # Dependency injection
    
    def render_points(self, points: list[CurvePoint]) -> QImage:
        """Render points to image."""
        # Testable with mock transform service

# ❌ HARD TO TEST - Hidden dependencies, side effects
def render_current_curve():
    # Gets global state, creates Qt widgets
    # Difficult to test in isolation
```

This coding standards document should be followed for all new code and used as a guide when refactoring existing code.