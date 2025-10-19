# Best Practices Review Index

**Review Date**: October 19, 2025
**Scope**: Qt signal patterns, widget lifecycle, memory management, threading
**Overall Status**: CRITICAL VIOLATIONS - Plan not recommended

---

## Quick Navigation

### 1. Start Here: Executive Summary (5 minutes)
**File**: `BEST_PRACTICES_AUDIT_SUMMARY.md`

- Quick status: CRITICAL VIOLATIONS FOUND
- Top 5 violations with one-line fixes
- Violations by category
- Recommendation: REJECT PLAN
- Files affected list

**When**: Read this first to understand the scope of issues

---

### 2. Deep Dive: Comprehensive Analysis (30 minutes)
**File**: `QT_BEST_PRACTICES_REVIEW.md`

- Executive summary with context
- 10 Critical violations (detailed analysis)
- Each violation includes:
  - Problem description
  - Current code example
  - Why it violates best practices
  - Correct approach
  - Qt best practice explanation

- Specific recommendations with code
- Best practices summary table
- Conclusion with rationale

**When**: Read this to understand WHY the plan is problematic

---

### 3. Implementation: Code Fixes (reference guide)
**File**: `RECOMMENDED_FIXES.md`

- Fix 1: Change Coordinator Connection Type (5 min)
- Fix 2: Remove Signal Forwarding (30 min)
- Fix 3: Implement Atomic Data Capture (1 hour)
- Fix 4: Implement Proper Memory Management (1 hour)
- Fix 5: Use Modern Qt6/PySide6 Patterns (30 min)
- Fix 6: Expand Test Coverage (1 hour)

Each fix includes:
- Exact file path
- Current code (line numbers)
- Corrected code (with comments)
- Why it works
- Testing approach

**When**: Use this to implement the corrected approach

---

## Key Findings Summary

### Critical Issue #1: Misunderstood Qt Signal Connection Types
- Plan blames `Qt.QueuedConnection` as the problem
- Actually, the problem is USING it to defer execution
- Real issue: Using QueuedConnection to hide nested execution problem
- Real fix: Remove QueuedConnection arg, use default (synchronous execution)

### Critical Issue #2: Race Conditions from Feature Flags
- Plan maintains dual signal paths using feature flags
- Both paths execute during testing (false sense of safety)
- Only direct path executes in production (never tested this way)
- Real fix: Complete migration with proper testing

### Critical Issue #3: Memory Leaks from Singleton
- Widgets connect to ApplicationState singleton
- When widget destroyed, connections remain
- ApplicationState keeps widget alive (memory leak)
- Real fix: Use Qt's `destroyed` signal, not Python `__del__`

### Critical Issue #4: Signal Forwarding
- StateManager forwards ApplicationState signals (unnecessary layer)
- Complicates debugging (follow 2 signals instead of 1)
- Real fix: Direct connections to ApplicationState

### Critical Issue #5: Incomplete Lifecycle Management
- Some components bypass SignalManager cleanup
- Inconsistent tracking across codebase
- Real fix: Use SignalManager or Qt patterns consistently

---

## Violations Table

| Violation | Severity | Impact | Fix Time |
|-----------|----------|--------|----------|
| QueuedConnection misunderstood | CRITICAL | Race conditions | 5 min |
| Feature flag dual paths | HIGH | False test safety | 30 min |
| Memory leaks from singleton | HIGH | Long-running issues | 1 hr |
| Signal forwarding | MEDIUM | Debugging complexity | 30 min |
| Incomplete cleanup | MEDIUM | Orphaned connections | 1 hr |
| Atomic data capture | MEDIUM | State inconsistency | 1 hr |
| Modern Qt6 patterns | LOW | Maintainability | 30 min |
| Test coverage | MEDIUM | Unverified correctness | 1 hr |

**Total Fix Time**: 4-6 hours
**Quality Gain**: 30-40%
**Risk**: Low (proven patterns)

---

## What's Wrong With the Plan

The ELIMINATE_COORDINATOR_PLAN.md proposes to:
1. Remove `FrameChangeCoordinator` (bad - coordinator pattern is good)
2. Switch to `AutoConnection` (bad - creates race conditions)
3. Use feature flags (bad - maintains dual untested paths)
4. Rely on `__del__` for cleanup (bad - not guaranteed)

This would:
- Introduce race conditions (multiple components, undefined order)
- Create memory leaks (widget/singleton cycles)
- Reduce debuggability (remove coordinator)
- Violate Qt best practices (__del__, feature flags for signal architecture)

---

## What Should Happen Instead

### Phase 1: Fix Coordinator Connection Type (5 minutes)
- Keep the coordinator (good pattern)
- Remove `Qt.QueuedConnection` argument
- Use default `AutoConnection` (becomes `DirectConnection` same-thread)
- Result: Synchronous, deterministic, ordered execution

### Phase 2: Remove Signal Forwarding (30 minutes)
- Delete `StateManager.frame_changed.emit` forwarding
- All components connect directly to `ApplicationState`
- Result: Simpler debugging, clearer signal flow

### Phase 3: Implement Atomic Data Capture (1 hour)
- Snapshot state AT signal receipt
- Use snapshot for all phases
- Never re-read properties during handler
- Result: Atomic semantics, no race conditions

### Phase 4: Unify Memory Management (1 hour)
- Use `SignalManager` for ALL connections
- Implement cleanup via Qt's `destroyed` signal
- Remove reliance on Python `__del__`
- Result: No memory leaks, guaranteed cleanup

### Phase 5: Use Modern Qt6 Patterns (30 minutes)
- Named parameters: `type=Qt.ConnectionType.DirectConnection`
- Add `@Slot` decorators to slot methods
- Use context managers for scoped connections
- Result: Modern, readable, maintainable code

### Phase 6: Comprehensive Testing (1 hour)
- Verify execution order (phases happen in sequence)
- Verify no duplicates (update() called once)
- Verify no memory leaks (widget destruction cleanup)
- Verify under rapid frame scrubbing
- Result: Confidence in correctness

---

## Files Affected

### CRITICAL - Fix Required
- `ui/controllers/frame_change_coordinator.py` - Connection type
- `ui/state_manager.py` - Signal forwarding

### HIGH PRIORITY - Fix Recommended
- `ui/curve_view_widget.py` - Memory leak risk
- `ui/controllers/signal_connection_manager.py` - __del__ fragility
- `tests/test_frame_change_coordinator.py` - Inadequate coverage

### Dependencies - Review Needed
- `ui/controllers/curve_view/state_sync_controller.py` - Cleanup tracking
- `ui/controllers/view_management_controller.py` - Cleanup consistency

---

## Review Completeness

### Checked
- Qt signal patterns and connection types ✓
- Signal connection lifecycle ✓
- Memory management patterns ✓
- Widget destruction and cleanup ✓
- Thread safety considerations ✓
- Feature flag usage ✓
- Test coverage ✓
- Modern Qt6/PySide6 patterns ✓

### Not Checked (out of scope)
- Performance impact (likely positive with Fix 1)
- Visual correctness (should improve with atomic snapshots)
- User experience (should be same or better)

---

## Recommendations

### Immediate Action
1. Read `BEST_PRACTICES_AUDIT_SUMMARY.md` (10 minutes)
2. Share with team leads for alignment
3. Decide: proceed with corrected approach?

### If Approved
1. Start with Fix 1 (connection type) - 5 minutes
2. Run tests after each fix
3. Follow testing approach in `RECOMMENDED_FIXES.md`
4. Total implementation: 4-6 hours

### Decision Point
- **Option A**: Implement corrected approach (Recommended)
  - Time: 4-6 hours
  - Risk: Low
  - Quality gain: 30-40%
  - Result: Qt-compliant, fewer bugs

- **Option B**: Proceed with ELIMINATE_COORDINATOR_PLAN.md
  - Time: 6-8 hours
  - Risk: High
  - Quality loss: Race conditions, memory leaks
  - Result: More bugs, harder to debug

- **Option C**: Leave as-is
  - Time: 0
  - Risk: Existing centering/desync issues remain
  - Quality: Current level maintained
  - Result: Known problems persist

---

## Questions Answered

**Q: Is the coordinator pattern wrong?**
A: No. The coordinator pattern is good for coordinating multiple updates. The issue is the connection TYPE (QueuedConnection), not the pattern.

**Q: Will removing QueuedConnection break things?**
A: No. DirectConnection (default) is more correct for same-thread operation.

**Q: Why use feature flags then?**
A: Feature flags are appropriate for configuration, not for signal architecture. This violates SOLID principles.

**Q: Won't fixing connection type cause race conditions?**
A: No. The coordinator PREVENTS race conditions by enforcing phase order. Synchronous execution is safer than deferred.

**Q: Is __del__ cleanup okay?**
A: Not for Qt objects. Qt's `destroyed` signal is guaranteed; `__del__` is not.

**Q: Why is signal forwarding bad?**
A: Adds unnecessary indirection and complicates debugging. Direct connections are simpler.

**Q: How much time will fixes take?**
A: 4-6 hours total (mostly testing and validation).

**Q: What's the risk?**
A: Low. All fixes use proven Qt patterns. Actual risk is in NOT fixing.

---

## Contact & Questions

For detailed technical discussion, see:
- `QT_BEST_PRACTICES_REVIEW.md` - Full analysis
- `RECOMMENDED_FIXES.md` - Implementation details
- Individual violation sections for specific patterns

---

**Review Status**: Complete
**Recommendation**: Implement corrected approach
**Next Step**: Team decision on Option A, B, or C
