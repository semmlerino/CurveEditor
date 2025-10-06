# Phase 6: Complete Deprecation Removal Plan

**Status**: PLANNING
**Goal**: Remove ALL backward compatibility code, force migration to modern APIs

---

## Executive Summary

Remove all deprecated code introduced during Phase 3-4 migration. This is a **breaking change** that eliminates the backward compatibility layer and forces all code to use ApplicationState as the single source of truth.

### Impact Analysis (UPDATED after agent + PDF review)

| Component | Files Affected | References | Migration Complexity |
|-----------|---------------|------------|---------------------|
| **CurveDataStore** | 43+ files | 352 `.curve_data` (69 prod, 283 tests) | **CRITICAL** |
| **StoreManager** | 1 file | FrameStore sync | **HIGH** ⚠️ Agent Review |
| **SignalConnectionManager** | 1 file | Selection sync | **HIGH** ⚠️ Agent Review |
| **ConnectionVerifier** | 1 file | Dev tool | **LOW** ⚠️ PDF Finding |
| **Test Fixtures** | 1 file | 48 fixtures | **MEDIUM** ⚠️ PDF Count |
| **main_window.curve_view** | 20 files | 40+ references | **HIGH** |
| **StateSyncController sync** | 1 file | 20 methods | **HIGH** |
| **timeline_tabs.frame_changed** | 5 files | 10 references | **MEDIUM** |
| **should_render_curve()** | 3 files | 5 references | **LOW** |
| **main_window.ui_components** | 1 file | 2 references | **TRIVIAL** |

**Total**: 75+ files, 352 `.curve_data` references (69 production, 283 tests) + other deprecations

**New Validation Tests Added**: 6 tests (read-only properties, thread-safety, multi-curve edge cases, FrameStore sync)

---

## Phase 6 Structure

### Phase 6.0: Pre-Migration Validation (NEW - REQUIRED)

**Goal**: Validate all assumptions before removing CurveDataStore

**Critical Validation Steps:**

1. **Add DeprecationWarnings to Deprecated APIs** (PREREQUISITE)

   **Why needed**: Only 1 of 3 deprecated APIs has warnings. Must add warnings to remaining 2 before enforcing them.

   **Current State** (verified):
   - ✅ `timeline_tabs.frame_changed` - Already has DeprecationWarning (line 675-680)
   - ❌ `widget.curve_data` - No warning yet
   - ❌ `main_window.curve_view` - No warning yet (only comment)

   ```python
   # ui/curve_view_widget.py - ADD THIS
   import warnings

   @property
   def curve_data(self) -> CurveDataList:
       """Get curve data from store (DEPRECATED - Phase 6 removal)."""
       warnings.warn(
           "widget.curve_data is deprecated and will be removed in Phase 6. "
           "Use app_state.get_curve_data(curve_name) instead.",
           DeprecationWarning,
           stacklevel=2
       )
       return self._curve_store.get_data()

   # ui/main_window.py - ADD THIS
   @property
   def curve_view(self) -> CurveViewWidget | None:
       """Deprecated alias for curve_widget."""
       warnings.warn(
           "main_window.curve_view is deprecated. Use main_window.curve_widget instead.",
           DeprecationWarning,
           stacklevel=2
       )
       return self.curve_widget
   ```

   **Validation**:
   - [ ] DeprecationWarnings added to: `widget.curve_data`, `main_window.curve_view` (timeline_tabs already has it)
   - [ ] Run `pytest tests/` - should see warnings (not errors yet)
   - [ ] Verify warning messages are helpful and include migration path

2. **Enforce DeprecationWarnings as Errors** (AFTER adding warnings)
   ```bash
   pytest -W error::DeprecationWarning tests/
   # Must pass with 0 warnings before proceeding
   # (All warnings should be fixed or explicitly ignored in test fixtures)
   ```

3. **Audit widget.curve_data Usage Patterns**
   ```bash
   # Find all write attempts (must be 0 in production):
   grep -rn "widget\.curve_data\s*=" --include="*.py" | grep -v tests/ | grep -v ".md"

   # Expected: Only test files and docs
   # Action: Fix any production code attempting writes
   ```

3. **Audit Signal Connections**
   ```bash
   # Find all CurveDataStore signal connections:
   grep -rn "\.data_changed\.connect\|\.point_added\.connect\|\.selection_changed\.connect" \
     --include="*.py" | grep -v tests/ | grep -v docs/

   # Expected: StoreManager, SignalConnectionManager, StateSyncController only
   # Action: Document migration path for each
   ```

4. **Check Batch Operation Signals** ⚠️ GAP IDENTIFIED
   ```bash
   # Verify if any code depends on batch signals:
   grep -rn "batch_operation_started\|batch_operation_ended" \
     --include="*.py" --exclude-dir=tests --exclude-dir=docs

   # Expected: Likely 0 (ApplicationState has begin_batch/end_batch but no signals)
   # Action: If found, add batch signals to ApplicationState or verify safe to remove
   ```

5. **Verify Undo/Redo System**
   ```bash
   # Ensure CommandManager is sole undo mechanism:
   grep -rn "\.can_undo\|\.can_redo" --include="*.py" | grep -v "test_curve_data_store"

   # Expected: Only CommandManager references
   # Action: Remove any CurveDataStore undo dependencies
   ```

6. **Check Session Manager Dependencies** ⚠️ GAP IDENTIFIED
   ```bash
   # Verify session persistence doesn't reference CurveDataStore:
   grep -rn "CurveDataStore\|_curve_store" session/ --include="*.py"

   # Expected: 0 results (session should use ApplicationState)
   # Action: If found, migrate session save/restore to ApplicationState
   ```

7. **Baseline Metrics Collection**
   ```bash
   # Type checking baseline:
   ./bpr --errors-only > pre_phase6_types.txt
   ```

8. **Identify Hidden Dependencies**
   - ✅ `stores/store_manager.py` - FrameStore synchronization via CurveDataStore.data_changed
   - ✅ `ui/controllers/signal_connection_manager.py` - Bidirectional selection sync
   - ✅ `stores/connection_verifier.py` - Signal validation tool (PDF finding)
   - ⚠️ Any other production code connecting to CurveDataStore signals

**Validation Checklist:**

- [ ] **DeprecationWarnings ADDED**: Add warnings.warn() to widget.curve_data, main_window.curve_view (timeline_tabs.frame_changed already has it)
- [ ] **DeprecationWarnings VERIFIED**: Run `pytest tests/` and confirm warnings appear (not errors yet)
- [ ] **DeprecationWarnings RESOLVED**: Fix or suppress all warnings, then `pytest -W error::DeprecationWarning` passes
- [ ] 0 production writes to `widget.curve_data` (read-only verified via grep)
- [ ] All signal connections documented and migration planned (grep audit complete)
- [ ] Batch operation signals checked (verified unused - safe to remove)
- [ ] CommandManager confirmed as sole undo system (verified via grep)
- [ ] Session manager CurveDataStore references checked (verified 0 results)
- [ ] StoreManager FrameStore sync migration planned (BOTH curves_changed AND active_curve_changed)
- [ ] SignalConnectionManager selection sync migration planned
- [ ] timeline_tabs.py migration planned (6 signal connections → 1 consolidated handler)
- [ ] ConnectionVerifier migration planned (recommended: deprecate - low priority dev tool)
- [ ] Baseline metrics collected (type checking: `./bpr --errors-only > pre_phase6_types.txt`)

**Exit Criteria**: All checklist items complete + validation test suite (Phase 6.0.5) passing before proceeding to Phase 6.1

---

### Phase 6.0.5: Implement Read-Only Enforcement & Validation Tests (NEW - REQUIRED)

**Goal**: Add read-only property setters, then create comprehensive validation test suite

**CRITICAL SEQUENCING**: Setters must be implemented BEFORE tests (tests expect AttributeError from setters).

---

#### Part A: Implement Read-Only Property Setters (PREREQUISITE)

**Goal**: Prevent silent attribute shadowing by adding explicit setters that raise errors

**Implementation**:

```python
# ui/curve_view_widget.py

@property
def curve_data(self) -> CurveDataList:
    """Get active curve data from ApplicationState (Phase 6: direct read)."""
    active = self._app_state.active_curve
    if not active:
        logger.warning("No active curve set, returning empty data")
        return []
    return self._app_state.get_curve_data(active)

@curve_data.setter
def curve_data(self, value: CurveDataList) -> None:
    """Prevent writes - property is read-only.

    Raises:
        AttributeError: Always raised - property is read-only
    """
    raise AttributeError(
        "widget.curve_data is read-only. "
        "Use app_state.set_curve_data(curve_name, data) instead."
    )

@property
def selected_indices(self) -> set[int]:
    """Get selection for active curve from ApplicationState."""
    active = self._app_state.active_curve
    if not active:
        logger.warning("No active curve set, returning empty selection")
        return set()
    return self._app_state.get_selection(active)

@selected_indices.setter
def selected_indices(self, value: set[int]) -> None:
    """Prevent writes - property is read-only.

    Raises:
        AttributeError: Always raised - property is read-only
    """
    raise AttributeError(
        "widget.selected_indices is read-only. "
        "Use app_state.set_selection(curve_name, indices) instead."
    )
```

**Why setters are needed**:
Without explicit setters, Python allows assignment which creates instance attribute:
```python
widget.curve_data = []  # Creates widget.__dict__['curve_data'] = []
                        # Property is now SHADOWED - getter never called again!
```

With explicit setters:
```python
widget.curve_data = []  # Raises AttributeError with helpful message
```

**Validation**:
- [ ] Both setters implemented in `ui/curve_view_widget.py`
- [ ] Manual test: `widget.curve_data = []` raises AttributeError
- [ ] Manual test: `widget.selected_indices = {1}` raises AttributeError

---

#### Part B: Create Validation Test Suite (tests now pass with setters in place)

**Critical Tests to Implement:**

```python
# tests/test_phase6_validation.py - NEW FILE (create before Phase 6.1)

"""Phase 6 migration validation tests."""

import pytest
import threading
from stores.application_state import get_application_state
from core.models import CurvePoint
from rendering.render_state import RenderState
from core.display_mode import DisplayMode

def test_curve_data_property_is_read_only(curve_view_widget):
    """Verify widget.curve_data setter raises AttributeError."""
    with pytest.raises(AttributeError, match="read-only"):
        curve_view_widget.curve_data = []

def test_selected_indices_property_is_read_only(curve_view_widget):
    """Verify widget.selected_indices setter raises AttributeError."""
    with pytest.raises(AttributeError, match="read-only"):
        curve_view_widget.selected_indices = {1, 2, 3}

def test_curve_data_thread_safety_during_batch():
    """Verify batch updates complete without race conditions."""
    import threading

    app_state = get_application_state()
    widget = create_test_widget()
    app_state.set_curve_data("test", create_test_curve())
    app_state.set_active_curve("test")

    errors = []

    def batch_update():
        """Perform batch update operations."""
        try:
            app_state.begin_batch()
            for i in range(50):
                data = list(app_state.get_curve_data("test"))
                data.append(CurvePoint(i, i, i))
                app_state.set_curve_data("test", data)
        except Exception as e:
            errors.append(e)
        finally:
            app_state.end_batch()

    # Run multiple concurrent batch operations
    threads = [threading.Thread(target=batch_update) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread safety errors: {errors}"
    # Verify final data is consistent
    final_data = app_state.get_curve_data("test")
    assert isinstance(final_data, list)

def test_rendering_all_visible_no_active_curve():
    """Verify display_mode=ALL_VISIBLE works when active_curve=None.

    Gap identified: Multi-curve edge case not covered by agent reviews or PDF.
    """
    widget = create_test_widget()
    app_state = get_application_state()

    # Load 10 curves but set no active curve
    for i in range(10):
        app_state.set_curve_data(f"Track{i}", create_test_curve())
    app_state.set_active_curve(None)  # No active curve

    # Set display mode to show all
    app_state.set_show_all_curves(True)

    # Should render all 10 curves, not crash with empty curve_data property
    render_state = RenderState.compute(widget)
    assert len(render_state.visible_curves) == 10

    # widget.curve_data should return [] with warning (no active curve)
    data = widget.curve_data
    assert data == []  # Expected behavior from amended plan

def test_frame_store_syncs_on_active_curve_switch():
    """Verify FrameStore updates when switching curves without data changes.

    Critical validation for StoreManager active_curve_changed connection.
    """
    app_state = get_application_state()
    app_state.set_curve_data("Track1", create_curve_with_frames(1, 100))
    app_state.set_curve_data("Track2", create_curve_with_frames(50, 200))

    app_state.set_active_curve("Track1")
    assert store_manager.frame_store.min_frame == 1
    assert store_manager.frame_store.max_frame == 100

    # Switch without modifying data
    app_state.set_active_curve("Track2")
    assert store_manager.frame_store.min_frame == 50  # Should update!
    assert store_manager.frame_store.max_frame == 200

def test_active_curve_none_rendering():
    """Verify rendering doesn't crash when active_curve=None."""
    widget = create_test_widget()
    app_state = get_application_state()

    app_state.set_active_curve(None)

    # Should not crash, returns empty data
    data = widget.curve_data
    assert data == []

    # Rendering should handle empty gracefully
    render_state = RenderState.compute(widget)
    # Should not crash
```

**Additional Recommended Tests** (Optional - raises confidence 85% → 90%):

```python
def test_batch_signal_deduplication():
    """Verify end_batch emits only 1 signal for N operations."""
    app_state = get_application_state()
    signals_received = []
    app_state.curves_changed.connect(lambda _: signals_received.append(1))

    app_state.begin_batch()
    for i in range(100):
        app_state.add_point("test", CurvePoint(i, i, i))
    app_state.end_batch()

    assert len(signals_received) == 1  # Not 100!

def test_selection_bidirectional_sync():
    """Verify selection syncs between widget and tracking controller."""
    # Test widget selection → ApplicationState → tracking controller
    # Test tracking controller selection → ApplicationState → widget
    pass

def test_undo_redo_integration_post_migration():
    """Verify CommandManager works after CurveDataStore removal."""
    # Execute command, undo, redo, verify state
    pass

def test_session_save_restore_post_migration():
    """Verify session persistence without CurveDataStore."""
    # Save session, clear state, restore, verify
    pass
```

---

**Exit Criteria**:

**Part A** (setters):
- [ ] Both setters implemented in `ui/curve_view_widget.py`
- [ ] Manual verification: `widget.curve_data = []` raises AttributeError
- [ ] Manual verification: `widget.selected_indices = {1}` raises AttributeError

**Part B** (tests):
- [ ] File created at `tests/test_phase6_validation.py`
- [ ] All 6 required tests implemented and passing
- [ ] 4 optional integration tests implemented (recommended)
- [ ] Integrated into pytest suite

---

### Phase 6.1: CurveDataStore Removal (CRITICAL)

**Goal**: Remove entire CurveDataStore class and migrate all readers to ApplicationState

#### Current Architecture (Phase 5)

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

#### Target Architecture (Phase 6.1)

```
User Action → CurveDataFacade → ApplicationState (Single Source of Truth)
                                        ↓ emits curves_changed
                                  Direct ApplicationState readers
                                        ↓
                                  All code uses app_state.get_curve_data(active_curve)
```

#### Migration Strategy

**Step 1: Add ApplicationState Accessors to CurveViewWidget**

```python
# ui/curve_view_widget.py

@property
def curve_data(self) -> CurveDataList:
    """Get active curve data from ApplicationState (Phase 6: direct read)."""
    active = self._app_state.active_curve
    if not active:
        logger.warning("No active curve set, returning empty data")
        return []
    return self._app_state.get_curve_data(active)

@curve_data.setter
def curve_data(self, value: CurveDataList) -> None:
    """Prevent writes - property is read-only."""
    raise AttributeError(
        "widget.curve_data is read-only. "
        "Use app_state.set_curve_data(curve_name, data) instead."
    )

@property
def selected_indices(self) -> set[int]:
    """Get selection for active curve from ApplicationState."""
    active = self._app_state.active_curve
    if not active:
        logger.warning("No active curve set, returning empty selection")
        return set()
    return self._app_state.get_selection(active)

@selected_indices.setter
def selected_indices(self, value: set[int]) -> None:
    """Prevent writes - property is read-only."""
    raise AttributeError(
        "widget.selected_indices is read-only. "
        "Use app_state.set_selection(curve_name, indices) instead."
    )
```

**Step 2: Remove CurveDataStore from CurveViewWidget**

```python
# Remove:
# - self._curve_store = CurveDataStore()
# - All _curve_store references
# - Store initialization

# Keep:
# - self._app_state = get_application_state()
```

**Step 3: Simplify StateSyncController**

Remove ALL CurveDataStore sync logic (7 signal connections + handler methods):

**Signal Connections to Remove** (verified at lines 72-80):
1. `self._curve_store.data_changed.connect(self._on_store_data_changed)` (line 72)
2. `self._curve_store.point_added.connect(self._on_store_point_added)` (line 73)
3. `self._curve_store.point_updated.connect(self._on_store_point_updated)` (line 74)
4. `self._curve_store.point_removed.connect(self._on_store_point_removed)` (line 75)
5. `self._curve_store.point_status_changed.connect(self._on_store_status_changed)` (line 76)
6. `self._curve_store.selection_changed.connect(self._on_store_selection_changed)` (line 77)
7. `self._curve_store.data_changed.connect(self._sync_data_service)` (line 80) ⚠️ Duplicate data_changed connection

**Methods to Remove**:
- `_connect_store_signals()` → DELETE entire method
- `_on_store_data_changed()` → DELETE
- `_on_store_point_added()` → DELETE
- `_on_store_point_updated()` → DELETE
- `_on_store_point_removed()` → DELETE
- `_on_store_status_changed()` → DELETE
- `_on_store_selection_changed()` → DELETE
- `_sync_data_service()` → DELETE (verify DataService no longer needs this)
- `_on_app_state_curves_changed()` sync to store → DELETE sync, keep widget update
- `_on_app_state_active_curve_changed()` sync to store → DELETE sync, keep widget update

**Step 4: Remove CurveDataFacade Store References**

```python
# ui/controllers/curve_view/curve_data_facade.py

# Remove:
# - self._curve_store = widget._curve_store

# All operations now go through ApplicationState only
```

**Step 5: Delete CurveDataStore File**

```bash
rm stores/curve_data_store.py
```

**Step 6: Migrate StoreManager**

```python
# stores/store_manager.py

# REMOVE old CurveDataStore sync:
# self.curve_store.data_changed.connect(
#     lambda: self.frame_store.sync_with_curve_data(self.curve_store.get_data())
# )

# ADD ApplicationState sync (BOTH signals required):
from stores.application_state import get_application_state

app_state = get_application_state()
app_state.curves_changed.connect(self._on_app_state_curves_changed)
app_state.active_curve_changed.connect(self._on_active_curve_changed)  # CRITICAL: Sync on curve switch

def _on_app_state_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
    """Sync FrameStore when ApplicationState curves change.

    NOTE: Signal emits entire dataset - fetch current state to avoid race conditions.
    """
    # Fetch data at sync time (not from signal args) to avoid temporal coupling
    active = self._app_state.active_curve
    if not active:
        return  # Early exit - no active curve

    # Fresh read of current state
    curve_data = self._app_state.get_curve_data(active)
    self.frame_store.sync_with_curve_data(curve_data)

def _on_active_curve_changed(self, curve_name: str | None) -> None:
    """Sync FrameStore when active curve changes (even if data unchanged).

    Critical for timeline updates when switching between curves.

    NOTE: Signal signature is Signal(str), but emits "" (empty string) when None.
    Handler accepts str | None for compatibility, checks falsy value (both None and "" are falsy).
    """
    if curve_name:  # Catches both None and "" (empty string)
        curve_data = self._app_state.get_curve_data(curve_name)
        self.frame_store.sync_with_curve_data(curve_data)
    else:
        self.frame_store.sync_with_curve_data([])  # Clear on None or ""
```

**Step 7: Migrate SignalConnectionManager**

```python
# ui/controllers/signal_connection_manager.py

# REMOVE old CurveDataStore connections (lines 108, 112-114):
# self.main_window.get_curve_store().selection_changed.connect(...)

# ADD ApplicationState connections:
from stores.application_state import get_application_state

app_state = get_application_state()

# NOTE: selection_changed signature changed from Signal(set) to Signal(set, str)
# ✅ HANDLERS ALREADY COMPATIBLE - Updated in Phase 4 with optional curve_name parameter
app_state.selection_changed.connect(self.main_window.on_store_selection_changed)
app_state.selection_changed.connect(
    self.main_window.tracking_controller.on_curve_selection_changed
)

# Handler signatures (ALREADY CORRECT):
# MainWindow.on_store_selection_changed(self, selection: set[int], curve_name: str | None = None)
# MultiPointTrackingController.on_curve_selection_changed(self, selection: set[int], curve_name: str | None = None)
```

**Step 8: Migrate ConnectionVerifier**

```python
# stores/connection_verifier.py (PDF finding - dev tool)

# OPTION A: Update to use ApplicationState (if still useful)
class ConnectionVerifier:
    def verify_curve_data_connections(self):
        app_state = get_application_state()
        # Update validation logic to check ApplicationState.curves_changed connections

# OPTION B: Deprecate entirely (recommended - dev-time only tool)
# Mark as deprecated, remove in Phase 7 cleanup
```

**Step 8.5: Migrate timeline_tabs.py Signal Connections** ⚠️ CRITICAL

```python
# ui/timeline_tabs.py

# REMOVE all 6 CurveDataStore signal connections (lines 338-343):
# self._curve_store.data_changed.connect(self._on_store_data_changed)
# self._curve_store.point_added.connect(self._on_store_point_added)
# self._curve_store.point_updated.connect(self._on_store_point_updated)
# self._curve_store.point_removed.connect(self._on_store_point_removed)
# self._curve_store.point_status_changed.connect(self._on_store_status_changed)
# self._curve_store.selection_changed.connect(self._on_store_selection_changed)

# ADD consolidated ApplicationState connection:
from stores.application_state import get_application_state

app_state = get_application_state()
app_state.curves_changed.connect(self._on_app_state_curves_changed)

def _on_app_state_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
    """Handle ApplicationState curves change (consolidates 6 handlers).

    Replaces:
    - _on_store_data_changed()
    - _on_store_point_added()
    - _on_store_point_updated()
    - _on_store_point_removed()
    - _on_store_status_changed()
    - _on_store_selection_changed() (might also use selection_changed signal)

    NOTE: Signal emits entire dataset - fetch current state to avoid race conditions.
    """
    # Fetch data at sync time (not from signal args) to avoid temporal coupling
    active = self._app_state.active_curve
    if not active:
        return

    # Fresh read of current state
    curve_data = self._app_state.get_curve_data(active)

    # Rebuild timeline based on current active curve data
    # (consolidate logic from all 6 old handlers)
    self._rebuild_timeline(curve_data)

# DELETE all 6 old handler methods:
# - _on_store_data_changed()
# - _on_store_point_added()
# - _on_store_point_updated()
# - _on_store_point_removed()
# - _on_store_status_changed()
# - _on_store_selection_changed()
```

**Why this is critical**:
- timeline_tabs.py has 6 CurveDataStore signal connections NOT covered in previous migration steps
- Without this migration, timeline will break when CurveDataStore is deleted
- Consolidation to single `curves_changed` handler simplifies logic

**Step 9: Update All Tests**

- Replace `widget.curve_data` reads with direct property access (still works)
- Verify `widget.curve_data = ...` writes raise AttributeError
- Replace `widget.selected_indices` reads with direct property access
- Verify `widget.selected_indices = ...` writes raise AttributeError
- Ensure all test fixtures set `active_curve` before accessing data
- **Update 48 test fixtures in tests/conftest.py** (PDF count)
- Remove CurveDataStore imports (43+ files)

#### Files to Modify (44+ files - UPDATED)

**Production Code (16 files - UPDATED from 15)**:
1. `ui/curve_view_widget.py` - Replace properties with explicit setters, remove _curve_store
2. `ui/controllers/curve_view/state_sync_controller.py` - Remove 10 sync methods
3. `ui/controllers/curve_view/curve_data_facade.py` - Remove store reference
4. `ui/timeline_tabs.py` - **CRITICAL: Migrate 6 CurveDataStore signal connections to ApplicationState.curves_changed**
5. `ui/main_window.py` - Remove store initialization
6. `ui/controllers/signal_connection_manager.py` - **CRITICAL: Migrate selection sync to ApplicationState**
7. `ui/controllers/point_editor_controller.py` - Use ApplicationState
8. `ui/controllers/multi_point_tracking_controller.py` - Use ApplicationState
9. `ui/controllers/action_handler_controller.py` - Use ApplicationState
10. `stores/store_manager.py` - **CRITICAL: Migrate FrameStore sync to ApplicationState (BOTH signals)**
11. `stores/frame_store.py` - Remove store dependencies
12. `stores/__init__.py` - Remove CurveDataStore export
13. `stores/connection_verifier.py` - **PDF: Update or deprecate dev tool** (low priority)
14. `services/interaction_service.py` - **CRITICAL: REPLACE curve_view with curve_widget in 6 fallback references (undo/redo)**
15. `ui/menu_bar.py` - Replace curve_view with curve_widget (4 menu handlers)
16. ⚠️ **NEW**: Any other files connecting to CurveDataStore signals (found via grep in Phase 6.0)

**Test Files (29+ files)**:
- All test files: Verify read-only properties raise errors on write
- **Update 48 test fixtures** in tests/conftest.py to set `active_curve`
- Add 2 new validation tests (thread-safety, multi-curve edge case)

#### Breaking Changes

1. **widget.curve_data is now read-only** (was always intended, now enforced)
2. **No more CurveDataStore signals** (data_changed, point_added, etc.)
3. **All modifications must go through ApplicationState**

#### Validation (ENHANCED)

**Pre-Migration:**
- [ ] Phase 6.0 validation complete (all checklist items)
- [ ] Phase 6.0.5 validation test suite created and passing (6 tests)
- [ ] DeprecationWarnings verified to exist in deprecated APIs
- [ ] Baseline metrics collected

**Post-Migration:**
- [ ] All tests passing (2297+ tests including 6 new validation tests)
- [ ] 0 type errors: `./bpr --errors-only`
- [ ] Type safety maintained: `diff pre_phase6_types.txt post_phase6_types.txt` (should be empty)
- [ ] No CurveDataStore references: `grep -r "CurveDataStore\|_curve_store" --include="*.py" --exclude-dir=tests --exclude-dir=docs | wc -l` → 0
- [ ] **Read-only properties enforced**: test_curve_data_property_is_read_only and test_selected_indices_property_is_read_only pass
- [ ] **Thread safety verified**: test_curve_data_thread_safety_during_batch passes
- [ ] **Multi-curve edge case**: test_rendering_all_visible_no_active_curve passes
- [ ] **FrameStore sync working**: test_frame_store_syncs_on_active_curve_switch passes (timeline updates on curve switch)
- [ ] **Active curve nullability**: test_active_curve_none_rendering passes (no crashes when `active_curve` is None)
- [ ] Selection sync working: Bidirectional selection between widget and tracking controller
- [ ] ConnectionVerifier updated or deprecated

**Manual Testing:**
- [ ] Load multi-curve session (10+ curves)
- [ ] Verify rendering with no active curve set (should show empty or log warning)
- [ ] Test all undo/redo operations (move, delete, status change)
- [ ] Background image load (thread safety)
- [ ] Batch operations (100+ point curve)
- [ ] Session save/restore with selection state
- [ ] Timeline navigation syncs correctly with curve data

---

### Phase 6.2: main_window.curve_view Removal (HIGH)

**Goal**: Remove `main_window.curve_view` alias, force use of `curve_widget`

#### Current Usage

**Production Code (4 files)**:
1. `ui/main_window.py:252` - `self.curve_view = None` (initialization)
2. `ui/main_window.py:1087` - `set_curve_view()` method
3. `ui/menu_bar.py:364-386` - 4 menu handlers check `curve_view`
4. `services/interaction_service.py:571-1330` - 6 fallback references

**Test Code (16 files)**:
- All test mocks set both `curve_widget` and `curve_view`

#### Migration Strategy

**Step 1: Update MainWindow**

```python
# ui/main_window.py

# Remove:
# - self.curve_view: CurveViewWidget | None = None
# - def set_curve_view(self, curve_view: CurveViewWidget | None) -> None

# Keep only:
# - self.curve_widget: CurveViewWidget
```

**Step 2: Update MenuBar**

```python
# ui/menu_bar.py

# Replace ALL:
if self.main_window and self.main_window.curve_view is not None:
    curve_view = self.main_window.curve_view

# With:
if self.main_window and self.main_window.curve_widget is not None:
    curve_widget = self.main_window.curve_widget
```

**Step 3: Update InteractionService (CRITICAL FIX)**

```python
# services/interaction_service.py

# ⚠️ DO NOT DELETE - This is history extraction code for undo/redo!
# REPLACE fallback with curve_widget (not delete):

# OLD:
elif main_window.curve_view is not None and getattr(main_window.curve_view, "curve_data", None) is not None:
    view_curve_data = getattr(main_window.curve_view, "curve_data")

# NEW:
elif main_window.curve_widget is not None and getattr(main_window.curve_widget, "curve_data", None) is not None:
    view_curve_data = getattr(main_window.curve_widget, "curve_data")

# All 6 fallback references must REPLACE curve_view with curve_widget (not delete)
```

**Step 4: Update All Tests**

```python
# Remove from all MockMainWindow:
# - self.curve_view = ...
# - main_window.curve_view = view

# Use only:
# - self.curve_widget = ...
```

#### Files to Modify (20 files)

**Production**: 4 files
**Tests**: 16 files

#### Breaking Changes

- **main_window.curve_view removed** - Use `main_window.curve_widget`
- **Protocol updated** - `MainWindowProtocol.curve_view` removed

---

### Phase 6.3: timeline_tabs.frame_changed Removal (MEDIUM)

**Goal**: Remove deprecated `timeline_tabs.frame_changed` signal

#### Current Status

- Signal exists with `DeprecationWarning`
- StateManager.frame_changed is the correct API
- 10 references across 5 files

#### Migration

```python
# Replace:
timeline_tabs.frame_changed.connect(handler)

# With:
state_manager.frame_changed.connect(handler)
```

#### Files to Modify

- `ui/timeline_tabs.py` - Remove signal definition and emission
- 4 files that connect to it

---

### Phase 6.4: should_render_curve() Removal (LOW)

**Goal**: Remove legacy `should_render_curve()` method

#### Migration

```python
# Replace:
if widget.should_render_curve(curve_name):
    render(curve_name)

# With:
render_state = RenderState.compute(widget)
for curve_name in render_state.visible_curves:
    render(curve_name)
```

#### Files to Modify

- `ui/curve_view_widget.py` - Remove method
- `rendering/optimized_curve_renderer.py` - Use RenderState
- 1-2 test files

---

### Phase 6.5: ui_components Removal (TRIVIAL)

**Goal**: Remove `main_window.ui_components` alias

```python
# ui/main_window.py

# Remove:
# - self.ui_components: object | None = None

# Use only:
# - self.ui: UIComponents
```

---

## Execution Strategy (REVISED)

### Recommended Order (UPDATED - Risk-First Approach)

**Rationale**: Do highest-risk changes first when rollback is cleanest. If Phase 6.1 succeeds, remaining phases are mechanical.

1. **Phase 6.0** - ⚠️ Pre-migration validation (audits, baseline collection)
2. **Phase 6.0.5** - ⚠️ NEW: Create validation test suite (REQUIRED before proceeding)
3. **Phase 6.1** - CRITICAL: CurveDataStore removal (do first for clean rollback)
4. **Phase 6.2** - HIGH: main_window.curve_view removal (straightforward after 6.1)
5. **Phase 6.3** - MEDIUM: timeline_tabs.frame_changed removal
6. **Phase 6.4** - LOW: should_render_curve() removal
7. **Phase 6.5** - TRIVIAL: ui_components removal

**Alternative**: Single atomic commit for all sub-phases with backup branch.

### Risk Mitigation (ENHANCED)

1. **Branch Strategy**:
   ```bash
   git checkout -b phase-6-backup         # Create backup before starting
   git checkout -b phase-6-dev            # Development branch
   # After each sub-phase, commit with clear message
   # If failure: git checkout phase-6-backup
   ```

2. **Incremental Commits with Reset Points**:
   ```bash
   git commit -m "Phase 6.0: Pre-migration validation complete"  # Hash: abc123
   git commit -m "Phase 6.1: CurveDataStore removed"             # Hash: def456
   # If Phase 6.2 fails: git reset --hard def456
   ```

3. **Test Suite**: Run enhanced validation checklist after each sub-phase

4. **Type Checking**: Maintain 0 errors throughout, compare pre/post baselines

5. **Enhanced Rollback Plan**:
   - **Option A**: Backup branch `git checkout phase-6-backup`
   - **Option B**: Single atomic commit `git revert <commit>`
   - **Option C**: Stacked commits with reset `git reset --hard <hash>`

---

## Benefits of Removal

### Code Quality

- **-1,200 lines**: Remove entire CurveDataStore class + sync logic
- **Simpler Architecture**: Single source of truth (no dual-store complexity)
- **Fewer Signals**: Eliminate 7 CurveDataStore signals
- **Clearer APIs**: No confusion between widget.curve_data vs ApplicationState

### Maintainability

- **No Backward Compatibility Code**: Clean, modern APIs only
- **Reduced Test Complexity**: No mocking CurveDataStore

---

## Breaking Changes Summary

1. **widget.curve_data is read-only property** (was always intended)
   - Migration: Use `app_state.set_curve_data(curve_name, data)`

2. **No CurveDataStore signals**
   - Migration: Connect to `app_state.curves_changed` instead

3. **main_window.curve_view removed**
   - Migration: Use `main_window.curve_widget`

4. **timeline_tabs.frame_changed removed**
   - Migration: Use `state_manager.frame_changed`

### API Migration Guide

```python
# OLD (Phase 5)
widget.curve_data = new_data  # Doesn't work anyway
data = widget.curve_data
widget._curve_store.data_changed.connect(handler)

# NEW (Phase 6)
app_state.set_curve_data(curve_name, new_data)
data = app_state.get_curve_data(curve_name)
app_state.curves_changed.connect(handler)
```

---

## Testing Strategy (ENHANCED)

### Phase 6.0 (Pre-Migration Validation)

1. **Deprecation Enforcement**:
   ```bash
   pytest -W error::DeprecationWarning tests/
   # Must pass before proceeding
   ```

2. **Pattern Audits** (see Phase 6.0 section for full commands):
   - widget.curve_data write attempts → 0 in production
   - CurveDataStore signal connections → documented and migration planned
   - Undo/redo dependencies → CommandManager only

3. **Baseline Collection**:
   - Type checking: `./bpr --errors-only > pre_phase6_types.txt`

### Phase 6.1 (CurveDataStore Removal)

**Validation Test Suite** (test_phase6_validation.py - 6 tests):

1. ✅ `test_curve_data_property_is_read_only()` - Verify explicit setter raises AttributeError
2. ✅ `test_selected_indices_property_is_read_only()` - Verify explicit setter raises AttributeError
3. ✅ `test_curve_data_thread_safety_during_batch()` - Verify concurrent batch operations
4. ✅ `test_rendering_all_visible_no_active_curve()` - Multi-curve edge case (active_curve=None)
5. ✅ `test_frame_store_syncs_on_active_curve_switch()` - Critical for StoreManager active_curve_changed connection
6. ✅ `test_active_curve_none_rendering()` - Verify no crashes with active_curve=None

**Additional Integration Tests**:
   - Widget updates correctly from ApplicationState
   - Selection syncs bidirectionally (widget ↔ tracking_controller)
   - Signal ordering correct (ApplicationState updates before emissions)
   - Background image load doesn't conflict with ApplicationState access

### Full Suite Validation

**Post-Migration Checklist:**
- [ ] 2297+ tests passing (including 6 validation tests)
- [ ] 0 type errors: `./bpr --errors-only`
- [ ] Type safety maintained: `diff pre_phase6_types.txt post_phase6_types.txt` (empty)
- [ ] No CurveDataStore references: `grep -r "CurveDataStore" --include="*.py" | wc -l` → 0
- [ ] All 6 validation tests passing (test_phase6_validation.py)
- [ ] FrameStore sync working (including active_curve_changed connection)
- [ ] Selection sync working
- [ ] Read-only properties enforced
- [ ] Multi-curve scenarios work

**Manual Testing (Enhanced):**
- [ ] Load multi-curve session (10+ curves)
- [ ] **Verify rendering with no active curve set** (display_mode=ALL_VISIBLE + active_curve=None)
- [ ] Test all undo/redo operations (move, delete, status, smooth, add point)
- [ ] **Background image load during batch update** (thread safety stress test)
- [ ] Batch operations (100+ point curve with rendering active)
- [ ] Session save/restore with selection state (verify no CurveDataStore persistence)
- [ ] Timeline navigation syncs correctly (FrameStore verification)

---

## Rollback Plan (ENHANCED)

If Phase 6 introduces critical bugs:

### Option A: Backup Branch (Recommended)
```bash
# Rollback to pre-Phase 6 state:
git checkout phase-6-backup

# If you need to preserve some changes:
git checkout phase-6-backup
git cherry-pick <specific-fixes-from-phase-6-dev>
```

### Option B: Single Atomic Commit
```bash
# If all phases in single commit:
git revert <phase-6-commit-hash>
```

### Option C: Stacked Commits Reset
```bash
# Find last good commit:
git log --oneline  # Identify hash of "Phase 6.0 complete"

# Reset to before failure:
git reset --hard <last-good-hash>

# Or revert specific sub-phase:
git revert <phase-6.1-hash>
```

### Emergency Fix Protocol
1. **Critical Production Bug**: Immediately `git checkout phase-6-backup`
2. **Apply Urgent Fix**: Cherry-pick to backup branch
3. **Re-attempt Phase 6**: After root cause analysis and enhanced testing

---

## Post-Phase 6 State

### Architecture

```
User Action → CurveDataFacade → ApplicationState (ONLY Source of Truth)
                                        ↓ emits curves_changed
                                  All components read from ApplicationState
```

### Removed Components

- ❌ `stores/curve_data_store.py` (entire file deleted)
- ❌ `StateSyncController` sync methods (10 methods removed)
- ❌ `main_window.curve_view` attribute
- ❌ `main_window.ui_components` attribute
- ❌ `timeline_tabs.frame_changed` signal
- ❌ `should_render_curve()` method

### Remaining Components

- ✅ `ApplicationState` (single source of truth)
- ✅ `CurveViewWidget` (reads from ApplicationState)
- ✅ `CurveDataFacade` (writes to ApplicationState)
- ✅ `StateSyncController` (widget update logic only, no store sync)
- ✅ `StateManager` (frame management)

---

## Decision Points

### Should We Do Phase 6?

**Arguments FOR**:
- Cleaner architecture (no backward compatibility cruft)
- Easier to maintain (simpler mental model)
- Forces correct API usage

**Arguments AGAINST**:
- Large refactoring (400+ references)
- Risk of introducing bugs
- No immediate user-facing benefits

---

## Conclusion

Phase 6 is a **major refactoring** that removes all backward compatibility code from Phase 3-4 migration. It simplifies the architecture significantly but requires careful execution.

---

**Plan Created**: October 5, 2025
**Plan Author**: Claude Code
**Last Amended**: October 6, 2025 (after concurrent python-code-reviewer and python-expert-architect reviews)
**Risk Level**: HIGH (upgraded from MEDIUM-HIGH due to hidden dependencies + signal architecture issues)
**Status**: AMENDED - CONDITIONAL GO (requires Phase 6.0 + 6.0.5 validation before Phase 6.1)

---

## Amendment Summary (October 5, 2025)

**Changes Made Based on Agent Reviews:**

1. ✅ **Added Phase 6.0**: Pre-migration validation (REQUIRED step)
2. ✅ **Updated Impact Analysis**: 73+ files (from 71), added StoreManager and SignalConnectionManager
3. ✅ **Enhanced Properties**: Added explicit setters that raise helpful errors
4. ✅ **Critical Fix**: InteractionService fallbacks must REPLACE not DELETE (undo/redo code)
5. ✅ **Migration Steps**: Added StoreManager and SignalConnectionManager migrations
6. ✅ **Execution Order**: Reversed to risk-first (6.0 → 6.1 → 6.5)
7. ✅ **Testing Strategy**: Enhanced with pre/post validation, baselines, and comprehensive checks
8. ✅ **Rollback Plan**: Multiple options with clear procedures
9. ✅ **Signal Signature Fixes**: Corrected handler signatures to match ApplicationState signals

**Additional Changes Based on PDF Assessment:**

10. ✅ **ConnectionVerifier Added**: stores/connection_verifier.py dev tool (low priority)
11. ✅ **Test Fixture Count**: 48 fixtures in conftest.py to update
12. ✅ **Thread Safety Test**: test_curve_data_thread_safety_during_batch() - Verify concurrent batch operations
13. ✅ **Batch Signal Check**: Added validation step for batch_operation_started/ended signals
14. ✅ **Session Manager Check**: Added validation step for CurveDataStore in session/
15. ✅ **Multi-Curve Edge Case Test**: test_rendering_all_visible_no_active_curve() - Gap identified by comparison

**Key Risks Addressed:**
- ⚠️ Hidden dependencies in StoreManager (FrameStore sync)
- ⚠️ Hidden dependencies in SignalConnectionManager (selection sync)
- ⚠️ Hidden dependency in ConnectionVerifier (dev tool)
- ⚠️ Read-only property enforcement (explicit setters)
- ⚠️ Active curve nullability (logging for None cases)
- ⚠️ InteractionService fallbacks are critical undo/redo code
- ⚠️ Signal signature mismatches (curves_changed emits dict, selection_changed emits set+str)
- ⚠️ Thread safety during batch updates
- ⚠️ Multi-curve edge case (ALL_VISIBLE + no active curve)

**Validation Sources:**
- Python Code Reviewer Agent (implementation risks, testing gaps)
- Python Expert Architect Agent (architectural trade-offs, design analysis)
- PDF "Phase 6 Codebase Validation" (concrete measurements, exact grep patterns)

**Approval Status (October 5)**: ❌ NOT READY - Complete Phase 6.0 validation first (including 2 new tests)

---

## Amendment Summary (October 6, 2025)

**Changes Made Based on Concurrent Agent Reviews:**

### Critical Issues Addressed

1. ✅ **Signal Architecture Optimization** (Architect - HIGH severity):
   - StoreManager handlers now fetch data at sync time (not from signal args)
   - Eliminates temporal coupling / race conditions
   - Pattern: `curve_data = self._app_state.get_curve_data(active)` instead of using signal parameter

2. ✅ **StoreManager Missing Signal Connection** (Code Reviewer - Critical):
   - Added `active_curve_changed` signal connection (CRITICAL for timeline sync)
   - Previous plan only connected to `curves_changed` - would miss curve switches without data changes
   - New handler: `_on_active_curve_changed()` syncs FrameStore when switching curves

3. ✅ **Phase 6.0.5 Validation Test Suite** (Code Reviewer - High):
   - Created new phase: Phase 6.0.5 to implement test_phase6_validation.py
   - Expanded from 2 tests to 6 comprehensive validation tests
   - Tests: read-only properties (2), thread safety (1), multi-curve edge cases (2), FrameStore sync (1)
   - Makes validation concrete before proceeding to Phase 6.1

4. ✅ **DeprecationWarning Verification** (Code Reviewer - Critical):
   - Added validation step to confirm DeprecationWarnings exist in deprecated APIs
   - Prevents false positive when running `pytest -W error::DeprecationWarning`

### Testing Enhancements

5. ✅ **Validation Test Count**: Updated from 2 to 6 tests throughout document
6. ✅ **Total Test Count**: Updated from 2294 to 2297 tests (includes 6 validation tests)
7. ✅ **Test Implementation**: Full test code provided in Phase 6.0.5 section
8. ✅ **Validation Checklist**: Added test suite creation as required step before Phase 6.1

### Execution Strategy Updates

9. ✅ **Phase 6.0.5 Added**: New phase between 6.0 and 6.1 for test creation
10. ✅ **Pre-Migration Requirements**: Updated to include test suite creation and DeprecationWarning verification

### Signal Architecture Documentation

11. ✅ **Handler Pattern Documented**: StoreManager migration now shows correct pattern:
   - Fetch data at sync time (not from signal args)
   - Early exit if no active curve
   - Separate handlers for `curves_changed` vs `active_curve_changed`

### Key Risks Addressed (October 6)

- ⚠️ **Signal Architecture**: Coarse-grained emission addressed via fresh data reads at sync time
- ⚠️ **FrameStore Sync Race**: Temporal coupling eliminated by fetching current state
- ⚠️ **Missing Signal Connection**: active_curve_changed now connected in StoreManager
- ⚠️ **Validation Gap**: Test suite must be created BEFORE Phase 6.1 (not during)
- ⚠️ **DeprecationWarning False Positives**: Explicit verification step added

**Validation Sources (October 6):**
- Python Code Reviewer Agent: 21 issues identified (3 critical, 4 high, 8 medium, 1 low)
- Python Expert Architect Agent: CONDITIONAL APPROVE with critical signal architecture concerns
- Both agents agreed on: signal architecture flaw, missing signal connections, test suite gaps

**Approval Status (October 6)**: ⚠️ CONDITIONAL GO - Proceed ONLY after:
1. Phase 6.0 validation complete (all checklist items)
2. Phase 6.0.5 validation test suite created and passing (6 tests)
3. DeprecationWarnings verified to exist in deprecated APIs
4. Baseline metrics collected
---

## Amendment Summary (October 6, 2025 - Second Review)

**Changes Made Based on Second Concurrent Agent Review:**

After initial amendments, both agents (python-code-reviewer and python-expert-architect) conducted a second concurrent review of the amended plan. The code reviewer identified **4 critical execution gaps**, while the architect validated the architectural design as **EXCELLENT (5/5 stars)**.

### Critical Execution Issues Fixed

**1. ✅ Phase 6.0.5 Sequencing Contradiction** (Code Reviewer - CRITICAL)

**Problem**: Tests expected setters to raise AttributeError, but setters weren't added until Phase 6.1 Step 1 → tests would FAIL

**Fix**: Restructured Phase 6.0.5 into two parts:
- **Part A**: Implement read-only property setters (PREREQUISITE)
  - Add explicit `@curve_data.setter` and `@selected_indices.setter` that raise AttributeError
  - Prevents silent attribute shadowing (`widget.curve_data = []` creates instance attribute without error)
- **Part B**: Create validation test suite (tests now pass with setters in place)

**Why critical**: Without setters, Python allows `widget.curve_data = []` which creates `widget.__dict__['curve_data']` and shadows the property. Tests would fail, and production code could have silent bugs.

---

**2. ✅ timeline_tabs.py Migration Missing from Plan** (Code Reviewer - CRITICAL)

**Problem**: Plan mentioned timeline_tabs.py but lacked detailed migration steps for its **6 CurveDataStore signal connections** (lines 338-343):
```python
self._curve_store.data_changed.connect(...)
self._curve_store.point_added.connect(...)
self._curve_store.point_updated.connect(...)
self._curve_store.point_removed.connect(...)
self._curve_store.point_status_changed.connect(...)
self._curve_store.selection_changed.connect(...)
```

**Fix**: Added **Step 8.5** in Phase 6.1 with complete migration:
- Consolidate all 6 handlers into single `_on_app_state_curves_changed()` handler
- Connect to `ApplicationState.curves_changed`
- Delete 6 old handler methods
- Use handler re-fetch pattern (fetch data at sync time, not from signal args)

**Impact**: Without this migration, timeline would BREAK when CurveDataStore is deleted in Phase 6.1 Step 5.

---

**3. ✅ DeprecationWarnings Don't Exist in Codebase** (Code Reviewer - CRITICAL)

**Problem**: Plan assumed DeprecationWarnings existed, but grep found **ZERO** `warnings.warn()` calls. Validation would pass falsely.

**Current State** (verified):
```bash
$ grep -r "warnings\.warn.*DeprecationWarning" --include="*.py" .
# No matches found
```

**Fix**: Split Phase 6.0 Step 1 into two steps:
- **Step 1a**: ADD DeprecationWarnings to deprecated APIs (widget.curve_data, main_window.curve_view, timeline_tabs.frame_changed)
- **Step 1b**: THEN enforce as errors with `pytest -W error::DeprecationWarning`

**Why critical**: Without this fix, `pytest -W error::DeprecationWarning` would pass with ZERO warnings (false positive), giving false confidence that migration is safe.

---

**4. ✅ File Count Inaccuracy** (Code Reviewer - Medium)

**Fix**: Updated file count from **15 → 16 production files**
- Added: `ui/timeline_tabs.py` with detailed migration requirements
- Corrected: `services/interaction_service.py` and `ui/menu_bar.py` were already listed

---

### Architectural Validation (Architect Review)

**Verdict**: **CONDITIONAL APPROVE** ✅

**Architecture Quality**: EXCELLENT ⭐⭐⭐⭐⭐

**Key Architectural Validations**:

1. ✅ **Single Source of Truth Pattern**: ApplicationState correctly applied
2. ✅ **Signal Architecture Design**: Coarse-grained signals with re-fetch pattern is **OPTIMAL**
   - Handler re-fetch eliminates temporal coupling
   - Batch mode deduplication works correctly
   - Fresh reads ensure thread safety
3. ✅ **Dual Signal Connection Requirement**: BOTH `curves_changed` AND `active_curve_changed` confirmed necessary
4. ✅ **Thread Safety Design**: Two-phase locking prevents deadlock
5. ✅ **Risk-First Execution Strategy**: Correct approach for clean rollback
6. ✅ **Read-Only Property Pattern**: Pythonic for migration purposes
7. ✅ **Comprehensive Validation Strategy**: Systematic and thorough

**Confidence Level**: 85-90% success probability (excellent with recommended additions)

---

### Optional Enhancements Added

**5. ✅ Integration Test Recommendations** (Architect - Recommended)

Added 4 optional integration tests to Phase 6.0.5 (raises confidence 85% → 90%):
- `test_batch_signal_deduplication()` - Verify 1 signal for N operations
- `test_selection_bidirectional_sync()` - Widget ↔ tracking_controller sync
- `test_undo_redo_integration_post_migration()` - CommandManager still works
- `test_session_save_restore_post_migration()` - Session persistence without CurveDataStore

**Status**: Recommended but not required (6 required tests provide adequate coverage)

---

### Updated Validation Checklist

**Phase 6.0 Checklist** (13 items - updated from 12):
- [ ] DeprecationWarnings ADDED (new step)
- [ ] DeprecationWarnings VERIFIED (warnings appear)
- [ ] DeprecationWarnings RESOLVED (tests pass)
- [ ] 0 production writes verified
- [ ] Signal connections audited
- [ ] Batch signals checked
- [ ] CommandManager sole undo
- [ ] Session manager clean
- [ ] StoreManager migration planned
- [ ] SignalConnectionManager migration planned
- [ ] **timeline_tabs.py migration planned** (NEW)
- [ ] ConnectionVerifier migration planned
- [ ] Baseline metrics collected

**Phase 6.0.5 Exit Criteria** (updated):

**Part A** (setters - PREREQUISITE):
- [ ] Both setters implemented
- [ ] Manual verification: raises AttributeError

**Part B** (tests):
- [ ] File created: test_phase6_validation.py
- [ ] 6 required tests implemented and passing
- [ ] 4 optional integration tests (recommended)
- [ ] Integrated into pytest suite

---

### Key Findings from Second Review

**Code Reviewer Verdict**: ❌ NO-GO (execution readiness)
- Plan quality: EXCELLENT
- Current state: Prerequisites not met (0% of Phase 6.0 complete)
- All issues: FIXABLE by executing Phase 6.0 checklist
- test_phase6_validation.py: Does not exist yet
- DeprecationWarnings: Not implemented yet
- Read-only setters: Not implemented yet

**Architect Verdict**: ✅ CONDITIONAL APPROVE (design quality)
- Architecture: EXCELLENT (5/5 stars)
- Signal design: Sound and well-reasoned
- Migration strategy: Correct
- Thread safety: Properly implemented
- No anti-patterns identified

**Reconciliation**: Both verdicts are CORRECT from different perspectives:
- **Design** (Architect): Architecture excellent, migration strategy sound
- **Process** (Code Reviewer): Prerequisites not met, can't execute Phase 6.1 safely yet

---

### Verification Summary

All Code Reviewer claims were **verified via grep/symbol search**:

✅ **timeline_tabs.py**: 6 signal connections found at lines 338-343
✅ **Zero DeprecationWarnings**: No `warnings.warn()` calls in codebase
✅ **No read-only setters**: Property has no `@curve_data.setter` defined
✅ **Signal signature mismatch**: ApplicationState emits `""` not `None` (low priority)

No contradictions found between agents - verdicts evaluate different dimensions.

---

### Updated Approval Status

**STATUS**: ⚠️ **CONDITIONAL GO** - Plan is EXCELLENT but prerequisites must be executed first

**Path to GO**:
1. ✅ Execute Phase 6.0 checklist (13 items including DeprecationWarning addition)
2. ✅ Execute Phase 6.0.5 Part A (add read-only setters)
3. ✅ Execute Phase 6.0.5 Part B (create test suite - 6 required + 4 recommended)
4. ✅ Verify all tests pass
5. ✅ Collect baseline metrics
6. → **THEN** proceed to Phase 6.1 CurveDataStore removal

**Files Modified in This Amendment**:
- PHASE_6_DEPRECATION_REMOVAL_PLAN.md (6 edits)
  - Phase 6.0.5: Restructured into Part A (setters) + Part B (tests)
  - Phase 6.1 Step 8.5: Added timeline_tabs.py migration
  - Phase 6.0 Step 1: Split into 1a (add warnings) + 1b (enforce)
  - File count: Updated 15 → 16 production files
  - Validation checklist: Updated with 3-step DeprecationWarning process + timeline_tabs.py
  - Optional tests: Added 4 integration test recommendations


- Python Code Reviewer Agent: 21 issues (4 critical execution gaps)
- Python Expert Architect Agent: CONDITIONAL APPROVE (architecture excellent)
- Systematic verification via Grep, mcp__serena__find_symbol, Read tools



---

## Amendment Summary (October 6, 2025 - Verification & Corrections)

**Changes Made Based on Systematic Verification:**

After concurrent agent reviews, performed systematic verification of all major claims using grep, mcp__serena__find_symbol, and direct code inspection. Found several discrepancies requiring corrections.

### Critical Corrections Made

**1. ✅ Reference Count Corrected** (Impact Analysis + totals)

**Agent Claims:**
- Code Reviewer: 442 references (INCORRECT - included archive_legacy)
- Plan Original: 304 references (undercount)

**Verified Actual:**
- Total `.curve_data`: 352 references (69 production, 283 tests)
- Excludes archive_legacy directory

**Changes:**
- Line 16: Updated from "304 `.curve_data`" → "352 `.curve_data` (69 prod, 283 tests)"
- Line 27: Updated total count with breakdown

---

**2. ✅ DeprecationWarning Status Clarified** (Phase 6.0 Step 1)

**Code Reviewer Claim:** "ZERO warnings.warn() calls" (INCORRECT)

**Verified Actual:**
- ✅ `timeline_tabs.frame_changed` - Already has DeprecationWarning (line 675-680)
- ❌ `widget.curve_data` - No warning yet
- ❌ `main_window.curve_view` - No warning yet

**Changes:**
- Lines 43-80: Updated to reflect 1 of 3 APIs already has warning
- Checklist updated: Add warnings to 2 APIs (not 3)
- Added "Current State (verified)" section showing existing warnings

---

**3. ✅ StateSyncController Count Clarified** (Phase 6.1 Step 3)

**Plan Original:** "Remove 10 methods" (misleading - mixed connections with methods)

**Verified Actual:**
- 7 signal connections (lines 72-80 in state_sync_controller.py)
- Includes 1 duplicate: data_changed connected twice (lines 72, 80)

**Changes:**
- Lines 501-522: Restructured to show:
  - 7 numbered signal connections with line numbers
  - Separate list of methods to remove
  - Note about duplicate data_changed connection
  - Reminder to verify DataService dependency

---

**4. ✅ Signal Handler Compatibility Verified** (Phase 6.1 Step 7)

**Code Reviewer Claim:** "Handler signatures need updating" (INCORRECT)

**Verified Actual:**
- Handlers ALREADY accept `(set[int], str | None)` signature
- Updated in Phase 4 with optional curve_name parameter
- No migration needed

**Changes:**
- Lines 600-609: Added note that handlers are already compatible
- Documented existing handler signatures
- Marked with ✅ to indicate no action needed

---

**5. ✅ Active Curve Signal Behavior Documented** (Phase 6.1 Step 6)

**Code Reviewer Finding:** Signal emits `""` when None (CORRECT)

**Verified:**
```python
# stores/application_state.py:603
self._emit(self.active_curve_changed, (curve_name or "",))
```

**Changes:**
- Lines 577-579: Added NOTE in _on_active_curve_changed handler
- Documented that signal emits "" (empty string) when None
- Explained that `if curve_name:` catches both None and "" (both falsy)

---

### Verification Methodology

All claims verified using:
1. **Grep**: Pattern searches for signal connections, references
2. **mcp__serena__find_symbol**: Code structure inspection
3. **Direct file reading**: Confirmation of exact line numbers

**Discrepancies Resolved:**
- ❌ Code Reviewer: Reference count too high (442 vs 352)
- ❌ Code Reviewer: Claimed zero warnings (actually 1 exists)
- ❌ Code Reviewer: Handler signature issue (actually already fixed)
- ✅ Code Reviewer: Active curve signal behavior (CORRECT)
- ✅ Code Reviewer: Timeline tabs 6 connections (CORRECT)
- ⚠️ Plan: StateSyncController count unclear (clarified as 7 connections)

---

### Updated Approval Status (Post-Verification)

**STATUS**: ⚠️ **CONDITIONAL GO** - Plan architecture is EXCELLENT (95/100), corrections applied

**Confidence:**
- Architect Review: 95/100 (architecture sound)
- Code Reviewer: Partially correct (70% after verification)
- Overall: 85% success probability with corrections

**Path Forward:**
1. ✅ Corrections applied to plan
2. ✅ All claims systematically verified
3. → Execute Phase 6.0 validation checklist (now accurate)
4. → Execute Phase 6.0.5 test suite
5. → Proceed to Phase 6.1 with confidence

**Files Modified:**
- PHASE_6_DEPRECATION_REMOVAL_PLAN.md (5 corrections)
  - Impact Analysis: Reference count corrected (352 not 304/442)
  - Phase 6.0 Step 1: DeprecationWarning status clarified (2 to add, 1 exists)
  - Phase 6.1 Step 3: StateSyncController connections detailed (7 numbered)
  - Phase 6.1 Step 6: Active curve signal behavior documented
  - Phase 6.1 Step 7: Handler compatibility verified (no changes needed)

**Validation Sources:**
- Systematic grep verification (reference counts, signal connections)
- mcp__serena__find_symbol (handler signatures, signal definitions)
- Direct code inspection (line-by-line confirmation)

**Key Insight:** Concurrent agent reviews are valuable but must be verified systematically. Code Reviewer identified real issues (active_curve signal, timeline_tabs) but made factual errors on counts and handler compatibility. Architect correctly assessed architecture quality but didn't verify implementation details.

---

**Amendment Date**: October 6, 2025
**Amendment Author**: Claude Code (verification analysis)
**Status**: AMENDED - Ready for Phase 6.0 execution with verified scope
