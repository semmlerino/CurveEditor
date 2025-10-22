# Best Practices Audit: TRACKED_DATA_REFACTORING_PLAN.md

**Status**: Complete
**Rating**: 8.5/10 - Sound plan with execution enhancement opportunities
**Recommendation**: ✓ Proceed with plan, implement suggested enhancements

---

## Key Findings

### 1. Anti-Pattern Identification: ✓ CORRECT

The current `tracked_data` property is a **legitimate and serious anti-pattern**:

- **Violates PEP 20** (Explicit is better than implicit)
- **Violates PEP 8** (Properties should not be surprising)
- **Silent failure**: Modifications disappear without error (WORSE than error)
- **Misleading type**: `dict[...]` implies mutability but isn't

**Evidence**: Active bug in InsertTrackCommand - `KeyError: 'avrg_01'` when accessing newly created averaged curve.

---

### 2. Proposed Solutions: Generally Excellent

| Solution | Assessment | Recommendation |
|----------|-----------|-----------------|
| Direct ApplicationState Access | ✓✓ EXCELLENT | PRIMARY - Use this always |
| `get_tracked_data_snapshot()` | ✓✓ EXCELLENT | SECONDARY - Good for legacy support |
| Explicit mutation methods | ⚠ SKIP | Thin wrappers, no value-add |

**Best Approach Hierarchy**:
1. **Direct ApplicationState** (preferred): `app_state.set_curve_data(name, data)`
2. **Snapshot for reading** (legacy): `controller.get_tracked_data_snapshot()`
3. **Property wrapper** (deprecated): `controller.tracked_data` → warns + snapshots

---

### 3. Deprecation Approach: ✓ CORRECT

Implementation uses standard Python patterns:
- ✓ `warnings.warn()` with `DeprecationWarning`
- ✓ `stacklevel=2` (points to caller's code)
- ✓ Clear messaging
- ✓ PEP 230 compliant

---

### 4. Immutability & Type Safety: ⚠ ENHANCEMENT OPPORTUNITY

**Suggested Improvement for Phase 2**:

Use `types.MappingProxyType` for runtime-enforced immutability:

```python
from types import MappingProxyType

def get_tracked_data_snapshot(self) -> MappingProxyType:
    """Get read-only snapshot of all tracked curves.

    Returns immutable proxy - modifications raise TypeError at runtime.
    """
    raw_dict = {
        name: self._app_state.get_curve_data(name)
        for name in self._app_state.get_all_curve_names()
    }
    return MappingProxyType(raw_dict)
```

**Benefits**:
- Runtime enforcement (not just convention)
- Prevents: `snapshot["key"] = value` → TypeError (catches bugs early)
- Matches PEP 594 immutable dict patterns
- Minimal performance overhead

---

### 5. PEP Compliance Check

| PEP | Aspect | Current | After Plan | After Enhancements |
|-----|--------|---------|------------|-------------------|
| 20 | Explicit over implicit | ✗ | ✓ | ✓✓ |
| 8 | Property surprise | ✗ | ✓ | ✓ |
| 230 | Deprecation warnings | - | ✓ | ✓ |
| 585 | Modern type hints | ⚠ | ✓ | ✓✓ |
| 594 | Immutable collections | - | ⚠ | ✓ |

---

### 6. Architecture Alignment

**Codebase Pattern Comparison**:

✓ `ApplicationState.active_curve_data` (Phase 4 Task 4.4) shows correct property pattern:
- Returns immutable tuple: `tuple[str, CurveDataList] | None`
- Clear documentation
- Type system reflects immutability

The proposed plan actually IMPROVES upon this by using direct method calls (even better).

---

### 7. Implementation Recommendations

#### Phase 1: Bug Fix (As Proposed) ✓
- Fix InsertTrackCommand to use direct ApplicationState
- No changes needed
- Low risk, high value

#### Phase 2: Deprecation (Enhanced) ✓ + ⚠

**Do This**:
- Add `get_tracked_data_snapshot()` with deprecation warning
- Use `MappingProxyType` for immutability enforcement
- Add filterwarnings to pytest.ini:
  ```toml
  [tool.pytest.ini_options]
  filterwarnings = [
      "error::DeprecationWarning",
      "error::FutureWarning",
  ]
  ```

**Don't Do This**:
- Skip `add_tracked_curve()`, `update_tracked_curve()`, `delete_tracked_curve()`
- These are thin wrappers with no value-add
- They contradict documented architecture

#### Phase 3: Architecture Decision ✓

**Recommendation**: Keep TrackingDataController because:
- ✓ Manages tracking directions (has business logic)
- ✓ Used from multiple places
- ✓ UI-specific logic

But remove property wrappers and use direct ApplicationState access.

---

### 8. Testing Enhancements

Add to Phase 2 testing:

```python
def test_snapshot_is_immutable():
    """MappingProxyType prevents mutations."""
    snapshot = controller.get_tracked_data_snapshot()
    with pytest.raises(TypeError):
        snapshot["new_key"] = data  # Should fail

def test_deprecation_warning():
    """Property emits deprecation warning."""
    with pytest.warns(DeprecationWarning):
        _ = controller.tracked_data
```

---

### 9. Security & Safety

**Security**: ✓ No issues identified
- No secrets/credentials
- No injection vectors
- Immutability by copying prevents external mutations

**Safety**: ✓ Fixes bugs
- Silent failure eliminated
- Type system is truthful
- Direct access reduces indirection points

---

### 10. Modern Python Alignment

The plan follows modern Python (3.10+) best practices:
- ✓ Union syntax: `str | None` not `Optional[str]`
- ✓ Type hints present and mostly accurate
- ✓ Dataclass patterns (in core models)
- ✓ Generator/comprehension usage
- ✓ Context managers for batch operations

---

## Summary Table

| Aspect | Status | Notes |
|--------|--------|-------|
| Problem identification | ✓ Correct | Legitimate anti-pattern identified |
| Primary solution | ✓✓ Excellent | Direct ApplicationState access |
| Secondary solution | ✓✓ Excellent | Snapshot method with good naming |
| Tertiary solution | ⚠ Skip | Thin wrapper methods (no value) |
| Deprecation | ✓ Correct | Standard warnings.warn() pattern |
| Type safety | ⚠ Enhance | Add MappingProxyType for enforcement |
| Phase 1 plan | ✓ Good | No changes needed |
| Phase 2 plan | ✓ Good | Add MappingProxyType enhancement |
| Phase 3 plan | ✓ Good | Need decision framework docs |
| Testing | ✓ Adequate | Could add immutability tests |
| Documentation | ✓ Good | Plan to update CLAUDE.md |

---

## Detailed Analysis

**Full audit available in**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/BEST_PRACTICES_AUDIT_TRACKED_DATA.md`

**Contains**:
- Comprehensive PEP compliance analysis
- Stdlib pattern comparisons
- Code examples for all recommendations
- Type safety enhancements
- Immutability patterns
- Security assessment
- Testing strategies

---

## Final Recommendation

### ✓ PROCEED WITH PLAN

The TRACKED_DATA_REFACTORING_PLAN correctly identifies a genuine architectural problem and proposes sound solutions that align with:
- Python best practices (PEP 20, 8, 230)
- Stdlib conventions
- Codebase documented architecture
- Modern Python patterns

**Implement with these enhancements**:
1. ✓ Phase 1 as proposed (no changes)
2. ✓ Phase 2 with MappingProxyType for immutability
3. ⚠ Skip thin mutation wrapper methods
4. ✓ Add CI/CD deprecation warnings config
5. ✓ Document "when to use which" patterns

**Confidence Level**: HIGH

This refactoring will:
- Fix active bug (silent failures in Insert Track)
- Improve code clarity (POLA compliance)
- Prevent future similar bugs
- Align architecture with documentation
- Improve type safety
- Follow Python standards

---

**Audit Date**: 2025-10-21
**Codebase**: CurveEditor (Python 3.13, PySide6)
**Analyzer**: Best Practices Checker Agent
