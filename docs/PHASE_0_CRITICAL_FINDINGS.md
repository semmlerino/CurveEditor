# Phase 0 Audit: Critical Findings & Action Items
## Active Curve Consolidation Plan

**Status**: GAPS IDENTIFIED - ACTION REQUIRED BEFORE PHASE 1
**Priority**: CRITICAL (Type safety and test stability)

---

## CRITICAL FINDING #1: Protocol Definitions Not Captured

### The Problem

Phase 0 audit searched for `.active_timeline_point\b` usage but **missed protocol definitions**.

**Example - What Was Found**:
```python
# ui/controllers/action_handler_controller.py
self.state_manager.active_timeline_point = "Track1"  # ✓ Found by grep
```

**Example - What Was NOT Found**:
```python
# protocols/ui.py (StateManagerProtocol)
@property
def active_timeline_point(self) -> str | None:  # ✗ NOT found by grep
    """Get the active timeline point..."""
    ...
```

### Why It Matters

Controllers type-check against **protocols**, not implementations:

```python
# ui/controllers/action_handler_controller.py
def __init__(self, state_manager: StateManagerProtocol, ...):
    # Type checker says: "StateManagerProtocol has active_timeline_point, OK!"
    # But if we remove from protocol, type check breaks!
```

### Files That Need Update

**Before Phase 1 starts** (not during Phase 4 cleanup):

1. **`protocols/ui.py` - Line 58-65**
   - Remove or deprecate StateManagerProtocol.active_timeline_point property
   - Add comment: "Use ApplicationState.active_curve instead"

2. **`protocols/ui.py` - Line 860-867**
   - Remove or deprecate MainWindowProtocol.active_timeline_point property
   - Add comment: "Use ApplicationState.active_curve instead"

### Verification Commands

```bash
# Find the exact protocol definitions
grep -n "def active_timeline_point" protocols/ui.py

# Find all files that use StateManagerProtocol type hints
rg ": StateManagerProtocol" --type py

# Verify which controllers will break
rg "state_manager: StateManagerProtocol" ui/controllers/ --type py
```

### Action Items

- [ ] **Immediate**: Read protocols/ui.py lines 58-65 (StateManagerProtocol)
- [ ] **Immediate**: Read protocols/ui.py lines 860-867 (MainWindowProtocol)
- [ ] **Pre-Phase 1**: Update StateManagerProtocol with deprecation notice
- [ ] **Pre-Phase 1**: Update MainWindowProtocol with deprecation notice
- [ ] **Pre-Phase 1**: Document in protocol docstrings: "DEPRECATED - use ApplicationState.active_curve"
- [ ] **Phase 4.1 (NEW)**: Add task to remove both protocol definitions after implementation removes property

---

## CRITICAL FINDING #2: Type Checking Will Fail at Phase 4

### The Scenario

```
Phase 1:  MainWindow.active_timeline_point → delegates to ApplicationState ✓
Phase 2:  Controllers use ApplicationState directly              ✓
Phase 3:  Tests updated                                          ✓
Phase 4:  Removed from StateManager and MainWindow              ???

What happens:
1. StateManager.active_timeline_point property is deleted
2. StateManagerProtocol.active_timeline_point still defined
3. ActionHandlerController expects it (type hints say so)
4. Type checker: "Protocol says it exists!" ✓
5. Runtime: "Attribute doesn't exist!" ✗
```

### Current Status

**Baseline Type Check**:
```bash
./bpr --errors-only
# How many errors? Need to establish baseline FIRST
```

**After Phase 4 Removal** (if protocols not updated):
```bash
./bpr --errors-only
# New errors about protocol/implementation mismatch
```

### Root Cause

Phase 0 audit didn't verify **protocol consistency**. The fix requires:

1. **Document protocols BEFORE changes** (Phase 0.1)
2. **Update protocols WHEN removing from implementation** (Phase 4)
3**NOT** leaving stale protocol definitions

### Action Items

- [ ] **Pre-Phase 1**: Run `./bpr --errors-only` and document baseline
- [ ] **Phase 0.1 (NEW)**: Create checklist of protocol changes needed
- [ ] **Phase 4 (ADD TASK)**: Update protocols before removing implementation
- [ ] **Phase 4 (ADD TASK)**: Run type checking after each protocol update
- [ ] **Phase 5 (ADD STEP)**: Verify all type errors cleared

---

## CRITICAL FINDING #3: Test Fixture Inventory Incomplete

### The Gap

Phase 0 found **8 test files** with direct `.active_timeline_point` usage.
Plan claims **14 test files** need updating.
**6 test files are unaccounted for.**

### Why This Matters

Missing 6 test files means:
1. Tests might fail silently during migration
2. Some fixture setup patterns might not be updated
3. conftest.py helpers might be missed
4. Cascade failures when running full test suite

### Files Found

**Direct Usage** (grep found these):
```
tests/test_event_filter_navigation.py
tests/test_keyframe_navigation.py
tests/test_helpers.py
tests/test_navigation_integration.py
tests/test_tracking_direction_undo.py
tests/test_protocol_coverage_gaps.py
tests/test_multi_point_tracking_merge.py
tests/test_insert_track_command.py
tests/controllers/test_tracking_selection_controller.py
tests/controllers/test_tracking_data_controller.py
```

**Files Mentioned in Plan but Not Found** (need manual check):
```
tests/test_tracking_point_status_commands.py
tests/test_multi_point_selection_signals.py
tests/test_multi_point_selection.py
tests/test_insert_track_integration.py
? (4 more unidentified)
```

### Pattern That's Likely Missed

```python
# conftest.py (NOT found by grep for some reason)
@pytest.fixture
def main_window_with_data():
    window = create_main_window()
    window.active_timeline_point = "TestCurve"  # Might not be in grep results
    return window

# All tests using this fixture would fail if fixture setup breaks!
```

### Action Items

- [ ] **Phase 0.3 (NEW)**: Search conftest.py for all "active_timeline_point" references
- [ ] **Phase 0.3 (NEW)**: Search test_helpers.py line-by-line for fixture setup
- [ ] **Phase 0.3 (NEW)**: Find all @pytest.fixture functions that set this property
- [ ] **Phase 0.3 (NEW)**: Create comprehensive test fixture inventory document
- [ ] **Phase 3**: Use inventory to guide test file migration
- [ ] **Phase 3**: Run `pytest tests/conftest.py -v` to verify fixtures work

---

## MEDIUM FINDING #4: Signal Handler Types Not Verified

### The Issue

Phase -1 fixed ApplicationState signal type from `Signal(str)` to `Signal(object)`.
But Phase 0 didn't verify that **all handlers** can accept `str | None`.

### Potential Problem

```python
# If a handler is defined as:
@safe_slot
def _on_active_timeline_point_changed(self, point_name: str) -> None:  # No union!
    if point_name:  # Works with str
        self.label.setText(f"Point: {point_name}")

# And it receives None during migration:
# - It will BREAK because None is not str
# - Won't fail type checking (slot signature not validated)
# - Only fails at runtime when None is emitted
```

### Files That Need Verification

```bash
# Find all handlers connected to this signal
rg "_on.*timeline.*point.*changed" ui/ --type py -A 3
rg "_on.*active.*curve.*changed" ui/ --type py -A 3
```

### Action Items

- [ ] **Phase 0.2 (NEW)**: Find all signal handlers for active_timeline_point_changed
- [ ] **Phase 0.2 (NEW)**: Verify each handler signature accepts `str | None`
- [ ] **Phase 0.2 (NEW)**: Create document listing all handlers and their signatures
- [ ] **Phase 2**: Update any handlers with incorrect signatures
- [ ] **Phase 5**: Test signal emission with None values

---

## MEDIUM FINDING #5: ApplicationState Signal Hookup Status Unknown

### The Question

Phase -1 fixed ApplicationState.active_curve_changed signal type.
But **is anything listening to it yet?**

### Current State

- ✓ StateManager.active_timeline_point_changed is wired
- ✓ Controllers listen to StateManager signal
- ? ApplicationState.active_curve_changed is defined but is it listened to?

### What Needs to Happen

**Current Flow**:
```
Controller → set active_timeline_point → StateManager emits signal → Timeline updates
```

**After Migration Flow**:
```
Controller → set active_curve → ApplicationState emits signal → Timeline updates
```

**Problem**: Timeline tabs currently connect to StateManager signal, not ApplicationState signal!

### Action Items

- [ ] **Phase 0 (CURRENT)**: Check if timeline_tabs.py listens to ApplicationState signal
- [ ] **Phase 1**: Add ApplicationState signal listener BEFORE removing StateManager property
- [ ] **Phase 1**: Have BOTH signals emit during transition (dual-emit temporary pattern)
- [ ] **Phase 4**: Remove StateManager signal emission
- [ ] **Phase 5**: Verify timeline updates when only ApplicationState signal emits

---

## SUMMARY: Pre-Phase 1 Checklist

**MUST DO Before Starting Phase 1**:

- [ ] Read protocols/ui.py lines 58-65 (StateManagerProtocol.active_timeline_point)
- [ ] Read protocols/ui.py lines 860-867 (MainWindowProtocol.active_timeline_point)
- [ ] Run `./bpr --errors-only` and document baseline
- [ ] Establish test fixture inventory (find all 14 test files)
- [ ] Verify ApplicationState.active_curve_changed signal listening status
- [ ] List all signal handlers and their type signatures
- [ ] Review conftest.py for fixture setup patterns

**Optional But Recommended**:

- [ ] Create integration test for protocol consistency
- [ ] Document signal emission order (prevent race conditions)
- [ ] Create comprehensive file-by-file migration checklist

---

## Risk If Ignored

**Type Checking Failures** (Worst Case):
- Phase 4 removal causes type checking to fail
- 13 files using StateManagerProtocol become type-invalid
- Must revert and retry with protocol updates

**Test Failures** (Worst Case):
- 6 unidentified test files fail during migration
- Test fixtures have stale setup patterns
- Must debug and patch tests individually

**Signal Connection Issues** (Worst Case):
- Timeline doesn't update after active curve change
- Silent failure (code runs but UI doesn't reflect state)
- Hard to debug during Phase 2-3 migration

---

## Estimated Time to Address

| Task | Time | Phase |
|---|---|---|
| Protocol Audit (0.1) | 30 min | Phase 0.1 |
| Signal Handler Verification (0.2) | 45 min | Phase 0.2 |
| Test Fixture Inventory (0.3) | 1 hour | Phase 0.3 |
| **Total Extension** | **2 hours 15 min** | **Phase 0** |
| Protocol Removal (4.1) | 30 min | Phase 4 |

**Total with Extensions**: 8-11 hours + 2h 15m + 0.5h = **10.75-13.75 hours**

Without extensions, risk of Phase 4 failures: **HIGH**

---

*Document created for coverage gap analysis. Provides specific, actionable findings.*
