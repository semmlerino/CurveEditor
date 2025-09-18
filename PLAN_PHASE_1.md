# PHASE 1: Reactive Data Store Implementation
## Detailed 2-Week Execution Plan

### Phase Goal
Establish centralized, reactive data management that automatically propagates changes to all UI components, eliminating the "orphaned component" problem that caused the timeline colors issue.

### Success Criteria
- ✅ All curve data flows through CurveDataStore
- ✅ All UI components update automatically via signals
- ✅ Zero direct data manipulation in UI components
- ✅ Connection verification system operational
- ✅ Integration tests prove data flow works

---

## Week 1: Core Store Implementation

### Day 1-2: CurveDataStore Foundation

#### Morning Day 1: Initial Store Structure
```python
# File: stores/curve_data_store.py
class CurveDataStore(QObject):
    # Signals for all data changes
    data_changed = Signal()  # Full data update
    point_added = Signal(int)  # Index
    point_updated = Signal(int, float, float)  # Index, x, y
    point_removed = Signal(int)  # Index
    point_status_changed = Signal(int, str)  # Index, status
    selection_changed = Signal(set)  # Selected indices

    def __init__(self):
        super().__init__()
        self._data: CurveDataList = []
        self._selection: set[int] = set()
        self._undo_stack: list[CurveDataList] = []

    def set_data(self, data: CurveDataList) -> None:
        """Replace all data"""
        self._add_to_undo()
        self._data = data
        self.data_changed.emit()
```

#### Afternoon Day 1: Store Operations
- Implement CRUD operations: `add_point()`, `update_point()`, `remove_point()`
- Add selection management: `select()`, `deselect()`, `clear_selection()`
- Implement status changes: `set_point_status()`
- Add validation layer

#### Day 2: Store Manager & Testing
```python
# File: stores/store_manager.py
class StoreManager:
    """Singleton manager for all application stores"""
    _instance: Optional['StoreManager'] = None

    def __init__(self):
        self.curve_store = CurveDataStore()
        self.frame_store = FrameStore()
        self.view_store = ViewStore()

    @classmethod
    def get_instance(cls) -> 'StoreManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

**Tests to Write**:
- `test_store_crud_operations.py`
- `test_store_signals.py`
- `test_store_undo_redo.py`

### Day 3-4: Connect CurveViewWidget

#### Day 3 Morning: Refactor CurveViewWidget
**Current State**: Direct data manipulation
**Target State**: Observer of store

```python
# In curve_view_widget.py
def __init__(self):
    super().__init__()
    self.store = StoreManager.get_instance().curve_store
    self._setup_store_connections()

def _setup_store_connections(self):
    """Connect to store signals"""
    self.store.data_changed.connect(self._on_store_data_changed)
    self.store.point_updated.connect(self._on_store_point_updated)
    self.store.selection_changed.connect(self._on_store_selection_changed)

def _on_store_data_changed(self):
    """Store data changed, update display"""
    self.curve_data = self.store.get_data()
    self.update()  # Trigger repaint
```

#### Day 3 Afternoon: Remove Direct Manipulation
- Replace `self.curve_data.append()` with `self.store.add_point()`
- Replace `self.curve_data[i] = ...` with `self.store.update_point()`
- Replace selection management with store methods

#### Day 4: Test & Verify
- Write integration tests
- Verify all curve operations work through store
- Check performance (should be equivalent or better)

### Day 5: Connect Timeline

#### Morning: TimelineTabs Integration
```python
# In timeline_tabs.py
def __init__(self):
    super().__init__()
    self.store = StoreManager.get_instance().curve_store
    self.store.data_changed.connect(self._update_from_store)
    self.store.point_status_changed.connect(self._update_frame_status)

def _update_from_store(self):
    """Complete timeline update from store"""
    data = self.store.get_data()
    frame_status = self._calculate_frame_status(data)
    self._update_all_tabs(frame_status)
```

#### Afternoon: Remove _update_timeline_tabs
- Delete the orphaned `_update_timeline_tabs()` from MainWindow
- Timeline now updates automatically via store signals
- Test all status types display correctly

---

## Week 2: Connection Verification & Testing

### Day 6-7: Connection Verification System

#### Day 6: Verification Framework
```python
# File: core/connection_verifier.py
class ConnectionVerifier:
    """Verify all required connections exist"""

    def __init__(self):
        self.required_connections: dict[str, list[tuple[str, str]]] = {}
        self.verified_connections: set[tuple[str, str]] = set()

    def register_component(self, component: QObject, requirements: list[tuple[str, str]]):
        """Register a component's connection requirements"""
        name = component.__class__.__name__
        self.required_connections[name] = requirements

    def verify_all(self) -> dict[str, list[str]]:
        """Check all connections, return missing ones"""
        missing = {}
        for component, requirements in self.required_connections.items():
            component_missing = []
            for signal_path, slot_path in requirements:
                if not self._is_connected(signal_path, slot_path):
                    component_missing.append(f"{signal_path} -> {slot_path}")
            if component_missing:
                missing[component] = component_missing
        return missing
```

#### Day 7: Runtime Verification
```python
# Add to MainWindow.__init__
def _verify_connections(self):
    """Verify all UI connections after setup"""
    verifier = ConnectionVerifier()

    # Register all components
    verifier.register_component(self.curve_widget, [
        ('store.data_changed', 'curve_widget.update'),
        ('store.selection_changed', 'curve_widget.update_selection')
    ])

    verifier.register_component(self.timeline_tabs, [
        ('store.data_changed', 'timeline_tabs.update'),
        ('store.point_status_changed', 'timeline_tabs.update_frame')
    ])

    # Verify and warn
    missing = verifier.verify_all()
    if missing:
        logger.error("Missing connections detected!")
        for component, connections in missing.items():
            logger.error(f"{component}: {connections}")
        if DEBUG_MODE:
            raise ConnectionError(f"Missing {len(missing)} connections")
```

### Day 8-9: Integration Testing Suite

#### Day 8: Test Infrastructure
```python
# File: tests/integration/test_data_flow.py
class TestDataFlow:
    """Verify data flows correctly through the system"""

    def test_curve_update_triggers_timeline(self, qtbot):
        """Adding a point updates timeline"""
        store = CurveDataStore()
        timeline = TimelineTabs()
        timeline.connect_to_store(store)

        with qtbot.waitSignal(timeline.updated, timeout=100):
            store.add_point((10, 100, 200, "keyframe"))

        assert timeline.has_frame_status(10)
        assert timeline.get_frame_color(10) == "green"

    def test_status_change_updates_timeline(self, qtbot):
        """Changing point status updates timeline color"""
        # ... test implementation
```

#### Day 9: Comprehensive Test Coverage
**Test Files to Create**:
- `test_store_to_curve_view.py` - Store → CurveView updates
- `test_store_to_timeline.py` - Store → Timeline updates
- `test_user_action_flow.py` - User action → Store → UI
- `test_connection_verification.py` - Verification system works
- `test_orphaned_components.py` - Detect disconnected UI

### Day 10: Documentation & Cleanup

#### Morning: Documentation
```markdown
# File: docs/data_flow_patterns.md
## How Data Flows in CurveEditor

### Adding a Point
1. User clicks in CurveViewWidget
2. CurveViewWidget calls `store.add_point()`
3. Store validates and adds point
4. Store emits `point_added` signal
5. All connected components update:
   - CurveViewWidget repaints
   - Timeline adds frame tab
   - StatusBar shows "Point added"

### Never Do This
❌ `self.curve_data.append(point)`  # Direct manipulation
❌ `timeline._update_manually()`     # Manual updates
❌ `if hasattr(self, 'timeline')`    # Optional connections

### Always Do This
✅ `self.store.add_point(point)`    # Through store
✅ Connect in `__init__`             # Automatic updates
✅ Verify connections exist          # Fail loud
```

#### Afternoon: Clean Up Old Patterns
- Remove all direct `curve_data` manipulation
- Delete orphaned update methods
- Remove manual update calls
- Add deprecation warnings for old patterns

---

## Deliverables Checklist

### Week 1 Deliverables
- [ ] `stores/curve_data_store.py` - Core store implementation
- [ ] `stores/store_manager.py` - Singleton manager
- [ ] `stores/frame_store.py` - Frame state store
- [ ] CurveViewWidget connected to store
- [ ] Timeline connected to store
- [ ] All direct manipulation removed from UI

### Week 2 Deliverables
- [ ] `core/connection_verifier.py` - Verification system
- [ ] Runtime connection checking in MainWindow
- [ ] 15+ integration tests
- [ ] Architecture documentation
- [ ] Migration guide for old code
- [ ] Performance benchmarks

### Migration Checkpoints

#### Checkpoint 1 (Day 2): Store Operational
- Store can manage curve data
- Signals emit correctly
- Basic tests pass

#### Checkpoint 2 (Day 4): CurveView Migrated
- CurveView uses store exclusively
- No regressions in functionality
- Performance acceptable

#### Checkpoint 3 (Day 5): Timeline Connected
- Timeline updates automatically
- All status colors working
- Original bug impossible to recreate

#### Checkpoint 4 (Day 9): Tests Complete
- All integration tests passing
- Connection verification working
- No orphaned components possible

#### Final Checkpoint (Day 10): Ready for Phase 2
- Documentation complete
- Old patterns removed
- Implementation patterns documented

---

## Risk Management

### Risk: Performance Degradation
**Mitigation**:
- Benchmark before/after each component migration
- Use signal batching for bulk updates
- Profile hot paths with cProfile

### Risk: Breaking Existing Features
**Mitigation**:
- Run full test suite after each change
- Keep compatibility shims temporarily
- Gradual migration with feature flags

### Risk: Implementation Complexity
**Mitigation**:
- Clear documentation with examples
- Test-driven implementation
- Incremental changes with verification

---

## Implementation Milestones

### Week 1 Milestones
- Mon: Store architecture implementation
- Tue: Store testing complete
- Wed: CurveView migration complete
- Thu: CurveView testing verified
- Fri: Timeline integration complete

### Week 2 Milestones
- Mon: Connection verification implemented
- Tue: Verification testing complete
- Wed: Integration test suite complete
- Thu: All tests passing
- Fri: Documentation complete

---

## Success Metrics

### Quantitative (End of Phase 1)
- ✅ 0 direct data manipulations in UI code
- ✅ 100% of UI components connected via store
- ✅ 15+ integration tests passing
- ✅ < 16ms update time for 1000 points
- ✅ 0 orphaned components possible

### Qualitative
- ✅ Clear data flow pattern established
- ✅ Timeline colors bug impossible to recreate
- ✅ Pattern is clear and documented
- ✅ Adding new UI components is straightforward

---

## Tools & Resources

### Development Tools
- Qt Signal Spy for testing signals
- cProfile for performance analysis
- pytest-qt for integration testing
- Type checkers: basedpyright, mypy

### Reference Documentation
- [Qt Signals & Slots](https://doc.qt.io/qt-6/signalsandslots.html)
- [Flux Architecture Pattern](https://facebook.github.io/flux/)
- [Redux Principles](https://redux.js.org/understanding/thinking-in-redux/three-principles)

### Implementation Resources
- Qt Signals & Slots documentation
- Test suite for verification
- Performance profiling tools
- Type checking with basedpyright

---

## Conclusion

Phase 1 establishes the foundation for a robust, maintainable architecture. By the end of these 2 weeks:

1. **The timeline colors bug becomes impossible** - Components can't be orphaned
2. **Adding new features is safe** - Clear patterns to follow
3. **Debugging is easier** - Single source of truth for data
4. **Testing is comprehensive** - Integration tests catch issues
5. **Implementation is verifiable** - Fail-loud architecture

This phase directly addresses the root cause of our timeline issue: inconsistent update patterns and silent failures. With the reactive store in place, UI updates become automatic and reliable.

**Next Phase Preview**: With the store foundation in place, Phase 2 will decompose MainWindow into focused controllers, reducing complexity and improving maintainability.
