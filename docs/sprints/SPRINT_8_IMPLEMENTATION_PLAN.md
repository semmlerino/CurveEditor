# Sprint 8: Service Decomposition - Detailed Implementation Plan

## Executive Summary

**Duration**: 2 weeks
**Objective**: Decompose 2 God objects (InteractionService: 1,090 lines, DataService: 1,152 lines) into 8-10 focused services following SOLID principles.

## Current State Analysis

### InteractionService (1,090 lines, 47 methods)
Currently handles:
- Mouse/keyboard event handling (8 methods)
- Point selection and manipulation (9 methods)
- History/undo/redo management (14 methods)
- State compression/decompression (8 methods)
- UI updates and info display (8 methods)

### DataService (1,152 lines, 20 methods)
Currently handles:
- File I/O operations (JSON/CSV) (6 methods)
- Image sequence management (9 methods)
- Recent files tracking (3 methods)
- Cache management (2 methods)

## Target Architecture

### From InteractionService → 4 New Services

#### 1. EventHandlerService (~250 lines)
**Responsibility**: Process raw input events
```python
# services/event_handler.py
class EventHandlerService:
    def handle_mouse_press(self, view, event) -> EventResult
    def handle_mouse_move(self, view, event) -> EventResult
    def handle_mouse_release(self, view, event) -> EventResult
    def handle_wheel_event(self, view, event) -> EventResult
    def handle_key_event(self, view, event) -> EventResult
    def handle_context_menu(self, view, event) -> EventResult
    def _convert_to_curve_coords(self, view, pos) -> tuple[float, float]
    def _determine_action(self, event, modifiers) -> ActionType
```

#### 2. SelectionService (~200 lines)
**Responsibility**: Manage point selection state
```python
# services/selection_service.py
class SelectionService:
    def find_point_at(self, view, x, y) -> int
    def select_point_by_index(self, view, idx, add_to_selection) -> bool
    def clear_selection(self, view) -> None
    def select_points_in_rect(self, view, rect) -> int
    def select_all_points(self, view) -> int
    def toggle_point_selection(self, view, idx) -> bool
    def get_selected_indices(self, view) -> list[int]
    def _update_selection_ui(self, main_window) -> None
```

#### 3. PointManipulationService (~300 lines)
**Responsibility**: Modify point data
```python
# services/point_manipulation.py
class PointManipulationService:
    def update_point_position(self, view, idx, x, y) -> bool
    def delete_selected_points(self, view) -> int
    def add_point(self, view, frame, x, y) -> int
    def nudge_points(self, view, dx, dy) -> int
    def interpolate_points(self, view, indices) -> None
    def smooth_points(self, view, indices, factor) -> None
    def _validate_point_position(self, x, y) -> bool
    def _maintain_frame_order(self, view, idx, new_frame) -> bool
```

#### 4. HistoryService (~340 lines)
**Responsibility**: Undo/redo and state management
```python
# services/history_service.py
class HistoryService:
    def add_to_history(self, main_window) -> None
    def undo(self, main_window) -> None
    def redo(self, main_window) -> None
    def clear_history(self, main_window) -> None
    def can_undo(self) -> bool
    def can_redo(self) -> bool
    def compress_state(self, state) -> CompressedState
    def decompress_state(self, compressed) -> State
    def _enforce_memory_limits(self) -> None
    def get_memory_stats(self) -> dict
```

### From DataService → 4 New Services

#### 5. FileIOService (~300 lines)
**Responsibility**: File reading and writing
```python
# services/file_io_service.py
class FileIOService:
    def load_json(self, file_path) -> CurveData
    def save_json(self, file_path, data) -> bool
    def load_csv(self, file_path) -> CurveData
    def save_csv(self, file_path, data) -> bool
    def load_track_data(self, file_path) -> CurveData
    def export_to_csv(self, file_path, data) -> bool
    def _validate_file_path(self, path) -> bool
    def _parse_json_format(self, content) -> CurveData
```

#### 6. ImageSequenceService (~400 lines)
**Responsibility**: Image loading and navigation
```python
# services/image_sequence_service.py
class ImageSequenceService:
    def load_image_sequence(self, directory) -> list[str]
    def set_current_image_by_frame(self, view, frame) -> None
    def load_current_image(self, view) -> QImage | None
    def navigate_to_next_image(self, view) -> bool
    def navigate_to_previous_image(self, view) -> bool
    def get_image_info(self, image_path) -> dict
    def browse_for_image_sequence(self, parent) -> tuple[str, list[str]]
    def _sort_by_frame_number(self, filenames) -> list[str]
    def _find_closest_image_index(self, filenames, frame) -> int
```

#### 7. CacheService (~200 lines)
**Responsibility**: Manage image and data caches
```python
# services/cache_service.py
class CacheService:
    def get_cached_image(self, path) -> QImage | None
    def cache_image(self, path, image) -> None
    def clear_image_cache(self) -> None
    def set_cache_size(self, size) -> None
    def get_cache_stats(self) -> dict
    def _trim_cache(self) -> None
    def _estimate_memory_usage(self) -> int
```

#### 8. RecentFilesService (~150 lines)
**Responsibility**: Track recently opened files
```python
# services/recent_files_service.py
class RecentFilesService:
    def add_recent_file(self, file_path) -> None
    def get_recent_files(self) -> list[str]
    def clear_recent_files(self) -> None
    def remove_invalid_entries(self) -> int
    def _load_recent_files(self) -> None
    def _save_recent_files(self) -> None
```

## Implementation Strategy

### Week 1: InteractionService Decomposition

#### Day 1-2: Setup and Analysis
**Morning**:
1. Create service skeleton files:
   ```bash
   touch services/event_handler.py
   touch services/selection_service.py
   touch services/point_manipulation.py
   touch services/history_service.py
   ```

2. Create protocol interfaces:
   ```python
   # services/protocols/event_protocol.py
   from typing import Protocol

   class EventHandlerProtocol(Protocol):
       def handle_mouse_press(self, view, event) -> None: ...
   ```

**Afternoon**:
3. Map existing methods to new services (create migration map)
4. Identify shared dependencies and data flow

#### Day 3: EventHandlerService
**Tasks**:
1. Extract event handling methods (6 methods)
2. Create EventResult data class for communication
3. Update imports in ui/curve_view_widget.py
4. Write unit tests (test_event_handler.py)

**Validation**:
- All mouse/keyboard events still work
- No UI responsiveness regression

#### Day 4: SelectionService
**Tasks**:
1. Extract selection methods (8 methods)
2. Create SelectionState class
3. Update InteractionService to delegate to SelectionService
4. Write unit tests (test_selection_service.py)

**Validation**:
- Multi-selection works
- Rubber band selection works
- Selection UI updates correctly

#### Day 5: PointManipulationService
**Tasks**:
1. Extract point modification methods (8 methods)
2. Create PointOperation enum for operation types
3. Integrate with HistoryService for undo/redo
4. Write unit tests (test_point_manipulation.py)

**Validation**:
- Point moves are recorded in history
- Delete operations work
- Frame ordering maintained

### Week 2: DataService Decomposition & Integration

#### Day 6: HistoryService
**Tasks**:
1. Extract history/compression methods (14 methods)
2. Implement memory-efficient state storage
3. Create HistoryEntry dataclass
4. Write comprehensive tests with memory limits

**Validation**:
- Undo/redo works with all operations
- Memory limits enforced
- State compression working

#### Day 7-8: FileIOService & ImageSequenceService
**Morning - FileIOService**:
1. Extract file I/O methods (6 methods)
2. Create FileFormat enum
3. Implement format detection
4. Add validation and error handling

**Afternoon - ImageSequenceService**:
1. Extract image methods (9 methods)
2. Implement frame-to-image mapping
3. Add image format support detection

**Validation**:
- All file formats load/save correctly
- Image sequences load properly
- Frame navigation works

#### Day 9: CacheService & RecentFilesService
**Morning - CacheService**:
1. Extract cache methods (4 methods)
2. Implement LRU cache with size limits
3. Add cache statistics

**Afternoon - RecentFilesService**:
1. Extract recent files methods (3 methods)
2. Implement persistence to user settings
3. Add file validation

**Validation**:
- Cache improves performance
- Recent files menu works
- Invalid files handled gracefully

#### Day 10: Integration & Testing
**Tasks**:
1. Update service registry in services/__init__.py
2. Fix all import statements
3. Run full test suite
4. Performance benchmarking
5. Create migration guide

## Migration Path

### Phase 1: Parallel Implementation (Days 1-8)
- New services created alongside existing ones
- Existing services delegate to new ones
- Feature flag to toggle between old/new

```python
# services/__init__.py
USE_NEW_SERVICES = False  # Toggle during migration

def get_interaction_service():
    if USE_NEW_SERVICES:
        return InteractionServiceFacade()  # Delegates to new services
    return InteractionService()  # Original God object
```

### Phase 2: Gradual Migration (Days 9-10)
1. Update one UI component at a time
2. Run tests after each migration
3. Monitor performance metrics
4. Rollback capability at each step

### Phase 3: Cleanup (End of Week 2)
1. Remove old service code
2. Remove feature flags
3. Update documentation
4. Final testing

## Testing Strategy

### Unit Tests (Per Service)
```python
# tests/test_selection_service.py
def test_select_single_point():
    service = SelectionService()
    view = MockCurveView(points=[(1, 100, 200)])
    assert service.select_point_by_index(view, 0)
    assert view.selected_indices == [0]

def test_rubber_band_selection():
    service = SelectionService()
    view = MockCurveView(points=[(1, 100, 200), (2, 150, 250)])
    rect = QRect(50, 150, 200, 200)
    count = service.select_points_in_rect(view, rect)
    assert count == 2
```

### Integration Tests
```python
# tests/test_service_integration.py
def test_select_move_undo_workflow():
    # Test that selection → move → undo works correctly
    selection = get_selection_service()
    manipulation = get_point_manipulation_service()
    history = get_history_service()

    # Select point
    selection.select_point_by_index(view, 0)

    # Move it
    manipulation.update_point_position(view, 0, 200, 300)

    # Undo
    history.undo(main_window)

    # Verify original position restored
    assert view.points[0] == (1, 100, 200)
```

### Performance Tests
```python
def test_large_dataset_performance():
    # Ensure no regression with 10k points
    points = generate_points(10000)
    start = time.time()
    service.select_all_points(view)
    elapsed = time.time() - start
    assert elapsed < 0.1  # 100ms threshold
```

## Risk Mitigation

### Risk 1: Breaking Changes
**Mitigation**:
- Feature flags for gradual rollout
- Comprehensive test coverage before migration
- Keep old code until new is proven

### Risk 2: Performance Regression
**Mitigation**:
- Benchmark before/after each service
- Profile memory usage
- Optimize inter-service communication

### Risk 3: Circular Dependencies
**Mitigation**:
- Use Protocol interfaces
- Dependency injection
- Clear service boundaries

### Risk 4: State Synchronization
**Mitigation**:
- Central state manager
- Event-driven updates
- Immutable state objects

## Success Metrics

### Code Quality
| Metric | Current | Target |
|--------|---------|--------|
| Largest service (lines) | 1,152 | <400 |
| Most methods per class | 47 | <15 |
| Cyclomatic complexity | 21 | <10 |
| Test coverage | ~70% | >85% |

### Performance
| Operation | Current | Target |
|-----------|---------|--------|
| Select all (10k points) | Unknown | <100ms |
| Undo operation | Unknown | <50ms |
| File load (1MB JSON) | Unknown | <500ms |

### Architecture
| Metric | Current | Target |
|--------|---------|--------|
| Number of services | 4 | 10 |
| God objects | 2 | 0 |
| Protocol violations | Many | 0 |
| Circular dependencies | Unknown | 0 |

## Daily Checklist

### Morning
- [ ] Review previous day's work
- [ ] Check test results
- [ ] Plan day's tasks
- [ ] Update progress tracking

### During Development
- [ ] Write tests first (TDD)
- [ ] Keep services under 400 lines
- [ ] Document public APIs
- [ ] Check for circular dependencies

### Evening
- [ ] Run full test suite
- [ ] Check performance benchmarks
- [ ] Commit working code
- [ ] Update progress report

## Deliverables

### Week 1 Deliverables
1. ✅ 4 new services from InteractionService
2. ✅ All event handling working
3. ✅ Selection operations functional
4. ✅ History/undo working
5. ✅ 50+ new unit tests

### Week 2 Deliverables
1. ✅ 4 new services from DataService
2. ✅ File I/O operations working
3. ✅ Image sequence handling functional
4. ✅ Cache system operational
5. ✅ Full integration tests passing
6. ✅ Migration guide complete
7. ✅ Performance benchmarks documented

## Rollback Plan

If critical issues arise:

1. **Hour 1**: Attempt hotfix
2. **Hour 2-4**: Debug with logging
3. **Hour 4+**: Revert to previous version

```python
# Quick rollback in services/__init__.py
USE_NEW_SERVICES = False  # Revert to God objects
```

## Next Steps After Sprint 8

### Sprint 9 Preview: Type Safety
- Fix 769 type errors
- Add Protocol types to all services
- Remove generic type: ignore
- Modern type syntax (X | None)

### Sprint 10 Preview: Performance
- Implement viewport culling
- Cache painter paths
- Optimize render pipeline
- Add performance monitoring

## Conclusion

This 2-week sprint will transform the unmaintainable God objects into a clean, SOLID architecture with 10 focused services. Each service will have a single responsibility, clean interfaces, and comprehensive tests.

The key to success is:
1. **Gradual migration** with feature flags
2. **Comprehensive testing** at each step
3. **Performance monitoring** to prevent regression
4. **Clear service boundaries** with Protocols

By the end of Sprint 8, the codebase will be significantly more maintainable, testable, and ready for future enhancements.

---

*Sprint Start Date: [TBD]*
*Sprint End Date: [TBD + 2 weeks]*
*Risk Level: High (architectural change)*
*Rollback Time: < 1 minute*
