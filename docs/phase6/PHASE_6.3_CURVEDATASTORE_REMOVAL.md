# Phase 6.3: CurveDataStore Removal (CRITICAL)

[← Previous: Phase 6.2](PHASE_6.2_READ_ONLY_ENFORCEMENT.md) | [Back to Main Plan](../../PHASE_6_DEPRECATION_REMOVAL_PLAN.md) | [Next: Phase 6.4 →](PHASE_6.4_CURVE_VIEW_REMOVAL.md)

---

## Goal

Remove entire CurveDataStore class and migrate all code to use ApplicationState directly.

## Prerequisites

- [Phase 6.0](PHASE_6.0_PRE_MIGRATION_VALIDATION.md) complete (audits done)
- [Phase 6.1](PHASE_6.1_SELECTED_INDICES_MIGRATION.md) complete (3 `selected_indices` setter calls migrated)
- [Phase 6.2](PHASE_6.2_READ_ONLY_ENFORCEMENT.md) complete (read-only setters + validation tests)

---

## Architecture Transformation

### Current Architecture (Phase 5)

```
User Action → CurveDataFacade → ApplicationState (Single Source of Truth)
                                        ↓ emits curves_changed
                                  StateSyncController
                                        ↓ syncs to
                                  CurveDataStore (Backward Compatibility Layer)
                                        ↓ emits data_changed
                                  widget.curve_data property
                                        ↓
                                  Legacy Code (304 references)
```

### Target Architecture (Phase 6.3)

```
User Action → CurveDataFacade → ApplicationState (Single Source of Truth)
                                        ↓ emits curves_changed
                                  Direct ApplicationState readers
                                        ↓
                                  All code uses app_state.get_curve_data(active_curve)
```

---

## Migration Steps

### Step 1: Update Property Getters to Use ApplicationState

**File**: `ui/curve_view_widget.py`

**Phase 6.2 added setters** (read-only enforcement), but **getters still use CurveDataStore**.

**Phase 6.3 must update getters** to read from ApplicationState:

```python
@property
def curve_data(self) -> CurveDataList:
    """Get active curve data from ApplicationState."""
    active_curve = self._app_state.active_curve
    if not active_curve:
        logger.warning("No active curve set, returning empty data")
        return []
    return self._app_state.get_curve_data(active_curve)

@property
def selected_indices(self) -> set[int]:
    """Get selection for active curve from ApplicationState."""
    active_curve = self._app_state.active_curve
    if not active_curve:
        logger.warning("No active curve set, returning empty selection")
        return set()
    return self._app_state.get_selection(active_curve)
```

**Setters remain unchanged** (still raise AttributeError from Phase 6.2).

### Step 1.5: Migrate Indexed Assignments ⚠️ CRITICAL

**Why needed**: After Step 1, `widget.curve_data` returns a COPY from ApplicationState. Indexed assignments modify the copy, not ApplicationState.

**Found**: 7 production writes (verified October 6, 2025)
- `data/batch_edit.py:568` (1 slice write)
- `services/interaction_service.py:278, 280, 959, 961, 1430, 1435` (6 indexed writes)

**Migration Pattern**:
```python
# ❌ OLD: Indexed assignment (modifies copy after Phase 6.3)
view.curve_data[idx] = (point[0], new_x, new_y)

# ✅ NEW: Update via ApplicationState
active_curve = self._app_state.active_curve
if active_curve:
    data = list(self._app_state.get_curve_data(active_curve))
    data[idx] = (point[0], new_x, new_y)
    self._app_state.set_curve_data(active_curve, data)
```

**For Real-Time Drag** (use batch mode):
```python
self._app_state.begin_batch()  # Prevent signal storm
try:
    if view.selected_points:
        active_curve = self._app_state.active_curve
        if active_curve:
            data = list(self._app_state.get_curve_data(active_curve))
            for idx in view.selected_points:
                if 0 <= idx < len(data):
                    point = data[idx]
                    new_x = point[1] + curve_delta_x
                    new_y = point[2] + curve_delta_y
                    data[idx] = (point[0], new_x, new_y, point[3]) if len(point) >= 4 else (point[0], new_x, new_y)
            self._app_state.set_curve_data(active_curve, data)
finally:
    self._app_state.end_batch()
```

**Validation**:
```bash
grep -rn "\.curve_data\[.*\].*=\|\.curve_data\[:\]" --include="*.py" . \
  --exclude-dir=tests --exclude-dir=archive_legacy --exclude-dir=.venv
# Expected: 0 results
```

**Test Coverage**: 4 existing drag operation tests will validate correctness:
- `test_mouse_press_starts_drag_operation`
- `test_mouse_move_drags_selected_points`
- `test_handle_mouse_move_drag_points`
- `test_handle_mouse_release_drag`

---

### Step 2: Simplify StateSyncController ⚠️ DO THIS FIRST

**File**: `ui/controllers/curve_view/state_sync_controller.py`

**Why First**: Must remove all `_curve_store` references BEFORE deleting the store itself (Step 3).

**Remove 7 CurveDataStore Signal Connections** (lines 72-80):
1. `self._curve_store.data_changed.connect(self._on_store_data_changed)`
2. `self._curve_store.point_added.connect(self._on_store_point_added)`
3. `self._curve_store.point_updated.connect(self._on_store_point_updated)`
4. `self._curve_store.point_removed.connect(self._on_store_point_removed)`
5. `self._curve_store.point_status_changed.connect(self._on_store_status_changed)`
6. `self._curve_store.selection_changed.connect(self._on_store_selection_changed)`
7. `self._curve_store.data_changed.connect(self._sync_data_service)` (duplicate)

**Remove Methods**:
- `_connect_store_signals()` → DELETE entire method
- `_on_store_data_changed()` → DELETE
- `_on_store_point_added()` → DELETE
- `_on_store_point_updated()` → DELETE
- `_on_store_point_removed()` → DELETE
- `_on_store_status_changed()` → DELETE
- `_on_store_selection_changed()` → DELETE
- `_sync_data_service()` → DELETE (moving to ApplicationState handlers)

**Update ApplicationState Handlers** (add DataService sync):
```python
def _on_app_state_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
    """Handle ApplicationState curves_changed signal."""
    # Update widget caches and display
    self.widget.invalidate_caches()
    self.widget.update()

    # Emit widget signal for backward compatibility
    self.widget.data_changed.emit()

    # Sync DataService with active curve (replaces _sync_data_service)
    active_curve = self._app_state.active_curve
    if active_curve and active_curve in curves:
        try:
            from services import get_data_service
            data_service = get_data_service()
            data_service.update_curve_data(curves[active_curve])
        except Exception as e:
            logger.error(f"Failed to sync DataService: {e}")

def _on_app_state_active_curve_changed(self, curve_name: str) -> None:
    """Handle ApplicationState active_curve_changed signal."""
    self.widget.invalidate_caches()
    self.widget.update()
```

---

### Step 3: Remove CurveDataStore from CurveViewWidget

**File**: `ui/curve_view_widget.py`

Remove:
- `self._curve_store = CurveDataStore()`
- All `_curve_store` references
- Store initialization

Keep:
- `self._app_state = get_application_state()`

---

### Step 3.5: Remove CurveDataStore from TimelineTabWidget

**File**: `ui/timeline_tabs.py`

**Remove 6 CurveDataStore Signal Connections** (lines 338-343):
1. `self._curve_store.data_changed.connect(self._on_store_data_changed)`
2. `self._curve_store.point_added.connect(self._on_store_point_added)`
3. `self._curve_store.point_updated.connect(self._on_store_point_updated)`
4. `self._curve_store.point_removed.connect(self._on_store_point_removed)`
5. `self._curve_store.point_status_changed.connect(self._on_store_status_changed)`
6. `self._curve_store.selection_changed.connect(self._on_store_selection_changed)`

**Remove**:
- `self._curve_store = self._store_manager.get_curve_store()` (line 239)
- All `self._curve_store.get_data()` calls (lines 360, 906)
- All `self._curve_store.get_point(index)` calls (line 454)
- All 6 signal handler methods

**Replace with ApplicationState**:
```python
# Line 239: Already has ApplicationState reference
self._app_state = get_application_state()  # Already exists

# Replace get_data() calls:
# OLD:
curve_data = self._curve_store.get_data()

# NEW:
active_curve = self._app_state.active_curve
if active_curve:
    curve_data = self._app_state.get_curve_data(active_curve)
```

**Connect to ApplicationState signals**:
```python
def _connect_signals(self) -> None:
    """Connect to ApplicationState signals for reactive updates."""
    self._app_state.curves_changed.connect(self._on_curves_changed)
    self._app_state.active_curve_changed.connect(self._on_active_curve_changed)
```

---

### Step 4: Remove CurveDataFacade Store References

**File**: `ui/controllers/curve_view/curve_data_facade.py`

Remove:
- `self._curve_store = widget._curve_store`
- All facade operations now go through ApplicationState only

---

### Step 5: Add ApplicationState Integration to StoreManager

**File**: `stores/store_manager.py`

**Current** (ACTUAL - No ApplicationState integration):
```python
# stores/store_manager.py:142-159
def _connect_stores(self) -> None:
    """Connect stores to each other for coordinated updates."""
    # Only connects CurveDataStore signals - NO ApplicationState
    self.curve_store.data_changed.connect(
        lambda: self.frame_store.sync_with_curve_data(self.curve_store.get_data())
    )

    self.curve_store.point_added.connect(
        lambda index, point: self.frame_store.sync_with_curve_data(self.curve_store.get_data())
    )
    self.curve_store.point_removed.connect(
        lambda index: self.frame_store.sync_with_curve_data(self.curve_store.get_data())
    )
```

**Required Changes**:
1. **Add ApplicationState import** (top of file):
   ```python
   from stores.application_state import get_application_state
   ```

2. **Initialize ApplicationState reference** (in `__init__`):
   ```python
   def __init__(self):
       # ... existing code ...
       self._app_state = get_application_state()
       self._connect_stores()
   ```

3. **Replace `_connect_stores()` method**:
   ```python
   def _connect_stores(self) -> None:
       """Connect ApplicationState to FrameStore for coordinated updates."""
       # Connect to ApplicationState signals (replaces CurveDataStore signals)
       self._app_state.curves_changed.connect(self._on_curves_changed)
       self._app_state.active_curve_changed.connect(self._on_active_curve_changed)

       logger.debug("Connected ApplicationState signals for store coordination")

   def _on_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
       """Sync FrameStore when curve data changes."""
       active = self._app_state.active_curve
       if active and active in curves:
           curve_data = curves[active]
           self.frame_store.sync_with_curve_data(curve_data)

   def _on_active_curve_changed(self, curve_name: str) -> None:
       """Sync FrameStore when active curve switches (without data change)."""
       if curve_name:
           curve_data = self._app_state.get_curve_data(curve_name)
           self.frame_store.sync_with_curve_data(curve_data)
   ```

---

### Step 6: Delete CurveDataStore File

```bash
rm stores/curve_data_store.py
```

---

### Step 7: Migrate SignalConnectionManager

**File**: `ui/controllers/signal_connection_manager.py`

Remove:
- CurveDataStore → MainWindow signal connections
- Bidirectional selection sync logic

Keep:
- ApplicationState signal connections
- Selection already syncs via ApplicationState

---

### Step 8: Update Imports

Remove from all files:
```python
from stores.curve_data_store import CurveDataStore
```

---

## Files to Modify (11 Production + 36+ Test Files)

**Critical Files** (CurveDataStore removal):
1. `ui/curve_view_widget.py` - Update property getters (Step 1), remove `_curve_store` (Step 2)
2. ⚠️ `ui/timeline_tabs.py` - Remove `_curve_store`, remove 6 signal handlers (Step 2.5)
3. `ui/controllers/curve_view/state_sync_controller.py` - Remove 7 signal handlers (Step 3)
4. `ui/controllers/curve_view/curve_data_facade.py` - Remove store references (Step 4)
5. `stores/store_manager.py` - Add ApplicationState integration (Step 5)
6. `ui/controllers/signal_connection_manager.py` - Remove store connections (Step 7)
7. `ui/main_window.py` - Remove `_curve_store` import
8. `stores/__init__.py` - Remove CurveDataStore export
9. `ui/controllers/action_handler_controller.py` - Remove `_curve_store` references
10. `ui/controllers/multi_point_tracking_controller.py` - Remove `_curve_store` references
11. `ui/controllers/point_editor_controller.py` - Remove `_curve_store` references
12. `core/commands/shortcut_commands.py` - Remove `_curve_store` references
13. `stores/curve_data_store.py` - **DELETE FILE** (Step 6)

**Service Files** (indexed assignments - Step 1.5):
14. `services/interaction_service.py` - Migrate 6 indexed writes
15. `data/batch_edit.py` - Migrate 1 slice write

**Test Files**:
16-50+. 36+ test files with `.curve_data` references

---

## Breaking Changes

1. **`widget.curve_data` returns COPY from ApplicationState** (not live CurveDataStore data)
   - Indexed assignments modify copy, not source
   - Must use ApplicationState.set_curve_data() to persist

2. **No CurveDataStore signals**
   - Migration: Connect to `app_state.curves_changed` instead

3. **`widget.curve_data = []` raises AttributeError**
   - Migration: Use `app_state.set_curve_data(curve_name, data)`

---

## Validation (ENHANCED)

### Type Checking
```bash
./bpr --errors-only
# Expected: 0 errors (same as pre-Phase 6 baseline)
```

### Test Suite
```bash
pytest tests/ -v
# Expected: 2105/2105 passing
```

### Signal Verification
```bash
# Verify no CurveDataStore signal connections remain:
grep -rn "\.data_changed\.connect\|\.point_added\.connect" --include="*.py" . --exclude-dir=tests
# Expected: 0 results
```

### Import Verification
```bash
# Verify CurveDataStore not imported:
grep -rn "from stores.curve_data_store import" --include="*.py" . --exclude-dir=tests
# Expected: 0 results
```

---

## Rollback Plan

If Phase 6.3 fails, use one of the main plan's rollback strategies:

**Option A (Recommended)**: Backup branch
```bash
git checkout phase-6-backup
git branch -D phase-6-dev
```

**Option B**: Single atomic commit
```bash
git revert <phase-6.3-commit-hash>
```

**Option C**: Stacked commits reset
```bash
git reset --hard <last-good-commit-hash>
git push --force-with-lease
```

See [Main Plan Emergency Fix Protocol](../../PHASE_6_DEPRECATION_REMOVAL_PLAN.md#emergency-fix-protocol) for detailed recovery steps.

---

## Exit Criteria

- [ ] All 7 indexed assignments migrated
- [ ] CurveDataStore file deleted
- [ ] StateSyncController simplified (7 handlers removed)
- [ ] StoreManager has active_curve_changed handler
- [ ] SignalConnectionManager updated
- [ ] All imports removed
- [ ] 0 type errors
- [ ] All tests passing (2105/2105)
- [ ] No CurveDataStore signals connected
- [ ] Validation test suite passing ([Phase 6.2](PHASE_6.2_READ_ONLY_ENFORCEMENT.md))

---

**Next**: [Phase 6.4 - curve_view Removal →](PHASE_6.4_CURVE_VIEW_REMOVAL.md)
