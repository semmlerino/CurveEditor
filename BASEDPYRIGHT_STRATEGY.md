# Basedpyright Configuration Strategy

**Last Updated:** October 2025
**Status:** Active Strategy Document

## Executive Summary

CurveEditor currently has **0 production type errors** but faces 14,719 warnings from basedpyright. This document provides a pragmatic, phased approach to improve type safety without disrupting development workflow.

**Key Insight:** Only ~476 warnings (3%) are actionable per current config. The rest (97%) are intentionally suppressed Qt type stub noise.

---

## Current State Analysis

### Error Breakdown (20 total)
- **0 production errors** ✅
- **20 test infrastructure errors:**
  - 3 in `test_curve_view.py`: Index out of range (PointTuple3 vs PointTuple4)
  - 17 protocol compliance: TestSignal incompatible with SignalProtocol

### Warning Distribution (14,719 total)

#### Actionable Warnings (~476, 3% of total)

**Critical Issues (47):**
- 7 `reportRedeclaration` - Duplicate declarations (potential bugs)
- 39 `reportUnnecessaryComparison` - Logic errors (e.g., always True)
- 1 `reportImportCycles` - Circular import

**Code Quality (407):**
- 174 `reportUnnecessaryTypeIgnoreComment` - Obsolete type ignores
- 38 `reportUnusedImport` - Dead imports
- 69 `reportUnusedVariable` - Dead code
- 31 `reportPrivateLocalImportUsage` - Wrong import locations
- 118 `reportImplicitOverride` - Missing @override decorators
- 29 `reportUnnecessaryIsInstance` - Redundant type checks

**Development Hygiene (1,155):**
- 321 `reportUnannotatedClassAttribute` - Missing type annotations
- 403 `reportPrivateUsage` - Protected methods (mostly false positives in signals)
- 331 `reportUnusedParameter` - Unused params (often callbacks)
- 460 `reportUnusedCallResult` - Unused return values (Qt signals)

#### Intentionally Suppressed (~13,088, 89% of total)

These are set to `"none"` in config and expected:
- 4,363 `reportUnknownMemberType` - Qt type stub limitations
- 2,150 `reportAny` - Test mocks intentionally use Any
- 1,810 `reportUnknownParameterType` - Qt stub gaps
- 1,801 `reportMissingParameterType` - Qt stub gaps
- 1,163 `reportUnknownArgumentType` - Qt stub gaps
- 1,134 `reportUnknownVariableType` - Qt stub gaps
- 165 `reportExplicitAny` - Test infrastructure

**Note:** PySide6 stubs ARE installed (PySide6-stubs 6.7.3.0). The "unknown" warnings persist due to stub limitations, not missing installation.

---

## Recommended Strategy: 4-Phase Approach

### Phase 1: Fix Critical Issues (Week 1)

**Goal:** Zero errors, fix obvious bugs

**Tasks:**
1. Fix 20 test infrastructure errors
2. Fix 7 `reportRedeclaration` issues
3. Fix 39 `reportUnnecessaryComparison` logic errors
4. Fix remaining import cycle

**Commands:**
```bash
# Fix errors
./bpr --errors-only

# Fix specific categories
./bpr 2>&1 | grep reportRedeclaration
./bpr 2>&1 | grep reportUnnecessaryComparison
```

**Success Criteria:** `./bpr --errors-only` shows 0 errors

---

### Phase 2: Baseline Strategy (Week 1-2)

**Goal:** Freeze current warnings, prevent regression

**Why Baseline Files?**
- Existing violations → shown as "hints" in IDE (not blocking)
- **NEW violations are blocked** (prevents regression)
- Team works without 14k warning noise
- Incremental improvement without big-bang refactor

**Implementation:**

```bash
# 1. Create baseline file
./bpr --writebaseline

# 2. Update basedpyrightconfig.json
```

Add to config:
```json
{
  "baselineFile": ".basedpyright-baseline.json"
}
```

```bash
# 3. Commit baseline (track progress over time)
git add .basedpyright-baseline.json basedpyrightconfig.json
git commit -m "chore: establish basedpyright baseline for incremental improvement"
```

**Success Criteria:**
- Baseline file exists
- New violations fail CI, existing violations are hints
- Development continues without warning noise

---

### Phase 3: Gradual Improvement (Ongoing)

**Goal:** Fix warnings by category, shrink baseline

**Priority Order:**

#### Sprint 1: Quick Wins (212 warnings, ~2 weeks)
```bash
# Remove obsolete type ignores (174)
./bpr 2>&1 | grep reportUnnecessaryTypeIgnoreComment

# Clean unused imports (38)
./bpr 2>&1 | grep reportUnusedImport

# Remove unused variables (69)
./bpr 2>&1 | grep reportUnusedVariable
```

**After each fix:**
```bash
./bpr --writebaseline  # Update baseline
git add .basedpyright-baseline.json
git commit -m "chore: remove obsolete type ignores from baseline"
```

#### Sprint 2: Code Quality (217 warnings, ~3 weeks)
```bash
# Fix import locations (31)
./bpr 2>&1 | grep reportPrivateLocalImportUsage

# Add @override decorators (118)
./bpr 2>&1 | grep reportImplicitOverride

# Remove redundant isinstance (29)
./bpr 2>&1 | grep reportUnnecessaryIsInstance

# Add type annotations to class attributes (39)
./bpr 2>&1 | grep reportUnannotatedClassAttribute | head -39
```

#### Sprint 3+: Remaining Categories (case-by-case)
- Evaluate reportPrivateUsage (403) - many are false positives for Qt signals
- Consider reportUnusedParameter (331) - often intentional for callback signatures
- Assess reportUnusedCallResult (460) - Qt signals don't need return values

**Weekly Progress Tracking:**
```bash
# Baseline size (should decrease)
cat .basedpyright-baseline.json | grep -c '"file"'

# Current vs baseline violations
./bpr --summary
```

---

### Phase 4: Enforce Strictness on New Code (Long-term)

**Goal:** Higher standards for new/refactored code, legacy as-is

**Use `"strict"` Array:**

```json
{
  "strict": [
    "ui/controllers/curve_view/",     // New controller architecture
    "stores/application_state.py",    // Recently migrated
    "core/commands/"                  // Well-tested command pattern
  ],
  "typeCheckingMode": "recommended"  // Keep existing code as-is
}
```

**Expansion Strategy:**
- New features → start in `strict` paths
- Refactored modules → graduate to `strict` after cleanup
- Legacy code → stays in `recommended` until touched

**Benefits:**
- New code: strict typing from day 1
- Legacy code: no disruption
- Gradual migration: module by module

---

## Configuration Best Practices

### 1. Modular Configuration (Use Extends)

**Structure:**
```
basedpyrightconfig.base.json  # Shared settings
basedpyrightconfig.json        # Project-specific overrides
```

**Example:**

`basedpyrightconfig.base.json`:
```json
{
  "typeCheckingMode": "recommended",
  "pythonVersion": "3.12",
  "pythonPlatform": "Linux",
  "venvPath": ".",
  "venv": "venv",
  "useLibraryCodeForTypes": true
}
```

`basedpyrightconfig.json`:
```json
{
  "extends": "./basedpyrightconfig.base.json",
  "baselineFile": ".basedpyright-baseline.json",
  "strict": ["ui/controllers/curve_view/"],

  "include": ["core", "ui", "services", "tests"],
  "exclude": ["**/archive", "**/.cache", "**/build"]
}
```

**Benefits:**
- DRY principle for team configs
- Easy to override per-environment
- Clear separation of shared vs. project settings

---

### 2. Diagnostic Severity Strategy

**Current config is good, consider these upgrades:**

```json
{
  // ERRORS - Block commits
  "reportUndefinedVariable": "error",
  "reportRedeclaration": "error",                    // ADD: Prevent duplicate declarations
  "reportIgnoreCommentWithoutRule": "error",         // KEEP: Require specific rules
  "reportIncompatibleMethodOverride": "error",       // KEEP: Type safety

  // WARNINGS - Fail CI with --warnings flag
  "reportUnnecessaryTypeIgnoreComment": "warning",   // KEEP: Remove obsolete ignores
  "reportUnnecessaryComparison": "warning",          // KEEP: Logic errors
  "reportUnusedImport": "warning",                   // KEEP: Dead code
  "reportUnusedVariable": "warning",                 // KEEP: Dead code
  "reportPrivateUsage": "warning",                   // KEEP: But many false positives

  // NONE - Intentionally suppressed
  "reportAny": "none",                               // KEEP: Test mocks need Any
  "reportUnknownMemberType": "none",                 // KEEP: Qt stub limitations
  "reportUnknownParameterType": "none",              // KEEP: Qt stub gaps
  "reportUnknownVariableType": "none",               // KEEP: Qt stub gaps
  "reportUnknownArgumentType": "none"                // KEEP: Qt stub gaps
}
```

**Severity Meanings (from basedpyright docs):**
- `"error"` - CLI exits 1 (blocks commits)
- `"warning"` - CLI exits 1 only with `--warnings` flag
- `"information"` - Never fails CLI
- `"hint"` - IDE only, not in CLI (used for baseline)
- `"none"` - Completely disabled

---

### 3. CI/CD Integration

**Local Development:**
```bash
# Warnings are informational
./bpr
```

**CI Pipeline:**
```bash
# Warnings fail the build
./bpr --warnings

# Or use config setting
```

Add to config for CI:
```json
{
  "failOnWarnings": true  // Equivalent to --warnings flag
}
```

**Recommended:** Use `--warnings` flag in CI only, keep config `failOnWarnings: false` for local dev.

---

### 4. Per-File Overrides

For specific files that need different rules:

```python
# Top of file - enable strict mode
# pyright: strict

# Or override specific rules
# pyright: reportPrivateUsage=false, reportUnusedParameter=false

# Or suppress all diagnostics (avoid)
# pyright: ignore
```

**Use sparingly:** Prefer config-level settings over per-file overrides.

---

## Practical Implementation Guide

### Week 1: Foundation

**Day 1: Setup Baseline**
```bash
# Current state snapshot
./bpr --summary > baseline_before.txt

# Create baseline
./bpr --writebaseline

# Add to config
cat >> basedpyrightconfig.json << 'EOF'
  "baselineFile": ".basedpyright-baseline.json",
EOF

# Commit
git add .basedpyright-baseline.json basedpyrightconfig.json baseline_before.txt
git commit -m "chore: establish basedpyright baseline (20 errors, 14719 warnings)"
```

**Day 2-3: Fix Critical Errors**
```bash
# Fix 20 test infrastructure errors
./bpr --errors-only

# Verify
./bpr --errors-only  # Should show 0 errors
git commit -m "fix: resolve 20 test infrastructure type errors"
```

**Day 4-5: Fix Logic Bugs**
```bash
# Fix redeclarations (7)
./bpr 2>&1 | grep reportRedeclaration

# Fix unnecessary comparisons (39)
./bpr 2>&1 | grep reportUnnecessaryComparison

# Update baseline
./bpr --writebaseline
git commit -m "fix: resolve redeclarations and logic errors"
```

---

### Week 2-4: Quick Wins

**Sprint 1: Remove Obsolete Type Ignores (174)**
```bash
# Find all unnecessary ignores
./bpr 2>&1 | grep reportUnnecessaryTypeIgnoreComment > unnecessary_ignores.txt

# Fix them (remove the ignore comments)
# ... edit files ...

# Update baseline
./bpr --writebaseline
git commit -m "chore: remove 174 obsolete type ignore comments"
```

**Sprint 2: Clean Dead Code (107)**
```bash
# Unused imports (38)
./bpr 2>&1 | grep reportUnusedImport

# Unused variables (69)
./bpr 2>&1 | grep reportUnusedVariable

# Fix and commit
./bpr --writebaseline
git commit -m "chore: remove unused imports and variables"
```

---

### Ongoing: Incremental Improvement

**Monthly Cycle:**
1. Pick a warning category
2. Fix all instances
3. Update baseline
4. Track progress

**Template PR:**
```markdown
## Type Safety Improvement: [Category]

**Category:** reportPrivateLocalImportUsage
**Count:** 31 → 0

### Changes
- Fixed import locations to use public API
- Updated 31 files to import from protocols.ui instead of services.service_protocols

### Verification
- ✅ Baseline updated: 31 fewer warnings
- ✅ All tests pass
- ✅ No new violations introduced

### Baseline Progress
- Before: 14,719 warnings
- After: 14,688 warnings (-31)
```

---

## Success Metrics

### Primary Metrics

**1. Error Count (Target: 0)**
```bash
./bpr --errors-only | tail -1
# Goal: "0 errors, 0 warnings, 0 notes"
```

**2. Baseline Size (Target: Decreasing)**
```bash
cat .basedpyright-baseline.json | grep -c '"file"'
# Track weekly: Should decrease over time
```

**3. Warning Velocity (Target: Negative)**
```bash
# Week over week change
./bpr --summary | grep warnings
# Goal: Fewer warnings each week
```

### Secondary Metrics

**4. Strict Path Coverage (Target: Increasing)**
```bash
grep -c "strict" basedpyrightconfig.json
# Track monthly: More paths → stricter codebase
```

**5. Config Cleanliness**
```bash
# Count of "none" suppressions (Target: Stable)
grep ': "none"' basedpyrightconfig.json | wc -l
# Should stay constant (intentional suppressions)
```

**6. CI Health**
```bash
# Local vs CI parity
./bpr --warnings
# Goal: Passes locally = Passes in CI
```

---

## Troubleshooting

### Issue: Baseline Not Working

**Symptom:** Still see all warnings after adding baseline

**Solution:**
```bash
# Verify baseline path in config
grep baselineFile basedpyrightconfig.json

# Regenerate baseline
./bpr --writebaseline

# Check baseline format
head .basedpyright-baseline.json
```

---

### Issue: Too Many False Positives

**Symptom:** `reportPrivateUsage` flags Qt signal connections

**Solution:**
```python
# Option 1: Disable for specific file
# pyright: reportPrivateUsage=false

# Option 2: Use public wrappers
# Bad:
self.action.triggered.connect(self._on_action)

# Good:
self.action.triggered.connect(self.handle_action)  # Public method
```

---

### Issue: Baseline Growing Instead of Shrinking

**Symptom:** More violations added than removed

**Solution:**
```bash
# Find new violations
git diff .basedpyright-baseline.json

# Review recent commits that added violations
git log --oneline -10

# Consider blocking new violations in CI
# Add to basedpyrightconfig.json:
"failOnWarnings": true
```

---

## Key Insights from Basedpyright Documentation

### 1. Baseline Files (Game Changer)
- **Purpose:** Acknowledge existing issues, prevent new ones
- **Format:** JSON file listing all current violations
- **Behavior:** Baseline violations → "hint" (not error/warning)
- **Workflow:** Fix issues → update baseline → shrinks over time

**Source:** [basedpyright/docs/benefits-over-pyright/baseline.md](https://github.com/detachhead/basedpyright/blob/main/docs/benefits-over-pyright/baseline.md)

---

### 2. Strict Paths (Gradual Strictness)
- **Purpose:** Higher standards for new code, legacy as-is
- **Usage:** `"strict": ["path1/", "path2/file.py"]`
- **Effect:** Enables most type checking rules for specified paths only
- **Strategy:** Expand strict paths as you refactor

**Source:** [basedpyright/docs/configuration/config-files.md](https://github.com/detachhead/basedpyright/blob/main/docs/configuration/config-files.md)

---

### 3. Diagnostic Severity Levels
- **"error"** → CLI fails (exit 1), blocks commits
- **"warning"** → CLI fails only with `--warnings` flag
- **"information"** → Never fails CLI
- **"hint"** → IDE only, not in CLI (baseline uses this)
- **"none"** → Completely disabled

**Source:** [basedpyright/docs/configuration/config-files.md](https://github.com/detachhead/basedpyright/blob/main/docs/configuration/config-files.md)

---

### 4. Config Inheritance (DRY)
- **Purpose:** Share settings across projects/environments
- **Usage:** `"extends": "./basedpyrightconfig.base.json"`
- **Behavior:** Top-level keys override base config
- **Pattern:** base.json (shared) + config.json (project-specific)

**Source:** [basedpyright/docs/configuration/config-files.md](https://github.com/detachhead/basedpyright/blob/main/docs/configuration/config-files.md)

---

### 5. Type Checking Modes
- **"off"** - Disable all type checking (syntax only)
- **"basic"** - Minimal checks
- **"standard"** - Balanced (Pyright default)
- **"recommended"** - Basedpyright's pragmatic default ← Current choice
- **"strict"** - Maximum strictness
- **"all"** - Every rule enabled

**Source:** [basedpyright/docs/configuration/config-files.md](https://github.com/detachhead/basedpyright/blob/main/docs/configuration/config-files.md)

---

## Configuration Reference

### Current Config Philosophy
- **Mode:** "recommended" (pragmatic balance)
- **Errors:** Critical issues only (undefined vars, incompatible overrides)
- **Warnings:** Code quality issues (unused imports, unnecessary comparisons)
- **Suppressions:** Qt type noise, test mock artifacts
- **Strategy:** Fix real bugs, ignore type noise

### Recommended Updates

**Add to basedpyrightconfig.json:**
```json
{
  // Baseline strategy (Phase 2)
  "baselineFile": ".basedpyright-baseline.json",

  // Gradual strictness (Phase 4)
  "strict": [
    "ui/controllers/curve_view/",
    "stores/application_state.py"
  ],

  // Enhanced error detection (Phase 1)
  "reportRedeclaration": "error",

  // CI integration (optional)
  "failOnWarnings": false  // Keep false locally, use --warnings in CI
}
```

### Complete Example Config

See current `basedpyrightconfig.json` for full config. Key sections:

```json
{
  "typeCheckingMode": "recommended",
  "pythonVersion": "3.12",
  "venvPath": ".",
  "venv": "venv",

  // Paths
  "include": ["core", "ui", "services", "tests"],
  "exclude": ["**/archive", "**/.cache"],

  // Baseline (add this)
  "baselineFile": ".basedpyright-baseline.json",

  // Strict paths (expand over time)
  "strict": [],

  // Errors (block commits)
  "reportUndefinedVariable": "error",
  "reportIgnoreCommentWithoutRule": "error",

  // Warnings (CI only with --warnings)
  "reportUnusedImport": "warning",
  "reportUnnecessaryComparison": "warning",

  // Suppressed (intentional)
  "reportAny": "none",
  "reportUnknownMemberType": "none"
}
```

---

## Summary

**Current State:** 0 production errors, 14.7k warnings (97% suppressed noise)

**Strategy:**
1. ✅ **Phase 1:** Fix 20 test errors + 47 critical warnings (Week 1)
2. 🎯 **Phase 2:** Implement baseline file (Week 1-2) ← **KEY STEP**
3. 📈 **Phase 3:** Fix categories incrementally (Ongoing)
4. 🚀 **Phase 4:** Enforce strictness on new code (Long-term)

**Key Tool:** Baseline files let you freeze existing issues, prevent new ones, and improve incrementally.

**Philosophy:** Pragmatic over pedantic. Fix real bugs, ignore type noise, gradually improve.

**Timeline:**
- **Week 1:** Baseline + critical fixes
- **Weeks 2-4:** Quick wins (386 warnings fixed)
- **Ongoing:** Category by category until baseline empty

**Success:** When baseline file is empty, graduate to `"strict"` mode for entire codebase. 🎉

---

**Next Steps:** See "Practical Implementation Guide" section above.
