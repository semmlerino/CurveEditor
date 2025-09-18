# PLAN OMEGA: CurveEditor Architecture Refactoring
## DO NOT DELETE - Master Architecture Plan

### Executive Summary
This plan addresses systemic architectural issues discovered through the "timeline colors not showing" incident, where `_update_timeline_tabs()` was defined but never called. The root cause revealed deeper problems: inconsistent update patterns, no reactive architecture, scattered state management, and silent failures.

### Core Problems Identified

#### 1. **Inconsistent Update Patterns**
- Some components use Qt signals (reactive)
- Some use direct method calls (imperative)
- Some aren't connected at all (orphaned)
- No clear pattern to follow in the codebase

#### 2. **Silent Failures**
- Missing connections fail silently
- No compile-time checking
- No runtime warnings
- UI just doesn't update, no errors

#### 3. **Monolithic MainWindow**
- 1400+ lines doing everything
- UI setup, signals, file ops, state management
- Impossible to trace data flow
- High coupling, low cohesion

#### 4. **Scattered State Management**
- Curve data in CurveViewWidget
- Frame state in TimelineTabs
- Selection state in multiple places
- Manual synchronization required

#### 5. **Implicit Dependencies**
- Components depend on each other without contracts
- No clear "when X changes, update Y" documentation
- Mental model too complex

### Architecture Vision

#### Target Architecture: Unidirectional Data Flow
```
User Action → Command → Store → Signal → Views Update
                ↑                           ↓
                └──────── Services ←────────┘
```

#### Key Principles
1. **Single Source of Truth**: All state in centralized stores
2. **Reactive Updates**: All UI updates via signals
3. **Explicit Contracts**: Clear interfaces and protocols
4. **Fail Loud**: Missing connections cause immediate errors
5. **Testable**: Integration tests for all data flows

### Implementation Phases

## Phase 1: Reactive Data Store (2 weeks)
**Goal**: Establish centralized data management with automatic UI updates

### Core Components:
```python
class CurveDataStore(QObject):
    """Single source of truth for curve data"""
    data_changed = Signal(CurveDataList)
    selection_changed = Signal(set)
    status_changed = Signal(int, PointStatus)  # frame, status

class StoreManager:
    """Manages all application stores"""
    curve_store: CurveDataStore
    frame_store: FrameStore
    view_store: ViewStore
```

### Deliverables:
- CurveDataStore implementation
- Connect all UI components to store
- Remove direct data manipulation
- Add connection verification
- Integration test suite

## Phase 2: MainWindow Decomposition (3 weeks)
**Goal**: Break monolithic MainWindow into focused controllers

### New Structure:
```
MainWindow (200 lines) - Thin coordination layer
├── FileController - File operations
├── PlaybackController - Animation/playback
├── ViewConthroller - View state management
├── EditController - Editing operations
└── UICoordinator - UI setup and layout
```

### Deliverables:
- Extract controllers with clear responsibilities
- Establish controller communication patterns
- Reduce MainWindow to < 300 lines
- Update all signal connections
- Maintain backwards compatibility

## Phase 3: Component Contracts (2 weeks)
**Goal**: Define clear interfaces between components

### Contract System:
```python
class DataObserver(Protocol):
    def on_data_changed(self, data: CurveDataList) -> None: ...
    def on_selection_changed(self, selection: set[int]) -> None: ...

class UIComponent(Protocol):
    required_connections: list[tuple[str, str]]
    def verify_connections(self) -> bool: ...
```

### Deliverables:
- Define protocols for all component types
- Implement contract verification
- Add runtime connection checking
- Create component documentation
- Type-check all interfaces

## Phase 4: Service Consolidation (2 weeks)
**Goal**: Align services with new architecture

### Service Refactoring:
- Merge overlapping service responsibilities
- Align with store architecture
- Remove service state (stateless operations)
- Clear service boundaries

### Deliverables:
- Refactored service layer
- Service protocol definitions
- Remove service dependencies on UI
- Performance optimization
- Service test suite

## Phase 5: Polish & Performance (1 week)
**Goal**: Optimize and document new architecture

### Focus Areas:
- Performance profiling
- Memory optimization
- Debug tooling
- Architecture documentation
- Migration guide

### Deliverables:
- Performance benchmarks
- Debug inspector for stores
- Architecture documentation
- Implementation guide
- Code examples

### Success Metrics

#### Quantitative
- Zero orphaned UI components (automated check)
- 100% signal coverage for data changes
- MainWindow < 300 lines
- 90%+ integration test coverage
- < 16ms frame time for updates

#### Qualitative
- Clear, understandable architecture
- Consistent patterns throughout
- Easy to add new features
- Difficult to create bugs
- Self-documenting architecture

### Risk Mitigation

#### Risk 1: Breaking Changes
- **Mitigation**: Maintain compatibility layer during migration
- **Strategy**: Parallel old/new systems with gradual cutover

#### Risk 2: Performance Regression
- **Mitigation**: Benchmark before/after each phase
- **Strategy**: Profile critical paths, optimize hot spots

#### Risk 3: Implementation Complexity
- **Mitigation**: Comprehensive documentation and examples
- **Strategy**: Incremental implementation with testing at each step

#### Risk 4: Scope Creep
- **Mitigation**: Strict phase boundaries
- **Strategy**: Feature freeze during refactoring phases

### Migration Strategy

#### Stage 1: Parallel Systems (Phases 1-2)
- New store runs alongside old data flow
- Gradual component migration
- A/B testing of approaches

#### Stage 2: Cutover (Phase 3)
- Switch primary data flow to stores
- Maintain compatibility shims
- Monitor for issues

#### Stage 3: Cleanup (Phases 4-5)
- Remove old patterns
- Delete compatibility layers
- Final optimization

### Long-term Benefits

1. **Maintainability**: Clear patterns, easy to understand
2. **Reliability**: Fail-loud architecture, comprehensive tests
3. **Performance**: Optimized update paths, minimal redraws
4. **Maintainability**: Consistent patterns, good tooling
5. **Extensibility**: Easy to add new features correctly

### Implementation Checklist

#### Pre-Phase 1
- [ ] Document current architecture
- [ ] Set up performance benchmarks
- [ ] Create migration branches
- [ ] Plan test coverage

#### Per-Phase
- [ ] Implement phase deliverables
- [ ] Run all tests after each major change
- [ ] Update documentation as needed
- [ ] Verify performance metrics

#### Post-Implementation
- [ ] Architecture documentation complete
- [ ] All tests passing
- [ ] Performance targets met
- [ ] Migration guide complete

### Conclusion

The timeline colors incident revealed fundamental architectural issues that make the codebase fragile and error-prone. This plan transforms the architecture from an implicit, imperative system to an explicit, reactive one where:

1. **Data flows are automatic and traceable**
2. **Missing connections fail immediately**
3. **Components have clear contracts**
4. **Testing is comprehensive and easy**
5. **Future modifications are safe and predictable**

By following this plan, we eliminate entire classes of bugs (like orphaned UI components) and create a robust foundation for future development.

### Timeline
- **Total Duration**: 10 weeks
- **Start Date**: [TBD]
- **Phase 1**: Weeks 1-2
- **Phase 2**: Weeks 3-5
- **Phase 3**: Weeks 6-7
- **Phase 4**: Weeks 8-9
- **Phase 5**: Week 10

### Document Status
**DO NOT DELETE** - This is the master architecture plan
- Created: 2025-01-18
- Last Updated: 2025-01-18
- Status: Active Planning
- Implementation: LLM-based development
