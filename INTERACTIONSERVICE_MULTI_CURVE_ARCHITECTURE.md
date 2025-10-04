# InteractionService Multi-Curve Architecture Design

**Date:** October 2025
**Status:** Design Complete - Ready for Implementation
**Target:** Eliminate 25 duplicated methods, fix 3 critical bugs, enable native multi-curve support

---

## Executive Summary

This document specifies the architecture for refactoring InteractionService to natively support multi-curve interactions, eliminating duplication between InteractionService (single-curve) and CurveViewWidget (multi-curve implementations).

**Key Outcomes:**
- **275 lines removed** (16.5% reduction)
- **25 duplicate methods eliminated** (single source of truth)
- **3 critical bugs fixed** (Y-flip, thread safety, protocol split)
- **0 type errors maintained** (type-safe throughout)
- **56 passing tests preserved** (~40-45 require updates, 70-80% of test suite)

---

## Current Problem Analysis

### 1. Code Duplication (25 Methods)

**InteractionService** (single-curve assumptions):
```python
def find_point_at(view, x, y) -> int:
    """ASSUMES active curve only."""
    active_curve_data = self._app_state.get_curve_data()  # No curve name!
    # ... searches active curve only
```

**CurveViewWidget** (multi-curve implementation):
```python
def _find_point_at_multi_curve(pos) -> tuple[int, str | None]:
    """Duplicates InteractionService logic with multi-curve support."""
    all_curve_names = self._app_state.get_all_curve_names()
    for curve_name, curve_data in curves_to_search:
        # ... duplicate spatial indexing logic
```

**Impact:**
- Bug fixes require updates in 2 places
- Maintenance burden (2 implementations to sync)
- Test coverage divided (56 tests split across both)

### 2. Three Critical Bugs

#### Bug #1: Y-Flip Direction Inversion (HIGH)
**Location:** `InteractionService._handle_mouse_move_consolidated` line 227

```python
# WRONG: Hardcoded Y inversion
curve_delta_y = -delta_y / transform.scale  # Always inverts!
```

**Problem:** When `flip_y_axis=False` (tracking data), double-inversion causes incorrect drag direction.

**Impact:** User drags up, point moves down (or vice versa).

#### Bug #2: Thread Safety Violation (HIGH)
**Location:** `InteractionService._point_index` access (lines 78, 681, 1021)

**Problem:** No synchronization protecting spatial index access.

**Current Design Issue:** Mixing thread-safety assumptions:
- ApplicationState: Main thread only (_assert_main_thread)
- InteractionService: No thread assertions (implicit assumption)

**Impact:** Potential race conditions if accessed from background threads.

#### Bug #3: Protocol Split (HIGH)
**Location:** Duplicate CurveViewProtocol definitions

- `services/service_protocols.py` (lines 82-199): 117 lines
- `protocols/ui.py` (lines 119-256): 137 lines

**Problem:** ~90% overlap, diverging over time, maintenance burden.

**Impact:** Type confusion, partial compatibility, duplicate maintenance.

### 3. ApplicationState Already Multi-Curve Native

```python
class ApplicationState:
    _curves_data: dict[str, CurveDataList]  # ✅ Multi-curve native
    _selection: dict[str, set[int]]         # ✅ Per-curve selection
    _active_curve: str | None                # ✅ Active curve tracking
```

**Implication:** InteractionService should match this design, not fight against it.

---

## Proposed Architecture

### Design Principles

1. **Multi-curve native by default** - Match ApplicationState's dict[str, CurveDataList] model
2. **Backward compatible** - Existing single-curve code continues working
3. **Type-safe** - 0 type errors, leverage dataclasses and protocols
4. **Single source of truth** - InteractionService is authoritative, widgets delegate
5. **Main thread only** - Follow ApplicationState's threading model

### Core Data Structures

#### 1. PointSearchResult (Replaces int return type)

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class PointSearchResult:
    """
    Result of searching for a point in curve view.

    Replaces bare int return type with structured result that includes
    curve context for multi-curve operations.
    """
    index: int  # Point index in curve, -1 if not found
    curve_name: str | None  # Curve containing point, None if not found
    distance: float = 0.0  # Distance to point (for debugging/logging)

    @property
    def found(self) -> bool:
        """True if point was found."""
        return self.index >= 0

    def to_tuple(self) -> tuple[int, str | None]:
        """Convert to tuple for backward compatibility."""
        return (self.index, self.curve_name)

    # Comparison operators for backward compatibility with int comparisons
    def __eq__(self, other: object) -> bool:
        """Allow comparison with int (compares index)."""
        if isinstance(other, int):
            return self.index == other
        if isinstance(other, PointSearchResult):
            return self.index == other.index and self.curve_name == other.curve_name
        return False

    def __lt__(self, other: int) -> bool:
        """Allow comparison with int (compares index)."""
        return self.index < other

    def __le__(self, other: int) -> bool:
        """Allow comparison with int (compares index)."""
        return self.index <= other

    def __gt__(self, other: int) -> bool:
        """Allow comparison with int (compares index)."""
        return self.index > other

    def __ge__(self, other: int) -> bool:
        """Allow comparison with int (compares index)."""
        return self.index >= other

    def __bool__(self) -> bool:
        """Allow truthiness check (True if found)."""
        return self.found

# Example usage:
result = service.find_point_at(view, x, y, mode="all_visible")
if result.found:
    print(f"Point {result.index} in curve {result.curve_name}")

# Backward compatibility patterns:
idx = service.find_point_at(view, x, y).index  # Access via .index property
if service.find_point_at(view, x, y) >= 0:     # Direct comparison (uses __ge__)
if service.find_point_at(view, x, y):          # Truthiness check (uses __bool__)
```

**Benefits:**
- **Type-safe**: basedpyright understands frozen dataclasses
- **Self-documenting**: Clear what each field means
- **Extensible**: Can add fields (e.g., `distance`) without breaking API
- **Discoverable**: `.found` property clearer than `idx != -1`

#### 2. SearchMode (Explicit search behavior)

```python
from typing import Literal

SearchMode = Literal["active", "all_visible"]

# Usage:
result = service.find_point_at(view, x, y, mode="active")       # Single-curve
result = service.find_point_at(view, x, y, mode="all_visible")  # Multi-curve
```

**Alternative Considered:** Boolean flag `search_all_curves=False`
**Rejected:** Less extensible (what about "selected_curves" mode in future?)

#### 3. CurveSelection (Multi-curve selection state)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CurveSelection:
    """
    Multi-curve selection state.

    Mirrors ApplicationState's _selection structure for type-safe access.
    Immutable for safety - create new instance to modify.
    """
    selections: dict[str, set[int]]  # curve_name -> selected indices
    active_curve: str | None = None  # Currently active curve

    @property
    def total_selected(self) -> int:
        """Total number of selected points across all curves."""
        return sum(len(s) for s in self.selections.values())

    @property
    def active_selection(self) -> set[int]:
        """Get selection for active curve only (backward compat)."""
        if self.active_curve is None:
            return set()
        return self.selections.get(self.active_curve, set()).copy()

    def get_selected_curves(self) -> list[str]:
        """Get list of curves that have selections."""
        return [name for name, sel in self.selections.items() if sel]

    def with_curve_selection(self, curve_name: str, indices: set[int]) -> "CurveSelection":
        """Create new selection with updated curve (deep copy for safety)."""
        # Deep copy all sets to prevent aliasing (frozen=True only prevents field reassignment)
        new_selections = {k: v.copy() for k, v in self.selections.items()}
        new_selections[curve_name] = indices.copy()
        return CurveSelection(new_selections, self.active_curve)

# Usage in commands:
def execute(self, main_window: MainWindowProtocol) -> None:
    selection = self._get_current_selection()  # Returns CurveSelection
    for curve_name in selection.get_selected_curves():
        indices = selection.selections[curve_name]
        # Process each curve's selection
```

**Benefits:**
- **Immutable**: Thread-safe, no accidental mutations
- **Type-safe**: Clear structure vs dict[str, set[int]]
- **Backward compatible**: `.active_selection` provides old single-curve interface
- **Extensible**: Can add metadata (colors, visibility) later

### Protocol Consolidation

**Problem:** Two duplicate CurveViewProtocol definitions

**Solution:** Single authoritative protocol in `protocols/ui.py`

```python
# protocols/ui.py (AUTHORITATIVE)
class CurveViewProtocol(Protocol):
    """
    Protocol for curve view widgets.

    AUTHORITATIVE DEFINITION - Do not duplicate!
    services/service_protocols.py re-exports this.
    """
    # Core attributes
    selected_point_idx: int
    curve_data: CurveDataList
    selected_points: set[int]

    # Multi-curve attributes (ADDED for native support)
    active_curve_name: str | None
    curves_data: dict[str, CurveDataList]

    # Transform attributes
    offset_x: float
    offset_y: float
    pan_offset_x: float
    pan_offset_y: float
    zoom_factor: float
    flip_y_axis: bool  # CRITICAL for Y-flip bug fix

    # ... (rest of protocol)
```

```python
# services/service_protocols.py (RE-EXPORT)
from protocols.ui import CurveViewProtocol  # noqa: F401
# Remove duplicate definition (lines 82-199)
```

**Migration Steps:**
1. Add missing attributes to `protocols/ui.py` CurveViewProtocol
2. Update `service_protocols.py` to re-export (like MainWindowProtocol)
3. Verify CurveViewWidget conforms to unified protocol
4. Remove duplicate definition

### Unified Method Signatures

#### Selection Methods (6 methods)

**1. find_point_at** - Core search with multi-curve support

```python
def find_point_at(
    self,
    view: CurveViewProtocol,
    x: float,
    y: float,
    mode: SearchMode = "active"
) -> PointSearchResult:
    """
    Find point at screen coordinates with spatial indexing (64.7x speedup).

    Args:
        view: Curve view to search in
        x, y: Screen coordinates in pixels
        mode: Search behavior:
            - "active": Search active curve only (default, backward compatible)
            - "all_visible": Search all visible curves

    Returns:
        PointSearchResult with index and curve name

    Examples:
        # Single-curve (backward compatible):
        result = service.find_point_at(view, 100, 200)
        if result.found:
            print(f"Point {result.index}")

        # Multi-curve:
        result = service.find_point_at(view, 100, 200, mode="all_visible")
        if result.found:
            print(f"Point {result.index} in {result.curve_name}")
    """
    self._assert_main_thread()

    if mode == "active":
        # Single-curve mode (backward compatible)
        active_curve = self._app_state.active_curve
        if active_curve is None:
            return PointSearchResult(index=-1, curve_name=None)

        # Use spatial index for O(1) lookup
        curve_data = self._app_state.get_curve_data(active_curve)
        if not curve_data:
            return PointSearchResult(index=-1, curve_name=None)

        # UPDATED: SpatialIndex API accepts curve_data parameter (no mutation needed)
        transform = self._get_transform_service().create_transform_from_view_state(
            self._get_transform_service().create_view_state(view)
        )
        idx = self._point_index.find_point_at_position(
            curve_data=curve_data,  # Pass explicitly
            transform=transform,
            x=x, y=y,
            threshold=5.0
        )
        return PointSearchResult(
            index=idx,
            curve_name=active_curve if idx >= 0 else None
        )

    elif mode == "all_visible":
        # Multi-curve mode - search all visible curves
        all_curve_names = self._app_state.get_all_curve_names()
        visible_curves = [
            name for name in all_curve_names
            if self._app_state.get_curve_metadata(name).get("visible", True)
        ]

        best_match: PointSearchResult | None = None
        threshold = 5.0

        for curve_name in visible_curves:
            curve_data = self._app_state.get_curve_data(curve_name)
            if not curve_data:
                continue

            # Search this curve with clean API (no mutation)
            transform = self._get_transform_service().create_transform_from_view_state(
                self._get_transform_service().create_view_state(view)
            )
            idx = self._point_index.find_point_at_position(
                curve_data=curve_data,  # Pass explicitly
                transform=transform,
                x=x, y=y,
                threshold=threshold
            )

            if idx >= 0:
                # Calculate distance to find best match
                point = curve_data[idx]
                data_x, data_y = float(point[1]), float(point[2])
                screen_point = self._data_to_screen(view, data_x, data_y)
                distance = ((screen_point.x() - x) ** 2 + (screen_point.y() - y) ** 2) ** 0.5

                if best_match is None or distance < best_match.distance:
                    best_match = PointSearchResult(idx, curve_name, distance)

        return best_match or PointSearchResult(index=-1, curve_name=None)

    else:
        raise ValueError(f"Invalid search mode: {mode}")
```

**2-6. Other selection methods** - Add curve_name parameter

```python
def select_point_by_index(
    self,
    view: CurveViewProtocol,
    main_window: MainWindowProtocol,
    idx: int,
    add_to_selection: bool = False,
    curve_name: str | None = None  # NEW: None = active curve
) -> bool:
    """Select point by index in specified curve."""
    self._assert_main_thread()
    if curve_name is None:
        curve_name = self._app_state.active_curve
    if curve_name is None:
        return False

    curve_data = self._app_state.get_curve_data(curve_name)
    if 0 <= idx < len(curve_data):
        if add_to_selection:
            self._app_state.add_to_selection(curve_name, idx)
        else:
            self._app_state.set_selection(curve_name, {idx})
        return True
    return False

def clear_selection(
    self,
    view: CurveViewProtocol,
    main_window: MainWindowProtocol,
    curve_name: str | None = None  # NEW: None = all curves
) -> None:
    """Clear selection for curve(s)."""
    self._assert_main_thread()
    self._app_state.clear_selection(curve_name)

def select_all_points(
    self,
    view: CurveViewProtocol,
    main_window: MainWindowProtocol,
    curve_name: str | None = None  # NEW: None = active curve
) -> int:
    """Select all points in curve."""
    self._assert_main_thread()
    if curve_name is None:
        curve_name = self._app_state.active_curve
    if curve_name is None:
        return 0

    curve_data = self._app_state.get_curve_data(curve_name)
    if curve_data:
        all_indices = set(range(len(curve_data)))
        self._app_state.set_selection(curve_name, all_indices)
        return len(all_indices)
    return 0

def select_points_in_rect(
    self,
    view: CurveViewProtocol,
    main_window: MainWindowProtocol,
    rect: QRect,
    curve_name: str | None = None  # NEW: None = active curve
) -> int:
    """Select points in rectangle using spatial indexing."""
    self._assert_main_thread()
    if curve_name is None:
        curve_name = self._app_state.active_curve
    if curve_name is None:
        return 0

    curve_data = self._app_state.get_curve_data(curve_name)
    if not curve_data:
        return 0

    transform = self._get_transform_service().create_transform_from_view_state(
        self._get_transform_service().create_view_state(view)
    )

    # Use spatial index for O(1) rectangular selection
    point_indices = self._point_index.get_points_in_rect(
        view, transform, rect.left(), rect.top(), rect.right(), rect.bottom()
    )

    selected = set(point_indices)
    self._app_state.set_selection(curve_name, selected)
    return len(selected)
```

#### Manipulation Methods (5 methods)

```python
def update_point_position(
    self,
    view: CurveViewProtocol,
    main_window: MainWindowProtocol,
    idx: int,
    x: float,
    y: float,
    curve_name: str | None = None  # NEW
) -> bool:
    """Update point position in curve."""
    self._assert_main_thread()
    if curve_name is None:
        curve_name = self._app_state.active_curve
    if curve_name is None:
        return False

    curve_data = self._app_state.get_curve_data(curve_name)
    if 0 <= idx < len(curve_data):
        point = curve_data[idx]
        # Update via ApplicationState (signals emitted automatically)
        from core.models import CurvePoint
        updated_point = CurvePoint(
            frame=point[0],
            x=x,
            y=y,
            status=point[3] if len(point) >= 4 else "normal"
        )
        self._app_state.update_point(curve_name, idx, updated_point)
        return True
    return False

def delete_selected_points(
    self,
    view: CurveViewProtocol,
    main_window: MainWindowProtocol,
    curve_name: str | None = None  # NEW
) -> None:
    """Delete selected points using DeletePointsCommand."""
    self._assert_main_thread()
    if curve_name is None:
        curve_name = self._app_state.active_curve
    if curve_name is None:
        return

    selected = self._app_state.get_selection(curve_name)
    curve_data = self._app_state.get_curve_data(curve_name)

    if selected and curve_data:
        from core.commands.curve_commands import DeletePointsCommand

        indices = list(selected)
        deleted_points = [
            (idx, curve_data[idx])
            for idx in sorted(indices)
            if 0 <= idx < len(curve_data)
        ]

        if deleted_points:
            command = DeletePointsCommand(
                description=f"Delete {len(deleted_points)} point{'s' if len(deleted_points) > 1 else ''}",
                indices=indices,
                deleted_points=deleted_points,
                curve_name=curve_name  # NEW: Track which curve
            )
            self.command_manager.execute_command(command, main_window)
            self._app_state.clear_selection(curve_name)

# Similar for nudge_selected_points, batch_move_points, smooth_points
```

#### Mouse Event Handlers (5 methods) - Auto-detect multi-curve

**Key Design Decision:** No signature changes. Handlers automatically detect if view has multiple curves and use appropriate search mode.

```python
def _handle_mouse_press_consolidated(
    self,
    view: CurveViewProtocol,
    event: QMouseEvent
) -> None:
    """
    Handle mouse press with automatic multi-curve detection.

    NO SIGNATURE CHANGE - auto-detects single vs multi-curve mode.
    """
    from PySide6.QtCore import Qt

    pos_f = event.position()
    pos = pos_f if isinstance(pos_f, QPoint) else pos_f.toPoint()

    # AUTO-DETECT: Use multi-curve search if multiple curves exist
    all_curves = self._app_state.get_all_curve_names()
    search_mode: SearchMode = "all_visible" if len(all_curves) > 1 else "active"

    # Find point using unified method
    result = self.find_point_at(view, pos.x(), pos.y(), mode=search_mode)

    if result.found:
        # AUTO-SWITCH: If point from different curve, make it active
        if result.curve_name != self._app_state.active_curve:
            logger.info(f"Switching active curve: {self._app_state.active_curve} → {result.curve_name}")
            self._app_state.set_active_curve(result.curve_name)
            # Update view's active curve reference
            if hasattr(view, 'set_active_curve'):
                view.set_active_curve(result.curve_name)

        # Select point (rest of logic unchanged)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Toggle in selection
            current = self._app_state.get_selection(result.curve_name)
            if result.index in current:
                self._app_state.remove_from_selection(result.curve_name, result.index)
            else:
                self._app_state.add_to_selection(result.curve_name, result.index)
        else:
            # Replace selection
            self._app_state.set_selection(result.curve_name, {result.index})

        # Start drag (existing logic)
        view.drag_active = True
        view.last_drag_pos = pos
        self.drag_point_idx = result.index
        # ... rest of drag setup

    # ... rest of method unchanged
```

**Benefits:**
- Zero breaking changes to signature
- Automatic multi-curve support
- Intelligent curve switching
- Maintains backward compatibility

### Bug Fixes

#### Bug Fix #1: Y-Flip Direction

**Problem:** Hardcoded Y inversion breaks flip_y_axis=False mode

```python
# BEFORE (line 227):
curve_delta_y = -delta_y / transform.scale  # Always inverts!

# AFTER:
y_multiplier = -1.0 if view.flip_y_axis else 1.0
curve_delta_y = (delta_y * y_multiplier) / transform.scale
```

**Application:** Update all 3 locations:
1. `_handle_mouse_move_consolidated` (line 227)
2. `_handle_key_event_consolidated` (line 439)
3. Any other Y-coordinate transformations

**Testing:**
```python
def test_y_flip_drag_direction():
    # Test flip_y_axis=True (default - inverted)
    view.flip_y_axis = True
    service.handle_mouse_move(view, drag_down_event)
    assert point.y < original_y  # Drag down = Y decreases

    # Test flip_y_axis=False (tracking - normal)
    view.flip_y_axis = False
    service.handle_mouse_move(view, drag_down_event)
    assert point.y > original_y  # Drag down = Y increases
```

#### Bug Fix #2: Thread Safety

**Problem:** No thread assertions, inconsistent with ApplicationState

**Solution:** Add `_assert_main_thread()` to all public methods

```python
class InteractionService:
    """
    Main-thread-only service (matches ApplicationState pattern).

    Thread Safety Contract:
    - ALL methods must be called from main Qt thread
    - Worker threads should emit signals, handlers update state
    - _assert_main_thread() enforces this at runtime
    """

    def _assert_main_thread(self) -> None:
        """Verify we're on the main thread."""
        from PySide6.QtCore import QCoreApplication, QThread

        app = QCoreApplication.instance()
        if app is not None:
            current_thread = QThread.currentThread()
            main_thread = app.thread()
            assert current_thread == main_thread, (
                f"InteractionService must be accessed from main thread only. "
                f"Current: {current_thread}, Main: {main_thread}"
            )

    # Add to ALL public methods:
    def find_point_at(self, ...) -> PointSearchResult:
        self._assert_main_thread()  # First line
        # ... rest of method

    def handle_mouse_press(self, ...) -> None:
        self._assert_main_thread()  # First line
        # ... rest of method
```

**Benefits:**
- Catches threading bugs early (assertion failure vs silent corruption)
- Matches ApplicationState pattern (consistency)
- Simpler than mutexes (no lock contention)
- Faster (no synchronization overhead)
- Aligns with Qt threading model

#### Bug Fix #3: Protocol Split

**Solution:** Already covered in Protocol Consolidation section above.

**Summary:**
1. Enhance `protocols/ui.py` CurveViewProtocol with missing attributes
2. Update `services/service_protocols.py` to re-export
3. Remove duplicate definition (117 lines)

---

## Prototyping Phase (REQUIRED Before Implementation)

**Purpose:** Validate architecture is implementable before committing to full refactor

**Scope:** Implement 8-10 methods (40% coverage) across all 6 categories to validate design

### Methods to Prototype

| Category | Method | Why Critical |
|----------|--------|--------------|
| Selection | find_point_at() | Core method, tests PointSearchResult API |
| Selection | select_point_by_index() | Tests curve_name parameter pattern |
| Manipulation | update_point_position() | Tests ApplicationState integration |
| Manipulation | nudge_selected_points() | Tests command creation with curve context |
| Mouse Events | handle_mouse_press() | Tests multi-curve event routing |
| Mouse Events | handle_mouse_move() | Tests Y-flip bug fix, pan logic |
| State Callbacks | on_data_changed() | Tests signal handling |
| History | add_to_history() | Tests state serialization |
| View | apply_pan_offset_y() | Tests Y-flip awareness |
| **Bonus** | handle_wheel_event() | Tests zoom with multi-curve |

### Success Criteria

Prototypes succeed if:
1. **Code compiles** with 0 type errors (basedpyright)
2. **Tests pass** for prototyped methods
3. **PointSearchResult** backward compatibility confirmed (comparison operators work)
4. **Spatial index** approach validated (mutation vs parameter approach chosen)
5. **Y-flip fix** validated (manual test shows correct drag direction)
6. **No architecture blockers** discovered

### Decision Gate

- ✅ **PASS**: All criteria met → Proceed to Migration Strategy implementation
- ⚠️ **ISSUES FOUND**: Address issues, update architecture, re-prototype
- ❌ **FUNDAMENTAL FLAW**: Loop back to Phase 3A redesign

### Prototype Deliverables

1. Working implementation of 8-10 methods
2. Updated tests for prototyped methods (8-10 test files)
3. Manual validation of Y-flip fix
4. Decision on spatial index approach (mutation vs parameter)
5. Architecture revision document (if issues found)

**Estimated Time:** 1-2 days

---

## Migration Strategy

### Phase 1: Foundation (Non-Breaking)

**Goal:** Add infrastructure without changing behavior

**Tasks:**
1. Add new data structures:
   - `PointSearchResult` dataclass
   - `CurveSelection` dataclass
   - `SearchMode` type alias
2. Consolidate protocols:
   - Enhance `protocols/ui.py` CurveViewProtocol
   - Update `service_protocols.py` to re-export
   - Add `active_curve_name`, `curves_data`, `flip_y_axis` to protocol
3. Add `_assert_main_thread()` method to InteractionService

**Risk:** LOW
**Tests Affected:** 0
**Lines Changed:** +120 lines (new code only)

**Validation:**
- `uv run basedpyright` - 0 errors
- `uv run pytest tests/test_interaction_service.py` - All pass (no behavior change)

### Phase 2: Extend Methods (Backward Compatible)

**Goal:** Add multi-curve parameters with defaults

**Tasks:**
1. Update `find_point_at()`:
   - Change return type: `int` → `PointSearchResult`
   - Add `mode: SearchMode = "active"` parameter
   - Implement multi-curve search logic
2. Update selection methods (6 total):
   - Add `curve_name: str | None = None` parameter
   - Default to active curve (backward compatible)
3. Update manipulation methods (5 total):
   - Add `curve_name: str | None = None` parameter
4. Add thread assertions to all public methods

**Risk:** MEDIUM
**Tests Affected:** 0 (defaults maintain behavior)
**Lines Changed:** ~200 lines (method extensions)

**Validation:**
- All existing tests pass (using defaults)
- New tests verify multi-curve behavior
- Type checker confirms PointSearchResult compatibility

### Phase 3: Update CurveViewWidget (Breaking)

**Goal:** Remove duplication, delegate to InteractionService

**Tasks:**
1. Replace `_find_point_at_multi_curve()` with `service.find_point_at(..., mode="all_visible")`
2. Remove duplicate mouse event logic (lines 938-1068)
3. Delegate to `service.handle_mouse_press()` etc.
4. Remove 25 duplicate methods from CurveViewWidget

**Risk:** HIGH
**Tests Affected:** ~20 CurveViewWidget tests
**Lines Changed:** -450 lines (removal), +50 lines (delegation)

**Test Updates Required:**
```python
# BEFORE:
idx, curve_name = widget._find_point_at_multi_curve(pos)

# AFTER:
result = widget.interaction_service.find_point_at(widget, pos.x(), pos.y(), mode="all_visible")
idx, curve_name = result.index, result.curve_name
```

**Validation:**
- Update 20 tests to use new API
- Verify multi-curve selection still works
- Check command execution with curve context

### Phase 4: Fix Bugs (Breaking)

**Goal:** Correct Y-flip behavior, verify thread safety

**Tasks:**
1. Fix Y-flip bug:
   - Replace hardcoded `-delta_y` with `delta_y * y_multiplier`
   - Use `view.flip_y_axis` to determine multiplier
2. Verify thread assertions work:
   - Add test that calls from worker thread
   - Confirm AssertionError raised
3. Update tests with corrected coordinates

**Risk:** MEDIUM
**Tests Affected:** ~10 coordinate tests
**Lines Changed:** ~30 lines (bug fixes)

**Test Updates Required:**
```python
# Tests using flip_y_axis=False need Y-coordinate updates
def test_drag_point_tracking_mode():
    view.flip_y_axis = False  # Tracking data
    service.handle_mouse_move(view, drag_down_event)
    # OLD: assert point.y < original_y (wrong!)
    # NEW: assert point.y > original_y (correct)
```

**Validation:**
- Manual testing with tracking data (verify drag direction)
- Update 10 tests with corrected expectations
- All 56 tests pass

### Phase 5: Cleanup & Documentation

**Tasks:**
1. Remove dead code paths
2. Update docstrings with multi-curve examples
3. Add migration guide for external code
4. Performance validation

**Risk:** LOW
**Tests Affected:** 0
**Lines Changed:** +100 (docs), -50 (cleanup)

---

## Incremental Implementation Plan (Phase 3B)

**Purpose:** Step-by-step execution guide with granular checkpoints for safe, incremental migration

**Principles:**
- ✅ **Tests pass at every step** (never break main branch)
- ✅ **Type errors = 0 at every step** (maintain type safety)
- ✅ **Each increment is independently testable** (clear validation)
- ✅ **Simple rollback** (git checkout specific files)
- ✅ **Visible progress** (checklist format)

**Timeline:** 1-2 weeks (10-12 increments × 1-2 hours each)

---

### Increment 1: Add Core Types (Non-Breaking)

**Goal:** Add new dataclasses and type aliases without changing any behavior

**Duration:** 30-45 minutes

#### Prerequisites
- [ ] Phase 1 complete (duplication verified, tests at 80%)
- [ ] Architecture approved
- [ ] On clean git branch (e.g., `phase8/increment-1-core-types`)

#### Changes

**File: `core/models.py`**
- [ ] Add import: `from typing import Literal`
- [ ] Add PointSearchResult dataclass after CurvePoint definition (lines ~110-173 from architecture doc)
- [ ] Add CurveSelection dataclass after PointSearchResult (lines ~199-240 from architecture doc)

**File: `core/type_aliases.py`**
- [ ] Add `SearchMode = Literal["active", "all_visible"]`
- [ ] Add docstring explaining search modes

#### Validation
```bash
# Type checking
./bpr core/models.py core/type_aliases.py  # Expect: 0 errors

# Syntax check
python3 -m py_compile core/models.py core/type_aliases.py

# Run existing tests (should all pass - no behavior change)
uv run pytest tests/test_interaction_service.py -xvs  # Expect: all pass
```

#### Rollback
```bash
git checkout core/models.py core/type_aliases.py
```

#### Success Criteria
- ✅ 0 type errors
- ✅ All existing tests pass (no behavior changed)
- ✅ New types importable: `from core.models import PointSearchResult, CurveSelection`
- ✅ SearchMode type alias usable: `mode: SearchMode = "active"`

---

### Increment 2: Consolidate CurveViewProtocol (Non-Breaking)

**Goal:** Single authoritative protocol definition, eliminate 117-line duplication

**Duration:** 45-60 minutes

#### Prerequisites
- [ ] Increment 1 complete

#### Changes

**File: `protocols/ui.py`** (Enhance CurveViewProtocol)
- [ ] Add to CurveViewProtocol (around line 200):
  ```python
  # Multi-curve attributes (for native multi-curve support)
  active_curve_name: str | None
  curves_data: dict[str, CurveDataList]

  # Coordinate system (CRITICAL for Y-flip bug fix)
  flip_y_axis: bool
  ```

**File: `services/service_protocols.py`**
- [ ] BEFORE removing duplicate, verify both protocols have same attributes
- [ ] Add import at top: `from protocols.ui import CurveViewProtocol  # noqa: F401`
- [ ] Add comment: `# Re-export from protocols.ui - DO NOT duplicate definition here`
- [ ] Remove duplicate CurveViewProtocol definition (lines 82-199)
- [ ] Verify no other code in this file references the old definition

**File: `ui/curve_view_widget.py`**
- [ ] Verify CurveViewWidget has all required attributes:
  - [ ] `active_curve_name: str | None` exists
  - [ ] `curves_data: dict[str, CurveDataList]` exists
  - [ ] `flip_y_axis: bool` exists
- [ ] If missing, add with appropriate defaults

#### Validation
```bash
# Type checking - CurveViewWidget should still conform
./bpr protocols/ui.py services/service_protocols.py ui/curve_view_widget.py

# Run tests that use CurveViewProtocol
uv run pytest tests/test_interaction_service.py tests/test_curve_view.py -xvs
```

#### Rollback
```bash
git checkout protocols/ui.py services/service_protocols.py ui/curve_view_widget.py
```

#### Success Criteria
- ✅ 0 type errors
- ✅ Single CurveViewProtocol definition (protocols/ui.py)
- ✅ service_protocols.py re-exports (no duplicate)
- ✅ CurveViewWidget conforms to unified protocol
- ✅ All tests pass

---

### Increment 3: Add Thread Safety Infrastructure (Non-Breaking)

**Goal:** Add `_assert_main_thread()` helper method to InteractionService

**Duration:** 30 minutes

#### Prerequisites
- [ ] Increment 2 complete

#### Changes

**File: `services/interaction_service.py`**
- [ ] Add method after `__init__`:
  ```python
  def _assert_main_thread(self) -> None:
      """
      Verify we're on the main Qt thread.

      Thread Safety Contract:
      - ALL InteractionService methods must be called from main thread
      - Worker threads should emit signals, handlers update state
      - Matches ApplicationState threading pattern

      Raises:
          AssertionError: If called from non-main thread
      """
      from PySide6.QtCore import QCoreApplication, QThread

      app = QCoreApplication.instance()
      if app is not None:
          current_thread = QThread.currentThread()
          main_thread = app.thread()
          assert current_thread == main_thread, (
              f"InteractionService must be accessed from main thread only. "
              f"Current: {current_thread}, Main: {main_thread}"
          )
  ```

#### Validation
```bash
# Type checking
./bpr services/interaction_service.py

# Run tests (method not called yet, so no behavior change)
uv run pytest tests/test_interaction_service.py -xvs

# Manual test: Verify assertion works
python3 -c "
from PySide6.QtWidgets import QApplication
from services.interaction_service import get_interaction_service
import sys

app = QApplication(sys.argv)
service = get_interaction_service()
service._assert_main_thread()  # Should pass
print('✅ Main thread assertion passed')
"
```

#### Rollback
```bash
git checkout services/interaction_service.py
```

#### Success Criteria
- ✅ 0 type errors
- ✅ Method exists and callable
- ✅ Passes when called from main thread
- ✅ All tests still pass

---

### Increment 4: Update find_point_at() Core Method (BREAKING)

**Goal:** Change return type to PointSearchResult, add multi-curve search support

**Duration:** 90-120 minutes (most critical method)

#### Prerequisites
- [ ] Increment 3 complete
- [ ] Read current `find_point_at()` implementation carefully

#### Changes

**File: `services/interaction_service.py`**

1. **Update method signature:**
   - [ ] Change return type: `-> int` to `-> PointSearchResult`
   - [ ] Add parameter: `mode: SearchMode = "active"`
   - [ ] Add import: `from core.models import PointSearchResult`
   - [ ] Add import: `from core.type_aliases import SearchMode`

2. **Add thread assertion:**
   - [ ] Add as first line: `self._assert_main_thread()`

3. **Implement single-curve mode (mode="active"):**
   - [ ] Replace `return -1` with `return PointSearchResult(index=-1, curve_name=None)`
   - [ ] Replace `return idx` with `return PointSearchResult(index=idx, curve_name=active_curve)`
   - [ ] Use spatial index (existing logic, just wrap return value)

4. **Implement multi-curve mode (mode="all_visible"):**
   - [ ] Copy logic from architecture doc lines 366-406
   - [ ] Search all visible curves
   - [ ] Return best match (closest point across all curves)

**Update test calls (tests that use find_point_at directly):**

**File: `tests/test_interaction_service.py`**
- [ ] Find all `service.find_point_at(` calls
- [ ] Update assertions:
  ```python
  # BEFORE:
  idx = service.find_point_at(view, x, y)
  assert idx >= 0

  # AFTER (Option A - use .index):
  result = service.find_point_at(view, x, y)
  assert result.index >= 0

  # AFTER (Option B - use comparison operators):
  result = service.find_point_at(view, x, y)
  assert result >= 0  # Uses __ge__ operator

  # AFTER (Option C - use .found):
  result = service.find_point_at(view, x, y)
  assert result.found
  ```

**File: `tests/test_interaction_mouse_events.py`**
- [ ] Same updates as above

#### Validation
```bash
# Type checking
./bpr services/interaction_service.py

# Run tests (should pass with updated assertions)
uv run pytest tests/test_interaction_service.py::test_find_point_at -xvs
uv run pytest tests/test_interaction_service.py -x

# Test multi-curve mode (NEW test)
# Add to tests/test_interaction_service.py:
def test_find_point_at_multi_curve_mode(
    interaction_service,
    mock_view,
    mock_main_window,
):
    """Test find_point_at with mode='all_visible'."""
    # Setup: Add multiple curves
    app_state = get_application_state()
    app_state.set_curve_data("curve1", [(1, 10.0, 20.0, "normal")])
    app_state.set_curve_data("curve2", [(1, 100.0, 200.0, "normal")])

    # Search all curves
    result = interaction_service.find_point_at(
        mock_view, 100, 200, mode="all_visible"
    )

    assert result.found
    assert result.curve_name == "curve2"  # Should find curve2's point
    assert result.index >= 0
```

#### Rollback
```bash
git checkout services/interaction_service.py tests/test_interaction_service.py tests/test_interaction_mouse_events.py
```

#### Success Criteria
- ✅ 0 type errors
- ✅ Returns PointSearchResult (not int)
- ✅ `mode="active"` works (single-curve, backward compat)
- ✅ `mode="all_visible"` works (multi-curve)
- ✅ Comparison operators work (`result >= 0`, `if result:`)
- ✅ All tests pass

---

### Increment 5: Add curve_name Parameter to Selection Methods (BREAKING)

**Goal:** Extend 6 selection methods with optional curve_name parameter

**Duration:** 60-90 minutes

#### Prerequisites
- [ ] Increment 4 complete (find_point_at returns PointSearchResult)

#### Changes

**File: `services/interaction_service.py`**

Update these 6 methods (add `curve_name: str | None = None` parameter):

1. **select_point_by_index()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] Default to active curve: `if curve_name is None: curve_name = self._app_state.active_curve`
   - [ ] Use `app_state.set_selection(curve_name, {idx})`

2. **clear_selection()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] If `curve_name=None`, clear ALL selections (new feature)
   - [ ] If `curve_name` specified, clear that curve only

3. **select_all_points()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] Default to active curve

4. **select_points_in_rect()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] Default to active curve

5. **toggle_selection()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] Default to active curve

6. **deselect_all_points()** (if exists)
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] Default to active curve

**Update tests:** Most tests don't need changes (use default None = active curve)

**File: `tests/test_interaction_service.py`**
- [ ] Add new test for explicit curve_name:
  ```python
  def test_select_point_by_curve_name(service, view, main_window):
      # Setup multiple curves
      app_state.set_curve_data("curve1", [(1, 10, 20, "normal")])
      app_state.set_curve_data("curve2", [(1, 100, 200, "normal")])

      # Select in specific curve
      service.select_point_by_index(view, main_window, 0, curve_name="curve2")

      # Verify selection in correct curve
      assert 0 in app_state.get_selection("curve2")
      assert 0 not in app_state.get_selection("curve1")
  ```

#### Validation
```bash
# Type checking
./bpr services/interaction_service.py

# Run tests
uv run pytest tests/test_interaction_service.py -x
```

#### Rollback
```bash
git checkout services/interaction_service.py tests/test_interaction_service.py
```

#### Success Criteria
- ✅ 0 type errors
- ✅ All 6 methods have `curve_name` parameter
- ✅ Default behavior unchanged (uses active curve)
- ✅ Explicit curve_name works
- ✅ All tests pass

---

### Increment 6: Add curve_name Parameter to Manipulation Methods (BREAKING)

**Goal:** Extend 5 manipulation methods with optional curve_name parameter

**Duration:** 60-90 minutes

#### Prerequisites
- [ ] Increment 5 complete

#### Changes

**File: `services/interaction_service.py`**

Update these 5 methods:

1. **update_point_position()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] Default to active curve
   - [ ] Use `app_state.update_point(curve_name, idx, point)`

2. **delete_selected_points()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] Default to active curve
   - [ ] Update DeletePointsCommand to include curve_name

3. **nudge_selected_points()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] Default to active curve

4. **batch_move_points()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] Default to active curve

5. **smooth_points()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] Default to active curve

**File: `core/commands/curve_commands.py`** (if DeletePointsCommand needs update)
- [ ] Add `curve_name: str` parameter to DeletePointsCommand.__init__
- [ ] Store as instance variable
- [ ] Use in execute/undo methods

#### Validation
```bash
# Type checking
./bpr services/interaction_service.py core/commands/curve_commands.py

# Run tests
uv run pytest tests/test_interaction_service.py -x
uv run pytest tests/test_data_service.py -x  # May use manipulation methods
```

#### Rollback
```bash
git checkout services/interaction_service.py core/commands/curve_commands.py
```

#### Success Criteria
- ✅ 0 type errors
- ✅ All 5 methods have `curve_name` parameter
- ✅ Commands track which curve was modified
- ✅ All tests pass

---

### Increment 7: Update Mouse Event Handlers (BREAKING)

**Goal:** Add auto-detect multi-curve logic to 5 mouse handlers

**Duration:** 90-120 minutes (complex logic)

#### Prerequisites
- [ ] Increment 6 complete
- [ ] Read current mouse handler implementations

#### Changes

**File: `services/interaction_service.py`**

1. **_handle_mouse_press_consolidated()**
   - [ ] Add thread assertion
   - [ ] Auto-detect search mode:
     ```python
     all_curves = self._app_state.get_all_curve_names()
     search_mode: SearchMode = "all_visible" if len(all_curves) > 1 else "active"
     ```
   - [ ] Use `find_point_at(..., mode=search_mode)`
   - [ ] Auto-switch active curve if point from different curve
   - [ ] Update selection using curve_name from result

2. **_handle_mouse_move_consolidated()**
   - [ ] Add thread assertion
   - [ ] **FIX Y-FLIP BUG HERE**:
     ```python
     y_multiplier = -1.0 if view.flip_y_axis else 1.0
     curve_delta_y = (delta_y * y_multiplier) / transform.scale
     ```
   - [ ] Use active curve name for point updates

3. **_handle_mouse_release_consolidated()**
   - [ ] Add thread assertion
   - [ ] Clear drag state (no curve-specific changes needed)

4. **handle_wheel_event()**
   - [ ] Add thread assertion
   - [ ] No curve-specific changes (zoom applies to view)

5. **handle_double_click()**
   - [ ] Add thread assertion
   - [ ] Use multi-curve search if applicable

**Update tests for Y-flip fix:**

**File: `tests/test_interaction_service.py`**
- [ ] Find tests that test mouse movement with `flip_y_axis=False`
- [ ] Update Y-coordinate expectations (was inverted, now correct)
- [ ] Add explicit test:
  ```python
  def test_mouse_drag_y_flip_false(service, view, main_window):
      """Test drag direction with flip_y_axis=False (tracking mode)."""
      view.flip_y_axis = False

      # Setup point at (10, 20)
      app_state.set_curve_data("test", [(1, 10.0, 20.0, "normal")])

      # Drag DOWN (screen Y increases)
      # In flip_y_axis=False mode, curve Y should INCREASE
      service.handle_mouse_move(view, drag_down_event)

      updated = app_state.get_curve_data("test")[0]
      assert updated[2] > 20.0, "Drag down should increase Y when flip_y_axis=False"
  ```

#### Validation
```bash
# Type checking
./bpr services/interaction_service.py

# Run mouse event tests
uv run pytest tests/test_interaction_mouse_events.py -xvs
uv run pytest tests/test_interaction_service.py -x

# Manual testing
# 1. Run application
# 2. Load multi-curve data
# 3. Click point in curve A
# 4. Verify active curve switches to A
# 5. Test drag direction with flip_y_axis=True
# 6. Test drag direction with flip_y_axis=False
```

#### Rollback
```bash
git checkout services/interaction_service.py tests/test_interaction_service.py tests/test_interaction_mouse_events.py
```

#### Success Criteria
- ✅ 0 type errors
- ✅ Auto-detects single vs multi-curve mode
- ✅ Auto-switches active curve on click
- ✅ Y-flip bug FIXED (correct drag direction)
- ✅ All tests pass
- ✅ Manual testing confirms correct behavior

---

### Increment 8: Update CurveViewWidget Delegation (HIGH RISK)

**Goal:** Remove 25 duplicate methods from CurveViewWidget, delegate to InteractionService

**Duration:** 2-3 hours (careful testing required)

#### Prerequisites
- [ ] Increment 7 complete (all InteractionService methods ready)
- [ ] Backup current CurveViewWidget: `cp ui/curve_view_widget.py ui/curve_view_widget.py.backup`

#### Changes

**File: `ui/curve_view_widget.py`**

1. **Replace mousePressEvent():**
   - [ ] Remove ~90 lines of duplicate logic
   - [ ] Delegate: `self.interaction_service.handle_mouse_press(self, event)`
   - [ ] Keep any widget-specific logic (cursor updates, etc.)

2. **Replace mouseMoveEvent():**
   - [ ] Remove duplicate drag logic
   - [ ] Delegate: `self.interaction_service.handle_mouse_move(self, event)`

3. **Replace mouseReleaseEvent():**
   - [ ] Remove duplicate logic
   - [ ] Delegate: `self.interaction_service.handle_mouse_release(self, event)`

4. **Replace wheelEvent():**
   - [ ] Remove duplicate zoom logic
   - [ ] Delegate: `self.interaction_service.handle_wheel_event(self, event)`

5. **Remove duplicate helper methods:**
   - [ ] `_find_point_at_multi_curve()` - now use `service.find_point_at(..., mode="all_visible")`
   - [ ] Any other duplicate selection/manipulation methods

**Update tests:**

**File: `tests/test_curve_view.py`** (and related widget tests)
- [ ] Find calls to removed methods
- [ ] Update to use InteractionService:
  ```python
  # BEFORE:
  idx, curve_name = widget._find_point_at_multi_curve(pos)

  # AFTER:
  result = widget.interaction_service.find_point_at(widget, pos.x(), pos.y(), mode="all_visible")
  idx, curve_name = result.index, result.curve_name
  ```

#### Validation
```bash
# Type checking
./bpr ui/curve_view_widget.py

# Run widget tests
uv run pytest tests/test_curve_view.py -xvs
uv run pytest tests/test_ui_components_integration.py -xvs

# Run full integration tests
uv run pytest tests/test_integration.py -xvs
uv run pytest tests/test_integration_real.py -xvs

# Manual testing
# 1. Run application
# 2. Test ALL mouse interactions:
#    - Click to select
#    - Ctrl+click multi-select
#    - Drag to move points
#    - Alt+drag rubber band select
#    - Mouse wheel zoom
#    - Middle-click pan
# 3. Test with single-curve data
# 4. Test with multi-curve data
# 5. Verify no regressions
```

#### Rollback
```bash
# If issues found, restore backup
cp ui/curve_view_widget.py.backup ui/curve_view_widget.py
git checkout tests/test_curve_view.py tests/test_ui_components_integration.py
```

#### Success Criteria
- ✅ 0 type errors
- ✅ ~275 lines removed from CurveViewWidget
- ✅ All mouse interactions delegate to service
- ✅ All tests pass (40-45 tests updated)
- ✅ Manual testing shows no regressions
- ✅ Multi-curve selection still works

---

### Increment 9: Update State Callbacks and History (FINAL METHODS)

**Goal:** Add curve_name parameter to state callbacks, verify history methods

**Duration:** 45-60 minutes

#### Prerequisites
- [ ] Increment 8 complete

#### Changes

**File: `services/interaction_service.py`**

1. **on_data_changed()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion
   - [ ] If `curve_name=None`, handle all curves changed
   - [ ] If specified, handle single curve changed

2. **on_selection_changed()**
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion

3. **on_frame_changed()** (if exists)
   - [ ] Add param: `curve_name: str | None = None`
   - [ ] Add thread assertion

4. **History methods** (verify already multi-curve via ApplicationState):
   - [ ] `add_to_history()` - verify uses ApplicationState (no changes needed)
   - [ ] `undo_action()` - verify uses ApplicationState
   - [ ] `redo_action()` - verify uses ApplicationState

#### Validation
```bash
# Type checking
./bpr services/interaction_service.py

# Run tests
uv run pytest tests/test_interaction_service.py -x
uv run pytest tests/test_interaction_history.py -xvs
```

#### Rollback
```bash
git checkout services/interaction_service.py
```

#### Success Criteria
- ✅ 0 type errors
- ✅ State callbacks support curve_name
- ✅ History methods work with ApplicationState
- ✅ All tests pass

---

### Increment 10: Cleanup and Documentation (FINAL POLISH)

**Goal:** Remove dead code, update documentation, validate metrics

**Duration:** 90-120 minutes

#### Prerequisites
- [ ] Increments 1-9 complete
- [ ] All tests passing
- [ ] 0 type errors

#### Changes

**File: `services/interaction_service.py`**
- [ ] Remove any deprecated code paths
- [ ] Add docstring examples showing multi-curve usage
- [ ] Verify all public methods have thread assertions

**File: `ui/curve_view_widget.py`**
- [ ] Remove any commented-out old code
- [ ] Update class docstring to mention delegation to InteractionService

**File: `CLAUDE.md`**
- [ ] Add multi-curve examples:
  ```markdown
  ### Multi-Curve Operations

  Search across all curves:
  \`\`\`python
  result = service.find_point_at(view, x, y, mode="all_visible")
  if result.found:
      print(f"Point {result.index} in {result.curve_name}")
  \`\`\`

  Select points in specific curve:
  \`\`\`python
  service.select_all_points(view, main_window, curve_name="pp56_TM_138G")
  \`\`\`
  ```

**File: Create `docs/MIGRATION_GUIDE_INTERACTIONSERVICE.md`**
- [ ] Document breaking changes
- [ ] Provide migration examples
- [ ] List deprecated methods

**Validation:**

1. **Code Quality Metrics:**
   ```bash
   # Count lines removed
   git diff --stat main...phase8/final | grep "ui/curve_view_widget.py"
   # Target: ~275 lines removed

   # Count duplicate methods removed
   # Target: 25 methods
   ```

2. **Test Coverage:**
   ```bash
   uv run pytest tests/ --cov=services.interaction_service --cov-report=term-missing
   # Target: ≥80% coverage maintained
   ```

3. **Performance Validation:**
   ```bash
   uv run pytest tests/test_cache_performance.py -xvs
   # Target: 99.9% cache hit rate maintained
   ```

4. **Type Safety:**
   ```bash
   ./bpr
   # Target: 0 errors (maintain current state)
   ```

5. **Full Test Suite:**
   ```bash
   uv run pytest tests/ -x
   # Target: All 2105+ tests pass
   ```

#### Success Criteria
- ✅ **Code Metrics:**
  - 275 lines removed
  - 25 duplicate methods eliminated
  - 1 protocol definition (was 2)
  - 0 type errors
- ✅ **Performance Maintained:**
  - 99.9% cache hit rate
  - 47x rendering speedup
  - 64.7x spatial index speedup
- ✅ **Test Coverage:**
  - All 2105+ tests pass
  - InteractionService ≥80% coverage
- ✅ **Documentation:**
  - Migration guide created
  - CLAUDE.md updated
  - Docstrings include multi-curve examples
- ✅ **Bug Fixes Confirmed:**
  - Y-flip bug fixed (manual test)
  - Thread safety enforced (assertions in place)
  - Protocol consolidation complete

---

## Migration Strategy Summary

**Total Timeline:** 1-2 weeks (10 increments)

| Increment | Duration | Risk | Dependencies |
|-----------|----------|------|--------------|
| 1. Core Types | 30-45 min | LOW | None |
| 2. Protocol Consolidation | 45-60 min | LOW | Inc 1 |
| 3. Thread Safety | 30 min | LOW | Inc 2 |
| 4. find_point_at() | 90-120 min | MEDIUM | Inc 3 |
| 5. Selection Methods | 60-90 min | MEDIUM | Inc 4 |
| 6. Manipulation Methods | 60-90 min | MEDIUM | Inc 5 |
| 7. Mouse Handlers + Y-flip Fix | 90-120 min | HIGH | Inc 6 |
| 8. CurveViewWidget Delegation | 2-3 hours | **VERY HIGH** | Inc 7 |
| 9. State Callbacks | 45-60 min | LOW | Inc 8 |
| 10. Cleanup & Docs | 90-120 min | LOW | Inc 9 |

**Cumulative Progress:**

- **After Inc 3:** Infrastructure ready (0% user-facing changes)
- **After Inc 7:** InteractionService fully multi-curve (50% complete)
- **After Inc 8:** Duplication eliminated (90% complete)
- **After Inc 10:** Full migration complete (100%)

**Rollback Strategy:**

Each increment is a git checkpoint. If issues arise:
1. Identify failing increment
2. Run rollback command for that increment
3. Review changes, fix issues
4. Re-attempt increment
5. Continue from that point

**Testing Strategy:**

- **After each increment:** Run affected tests (fast validation)
- **After increments 4, 7, 8:** Run full test suite (comprehensive validation)
- **After increment 10:** Full QA pass (manual + automated)

---

## Success Metrics

### Code Quality Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Lines | 1,662 | 1,387 | **-275 (-16.5%)** |
| Duplicate Methods | 25 | 0 | **-25 (-100%)** |
| Protocol Definitions | 2 | 1 | **-1 (-50%)** |
| Type Errors | 0 | 0 | **0 (maintained)** |

### Performance Metrics (Must Maintain)

| Metric | Target | Validation |
|--------|--------|------------|
| Cache Hit Rate | 99.9% | TransformService cache stats |
| Rendering Speed | 47x baseline | OptimizedCurveRenderer benchmarks |
| Point Query Speed | 64.7x linear | Spatial index query benchmarks |

### Test Coverage

| Category | Tests | Updates Needed |
|----------|-------|----------------|
| No Changes | 11-16 | 0 (use defaults, no API changes) |
| Minor Updates | 25-30 | Add .index, .found, update comparisons |
| Coordinate Fixes | 10 | Update Y-flip expectations |
| **Total** | **56** | **40-45 (70-80%)** |

**Note:** Initial estimate of 54% was optimistic. Return type changes (int → PointSearchResult) affect most tests using find_point_at() and related methods, requiring `.index` access or comparison updates.

### Bug Fixes

| Bug | Severity | Fixed | Validation |
|-----|----------|-------|------------|
| Y-flip direction | HIGH | ✅ | Manual test + 10 test updates |
| Thread safety | HIGH | ✅ | Assertion coverage |
| Protocol split | HIGH | ✅ | Single definition, re-export |

---

## Code Examples

### Example 1: Single-Curve Selection (Backward Compatible)

```python
# OLD CODE (still works):
idx = service.find_point_at(view, 100, 200)
if idx >= 0:
    service.select_point_by_index(view, main_window, idx)

# NEW CODE (with PointSearchResult):
result = service.find_point_at(view, 100, 200)  # mode="active" default
if result.found:
    service.select_point_by_index(view, main_window, result.index)

# Or use .index property for compatibility:
idx = service.find_point_at(view, 100, 200).index
if idx >= 0:
    # ... exact same as old code
```

### Example 2: Multi-Curve Selection (New Feature)

```python
# Search across all visible curves
result = service.find_point_at(view, 100, 200, mode="all_visible")
if result.found:
    print(f"Found point {result.index} in curve '{result.curve_name}'")

    # Automatically switches active curve if needed
    service.select_point_by_index(
        view, main_window,
        idx=result.index,
        curve_name=result.curve_name  # Explicit curve context
    )
```

### Example 3: Cross-Curve Operations

```python
# Select points from multiple curves
for curve_name in ["pp56_TM_138G", "pp53_TM_134G", "pp50_TM_134G"]:
    service.select_all_points(view, main_window, curve_name=curve_name)

# Clear selection for specific curve
service.clear_selection(view, main_window, curve_name="pp56_TM_138G")

# Clear all selections
service.clear_selection(view, main_window)  # curve_name=None
```

### Example 4: CurveViewWidget Simplification

```python
# BEFORE (90 lines of duplicate logic):
class CurveViewWidget:
    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()

        # Duplicate multi-curve logic
        all_curve_names = self._app_state.get_all_curve_names()
        if all_curve_names:
            idx, curve_name = self._find_point_at_multi_curve(pos)
        else:
            idx = self._find_point_at(pos)
            curve_name = None

        if idx >= 0:
            # Duplicate curve switching logic
            if curve_name and curve_name != self.active_curve_name:
                self.set_active_curve(curve_name)

            # Duplicate selection logic
            add_to_selection = event.modifiers() & Qt.KeyboardModifier.ControlModifier
            self._select_point(idx, add_to_selection, curve_name)
            # ... 70 more lines

# AFTER (5 lines - delegate to service):
class CurveViewWidget:
    def mousePressEvent(self, event: QMouseEvent) -> None:
        # InteractionService handles everything:
        # - Multi-curve detection
        # - Curve switching
        # - Selection logic
        # - Drag setup
        self.interaction_service.handle_mouse_press(self, event)
```

### Example 5: Y-Flip Bug Fix

```python
# BEFORE (bug - hardcoded inversion):
def _handle_mouse_move_consolidated(self, view, event):
    delta_y = pos.y() - last_pos.y()
    curve_delta_y = -delta_y / scale  # Always inverts!

# AFTER (respects view setting):
def _handle_mouse_move_consolidated(self, view, event):
    delta_y = pos.y() - last_pos.y()

    # Respect view's coordinate system
    y_multiplier = -1.0 if view.flip_y_axis else 1.0
    curve_delta_y = (delta_y * y_multiplier) / scale

    # Now works correctly for both:
    # - Traditional mode (flip_y_axis=True): Y=0 at bottom
    # - Tracking mode (flip_y_axis=False): Y=0 at top
```

---

## Risk Assessment

### Low Risk Items (Safe to Implement)

1. **New dataclasses** - Additive only, no existing code affected
2. **Protocol consolidation** - Structural refactoring, no behavior change
3. **Optional parameters** - Backward compatible with defaults
4. **Thread assertions** - Early error detection (better than silent failure)

### Medium Risk Items (Requires Testing)

1. **PointSearchResult return type** - Most code just adds `.index`
   - **Mitigation:** Property access identical to int usage
   - **Test coverage:** Verify all call sites updated

2. **Y-flip bug fix** - Changes drag direction for flip_y_axis=False
   - **Mitigation:** This is a BUG FIX - current behavior is wrong
   - **Test coverage:** Update 10 tests with corrected expectations

3. **Method signature extensions** - curve_name parameter added
   - **Mitigation:** Optional with None default (active curve)
   - **Test coverage:** Existing tests use defaults (no change)

### High Risk Items (Requires Careful Migration)

1. **CurveViewWidget delegation** - Removes 450 lines of logic
   - **Mitigation:** Phase 3 only, incremental testing
   - **Test coverage:** Update 20 tests to use service methods
   - **Rollback plan:** Keep old methods as deprecated for one release

2. **Mouse event handler changes** - Auto-detect multi-curve
   - **Mitigation:** Match existing CurveViewWidget behavior exactly
   - **Test coverage:** Integration tests for multi-curve selection
   - **Validation:** Manual testing with real tracking data

### Mitigation Strategies

1. **Feature flags:** Add `ENABLE_MULTI_CURVE_SERVICE` env var for gradual rollout
2. **Parallel implementation:** Keep old methods with deprecation warnings (Phase 3)
3. **Comprehensive testing:** Run full test suite after each phase
4. **Manual validation:** Test with real 3DEqualizer tracking data
5. **Performance benchmarks:** Validate 99.9% cache hit rate maintained

---

## Implementation Checklist

### Phase 1: Foundation ✅ Design Complete

- [ ] Add `PointSearchResult` dataclass to `core/models.py`
- [ ] Add `CurveSelection` dataclass to `core/models.py`
- [ ] Add `SearchMode` type alias to `core/type_aliases.py`
- [ ] Enhance `protocols/ui.py` CurveViewProtocol:
  - [ ] Add `active_curve_name: str | None`
  - [ ] Add `curves_data: dict[str, CurveDataList]`
  - [ ] Add `flip_y_axis: bool`
- [ ] Update `service_protocols.py` to re-export CurveViewProtocol
- [ ] Remove duplicate CurveViewProtocol (lines 82-199)
- [ ] Add `_assert_main_thread()` to InteractionService
- [ ] Run `uv run basedpyright` - target: 0 errors
- [ ] Run `uv run pytest tests/test_interaction_service.py` - target: all pass

### Phase 2: Extend Methods ⏳ Ready to Implement

- [ ] Update `find_point_at()`:
  - [ ] Change return type to `PointSearchResult`
  - [ ] Add `mode: SearchMode = "active"` parameter
  - [ ] Implement `mode="active"` path (single-curve)
  - [ ] Implement `mode="all_visible"` path (multi-curve)
  - [ ] Add thread assertion
- [ ] Update selection methods (6):
  - [ ] `select_point_by_index()` - add curve_name param
  - [ ] `clear_selection()` - add curve_name param
  - [ ] `select_all_points()` - add curve_name param
  - [ ] `select_points_in_rect()` - add curve_name param
  - [ ] `toggle_selection()` - add curve_name param
  - [ ] Add thread assertions to all
- [ ] Update manipulation methods (5):
  - [ ] `update_point_position()` - add curve_name param
  - [ ] `delete_selected_points()` - add curve_name param
  - [ ] `nudge_selected_points()` - add curve_name param
  - [ ] `batch_move_points()` - add curve_name param
  - [ ] `smooth_points()` - add curve_name param
  - [ ] Add thread assertions to all
- [ ] Write new tests:
  - [ ] `test_find_point_at_multi_curve()`
  - [ ] `test_select_across_curves()`
  - [ ] `test_thread_assertion_failure()`
- [ ] Run full test suite - target: 56/56 pass

### Phase 3: Update CurveViewWidget 🔜 Implementation Ready

- [ ] Update `mousePressEvent()`:
  - [ ] Replace `_find_point_at_multi_curve()` with `service.find_point_at()`
  - [ ] Delegate to `service.handle_mouse_press()`
- [ ] Update mouse handlers:
  - [ ] Replace `mouseMoveEvent()` logic
  - [ ] Replace `mouseReleaseEvent()` logic
- [ ] Remove duplicate methods:
  - [ ] `_find_point_at_multi_curve()` (44 lines)
  - [ ] Duplicate selection logic (~200 lines)
  - [ ] Duplicate manipulation logic (~150 lines)
- [ ] Update 20 tests:
  - [ ] Replace `_find_point_at_multi_curve()` calls
  - [ ] Update assertions for PointSearchResult
- [ ] Manual testing:
  - [ ] Multi-curve selection works
  - [ ] Curve switching works
  - [ ] Drag & drop works
- [ ] Run full test suite - target: 56/56 pass

### Phase 4: Fix Bugs 🔜 Implementation Ready

- [ ] Fix Y-flip bug (3 locations):
  - [ ] `_handle_mouse_move_consolidated()` line 227
  - [ ] `_handle_key_event_consolidated()` line 439
  - [ ] Any other Y-transform locations
- [ ] Update 10 coordinate tests:
  - [ ] Fix Y-flip expectations for `flip_y_axis=False`
  - [ ] Verify drag direction correctness
- [ ] Manual testing:
  - [ ] Test with `flip_y_axis=True` (traditional)
  - [ ] Test with `flip_y_axis=False` (tracking)
  - [ ] Verify correct drag directions
- [ ] Run full test suite - target: 56/56 pass

### Phase 5: Cleanup 🔜 Final Polish

- [ ] Remove deprecated code
- [ ] Update docstrings with examples
- [ ] Add migration guide
- [ ] Performance validation:
  - [ ] Cache hit rate: 99.9%
  - [ ] Rendering: 47x baseline
  - [ ] Point queries: 64.7x linear
- [ ] Documentation:
  - [ ] Update CLAUDE.md with new patterns
  - [ ] Add migration examples
  - [ ] Document multi-curve workflows
- [ ] Final validation:
  - [ ] All 56 tests pass
  - [ ] 0 type errors
  - [ ] Performance metrics maintained

---

## Appendix: Complete Method Inventory

### Selection Methods (6)

| Method | Current Signature | New Signature | Change Type |
|--------|------------------|---------------|-------------|
| find_point_at | `(view, x, y) -> int` | `(view, x, y, mode="active") -> PointSearchResult` | Return type, add param |
| select_point_by_index | `(view, mw, idx, add=False) -> bool` | `(..., curve_name=None) -> bool` | Add param |
| clear_selection | `(view, mw) -> None` | `(..., curve_name=None) -> None` | Add param |
| select_all_points | `(view, mw) -> int` | `(..., curve_name=None) -> int` | Add param |
| select_points_in_rect | `(view, mw, rect) -> int` | `(..., curve_name=None) -> int` | Add param |
| toggle_selection | `(view, mw, idx) -> None` | `(..., curve_name=None) -> None` | Add param |

### Manipulation Methods (5)

| Method | Current Signature | New Signature | Change Type |
|--------|------------------|---------------|-------------|
| update_point_position | `(view, mw, idx, x, y) -> bool` | `(..., curve_name=None) -> bool` | Add param |
| delete_selected_points | `(view, mw) -> None` | `(..., curve_name=None) -> None` | Add param |
| nudge_selected_points | `(view, mw, dx, dy) -> bool` | `(..., curve_name=None) -> bool` | Add param |
| batch_move_points | `(view, mw, moves) -> None` | `(..., curve_name=None) -> None` | Add param |
| smooth_points | `(view, mw, indices) -> None` | `(..., curve_name=None) -> None` | Add param |

### Mouse Event Handlers (5)

| Method | Signature | Change Type |
|--------|-----------|-------------|
| handle_mouse_press | `(view, event) -> None` | Internal logic only |
| handle_mouse_move | `(view, event) -> None` | Internal logic only |
| handle_mouse_release | `(view, event) -> None` | Internal logic only |
| handle_wheel_event | `(view, event) -> None` | Internal logic only |
| handle_double_click | `(view, event) -> None` | Internal logic only |

### State Callbacks (3)

| Method | Current Signature | New Signature | Change Type |
|--------|------------------|---------------|-------------|
| on_data_changed | `(view) -> None` | `(view, curve_name=None) -> None` | Add param |
| on_selection_changed | `(view) -> None` | `(view, curve_name=None) -> None` | Add param |
| on_frame_changed | `(view, frame) -> None` | `(..., curve_name=None) -> None` | Add param |

### History Methods (5)

| Method | Signature | Change Type |
|--------|-----------|-------------|
| add_to_history | `(mw, state=None) -> None` | None (already multi-curve) |
| undo_action | `(mw) -> None` | None (already multi-curve) |
| redo_action | `(mw) -> None` | None (already multi-curve) |
| save_state | `(mw) -> None` | None (already multi-curve) |
| restore_state | `(mw, state) -> None` | None (already multi-curve) |

### View Methods (1)

| Method | Current Implementation | New Implementation | Change Type |
|--------|----------------------|-------------------|-------------|
| apply_pan_offset_y | `delta_y = -delta / scale` | `delta_y = (delta * y_mul) / scale` | Bug fix |

**Total: 25 methods**
- **11 signature changes** (add optional curve_name parameter)
- **5 internal changes** (auto-detect multi-curve)
- **5 no changes** (already multi-curve via ApplicationState)
- **1 bug fix** (Y-flip calculation)
- **3 new types** (PointSearchResult, CurveSelection, SearchMode)

---

**End of Architecture Design Document**

*This document serves as the implementation blueprint for the InteractionService multi-curve refactoring. All design decisions are finalized and ready for code implementation.*
