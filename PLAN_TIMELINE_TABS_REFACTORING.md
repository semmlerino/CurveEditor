# Timeline_tabs Refactoring Plan - Fix KISS/SOLID Violations

## Executive Summary
Timeline_tabs currently violates the Single Source of Truth principle by maintaining its own `current_frame` state independent of StateManager. This causes desynchronization bugs where different components have different ideas of the current frame.

## 1. Problem Statement

### 1.1 Concrete Bug Example
**Test Failure Analysis**:
```
Setting: state_manager.current_frame = 10
Timeline_tabs state: current_frame = 1 (not updated)
User action: Press Right arrow key
Expected: Move to frame 11
Actual: Jump to frame 2 (timeline_tabs increments from 1 to 2)
```

### 1.2 Current Architecture Violations
1. **Multiple Sources of Truth**:
   - StateManager.current_frame (intended single source)
   - timeline_tabs.current_frame (duplicate state)
   - TimelineController.frame_spinbox.value() (UI state)

2. **Broken Observer Pattern**:
   - timeline_tabs emits frame_changed signal
   - timeline_tabs does NOT listen to StateManager.frame_changed
   - One-way communication creates desynchronization

3. **Improper State Management**:
   - timeline_tabs updates its own state directly in event handlers
   - Should delegate to StateManager and react to changes

## 2. Detailed Implementation Plan

### Phase 1: Add StateManager Observer Connection

**File**: `ui/timeline_tabs.py`

**Add StateManager connection in __init__**:
```python
def __init__(self, parent=None):
    super().__init__(parent)
    # ... existing init code ...

    # NEW: Store StateManager reference
    self._state_manager = None

    # NEW: Property-based current_frame (remove self.current_frame = 1)
    # self.current_frame = 1  # DELETE THIS LINE

def set_state_manager(self, state_manager):
    """Connect to StateManager for frame synchronization."""
    self._state_manager = state_manager
    # Connect to frame changes
    state_manager.frame_changed.connect(self._on_state_frame_changed)

@property
def current_frame(self):
    """Get current frame from StateManager (single source of truth)."""
    if self._state_manager:
        return self._state_manager.current_frame
    return 1  # Fallback for initialization

@current_frame.setter
def current_frame(self, value):
    """Redirect frame changes through StateManager."""
    if self._state_manager:
        self._state_manager.current_frame = value
    # Note: Visual update happens via signal callback

def _on_state_frame_changed(self, frame):
    """React to StateManager frame changes."""
    # Update visual state only
    if self.current_frame in self.frame_tabs:
        self.frame_tabs[self.current_frame].set_current_frame(False)
    if frame in self.frame_tabs:
        self.frame_tabs[frame].set_current_frame(True)
    self._update_frame_info()
    # Do NOT emit frame_changed here (would create loop)
```

### Phase 2: Update Event Handlers

**File**: `ui/timeline_tabs.py`

**Update keyboard event handler**:
```python
def keyPressEvent(self, event):
    """Handle keyboard navigation."""
    if event.key() == Qt.Key.Key_Left:
        # OLD: self.set_current_frame(self.current_frame - 1)
        # NEW: Delegate to StateManager
        if self._state_manager:
            self._state_manager.current_frame = max(
                self.min_frame,
                self._state_manager.current_frame - 1
            )
        event.accept()
    elif event.key() == Qt.Key.Key_Right:
        # OLD: self.set_current_frame(self.current_frame + 1)
        # NEW: Delegate to StateManager
        if self._state_manager:
            self._state_manager.current_frame = min(
                self.max_frame,
                self._state_manager.current_frame + 1
            )
        event.accept()
    # ... similar for Home/End keys ...
```

**Update mouse event handlers**:
```python
def mousePressEvent(self, event):
    """Start scrubbing when mouse is pressed."""
    if event.button() == Qt.MouseButton.LeftButton:
        frame = self._get_frame_from_position(event.pos().x())
        if frame is not None and self._state_manager:
            self.is_scrubbing = True
            self.scrub_start_frame = frame
            # Delegate to StateManager
            self._state_manager.current_frame = frame
            event.accept()
            return
    super().mousePressEvent(event)
```

### Phase 3: Update Signal Flow

**File**: `ui/controllers/signal_connection_manager.py`

**Remove redundant signal connection**:
```python
def _connect_timeline_signals(self):
    if self.main_window.timeline_tabs:
        # DELETE THIS LINE (creates circular flow):
        # self.main_window.timeline_tabs.frame_changed.connect(
        #     self.main_window.timeline_controller.set_frame
        # )

        # NEW: Connect timeline_tabs to StateManager
        self.main_window.timeline_tabs.set_state_manager(
            self.main_window.state_manager
        )
```

### Phase 4: Remove Band-aid Fixes

**File**: `ui/controllers/timeline_controller.py`

**Remove manual sync in _update_frame**:
```python
def _update_frame(self, frame):
    """Update the current frame and notify listeners."""
    # Update state manager (single source of truth)
    self.state_manager.current_frame = frame
    logger.debug(f"[FRAME] Current frame set to: {frame}")

    # DELETE THIS BAND-AID:
    # if hasattr(self.main_window, "timeline_tabs") and self.main_window.timeline_tabs:
    #     self.main_window.timeline_tabs.set_current_frame(frame)

    # Emit signal for other components
    self.frame_changed.emit(frame)
```

**File**: `tests/test_navigation_integration.py`

**Remove test workaround**:
```python
def test_rapid_navigation_stability(self, fully_configured_window, qtbot):
    window = fully_configured_window
    initial_frame = 10
    window.state_manager.current_frame = initial_frame

    # DELETE THIS WORKAROUND:
    # if window.timeline_tabs:
    #     window.timeline_tabs.set_current_frame(initial_frame)

    # Test should now work without manual sync
    for _ in range(5):
        qtbot.keyClick(window.timeline_tabs or window, Qt.Key.Key_Right)
```

### Phase 5: Deprecate timeline_tabs.frame_changed Signal

**File**: `ui/timeline_tabs.py`

**Mark signal as deprecated**:
```python
class TimelineTabWidget(QWidget):
    # DEPRECATED: Use StateManager.frame_changed instead
    # Keep for backward compatibility but don't emit
    frame_changed = Signal(int)  # Add deprecation comment

    def set_current_frame(self, frame):
        """Legacy method - redirects to StateManager."""
        # For backward compatibility
        if self._state_manager:
            self._state_manager.current_frame = frame
        else:
            # Fallback for tests/legacy code
            logger.warning("set_current_frame called without StateManager")
```

## 3. Success Metrics

### 3.1 Quantitative Metrics
- **Zero duplicate state**: `grep -r "self.current_frame =" ui/timeline_tabs.py` returns 0 results
- **All tests pass**: 1055/1055 tests passing without manual sync
- **No circular dependencies**: Signal flow is unidirectional

### 3.2 Qualitative Metrics
- **Single Source of Truth**: Only StateManager can change current_frame
- **Clear Data Flow**: User input → StateManager → All observers
- **No Manual Sync**: No need for band-aid synchronization code

## 4. Verification Steps

### 4.1 Unit Test
```python
def test_timeline_tabs_observes_state_manager():
    """Verify timeline_tabs updates when StateManager changes."""
    state_manager = StateManager()
    timeline_tabs = TimelineTabWidget()
    timeline_tabs.set_state_manager(state_manager)

    # Change state manager
    state_manager.current_frame = 10

    # Timeline tabs should reflect change
    assert timeline_tabs.current_frame == 10

    # Keyboard event should update state manager
    event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right)
    timeline_tabs.keyPressEvent(event)

    assert state_manager.current_frame == 11
    assert timeline_tabs.current_frame == 11
```

### 4.2 Integration Test
```python
def test_no_desynchronization():
    """Verify no desync between components."""
    window = MainWindow()

    # Set frame via different paths
    window.state_manager.current_frame = 15
    assert window.timeline_tabs.current_frame == 15
    assert window.timeline_controller.frame_spinbox.value() == 15

    # Navigate via timeline_tabs
    qtbot.keyClick(window.timeline_tabs, Qt.Key.Key_Left)
    assert window.state_manager.current_frame == 14
    assert window.timeline_tabs.current_frame == 14
```

## 5. Rollback Plan

If issues arise:
1. **Phase 1 Rollback**: Remove StateManager connection, restore self.current_frame
2. **Phase 2 Rollback**: Restore direct state updates in event handlers
3. **Phase 3 Rollback**: Restore timeline_tabs.frame_changed signal connection
4. **Emergency**: Revert to commit before refactoring began

## 6. Timeline

- **Day 1**: Implement Phase 1 (StateManager connection)
- **Day 2**: Implement Phase 2 (Event handler updates)
- **Day 3**: Implement Phase 3-4 (Signal flow cleanup)
- **Day 4**: Implement Phase 5 (Deprecation)
- **Day 5**: Testing and verification

## 7. Risk Assessment

### Risks:
1. **Backward Compatibility**: Some code may directly access timeline_tabs.current_frame
   - Mitigation: Use property to maintain compatibility
2. **Performance**: Additional signal overhead
   - Mitigation: Signals are already used extensively, minimal impact
3. **Test Failures**: Tests may assume old behavior
   - Mitigation: Update tests as part of refactoring

### Benefits:
1. **Bug Prevention**: Impossible for components to desynchronize
2. **Simplified Testing**: Only need to test StateManager
3. **Cleaner Architecture**: Clear separation of concerns
4. **Future-proof**: Easy to add new frame observers

---
*Comprehensive plan for implementing timeline_tabs Single Source of Truth architecture*
