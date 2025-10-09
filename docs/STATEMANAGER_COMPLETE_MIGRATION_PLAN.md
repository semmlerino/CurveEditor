# StateManager Complete Migration Plan - Option A (Amended)

## Executive Summary

**Status**: ✅ **AMENDED #8** - All blockers fixed, migration is COMPLETE (including _original_data), ready for execution

**Goal**: Complete the StateManager migration by moving **ALL** application data to ApplicationState and establishing StateManager as a **pure UI preferences layer**.

**Root Cause**: StateManager is a hybrid containing both application data (track_data, image_files, _original_data) and UI state (zoom, tool, window). This creates:
- **Data in wrong layer** (violates "single source of truth" - data should be in ApplicationState)
- **Thread safety gaps** (ApplicationState has mutex, StateManager doesn't)
- **Risk of inconsistent signals** (if signals were added to both layers for same data)

**Solution**: Follow FrameChangeCoordinator pattern - fix root cause, not symptoms.

**Timeline**: 55-69 hours over 4-5 weeks (includes complete migration + optimizations)

**Amendments** (2025-10-07):
- **16:30** - Fixed method naming errors (`active_curve` property vs `get_active_curve_name()`)
- **16:30** - Fixed thread safety pattern (use `_assert_main_thread()` + `_emit()`, not explicit mutex)
- **16:30** - Optimized with cached `self._app_state` references
- **16:30** - Added Phase 0 for pre-implementation verification
- **16:30** - Documented `_original_data` deferral to future phase
- **18:00** - **CRITICAL**: Fixed `curves_changed` signal specification (dict, not str)
- **18:00** - Fixed file path references (`data/data_operations.py` → `services/data_service.py`)
- **18:00** - Updated signal connection examples to handle dict payload

**Amendments** (2025-10-08):
- **19:00** - **CRITICAL**: Fixed `_emit_signal` API usage (pass Signal instance, not string name)
- **19:00** - **CRITICAL**: Fixed toolbar button references (use `action_undo`/`action_redo`, not nonexistent `ui.toolbar.undo_button`)
- **19:00** - Added verification checklists with line numbers to Phases 1, 2, and 4
- **19:00** - Updated test examples to use correct QAction API
- **21:00** - **CRITICAL**: Fixed `active_curve=None` edge case (auto-create `__default__` curve)
- **21:00** - Added `current_frame.setter` update to Phase 2 (use property, not field)
- **21:00** - Fixed test file path (`tests/test_state_manager.py` not `tests/ui/`)
- **21:00** - Reframed "duplicate signals" claim (prevents future duplication, not removing existing)
- **21:00** - Added phase dependency warning (Phases 1-2 must complete together)

**Amendments** (2025-10-09):
- **TBD** - **Amendment #5**: Tri-agent review synthesis (service layer integration, risk assessment, timeline buffer)
- **TBD** - **Amendment #6 (CRITICAL)**: Thread safety clarification, grep pattern fixes, migration example corrections, safety layer
- **TBD** - **Amendment #7 (BLOCKER)**: Tri-agent verification - Added Phase 0.4 to implement missing ApplicationState methods (6-8h), fixed thread safety docs line 1035, updated timeline to 43-54h
- **TBD** - **Amendment #8 (COMPLETE MIGRATION)**: Fixed all blockers - Fail fast (no auto-create), fix Phase 1-2 dependency, complete _original_data migration (Phase 2.5), lazy signal payload, batch rollback, updated timeline to 52-66h
- **TBD** - **Amendment #9 (VERIFICATION FIXES)**: Tri-agent verification - Fixed hasattr() anti-pattern, type inconsistencies, clarified sequencing, removed "already fixed" claims, made safety layer mandatory, updated timeline to 55-69h

---

## Architectural Principles

### Principle 1: Clear Layer Separation

```
ApplicationState (Data Layer)
├─ Curve data (track_data, curve points)
├─ Image sequence (image files, directory)
├─ Frame state (current frame, total frames)
└─ Selection state (selected curves, points)

DataService (Service Layer)
├─ File I/O operations
├─ Image loading/management
└─ Data transformations

StateManager (UI Preferences Layer) ✨ THIS IS THE GOAL
├─ View state (zoom, pan, bounds)
├─ Tool state (current tool, smoothing params)
├─ Window state (position, sizes, fullscreen)
├─ Session state (recent directories)
└─ History UI state (can_undo, can_redo)
```

### Principle 2: Single Signal Source per Data Type

**Current Issue**: StateManager stores data but doesn't emit data-change signals. This means:
- Data changes are invisible to UI components
- Future developers might add signals to both layers, creating duplication

**After Migration** (Clean):
```python
ApplicationState.curves_changed     # ONLY signal for curve data ✅
StateManager.view_state_changed     # ONLY signal for view state ✅
StateManager.tool_state_changed     # ONLY signal for tool state ✅
```

**Note**: StateManager does NOT currently have `track_data_changed` signal. This migration **prevents** future signal duplication by moving data to correct layer.

### Principle 3: Thread Safety by Layer

- **ApplicationState**: Main-thread only (enforced by `_assert_main_thread()`) - services must call from main thread or use Qt signals for cross-thread communication
- **StateManager**: Main-thread only - UI preferences don't need cross-thread access

**Note**: ApplicationState has a QMutex, but it ONLY protects the batch flag (see `_emit()` implementation). All data access must occur on the main thread. Services running in background threads must use Qt signals to communicate with ApplicationState.

---

## Current State Analysis

### Properties Correctly in StateManager ✅ (12)

| Property | Type | Signal | Notes |
|----------|------|--------|-------|
| `zoom_level` | UI state | `view_state_changed` | ✅ Correct |
| `pan_offset` | UI state | `view_state_changed` | ✅ Correct |
| `view_bounds` | UI state | `view_state_changed` | ✅ Correct |
| `current_tool` | UI state | None → ADD | ⚠️ Needs signal |
| `hover_point` | UI state | None (intentional) | ✅ Performance opt |
| `smoothing_window_size` | UI state | None | ✅ Write-only |
| `smoothing_filter_type` | UI state | None | ✅ Write-only |
| `window_position` | Session | None | ✅ Session only |
| `splitter_sizes` | Session | None | ✅ Session only |
| `is_fullscreen` | Session | None | ✅ Session only |
| `recent_directories` | Session | None | ✅ Session only |
| `tool_options` | UI state | None | ✅ Write-only |

### Properties to MIGRATE ❌ (5)

| Property | Current Location | Correct Location | Reason |
|----------|-----------------|------------------|--------|
| `track_data` | StateManager | **ApplicationState** | Curve data (application state) |
| `image_files` | StateManager | **ApplicationState** | Image sequence (application state) |
| `image_directory` | StateManager | **ApplicationState** | Image sequence root |
| `total_frames` | StateManager | **ApplicationState** | Derived from image_files |
| `_original_data` | StateManager | **ApplicationState** | Original curve data (application state) - **Phase 2.5** |

### Properties to ADD Signals ✅ (3)

| Property | Location | Signal to Add | Priority |
|----------|----------|---------------|----------|
| `can_undo` | StateManager | `undo_state_changed` | 🔴 Critical |
| `can_redo` | StateManager | `redo_state_changed` | 🔴 Critical |
| `current_tool` | StateManager | `tool_state_changed` | 🟡 Important |

### File State Properties (Already Correct) ✅ (3)

| Property | Location | Signal | Notes |
|----------|----------|--------|-------|
| `current_file` | StateManager | `file_changed` | ✅ UI state (current file path) |
| `is_modified` | StateManager | `modified_changed` | ✅ UI state (dirty flag) |
| `file_format` | StateManager | None | ✅ Write-only |

---

## Migration Plan: 5 Phases

### Phase 0: Pre-Implementation Fixes (10.5-12.5 hours)

**CRITICAL**: Implement missing methods and fix bugs identified in tri-agent review before starting migration.

**⚠️ SEQUENCING**: Steps 0.1-0.3 must complete BEFORE Phase 1 can begin. Phase 0.4 must complete BEFORE Phase 2 can begin.

#### 0.1 Verify Method Names

**Issue**: Plan references `get_active_curve_name()` which doesn't exist in ApplicationState.

**Actual code**: `@property active_curve` (application_state.py:607-610)

**Fix**: Use `self.active_curve` throughout (not `get_active_curve_name()`)

#### 0.2 Understand Thread Safety Pattern

**ApplicationState threading model**:
- **Main-thread ONLY** (enforced by `_assert_main_thread()`)
- **Mutex ONLY protects batch flag** (not data)
- **Never use explicit mutex.lock()/unlock()** for data operations

**Correct pattern**:
```python
def set_data(self, data):
    self._assert_main_thread()  # ✅ Enforce main thread
    self._data = data           # Direct assignment (no mutex)
    self._emit(self.signal, ())  # ✅ Uses mutex internally for batch flag
```

**Wrong pattern** (DO NOT USE):
```python
def set_data(self, data):
    self._mutex.lock()  # ❌ WRONG - This is for batch flag only
    try:
        self._data = data
        if not self._batch_mode:
            self.signal.emit()
    finally:
        self._mutex.unlock()
```

#### 0.3 Add Missing Declarations

**Add to ApplicationState (these will be added in Phase 2)**:

In `stores/application_state.py`, after existing signals (~line 141):
```python
# Image sequence signal (added in Phase 2 migration)
image_sequence_changed: Signal = Signal()  # Emits when image files/directory changes
```

In `ApplicationState.__init__()` (~line 166):
```python
# Image sequence state (added in Phase 2 migration)
self._image_files: list[str] = []
self._image_directory: str | None = None
self._total_frames: int = 1
```

In StateManager (~line 46, added in Phase 3):
```python
# History UI state signals (added in Phase 3)
undo_state_changed: Signal = Signal(bool)  # Emits can_undo
redo_state_changed: Signal = Signal(bool)  # Emits can_redo
tool_state_changed: Signal = Signal(str)   # Emits tool name
```

**Checklist**:
- [ ] Verified `active_curve` is property, not method
- [ ] Understood thread safety pattern (`_assert_main_thread` + `_emit`)
- [ ] Located where to add signal definitions
- [ ] Located where to add instance variables
- [ ] Read `_emit()` implementation (application_state.py:980-991)

#### 0.4 Fix hasattr() Anti-Pattern (1 hour)

**🔴 CRITICAL**: The plan uses `hasattr()` for attribute checking, which violates CLAUDE.md best practices.

**File**: `stores/application_state.py`

**Fix in `__init__`** (~line 166):
```python
# Add to ApplicationState.__init__() - initialize _original_data
self._original_data: dict[str, CurveDataList] = {}
```

**Then remove all hasattr() checks** (will be in Phase 2.5 code):
```python
# Phase 2.5.1 - set_original_data (NO hasattr check)
def set_original_data(self, curve_name: str, data: CurveDataInput) -> None:
    self._assert_main_thread()
    self._original_data[curve_name] = list(data)  # Direct access
    logger.debug(f"Stored original data for '{curve_name}': {len(data)} points")

# Phase 2.5.1 - get_original_data (NO hasattr check)
def get_original_data(self, curve_name: str) -> CurveDataList:
    self._assert_main_thread()
    return self._original_data.get(curve_name, []).copy()

# Phase 2.5.1 - clear_original_data (NO hasattr check)
def clear_original_data(self, curve_name: str | None = None) -> None:
    self._assert_main_thread()
    if curve_name is None:
        self._original_data.clear()
    elif curve_name in self._original_data:
        del self._original_data[curve_name]
```

**Why this matters**: Using `hasattr()` loses type information and violates the project's documented standards.

#### 0.5 Add Missing Signals to ApplicationState (2 hours)

**🔴 BLOCKER**: Phase 2 expects these signals to exist, but they don't yet.

**File**: `stores/application_state.py`

**Add signals** (after existing signals ~line 141):
```python
# Image sequence signals (added in Phase 0.5)
image_sequence_changed: Signal = Signal()  # Emits when image files/directory changes
total_frames_changed: Signal = Signal(int)  # Emits new total frames count
```

**Add instance variables** (in `__init__`, ~line 166):
```python
# Image sequence state (added in Phase 0.5)
self._image_files: list[str] = []
self._image_directory: str | None = None
self._total_frames: int = 1
```

**Checklist**:
- [ ] Added `image_sequence_changed` signal declaration
- [ ] Added `total_frames_changed` signal declaration
- [ ] Added `_image_files` instance variable
- [ ] Added `_image_directory` instance variable
- [ ] Added `_total_frames` instance variable

#### 0.6 Implement Missing ApplicationState Methods (6-8 hours)

**🔴 BLOCKER**: Phase 1.2 creates delegation properties that call these methods, but they don't exist yet. They must be implemented FIRST.

**File**: `stores/application_state.py`

**Missing methods** (verified via grep - zero matches found):
- `set_track_data(data)` - Set data for active curve
- `get_track_data()` - Get data for active curve
- `has_data` property - Check if active curve has data
- `set_image_files(files, directory)` - Set image sequence
- `get_image_files()` - Get image sequence
- `get_image_directory()` - Get image directory
- `get_total_frames()` - Get frame count

**Implementation** (add after existing curve methods, ~line 280):

```python
# ==================== Single-Curve Convenience Methods ====================
# These methods provide backward-compatible single-curve API during migration.
# They delegate to multi-curve methods using the active curve.
#
# ⚠️ DEPRECATION NOTICE: These methods create a dual API (violates PEP 20).
# Mark as deprecated immediately. Plan removal in Phase 5 (6-12 months post-migration).
# Prefer explicit curve_name: use set_curve_data(curve_name, data) instead.

def set_track_data(self, data: CurveDataInput) -> None:
    """
    Set data for active curve (single-curve convenience method).

    Args:
        data: List of (x, y) tuples or CurvePoint sequence

    Raises:
        ValueError: If data is empty list, invalid format, or exceeds size limit
        TypeError: If data is not a sequence

    Note: Prefer set_curve_data(curve_name, data) for explicit multi-curve workflows.
    """
    self._assert_main_thread()

    # Validation: Type check
    if not isinstance(data, (list, tuple)):
        raise TypeError(f"data must be list or tuple, got {type(data).__name__}")

    # Validation: Size limit (prevent resource exhaustion)
    MAX_POINTS = 100_000  # Reasonable limit for single curve
    if len(data) > MAX_POINTS:
        raise ValueError(f"Too many points: {len(data)} (max: {MAX_POINTS})")

    # Fail fast: No active curve is a BUG, not a use case
    active_curve = self.active_curve
    if active_curve is None:
        raise RuntimeError(
            "No active curve set. This is an initialization bug. "
            "Call set_active_curve() before set_track_data(). "
            "If you need a default curve, create it explicitly."
        )

    # Delegate to multi-curve method
    self.set_curve_data(active_curve, data)

def get_track_data(self) -> CurveDataList:
    """
    Get data for active curve (single-curve convenience method).

    Returns:
        Copy of curve data for active curve, or empty list if no active curve

    Note: Prefer get_curve_data(curve_name) for explicit multi-curve workflows.
    """
    self._assert_main_thread()
    active_curve = self.active_curve
    if active_curve is None:
        return []
    return self.get_curve_data(active_curve)

@property
def has_data(self) -> bool:
    """Check if active curve has data (single-curve convenience property)."""
    return len(self.get_track_data()) > 0


# ==================== Image Sequence Methods ====================
# NEW in Phase 0.4: Implement these BEFORE Phase 2 starts

def set_image_files(self, files: list[str], directory: str | None = None) -> None:
    """
    Set the image file sequence.

    Args:
        files: List of image file paths
        directory: Optional base directory

    Raises:
        TypeError: If files is not a list
        ValueError: If files list is too large or contains invalid paths
    """
    self._assert_main_thread()

    # Validation: Type check
    if not isinstance(files, list):
        raise TypeError(f"files must be list, got {type(files).__name__}")

    # Validation: Size limit (prevent resource exhaustion)
    MAX_FILES = 10_000
    if len(files) > MAX_FILES:
        raise ValueError(f"Too many files: {len(files)} (max: {MAX_FILES})")

    # Validation: File path types
    for f in files:
        if not isinstance(f, str):
            raise TypeError(f"File path must be str, got {type(f).__name__}")

    old_files = self._image_files
    old_dir = self._image_directory

    # Update state
    self._image_files = files.copy()
    if directory is not None:
        self._image_directory = directory

    # Update derived state
    old_total = self._total_frames
    self._total_frames = len(files) if files else 1

    # Emit signals if changed
    if old_files != self._image_files or (directory is not None and old_dir != directory):
        self._emit(self.image_sequence_changed, ())

    if old_total != self._total_frames:
        self._emit(self.total_frames_changed, (self._total_frames,))

    logger.debug(f"Image files updated: {len(files)} files, total_frames={self._total_frames}")

def get_image_files(self) -> list[str]:
    """Get the image file sequence (returns copy for safety)."""
    self._assert_main_thread()
    return self._image_files.copy()

def get_image_directory(self) -> str | None:
    """Get the image base directory."""
    self._assert_main_thread()
    return self._image_directory

def get_total_frames(self) -> int:
    """Get total frame count (derived from image sequence length)."""
    self._assert_main_thread()
    return self._total_frames
```

**Also add missing signals and instance variables** (see Phase 0.3 above):

```python
# In signal declarations (~line 141):
image_sequence_changed: Signal = Signal()
total_frames_changed: Signal = Signal(int)

# In __init__ (~line 166):
self._image_files: list[str] = []
self._image_directory: str | None = None
self._total_frames: int = 1
```

**Testing Phase 0.4**:
```python
def test_set_track_data_validates_type():
    """set_track_data raises TypeError for non-sequence."""
    state = get_application_state()
    with pytest.raises(TypeError, match="must be list or tuple"):
        state.set_track_data("not a list")  # type: ignore

def test_set_track_data_validates_size():
    """set_track_data raises ValueError for too many points."""
    state = get_application_state()
    huge_data = [(i, i) for i in range(200_000)]
    with pytest.raises(ValueError, match="Too many points"):
        state.set_track_data(huge_data)

def test_set_image_files_validates_type():
    """set_image_files raises TypeError for non-list."""
    state = get_application_state()
    with pytest.raises(TypeError, match="must be list"):
        state.set_image_files("not a list")  # type: ignore

def test_get_methods_exist():
    """Verify all convenience methods are implemented."""
    state = get_application_state()
    # Should not raise AttributeError
    _ = state.get_track_data()
    _ = state.has_data
    _ = state.get_image_files()
    _ = state.get_image_directory()
    _ = state.get_total_frames()
```

**Checklist**:
- [ ] Implemented set_track_data() with validation
- [ ] Implemented get_track_data()
- [ ] Implemented has_data property
- [ ] Implemented set_image_files() with validation
- [ ] Implemented get_image_files()
- [ ] Implemented get_image_directory()
- [ ] Implemented get_total_frames()
- [ ] Added validation tests for each method
- [ ] Run: `uv run pytest tests/stores/test_application_state.py -v`

**Why this is a blocker**: Without these methods, Phase 1.2 cannot create delegation properties that call non-existent methods.

#### 0.7 Fix current_frame.setter Dependency (1 hour)

**🔴 BLOCKER**: Current code uses `self._total_frames` field, which will be removed in Phase 2. Fix this BEFORE Phase 2 begins.

**File**: `ui/state_manager.py`

**Current code** (line ~354):
```python
@current_frame.setter
def current_frame(self, frame: int) -> None:
    """Set the current frame number (delegated to ApplicationState)."""
    frame = max(1, min(frame, self._total_frames))  # ❌ Uses field!
    self._app_state.set_frame(frame)
```

**Fixed code**:
```python
@current_frame.setter
def current_frame(self, frame: int) -> None:
    """Set the current frame number (delegated to ApplicationState)."""
    # Validation with total_frames clamping (StateManager responsibility)
    total = self._app_state.get_total_frames()  # ✅ Use ApplicationState
    frame = max(1, min(frame, total))
    # Delegate to ApplicationState for storage
    self._app_state.set_frame(frame)
    logger.debug(f"Current frame changed to: {frame}")
```

**Why this is critical**: This removes the Phase 1-2 atomic dependency. Without this fix, removing `self._total_frames` in Phase 2 will break `current_frame.setter`.

**Checklist**:
- [ ] Updated current_frame.setter to use `_app_state.get_total_frames()`
- [ ] Verified no other methods use `self._total_frames` field directly
- [ ] Run: `uv run pytest tests/ -k current_frame -v`

#### 0.8 Update Plan Type Hints (30 minutes)

**🔴 FIX DOCUMENTATION**: The plan has type inconsistencies that reduce type safety.

**Files**: This document (STATEMANAGER_COMPLETE_MIGRATION_PLAN.md)

**Find and replace**:
- ❌ `dict[str, list]` → ✅ `dict[str, CurveDataList]` (in all signal handler examples)

**Example** (line ~552):
```python
# BEFORE:
def _on_curve_data_changed(self, curves_data: dict[str, list]) -> None:

# AFTER:
def _on_curve_data_changed(self, curves_data: dict[str, CurveDataList]) -> None:
```

**Checklist**:
- [ ] Updated all signal handler type hints to use CurveDataList
- [ ] Verified consistency with type aliases throughout plan

---

### Phase 1: Migrate track_data to ApplicationState (Week 1, 8-10 hours)

#### 1.1 Verify ApplicationState Methods Exist

**✅ COMPLETED IN PHASE 0.6**: The single-curve convenience methods were implemented in Phase 0.6.

**Verify methods exist** (should NOT raise AttributeError):
```bash
# Quick check that methods are callable
python3 -c "from stores.application_state import get_application_state; s = get_application_state(); s.set_track_data([(1,2)]); print('✅ Methods exist')"
```

**Methods that should now exist**:
- ✅ `set_track_data(data)` - Set data for active curve (with validation)
- ✅ `get_track_data()` - Get data for active curve
- ✅ `has_data` - Property to check if active curve has data

**Note**: These ApplicationState methods are permanent (useful convenience methods). The **StateManager delegation methods** (added in Phase 1.2) are what get removed later.

#### 1.2 Add TEMPORARY Delegation to StateManager

**File**: `ui/state_manager.py`

**⚠️ TEMPORARY**: These delegation methods will be REMOVED in step 1.6 after all callers are migrated.

**Replace implementation**:
```python
# OLD: Direct storage (REMOVE these)
# _track_data: list[tuple[float, float]] = []
# _has_data: bool = False

# NEW: TEMPORARY delegation (will be removed in step 1.6)
@property
def track_data(self) -> list[tuple[float, float]]:
    """TEMPORARY: Get track data from ApplicationState. WILL BE REMOVED."""
    return self._app_state.get_track_data()

def set_track_data(self, data: list[tuple[float, float]], mark_modified: bool = True) -> None:
    """TEMPORARY: Set track data via ApplicationState. WILL BE REMOVED."""
    self._app_state.set_track_data(data)
    # Signal: ApplicationState.curves_changed emits (not StateManager)

    if mark_modified:
        self.is_modified = True

@property
def has_data(self) -> bool:
    """TEMPORARY: Check if active curve has data. WILL BE REMOVED."""
    return self._app_state.has_data
```

**Remove**: `_track_data` and `_has_data` instance variables

#### 1.3 Update All Callers to Use ApplicationState Directly

**Find callers**:
```bash
uv run rg "state_manager\.track_data" --type py
uv run rg "state_manager\.set_track_data" --type py
uv run rg "state_manager\.has_data" --type py
```

**Expected files** (~10-15 files):
- `services/data_service.py` - File loading/saving and data operations ✅ FIXED: Correct file path
- `ui/main_window.py` - Menu actions
- Test files - Update to use ApplicationState directly

**Migration pattern** (ALL callers must be updated):
```python
# OLD: Via StateManager (REMOVE ALL)
state_manager.set_track_data(data)
state_manager.track_data
state_manager.has_data

# NEW: Via ApplicationState (REQUIRED)
from stores.application_state import get_application_state
app_state = get_application_state()
app_state.set_track_data(data)  # Or set_curve_data(curve_name, data)
app_state.get_track_data()
app_state.has_data
```

**IMPORTANT**: Do NOT keep any StateManager calls. All must migrate to ApplicationState.

#### 1.3.1 Service Layer Integration Pattern

**Architectural Decision**: Services should access ApplicationState directly for data operations.

**Pattern for DataService**:
```python
# File loading (data operation)
from stores.application_state import get_application_state

def load_tracking_file(self, path: str) -> None:
    data = self._parse_file(path)
    app_state = get_application_state()

    # Data to ApplicationState
    app_state.set_curve_data(curve_name, data)

    # UI state to StateManager (separate concern)
    state_manager.current_file = path
    state_manager.is_modified = False
```

**Rationale**:
- Separates data operations (ApplicationState) from UI state (StateManager)
- Services operate on domain model, not UI layer
- Clearer architectural boundaries

**Update Callers**:
- `services/data_service.py` - Use ApplicationState directly for data
- State Manager delegation is ONLY for legacy UI code compatibility

#### 1.4 Update Signal Connections

**Find signal listeners**:
```bash
uv run rg "track_data_changed" --type py
```

**Replace with**:
```python
# Connect to ApplicationState signal instead
state = get_application_state()
state.curves_changed.connect(self._on_curve_data_changed)

def _on_curve_data_changed(self, curves_data: dict[str, CurveDataList]) -> None:
    """Curve data changed - refresh if active curve changed."""
    # ✅ FIXED: Signal emits dict[str, CurveDataList], not curve_name
    active_curve = state.active_curve  # ✅ FIXED: Use property
    if active_curve and active_curve in curves_data:
        # Refresh UI for active curve
        pass
```

#### 1.5 Testing

**Unit tests**:
```python
def test_track_data_delegates_to_application_state():
    """StateManager.track_data now delegates to ApplicationState."""
    state_manager = StateManager()
    app_state = get_application_state()

    # Set via StateManager
    test_data = [(1.0, 2.0), (3.0, 4.0)]
    state_manager.set_track_data(test_data)

    # Should be in ApplicationState
    assert app_state.get_track_data() == test_data
    assert state_manager.track_data == test_data  # Delegated property

def test_track_data_uses_curves_changed_signal():
    """Track data changes emit ApplicationState.curves_changed."""
    app_state = get_application_state()
    state_manager = StateManager()

    signal_emitted = False
    def on_changed(curves_data: dict[str, CurveDataList]) -> None:
        """Handler for curves_changed signal.

        Args:
            curves_data: Dict mapping curve names to curve data lists
        """
        nonlocal signal_emitted
        signal_emitted = True

    app_state.curves_changed.connect(on_changed)
    state_manager.set_track_data([(1.0, 2.0)])

    assert signal_emitted

def test_set_track_data_fails_without_active_curve():
    """set_track_data raises RuntimeError when no active curve set."""
    app_state = get_application_state()
    app_state.set_active_curve(None)  # Ensure no active curve

    test_data = [(1.0, 2.0), (3.0, 4.0)]

    # Should raise RuntimeError (fail fast)
    with pytest.raises(RuntimeError, match="No active curve set"):
        app_state.set_track_data(test_data)
```

**Integration tests**: Verify UI updates work with new signal source

#### 1.6 Remove Legacy Delegation Methods

**After all callers migrated, REMOVE these methods from StateManager**:

```python
# DELETE these entire methods from ui/state_manager.py:
@property
def track_data(self) -> list[tuple[float, float]]:  # ❌ DELETE
    """Get track data from ApplicationState (legacy compatibility)."""
    return self._app_state.get_track_data()

def set_track_data(self, data: list[tuple[float, float]], mark_modified: bool = True) -> None:  # ❌ DELETE
    """Set track data via ApplicationState (legacy compatibility)."""
    self._app_state.set_track_data(data)
    if mark_modified:
        self.is_modified = True

@property
def has_data(self) -> bool:  # ❌ DELETE
    """Check if active curve has data (legacy compatibility)."""
    return self._app_state.has_data
```

**Why remove**: No confusion - ApplicationState is the ONLY way to access data.

**REQUIRED Safety Layer**: Add `__getattr__` to catch accidental usage:
```python
# REQUIRED: Add to StateManager class for runtime safety (catches dynamic attribute access)
def __getattr__(self, name: str) -> None:
    """Provide clear error for removed data access methods."""
    removed_methods = {
        "track_data", "set_track_data", "has_data",
        "image_files", "set_image_files", "image_directory", "total_frames"
    }
    if name in removed_methods:
        raise AttributeError(
            f"StateManager.{name} was removed in Phase 6 migration. "
            f"Use ApplicationState.get_{name.replace('set_', '')}() instead. "
            f"See CLAUDE.md for migration guide."
        )
    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
```

**Why required**: Catches dynamic attribute access (e.g., `getattr(state_manager, 'track_data')`) and config-driven code that grep patterns cannot detect. Provides clear error messages with migration instructions.

#### 1.7 Verification Checklist

**After Phase 1 completion, verify complete removal:**

- [ ] `data_bounds` (state_manager.py:243-249) - Should call `_app_state.get_curve_data()`, not read `self._track_data`
- [ ] `reset_to_defaults` (state_manager.py:629) - Should delegate to ApplicationState, not clear `self._track_data`
- [ ] `get_state_summary` (state_manager.py:686) - Should read from ApplicationState, not `len(self._track_data)`

**Grep verification** (should find ZERO matches):
```bash
# No instance variables
uv run rg 'self\._track_data' ui/state_manager.py
uv run rg 'self\._has_data' ui/state_manager.py

# No legacy methods (catches both regular methods AND @property decorators)
uv run rg '(@property|def)\s+(track_data|set_track_data|has_data)' ui/state_manager.py

# Verify no external callers remain
uv run rg 'state_manager\.track_data\b' --type py
uv run rg 'state_manager\.set_track_data' --type py
uv run rg 'state_manager\.has_data\b' --type py
```

#### 1.6.1 Migration Hotspot Examples

**data_bounds** (state_manager.py:240-249):

Before:
```python
@property
def data_bounds(self) -> tuple[float, float, float, float]:
    if not self._track_data:  # ❌ Direct field access
        return (0.0, 0.0, 1.0, 1.0)

    x_coords = [point[0] for point in self._track_data]
    y_coords = [point[1] for point in self._track_data]
    return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
```

After:
```python
@property
def data_bounds(self) -> tuple[float, float, float, float]:
    track_data = self._app_state.get_track_data()  # ✅ Delegate
    if not track_data:
        return (0.0, 0.0, 1.0, 1.0)

    x_coords = [point[0] for point in track_data]
    y_coords = [point[1] for point in track_data]
    return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
```

**reset_to_defaults** (state_manager.py:629):

Before:
```python
self._track_data.clear()  # ❌ Direct mutation
self._has_data = False
```

After:
```python
self._app_state.set_track_data([])  # ✅ Delegate
# has_data is now a property, no manual update needed
```

**get_state_summary** (state_manager.py:686):

Before:
```python
"data": {
    "has_data": self._has_data,
    "point_count": len(self._track_data),  # ❌ Direct field access
}
```

After (Phase 1.6 - Final State):
```python
"data": {
    "has_data": self._app_state.has_data,  # ✅ Direct ApplicationState access
    "point_count": len(self._app_state.get_track_data()),  # ✅ NOT self.track_data (removed!)
}
```

**Note**: Example shows FINAL state after Phase 1.6 removes all delegation properties.

---

### Phase 2: Migrate image_files to ApplicationState (Week 2, 6-8 hours)

**✅ FIXED IN PHASE 0.7**: Phase 1-2 dependency removed. `current_frame.setter` was updated to use ApplicationState directly (no field dependency).

#### 2.1 Add Image Sequence Methods to ApplicationState

**✅ SIGNALS ALREADY ADDED IN PHASE 0.5**: Skip signal and instance variable additions.

**File**: `stores/application_state.py`

**Add methods** (following ApplicationState patterns, after line ~380):
```python
def set_image_files(self, files: list[str], directory: str | None = None) -> None:
    """
    Set the image file sequence.

    Args:
        files: List of image file paths
        directory: Optional base directory (if None, keeps current)
    """
    self._assert_main_thread()  # ✅ FIXED: Main thread only, no explicit mutex

    old_files = self._image_files
    old_dir = self._image_directory

    # Update state
    self._image_files = files.copy()
    if directory is not None:
        self._image_directory = directory

    # Update derived state
    old_total = self._total_frames
    self._total_frames = len(files) if files else 1

    # Emit signals if changed (uses _emit for batch mode compatibility)
    if old_files != self._image_files or (directory is not None and old_dir != directory):
        self._emit(self.image_sequence_changed, ())  # ✅ FIXED: Use _emit()

    if old_total != self._total_frames:
        self._emit(self.total_frames_changed, (self._total_frames,))  # ✅ FIXED: Use _emit()

    logger.debug(f"Image files updated: {len(files)} files, total_frames={self._total_frames}")

def get_image_files(self) -> list[str]:
    """Get the image file sequence."""
    self._assert_main_thread()  # ✅ FIXED: Main thread only
    return self._image_files.copy()

def get_image_directory(self) -> str | None:
    """Get the image base directory."""
    self._assert_main_thread()  # ✅ FIXED: Main thread only
    return self._image_directory

def set_image_directory(self, directory: str | None) -> None:
    """Set the image base directory (emits signal if changed)."""
    self._assert_main_thread()  # ✅ FIXED: Main thread only

    if self._image_directory != directory:
        self._image_directory = directory
        self._emit(self.image_sequence_changed, ())  # ✅ FIXED: Use _emit()
        logger.debug(f"Image directory changed to: {directory}")

def get_total_frames(self) -> int:
    """Get total frame count (derived from image sequence)."""
    self._assert_main_thread()  # ✅ FIXED: Main thread only
    return self._total_frames
```

**Note**: ApplicationState is main-thread only. The `_mutex` is ONLY used inside `_emit()` to protect the batch flag, not for data access.

**Signal Method Naming Clarification**:
- **ApplicationState** uses `self._emit(signal, args)` - Internal batch-aware emission
- **StateManager** uses `self._emit_signal(signal, args)` - External signal helper
Both are correct for their respective classes.

#### 2.2 Verify total_frames Setup

**✅ ALREADY DONE IN PHASE 0.5**: `_total_frames` was added to ApplicationState instance variables.

**Verify**:
```bash
uv run rg "_total_frames" stores/application_state.py
# Should find the instance variable declaration
```

#### 2.3 Add TEMPORARY Delegation to StateManager

**File**: `ui/state_manager.py`

**⚠️ TEMPORARY**: These delegation methods will be REMOVED in step 2.6 after all callers are migrated.

```python
# Remove instance variables (DELETE these)
# _image_files: list[str] = []
# _image_directory: str | None = None
# _total_frames: int = 1  (if still here)

# NEW: TEMPORARY delegation (will be removed in step 2.6)
@property
def image_files(self) -> list[str]:
    """TEMPORARY: Get image files from ApplicationState. WILL BE REMOVED."""
    return self._app_state.get_image_files()

def set_image_files(self, files: list[str]) -> None:
    """TEMPORARY: Set image files via ApplicationState. WILL BE REMOVED."""
    self._app_state.set_image_files(files)
    # Signal: ApplicationState.image_sequence_changed emits

@property
def image_directory(self) -> str | None:
    """TEMPORARY: Get image directory from ApplicationState. WILL BE REMOVED."""
    return self._app_state.get_image_directory()

@image_directory.setter
def image_directory(self, directory: str | None) -> None:
    """TEMPORARY: Set image directory via ApplicationState. WILL BE REMOVED."""
    self._app_state.set_image_directory(directory)
    # Signal: ApplicationState.image_sequence_changed emits

@property
def total_frames(self) -> int:
    """TEMPORARY: Get total frames from ApplicationState. WILL BE REMOVED."""
    return self._app_state.get_total_frames()

# Note: total_frames is derived from image_files count, set automatically

# ✅ NOTE: current_frame.setter was fixed in Phase 0.7 to use ApplicationState directly.
# No changes needed in this phase - it already uses _app_state.get_total_frames().
```

**Remove**: `_total_frames`, `_image_files`, `_image_directory` instance variables

#### 2.4 Update All Callers to Use ApplicationState Directly

**Find callers**:
```bash
uv run rg "\.image_files\b" --type py
uv run rg "set_image_files" --type py
uv run rg "\.image_directory\b" --type py
uv run rg "\.total_frames\b" --type py
```

**Expected files**:
- `services/data_service.py` - Image loading and management ✅ FIXED: Correct file path
- `ui/main_window.py` - File menu actions

**Migration pattern** (ALL callers must be updated):
```python
# OLD: Via StateManager (REMOVE ALL)
state_manager.image_files
state_manager.set_image_files(files)
state_manager.image_directory
state_manager.total_frames

# NEW: Via ApplicationState (REQUIRED)
from stores.application_state import get_application_state
app_state = get_application_state()
app_state.get_image_files()
app_state.set_image_files(files)
app_state.get_image_directory()
app_state.get_total_frames()
```

**IMPORTANT**: Do NOT keep any StateManager calls. All must migrate to ApplicationState.

#### 2.5 Testing

```python
def test_image_files_delegates_to_application_state():
    """StateManager.image_files delegates to ApplicationState."""
    state_manager = StateManager()
    app_state = get_application_state()

    files = ["/path/img001.jpg", "/path/img002.jpg"]
    state_manager.set_image_files(files)

    assert app_state.get_image_files() == files
    assert state_manager.image_files == files

def test_image_sequence_changed_signal():
    """Image file changes emit ApplicationState.image_sequence_changed."""
    app_state = get_application_state()

    signal_count = 0
    def on_changed():
        nonlocal signal_count
        signal_count += 1

    app_state.image_sequence_changed.connect(on_changed)
    app_state.set_image_files(["/img1.jpg", "/img2.jpg"])

    assert signal_count == 1

def test_set_image_files_updates_total_frames():
    """Setting image files automatically updates total_frames."""
    app_state = get_application_state()

    app_state.set_image_files(["/img1.jpg", "/img2.jpg", "/img3.jpg"])
    assert app_state.get_total_frames() == 3

    app_state.set_image_files([])
    assert app_state.get_total_frames() == 1  # Default
```

#### 2.6 Remove Legacy Delegation Methods

**After all callers migrated, REMOVE these methods from StateManager**:

```python
# DELETE these entire methods from ui/state_manager.py:
@property
def image_files(self) -> list[str]:  # ❌ DELETE
    """Get image files from ApplicationState (legacy compatibility)."""
    return self._app_state.get_image_files()

def set_image_files(self, files: list[str]) -> None:  # ❌ DELETE
    """Set image files via ApplicationState (legacy compatibility)."""
    self._app_state.set_image_files(files)

@property
def image_directory(self) -> str | None:  # ❌ DELETE
    """Get image directory from ApplicationState (legacy compatibility)."""
    return self._app_state.get_image_directory()

@image_directory.setter
def image_directory(self, directory: str | None) -> None:  # ❌ DELETE
    """Set image directory via ApplicationState (legacy compatibility)."""
    self._app_state.set_image_directory(directory)

@property
def total_frames(self) -> int:  # ❌ DELETE
    """Get total frames from ApplicationState (legacy compatibility)."""
    return self._app_state.get_total_frames()
```

**Why remove**: No confusion - ApplicationState is the ONLY way to access data.

#### 2.7 Verification Checklist

**After Phase 2 completion, verify complete removal:**

- [ ] `current_frame.setter` (state_manager.py:354) - Should use `_app_state.get_total_frames()`, not `self.total_frames`
- [ ] `current_image` (state_manager.py:446-447) - Should call `_app_state.get_image_files()`, not read `self._image_files`
- [ ] `reset_to_defaults` (state_manager.py:646) - Should delegate to ApplicationState, not clear `self._image_files`
- [ ] `get_state_summary` (state_manager.py:700-701) - Should read from ApplicationState, not `self._image_files`

**Grep verification** (should find ZERO matches):
```bash
# No instance variables
uv run rg 'self\._image_files|self\._total_frames|self\._image_directory' ui/state_manager.py

# No legacy methods (catches both regular methods AND @property decorators)
uv run rg '(@property|def)\s+(image_files|set_image_files|image_directory|total_frames)' ui/state_manager.py

# Verify no external callers remain
uv run rg 'state_manager\.image_files\b' --type py
uv run rg 'state_manager\.set_image_files' --type py
uv run rg 'state_manager\.image_directory\b' --type py
uv run rg 'state_manager\.total_frames\b' --type py
```

---

### Phase 2.5: Migrate _original_data to ApplicationState (Week 2, 4-6 hours)

**🎯 COMPLETE MIGRATION**: Migrate `_original_data` to achieve true "pure UI layer" goal.

#### 2.5.1 Add Original Data Storage to ApplicationState

**File**: `stores/application_state.py`

**Add to ApplicationState** (after curve data methods, ~line 380):

```python
# ==================== Original Data (Undo/Comparison) ====================

def set_original_data(self, curve_name: str, data: CurveDataInput) -> None:
    """
    Store original unmodified data for comparison (used by smoothing/filtering).

    Args:
        curve_name: Curve to store original data for
        data: Original curve data before modifications
    """
    self._assert_main_thread()
    # ✅ FIXED IN PHASE 0.4: _original_data initialized in __init__, no hasattr needed
    self._original_data[curve_name] = list(data)
    logger.debug(f"Stored original data for '{curve_name}': {len(data)} points")

def get_original_data(self, curve_name: str) -> CurveDataList:
    """
    Get original unmodified data for curve.

    Returns copy for safety.

    Args:
        curve_name: Curve to get original data for

    Returns:
        Copy of original data, or empty list if not set
    """
    self._assert_main_thread()
    # ✅ FIXED IN PHASE 0.4: _original_data initialized in __init__, no hasattr needed
    return self._original_data.get(curve_name, []).copy()

def clear_original_data(self, curve_name: str | None = None) -> None:
    """
    Clear original data (after committing changes).

    Args:
        curve_name: Curve to clear, or None to clear all
    """
    self._assert_main_thread()
    # ✅ FIXED IN PHASE 0.4: _original_data initialized in __init__, no hasattr needed
    if curve_name is None:
        self._original_data.clear()
        logger.debug("Cleared all original data")
    elif curve_name in self._original_data:
        del self._original_data[curve_name]
        logger.debug(f"Cleared original data for '{curve_name}'")
```

**✅ ALREADY ADDED IN PHASE 0.4**: `_original_data` was initialized in ApplicationState.__init__.

#### 2.5.2 Add TEMPORARY Delegation to StateManager

**File**: `ui/state_manager.py`

**Replace implementation** (line 72):

```python
# OLD: Direct storage (REMOVE)
# _original_data: list[tuple[float, float]] = []

# NEW: TEMPORARY delegation (will be removed in step 2.5.5)
def set_original_data(self, data: list[tuple[float, float]]) -> None:
    """TEMPORARY: Set original data via ApplicationState. WILL BE REMOVED."""
    # Determine active curve for storage
    active_curve = self._get_curve_name_for_selection()
    if active_curve:
        self._app_state.set_original_data(active_curve, data)
    else:
        logger.warning("No active curve for original data - ignoring")

@property
def original_data(self) -> list[tuple[float, float]]:
    """TEMPORARY: Get original data from ApplicationState. WILL BE REMOVED."""
    active_curve = self._get_curve_name_for_selection()
    if active_curve:
        return self._app_state.get_original_data(active_curve)
    return []
```

**Remove**: `_original_data` instance variable

#### 2.5.3 Update All Callers

**Find callers**:
```bash
uv run rg "\.set_original_data|_original_data" --type py
```

**Expected files**:
- Smoothing operations in services or UI
- Undo/redo system (if implemented)

**Migration pattern**:
```python
# OLD: Via StateManager
state_manager.set_original_data(data)
original = state_manager._original_data  # or .original_data property

# NEW: Via ApplicationState
from stores.application_state import get_application_state
app_state = get_application_state()
app_state.set_original_data(curve_name, data)
original = app_state.get_original_data(curve_name)
```

#### 2.5.4 Testing

```python
def test_original_data_per_curve():
    """Original data is stored per-curve."""
    app_state = get_application_state()

    data1 = [(1.0, 2.0), (3.0, 4.0)]
    data2 = [(5.0, 6.0), (7.0, 8.0)]

    app_state.set_original_data("Track1", data1)
    app_state.set_original_data("Track2", data2)

    assert app_state.get_original_data("Track1") == data1
    assert app_state.get_original_data("Track2") == data2

def test_clear_original_data():
    """Clear original data for specific curve."""
    app_state = get_application_state()

    app_state.set_original_data("Track1", [(1.0, 2.0)])
    app_state.clear_original_data("Track1")

    assert app_state.get_original_data("Track1") == []
```

#### 2.5.5 Remove Legacy Methods

**After all callers migrated, REMOVE from StateManager**:

```python
# DELETE these from ui/state_manager.py:
def set_original_data(self, data: list[tuple[float, float]]) -> None:  # ❌ DELETE
    ...

@property
def original_data(self) -> list[tuple[float, float]]:  # ❌ DELETE
    ...
```

#### 2.5.6 Verification Checklist

- [ ] `_original_data` removed from StateManager (line 72)
- [ ] `set_original_data()` method removed from StateManager
- [ ] `original_data` property removed from StateManager
- [ ] All callers use ApplicationState directly
- [ ] Tests pass: `uv run pytest tests/stores/test_application_state.py -k original`

**Grep verification** (should find ZERO matches):
```bash
uv run rg 'self\._original_data' ui/state_manager.py
uv run rg 'def (set_original_data|original_data)' ui/state_manager.py
```

**Why this phase is critical**: Without migrating `_original_data`, StateManager is NOT a "pure UI layer" - it still contains application data. This violates the architectural goal.

---

### Phase 3: Add UI State Signals (Week 2, 4-6 hours)

Now that data is properly separated, add signals for **true UI state** in StateManager.

#### 3.1 Undo/Redo State Signals

**File**: `ui/state_manager.py`

**Add signals** (after existing signals ~line 46):
```python
# History UI state signals
undo_state_changed: Signal = Signal(bool)  # Emits can_undo
redo_state_changed: Signal = Signal(bool)  # Emits can_redo
```

**Update method**:
```python
def set_history_state(self, can_undo: bool, can_redo: bool, position: int = 0, size: int = 0) -> None:
    """
    Update history state for UI (toolbar button enable/disable).

    Args:
        can_undo: Whether undo is available
        can_redo: Whether redo is available
        position: Current position in history (optional)
        size: Total history size (optional)
    """
    self._history_position = position
    self._history_size = size

    # Emit signals only if values changed
    if self._can_undo != can_undo:
        self._can_undo = can_undo
        self._emit_signal(self.undo_state_changed, can_undo)  # ✅ FIXED: Pass Signal instance

    if self._can_redo != can_redo:
        self._can_redo = can_redo
        self._emit_signal(self.redo_state_changed, can_redo)  # ✅ FIXED: Pass Signal instance
```

#### 3.2 Current Tool Signal

**Add signal**:
```python
# Tool state signal
tool_state_changed: Signal = Signal(str)  # Emits new tool name
```

**Update property**:
```python
@current_tool.setter
def current_tool(self, tool: str) -> None:
    """Set current tool and emit signal if changed."""
    if self._current_tool != tool:
        self._current_tool = tool
        self._emit_signal(self.tool_state_changed, tool)  # ✅ FIXED: Pass Signal instance
        logger.debug(f"Current tool changed to: {tool}")
```

#### 3.3 Connect Signals in SignalConnectionManager

**File**: `ui/controllers/signal_connection_manager.py`

**Add connections**:
```python
def _connect_state_manager_signals(self) -> None:
    """Connect StateManager UI state signals."""

    # Undo/Redo action state (toolbar uses QActions, not QPushButtons)
    _ = self.state_manager.undo_state_changed.connect(
        lambda enabled: self.main_window.action_undo.setEnabled(enabled)  # ✅ FIXED: Use QAction
    )
    _ = self.state_manager.redo_state_changed.connect(
        lambda enabled: self.main_window.action_redo.setEnabled(enabled)  # ✅ FIXED: Use QAction
    )

    # Tool state (if toolbar has tool buttons that need syncing)
    _ = self.state_manager.tool_state_changed.connect(
        self._on_tool_changed
    )

def _on_tool_changed(self, tool_name: str) -> None:
    """Update toolbar when tool changes programmatically."""
    # Update toolbar button states if needed
    logger.debug(f"Tool changed to: {tool_name}")
```

**Verify UI component paths**:
```bash
uv run rg "undo_button\b" ui/ui_components.py
uv run rg "redo_button\b" ui/ui_components.py
```

#### 3.4 Testing

```python
def test_undo_state_changed_signal(qtbot):
    """Undo state changes emit signal."""
    state = StateManager()

    with qtbot.waitSignal(state.undo_state_changed) as blocker:
        state.set_history_state(can_undo=True, can_redo=False)

    assert blocker.args == [True]

def test_redo_state_changed_signal(qtbot):
    """Redo state changes emit signal."""
    state = StateManager()

    with qtbot.waitSignal(state.redo_state_changed) as blocker:
        state.set_history_state(can_undo=False, can_redo=True)

    assert blocker.args == [True]

def test_tool_state_changed_signal(qtbot):
    """Tool changes emit signal."""
    state = StateManager()

    with qtbot.waitSignal(state.tool_state_changed) as blocker:
        state.current_tool = "smooth"

    assert blocker.args == ["smooth"]

def test_undo_action_updates_with_state(qtbot, main_window):
    """Undo action enables/disables based on history state."""
    # Initially no undo
    main_window.state_manager.set_history_state(can_undo=False, can_redo=False)
    assert not main_window.action_undo.isEnabled()  # ✅ FIXED: Use QAction

    # Enable undo
    main_window.state_manager.set_history_state(can_undo=True, can_redo=False)
    qtbot.wait(10)  # Allow signal processing
    assert main_window.action_undo.isEnabled()  # ✅ FIXED: Use QAction
```

---

### Phase 4: Documentation and Cleanup (Week 3, 2-4 hours)

#### 4.1 Update StateManager Docstring

**File**: `ui/state_manager.py`

```python
class StateManager(QObject):
    """
    Manages UI preferences and view state for the CurveEditor application.

    **Architectural Scope** (Post-Migration):

    This class handles **UI-layer state only**:
    - View state: zoom_level, pan_offset, view_bounds
    - Tool state: current_tool, smoothing_window_size, smoothing_filter_type
    - Window state: window_position, splitter_sizes, is_fullscreen
    - History UI: can_undo, can_redo (for toolbar button state)
    - Session state: recent_directories, file_format
    - File UI: current_file, is_modified (file path and dirty flag)

    **Application data** (curves, images, frames, selection) is managed by:
    - ApplicationState: Single source of truth for ALL application data
    - DataService: File I/O and data operations

    **⚠️ NO LEGACY METHODS**:
    StateManager does NOT provide access to application data.
    All data access must go through ApplicationState:
    - Use ApplicationState.get_track_data(), NOT StateManager.track_data
    - Use ApplicationState.get_image_files(), NOT StateManager.image_files
    - Use ApplicationState.get_total_frames(), NOT StateManager.total_frames

    **Thread Safety**:
    Both StateManager and ApplicationState are main-thread only.
    ApplicationState enforces this via `_assert_main_thread()`.
    The QMutex in ApplicationState ONLY protects batch mode flag, NOT data access.
    Services running in background threads must use Qt signals to communicate with ApplicationState.

    **Signals** (UI State Only):
    - view_state_changed: Zoom, pan, or bounds changed
    - file_changed: Current file path changed
    - modified_changed: Dirty flag changed
    - undo_state_changed: Undo availability changed
    - redo_state_changed: Redo availability changed
    - tool_state_changed: Current tool changed
    - playback_state_changed: Playback mode changed
    - active_timeline_point_changed: Active timeline point changed

    **Data Signals** (Use ApplicationState):
    - ApplicationState.curves_changed: Curve data changed
    - ApplicationState.image_sequence_changed: Image files changed
    - ApplicationState.total_frames_changed: Frame count changed
    - ApplicationState.frame_changed: Current frame changed
    - ApplicationState.selection_changed: Selected points changed
    """
```

#### 4.2 Update CLAUDE.md

**File**: `CLAUDE.md`

**Update State Management section**:
```markdown
## State Management

**ApplicationState** is the single source of truth for **application data**.

```python
from stores.application_state import get_application_state

state = get_application_state()

# Curve data
state.set_curve_data("Track1", curve_data)
data = state.get_curve_data("Track1")

# Image sequence
state.set_image_files(files, directory="/path/to/images")
files = state.get_image_files()

# Frame state
state.set_current_frame(42)
frame = state.get_current_frame()

# Subscribe to changes
state.curves_changed.connect(self._on_data_changed)
state.image_sequence_changed.connect(self._on_images_changed)
```

**StateManager** handles **UI preferences and view state**.

```python
from ui.state_manager import StateManager

# View state
state_manager.zoom_level = 2.0
state_manager.pan_offset = (100, 50)

# Tool state
state_manager.current_tool = "smooth"

# Window state
state_manager.window_position = (100, 100)
state_manager.is_fullscreen = True

# History UI state
state_manager.set_history_state(can_undo=True, can_redo=False)

# Subscribe to UI state changes
state_manager.view_state_changed.connect(self._on_view_changed)
state_manager.undo_state_changed.connect(self._update_undo_button)
```

**Migration Complete** (October 2025):
- Phase 5: ApplicationState migration (66 files, 83.3% memory reduction)
- Phase 6: StateManager data migration (clear layer separation)
- Result: Single source of truth, no duplicate signals, NO legacy methods
```

**⚠️ StateManager has NO data access methods**:
```python
# ❌ WRONG - These don't exist anymore
state_manager.track_data
state_manager.image_files
state_manager.total_frames

# ✅ CORRECT - Use ApplicationState directly
state = get_application_state()
state.get_track_data()
state.get_image_files()
state.get_total_frames()
```

#### 4.3 Update ARCHITECTURE.md

Add section on State Layer architecture:

```markdown
### State Layer Architecture

**Separation of Concerns**:

```
ApplicationState (Data)        StateManager (UI Preferences)
├─ Curve data                  ├─ View state (zoom, pan)
├─ Image sequence              ├─ Tool state (current tool)
├─ Frame state                 ├─ Window state (position, size)
├─ Selection state             ├─ History UI (can_undo, can_redo)
└─ Thread-safe (QMutex)        └─ Session state (recent dirs)
```

**Signal Sources**:
- `ApplicationState.*_changed` - Data changes (curves, images, frames, selection)
- `StateManager.*_changed` - UI state changes (view, tool, window)

**No signal duplication** - each data type has exactly one signal source.
```

#### 4.4 Archive Old Plan

**Move to archive**:
```bash
mv docs/STATEMANAGER_SIGNAL_ARCHITECTURE_REFACTOR.md \
   docs/archive_2025_oct/STATEMANAGER_SIGNAL_ARCHITECTURE_REFACTOR_OLD.md
```

**Add note to archived file**:
```markdown
# ARCHIVED - October 2025

This plan was superseded by Option A: Complete Migration.

See: `docs/STATEMANAGER_COMPLETE_MIGRATION_PLAN.md`

Reason: Architectural review identified that adding signals to hybrid state
would maintain technical debt. Option A completes the migration instead.
```

---

## Testing Strategy

### Unit Tests (15+ tests)

**ApplicationState data migration**:
- `test_track_data_in_application_state()` - Verify delegation works
- `test_image_files_in_application_state()` - Verify delegation works
- `test_image_directory_in_application_state()` - Verify delegation works
- `test_total_frames_derived_from_images()` - Verify automatic update
- `test_curves_changed_signal_for_track_data()` - Single signal source
- `test_image_sequence_changed_signal()` - Single signal source

**StateManager UI signals**:
- `test_undo_state_changed_signal()` - Verify emission
- `test_redo_state_changed_signal()` - Verify emission
- `test_tool_state_changed_signal()` - Verify emission
- `test_signals_use_emit_signal()` - Verify batch mode compatibility

**Thread safety**:
- `test_application_state_thread_safe_access()` - Multiple threads
- `test_state_manager_main_thread_only()` - Assert main thread

**No signal duplication**:
- `test_no_duplicate_curve_signals()` - Only curves_changed emits for curve data
- `test_no_duplicate_image_signals()` - Only image_sequence_changed emits

**Backward compatibility**:
- `test_state_manager_track_data_legacy_api()` - Old API still works
- `test_state_manager_image_files_legacy_API()` - Old API still works

### Integration Tests (8+ tests)

**UI responsiveness**:
- `test_undo_button_updates_automatically()` - Button state tracks history
- `test_redo_button_updates_automatically()` - Button state tracks history
- `test_toolbar_syncs_with_tool_changes()` - Tool button state syncs
- `test_view_updates_on_image_sequence_change()` - Timeline updates

**Signal coordination**:
- `test_batch_updates_across_layers()` - ApplicationState + StateManager batching
- `test_no_circular_signal_dependencies()` - No infinite loops
- `test_signal_order_deterministic()` - With FrameChangeCoordinator

**Migration validation**:
- `test_all_callers_migrated()` - No direct _track_data access
- `test_no_orphaned_signals()` - No unused signal connections

### Regression Tests

**Run full test suite**:
```bash
uv run pytest tests/ -v
```

**Expected**: All 2100+ tests pass (zero regressions)

**If failures**: Likely backward compatibility issues - check delegation

---

## Risk Assessment

### Low Risk ✅

- **Non-breaking**: Delegation maintains API compatibility
- **Incremental**: Can test each phase independently
- **Proven pattern**: ApplicationState migration already succeeded
- **Clear rollback**: Each phase can be reverted

### Medium Risk ⚠️

- **Large refactor scope**: 20-30 hours across many files
- **Signal connection changes**: Must verify all listeners updated
- **Test updates**: ~15-20 test files may need updates

**Mitigation**:
- Phase-by-phase execution with full test runs after each
- Automated search for all callers before migration
- Keep backward-compatible delegation (don't break existing code)

### High Risk 🔴

- ~~**Phase 1-2 Atomic Dependency**~~: **RESOLVED IN PHASE 0.7** - `current_frame.setter` now uses ApplicationState directly, no field dependency
- **Behavioral Change (Fail-Fast)**: `set_track_data()` raises RuntimeError when no active curve (was auto-create in Amendment #4)
  - **Mitigation**: Comprehensive initialization order testing + explicit error messages
- **Performance Regression (Temporary)**: Delegation adds double-copying **during migration only** (Phases 1.2-1.6)
  - **Duration**: Only while delegation methods exist (removed in Phase 1.6)
  - **Final State**: Same performance as intended architecture (single defensive copy)
  - **Mitigation**: Accept temporary overhead for migration safety; benchmark tests to verify final performance

---

## Success Metrics

### Architectural Cleanliness ✅

- [ ] **Zero duplicate signals**: Each data type has ONE signal source
- [ ] **Clear layer separation**: Data in ApplicationState, UI in StateManager
- [ ] **Thread safety**: ApplicationState has mutex, StateManager main-thread only
- [ ] **Single source of truth**: ApplicationState is authoritative for data

### Code Quality ✅

- [ ] **All 2100+ tests pass**: Zero regressions
- [ ] **15+ new tests**: Validate migration and signals
- [ ] **Type checking clean**: `./bpr --errors-only` passes
- [ ] **No deprecation warnings**: No legacy pattern usage

### Documentation ✅

- [ ] **StateManager docstring updated**: Clear architectural scope
- [ ] **CLAUDE.md updated**: Separate ApplicationState vs StateManager usage
- [ ] **ARCHITECTURE.md updated**: Layer separation documented
- [ ] **Old plan archived**: With explanation

### Migration Completeness ✅

- [ ] **track_data migrated**: No `_track_data` in StateManager
- [ ] **image_files migrated**: No `_image_files` in StateManager
- [ ] **image_directory migrated**: No `_image_directory` in StateManager
- [ ] **total_frames migrated**: Derived from image count in ApplicationState
- [ ] **_original_data migrated**: No `_original_data` in StateManager (**Phase 2.5 - COMPLETE MIGRATION**)
- [ ] **UI signals added**: undo_state_changed, redo_state_changed, tool_state_changed
- [ ] **NO LEGACY METHODS**: All delegation methods removed from StateManager
- [ ] **Zero StateManager data access**: All callers use ApplicationState directly
- [ ] **Pure UI layer achieved**: StateManager contains ONLY UI state, ZERO application data

---

## Timeline and Effort

| Phase | Duration | Effort | Deliverables |
|-------|----------|--------|--------------|
| **Phase 0: Pre-work** | **Week 1** | **10.5-12.5h** | **Fix hasattr, add signals, implement methods, fix current_frame** |
| Phase 1: track_data | Week 1-2 | 8-10h | Migration + tests |
| Phase 2: image_files | Week 2 | 6-8h | Migration + tests |
| **Phase 2.5: _original_data** | **Week 2-3** | **4-6h** | **COMPLETE migration (pure UI layer)** |
| Phase 3: UI signals | Week 3 | 4-6h | Signals + connections |
| Phase 4: Documentation | Week 4 | 2-4h | Docs + cleanup |
| **Buffer** | - | **+10-14h** | **Discovery, testing, rework** |
| **Total** | **4-5 weeks** | **55-69h** | **100% Complete migration** |

**Revised from previous estimates**:
- **Amendment #7**: Added Phase 0.4 (6-8h) for missing ApplicationState methods
- **Amendment #8**: Added Phase 2.5 (4-6h) for `_original_data` migration (COMPLETE migration goal)
- **Amendment #9**: Added Phase 0.4 (hasattr fix), 0.5 (signals), 0.7 (current_frame fix), 0.8 (type hints) (+2.5-3h)
- **Amendment #9**: Made __getattr__ safety layer mandatory (was optional)
- **Amendment #9**: Added deprecation notice for convenience methods (long-term cleanup)
- Increased buffer to 10-14h for comprehensive testing
- **Total increased from 52-66h to 55-69h (+3h for verification fixes)**

**Comparison to Quick Fix (Option B)**:
- Option B: 7-11 hours, maintains technical debt, incomplete migration
- Option A (Amendment #8): 52-66 hours, ZERO technical debt, 100% complete
- **Extra cost**: 45-55 hours upfront
- **Future savings**: 80+ hours (prevents compounding debt, no future Phase 7/8 needed)

**Amendment #8 Impact**: Completes the migration properly - StateManager is NOW a true "pure UI layer" with ZERO application data remaining. No technical debt deferred to future phases.

---

## Lessons from FrameChangeCoordinator

### What Made FrameChangeCoordinator Successful ✅

1. **Fixed root cause** (non-deterministic ordering), not symptom
2. **Eliminated duplication** (6 handlers → 1 coordinator)
3. **Clear single responsibility** (coordinator owns all frame change responses)
4. **Backward compatible** (old code kept working during migration)
5. **Comprehensive testing** (14 tests + edge cases)
6. **Atomic guarantees** (error handling prevents partial updates)

### Applying to StateManager Migration

1. **Fix root cause** (data in wrong layer), not symptom (missing signals)
2. **Eliminate duplication** (2 signal sources → 1 per data type)
3. **Clear separation** (ApplicationState = data, StateManager = UI prefs)
4. **Backward compatible** (delegation maintains old API)
5. **Comprehensive testing** (15+ unit + 8+ integration tests)
6. **Thread safety** (ApplicationState mutex prevents race conditions)

#### 4.5 Final Verification Checklist

**After all phases complete, verify NO legacy data fields remain in StateManager:**

```bash
# Should find ZERO matches for these patterns (100% complete migration):
uv run rg "self\._track_data" ui/state_manager.py
uv run rg "self\._image_files" ui/state_manager.py
uv run rg "self\._total_frames" ui/state_manager.py
uv run rg "self\._original_data" ui/state_manager.py  # ✅ NEW: Amendment #8
```

**Verify all migration hotspots now delegate to ApplicationState:**

- [ ] `data_bounds` (state_manager.py:240-249) - Reads from `_app_state`, not `_track_data`
- [ ] `current_frame.setter` (state_manager.py:345-358) - Uses `_app_state.get_total_frames()`, not `self._total_frames`
- [ ] `current_image` (state_manager.py:442-447) - Calls `_app_state.get_image_files()`, not reads `self._image_files`
- [ ] `reset_to_defaults` (state_manager.py:621-672) - Delegates to ApplicationState for all data (including original_data)
- [ ] `get_state_summary` (state_manager.py:676-710) - Reads all data from ApplicationState

**✅ Amendment #8: Verify StateManager is a TRUE "pure UI layer":**

```bash
# Should find ZERO application data in StateManager:
uv run rg "self\._(track_data|image_files|image_directory|total_frames|original_data)" ui/state_manager.py
```

**Expected result**: NO matches. StateManager contains ONLY UI preferences.

**Run full test suite**:
```bash
uv run pytest tests/test_state_manager.py -v  # ✅ FIXED: Correct test path
uv run pytest tests/stores/test_application_state.py -v
```

---

## Appendix: Signal Reference

### ApplicationState Signals (Data Layer)

```python
# Curve data
curves_changed: Signal = Signal(dict)                   # ✅ FIXED: Emits dict[str, CurveDataList]

# Image sequence
image_sequence_changed: Signal = Signal()               # NEW: Images or directory changed

# Frame state
frame_changed: Signal = Signal(int)                     # Emits new frame
total_frames_changed: Signal = Signal(int)              # NEW: Emits new total

# Selection state (point-level within a curve)
selection_changed: Signal = Signal(set, str)            # Emits (indices, curve_name)

# Selection state (curve-level - which curves to display)
selection_state_changed: Signal = Signal(set, bool)     # ✅ ACTUAL: Combined signal (selected_curves, show_all)

# Active curve
active_curve_changed: Signal = Signal(str)              # Emits curve_name or ""

# View state
view_changed: Signal = Signal(object)                   # Emits ViewState object
```

**Note**: Code uses combined `selection_state_changed: Signal(set, bool)` instead of separate
`selected_curves_changed` + `show_all_curves_changed` signals. This is the correct implementation.

### StateManager Signals (UI Layer)

```python
# View state
view_state_changed: Signal = Signal()                   # Zoom, pan, bounds

# File UI state
file_changed: Signal = Signal(str)                      # Current file path
modified_changed: Signal = Signal(bool)                 # Dirty flag

# History UI state
undo_state_changed: Signal = Signal(bool)               # NEW: Can undo
redo_state_changed: Signal = Signal(bool)               # NEW: Can redo

# Tool state
tool_state_changed: Signal = Signal(str)                # NEW: Current tool

# Playback state
playback_state_changed: Signal = Signal(object)         # Playback mode

# Timeline state
active_timeline_point_changed: Signal = Signal(object)  # Active point
```

### Total Signals After Migration

- **ApplicationState**: 9 signals (all data-related)
- **StateManager**: 8 signals (all UI-related)
- **Total**: 17 signals, **zero duplication** ✅

---

## Document History

- **2025-10-07 14:00**: Initial Option A plan created after agent reviews
- **2025-10-07 16:30**: **AMENDED #1** - Fixed implementation bugs identified in code review
  - Fixed: `get_active_curve_name()` → `self.active_curve` (property)
  - Fixed: Thread safety pattern (removed explicit mutex locks, use `_assert_main_thread()` + `_emit()`)
  - Fixed: Signal storage (use `_emit()` instead of `.add()` to pending_signals)
  - Added: Phase 0 for pre-implementation verification (2 hours)
  - Added: Cached `self._app_state` usage (architect optimization)
  - Added: `_original_data` deferral documentation
  - Revised timeline: 22-30 hours (was 20-28 hours)
- **2025-10-07 18:00**: **AMENDED #2** - Fixed signal specifications from GPTAudit report
  - **CRITICAL**: Fixed `curves_changed` signal payload (Signal(dict), not Signal(str))
  - Fixed: All signal connection examples to handle dict[str, CurveDataList] payload
  - Fixed: File path references (`data/data_operations.py` → `services/data_service.py`)
  - Documented: Combined `selection_state_changed: Signal(set, bool)` is correct
  - Updated: Appendix signal reference with actual code signatures
  - Verified: view_state_changed already emitted correctly (no changes needed)
- **2025-10-08 19:00**: **AMENDED #3** - Fixed implementation API bugs from code verification review
  - **CRITICAL**: Fixed `_emit_signal` API usage (must pass Signal instance, not string name)
  - **CRITICAL**: Fixed toolbar references (use `action_undo`/`action_redo` QActions, not nonexistent `ui.toolbar.undo_button`)
  - Added: Phase 1.6 verification checklist (data_bounds, reset_to_defaults, get_state_summary line numbers)
  - Added: Phase 2.6 verification checklist (current_frame.setter, current_image line numbers)
  - Added: Phase 4.5 final verification checklist (all 5 migration hotspots with grep patterns)
  - Fixed: Test example `test_undo_action_updates_with_state` to use QAction API
  - Impact: Prevents 2 runtime crashes (TypeError on signal emission, AttributeError on button access)
- **2025-10-08 21:00**: **AMENDED #4** - Fixed critical edge cases from dual-agent architectural review
  - **CRITICAL**: Fixed `active_curve=None` edge case (auto-create `__default__` curve to prevent silent data loss)
  - Added: `current_frame.setter` update in Phase 2 (use `self.total_frames` property, not `self._total_frames` field)
  - Fixed: Test file path (`tests/test_state_manager.py`, not `tests/ui/test_state_manager.py`)
  - Reframed: "Duplicate signals" claim (prevents future duplication, not removing existing - `track_data_changed` never existed)
  - Added: Phase dependency warning (Phases 1-2 must complete in same session - removing `_total_frames` breaks `current_frame.setter`)
  - Added: Test case `test_set_track_data_auto_creates_default_curve()`
  - Impact: Prevents silent data loss during file loading, clarifies implementation dependencies
- **2025-10-09 TBD**: **AMENDED #5** - Tri-agent review synthesis findings
  - Fixed: Test signal signatures (lines 373-380) - Use `dict[str, list]` instead of `str` for curves_changed handler
  - Added: Phase 1.3.1 Service Layer Integration Pattern - Services access ApplicationState directly for data operations
  - Updated: Risk Assessment - Added 3 high risks (Phase 1-2 atomic dependency, behavioral change, performance regression)
  - Added: Phase 1.6.1 Migration Hotspot Examples - Before/after code for data_bounds, reset_to_defaults, get_state_summary
  - Updated: Timeline - Added 8-10h buffer (33%) for discovery and rework, total now 30-40h
  - Impact: Clarifies service layer architecture, realistic risk assessment, concrete migration examples
- **2025-10-09 TBD**: **AMENDED #6** - Critical fixes from tri-agent code verification
  - **CRITICAL**: Fixed thread safety contradiction (line 82) - ApplicationState is main-thread only, NOT thread-safe for data access
  - Fixed: Migration hotspot example for get_state_summary (line 536-542) - Shows final state after Phase 1.6, not intermediate
  - Fixed: Grep verification patterns (lines 474-481, 808-815) - Now catches @property decorators and external callers
  - Changed: Auto-create logging level from info to warning (line 242) - Highlights potential initialization bugs
  - Added: Optional `__getattr__` safety layer to Phase 1.6 - Provides clear error messages for removed methods
  - Added: Signal method naming clarification (after line 626) - Explains `_emit()` vs `_emit_signal()` difference
  - Impact: Prevents thread safety misunderstandings, ensures complete verification, better debugging experience
- **2025-10-09 TBD**: **AMENDED #7 (BLOCKER)** - Tri-agent verification findings (best-practices-checker, code-refactoring-expert, python-expert-architect)
  - **🔴 BLOCKER**: Added Phase 0.4 (6-8h) - Implement missing ApplicationState methods (set_track_data, get_track_data, has_data, set_image_files, get_image_files, get_image_directory, get_total_frames)
  - **CRITICAL**: Fixed thread safety documentation at line 1035 (removed "thread-safe data access" claim)
  - **CRITICAL**: Added input validation to all new methods (TypeError, ValueError, size limits) to prevent resource exhaustion and crashes
  - **CRITICAL**: Changed auto-create logging from warning to error level (highlights initialization bugs, not hides them)
  - Updated: Phase 1.1 no longer duplicates implementation (references Phase 0.4)
  - Updated: Timeline from 30-40h to 43-54h (+13-14h for missing implementation)
  - Updated: Timeline comparison to Option B (acknowledges higher cost but validates approach)
  - Verified: All methods confirmed missing via grep (0 matches found in ApplicationState)
  - Impact: BLOCKS execution - Phase 1.2 cannot create delegation without these methods existing first. Finding now prevents mid-migration emergency.
- **2025-10-09 TBD**: **AMENDED #8 (COMPLETE MIGRATION)** - Fixed all tri-agent blockers, COMPLETE migration (100% pure UI layer)
  - **✅ FIXED CF2**: Changed auto-create behavior to fail-fast - `set_track_data()` now raises `RuntimeError` when no active curve (lines 261-268)
  - **✅ FIXED CF3**: Removed Phase 1-2 atomic dependency - `current_frame.setter` uses ApplicationState directly, no field dependency (line 889)
  - **✅ FIXED CF4**: Added Phase 2.5 (4-6h) - Complete `_original_data` migration, achieving TRUE "pure UI layer" goal (lines 1029-1212)
  - **✅ OPTIMIZATION UC1**: Lazy signal payload (send `set[str]` instead of full dict) - reduces 8MB+ signals to ~100 bytes (deferred to Phase 0.4)
  - **✅ OPTIMIZATION UC2**: Batch rollback mechanism with snapshot/restore for atomicity (deferred to Phase 0.4)
  - **✅ DISMISSED UC3**: Path traversal validation not needed (user confirmed personal app, security not a concern)
  - Updated: Timeline from 43-54h to 52-66h (+9-12h for complete migration)
  - Updated: Executive summary - NOW claims "pure UI layer" honestly (includes _original_data)
  - Updated: Properties to MIGRATE table - Added `_original_data` (5 total, not 4)
  - Updated: Migration Completeness metrics - Added `_original_data` verification
  - Updated: Final verification checklist - Includes `_original_data` grep check
  - Removed: "Document Deferred Work" section (Phase 4.4) - NO technical debt remains!
  - Updated: Timeline comparison - 100% complete vs 80% complete (Option B), saves 80+ hours future work
  - Impact: Migration is NOW truly complete - StateManager contains ZERO application data, architectural goal achieved without compromise
- **2025-10-09 TBD**: **AMENDED #9 (VERIFICATION FIXES)** - Tri-agent post-review verification fixes
  - **✅ FIXED**: hasattr() anti-pattern - Added Phase 0.4 to initialize _original_data in __init__ (1h)
  - **✅ FIXED**: Missing signals - Added Phase 0.5 to add image_sequence_changed and total_frames_changed (2h)
  - **✅ FIXED**: current_frame.setter dependency - Added Phase 0.7 to fix before Phase 2 (1h)
  - **✅ FIXED**: Type inconsistencies - Added Phase 0.8 to update dict[str, list] → dict[str, CurveDataList] (30m)
  - **✅ FIXED**: Sequencing confusion - Clarified "already fixed" claims, explicit phase dependencies
  - **✅ CHANGED**: Made __getattr__ safety layer MANDATORY (was optional) - catches dynamic attribute access
  - **✅ ADDED**: Deprecation notice for convenience methods - dual API violation of PEP 20, plan Phase 5 removal
  - **✅ UPDATED**: Risk assessment - Removed obsolete Phase 1-2 dependency, clarified temporary performance impact
  - Updated: Timeline from 52-66h to 55-69h (+3h for verification fixes)
  - Updated: Phase 0 from 8-10h to 10.5-12.5h (split into 8 substeps)
  - Impact: Removes all blockers identified in tri-agent verification, clarifies execution sequencing
- **Author**: Architectural review identified hybrid state as root cause
- **Status**: ✅ **EXECUTION-READY** - All blockers fixed, migration is 100% complete, no technical debt deferred
- **Supersedes**: `STATEMANAGER_SIGNAL_ARCHITECTURE_REFACTOR.md` (Option B)

---

*End of Migration Plan - Amended Version*
