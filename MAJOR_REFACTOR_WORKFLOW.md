# 🔄 Major Refactor Workflow

**Audience:** Claude Code (orchestrator)
**Purpose:** Execute safe, incremental major refactoring with comprehensive validation

---

## When to Use This Workflow

**Major Refactor Indicators:**
- Affects multiple files/modules
- Structural or architectural changes
- High risk of breaking existing functionality
- User keywords: "major refactor", "restructure", "redesign", "technical debt"

**Not for:**
- Single file cleanup → Use standard code quality pattern
- Simple bug fixes → Use bug investigation pattern
- Adding features → Use feature implementation pattern

---

## Pre-Flight: Determine Refactor Type

| Refactor Type | Indicators | Primary Agent |
|---------------|------------|---------------|
| **Structural** | Code organization, duplication, coupling, class/method extraction | `code-refactoring-expert` |
| **Architectural** | Design patterns, async/concurrency, framework changes, API redesign | `python-expert-architect` |

**Decision Rule:** If user mentions "architecture", "design patterns", "async", or changes affect core design → use `python-expert-architect`. Otherwise → `code-refactoring-expert`.

---

## The Workflow

### **Phase 1: Comprehensive Assessment** ⚡ PARALLEL

**Agents:** `python-code-reviewer` + `type-system-expert` + `performance-profiler` (if relevant)

**Why Parallel:** All read-only, no conflicts possible

**Command Template:**
```bash
"Use python-code-reviewer and type-system-expert in parallel to comprehensively analyze [module/component]"
# Add performance-profiler if performance mentioned
```

**Outputs:**
- Bugs and design issues (python-code-reviewer)
- Type errors and type safety gaps (type-system-expert)
- Performance bottlenecks (performance-profiler, if used)
- Current test coverage assessment

**Duration:** Fast (parallel execution)

---

### **Phase 2: Test Safety Net** 🛡️ CRITICAL - SEQUENTIAL

**Check:** Does comprehensive test coverage exist?

**Validation:**
```bash
pytest --cov=[module] --cov-report=term-missing
```

**Decision Tree:**
```
Coverage ≥ 80% AND critical paths covered?
├─ YES → Proceed to Phase 3
└─ NO → Add tests FIRST
   └─ Agent: test-development-master
      └─ "Use test-development-master to add comprehensive tests for [module] covering [critical functionality]"
      └─ Validate: pytest (all tests must pass)
```

**⚠️ GOLDEN RULE: NEVER refactor without comprehensive tests**

**Why Critical:**
- Tests are your safety net
- Without tests, you can't verify refactor didn't break functionality
- Adding tests after refactor = testing the refactored code, not the original behavior

---

### **Phase 3: Planning** 📋 SEQUENTIAL

**Agent:** `code-refactoring-expert` (structural) OR `python-expert-architect` (architectural)

**Command Template:**
```bash
# Structural refactor:
"Use code-refactoring-expert to analyze findings from assessment and create detailed refactoring plan for [module]"

# Architectural refactor:
"Use python-expert-architect to design new architecture for [module] addressing [issues]"
```

**Expected Outputs:**
- Refactoring strategy
- Incremental transformation plan (what changes in each step)
- Dependency order (what must change first)
- Risk assessment
- Estimated increments

**User Action:** Review and approve plan before execution

---

### **Phase 4: Incremental Execution** 🔄 SEQUENTIAL

**Agent:** Same agent from Phase 3

**The Increment Loop:**

```bash
# Increment 1
"Use [agent] to execute increment 1: [specific transformation]"

# Validate increment 1
pytest                    # All tests must pass
basedpyright             # No new type errors
git add . && git commit -m "refactor: [what changed]"

# Increment 2
"Use [agent] to execute increment 2: [specific transformation]"

# Validate increment 2
pytest                    # All tests must pass
basedpyright             # No new type errors
git add . && git commit -m "refactor: [what changed]"

# Repeat until all increments complete...
```

**Increment Strategies:**

| Strategy | Use When | Pattern |
|----------|----------|---------|
| **By Transformation Type** | Clear refactoring sequence | Extract methods → Move to classes → Update dependencies |
| **By Module/Component** | Loosely coupled modules | Module A → Module B → Integration points |
| **By Layer** | Layered architecture | Data layer → Business logic → Presentation |
| **By Dependency Order** | Tight coupling | Dependencies → Dependents |

**Rules:**
1. **One increment at a time** - Never batch multiple transformations
2. **Always validate** - pytest && basedpyright after EVERY increment
3. **Never proceed with failures** - Fix before moving to next increment
4. **Always commit** - Each successful increment = atomic commit
5. **Working code only** - Each increment leaves codebase in working state

**If Validation Fails:**
```bash
# Tests fail or type errors appear
"Use [agent] to fix [specific issue] in increment [N]"
pytest && basedpyright  # Re-validate
# Only proceed when all validation passes
```

---

### **Phase 5: Final Validation** ✅ PARALLEL + SEQUENTIAL

**Step 1: Parallel Review (FAST)**
```bash
"Use python-code-reviewer and type-system-expert in parallel to review refactored [module]"
```

**Step 2: Address Findings (if any)**
```bash
# If issues found:
"Use [appropriate-agent] to address [specific issues]"
pytest && basedpyright
```

**Step 3: Full Validation**
```bash
# Run complete test suite
pytest

# Full type check
basedpyright

# Manual smoke test for critical functionality (if needed)
```

---

## Complete Example: "Refactor the messy auth module"

**User Request:** "Refactor the auth module - it's messy and has technical debt"

**Classification:** Major refactor (structural)

**Execution:**

```bash
# Phase 1: Assessment (PARALLEL - ~2 min)
"Use python-code-reviewer and type-system-expert in parallel to analyze the auth module"

# Results:
# - 12 design issues (tight coupling, god class, duplicated validation)
# - 8 type errors
# - Test coverage: 65%

# Phase 2: Test Safety Net
pytest --cov=auth --cov-report=term-missing
# Coverage: 65% - missing tests for edge cases and error paths

"Use test-development-master to add tests for auth module covering edge cases, error handling, and validation paths"
pytest  # All tests pass ✓

# Phase 3: Planning
"Use code-refactoring-expert to create refactoring plan for auth module addressing the 12 design issues found"

# Plan presented:
# Increment 1: Extract validation logic into separate validator classes
# Increment 2: Split AuthManager god class into AuthService, TokenService, SessionService
# Increment 3: Remove duplicated validation code
# Increment 4: Update imports and integration points

# User approves plan

# Phase 4: Incremental Execution
"Use code-refactoring-expert to execute increment 1: extract validation logic"
pytest && basedpyright  # Pass ✓
git commit -m "refactor(auth): extract validation logic to validators"

"Use code-refactoring-expert to execute increment 2: split AuthManager into focused services"
pytest && basedpyright  # Pass ✓
git commit -m "refactor(auth): split AuthManager into AuthService, TokenService, SessionService"

"Use code-refactoring-expert to execute increment 3: remove duplicated validation"
pytest && basedpyright  # Pass ✓
git commit -m "refactor(auth): remove duplicated validation code"

"Use code-refactoring-expert to execute increment 4: update imports and integration"
pytest && basedpyright  # Pass ✓
git commit -m "refactor(auth): update imports and integration points"

# Phase 5: Final Validation
"Use python-code-reviewer and type-system-expert in parallel to review refactored auth module"

# Results: Clean! No issues found.

pytest && basedpyright  # Final validation ✓
```

**Outcome:** Auth module refactored with 4 atomic commits, all tests passing, zero breakage.

---

## Common Pitfalls & Solutions

| Pitfall | Consequence | Solution |
|---------|-------------|----------|
| **Refactoring without tests** | Can't verify no breakage | Phase 2: Add tests FIRST |
| **Too large increments** | Hard to debug failures | Small, focused increments (one transformation type) |
| **Mixing concerns** | Confusion, hard to review | Separate bugs → refactor → features |
| **Skipping validation** | Accumulating errors | pytest && basedpyright after EVERY increment |
| **No rollback plan** | Can't undo bad changes | Git commit after each validated increment |
| **Parallel modifications to dependent files** | Race conditions, broken imports | Sequential execution with dependency order |
| **Breaking API contracts** | Breaking consumer code | Maintain backward compatibility or deprecation cycle |

---

## Workflow Variants

### **Variant A: Refactor with Good Test Coverage**

**Scenario:** Module has ≥80% coverage, tests are comprehensive

**Workflow:**
```
Phase 1: Assessment (PARALLEL)
  ↓
Phase 2: Verify coverage ✓
  ↓
Phase 3: Planning
  ↓
Phase 4: Incremental execution
  ↓
Phase 5: Final validation
```

**Duration:** Fast (skip test creation)

---

### **Variant B: Refactor with Poor/No Test Coverage**

**Scenario:** Module has <80% coverage or missing critical tests

**Workflow:**
```
Phase 1: Assessment (PARALLEL)
  ↓
Phase 2: Add comprehensive tests FIRST
  ↓
Phase 3: Planning
  ↓
Phase 4: Incremental execution
  ↓
Phase 5: Final validation
```

**Duration:** Longer (test creation required) but SAFER

---

### **Variant C: Architectural Refactor**

**Scenario:** Design patterns, async/concurrency, framework changes

**Workflow:**
```
Phase 1: Assessment (PARALLEL + performance-profiler)
  ↓
Phase 2: Test coverage check/add
  ↓
Phase 3: Architecture design (python-expert-architect)
  ↓ (User reviews/approves)
Phase 4: Incremental execution BY LAYER
  ↓
Phase 5: Final validation + integration testing
```

**Special Considerations:**
- User approval required for architecture design
- Longer planning phase
- May require API versioning strategy
- Integration testing critical

---

## Critical Success Factors

### ✅ Do This

1. **Always test-first** - Add comprehensive tests before refactoring
2. **Always incremental** - Small, focused steps with validation
3. **Always validate** - pytest && basedpyright after EVERY increment
4. **Always commit** - Create rollback points after successful increments
5. **Always sequential execution** - One increment at a time
6. **Always fix bugs separately** - Bug fixes ≠ refactoring ≠ new features
7. **Always respect dependencies** - Refactor dependencies before dependents

### ❌ Never Do This

1. **Never refactor without tests** - This is Russian roulette
2. **Never skip validation steps** - Accumulating errors = debugging nightmare
3. **Never big-bang refactors** - Too risky, impossible to debug
4. **Never parallel modifications to same/dependent files** - Guaranteed conflicts
5. **Never mix refactoring with functional changes** - Confusing and risky
6. **Never proceed with failing tests** - Fix immediately before next increment

---

## Integration with Other Workflows

**Before Major Refactor:**
- If bugs exist → Use **bug investigation pattern** to fix first
- If performance critical → Use **performance optimization pattern** to profile first

**After Major Refactor:**
- If type errors remain → Use `type-system-expert` to clean up
- If new features needed → Use **feature implementation pattern**
- If security critical → Use `python-code-reviewer` with security focus

**Chains Well With:**
- **Code Quality Pattern** (before refactor: identify issues)
- **Testing Pattern** (during refactor: ensure coverage)
- **Type System Pattern** (after refactor: fix type issues)

---

## Quick Reference: Major Refactor Checklist

**Pre-Flight:**
- [ ] Determine refactor type (structural vs architectural)
- [ ] Select primary agent (code-refactoring-expert vs python-expert-architect)

**Phase 1: Assessment**
- [ ] Run python-code-reviewer + type-system-expert in parallel
- [ ] Review all findings
- [ ] Assess test coverage

**Phase 2: Test Safety Net**
- [ ] Check coverage: `pytest --cov=[module]`
- [ ] If <80%, add tests with test-development-master
- [ ] Validate all tests pass

**Phase 3: Planning**
- [ ] Agent analyzes and creates refactoring plan
- [ ] Plan includes increments and dependency order
- [ ] User reviews and approves plan

**Phase 4: Execution (REPEAT FOR EACH INCREMENT)**
- [ ] Execute one increment
- [ ] Run pytest (must pass)
- [ ] Run basedpyright (no new errors)
- [ ] Git commit with descriptive message
- [ ] Repeat for next increment

**Phase 5: Final Validation**
- [ ] Parallel review (python-code-reviewer + type-system-expert)
- [ ] Address any findings
- [ ] Full test suite passes
- [ ] Full type check passes
- [ ] Manual smoke test (if critical)

---

## Related Documentation

- **[AGENT_ORCHESTRATION_GUIDE.md](AGENT_ORCHESTRATION_GUIDE.md)** - General orchestration patterns
- **[ORCHESTRATION.md](ORCHESTRATION.md)** - Parallel execution safety
- **[QUICK-REFERENCE.md](QUICK-REFERENCE.md)** - Agent capabilities
