# API Compatibility Verification Report
## StateManager.active_timeline_point vs ApplicationState.active_curve

**Project**: CurveEditor  
**Date**: November 2025  
**Task**: Verify ApplicationState.active_curve can replace StateManager.active_timeline_point WITHOUT breaking changes

---

## EXECUTIVE SUMMARY

**VERDICT**: ✅ **VERIFIED WITH CRITICAL ISSUES** - APIs can be consolidated, BUT **2 critical bugs must be fixed** before safe migration.

**Status**: 
- Getter/Setter API: Replaceable (expected breaking changes acknowledged in plan)
- Signal emissions: **🔴 CRITICAL MISMATCH** - ApplicationState converts `None→""`, breaks handlers
- Type safety: **🟡 DEGRADED** - Existing `frame_change_coordinator.py` has uncaught type bug

**Action Required**: Fix ApplicationState signal emission to preserve `None` type before consolidation.

---

## 1. API SIGNATURE COMPARISON

### StateManager (ui/state_manager.py:280-290)
```python
@property
def active_timeline_point(self) -> str | None:
    """Get the active timeline point name."""
    return self._active_timeline_point

@active_timeline_point.setter
def active_timeline_point(self, point_name: str | None) -> None:
    """Set the active timeline point name."""
    if self._active_timeline_point != point_name:
        self._active_timeline_point = point_name
        self._emit_signal(self.active_timeline_point_changed, point_name)  # ← Emits raw value
```

**Signal** (line 58):
```python
active_timeline_point_changed: Signal = Signal(object)  # Emits str | None (raw, no conversion)
```

**Emission Pattern**: `point_name` emitted as-is (None stays None, str stays str)

---

### ApplicationState (stores/application_state.py:612-632)
```python
@property
def active_curve(self) -> str | None:
    """Get name of active curve."""
    return self._active_curve

def set_active_curve(self, curve_name: str | None) -> None:
    """Set active curve."""
    self._assert_main_thread()
    if self._active_curve != curve_name:
        old_curve = self._active_curve
        self._active_curve = curve_name
        self._emit(self.active_curve_changed, (curve_name or "",))  # ← CONVERTS None→""
        logger.info(f"Active curve changed: '{old_curve}' -> '{curve_name}'")
```

**Signal** (line 116):
```python
active_curve_changed: Signal = Signal(str)  # Emits str only (NEVER None)
```

**Emission Pattern**: `(curve_name or "")` converts `None→""`

---

## 2. CRITICAL INCOMPATIBILITY: Signal Type Mismatch

### The Problem

StateManager and ApplicationState emit different types for the "no active" state:

| Scenario | StateManager | ApplicationState |
|----------|-------------|-----------------|
| `set(None)` called | Emits: `None` (type: `None`) | Emits: `""` (type: `str`) |
| Getter returns | `None` | `None` |
| Handler receives | `None` | `""` |

### Code Evidence

**ApplicationState line 630** (stores/application_state.py):
```python
self._emit(self.active_curve_changed, (curve_name or "",))
```

The `(curve_name or "")` expression:
- If `curve_name = None`: emits `("")` → handler receives `""`
- If `curve_name = "Track1"`: emits `("Track1",)` → handler receives `"Track1"`
- **Never emits `None`** because `None or "" = ""`

**StateManager line 289** (ui/state_manager.py):
```python
self._emit_signal(self.active_timeline_point_changed, point_name)
```

Direct emission:
- If `point_name = None`: emits `None` → handler receives `None`
- If `point_name = "Track1"`: emits `"Track1"` → handler receives `"Track1"`
- **Preserves `None`** as-is

---

## 3. MIGRATION IMPACT ANALYSIS

### 3.1 Setter Call Sites (15 total)

**Current Pattern**: Property assignment
```python
main_window.active_timeline_point = point_name  # or state_manager.active_timeline_point = ...
```

**After Migration**: Method call
```python
get_application_state().set_active_curve(point_name)
```

**Call Sites**:
1. `ui/controllers/tracking_data_controller.py` - 5+ assignments
2. `ui/controllers/tracking_selection_controller.py` - 2+ assignments
3. `core/commands/insert_track_command.py` - 1 assignment
4. `ui/main_window.py` - 1 assignment (proxies to StateManager)
5. Test files - Several assignments

**Impact**: 🔴 **BREAKING** - All setter call sites must be updated

---

### 3.2 Getter Call Sites (19 files)

**Current Pattern**:
```python
point = main_window.active_timeline_point
if point == "Track1":
    ...
```

**After Migration**: Via MainWindow proxy OR direct ApplicationState access
```python
point = get_application_state().active_curve
if point == "Track1":
    ...
```

**Impact**: 🟡 **MANAGEABLE** - Getter logic unchanged, just source changes

---

### 3.3 Signal Connections (7 total)

**Current**:
```python
state_manager.active_timeline_point_changed.connect(handler)
```

**After**:
```python
get_application_state().active_curve_changed.connect(handler)
```

**Signal Connection Sites**:
1. `ui/timeline_tabs.py` (line 310) - Main handler
2. `ui/controllers/signal_connection_manager.py` - Status update
3. `ui/controllers/frame_change_coordinator.py` - Centering
4. Test files - Multiple connections

**Impact**: 🔴 **BREAKING** - All connections must be updated

---

## 4. CRITICAL BREAKING CHANGE #1: Signal Parameter Type

### The Issue

**Timeline Tab Handler** (ui/timeline_tabs.py:350):
```python
def _on_active_timeline_point_changed(self, point_name: str | None) -> None:
    # Current behavior: point_name can be None
    if point_name is None:  # ← This logic will BREAK
        self._on_curve_selection_cleared()
    elif point_name:
        self._update_timeline(point_name)
```

### What Breaks

When migrating to ApplicationState:
- Current code receives `None` from StateManager
- Will receive `""` (empty string) from ApplicationState
- Condition `if point_name is None:` becomes **unreachable**
- Function behavior changes silently

### Handler Logic Changes Required

```python
# ❌ BROKEN after migration
if point_name is None:  # Never true - ApplicationState sends ""
    self._on_curve_selection_cleared()

# ✅ FIXED - Works with both StateManager (None) and ApplicationState ("")
if not point_name:  # True for both None and ""
    self._on_curve_selection_cleared()
```

### All Handlers Must Change

1. **timeline_tabs.py:350** - `_on_active_timeline_point_changed()`
   - Change: `if point_name is None:` → `if not point_name:`

2. **Any other handlers checking `is None`** - Must be updated similarly

---

## 5. CRITICAL BREAKING CHANGE #2: Type Annotation Bug

### Frame Change Coordinator Mismatch

**File**: `ui/controllers/frame_change_coordinator.py`

**Current Handler**:
```python
def on_active_curve_changed(self, curve_name: str | None) -> None:
    """Handle active curve change."""
    if not self.curve_widget or not self.curve_widget.centering_mode:
        return
    # ... use curve_name
```

**Issue**: 
- Handler declares parameter type as `str | None`
- But ApplicationState ALWAYS sends `str` (never `None`)
- This is already a **latent type safety bug** in the codebase
- Type checkers (basedpyright) should flag this as violation

### Type Safety Degradation

```
Before Consolidation:
- ApplicationState handlers typed correctly (expect str)
- StateManager handlers typed correctly (expect str | None)
- Type checker: ✅ Clean

After Consolidation (without fix):
- Old StateManager handlers expect str | None
- New ApplicationState signal sends str (but declares Signal(str))
- frame_change_coordinator declares str | None (still wrong)
- Type checker: 🟡 Reports violation
```

**Fix**: Change `frame_change_coordinator.py` handler to declare `str`:
```python
def on_active_curve_changed(self, curve_name: str) -> None:  # ← Remove None option
```

---

## 6. COMPREHENSIVE MIGRATION CHECKLIST

### Phase 1: Fix ApplicationState (MUST DO FIRST)
- [ ] Change ApplicationState.set_active_curve() to emit `None` instead of `""`
  - From: `self._emit(self.active_curve_changed, (curve_name or "",))`
  - To: `self._emit(self.active_curve_changed, (curve_name,))`
- [ ] Change Signal definition to match
  - From: `Signal(str)`
  - To: `Signal(object)` OR implement optional parameter syntax
- [ ] Fix type annotations on existing handlers
  - `store_manager.py`: Add `| None` to parameter
  - `frame_change_coordinator.py`: Already declares `str | None` (remove None option)

### Phase 2: Update Handler Logic
- [ ] Update all `is None` checks to `not value` checks
  - In: `timeline_tabs.py:350`
  - Pattern: `if point_name is None:` → `if not point_name:`

### Phase 3: Migrate Setter Call Sites
- [ ] Update all 15 setter assignments
  - From: `obj.active_timeline_point = value`
  - To: `get_application_state().set_active_curve(value)`

### Phase 4: Migrate Signal Connections
- [ ] Update all 7 signal connections
  - From: `state_manager.active_timeline_point_changed.connect(handler)`
  - To: `get_application_state().active_curve_changed.connect(handler)`

### Phase 5: Test & Validation
- [ ] Run full test suite: `pytest tests/ -xv`
- [ ] Type checking: `./bpr` (should be clean)
- [ ] Manual testing of curve switching scenarios

---

## 7. DETAILED CHANGE REQUIREMENTS

### 7.1 ApplicationState Signal Fix (stores/application_state.py:630)

**Current**:
```python
def set_active_curve(self, curve_name: str | None) -> None:
    ...
    self._emit(self.active_curve_changed, (curve_name or "",))  # ← Converts None→""
```

**Fixed**:
```python
def set_active_curve(self, curve_name: str | None) -> None:
    ...
    self._emit(self.active_curve_changed, (curve_name,) if curve_name is not None else (None,))
    # OR more simply:
    self._emit(self.active_curve_changed, (curve_name,))
```

**Also update Signal definition** (line 116):
```python
# Option A: Flexible Signal type
active_curve_changed: Signal = Signal(object)  # Emits str | None

# Option B: Keep Signal(str) but fix handlers to accept Optional
# (requires updating all handler types)
```

### 7.2 Timeline Tabs Handler Fix (ui/timeline_tabs.py:350)

**Current**:
```python
def _on_active_timeline_point_changed(self, point_name: str | None) -> None:
    if point_name is None:
        self._on_curve_selection_cleared()
    elif point_name:
        self._update_timeline(point_name)
```

**Fixed** (works with both StateManager and ApplicationState):
```python
def _on_active_timeline_point_changed(self, point_name: str | None) -> None:
    if not point_name:  # Works with None OR ""
        self._on_curve_selection_cleared()
    else:
        self._update_timeline(point_name)
```

### 7.3 Frame Change Coordinator Fix (ui/controllers/frame_change_coordinator.py)

**Current** (type mismatch):
```python
def on_active_curve_changed(self, curve_name: str | None) -> None:  # Won't receive None from ApplicationState!
```

**Option A** - Remove None (if ApplicationState fixed to never send None):
```python
def on_active_curve_changed(self, curve_name: str) -> None:
    # curve_name is guaranteed str (never None after ApplicationState fix)
```

**Option B** - Keep defensive typing (handles both StateManager and ApplicationState):
```python
def on_active_curve_changed(self, curve_name: str | None) -> None:
    if not curve_name:
        return  # No active curve
    # Use curve_name
```

---

## 8. TESTING IMPACT

### Test Updates Required

Files with signal connections that need testing:
1. `tests/controllers/test_tracking_*` - Tracking controller tests
2. `tests/test_*navigation*.py` - Navigation tests
3. `tests/test_*tracking*.py` - Multi-point tracking tests

### Test Scenarios to Validate

1. **Setter behavior**:
   ```python
   get_application_state().set_active_curve(None)
   # Should emit active_curve_changed(None)
   # NOT active_curve_changed("")
   ```

2. **Handler receives correct type**:
   ```python
   received_values = []
   get_application_state().active_curve_changed.connect(lambda v: received_values.append(v))
   
   get_application_state().set_active_curve(None)
   assert received_values[-1] is None  # Not ""
   
   get_application_state().set_active_curve("Track1")
   assert received_values[-1] == "Track1"
   ```

3. **Timeline tab behavior**:
   ```python
   # Clearing active curve should clear timeline
   # Whether signal sends None or "" should have same effect
   ```

---

## 9. VERIFICATION CHECKLIST

### Before Migration

- [ ] ApplicationState signal fixed to emit `None` (not `""`)
- [ ] Signal definition updated: `Signal(object)` or parameterized optional
- [ ] All handler signatures reviewed for type safety
- [ ] Timeline tabs handler updated: `is None` → `not value`
- [ ] Frame change coordinator type annotation fixed
- [ ] Full test suite passing: `pytest tests/ -xv`
- [ ] Type checking clean: `./bpr` with no errors

### After Migration

- [ ] All 15 setter call sites updated
- [ ] All 7 signal connections updated
- [ ] All 19 getter call sites updated (via MainWindow proxy or direct)
- [ ] Full test suite passing
- [ ] Type checking clean
- [ ] Manual testing: Curve switching works correctly
- [ ] StateManager.active_timeline_point removed from codebase

---

## 10. FINAL VERDICT

### ✅ CONCLUSION: **VERIFIED - CONSOLIDATION POSSIBLE WITH FIXES**

**Current Status**:
- ❌ APIs incompatible as currently implemented
- ❌ ApplicationState has silent type bug
- ❌ Signal emission converts `None→""` (breaks handlers)

**After Proposed Fixes**:
- ✅ ApplicationState signal emits correct type
- ✅ All handler type annotations correct
- ✅ Safe consolidation path clear
- ✅ Type checker clean

**Critical Path Items**:
1. Fix ApplicationState.set_active_curve() signal emission
2. Update handler logic: `is None` → `not value`
3. Migrate all 15 setter call sites
4. Migrate all 7 signal connections
5. Verify no type checker violations

**Estimated Effort**: 3-4 hours (including tests)

**Risk Level**: Medium (type safety bugs must be fixed first)

---

## APPENDIX: Code References

### Signal Emission (ApplicationState)
**File**: stores/application_state.py, Line 630
```python
self._emit(self.active_curve_changed, (curve_name or "",))
```
🔴 **Issue**: Converts None to empty string

### Signal Definition (ApplicationState)
**File**: stores/application_state.py, Line 116
```python
active_curve_changed: Signal = Signal(str)
```
🔴 **Issue**: Declares `str` only, but should be `str | None`

### Current Handler (Timeline Tabs)
**File**: ui/timeline_tabs.py, Lines 350+
```python
def _on_active_timeline_point_changed(self, point_name: str | None) -> None:
    if point_name is None:  # ← Will break with ApplicationState
```
🔴 **Issue**: Handler logic incompatible with ApplicationState emission

### Type Mismatch (Frame Change Coordinator)
**File**: ui/controllers/frame_change_coordinator.py
```python
def on_active_curve_changed(self, curve_name: str | None) -> None:
    # Will never receive None from ApplicationState!
```
🟡 **Issue**: Type annotation incorrect (should be `str` only)

