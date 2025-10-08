# StateManager Complete Migration Plan - Option A (Amended)

## Executive Summary

**Status**: ✅ **AMENDED** - Implementation bugs fixed, ready for execution

**Goal**: Complete the StateManager migration by moving application data to ApplicationState and establishing StateManager as a **pure UI preferences layer**.

**Root Cause**: StateManager is a hybrid containing both application data (track_data, image_files) and UI state (zoom, tool, window). This creates:
- **Duplicate signal sources** (ApplicationState.curves_changed + StateManager.track_data_changed)
- **Thread safety gaps** (ApplicationState has mutex, StateManager doesn't)
- **Architectural confusion** (violates "single source of truth" principle)

**Solution**: Follow FrameChangeCoordinator pattern - fix root cause, not symptoms.

**Timeline**: 22-30 hours over 2-3 weeks (includes Phase 0 bug fixes)

**Amendments** (2025-10-07):
- Fixed method naming errors (`active_curve` property vs `get_active_curve_name()`)
- Fixed thread safety pattern (use `_assert_main_thread()` + `_emit()`, not explicit mutex)
- Optimized with cached `self._app_state` references
- Added Phase 0 for pre-implementation verification
- Documented `_original_data` deferral to future phase

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

**Before** (Problematic):
```python
ApplicationState.curves_changed     # When curve data changes
StateManager.track_data_changed     # Also when curve data changes ❌ DUPLICATE
```

**After** (Clean):
```python
ApplicationState.curves_changed     # ONLY signal for curve data ✅
StateManager.view_state_changed     # ONLY signal for view state ✅
StateManager.tool_state_changed     # ONLY signal for tool state ✅
```

### Principle 3: Thread Safety by Layer

- **ApplicationState**: Thread-safe (has QMutex) - services may access from background threads
- **StateManager**: Main-thread only - UI preferences don't need cross-thread access

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

### Properties to MIGRATE ❌ (4)

| Property | Current Location | Correct Location | Reason |
|----------|-----------------|------------------|--------|
| `track_data` | StateManager | **ApplicationState** | Curve data (application state) |
| `image_files` | StateManager | **ApplicationState** | Image sequence (application state) |
| `image_directory` | StateManager | **ApplicationState** | Image sequence root |
| `total_frames` | StateManager | **ApplicationState** | Derived from image_files |

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

### Phase 0: Pre-Implementation Fixes (2 hours)

**CRITICAL**: Fix implementation bugs identified in code review before starting migration.

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

---

### Phase 1: Migrate track_data to ApplicationState (Week 1, 8-10 hours)

#### 1.1 Add track_data to ApplicationState

**File**: `stores/application_state.py`

**Current ApplicationState has**:
```python
# Curve data storage
_curves_data: dict[str, CurveDataList]  # Multiple curves

# Signals
curves_changed: Signal = Signal(str)  # Emits curve_name when curve changes
```

**Add legacy compatibility method**:
```python
def set_track_data(self, data: list[tuple[float, float]]) -> None:
    """
    Legacy compatibility method for single-curve workflow.
    Sets data for the active curve.

    Args:
        data: List of (x, y) tuples

    Note: Prefer set_curve_data(curve_name, data) for multi-curve workflows.
          Caller should handle is_modified state (UI concern).
    """
    active_curve = self.active_curve  # ✅ FIXED: Use property, not method
    if active_curve is None:
        logger.warning("set_track_data called with no active curve")
        return

    self.set_curve_data(active_curve, data)
    # curves_changed signal emitted by set_curve_data()

def get_track_data(self) -> list[tuple[float, float]]:
    """
    Legacy compatibility method for single-curve workflow.
    Gets data for the active curve.

    Returns:
        List of (x, y) tuples for active curve, or empty list

    Note: Prefer get_curve_data(curve_name) for multi-curve workflows.
    """
    active_curve = self.active_curve  # ✅ FIXED: Use property, not method
    if active_curve is None:
        return []

    return self.get_curve_data(active_curve)

@property
def has_data(self) -> bool:
    """Legacy compatibility: Check if active curve has data."""
    return len(self.get_track_data()) > 0
```

#### 1.2 Update StateManager to Delegate

**File**: `ui/state_manager.py`

**Replace implementation**:
```python
# OLD: Direct storage (REMOVE these)
# _track_data: list[tuple[float, float]] = []
# _has_data: bool = False

# NEW: Delegate to ApplicationState (use cached self._app_state)
@property
def track_data(self) -> list[tuple[float, float]]:
    """Get track data from ApplicationState (legacy compatibility)."""
    return self._app_state.get_track_data()  # ✅ OPTIMIZED: Use cached reference

def set_track_data(self, data: list[tuple[float, float]], mark_modified: bool = True) -> None:
    """Set track data via ApplicationState (legacy compatibility)."""
    self._app_state.set_track_data(data)  # ✅ OPTIMIZED: Use cached reference
    # Signal: ApplicationState.curves_changed emits (not StateManager)

    if mark_modified:
        self.is_modified = True

@property
def has_data(self) -> bool:
    """Check if active curve has data (legacy compatibility)."""
    return self._app_state.has_data  # ✅ OPTIMIZED: Use cached reference
```

**Remove**: `_track_data` and `_has_data` instance variables

#### 1.3 Update All Callers

**Find callers**:
```bash
uv run rg "state_manager\.track_data" --type py
uv run rg "state_manager\.set_track_data" --type py
uv run rg "state_manager\.has_data" --type py
```

**Expected files** (~10-15 files):
- `data/data_operations.py` - File loading/saving
- `ui/main_window.py` - Menu actions
- `services/data_service.py` - Data operations
- Test files - Update to use ApplicationState directly

**Migration pattern**:
```python
# OLD: Via StateManager
state_manager.set_track_data(data)

# NEW: Via ApplicationState (for new code)
from stores.application_state import get_application_state
get_application_state().set_curve_data(curve_name, data)

# OR: Keep StateManager call (backward compatible)
state_manager.set_track_data(data)  # Now delegates to ApplicationState
```

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

def _on_curve_data_changed(self, curve_name: str) -> None:
    """Curve data changed - refresh if it's the active curve."""
    if curve_name == state.active_curve:  # ✅ FIXED: Use property
        # Refresh UI
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
    def on_changed(curve_name: str):
        nonlocal signal_emitted
        signal_emitted = True

    app_state.curves_changed.connect(on_changed)
    state_manager.set_track_data([(1.0, 2.0)])

    assert signal_emitted
```

**Integration tests**: Verify UI updates work with new signal source

---

### Phase 2: Migrate image_files to ApplicationState (Week 2, 6-8 hours)

#### 2.1 Add Image Sequence to ApplicationState

**File**: `stores/application_state.py`

**Step 1: Add signal** (after line 141, with other signals):
```python
# Image sequence signal
image_sequence_changed: Signal = Signal()  # Emits when image files or directory changes
```

**Step 2: Add instance variables** (in `__init__`, after line 166):
```python
# Image sequence state
self._image_files: list[str] = []
self._image_directory: str | None = None
self._total_frames: int = 1
```

**Step 3: Add methods** (following ApplicationState patterns):
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

#### 2.2 Migrate total_frames to ApplicationState

**Current**: `total_frames` is in StateManager but delegates to ApplicationState

**Verify**: Check if already migrated
```bash
uv run rg "total_frames" stores/application_state.py
```

**If not migrated**: Add `_total_frames` to ApplicationState and migrate (likely already done based on git history)

#### 2.3 Update StateManager to Delegate

**File**: `ui/state_manager.py`

```python
# Remove instance variables (DELETE these)
# _image_files: list[str] = []
# _image_directory: str | None = None
# _total_frames: int = 1  (if still here)

@property
def image_files(self) -> list[str]:
    """Get image files from ApplicationState (legacy compatibility)."""
    return self._app_state.get_image_files()  # ✅ OPTIMIZED: Use cached reference

def set_image_files(self, files: list[str]) -> None:
    """Set image files via ApplicationState (legacy compatibility)."""
    self._app_state.set_image_files(files)  # ✅ OPTIMIZED: Use cached reference
    # Signal: ApplicationState.image_sequence_changed emits

@property
def image_directory(self) -> str | None:
    """Get image directory from ApplicationState (legacy compatibility)."""
    return self._app_state.get_image_directory()  # ✅ OPTIMIZED: Use cached reference

@image_directory.setter
def image_directory(self, directory: str | None) -> None:
    """Set image directory via ApplicationState (legacy compatibility)."""
    self._app_state.set_image_directory(directory)  # ✅ OPTIMIZED: Use cached reference
    # Signal: ApplicationState.image_sequence_changed emits

@property
def total_frames(self) -> int:
    """Get total frames from ApplicationState (legacy compatibility)."""
    return self._app_state.get_total_frames()  # ✅ OPTIMIZED: Use cached reference

# Note: total_frames is derived from image_files count, set automatically
```

#### 2.4 Update Callers

**Find callers**:
```bash
uv run rg "\.image_files\b" --type py
uv run rg "set_image_files" --type py
uv run rg "\.image_directory\b" --type py
```

**Expected files**:
- `data/data_operations.py` - Image loading
- `services/data_service.py` - Image management
- `ui/main_window.py` - File menu actions

**Update to use ApplicationState directly** (or keep StateManager delegation)

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
        self._emit_signal('undo_state_changed', can_undo)

    if self._can_redo != can_redo:
        self._can_redo = can_redo
        self._emit_signal('redo_state_changed', can_redo)
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
        self._emit_signal('tool_state_changed', tool)
        logger.debug(f"Current tool changed to: {tool}")
```

#### 3.3 Connect Signals in SignalConnectionManager

**File**: `ui/controllers/signal_connection_manager.py`

**Add connections**:
```python
def _connect_state_manager_signals(self) -> None:
    """Connect StateManager UI state signals."""

    # Undo/Redo toolbar button state
    _ = self.state_manager.undo_state_changed.connect(
        lambda enabled: self.main_window.ui.toolbar.undo_button.setEnabled(enabled)
    )
    _ = self.state_manager.redo_state_changed.connect(
        lambda enabled: self.main_window.ui.toolbar.redo_button.setEnabled(enabled)
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

def test_undo_button_updates_with_state(qtbot, main_window):
    """Undo button enables/disables based on history state."""
    # Initially no undo
    main_window.state_manager.set_history_state(can_undo=False, can_redo=False)
    assert not main_window.ui.toolbar.undo_button.isEnabled()

    # Enable undo
    main_window.state_manager.set_history_state(can_undo=True, can_redo=False)
    qtbot.wait(10)  # Allow signal processing
    assert main_window.ui.toolbar.undo_button.isEnabled()
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
    - ApplicationState: Single source of truth for all application data
    - DataService: File I/O and data operations

    **Legacy Compatibility**:
    Some properties (track_data, image_files, total_frames) delegate to
    ApplicationState for backward compatibility with existing code. New code
    should use ApplicationState directly for data access.

    **Thread Safety**:
    StateManager assumes main-thread access only (UI preferences). For
    thread-safe data access, use ApplicationState which has QMutex protection.

    **Signals**:
    - view_state_changed: Zoom, pan, or bounds changed
    - file_changed: Current file path changed
    - modified_changed: Dirty flag changed
    - undo_state_changed: Undo availability changed
    - redo_state_changed: Redo availability changed
    - tool_state_changed: Current tool changed
    - playback_state_changed: Playback mode changed
    - active_timeline_point_changed: Active timeline point changed

    **Data signals** (delegated to ApplicationState):
    - ApplicationState.curves_changed: Curve data changed
    - ApplicationState.image_sequence_changed: Image files changed
    - ApplicationState.total_frames_changed: Frame count changed
    - ApplicationState.current_frame_changed: Current frame changed
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
- Result: Single source of truth, no duplicate signals
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

#### 4.4 Document Deferred Work

**StateManager._original_data Not Migrated (Deferred)**:

The `_original_data` property (line 72 in StateManager) stores the original unmodified curve data before smoothing/filtering. This is **application data** and should eventually migrate to ApplicationState.

**Why deferred**:
- Needs multi-curve design (original state per curve)
- Complex: Ties into undo/redo system
- Low priority: Current usage is limited to smoothing operations

**Future work**: Add to Phase 7 or 8 when multi-curve undo/redo is implemented.

**Document in ARCHITECTURE.md**:
```markdown
## Known Technical Debt (Post-Migration)

**StateManager._original_data** (Deferred to Phase 7/8):
- Currently: Stores original curve data before smoothing (in StateManager)
- Should be: Per-curve original state in ApplicationState
- Blocked by: Multi-curve undo/redo design not yet implemented
- Impact: LOW - Limited usage, doesn't affect new code
```

#### 4.5 Archive Old Plan

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

- **None identified** - Following proven FrameChangeCoordinator pattern

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
- [ ] **total_frames correct**: Derived from image count in ApplicationState
- [ ] **UI signals added**: undo_state_changed, redo_state_changed, tool_state_changed
- [ ] **Backward compatible**: Old API calls still work via delegation

---

## Timeline and Effort

| Phase | Duration | Effort | Deliverables |
|-------|----------|--------|--------------|
| **Phase 0: Pre-fixes** | **Day 1** | **2h** | **Bug fixes + verification** |
| Phase 1: track_data | Week 1 | 8-10h | Migration + tests |
| Phase 2: image_files | Week 2 | 6-8h | Migration + tests |
| Phase 3: UI signals | Week 2 | 4-6h | Signals + connections |
| Phase 4: Documentation | Week 3 | 2-4h | Docs + cleanup |
| **Total** | **2-3 weeks** | **22-30h** | **Complete migration** |

**Revised from original estimate**: Added Phase 0 (2h) for implementation bug fixes identified in code review.

**Comparison to Quick Fix (Option B)**:
- Option B: 7-11 hours, maintains technical debt
- Option A: 22-30 hours, eliminates technical debt
- **Extra cost**: 15-19 hours upfront
- **Future savings**: 50+ hours (prevents compounding debt)

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

---

## Appendix: Signal Reference

### ApplicationState Signals (Data Layer)

```python
# Curve data
curves_changed: Signal = Signal(str)                    # Emits curve_name

# Image sequence
image_sequence_changed: Signal = Signal()               # NEW: Images or directory changed

# Frame state
current_frame_changed: Signal = Signal(int)             # Emits new frame
total_frames_changed: Signal = Signal(int)              # Emits new total

# Selection state
selection_changed: Signal = Signal(str)                 # Emits curve_name
selected_curves_changed: Signal = Signal(set)           # Emits curve names
show_all_curves_changed: Signal = Signal(bool)          # Emits show_all
active_curve_changed: Signal = Signal(str)              # Emits curve_name or ""
```

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
- **2025-10-07 16:30**: **AMENDED** - Fixed implementation bugs identified in code review
  - Fixed: `get_active_curve_name()` → `self.active_curve` (property)
  - Fixed: Thread safety pattern (removed explicit mutex locks, use `_assert_main_thread()` + `_emit()`)
  - Fixed: Signal storage (use `_emit()` instead of `.add()` to pending_signals)
  - Added: Phase 0 for pre-implementation verification (2 hours)
  - Added: Cached `self._app_state` usage (architect optimization)
  - Added: `_original_data` deferral documentation
  - Revised timeline: 22-30 hours (was 20-28 hours)
- **Author**: Architectural review identified hybrid state as root cause
- **Status**: READY FOR EXECUTION - Implementation bugs fixed, awaiting approval
- **Supersedes**: `STATEMANAGER_SIGNAL_ARCHITECTURE_REFACTOR.md` (Option B)

---

*End of Migration Plan - Amended Version*
