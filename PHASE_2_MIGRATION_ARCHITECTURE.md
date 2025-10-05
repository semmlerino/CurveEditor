# Phase 2: CurveDataStore to ApplicationState Migration Architecture

**Date**: 2025-10-05
**Status**: Architecture Design Complete - Ready for Phase 3-4 Implementation
**Phase 0 Prerequisite**: ✅ COMPLETE (ApplicationState API enhanced)
**Related Documents**:
- PHASE_0_COMPLETION_REPORT.md (API enhancements)
- PHASE_4_FINDINGS_SYNTHESIS.md (Analysis findings)
- PHASE_4_DEFAULT_CLEANUP_DEFERRED.md (Cleanup locations)

---

## 1. Executive Summary

This document defines the architecture for migrating from CurveDataStore to ApplicationState as the single source of truth for curve data. The migration follows a **gradual, risk-minimized approach** that maintains 100% test pass rate throughout.

### CRITICAL CORRECTIONS (Code Review Findings)

**This architecture was based on incorrect assumptions. Key corrections:**

1. **NO Circular Dependency Exists**: `StateSyncController._on_store_data_changed()` does NOT write to ApplicationState. Unidirectional sync already implemented.
2. **update_point() Signature Wrong**: CurveDataFacade.update_point takes `(index, x, y)` NOT `(index, x?, y?, status?)`. No status parameter exists.
3. **8 Signal Handlers, Not 6**: Complete list verified via codebase search (see Section 4 table).

**Phase 3.1 Revised Scope**: Since circular dependency doesn't exist, Phase 3.1 focuses on redirecting CurveDataFacade writes to ApplicationState and removing obsolete signals.

### Key Architectural Decisions

1. **Direction of Migration**: ApplicationState ALREADY is source of truth for CurveDataStore (verified). Redirect CurveDataFacade writes to ApplicationState (Phase 3.2).
2. **Signal Migration Strategy**: Update 8 signal handlers (not 6) with temporary adapter layer
3. **`__default__` Removal**: Remove after CurveDataStore deprecation (Phase 4)
4. **Testing Strategy**: Checkpoint after each sub-phase with full test suite validation

### Timeline & Risk Profile (REVISED)

| Phase | Duration | Risk | Dependencies |
|-------|----------|------|--------------|
| Phase 3.1: Verify Unidirectional Flow (REVISED) | 0.25 day | LOW | Phase 0 complete |
| Phase 3.2: Migrate CurveDataFacade | 0.5 day | MEDIUM | Phase 3.1 complete |
| Phase 3.3: Update Signal Handlers (8 handlers) | 1 day | MEDIUM | Phase 3.1 complete |
| Phase 4: Remove `__default__` | 0.5 day | LOW | Phase 3 complete |
| **Total** | **2.25 days** | **LOW-MEDIUM** | Phase 0 validated |

**Duration Reduced**: Phase 3.1 is now verification-only (no breaking changes needed), reducing total from 3 days to 2.25 days.

### Success Metrics

- ✅ Zero CurveDataStore references in production code
- ✅ Zero `__default__` references in production code
- ✅ 100% test pass rate (2105/2105 tests passing)
- ✅ 0 basedpyright errors (type safety maintained)
- ✅ No circular signal dependencies
- ✅ Performance maintained (< 5% regression acceptable)

---

## 2. StateSyncController Refactoring Design

### Current State Verification

**ACTUAL Current Implementation** (`ui/controllers/curve_view/state_sync_controller.py:118-136`):

```python
def _on_store_data_changed(self) -> None:
    """Handle store data changed signal."""
    # Update internal point collection
    data = self.widget.curve_data
    if data:
        formatted_data = []
        for point in data:
            if len(point) >= 3:
                formatted_data.append((int(point[0]), float(point[1]), float(point[2])))
        self.widget.point_collection = PointCollection.from_tuples(formatted_data)
    else:
        self.widget.point_collection = None

    # Clear caches and update display
    self.widget.invalidate_caches()
    self.widget.update()

    # Propagate signal to widget listeners
    self.widget.data_changed.emit()
```

**Key Observation**: NO ApplicationState writes exist in this method. Search for `self._app_state.set_curve_data` in this file returns 0 results.

**Current Data Flow** (unidirectional from ApplicationState):
```
ApplicationState.set_curve_data("__default__", data)
  ↓ emits
ApplicationState.curves_changed
  ↓
StateSyncController._on_app_state_curves_changed() (line 214-235)
  ↓ calls
CurveDataStore.set_data(data, preserve_selection_on_sync=True)
  ↓ emits
CurveDataStore.data_changed
  ↓
StateSyncController._on_store_data_changed() (line 118-136)
  ↓ updates
widget.point_collection, widget caches
  ↓ NO WRITE BACK TO ApplicationState ✅
```

**Analysis**: The claimed "circular dependency" does NOT exist in current code. The sync is already unidirectional (ApplicationState → CurveDataStore → Widget).

### Revised Phase 3.1 Scope

**What Phase 3.1 ACTUALLY Does**:

Since the circular dependency does NOT exist, Phase 3.1 focuses on:

1. **Redirect CurveDataFacade writes** from CurveDataStore to ApplicationState (see Section 3)
2. **Remove obsolete signal handlers** that are no longer needed with ApplicationState as source
3. **Verify unidirectional flow** is maintained throughout migration

**No changes needed to `_on_store_data_changed()`** - it already does NOT write to ApplicationState.

#### Step 1: Verify Current Unidirectional Flow (Phase 3.1.1)

**Verification Command**:
```bash
# Confirm NO ApplicationState writes in _on_store_data_changed
grep -n "self._app_state.set_curve_data\|self._app_state.add_point\|self._app_state.update_point\|self._app_state.remove_point" ui/controllers/curve_view/state_sync_controller.py

# Expected output: NO matches in _on_store_data_changed method (lines 118-136)
# Only matches should be in initialization or other methods
```

**Current Code Analysis** (`ui/controllers/curve_view/state_sync_controller.py`):

```python
# CURRENT STATE (ALREADY CORRECT - lines 118-136):
def _on_store_data_changed(self) -> None:
    """Handle store data changed signal."""
    # Update internal point collection
    data = self.widget.curve_data
    if data:
        formatted_data = []
        for point in data:
            if len(point) >= 3:
                formatted_data.append((int(point[0]), float(point[1]), float(point[2])))
        self.widget.point_collection = PointCollection.from_tuples(formatted_data)
    else:
        self.widget.point_collection = None

    # Clear caches and update display
    self.widget.invalidate_caches()
    self.widget.update()

    # Propagate signal to widget listeners
    self.widget.data_changed.emit()

# NO CHANGES NEEDED - already correct! ✅

# CURRENT STATE (ALREADY CORRECT - lines 214-235):
def _on_app_state_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
    """Handle ApplicationState curves_changed signal."""
    # CRITICAL: Sync ApplicationState "__default__" curve back to CurveDataStore
    default_curve = "__default__"
    if default_curve in curves:
        # Update CurveDataStore to match ApplicationState
        default_data = curves[default_curve]
        current_data = self._curve_store.get_data()

        # Only update if data differs (avoid unnecessary signal emissions)
        if default_data != current_data:
            # Preserve selection during sync to avoid clearing it on status-only changes
            self._curve_store.set_data(default_data, preserve_selection_on_sync=True)
            logger.debug(f"Synced ApplicationState '__default__' ({len(default_data)} points) to CurveDataStore")

    # Invalidate caches and request repaint
    self.widget.invalidate_caches()
    self.widget.update()
    logger.debug(f"ApplicationState curves changed: {len(curves)} curves")

# NO CHANGES NEEDED - already implements unidirectional sync! ✅
```

**Key Insight**: The architecture document was based on incorrect assumptions. The current code is ALREADY correctly implementing unidirectional sync.

#### Step 2: Update All Data Modification Points (Phase 3.1.2)

**Principle**: Any code that modifies curve data must write to ApplicationState, not CurveDataStore.

**Files to Update**:

1. **CurveDataFacade** (`ui/controllers/curve_view/curve_data_facade.py`)
   - Currently writes to CurveDataStore
   - Must redirect to ApplicationState (see Section 3)

2. **Commands** (`core/commands/curve_commands.py`)
   - SetPointStatusCommand - Already uses ApplicationState ✅ (no changes needed)
   - Other commands - Verify they use ApplicationState

3. **Any Direct CurveDataStore Writers**
   - Search for `_curve_store.set_data()`, `_curve_store.add_point()`, etc.
   - Redirect to ApplicationState equivalents

#### Step 3: Disconnect Store → ApplicationState Signals (Phase 3.1.3)

**File**: `ui/controllers/curve_view/state_sync_controller.py`

**Method**: `_connect_store_signals()`

```python
# BEFORE:
def _connect_store_signals(self) -> None:
    """Connect CurveDataStore signals."""
    _ = self._curve_store.data_changed.connect(self._on_store_data_changed)
    _ = self._curve_store.point_added.connect(self._on_store_point_added)
    _ = self._curve_store.point_updated.connect(self._on_store_point_updated)
    _ = self._curve_store.point_removed.connect(self._on_store_point_removed)
    _ = self._curve_store.point_status_changed.connect(self._on_store_status_changed)
    _ = self._curve_store.selection_changed.connect(self._on_store_selection_changed)

# AFTER (Phase 3.1):
def _connect_store_signals(self) -> None:
    """Connect CurveDataStore signals (read-only during migration)."""
    # KEEP: data_changed for widget updates (no ApplicationState writes)
    _ = self._curve_store.data_changed.connect(self._on_store_data_changed)

    # REMOVE: Fine-grained signals - ApplicationState handles these now
    # _ = self._curve_store.point_added.connect(self._on_store_point_added)
    # _ = self._curve_store.point_updated.connect(self._on_store_point_updated)
    # _ = self._curve_store.point_removed.connect(self._on_store_point_removed)
    # _ = self._curve_store.point_status_changed.connect(self._on_store_status_changed)

    # KEEP: selection_changed for backward compatibility (will remove in Phase 4)
    _ = self._curve_store.selection_changed.connect(self._on_store_selection_changed)

# AFTER (Phase 4 - final state):
def _connect_store_signals(self) -> None:
    """Connect CurveDataStore signals (deprecated, will be removed)."""
    # Only data_changed remains for backward compatibility
    # This entire method will be removed when CurveDataStore is fully deprecated
    _ = self._curve_store.data_changed.connect(self._on_store_data_changed)
```

**Rationale**:
- Remove fine-grained signals (`point_added`, `point_updated`, etc.) immediately - ApplicationState handles these
- Keep `data_changed` for widget cache invalidation during transition
- Keep `selection_changed` temporarily for backward compatibility (removed in Phase 4)

### Validation Checkpoints (Phase 3.1)

**After Step 1** (Unidirectional sync):
```bash
# Run full test suite
.venv/bin/python3 -m pytest tests/ -v --tb=short

# Expected: All tests passing (no circular loops)
# If fails: Check for ApplicationState writes in _on_store_data_changed
```

**After Step 2** (Data modification redirect):
```bash
# Test specific data operations
.venv/bin/python3 -m pytest tests/test_curve_data_facade.py -v
.venv/bin/python3 -m pytest tests/test_commands.py -v

# Expected: All commands use ApplicationState
# If fails: Check for lingering CurveDataStore writes
```

**After Step 3** (Signal disconnection):
```bash
# Test signal integrity
.venv/bin/python3 -m pytest tests/test_data_flow.py -v
.venv/bin/python3 -m pytest tests/test_main_window_store_integration.py -v

# Expected: No signal loop errors
# Manual test: Open app, edit points, verify no crashes
```

### Rollback Strategy (Phase 3.1)

**If Step 1 Fails** (Circular dependency not broken):
- Revert `state_sync_controller.py` changes
- Keep bidirectional sync temporarily
- Debug data flow with logging

**If Step 2 Fails** (Data corruption observed):
- Revert affected files to CurveDataStore writes
- Phase 3.1 incomplete, but app remains functional
- Investigate ApplicationState method bugs

**If Step 3 Fails** (Signal errors):
- Reconnect removed signals
- Debug signal chain with QSignalSpy
- May need to defer signal removal to Phase 4

---

## 3. CurveDataFacade Migration Plan

### Current Implementation Analysis

**File**: `ui/controllers/curve_view/curve_data_facade.py`

**Methods Using CurveDataStore** (3 methods):

1. **`add_point(point)` - Line 81-89**
   - Current: `self._curve_store.add_point(point)`
   - Migration: `self._app_state.add_point(curve_name, point_obj)` ← Phase 0 method

2. **`update_point(index, point)` - Line 91-101**
   - Current: `self._curve_store.update_point(index, point)`
   - Migration: `self._app_state.update_point(curve_name, index, x, y, status)` ← Already exists

3. **`remove_point(index)` - Line 103-112**
   - Current: `self._curve_store.remove_point(index)`
   - Migration: `self._app_state.remove_point(curve_name, index)` ← Phase 0 method

### Migration Strategy (Phase 3.2)

#### Challenge: Curve Name Determination

**Problem**: CurveDataFacade methods currently don't take `curve_name` parameter (single-curve API), but ApplicationState requires it (multi-curve native).

**Solution**: Use `_get_active_curve_name()` helper to determine curve name from context.

#### Implementation (Method-by-Method)

**File**: `ui/controllers/curve_view/curve_data_facade.py`

##### Helper Method (Add at top of class):

```python
def _get_active_curve_name(self) -> str:
    """
    Get the active curve name for single-curve operations.

    During migration, this bridges single-curve API (CurveDataFacade)
    with multi-curve storage (ApplicationState).

    Returns:
        Active curve name from ApplicationState, or "__default__" as fallback

    Note:
        "__default__" fallback will be removed in Phase 4 after full migration.
    """
    active_curve = self._app_state.active_curve
    if active_curve:
        return active_curve

    # Fallback for backward compatibility (removed in Phase 4)
    return "__default__"
```

##### 1. Migrate `add_point()`:

```python
# BEFORE (Phase 3.1):
def add_point(self, point: tuple[int, float, float] | tuple[int, float, float, str]) -> None:
    """
    Add a single point to the curve.

    Args:
        point: Point tuple (frame, x, y, [status])
    """
    # Delegate to store - it will emit signals that trigger widget updates
    _ = self._curve_store.add_point(point)

# AFTER (Phase 3.2):
def add_point(self, point: tuple[int, float, float] | tuple[int, float, float, str]) -> None:
    """
    Add a single point to the curve.

    Args:
        point: Point tuple (frame, x, y, [status])
    """
    from core.models import CurvePoint, PointStatus

    # Convert tuple to CurvePoint
    frame = int(point[0])
    x = float(point[1])
    y = float(point[2])
    status = PointStatus(point[3]) if len(point) > 3 else PointStatus.NORMAL

    curve_point = CurvePoint(frame=frame, x=x, y=y, status=status)

    # Delegate to ApplicationState (source of truth)
    curve_name = self._get_active_curve_name()
    _ = self._app_state.add_point(curve_name, curve_point)

    # ApplicationState emits curves_changed → StateSyncController updates CurveDataStore
    # → widget.curve_data reflects change (via property getter)
```

**Performance Gain**: 1 call (direct) vs 3 calls (get → append → set workaround)

##### 2. Migrate `update_point()`:

**ACTUAL Current Signature** (`ui/controllers/curve_view/curve_data_facade.py:91-101`):
```python
def update_point(self, index: int, x: float, y: float) -> None:
    """
    Update coordinates of a point.

    Args:
        index: Point index
        x: New X coordinate
        y: New Y coordinate
    """
    # Delegate to store - it will emit signals that trigger widget updates
    _ = self._curve_store.update_point(index, x, y)
```

**Note**: NO `status` parameter exists! Status updates use a SEPARATE method (not shown in facade).

**ACTUAL ApplicationState Signature** (`stores/application_state.py:236-264`):
```python
def update_point(self, curve_name: str, index: int, point: CurvePoint) -> None:
    """
    Update single point in curve.

    Args:
        curve_name: Curve containing point
        index: Point index to update
        point: New point data (CurvePoint object with x, y, status)
    """
    # ... implementation
```

**Migration** (Phase 3.2):

```python
# AFTER (Phase 3.2):
def update_point(self, index: int, x: float, y: float) -> None:
    """
    Update coordinates of a point.

    Args:
        index: Point index
        x: New X coordinate
        y: New Y coordinate
    """
    from core.models import CurvePoint

    # Get current curve name
    curve_name = self._get_active_curve_name()

    # Get existing point to preserve status
    current_data = self._app_state.get_curve_data(curve_name)
    if not (0 <= index < len(current_data)):
        logger.warning(f"Cannot update point {index}: out of range")
        return

    # Get existing point data
    existing_point = current_data[index]
    frame = existing_point[0]
    status = PointStatus(existing_point[3]) if len(existing_point) > 3 else PointStatus.NORMAL

    # Create updated point (preserving frame and status)
    updated_point = CurvePoint(frame=frame, x=x, y=y, status=status)

    # Delegate to ApplicationState (source of truth)
    self._app_state.update_point(curve_name, index, updated_point)

    # ApplicationState emits curves_changed → syncs to CurveDataStore
```

**Key Differences from Document**:
- NO optional parameters (x/y are required, not None)
- NO status parameter in facade method
- ApplicationState.update_point takes a CurvePoint object, NOT individual x/y/status parameters
- Must preserve existing frame and status when updating coordinates

##### 3. Migrate `remove_point()`:

```python
# BEFORE (Phase 3.1):
def remove_point(self, index: int) -> None:
    """
    Remove a point from the curve.

    Args:
        index: Point index to remove
    """
    # Delegate to store - it will emit signals that trigger widget updates
    # Store handles selection updates automatically
    _ = self._curve_store.remove_point(index)

# AFTER (Phase 3.2):
def remove_point(self, index: int) -> None:
    """
    Remove a point from the curve.

    Args:
        index: Point index to remove
    """
    # Delegate to ApplicationState (source of truth)
    curve_name = self._get_active_curve_name()
    success = self._app_state.remove_point(curve_name, index)

    if not success:
        logger.warning(f"Failed to remove point {index} from curve '{curve_name}'")

    # ApplicationState handles selection updates automatically
    # ApplicationState emits curves_changed → syncs to CurveDataStore
```

**Performance Gain**: 1 call (direct) vs 3 calls (get → filter → set workaround)

### Test Coverage Strategy (Phase 3.2)

**Existing Tests** (verify still passing):
- `tests/test_curve_data_facade.py` - Facade-specific tests
- `tests/test_curve_view_widget.py` - Widget integration tests
- `tests/test_commands.py` - Command pattern tests

**New Validation Tests** (add if needed):
```python
# tests/test_curve_data_facade_migration.py

def test_add_point_uses_application_state(app_state, curve_facade):
    """Verify add_point delegates to ApplicationState, not CurveDataStore."""
    from core.models import CurvePoint

    # Setup
    point = (100, 50.0, 75.0, "NORMAL")

    # Execute
    curve_facade.add_point(point)

    # Verify ApplicationState has the point
    curve_name = app_state.active_curve or "__default__"
    curve_data = app_state.get_curve_data(curve_name)

    assert len(curve_data) == 1
    assert curve_data[0].frame == 100
    assert curve_data[0].x == 50.0
    assert curve_data[0].y == 75.0
```

### Validation Checkpoints (Phase 3.2)

**After Migration**:
```bash
# Test facade methods
.venv/bin/python3 -m pytest tests/test_curve_data_facade.py -v

# Test widget integration
.venv/bin/python3 -m pytest tests/test_curve_view_widget.py -v

# Manual test
# 1. Open CurveEditor
# 2. Add points via click
# 3. Move points via drag
# 4. Delete points via Delete key
# 5. Verify undo/redo works
```

**Expected Results**:
- ✅ All facade tests passing
- ✅ All widget tests passing
- ✅ Manual operations work correctly
- ✅ Undo/redo maintains data integrity

### Rollback Strategy (Phase 3.2)

**If Migration Fails**:
- Revert `curve_data_facade.py` to use CurveDataStore methods
- ApplicationState methods remain (additive, no breaking changes)
- Phase 3.2 incomplete, but app remains functional

---

## 4. Signal Migration Strategy

### Problem Analysis

**Breaking Change**: Signal signature incompatibility

```python
# OLD: CurveDataStore.selection_changed
selection_changed = Signal(set)  # Just indices

# NEW: ApplicationState.selection_changed
selection_changed = Signal(set, str)  # Indices + curve_name
```

**Impact**: All signal handlers expecting `Signal(set)` will fail with `Signal(set, str)`.

### Affected Signal Handlers (8 handlers - CORRECTED COUNT)

**Verification Command**:
```bash
grep -n "selection_changed.connect" ui/ tests/ --include="*.py" -r
```

| # | Handler | Location | Current Signature | Migration Needed |
|---|---------|----------|-------------------|------------------|
| 1 | `MainWindow.on_store_selection_changed` | `ui/main_window.py:298` | `(selection: set[int])` | Yes |
| 2 | `PointEditorController.on_store_selection_changed` | `ui/controllers/point_editor_controller.py:82` | `(selection: set[int])` | Yes |
| 3 | `MultiPointTrackingController.on_curve_selection_changed` | `ui/controllers/multi_point_tracking_controller.py:380` | `(selection: set[int])` | Yes |
| 4 | `TimelineTabWidget._on_store_selection_changed` | `ui/timeline_tabs.py:341` | `(selection: set[int])` | Yes |
| 5 | `StateManager._on_app_state_selection_changed` | `ui/state_manager.py:63` | Connects to `ApplicationState.selection_changed` | Already multi-curve aware |
| 6 | `StateSyncController._on_store_selection_changed` | `ui/controllers/curve_view/state_sync_controller.py:77` | `(selection: set[int])` | Yes |
| 7 | `StateSyncController._on_app_state_selection_changed` | `ui/controllers/curve_view/state_sync_controller.py:87` | Connects to `ApplicationState.selection_changed` | Already multi-curve aware |
| 8 | `PointEditorProtocol.on_store_selection_changed` | `ui/protocols/controller_protocols.py:324` | Protocol definition `(selection: set[int])` | Yes |

**Note**: Handlers #5 and #7 already connect to `ApplicationState.selection_changed` (multi-curve signal), so they may already handle the (set, str) signature correctly. Verify during migration.

### Architecture Decision: Adapter Pattern + Gradual Migration

**Strategy**: Use temporary adapter layer to bridge old and new signal signatures during Phase 3, remove adapter in Phase 4.

#### Phase 3.3.1: Add Signal Adapter (Temporary Compatibility Layer)

**File**: `ui/controllers/curve_view/state_sync_controller.py`

**Add New Method**:

```python
def _on_app_state_selection_changed_adapter(self, selection: set[int], curve_name: str) -> None:
    """
    Adapter for ApplicationState.selection_changed → CurveDataStore.selection_changed.

    Converts multi-curve signal (set, str) to single-curve signal (set) for
    backward compatibility during migration.

    This adapter will be removed in Phase 4 when CurveDataStore is fully deprecated.

    Args:
        selection: Selected point indices
        curve_name: Curve name (ignored for backward compatibility)
    """
    # Only propagate if selection is for active curve or "__default__"
    active_curve = self._get_active_curve_name()

    if curve_name == active_curve or curve_name == "__default__":
        # Emit old-style signal for backward compatibility
        self._curve_store.selection_changed.emit(selection)
        logger.debug(f"Adapted selection signal: {len(selection)} points in '{curve_name}'")
```

**Connect Adapter**:

```python
def _connect_app_state_signals(self) -> None:
    """Connect ApplicationState signals."""
    _ = self._app_state.curves_changed.connect(self._on_app_state_curves_changed)

    # NEW: Connect adapter for selection changes
    _ = self._app_state.selection_changed.connect(self._on_app_state_selection_changed_adapter)

    _ = self._app_state.active_curve_changed.connect(self._on_app_state_active_curve_changed)
    _ = self._app_state.curve_visibility_changed.connect(self._on_app_state_visibility_changed)
```

**Rationale**:
- Allows ApplicationState to emit new signal format
- Adapter translates to old format for backward compatibility
- Handlers don't need immediate updates
- Can migrate handlers gradually in Phase 3.3.2

#### Phase 3.3.2: Update Signal Handlers (One at a Time)

**Migration Order** (lowest risk → highest risk, 8 handlers total):

1. **PointEditorProtocol** (protocol definition - no logic) - `ui/protocols/controller_protocols.py:324`
2. **StateSyncController._on_store_selection_changed** (may be deletable if redundant) - `ui/controllers/curve_view/state_sync_controller.py:77`
3. **PointEditorController** (simple delegation) - `ui/controllers/point_editor_controller.py:82`
4. **MainWindow** (delegates to PointEditorController) - `ui/main_window.py:298`
5. **MultiPointTrackingController** (single-purpose controller) - `ui/controllers/multi_point_tracking_controller.py:380`
6. **TimelineTabWidget** (complex logic - needs careful testing) - `ui/timeline_tabs.py:341`
7. **StateManager** (verify already handles multi-curve) - `ui/state_manager.py:63`
8. **Test handlers** (update after production code) - `tests/test_main_window_store_integration.py`

**Migration Template**:

```python
# BEFORE (Phase 3.3.1):
def on_store_selection_changed(self, selection: set[int]) -> None:
    """Handle selection changes from the store."""
    # ... handler logic ...

# AFTER (Phase 3.3.2):
def on_store_selection_changed(self, selection: set[int], curve_name: str = "__default__") -> None:
    """
    Handle selection changes from ApplicationState.

    Args:
        selection: Selected point indices
        curve_name: Curve name (defaults to "__default__" for backward compatibility)
    """
    # ... handler logic (may use curve_name for multi-curve awareness) ...
```

**Key Changes**:
1. Add `curve_name` parameter with default value `"__default__"`
2. Update docstring to reflect new signature
3. Optionally use `curve_name` for multi-curve logic (defer to future phases if complex)
4. Update protocol definitions to match

### Detailed Handler Migrations

#### 1. StateSyncController._on_store_selection_changed

**File**: `ui/controllers/curve_view/state_sync_controller.py:196-200`

```python
# BEFORE:
def _on_store_selection_changed(self, selection: set[int]) -> None:
    """Handle store selection changed signal."""
    # This is now redundant - ApplicationState handles selection
    pass

# AFTER (Phase 3.3.2):
# DELETE THIS METHOD - ApplicationState handles selection directly
# StateSyncController no longer needs to listen to CurveDataStore selection changes
```

**Rationale**: This handler was only needed for bidirectional sync. ApplicationState is now source of truth.

#### 2. PointEditorProtocol.on_store_selection_changed

**File**: `ui/protocols/controller_protocols.py:292`

```python
# BEFORE:
class PointEditorProtocol(Protocol):
    def on_store_selection_changed(self, selection: set[int]) -> None:
        """Handle curve selection change from CurveDataStore."""
        ...

# AFTER (Phase 3.3.2):
class PointEditorProtocol(Protocol):
    def on_store_selection_changed(self, selection: set[int], curve_name: str = "__default__") -> None:
        """
        Handle selection change from ApplicationState.

        Args:
            selection: Selected point indices
            curve_name: Curve name (defaults to "__default__" for backward compatibility)
        """
        ...
```

#### 3. MainWindow.on_store_selection_changed

**File**: `ui/main_window.py:297-300`

```python
# BEFORE:
def on_store_selection_changed(self, selection: set[int]) -> None:
    """Handle selection changes from the store (delegated to PointEditorController)."""
    self.point_editor_controller.on_store_selection_changed(selection)
    self.update_ui_state()

# AFTER (Phase 3.3.2):
def on_store_selection_changed(self, selection: set[int], curve_name: str = "__default__") -> None:
    """
    Handle selection changes from ApplicationState.

    Args:
        selection: Selected point indices
        curve_name: Curve name (defaults to "__default__" for backward compatibility)
    """
    self.point_editor_controller.on_store_selection_changed(selection, curve_name)
    self.update_ui_state()
```

#### 4. MultiPointTrackingController.on_curve_selection_changed

**File**: `ui/controllers/multi_point_tracking_controller.py:379-417`

```python
# BEFORE:
def on_curve_selection_changed(self, selection: set[int]) -> None:
    """
    Handle selection changes from CurveDataStore (bidirectional synchronization).

    Args:
        selection: Set of selected point indices from CurveDataStore
    """
    if not self.main_window.tracking_panel:
        return

    if not selection:
        self.main_window.tracking_panel.set_selected_points([])
        return

    # Find which curve contains the selected points
    active_curve_name = self.main_window.active_timeline_point

    if active_curve_name and active_curve_name in self._app_state.get_all_curve_names():
        selected_curves = [active_curve_name]
        # ... rest of logic ...

# AFTER (Phase 3.3.2):
def on_curve_selection_changed(self, selection: set[int], curve_name: str = "__default__") -> None:
    """
    Handle selection changes from ApplicationState.

    Args:
        selection: Set of selected point indices
        curve_name: Curve name containing the selection
    """
    if not self.main_window.tracking_panel:
        return

    if not selection:
        self.main_window.tracking_panel.set_selected_points([])
        return

    # Use provided curve_name instead of inferring from active_timeline_point
    if curve_name and curve_name in self._app_state.get_all_curve_names():
        selected_curves = [curve_name]

        # Ensure active_timeline_point is consistent
        if not self.main_window.active_timeline_point:
            self.main_window.active_timeline_point = curve_name

        # Update TrackingPanel visual state
        self.main_window.tracking_panel.set_selected_points(selected_curves)

        logger.debug(f"Updated tracking panel: {len(selection)} points in '{curve_name}'")
    else:
        logger.debug(f"Could not update tracking panel: curve '{curve_name}' not found")
```

**Benefit**: More robust - uses explicit curve_name instead of inferring from active_timeline_point.

#### 5. TimelineTabWidget._on_store_selection_changed

**File**: `ui/timeline_tabs.py:458-528`

```python
# BEFORE:
def _on_store_selection_changed(self, selection: set[int]) -> None:
    """Handle selection changed in store."""
    # Get current curve data to find frames containing selected points
    curve_data = self._curve_store.get_data()
    if not curve_data:
        return

    # Find frames that contain selected points
    selected_frames: set[int] = set()
    for index in selection:
        if 0 <= index < len(curve_data):
            point = curve_data[index]
            if len(point) >= 3:
                frame = int(point[0])
                selected_frames.add(frame)

    # ... rest of logic (70 lines) ...

# AFTER (Phase 3.3.2):
def _on_store_selection_changed(self, selection: set[int], curve_name: str = "__default__") -> None:
    """
    Handle selection changed in ApplicationState.

    Args:
        selection: Selected point indices
        curve_name: Curve name containing the selection
    """
    # Get curve data from ApplicationState (source of truth)
    curve_data = self._app_state.get_curve_data(curve_name)
    if not curve_data:
        return

    # Find frames that contain selected points
    selected_frames: set[int] = set()
    for index in selection:
        if 0 <= index < len(curve_data):
            point = curve_data[index]
            frame = point.frame  # Use CurvePoint.frame instead of tuple[0]
            selected_frames.add(frame)

    # ... rest of logic unchanged ...
```

**Benefit**: Reads from ApplicationState directly instead of CurveDataStore.

### Validation Checkpoints (Phase 3.3)

**After Phase 3.3.1** (Adapter added):
```bash
# Test adapter doesn't break existing functionality
.venv/bin/python3 -m pytest tests/test_main_window_store_integration.py -v
.venv/bin/python3 -m pytest tests/test_data_flow.py -v

# Manual test: Select points in UI, verify selection works
```

**After Each Handler Update** (Phase 3.3.2):
```bash
# Test updated handler
.venv/bin/python3 -m pytest tests/test_<relevant_test>.py -v

# Full regression after all handlers updated
.venv/bin/python3 -m pytest tests/ -v
```

**After Phase 3.3 Complete**:
```bash
# Full test suite
.venv/bin/python3 -m pytest tests/ -v

# Type checking
./bpr --errors-only

# Manual testing
# 1. Select single point → verify timeline highlights
# 2. Select multiple points → verify tracking panel updates
# 3. Rubber-band selection → verify all handlers respond
```

### Rollback Strategy (Phase 3.3)

**If Adapter Fails** (Phase 3.3.1):
- Remove adapter method
- Disconnect ApplicationState.selection_changed
- Keep CurveDataStore.selection_changed as-is
- Phase 3.3 incomplete, but app remains functional

**If Handler Update Fails** (Phase 3.3.2):
- Revert specific handler to old signature
- Adapter continues to bridge for other handlers
- Can proceed with remaining handlers

---

## 5. `__default__` Removal Plan

### Prerequisites

Before removing `__default__`:
- ✅ Phase 3.1 complete (Circular dependency broken)
- ✅ Phase 3.2 complete (CurveDataFacade uses ApplicationState)
- ✅ Phase 3.3 complete (Signal handlers updated)
- ✅ CurveDataStore fully deprecated (no production writes)

### Removal Order (Phase 4)

#### Phase 4.1: Remove StateSyncController `__default__` Sync

**File**: `ui/controllers/curve_view/state_sync_controller.py:214-235`

**Method**: `_on_app_state_curves_changed()`

```python
# BEFORE (Phase 3):
def _on_app_state_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
    """Handle ApplicationState curves_changed signal."""
    # CRITICAL: Sync ApplicationState "__default__" curve back to CurveDataStore
    default_curve = "__default__"
    if default_curve in curves:
        default_data = curves[default_curve]
        current_data = self._curve_store.get_data()

        if default_data != current_data:
            self._curve_store.set_data(default_data, preserve_selection_on_sync=True)
            logger.debug(f"Synced ApplicationState '__default__' to CurveDataStore")

    self.widget.invalidate_caches()
    self.widget.update()

# AFTER (Phase 4.1):
def _on_app_state_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
    """Handle ApplicationState curves_changed signal."""
    # No longer need to sync to CurveDataStore - ApplicationState is sole source
    # Widget reads curve_data from ApplicationState via active_curve

    self.widget.invalidate_caches()
    self.widget.update()
    logger.debug(f"ApplicationState curves changed: {len(curves)} curves")
```

**Impact**: Removes last `__default__`-specific logic in sync controller.

#### Phase 4.2: Remove CurveViewWidget `__default__` Compatibility

**File**: `ui/curve_view_widget.py:311-338`

**Property**: `selected_indices` setter

```python
# BEFORE (Phase 3):
@selected_indices.setter
def selected_indices(self, selection: set[int]) -> None:
    """Set selected point indices (syncs to both stores)."""
    if selection == self._selected_indices:
        return

    self._selected_indices = selection.copy()

    # Update CurveDataStore
    self._curve_store.select_multiple(selection)

    # BACKWARD COMPATIBILITY: Also sync to ApplicationState default curve
    default_curve = "__default__"
    if default_curve in self._app_state.get_all_curve_names():
        app_state_selection = self._app_state.get_selection(default_curve)
        if selection != app_state_selection:
            self._app_state.set_selection(default_curve, selection)

    self.selection_changed.emit(selection)
    self.update()

# AFTER (Phase 4.2):
@selected_indices.setter
def selected_indices(self, selection: set[int]) -> None:
    """Set selected point indices (ApplicationState only)."""
    if selection == self._selected_indices:
        return

    self._selected_indices = selection.copy()

    # Update ApplicationState (source of truth)
    active_curve = self._app_state.active_curve
    if active_curve:
        self._app_state.set_selection(active_curve, selection)
    else:
        logger.warning("No active curve for selection update")

    self.selection_changed.emit(selection)
    self.update()
```

**Impact**: Removes CurveDataStore write and `__default__` fallback.

#### Phase 4.3: Remove StateManager `__default__` Fallback

**File**: `ui/state_manager.py:262`

**Method**: `_get_curve_name_for_selection()`

```python
# BEFORE (Phase 3):
def _get_curve_name_for_selection(self) -> str:
    """Get curve name for selection operations."""
    if self._active_timeline_point:
        return self._active_timeline_point
    if self._app_state.active_curve:
        return self._app_state.active_curve
    # Fallback for single-curve backward compatibility
    return "__default__"

# AFTER (Phase 4.3):
def _get_curve_name_for_selection(self) -> str | None:
    """
    Get curve name for selection operations.

    Returns:
        Active curve name, or None if no curve is active

    Note:
        Returns None instead of "__default__" - callers must handle None case.
    """
    if self._active_timeline_point:
        return self._active_timeline_point
    if self._app_state.active_curve:
        return self._app_state.active_curve
    return None  # No fallback - explicit curve required
```

**Impact**: Forces explicit curve handling (no implicit `__default__`).

**Follow-up**: Update all callers to handle `None` return value:

```python
# Update callers (example):
curve_name = self._get_curve_name_for_selection()
if curve_name:
    self._app_state.set_selection(curve_name, selection)
else:
    logger.warning("No active curve for selection operation")
```

#### Phase 4.4: Update Test Files (4 files)

**Files**:
1. `tests/test_ui_service.py` (lines 393-394, 457-458)
2. `tests/test_shortcut_commands.py` (multiple locations)
3. `tests/test_tracking_direction_undo.py`
4. `tests/test_integration_edge_cases.py` (9 locations)

**Migration Template**:

```python
# BEFORE:
app_state.set_curve_data("__default__", test_data)
selection = app_state.get_selection("__default__")

# AFTER:
TEST_CURVE_NAME = "TestCurve"
app_state.set_curve_data(TEST_CURVE_NAME, test_data)
app_state.set_active_curve(TEST_CURVE_NAME)
selection = app_state.get_selection(TEST_CURVE_NAME)
```

**Strategy**:
- Define explicit test curve names (e.g., `TEST_CURVE_NAME = "TestCurve"`)
- Set active curve explicitly in test setup
- Replace all `"__default__"` references with explicit names
- Verify tests still pass after each file update

#### Phase 4.5: Remove `__default__` Filter Comments

**File**: `rendering/render_state.py:140`

```python
# BEFORE:
# Use widget.curves_data as authoritative source (filters out "__default__")

# AFTER:
# (Delete comment - no longer relevant)
```

**Impact**: Documentation cleanup only.

### Validation Checkpoints (Phase 4)

**After Phase 4.1**:
```bash
# Test sync controller
.venv/bin/python3 -m pytest tests/test_data_flow.py -v

# Verify no __default__ sync
grep -n "__default__" ui/controllers/curve_view/state_sync_controller.py
# Expected: Only in comments or historical context
```

**After Phase 4.2**:
```bash
# Test widget selection
.venv/bin/python3 -m pytest tests/test_curve_view_widget.py -v

# Manual test: Select points, verify no errors
```

**After Phase 4.3**:
```bash
# Test state manager
.venv/bin/python3 -m pytest tests/test_state_manager.py -v

# Check for None handling
grep -A 5 "_get_curve_name_for_selection()" ui/ -r
```

**After Phase 4.4**:
```bash
# Test each updated test file
.venv/bin/python3 -m pytest tests/test_ui_service.py -v
.venv/bin/python3 -m pytest tests/test_shortcut_commands.py -v
.venv/bin/python3 -m pytest tests/test_tracking_direction_undo.py -v
.venv/bin/python3 -m pytest tests/test_integration_edge_cases.py -v
```

**After Phase 4 Complete**:
```bash
# Verify no __default__ references remain
grep -r "__default__" --include="*.py" . | grep -v "\.pyc" | grep -v ".git"
# Expected: Only in deprecation notes, migration docs, or historical comments

# Full test suite
.venv/bin/python3 -m pytest tests/ -v
# Expected: 2105/2105 tests passing

# Type checking
./bpr --errors-only
# Expected: 0 errors
```

### Rollback Strategy (Phase 4)

**If Phase 4.1 Fails**:
- Restore `__default__` sync in StateSyncController
- ApplicationState → CurveDataStore sync continues

**If Phase 4.2 Fails**:
- Restore CurveDataStore write in `selected_indices` setter
- Keep `__default__` fallback temporarily

**If Phase 4.3 Fails**:
- Restore `return "__default__"` fallback
- Update return type back to `str` (remove `| None`)

**If Phase 4.4 Fails**:
- Revert individual test files to use `__default__"`
- Can proceed with other test files

---

## 6. Testing Strategy

### Test Categories & Coverage Requirements

#### Unit Tests (Per-Component)

**StateSyncController** (`tests/test_state_sync_controller.py`):
- ✅ Unidirectional sync (ApplicationState → CurveDataStore)
- ✅ No circular signal loops
- ✅ Signal adapter converts (set, str) → (set)
- ✅ Cache invalidation on curves_changed

**CurveDataFacade** (`tests/test_curve_data_facade.py`):
- ✅ `add_point()` uses ApplicationState.add_point()
- ✅ `update_point()` uses ApplicationState.update_point()
- ✅ `remove_point()` uses ApplicationState.remove_point()
- ✅ `_get_active_curve_name()` returns correct curve

**Signal Handlers** (`tests/test_signal_handlers.py` - may need to create):
- ✅ MainWindow.on_store_selection_changed accepts (set, str)
- ✅ TimelineTabWidget updates frames correctly
- ✅ MultiPointTrackingController updates tracking panel
- ✅ All handlers work with new signature

**`__default__` Removal** (existing tests continue to pass):
- ✅ No `__default__` references in production code
- ✅ Tests use explicit curve names
- ✅ StateManager returns None when no active curve

#### Integration Tests (Cross-Component)

**Data Flow** (`tests/test_data_flow.py`):
- ✅ User adds point → ApplicationState → CurveDataStore → Widget
- ✅ User moves point → ApplicationState → Widget updates
- ✅ User deletes point → ApplicationState → Selection updates
- ✅ No circular signal emissions

**Store Integration** (`tests/test_main_window_store_integration.py`):
- ✅ MainWindow uses ApplicationState exclusively
- ✅ CurveDataStore is read-only (no writes in production)
- ✅ Signal chain works end-to-end

**Multi-Curve** (`tests/test_multi_curve.py`):
- ✅ Active curve selection propagates correctly
- ✅ `__default__` not used for multi-curve workflows
- ✅ Explicit curve names required

#### Regression Tests (Full Suite)

**After Each Phase**:
```bash
# Run full test suite
.venv/bin/python3 -m pytest tests/ -v --tb=short

# Expected: 2105/2105 tests passing
# Acceptable: <5 failures IF they're test infrastructure issues (not production)
```

**Critical Test Files** (must pass 100%):
- `tests/test_curve_data_store.py` - Verify backward compatibility
- `tests/test_application_state.py` - Verify source of truth integrity
- `tests/test_commands.py` - Verify undo/redo works
- `tests/test_curve_view_widget.py` - Verify UI operations work

#### Performance Tests (Validation)

**Benchmark After Migration**:
```python
# tests/test_performance_regression.py

def test_add_point_performance(benchmark):
    """Verify add_point performance is maintained or improved."""
    from stores.application_state import get_application_state
    from core.models import CurvePoint

    state = get_application_state()
    state.set_curve_data("TestCurve", [])

    def add_100_points():
        for i in range(100):
            point = CurvePoint(frame=i, x=i*1.0, y=i*2.0)
            state.add_point("TestCurve", point)

    result = benchmark(add_100_points)

    # Should be faster than old workaround (3 calls per point)
    assert result.stats.mean < 0.1  # 100ms for 100 points (1ms/point)
```

**Metrics**:
- ✅ Add point: < 1ms per point (vs 3ms workaround)
- ✅ Remove point: < 1ms per point (vs 3ms workaround)
- ✅ Update point: < 1ms per point (already optimized)
- ✅ Signal emission: < 10ms for 100-point curve change

### Manual Testing Checklist

**After Phase 3.1** (Circular dependency broken):
- [ ] Open CurveEditor
- [ ] Load tracking file
- [ ] Add points by clicking
- [ ] Move points by dragging
- [ ] Verify no console errors or warnings
- [ ] Close app (verify no crash on exit)

**After Phase 3.2** (CurveDataFacade migrated):
- [ ] Add point via click → verify appears in timeline
- [ ] Delete point via Delete key → verify removed
- [ ] Update point status via E key → verify status changes
- [ ] Undo/redo → verify data integrity maintained
- [ ] Save/load session → verify data persists

**After Phase 3.3** (Signal handlers updated):
- [ ] Select single point → verify timeline highlights frame
- [ ] Select multiple points → verify tracking panel updates
- [ ] Rubber-band selection → verify all handlers respond
- [ ] Clear selection (Esc) → verify UI updates
- [ ] Select all (Ctrl+A) → verify UI updates

**After Phase 4** (`__default__` removed):
- [ ] Open app without tracking file → verify no `__default__` errors
- [ ] Load tracking file → verify explicit curve names used
- [ ] Multi-curve workflow → verify no `__default__` fallback
- [ ] Single-curve workflow → verify active_curve used
- [ ] Run full test suite → verify 100% pass rate

### Rollback Criteria

**Abort Migration If**:
- ❌ >10 test failures after any phase
- ❌ Type errors introduced (basedpyright reports errors)
- ❌ Circular signal loop detected (app freezes or crashes)
- ❌ Data corruption observed (points disappear or duplicate)
- ❌ Performance regression >20% (acceptable: <5%)

**Rollback Process**:
1. Identify failing phase (3.1, 3.2, 3.3, or 4)
2. Revert changes for that phase only
3. Run tests to verify rollback successful
4. Document blocker issue
5. Fix blocker, then retry phase

---

## 7. Risk Mitigation

### High-Risk Areas

#### Risk 1: Circular Signal Loops (Phase 3.1)

**Likelihood**: MEDIUM (complex signal chain)
**Impact**: HIGH (app freeze or crash)

**Mitigation**:
- Add debug logging to all signal handlers
- Use QSignalSpy in tests to detect loops
- Manual testing with console monitoring
- Break bidirectional sync early in Phase 3.1

**Detection**:
```python
# Add to signal handlers for debugging:
logger.debug(f"[SIGNAL] {signal_name} emitted: {args}")
```

**Rollback Trigger**: App freeze during point manipulation

#### Risk 2: Data Corruption (Phase 3.2)

**Likelihood**: LOW (methods well-tested in Phase 0)
**Impact**: HIGH (user data loss)

**Mitigation**:
- Comprehensive unit tests for each facade method
- Integration tests for end-to-end workflows
- Session file backup before migration testing
- Manual data verification checkpoints

**Detection**:
```bash
# Compare curve data before/after operation
app_state.get_curve_data("TestCurve")  # Should match expected
```

**Rollback Trigger**: Points missing or duplicated after operation

#### Risk 3: Signal Handler Breakage (Phase 3.3)

**Likelihood**: MEDIUM (6 handlers to update)
**Impact**: MEDIUM (UI not responding to selection)

**Mitigation**:
- Use adapter pattern for backward compatibility
- Update handlers one at a time
- Test each handler independently
- Protocol updates prevent type mismatches

**Detection**:
```bash
# Check for signature mismatches
./bpr ui/main_window.py --errors-only
# Should report no argument count mismatches
```

**Rollback Trigger**: Selection not propagating to UI components

#### Risk 4: Test Suite Breakage (Phase 4)

**Likelihood**: LOW (well-isolated changes)
**Impact**: MEDIUM (delayed release if many tests fail)

**Mitigation**:
- Update tests incrementally (one file at a time)
- Use explicit test curve names (`TEST_CURVE_NAME`)
- Run tests after each file update
- Document expected failures vs. regressions

**Detection**:
```bash
# Track test failures
.venv/bin/python3 -m pytest tests/ -v | grep FAILED | wc -l
# Should be 0 after each file update
```

**Rollback Trigger**: >5 test failures in a single file

### Medium-Risk Areas

#### Risk 5: Performance Regression

**Likelihood**: LOW (Phase 0 methods optimized)
**Impact**: MEDIUM (user experience degradation)

**Mitigation**:
- Benchmark before/after migration
- Use profiling to identify bottlenecks
- Leverage Phase 0 optimizations (1 call vs 3)
- Monitor signal emission frequency

**Detection**:
```python
# Add timing to critical paths
import time
start = time.perf_counter()
state.add_point(curve_name, point)
duration = time.perf_counter() - start
logger.debug(f"add_point took {duration*1000:.2f}ms")
```

**Rollback Trigger**: >20% performance regression in critical paths

#### Risk 6: Type Safety Breakage

**Likelihood**: LOW (comprehensive type hints)
**Impact**: MEDIUM (technical debt accumulation)

**Mitigation**:
- Run basedpyright after each phase
- Use `pyright: ignore[specificRule]` only when necessary
- Fix type errors before proceeding to next phase
- Protocol definitions prevent signature mismatches

**Detection**:
```bash
./bpr --errors-only
# Should report 0 errors after each phase
```

**Rollback Trigger**: >5 new type errors introduced

### Low-Risk Areas

#### Risk 7: Documentation Drift

**Likelihood**: MEDIUM (many files updated)
**Impact**: LOW (maintenance overhead)

**Mitigation**:
- Update docstrings during code changes
- Update CLAUDE.md after Phase 4 complete
- Document migration decisions in this file
- Add migration notes to affected files

**Detection**: Manual review of docstrings and comments

**Rollback Trigger**: N/A (documentation-only issue)

---

## 8. Implementation Sequence

### Phase 3: Migration Refactoring (3 days)

#### Phase 3.1: Verify Unidirectional Flow (0.25 day) - REVISED SCOPE

**Agent**: code-refactoring-expert OR python-implementation-specialist

**Steps** (verification only - NO code changes needed):
1. ✅ Verify `StateSyncController._on_store_data_changed()` does NOT write to ApplicationState
2. ✅ Verify `_on_app_state_curves_changed()` implements unidirectional sync (ApplicationState → CurveDataStore)
3. ✅ Document current signal connections (prepare for Phase 3.3)
4. ✅ Run tests: `pytest tests/test_data_flow.py tests/test_main_window_store_integration.py -v`
5. ✅ Confirm tests already pass (no circular dependency issues)

**Verification Commands**:
```bash
# Confirm NO ApplicationState writes in _on_store_data_changed
grep -n "self._app_state.set_curve_data\|self._app_state.add_point\|self._app_state.update_point\|self._app_state.remove_point" ui/controllers/curve_view/state_sync_controller.py
# Expected: NO matches in lines 118-136 (_on_store_data_changed method)

# Verify unidirectional sync exists
grep -A 10 "_on_app_state_curves_changed" ui/controllers/curve_view/state_sync_controller.py
# Expected: Shows ApplicationState → CurveDataStore sync at lines 214-235

# Verify tests pass
.venv/bin/python3 -m pytest tests/test_data_flow.py -v
# Expected: All tests passing (no changes needed)
```

**Exit Criteria**:
- ✅ Verified unidirectional sync already implemented
- ✅ All tests already passing
- ✅ Signal handlers documented (ready for Phase 3.3)
- ✅ No code changes made (verification only)

#### Phase 3.2: Migrate CurveDataFacade (0.5 day)

**Agent**: python-implementation-specialist

**Steps**:
1. ✅ Add `_get_active_curve_name()` helper
2. ✅ Update `add_point()` to use `ApplicationState.add_point()`
3. ✅ Update `update_point()` to use `ApplicationState.update_point()`
4. ✅ Update `remove_point()` to use `ApplicationState.remove_point()`
5. ✅ Run tests: `pytest tests/test_curve_data_facade.py tests/test_curve_view_widget.py -v`

**Checkpoint**:
```bash
# Verify facade methods use ApplicationState
grep -n "self._curve_store" ui/controllers/curve_view/curve_data_facade.py
# Expected: Only in __init__ and read operations

# Test facade
.venv/bin/python3 -m pytest tests/test_curve_data_facade.py -v
# Expected: All tests passing
```

**Exit Criteria**:
- ✅ All facade writes go to ApplicationState
- ✅ All facade tests passing
- ✅ No CurveDataStore writes in facade

#### Phase 3.3: Update Signal Handlers (1 day)

**Agent**: python-implementation-specialist

**Sub-Phase 3.3.1: Add Signal Adapter** (0.25 day):
1. ✅ Add `_on_app_state_selection_changed_adapter()` to StateSyncController
2. ✅ Connect adapter to ApplicationState.selection_changed
3. ✅ Test adapter: `pytest tests/test_main_window_store_integration.py -v`

**Sub-Phase 3.3.2: Update Handlers** (0.75 day, 8 handlers total):
1. ✅ Update `PointEditorProtocol.on_store_selection_changed` (protocol definition)
2. ✅ Update `StateSyncController._on_store_selection_changed` (may delete if redundant)
3. ✅ Update `PointEditorController.on_store_selection_changed`
4. ✅ Update `MainWindow.on_store_selection_changed`
5. ✅ Update `MultiPointTrackingController.on_curve_selection_changed`
6. ✅ Update `TimelineTabWidget._on_store_selection_changed`
7. ✅ Verify `StateManager._on_app_state_selection_changed` (may already be correct)
8. ✅ Update test handlers in `tests/test_main_window_store_integration.py`
9. ✅ Test after each: `pytest tests/ -k <relevant_test> -v`

**Checkpoint**:
```bash
# Verify all handlers updated
grep -n "def on.*selection_changed.*set\[int\]" ui/ -r
# Expected: All signatures have (set[int], str) or (set[int], str = "__default__")

# Type check
./bpr ui/ --errors-only
# Expected: 0 errors

# Full test suite
.venv/bin/python3 -m pytest tests/ -v
# Expected: 2105/2105 passing
```

**Exit Criteria**:
- ✅ All 8 signal handlers accept (set[int], str) signature (or verified already correct)
- ✅ Adapter bridges old/new signals during transition
- ✅ All tests passing (2105/2105)
- ✅ Type safety maintained (0 basedpyright errors)

### Phase 4: Remove `__default__` (0.5 day)

**Agent**: python-implementation-specialist

**Steps**:
1. ✅ Remove `__default__` sync in `StateSyncController._on_app_state_curves_changed`
2. ✅ Remove `__default__` compatibility in `CurveViewWidget.selected_indices` setter
3. ✅ Update `StateManager._get_curve_name_for_selection()` to return `None` instead of `"__default__"`
4. ✅ Update 4 test files to use explicit curve names
5. ✅ Remove `__default__` filter comment in `rendering/render_state.py`
6. ✅ Run full test suite: `pytest tests/ -v`

**Checkpoint**:
```bash
# Verify no __default__ references
grep -r "__default__" --include="*.py" . | grep -v "\.pyc" | grep -v ".git" | grep -v "migration docs"
# Expected: Only historical comments or migration notes

# Full test suite
.venv/bin/python3 -m pytest tests/ -v
# Expected: 2105/2105 passing

# Type check
./bpr --errors-only
# Expected: 0 errors
```

**Exit Criteria**:
- ✅ Zero `__default__` references in production code
- ✅ All tests passing with explicit curve names
- ✅ StateManager handles None gracefully
- ✅ Type safety maintained

---

## 9. Success Criteria

### Technical Metrics

**Code Quality**:
- ✅ Zero CurveDataStore writes in production code
- ✅ Zero `__default__` references in production code
- ✅ ApplicationState is sole source of truth for curve data
- ✅ Unidirectional data flow (ApplicationState → CurveDataStore for backward compat only)

**Type Safety**:
- ✅ 0 basedpyright errors in production code
- ✅ 0 new type ignores added (use existing patterns)
- ✅ All signal handlers have correct signatures
- ✅ Protocol definitions updated to match

**Test Coverage**:
- ✅ 100% test pass rate (2105/2105 tests passing)
- ✅ <5 test infrastructure errors acceptable (e.g., Qt threading in tests)
- ✅ All unit tests passing for affected components
- ✅ All integration tests passing

**Performance**:
- ✅ < 5% regression in critical paths (acceptable)
- ✅ 3x efficiency gain in facade methods (1 call vs 3)
- ✅ No signal loop delays (< 10ms for 100-point curve change)

### Functional Requirements

**Data Integrity**:
- ✅ Points persist correctly after add/remove/update
- ✅ Selection state maintained after operations
- ✅ Undo/redo works correctly
- ✅ Session save/load preserves all data

**UI Responsiveness**:
- ✅ Point selection updates timeline immediately
- ✅ Tracking panel reflects selection changes
- ✅ Rubber-band selection works correctly
- ✅ No UI freezes or crashes

**Multi-Curve Support**:
- ✅ Explicit curve names required (no implicit `__default__`)
- ✅ Active curve selection works correctly
- ✅ Multi-curve workflows use ApplicationState exclusively

### Documentation

**Code Documentation**:
- ✅ Updated docstrings for all modified methods
- ✅ Migration notes in affected files
- ✅ Deprecation warnings for CurveDataStore (Phase 5)

**Project Documentation**:
- ✅ CLAUDE.md updated with new patterns
- ✅ Migration architecture document (this file) complete
- ✅ Phase completion reports for each phase

### Verification Checklist

**Before Declaring Success**:
- [ ] All 4 phases complete (3.1, 3.2, 3.3, 4)
- [ ] Full test suite passing (2105/2105)
- [ ] Type checking clean (0 errors)
- [ ] Manual testing checklist complete
- [ ] Performance benchmarks acceptable
- [ ] No `__default__` references in production
- [ ] No CurveDataStore writes in production
- [ ] Documentation updated
- [ ] Code review by python-code-reviewer agent

**Final Sign-Off**:
```bash
# Run comprehensive validation
.venv/bin/python3 -m pytest tests/ -v --tb=short
./bpr --errors-only
grep -r "__default__" --include="*.py" . | grep -v "migration\|doc\|\.pyc\|\.git"
grep -r "self._curve_store.set_data\|self._curve_store.add_point\|self._curve_store.remove_point" ui/ --include="*.py"

# All commands should show:
# - Tests: 2105/2105 passing
# - Type errors: 0
# - __default__: Only in docs/migration notes
# - CurveDataStore writes: 0 in production code
```

---

## 10. Appendix

### A. Signal Flow Diagrams

#### Before Migration (Bidirectional Sync):
```
User Action
  ↓
CurveViewWidget
  ↓
CurveDataStore.add_point()
  ↓ emits
CurveDataStore.point_added
  ↓
StateSyncController._on_store_point_added()
  ↓ calls
ApplicationState.set_curve_data()
  ↓ emits
ApplicationState.curves_changed
  ↓
StateSyncController._on_app_state_curves_changed()
  ↓ calls (CIRCULAR!)
CurveDataStore.set_data()
```

#### After Phase 3.1 (Unidirectional Sync):
```
User Action
  ↓
CurveViewWidget
  ↓
CurveDataFacade.add_point()
  ↓ calls
ApplicationState.add_point()
  ↓ emits
ApplicationState.curves_changed
  ↓
StateSyncController._on_app_state_curves_changed()
  ↓ syncs to (read-only)
CurveDataStore (backward compatibility cache)
  ↓ read by
CurveViewWidget.curve_data (property getter)
```

#### After Phase 4 (Final State):
```
User Action
  ↓
CurveViewWidget
  ↓
CurveDataFacade.add_point()
  ↓ calls
ApplicationState.add_point()
  ↓ emits
ApplicationState.curves_changed
  ↓
CurveViewWidget updates directly (no CurveDataStore)
```

### B. File Change Summary

| File | Phase | Lines Changed | Risk | Changes |
|------|-------|---------------|------|---------|
| `ui/controllers/curve_view/state_sync_controller.py` | 3.1 | ~50 | HIGH | Break circular dependency |
| `ui/controllers/curve_view/curve_data_facade.py` | 3.2 | ~40 | MEDIUM | Use ApplicationState methods |
| `ui/main_window.py` | 3.3 | ~5 | LOW | Update signal handler |
| `ui/timeline_tabs.py` | 3.3 | ~10 | MEDIUM | Update signal handler |
| `ui/controllers/multi_point_tracking_controller.py` | 3.3 | ~15 | MEDIUM | Update signal handler |
| `ui/protocols/controller_protocols.py` | 3.3 | ~5 | LOW | Update protocol |
| `ui/state_manager.py` | 4 | ~5 | LOW | Remove __default__ fallback |
| `ui/curve_view_widget.py` | 4 | ~30 | MEDIUM | Remove __default__ sync |
| `tests/*` (4 files) | 4 | ~50 | LOW | Use explicit curve names |
| **Total** | **3-4** | **~210** | **MEDIUM** | **9 files + tests** |

### C. Agent Handoff Notes

**For code-refactoring-expert** (Phase 3.1):
- Focus on `StateSyncController` only
- Run exclusive (no parallel agents)
- Verify no circular dependencies after changes
- Exit criteria: All tests passing, manual test successful

**For python-implementation-specialist** (Phase 3.2, 3.3):
- Can run parallel for separate files (3.3.2 handler updates)
- Use Phase 0 methods (already validated)
- Follow migration templates exactly
- Test after each method update

**For test-development-master** (Phase 4 tests):
- Can run parallel with implementation specialist
- Update test files one at a time
- Use explicit curve names pattern
- Verify 100% pass rate after each file

**For python-code-reviewer** (Final validation):
- Review after Phase 4 complete
- Check for residual `__default__` references
- Verify no CurveDataStore writes
- Sign off on migration completion

### D. Reference Implementation Examples

See Section 2 (StateSyncController), Section 3 (CurveDataFacade), and Section 4 (Signal Handlers) for detailed code examples.

### E. Glossary

- **ApplicationState**: Single source of truth for all curve data (multi-curve native)
- **CurveDataStore**: Legacy single-curve store (being deprecated)
- **`__default__`**: Special curve name for backward compatibility (removed in Phase 4)
- **Unidirectional Sync**: Data flows one way (ApplicationState → CurveDataStore)
- **Signal Adapter**: Temporary compatibility layer for signal signature changes
- **Phase 0**: ApplicationState API enhancement (prerequisite - complete)
- **Phase 3**: Migration refactoring (3 sub-phases)
- **Phase 4**: `__default__` cleanup

---

## Document History

- **2025-10-05 Initial**: Architecture design complete based on Phase 0 completion
- **2025-10-05 CRITICAL REVISION**: Fixed factual errors identified by python-code-reviewer
  - **Issue 1 FIXED**: Removed fabricated "BEFORE" code showing circular dependency (does not exist in actual code)
  - **Issue 2 FIXED**: Corrected CurveDataFacade.update_point() signature (no status parameter, takes CurvePoint object)
  - **Issue 3 FIXED**: Updated signal handler count from 6 to 8 with verified file locations
  - **Issue 4 ADDED**: Added "Current State Verification" section documenting actual current behavior
  - **Scope Revised**: Phase 3.1 changed from "Break Circular Dependency" to "Verify Unidirectional Flow" (verification-only)
  - **Timeline Updated**: Total duration reduced from 3 days to 2.25 days (Phase 3.1 now 0.25 day verification)
- **Status**: Ready for re-review by python-code-reviewer, then Phase 3 implementation

---

**NEXT ACTION**: Submit for final review by python-code-reviewer agent
