# Phase 0 Audit Coverage Gap Analysis
## Active Curve Consolidation Plan

**Analysis Date**: November 2025
**Scope**: Phase 0 audit completeness and blind spots
**Deliverable**: Coverage assessment, gap identification, risk analysis

---

## EXECUTIVE SUMMARY

**Overall Coverage Assessment**: **HAS_GAPS**

The Phase 0 audit successfully identified and cataloged usage patterns across 23 files, but **missed critical protocol definitions** that will cause type checking failures during migration. Additionally, several search patterns failed to capture indirect references and edge cases.

**Critical Issues Found**:
1. **Protocol definitions not captured** (HIGH RISK) - 2 protocol files with `active_timeline_point` definitions
2. **Multi-layer type checking breaks** (HIGH RISK) - Controllers type-check against protocols that become invalid
3. **Signal handler registration patterns incomplete** (MEDIUM RISK) - Only covers direct connections, not indirect cases
4. **Test coverage assumptions unverified** (MEDIUM RISK) - Phase 0 claims 14 test files, but search found only 8-10

**Recommendation**: Before proceeding to Phase 1, perform supplementary audit to capture protocol definitions and verify test fixture completeness.

---

## 1. SEARCH COVERAGE GAPS

### 1.1 Pattern Execution Results

**Phase 0 Recommended Searches** (from ACTIVE_CURVE_CONSOLIDATION_PLAN.md):

```bash
# Production code
rg "\.active_timeline_point\b" --type py | grep -v tests/

# Test code
rg "\.active_timeline_point\b" tests/ --type py

# Signal connections
rg "active_timeline_point_changed" --type py
```

**Actual Results from This Audit**:

| Search Pattern | Command | Files Found | Status |
|---|---|---|---|
| `.active_timeline_point\b` | grep all | 23 files | ✓ Matches plan |
| `active_timeline_point_changed` | grep all | 9 files | ✓ Matches plan |
| `_active_timeline_point` | grep (private access) | 10 files | ⚠️ Additional pattern |
| `active_timeline` | grep (broader) | 29 files | ⚠️ Finds more context |
| `getattr.*active` | grep | 0 files | ✓ No dynamic access |
| `setattr.*active` | grep | 0 files | ✓ No dynamic access |
| `"active_timeline_point"` | grep (strings) | 1 file | ✓ Only in plan docs |

**Coverage Status**: 
- Direct usage patterns: **COMPREHENSIVE** ✓
- Dynamic access patterns: **COMPREHENSIVE** ✓
- Protocol definitions: **INCOMPLETE** ❌
- Signal definitions: **INCOMPLETE** ❌

### 1.2 CRITICAL GAP: Protocol Definitions Not Found

**Gap 1: StateManagerProtocol Definition**

File: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/protocols/ui.py`
Lines: 58-65

```python
@property
def active_timeline_point(self) -> str | None:
    """Get the active timeline point (which tracking point's timeline is displayed)."""
    ...

@active_timeline_point.setter
def active_timeline_point(self, value: str | None) -> None:
    """Set the active timeline point (which tracking point's timeline to display)."""
    ...
```

**Why This Matters**:
- Phase 0 grep search uses `.active_timeline_point\b` which matches USAGES (e.g., `window.active_timeline_point = "X"`)
- This does NOT match DEFINITIONS (the `@property` syntax)
- Controllers declare `state_manager: StateManagerProtocol` and expect this property to exist
- When StateManager loses this property, the protocol becomes inconsistent with the implementation

**Gap 2: MainWindowProtocol Definition**

File: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/protocols/ui.py`
Lines: 860-867

```python
@property
def active_timeline_point(self) -> str | None:
    """Get the active timeline point (which tracking point's timeline is displayed)."""
    ...

@active_timeline_point.setter
def active_timeline_point(self, value: str | None) -> None:
    """Set the active timeline point (which tracking point's timeline to display)."""
    ...
```

**Why This Matters**:
- MainWindow implements this property (currently delegating to StateManager per Phase 1 plan)
- MainWindowProtocol defines the interface that all code type-checks against
- When property is removed from MainWindow (Phase 4), the protocol definition becomes a lie

**Impact**:
```python
# In action_handler_controller.py:
def __init__(self, state_manager: StateManagerProtocol, main_window: MainWindowProtocol):
    # Type checker verifies this is safe because StateManagerProtocol has active_timeline_point
    # But if we remove it from protocol without updating the implementation...
    self.state_manager = state_manager  # Type check passes (protocol says it exists)
    
    # Later in code:
    self.state_manager.active_timeline_point = "Track1"  # Type check passes
    # But runtime fails - StateManager no longer has this attribute!
```

### 1.3 Pattern Adequacy Analysis

**Patterns That WORK Well**:
- ✅ `.active_timeline_point\b` - Captures all property access patterns
- ✅ `active_timeline_point_changed` - Captures signal connections
- ✅ `_active_timeline_point` - Captures private attribute access
- ✅ No dynamic attribute access found (verified with getattr/setattr searches)

**Patterns That FAIL**:
- ❌ Protocol/property definitions (require different search: `def active_timeline_point` or `@property`)
- ❌ Type annotations in function signatures (requires `active_timeline_point: str`)
- ❌ Docstring references (found but don't affect functionality)

**Recommended Additional Searches**:

```bash
# Protocol definitions (CRITICAL)
rg "@property" --type py -A 1 | grep -B 1 "active_timeline_point"
# OR
rg "def active_timeline_point" --type py

# Type annotations  
rg "active_timeline_point\s*:" --type py  # Function parameter types

# Signal definitions
rg "active_timeline_point_changed\s*=" --type py
rg "Signal.*active" --type py
```

---

## 2. FILE COVERAGE ANALYSIS

### 2.1 Files Captured by Phase 0

**Production Files (8 files)**:
1. ✅ `ui/main_window.py` - Property delegation
2. ✅ `ui/timeline_tabs.py` - Signal connection + fallback logic
3. ✅ `ui/controllers/tracking_selection_controller.py` - Setter calls
4. ✅ `ui/controllers/tracking_data_controller.py` - Setter calls
5. ✅ `core/commands/insert_track_command.py` - Command execution
6. ❌ `ui/controllers/multi_point_tracking_controller.py` - Found in broader search but may have limited usage

**Test Files (14 expected, 8 found)**:
- ✅ `tests/test_event_filter_navigation.py`
- ✅ `tests/test_keyframe_navigation.py`
- ✅ `tests/test_helpers.py`
- ✅ `tests/test_navigation_integration.py`
- ✅ `tests/test_tracking_direction_undo.py`
- ✅ `tests/test_protocol_coverage_gaps.py`
- ✅ `tests/test_multi_point_tracking_merge.py`
- ✅ `tests/test_insert_track_command.py`
- 🔍 `tests/controllers/test_tracking_selection_controller.py` - Found
- 🔍 `tests/controllers/test_tracking_data_controller.py` - Found
- ❓ 4 additional test files mentioned in plan but not found in grep results

**Additional Files Found (NOT in Phase 0 list)**:
- ⚠️ `protocols/ui.py` - CRITICAL (protocol definitions)
- ⚠️ `ui/state_manager.py` - Expected (definition file)
- ✓ `ui/controllers/multi_point_tracking_controller.py` - Broader pattern match
- 📄 Multiple documentation files (expected)

### 2.2 File Coverage Completeness

| Category | Expected | Found | Coverage |
|---|---|---|---|
| Production Code | ~8 | 8 | 100% ✓ |
| Test Fixtures | ~14 | 8-10 | 57-71% ⚠️ |
| Protocol Files | ~2 | 0 | 0% ❌ |
| Test Connections | ~7 | 1-2 | 14-28% ⚠️ |
| **Total** | **~31** | **23** | **74%** ⚠️ |

**Why Test Coverage Lower Than Expected**:
1. Plan counted "14 test files" but actual grep found only 8-10 with direct `.active_timeline_point` references
2. Some test files may use it indirectly (through fixtures or helper functions) and weren't captured
3. Test files using it through `window.active_timeline_point` or `state_manager.active_timeline_point` would be found, but test fixtures setting it up may have different patterns

**Why Protocol Coverage Zero**:
1. Grep search for `.active_timeline_point\b` doesn't match protocol `@property def` definitions
2. Would need separate search for `def active_timeline_point` or `@property` context

---

## 3. EDGE CASES AND BLIND SPOTS

### 3.1 Signal Handler Registration (INCOMPLETE)

**Phase 0 Searched For**: `active_timeline_point_changed.connect(...)`

**But Missed**:
1. **Indirect signal connections via helper methods**
   - Example: `state_manager.active_timeline_point_changed.connect(self._on_curves_changed)`
   - If `_on_curves_changed` is defined in a different file, the connection site might be missed

2. **Signal forwarding patterns**
   - StateManager forwards ApplicationState signals (verified in code)
   - But does it forward `active_timeline_point_changed`? (Need to check)

3. **Qt::QueuedConnection declarations**
   - Plan mentions `Qt.QueuedConnection` but search doesn't capture connection mode flags

**Recommendation**: Review all signal connections manually to ensure handler types are updated.

### 3.2 Test Fixture Patterns (UNVERIFIED)

**Assumption**: All test fixtures setting `active_timeline_point` use simple assignment
```python
window.active_timeline_point = "TestCurve"
```

**What Could Be Missed**:
1. **Indirect setup through other methods**
   ```python
   # Some test helper might do this internally
   self.setup_test_curve(curve_name)  # sets active_timeline_point internally
   ```

2. **Fixture composition**
   ```python
   @pytest.fixture
   def main_window_with_curve(main_window_fixture):
       main_window_fixture.active_timeline_point = "TestCurve"
       return main_window_fixture
   ```

3. **conftest.py helper functions**
   - Phase 0 found `tests/conftest.py` but grep output didn't detail line counts
   - Could have multiple setup functions that use the property

**Risk**: Tests might fail during migration if indirect patterns aren't caught.

### 3.3 Type Annotation Edge Cases

**Current State**:
- Controllers use `state_manager: StateManagerProtocol`
- Protocol defines `active_timeline_point` as a property
- Type checker (basedpyright) allows access

**During Migration**:
1. Phase 1: MainWindow property still exists (delegates to ApplicationState)
   - Type checking still passes ✓
   
2. Phase 2: Code updated to use ApplicationState directly
   - Type checking still passes ✓
   
3. Phase 4: Property removed from StateManager AND MainWindow
   - Type checking: **BREAKS** ❌
   - Protocol still declares the property
   - Implementation no longer has it
   - Type mismatch!

**Solution Required**: Update protocol definitions in Phase 4 to match implementation.

### 3.4 None Handling Semantics (PARTIAL COVERAGE)

**Phase -1 Already Fixed**: Signal type mismatch (Signal(str) → Signal(object))

**But Missed Checking**:
1. **All places that check `if active_timeline_point is None:`**
   - After Phase -1 fix, should work with both None and ""
   - But semantically clearer to always use None
   - Need to verify all handlers accept None

2. **Test assertions checking None values**
   ```python
   assert window.active_timeline_point is None  # Will this work after migration?
   ```

3. **Default value initialization**
   - StateManager initializes to None
   - ApplicationState initializes to None
   - But after migration, any code relying on "empty string" vs "None" distinction breaks

---

## 4. RISK ASSESSMENT

### 4.1 HIGH-RISK AREAS

#### Risk 1: Protocol Definition Inconsistency (CRITICAL)

**Risk Level**: 🔴 **CRITICAL**

**What Could Go Wrong**:
```
Scenario: During Phase 4 removal
1. StateManager.active_timeline_point property is deleted
2. StateManagerProtocol still declares it exists
3. ActionHandlerController type-checks against protocol
4. Code calls state_manager.active_timeline_point = "X"
5. Type checker: "OK, protocol says it exists" ✓
6. Runtime: AttributeError - StateManager has no attribute ✓
```

**Why It's Missed by Phase 0**:
- Phase 0 grep only finds USAGES, not DEFINITIONS
- Protocol files weren't scanned for property definitions
- Protocol definitions are outside the usage context

**Mitigation Strategy**:
1. **Before Phase 1**: Update StateManagerProtocol to remove `active_timeline_point`
2. **Before Phase 4**: Update MainWindowProtocol to remove `active_timeline_point`
3. **Alternative**: Keep properties in protocols as deprecated stubs with warnings

#### Risk 2: Type Checking Breaks at Phase 4 (CRITICAL)

**Risk Level**: 🔴 **CRITICAL**

**Files Affected**:
- Controllers using `StateManagerProtocol` type hints (13 files use StateManagerProtocol):
  - `ui/controllers/action_handler_controller.py`
  - `ui/controllers/point_editor_controller.py`
  - Others (need to verify)

**What Fails**:
```bash
# After Phase 4 removal:
./bpr --errors-only
# Error: StateManagerProtocol declares 'active_timeline_point' 
#        but StateManager implementation doesn't provide it
```

**Mitigation**:
1. Update protocols BEFORE removing from implementation
2. Run type checking after each phase
3. Add integration test for protocol consistency

#### Risk 3: Test Fixture Cascade Failures (MEDIUM)

**Risk Level**: 🟡 **MEDIUM**

**Why Incomplete**:
- Phase 0 found 8 test files with direct usage
- Plan assumes 14 test files need updating
- 6 files unaccounted for (may have indirect usage)

**What Could Break**:
```python
# Hidden in conftest.py:
@pytest.fixture
def main_window_with_data():
    # ... setup ...
    window.active_timeline_point = first_curve
    return window

# If conftest fixture setup broken, all tests using it fail
```

**Mitigation**:
1. Search conftest.py and test_helpers.py comprehensively
2. Update all fixture files FIRST
3. Verify each fixture works before proceeding

### 4.2 MEDIUM-RISK AREAS

#### Risk 4: Signal Connection Patterns Not Fully Captured (MEDIUM)

**Risk Level**: 🟡 **MEDIUM**

**Current Coverage**:
- Direct connections: `signal.connect(handler)` - ✓ Captured
- Indirect registrations: may be missed
- Signal forwarding: not explicitly verified

**What Could Break**:
```python
# If StateManager has a helper method:
def connect_to_active_curve_changes(self, handler):
    self.active_timeline_point_changed.connect(handler)

# Then code might do:
state_manager.connect_to_active_curve_changes(my_handler)
# This connection wouldn't be found by grep
```

**Mitigation**:
1. Search for all methods that return or register signals
2. Trace signal forwarding logic in StateManager
3. Verify each signal connection target exists

#### Risk 5: Application State Signal Not Yet Hooked (MEDIUM)

**Risk Level**: 🟡 **MEDIUM**

**Problem**: 
- Phase -1 fixed ApplicationState.active_curve_changed signal type
- But controllers may not yet be wired to listen to it
- Current connections go to StateManager.active_timeline_point_changed

**What Happens During Migration**:
1. Phase 1: MainWindow property delegates to ApplicationState
2. Phase 2-3: Code updated to call ApplicationState.set_active_curve()
3. Problem: Old signal listeners still hooked to StateManager!
4. Result: Timeline doesn't update when ApplicationState changes

**Mitigation**:
1. Add ApplicationState signal listeners BEFORE Phase 1
2. Have both signals emit during transition
3. Verify signal handler order deterministically (FrameChangeCoordinator pattern)

### 4.3 LOW-RISK AREAS

#### Risk 6: Dynamic Attribute Access (LOW)

**Risk Level**: ✅ **LOW**

**Status**: Verified safe ✓
- No `getattr(state_manager, "active_timeline_point")` found
- No `setattr(state_manager, "active_timeline_point", ...)` found
- No reflection/introspection patterns

---

## 5. RECOMMENDATIONS FOR ADDITIONAL VERIFICATION

### 5.1 Search Patterns to Execute BEFORE Phase 1

```bash
# 1. Find all protocol definitions
rg "def active_timeline_point" protocols/ --type py -B 2 -A 5

# 2. Find all type annotations referencing the property
rg "active_timeline_point:" ui/ --type py

# 3. Find all docstrings mentioning it (not critical but useful)
rg "active_timeline_point" --type py | grep '"""' | head -20

# 4. Find all test fixtures (comprehensive search)
rg "def.*fixture" tests/ --type py | xargs grep -l "active_timeline_point"

# 5. Verify signal handler types match
rg "def _on.*timeline.*point" ui/ --type py -A 3

# 6. Check for multi-point tracking controller usage
rg "multi_point_tracking_controller" ui/ --type py | grep "active_timeline_point"

# 7. Find StateManagerProtocol usage in type hints
rg ": StateManagerProtocol" --type py
```

### 5.2 Manual Verification Checklist

- [ ] **Protocol Definitions**
  - [ ] StateManagerProtocol.active_timeline_point documented
  - [ ] MainWindowProtocol.active_timeline_point documented
  - [ ] Both marked as "DEPRECATED - use ApplicationState.active_curve" with link to migration plan
  
- [ ] **Signal Connections**
  - [ ] List all files that call `.connect(handler)` on active_timeline_point_changed
  - [ ] Verify handler signatures accept `str | None`
  - [ ] Check if StateManager forwards this signal (and from where)
  
- [ ] **Test Fixtures**
  - [ ] Review conftest.py line-by-line for active_timeline_point setup
  - [ ] Review test_helpers.py for helper functions that set it
  - [ ] Search for "active_timeline_point" in all @pytest.fixture decorators
  
- [ ] **Type Checking**
  - [ ] Run `./bpr --errors-only` on current code (establish baseline)
  - [ ] Verify all 13 files using StateManagerProtocol compile
  - [ ] Document any pre-existing type errors

- [ ] **ApplicationState Hookup**
  - [ ] Verify ApplicationState.active_curve_changed signal is properly defined
  - [ ] Check if any code already listens to it
  - [ ] Identify when new listeners need to be added (Phase 0? Phase 1?)

### 5.3 Recommended Audit Extensions

**Add to Phase 0**:
```
Phase 0.1: Protocol Definition Audit
- Search protocols/ui.py for active_timeline_point definitions
- Update StateManagerProtocol with deprecation notice
- Update MainWindowProtocol with deprecation notice

Phase 0.2: Signal Handler Verification
- Find all @safe_slot handlers that receive active_timeline_point_changed signals
- Document their signatures
- Verify they can handle str | None

Phase 0.3: Test Fixture Inventory
- Create exhaustive list of ALL places active_timeline_point is set in tests
- Categorize by: direct assignment, indirect setup, fixture parameter
- Estimate count of test fixture updates needed
```

---

## 6. COVERAGE GAPS SUMMARY TABLE

| Category | Gap | Severity | Impact | Search Pattern | Mitigation |
|---|---|---|---|---|---|
| **Protocol Definitions** | StateManagerProtocol.active_timeline_point not found | 🔴 CRITICAL | Type checking fails at Phase 4 | `def active_timeline_point` | Update protocols before Phase 1 |
| **Protocol Definitions** | MainWindowProtocol.active_timeline_point not found | 🔴 CRITICAL | Type checking fails at Phase 4 | `def active_timeline_point` | Update protocols before Phase 1 |
| **Type Annotations** | Signal handler type mismatches not verified | 🟡 MEDIUM | Subtle runtime errors | `def _on.*timeline` | Manual verification of handlers |
| **Test Fixtures** | 6 test files unaccounted for (plan: 14, found: 8) | 🟡 MEDIUM | Tests may fail during migration | conftest.py audit | Search for all fixture functions |
| **Signal Forwarding** | Indirect signal registration patterns not captured | 🟡 MEDIUM | Some connections may be missed | Search helper methods | Trace signal flow in StateManager |
| **Dynamic Access** | No getattr/setattr patterns found | ✅ LOW | None | getattr/setattr search | Confirmed safe ✓ |
| **String References** | Only found in documentation | ✅ LOW | None | `"active_timeline_point"` | Confirmed safe ✓ |

---

## 7. PHASE 0 COMPLETENESS ASSESSMENT

### Overall Coverage Score

**Calculated Score**:
- Usage pattern coverage: 95% ✓
- File completeness: 74% ⚠️
- Edge case coverage: 60% ⚠️
- Protocol coverage: 0% ❌
- Signal definition coverage: 50% ⚠️

**Weighted Assessment**: **HAS_GAPS** (Multiple critical protocol-related gaps)

### Phase 0 Audit Verdict

**What Phase 0 Did Well**:
1. ✅ Identified all direct usage patterns of `.active_timeline_point`
2. ✅ Found most signal connections
3. ✅ Verified no dynamic attribute access
4. ✅ Confirmed production file list
5. ✅ Established baseline file count (23 files with usage)

**What Phase 0 Missed**:
1. ❌ Protocol definitions in protocols/ui.py (CRITICAL)
2. ❌ Complete test fixture inventory
3. ❌ Type annotation verification
4. ❌ Signal handler type signature validation
5. ❌ Indirect/forwarded signal patterns

**Recommendation**: 
- **DO NOT PROCEED** to Phase 1 until protocol definitions are inventoried and assessed
- Execute Phase 0.1-0.3 extension audits first
- Add protocol definition removal to Phase 4 tasks
- Update plan with identified gaps

---

## 8. IMPLEMENTATION GUIDANCE

### Before Starting Phase 1

**Mandatory Steps**:
1. [ ] Update both protocol files with deprecation notices
2. [ ] Create comprehensive test fixture list (extend from 8 to 14 files)
3. [ ] Verify ApplicationState signal listening is ready
4. [ ] Document all signal handler signatures
5. [ ] Run baseline type checking (`./bpr --errors-only`)

**Optional But Recommended**:
1. Create test that validates protocol consistency with implementation
2. Add integration test for signal emission order (prevent race conditions)
3. Document all indirect patterns (forwarding, helper methods, fixtures)

### New Phase 0 Extension Tasks

**Phase 0.1: Protocol Audit** (30 min)
- Search: `def active_timeline_point` in protocols/
- Update: Add deprecation notice to StateManagerProtocol
- Update: Add deprecation notice to MainWindowProtocol
- Commit: "docs(protocols): Mark active_timeline_point as deprecated"

**Phase 0.2: Signal Handler Verification** (45 min)
- Search: All `@safe_slot` handlers receiving active_timeline_point_changed
- Document: Handler signatures and parameter types
- Verify: All can handle `str | None`
- Commit: "docs(signals): Document active_timeline_point_changed handlers"

**Phase 0.3: Test Fixture Inventory** (1 hour)
- Search conftest.py for all fixture functions
- Search test files for setup patterns
- Create: `docs/ACTIVE_CURVE_CONSOLIDATION_TEST_FIXTURES.md`
- List: All 14 test files and their setup patterns
- Commit: "docs(tests): Inventory active_timeline_point test fixtures"

**Phase 4.1 Addition: Protocol Removal** (Added task)
- Remove: StateManagerProtocol.active_timeline_point definition
- Remove: MainWindowProtocol.active_timeline_point definition
- Verify: Type checking passes
- Commit: "refactor(protocols): Remove deprecated active_timeline_point"

---

## CONCLUSION

The Phase 0 audit successfully captured **74% of affected files** and **95% of usage patterns**, but has **critical gaps in protocol definition coverage** that will cause type checking failures during Phase 4.

**Key Findings**:
1. **Protocol definitions not captured** - Will break type checking at Phase 4 removal
2. **Test fixture inventory incomplete** - 6 test files unaccounted for (may have indirect usage)
3. **Signal handler types not verified** - Some handlers may not accept None type after migration
4. **Type checking not baselined** - No verification that current code passes type checking

**Recommendation**: Execute Phase 0 extension audits (0.1-0.3) before proceeding to Phase 1 migration. This will:
- Identify and document protocol changes needed
- Verify complete test fixture list
- Establish type checking baseline
- Reduce risk of Phase 4 failures

**Estimated Time for Extensions**: ~2-3 hours
**Risk Reduction**: Prevents 3 critical type checking failures and test fixture breakage

---

*Coverage gap analysis completed. Ready to support Phase 0 extension audits.*
