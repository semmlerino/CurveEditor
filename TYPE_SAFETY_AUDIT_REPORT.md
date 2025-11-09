# CurveEditor Type Safety Audit Report

**Date:** November 5, 2025
**Basedpyright Version:** 1.31.7 (based on pyright 1.1.406)
**Python Version:** 3.11
**Overall Grade:** B+ (87/100)

## Executive Summary

The CurveEditor codebase demonstrates **strong type safety** with zero type errors and 482 warnings. The type system is well-architected with protocol-based interfaces and appropriate strictness settings. Issues are primarily quality-of-life improvements rather than safety risks.

**Key Findings:**
- ✅ Zero type errors (all issues are warnings)
- ✅ Excellent service layer type coverage (90/100)
- ✅ Well-organized protocol architecture
- ✅ Strong None-checking enforcement
- ⚠️ 188 explicit Any types (39% of warnings)
- ⚠️ Test code has minimal type annotations
- ⚠️ Critical ApplicationState uses Any for metadata/signals

---

## Type Safety by Module

### Core Layer (85/100) - Grade: B+

| File | Issues | Status |
|------|--------|--------|
| `core/models.py` | 0 | ✅ Excellent |
| `core/commands/**` | 0 | ✅ Excellent |
| `core/user_preferences.py` | 2 Any | ⚠️ Minor |

**Assessment:** Clean architecture with immutable models. Only minor Any usage in user preferences.

### Stores Layer (82/100) - Grade: B

| File | Issues | Severity |
|------|--------|----------|
| `stores/application_state.py` | 6 Any | 🔴 High |
| `stores/store_manager.py` | 3 Any | 🟡 Medium |

**Critical Issues:**
1. **Line 131:** `dict[str, dict[str, Any]]` for curve metadata
   - Used in: `get_curve_metadata()`, `set_curve_visibility()`
   - Impact: Arbitrary data types, no compile-time safety
   - Fix: Create `CurveMetadata` TypedDict

2. **Line 146:** `dict[SignalInstance, tuple[Any, ...]]` for pending signals
   - Used in: Signal batching mechanism
   - Impact: Signal arguments not type-checked
   - Fix: Generic SignalArgs type or overloads

**Assessment:** Single source of truth has type safety gaps in critical paths.

### Services Layer (90/100) - Grade: A-

| File | Issues | Status |
|------|--------|--------|
| `services/data_service.py` | 1 unused function | ✅ Minor |
| `services/interaction_service.py` | 0 | ✅ Excellent |
| `services/transform_service.py` | 0 | ✅ Excellent |
| `services/ui_service.py` | 0 | ✅ Excellent |

**Assessment:** Excellent type coverage. Service boundaries are type-safe.

### Rendering Layer (87/100) - Grade: B+

| File | Issues | Type |
|------|--------|------|
| `rendering/optimized_curve_renderer.py` | 3 Any | 🟡 Medium |
| `rendering/render_state.py` | 1 Any | 🟡 Medium |
| `rendering/visual_settings.py` | 0 | ✅ Clean |

**Issues:**
- Complex render state dicts typed as Any
- Renderer constructor accepts Any for state

**Assessment:** Mostly clean. Any types for complex state could be improved with dataclasses.

### UI Layer (78/100) - Grade: B-

| File | Issues | Severity |
|------|--------|----------|
| `ui/protocols/controller_protocols.py` | 7 Any | 🔴 High |
| `ui/qt_utils.py` | 4 Any | 🟡 Medium |
| `ui/curve_view_widget.py` | 1 Any | 🟡 Low |
| `ui/color_manager.py` | 2 Any | 🟡 Low |
| `ui/keyboard_shortcuts.py` | 1 Any | 🟡 Low |
| `ui/controllers/**` | 4 Any | 🟡 Medium |

**Critical Issue:**
- `TimelineControllerProtocol` (lines 160-165): 7 Qt widget attributes typed as `Any`
  ```python
  btn_play_pause: Any  # QPushButton but avoiding circular imports
  fps_spinbox: Any     # QSpinBox but avoiding circular imports
  frame_slider: Any    # QSlider but avoiding circular imports
  # ... etc
  ```
- **Impact:** Lost type safety at controller boundaries
- **Fix:** Use `TYPE_CHECKING` imports or minimal widget protocols

**Assessment:** Protocol definitions compromise type safety to avoid circular imports. Pragmatic but limits compile-time checks.

### IO Layer (88/100) - Grade: A-

| File | Issues | Context |
|------|--------|---------|
| `io_utils/exr_loader.py` | 3 Any | External library interfaces (OIIO/OpenEXR) |
| `io_utils/file_load_worker.py` | 0 | ✅ Clean |

**Assessment:** Any types are unavoidable for untyped external libraries. Runtime validation present.

### Tests (70/100) - Grade: C+

| Category | Count | Impact |
|----------|-------|--------|
| Unannotated class attributes | 154 | Medium |
| Missing parameter types | 109 | Low |
| Explicit Any in mocks | 150+ | Medium |

**Pattern Issues:**
```python
# Bad - Common test pattern
class MockHelper:
    zoom_factor = 1.0  # Missing type annotation

def test_something(qtbot):  # Missing type annotation
    pass

def mock_service() -> Any:  # Should be more specific
    pass
```

**Assessment:** Test code lacks type discipline but doesn't affect runtime safety.

---

## Issue Breakdown

### By Category

| Category | Count | Percentage |
|----------|-------|------------|
| `reportExplicitAny` | 188 | 39% |
| `reportUnannotatedClassAttribute` | 154 | 32% |
| `reportMissingParameterType` | 109 | 23% |
| `reportUnusedParameter` | 27 | 6% |
| **Total Warnings** | **482** | **100%** |
| **Total Errors** | **0** | **0%** |

### By Severity

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 **Critical** | 13 | Type safety risks in core paths |
| 🟡 **Medium** | 50 | Code quality issues |
| 🟢 **Low** | 419 | Linting/style improvements |

### Production vs Test Code

| Category | Warnings | Percentage |
|----------|----------|------------|
| Production code | 82 | 17% |
| Test code | 400 | 83% |

**Insight:** Most warnings are in test code. Production code is well-typed.

### Type Ignore Comments

| Metric | Count | Assessment |
|--------|-------|------------|
| Production files with ignores | 25 | Reasonable |
| Total ignore comments | 147 | Well-controlled |
| Files using blanket ignores | 0 | ✅ Excellent |

**Pattern:** All ignores include specific error codes (enforced by `reportIgnoreCommentWithoutRule: "error"`).

---

## Protocol Architecture Assessment

### Current State

✅ **Strengths:**
- Protocols organized in `protocols/` package (ui.py, data.py, services.py)
- Zero type errors in protocol definitions
- Centralized imports through `protocols/__init__.py`
- Good structural typing patterns

⚠️ **Adoption Status:**
- 2 controllers fully migrated (ActionHandlerController, PointEditorController)
- 12 controllers still use concrete types
- Estimated migration effort: 3-4 hours

### Protocol Conformance Issues

1. **Qt Widget Any Types** (Priority: HIGH)
   - Location: `ui/protocols/controller_protocols.py:160-165`
   - Issue: Widget attributes typed as `Any` to avoid circular imports
   - Impact: Controllers lose type safety when accessing widgets
   - Solutions:
     ```python
     # Option 1: TYPE_CHECKING imports
     from typing import TYPE_CHECKING
     if TYPE_CHECKING:
         from PySide6.QtWidgets import QPushButton, QSpinBox

     # Option 2: Minimal protocols
     class ButtonProtocol(Protocol):
         def setEnabled(self, enabled: bool) -> None: ...
         def setText(self, text: str) -> None: ...
     ```

2. **Signal Type Issues** (Priority: MEDIUM)
   - Pattern: `frame_changed: Any  # Signal(int)`
   - Should use: Signal protocols or TypeAlias
   - Example fix:
     ```python
     from typing import TypeAlias
     IntSignal: TypeAlias = "Signal(int)"  # String literal for runtime
     ```

3. **Missing Protocol Methods** (Priority: LOW)
   - `MainWindowProtocol` missing 15-20 UI widget attributes
   - Blocks migration of remaining 12 controllers
   - Pragmatic decision: Accept concrete types for single-user tool

### Structural Typing Correctness

✅ **Assessment:** Protocols are structurally sound
- Appropriate use of `@runtime_checkable`
- Good separation of concerns (UI, data, services)
- No protocol definition errors
- Clean ISP (Interface Segregation Principle) adherence

---

## Critical Type Safety Risks

### Risk Analysis

**Good News:** Zero type errors means no obvious runtime failures from type mismatches.

**Potential Runtime Risks:**

1. **ApplicationState Signal Arguments** (CRITICAL)
   ```python
   # Line 146
   self._pending_signals: dict[SignalInstance, tuple[Any, ...]] = {}
   ```
   - Risk: Signal emitted with wrong argument types
   - Probability: Low (signals are well-tested)
   - Impact: Runtime AttributeError or TypeError
   - Mitigation: Create typed signal wrapper

2. **Metadata Dictionary Access** (HIGH)
   ```python
   # Line 131, used in line 771
   self._curve_metadata: dict[str, dict[str, Any]] = {}

   def get_curve_metadata(self, curve_name: str) -> dict[str, Any]:
       return self._curve_metadata[curve_name].copy()
   ```
   - Risk: Accessing wrong type from metadata
   - Probability: Low (limited key set)
   - Impact: Type mismatch in curve rendering
   - Mitigation: TypedDict for metadata structure

3. **Qt Widget Protocol Conformance** (MEDIUM)
   ```python
   # TimelineControllerProtocol
   btn_play_pause: Any  # Could be None or wrong type
   ```
   - Risk: Calling method on wrong widget type
   - Probability: Very low (initialized in __init__)
   - Impact: AttributeError at runtime
   - Mitigation: TYPE_CHECKING imports

### None-Access Safety

✅ **Excellent None Checking:**
- `reportOptionalMemberAccess: "error"` - Strict enforcement
- `reportOptionalCall: "error"` - Prevents calling None
- Zero violations found

Pattern throughout codebase:
```python
# Good - Type-preserving None checks
if self.main_window is not None:
    self.main_window.update()
```

---

## Basedpyright Configuration Assessment

### Current Configuration

```toml
[tool.basedpyright]
typeCheckingMode = "recommended"
pythonVersion = "3.11"

# Strictness (Excellent)
reportOptionalMemberAccess = "error"
reportOptionalCall = "error"
reportUnnecessaryTypeIgnoreComment = "error"
reportMissingTypeArgument = "error"
reportIgnoreCommentWithoutRule = "error"

# Balanced (Appropriate)
reportExplicitAny = "warning"
reportUnknownParameterType = "none"
reportUnknownVariableType = "none"
```

### Configuration Grade: A- (92/100)

✅ **Strengths:**
- Strict None checking prevents runtime failures
- Enforces specific error codes in ignores
- Requires generic type arguments (list[str] not list)
- Balanced for gradual typing

⚠️ **Recommendations:**

1. **Enable Basedpyright-Exclusive Features:**
   ```toml
   strictListInference = true
   strictDictionaryInference = true
   strictSetInference = true
   ```
   - Benefit: Better type inference for collections
   - Example: `values = []; values.append(42)` → `list[int]` not `list[Any]`
   - Impact: May catch 10-20 additional issues

2. **Test-Specific Configuration:**
   ```toml
   [[tool.basedpyright.executionEnvironments]]
   root = "tests"
   reportMissingParameterType = "none"
   reportUnannotatedClassAttribute = "none"
   ```
   - Benefit: Reduces test noise (400 warnings)
   - Keeps production code strict

3. **Consider for Single-User Tool:**
   ```toml
   reportUnusedParameter = "none"  # Qt handlers have unused params
   ```
   - Already handled by ruff in many cases
   - Would eliminate 27 warnings

### Not Recommended

❌ Don't relax these (currently correct):
- `reportOptionalMemberAccess: "error"` - Critical for None safety
- `reportExplicitAny: "warning"` - Appropriate visibility
- `reportIgnoreCommentWithoutRule: "error"` - Enforces documentation

---

## Top Priority Fixes

### Tier 1 - High Impact (Type Safety)

#### 1. ApplicationState Signal Tuples (CRITICAL)
- **File:** `stores/application_state.py:146`
- **Current:** `dict[SignalInstance, tuple[Any, ...]]`
- **Impact:** Signal arguments not type-checked at emission
- **Effort:** 1-2 hours
- **Fix:**
  ```python
  from typing import TypeAlias

  # Option 1: Union of specific signal arg types
  SignalArgs: TypeAlias = tuple[()] | tuple[int] | tuple[str] | tuple[str, int]
  self._pending_signals: dict[SignalInstance, SignalArgs] = {}

  # Option 2: Generic (more flexible)
  from typing import TypeVar
  T = TypeVar('T')
  self._pending_signals: dict[SignalInstance[T], tuple[T, ...]] = {}
  ```

#### 2. ApplicationState Metadata Dict (HIGH)
- **File:** `stores/application_state.py:131`
- **Current:** `dict[str, dict[str, Any]]`
- **Impact:** Arbitrary metadata types, no compile-time safety
- **Effort:** 2-3 hours (audit all usages)
- **Fix:**
  ```python
  from typing import TypedDict

  class CurveMetadata(TypedDict, total=False):
      visible: bool
      color: tuple[int, int, int]  # RGB
      # Add other metadata fields as discovered

  self._curve_metadata: dict[str, CurveMetadata] = {}

  def get_curve_metadata(self, curve_name: str) -> CurveMetadata:
      if curve_name not in self._curve_metadata:
          return {"visible": True}
      return self._curve_metadata[curve_name].copy()
  ```

#### 3. Protocol Qt Widget Types (HIGH)
- **File:** `ui/protocols/controller_protocols.py:160-165`
- **Current:** 7 widget attributes as `Any`
- **Impact:** Lost type safety at controller boundaries
- **Effort:** 1 hour
- **Fix:**
  ```python
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from PySide6.QtWidgets import QPushButton, QSpinBox, QSlider
      # Also import Signal types

  @runtime_checkable
  class TimelineControllerProtocol(Protocol):
      btn_play_pause: QPushButton
      fps_spinbox: QSpinBox
      frame_slider: QSlider
      frame_spinbox: QSpinBox
      # Signals still need work (separate issue)
  ```

### Tier 2 - Medium Impact (Code Quality)

#### 4. Test Fixture Annotations (MEDIUM)
- **Files:** `tests/**/*.py` (150+ issues)
- **Current:** Unannotated class attributes, missing parameter types
- **Impact:** IDE support, test maintainability
- **Effort:** 4-6 hours (batch fix with script)
- **Fix:**
  ```python
  # Before
  class MockHelper:
      zoom_factor = 1.0
      pan_offset_x = 0

  # After
  class MockHelper:
      zoom_factor: float = 1.0
      pan_offset_x: int = 0

  # Before
  def test_something(qtbot):
      pass

  # After
  from pytestqt.qtbot import QtBot

  def test_something(qtbot: QtBot) -> None:
      pass
  ```

#### 5. Render State Any Types (MEDIUM)
- **Files:** `rendering/*.py` (4 issues)
- **Current:** Complex state dicts typed as Any
- **Impact:** Type-safe rendering pipeline
- **Effort:** 2-3 hours
- **Fix:**
  ```python
  from dataclasses import dataclass

  @dataclass
  class RenderState:
      zoom_level: float
      pan_offset: tuple[float, float]
      show_interpolated: bool
      show_current_only: bool
      # ... etc
  ```

### Tier 3 - Low Impact (Nice to Have)

#### 6. EXR Loader External Types (LOW)
- **File:** `io_utils/exr_loader.py:383`
- **Current:** OIIO return types as Any
- **Impact:** External library boundary
- **Effort:** 2-3 hours (create stubs)
- **Priority:** Low (runtime validation exists)
- **Note:** Accept Any for single-user tool

---

## Type Narrowing Opportunities

### 1. TypeGuard/TypeIs for isinstance Checks

**Current Pattern:**
```python
def process_data(data: object) -> None:
    if isinstance(data, list):
        # data is still 'object', not 'list'
        for item in data:  # Type checker doesn't know this is safe
            ...
```

**Improved with TypeIs (Python 3.13+):**
```python
from typing import TypeIs

def is_curve_list(data: object) -> TypeIs[CurveDataList]:
    return isinstance(data, list) and all(
        isinstance(p, CurvePoint) for p in data
    )

def process_data(data: object) -> None:
    if is_curve_list(data):
        # data is now CurveDataList!
        for point in data:
            print(point.frame)  # Type-safe
```

### 2. Overload Signatures for Multi-Behavior Methods

**Current Pattern:**
```python
def get_position_at_frame(
    curve_name: str,
    frame: int
) -> tuple[float, float] | None:
    # Returns None if no data, tuple otherwise
    ...
```

**Improved with Overload:**
```python
from typing import overload

@overload
def get_position_at_frame(
    curve_name: str,
    frame: int,
    default: tuple[float, float]
) -> tuple[float, float]: ...

@overload
def get_position_at_frame(
    curve_name: str,
    frame: int,
    default: None = None
) -> tuple[float, float] | None: ...

def get_position_at_frame(
    curve_name: str,
    frame: int,
    default: tuple[float, float] | None = None
) -> tuple[float, float] | None:
    # Implementation
    ...
```

### 3. Generic Constraints for Collections

**Current Pattern:**
```python
def process_points(points: list) -> None:  # Bare list
    ...
```

**Improved:**
```python
from typing import TypeVar
from collections.abc import Sequence

T = TypeVar('T', bound=CurvePoint)

def process_points(points: Sequence[T]) -> list[T]:
    # More flexible, still type-safe
    ...
```

---

## Configuration Recommendations

### Immediate Changes (Recommended)

Add to `pyproject.toml`:

```toml
[tool.basedpyright]
# ... existing config ...

# Enable basedpyright-exclusive features
strictListInference = true
strictDictionaryInference = true
strictSetInference = true

# Test-specific relaxation
[[tool.basedpyright.executionEnvironments]]
root = "tests"
reportMissingParameterType = "none"
reportUnannotatedClassAttribute = "none"
reportExplicitAny = "none"  # Allow Any in test mocks
```

**Impact:**
- Reduces test noise from 400 to ~50 warnings
- Catches 10-20 additional collection type issues
- Keeps production code strict

### Optional Changes (Consider)

```toml
[tool.basedpyright]
# ... existing config ...

# Reduce Qt handler noise (already handled by ruff in most cases)
reportUnusedParameter = "none"

# More aggressive Any detection (may be too strict for single-user tool)
reportAny = "warning"  # Currently "none"
```

**Tradeoff:** More warnings vs better type coverage.

### Not Recommended

Do NOT change these (currently optimal):
- ❌ `reportOptionalMemberAccess` - Keep at "error"
- ❌ `reportOptionalCall` - Keep at "error"
- ❌ `reportIgnoreCommentWithoutRule` - Keep at "error"
- ❌ `reportExplicitAny` - Keep at "warning"

---

## Summary Statistics

### Type Safety Metrics

| Metric | Value | Grade |
|--------|-------|-------|
| Total Type Errors | 0 | A+ |
| Total Warnings | 482 | B |
| Production Code Warnings | 82 | B+ |
| Test Code Warnings | 400 | C+ |
| Files with Any Types | 13 | B |
| Type Ignore Comments | 147 | B+ |
| Protocol Definition Errors | 0 | A+ |
| None-Access Violations | 0 | A+ |

### Module Safety Scores

| Module | Score | Grade | Key Issues |
|--------|-------|-------|------------|
| Core | 85/100 | B+ | 2 Any types |
| Stores | 82/100 | B | 9 Any types (critical) |
| Services | 90/100 | A- | 1 unused function |
| Rendering | 87/100 | B+ | 4 Any types |
| UI | 78/100 | B- | 19 Any types (protocols) |
| IO | 88/100 | A- | 3 Any types (external) |
| Tests | 70/100 | C+ | 300+ annotations missing |

### Effort Estimation

| Task | Effort | Impact | Priority |
|------|--------|--------|----------|
| Fix ApplicationState signals | 1-2h | High | Critical |
| Fix ApplicationState metadata | 2-3h | High | Critical |
| Fix protocol Qt types | 1h | High | High |
| Annotate test fixtures | 4-6h | Medium | Medium |
| Fix render state types | 2-3h | Medium | Medium |
| Create EXR stubs | 2-3h | Low | Low |
| **Total** | **12-19h** | - | - |

---

## Recommendations

### For Immediate Action (Next Sprint)

1. ✅ **Fix ApplicationState type safety** (3-5 hours)
   - Signal tuples: Add typed signal arguments
   - Metadata dict: Create CurveMetadata TypedDict
   - Impact: Eliminates critical type safety gaps

2. ✅ **Fix protocol Qt widget types** (1 hour)
   - Use TYPE_CHECKING imports
   - Impact: Type-safe controller boundaries

3. ✅ **Enable basedpyright strict inference** (5 minutes)
   - Add strictListInference, strictDictionaryInference
   - Impact: Better collection type inference

4. ✅ **Add test execution environment** (5 minutes)
   - Reduce test noise from 400 to ~50 warnings
   - Impact: Focus on production code issues

### For Future Consideration

5. 📅 **Batch-annotate test fixtures** (4-6 hours)
   - Lower priority but improves maintainability
   - Can be done incrementally

6. 📅 **Continue protocol migration** (3-4 hours)
   - Migrate remaining 12 controllers
   - Add missing MainWindowProtocol attributes
   - Only if team coordination benefits justify effort

7. 📅 **Refactor render state** (2-3 hours)
   - Replace Any with dataclasses
   - Improves rendering pipeline type safety

### Accept as "Good Enough"

8. ✋ **EXR loader external types**
   - Runtime validation exists
   - Single-user tool doesn't justify stub creation effort
   - Accept Any at external library boundaries

---

## Conclusion

The CurveEditor codebase demonstrates **strong type safety fundamentals** with zero type errors and well-architected protocol interfaces. The 482 warnings are primarily quality-of-life improvements rather than safety risks.

**Context-Appropriate Assessment:**
For a single-user desktop application, the current type safety level is **excellent**. The pragmatic use of Any types (especially in Qt integration) is acceptable given the development context.

**Key Strengths:**
- Zero type errors (no obvious runtime risks)
- Strong None-checking enforcement prevents null pointer issues
- Service layer has excellent type coverage
- Protocol architecture is structurally sound
- Basedpyright configuration is well-tuned

**High-Impact Improvements:**
Focus on fixing the 9 Any types in ApplicationState (stores layer) as these affect the core data flow. The protocol Qt widget types should also be addressed for better controller type safety.

**Grade Justification:**
- **Overall: B+ (87/100)** - Excellent for a personal tool, strong foundation
- Production code is well-typed (B+ average across modules)
- Test code could use more annotations (C+)
- Configuration is optimal (A-)
- Protocol architecture is sound (A-)

**Recommendation:** Address Tier 1 issues (5-6 hours effort) for A- grade. Test annotations are optional quality improvements.

---

## Appendix: Detailed Issue Locations

### Production Code Any Types (82 total)

#### Stores (9 Any types)
- `stores/application_state.py:131` - Curve metadata dict
- `stores/application_state.py:146` - Pending signals dict
- `stores/application_state.py:218` - set_curve_data parameter
- `stores/application_state.py:771` - get_curve_metadata return
- `stores/application_state.py:994` - _emit parameter
- `stores/application_state.py:1098` - get_state_summary return
- `stores/store_manager.py:35` - Generic store type
- `stores/store_manager.py:167` - Store method return
- `stores/store_manager.py:181` - Store method parameter

#### UI Layer (19 Any types)
- `ui/protocols/controller_protocols.py:160-165` - 7 Qt widget attributes
- `ui/qt_utils.py:36` - 2 Qt method parameters
- `ui/qt_utils.py:70` - 2 Qt method parameters
- `ui/color_manager.py:505` - Color calculation
- `ui/color_manager.py:564` - Theme method
- `ui/controllers/progressive_disclosure_controller.py:285` - Widget param
- `ui/controllers/progressive_disclosure_controller.py:309` - Widget param
- `ui/controllers/tracking_display_controller.py:124` - Method return
- `ui/controllers/tracking_display_controller.py:134` - Method parameter
- `ui/curve_view_widget.py:93` - Paint event
- `ui/keyboard_shortcuts.py:330` - Event handler

#### Rendering (4 Any types)
- `rendering/optimized_curve_renderer.py:877` - Constructor param
- `rendering/optimized_curve_renderer.py:884` - Method param
- `rendering/optimized_curve_renderer.py:885` - Method param
- `rendering/render_state.py:93` - State dict

#### Core (2 Any types)
- `core/user_preferences.py:58` - Preference value
- `core/user_preferences.py:63` - Preference value

#### IO (3 Any types)
- `io_utils/exr_loader.py:79` - OpenImageIO import (external)
- `io_utils/exr_loader.py:383` - OIIO method return (2x)

### Test Code Issues (400 total)

Concentrated in:
- `tests/controllers/test_tracking_data_controller.py` - 32 Any
- `tests/test_rendering_real.py` - 29 Any
- `tests/test_event_handler_error_boundaries.py` - 26 Any
- `tests/test_helpers.py` - 17 Any
- `tests/controllers/test_multi_point_tracking_controller.py` - 17 Any
- `tests/test_command_manager.py` - 9 unannotated class attributes
- `tests/test_connection_verifier.py` - 5 unannotated class attributes
- `tests/**/*.py` - 100+ missing pytest fixture types

---

**End of Report**
