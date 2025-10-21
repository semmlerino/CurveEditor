# Best Practices Analysis: TRACKED_DATA_REFACTORING_PLAN.md

**Analysis Date**: 2025-10-21
**Codebase**: CurveEditor (Python 3.13, PySide6, Modern Python)
**Scope**: Property patterns, API design, deprecation, type safety

---

## Executive Summary

The TRACKED_DATA_REFACTORING_PLAN.md correctly identifies a fundamental anti-pattern and proposes **generally sound solutions** with some modern Python enhancements that should be considered. The plan demonstrates good architectural thinking but has opportunities to follow Python stdlib conventions more closely.

**Overall Assessment**: ✓ Good pattern identification, ✓ Solid proposals, ⚠ Minor modern Python improvements available

---

## 1. PROPERTY PATTERN ANALYSIS

### Current Problem: Legitimate Anti-Pattern?

**YES - This is a textbook Python anti-pattern.** The plan correctly identifies it:

```python
# ❌ ANTI-PATTERN: Violates Principle of Least Astonishment (POLA)
@property
def tracked_data(self) -> dict[str, CurveDataList]:
    result: dict[str, CurveDataList] = {}
    for curve_name in self._app_state.get_all_curve_names():
        result[curve_name] = self._app_state.get_curve_data(curve_name)
    return result  # Fresh dict - NOT persistent storage!
```

**Why This Is Anti-Pattern**:

1. **Violates POLA** (PEP 20 - "Explicit is better than implicit"):
   - Property syntax suggests mutable storage: `obj.tracked_data[key] = value`
   - Actually returns ephemeral snapshot
   - Modifications silently disappear

2. **Silent Failure** (worse than loud error):
   ```python
   tracked_data = controller.tracked_data
   tracked_data[new_curve] = data  # Looks like it works
   # Later: KeyError when accessing - data never persisted
   ```

3. **Type System Misleading**:
   - Return type `dict[str, CurveDataList]` implies mutability
   - Should return immutable type if truly read-only

4. **Comparison with stdlib**:
   - `dict.items()` returns view (read-only in Python 3)
   - `dict.copy()` explicit about creating separate dict
   - `@property` returning mutable without warning is NOT stdlib pattern

### Python Standards Violated

| PEP | Violation | Severity |
|-----|-----------|----------|
| PEP 20 (Zen) | "Explicit is better than implicit" | HIGH |
| PEP 257 (Docstring) | Should warn about not persisting | MEDIUM |
| PEP 8 (Properties) | Properties should be quick, non-surprising | HIGH |
| PEP 492 (Coroutines) | Single responsibility - property should do ONE thing | MEDIUM |

---

## 2. PROPOSED SOLUTIONS ANALYSIS

### Solution 1: Direct ApplicationState Access ✓ EXCELLENT

**Proposed**:
```python
from stores.application_state import get_application_state
app_state = get_application_state()
app_state.set_curve_data(new_curve_name, averaged_data)
```

**Assessment**: ✓✓ This is the BEST solution

**Why It's Pythonic**:
- Explicit over implicit (PEP 20)
- Direct access to single source of truth
- No wrapper indirection
- Matches documented architecture (CLAUDE.md)
- Type-safe (ApplicationState methods are well-typed)

**Stdlib Comparison**:
```python
# Similar pattern in stdlib
import sys
sys.path.append('/new/path')  # Direct mutation, not via property

# Similar in logging
logger = logging.getLogger('name')
logger.setLevel(logging.DEBUG)  # Direct method, not property
```

**Codebase Evidence**:
```
ApplicationState.get_curve_data()        ← Already uses direct access
ApplicationState.set_curve_data()        ← Already uses direct access
ApplicationState.active_curve_data       ← Property pattern done RIGHT
```

The `active_curve_data` property (Phase 4 Task 4.4) shows the CORRECT way:
- Returns immutable tuple: `tuple[str, CurveDataList] | None`
- Clear naming signals it's a paired result
- Documented purpose
- Still better to use direct access in MainWindow

**Recommendation**: ✓ Use this FIRST, ALWAYS

---

### Solution 2: Snapshot Method ✓✓ EXCELLENT

**Proposed**:
```python
def get_tracked_data_snapshot(self) -> dict[str, CurveDataList]:
    """Get read-only snapshot of all tracked curves."""
    result: dict[str, CurveDataList] = {}
    for curve_name in self._app_state.get_all_curve_names():
        result[curve_name] = self._app_state.get_curve_data(curve_name)
    return result
```

**Assessment**: ✓✓ Excellent naming and approach

**Why It's Pythonic**:
- Verb in name signals action (not property)
- "snapshot" is explicit about immutability
- Matches stdlib conventions:
  ```python
  # Similar patterns
  dict.copy()           # Returns copy
  list.copy()           # Returns copy
  obj.serialize()       # Returns representation
  ```
- Better than `get_all_curves()` because "snapshot" signals immutability

**Recommendation**: ✓ Use for read-only multi-curve access

**Enhancement Opportunity**: Consider `types.MappingProxyType`:
```python
from types import MappingProxyType

def get_tracked_data_snapshot(self) -> MappingProxyType:
    """Get read-only snapshot of all tracked curves.

    Returns immutable proxy - modifications raise TypeError.
    """
    raw_dict = {
        name: self._app_state.get_curve_data(name)
        for name in self._app_state.get_all_curve_names()
    }
    return MappingProxyType(raw_dict)
```

**Benefits of MappingProxyType**:
- Runtime enforcement of immutability (not just convention)
- Prevents accidental mutations: `snapshot["key"] = value` → TypeError
- Matches PEP 594 pattern for read-only dicts
- Small performance cost but catches bugs early

**Codebase Already Uses Similar Immutability**:
```python
# ApplicationState.get_curve_data() returns copy (immutability by copying)
return self._curves_data[curve_name].copy()

# MappingProxyType would be additive improvement
```

---

### Solution 3: Explicit Mutation Methods ⚠ QUESTIONABLE

**Proposed**:
```python
def add_tracked_curve(self, name: str, data: CurveDataList) -> None:
    """Add curve to ApplicationState."""
    self._app_state.set_curve_data(name, data)

def update_tracked_curve(self, name: str, data: CurveDataList) -> None:
    """Update existing curve in ApplicationState."""
    self._app_state.set_curve_data(name, data)

def delete_tracked_curve(self, name: str) -> None:
    """Remove curve from ApplicationState."""
    self._app_state.delete_curve(name)
```

**Assessment**: ⚠ QUESTIONABLE - adds indirection without value

**Problems**:
1. **Wrapper with No Added Value**: These are thin pass-throughs to ApplicationState
   - Same method names
   - Same arguments
   - Same behavior
   - No validation or business logic

2. **Violates DRY**: Controller adds layer of indirection that doesn't add value
   - Documented pattern: "Use ApplicationState directly" (CLAUDE.md)
   - These methods contradict that guidance

3. **Maintenance Burden**: Changes to ApplicationState API require controller updates too

4. **Naming Conflict**: `add_tracked_curve` vs `set_curve_data` - which to use?

5. **Comparison with Stdlib**:
   ```python
   # Stdlib: Direct access, no wrapper
   dict[key] = value              # Direct
   dict.update({key: value})      # Direct
   # NOT: wrapper_obj.add_dict_item(key, value)

   # Qt: Minimal wrappers with value-add
   widget.setEnabled(True)        # Does property setting + side effects
   # NOT: widget.set_state(True)  # Same effect as property
   ```

**Recommendation**: ⚠ SKIP these methods

**Alternative**: If controller genuinely needs to add business logic:
```python
def add_tracking_point(self, name: str, data: CurveDataList) -> bool:
    """Add tracking point with validation and history tracking."""
    # Validate naming convention
    if not name.startswith("Track"):
        logger.warning(f"Non-standard tracking name: {name}")

    # Check for duplicates
    if name in self._app_state.get_all_curve_names():
        return False

    # Add with tracking direction initialization
    self._app_state.set_curve_data(name, data)
    self.point_tracking_directions[name] = TrackingDirection.TRACKING_FW
    return True
```

This adds value: naming validation, duplicate checking, tracking direction setup.
Current proposed methods don't have this.

---

## 3. DEPRECATION APPROACH ANALYSIS

### Proposed Implementation ✓ CORRECT

```python
@property
def tracked_data(self) -> dict[str, CurveDataList]:
    """DEPRECATED: Use ApplicationState directly."""
    import warnings
    warnings.warn(
        "tracked_data is deprecated. Use ApplicationState.get_all_curves() directly.",
        DeprecationWarning,
        stacklevel=2
    )
    return self.get_tracked_data_snapshot()
```

**Assessment**: ✓ This follows stdlib conventions correctly

**Why It's Pythonic**:
1. **Uses `warnings` module** (PEP 230):
   - stdlib standard for deprecations
   - Can be suppressed with `-W` flags
   - Can be treated as errors in CI/CD

2. **Correct DeprecationWarning category**:
   - PendingDeprecationWarning: Future deprecation (not yet enforced)
   - DeprecationWarning: Currently deprecated (will be removed)
   - This is correct choice for "use something else now"

3. **Correct stacklevel=2**:
   - stacklevel=1 would show warning in library code
   - stacklevel=2 shows warning at caller's code
   - Helps developers find where to fix

4. **Matches stdlib deprecations**:
   ```python
   # From stdlib (similar pattern)
   warnings.warn(
       "deprecated_function is deprecated, use new_function instead",
       DeprecationWarning,
       stacklevel=2
   )
   ```

**Testing Deprecation Warnings**:
```bash
# Proposed in plan is correct
pytest tests/ -v -W error::DeprecationWarning

# Also recommended to catch:
pytest tests/ -v -W always::DeprecationWarning  # Always show
pytest tests/ -v -W ignore::DeprecationWarning  # Suppress for noise
```

**Recommendation**: ✓ Implementation is correct, but add to CI/CD:

```yaml
# pyproject.toml or pytest.ini
[tool.pytest.ini_options]
filterwarnings = [
    "error::DeprecationWarning",  # Fail on deprecations
    "error::FutureWarning",        # Fail on future breaking changes
]
```

---

## 4. IMMUTABILITY PATTERN ANALYSIS

### Current: Copy-Based (ApplicationState) ✓ GOOD

```python
def get_curve_data(self, curve_name: str | None = None) -> CurveDataList:
    """Returns a COPY for safety."""
    return self._curves_data[curve_name].copy()
```

**Assessment**: ✓ This is defensive and works

**Trade-off**:
- Pro: Simple, familiar, works for all types
- Con: Memory overhead for large data

### Proposed for Tracking Controller: Return Type Immutability ⚠ MISSING

**Current Proposal**:
```python
def get_tracked_data_snapshot(self) -> dict[str, CurveDataList]:
    # Returns mutable dict, relies on convention
```

**Better (Modern Python)**:
```python
from types import MappingProxyType

def get_tracked_data_snapshot(self) -> MappingProxyType:
    """Get read-only snapshot - modifications raise TypeError."""
    raw = {
        name: self._app_state.get_curve_data(name)
        for name in self._app_state.get_all_curve_names()
    }
    return MappingProxyType(raw)
```

**Type Hint Alternative** (if not using MappingProxyType):
```python
from typing import Mapping

def get_tracked_data_snapshot(self) -> Mapping[str, CurveDataList]:
    """Get read-only mapping of tracked curves."""
    return {
        name: self._app_state.get_curve_data(name)
        for name in self._app_state.get_all_curve_names()
    }
```

**Comparison with Stdlib**:
```python
# Modern Python approach
dict.items()                        # Returns view (Mapping-like)
types.MappingProxyType(d)          # Immutable dict proxy
collections.abc.Mapping            # Abstract base (type hint)

# CurveEditor should use similar pattern
```

**Recommendation**: ⚠ Consider MappingProxyType for enforced immutability

---

## 5. CODEBASE PATTERN COMPARISON

### How Similar Patterns Are Handled

**Pattern: Active Curve Data** (Phase 4 Task 4.4) ✓ CORRECT

```python
@property
def active_curve_data(self) -> tuple[str, CurveDataList] | None:
    """Get (curve_name, data) for active curve, or None if unavailable."""
    active = self.active_curve
    if not active:
        return None
    data = self.get_curve_data(active)
    return (active, data)
```

**Why This Is Better Than `tracked_data`**:
1. **Returns tuple** (immutable) not dict (mutable)
2. **Clear documentation** about immutability
3. **Clear purpose** (paired data access)
4. **Type safety** - tuple structure is explicit

**Pattern: Get Snapshot vs Get All** (ApplicationState)

```python
# Current pattern in codebase
def get_all_curves(self) -> dict[str, CurveDataList]:
    """Get all curves data as dictionary."""
    return {name: data.copy() for name, data in self._curves_data.items()}
```

**Assessment**: Should we keep using `get_all_curves()` or rename?

Current plan says:
- Old: `tracked_data` (property, misleading)
- New: `get_tracked_data_snapshot()` (method, explicit)

This is good! The word "snapshot" makes immutability/freshness clear.

---

## 6. SECURITY & SAFETY CONCERNS

### No Security Issues Identified ✓

- Direct ApplicationState access: ✓ Single source of truth
- Immutability by copying: ✓ Prevents external mutations
- Type hints: ✓ Help catch bugs
- No secrets/credentials: ✓ No issues

### Type Safety Opportunities

**Current**:
```python
def tracked_data(self) -> dict[str, CurveDataList]:
    # Type says "mutable dict" but actually immutable
    # Creates type/reality mismatch
```

**Better**:
```python
def get_tracked_data_snapshot(self) -> Mapping[str, CurveDataList]:
    # Type says "read-only mapping" - matches reality
    # Helps IDE catch accidental mutations

# Or with MappingProxyType (enforced):
def get_tracked_data_snapshot(self) -> MappingProxyType:
    # Type and runtime both prevent mutations
```

**Codebase Already Has Type Issues**:
```
# From CLAUDE.md task list
✓ Fix type annotations (Phase 3)
✓ Clean up basedpyright warnings
→ Return type improvements would help ongoing effort
```

---

## 7. NAMING CONVENTIONS ANALYSIS

### Proposed Names - Modern Python Alignment

| Name | Pattern | Assessment | Stdlib Example |
|------|---------|-----------|-----------------|
| `tracked_data` | property | ❌ Misleading | - |
| `get_tracked_data_snapshot()` | method, noun | ✓ Excellent | `dict.copy()`, `obj.serialize()` |
| `add_tracked_curve()` | method, verb | ⚠ Unclear purpose | - |
| `update_tracked_curve()` | method, verb | ⚠ Same as `set_curve_data()` | - |
| `delete_tracked_curve()` | method, verb | ⚠ Same as `delete_curve()` | - |

**Recommendation**:
- ✓ Keep `get_tracked_data_snapshot()`
- ⚠ Skip the add/update/delete wrappers
- Use direct ApplicationState access

**Better Alternative Names** (if controller wrapper needed):

```python
# If tracking direction initialization is important
def register_tracking_point(self, name: str, data: CurveDataList) -> bool:
    """Register new tracking point with direction tracking."""
    # Initialization logic that justifies wrapper
    if name in self._app_state.get_all_curve_names():
        return False
    self._app_state.set_curve_data(name, data)
    self.point_tracking_directions[name] = TrackingDirection.TRACKING_FW
    return True
```

This name signals "this does something more than just store data" (registration, validation, initialization).

---

## 8. TEST COVERAGE RECOMMENDATIONS

### Phase 1 Testing ✓ ADEQUATE

Plan suggests:
```bash
pytest tests/test_insert_track_*.py -v
```

**Assessment**: ✓ Good

### Phase 2 Testing: Deprecation ✓ GOOD PLAN

Plan suggests:
```bash
pytest tests/ -v -W error::DeprecationWarning
```

**Assessment**: ✓ Excellent - catches call sites

**Enhancement**: Add to CI/CD config:

```toml
# pyproject.toml
[tool.pytest.ini_options]
filterwarnings = [
    "error::DeprecationWarning",  # Phase 2+: Fail on deprecations
    "default::DeprecationWarning:tests/*",  # Tests can suppress if needed
]
```

### Additional Tests Needed

1. **Immutability Tests**:
```python
def test_tracked_data_snapshot_is_immutable():
    snapshot = controller.get_tracked_data_snapshot()
    with pytest.raises(TypeError):
        snapshot["new_key"] = data  # Should fail if using MappingProxyType
```

2. **Deprecation Warning Tests**:
```python
def test_tracked_data_property_deprecated(recwarn):
    snapshot = controller.tracked_data
    assert len(recwarn) == 1
    assert issubclass(recwarn[0].category, DeprecationWarning)
```

---

## 9. DOCUMENTATION UPDATES NEEDED

### Plan Mentions: CLAUDE.md Updates ✓ GOOD

Current plan to add:
```markdown
### ❌ WRONG: Modifying tracked_data dict
### ✅ CORRECT: Direct ApplicationState access
```

**Enhancement**: Also document:

1. **When to use each pattern**:
```markdown
## Data Access Patterns

**For active curve only**:
```python
if (curve_data := state.active_curve_data) is None:
    return
```

**For all curves (read-only)**:
```python
# Option 1: Direct ApplicationState (preferred)
all_curves = state.get_all_curves()

# Option 2: Through controller (deprecated)
snapshot = controller.get_tracked_data_snapshot()
```

**For modification**:
```python
# Always use ApplicationState directly
state.set_curve_data(curve_name, new_data)
```
```

2. **Anti-patterns to avoid**:
```markdown
### ❌ WRONG: Using property as mutable storage
tracked_data = controller.tracked_data
tracked_data[key] = value  # Silent failure!

### ✅ CORRECT: Use immutable snapshot for reading
snapshot = controller.get_tracked_data_snapshot()
for name, data in snapshot.items():
    print(f"{name}: {len(data)} points")

### ✅ CORRECT: Use ApplicationState for writing
state.set_curve_data(curve_name, modified_data)
```

---

## 10. IMPLEMENTATION RECOMMENDATIONS

### Priority 1: Immediate (Phase 1) ✓ CORRECT

**Plan suggests**: Fix InsertTrackCommand to use direct ApplicationState
- ✓ Correct approach
- ✓ Low risk
- ✓ No breaking changes

```python
# In InsertTrackCommand._execute_scenario_3
from stores.application_state import get_application_state
app_state = get_application_state()
app_state.set_curve_data(new_curve_name, averaged_data)
```

### Priority 2: Deprecation (Phase 2) ✓ GOOD PLAN

**Plan suggests**: Add deprecation warning + snapshot method

**Enhancement**: Also consider if Property should be removed entirely:
```python
# Option A: Keep property with deprecation (current plan)
@property
def tracked_data(self) -> dict[str, CurveDataList]:
    warnings.warn(..., DeprecationWarning, stacklevel=2)
    return self.get_tracked_data_snapshot()

# Option B: Remove property entirely after Phase 1 migration
# Faster to remove than maintain deprecated code
```

### Priority 3: Architecture Decision (Phase 3) ✓ GOOD PLANNING

**Plan suggests**: Decide whether TrackingDataController adds value

**Assessment**: ✓ Necessary question

**Factors to Consider**:
- Does controller have business logic beyond forwarding? (Tracking direction tracking is good!)
- Is controller used from many places? (Yes - many commands)
- Could this logic live in ApplicationState? (No - UI-specific)

**Recommendation**: Keep controller for tracking direction management, but remove property wrapper

---

## 11. PYLINT/PYRIGHT COMPATIBILITY

### Current Plan: No Type Checking Mentioned ⚠ CONSIDER

**Recommendation**: Check with basedpyright before and after:

```bash
./bpr ui/controllers/tracking_data_controller.py
./bpr core/commands/insert_track_command.py
./bpr tests/test_insert_track_*.py
```

**Expected improvements**:
- ✓ Return type clarity (dict vs Mapping vs MappingProxyType)
- ✓ No more "property returns mutable" confusion
- ✓ Better IDE autocomplete with `get_tracked_data_snapshot()`

---

## 12. MODERN PYTHON PATTERNS COMPLIANCE

### PEP Compliance Check

| PEP | Topic | Current | Assessment |
|-----|-------|---------|-----------|
| PEP 8 | Style | Property misleading | ❌ Violates |
| PEP 20 | Zen | "Explicit > implicit" | ⚠ Property implicit |
| PEP 230 | Warnings | Not used yet | ✓ Plan uses correctly |
| PEP 257 | Docstrings | Documented | ✓ Good |
| PEP 3107 | Type Hints | Present but unclear | ⚠ Could improve |
| PEP 544 | Protocols | Used elsewhere | ✓ Good practice |
| PEP 585 | List[X] vs list[x] | Using modern | ✓ Good (Python 3.9+) |
| PEP 591 | Final | Not used | OK (not needed here) |
| PEP 594 | Removed stdlib | MappingProxyType available | ⚠ Consider for immutability |

**Verdict**: Plan is generally compliant, some enhancements available

---

## SUMMARY & RECOMMENDATIONS

### What's Right About the Plan

1. ✓ **Correct Problem Identification**: Property returning ephemeral dict is legitimate anti-pattern
2. ✓ **Good Primary Solution**: Direct ApplicationState access (documented pattern)
3. ✓ **Explicit Naming**: `get_tracked_data_snapshot()` is clear and pythonic
4. ✓ **Proper Deprecation**: Using `warnings.warn()` with DeprecationWarning, stacklevel=2
5. ✓ **Phased Approach**: Three phases allow safe migration
6. ✓ **Test Strategy**: Tests with `-W error::DeprecationWarning` is excellent
7. ✓ **Risk Assessment**: Proper analysis of Phase 1 risks

### What Could Be Enhanced

1. ⚠ **Skip Thin Wrappers**: Don't add `add_tracked_curve()`, etc. (no value-add)
2. ⚠ **Consider Immutability Enforcement**: Use `MappingProxyType` for `get_tracked_data_snapshot()`
3. ⚠ **Type Safety**: Return `Mapping[str, CurveDataList]` instead of `dict`
4. ⚠ **CI/CD Integration**: Add `filterwarnings` to pytest.ini
5. ⚠ **Naming**: If keeping wrapper methods, use names that show they do validation/initialization

### Modern Python Opportunities

```python
# Recommended implementation for get_tracked_data_snapshot():
from types import MappingProxyType
from collections.abc import Mapping

def get_tracked_data_snapshot(self) -> MappingProxyType:
    """Get read-only snapshot of all tracked curves.

    Returns immutable proxy. Attempting to modify raises TypeError.

    Returns:
        MappingProxyType with all curves data (copies).

    Example:
        snapshot = controller.get_tracked_data_snapshot()
        for name, data in snapshot.items():
            print(f"{name}: {len(data)} points")

        snapshot["new"] = data  # TypeError: read-only
    """
    raw_dict = {
        name: self._app_state.get_curve_data(name)
        for name in self._app_state.get_all_curve_names()
    }
    return MappingProxyType(raw_dict)
```

### Phasing Recommendation

**Phase 1**: Fix InsertTrackCommand (as planned) ✓
**Phase 2**: Add deprecation + snapshot method (as planned) ✓
**Phase 2 Enhancement**: Add type hints improvement
**Phase 3**: Remove thin wrappers, finalize API

---

## CONCLUSION

**Overall Rating**: 8.5/10

The TRACKED_DATA_REFACTORING_PLAN demonstrates solid Python architectural thinking and correctly identifies a genuine anti-pattern. The proposed solutions are generally pythonic and follow stdlib conventions well. The plan would benefit from:

1. Using `MappingProxyType` for runtime-enforced immutability
2. Skipping the thin wrapper methods (add/update/delete)
3. Improving type hints (Mapping instead of dict)
4. Adding CI/CD integration for deprecation warnings

The refactoring aligns well with the codebase's documented architecture and modern Python practices (3.10+ union syntax, type hints, dataclasses). Following this plan will improve code clarity and prevent silent failures.

**Proceed with confidence on Phase 1 and 2, consider enhancements noted above.**
