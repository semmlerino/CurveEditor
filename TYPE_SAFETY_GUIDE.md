# Type Safety Guide for CurveEditor

## Overview

This guide documents the type safety infrastructure established during Sprint 9 and provides best practices for maintaining type safety in the CurveEditor codebase.

## Current Type Safety Status

### Overall Metrics (As of Sprint 9 Day 6)
- **Type Errors**: ~1,135 total (but mostly false positives)
- **Production Code**: ~200 errors (many are widget initialization warnings)
- **Test Code**: ~950 errors (not critical)
- **Type Coverage**: Partial (focused on critical paths)

### Well-Typed Modules (>90% clean)
```python
services/transform_service.py    # 92% test coverage, minimal type errors
core/models.py                   # 99% test coverage, fully typed
core/image_state.py             # Well-typed data structures
core/path_security.py           # Security-critical, well-typed
```

### Modules Needing Attention
```python
ui/main_window.py               # Widget initialization warnings
services/interaction_service.py # Legacy compatibility issues
test files                      # Low priority but high error count
```

## Type Infrastructure

### 1. Core Type Definitions
**Location**: `core/typing_extensions.py`

Key type aliases:
```python
# Point types
PointTuple: TypeAlias = Tuple[int, float, float]
PointType: TypeAlias = Union[PointTuple, PointTupleWithStatus]
CurveData: TypeAlias = List[PointType]

# Transform types
TransformMatrix: TypeAlias = NDArray[np.float64]
ScaleFactors: TypeAlias = Tuple[float, float]

# UI types
ColorType: TypeAlias = Union[ColorRGB, ColorRGBA, ColorHex, "QColor"]
EventResult: TypeAlias = Optional[bool]

# Service types
SelectionSet: TypeAlias = set[int]
HistoryState: TypeAlias = CurveData
```

### 2. Protocol Definitions
**Location**: `services/protocols/base_protocols.py`

Key protocols:
```python
@runtime_checkable
class CurveViewProtocol(Protocol):
    """Protocol for curve view objects."""
    @property
    def points(self) -> CurveData: ...
    @property
    def selected_points(self) -> SelectionSet: ...
    def update(self) -> None: ...

@runtime_checkable
class ServiceProtocol(Protocol):
    """Base protocol for all services."""
    def initialize(self) -> None: ...
    def shutdown(self) -> None: ...
```

### 3. Type Checking Configuration
**File**: `basedpyrightconfig.json`

```json
{
  "typeCheckingMode": "standard",
  "pythonVersion": "3.12",
  "reportUnknownMemberType": "none",  // Reduces PySide6 noise
  "reportUnknownParameterType": "none",
  "reportUnknownVariableType": "none",
  "exclude": ["archive", "test_*.py"]
}
```

## Best Practices

### 1. Handling Qt Widget Types

#### Problem: Lazy Initialization
Qt widgets are often initialized in separate methods, causing "uninitialized" warnings.

#### Solution: Type Annotations with Defaults
```python
class MainWindow(QMainWindow):
    # Declare with None default
    frame_spinbox: QSpinBox | None = None
    total_frames_label: QLabel | None = None
    
    def __init__(self):
        super().__init__()
        self._init_widgets()  # Widgets created here
    
    def _init_widgets(self):
        self.frame_spinbox = QSpinBox()
        self.total_frames_label = QLabel()
```

#### Alternative: Type Ignore Comments
```python
def use_widget(self):
    # If you know it's initialized by this point
    self.frame_spinbox.setValue(10)  # type: ignore[union-attr]
```

### 2. Service Type Patterns

#### Singleton Services
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.transform_service import TransformService

_transform_service: TransformService | None = None

def get_transform_service() -> TransformService:
    global _transform_service
    if _transform_service is None:
        from services.transform_service import TransformService
        _transform_service = TransformService()
    return _transform_service
```

#### Protocol-Based Design
```python
def process_view(view: CurveViewProtocol) -> None:
    """Accept any object that implements CurveViewProtocol."""
    points = view.points
    view.update()
```

### 3. Handling Optional Types

#### Check Before Use
```python
def process_data(data: CurveData | None) -> None:
    if data is None:
        return
    # Now type checker knows data is not None
    for point in data:
        process_point(point)
```

#### Early Return Pattern
```python
def update_widget(widget: QWidget | None) -> None:
    if not widget:
        return
    widget.update()  # Safe to use
```

### 4. Type Aliases for Complex Types

Create readable aliases for complex types:
```python
# Instead of this:
def process(data: List[Tuple[int, float, float]]) -> Dict[int, List[Tuple[float, float]]]:
    ...

# Use this:
from core.typing_extensions import CurveData, FrameMap
def process(data: CurveData) -> FrameMap:
    ...
```

## Common Type Issues and Solutions

### Issue 1: PySide6 Unknown Members
**Problem**: `reportUnknownMemberType` warnings for Qt methods

**Solution**: Configure basedpyright to suppress:
```json
"reportUnknownMemberType": "none"
```

### Issue 2: Circular Imports
**Problem**: Type hints causing circular imports

**Solution**: Use `TYPE_CHECKING` guard:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.data_service import DataService

def process(service: "DataService") -> None:
    ...
```

### Issue 3: Protocol Mismatches
**Problem**: Classes don't exactly match protocol

**Solution**: Use structural typing or adapt:
```python
class ViewAdapter:
    """Adapt any view to CurveViewProtocol."""
    def __init__(self, view: Any):
        self._view = view
    
    @property
    def points(self) -> CurveData:
        return getattr(self._view, 'points', [])
```

### Issue 4: Test Mock Types
**Problem**: Mocks don't satisfy type requirements

**Solution**: Use `Any` or create typed mocks:
```python
from unittest.mock import Mock
from typing import Any

def test_something():
    mock_view: Any = Mock()  # Use Any for test mocks
    mock_view.points = [(1, 10.0, 20.0)]
```

## Running Type Checks

### Basic Check
```bash
./bpr  # Use the wrapper script
```

### Check Specific Files
```bash
./bpr ui/main_window.py services/data_service.py
```

### Ignore Warnings, Show Only Errors
```bash
./bpr | grep "error"
```

### Count Errors by File
```bash
./bpr | grep -E "\.py:.*error" | cut -d: -f1 | sort | uniq -c | sort -rn
```

## Migration Path

### For New Code
1. Always add type hints to function signatures
2. Use type aliases from `core/typing_extensions.py`
3. Implement protocols from `services/protocols/`
4. Run `./bpr` before committing

### For Existing Code
1. Add types when modifying functions
2. Don't fix all type errors at once
3. Focus on public APIs first
4. Use `# type: ignore` pragmatically

### Priority Order
1. **High Priority**: Service interfaces, public APIs
2. **Medium Priority**: Core business logic
3. **Low Priority**: UI code (many false positives)
4. **Lowest Priority**: Test files

## Type Safety Checklist

Before committing code:
- [ ] Function signatures have type hints
- [ ] Used type aliases for complex types
- [ ] Handled None/Optional cases
- [ ] Ran `./bpr` on changed files
- [ ] Added `# type: ignore` with explanation if needed
- [ ] No circular imports from type hints

## Tools and Resources

### Installed Tools
- **basedpyright**: 1.31.1 (via `./bpr` wrapper)
- **PySide6-stubs**: 6.7.3.0 (type hints for Qt)

### Key Files
- `core/typing_extensions.py` - Type aliases
- `services/protocols/base_protocols.py` - Protocol definitions
- `basedpyrightconfig.json` - Type checker configuration
- `./bpr` - Wrapper script for basedpyright

### VS Code Integration
```json
// .vscode/settings.json
{
  "python.analysis.typeCheckingMode": "standard",
  "python.analysis.autoImportCompletions": true,
  "python.analysis.diagnosticMode": "workspace"
}
```

## Conclusion

The CurveEditor codebase has a solid type safety foundation. While not all code is fully typed, the critical paths (services, core models) have good type coverage. The main challenges are Qt widget patterns that create false positives.

Focus on maintaining type safety in new code and gradually improving existing code. Use the infrastructure in `core/typing_extensions.py` and protocols to ensure consistency.

Remember: **Pragmatism over perfection**. Some type errors are false positives from Qt patterns - use `# type: ignore` judiciously with explanatory comments.

---

*Last Updated: Sprint 9 Day 6*
*Type Checker: basedpyright 1.31.1*
*Python: 3.12*