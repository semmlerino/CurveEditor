# Phase 2: Type Safety Migration Plan

## Executive Summary

Phase 2 focuses on systematically replacing 97 `hasattr()` calls across 20 production files to restore type information and prevent runtime AttributeErrors. This follows Phase 1's successful implementation of the current_frame property fix.

## Current State Analysis

### Metrics
- **Total hasattr() calls**: 97 across 20 files
- **Type errors in basedpyright**: 556 (down from 528)
- **Critical paths affected**: Rendering, data operations, UI interactions
- **Estimated migration effort**: 4 weeks

### Hotspot Files (Top Priority)
1. **data/curve_view_plumbing.py** - 11 occurrences (data operations)
2. **data/batch_edit.py** - 9 occurrences (batch operations)
3. **rendering/optimized_curve_renderer.py** - 8 occurrences (performance critical)
4. **core/image_state.py** - 7 occurrences (state management)
5. **core/spatial_index.py** - 6 occurrences (spatial queries)

## Pattern Classification & Solutions

### 1. Optional Dependencies Pattern
**Problem**:
```python
if hasattr(main_window, "statusBar"):
    main_window.statusBar().showMessage("Done")
```

**Solution**:
```python
from typing import Optional

class Component:
    status_bar: Optional[QStatusBar] = None

    def show_status(self, msg: str) -> None:
        if self.status_bar is not None:
            self.status_bar.showMessage(msg)
```

### 2. Duck-Typing Pattern
**Problem**:
```python
if hasattr(target, "points"):
    return target.points
```

**Solution**:
```python
from typing import Protocol

class HasPoints(Protocol):
    points: list[CurvePoint]

def get_points(target: HasPoints) -> list[CurvePoint]:
    return target.points
```

### 3. State Management Pattern
**Problem**:
```python
if hasattr(self, "_last_point_count"):
    changed = self._last_point_count != count
```

**Solution**:
```python
class Renderer:
    def __init__(self) -> None:
        self._last_point_count: Optional[int] = None

    def check_change(self, count: int) -> bool:
        if self._last_point_count is not None:
            return self._last_point_count != count
        return True
```

### 4. Component Discovery Pattern
**Problem**:
```python
if hasattr(self.parent, "curve_view"):
    view = self.parent.curve_view
```

**Solution**:
```python
class Parent:
    curve_view: Optional[CurveView] = None

# Or with dependency injection:
class Component:
    def __init__(self, curve_view: Optional[CurveView] = None):
        self.curve_view = curve_view
```

## Implementation Schedule

### Week 1: Protocol Interfaces (Jan 6-12)
- [ ] Create `protocols/view_protocols.py` with CurveViewProtocol
- [ ] Create `protocols/edit_protocols.py` with BatchEditableProtocol
- [ ] Enhance existing MainWindowProtocol
- [ ] Add Protocol tests

### Week 2: High-Frequency Paths (Jan 13-19)
- [ ] Refactor `optimized_curve_renderer.py` (8 hasattr)
- [ ] Refactor `curve_view_plumbing.py` (11 hasattr)
- [ ] Refactor `batch_edit.py` (9 hasattr)
- [ ] Performance benchmarking

### Week 3: Core Components (Jan 20-26)
- [ ] Fix `core/image_state.py` (7 hasattr)
- [ ] Fix `core/spatial_index.py` (6 hasattr)
- [ ] Fix `ui/animation_utils.py` (4 hasattr)
- [ ] Fix remaining UI components

### Week 4: Testing & Documentation (Jan 27-Feb 2)
- [ ] Update test suite (remove 27 test hasattr calls)
- [ ] Run comprehensive type checking
- [ ] Performance validation (<5% impact)
- [ ] Update CLAUDE.md with patterns

## Success Criteria

### Quantitative Metrics
- **hasattr() reduction**: From 97 to <50 (50% reduction)
- **Type errors**: From 556 to <300
- **Performance impact**: <5% on critical paths
- **Test coverage**: 100% for refactored code

### Qualitative Improvements
- Zero runtime AttributeErrors
- Improved IDE autocomplete
- Better debuggability
- Clearer component interfaces

## Risk Mitigation

### Risks
1. **Breaking changes** during refactoring
2. **Performance regression** from type checks
3. **Incomplete migration** leaving mixed patterns

### Mitigations
1. **Comprehensive testing** before each refactor
2. **Performance benchmarks** for critical paths
3. **Feature flags** for gradual rollout
4. **Code review** checkpoints weekly

## Refactoring Checklist

For each file being refactored:

1. **Pre-refactoring**
   - [ ] Create tests for existing behavior
   - [ ] Run performance benchmark
   - [ ] Document current hasattr patterns

2. **During refactoring**
   - [ ] Replace hasattr with appropriate pattern
   - [ ] Add type annotations
   - [ ] Update imports for Protocols
   - [ ] Verify with basedpyright

3. **Post-refactoring**
   - [ ] Run all tests
   - [ ] Compare performance metrics
   - [ ] Update documentation
   - [ ] Commit with descriptive message

## Example Migration

### Before (curve_view_plumbing.py)
```python
def get_view(target):
    return target if hasattr(target, "points") else target.curve_view
```

### After
```python
from typing import Protocol, Union

class PointsContainer(Protocol):
    points: list[CurvePoint]

class ViewContainer(Protocol):
    curve_view: PointsContainer

def get_view(target: Union[PointsContainer, ViewContainer]) -> PointsContainer:
    if isinstance(target, ViewContainer):
        return target.curve_view
    return target  # Already a PointsContainer
```

## Tooling Commands

```bash
# Count hasattr occurrences
rg "hasattr\(" --count-matches

# Find specific patterns
rg "hasattr\(.*statusBar" -A 2 -B 2

# Type check specific file
./bpr rendering/optimized_curve_renderer.py

# Run benchmarks
python -m pytest tests/benchmarks/ -v

# Check migration progress
python scripts/migration_progress.py
```

## Next Steps

1. **Immediate**: Start Week 1 Protocol interface creation
2. **This week**: Complete first 3 Protocol definitions
3. **Next review**: Weekly progress check on Fridays

---
*Phase 2 Start Date: January 6, 2025*
*Estimated Completion: February 2, 2025*
