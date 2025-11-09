# Type Safety Quick Fixes

**Priority fixes from the comprehensive audit. Total effort: 5-6 hours for Tier 1.**

## Tier 1: Critical Type Safety Issues (5-6 hours)

### 1. ApplicationState Signal Tuples (1-2 hours)

**File:** `stores/application_state.py:146`

**Current:**
```python
self._pending_signals: dict[SignalInstance, tuple[Any, ...]] = {}
```

**Fix:**
```python
from typing import TypeAlias

# Define signal argument types
SignalArgs: TypeAlias = (
    tuple[()]           # Void signals
    | tuple[int]        # frame_changed
    | tuple[str]        # Curve name signals
    | tuple[str, int]   # Curve + frame signals
)

self._pending_signals: dict[SignalInstance, SignalArgs] = {}
```

**Why:** Prevents emitting signals with wrong argument types at compile time.

---

### 2. ApplicationState Metadata Dict (2-3 hours)

**File:** `stores/application_state.py:131`

**Current:**
```python
self._curve_metadata: dict[str, dict[str, Any]] = {}

def get_curve_metadata(self, curve_name: str) -> dict[str, Any]:
    if curve_name not in self._curve_metadata:
        return {"visible": True}
    return self._curve_metadata[curve_name].copy()
```

**Fix:**
```python
from typing import TypedDict

class CurveMetadata(TypedDict, total=False):
    """Metadata for a curve trajectory."""
    visible: bool
    color: tuple[int, int, int] | None  # RGB if custom color set
    # Add other fields as discovered during audit

self._curve_metadata: dict[str, CurveMetadata] = {}

def get_curve_metadata(self, curve_name: str) -> CurveMetadata:
    """Get metadata for curve (visibility, color, etc.)."""
    if curve_name not in self._curve_metadata:
        return {"visible": True}
    return self._curve_metadata[curve_name].copy()
```

**Steps:**
1. Audit all `_curve_metadata` usage to find keys
2. Add keys to `CurveMetadata` TypedDict
3. Update all access sites to use typed dict

**Why:** Type-safe metadata access throughout application.

---

### 3. Protocol Qt Widget Types (1 hour)

**File:** `ui/protocols/controller_protocols.py:160-165`

**Current:**
```python
@runtime_checkable
class TimelineControllerProtocol(Protocol):
    btn_play_pause: Any  # QPushButton but avoiding circular imports
    fps_spinbox: Any     # QSpinBox but avoiding circular imports
    frame_slider: Any    # QSlider but avoiding circular imports
    frame_spinbox: Any   # QSpinBox but avoiding circular imports
    frame_changed: Any   # Signal(int)
    status_message: Any  # Signal(str)
```

**Fix:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QPushButton, QSlider, QSpinBox

@runtime_checkable
class TimelineControllerProtocol(Protocol):
    """Protocol for timeline controller."""

    btn_play_pause: QPushButton
    fps_spinbox: QSpinBox
    frame_slider: QSlider
    frame_spinbox: QSpinBox

    # Signals (TYPE_CHECKING handles circular imports)
    frame_changed: Signal  # Signal[int]
    status_message: Signal  # Signal[str]
```

**Why:** Type-safe controller widget access.

---

## Configuration Updates (10 minutes)

**File:** `pyproject.toml`

Add to `[tool.basedpyright]` section:

```toml
[tool.basedpyright]
# ... existing config ...

# Enable basedpyright-exclusive features for better inference
strictListInference = true
strictDictionaryInference = true
strictSetInference = true

# Reduce test noise while keeping production strict
[[tool.basedpyright.executionEnvironments]]
root = "tests"
reportMissingParameterType = "none"
reportUnannotatedClassAttribute = "none"
reportExplicitAny = "none"
```

**Impact:**
- Better collection type inference in production code
- Reduces test warnings from 400 to ~50
- Keeps production code strict

---

## Verification

After fixes, run:

```bash
# Check type safety
~/.local/bin/uv run basedpyright

# Expected results:
# - 0 errors (maintained)
# - ~50-100 warnings (down from 482)
# - All Tier 1 Any types resolved
```

---

## Optional: Tier 2 Improvements

### Test Fixture Annotations (4-6 hours)

**Pattern fixes throughout `tests/`:**

```python
# Before
class MockHelper:
    zoom_factor = 1.0
    pan_offset_x = 0

def test_something(qtbot):
    pass

# After
class MockHelper:
    zoom_factor: float = 1.0
    pan_offset_x: int = 0

from pytestqt.qtbot import QtBot

def test_something(qtbot: QtBot) -> None:
    pass
```

**Automation opportunity:**
Create script to batch-fix common patterns:
- Unannotated class attributes
- Missing pytest fixture types
- Mock return types as Any

---

## Success Criteria

After Tier 1 fixes:

✅ Zero explicit Any types in ApplicationState
✅ Zero Any types in protocol definitions
✅ Type-safe signal emissions
✅ Type-safe metadata access
✅ Type-safe controller widget access
✅ Test noise reduced by 80%

**Grade improvement: B+ (87/100) → A- (92/100)**
