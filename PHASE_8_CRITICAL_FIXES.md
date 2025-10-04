# Phase 8: Critical Issues & Fixes (Pre-Implementation)

**Date:** October 2025
**Status:** ⚠️ MUST FIX BEFORE IMPLEMENTATION
**Source:** Phase 6 parallel agent validation findings

---

## Overview

Three critical issues were identified during Phase 6 validation that MUST be fixed before beginning implementation. All three agents (python-code-reviewer, type-system-expert, performance-profiler) confirmed these issues would cause bugs if not addressed.

**Estimated fix time:** 2-3 hours
**Impact if not fixed:** Data corruption, undo/redo failures, reentrancy bugs

---

## Critical Issue #1: CurveSelection Shallow Copy Bug

### Severity: CRITICAL
**Found by:** python-code-reviewer + type-system-expert (independently)
**Affects:** Increment 1 (Add Core Types)
**Impact:** Silent data corruption in multi-curve selection operations

### Problem

The `CurveSelection` dataclass claims to be immutable via `frozen=True`, but contains mutable fields:

```python
@dataclass(frozen=True)
class CurveSelection:
    selections: dict[str, set[int]]  # MUTABLE despite frozen=True!
    active_curve: str | None = None
```

The `with_curve_selection()` method uses **shallow copy**, causing aliasing bugs:

```python
def with_curve_selection(self, curve_name: str, indices: set[int]) -> "CurveSelection":
    """Create new selection with updated curve."""
    new_selections = self.selections.copy()  # SHALLOW COPY - shares set references!
    new_selections[curve_name] = indices.copy()
    return CurveSelection(new_selections, self.active_curve)
```

### Bug Demonstration

```python
# Create selection with 2 curves
sel1 = CurveSelection({"curve1": {0, 1}, "curve2": {2, 3}})

# Create "new" selection by updating curve1
sel2 = sel1.with_curve_selection("curve1", {4, 5, 6})

# BUG: Modifying sel1 corrupts sel2 due to shared set reference!
sel1.selections["curve2"].add(99)

# Both sel1 AND sel2 now have 99 in curve2!
assert 99 in sel1.selections["curve2"]  # Expected
assert 99 in sel2.selections["curve2"]  # BUG! Should not have 99!
```

### Why It's Critical

1. **Thread safety claim is FALSE** - mutation still possible despite `frozen=True`
2. **Silent data corruption** - modifying one instance corrupts others
3. **Violates immutability contract** - documentation claims immutability

### Fix (Required for Increment 1)

**Option 1: Deep Copy (RECOMMENDED - Simplest)**

```python
def with_curve_selection(self, curve_name: str, indices: set[int]) -> "CurveSelection":
    """Create new selection with updated curve (deep copy for safety)."""
    # Deep copy all sets to prevent aliasing
    new_selections = {k: v.copy() for k, v in self.selections.items()}
    new_selections[curve_name] = indices.copy()
    return CurveSelection(new_selections, self.active_curve)
```

**Option 2: Use Immutable Types (Most Correct, More Complex)**

```python
from typing import Mapping

@dataclass(frozen=True)
class CurveSelection:
    selections: Mapping[str, frozenset[int]]  # Truly immutable
    active_curve: str | None = None

    def __init__(self, selections: dict[str, set[int]], active_curve: str | None = None):
        # Convert to immutable types
        object.__setattr__(self, 'selections', types.MappingProxyType({
            k: frozenset(v) for k, v in selections.items()
        }))
        object.__setattr__(self, 'active_curve', active_curve)

    def with_curve_selection(self, curve_name: str, indices: set[int]) -> "CurveSelection":
        # No copying needed - immutable types
        new_selections = {**self.selections, curve_name: frozenset(indices)}
        return CurveSelection(new_selections, self.active_curve)
```

**Recommendation:** Use **Option 1** (deep copy) for initial implementation. Simple, maintains API, fixes the bug. Later refactor to Option 2 if performance profiling shows benefit.

### Files to Update

1. **INTERACTIONSERVICE_MULTI_CURVE_ARCHITECTURE.md** lines 228-232
   - Update `with_curve_selection()` implementation
   - Add comment explaining deep copy necessity

2. **Increment 1 checklist** (Implementation Plan lines 916-959)
   - Add validation step to test immutability

### Test to Add (Increment 1 Validation)

```python
def test_curve_selection_immutability():
    """Verify CurveSelection is truly immutable (no aliasing)."""
    from core.models import CurveSelection

    # Create selection with 2 curves
    sel1 = CurveSelection({"curve1": {0, 1}, "curve2": {2, 3}})

    # Create new selection
    sel2 = sel1.with_curve_selection("curve1", {4, 5, 6})

    # Modify sel1 - should NOT affect sel2
    sel1.selections["curve2"].add(99)

    # Verify sel2 is unaffected
    assert 99 in sel1.selections["curve2"], "sel1 should have 99"
    assert 99 not in sel2.selections["curve2"], "sel2 should NOT have 99 (immutability violated!)"
```

---

## Critical Issue #2: Spatial Index Reentrancy Hazard

### Severity: CRITICAL
**Found by:** python-code-reviewer
**Affects:** Increment 4 (find_point_at implementation)
**Impact:** State corruption if Qt signals fire during search

### Problem

The `find_point_at()` implementation temporarily mutates `view.curve_data` to work around SpatialIndex API limitations:

```python
# From architecture doc lines 352-364
saved_data = view.curve_data
try:
    view.curve_data = curve_data  # MUTATION - creates reentrancy risk!
    transform = self._get_transform_service().create_transform_from_view_state(...)
    idx = self._point_index.find_point_at_position(view, transform, x, y, threshold=5.0)
    return PointSearchResult(index=idx, curve_name=active_curve if idx >= 0 else None)
finally:
    view.curve_data = saved_data
```

### Reentrancy Scenario

1. Main thread calls `find_point_at(mode="all_visible")`
2. Sets `view.curve_data = curve1_data` (mutation point)
3. ApplicationState emits `curves_changed` signal (Qt signal, synchronous)
4. Signal handler calls `service.on_data_changed()`
5. Handler reads `view.curve_data` → gets `curve1_data` instead of expected active curve
6. **Inconsistent state corruption**

### Why _assert_main_thread() Doesn't Help

Both the outer call and signal handler are on main thread. This is **reentrancy** (same thread, nested calls), not threading.

### Fix (Required for Increment 4)

Update `SpatialIndex.find_point_at_position()` to accept `curve_data` as parameter:

**Current Signature:**
```python
# services/spatial_index.py (or wherever SpatialIndex lives)
def find_point_at_position(
    self,
    view: CurveViewProtocol,  # Reads view.curve_data internally
    transform: CoordinateTransform,
    x: float,
    y: float,
    threshold: float = 5.0
) -> int:
    curve_data = view.curve_data  # IMPLICIT dependency
    # ... search logic
```

**New Signature:**
```python
def find_point_at_position(
    self,
    curve_data: CurveDataList,  # EXPLICIT parameter
    transform: CoordinateTransform,
    x: float,
    y: float,
    threshold: float = 5.0
) -> int:
    # ... search logic using passed curve_data
```

**Updated find_point_at() usage:**
```python
# No more mutation - pass curve_data directly!
transform = self._get_transform_service().create_transform_from_view_state(
    self._get_transform_service().create_view_state(view)
)
idx = self._point_index.find_point_at_position(
    curve_data=curve_data,  # Pass explicitly
    transform=transform,
    x=x, y=y,
    threshold=5.0
)
return PointSearchResult(index=idx, curve_name=active_curve if idx >= 0 else None)
```

### Files to Update

1. **SpatialIndex class** (find file with `class SpatialIndex`)
   - Update `find_point_at_position()` signature
   - Update all internal references to use `curve_data` parameter

2. **All SpatialIndex call sites**
   - Update to pass `curve_data` explicitly
   - Remove mutation workarounds

3. **INTERACTIONSERVICE_MULTI_CURVE_ARCHITECTURE.md** lines 346-364
   - Remove mutation hack
   - Update with clean implementation
   - Remove "NOTE: Cleaner alternative" comment (it's now the default)

4. **Increment 4 checklist** (Implementation Plan lines 1094-1196)
   - Add SpatialIndex API update as prerequisite
   - Add validation for reentrancy safety

### Test to Add (Increment 4 Validation)

```python
def test_find_point_at_reentrancy_safe():
    """Verify find_point_at doesn't corrupt state on signal reentrancy."""
    from PySide6.QtCore import QObject, pyqtSignal

    # Setup: Create view with curve_data
    view.curve_data = original_data

    # Hook into ApplicationState signal to detect reentrancy
    reentrancy_detected = False

    def on_curves_changed():
        nonlocal reentrancy_detected
        # If we're here, we're in reentrant call
        reentrancy_detected = True
        # Check view.curve_data hasn't been corrupted
        assert view.curve_data == original_data, "view.curve_data corrupted by reentrancy!"

    app_state.curves_changed.connect(on_curves_changed)

    # This might trigger signal during search
    result = service.find_point_at(view, x, y, mode="all_visible")

    # Verify state is correct regardless of reentrancy
    assert view.curve_data == original_data
```

---

## Critical Issue #3: Incomplete Command Tracking

### Severity: CRITICAL
**Found by:** python-code-reviewer
**Affects:** Increment 6 (Manipulation Methods)
**Impact:** Undo/redo fails or affects wrong curve

### Problem

Only `DeletePointsCommand` is documented for `curve_name` tracking. Other commands that manipulate points are not mentioned:

- **MovePointCommand** (used by `update_point_position`)
- **BatchMoveCommand** (used by `batch_move_points`)
- **SmoothCommand** (used by `smooth_points`)
- **SetPointStatusCommand** (potentially called from interaction service)

### Undo/Redo Bug Scenario

```python
# User is editing curve A
app_state.set_active_curve("curve_a")
service.update_point_position(view, main_window, idx=5, x=10, y=20)
# Creates MovePointCommand but WITHOUT curve_name tracking

# User switches to curve B
app_state.set_active_curve("curve_b")

# User hits Undo (Ctrl+Z)
command_manager.undo()
# Command executes on ACTIVE curve (curve_b) instead of original (curve_a)
# BUG: Wrong curve modified!
```

### Fix (Required for Increment 6)

Audit ALL commands that modify curve data and add `curve_name: str` parameter:

**Commands to Update:**

1. **MovePointCommand** (core/commands/curve_commands.py)
```python
@dataclass
class MovePointCommand:
    description: str
    point_idx: int
    old_position: tuple[float, float]
    new_position: tuple[float, float]
    curve_name: str  # ADD THIS

    def execute(self, main_window: MainWindowProtocol) -> None:
        # Use self.curve_name, NOT app_state.active_curve
        app_state = get_application_state()
        curve_data = app_state.get_curve_data(self.curve_name)
        # ... update point in self.curve_name
```

2. **BatchMoveCommand**
```python
@dataclass
class BatchMoveCommand:
    description: str
    moves: list[tuple[int, tuple[float, float], tuple[float, float]]]
    curve_name: str  # ADD THIS
```

3. **SmoothCommand**
```python
@dataclass
class SmoothCommand:
    description: str
    point_indices: list[int]
    old_positions: list[tuple[float, float]]
    curve_name: str  # ADD THIS
```

4. **SetPointStatusCommand** (if exists)
```python
@dataclass
class SetPointStatusCommand:
    description: str
    point_idx: int
    old_status: PointStatus
    new_status: PointStatus
    curve_name: str  # ADD THIS
```

5. **Any other curve manipulation commands**

### Files to Update

1. **core/commands/curve_commands.py**
   - Update ALL commands that modify curve data
   - Add `curve_name: str` parameter to dataclass
   - Update `execute()` and `undo()` to use `self.curve_name`

2. **services/interaction_service.py**
   - Update all command instantiation to pass `curve_name`
   - Example:
     ```python
     def update_point_position(self, ..., curve_name: str | None = None):
         if curve_name is None:
             curve_name = self._app_state.active_curve

         command = MovePointCommand(
             description=f"Move point {idx}",
             point_idx=idx,
             old_position=old_pos,
             new_position=new_pos,
             curve_name=curve_name  # PASS curve context
         )
         self.command_manager.execute_command(command, main_window)
     ```

3. **INTERACTIONSERVICE_MULTI_CURVE_ARCHITECTURE.md** lines 549-567
   - Update DeletePointsCommand example to show pattern
   - Add note about ALL commands requiring curve_name

4. **Increment 6 checklist** (Implementation Plan lines 1286-1354)
   - Explicitly list ALL commands requiring updates
   - Add validation step to test undo/redo with curve switching

### Commands Audit Checklist (Add to Increment 6)

```markdown
- [ ] **Find all Command classes:**
  ```bash
  grep -r "class.*Command" core/commands/
  ```

- [ ] **For each command that modifies curve data:**
  - [ ] Add `curve_name: str` parameter to dataclass
  - [ ] Update `execute()` to use `self.curve_name`
  - [ ] Update `undo()` to use `self.curve_name`
  - [ ] Update all instantiation sites to pass `curve_name`

- [ ] **Commands requiring updates:**
  - [ ] MovePointCommand
  - [ ] BatchMoveCommand
  - [ ] SmoothCommand
  - [ ] SetPointStatusCommand
  - [ ] AddPointCommand (if exists)
  - [ ] DeletePointsCommand (already documented)
  - [ ] ConvertToInterpolatedCommand (if affects curves)
  - [ ] Any others found in audit
```

### Test to Add (Increment 6 Validation)

```python
def test_undo_redo_curve_context_preserved():
    """Verify undo/redo uses original curve, not active curve."""
    from core.commands.curve_commands import MovePointCommand

    # Setup: Create two curves
    app_state.set_curve_data("curve_a", [(1, 10.0, 20.0, "normal")])
    app_state.set_curve_data("curve_b", [(1, 100.0, 200.0, "normal")])

    # Edit curve A
    app_state.set_active_curve("curve_a")
    service.update_point_position(view, main_window, idx=0, x=50, y=60)

    # Switch to curve B
    app_state.set_active_curve("curve_b")

    # Undo - should affect curve A (original), not curve B (active)
    command_manager.undo()

    # Verify: curve A reverted, curve B unchanged
    curve_a_data = app_state.get_curve_data("curve_a")
    curve_b_data = app_state.get_curve_data("curve_b")

    assert curve_a_data[0][1] == 10.0, "Curve A should be reverted"
    assert curve_a_data[0][2] == 20.0, "Curve A should be reverted"
    assert curve_b_data[0][1] == 100.0, "Curve B should be unchanged"
    assert curve_b_data[0][2] == 200.0, "Curve B should be unchanged"
```

---

## Summary of Fixes

| Issue | Severity | Fix Time | Affected Increment | Lines Changed |
|-------|----------|----------|-------------------|---------------|
| CurveSelection Shallow Copy | CRITICAL | 30 min | Increment 1 | ~10 lines |
| Spatial Index Reentrancy | CRITICAL | 60 min | Increment 4 | ~30 lines |
| Command Tracking | CRITICAL | 60-90 min | Increment 6 | ~50 lines |
| **TOTAL** | - | **2-3 hours** | - | **~90 lines** |

---

## Implementation Order

Apply fixes in this order:

1. **First: Issue #1 (CurveSelection)**
   - Easiest fix
   - Blocks Increment 1
   - Independent of other fixes

2. **Second: Issue #2 (Spatial Index)**
   - Moderate complexity
   - Blocks Increment 4
   - Independent of other fixes

3. **Third: Issue #3 (Command Tracking)**
   - Most complex (requires audit)
   - Blocks Increment 6
   - Can be done in parallel with Increments 1-5

---

## Validation Checklist

After applying all fixes:

- [ ] Issue #1: Run `test_curve_selection_immutability()` - MUST PASS
- [ ] Issue #2: Run `test_find_point_at_reentrancy_safe()` - MUST PASS
- [ ] Issue #3: Run `test_undo_redo_curve_context_preserved()` - MUST PASS
- [ ] All fixes: `./bpr --errors-only` - 0 errors
- [ ] All fixes: `uv run pytest tests/test_interaction_service.py` - All pass
- [ ] Architecture doc updated with corrections
- [ ] Implementation plan updated with revised timeline

---

## Next Steps

1. **Apply fixes** (2-3 hours)
2. **Update documentation** (30 min)
3. **Run validation** (15 min)
4. **Begin Increment 1** implementation

**Ready to proceed once these critical fixes are applied.**

---

**Document Version:** 1.0
**Date:** October 2025
**Status:** ⚠️ BLOCKING - Must fix before implementation
**Approved by:** User decision (Option A)
