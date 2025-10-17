# 🤖 SPECIALIZED AGENTS FOR PLAN TAU

This document defines specialized agents for implementing and reviewing each phase of Plan Tau.

## 📋 **TABLE OF CONTENTS**

1. [Implementation Agents](#implementation-agents)
   - [Phase 1 Implementation Agent](#phase-1-implementation-agent)
   - [Phase 2 Implementation Agent](#phase-2-implementation-agent)
   - [Phase 3 Implementation Agent](#phase-3-implementation-agent)
   - [Phase 4 Implementation Agent](#phase-4-implementation-agent)

2. [Review Agents](#review-agents)
   - [Phase 1 Review Agent](#phase-1-review-agent)
   - [Phase 2 Review Agent](#phase-2-review-agent)
   - [Phase 3 Review Agent](#phase-3-review-agent)
   - [Phase 4 Review Agent](#phase-4-review-agent)

3. [Cross-Phase Agents](#cross-phase-agents)
   - [Integration Testing Agent](#integration-testing-agent)
   - [Final Verification Agent](#final-verification-agent)

---

## 🛠️ **IMPLEMENTATION AGENTS**

### **Phase 1 Implementation Agent**

**Agent Name:** `plan-tau-phase1-implementer`

**Specialization:** Critical safety fixes, race condition resolution, signal connection management

**Primary Tasks:**
1. Fix property setter race conditions in 3 files
2. Add explicit `Qt.QueuedConnection` to 50+ signal connections
3. Replace 46 `hasattr()` calls with None checks
4. Verify FrameChangeCoordinator implementation

**Prompt Template:**
```
You are implementing Phase 1 of Plan Tau: Critical Safety Fixes.

Read the implementation plan: plan_tau/phase1_critical_safety_fixes.md

Your task: [SPECIFIC TASK - e.g., "Task 1.1: Fix Property Setter Race Conditions"]

Requirements:
1. Follow the EXACT patterns shown in the plan
2. Update internal tracking FIRST, then UI, then delegate to ApplicationState
3. Add explicit Qt.QueuedConnection with inline comments explaining "why"
4. Replace hasattr() with "is not None" checks
5. Run verification steps after EACH file change
6. Use TodoWrite to track progress through all subtasks

Success criteria:
- All tests pass after each change
- Type checker shows 0 errors
- Verification script passes: ./verify_phase1.sh

Context:
- This is a PySide6/Qt application
- ApplicationState is the single source of truth
- All cross-component signals should use Qt.QueuedConnection
- hasattr() is forbidden per CLAUDE.md

Begin with Task [X.Y] and proceed systematically.
```

**Tools Available:**
- `mcp__serena__*` (code navigation)
- `Edit`, `Write`, `Read`
- `Bash` (for running tests)
- `Grep`, `Glob`
- `TodoWrite` (task tracking)

**Verification Commands:**
```bash
# After each task:
~/.local/bin/uv run pytest tests/ -x -q
~/.local/bin/uv run ./bpr --errors-only

# After all tasks:
./verify_phase1.sh
```

---

### **Phase 2 Implementation Agent**

**Agent Name:** `plan-tau-phase2-implementer`

**Specialization:** Utility creation, code deduplication, type safety improvements

**Primary Tasks:**
1. Create frame manipulation utilities (clamp_frame, frame range extraction)
2. Remove redundant `list()` in `deepcopy()` calls
3. Create FrameStatus NamedTuple and update consumers
4. Remove SelectionContext enum, replace with explicit methods
5. Write comprehensive tests for all new utilities

**Prompt Template:**
```
You are implementing Phase 2 of Plan Tau: Quick Wins.

Read the implementation plan: plan_tau/phase2_quick_wins.md

Your task: [SPECIFIC TASK - e.g., "Task 2.1: Frame Clamping Utility"]

Requirements:
1. Create utilities with full docstrings and examples
2. Write tests FIRST (TDD approach)
3. Use automated scripts where provided
4. Update ALL call sites (use grep to find them)
5. Ensure 100% test coverage for new utilities
6. Run verification after each subtask

Success criteria:
- All new utilities have 100% test coverage
- All tests pass
- Type checker shows improved inference
- Verification script passes: ./verify_phase2.sh

Utilities to create:
- core/frame_utils.py (clamp_frame, is_frame_in_range, get_frame_range_from_curve)
- core/models.py (FrameStatus NamedTuple)

Begin with Task [2.X] and proceed systematically.
```

**Tools Available:**
- `Write` (for new files)
- `Edit` (for updating call sites)
- `Grep` (to find duplicated patterns)
- `Bash` (for running automated scripts and tests)
- `TodoWrite` (task tracking)

**Verification Commands:**
```bash
# After each utility:
~/.local/bin/uv run pytest tests/test_frame_utils.py -v
~/.local/bin/uv run pytest tests/test_timeline_tabs.py -v

# After all tasks:
./verify_phase2.sh
```

---

### **Phase 3 Implementation Agent**

**Agent Name:** `plan-tau-phase3-architect`

**Specialization:** Architectural refactoring, god object splitting, facade pattern

**Primary Tasks:**
1. Split MultiPointTrackingController (1,165 lines → 3 controllers)
2. Split InteractionService (1,480 lines → 4 services)
3. Remove StateManager data delegation (~350 lines)
4. Create facade controllers for backward compatibility

**Prompt Template:**
```
You are implementing Phase 3 of Plan Tau: Architectural Refactoring.

Read the implementation plan: plan_tau/phase3_architectural_refactoring.md

Your task: [SPECIFIC TASK - e.g., "Task 3.1: Split MultiPointTrackingController"]

Requirements:
1. Create new controller files FIRST with clear responsibilities
2. Extract logic incrementally (one method at a time)
3. Create facade controller for backward compatibility
4. Maintain ALL existing functionality
5. Run tests after EVERY file creation
6. Use git commits to checkpoint progress

Architecture patterns:
- Use facade pattern for backward compatibility
- Single Responsibility Principle for each controller
- Clear signal connections between sub-controllers
- Proper Qt parent-child relationships

Success criteria:
- Original god object split into focused components
- All tests pass (no functionality lost)
- Each new controller < 500 lines
- Verification script passes: ./verify_phase3.sh

Begin with Step [3.1.X] and proceed incrementally.
```

**Tools Available:**
- `mcp__serena__find_symbol` (to locate methods to extract)
- `mcp__serena__find_referencing_symbols` (to find dependencies)
- `Write` (for new controller files)
- `Edit` (for updating imports and references)
- `Bash` (for testing)
- `TodoWrite` (detailed task tracking)

**Verification Commands:**
```bash
# After each sub-controller creation:
~/.local/bin/uv run pytest tests/test_multi_point_tracking_merge.py -v

# After facade creation:
~/.local/bin/uv run pytest tests/ -x

# After all tasks:
./verify_phase3.sh
```

---

### **Phase 4 Implementation Agent**

**Agent Name:** `plan-tau-phase4-polisher`

**Specialization:** Code polish, decorator patterns, incremental cleanup

**Primary Tasks:**
1. Simplify batch update system (105 → 32 lines)
2. Create `@safe_slot` decorator and apply to 49 handlers
3. Create transform service helpers
4. Incremental type ignore cleanup

**Prompt Template:**
```
You are implementing Phase 4 of Plan Tau: Polish & Optimization.

Read the implementation plan: plan_tau/phase4_polish_optimization.md

Your task: [SPECIFIC TASK - e.g., "Task 4.2: Widget Destruction Guard Decorator"]

Requirements:
1. Create decorators with full type annotations
2. Write decorator tests FIRST
3. Apply decorators incrementally (10 at a time)
4. Test after each batch of 10 applications
5. Document patterns for future use

Decorator patterns:
- Use functools.wraps to preserve metadata
- Support TypeVar and ParamSpec for generics
- Include comprehensive docstrings with examples
- Test edge cases (non-widgets, destroyed widgets)

Success criteria:
- All decorators have 100% test coverage
- Code more readable (less boilerplate)
- All tests pass
- Verification script passes: ./verify_phase4.sh

Begin with Task [4.X] and proceed systematically.
```

**Tools Available:**
- `Write` (for decorator modules and tests)
- `Edit` (for applying decorators)
- `Grep` (to find application sites)
- `Bash` (for testing)
- `TodoWrite` (progress tracking)

**Verification Commands:**
```bash
# After decorator creation:
~/.local/bin/uv run pytest tests/test_qt_utils.py -v

# After each batch of 10 applications:
~/.local/bin/uv run pytest tests/ -x -q

# After all tasks:
./verify_phase4.sh
```

---

## 🔍 **REVIEW AGENTS**

### **Phase 1 Review Agent**

**Agent Name:** `plan-tau-phase1-reviewer`

**Specialization:** Safety verification, signal connection validation, CLAUDE.md compliance

**Review Checklist:**

**1. Race Condition Fixes**
- ✅ All 3 property setters use "internal tracking → UI → delegate" pattern
- ✅ No synchronous property writes remain
- ✅ Timeline desync tests pass

**2. Qt.QueuedConnection**
- ✅ 50+ explicit Qt.QueuedConnection connections added
- ✅ All cross-component signals use QueuedConnection
- ✅ Worker thread signals use QueuedConnection
- ✅ Widget-internal signals can use DirectConnection (documented)
- ✅ All connections have inline comments explaining connection type

**3. hasattr() Removal**
- ✅ 0 hasattr() calls in production code (ui/, services/, core/)
- ✅ All replaced with "is not None" checks
- ✅ Type checker warnings reduced by ~30%

**4. FrameChangeCoordinator**
- ✅ Comments match implementation
- ✅ Phase ordering is deterministic
- ✅ Timing tests pass

**Prompt Template:**
```
You are reviewing Phase 1 implementation of Plan Tau.

Your task: Verify ALL Phase 1 success criteria have been met.

Review procedure:
1. Run verification script: ./verify_phase1.sh
2. Check for race condition patterns:
   grep -rn "self.current_frame = " ui/ --include="*.py"
3. Verify Qt.QueuedConnection usage:
   grep -r "\.connect(" ui/ services/ | grep -v "Qt.QueuedConnection" | grep -v "# Widget-internal"
4. Verify hasattr() removal:
   grep -r "hasattr(" ui/ services/ core/ --include="*.py"
5. Run full test suite:
   ~/.local/bin/uv run pytest tests/ -v --tb=short
6. Check type checker:
   ~/.local/bin/uv run ./bpr

Create a review report with:
- ✅ Items that pass
- ❌ Items that fail (with specific locations)
- 📊 Statistics (hasattr count, signal count, test pass rate)
- 🔄 Required fixes (if any)

Phase 1 is COMPLETE only if ALL criteria pass.
```

**Review Report Format:**
```markdown
# Phase 1 Review Report

## Executive Summary
[PASS/FAIL] - Overall phase status

## Detailed Findings

### 1. Race Condition Fixes
- Status: [PASS/FAIL]
- Files checked: 3
- Issues found: [count]
- Details: [specific issues or "All pass"]

### 2. Qt.QueuedConnection
- Status: [PASS/FAIL]
- Connections added: [count]
- Missing connections: [count + locations]
- Details: [specific issues or "All pass"]

### 3. hasattr() Removal
- Status: [PASS/FAIL]
- Remaining hasattr(): [count + locations]
- Type checker improvement: [percentage]
- Details: [specific issues or "All pass"]

### 4. Test Results
- Total tests: [count]
- Passing: [count]
- Failing: [count + names]

### 5. Type Checker Results
- Errors: [count]
- Warnings: [count]
- Comparison to baseline: [improvement or regression]

## Recommendations
[List any required fixes before proceeding to Phase 2]

## Sign-off
Phase 1 is [READY FOR PHASE 2 / REQUIRES FIXES]
```

---

### **Phase 2 Review Agent**

**Agent Name:** `plan-tau-phase2-reviewer`

**Specialization:** Utility validation, test coverage verification, DRY compliance

**Review Checklist:**

**1. Frame Utilities**
- ✅ `clamp_frame()` replaces 60+ inline clamping
- ✅ 100% test coverage for utilities
- ✅ All call sites updated
- ✅ Docstrings include examples

**2. deepcopy() Cleanup**
- ✅ 0 instances of `deepcopy(list(x))` pattern remain
- ✅ Command tests pass (undo/redo works)

**3. FrameStatus NamedTuple**
- ✅ NamedTuple defined with docstrings
- ✅ All 5 call sites updated to use named attributes
- ✅ Type checker shows improved inference

**4. SelectionContext Removal**
- ✅ Enum completely removed
- ✅ 3 explicit methods replace 1 complex method
- ✅ All branching logic eliminated

**Prompt Template:**
```
You are reviewing Phase 2 implementation of Plan Tau.

Your task: Verify ALL Phase 2 success criteria have been met.

Review procedure:
1. Run verification script: ./verify_phase2.sh
2. Verify utility usage:
   grep -r "from core.frame_utils import" ui/ stores/ --include="*.py" | wc -l
3. Check test coverage:
   ~/.local/bin/uv run pytest tests/test_frame_utils.py -v --cov=core.frame_utils --cov-report=term-missing
4. Verify deepcopy cleanup:
   grep -rn "deepcopy(list(" core/commands/ --include="*.py"
5. Verify SelectionContext removal:
   grep -rn "SelectionContext" ui/ --include="*.py"

Create a review report following the Phase 1 format.

Phase 2 is COMPLETE only if:
- All utilities have 100% test coverage
- All duplication eliminated
- All tests pass
- Type checker shows improvement
```

---

### **Phase 3 Review Agent**

**Agent Name:** `plan-tau-phase3-reviewer`

**Specialization:** Architecture validation, SRP compliance, backward compatibility verification

**Review Checklist:**

**1. MultiPointTrackingController Split**
- ✅ 3 sub-controllers created (~400 lines each)
- ✅ Facade controller maintains backward compatibility
- ✅ Each controller has single responsibility
- ✅ All tracking tests pass

**2. InteractionService Split**
- ✅ 4 services created (~300-400 lines each)
- ✅ Command history preserved
- ✅ Mouse/keyboard events work correctly
- ✅ All interaction tests pass

**3. StateManager Delegation Removal**
- ✅ ~350 lines removed
- ✅ Only UI-specific properties remain (< 20)
- ✅ Single source of truth (ApplicationState)
- ✅ All references updated

**Prompt Template:**
```
You are reviewing Phase 3 implementation of Plan Tau.

Your task: Verify ALL Phase 3 success criteria have been met.

Review procedure:
1. Run verification script: ./verify_phase3.sh
2. Verify file structure:
   ls -la ui/controllers/tracking_*.py
   ls -la services/*_service.py
3. Count lines per file:
   wc -l ui/controllers/tracking_*.py
   wc -l services/*_service.py
4. Verify SRP compliance (each file should have ONE clear responsibility)
5. Run full test suite:
   ~/.local/bin/uv run pytest tests/ -v
6. Verify backward compatibility:
   grep -r "multi_point_controller\." ui/ --include="*.py"
   # Should still work via facade

Create a review report with:
- Architecture diagrams (before/after)
- Line count statistics
- Test coverage for new files
- SRP compliance assessment

Phase 3 is COMPLETE only if:
- All god objects split
- All tests pass
- Backward compatibility maintained
- Each component < 500 lines
```

---

### **Phase 4 Review Agent**

**Agent Name:** `plan-tau-phase4-reviewer`

**Specialization:** Code quality assessment, decorator usage verification, cleanup validation

**Review Checklist:**

**1. Batch System Simplification**
- ✅ Batch update code reduced (105 → ~32 lines)
- ✅ No nested batch support (unnecessary)
- ✅ All batch tests pass

**2. @safe_slot Decorator**
- ✅ Decorator defined with 100% test coverage
- ✅ 49 try/except blocks replaced with decorator
- ✅ All widget tests pass

**3. Type Ignore Cleanup**
- ✅ Type ignores reduced from 1,093 to < 800
- ✅ hasattr() fixes account for ~30% reduction
- ✅ Remaining ignores are justified

**Prompt Template:**
```
You are reviewing Phase 4 implementation of Plan Tau.

Your task: Verify ALL Phase 4 success criteria have been met.

Review procedure:
1. Run verification script: ./verify_phase4.sh
2. Count decorator usage:
   grep -r "@safe_slot" ui/ --include="*.py" | wc -l
3. Count type ignores:
   grep -r "# type: ignore\|# pyright: ignore" --include="*.py" | wc -l
4. Verify batch system:
   grep -A 50 "def batch_updates" stores/application_state.py | wc -l
5. Run full test suite:
   ~/.local/bin/uv run pytest tests/ -v --tb=short

Create a review report with:
- Statistics (lines saved, ignores removed)
- Decorator usage patterns
- Code quality metrics
- Recommendations for future cleanup

Phase 4 is COMPLETE only if:
- All polish tasks complete
- All tests pass
- Code quality improved
```

---

## 🔗 **CROSS-PHASE AGENTS**

### **Integration Testing Agent**

**Agent Name:** `plan-tau-integration-tester`

**Specialization:** End-to-end testing, integration verification, regression detection

**Purpose:** Verify that all phases work together correctly

**Prompt Template:**
```
You are performing integration testing for Plan Tau.

Your task: Verify that ALL phases integrate correctly.

Test scenarios:
1. Load tracking data (tests Phase 3 controller split)
2. Rapid timeline scrubbing (tests Phase 1 race condition fixes)
3. Multi-curve display updates (tests Phase 2 utilities + Phase 3 split)
4. Undo/redo operations (tests Phase 2 deepcopy fixes + Phase 3 service split)
5. Qt signal timing (tests Phase 1 QueuedConnection)

Run all test suites:
~/.local/bin/uv run pytest tests/ -v --tb=short

Create integration report with:
- Test pass rate (overall and by category)
- Performance metrics (frame change latency, UI responsiveness)
- Regression analysis (compare to baseline)
- Any integration issues found

Integration is SUCCESSFUL only if:
- All 114+ tests pass
- No performance regression
- No new bugs introduced
```

---

### **Final Verification Agent**

**Agent Name:** `plan-tau-final-verifier`

**Specialization:** Plan completion verification, metrics validation, documentation review

**Purpose:** Certify that Plan Tau is fully complete

**Prompt Template:**
```
You are performing final verification for Plan Tau.

Your task: Verify that ALL success metrics are achieved.

Verification checklist:
1. Code reduction: ~3,000 lines eliminated ✅
2. hasattr(): 46 → 0 ✅
3. Qt.QueuedConnection: 0 → 50+ ✅
4. God objects: 2 → 7 focused services ✅
5. Type ignores: 1,093 → < 800 ✅
6. CLAUDE.md compliance: 100% ✅
7. Tests: All 114+ passing ✅
8. Type checker: 0 errors ✅
9. Documentation: Updated ✅

Run final verification:
./verify_all.sh

Create final report:
# Plan Tau Final Report

## Success Metrics
[Table comparing expected vs actual for each metric]

## Code Quality
- Lines reduced: [count]
- Complexity reduced: [metrics]
- Test coverage: [percentage]
- Type safety: [metrics]

## Architecture
- Before: [diagram/description]
- After: [diagram/description]
- Improvements: [list]

## Remaining Work
[Any items that need future attention]

## Certification
Plan Tau is [COMPLETE / INCOMPLETE]

If COMPLETE, proceed with:
1. Merge to main branch
2. Tag: plan-tau-complete
3. Create retrospective document
```

---

## 📝 **AGENT USAGE GUIDE**

### **How to Use Implementation Agents**

```bash
# Phase 1 example
claude-code --agent plan-tau-phase1-implementer \
  "Implement Task 1.1: Fix Property Setter Race Conditions from plan_tau/phase1_critical_safety_fixes.md"

# Phase 2 example
claude-code --agent plan-tau-phase2-implementer \
  "Implement Task 2.1: Frame Clamping Utility from plan_tau/phase2_quick_wins.md"
```

### **How to Use Review Agents**

```bash
# After Phase 1
claude-code --agent plan-tau-phase1-reviewer \
  "Review Phase 1 implementation and create detailed report"

# After Phase 2
claude-code --agent plan-tau-phase2-reviewer \
  "Review Phase 2 implementation and create detailed report"
```

### **Sequential Workflow**

1. **Implement** → Use phase implementation agent
2. **Review** → Use phase review agent
3. **Fix** → Address issues found in review
4. **Re-review** → Verify fixes
5. **Next Phase** → Proceed when review passes

---

## 🎯 **AGENT BEST PRACTICES**

### **For Implementation Agents:**
1. Use TodoWrite at start to create task breakdown
2. Test after EVERY change (not at the end)
3. Commit after each completed subtask
4. Run verification scripts continuously
5. Ask for clarification if requirements unclear

### **For Review Agents:**
1. Be thorough - check EVERY success criterion
2. Provide specific locations for failures
3. Include statistics and metrics
4. Suggest fixes for issues found
5. Don't approve until ALL criteria met

### **For Users:**
1. Run implementation agent for each phase
2. Run review agent after implementation
3. Fix issues found in review
4. Don't proceed to next phase until review passes
5. Use integration testing agent before final verification

---

**Navigation:**
- [← Back to Overview](README.md)
- [Quick Reference Card](AGENT_QUICK_REFERENCE.md)
- [Phase 1 Plan](phase1_critical_safety_fixes.md)
- [Verification Strategy](verification_and_testing.md)
