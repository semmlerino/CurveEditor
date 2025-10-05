# Selection State Refactoring Plan

**Date:** October 2025
**Status:** Approved - Ready for Implementation
**Priority:** High - Fixes race condition bug in multi-point selection

## Executive Summary

This document describes the architectural issues with selection state management in CurveEditor and provides a detailed refactoring plan to eliminate synchronization loops while preserving existing functionality.

**Recommended Approach:** Hybrid + One-Way Flow (eliminates sync loop, documents ownership, minimal changes)

---

## The Core Architectural Problems

### 1. Distributed State Without Clear Ownership

The Selection State Lives in **4+ Places**:
- `QTableWidget.selectionModel()` (Qt's internal state)
- `CurveViewWidget.selected_curve_names` (view state for rendering)
- `point_names` parameter in signals (transient)
- **Notably NOT** in `ApplicationState` (the "single source of truth")

**Problem:** Nobody owns it. Everyone is synchronizing with everyone else, creating fragile coupling.

### 2. Query-After-Emit Anti-Pattern

```python
# Anti-pattern that caused the bug:
self.points_selected.emit(selected_points)  # Send data via signal
...
selected = self.get_selected_points()  # Query it back!
```

**Why this is broken:**
- Signal emission queues async Qt events
- Between emit and query, Qt selection might change
- Classic read-during-write race condition
- Fix: Pass the parameter forward instead of re-querying

**Better pattern:**
```python
# Signal contains ALL needed data, receiver uses it directly
self.points_selected.emit(selected_points)
# Receiver: Use the parameter, NEVER query back
```

### 3. Synchronization Loops Create Reentrancy Bugs

**The flow when you Ctrl+click:**

1. User clicks → Qt selection changes
2. `_on_selection_changed()` fires
3. `points_selected.emit(["Point06", "Point10"])`
4. `on_tracking_points_selected(["Point06", "Point10"])`
5. **`set_selected_points(["Point06", "Point10"])`** ← **WHY??**
6. `set_selected_points()` CLEARS then re-selects
7. Qt fires **ANOTHER** `_on_selection_changed()` during step 6
8. **Race condition:** query happens during clearing phase

**Step 5 is the architectural mistake:** The UI already has the correct selection! Why force-sync something that's already right? This is "defensive programming" that creates the bug it's defending against.

### 4. Signal-Driven Architecture Without Transactions

`ApplicationState` has `begin_batch()` / `end_batch()` for data mutations, but there's no equivalent for UI state changes. Can't say "these 3 operations are atomic, don't fire signals mid-way."

Qt's signal system is asynchronous - you can't control when queued signals fire. The `_updating` flag tries to prevent reentrancy but fails because:

```python
self._updating = True
table.clearSelection()  # Queues Qt signal
table.select(rows)      # Queues Qt signal
self._updating = False  # Released!
# ...later, Qt signals fire with _updating=False
```

### 5. Why TDD Failed Initially

Early tests called methods directly:
```python
widget.set_curves_data(...)  # Direct call
```

This bypassed the signal chain and didn't trigger the race condition. Only the full integration test with `MainWindow` and Qt's event loop reproduced it.

**Testing lesson:** Signal-driven architectures need integration tests that exercise the full async signal chain, not just unit tests of individual methods.

### 6. Lack of Immutability

Signals pass `list[str]` (mutable). If any handler modifies it, everyone gets confused. Should use `tuple[str, ...]` or `frozenset[str]`.

---

## Architecture Options Considered

### Option A: Selection in ApplicationState (True Single Source of Truth)

```python
# Move selection into ApplicationState
app_state.set_selected_curves(frozenset(["Point06", "Point10"]))

# UI observes and updates
app_state.selected_curves_changed.connect(
    tracking_panel.sync_table_selection  # One-way: State → UI
)
app_state.selected_curves_changed.connect(
    curve_widget.update  # Renderer observes
)

# User interaction → Command → State
def _on_table_selection_changed(self):
    selected = frozenset(self.get_selected_points())
    app_state.set_selected_curves(selected)  # ONE source of truth
```

**Pros:**
- One definitive source of truth
- Testable without UI
- Serializable for undo/redo
- No sync loops

**Cons:**
- Fights Qt's selection model abstraction
- More boilerplate
- Major architectural change

### Option B: UI Owns Selection (One-Way Data Flow)

```python
# TrackingPointsPanel owns its selection, everyone else observes
tracking_panel.selection_changed.connect(
    lambda names: controller.update_curves(names)
)

# NEVER call set_selected_points() from outside
# Panel manages its own state
```

**Pros:**
- Clear ownership
- Qt selection model works naturally
- Simpler

**Cons:**
- Selection state not in data layer
- Harder to test without UI
- No serialization support

### Option C: Hybrid + Enforce One-Way Flow ✅ **RECOMMENDED**

**Combines best of both:**
1. `TrackingPointsPanel` owns table selection (UI state stays in UI)
2. Signals carry complete data (never query back)
3. **Remove the synchronization loop:**
   ```python
   # DELETE this line from on_tracking_points_selected():
   self.main_window.tracking_panel.set_selected_points(point_names)
   # The panel already has the right selection - don't force-sync!
   ```
4. Add selection query to `ApplicationState` (for non-UI code):
   ```python
   # Read-only query, not a source of truth
   app_state.get_selected_curves() → delegates to widget
   ```
5. Document ownership clearly
6. Make signal data immutable:
   ```python
   points_selected: Signal = Signal(tuple)  # Not list
   ```

**Why this is best:**
- Minimal code changes
- Fixes the bug
- Works with Qt naturally
- Preserves existing architecture
- Clear ownership documentation
- Path to future ApplicationState migration if needed

---

## Detailed Implementation Plan

### Step 1: Remove Synchronization Loop ⚠️ **CRITICAL FIX**

**File:** `ui/controllers/multi_point_tracking_controller.py`
**Line:** 357

**Change:**
```python
# DELETE THIS LINE:
self.main_window.tracking_panel.set_selected_points(point_names)
```

**Reason:** The panel already has the correct selection (it just emitted the signal!). Re-setting creates the reentrancy bug.

**Context:**
```python
def on_tracking_points_selected(self, point_names: list[str]) -> None:
    """Handle selection of tracking points from panel."""
    self.main_window.active_timeline_point = point_names[-1] if point_names else None

    # ❌ DELETE THIS - Creates synchronization loop:
    # if self.main_window.tracking_panel:
    #     self.main_window.tracking_panel.set_selected_points(point_names)

    # ✅ KEEP THIS - Direct sync to data layer:
    self._sync_tracking_selection_to_curve_store(point_names)

    # ✅ KEEP THIS - Update display with signal data:
    self.update_curve_display(SelectionContext.MANUAL_SELECTION, selected_points=point_names)

    # ... rest of method
```

### Step 2: Make Signal Data Immutable

**File:** `ui/tracking_points_panel.py`

**Line 134 - Signal Definition:**
```python
# BEFORE:
points_selected: Signal = Signal(list)

# AFTER:
points_selected: Signal = Signal(tuple)  # Immutable
```

**Line 517 - Signal Emission:**
```python
def _on_selection_changed(self) -> None:
    """Handle table selection changes."""
    if self._updating:
        return

    selected_points = self.get_selected_points()
    # BEFORE: self.points_selected.emit(selected_points)
    # AFTER:
    self.points_selected.emit(tuple(selected_points))  # Convert to immutable tuple
```

**Reason:** Prevents handlers from accidentally modifying shared list data.

### Step 3: Update Signal Handler Types

**File:** `ui/controllers/multi_point_tracking_controller.py`

**Line 342:**
```python
# BEFORE:
def on_tracking_points_selected(self, point_names: list[str]) -> None:

# AFTER:
def on_tracking_points_selected(self, point_names: tuple[str, ...]) -> None:
```

**Note:** Update docstrings to reflect tuple instead of list.

**Other files to check:**
- Search for all `points_selected.connect` calls
- Update handler signatures to accept `tuple[str, ...]`

### Step 4: Document Ownership (Architecture Clarity)

**File:** `ui/tracking_points_panel.py`

**Add to class docstring:**
```python
class TrackingPointsPanel(QWidget):
    """
    Panel for managing multi-point tracking data.

    SELECTION STATE OWNERSHIP:
    --------------------------
    This widget OWNS its table selection state (QTableWidget.selectionModel()).

    External code interaction patterns:
    1. OBSERVE changes via points_selected signal (one-way flow)
       - Signal emits tuple of selected point names
       - Handlers should NEVER call set_selected_points() in response

    2. SET selection programmatically via set_selected_points()
       - For initialization after data load
       - For syncing from OTHER sources (e.g., curve view → panel)
       - NEVER in response to points_selected signal (creates loop!)

    3. QUERY current selection via get_selected_points()
       - Returns list of currently selected point names
       - Used by external code that doesn't subscribe to signals

    ANTI-PATTERN (causes race condition):
        panel.points_selected.connect(
            lambda names: panel.set_selected_points(names)  # ❌ DON'T!
        )

    CORRECT PATTERN:
        panel.points_selected.connect(
            lambda names: controller.handle_selection(names)  # ✅ Use data
        )

    See SELECTION_STATE_REFACTORING_PLAN.md for full architecture details.
    """
```

### Step 5: Verify Legitimate set_selected_points() Calls

**These calls are CORRECT and should REMAIN:**

**File:** `ui/controllers/multi_point_tracking_controller.py`

1. **Line 149:** Initial selection after loading single-point data
   ```python
   self.main_window.tracking_panel.set_selected_points(["Track1"])
   # ✅ KEEP - Programmatic initialization
   ```

2. **Line 214, 227:** Programmatic selection for new points
   ```python
   self.main_window.tracking_panel.set_selected_points([new_point_names[0]])
   self.main_window.tracking_panel.set_selected_points([first_point])
   # ✅ KEEP - Initialization after data load
   ```

3. **Line 395:** Clear selection (from curve view)
   ```python
   self.main_window.tracking_panel.set_selected_points([])
   # ✅ KEEP - Sync from OTHER source (curve selection → panel)
   ```

4. **Line 412:** Sync curve selection to panel
   ```python
   self.main_window.tracking_panel.set_selected_points(selected_curves)
   # ✅ KEEP - Sync from OTHER source (curve selection → panel)
   ```

**The key difference:**
- ❌ DELETE: Calling `set_selected_points()` in response to `points_selected` signal
- ✅ KEEP: Calling `set_selected_points()` from OTHER sources (file load, curve view)

### Step 6: Add Type Conversions Where Needed

Since we're changing from `list` to `tuple`, some code may need conversions:

**Pattern to search for:**
```python
# If code needs a mutable list from the signal:
def handler(self, point_names: tuple[str, ...]) -> None:
    # Convert to list only if mutation needed:
    mutable_names = list(point_names)
```

**Most code should work unchanged** since both list and tuple support:
- Iteration: `for name in point_names`
- Membership: `if name in point_names`
- Indexing: `point_names[-1]`
- Length: `len(point_names)`

---

## Files Modified

### Primary Changes
1. **`ui/controllers/multi_point_tracking_controller.py`**
   - Remove synchronization loop (line 357)
   - Update parameter type `on_tracking_points_selected()` (line 342)

2. **`ui/tracking_points_panel.py`**
   - Change signal type to tuple (line 134)
   - Emit tuple instead of list (line 517)
   - Add comprehensive ownership documentation to class docstring

### Verification Required
3. **Search for:** `points_selected.connect`
   - Update any other handlers to accept `tuple[str, ...]`
   - Verify no other synchronization loops exist

4. **Search for:** Uses of `point_names` parameter
   - Add `list()` conversion if mutation needed
   - Most cases should work unchanged

---

## Testing Strategy

### 1. Manual Testing (Reproduce Original Bug)
- Load multi-point tracking data
- Ctrl+click to select multiple points in panel
- **Expected:** No race condition, stable selection
- **Previous bug:** Race condition on second click

### 2. Integration Testing
Test the full signal chain with Qt event loop:
```python
def test_selection_signal_chain(main_window):
    """Test that selection signals don't create loops."""
    panel = main_window.tracking_panel

    # Load multi-point data
    panel.set_tracked_data({"Point1": [...], "Point2": [...]})

    # Simulate user selection
    # (Use QTest.mouseClick or direct table selection)

    # Verify signal emitted with correct data
    # Verify no reentrancy issues
    # Verify display updated correctly
```

### 3. Regression Testing
Verify existing functionality still works:
- File loading with automatic selection
- Programmatic selection from curve view
- Clear selection operations
- Multi-curve display mode switching

### 4. Type Checking
```bash
./bpr ui/tracking_points_panel.py
./bpr ui/controllers/multi_point_tracking_controller.py
```

---

## Migration Path for Future Improvements

### Phase 1 (This Refactoring): Tactical Fix ✅
- Remove synchronization loop
- Document ownership
- Make signals immutable
- **Status:** Minimal changes, fixes bug immediately

### Phase 2 (Future): Enhanced Observability
- Add `ApplicationState.get_selected_curves()` as read-only query
- Delegates to `TrackingPointsPanel.get_selected_points()`
- Allows non-UI code to query selection without coupling to widget
- **Status:** Optional, improves API

### Phase 3 (Future): Full ApplicationState Migration
- Move selection into `ApplicationState._selected_curves`
- UI becomes pure observer
- Enables serialization for undo/redo
- Requires larger refactoring
- **Status:** Future consideration if serialization needed

---

## Architectural Principles Established

### 1. Signal Ownership Rule
**"The emitter owns the data, receivers observe it"**
- Never call setter methods in response to the signal they trigger
- Signals should carry complete data (no querying back)
- Use immutable types in signals to prevent mutation bugs

### 2. UI State Ownership
**"UI widgets own their own visual state"**
- `QTableWidget` owns its selection model
- External code observes via signals
- Programmatic updates only from OTHER sources, not signal feedback

### 3. One-Way Data Flow
**"Data flows in one direction through the signal chain"**
```
User Action → Qt Event → Signal → Controller → Data Layer → Display Update
                ↑                                                    ↓
                └──────────────── NO FEEDBACK LOOP ─────────────────┘
```

### 4. Synchronization Pattern
**"Initialize from source, synchronize to targets"**
```python
# ✅ CORRECT: Initialize/sync from authoritative source
file_data_loaded → set_selected_points(initial_point)

# ✅ CORRECT: Sync from one UI to another UI
curve_view_selection_changed → set_selected_points(curve_names)

# ❌ WRONG: Sync back to origin
panel.points_selected → set_selected_points(same_data)  # Creates loop!
```

---

## Success Criteria

### Must Have ✅
- [ ] No race condition on multi-point selection (Ctrl+click)
- [ ] No reentrancy bugs in signal chain
- [ ] Existing functionality preserved (file load, programmatic selection)
- [ ] Type checking passes (basedpyright)
- [ ] All tests pass

### Should Have 📋
- [ ] Clear documentation of ownership patterns
- [ ] Immutable signal types prevent mutation bugs
- [ ] Code comments explain why synchronization loop was removed

### Nice to Have 🎯
- [ ] Integration test covering full signal chain
- [ ] Architecture diagram showing data flow
- [ ] Performance improvement from eliminating unnecessary sync

---

## Risk Assessment

### Low Risk Changes ✅
- Removing sync loop: Eliminates code, can't introduce new bugs
- Documentation: No functional impact
- Signal type change: Compile-time verified by type checker

### Medium Risk Changes ⚠️
- Tuple conversion: May require list() calls in some handlers
- **Mitigation:** Type checker will catch incompatibilities

### No Risk 🟢
- Keeping legitimate set_selected_points() calls unchanged
- Observable behavior remains identical to users

---

## References

- **Original bug report:** Race condition in multi-point Ctrl+click selection
- **Root cause analysis:** Query-after-emit anti-pattern + sync loop
- **Architecture assessment:** Distributed state without clear ownership
- **Testing gap:** Integration tests needed for signal chains

---

## Appendix: Code Locations Reference

### Key Methods
- `TrackingPointsPanel._on_selection_changed()` - Line 511-517
- `TrackingPointsPanel.set_selected_points()` - Line 319-352
- `TrackingPointsPanel.get_selected_points()` - Line 299-317
- `MultiPointTrackingController.on_tracking_points_selected()` - Line 342-377
- `MultiPointTrackingController.on_curve_selection_changed()` - Line 379-417

### Signal Connections
- `ui/controllers/ui_initialization_controller.py:420` - Primary connection
- Search pattern: `points_selected.connect` for all connections

### ApplicationState Selection API
- `ApplicationState.get_selection()` - Line 263-280 (per-curve point indices)
- `ApplicationState.set_selection()` - Line 282-300 (per-curve point indices)
- **Note:** This is for point-level selection within curves, not curve-level selection in panel

---

**End of Plan**
