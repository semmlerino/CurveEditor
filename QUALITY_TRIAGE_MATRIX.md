# Quality Issue Triage Matrix

## Priority Classification
Use this matrix to prioritize fixes if time becomes constrained.

## P0 - MUST FIX (Blocking Issues)
These prevent normal development or usage:
- [ ] Import errors preventing module loading
- [ ] Syntax errors in core files
- [ ] Service initialization failures
- [ ] Test framework breakage
- [ ] Critical type errors in service interfaces

## P1 - HIGH PRIORITY (Functionality Impact)
These affect code functionality or maintainability:
- [ ] Unused imports in service files (F401)
- [ ] Import sorting in services/ and ui/ (I001)
- [ ] Missing type annotations for public APIs
- [ ] Undefined variables or functions
- [ ] Service protocol violations

## P2 - MEDIUM PRIORITY (Quality Impact)
These affect code quality but not functionality:
- [ ] Trailing whitespace (W293)
- [ ] Missing final newlines (W292)
- [ ] Line too long in docstrings
- [ ] Import sorting in tests/
- [ ] Type errors in test files

## P3 - LOW PRIORITY (Cosmetic)
Fix if time permits:
- [ ] Extra blank lines
- [ ] Indentation inconsistencies
- [ ] Comment formatting
- [ ] Variable naming conventions
- [ ] Docstring formatting

## Quick Win Categories
Focus on these for maximum impact:

### Bulk Auto-Fixable (5 min each)
1. Trailing whitespace: `ruff check . --select W293 --fix`
2. Import sorting: `ruff check . --select I001 --fix`
3. Unused imports: `ruff check . --select F401 --fix`
4. Missing newlines: `ruff check . --select W292 --fix`

### High-Impact Fixes (30 min each)
1. Service import paths standardization
2. Core model type annotations
3. Service protocol completions
4. Test fixture typing

### Documentation Updates (15 min each)
1. README.md architecture section
2. Version history update
3. Migration guide reference
4. Deprecation notice

## Time Estimation
| Issue Category | Count | Fix Time | Total Time |
|----------------|-------|----------|------------|
| Auto-fixable | ~20,000 | 1 sec/fix (bulk) | 30 min |
| Import errors | ~150 | 1 min/fix | 2.5 hours |
| Type errors | ~700 | 2 min/fix | 23 hours |
| Documentation | 4 sections | 15 min/section | 1 hour |
| Feature tests | 5 tests | 20 min/test | 1.7 hours |

## Decision Tree
```
Time Available?
├─ < 1 hour: P0 only + auto-fix
├─ 1-3 hours: P0 + P1 + auto-fix
├─ 3-6 hours: P0 + P1 + P2 + docs
└─ > 6 hours: Complete all priorities
```

## Rollback Triggers
Rollback if any of these occur:
- Test pass rate drops below 80%
- Core functionality breaks
- Service initialization fails
- More than 10 new test failures

---
*Use this matrix to make rapid triage decisions during the Emergency Quality Recovery Sprint*
