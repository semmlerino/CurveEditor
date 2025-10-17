# PLAN TAU Phase 4: StateManager Setter Migrations

**Status**: Implementation Planning
**Created**: 2025-10-17
**Target**: Complete StateManager setter migration to ApplicationState

## Executive Summary

Phase 4 completes the StateManager simplification (PLAN TAU) by migrating all remaining setter callsites from StateManager properties to ApplicationState direct methods. This eliminates the deprecated synthetic image_files pattern for `total_frames` and centralizes all frame management in ApplicationState.

**Total Setters to Migrate**: **115 instances** across **36 files**
- **current_frame**: 84 instances (73%)
- **total_frames**: 31 instances (27%)

## Current Architecture Status

### Phase 3 Completed
- ✅ StateManager getters migrated (all data access via ApplicationState)
- ✅ ApplicationState single source of truth established
- ✅ StateManager now delegates all data reads

### Phase 4 Tasks
- ⏳ Migrate `current_frame` setters (84 instances)
- ⏳ Migrate `total_frames` setters (31 instances)
- ⏳ Resolve total_frames replacement strategy
- ⏳ Remove deprecated StateManager setters

## Detailed Inventory

### By Setter Type

#### 1. `current_frame` Setter (84 total instances)

**Pattern**:
```python
# Before (deprecated)
state_manager.current_frame = frame

# After (ApplicationState direct)
get_application_state().set_frame(frame)
```

**Files with current_frame setters** (14 files):

| File | Count | Category |
|------|-------|----------|
| `tests/test_state_manager.py` | 28 | Legacy tests |
| `tests/test_keyframe_navigation.py` | 12 | Navigation tests |
| `tests/stores/test_application_state_phase0a.py` | 8 | State tests |
| `tests/test_frame_highlight.py` | 7 | Display tests |
| `tests/test_event_filter_navigation.py` | 7 | Event handling tests |
| `tests/test_frame_change_coordinator.py` | 5 | Coordinator tests |
| `tests/test_tracking_point_status_commands.py` | 4 | Tracking tests |
| `tests/test_unified_curve_rendering.py` | 3 | Rendering tests |
| `tests/test_multi_point_selection.py` | 2 | Selection tests |
| `tests/test_keyboard_shortcuts_enhanced.py` | 2 | Input tests |
| `tests/test_global_shortcuts.py` | 2 | Keyboard tests |
| `stores/frame_store.py` | 2 | Production code |
| `tests/test_timeline_focus_behavior.py` | 1 | Focus tests |
| `tests/test_data_service_synchronization.py` | 1 | Sync tests |

**Total**: 84 instances (73% of all setters)

---

#### 2. `total_frames` Setter (31 total instances)

**Current Pattern** (Deprecated):
```python
# Before (creates synthetic image_files list)
state_manager.total_frames = count

# StateManager implementation (line 424-460):
# Creates synthetic files: [f"<synthetic_frame_{i+1}>" for i in range(count)]
# Then calls: self._app_state.set_image_files(synthetic_files)
```

**Migration Strategy** (TBD - Architecture Decision Needed):

Three options exist, pending architecture agent guidance:

**Option A: Replace with set_image_files()**
```python
# Best for: Image sequence workflows
# Replaces synthetic pattern with explicit file list
get_application_state().set_image_files([f"frame_{i:04d}.png" for i in range(count)])

# Pros:
#   - Explicit file paths (correct semantics)
#   - Aligns with actual image loading
#   - No synthetic empty files
# Cons:
#   - Requires knowing file naming convention
#   - May not work for curve-only workflows
```

**Option B: Add state.set_frame_count(n) method** (Recommended)
```python
# Best for: Curve-only workflows (no images)
# Direct setter, semantically clear
get_application_state().set_frame_count(count)

# Pros:
#   - Direct and clear API
#   - Works for tracking data without images
#   - Maintains current semantics
# Cons:
#   - Adds new method to ApplicationState
#   - Breaks "derived from image_files" principle
```

**Option C: Remove and require explicit image loading**
```python
# Best for: Long-term consistency
# No setter at all - force explicit image sequence loading
# Only way to set total_frames is via set_image_files()

# Pros:
#   - Enforces correct data flow
#   - Single source of truth
#   - No semantic confusion
# Cons:
#   - Breaking change for tests
#   - Requires image files for any frame range
#   - Doesn't work for synthetic/curve-only data
```

**Files with total_frames setters** (13 files):

| File | Count | Category | Context |
|------|-------|----------|---------|
| `tests/test_state_manager.py` | 16 | Legacy tests | Tests the setter itself |
| `ui/controllers/tracking_display_controller.py` | 2 | Production | Tracking display setup |
| `tests/test_frame_change_coordinator.py` | 3 | Coordinator tests | Testing frame bounds |
| `ui/timeline_tabs.py` | 1 | Production | Timeline range setting |
| `ui/controllers/timeline_controller.py` | 1 | Production | Timeline range setting |
| `tests/test_timeline_tabs.py` | 1 | Timeline tests | Timeline initialization |
| `tests/test_timeline_scrubbing.py` | 1 | Timeline tests | Scrubbing setup |
| `tests/test_timeline_integration.py` | 1 | Timeline tests | Timeline integration |
| `tests/test_timeline_functionality.py` | 1 | Timeline tests | Timeline functionality |
| `tests/test_timeline_focus_behavior.py` | 1 | Timeline tests | Focus behavior |
| `tests/test_frame_highlight.py` | 1 | Display tests | Frame highlighting |
| `tests/test_file_operations.py` | 1 | File tests | File operations |
| `stores/frame_store.py` | 1 | Production | Frame synchronization |

**Total**: 31 instances (27% of all setters)

---

## Production Code vs Test Code

### Production Code (Source Files)

**critical_path** = 5 instances (must migrate first):

1. `ui/timeline_tabs.py:620` - TimelineTabWidget.set_frame_range()
   - Sets total_frames when frame range updates
   - Called during timeline initialization and curve data updates

2. `ui/controllers/timeline_controller.py:499` - TimelineController.set_frame_range()
   - Sets total_frames when playback bounds update
   - Called during playback setup and curve changes

3. `stores/frame_store.py:106` - FrameStore.set_current_frame()
   - Uses current_frame setter to delegate to StateManager
   - Single instance - direct replacement

4. `stores/frame_store.py:195` - FrameStore._update_frame_range()
   - Sets total_frames when frame range changes
   - Called when curve data synchronization occurs

5. `ui/controllers/tracking_display_controller.py:X` - (2 instances)
   - Sets total_frames during tracking display setup
   - Context: Multi-curve tracking workflows

### Test Code (110 instances)

Can be migrated in bulk with automated search-and-replace:
- Tests are isolated and have no side effects on production behavior
- Bulk replacement is safe once pattern is established
- Tests validate same logic as production code

---

## Migration Implementation Plan

### Phase 4.1: Architecture Decision (0.5 day)

**Blocking**: Resolve `total_frames` replacement strategy
- [ ] Architecture agent reviews three options above
- [ ] Decision: Which option is correct for CurveEditor architecture?
- [ ] Document rationale in CLAUDE.md

**Options to resolve**:
1. Is synthetic image_files pattern intentional or technical debt?
2. Should total_frames be settable without image files?
3. What's the proper API for frame-only data (no images)?

---

### Phase 4.2: Production Code Migration (1.0 day)

**Step 1**: Update FrameStore (0.2 day)
- [ ] Replace 2 `current_frame` setters in `frame_store.py`
- [ ] Replace 1 `total_frames` setter in `frame_store.py`
- [ ] Pattern:
  ```python
  # Before
  self._state_manager.current_frame = frame
  self._state_manager.total_frames = max_frame

  # After
  get_application_state().set_frame(frame)
  get_application_state().set_image_files([...])  # or set_frame_count()
  ```

**Step 2**: Update TimelineController (0.3 day)
- [ ] Replace 1 `total_frames` setter in `timeline_controller.py:499`
- [ ] Method: `TimelineController.set_frame_range()`
- [ ] Logic: Keep existing frame range setup, replace setter only

**Step 3**: Update TimelineTabWidget (0.3 day)
- [ ] Replace 1 `total_frames` setter in `timeline_tabs.py:620`
- [ ] Method: `TimelineTabWidget.set_frame_range()`
- [ ] Logic: Keep existing frame range setup, replace setter only

**Step 4**: Update TrackingDisplayController (0.2 day)
- [ ] Replace 2 `total_frames` setters in `tracking_display_controller.py`
- [ ] Context: Multi-curve tracking display setup
- [ ] Pattern: Same as TimelineController

**Validation**:
- [ ] Run unit tests: `uv run pytest tests/ -k "timeline or frame_store or tracking"`
- [ ] Manual test: Load project, verify frame range works
- [ ] Verify no regressions in playback, scrubbing, frame navigation

---

### Phase 4.3: Test Code Migration (1.5 days)

**Step 1**: Automated Migration Script (0.5 day)
- [ ] Create migration script for bulk replacement
- [ ] Pattern:
  ```python
  # Regex pattern
  OLD: state_manager\.current_frame\s*=\s*(\d+|[a-z_]+)
  NEW: get_application_state().set_frame($1)

  OLD: state_manager\.total_frames\s*=\s*(\d+|[a-z_]+)
  NEW: get_application_state().set_image_files([...])  # Based on architecture decision
  ```
- [ ] Safety: Apply with search-verify-replace workflow
- [ ] Test coverage: Ensure all test patterns are handled

**Step 2**: Manual Migration (1.0 day)
- [ ] Review bulk-replaced tests for edge cases
- [ ] Fix any tests that need special handling:
  - Tests that validate StateManager behavior
  - Tests with complex fixture setups
  - Tests that check current_frame/total_frames bounds

**Tests by category**:

| Category | File | Count | Migration Difficulty |
|----------|------|-------|---------------------|
| Legacy tests | test_state_manager.py | 28 | HIGH - validates setter behavior |
| Navigation | test_keyframe_navigation.py | 12 | LOW - standard setup |
| State tests | test_application_state_phase0a.py | 8 | MEDIUM - tests state invariants |
| Display | test_frame_highlight.py | 7 | LOW - standard setup |
| Events | test_event_filter_navigation.py | 7 | LOW - standard setup |
| Coordinator | test_frame_change_coordinator.py | 5 | MEDIUM - timing-sensitive |
| Tracking | test_tracking_point_status_commands.py | 4 | LOW - standard setup |
| Rendering | test_unified_curve_rendering.py | 3 | LOW - standard setup |
| Selection | test_multi_point_selection.py | 2 | LOW - standard setup |
| Keyboard | test_keyboard_shortcuts_enhanced.py + test_global_shortcuts.py | 4 | LOW - standard setup |
| Timeline | test_timeline_focus_behavior.py + test_timeline_tabs.py + test_timeline_scrubbing.py + test_timeline_integration.py + test_timeline_functionality.py | 5 | MEDIUM - timeline-specific |
| Sync | test_data_service_synchronization.py | 1 | MEDIUM - synchronization |
| Files | test_file_operations.py | 1 | MEDIUM - file I/O |

**High-Risk Tests**:
- `test_state_manager.py` (28 instances) - Tests that validate StateManager behavior directly
  - Action: Rewrite as ApplicationState tests
  - Verify: Setter bounds checking, clamping behavior preserved
  - New tests: Ensure ApplicationState methods work correctly

---

### Phase 4.4: Deprecation & Cleanup (0.5 day)

**Step 1**: Mark setters as removed (0.2 day)
- [ ] Remove `@current_frame.setter` from StateManager
  - Test any external code that was using it
  - Verify all migrations complete first
- [ ] Remove `@total_frames.setter` from StateManager
  - Test any external code that was using it
  - Verify all migrations complete first

**Step 2**: Update CLAUDE.md documentation (0.3 day)
- [ ] Document new API: `get_application_state().set_frame(frame)`
- [ ] Document new API for total_frames (based on architecture decision)
- [ ] Mark StateManager setters as removed (Phase 4)
- [ ] Update migration pattern in development guide

---

## Risk Assessment & Mitigations

### Risks

1. **total_frames semantics** (HIGH)
   - Risk: Wrong replacement strategy breaks frame clamping
   - Mitigation: Architecture decision before implementation
   - Test: Bounds checking tests verify clamping still works

2. **Test-production divergence** (MEDIUM)
   - Risk: Tests migrate but production code doesn't
   - Mitigation: Check both locations during migration
   - Test: Run full test suite after each production migration

3. **StateManager signal forwarding** (MEDIUM)
   - Risk: Removing setters breaks signal emission
   - Mitigation: Verify ApplicationState emits same signals
   - Test: Signal tests confirm frame_changed and total_frames_changed still work

4. **Frame clamping behavior** (MEDIUM)
   - Risk: Current frame clamping logic changes
   - Mitigation: ApplicationState.set_frame() already implements clamping
   - Test: Test minimum=1, maximum=total_frames clamping

5. **Cascading failures in edge cases** (LOW)
   - Risk: Complex test fixtures with unusual patterns
   - Mitigation: Review high-risk test categories before bulk migration
   - Test: Run tests incrementally after each file migration

### Testing Strategy

**Pre-Migration**:
- [ ] Run full test suite: `uv run pytest tests/`
- [ ] Baseline: All tests passing

**Per-File Migration**:
- [ ] Migrate production file
- [ ] Run related test suite: `uv run pytest tests/ -k "<related_tests>"`
- [ ] Verify: No new failures introduced

**Post-Migration**:
- [ ] Full test suite again: `uv run pytest tests/`
- [ ] Type checking: `./bpr`
- [ ] Manual smoke test: Load project, verify key workflows

---

## Success Criteria

Phase 4 is complete when:

1. ✅ All 84 `current_frame` setters replaced with `get_application_state().set_frame()`
2. ✅ All 31 `total_frames` setters replaced with agreed-upon strategy
3. ✅ StateManager `@current_frame.setter` removed
4. ✅ StateManager `@total_frames.setter` removed
5. ✅ All 36 affected files have zero deprecated setter usage
6. ✅ Full test suite passing: `uv run pytest tests/`
7. ✅ Type checking passing: `./bpr --errors-only`
8. ✅ CLAUDE.md updated with new API documentation
9. ✅ No remaining TODO comments for Phase 4

---

## Implementation Timeline

**Total Effort**: ~3.5 days

| Phase | Task | Duration | Critical Path |
|-------|------|----------|---|
| 4.1 | Architecture Decision | 0.5 days | 🔴 BLOCKING |
| 4.2 | Production Code Migration | 1.0 day | ✅ After 4.1 |
| 4.3 | Test Code Migration | 1.5 days | ✅ Parallel with 4.2 |
| 4.4 | Deprecation & Cleanup | 0.5 days | ✅ After 4.2, 4.3 |
| — | **Total** | **~3.5 days** | — |

---

## Files Requiring Changes

### Production Files (5 setters)
1. ✅ `stores/frame_store.py` (2 current_frame + 1 total_frames)
2. ✅ `ui/timeline_tabs.py` (1 total_frames)
3. ✅ `ui/controllers/timeline_controller.py` (1 total_frames)
4. ✅ `ui/controllers/tracking_display_controller.py` (2 total_frames)
5. ✅ `ui/state_manager.py` (REMOVE setters)

### Test Files (110 setters across 30 files)

**High-Priority Tests** (High-risk, review first):
- `tests/test_state_manager.py` (28 instances)
- `tests/stores/test_application_state_phase0a.py` (8 instances)
- `tests/test_frame_change_coordinator.py` (5 instances)

**Standard Migration Tests**:
- `tests/test_keyframe_navigation.py` (12 instances)
- `tests/test_frame_highlight.py` (7 instances)
- `tests/test_event_filter_navigation.py` (7 instances)
- `tests/test_tracking_point_status_commands.py` (4 instances)
- `tests/test_unified_curve_rendering.py` (3 instances)
- `tests/test_multi_point_selection.py` (2 instances)
- `tests/test_keyboard_shortcuts_enhanced.py` (2 instances)
- `tests/test_global_shortcuts.py` (2 instances)
- `tests/test_timeline_focus_behavior.py` (1 instance)
- `tests/test_data_service_synchronization.py` (1 instance)
- `tests/test_timeline_tabs.py` (1 instance)
- `tests/test_timeline_scrubbing.py` (1 instance)
- `tests/test_timeline_integration.py` (1 instance)
- `tests/test_timeline_functionality.py` (1 instance)
- `tests/test_file_operations.py` (1 instance)

---

## Migration Patterns Reference

### Pattern 1: Simple current_frame
```python
# Before
state_manager.current_frame = 5

# After
get_application_state().set_frame(5)
```

### Pattern 2: current_frame with variable
```python
# Before
state_manager.current_frame = frame

# After
get_application_state().set_frame(frame)
```

### Pattern 3: total_frames with count
```python
# Before (DEPRECATED - creates synthetic files)
state_manager.total_frames = 100

# After (PENDING ARCHITECTURE DECISION)
# Option A: Use set_image_files()
get_application_state().set_image_files([f"frame_{i:04d}.png" for i in range(100)])

# Option B: Use set_frame_count() (if implemented)
get_application_state().set_frame_count(100)

# Option C: Enforce set_image_files() only (remove setter entirely)
```

### Pattern 4: Accessing via window reference
```python
# Before
window.state_manager.current_frame = 10

# After
get_application_state().set_frame(10)
```

---

## Next Steps

1. **Decision Required**: Architecture team to review total_frames options above
2. **Pre-migration**: Run baseline test suite
3. **Phase 4.2**: Migrate production code (following decision)
4. **Phase 4.3**: Migrate test code with bulk replacement script
5. **Phase 4.4**: Remove deprecated setters and update documentation

---

**Document Status**: Ready for Implementation
**Last Updated**: 2025-10-17
**Next Review**: After Phase 4.1 architecture decision
