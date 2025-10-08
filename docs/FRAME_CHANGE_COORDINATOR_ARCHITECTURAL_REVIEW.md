# FrameChangeCoordinator - Architectural Review

**Reviewer**: Python Expert Architect
**Date**: 2025-10-07
**Review Focus**: High-level design, architectural patterns, SOLID principles, maintainability

---

## Executive Summary

**Overall Assessment**: ✅ **APPROVE WITH RECOMMENDATIONS**

The FrameChangeCoordinator refactor is **architecturally sound** and solves a real production bug caused by Qt's non-deterministic signal ordering. The coordinator pattern is appropriate for this codebase and follows existing controller patterns well. However, several design decisions could be improved for better long-term maintainability.

**Key Strengths**:
- Solves genuine race condition through explicit ordering
- Matches existing controller patterns (consistency)
- Highly testable design with clear boundaries
- Follows Qt best practices (single update() call)
- Single Responsibility Principle well-applied

**Key Concerns**:
1. ⚠️ **Wrong placement** - Should be created in MainWindow, not SignalConnectionManager
2. ⚠️ **Implicit dependencies** - Handler ordering rationale should be more explicit
3. ⚠️ **Private method access** - Consider public wrappers for better encapsulation
4. ℹ️ **Limited extensibility** - Hard-coded sequence, but acceptable for stable domain

---

## 1. Architectural Pattern Evaluation

### Does the Coordinator Pattern Fit This Codebase?

✅ **YES - Strong fit with existing patterns**

**Evidence from codebase**:

1. **SignalConnectionManager precedent** (201 lines)
   - Already centralizes signal wiring
   - Coordinator follows same "centralization for control" philosophy

2. **StateSyncController precedent** (149 lines)
   - Similar role: coordinates ApplicationState signals → CurveViewWidget updates
   - Pattern: Orchestration without implementation
   - Constructor: Takes dependencies explicitly

3. **4-service architecture compatibility**
   - Coordinator delegates to services (doesn't duplicate logic)
   - Acts as orchestrator, not implementer
   - Maintains separation of concerns

4. **Existing controllers in ui/controllers/**:
   - ViewManagementController (404 lines) - Delegates to services/widgets
   - TimelineController - Mix of state management and coordination
   - PointEditorController - Editing logic coordination
   - All follow "orchestration not implementation" principle

**Pattern Classification**: **Mediator Pattern** (GoF)
- Reduces coupling between components by centralizing interactions
- Components don't need to know about each other
- Mediator knows about all components and coordinates them

**Horizontal vs Vertical Coordination**:
- **StateSyncController**: Vertical (ApplicationState → Widget synchronization)
- **FrameChangeCoordinator**: Horizontal (orchestrating multiple components for one event)

Both are valid applications of the controller pattern in this architecture.

---

## 2. Separation of Concerns

### Is the Coordinator Doing Too Much or Too Little?

✅ **APPROPRIATE scope - Pure orchestration**

**What the coordinator does**:
1. Load background image → Delegates to `ViewManagementController`
2. Apply centering → Delegates to `CurveViewWidget`
3. Invalidate caches → Delegates to `CurveViewWidget`
4. Update timeline widgets → Delegates to `TimelineController`, `TimelineTabs`
5. Trigger repaint → Delegates to `CurveViewWidget`

**What the coordinator does NOT do**:
- ❌ Implement any business logic
- ❌ Manipulate data structures
- ❌ Make decisions about WHAT to do (only WHEN)
- ❌ Own any state (except component references)

**Comparison to Anti-Pattern (God Object)**:

| God Object | FrameChangeCoordinator |
|------------|------------------------|
| Implements everything itself | Delegates everything |
| Knows HOW to do operations | Only knows WHEN to call operations |
| Owns business logic | Orchestrates existing logic |
| Difficult to test | Easy to test (mockable) |

**Verdict**: This is **Mediator pattern applied correctly**, not a god object.

---

## 3. Dependency Management

### Are Dependencies Cleanly Injected or Tightly Coupled?

⚠️ **TIGHTLY COUPLED but matches existing pattern**

**Current design**:
```python
def __init__(self, main_window: MainWindow):
    self.main_window = main_window
    self.curve_widget = main_window.curve_widget
    self.view_management = main_window.view_management_controller
    self.timeline_controller = main_window.timeline_controller
    self.timeline_tabs = main_window.timeline_tabs
```

**Issues**:
1. Tightly coupled to MainWindow's internal structure
2. Extracting dependencies from main_window is fragile
3. If MainWindow reorganizes, coordinator breaks

**Existing precedent**: ViewManagementController does the same thing (line 41):
```python
def __init__(self, main_window: MainWindow):
    self.main_window: MainWindow = main_window
    # Uses main_window.curve_widget, main_window.state_manager, etc.
```

**Better alternatives**:

1. **Constructor injection** (explicit dependencies):
```python
def __init__(
    self,
    state_manager: StateManager,
    curve_widget: CurveViewWidget,
    view_management: ViewManagementController,
    timeline_controller: TimelineController,
    timeline_tabs: TimelineTabs,
):
```

2. **Facade pattern** (grouped dependencies):
```python
@dataclass
class FrameChangeComponents:
    state_manager: StateManager
    curve_widget: CurveViewWidget
    view_management: ViewManagementController
    timeline_controller: TimelineController
    timeline_tabs: TimelineTabs

def __init__(self, components: FrameChangeComponents):
    self.components = components
```

**Recommendation**:
- ✅ **Accept current design for consistency with existing controllers**
- 📝 Document the tight coupling explicitly
- 🔮 Consider facade pattern if 3+ more coordinators emerge

**Pragmatism vs Purity**: Current design is pragmatic:
- MainWindow is already the dependency root
- Null checks handle missing components gracefully
- Consistency with existing patterns > theoretical purity

---

## 4. Extensibility

### Can This Handle Future Frame-Change Handlers?

⚠️ **LIMITED EXTENSIBILITY - Hard-coded sequence**

**Current design**: Inflexible
```python
def on_frame_changed(self, frame: int) -> None:
    self._update_background(frame)      # 1
    self._apply_centering(frame)        # 2
    self._invalidate_caches()           # 3
    self._update_timeline_widgets(frame) # 4
    self._trigger_repaint()             # 5
```

**Violates Open/Closed Principle**: Adding new handler requires modifying coordinator code.

**Alternative approaches**:

1. **Strategy pattern with registration**:
```python
class FrameChangeCoordinator:
    def __init__(self, main_window):
        self.handlers: list[tuple[int, FrameChangeHandler]] = []

    def register_handler(self, handler: FrameChangeHandler, phase: int, priority: int):
        self.handlers.append((phase * 100 + priority, handler))
        self.handlers.sort()
```

2. **Chain of Responsibility**:
```python
handlers = [
    BackgroundHandler(),
    CenteringHandler(),
    CacheHandler(),
    WidgetHandler(),
    RepaintHandler()
]
for handler in handlers:
    handler.handle(frame)
```

3. **Event pipeline**:
```python
pipeline = FrameChangePipeline()
pipeline.add_stage("pre_render", background_handler)
pipeline.add_stage("pre_render", centering_handler)
pipeline.add_stage("render", repaint_handler)
pipeline.execute(frame)
```

**HOWEVER**: Is extensibility actually needed?

**Analysis - YAGNI Principle**:
- Frame change response is a **FINITE, STABLE** set of behaviors
- Not a plugin system
- Dependencies are semantic (background MUST load before centering)
- No evidence of need for runtime handler registration

**Critical dependencies** (semantically constrained):
1. Background MUST load before centering (centering uses viewport dimensions)
2. All state updates MUST complete before repaint
3. Cache invalidation MUST happen before repaint

These aren't configuration preferences - they're **problem domain constraints**.

**Recommendation**:
- ✅ **Accept hard-coded sequence** for initial implementation (YAGNI)
- 📝 Document WHY ordering matters (make dependencies explicit)
- 🔮 Refactor to pipeline pattern if 3+ new handlers are added

**When to refactor to extensible design**:
- Multiple valid orderings emerge
- Different contexts need different orders
- Third-party plugins need to insert handlers
- More than 8-10 handlers total

---

## 5. Testability

### Is the Coordinator Design Testable? Can Handlers Be Mocked?

✅ **EXCELLENT testability**

**Why it's testable**:

1. **Single entry point**: `on_frame_changed(frame)` - clear contract
2. **Mockable dependencies**: All delegates can be mocked/stubbed
3. **Observable behavior**: Can verify call order and arguments
4. **No hidden state**: Stateless coordination logic
5. **Null-safe**: Can test with missing components

**Test approach example**:
```python
def test_update_order_is_deterministic(qtbot, mocker):
    """Test updates happen in correct order."""
    main_window = create_test_main_window(qtbot)
    coordinator = FrameChangeCoordinator(main_window)

    # Mock all delegates
    mock_bg = mocker.patch.object(
        coordinator.view_management, 'update_background_for_frame'
    )
    mock_center = mocker.patch.object(
        coordinator.curve_widget, 'center_on_frame'
    )
    mock_cache = mocker.patch.object(
        coordinator.curve_widget, 'invalidate_caches'
    )
    mock_update = mocker.patch.object(
        coordinator.curve_widget, 'update'
    )

    # Execute
    coordinator.on_frame_changed(42)

    # Verify order using mock_calls
    assert mock_bg.call_count == 1
    assert mock_center.call_count == 1
    assert mock_cache.call_count == 1
    assert mock_update.call_count == 1

    # Verify background called before centering
    call_order = [
        call[0] for call in mocker.mock_calls
        if 'update_background' in str(call) or 'center_on_frame' in str(call)
    ]
    bg_index = next(i for i, c in enumerate(call_order) if 'background' in str(c))
    center_index = next(i for i, c in enumerate(call_order) if 'center' in str(c))
    assert bg_index < center_index
```

**Advantages over current scattered approach**:
- Current: Must mock Qt signal emission order (non-deterministic, hard to test)
- Coordinator: Mock straightforward method calls (deterministic, easy to test)

**Test coverage requirements**:
- ✅ Ordering verification (most critical)
- ✅ Null safety (missing components)
- ✅ Conditional logic (centering enabled/disabled, background present/absent)
- ✅ Integration test (no mocks, verify behavior)
- ✅ Regression test (no visual jumps with background + centering)

---

## 6. Qt Best Practices

### Is This Idiomatic Qt/PySide6 Signal/Slot Usage?

✅ **EXCELLENT - Follows Qt best practices**

**Current problematic approach**:
```python
# 6 independent connections to same signal
state_manager.frame_changed.connect(handler1)
state_manager.frame_changed.connect(handler2)
# ... 4 more connections
# Problem: Qt doesn't guarantee execution order
```

**Proposed coordinator approach**:
```python
# Single connection to coordinator
state_manager.frame_changed.connect(coordinator.on_frame_changed)
# Coordinator calls methods directly (deterministic order)
coordinator._update_background()
coordinator._apply_centering()
```

**Qt Signal/Slot Design Principles**:

1. **Use signals for decoupling** - When sender shouldn't know about receiver
2. **Use direct calls for sequencing** - When order matters
3. **Single update() per event cycle** - Qt performance best practice

**The coordinator follows ALL three principles**:
- ✅ Uses signal for initial notification (state_manager → coordinator)
- ✅ Uses direct method calls for coordinated sequence
- ✅ Batches updates to single `update()` call

**Qt's own internal architecture** follows this pattern:
- Example: `QWidget::updateGeometry()` doesn't emit signals for sub-updates
- It batches layout changes and triggers single relayout
- Same principle as coordinator batching to single repaint

**From Qt documentation**:
> "The order in which the slots connected to a signal are called is undefined.
> If you need to process events in a particular order, don't use signals."

The coordinator respects this by using direct calls for ordered operations.

**Anti-pattern avoided**:
```python
# BAD: Trying to enforce order with queued connections
state_manager.frame_changed.connect(handler1, Qt.DirectConnection)
state_manager.frame_changed.connect(handler2, Qt.QueuedConnection)
# Still non-deterministic, depends on event loop timing
```

---

## 7. Consistency with Existing Controllers

### Does This Match ui/controllers/ Patterns?

✅ **GOOD consistency, with one placement issue**

**Comparison table**:

| Controller | Constructor Pattern | Role | State Ownership |
|-----------|-------------------|------|----------------|
| **ViewManagementController** | Takes main_window | Background/view management | Owns image data |
| **StateSyncController** | Takes widget + state_manager | ApplicationState ↔ Widget sync | Stateless |
| **TimelineController** | Takes state_manager + main_window | Playback control | Owns playback state |
| **FrameChangeCoordinator** | Takes main_window | Frame change orchestration | Stateless |

**Pattern consistency**:
- ✅ Constructor pattern matches ViewManagementController
- ✅ Stateless coordination matches StateSyncController
- ✅ Naming consistent: `*Controller` suffix
- ✅ Location: `ui/controllers/` is correct

**Controller lifecycle in MainWindow** (from `__init__`, line 183):
```python
def __init__(self, parent: QWidget | None = None):
    # ... state manager init ...

    # Initialize controllers (all created in MainWindow.__init__)
    self.timeline_controller = TimelineController(self.state_manager, self)
    self.action_controller = ActionHandlerController(self.state_manager, self)
    self.ui_init_controller = UIInitializationController(self)
    self.view_management_controller = ViewManagementController(self)
    self.point_editor_controller = PointEditorController(self, self.state_manager)
    self.tracking_controller = MultiPointTrackingController(self)
    self.signal_manager = SignalConnectionManager(self)
```

**⚠️ PLACEMENT ISSUE**: Plan says coordinator created in SignalConnectionManager

**From refactor plan** (Phase 3):
```python
# ui/controllers/signal_connection_manager.py
main_window.frame_change_coordinator = FrameChangeCoordinator(main_window)
main_window.frame_change_coordinator.connect()
```

**This is WRONG** - breaks existing pattern!

**SignalConnectionManager's role**: Wire signals (line 38-52)
- Calls `.connect()` on controllers
- Doesn't create controllers

**Correct approach** (matches existing pattern):
```python
# ui/main_window.py __init__
self.timeline_controller = TimelineController(self.state_manager, self)
self.frame_change_coordinator = FrameChangeCoordinator(self)  # ← Add here
self.signal_manager = SignalConnectionManager(self)

# ui/controllers/signal_connection_manager.py
def connect_all_signals(self) -> None:
    # ... existing connections ...
    # Connect frame change coordinator
    self.main_window.frame_change_coordinator.connect()
```

**Recommendation**: Move coordinator creation to MainWindow.__init__()

---

## 8. SOLID Principles Evaluation

### Single Responsibility Principle (SRP)

✅ **EXCELLENT**

**Coordinator has ONE job**: Orchestrate frame change responses in correct order

**Doesn't do**:
- ❌ Implement business logic
- ❌ Own state beyond component references
- ❌ Make decisions about behavior (only timing/ordering)

**Comparison**: Each private method is single-responsibility:
- `_update_background()` - One thing
- `_apply_centering()` - One thing
- `_invalidate_caches()` - One thing
- `_update_timeline_widgets()` - One thing
- `_trigger_repaint()` - One thing

### Open/Closed Principle (OCP)

⚠️ **WEAK - Hard-coded sequence**

**Violation**: Adding new handler requires modifying `on_frame_changed()`

**However**: For stable domain (frame changes), this is acceptable trade-off.

**Recommendation**:
- Accept for initial implementation (YAGNI)
- Refactor to pipeline pattern if extensibility becomes needed

### Liskov Substitution Principle (LSP)

**N/A** - No inheritance hierarchy

### Interface Segregation Principle (ISP)

✅ **GOOD**

**Depends on concrete types but uses minimal interface**:
- `view_management.update_background_for_frame(frame)` - Specific method only
- `curve_widget.center_on_frame(frame)` - Specific method only
- No fat interfaces or unused methods

### Dependency Inversion Principle (DIP)

⚠️ **MODERATE**

**Issue**: Depends on concrete MainWindow, not abstraction

**Better approach**:
```python
class FrameChangeComponentsProtocol(Protocol):
    @property
    def curve_widget(self) -> CurveViewWidget: ...
    @property
    def view_management_controller(self) -> ViewManagementController: ...
    # etc.

def __init__(self, components: FrameChangeComponentsProtocol):
```

**However**: Matches existing pattern in codebase (pragmatic consistency)

**Overall SOLID Score: 3.5/5**
- Good fundamentals
- Violations are pragmatic, not ignorant
- Acceptable for this codebase's architecture

---

## 9. Design Decision Analysis

### Decision 1: No Feature Flag

✅ **CORRECT for this context**

**Plan's reasoning**: "Git revert is simpler than dual code paths"

**Assessment**:

| Context | Feature Flag? | Reasoning |
|---------|---------------|-----------|
| **Enterprise production** | ✅ Yes | Gradual rollout, A/B testing, safe rollback |
| **Personal project + 2105 tests** | ❌ No | Git revert simpler, no deployment complexity |

**Trade-offs**:

PROs of feature flag:
- Safe rollback via config toggle
- Can enable/disable per-user
- A/B testing possible

CONs of feature flag:
- Maintains two code paths (complexity)
- Eventually removed anyway (temporary value)
- Requires conditional logic throughout

**For this project**: Git revert is simpler.

**However, one inaccuracy**: Plan claims "small changeset" but Phase 4 touches 6+ files:
- signal_connection_manager.py
- curve_view_widget.py (remove fallback)
- state_sync_controller.py (remove method)
- main_window.py (remove method)
- timeline_controller.py (verify no repaint)
- timeline_tabs.py (keep method)

Not as "small" as claimed, but still manageable with comprehensive tests.

---

### Decision 2: Call Private Methods Directly

⚠️ **ACCEPTABLE but not ideal**

**Plan's decision**: Coordinator calls `TimelineTabs._on_state_frame_changed()` (private method)

**Plan's reasoning**:
- "Coordinator owns orchestration, accessing internals is appropriate"
- "Avoid wrapper proliferation"
- "Python's `_` is hint, not enforcement"

**Python naming convention**:
- `_method()` = "internal use" (soft privacy)
- `__method()` = name mangling (harder privacy)
- Single underscore is convention, not enforcement

**Alternative: Public wrapper**
```python
# TimelineTabs
def update_frame_display(self, frame: int) -> None:
    """Public API for coordinator to update frame display."""
    self._on_state_frame_changed(frame)
```

**Trade-offs**:

| Approach | PROs | CONs |
|----------|------|------|
| **Call private directly** | Less boilerplate, acknowledges tight coupling | Violates encapsulation principle |
| **Public wrapper** | Better encapsulation, clearer API | One-line wrapper "proliferation" |

**Assessment**: This is philosophical, not technical
- Components are already tightly coupled (TimelineTabs created by MainWindow)
- Coupling is inevitable given coordinator's role
- Public wrapper is ONE line but clarifies intent

**Recommendation**:
- ✅ **Add public wrapper** for better encapsulation
- 📝 Document that wrapper exists for coordinator
- If TimelineTabs has 3+ internal methods coordinator needs, then reconsider

**Example**:
```python
# ui/timeline_tabs.py
def update_frame_display(self, frame: int) -> None:
    """
    Update frame display (visual updates only).

    Called by FrameChangeCoordinator during frame change orchestration.
    Does NOT modify state (state already changed).
    """
    self._on_state_frame_changed(frame)
```

---

### Decision 3: Hard-Coded Handler Sequence

✅ **CORRECT - Order is semantically constrained**

**Critical dependencies** (from problem domain):
1. Background MUST load before centering (centering needs viewport dimensions from background)
2. Centering MUST complete before repaint (repaint uses pan_offset from centering)
3. Cache invalidation MUST happen before repaint
4. All state updates MUST complete before repaint

These are **semantic constraints**, not configuration preferences.

**When to hard-code order**:
- ✅ Single correct order exists (this case)
- ✅ Order dictated by dependencies (this case)
- ✅ No valid alternative orderings (this case)

**When to make configurable**:
- ❌ Multiple valid orderings
- ❌ Different contexts need different orders
- ❌ Plugins need to insert handlers

**Verdict**: Hard-coding is correct. Making it configurable adds complexity with zero benefit (YAGNI).

**Recommendation**: Make dependencies EXPLICIT in comments
```python
def on_frame_changed(self, frame: int) -> None:
    """
    Handle frame change with coordinated updates.

    Order is CRITICAL (semantic dependencies):
    1. Background → Provides viewport dimensions for centering
    2. Centering → Uses background dimensions, updates pan_offset
    3. Cache invalidation → Prepares for render with updated state
    4. Widget updates → No repaints (prevents multiple update() calls)
    5. Repaint → Single update() with all state applied
    """
```

---

### Decision 4: Controller Placement

❌ **WRONG - Should be created in MainWindow, not SignalConnectionManager**

**Plan says** (Phase 3):
```python
# ui/controllers/signal_connection_manager.py
main_window.frame_change_coordinator = FrameChangeCoordinator(main_window)
main_window.frame_change_coordinator.connect()
```

**This breaks existing pattern!**

**Existing pattern** (from MainWindow.__init__, line 220-228):
```python
# Controllers created in MainWindow.__init__
self.timeline_controller = TimelineController(self.state_manager, self)
self.action_controller = ActionHandlerController(self.state_manager, self)
self.view_management_controller = ViewManagementController(self)
self.point_editor_controller = PointEditorController(self, self.state_manager)
self.tracking_controller = MultiPointTrackingController(self)
self.signal_manager = SignalConnectionManager(self)
```

**SignalConnectionManager's role** (line 38-52):
- Wire signals (`connect_all_signals()`)
- Call `.connect()` on existing controllers
- **NOT** create controllers

**Correct approach**:
```python
# ui/main_window.py __init__ (line ~228)
self.tracking_controller = MultiPointTrackingController(self)
self.frame_change_coordinator = FrameChangeCoordinator(self)  # ← Add here
self.signal_manager = SignalConnectionManager(self)

# ui/controllers/signal_connection_manager.py
def connect_all_signals(self) -> None:
    self._connect_file_operations_signals()
    self._connect_signals()
    self._connect_store_signals()
    self._connect_curve_widget_signals()
    self._connect_frame_change_coordinator()  # ← New method
    self._verify_connections()

def _connect_frame_change_coordinator(self) -> None:
    """Connect frame change coordinator to state manager."""
    if self.main_window.frame_change_coordinator:
        self.main_window.frame_change_coordinator.connect()
        logger.info("Frame change coordinator connected")
```

**This maintains separation of concerns**:
- **MainWindow**: Creates and owns controllers
- **SignalConnectionManager**: Wires controllers to signals

---

## 10. Long-Term Maintainability

### What Will Make This Hard to Maintain?

**Potential issues**:

1. **Implicit dependencies between handlers** ⚠️
   - Background → Centering dependency is IMPLICIT in code order
   - Future developer might reorder without understanding why
   - **Mitigation**: Add extensive comments explaining dependencies

2. **Tight coupling to MainWindow structure** (acceptable)
   - If MainWindow reorganizes, coordinator breaks
   - **Mitigation**: This is inevitable given coordinator's role, matches existing controllers

3. **Hidden control flow** ⚠️
   - Frame changes now go through coordinator, not obvious from signal connections
   - Debugging requires knowing coordinator exists
   - **Mitigation**: Clear logging + documentation in CLAUDE.md

4. **Testing complexity** ⚠️
   - Integration tests need to understand coordinator exists
   - Mocking becomes more complex
   - **Mitigation**: Comprehensive test suite (planned in Phase 2)

**Specific maintainability improvements needed**:

1. **Make dependencies EXPLICIT**:
```python
def on_frame_changed(self, frame: int) -> None:
    """
    Handle frame change with coordinated updates.

    ⚠️ ORDER IS CRITICAL - DO NOT REORDER ⚠️

    Phase 1: Pre-Render State Updates (with dependencies)
    ├─ Background loading   [No dependencies]
    ├─ Centering           [Depends on: Background for viewport size]
    └─ Cache invalidation  [Depends on: Centering for pan_offset]

    Phase 2: Widget Updates (no repaints)
    └─ Timeline widgets    [No dependencies]

    Phase 3: Single Repaint
    └─ Trigger update()    [Depends on: ALL above complete]
    """
```

2. **Add dependency graph documentation**:
```
docs/FRAME_CHANGE_COORDINATOR_DEPENDENCIES.md
    Background Loading
           ↓
    Centering (needs viewport dimensions)
           ↓
    Cache Invalidation
           ↓
    Widget Updates
           ↓
    Single Repaint (update())
```

3. **Add logging for debugging**:
```python
def on_frame_changed(self, frame: int) -> None:
    logger.debug(f"[COORDINATOR] Frame change started: {frame}")
    start_time = time.perf_counter()

    self._update_background(frame)
    logger.debug(f"[COORDINATOR] Background updated in {(time.perf_counter() - start_time)*1000:.2f}ms")
    # ... etc
```

---

## 11. Alternative Approaches

### Are There Viable Alternatives to Coordinator Pattern?

**Alternative 1: Event Pipeline (Pub/Sub with ordering)**
```python
class FrameChangeEvent:
    def __init__(self, frame: int):
        self.frame = frame
        self.background_loaded = False
        self.centering_applied = False

pipeline.register(BackgroundHandler, depends_on=[])
pipeline.register(CenteringHandler, depends_on=[BackgroundHandler])
```

**PROs**:
- More extensible
- Explicit dependency graph
- Could support plugins

**CONs**:
- Over-engineered for 5 handlers
- Adds significant complexity
- Still need to implement dependency resolution

**Verdict**: ❌ Overkill for this use case

---

**Alternative 2: State Machine**
```python
# Frame change triggers state transitions
IDLE → BACKGROUND_LOADING → BACKGROUND_LOADED → CENTERING →
CACHE_INVALIDATED → WIDGETS_UPDATED → READY_TO_PAINT → IDLE
```

**PROs**:
- Clear state transitions
- Testable states
- Could handle async operations

**CONs**:
- Massive overkill for synchronous operations
- All updates happen in single event loop iteration
- No actual async steps that need state tracking

**Verdict**: ❌ Wrong abstraction

---

**Alternative 3: Qt's queued connections with priority**

Use Qt's connection order by strategically ordering connections with QueuedConnection

**PROs**:
- Uses Qt's built-in mechanisms
- No new code needed

**CONs**:
- ❌ Still non-deterministic (Qt doesn't guarantee order even with queued)
- ❌ Priority-based ordering is Qt internal detail (not exposed in public API)
- ❌ Depends on event loop timing

**Verdict**: ❌ Doesn't solve the fundamental problem

---

**Alternative 4: Fix ordering with QTimer.singleShot(0)**

Keep current scattered approach but use timers to enforce order:
```python
def handler1():
    do_work()
    QTimer.singleShot(0, handler2)

def handler2():
    do_work()
    QTimer.singleShot(0, handler3)
```

**PROs**:
- Minimal code changes

**CONs**:
- ❌ Still fragile
- ❌ Horrible for debugging
- ❌ Doesn't solve coordination problem
- ❌ Multiple event loop iterations (slower)

**Verdict**: ❌ Hack, not solution

---

**Alternative 5: Keep current approach, fix duplicate connection**

Just fix the duplicate connection bug, document handler ordering carefully

**PROs**:
- Minimal changes
- No new abstractions

**CONs**:
- ❌ Doesn't solve non-deterministic ordering
- ❌ Still fragile
- ❌ Still multiple update() calls
- ❌ User reported it "still jumps" despite patches

**Verdict**: ❌ Doesn't address root cause

---

### **Conclusion: Coordinator Pattern is the RIGHT Choice**

✅ Simplest solution that solves the problem
✅ Matches existing patterns in codebase
✅ No over-engineering
✅ Clear ownership and testability
✅ Respects Qt's signal/slot design principles

---

## 12. Summary of Recommendations

### Critical Issues (Must Fix)

1. **⚠️ Wrong Placement**
   - **Issue**: Plan creates coordinator in SignalConnectionManager
   - **Fix**: Create in MainWindow.__init__() like other controllers
   - **Impact**: Breaks existing pattern, confuses responsibility

2. **⚠️ Implicit Dependencies**
   - **Issue**: Handler ordering rationale not explicit in code
   - **Fix**: Add comprehensive comments explaining dependencies
   - **Impact**: Future developers might reorder incorrectly

### Recommended Improvements

3. **📝 Add Public Wrapper for TimelineTabs**
   - **Issue**: Calling private `_on_state_frame_changed()` directly
   - **Fix**: Add one-line public wrapper `update_frame_display()`
   - **Impact**: Better encapsulation, clearer API

4. **📝 Document Coordinator in Architecture**
   - **Issue**: CLAUDE.md doesn't mention coordinator yet
   - **Fix**: Add to "UI Controllers" section with role explanation
   - **Impact**: Helps future developers understand control flow

5. **📝 Add Dependency Graph Documentation**
   - **Issue**: Dependencies between handlers not visualized
   - **Fix**: Create docs/FRAME_CHANGE_COORDINATOR_DEPENDENCIES.md
   - **Impact**: Easier to understand rationale for ordering

### Future Considerations

6. **🔮 Monitor for Extensibility Needs**
   - **When**: If 3+ new frame change handlers added
   - **Action**: Refactor to pipeline pattern with dependency graph
   - **Trigger**: When hard-coded sequence becomes unwieldy

7. **🔮 Consider Facade Pattern for Dependencies**
   - **When**: If 3+ more coordinators created with similar dependencies
   - **Action**: Create FrameChangeComponents facade
   - **Trigger**: Pattern repetition across multiple coordinators

---

## 13. Final Verdict

### Overall Assessment: ✅ **APPROVE WITH RECOMMENDATIONS**

**The refactor is architecturally sound and solves a genuine production bug.**

**Strengths**:
1. ✅ Solves real race condition (non-deterministic Qt signal ordering)
2. ✅ Follows existing controller patterns (consistency)
3. ✅ Highly testable design (mockable dependencies)
4. ✅ Follows Qt best practices (single update() call)
5. ✅ Single Responsibility Principle well-applied
6. ✅ Mediator pattern applied correctly (not a god object)
7. ✅ Pragmatic trade-offs (YAGNI over premature generalization)

**Required changes before implementation**:
1. ⚠️ Move coordinator creation to MainWindow.__init__() (critical)
2. ⚠️ Add extensive comments explaining handler dependencies (critical)
3. 📝 Add public wrapper for TimelineTabs._on_state_frame_changed()
4. 📝 Update CLAUDE.md to document coordinator

**SOLID Score**: 3.5/5 (Good but not perfect - violations are pragmatic)

**Recommendation**: **PROCEED with refactor** after addressing critical placement issue.

---

## Appendix: Implementation Checklist

### Before Starting Phase 1

- [ ] Move coordinator creation to MainWindow.__init__() (not SignalConnectionManager)
- [ ] Add public wrapper to TimelineTabs: `update_frame_display()`
- [ ] Prepare documentation updates for CLAUDE.md

### During Implementation

- [ ] Add extensive comments explaining dependencies in `on_frame_changed()`
- [ ] Implement comprehensive logging for debugging
- [ ] Ensure null safety for all components
- [ ] Add type hints for all methods

### After Implementation

- [ ] Update CLAUDE.md with coordinator documentation
- [ ] Create dependency graph visualization (optional but helpful)
- [ ] Verify all 2105+ tests pass
- [ ] Manual testing: background + centering mode during playback
- [ ] Document tight coupling explicitly in coordinator docstring

---

**Review Date**: 2025-10-07
**Reviewed By**: Python Expert Architect Agent
**Recommendation**: ✅ APPROVE WITH CRITICAL PLACEMENT FIX
