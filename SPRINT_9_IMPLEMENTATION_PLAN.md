# Sprint 9: Type Safety & Testing - Implementation Plan

## Current State Analysis

### Type Checking Status (Critical)
- **900 type errors** (2x worse than expected 424)
- **11,272 warnings** (mostly PySide6 unknown types)
- **20 type: ignore** statements in our code (acceptable)

### Testing Status (Good)
- **600+ total tests** (534 in tests/ + 71 from Sprint 8)
- **19 test files** in tests/ directory
- **Test organization** needs improvement
- **Coverage** needs measurement

## Sprint 9 Goals

### Primary Objectives
1. ✅ Reduce type errors from 900 to <50
2. ✅ Achieve 80% test coverage
3. ✅ Remove unnecessary type: ignore
4. ✅ Make all tests meaningful
5. ✅ Consolidate test files

### Secondary Objectives
- Install PySide6 type stubs
- Fix critical type safety issues
- Improve test organization
- Add missing protocol types
- Document type patterns

## 7-Day Implementation Plan

### Day 1: Type Infrastructure Setup
**Goal**: Establish foundation for type safety improvements

#### Tasks:
1. **Install PySide6 Stubs**
   ```bash
   pip install types-PySide6-essentials
   # or
   pip install PySide6-stubs
   ```

2. **Update basedpyright Configuration**
   ```json
   {
     "reportUnknownMemberType": "none",  // Disable PySide6 warnings
     "reportUnknownParameterType": "warning",
     "reportMissingTypeStubs": "none",
     "typeCheckingMode": "standard"
   }
   ```

3. **Create Type Alias Module**
   ```python
   # core/typing_extensions.py
   from typing import TypeAlias, Union, Optional

   PointTuple: TypeAlias = tuple[int, float, float]
   PointTupleWithStatus: TypeAlias = tuple[int, float, float, str | bool]
   CurveData: TypeAlias = list[PointTuple | PointTupleWithStatus]
   ```

4. **Fix Import Cycle Issues**
   - Identify circular imports causing type errors
   - Use TYPE_CHECKING imports
   - Create protocol interfaces where needed

**Deliverables**:
- PySide6 warnings reduced by 90%
- Type alias module created
- basedpyright config optimized

---

### Day 2: Service Type Annotations
**Goal**: Fix type errors in new services from Sprint 8

#### Focus Areas:
1. **Event Handler Types**
   ```python
   # services/event_handler.py
   from typing import Protocol
   from PySide6.QtCore import QPointF
   from PySide6.QtGui import QMouseEvent

   def handle_mouse_press(
       self,
       view: "CurveViewProtocol",
       event: QMouseEvent,
       selection_service: SelectionProtocol,
       manipulation_service: ManipulationProtocol
   ) -> EventResult:
   ```

2. **Selection Service Types**
   ```python
   def select_point_by_index(
       self,
       view: CurveViewProtocol,
       idx: int,
       add_to_selection: bool = False
   ) -> bool:
   ```

3. **History Service Types**
   ```python
   def add_to_history(
       self,
       state: CurveData,
       description: str = ""
   ) -> None:
   ```

**Target**: Fix 200 type errors in services/

---

### Day 3: UI Component Type Safety
**Goal**: Fix type errors in UI components

#### Priority Files:
1. **ui/main_window.py** (~100 errors)
   - Add proper Qt type annotations
   - Fix signal/slot decorators
   - Type component containers

2. **ui/curve_view_widget.py** (~80 errors)
   - Annotate paint methods
   - Fix transform types
   - Type point collections

3. **ui/ui_components.py** (~50 errors)
   - Type all component groups
   - Fix container protocols
   - Add generic types

**Target**: Fix 250 type errors in ui/

---

### Day 4: Data & Rendering Types
**Goal**: Fix type errors in data processing and rendering

#### Focus Areas:
1. **data/*.py** (~150 errors)
   - Type curve operations
   - Fix numpy array types
   - Annotate view protocols

2. **rendering/*.py** (~100 errors)
   - Type QPainter methods
   - Fix coordinate types
   - Annotate render contexts

3. **core/*.py** (~100 errors)
   - Complete protocol definitions
   - Fix model types
   - Type utility functions

**Target**: Fix 350 type errors

---

### Day 5: Test Organization & Coverage
**Goal**: Consolidate tests and measure coverage

#### Tasks:
1. **Move Sprint 8 Tests**
   ```bash
   # Move test files to tests/
   mv test_*.py tests/sprint8/
   ```

2. **Install Coverage Tools**
   ```bash
   pip install pytest-cov coverage
   ```

3. **Run Coverage Analysis**
   ```bash
   pytest tests/ --cov=. --cov-report=html
   ```

4. **Identify Coverage Gaps**
   - Services < 80% coverage
   - UI components untested
   - Critical paths missing tests

5. **Create Test Plan**
   - List missing test areas
   - Prioritize by risk
   - Estimate test count needed

**Deliverables**:
- Coverage report generated
- Test gaps identified
- Test files organized

---

### Day 6: Write Missing Tests
**Goal**: Achieve 80% test coverage

#### Priority Areas:
1. **New Services (Sprint 8)**
   - Each service needs 10+ tests
   - Test error conditions
   - Test edge cases

2. **Critical Paths**
   ```python
   # tests/test_critical_paths.py
   def test_point_selection_workflow():
       """Test complete selection workflow."""

   def test_undo_redo_workflow():
       """Test undo/redo with state changes."""

   def test_file_save_load_cycle():
       """Test complete save/load cycle."""
   ```

3. **Integration Tests**
   ```python
   # tests/test_service_integration.py
   def test_all_services_with_feature_flag():
       """Test services work together."""
   ```

**Target**: Write 100+ new tests

---

### Day 7: Final Validation & Cleanup
**Goal**: Validate all improvements and document

#### Tasks:
1. **Final Type Check**
   ```bash
   ./bpr | grep "error" | wc -l
   # Target: <50 errors
   ```

2. **Final Coverage Check**
   ```bash
   pytest tests/ --cov=. --cov-report=term
   # Target: >80% coverage
   ```

3. **Remove Unnecessary type: ignore**
   ```python
   # Search and validate each usage
   grep -r "type: ignore" --include="*.py"
   ```

4. **Document Type Patterns**
   ```markdown
   # TYPE_SAFETY_GUIDE.md
   - How to type Qt signals/slots
   - Protocol usage patterns
   - Common type aliases
   ```

5. **Create Migration Guide**
   - List remaining type errors
   - Document workarounds
   - Plan for Sprint 10

**Deliverables**:
- <50 type errors
- >80% test coverage
- Type safety documentation

---

## Risk Mitigation

### High Risk Areas
1. **PySide6 Type Stubs**
   - May not exist or be incomplete
   - Mitigation: Disable PySide6 warnings if needed

2. **Time Constraint**
   - 900 errors in 7 days = 130/day
   - Mitigation: Focus on critical paths first

3. **Test Quality**
   - Risk of writing meaningless tests for coverage
   - Mitigation: Focus on behavior, not lines

### Fallback Plan
If we can't achieve <50 errors:
1. Focus on critical type safety (no Any types)
2. Document remaining issues
3. Create technical debt tickets

## Success Metrics

### Must Have (Day 7)
- [ ] Type errors < 100 (from 900)
- [ ] Test coverage > 70%
- [ ] All new services fully typed
- [ ] Critical paths tested

### Should Have
- [ ] Type errors < 50
- [ ] Test coverage > 80%
- [ ] PySide6 warnings resolved
- [ ] All tests meaningful

### Nice to Have
- [ ] Type errors < 25
- [ ] Test coverage > 90%
- [ ] Zero type: ignore
- [ ] Performance benchmarks

## Daily Schedule

| Day | Focus | Errors Fixed | Tests Added | Target |
|-----|-------|--------------|-------------|--------|
| 1 | Infrastructure | 200 | 0 | Setup complete |
| 2 | Services | 200 | 20 | Services typed |
| 3 | UI Components | 250 | 20 | UI typed |
| 4 | Data/Rendering | 350 | 20 | Core typed |
| 5 | Test Organization | 0 | 0 | Tests organized |
| 6 | Missing Tests | 0 | 100 | 80% coverage |
| 7 | Validation | 50 | 20 | Sprint complete |

**Total**: 850 errors fixed, 180 tests added

## Implementation Order

### Why This Order?
1. **Infrastructure first** - Makes everything else easier
2. **Services second** - They're already clean from Sprint 8
3. **UI third** - Most complex, needs service types
4. **Data/rendering fourth** - Depends on other types
5. **Tests fifth-seventh** - After code is typed

## Tools & Commands

### Useful Commands
```bash
# Check type errors
./bpr | grep "error" | wc -l

# Check specific file
./bpr path/to/file.py

# Run coverage
pytest tests/ --cov=. --cov-report=html

# Find type: ignore
grep -r "type: ignore" --include="*.py" .

# Find Any types
grep -r ": Any" --include="*.py" .
```

### VS Code Extensions
- Pylance (Microsoft)
- Python Test Explorer
- Coverage Gutters

## Conclusion

Sprint 9 will be challenging due to the 900 type errors (2x expected), but achievable with focused effort. The key is to:

1. **Reduce noise** by configuring tools properly
2. **Focus on real errors** not PySide6 warnings
3. **Write meaningful tests** not coverage padding
4. **Document patterns** for future development

Success depends on disciplined execution and not getting bogged down in perfect type coverage. The goal is safety and maintainability, not zero errors.

---

**Sprint Duration**: 7 days
**Start Date**: [Next working day]
**End Date**: [7 days later]
**Risk Level**: High (due to error volume)
**Success Probability**: 70% for <50 errors, 90% for <100 errors
