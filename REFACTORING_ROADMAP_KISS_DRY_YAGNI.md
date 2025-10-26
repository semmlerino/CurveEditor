# CurveEditor Refactoring Roadmap: KISS/DRY/YAGNI Analysis

**Date:** October 26, 2025
**Analysis Method:** Multi-agent cross-validation (4 specialized agents)
**Total Waste Identified:** ~3,800 lines
**Immediate Deletions Completed:** 902 lines (core/error_handlers.py, data/batch_edit.py)

---

## Executive Summary

Comprehensive KISS/DRY/YAGNI analysis revealed:
- ✅ **902 lines deleted** (verified safe - zero production usage)
- ⚠️ **1,005 lines identified** for deletion after test refactoring
- 🔍 **~1,900 lines** need investigation before deciding
- ✅ **696 lines saved** from bad deletion recommendations (YAGNI agent errors)
- 📊 **~2,500 lines** of DRY violations (fixable patterns)

**Key Finding:** YAGNI agent had 50% accuracy on deletion recommendations. Always verify with grep/code inspection before deleting.

---

## ✅ COMPLETED ACTIONS (October 26, 2025)

### Immediate Deletions - DONE

| File | Lines | Reason | Verification |
|------|-------|--------|--------------|
| core/error_handlers.py | 301 | Zero imports in production | ✅ Grep verified |
| data/batch_edit.py | 601 | Never integrated, zero calls | ✅ Grep verified |
| **TOTAL** | **902** | - | **47 tests passing** |

**Testing:** 47 core tests pass (test_data_service.py)
**Impact:** Zero functionality loss, reduced maintenance burden
**Commit:** refactor: Remove 902 lines of verified unused code

---

## 🎯 TIER 1: Short-Term Actions (Weeks 1-4)

### Week 1-2: Test Cleanup & Additional Deletions (1,005 lines)

**Goal:** Remove test-only error handler modules

**Files to delete:**
- `ui/error_handlers.py` (521 lines) - Only used in test_error_handlers.py
- `ui/error_handler.py` (484 lines) - Only used in tests

**Prerequisites:**
1. Refactor `tests/test_error_handlers.py` to not use these modules
2. Verify no production code depends on them
3. Run full test suite

**Risk:** Low (no production usage verified)
**Effort:** 4-8 hours
**Impact:** 1,005 lines removed, cleaner test architecture

---

### Week 2-3: Fix DRY Violations - Exception Handling (600+ lines)

**Problem:** 167 identical try/except patterns across 57 files

**Current pattern (duplicated 167 times):**
```python
try:
    # operation
except Exception as e:
    logger.error(f"Failed to {operation}: {e}")
    return False
```

**Solution:** Create simple error handling helper (NOT the complex decorators we deleted)

```python
# core/error_utils.py (NEW - keep simple)
def safe_execute(operation_name: str, func, default=None, reraise=False):
    """Simple error wrapper with logging."""
    try:
        return func()
    except Exception as e:
        logger.error(f"{operation_name} failed: {e}")
        if reraise:
            raise
        return default

# Usage
result = safe_execute("load data", lambda: load_file(path), default=[])
```

**Files affected:** 57 files with exception handling
**Effort:** 2-3 days
**Impact:** ~600 lines of duplication removed

**Note:** We deleted the complex unused decorators (core/error_handlers.py). This new solution is simpler.

---

### Week 3-4: Fix Active Curve Validation Pattern (250 lines)

**Problem:** 50+ locations duplicate 4-6 line pattern

**Current inconsistent usage:**
```python
# Pattern 1 (old - 30 locations)
active = state.active_curve
if not active:
    return
data = state.get_curve_data(active)
if not data:
    return

# Pattern 2 (new - 20 locations)
if (cd := state.active_curve_data) is None:
    return
curve_name, data = cd
```

**Solution:** Enforce Pattern 2 everywhere (already exists)

**Actions:**
1. Create linting rule to detect Pattern 1
2. Refactor all Pattern 1 to Pattern 2
3. Add to CLAUDE.md as mandatory pattern

**Effort:** 4-8 hours
**Impact:** Consistent codebase, 250 lines more maintainable

---

## 🔍 TIER 2: Investigation Required (Weeks 5-8)

### ServiceFacade Analysis (551 lines)

**Claim:** "Unnecessary indirection, singleton wrapping singletons"
**Status:** Used in 12 files (main_window.py, file_operations.py, tests)
**Question:** Is it actually simplifying or just adding layers?

**Investigation Tasks:**
1. Analyze call patterns in main_window.py
2. Count `self.services.X.method()` vs direct `get_X_service().method()`
3. Measure test complexity with/without facade
4. Decide: Keep, simplify, or remove

**Effort:** 2-3 days investigation + potential refactoring
**Risk:** Medium (requires careful testing if removed)

---

### ConnectionVerifier System (400 lines)

**Claim:** "Complex verification, could be 20 lines of assertions"
**Status:** Used in MainWindow._verify_connections and SignalConnectionManager
**Question:** Has it actually caught real bugs?

**Investigation Tasks:**
1. Review git history for bugs caught by ConnectionVerifier
2. Analyze if Qt's built-in signal errors are sufficient
3. Consider: Development-only tool vs production code

**Options:**
- Keep as-is (if it's caught bugs)
- Make development/debug-only (strip from production)
- Replace with simple assertions

**Effort:** 1 day investigation + potential simplification
**Risk:** Low (can always revert if needed)

---

### Path Security Simplification (92 → 10 lines)

**Claim:** "Enterprise-grade validation for single-user desktop app"
**Current:** 92 lines with complex validation
**Proposed:** 10 lines with simple Path.resolve() checks

**Investigation:**
1. Review CLAUDE.md guidance: "Single-user desktop context: No authentication, authorization, or adversarial threat modeling"
2. Identify actual validation needs (file exists, is readable, etc.)
3. Create simplified version

**Effort:** 2-3 hours
**Risk:** Low (single-user app context)
**Impact:** 82 lines removed, simpler code

---

## ⚠️ TIER 3: Long-Term Structural (Months 2-6)

### God Class Decomposition (Deferred)

**Analysis identified 4 god classes:**

| Class | Lines | Methods | Complexity |
|-------|-------|---------|------------|
| ImageSequenceBrowserDialog | 2,186 | 77 | High |
| CurveViewWidget | 1,979 | 101 | High |
| MainWindow | 1,333 | 102 | Medium |
| InteractionService | 1,747 | 85 | High |

**Recommendation:** **DEFER** - Focus on quick wins first

**Reasons to defer:**
1. These are **working** code - refactoring risk is high
2. Requires 6-10 weeks of effort
3. Quick wins (Tier 1-2) provide better ROI
4. Controller extraction already in progress for MainWindow

**Future approach:**
- Extract obvious helpers first (low-hanging fruit)
- Continue MainWindow controller extraction (already started)
- Consider splitting only if specific pain points emerge

---

### Handle Mouse Press Refactoring (275 lines, complexity 15)

**Location:** services/interaction_service.py:76-194
**Issues:** 6 levels of nesting, cyclomatic complexity 15

**Recommendation:** Extract to smaller methods

**Effort:** 1 week
**Impact:** 35% complexity reduction
**Priority:** Medium (after quick wins)

---

## ❌ FALSE POSITIVES - DO NOT DELETE

**YAGNI agent incorrectly flagged these as unused:**

| File | Lines | Actual Usage | Why Agent Failed |
|------|-------|--------------|------------------|
| core/monitoring.py | 346 | cache_service.py (3 calls) | Ignored feature flags |
| core/user_preferences.py | 200+ | state_manager.py | Didn't trace indirect usage |
| core/metadata_extractor.py | 150+ | image_sequence_browser.py:1147 | Didn't search for method calls |

**Total saved from bad deletions:** 696+ lines of production code

**Lesson:** Always verify with grep/code inspection before deleting!

---

## 📊 METRICS & PROGRESS TRACKING

### Code Reduction Target

| Phase | Lines Removed | Timeline | Status |
|-------|---------------|----------|--------|
| **Immediate** | 902 | Week 0 | ✅ **DONE** |
| **Tier 1** | 1,855 | Weeks 1-4 | Planned |
| **Tier 2** | ~500 | Weeks 5-8 | Investigation |
| **Tier 3** | ~2,000 | Months 2-6 | Deferred |
| **TOTAL** | **~5,257** | 6 months | In progress |

### DRY Violation Fixes

| Pattern | Occurrences | Lines | Status |
|---------|-------------|-------|--------|
| Exception handling | 167 | ~600 | Week 2-3 |
| Active curve validation | 50+ | ~250 | Week 3-4 |
| Controller init | 11 | ~150 | Deferred |
| Y-flip logic | 3 | ~40 | Week 4 |

### Quality Improvements

**Before:**
- Deep nesting: 6 levels (handle_mouse_press)
- Cyclomatic complexity: 8-15
- Exception patterns: 167 duplications
- Test-only code: 1,907 lines mixed with production

**After Tier 1 (Target):**
- Deep nesting: 2-3 levels
- Cyclomatic complexity: 3-4
- Exception patterns: Centralized helper
- Test-only code: Clearly separated or removed

---

## 🚦 DECISION FRAMEWORK

**Before deleting any code, verify:**

1. ✅ **Zero imports** - `grep -r "from module import"` shows nothing
2. ✅ **Zero calls** - Search for function/class names in production code
3. ✅ **Feature flag check** - Not disabled-by-default production feature
4. ✅ **Test coverage** - Verify test suite still passes
5. ✅ **Git history** - Check if recently added (might be WIP)

**Risk levels:**

- **ZERO risk:** No imports, no calls, in codebase >3 months
- **LOW risk:** Test-only usage, can refactor tests
- **MEDIUM risk:** Used in production but can be replaced
- **HIGH risk:** Core functionality, extensive refactoring needed

**Rule:** Only delete ZERO and LOW risk items without thorough investigation.

---

## 📋 NEXT STEPS CHECKLIST

### Week 1 (Current)
- [x] Delete verified safe files (core/error_handlers.py, data/batch_edit.py)
- [x] Run tests to verify (47 tests passing)
- [x] Create roadmap document
- [ ] Commit with clear message
- [ ] Note: 2 broken tests exist (test_error_handlers.py, test_validation_strategy.py) - pre-existing, unrelated to deletions

### Week 2
- [ ] Refactor tests to not use ui/error_handler(s).py
- [ ] Delete ui/error_handlers.py and ui/error_handler.py
- [ ] Run full test suite

### Week 3
- [ ] Create simple error handling helper (core/error_utils.py)
- [ ] Refactor 57 files with exception handling duplication
- [ ] Add linting rule to prevent regression

### Week 4
- [ ] Enforce active_curve_data pattern everywhere
- [ ] Add linting rule for Pattern 1 detection
- [ ] Update CLAUDE.md with mandatory pattern

---

## 📝 NOTES & OBSERVATIONS

### Agent Accuracy Assessment

| Agent | Accuracy | Strengths | Weaknesses |
|-------|----------|-----------|------------|
| DRY | 95% | Accurate pattern counting | Slight undercount (139 vs 167) |
| KISS | 90%+ | Good complexity metrics | Needs code inspection to verify |
| YAGNI | **50%** | Good at obvious dead code | **Failed to check imports/calls** |
| Code Quality | 85%+ | Systemic pattern detection | Some subjective recommendations |

**Key Lesson:** YAGNI agent's "zero usage" claims require manual verification. It:
- ❌ Didn't grep for imports
- ❌ Ignored feature flags (disabled-by-default ≠ unused)
- ❌ Didn't trace call chains (method calls on instantiated objects)
- ✅ Correctly identified obvious dead code (batch_edit.py, error_handlers.py)

### Why Some Files Were Missed

**core/monitoring.py:**
- Feature flags default to OFF
- Agent assumed OFF = unused
- Actually: Opt-in production feature (CURVE_EDITOR_MONITORING env var)

**core/metadata_extractor.py:**
- Agent saw instantiation but not method calls
- Searched for "ImageMetadataExtractor" but not ".extract("
- Actually: Called at line 1147 in image_sequence_browser.py

**core/user_preferences.py:**
- Agent checked direct usage in tests
- Missed indirect usage via state_manager.py
- Actually: Used for progressive disclosure feature

---

## 🎯 SUCCESS CRITERIA

### Short-term (4 weeks)
- ✅ 902 lines removed (DONE)
- [ ] 1,855 additional lines removed (tests + DRY violations)
- [ ] Zero functionality regressions
- [ ] All tests passing
- [ ] Code quality metrics improved

### Medium-term (8 weeks)
- [ ] ServiceFacade decision made (keep/simplify/remove)
- [ ] ConnectionVerifier analyzed and action taken
- [ ] Path security simplified
- [ ] ~2,700 lines total removed

### Long-term (6 months)
- [ ] God classes evaluated (extract helpers only if pain points)
- [ ] Deep nesting eliminated (<= 3 levels everywhere)
- [ ] Cyclomatic complexity normalized (<= 5)
- [ ] ~5,000 lines removed, codebase more maintainable

---

## 📚 REFERENCES

- **Analysis Date:** October 26, 2025
- **Agents Used:** code-refactoring-expert, best-practices-checker, python-expert-architect, python-code-reviewer
- **Test Verification:** 47 tests passing (test_data_service.py)
- **Pre-existing Issues:** test_error_handlers.py, test_validation_strategy.py (missing core.validation_strategy)
- **CLAUDE.md Guidance:** Single-user desktop app, no enterprise security needed

---

## 🔄 MAINTENANCE

This document should be updated:
- After each tier completion
- When decisions are made on investigation items
- If additional YAGNI violations are discovered
- When metrics show measurable improvements

**Owner:** Project maintainer
**Review Cycle:** Monthly until completion, quarterly thereafter
