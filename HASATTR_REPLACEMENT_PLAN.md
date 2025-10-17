# hasattr() Replacement Plan

**Date**: 2025-10-13
**Status**: Planning Phase
**Estimated Effort**: 1-2 hours
**Priority**: 🟡 MEDIUM

---

## Executive Summary

Analysis of the codebase reveals **59 hasattr() usages** across **16 production files**. However, approximately **~25-30 are type safety violations** that should be replaced with None checks, while **~30 are legitimate** uses (cleanup in `__del__`, protocol checks, duck typing).

**Key Findings**:
- ✅ **Legitimate Uses (~30)**: Cleanup in `__del__()` methods, protocol/duck-type checks
- ⚠️ **Type Safety Violations (~25-30)**: Checking for attributes that are always defined
- 🎯 **High-Value Targets**: Commands and session management (critical paths)

**Strategy**: **Selective replacement** focusing on high-impact type safety violations in critical paths, leaving legitimate uses intact.

---

## Analysis Results

### Total hasattr() Usage

```bash
# Production code (core/, services/, ui/)
59 usages across 16 files

# Top offenders:
12 - ui/image_sequence_browser.py
 9 - ui/controllers/timeline_controller.py (ALL legitimate - __del__ cleanup)
 9 - core/commands/insert_track_command.py (ALL violations)
 5 - ui/session_manager.py (ALL violations)
 5 - ui/controllers/signal_connection_manager.py (likely __del__ cleanup)
 4 - services/interaction_service.py (protocol checks - legitimate)
```

---

## Categorization

### Category A: TYPE SAFETY VIOLATIONS (Replace with None checks)

**Estimated**: ~25-30 instances

#### High-Priority Files (Critical Paths):

1. **core/commands/insert_track_command.py** - 9 violations
   ```python
   # ❌ VIOLATIONS (lines 73, 367, 371, 379, 390, 394, 405, 437, 474)
   if hasattr(main_window, "multi_point_controller"):
   if hasattr(main_window, "active_timeline_point"):
   if hasattr(main_window, "update_timeline_tabs"):

   # ✅ SHOULD BE:
   if main_window.multi_point_controller is not None:
   if main_window.active_timeline_point is not None:
   if main_window.update_timeline_tabs is not None:
   ```
   **Impact**: Critical path - command execution
   **Type Safety**: Loses MainWindow attribute types

2. **ui/session_manager.py** - 5 violations
   ```python
   # ❌ VIOLATIONS (lines 318, 324, 340, 355, 372)
   if hasattr(main_window, "state_manager"):
   if hasattr(main_window, "file_load_worker"):
   if hasattr(main_window, "file_operations_manager"):

   # ✅ SHOULD BE:
   if main_window.state_manager is not None:
   if main_window.file_load_worker is not None:
   if main_window.file_operations_manager is not None:
   ```
   **Impact**: Critical path - session restoration at startup
   **Type Safety**: Loses MainWindow attribute types

3. **ui/image_sequence_browser.py** - 5 violations (state_manager checks only)
   ```python
   # ❌ VIOLATIONS (lines 483, 1051, 1400, 2173, 2226)
   if hasattr(parent_window, "state_manager"):

   # ✅ SHOULD BE:
   if parent_window.state_manager is not None:
   ```
   **Impact**: Medium - dialog initialization and state persistence
   **Type Safety**: Loses parent window type

   **Note**: Lines 485, 1053, 1402, 2181, 2234 check for state_manager **methods** - these are **legitimate protocol checks** (duck typing) and should be kept.

4. **ui/controllers/ui_initialization_controller.py** - 2 violations (lines 68, 81)
   ```python
   # ❌ VIOLATIONS
   if hasattr(self, "main_window") and hasattr(self.main_window, "ui"):
   if hasattr(self, "main_window") and hasattr(self.main_window, "tracking_panel"):

   # ✅ SHOULD BE:
   if self.main_window is not None and self.main_window.ui is not None:
   if self.main_window is not None and self.main_window.tracking_panel is not None:
   ```

5. **ui/controllers/point_editor_controller.py** - 2 violations (need verification)

6. **ui/controllers/multi_point_tracking_controller.py** - 2 violations (need verification)

7. **core/commands/shortcut_commands.py** - 3 violations (need verification)

8. **ui/** (various) - 5 violations across:
   - ui/curve_view_widget.py (1)
   - ui/tracking_points_panel.py (1)
   - ui/main_window_builder.py (1)
   - ui/global_event_filter.py (1)
   - ui/file_operations.py (1)

---

### Category B: LEGITIMATE USES (Keep as-is)

**Estimated**: ~30 instances

#### Legitimate Pattern #1: Cleanup in `__del__()` Methods

**ui/controllers/timeline_controller.py** - ALL 9 usages (lines 111-139)
```python
def __del__(self) -> None:
    """Cleanup controller resources."""
    try:
        if hasattr(self, "playback_timer"):  # ✅ CORRECT - __del__ cleanup
            _ = self.playback_timer.timeout.disconnect(self._on_playback_timer)
            self.playback_timer.stop()
    except (RuntimeError, AttributeError):
        pass
```

**Why Legitimate**: `__del__` may be called during partial initialization failures. Using `hasattr()` prevents AttributeError if object never fully initialized.

**Similar Files**:
- ui/controllers/signal_connection_manager.py (5 usages) - likely all __del__ cleanup
- ui/tracking_points_panel.py (1 usage, line 719) - cleanup check

#### Legitimate Pattern #2: Protocol/Duck-Type Checks

**services/interaction_service.py** - 4 usages
```python
# ✅ LEGITIMATE - Protocol check for QWidget interface
if undo_btn is not None and hasattr(undo_btn, "setEnabled"):
    undo_btn.setEnabled(can_undo_val)

# ✅ LEGITIMATE - Duck-type check for view update method
if hasattr(view, "update"):
    view.update()

# ✅ LEGITIMATE - Optional view attribute check
if hasattr(view, "pan_offset_y"):
    view.pan_offset_y = current_pan_y + adjusted_delta
```

**Why Legitimate**: Checking for methods/attributes on duck-typed objects where we don't have strong type guarantees.

**ui/image_sequence_browser.py** - 7 legitimate usages
```python
# ✅ LEGITIMATE - Duck-type checks for state_manager methods
if state_manager and hasattr(state_manager, "recent_directories"):
if hasattr(state_manager, "get_value"):
if hasattr(state_manager, "set_value"):
if hasattr(state_manager, "add_recent_directory"):

# ✅ LEGITIMATE - Initialization guard
if not hasattr(self, "tree_view"):
    return
```

#### Legitimate Pattern #3: Initialization Guards

**ui/widgets/card.py** (line 136)
```python
# ✅ LEGITIMATE - Defensive check for optional UI element
if hasattr(self, "_collapse_button"):
    self._collapse_button.setChecked(is_collapsed)
```

---

## CLAUDE.md Violation Analysis

From CLAUDE.md:
```python
# ❌ BAD - Type lost (documented anti-pattern)
if hasattr(self, 'main_window') and self.main_window:
    frame = self.main_window.current_frame

# ✅ GOOD - Type preserved (documented best practice)
if self.main_window is not None:
    frame = self.main_window.current_frame
```

**Violations**: The codebase has ~25-30 instances that violate this documented anti-pattern, primarily in:
- Command classes checking MainWindow attributes
- Session management checking MainWindow attributes
- Controllers checking parent attributes

**Impact**:
- Lost type information → IDE autocomplete broken
- Type checkers can't verify attribute access
- Increased risk of typos going undetected

---

## Prioritized Replacement Plan

### Phase 1: High-Impact Commands (30 minutes)

**File**: `core/commands/insert_track_command.py`
**Changes**: 9 hasattr() → None checks
**Impact**: Critical path - every insert track command execution
**Risk**: 🟢 LOW (straightforward replacement)

**Locations**:
- Line 73: `hasattr(main_window, "multi_point_controller")`
- Line 367: `hasattr(main_window, "multi_point_controller")`
- Line 371: `hasattr(main_window, "active_timeline_point")`
- Line 379: `hasattr(main_window, "update_timeline_tabs")`
- Line 390: `hasattr(main_window, "multi_point_controller")`
- Line 394: `hasattr(main_window, "active_timeline_point")`
- Line 405: `hasattr(main_window, "update_timeline_tabs")`
- Line 437: `hasattr(main_window, "multi_point_controller")`
- Line 474: `hasattr(main_window, "multi_point_controller")`

**Pattern**:
```python
# REPLACE:
if not hasattr(main_window, "multi_point_controller"):
    return False
main_window.multi_point_controller.update_tracking_panel()

# WITH:
if main_window.multi_point_controller is None:
    return False
main_window.multi_point_controller.update_tracking_panel()
```

---

### Phase 2: Session Management (20 minutes)

**File**: `ui/session_manager.py`
**Changes**: 5 hasattr() → None checks
**Impact**: Critical path - startup and session restoration
**Risk**: 🟢 LOW (straightforward replacement)

**Locations**:
- Line 318: `hasattr(main_window, "state_manager")`
- Line 324: `hasattr(main_window, "file_load_worker")`
- Line 340: `hasattr(main_window, "file_operations_manager")`
- Line 355: `hasattr(main_window, "file_operations_manager")`
- Line 372: `hasattr(main_window, "file_operations_manager")`

**Pattern**:
```python
# REPLACE:
if hasattr(main_window, "file_load_worker") and main_window.file_load_worker:

# WITH:
if main_window.file_load_worker is not None:
```

---

### Phase 3: Image Browser (20 minutes)

**File**: `ui/image_sequence_browser.py`
**Changes**: 5 hasattr() → None checks (state_manager parent checks only)
**Impact**: Medium - dialog initialization
**Risk**: 🟢 LOW (straightforward replacement)

**Locations** (state_manager checks only - NOT method checks):
- Line 483: `hasattr(parent, "state_manager")`
- Line 1051: `hasattr(parent_window, "state_manager")`
- Line 1400: `hasattr(parent_window, "state_manager")`
- Line 2173: `hasattr(parent_window, "state_manager")`
- Line 2226: `hasattr(parent_window, "state_manager")`

**Pattern**:
```python
# REPLACE:
if hasattr(parent_window, "state_manager"):
    state_manager = getattr(parent_window, "state_manager", None)

# WITH:
if parent_window.state_manager is not None:
    state_manager = parent_window.state_manager
```

**IMPORTANT**: Do NOT replace:
- Line 485, 1053, 1402: `hasattr(state_manager, "recent_directories")` - Duck-type check
- Line 2181: `hasattr(state_manager, "get_value")` - Protocol check
- Line 2234: `hasattr(state_manager, "set_value")` - Protocol check
- Line 1903: `hasattr(self, "tree_view")` - Initialization guard

---

### Phase 4: Controllers & Commands (30 minutes)

**Files**:
- `ui/controllers/ui_initialization_controller.py` (2 changes)
- `ui/controllers/point_editor_controller.py` (2 changes - need verification)
- `ui/controllers/multi_point_tracking_controller.py` (2 changes - need verification)
- `core/commands/shortcut_commands.py` (3 changes - need verification)

**Process**:
1. Read each file
2. Verify pattern (type safety violation vs legitimate)
3. Replace if violation
4. Test type checking

---

### Phase 5: Miscellaneous UI (20 minutes)

**Files**:
- ui/curve_view_widget.py (1 change - need verification)
- ui/tracking_points_panel.py (1 change - likely legitimate __del__)
- ui/main_window_builder.py (1 change)
- ui/global_event_filter.py (1 change)
- ui/file_operations.py (1 change)

**Process**: Individual file review and selective replacement

---

## Testing Strategy

### Type Checking
```bash
# After each phase:
./bpr <modified_files>

# Verify 0 new errors
# Expected: Type information restored, autocomplete improved
```

### Syntax Validation
```bash
python3 -m py_compile <modified_file.py>
```

### Test Suite
```bash
# Full test suite after all phases:
uv run pytest tests/ -v

# Expected: All tests pass, no regressions
```

### Manual Testing
- Open application
- Test commands (Insert Track, etc.)
- Test session save/restore
- Test image browser dialog
- Verify no AttributeErrors

---

## Success Metrics

✅ **Complete when**:
1. ~25 high-value hasattr() replacements completed in critical paths
2. Type checking confirms 0 new errors
3. IDE autocomplete works for replaced attributes
4. All tests passing
5. Manual testing confirms no regressions
6. ~30 legitimate hasattr() uses remain (documented as intentional)

**Excluded from scope**:
- `__del__()` cleanup methods (legitimate defensive programming)
- Protocol/duck-type checks (legitimate dynamic behavior)
- Initialization guards (legitimate safety checks)
- Test code hasattr() usage

---

## Risk Assessment

### Low Risk ✅
- Straightforward pattern replacement
- High test coverage will catch issues
- Type checking provides immediate feedback
- Incremental phase approach allows validation

### Medium Risk ⚠️
- Must distinguish violations from legitimate uses
- Some files need verification before replacement
- Protocol checks must be preserved

### Mitigation
- Phase-by-phase approach with testing after each
- Clear categorization of violations vs legitimate uses
- Type checking after each file
- Full test suite run before commit

---

## Estimated Timeline

| Phase | File(s) | Changes | Time | Cumulative |
|-------|---------|---------|------|------------|
| 1 | insert_track_command.py | 9 | 30min | 30min |
| 2 | session_manager.py | 5 | 20min | 50min |
| 3 | image_sequence_browser.py | 5 | 20min | 70min |
| 4 | Controllers & Commands | 9 | 30min | 100min |
| 5 | Miscellaneous UI | 5 | 20min | 120min |
| **TOTAL** | **7-10 files** | **~25-30** | **2 hours** | |

---

## Expected Benefits

### Type Safety
- ✅ Restored type information for MainWindow attributes
- ✅ IDE autocomplete works correctly
- ✅ Type checker can verify attribute access
- ✅ Compile-time detection of typos

### Code Quality
- ✅ Adherence to CLAUDE.md documented best practices
- ✅ Consistent pattern across codebase
- ✅ Reduced technical debt
- ✅ Easier maintenance

### Developer Experience
- ✅ Better IDE support
- ✅ Clearer code intent
- ✅ Fewer runtime errors from typos

---

## Implementation Checklist

### Pre-Work
- [x] Analyze all hasattr() usage (grep analysis complete)
- [x] Categorize violations vs legitimate uses
- [x] Create prioritized plan

### Phase 1: Insert Track Command
- [ ] Read core/commands/insert_track_command.py
- [ ] Replace 9 hasattr() instances
- [ ] Run type check: `./bpr core/commands/insert_track_command.py`
- [ ] Run syntax check
- [ ] Test relevant command tests
- [ ] Commit Phase 1

### Phase 2: Session Manager
- [ ] Read ui/session_manager.py
- [ ] Replace 5 hasattr() instances
- [ ] Run type check: `./bpr ui/session_manager.py`
- [ ] Run syntax check
- [ ] Test session save/restore manually
- [ ] Commit Phase 2

### Phase 3: Image Browser
- [ ] Read ui/image_sequence_browser.py
- [ ] Replace 5 hasattr() instances (parent checks only, NOT method checks)
- [ ] Verify legitimate uses preserved (lines 485, 1053, 1402, 1903, 2181, 2234)
- [ ] Run type check: `./bpr ui/image_sequence_browser.py`
- [ ] Run syntax check
- [ ] Test image browser dialog
- [ ] Commit Phase 3

### Phase 4: Controllers & Commands
- [ ] Verify patterns in 4 files (read first)
- [ ] Replace verified violations (~9 instances)
- [ ] Run type check on all modified files
- [ ] Run syntax check
- [ ] Commit Phase 4

### Phase 5: Miscellaneous
- [ ] Verify patterns in 5 files (read first)
- [ ] Replace verified violations (~5 instances)
- [ ] Run type check on all modified files
- [ ] Run syntax check
- [ ] Commit Phase 5

### Final Steps
- [ ] Run full type check: `./bpr --errors-only`
- [ ] Run full test suite: `uv run pytest tests/ -v`
- [ ] Manual testing (commands, session, dialogs)
- [ ] Update CODE_REVIEW_CROSS_CHECK_ANALYSIS.md
- [ ] Update HASATTR_REPLACEMENT_PLAN.md status
- [ ] Create final commit with all phases
- [ ] Push to remote

---

## Future Considerations

### Follow-up Tasks
- Document legitimate hasattr() patterns in CLAUDE.md
- Add pre-commit hook to flag new hasattr() in non-legitimate contexts
- Consider mypy/basedpyright rule for hasattr() warnings

### Pattern Documentation
Should add to CLAUDE.md:
```markdown
## When to Use hasattr()

✅ **Legitimate uses**:
- Cleanup in `__del__()` methods (partial initialization safety)
- Protocol/duck-type checks for optional interfaces
- Initialization guards (defensive programming)

❌ **Anti-patterns**:
- Checking for attributes that are always defined
- Losing type information for known types
- Any check that could use `is not None` instead
```

---

**Report Generated**: 2025-10-13
**Next Step**: Execute Phase 1 (insert_track_command.py)
**Estimated Completion**: 2 hours from start
