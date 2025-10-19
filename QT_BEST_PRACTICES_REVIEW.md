# Qt & Python Best Practices Review: ELIMINATE_COORDINATOR_PLAN.md

**Date**: October 19, 2025
**Review Scope**: Signal patterns, Qt lifecycle, memory management, threading, refactoring approach
**Severity Rating**: High - plan contains fundamental Qt misconceptions that could introduce new bugs

---

## Executive Summary

The ELIMINATE_COORDINATOR_PLAN.md proposes to eliminate `FrameChangeCoordinator` and switch from `Qt.QueuedConnection` to direct signal connections. **This approach has critical Qt best practice violations:**

1. **Misdiagnosis of Root Cause**: Plan blames `QueuedConnection` when it's actually correct for this use case. The real issue is the connection TYPE, not the coordinator pattern.
2. **Introduces Race Conditions**: Removing the coordinator without proper synchronization allows non-deterministic signal execution order.
3. **Creates Memory Leaks**: Direct connections to singleton `ApplicationState` won't clean up when widgets destroyed.
4. **Feature Flag Anti-Pattern**: Using feature flags to maintain dual signal paths violates refactoring best practices.
5. **Inadequate Lifecycle Management**: Relies on Python `__del__` instead of Qt's proven object lifetime patterns.

**Recommendation**: Do NOT proceed with this plan as written. Instead, fix the ROOT CAUSE (connection type and data atomicity) while keeping the coordinator pattern which is architecturally sound.

---

## Critical Violations

### VIOLATION 1: Fundamental Misunderstanding of Qt Signal Connection Types

**Severity**: CRITICAL
**Files Affected**: `ELIMINATE_COORDINATOR_PLAN.md` (lines 313-335), `frame_change_coordinator.py` (lines 107-114)

**The Problem**:
- Plan assumes `Qt.QueuedConnection` is "wrong" and `AutoConnection` (default) is "right"
- Actually removes the connection that prevents nested signal/slot execution
- Replaces it with `AutoConnection` which becomes `DirectConnection` when same thread (default behavior)

**Qt Reality**:
```
AutoConnection  → DirectConnection (same thread) OR QueuedConnection (different thread)
QueuedConnection → Always deferred to next event loop iteration (PREVENTS nesting)
DirectConnection → Synchronous (can cause nesting issues when signal emitted from within slot)
```

**Current Code** (frame_change_coordinator.py:109-112):
```python
_ = self.main_window.state_manager.frame_changed.connect(
    self.on_frame_changed,
    Qt.QueuedConnection,  # Defers execution to next event loop iteration
)
```

**What Plan Proposes** (ELIMINATE_COORDINATOR_PLAN.md Phase 1-3):
```python
# WRONG - will use AutoConnection by default
self._app_state.frame_changed.connect(self._on_frame_changed)
# In same thread → becomes DirectConnection (synchronous)
# This reintroduces the nested execution problem!
```

**Why This Matters**:
1. `DirectConnection` executes immediately, synchronously
2. If a slot handler emits signals that trigger other handlers, execution nests
3. This can cause state to be modified between signal emit and handler completion
4. Tests pass (synchronous execution all happens immediately)
5. Real app fails (user input sequence exposes ordering issues)

**Best Practice Solution**:
Instead of removing the coordinator, FIX it by removing `QueuedConnection`:

```python
# Frame change coordinator KEEP, just fix connection type
from PySide6.QtCore import Qt

def connect(self) -> None:
    """Connect with DirectConnection for deterministic, synchronous handling."""
    # Use default AutoConnection (becomes DirectConnection in same thread)
    # or explicitly use DirectConnection
    _ = self.main_window.state_manager.frame_changed.connect(
        self.on_frame_changed
        # No connection type = AutoConnection = DirectConnection (same thread)
        # Synchronous, deterministic, prevents nested execution chaos
    )
```

**Why This Works**:
- DirectConnection makes execution synchronous and deterministic
- Coordinator ensures execution order is controlled
- Each phase completes before next phase starts
- No interleaving of state changes
- Still benefits from singleton ApplicationState

---

### VIOLATION 2: Race Conditions Created by Feature Flags

**Severity**: HIGH
**Files Affected**: `ELIMINATE_COORDINATOR_PLAN.md` (Phases 1-5), proposed new code

**The Problem**:
Plan uses feature flags to maintain two parallel signal paths:
- `USE_DIRECT_FRAME_CONNECTION = True/False` to toggle between coordinator and direct connections
- Both paths tested separately, never simultaneously
- Creates false sense of safety during testing phase

**Phase 1 Implementation** (ELIMINATE_COORDINATOR_PLAN.md:51-54):
```python
# Feature flag wrapping both paths
if USE_DIRECT_FRAME_CONNECTION:
    self._app_state.frame_changed.connect(self._on_frame_changed)  # Direct
else:
    # Coordinator still connected (parallel paths!)
```

**Why This Violates Best Practices**:

1. **Dual Execution**: Both direct connection AND coordinator are active during flag==True
   - Frame change triggers both paths
   - Creates duplicate updates
   - Makes testing unreliable

2. **Inadequate Test Coverage**:
   - With flag=False: Tests coordinator path (WORKS - uses QueuedConnection)
   - With flag=True: Tests direct path (appears to work in synchronous test)
   - Switch to production with flag=True: Non-deterministic failures appear

3. **Single Source of Truth Violation**:
   - Qt signals are designed to have ONE connection path
   - Maintaining two paths violates SOLID principle
   - Configuration flags fine; signal architecture flags are problematic

**Real Execution During Testing**:
```
User scrubs timeline (multiple frames rapidly)
│
├─ Frame change event #1
│  ├─ Coordinator handler fires (QueuedConnection - deferred)
│  └─ Direct handler fires (AutoConnection - immediate)
│     └─ Modifies view state
│
├─ Frame change event #2 (queued)
│  ├─ Coordinator handler fires
│  └─ Direct handler fires
│     └─ Modifies same view state (CONFLICT!)
│
└─ Race condition manifests
```

**Qt Best Practice**: Migrate completely to new pattern, don't maintain parallel signal paths

**Correct Approach**:
1. Fix the connection TYPE in coordinator (remove QueuedConnection)
2. Delete coordinator ENTIRELY when all components independently ready
3. No feature flags for signal architecture changes
4. One test pass with old code, one with new code, no parallel paths

---

### VIOLATION 3: Memory Leaks from Singleton State

**Severity**: HIGH
**Files Affected**: `ui/curve_view_widget.py` (lines 176-187), `state_sync_controller.py`

**The Problem**:
CurveViewWidget connects directly to `ApplicationState` (singleton):
- When widget destroyed, signal connections remain
- `ApplicationState` keeps widget alive via signal slot references
- Memory leak: widget not freed until application terminates

**Current Code** (curve_view_widget.py:176-180):
```python
_ = self.signal_manager.connect(
    self._app_state.selection_state_changed,
    self._on_selection_state_changed,
    "selection_state_changed",
)
```

**Issue**:
- `signal_manager` tracks connections via weak reference (line 110 of signal_manager.py)
- But `ApplicationState` doesn't know about this cleanup
- When widget destroyed, `ApplicationState` still holds the slot reference
- Slot cannot be garbage collected

**Cascading Problem**:
```python
# state_sync_controller.py connections bypass SignalManager
self._app_state.curves_changed.connect(self._on_app_state_curves_changed)
# ^^^ NOT tracked by signal_manager
# When StateSyncController destroyed, connection remains in ApplicationState
# Memory leak guaranteed
```

**Qt Best Practice**: Use object lifetime for cleanup

**Correct Approach**:
```python
# Option 1: Use Qt parent-child relationships (PREFERRED)
class CurveViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Make a helper object with widget as parent
        # When widget destroyed, helper destroyed, signals auto-disconnected
        self._signal_helper = SignalHelper(self)

# Option 2: Explicit cleanup in destructor
class CurveViewWidget(QWidget):
    def __del__(self):
        # Explicitly disconnect all signals
        self._app_state.selection_state_changed.disconnect(self._on_selection_state_changed)
        # ... etc (but this is fragile)

# Option 3: Use destroyed signal (Qt pattern)
class CurveViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # When widget destroyed, disconnect signals
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self):
        self._app_state.selection_state_changed.disconnect()
```

**The Plan's Approach** (Violates Best Practice):
- Relies on `SignalConnectionManager.__del__` (line 38-60)
- `__del__` is NOT guaranteed to run immediately
- May run seconds/minutes after widget destruction
- Objects keep references alive during this time
- Real memory leak in long-running applications

---

### VIOLATION 4: Inadequate Atomic Data Capture

**Severity**: MEDIUM
**Files Affected**: `frame_change_coordinator.py` (lines 186-196), proposed new code

**The Problem**:
Coordinator reads properties DURING handler execution, not AT signal receipt:

**Current Code** (frame_change_coordinator.py:186-196):
```python
def _update_background(self, frame: int) -> None:
    """Update background image for frame (if images loaded)."""
    if self.view_management and self.view_management.image_filenames:
        # ^^^ Property read DURING execution
        # Between signal emit and here, state could change!
        self.view_management.update_background_for_frame(frame)
```

**Race Scenario**:
```
Thread 1: Frame change emitted with frame=42
Thread 2: User loads new image sequence

Coordinator.on_frame_changed(42) receives signal
├─ Read: self.view_management.image_filenames (returns old list)
├─ Thread 2: Set new image files
└─ Use OLD image list for frame 42 (WRONG! off by N frames)
```

**Qt Best Practice**: Capture all needed state AT signal receipt, use snapshot

**Correct Approach**:
```python
def on_frame_changed(self, frame: int) -> None:
    """Atomic state capture at signal receipt."""
    # SNAPSHOT state immediately - don't re-read properties
    snapshot = {
        'frame': frame,
        'image_filenames': self.view_management.image_filenames.copy()
                          if self.view_management and self.view_management.image_filenames
                          else None,
        'centering_enabled': self.curve_widget.centering_mode
                            if self.curve_widget
                            else False,
        'background_pixmap': self.view_management.background_image
                            if self.view_management
                            else None,
    }

    # Now use SNAPSHOT, never re-read properties
    self._update_background(snapshot['frame'], snapshot['image_filenames'])
    self._apply_centering(snapshot['frame'], snapshot['centering_enabled'])
```

**Why This Matters**:
- Ensures consistency between all operations in this frame update
- Prevents state changes between different handler phases
- Makes coordinator truly atomic

---

### VIOLATION 5: Feature Flags Create False Test Safety

**Severity**: MEDIUM
**Files Affected**: `ELIMINATE_COORDINATOR_PLAN.md` (Phases 1-5)

**The Problem**:
Plan (lines 71-74) says:
> Set `USE_DIRECT_FRAME_CONNECTION = True`, run full suite
> Set `USE_DIRECT_FRAME_CONNECTION = False`, run full suite
> Both should pass (proves either path works independently)

**This is Exactly Wrong**:
- Testing paths "independently" doesn't prove they work
- Real app runs with ONE path active
- But BOTH paths execute during testing
- Tests exercise code that won't run in production

**Testing Matrix**:
```
Test Phase       | Flag | Coordinator | Direct Conn | Both Active?
─────────────────┼──────┼─────────────┼─────────────┼─────────────
Phase 1 test     | True | Yes         | Yes         | YES ← Wrong!
Phase 1 test     | False| Yes         | No          | No
Production       | True | No          | Yes         | No  ← Never tested!
```

**What Can Go Wrong**:
1. Phase 1 test with flag=True: Both handlers execute (masks conflicts)
2. Phase 1 test with flag=False: Only coordinator executes (old code tested)
3. Production: Only direct connection executes (never tested in this combo!)
4. Production failure: Direct connection + background loading race condition

**Qt Best Practice**: Complete migration with proper test coverage

**Correct Approach**:
```python
# NO feature flags in production code
# Instead:

# 1. Write new direct connection code
# 2. Write tests for new code ONLY
# 3. Keep old coordinator code in git history
# 4. Delete old code when confident
# 5. Tag production release with "Coordinator removal"

# Never maintain dual signal paths
```

---

### VIOLATION 6: Signal Forwarding Complicates Debugging

**Severity**: MEDIUM
**Files Affected**: `ui/state_manager.py` (lines 69-72)

**Current Anti-Pattern**:
```python
# StateManager forwards ApplicationState signals
_ = self._app_state.frame_changed.connect(self.frame_changed.emit)
```

**Signal Chain**:
```
ApplicationState.frame_changed
    ↓ (forwarded by StateManager)
StateManager.frame_changed
    ↓ (connected by various components)
    ├─ FrameChangeCoordinator.on_frame_changed
    ├─ TimelineController.on_frame_changed
    ├─ CurveViewWidget._on_frame_changed
    └─ ...
```

**Problems**:
1. **Debugging Hell**: Where does frame change originate? Follow 2 signals instead of 1
2. **Unnecessary Indirection**: Components already have ApplicationState reference
3. **Inconsistency**: Some components connect to ApplicationState, others to StateManager
4. **Tight Coupling**: StateManager must know about all downstream connections

**Qt Best Practice**: Direct connections to source

**Correct Approach**:
All components connect directly to ApplicationState:
```python
# ✅ Correct
app_state.frame_changed.connect(self._on_frame_changed)

# ❌ Wrong (current)
state_manager.frame_changed.connect(self._on_frame_changed)
```

**Plan's Approach** (Phase 6):
Correct, but should be Phase 1. Remove forwarding FIRST, then tackle coordinator.

---

### VIOLATION 7: Relying on Python `__del__` for Qt Cleanup

**Severity**: MEDIUM
**Files Affected**: `ui/controllers/signal_connection_manager.py` (lines 38-114)

**The Problem**:
```python
def __del__(self) -> None:
    """Disconnect all signals to prevent memory leaks."""
    # ... attempts to disconnect signals
```

**Why This is Fragile**:

1. **No Execution Guarantee**:
   ```python
   # When does __del__ run?
   obj = SignalConnectionManager()
   # ↑ object created
   del obj
   # ↑ __del__ scheduled... maybe
   # Qt may still have references!
   # __del__ might not run for seconds or minutes
   ```

2. **Already Destroyed Objects**:
   ```python
   def __del__(self) -> None:
       try:
           if self.main_window.state_manager:  # ← main_window already destroyed!
               # This line may crash with segfault
       except (RuntimeError, AttributeError):
           pass  # Silently ignore
   ```

3. **Not Portable**:
   - CPython uses reference counting (relatively predictable)
   - Other Python implementations (PyPy, Jython) have different GC
   - Code works in development, breaks in production

**Qt Best Practice**: Use Qt's proven lifetime management

**Correct Approach**:
```python
# Use Qt's destroyed signal (guaranteed timing)
class SignalConnectionManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        # When THIS object destroyed by Qt, cleanup runs
        self.destroyed.connect(self.cleanup)

    def cleanup(self):
        """Called when destroyed by Qt - guaranteed."""
        # Safe to disconnect signals

# Or use context managers for scoped connections
with signal_manager.temporary_connection(signal, slot):
    # Signal connected here
    do_work()
# Signal auto-disconnected here (context manager exit)
```

---

### VIOLATION 8: Missing Modern Qt6/PySide6 Patterns

**Severity**: LOW (style issue but affects readability)
**Files Affected**: `frame_change_coordinator.py` (lines 109-112), all signal connections

**Current Code**:
```python
_ = self.main_window.state_manager.frame_changed.connect(
    self.on_frame_changed,
    Qt.QueuedConnection,  # Positional argument - ambiguous
)
```

**Modern Qt6/PySide6**:
```python
# Use keyword argument for clarity
_ = self.main_window.state_manager.frame_changed.connect(
    self.on_frame_changed,
    type=Qt.ConnectionType.QueuedConnection  # ← Named parameter, modern style
)
```

**Missing @Slot Decorator**:
```python
# ❌ Current (missing decorator)
def on_frame_changed(self, frame: int) -> None:
    ...

# ✅ Modern Qt6/PySide6 (use @Slot)
from PySide6.QtCore import Slot

@Slot(int)
def on_frame_changed(self, frame: int) -> None:
    ...
```

**Why**: `@Slot` decorator optimizes signal/slot connections in Qt

---

### VIOLATION 9: Race Conditions Not Eliminated

**Severity**: HIGH
**Files Affected**: `ELIMINATE_COORDINATOR_PLAN.md` (lines 312-335)

**The Plan's Claim**:
> "Each component connects directly to ApplicationState"
> "Captures data atomically at signal receipt"
> "No execution order dependencies"
> "Race conditions eliminated"

**Reality**:
Removing the coordinator doesn't eliminate race conditions if multiple components connect with DirectConnection:

**Scenario**:
```
Frame 42 signal emitted

Component A receives (DirectConnection):
├─ Reads background_image
├─ Updates view_offset
└─ Calls repaint()

Component B receives (depends on connection order):
├─ Reads background_image
├─ Reads view_offset
├─ Applies centering
└─ Calls repaint()
```

**Problem**:
- Order of A and B is determined by Qt's internal connection list
- Tests (synchronous) have predictable order
- Real app (async user input) has non-deterministic order
- Rapid frame scrubbing: order changes each time
- Visual desync results

**Why Coordinator Was Helping**:
```
With Coordinator + QueuedConnection:
Frame 42 → Coordinator deferred to next event loop → All phases execute in order

Without Coordinator + DirectConnection:
Frame 42 → Component A fires → Component B fires → Component C fires...
Order undefined!
```

**Real Solution**:
Keep the coordinator to enforce order, just fix the connection TYPE:
```python
# Keep this pattern - it's correct!
class FrameChangeCoordinator:
    def connect(self) -> None:
        # FIX: Remove QueuedConnection (causes deferral)
        # KEEP: Coordinator pattern (ensures order)
        _ = self.main_window.state_manager.frame_changed.connect(
            self.on_frame_changed
            # Use default AutoConnection (becomes DirectConnection in same thread)
            # Synchronous, deterministic, ordered
        )
```

---

### VIOLATION 10: Incomplete Widget Lifecycle Management

**Severity**: MEDIUM
**Files Affected**: `ui/curve_view_widget.py`, `state_sync_controller.py`

**The Problem**:
Multiple components connect to ApplicationState without coordinated cleanup:

1. **CurveViewWidget** (lines 176-180):
   - Uses SignalManager for selection_state_changed
   - But NOT for state_sync connections (line 187)

2. **StateSyncController** (not shown but described):
   - Connects directly: `self._app_state.curves_changed.connect(...)`
   - No cleanup tracking

3. **ViewManagementController**:
   - Connects to images, background, etc.
   - Cleanup not verified

**Cleanup Holes**:
```python
# ❌ Untracked - memory leak risk
self._app_state.curves_changed.connect(self._on_app_state_curves_changed)

# ✅ Tracked via SignalManager
self.signal_manager.connect(signal, slot, "name")
```

**Qt Best Practice**: Consistent cleanup strategy

**Correct Approach**:
```python
class StateSyncController(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self._signal_manager = SignalManager(self)

        # Track ALL connections
        self._signal_manager.connect(
            self._app_state.curves_changed,
            self._on_app_state_curves_changed,
            "curves_changed"
        )
        self._signal_manager.connect(
            self._app_state.active_curve_changed,
            self._on_app_state_active_curve_changed,
            "active_curve_changed"
        )
        # ... etc
```

---

## Specific Recommendations

### RECOMMENDATION 1: Fix the Connection Type, Keep the Coordinator

**Instead of eliminating the coordinator, fix it:**

```python
# ui/controllers/frame_change_coordinator.py
class FrameChangeCoordinator:
    def connect(self) -> None:
        """Connect to frame changes with synchronous execution.

        Uses default AutoConnection which becomes DirectConnection
        in same thread. This ensures:
        - Deterministic execution order (coordinator enforces order)
        - Synchronous handling (no race conditions)
        - Atomic state updates (no interleaving)
        """
        # CHANGE: Remove Qt.QueuedConnection
        # WHY: DirectConnection is correct for same-thread coordination
        _ = self.main_window.state_manager.frame_changed.connect(
            self.on_frame_changed
            # Default AutoConnection → DirectConnection (same thread)
        )
```

**Result**:
- Coordinator still exists (good pattern for coordinating multiple updates)
- Execution is synchronous (no race conditions)
- Order is deterministic (all phases in correct sequence)
- Tests pass and real app works (same behavior)

---

### RECOMMENDATION 2: Remove Signal Forwarding First (Phase 1)

**Don't wait for Phase 6 - do this immediately:**

```python
# ui/state_manager.py - REMOVE
_ = self._app_state.frame_changed.connect(self.frame_changed.emit)  # DELETE

# Update all components to connect directly to ApplicationState
# Old: state_manager.frame_changed.connect(...)
# New: app_state.frame_changed.connect(...)
```

**Benefit**: Simpler debugging, clearer signal flow, fewer indirections

---

### RECOMMENDATION 3: Implement Proper Memory Management

**Use Qt parent-child relationships:**

```python
# ui/curve_view_widget.py
class CurveViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Use SignalManager for ALL connections
        self.signal_manager = SignalManager(self)

        # All connections tracked
        self.signal_manager.connect(
            self._app_state.frame_changed,
            self._on_frame_changed,
            "frame_changed"
        )
        self.signal_manager.connect(
            self._app_state.selection_state_changed,
            self._on_selection_state_changed,
            "selection_state_changed"
        )
        # ... rest of connections

    # __del__ not needed - Qt handles cleanup when destroyed
```

---

### RECOMMENDATION 4: Implement Atomic Data Capture

**Snapshot state at signal receipt:**

```python
# ui/controllers/frame_change_coordinator.py
def on_frame_changed(self, frame: int) -> None:
    """Handle frame change with atomic state snapshot."""
    # Snapshot ALL state at signal receipt
    frame_state = {
        'frame': frame,
        'image_filenames': (
            self.view_management.image_filenames.copy()
            if self.view_management and self.view_management.image_filenames
            else None
        ),
        'centering_mode': (
            self.curve_widget.centering_mode
            if self.curve_widget
            else False
        ),
        'background_image': (
            self.view_management.background_image
            if self.view_management
            else None
        ),
    }

    # Use snapshot, never re-read properties
    self._update_background_atomic(frame_state)
    self._apply_centering_atomic(frame_state)
    self._invalidate_caches()
    self._update_timeline_widgets(frame_state['frame'])
    self._trigger_repaint()

def _update_background_atomic(self, frame_state: dict) -> None:
    """Update background using atomic snapshot."""
    if frame_state.get('image_filenames'):
        self.view_management.update_background_for_frame(frame_state['frame'])

def _apply_centering_atomic(self, frame_state: dict) -> None:
    """Apply centering using atomic snapshot."""
    if frame_state.get('centering_mode') and self.curve_widget:
        self.curve_widget.center_on_frame(frame_state['frame'])
```

---

### RECOMMENDATION 5: Use Modern Qt6/PySide6 Patterns

**Update all signal connections:**

```python
from PySide6.QtCore import Qt, Slot

class FrameChangeCoordinator:
    def connect(self) -> None:
        """Connect using modern Qt6 pattern."""
        _ = self.main_window.state_manager.frame_changed.connect(
            self.on_frame_changed,
            type=Qt.ConnectionType.DirectConnection  # Named parameter, modern style
        )

    @Slot(int)
    def on_frame_changed(self, frame: int) -> None:
        """Handle frame changes with @Slot decorator."""
        logger.debug(f"[FRAME-COORDINATOR] Frame changed to {frame}")
        # ... implementation
```

---

### RECOMMENDATION 6: Add Explicit Test Coverage

**Test what matters:**

```python
# tests/test_frame_change_coordinator.py
class TestFrameChangeCoordinator:
    def test_no_duplicate_updates(self, main_window, qtbot):
        """Verify update() called exactly once per frame change."""
        coordinator = main_window.frame_change_coordinator

        with patch.object(coordinator.curve_widget, 'update') as mock_update:
            get_application_state().set_frame(42)

            # Wait for synchronous execution (no deferred events)
            # Should be called exactly once
            assert mock_update.call_count == 1

    def test_execution_order(self, main_window, qtbot):
        """Verify phases execute in correct order."""
        call_order = []
        coordinator = main_window.frame_change_coordinator

        def track_call(name):
            call_order.append(name)

        with patch.object(coordinator, '_update_background', side_effect=lambda f: track_call('bg')):
            with patch.object(coordinator, '_apply_centering', side_effect=lambda f: track_call('center')):
                with patch.object(coordinator, '_invalidate_caches', side_effect=lambda: track_call('cache')):
                    with patch.object(coordinator, '_trigger_repaint', side_effect=lambda: track_call('paint')):
                        get_application_state().set_frame(42)

        # Verify order
        assert call_order == ['bg', 'center', 'cache', 'paint']

    def test_no_memory_leak_on_widget_destruction(self, main_window, qtbot):
        """Verify signals disconnect when widget destroyed."""
        widget = main_window.curve_widget
        signal_count_before = len(get_application_state().frame_changed.receivers())

        # Destroy widget
        widget.deleteLater()
        qtbot.wait(100)

        signal_count_after = len(get_application_state().frame_changed.receivers())

        # One fewer connection
        assert signal_count_after < signal_count_before
```

---

## Revised Approach (Qt Best Practices Compliant)

### Phase 1: Fix Coordinator Connection Type
- Remove `Qt.QueuedConnection` from coordinator
- Use `AutoConnection` (becomes `DirectConnection` in same thread)
- Keeps coordinator pattern (architecturally sound)
- Makes execution synchronous and deterministic

### Phase 2: Remove Signal Forwarding
- Delete `StateManager.frame_changed.emit` forwarding
- All components connect directly to `ApplicationState`
- Simpler debugging, clearer signal flow

### Phase 3: Implement Atomic Data Capture
- Snapshot state at signal receipt in coordinator
- Use snapshot for all phases
- Prevents state changes during update sequence

### Phase 4: Unify Memory Management
- Use `SignalManager` for ALL signal connections
- Implement consistent cleanup via `destroyed` signal
- No reliance on Python `__del__`

### Phase 5: Migrate to Modern Qt6 Patterns
- Use named parameter: `type=Qt.ConnectionType.DirectConnection`
- Add `@Slot` decorators to signal handlers
- Use context managers for temporary connections

### Phase 6: Comprehensive Testing
- Test execution order (phases happen in sequence)
- Test no duplicates (update called once per frame)
- Test memory management (no leaks after widget destruction)
- Test under rapid frame scrubbing (async user input)

---

## Best Practices Summary

| Practice | Current | Violates | Fix |
|----------|---------|----------|-----|
| Signal Connection Type | QueuedConnection | Defers execution (wrong reason) | Remove connection type, use default |
| Coordinator Pattern | Exists | Blamed as problem | Keep coordinator, fix connection |
| Signal Forwarding | StateManager forwards | Unnecessary indirection | Direct to ApplicationState |
| Memory Management | __del__ + weakref | Python GC unreliable | Qt destroyed signal |
| Feature Flags | Dual signal paths | Not testable properly | Complete migration, no flags |
| Atomic Data Capture | Re-reads properties | State changes mid-update | Snapshot at signal receipt |
| Lifecycle Management | Incomplete tracking | Memory leaks possible | Consistent SignalManager usage |
| Qt6 Patterns | Positional args | Hard to read | Named parameters, @Slot |
| Test Coverage | Call count only | Doesn't verify correctness | Order, duplicates, memory |

---

## Conclusion

**Do NOT proceed with ELIMINATE_COORDINATOR_PLAN.md as written.**

The plan misidentifies the root cause and proposes a solution that would:
1. Introduce race conditions (multiple components, undefined order)
2. Create memory leaks (widget/singleton signal reference cycles)
3. Reduce debuggability (remove coordinator which serializes updates)
4. Violate Qt best practices (ignore connection types, rely on __del__)

**Instead, implement the revised approach:**
1. Fix the connection TYPE (the real issue)
2. Keep the coordinator (good pattern)
3. Remove signal forwarding (cleanup, not core issue)
4. Implement proper memory management (Qt lifetime patterns)
5. Add atomic data capture (prevent state changes during update)

This approach is **Qt compliant**, **architecturally sound**, and **will actually work** in both tests and production.
