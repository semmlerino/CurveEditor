# StateManager Simplified Migration Plan

## Executive Summary

**Status**: ✅ **READY FOR EXECUTION** - Clean, debt-free approach

**Goal**: Complete the StateManager migration by moving **ALL** application data to ApplicationState with **ZERO technical debt**.

**Principles**:
- ✅ **KISS**: One API, no temporary code, no dual APIs
- ✅ **DRY**: Update each caller ONCE (not twice)
- ✅ **Zero Technical Debt**: No "temporary" code, no future deprecations
- ✅ **Explicit > Implicit**: Direct curve_name parameters, no hidden state

**Timeline**: 23-31 hours over 2-3 weeks (59-67% faster than original plan)

**Supersedes**: `STATEMANAGER_COMPLETE_MIGRATION_PLAN.md` (Amendment #9)

**Why This is Better**:
- 🚀 **44-63 hours faster** (23-31h vs 55-69h + buffer)
- 🧹 **Zero technical debt** (no dual API to deprecate later)
- 🎯 **Simpler** (5 phases vs 8, no delegation)
- ✅ **DRY compliance** (update callers once, not twice)
- 📖 **Easier to understand** (explicit > implicit)

---

## Table of Contents

1. [Architectural Principles](#architectural-principles)
2. [Current State Analysis](#current-state-analysis)
3. [Migration Plan: 5 Phases](#migration-plan-5-phases)
4. [Testing Strategy](#testing-strategy)
5. [Risk Assessment](#risk-assessment)
6. [Success Metrics](#success-metrics)
7. [Timeline and Effort](#timeline-and-effort)
8. [Comparison to Original Plan](#comparison-to-original-plan)

---

## Architectural Principles

### Principle 1: Single API (KISS)

```
ApplicationState (Data Layer) - ONE WAY to access data
├─ set_curve_data(curve_name, data)     # Explicit multi-curve API
├─ get_curve_data(curve_name)           # Explicit multi-curve API
├─ set_image_files(files, directory)    # Direct API
└─ get_image_files()                    # Direct API

❌ NO convenience methods (set_track_data, etc.)
❌ NO dual APIs
❌ NO "temporary" code
```

**Why**: PEP 20 - "There should be one-- and preferably only one --obvious way to do it."

### Principle 2: Direct Migration (DRY)

```
❌ Original Plan (update callers TWICE):
Phase 1.3: state_manager.track_data → state_manager delegation
Phase 1.6: state_manager delegation → app_state.get_curve_data()

✅ Simplified Plan (update callers ONCE):
Phase 1: state_manager.track_data → app_state.get_curve_data(curve_name)
```

**Why**: Don't create temporary code just to remove it later.

### Principle 3: Explicit Over Implicit

```python
# ❌ Implicit (hidden dependency on active_curve):
app_state.set_track_data(data)

# ✅ Explicit (clear which curve):
active = app_state.active_curve
if active:
    app_state.set_curve_data(active, data)
```

**Why**: No hidden state, no fail-fast brittleness, easier to reason about.

### Principle 4: Zero Technical Debt

- ❌ No "TEMPORARY - WILL BE REMOVED" markers
- ❌ No future deprecation work
- ❌ No dual APIs to maintain
- ✅ Clean architecture from day one

---

## Current State Analysis

### Properties to MIGRATE (5)

| Property | Current Location | Target Location | Phase |
|----------|-----------------|-----------------|-------|
| `track_data` | StateManager | ApplicationState (via `get_curve_data`) | 1 |
| `image_files` | StateManager | ApplicationState | 2 |
| `image_directory` | StateManager | ApplicationState | 2 |
| `total_frames` | StateManager | ApplicationState | 2 |
| `_original_data` | StateManager | ApplicationState | 3 |

### Properties Staying in StateManager (12)

UI preferences only:
- View state: `zoom_level`, `pan_offset`, `view_bounds`
- Tool state: `current_tool`, `smoothing_*`, `tool_options`
- Window state: `window_position`, `splitter_sizes`, `is_fullscreen`
- Session state: `recent_directories`, `file_format`, `current_file`, `is_modified`

### Signals to ADD (3)

New StateManager signals for UI state:
- `undo_state_changed: Signal(bool)` - Toolbar button state
- `redo_state_changed: Signal(bool)` - Toolbar button state
- `tool_state_changed: Signal(str)` - Tool selection state

---

## Migration Plan: 5 Phases

### Phase 0: Add ApplicationState Methods (Week 1, 4-5 hours)

**Goal**: Add missing methods to ApplicationState (multi-curve API only).

#### 0.1 Add Image Sequence Methods

**File**: `stores/application_state.py`

**Add signals** (after existing signals ~line 141):
```python
# Image sequence signals
image_sequence_changed: Signal = Signal()
total_frames_changed: Signal = Signal(int)
```

**Add instance variables** (in `__init__`, ~line 166):
```python
# Image sequence state
self._image_files: list[str] = []
self._image_directory: str | None = None
self._total_frames: int = 1
```

**Add methods** (after existing curve methods, ~line 280):
```python
# ==================== Image Sequence Methods ====================

def set_image_files(self, files: list[str], directory: str | None = None) -> None:
    """
    Set the image file sequence.

    Args:
        files: List of image file paths
        directory: Optional base directory (if None, keeps current)

    Raises:
        TypeError: If files is not a list
        ValueError: If files list is too large or contains invalid paths
    """
    self._assert_main_thread()

    # Validation
    if not isinstance(files, list):
        raise TypeError(f"files must be list, got {type(files).__name__}")

    MAX_FILES = 10_000
    if len(files) > MAX_FILES:
        raise ValueError(f"Too many files: {len(files)} (max: {MAX_FILES})")

    for f in files:
        if not isinstance(f, str):
            raise TypeError(f"File path must be str, got {type(f).__name__}")

    # Update state (NO defensive copy on write for performance)
    old_files = self._image_files
    old_dir = self._image_directory
    self._image_files = files

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
    """Get the image file sequence (defensive copy for safety)."""
    self._assert_main_thread()
    return self._image_files.copy()

def get_image_directory(self) -> str | None:
    """Get the image base directory."""
    self._assert_main_thread()
    return self._image_directory

def set_image_directory(self, directory: str | None) -> None:
    """Set the image base directory (emits signal if changed)."""
    self._assert_main_thread()

    if self._image_directory != directory:
        self._image_directory = directory
        self._emit(self.image_sequence_changed, ())
        logger.debug(f"Image directory changed to: {directory}")

def get_total_frames(self) -> int:
    """Get total frame count (derived from image sequence length)."""
    self._assert_main_thread()
    return self._total_frames
```

#### 0.2 Add Original Data Methods

**Add instance variable** (in `__init__`, ~line 166):
```python
# Original data for undo/comparison
self._original_data: dict[str, CurveDataList] = {}
```

**Add methods** (after image methods):
```python
# ==================== Original Data (Undo/Comparison) ====================

def set_original_data(self, curve_name: str, data: CurveDataInput) -> None:
    """
    Store original unmodified data for comparison/undo.

    Args:
        curve_name: Curve to store original data for
        data: Original curve data before modifications
    """
    self._assert_main_thread()
    self._original_data[curve_name] = list(data)
    logger.debug(f"Stored original data for '{curve_name}': {len(data)} points")

def get_original_data(self, curve_name: str) -> CurveDataList:
    """
    Get original unmodified data for curve.

    Args:
        curve_name: Curve to get original data for

    Returns:
        Copy of original data, or empty list if not set
    """
    self._assert_main_thread()
    return self._original_data.get(curve_name, []).copy()

def clear_original_data(self, curve_name: str | None = None) -> None:
    """
    Clear original data (after committing changes).

    Args:
        curve_name: Curve to clear, or None to clear all
    """
    self._assert_main_thread()

    if curve_name is None:
        self._original_data.clear()
        logger.debug("Cleared all original data")
    elif curve_name in self._original_data:
        del self._original_data[curve_name]
        logger.debug(f"Cleared original data for '{curve_name}'")
```

#### 0.3 Fix current_frame.setter

**File**: `ui/state_manager.py`

**Update** (current_frame.setter, ~line 354):
```python
@current_frame.setter
def current_frame(self, frame: int) -> None:
    """Set the current frame number (with clamping to valid range)."""
    # Get total frames from ApplicationState
    total = self._app_state.get_total_frames()
    frame = max(1, min(frame, total))

    # Delegate to ApplicationState for storage
    self._app_state.set_frame(frame)
    logger.debug(f"Current frame changed to: {frame}")
```

**Why**: This removes dependency on `self._total_frames` before Phase 2 removes it.

#### 0.4 Verification

**Run tests**:
```bash
# Verify all methods exist
python3 -c "
from stores.application_state import get_application_state
state = get_application_state()
assert hasattr(state, 'set_image_files')
assert hasattr(state, 'get_image_files')
assert hasattr(state, 'get_image_directory')
assert hasattr(state, 'get_total_frames')
assert hasattr(state, 'set_original_data')
assert hasattr(state, 'get_original_data')
assert hasattr(state, 'clear_original_data')
print('✅ Phase 0 complete - all methods exist')
"

# Run unit tests
uv run pytest tests/stores/test_application_state.py -v
```

**Checklist**:
- [ ] Added `image_sequence_changed` signal
- [ ] Added `total_frames_changed` signal
- [ ] Added `_image_files`, `_image_directory`, `_total_frames` instance variables
- [ ] Added `_original_data` instance variable
- [ ] Implemented all 7 methods (image + original data)
- [ ] Updated `current_frame.setter` to use ApplicationState
- [ ] All tests pass

---

### Phase 1: Migrate track_data (Week 1-2, 6-8 hours)

**Goal**: Remove `track_data` from StateManager, migrate all callers to ApplicationState.

#### 1.1 Find All Callers

```bash
# Find all uses of track_data
uv run rg "state_manager\.track_data\b" --type py > track_data_callers.txt
uv run rg "state_manager\.set_track_data" --type py >> track_data_callers.txt
uv run rg "state_manager\.has_data\b" --type py >> track_data_callers.txt
```

**Expected files** (~10-15):
- `services/data_service.py` - File I/O
- `ui/main_window.py` - Menu actions
- `ui/controllers/*.py` - Various controllers
- `tests/*.py` - Test files

#### 1.2 Update Each Caller (ONCE, not twice)

**Pattern** (update directly to ApplicationState):

```python
# BEFORE (StateManager):
data = state_manager.track_data
state_manager.set_track_data(new_data)
has_data = state_manager.has_data

# AFTER (ApplicationState - explicit multi-curve):
from stores.application_state import get_application_state
app_state = get_application_state()

active = app_state.active_curve
if active:
    data = app_state.get_curve_data(active)
    app_state.set_curve_data(active, new_data)
    has_data = len(app_state.get_curve_data(active)) > 0
else:
    # Handle no active curve case
    data = []
    has_data = False
```

**Example - data_service.py**:
```python
# BEFORE:
def load_tracking_file(self, path: str) -> None:
    data = self._parse_file(path)
    state_manager.set_track_data(data)
    state_manager.current_file = path
    state_manager.is_modified = False

# AFTER:
def load_tracking_file(self, path: str) -> None:
    data = self._parse_file(path)

    # Data to ApplicationState (explicit curve)
    app_state = get_application_state()
    curve_name = self._extract_curve_name(path) or "__default__"
    app_state.set_curve_data(curve_name, data)
    app_state.set_active_curve(curve_name)

    # UI state to StateManager (separate concern)
    state_manager.current_file = path
    state_manager.is_modified = False
```

#### 1.3 Update Signal Connections

**Find signal listeners**:
```bash
uv run rg "track_data_changed" --type py
```

**Note**: StateManager doesn't currently emit `track_data_changed` signal, so this should find nothing. ApplicationState already emits `curves_changed`.

**If needed**:
```python
# Connect to ApplicationState signal
app_state = get_application_state()
app_state.curves_changed.connect(self._on_curves_changed)

def _on_curves_changed(self, curves_data: dict[str, CurveDataList]) -> None:
    """Curve data changed - refresh if active curve changed."""
    active = app_state.active_curve
    if active and active in curves_data:
        self.refresh_view()
```

#### 1.4 Remove from StateManager

**File**: `ui/state_manager.py`

**Delete entirely**:
```python
# DELETE these instance variables (find with grep):
# self._track_data: list[tuple[float, float]] = []
# self._has_data: bool = False

# DELETE any track_data property or method
# @property
# def track_data(self): ...
#
# def set_track_data(self, data): ...
#
# @property
# def has_data(self): ...
```

**Verify removal**:
```bash
# Should find ZERO matches:
uv run rg "self\._track_data" ui/state_manager.py
uv run rg "def track_data|@property.*track_data" ui/state_manager.py
```

#### 1.5 Add Safety Layer

**Add to StateManager** (after `__init__`):
```python
def __getattr__(self, name: str) -> None:
    """Provide clear error for removed data access methods."""
    removed_methods = {
        "track_data", "set_track_data", "has_data"
    }

    if name in removed_methods:
        raise AttributeError(
            f"StateManager.{name} was removed in StateManager migration. "
            f"Use ApplicationState directly:\n"
            f"  from stores.application_state import get_application_state\n"
            f"  app_state = get_application_state()\n"
            f"  active = app_state.active_curve\n"
            f"  if active:\n"
            f"      data = app_state.get_curve_data(active)\n"
            f"See CLAUDE.md for migration guide."
        )

    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
```

**Why**: Catches dynamic attribute access with clear migration instructions.

#### 1.6 Testing

**Unit tests**:
```python
def test_track_data_in_application_state():
    """Track data is stored in ApplicationState, not StateManager."""
    app_state = get_application_state()

    # Create curve
    app_state.create_curve("Track1")
    app_state.set_active_curve("Track1")

    # Set data via ApplicationState
    test_data = [(1.0, 2.0), (3.0, 4.0)]
    app_state.set_curve_data("Track1", test_data)

    # Verify stored correctly
    assert app_state.get_curve_data("Track1") == test_data

def test_state_manager_track_data_removed():
    """StateManager no longer has track_data access."""
    state_manager = StateManager()

    # Should raise AttributeError with clear message
    with pytest.raises(AttributeError, match="was removed in StateManager migration"):
        _ = state_manager.track_data

def test_curves_changed_signal_emits():
    """ApplicationState emits curves_changed signal."""
    app_state = get_application_state()
    app_state.create_curve("Track1")

    signal_emitted = False
    def on_changed(curves_data: dict[str, CurveDataList]):
        nonlocal signal_emitted
        signal_emitted = True

    app_state.curves_changed.connect(on_changed)
    app_state.set_curve_data("Track1", [(1.0, 2.0)])

    assert signal_emitted

def test_explicit_curve_name_required():
    """Migration forces explicit curve_name parameter."""
    app_state = get_application_state()
    app_state.create_curve("Track1")

    # Explicit curve_name (good)
    app_state.set_curve_data("Track1", [(1.0, 2.0)])
    assert len(app_state.get_curve_data("Track1")) == 1
```

**Integration tests**:
```bash
# Full test suite should pass
uv run pytest tests/ -v
```

#### 1.7 Verification Checklist

**Complete removal verification**:

```bash
# No instance variables (should find ZERO):
uv run rg "self\._track_data" ui/state_manager.py
uv run rg "self\._has_data" ui/state_manager.py

# No methods/properties (should find ZERO):
uv run rg "(@property|def)\s+(track_data|set_track_data|has_data)" ui/state_manager.py

# No external callers (should find ZERO):
uv run rg "state_manager\.track_data\b" --type py
uv run rg "state_manager\.set_track_data" --type py
uv run rg "state_manager\.has_data\b" --type py
```

**Migration hotspots verified**:
- [ ] `data_bounds` (state_manager.py:~243) - Uses `_app_state.get_curve_data()`, not `_track_data`
- [ ] `reset_to_defaults` (state_manager.py:~629) - Delegates to ApplicationState
- [ ] `get_state_summary` (state_manager.py:~686) - Reads from ApplicationState
- [ ] All tests pass: `uv run pytest tests/ -v`

---

### Phase 2: Migrate image_files (Week 2, 5-7 hours)

**Goal**: Remove image-related fields from StateManager, migrate to ApplicationState.

#### 2.1 Find All Callers

```bash
uv run rg "\\.image_files\\b" --type py > image_callers.txt
uv run rg "set_image_files" --type py >> image_callers.txt
uv run rg "\\.image_directory\\b" --type py >> image_callers.txt
uv run rg "\\.total_frames\\b" --type py >> image_callers.txt
```

#### 2.2 Update Each Caller (ONCE)

```python
# BEFORE (StateManager):
files = state_manager.image_files
state_manager.set_image_files(files)
directory = state_manager.image_directory
total = state_manager.total_frames

# AFTER (ApplicationState):
from stores.application_state import get_application_state
app_state = get_application_state()

files = app_state.get_image_files()
app_state.set_image_files(files, directory="/path/to/images")
directory = app_state.get_image_directory()
total = app_state.get_total_frames()
```

**Example - data_service.py**:
```python
# BEFORE:
def load_image_sequence(self, directory: str) -> None:
    files = self._scan_directory(directory)
    state_manager.image_directory = directory
    state_manager.set_image_files(files)

# AFTER:
def load_image_sequence(self, directory: str) -> None:
    files = self._scan_directory(directory)

    # Image sequence to ApplicationState
    app_state = get_application_state()
    app_state.set_image_files(files, directory=directory)
```

#### 2.3 Update Signal Connections

**Find signal listeners**:
```bash
uv run rg "image.*changed" --type py
```

**Connect to ApplicationState signals**:
```python
app_state.image_sequence_changed.connect(self._on_images_changed)
app_state.total_frames_changed.connect(self._on_total_frames_changed)

def _on_images_changed(self) -> None:
    """Image sequence changed - refresh timeline."""
    self.update_timeline()

def _on_total_frames_changed(self, total: int) -> None:
    """Total frames changed - update UI limits."""
    self.timeline.setMaximum(total)
```

#### 2.4 Remove from StateManager

**Delete from ui/state_manager.py**:
```python
# DELETE these instance variables:
# self._image_files: list[str] = []
# self._image_directory: str | None = None
# self._total_frames: int = 1

# DELETE any image-related properties/methods
```

**Verify removal**:
```bash
# Should find ZERO matches:
uv run rg "self\\._image_files|self\\._total_frames|self\\._image_directory" ui/state_manager.py
uv run rg "(@property|def)\\s+(image_files|set_image_files|image_directory|total_frames)" ui/state_manager.py
```

#### 2.5 Update Safety Layer

**Update `__getattr__` in StateManager**:
```python
removed_methods = {
    "track_data", "set_track_data", "has_data",
    "image_files", "set_image_files", "image_directory", "total_frames"
}
```

#### 2.6 Testing

```python
def test_image_files_in_application_state():
    """Image files are stored in ApplicationState."""
    app_state = get_application_state()

    files = ["/path/img001.jpg", "/path/img002.jpg"]
    app_state.set_image_files(files, directory="/path")

    assert app_state.get_image_files() == files
    assert app_state.get_image_directory() == "/path"
    assert app_state.get_total_frames() == 2

def test_total_frames_derived_from_images():
    """total_frames updates automatically from image count."""
    app_state = get_application_state()

    app_state.set_image_files(["/img1.jpg", "/img2.jpg", "/img3.jpg"])
    assert app_state.get_total_frames() == 3

    app_state.set_image_files([])
    assert app_state.get_total_frames() == 1  # Default

def test_image_sequence_changed_signal():
    """image_sequence_changed signal emits on changes."""
    app_state = get_application_state()

    signal_count = 0
    def on_changed():
        nonlocal signal_count
        signal_count += 1

    app_state.image_sequence_changed.connect(on_changed)
    app_state.set_image_files(["/img1.jpg", "/img2.jpg"])

    assert signal_count == 1
```

#### 2.7 Verification Checklist

```bash
# No instance variables (should find ZERO):
uv run rg "self\\._image_files|self\\._total_frames|self\\._image_directory" ui/state_manager.py

# No methods/properties (should find ZERO):
uv run rg "(@property|def)\\s+(image_files|set_image_files|image_directory|total_frames)" ui/state_manager.py

# No external callers (should find ZERO):
uv run rg "state_manager\\.image_files\\b" --type py
uv run rg "state_manager\\.total_frames\\b" --type py
```

**Migration hotspots verified**:
- [ ] `current_image` (state_manager.py:~446) - Uses `_app_state.get_image_files()`, not `_image_files`
- [ ] `current_frame.setter` (state_manager.py:~354) - Uses `_app_state.get_total_frames()` (already fixed in Phase 0.3)
- [ ] All tests pass

---

### Phase 3: Migrate _original_data (Week 2, 3-4 hours)

**Goal**: Remove `_original_data` from StateManager, complete migration to pure UI layer.

#### 3.1 Find All Callers

```bash
uv run rg "set_original_data|_original_data\\b" --type py > original_data_callers.txt
```

**Expected**: Smoothing operations, undo/redo logic.

#### 3.2 Update Each Caller (ONCE)

```python
# BEFORE (StateManager):
state_manager.set_original_data(data)
original = state_manager._original_data  # Direct field access
# or
original = state_manager.original_data   # Property access

# AFTER (ApplicationState - explicit curve):
from stores.application_state import get_application_state
app_state = get_application_state()

active = app_state.active_curve
if active:
    app_state.set_original_data(active, data)
    original = app_state.get_original_data(active)
```

**Example - smoothing operation**:
```python
# BEFORE:
def apply_smoothing(self) -> None:
    # Store original for undo
    state_manager.set_original_data(state_manager.track_data)

    # Apply smoothing
    smoothed = self._smooth(state_manager.track_data)
    state_manager.set_track_data(smoothed)

# AFTER:
def apply_smoothing(self) -> None:
    app_state = get_application_state()
    active = app_state.active_curve

    if not active:
        return

    # Store original for undo (explicit curve)
    original = app_state.get_curve_data(active)
    app_state.set_original_data(active, original)

    # Apply smoothing (explicit curve)
    smoothed = self._smooth(original)
    app_state.set_curve_data(active, smoothed)
```

#### 3.3 Remove from StateManager

**Delete from ui/state_manager.py**:
```python
# DELETE instance variable:
# self._original_data: list[tuple[float, float]] = []

# DELETE any original_data property or method
```

**Verify removal**:
```bash
# Should find ZERO matches:
uv run rg "self\\._original_data" ui/state_manager.py
uv run rg "(@property|def)\\s+(set_original_data|original_data)" ui/state_manager.py
```

#### 3.4 Update Safety Layer

**Update `__getattr__` in StateManager**:
```python
removed_methods = {
    "track_data", "set_track_data", "has_data",
    "image_files", "set_image_files", "image_directory", "total_frames",
    "original_data", "set_original_data"
}
```

#### 3.5 Testing

```python
def test_original_data_per_curve():
    """Original data is stored per-curve in ApplicationState."""
    app_state = get_application_state()

    data1 = [(1.0, 2.0), (3.0, 4.0)]
    data2 = [(5.0, 6.0), (7.0, 8.0)]

    app_state.set_original_data("Track1", data1)
    app_state.set_original_data("Track2", data2)

    assert app_state.get_original_data("Track1") == data1
    assert app_state.get_original_data("Track2") == data2

def test_clear_original_data():
    """Can clear original data per-curve or all."""
    app_state = get_application_state()

    app_state.set_original_data("Track1", [(1.0, 2.0)])
    app_state.set_original_data("Track2", [(3.0, 4.0)])

    # Clear specific curve
    app_state.clear_original_data("Track1")
    assert app_state.get_original_data("Track1") == []
    assert len(app_state.get_original_data("Track2")) == 1

    # Clear all
    app_state.clear_original_data(None)
    assert app_state.get_original_data("Track2") == []
```

#### 3.6 Verification Checklist

```bash
# No instance variable (should find ZERO):
uv run rg "self\\._original_data" ui/state_manager.py

# No methods/properties (should find ZERO):
uv run rg "(@property|def)\\s+(set_original_data|original_data)" ui/state_manager.py

# No external callers (should find ZERO):
uv run rg "state_manager\\.original_data\\b|state_manager\\.set_original_data" --type py
```

**Final verification** - StateManager is now pure UI layer:
- [ ] NO application data fields remain in StateManager
- [ ] All data is in ApplicationState
- [ ] All tests pass

---

### Phase 4: Add UI State Signals (Week 2-3, 3-4 hours)

**Goal**: Add missing signals for true UI state in StateManager.

#### 4.1 Add Undo/Redo State Signals

**File**: `ui/state_manager.py`

**Add signals** (after existing signals ~line 46):
```python
# History UI state signals (for toolbar button enable/disable)
undo_state_changed: Signal = Signal(bool)  # Emits can_undo
redo_state_changed: Signal = Signal(bool)  # Emits can_redo
```

**Update method** (set_history_state):
```python
def set_history_state(self, can_undo: bool, can_redo: bool,
                      position: int = 0, size: int = 0) -> None:
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
        self._emit_signal(self.undo_state_changed, can_undo)

    if self._can_redo != can_redo:
        self._can_redo = can_redo
        self._emit_signal(self.redo_state_changed, can_redo)
```

#### 4.2 Add Current Tool Signal

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
        self._emit_signal(self.tool_state_changed, tool)
        logger.debug(f"Current tool changed to: {tool}")
```

#### 4.3 Connect Signals in UI

**File**: `ui/controllers/signal_connection_manager.py`

**Add connections**:
```python
def _connect_state_manager_signals(self) -> None:
    """Connect StateManager UI state signals."""

    # Undo/Redo action state (toolbar uses QActions)
    self.state_manager.undo_state_changed.connect(
        lambda enabled: self.main_window.action_undo.setEnabled(enabled)
    )
    self.state_manager.redo_state_changed.connect(
        lambda enabled: self.main_window.action_redo.setEnabled(enabled)
    )

    # Tool state (if toolbar has tool buttons that need syncing)
    self.state_manager.tool_state_changed.connect(
        self._on_tool_changed
    )

def _on_tool_changed(self, tool_name: str) -> None:
    """Update toolbar when tool changes programmatically."""
    logger.debug(f"Tool changed to: {tool_name}")
    # Update toolbar button states if needed
```

#### 4.4 Testing

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
    assert not main_window.action_undo.isEnabled()

    # Enable undo
    main_window.state_manager.set_history_state(can_undo=True, can_redo=False)
    qtbot.wait(10)  # Allow signal processing
    assert main_window.action_undo.isEnabled()
```

---

### Phase 5: Documentation (Week 3, 2-3 hours)

**Goal**: Update documentation to reflect clean architecture.

#### 5.1 Update StateManager Docstring

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

    **⚠️ NO DATA ACCESS METHODS**:
    StateManager does NOT provide access to application data.
    All data access must go through ApplicationState:

    ```python
    from stores.application_state import get_application_state
    app_state = get_application_state()

    # Explicit multi-curve API (one way to do it)
    active = app_state.active_curve
    if active:
        data = app_state.get_curve_data(active)
        app_state.set_curve_data(active, new_data)
    ```

    **Thread Safety**:
    Both StateManager and ApplicationState are main-thread only.
    ApplicationState enforces this via `_assert_main_thread()`.

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

#### 5.2 Update CLAUDE.md

**File**: `CLAUDE.md`

**Update State Management section**:
```markdown
## State Management

**ApplicationState** is the single source of truth for **application data**.

```python
from stores.application_state import get_application_state

state = get_application_state()

# Explicit multi-curve API (one way to do things)
active = state.active_curve
if active:
    # Curve data
    state.set_curve_data(active, curve_data)
    data = state.get_curve_data(active)

    # Original data (for undo)
    state.set_original_data(active, original_data)
    original = state.get_original_data(active)

# Image sequence
state.set_image_files(files, directory="/path/to/images")
files = state.get_image_files()

# Frame state
state.set_frame(42)
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
- StateManager Simplified Migration (23-31 hours)
- Result: Single source of truth, one API, ZERO technical debt

**⚠️ StateManager has NO data access methods**:
```python
# ❌ WRONG - These don't exist
state_manager.track_data
state_manager.image_files
state_manager.total_frames

# ✅ CORRECT - Use ApplicationState directly
state = get_application_state()
active = state.active_curve
if active:
    data = state.get_curve_data(active)
    state.set_curve_data(active, new_data)
```
```

#### 5.3 Update ARCHITECTURE.md

**Add section on State Layer architecture**:

```markdown
### State Layer Architecture

**Separation of Concerns**:

```
ApplicationState (Data)              StateManager (UI Preferences)
├─ Curve data (multi-curve)          ├─ View state (zoom, pan)
├─ Image sequence                    ├─ Tool state (current tool)
├─ Frame state                       ├─ Window state (position, size)
├─ Selection state                   ├─ History UI (can_undo, can_redo)
└─ Original data (undo)              └─ Session state (recent dirs)
```

**API Design**:
- **One way to access data**: Explicit multi-curve API
- **No convenience methods**: Explicit > implicit
- **No temporary code**: Zero technical debt

**Signal Sources**:
- `ApplicationState.*_changed` - Data changes (curves, images, frames, selection)
- `StateManager.*_changed` - UI state changes (view, tool, window)

**No signal duplication** - each data type has exactly one signal source.
```

#### 5.4 Archive Old Plan

```bash
mv docs/STATEMANAGER_COMPLETE_MIGRATION_PLAN.md \
   docs/archive_2025_oct/STATEMANAGER_COMPLETE_MIGRATION_PLAN_AMENDMENT9.md
```

**Add note to archived file**:
```markdown
# ARCHIVED - October 2025

This plan was superseded by Simplified Migration Plan.

See: `docs/STATEMANAGER_SIMPLIFIED_MIGRATION_PLAN.md`

Reason: Tri-agent review (best-practices-checker, code-refactoring-expert,
python-expert-architect) identified:
- Dual API violates PEP 20 (violates KISS)
- Delegation requires updating callers twice (violates DRY)
- "Temporary" code creates technical debt

Simplified plan: One API, direct migration, zero debt, 59-67% faster.
```

---

## Testing Strategy

### Unit Tests (15+ tests)

**ApplicationState methods**:
- `test_image_files_in_application_state()` - Image sequence storage
- `test_total_frames_derived_from_images()` - Automatic frame count
- `test_original_data_per_curve()` - Per-curve original data
- `test_clear_original_data()` - Clear original data
- `test_image_sequence_changed_signal()` - Signal emission
- `test_total_frames_changed_signal()` - Signal emission
- `test_explicit_curve_name_required()` - No implicit active_curve

**StateManager removal**:
- `test_state_manager_track_data_removed()` - Raises AttributeError
- `test_state_manager_image_files_removed()` - Raises AttributeError
- `test_state_manager_original_data_removed()` - Raises AttributeError

**StateManager UI signals**:
- `test_undo_state_changed_signal()` - Undo signal emission
- `test_redo_state_changed_signal()` - Redo signal emission
- `test_tool_state_changed_signal()` - Tool signal emission
- `test_signals_only_emit_on_change()` - No redundant emissions

**Thread safety**:
- `test_application_state_main_thread_only()` - Assert main thread
- `test_cross_thread_access_raises()` - Clear error from other threads

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
- `test_all_callers_migrated()` - No StateManager data access
- `test_no_orphaned_signals()` - No unused signal connections

### Regression Tests

**Run full test suite**:
```bash
uv run pytest tests/ -v
```

**Expected**: All 2100+ tests pass (zero regressions)

---

## Risk Assessment

### Low Risk ✅

- **Clear architecture**: ApplicationState = data, StateManager = UI
- **One API**: No confusion about which method to use
- **Direct migration**: Update callers once, not twice
- **Explicit parameters**: No hidden state dependencies
- **Safety layer**: `__getattr__` catches accidental usage

### Medium Risk ⚠️

- **Caller updates**: Need to update 10-15 files per phase
- **Manual verification**: Grep patterns may miss dynamic access
- **Testing thoroughness**: Need comprehensive integration tests

**Mitigation**:
- Systematic grep-based caller identification
- `__getattr__` catches runtime dynamic access
- Phase-by-phase execution with full test runs
- Safety layer provides clear error messages

### No High Risks 🎉

**Why no high risks**:
- ✅ No delegation to remove later (no "temporary" code)
- ✅ No dual API confusion (one way to do things)
- ✅ No behavioral breaking changes (explicit parameters are clear)
- ✅ No atomic phase dependencies (each phase independent)
- ✅ Simple rollback (git revert per phase)

---

## Success Metrics

### Architectural Cleanliness ✅

- [ ] **One API**: ApplicationState has ONE way to access each data type
- [ ] **Zero temporary code**: No "WILL BE REMOVED" markers
- [ ] **Clear layer separation**: Data in ApplicationState, UI in StateManager
- [ ] **Explicit > Implicit**: No hidden active_curve dependencies
- [ ] **Zero technical debt**: Nothing to deprecate or remove later

### Code Quality ✅

- [ ] **All 2100+ tests pass**: Zero regressions
- [ ] **15+ new tests**: Validate migration and signals
- [ ] **Type checking clean**: `./bpr --errors-only` passes
- [ ] **Safety layer works**: `__getattr__` catches accidental usage

### Documentation ✅

- [ ] **StateManager docstring updated**: Clear architectural scope
- [ ] **CLAUDE.md updated**: Explicit multi-curve API examples
- [ ] **ARCHITECTURE.md updated**: Layer separation documented
- [ ] **Old plan archived**: With explanation

### Migration Completeness ✅

- [ ] **track_data migrated**: No `_track_data` in StateManager
- [ ] **image_files migrated**: No `_image_files` in StateManager
- [ ] **image_directory migrated**: No `_image_directory` in StateManager
- [ ] **total_frames migrated**: Derived from image count in ApplicationState
- [ ] **_original_data migrated**: No `_original_data` in StateManager
- [ ] **UI signals added**: undo_state_changed, redo_state_changed, tool_state_changed
- [ ] **Pure UI layer achieved**: StateManager contains ONLY UI state

---

## Timeline and Effort

| Phase | Duration | Effort | Deliverables |
|-------|----------|--------|--------------|
| **Phase 0: Add ApplicationState methods** | Week 1 | 4-5h | Image methods, original data methods, fix current_frame.setter |
| **Phase 1: Migrate track_data** | Week 1-2 | 6-8h | Direct migration, safety layer, tests |
| **Phase 2: Migrate image_files** | Week 2 | 5-7h | Direct migration, tests |
| **Phase 3: Migrate _original_data** | Week 2 | 3-4h | Direct migration, tests |
| **Phase 4: Add UI signals** | Week 2-3 | 3-4h | Signals, connections, tests |
| **Phase 5: Documentation** | Week 3 | 2-3h | Docs, cleanup, archive old plan |
| **Total** | **2-3 weeks** | **23-31h** | **100% Complete, zero debt** |

---

## Comparison to Original Plan

| Metric | Original Plan (Amendment #9) | Simplified Plan | Improvement |
|--------|------------------------------|-----------------|-------------|
| **Total Effort** | 55-69h + 10-14h buffer = **65-83h** | **23-31h** | **44-63h faster (59-67%)** |
| **Number of Phases** | 8 phases (0, 1, 2, 2.5, 3, 4) | **5 phases** | 3 fewer phases |
| **Caller Updates** | **TWICE** (delegation → direct) | **ONCE** (direct) | 50% less work |
| **Technical Debt Created** | Dual API (deferred 6-12mo) | **ZERO** | ✅ No future work |
| **Temporary Code** | Delegation methods (remove in 1.6, 2.6, 2.5.5) | **NONE** | ✅ No cleanup needed |
| **API Complexity** | Dual API (convenience + explicit) | **Single API** (explicit only) | ✅ KISS compliant |
| **DRY Compliance** | ❌ Creates duplicate API | ✅ **One way** | Follows DRY |
| **PEP 20 Compliance** | ❌ Violates "one way" | ✅ **Compliant** | Pythonic |
| **Fail-Fast Brittleness** | ❌ RuntimeError if no active_curve | ✅ **Explicit parameters** | More robust |
| **Rollback Complexity** | High (phases 1.6, 2.6 are points of no return) | **Low** (git revert per phase) | Safer |
| **Future Deprecation Work** | 6-12 months later | **NONE** | ✅ Done once |

### Why Simplified is Better

**Original Plan Issues**:
1. ❌ Creates dual API (violates KISS, PEP 20)
2. ❌ Requires updating callers twice (violates DRY)
3. ❌ Creates "temporary" code that becomes technical debt
4. ❌ Fail-fast behavior creates brittleness
5. ❌ Timeline tripled through 9 amendments (20h → 69h)

**Simplified Plan Benefits**:
1. ✅ One API (KISS, PEP 20 compliant)
2. ✅ Update callers once (DRY)
3. ✅ No temporary code (zero debt)
4. ✅ Explicit parameters (no brittleness)
5. ✅ 59-67% faster (23-31h vs 65-83h)

**Key Insight**: The original plan tried to maintain backward compatibility with delegation, but this created more work (update twice) and technical debt (remove delegation later). Direct migration is simpler, faster, and cleaner.

---

## Execution Checklist

### Pre-Execution (Before Starting Phase 0)

- [ ] Read entire plan
- [ ] Understand KISS/DRY/zero-debt principles
- [ ] Create feature branch: `git checkout -b feature/statemanager-simplified-migration`
- [ ] Ensure full test suite passes: `uv run pytest tests/ -v`
- [ ] Commit baseline: `git commit -m "Pre-migration baseline"`

### Phase 0 Checklist

- [ ] Add image sequence signals to ApplicationState
- [ ] Add image sequence instance variables to ApplicationState
- [ ] Implement 5 image methods (set_image_files, get_image_files, etc.)
- [ ] Add _original_data instance variable to ApplicationState
- [ ] Implement 3 original data methods (set_original_data, etc.)
- [ ] Fix current_frame.setter to use ApplicationState
- [ ] Run verification script
- [ ] Run tests: `uv run pytest tests/stores/test_application_state.py -v`
- [ ] Commit: `git commit -m "Phase 0: Add ApplicationState methods"`

### Phase 1 Checklist

- [ ] Grep for all track_data callers
- [ ] Update each caller to use ApplicationState directly
- [ ] Update signal connections (if any)
- [ ] Remove _track_data instance variable from StateManager
- [ ] Remove track_data properties/methods from StateManager
- [ ] Add __getattr__ safety layer
- [ ] Run verification greps (should find ZERO)
- [ ] Run tests: `uv run pytest tests/ -v`
- [ ] Commit: `git commit -m "Phase 1: Migrate track_data to ApplicationState"`

### Phase 2 Checklist

- [ ] Grep for all image_files callers
- [ ] Update each caller to use ApplicationState directly
- [ ] Update signal connections
- [ ] Remove image-related instance variables from StateManager
- [ ] Remove image-related properties/methods from StateManager
- [ ] Update __getattr__ safety layer
- [ ] Run verification greps (should find ZERO)
- [ ] Run tests: `uv run pytest tests/ -v`
- [ ] Commit: `git commit -m "Phase 2: Migrate image_files to ApplicationState"`

### Phase 3 Checklist

- [ ] Grep for all _original_data callers
- [ ] Update each caller to use ApplicationState directly
- [ ] Remove _original_data instance variable from StateManager
- [ ] Remove original_data properties/methods from StateManager
- [ ] Update __getattr__ safety layer
- [ ] Run verification greps (should find ZERO)
- [ ] Verify StateManager is pure UI layer
- [ ] Run tests: `uv run pytest tests/ -v`
- [ ] Commit: `git commit -m "Phase 3: Migrate _original_data to ApplicationState"`

### Phase 4 Checklist

- [ ] Add undo_state_changed signal to StateManager
- [ ] Add redo_state_changed signal to StateManager
- [ ] Add tool_state_changed signal to StateManager
- [ ] Update set_history_state to emit signals
- [ ] Update current_tool.setter to emit signal
- [ ] Connect signals in SignalConnectionManager
- [ ] Run tests: `uv run pytest tests/ -v`
- [ ] Commit: `git commit -m "Phase 4: Add UI state signals"`

### Phase 5 Checklist

- [ ] Update StateManager docstring
- [ ] Update CLAUDE.md State Management section
- [ ] Update ARCHITECTURE.md State Layer section
- [ ] Archive old plan with explanation
- [ ] Run full test suite: `uv run pytest tests/ -v`
- [ ] Run type checking: `./bpr --errors-only`
- [ ] Commit: `git commit -m "Phase 5: Update documentation"`

### Post-Execution

- [ ] Final verification: All greps show ZERO StateManager data access
- [ ] Final test run: All 2100+ tests pass
- [ ] Review changes: `git diff main`
- [ ] Create PR: `gh pr create --title "StateManager Simplified Migration (KISS/DRY/Zero Debt)"`
- [ ] Update CHANGELOG.md with migration notes

---

## Rollback Procedures

**Easy rollback** (any phase):

```bash
# Rollback to previous commit
git revert HEAD

# Or rollback entire branch
git checkout main
git branch -D feature/statemanager-simplified-migration

# Restart from baseline
git checkout -b feature/statemanager-simplified-migration
```

**Why rollback is easy**:
- No delegation to untangle (unlike original plan)
- Each phase is independent
- No "temporary" code to track
- Git revert per phase or full branch reset

---

## Document History

- **2025-10-09**: Initial simplified plan created after tri-agent review
- **Basis**: Python-Expert-Architect recommendations (KISS, DRY, zero debt)
- **Supersedes**: `STATEMANAGER_COMPLETE_MIGRATION_PLAN.md` (Amendment #9)
- **Author**: Tri-agent synthesis (best-practices-checker, code-refactoring-expert, python-expert-architect)
- **Status**: ✅ **READY FOR EXECUTION**

---

*End of Simplified Migration Plan*
