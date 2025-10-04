# CurveEditor Code Style & Conventions

## Type Safety First

1. **Always use type hints** - Required for all functions and methods
2. **Avoid hasattr()** - Destroys type information, use `is not None` instead
3. **Use Protocols** - Type-safe duck-typing for interfaces
4. **Immutable models** - `@dataclass(frozen=True)` for thread safety

### Example: Bad vs Good
```python
# BAD - Type becomes Any
if hasattr(self, 'main_window') and self.main_window:
    frame = self.main_window.current_frame  # Type lost!

# GOOD - Type preserved
if self.main_window is not None:
    frame = self.main_window.current_frame  # Type safe!
```

## Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`
- **Qt overrides**: Allow `mixedCase` (N802, N815 ignored for Qt methods)

## Type Ignore Comments

Use basedpyright-specific format with rules:
```python
# BAD - Old style
data = something()  # type: ignore

# BAD - Blanket ignore
self.func(data)  # pyright: ignore

# GOOD - Specific rule
self.func(data)  # pyright: ignore[reportArgumentType]
```

Common rules: `reportArgumentType`, `reportReturnType`, `reportOptionalMemberAccess`

## Docstrings

- Use Google-style docstrings
- Required for public APIs
- Include type information in docstring (even with hints)

## Line Length

- **Maximum**: 120 characters (ruff configured)
- Break long lines logically

## Import Organization

```python
# Standard library
import sys
from pathlib import Path

# Third-party
from PySide6.QtWidgets import QWidget

# Local
from core.models import CurvePoint
from services import get_data_service
```

## Design Patterns

1. **Service Singleton**: Thread-safe service instances
2. **Protocol-based**: Type-safe interfaces without tight coupling
3. **Command Pattern**: All operations undoable
4. **Component Container**: UI organized in `ui/ui_components.py`
5. **Immutable Models**: Thread-safe `CurvePoint`
