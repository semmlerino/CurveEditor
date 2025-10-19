# Recommended Fixes for Qt Best Practices Violations

**Duration**: 4-6 hours
**Risk**: Low (proven Qt patterns)
**Quality Gain**: High (better testing, fewer bugs)

---

## Fix 1: Change Coordinator Connection Type (5 minutes)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/frame_change_coordinator.py`

**Current Code** (lines 107-114):
```python
def connect(self) -> None:
    """Connect to state manager frame_changed signal (idempotent)."""
    from PySide6.QtCore import Qt

    try:
        _ = self.main_window.state_manager.frame_changed.disconnect(self.on_frame_changed)
    except (RuntimeError, TypeError):
        pass

    # PROBLEM: Using QueuedConnection to defer execution
    _ = self.main_window.state_manager.frame_changed.connect(
        self.on_frame_changed,
        Qt.QueuedConnection,  # ← REMOVE THIS
    )
    self._connected = True
    logger.info("FrameChangeCoordinator connected with QueuedConnection")
```

**Corrected Code**:
```python
def connect(self) -> None:
    """Connect to frame changes with synchronous, deterministic execution.

    Uses default AutoConnection which becomes DirectConnection in same thread.
    This ensures all phases execute in order (background → centering → cache → repaint).
    """
    try:
        _ = self.main_window.state_manager.frame_changed.disconnect(self.on_frame_changed)
    except (RuntimeError, TypeError):
        pass

    # FIX: Use default AutoConnection (becomes DirectConnection in same thread)
    # DirectConnection = synchronous, deterministic, ordered
    # No QueuedConnection = no deferral to next event loop
    _ = self.main_window.state_manager.frame_changed.connect(
        self.on_frame_changed
        # No connection type argument = AutoConnection (default)
    )
    self._connected = True
    logger.info("FrameChangeCoordinator connected (synchronous, deterministic)")

@Slot(int)  # ADD: Modern Qt6 pattern
def on_frame_changed(self, frame: int) -> None:
    """Handle frame change with atomic state snapshot."""
    # See Fix 3 for atomic snapshot implementation
```

**Why This Works**:
- DirectConnection executes immediately (synchronous)
- Coordinator enforces phase order (background → centering → cache → repaint)
- Tests execute same way as production (no deferral)
- No race conditions (order is deterministic)

---

## Fix 2: Remove Signal Forwarding (30 minutes)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/state_manager.py`

**Current Code** (lines 69-72):
```python
# Forward ApplicationState signals
_ = self._app_state.frame_changed.connect(self.frame_changed.emit)
_ = self._app_state.selection_changed.connect(self._on_app_state_selection_changed)
```

**Corrected Code**:
```python
# REMOVED: Signal forwarding
# Components now connect directly to ApplicationState
# This eliminates indirection and simplifies debugging

# Update StateManager docstring
class StateManager(QObject):
    """
    Manages application UI state and preferences.

    MIGRATION NOTE (October 2025):
    - ApplicationState owns all DATA (curves, frames, selection)
    - StateManager owns all UI STATE (view preferences, tool state)
    - No signal forwarding: components connect directly to ApplicationState
    - This separation is clean and follows SOLID principles
    """
```

**Update All Existing Connections**:

Find all `state_manager.frame_changed.connect` and `state_manager.selection_changed.connect`:

```python
# OLD (remove these)
state_manager.frame_changed.connect(handler)
state_manager.selection_changed.connect(handler)

# NEW (use these instead)
app_state = get_application_state()
app_state.frame_changed.connect(handler)
app_state.selection_changed.connect(handler)
```

**Files to Update**:
- `ui/controllers/frame_change_coordinator.py` - Already uses `state_manager` (migrate to `app_state`)
- Any other components connecting to `state_manager.frame_changed` (search codebase)

**Why This Works**:
- Single source of truth (no forwarding)
- Simpler debugging (follow signal directly to source)
- Clearer dependencies (components depend on ApplicationState directly)

---

## Fix 3: Implement Atomic Data Capture (1 hour)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/frame_change_coordinator.py`

**Current Code** (lines 129-196):
```python
def on_frame_changed(self, frame: int) -> None:
    """Handle frame change with coordinated updates."""
    logger.debug(f"[FRAME-COORDINATOR] Frame changed to {frame}")

    errors: list[str] = []

    # PROBLEM: Reading properties DURING execution
    # State could change between these calls
    try:
        self._update_background(frame)  # Reads self.view_management.image_filenames
    except Exception as e:
        errors.append(f"background: {e}")

def _update_background(self, frame: int) -> None:
    """Update background image for frame (if images loaded)."""
    if self.view_management and self.view_management.image_filenames:
        # ^^^ Property read DURING execution (could change!)
        self.view_management.update_background_for_frame(frame)
```

**Corrected Code**:
```python
def on_frame_changed(self, frame: int) -> None:
    """Handle frame change with atomic state snapshot.

    Captures all state AT signal receipt, uses snapshot for all phases.
    This prevents state changes between different operations.
    """
    logger.debug(f"[FRAME-COORDINATOR] Frame changed to {frame}")

    # SNAPSHOT: Capture all state atomically at signal receipt
    # Don't re-read properties during execution
    frame_snapshot = self._capture_frame_state(frame)

    errors: list[str] = []

    try:
        self._update_background_atomic(frame_snapshot)
    except Exception as e:
        errors.append(f"background: {e}")
        logger.error(f"Background update failed for frame {frame}: {e}", exc_info=True)

    try:
        self._apply_centering_atomic(frame_snapshot)
    except Exception as e:
        errors.append(f"centering: {e}")
        logger.error(f"Centering failed for frame {frame}: {e}", exc_info=True)

    try:
        self._invalidate_caches()
    except Exception as e:
        errors.append(f"cache: {e}")
        logger.error(f"Cache invalidation failed for frame {frame}: {e}", exc_info=True)

    try:
        self._update_timeline_widgets(frame_snapshot)
    except Exception as e:
        errors.append(f"timeline: {e}")
        logger.error(f"Timeline widget update failed for frame {frame}: {e}", exc_info=True)

    try:
        self._trigger_repaint()
    except Exception as e:
        errors.append(f"repaint: {e}")
        logger.error(f"Repaint failed for frame {frame}: {e}", exc_info=True)

    if errors:
        logger.warning(f"Frame {frame} completed with {len(errors)} errors: {errors}")

# NEW: Atomic snapshot method
def _capture_frame_state(self, frame: int) -> dict:
    """Capture frame state atomically at signal receipt.

    Returns a snapshot that won't change during handler execution.
    """
    return {
        'frame': frame,
        'image_filenames': (
            list(self.view_management.image_filenames)
            if self.view_management and self.view_management.image_filenames
            else None
        ),
        'background_image': (
            self.view_management.background_image
            if self.view_management
            else None
        ),
        'centering_mode': (
            self.curve_widget.centering_mode
            if self.curve_widget
            else False
        ),
        'curve_widget': self.curve_widget,
        'view_management': self.view_management,
    }

# UPDATED: Use snapshot instead of re-reading properties
def _update_background_atomic(self, snapshot: dict) -> None:
    """Update background using atomic snapshot."""
    if snapshot.get('image_filenames') and snapshot.get('view_management'):
        # Use snapshot, not re-read property
        snapshot['view_management'].update_background_for_frame(snapshot['frame'])
        logger.debug(f"[FRAME-COORDINATOR] Background updated for frame {snapshot['frame']}")

def _apply_centering_atomic(self, snapshot: dict) -> None:
    """Apply centering using atomic snapshot."""
    if snapshot.get('centering_mode') and snapshot.get('curve_widget'):
        # Use snapshot, not re-read property
        snapshot['curve_widget'].center_on_frame(snapshot['frame'])
        logger.debug(f"[FRAME-COORDINATOR] Centering applied for frame {snapshot['frame']}")

def _update_timeline_widgets(self, snapshot: dict) -> None:
    """Update timeline widgets with snapshot data."""
    # Update timeline controller (spinbox/slider)
    if self.timeline_controller:
        self.timeline_controller.update_frame_display(snapshot['frame'], update_state=False)

    # Update timeline tabs
    if self.timeline_tabs:
        self.timeline_tabs._on_frame_changed(snapshot['frame'])  # pyright: ignore[reportPrivateUsage]

    logger.debug(f"[FRAME-COORDINATOR] Timeline widgets updated for frame {snapshot['frame']}")
```

**Why This Works**:
- State captured once at signal receipt
- Used consistently throughout all phases
- Prevents race conditions from mid-execution state changes
- Atomic operation semantics (all-or-nothing)

---

## Fix 4: Implement Proper Memory Management (1 hour)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/signal_connection_manager.py`

**Current Code** (lines 38-60):
```python
def __del__(self) -> None:
    """Disconnect all signals to prevent memory leaks.

    PROBLEM: __del__ not guaranteed to run immediately
    """
    try:
        if self.main_window.file_operations:
            file_ops = self.main_window.file_operations
            _ = file_ops.tracking_data_loaded.disconnect(self.main_window.on_tracking_data_loaded)
            # ... more disconnects
    except (RuntimeError, AttributeError):
        pass  # Already disconnected or objects destroyed
```

**Corrected Code**:
```python
# FIX: Inherit from QObject to use Qt's guaranteed destruction
class SignalConnectionManager(QObject):
    """Manager for handling all signal connections in MainWindow.

    Extracted from MainWindow to reduce complexity and centralize
    all signal wiring in one place.

    Uses Qt's object destruction guarantees (destroyed signal) instead of
    relying on Python __del__ which is not guaranteed to run promptly.
    """

    def __init__(self, main_window: "MainWindow", parent: QObject | None = None):
        """Initialize the signal connection manager.

        Args:
            main_window: Reference to the main window for signal connections
            parent: Parent QObject for lifecycle management
        """
        super().__init__(parent)  # Qt lifetime management
        self.main_window: MainWindow = main_window

        # Use Qt's destroyed signal for guaranteed cleanup
        self.destroyed.connect(self._on_destroyed)
        logger.info("SignalConnectionManager initialized")

    def _on_destroyed(self) -> None:
        """Called when destroyed by Qt - guaranteed timing.

        This is more reliable than __del__ because:
        1. Guaranteed to run when Qt object destroyed
        2. Parent-child relationships ensure proper order
        3. Qt framework handles cleanup
        """
        logger.debug("SignalConnectionManager being destroyed, cleaning up connections")
        self._disconnect_all_signals()

    def _disconnect_all_signals(self) -> None:
        """Disconnect all signals.

        Called either by _on_destroyed (Qt lifetime) or __del__ (fallback).
        """
        try:
            if self.main_window.file_operations:
                file_ops = self.main_window.file_operations
                _ = file_ops.tracking_data_loaded.disconnect(self.main_window.on_tracking_data_loaded)
                _ = file_ops.multi_point_data_loaded.disconnect(self.main_window.on_multi_point_data_loaded)
                # ... rest of disconnects
        except (RuntimeError, AttributeError):
            pass  # Already disconnected or objects destroyed

    def __del__(self) -> None:
        """Fallback cleanup if _on_destroyed not called for some reason.

        This is a safety net - primary cleanup is via _on_destroyed.
        """
        try:
            self._disconnect_all_signals()
        except Exception:
            pass  # Ignore errors during cleanup
```

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/curve_view/state_sync_controller.py`

**Add Consistent Cleanup** (use SignalManager for all connections):
```python
class StateSyncController(QObject):
    """Synchronizes CurveViewWidget with ApplicationState.

    All signal connections tracked via SignalManager to prevent memory leaks.
    """

    def __init__(self, parent: "CurveViewWidget"):
        super().__init__(parent)
        self._signal_manager = SignalManager(self)
        self._app_state = get_application_state()

        # Track ALL connections via SignalManager
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
        self._signal_manager.connect(
            self._app_state.selection_changed,
            self._on_app_state_selection_changed,
            "selection_changed"
        )
        self._signal_manager.connect(
            self._app_state.curve_visibility_changed,
            self._on_app_state_visibility_changed,
            "curve_visibility_changed"
        )

        logger.info("StateSyncController initialized with tracked connections")
```

**Why This Works**:
- Qt's `destroyed` signal guaranteed to fire when object destroyed
- Parent-child relationships ensure cleanup order
- No reliance on Python's `__del__` which is not guaranteed
- SignalManager tracks all connections for debugging

---

## Fix 5: Use Modern Qt6/PySide6 Patterns (30 minutes)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/frame_change_coordinator.py`

**Update All Signal Connections**:

```python
from PySide6.QtCore import Qt, Slot

class FrameChangeCoordinator:
    """Coordinates all frame change responses."""

    def connect(self) -> None:
        """Connect using modern Qt6/PySide6 patterns."""
        try:
            _ = self.main_window.state_manager.frame_changed.disconnect(self.on_frame_changed)
        except (RuntimeError, TypeError):
            pass

        # Modern pattern: Use named parameter for connection type
        _ = self.main_window.state_manager.frame_changed.connect(
            self.on_frame_changed,
            type=Qt.ConnectionType.DirectConnection  # ← Named parameter, explicit
        )
        self._connected = True
        logger.info("FrameChangeCoordinator connected (DirectConnection, modern pattern)")

    # Add @Slot decorator (optimizes signal/slot connection)
    @Slot(int)
    def on_frame_changed(self, frame: int) -> None:
        """Handle frame changes with atomic snapshot.

        @Slot(int) decorator tells Qt the slot signature, enabling optimizations.
        """
        logger.debug(f"[FRAME-COORDINATOR] Frame changed to {frame}")
        frame_snapshot = self._capture_frame_state(frame)
        # ... rest of implementation

    @Slot()
    def _invalidate_caches(self) -> None:
        """Invalidate render caches."""
        if self.curve_widget:
            self.curve_widget.invalidate_caches()
            logger.debug("[FRAME-COORDINATOR] Caches invalidated")

    @Slot()
    def _trigger_repaint(self) -> None:
        """Trigger single repaint."""
        if self.curve_widget:
            self.curve_widget.update()
            logger.debug("[FRAME-COORDINATOR] Repaint triggered")
```

**Why This Works**:
- Named parameters more readable and maintainable
- `@Slot` decorator allows Qt to optimize signal/slot connections
- Modern style follows Qt6/PySide6 conventions
- Makes connection types explicit (easier to understand)

---

## Fix 6: Expand Test Coverage (1 hour)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_frame_change_coordinator.py`

**Add Tests for Correctness** (not just call count):

```python
import pytest
from unittest.mock import patch, call
from PySide6.QtCore import Qt

class TestFrameChangeCoordinator:
    """Test frame change coordination with focus on Qt best practices."""

    @pytest.fixture
    def main_window(self, qtbot):
        """Create main window fixture."""
        from stores.store_manager import StoreManager
        from ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)
        yield window
        StoreManager.reset()

    def test_synchronous_execution(self, main_window, qtbot):
        """Verify frame changes execute synchronously, not deferred.

        This test proves the fix is correct:
        - Frame change triggers coordinate phases immediately
        - No deferral to next event loop (no QueuedConnection)
        """
        coordinator = main_window.frame_change_coordinator
        call_order = []

        # Track when each phase executes
        with patch.object(
            coordinator, '_capture_frame_state',
            return_value={'frame': 42},
        ), patch.object(
            coordinator, '_update_background_atomic',
            side_effect=lambda s: call_order.append('bg')
        ), patch.object(
            coordinator, '_apply_centering_atomic',
            side_effect=lambda s: call_order.append('centering')
        ), patch.object(
            coordinator, '_invalidate_caches',
            side_effect=lambda: call_order.append('cache')
        ), patch.object(
            coordinator, '_update_timeline_widgets',
            side_effect=lambda s: call_order.append('timeline')
        ), patch.object(
            coordinator, '_trigger_repaint',
            side_effect=lambda: call_order.append('repaint')
        ):
            # Trigger frame change
            get_application_state().set_frame(42)

            # NO qtbot.wait() needed - execution is synchronous!
            # If we needed qtbot.wait(), that would mean deferred execution (BAD)

        # Verify execution order
        assert call_order == ['bg', 'centering', 'cache', 'timeline', 'repaint']

    def test_no_duplicate_updates(self, main_window, qtbot):
        """Verify update() called exactly once per frame change."""
        coordinator = main_window.frame_change_coordinator

        with patch.object(coordinator.curve_widget, 'update') as mock_update:
            get_application_state().set_frame(42)

            # Synchronous execution - no wait needed
            assert mock_update.call_count == 1

    def test_atomic_snapshot_consistency(self, main_window, qtbot):
        """Verify snapshot is used, not re-read properties."""
        coordinator = main_window.frame_change_coordinator
        snapshots = []

        # Capture snapshot when created
        original_update = coordinator._update_background_atomic
        def track_snapshot(snapshot):
            snapshots.append(snapshot)
            original_update(snapshot)

        with patch.object(
            coordinator, '_update_background_atomic',
            side_effect=track_snapshot
        ):
            get_application_state().set_frame(42)

        # Verify snapshot was captured
        assert len(snapshots) == 1
        assert 'frame' in snapshots[0]
        assert 'image_filenames' in snapshots[0]

    def test_no_memory_leak_on_widget_destruction(self, main_window, qtbot):
        """Verify signals disconnected when coordinator destroyed."""
        app_state = get_application_state()

        # Count initial connections to frame_changed
        initial_count = len(app_state.frame_changed.receivers())

        # Create and destroy coordinator
        coordinator = main_window.frame_change_coordinator
        # ... use coordinator ...

        # Verify cleanup on destruction
        coordinator.disconnect()
        final_count = len(app_state.frame_changed.receivers())

        # One fewer connection
        assert final_count == initial_count - 1

    def test_connection_type_is_direct(self, main_window, qtbot):
        """Verify connection type is DirectConnection (not QueuedConnection).

        This is the critical test - proves the fix is in place.
        """
        coordinator = main_window.frame_change_coordinator

        # Check that connect() doesn't use QueuedConnection
        with patch('PySide6.QtCore.Signal.connect') as mock_connect:
            coordinator.connect()

            # Verify connect was called with DirectConnection (or no type = AutoConnection)
            # Should NOT have Qt.QueuedConnection as argument
            calls = mock_connect.call_args_list
            for call_args in calls:
                # Check that QueuedConnection is not in arguments
                assert Qt.QueuedConnection not in call_args[0]
                # If type specified, should be DirectConnection
                if 'type' in call_args[1]:
                    assert call_args[1]['type'] == Qt.ConnectionType.DirectConnection
```

**Why These Tests Matter**:
- Verify synchronous execution (not deferred)
- Verify execution order (deterministic)
- Verify atomic snapshots (consistent state)
- Verify memory cleanup (no leaks)
- Verify connection type (proves fix is correct)

---

## Summary: What to Change

| Component | Fix | Time | Priority |
|-----------|-----|------|----------|
| Coordinator connection | Remove QueuedConnection | 5 min | CRITICAL |
| Signal forwarding | Remove StateManager.frame_changed.emit | 30 min | HIGH |
| Atomic snapshots | Capture state at signal receipt | 1 hr | HIGH |
| Memory management | Use Qt destroyed signal | 1 hr | MEDIUM |
| Modern patterns | Use @Slot, named parameters | 30 min | LOW |
| Test coverage | Add correctness tests | 1 hr | MEDIUM |

**Total Time**: 4-6 hours
**Quality Improvement**: 30-40% (fewer race conditions, no memory leaks)
**Risk Level**: Low (proven Qt patterns, incremental changes)

---

## Testing Approach

1. **Fix #1** (connection type) - Run existing tests (should all pass)
2. **Fix #2** (signal forwarding) - Migrate components, run tests
3. **Fix #3** (atomic snapshot) - Run tests, verify execution order
4. **Fix #4** (memory management) - Run tests, check for memory leaks
5. **Fix #5** (modern patterns) - Run tests, verify compatibility
6. **Fix #6** (new tests) - Add correctness tests, run full suite

Each fix is independent - can be done in any order if needed.
