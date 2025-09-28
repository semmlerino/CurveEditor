# KISS/SOLID Architecture Refactoring Plan - DO NOT DELETE

## Executive Summary
This plan addresses critical architectural violations discovered during the investigation of the frame synchronization bug. The current architecture violates Single Source of Truth, has tight coupling, and unclear data flow patterns.

## 1. Problem Statement

### 1.1 Current Issues
1. **Multiple Sources of Truth for Frame State**
   - `StateManager.current_frame`
   - `TimelineController.playback_state.current_frame`
   - `CurveViewWidget._current_frame` (added as workaround)
   - Each can become desynchronized

2. **Tight Coupling Chain**
   ```
   Renderer → CurveViewWidget → MainWindow → StateManager
   ```
   - Renderer reaches through 3 layers to get current frame
   - Changes to any layer breaks the chain

3. **Unclear Data Flow**
   - Frame changes propagate through multiple manual calls
   - Each component must remember to update the next
   - No clear ownership of state

4. **Single Responsibility Violations**
   - CurveViewWidget: Renders AND tracks application state
   - TimelineController: Controls timeline AND maintains duplicate state
   - Renderer: Renders AND knows about application structure

### 1.2 Root Cause
The architecture grew organically without clear state management strategy, leading to each component maintaining its own state cache "for convenience".

## 2. Proposed Architecture

### 2.1 Core Principles
1. **Single Source of Truth**: StateManager owns ALL application state
2. **Observer Pattern**: Components subscribe to state changes
3. **Dependency Injection**: Pass state as parameters, not through parent chains
4. **Pure Functions**: Renderers receive state, don't fetch it

### 2.2 New Data Flow
```
User Action → Controller → StateManager → Signal → All Observers
                              ↓
                        (Single Source)
                              ↓
                    ┌─────────┴────────┬──────────┐
                    ↓                  ↓          ↓
              CurveWidget      TimelineUI   Renderer
              (Observer)       (Observer)   (Receives)
```

## 3. Detailed Implementation Plan

### Phase 1: Enhance StateManager (Week 1)

#### 3.1.1 Make StateManager Observable
**File**: `services/state_manager.py`

**Current Code**:
```python
class StateManager:
    def __init__(self):
        self.current_frame: int = 1
        self.session_id: str = ""
        # ... other state
```

**New Code**:
```python
from PySide6.QtCore import QObject, Signal

class StateManager(QObject):
    # Signals for state changes
    frame_changed = Signal(int)
    selection_changed = Signal(set)
    playback_state_changed = Signal(object)

    def __init__(self):
        super().__init__()
        self._current_frame: int = 1
        self._selected_indices: set[int] = set()
        self._playback_mode: PlaybackMode = PlaybackMode.STOPPED

    @property
    def current_frame(self) -> int:
        return self._current_frame

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        if self._current_frame != value:
            self._current_frame = value
            self.frame_changed.emit(value)

    @property
    def selected_indices(self) -> set[int]:
        return self._selected_indices.copy()

    @selected_indices.setter
    def selected_indices(self, value: set[int]) -> None:
        if self._selected_indices != value:
            self._selected_indices = value.copy()
            self.selection_changed.emit(self._selected_indices)
```

#### 3.1.2 Add State Transaction Support
```python
@contextmanager
def batch_update(self):
    """Batch multiple state changes into single signal emission."""
    self._batch_mode = True
    self._pending_signals = []
    try:
        yield
    finally:
        self._batch_mode = False
        # Emit all pending signals
        for signal, value in self._pending_signals:
            signal.emit(value)
        self._pending_signals.clear()
```

### Phase 2: Refactor CurveViewWidget (Week 1)

#### 3.2.1 Remove Redundant State
**File**: `ui/curve_view_widget.py`

**Remove**:
```python
# DELETE THESE LINES
self._current_frame: int = 1

def on_frame_changed(self, frame: int) -> None:
    self._current_frame = frame
    self.invalidate_caches()
    self.update()

@property
def current_frame(self) -> int:
    return self._current_frame
```

**Add**:
```python
def __init__(self, parent: QWidget | None = None):
    # ... existing init code ...

    # Connect to state manager
    self._state_manager = get_state_manager()
    self._state_manager.frame_changed.connect(self._on_frame_changed)
    self._state_manager.selection_changed.connect(self._on_selection_changed)

def _on_frame_changed(self, frame: int) -> None:
    """React to frame changes from state manager."""
    self.invalidate_caches()
    self.update()  # Trigger repaint with new frame

    if self.centering_mode:
        self.center_on_frame(frame)

def _on_selection_changed(self, indices: set[int]) -> None:
    """React to selection changes from state manager."""
    # Update view, no need to store locally
    self.update()

@property
def current_frame(self) -> int:
    """Get current frame from state manager."""
    return self._state_manager.current_frame

@property
def selected_indices(self) -> set[int]:
    """Get selection from state manager."""
    return self._state_manager.selected_indices
```

### Phase 3: Decouple Renderer (Week 2)

#### 3.3.1 Pass State as Parameters
**File**: `rendering/optimized_curve_renderer.py`

**Remove from CurveViewProtocol**:
```python
# DELETE THESE LINES
current_frame: int
main_window: "MainWindowProtocol | None"
```

**Change render methods**:
```python
def render(
    self,
    painter: QPainter,
    event: object | None,
    curve_view: CurveViewProtocol,
    render_state: RenderState  # NEW PARAMETER
) -> None:
    """Render with explicitly passed state."""
    # Use render_state.current_frame instead of curve_view.current_frame
    # Use render_state.selected_indices instead of curve_view.selected_points

@dataclass
class RenderState:
    """State needed for rendering, passed explicitly."""
    current_frame: int
    selected_indices: set[int]
    playback_mode: PlaybackMode
    # Add other render-relevant state
```

**Update widget paint event**:
```python
def paintEvent(self, event: QPaintEvent) -> None:
    # Build render state from state manager
    render_state = RenderState(
        current_frame=self._state_manager.current_frame,
        selected_indices=self._state_manager.selected_indices,
        playback_mode=self._state_manager.playback_mode
    )

    # Pass to renderer
    self.renderer.render(painter, event, self, render_state)
```

### Phase 4: Simplify TimelineController (Week 2)

#### 3.4.1 Remove Duplicate State
**File**: `ui/controllers/timeline_controller.py`

**Remove**:
```python
# DELETE THESE
self.playback_state.current_frame = frame
```

**Change to**:
```python
def _on_frame_changed(self, value: int) -> None:
    """Handle frame spinbox value change."""
    # Only update state manager, let signals handle the rest
    self.state_manager.current_frame = value

def _on_playback_timer(self) -> None:
    """Handle playback tick."""
    current = self.state_manager.current_frame
    # Calculate next frame...
    self.state_manager.current_frame = next_frame
```

### Phase 5: Update Signal Connections (Week 3)

#### 3.5.1 MainWindow Signal Management
**File**: `ui/main_window.py`

**Remove cascade calls**:
```python
# DELETE THIS PATTERN
def _update_frame_display(self, frame: int, update_state_manager: bool = True) -> None:
    if update_state_manager:
        self.state_manager.current_frame = frame
    self.timeline_controller.update_for_current_frame(frame)
    self.view_management_controller.update_background_for_frame(frame)
    if self.curve_widget:
        self.curve_widget.on_frame_changed(frame)
```

**Replace with**:
```python
def _update_frame_display(self, frame: int) -> None:
    """Simply update state manager, signals handle the rest."""
    self.state_manager.current_frame = frame
    # That's it! Observers will react
```

## 4. Success Metrics

### 4.1 Quantitative Metrics
1. **Code Reduction**: Remove at least 200 lines of state synchronization code
2. **Coupling Score**: Reduce average component coupling from 5 to 2
3. **Test Coverage**: Achieve 95% coverage on state management
4. **Performance**: No degradation in 25K point rendering benchmark

### 4.2 Qualitative Metrics
1. **Single Source**: `git grep "current_frame ="` shows only StateManager
2. **No Parent Access**: Renderer has no `main_window` or `parent` access
3. **Clear Data Flow**: State changes traceable through signals
4. **Testability**: State changes testable in isolation

## 5. Verification Steps

### 5.1 Unit Tests
```python
def test_single_source_of_truth():
    """Verify only StateManager can set current_frame."""
    state_manager = StateManager()
    widget = CurveViewWidget()
    controller = TimelineController(state_manager)

    # Change frame through state manager
    state_manager.current_frame = 10

    # All components should reflect this
    assert widget.current_frame == 10
    assert controller.get_current_frame() == 10
    # No component should have its own _current_frame

def test_observer_pattern():
    """Verify components react to state changes."""
    state_manager = StateManager()
    widget = CurveViewWidget()

    update_called = False
    def on_update():
        nonlocal update_called
        update_called = True
    widget.update = on_update

    state_manager.current_frame = 5
    assert update_called

def test_renderer_independence():
    """Verify renderer doesn't access parent objects."""
    renderer = OptimizedCurveRenderer()
    # Should not have main_window access
    assert not hasattr(renderer, 'main_window')
    # render() should require state parameter
    assert 'render_state' in renderer.render.__code__.co_varnames
```

### 5.2 Integration Tests
1. **Frame Sync Test**: Original bug test should still pass
2. **Multi-Selection Test**: Selections remain synchronized
3. **Playback Test**: Animation updates all views correctly
4. **Performance Test**: 25K point benchmark maintains <20ms render

### 5.3 Manual Testing Checklist
- [ ] Select point, navigate timeline - frame indicator updates
- [ ] Play animation - all views update smoothly
- [ ] Multi-select points - selection appears everywhere
- [ ] Undo/redo - state changes propagate correctly
- [ ] Load new file - state resets cleanly

## 6. Risk Assessment & Mitigation

### 6.1 Risks
1. **Signal Storm**: Too many signals during batch operations
   - **Mitigation**: Implement batch_update context manager

2. **Circular Dependencies**: Signal handlers triggering more signals
   - **Mitigation**: Use signal blocking during programmatic updates

3. **Performance Regression**: Signal overhead affects rendering
   - **Mitigation**: Benchmark before/after, optimize hot paths

4. **Breaking Existing Features**: Refactor breaks working code
   - **Mitigation**: Comprehensive test suite before refactoring

### 6.2 Rollback Plan
1. Git branch `feature/kissolid-refactor` for all changes
2. Keep old synchronization code commented for 2 releases
3. Feature flag to toggle between old/new architecture
4. Gradual rollout: StateManager first, then components

## 7. Implementation Schedule

### Week 1: Foundation
- [ ] Create observable StateManager
- [ ] Write state manager tests
- [ ] Update CurveViewWidget to use signals
- [ ] Verify frame sync bug remains fixed

### Week 2: Decoupling
- [ ] Refactor renderer to accept RenderState
- [ ] Simplify TimelineController
- [ ] Remove redundant state variables
- [ ] Update all signal connections

### Week 3: Testing & Polish
- [ ] Run full test suite
- [ ] Performance benchmarking
- [ ] Fix any regressions
- [ ] Update documentation

### Week 4: Review & Deploy
- [ ] Code review
- [ ] Final testing
- [ ] Merge to main
- [ ] Monitor for issues

## 8. Long-term Benefits

1. **Maintainability**: New developers understand state flow immediately
2. **Extensibility**: Adding new state is trivial
3. **Reliability**: Single source prevents desync bugs
4. **Testability**: State changes are observable and predictable
5. **Performance**: Optimized update paths, no redundant updates

## 9. Code Examples

### Before (Complex, Coupled):
```python
# Frame change requires manual propagation
self.state_manager.current_frame = 10
self.timeline_controller.update_frame_display(10)
self.curve_widget.on_frame_changed(10)
self.curve_widget.invalidate_caches()
self.curve_widget.update()
```

### After (Simple, Decoupled):
```python
# Frame change automatically propagates
self.state_manager.current_frame = 10
# Done! All observers update themselves
```

## 10. Definition of Done

- [ ] All state stored in single StateManager instance
- [ ] No component caches application state locally
- [ ] Renderer receives state as parameters
- [ ] All tests pass with new architecture
- [ ] Performance benchmarks meet or exceed current
- [ ] Documentation updated with new patterns
- [ ] Code review approved by team lead

## Notes
- This refactoring is critical for long-term maintainability
- Fixes entire class of synchronization bugs
- Enables future features like collaborative editing
- Makes the codebase more professional and maintainable

---
*Created: January 2025*
*Status: PENDING IMPLEMENTATION*
*Priority: HIGH*
*Estimated Effort: 4 weeks*
