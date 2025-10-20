# Layer Violations - Detailed Technical Analysis

**Date**: 2025-10-20
**Status**: All 12 violations verified and analyzed
**Recommendation**: Proceed with refactoring

---

## Violation Categories with Root Cause Analysis

### Category 1: Constant Imports (5 violations)

#### Issue
Services and rendering layer importing non-UI-specific constants from `ui.ui_constants`.

#### Violations Found

| # | File | Line | Import | Issue |
|---|------|------|--------|-------|
| 1.1 | `services/transform_service.py` | 17 | `DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH` | Transform service uses image dimensions for default viewport |
| 1.2 | `services/transform_core.py` | 27 | `DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH` | Core transformation logic needs image defaults |
| 1.3 | `services/ui_service.py` | 19 | `DEFAULT_STATUS_TIMEOUT` | UI service timeout for status messages |
| 1.4 | `core/commands/shortcut_commands.py` | 718 | `DEFAULT_NUDGE_AMOUNT` | Nudge command needs movement increment |
| 1.5 | `rendering/optimized_curve_renderer.py` | 26 | `GRID_CELL_SIZE, RENDER_PADDING` | Renderer needs grid and padding constants |

#### Root Cause
These are **domain constants**, not UI-specific styling. They belong in the service/core layer but were placed in UI layer (likely as a "common constants" location). Services and rendering need them but shouldn't depend on UI layer.

#### Impact
- **Services layer**: Depends on UI layer (circular risk)
- **Rendering layer**: Depends on UI layer (architectural violation)
- **Testability**: Harder to test services in isolation from UI

#### Solution
Extract all 5 constants to `core/defaults.py`:

```python
# core/defaults.py
DEFAULT_IMAGE_WIDTH: int = 1920
DEFAULT_IMAGE_HEIGHT: int = 1080
DEFAULT_NUDGE_AMOUNT: float = 1.0
DEFAULT_STATUS_TIMEOUT: int = 2000  # milliseconds
GRID_CELL_SIZE: int = 100
RENDER_PADDING: int = 50
```

Update imports:
- `services/transform_service.py:17` → `from core.defaults import ...`
- `services/transform_core.py:27` → `from core.defaults import ...`
- `services/ui_service.py:19` → `from core.defaults import ...`
- `core/commands/shortcut_commands.py:718` → `from core.defaults import ...`
- `rendering/optimized_curve_renderer.py:26` → `from core.defaults import ...`

#### Risk Level: **LOW**
- Simple, mechanical refactoring
- No behavior changes
- Improves architecture
- Estimated time: 30 minutes including testing

---

### Category 2: Color Imports (6 violations)

#### Issue
Rendering layer importing colors from UI layer. **5 of 6 are method-level imports** (symptomatic of circular dependency workaround).

#### Violations Found

| # | File | Line | Type | Import |
|---|------|------|------|--------|
| 2.1 | `rendering/optimized_curve_renderer.py` | 25 | Static | `from ui.color_constants import CurveColors` |
| 2.2 | `rendering/optimized_curve_renderer.py` | 892 | Runtime | `from ui.color_manager import SPECIAL_COLORS, get_status_color` |
| 2.3 | `rendering/optimized_curve_renderer.py` | 963 | Runtime | `from ui.color_manager import COLORS_DARK` |
| 2.4 | `rendering/optimized_curve_renderer.py` | 1014 | Runtime | `from ui.color_manager import get_status_color` |
| 2.5 | `rendering/optimized_curve_renderer.py` | 1209 | Runtime | `from ui.color_manager import COLORS_DARK` |
| 2.6 | `rendering/optimized_curve_renderer.py` | 1282 | Runtime | `from ui.color_manager import COLORS_DARK` |

#### Root Cause - CRITICAL FINDING

The 5 **runtime imports** (lines 892, 963, 1014, 1209, 1282) are **workarounds for circular import**:

```python
# File: rendering/optimized_curve_renderer.py
# Note at top of file:
# pyright: reportImportCycles=false

# If we tried to import at module level:
from ui.color_constants import CurveColors  # Line 25 - this works
from ui.color_manager import COLORS_DARK    # This would cause circular import!

# So instead, imports are done inside methods:
def _draw_points(self, ...):
    from ui.color_manager import SPECIAL_COLORS  # Workaround at line 892
```

**Why circular?** Likely because:
1. `ui.color_manager` depends on some UI state/components
2. UI components use `rendering/optimized_curve_renderer.py`
3. Creating circular: ui → rendering → ui

This is a **fundamental architecture problem**, not just import ordering.

#### Evidence of Problem
- **File marker**: `# pyright: reportImportCycles=false` at top of renderer
- **Method-level imports**: 5 deferred imports to break cycle
- **Incomplete fix**: Line 25 still static-imports CurveColors (can't defer this one)

#### Impact
- **Runtime overhead**: 5 import operations per render method call (performance)
- **Type checking**: Pylance/pyright can't properly analyze these imports
- **Maintainability**: Non-obvious why imports are deferred
- **Testability**: Hard to mock color functions in tests

#### Solution
Extract colors to `core/colors.py` (neutral layer, breaks circular dependency):

```python
# core/colors.py - NO dependencies on ui or rendering

from dataclasses import dataclass
from PySide6.QtGui import QColor

@dataclass(frozen=True)
class CurveColors:
    point: QColor
    selected_point: QColor
    line: QColor
    interpolated: QColor
    keyframe: QColor
    endframe: QColor
    tracked: QColor

    @classmethod
    def default(cls) -> "CurveColors":
        return cls(
            point=QColor(255, 255, 255),
            selected_point=QColor(255, 100, 100),
            line=QColor(200, 200, 200),
            interpolated=QColor(150, 150, 255),
            keyframe=QColor(255, 255, 0),
            endframe=QColor(255, 0, 0),
            tracked=QColor(0, 255, 0),
        )

COLORS_DARK = {
    "normal": QColor(200, 200, 200),
    "interpolated": QColor(100, 100, 255),
    "keyframe": QColor(255, 255, 100),
    "tracked": QColor(100, 255, 100),
    "endframe": QColor(255, 100, 100),
}

SPECIAL_COLORS = {
    "selected": QColor(255, 100, 100),
    "hover": QColor(255, 200, 100),
}

def get_status_color(status: str, selected: bool = False) -> QColor:
    if selected:
        return SPECIAL_COLORS["selected"]
    return COLORS_DARK.get(status, COLORS_DARK["normal"])
```

Then update renderer (replace lines 25, 892, 963, 1014, 1209, 1282):

```python
# At top of file - single module-level import
from core.colors import CurveColors, COLORS_DARK, SPECIAL_COLORS, get_status_color

# Remove all 5 method-level imports
```

**Why this works**:
- `core/colors.py` has no dependencies on ui or rendering
- `rendering/optimized_curve_renderer.py` imports from core/ (allowed)
- `ui/color_manager.py` can import from `core/colors.py` (no cycle)
- Cycle broken: ui ← core ← rendering (no backwards dependency)

#### Risk Level: **MEDIUM**
- Requires creating new file `core/colors.py`
- Need to verify color values are exactly preserved
- Update UI layer to import from core instead
- More complex than constants but still straightforward
- Estimated time: 45 minutes including testing

---

### Category 3: Protocol Import (1 violation)

#### Issue
`rendering/rendering_protocols.py` imports StateManager from UI layer **at runtime** inside protocol class definition.

#### Violation Details

**Current code** (lines 48-53):
```python
class MainWindowProtocol(Protocol):
    """Protocol for main window objects."""

    from ui.state_manager import StateManager  # ← Runtime import (WRONG)

    state_manager: StateManager  # Has current_frame attribute
```

#### Problem
1. **Layer violation**: Rendering protocol depends on UI class (StateManager)
2. **Runtime import**: StateManager actually imported at class definition time (unnecessary)
3. **Type checking issue**: Type checkers see the runtime import, not just the annotation

#### Root Cause
The developer likely tried to avoid circular import by making it a class-level import, but this still creates the runtime dependency. The proper solution is `TYPE_CHECKING` block.

#### Solution
Move to TYPE_CHECKING block with forward reference:

```python
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PySide6.QtGui import QImage, QPixmap
    from services.transform_service import Transform
    from ui.state_manager import StateManager  # ← Move here

class MainWindowProtocol(Protocol):
    """Protocol for main window objects."""

    state_manager: "StateManager"  # ← String annotation (forward reference)
```

**Benefits**:
- No runtime import (StateManager only imported during type checking)
- Type checkers understand the annotation
- No circular import risk at runtime
- Standard Python pattern (PEP 484)

#### Risk Level: **LOW**
- Minimal change
- Purely type-checking level
- No runtime behavior impact
- Estimated time: 5 minutes

---

## Severity Ranking

### Critical (Fix Immediately)
**Color imports (6 violations)** - HIGHEST PRIORITY
- Cause: Unresolved circular dependency
- Evidence: 5 method-level imports as workarounds
- Impact: Architecture problem, not just code smell
- Effort: Medium (45 min)
- Fix: Task 1.4 in refactoring plan

### High (Should Fix)
**Constants in rendering (1 of 5)** - Rendering specifically
- `rendering/optimized_curve_renderer.py:26`
- Used for grid and rendering UI, not image transforms
- Could use different values than transforms
- Still lower priority than colors

### Medium (Fix in Refactoring)
**Constants in services (4 of 5)** - Services layer
- Image dimensions and timeouts
- Lower architectural impact than rendering
- Can be fixed with other constants
- Effort: Low (30 min)

**Protocol import (1 violation)** - Type checking only
- Only affects type checking, not runtime
- Already partially isolated (not module-level)
- Effort: Minimal (5 min)

---

## Execution Order Analysis

### Recommended Order: **Task 1.4 THEN Task 1.2**

Why?
1. **Task 1.4 (colors) must go first** - creates core/colors.py
2. **Then Task 1.2 (constants)** - creates core/defaults.py
3. Both extract from ui/ to core/, but colors has more dependencies
4. Protocol fix is part of Task 1.4

### Why Not Reverse Order?
- Task 1.2 creates core/defaults.py (uses only constants)
- Task 1.4 creates core/colors.py (uses constants AND Qt classes)
- If we do 1.2 first, 1.4 might pull constants back to ui/ if not careful
- Doing colors first ensures clear separation

---

## Verification Checklist

- [x] All 5 constant violations found and documented
- [x] All 6 color violations found and documented
- [x] Color violations analyzed as circular import workarounds
- [x] Protocol violation found and analyzed
- [x] Root causes identified for each category
- [x] No additional violations found
- [x] Proposed solutions architecturally sound
- [x] Execution order validated
- [x] Risk levels assessed
- [x] Effort estimates provided

---

## Conclusion

**Status**: VERIFIED AND READY FOR EXECUTION

All 12 violations are:
1. Real (not false positives)
2. Architecturally problematic (not just style)
3. Properly understood (root causes identified)
4. Solvable (good solutions proposed)
5. Ordered correctly (dependencies understood)

The refactoring plan is sound and should proceed as designed.

**Next Step**: Execute Task 1.4 (colors) first, then Task 1.2 (constants).
