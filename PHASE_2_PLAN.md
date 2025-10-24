# Phase 2: Controller Consolidation - Detailed Plan

**Date Created**: 2025-10-24
**Estimated Time**: 12 hours
**Current Controllers**: 17 files (5,492 lines)
**Target Controllers**: 10-12 files (~4,800 lines)
**Expected Savings**: ~700 lines

---

## Executive Summary

Phase 2 consolidates 17 controllers into 10-12 focused controllers by merging closely related responsibilities. This reduces MainWindow complexity, improves testability, and establishes clearer separation of concerns.

**Key Objectives:**
1. Consolidate 4 tracking controllers → 1-2 controllers
2. Merge view management and camera controllers
3. Extract SessionManager from MainWindow (properly integrate existing module)
4. Verify zero regressions with 2,943 test suite

---

## Current State Analysis

### Controller Inventory (17 files, 5,492 lines)

**Tracking Controllers (4 files, 1,282 lines):**
- `tracking_data_controller.py` (398 lines) - Data loading, storage
- `tracking_display_controller.py` (450 lines) - UI display updates
- `tracking_selection_controller.py` (217 lines) - Selection sync
- `base_tracking_controller.py` (36 lines) - Base class
- **Issue**: Tightly coupled, share state, high coordination overhead

**View Controllers (2 files, 1,038 lines):**
- `view_management_controller.py` (476 lines) - Options, images, backgrounds
- `view_camera_controller.py` (562 lines) - Zoom, pan, fit, center
- **Issue**: Overlapping responsibilities (both handle view state)

**Action/UI Controllers (3 files, 1,207 lines):**
- `action_handler_controller.py` (369 lines) - Menu/toolbar actions
- `ui_initialization_controller.py` (535 lines) - UI setup
- `signal_connection_manager.py` (303 lines) - Signal wiring
- **Status**: Well-separated, keep as-is

**Specialized Controllers (5 files, 1,406 lines):**
- `timeline_controller.py` (556 lines) - Timeline/playback
- `multi_point_tracking_controller.py` (307 lines) - Multi-point operations
- `point_editor_controller.py` (304 lines) - Point editing
- `frame_change_coordinator.py` (239 lines) - Frame change coordination
- **Status**: Focused responsibilities, keep as-is

**CurveView Subcontrollers (3 files, 699 lines):**
- `curve_data_facade.py` (345 lines)
- `render_cache_controller.py` (218 lines)
- `state_sync_controller.py` (136 lines)
- **Status**: Well-encapsulated, keep as-is

**SessionManager:**
- Module exists: `ui/session_manager.py`
- Status: NOT integrated into MainWindow (property returns None)
- Action needed: Properly instantiate and use

---

## Consolidation Strategy

### Task 1: Consolidate Tracking Controllers (4 → 1-2)

**Target**: Merge 4 tracking controllers into 1-2 focused controllers

**Option A: Single TrackingController (RECOMMENDED)**
```
TrackingController (800-900 lines)
├── Data Management (from TrackingDataController)
│   ├── Load tracking data
│   ├── Manage curve storage
│   ├── Handle deletions/renames
│   └── Generate unique names
├── Display Management (from TrackingDisplayController)
│   ├── Update tracking panel
│   ├── Handle visibility/colors
│   └── Manage frame range updates
└── Selection Management (from TrackingSelectionController)
    ├── Sync selections
    └── Auto-select at frame
```

**Option B: Two Controllers (Data + UI)**
```
TrackingDataController (450 lines) - Data operations only
TrackingUIController (450 lines) - Display + Selection
```

**Recommendation**: Option A (single controller) for tightly coupled operations.

#### Checklist: Consolidate Tracking Controllers

- [ ] **1.1 Analysis Phase**
  - [ ] Read all 4 tracking controller files in detail
  - [ ] Map method dependencies between controllers
  - [ ] Identify shared state and signals
  - [ ] Document public API surface (methods used by MainWindow)
  - [ ] Check for circular dependencies

- [ ] **1.2 Design Merged Controller**
  - [ ] Create `TrackingController` class skeleton
  - [ ] Design internal organization (data / display / selection sections)
  - [ ] Plan signal consolidation (merge duplicate signals)
  - [ ] Define clear method groupings with comments
  - [ ] Document protocol compatibility (use focused protocols from Phase 1)

- [ ] **1.3 Merge Implementation**
  - [ ] Copy TrackingDataController methods (data section)
  - [ ] Copy TrackingDisplayController methods (display section)
  - [ ] Copy TrackingSelectionController methods (selection section)
  - [ ] Merge `__init__` methods (combine initialization)
  - [ ] Consolidate duplicate signals
  - [ ] Remove base_tracking_controller.py (no longer needed)

- [ ] **1.4 Update MainWindow Integration**
  - [ ] Update MainWindow imports
  - [ ] Replace 3 controller properties with single `tracking_controller`
  - [ ] Update signal connections (point to new controller)
  - [ ] Update method calls (adjust for new API)
  - [ ] Remove old controller instantiations

- [ ] **1.5 Update Tests**
  - [ ] Update test imports
  - [ ] Fix test mocks (single controller instead of 3)
  - [ ] Run tracking-related tests: `pytest tests/ -k tracking -v`
  - [ ] Verify no regressions

- [ ] **1.6 Documentation & Cleanup**
  - [ ] Update CLAUDE.md (document new TrackingController)
  - [ ] Delete old controller files (4 files)
  - [ ] Run full test suite: `pytest tests/ -q`
  - [ ] Commit: "refactor: Consolidate 4 tracking controllers into TrackingController"

**Expected Savings**: 1,282 lines → ~850 lines = **432 lines saved**

---

### Task 2: Merge View Controllers (2 → 1)

**Target**: Combine ViewManagementController + ViewCameraController

```
ViewportController (900-1000 lines)
├── Camera Operations (from ViewCameraController)
│   ├── Zoom (factor, wheel handling)
│   ├── Pan (offsets, dragging)
│   ├── Fit operations (image, curve, reset)
│   ├── Center operations (point, selection, frame)
│   └── Transform management (cache, invalidation)
├── View Options (from ViewManagementController)
│   ├── Point size, line width
│   ├── Show grid, tooltips
│   └── View options get/set
└── Background Images (from ViewManagementController)
    ├── Image loading (disk, cache)
    ├── Image sequence management
    ├── Frame range updates
    └── Cache management (LRU)
```

**Rationale**: Both controllers manage view state and are tightly coupled.

#### Checklist: Merge View Controllers

- [ ] **2.1 Analysis Phase**
  - [ ] Read ViewCameraController in detail
  - [ ] Read ViewManagementController in detail
  - [ ] Identify method dependencies between controllers
  - [ ] Check MainWindow usage patterns
  - [ ] Document public API surface

- [ ] **2.2 Design Merged Controller**
  - [ ] Create `ViewportController` class skeleton
  - [ ] Organize into 3 sections (camera / options / images)
  - [ ] Plan state consolidation (zoom, pan, options)
  - [ ] Design clean section boundaries with comments
  - [ ] Consider focused protocols for dependencies

- [ ] **2.3 Merge Implementation**
  - [ ] Copy ViewCameraController methods (camera section)
  - [ ] Copy ViewManagementController methods (options + images sections)
  - [ ] Merge `__init__` methods
  - [ ] Consolidate overlapping functionality
  - [ ] Preserve all public API methods

- [ ] **2.4 Update MainWindow Integration**
  - [ ] Update MainWindow imports
  - [ ] Replace 2 controller properties with `viewport_controller`
  - [ ] Update method calls throughout MainWindow
  - [ ] Verify signal connections

- [ ] **2.5 Update Tests**
  - [ ] Update test imports and mocks
  - [ ] Run view-related tests: `pytest tests/ -k "view or camera or viewport" -v`
  - [ ] Verify no regressions

- [ ] **2.6 Documentation & Cleanup**
  - [ ] Update CLAUDE.md (document ViewportController)
  - [ ] Delete old controller files (2 files)
  - [ ] Run full test suite: `pytest tests/ -q`
  - [ ] Commit: "refactor: Merge ViewManagementController and ViewCameraController into ViewportController"

**Expected Savings**: 1,038 lines → ~950 lines = **88 lines saved**

---

### Task 3: Extract SessionManager (Integration)

**Current State**:
- SessionManager module exists in `ui/session_manager.py`
- MainWindow has `session_manager` property that returns `None`
- No actual integration or usage

**Target**: Properly integrate SessionManager into MainWindow

#### Checklist: Integrate SessionManager

- [ ] **3.1 Analysis Phase**
  - [ ] Read existing SessionManager class (ui/session_manager.py)
  - [ ] Identify all session-related code in MainWindow
  - [ ] List file loading/saving methods in MainWindow
  - [ ] Check for auto_load_data parameter usage
  - [ ] Document current session state management

- [ ] **3.2 SessionManager Instantiation**
  - [ ] Initialize `_session_manager` in MainWindow.__init__
  - [ ] Pass project_root parameter (if needed)
  - [ ] Update `session_manager` property to return instance
  - [ ] Verify SessionManager creates session/ directory

- [ ] **3.3 Integrate Session Loading**
  - [ ] Add `load_last_session()` call in MainWindow.__init__ (if auto_load_data=True)
  - [ ] Implement session loading for:
    - [ ] Last opened file path
    - [ ] View state (zoom, pan)
    - [ ] Frame position
    - [ ] Window geometry
    - [ ] View options (grid, background, etc.)

- [ ] **3.4 Integrate Session Saving**
  - [ ] Call `save_session()` in `closeEvent()`
  - [ ] Call `save_session()` after successful file load
  - [ ] Save current state:
    - [ ] Active file path
    - [ ] View state (from ViewportController)
    - [ ] Current frame
    - [ ] Window geometry
    - [ ] View options

- [ ] **3.5 Add Session Management Actions**
  - [ ] Add "Clear Session" menu action (optional)
  - [ ] Add session error handling (corrupted JSON)
  - [ ] Log session save/load operations

- [ ] **3.6 Testing**
  - [ ] Test session save on application close
  - [ ] Test session restore on application start
  - [ ] Test with missing session file
  - [ ] Test with corrupted session file
  - [ ] Test relative path handling (files inside project)
  - [ ] Test absolute path handling (files outside project)

- [ ] **3.7 Documentation & Cleanup**
  - [ ] Update CLAUDE.md (document SessionManager integration)
  - [ ] Add session management to User Guide (if exists)
  - [ ] Commit: "feat: Integrate SessionManager for automatic session persistence"

**Expected Impact**: Improved user experience (automatic restore), no line savings (already implemented module)

---

### Task 4: Optional - Refine Remaining Controllers

**Consider if time permits (not critical):**

#### 4.1 SignalConnectionManager Review
- [ ] Check if signal connections could be moved closer to components
- [ ] Consider if this controller is still needed after consolidation
- [ ] Document rationale for keeping/removing

#### 4.2 UIInitializationController Review
- [ ] Check if initialization logic could be in MainWindow.__init__
- [ ] Assess benefits of separate controller vs inline setup
- [ ] Document decision

#### 4.3 ActionHandlerController Review
- [ ] Verify clear separation from business logic
- [ ] Check if any actions belong in other controllers
- [ ] Confirm controller focuses only on action dispatching

---

## Testing Strategy

### Test Categories

**Unit Tests:**
- [ ] Test merged controller methods individually
- [ ] Test signal emissions
- [ ] Test state management
- [ ] Mock dependencies using Phase 1 protocols

**Integration Tests:**
- [ ] Test MainWindow with new controllers
- [ ] Test controller interactions
- [ ] Test file loading workflow
- [ ] Test session persistence

**Regression Tests:**
- [ ] Run full test suite after each consolidation: `pytest tests/ -q`
- [ ] Target: 2,943/2,956 tests passing (maintain current pass rate)
- [ ] Investigate any new failures immediately

**Manual Testing:**
- [ ] Load tracking data → verify display
- [ ] Multi-curve operations → verify all curves update
- [ ] View operations (zoom, pan, fit) → verify smooth operation
- [ ] Session save/restore → verify state persistence
- [ ] Close and reopen app → verify last file loads

---

## Rollback Strategy

### If Issues Arise:

1. **Each task is atomic** - Can revert individual consolidations
2. **Git commits are focused** - One controller consolidation per commit
3. **Tests run after each change** - Catch regressions early

### Rollback Commands:
```bash
# Revert last commit
git revert HEAD

# Revert specific consolidation
git log --oneline | grep "Consolidate"
git revert <commit-hash>

# Nuclear option - reset to Phase 1 complete
git reset --hard <phase1-complete-commit>
```

---

## Success Metrics

### Quantitative:
- [ ] Controllers: 17 → 10-12 files
- [ ] Lines of code: 5,492 → ~4,800 lines (~700 lines saved)
- [ ] Test pass rate: Maintain 99.6% (2,943/2,956)
- [ ] Type errors: No increase from current baseline

### Qualitative:
- [ ] MainWindow: Clearer controller responsibilities
- [ ] Tests: Simpler mocks (fewer controllers to mock)
- [ ] Code navigation: Easier to find related functionality
- [ ] Session management: Automatic file/state restoration works

---

## Timeline

**Week 1 (6 hours):**
- Task 1: Consolidate tracking controllers (4 hours)
- Task 2: Merge view controllers (2 hours)

**Week 2 (6 hours):**
- Task 3: Integrate SessionManager (3 hours)
- Task 4: Optional refinements (2 hours)
- Final testing & documentation (1 hour)

**Total: 12 hours**

---

## Dependencies

**Prerequisites:**
- Phase 1 complete ✅
- Test suite passing (2,943/2,956) ✅
- Type checking baseline established ✅

**Required for Phase 3:**
- Phase 2 complete
- Controller consolidation proven successful
- Testing infrastructure validated

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking MainWindow integration | High | Medium | Test after each consolidation, atomic commits |
| Test failures due to mocking changes | Medium | High | Update mocks incrementally, use protocols |
| Signal connection errors | Medium | Medium | Document all signal flows, test thoroughly |
| Session loading breaks existing data | High | Low | Graceful fallback, validate session JSON |
| Merge conflicts in large files | Low | Low | Work sequentially, commit frequently |

---

## Phase 2 Complete Checklist

### Code Changes:
- [ ] Task 1: Tracking controllers consolidated (4 → 1-2)
- [ ] Task 2: View controllers merged (2 → 1)
- [ ] Task 3: SessionManager integrated
- [ ] Task 4: Optional refinements (if time permits)

### Testing:
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Full test suite: 2,943+ tests passing
- [ ] Manual smoke test completed

### Documentation:
- [ ] CLAUDE.md updated with new controllers
- [ ] PHASE_2_COMPLETE.md created (summary document)
- [ ] Controller inventory updated
- [ ] Git commits are clean and focused

### Quality:
- [ ] No new type errors introduced
- [ ] No new linting warnings
- [ ] Code follows existing patterns
- [ ] Protocols used where appropriate (Phase 1 principles)

---

## Next Steps After Phase 2

**Phase 3 (Optional - 16 hours):**
- Split large services (InteractionService, DataService)
- Only if testability is blocking further development
- Requires Phase 2 consolidation experience first

**Alternative Path:**
- Start using Phase 1 protocols in new code
- Gradually migrate existing code to use protocols
- Focus on feature development with cleaner architecture

---

**Ready to proceed?**

Would you like to:
1. Start with Task 1 (Tracking Controller Consolidation)
2. Review/modify the plan first
3. Focus on a specific task
4. Discuss alternative consolidation strategies
