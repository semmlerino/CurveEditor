# CurveEditor Development Guide

Comprehensive reference for the CurveEditor codebase - a Python/PySide6 application for editing animation curves with a consolidated 4-service architecture.

## Code Quality Standards

1. **Type Safety First**: Use type hints, avoid `hasattr()` (destroys type information)
2. **Service Architecture**: Respect the 4-service pattern
3. **Protocol Interfaces**: Type-safe duck-typing
4. **Component Container Pattern**: Access UI via `self.ui.<group>.<widget>`
5. **Validation Before Integration**: Prevent silent attribute creation

## Architecture

### Core Services
1. **TransformService**: Coordinate transformations, view state (99.9% cache hit rate)
2. **DataService**: Data operations, file I/O, image management
3. **InteractionService**: User interactions, point manipulation (64.7x spatial indexing)
4. **UIService**: UI operations, dialogs, status updates

### Service Access
```python
from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service
```

## Core Data Models (`core/models.py`)

```python
@dataclass(frozen=True)
class CurvePoint:
    frame: int
    x: float
    y: float
    status: PointStatus = PointStatus.NORMAL
    # Methods: distance_to(), with_status(), with_coordinates(), to_tuple3/4()

class PointCollection:
    # Methods: get_keyframes(), find_at_frame(), sorted_by_frame()

class PointStatus(Enum):
    NORMAL, INTERPOLATED, KEYFRAME
```

## Main UI Components

### CurveViewWidget (`ui/curve_view_widget.py`)
- **Data**: `curve_data`, `selected_indices`
- **View**: `zoom_factor`, `pan_offset_x/y`, `background_image`
- **Transform**: `data_to_screen()`, `screen_to_data()`, `get_transform()`
- **Operations**: `set_curve_data()`, `add_point()`, `update_point()`, `remove_point()`
- **Signals**: `point_selected`, `point_moved`, `selection_changed`, `view_changed`

### MainWindow (`ui/main_window.py`)
- **Components**: `curve_widget`, `timeline_tabs`, `playback_state`, `ui` (UIComponents)
- **File Ops**: Delegated to FileOperations class
- **State**: Managed by StateManager class
- **Frame Nav**: `_on_frame_changed()`, `_update_frame_display()`
- **Playback**: Oscillating playback with timer
- **Features**: Background thread loading, keyboard shortcuts

## Key Operations

### Point Manipulation
- **Select**: Left-click (single), Ctrl+click (multi), Alt+drag (rubber band)
- **Move**: Drag & drop, Numpad 2/4/6/8 (with Shift=10x, Ctrl=0.1x)
- **Delete**: Delete key
- **Status**: Toggle Normal/Interpolated/Keyframe

### View Controls
- **Zoom**: Mouse wheel (cursor-centered)
- **Pan**: Middle-click drag
- **Center**: C key (on selection)
- **Fit**: F key (to background/curve)

### Keyboard Shortcuts
```
C: Center on selection    Delete: Remove points     Numpad 2/4/6/8: Nudge
F: Fit to view           Escape: Deselect all      Ctrl+Z/Y: Undo/Redo
```

## Rendering Pipeline (`rendering/optimized_curve_renderer.py`)

**47x Performance Improvement**:
- Viewport culling with spatial indexing
- Level-of-detail based on zoom
- NumPy vectorized transformations
- Adaptive quality based on FPS

## File Organization

```
CurveEditor/
├── core/           # Data models (CurvePoint, PointCollection)
├── data/           # Data operations, batch editing
├── rendering/      # Optimized rendering (47x faster)
├── services/       # 4 consolidated services
├── ui/             # MainWindow, CurveViewWidget, UIComponents, FileOperations
├── tests/          # Test suite (549 tests)
├── session/        # Session state persistence
├── main.py         # Entry point
├── bpr             # Basedpyright wrapper (MUST USE THIS!)
└── venv/           # Python 3.11, PySide6==6.4.0
```

## Development Environment

### Linting & Type Checking
```bash
source venv/bin/activate

# Ruff
ruff check . --fix

# Basedpyright (MUST use wrapper due to shell redirection bug)
./bpr                     # Check all
./bpr ui/main_window.py  # Check specific
./bpr | tail -10         # Summary

# DON'T use: basedpyright . 2>&1  # BROKEN - interprets "2" as filename
```

### Testing
```bash
python -m pytest tests/           # All tests
python -m pytest tests/ -x        # Stop on first failure
python3 -m py_compile <file.py>  # Syntax check
```

## Type Safety Best Practices

### Avoid hasattr() - Destroys Type Information
```python
# BAD - Type becomes Any
if hasattr(self, 'main_window') and self.main_window:
    current_frame = self.main_window.current_frame  # Type lost!

# GOOD - Type preserved
if self.main_window is not None:
    current_frame = self.main_window.current_frame  # Type safe!
```

### Use Properties & Protocols
```python
@property
def current_frame(self) -> int:
    return self._get_current_frame()

class HasCurrentFrame(Protocol):
    @property
    def current_frame(self) -> int: ...
```

### When hasattr() is OK
- Dynamic runtime attributes
- Duck-typing multiple object types
- Cache initialization checks
- Optional debug flags

## Basedpyright Type Ignores

### Use `pyright: ignore` with Specific Rules
```python
# BAD - Old style, less safe
data = something()  # type: ignore

# BAD - Blanket ignore without rule
self.curve_widget.set_curve_data(data)  # pyright: ignore

# GOOD - Basedpyright preferred with specific rule
self.curve_widget.set_curve_data(data)  # pyright: ignore[reportArgumentType]
```

### Common Diagnostic Rules
- **reportArgumentType**: Argument type mismatches
- **reportReturnType**: Return type mismatches
- **reportAssignmentType**: Assignment incompatibilities
- **reportOptionalMemberAccess**: Accessing potentially None attributes
- **reportUnknownVariableType**: Unknown variable types
- **reportUnknownMemberType**: Unknown class/instance member types

### Enforced in Configuration
```json
// basedpyrightconfig.json
{
  "reportIgnoreCommentWithoutRule": "error"  // Requires specific rules
}
```

### Better Alternatives to Type Ignores
1. **Type Casting**: `cast(TargetType, value)`
2. **Fix Root Cause**: Update protocols and type definitions
3. **Union Types**: Handle multiple possibilities explicitly
4. **Type Guards**: Use isinstance() or custom type guards

## Integration Pitfalls


### Prevention
```python
# Validate structure first
assert hasattr(ui.timeline, 'frame_spinbox')
assert isinstance(self.point_x_spinbox, QDoubleSpinBox)

# Use built-in validation
missing = window.ui.validate_completeness()
if missing:
    raise ValueError(f"Missing: {missing}")
```

## Performance Optimizations

- **Rendering**: 47x faster (viewport culling, LOD, vectorization)
- **Point Queries**: 64.7x faster (spatial indexing)
- **Transforms**: 99.9% cache hit rate
- **Threading**: Background file loading

## Common Import Patterns

```python
# Services
from services import get_data_service, get_interaction_service

# Core types
from core.models import CurvePoint, PointCollection
from core.type_aliases import CurveDataList

# UI
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow
from ui.file_operations import FileOperations
```

## Known Issues

1. **PySide6 Type Stubs**: Not installed (causes expected warnings)
2. **All tests passing**: 549 tests fully functional
3. **Legacy Code**: `archive_obsolete/` contains old refactored code

## Key Design Patterns

1. **Component Container**: 85+ UI attributes organized in `ui/ui_components.py`
2. **Service Singleton**: Thread-safe service instances
3. **Protocol-based**: Type-safe interfaces without tight coupling
4. **Immutable Models**: Thread-safe CurvePoint
5. **Transform Caching**: LRU cache for coordinate transforms
6. **Spatial Indexing**: Grid-based point location

## Development Tips

1. Always activate venv: `source venv/bin/activate`
2. Use `./bpr` for type checking, never `basedpyright` directly
3. Check syntax first: `python3 -m py_compile <file>`
4. Validate before integration to prevent silent failures
5. Prefer None checks over hasattr() for type safety
6. Use `pyright: ignore[rule]` not `type: ignore` for suppressions

---
*Last Updated: January 2025*

# Important Reminders
- Do what's asked; nothing more, nothing less
- **NEVER** make assumptions
- ALWAYS prefer editing existing files
- NEVER create documentation unless explicitly requested
