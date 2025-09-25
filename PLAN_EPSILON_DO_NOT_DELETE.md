# PLAN EPSILON - DO NOT DELETE
## Comprehensive Code Refactoring Plan - Prioritized by Impact

Based on multi-agent comprehensive review of CurveEditor codebase focusing on SOLID, DRY, KISS, and YAGNI principles.

**Review Date**: 2025-09-25
**Total Estimated Refactoring Time**: 20-30 hours
**Expected Code Reduction**: ~2,500-3,000 lines

---

## VIOLATION SUMMARY

### Critical Issues Found:
- **SOLID Violations**: 10 major violations (2 Critical, 4 High, 3 Medium, 1 Low)
- **DRY Violations**: ~400+ lines of duplicated code across 8 major patterns
- **KISS Violations**: ~1,950 lines of unnecessary abstraction
- **YAGNI Violations**: ~1,200+ lines of unused or speculative code

### Most Severe Multi-Principle Violations:
1. **Service Architecture**: Violates SOLID (SRP, DIP), KISS, and YAGNI
2. **Path Security Module**: Violates YAGNI and KISS
3. **Signal Management**: Violates YAGNI and KISS
4. **Transform System**: Violates KISS and DRY
5. **Test Infrastructure**: Violates DRY and YAGNI

---

## PHASE 1: IMMEDIATE WINS
**Time**: 1-2 hours
**Impact**: Removes ~500 lines, eliminates 100MB dependency

### 1.1 Delete Unused CurveSegment Module
- **File**: `core/curve_segments.py`
- **Size**: 150+ lines of completely dead code
- **Violations**: YAGNI
- **Evidence**: No imports or usage anywhere in codebase
- **Action**: Simple deletion

### 1.2 Remove/Simplify Scipy Dependency
- **Location**: `services/data_service.py` lines 169-216
- **Issue**: Entire scipy library (~100MB) for one Butterworth filter
- **Usage**: Only in `filter_butterworth()` method
- **Violations**: YAGNI, KISS
- **Action**: Replace with simpler filter or make optional

### 1.3 Consolidate ThreadSafeTestImage
- **Duplicated In**:
  - `/tests/test_helpers.py` (lines 100-155)
  - `/tests/qt_test_helpers.py` (lines 18-66)
  - `/tests/test_background_image_fitting.py` (lines 20-57)
- **Size**: 140+ lines duplicated 3 times
- **Violations**: DRY
- **Action**: Keep only in `qt_test_helpers.py`, delete others

---

## PHASE 2: TEST CODE CLEANUP
**Time**: 2-3 hours
**Impact**: Improves test maintainability

### 2.1 Extract Widget Cleanup Function
- **Pattern Repeated In**:
  - `/tests/fixtures/qt_fixtures.py` (5+ occurrences)
  - `/tests/test_helpers.py`
- **Violations**: DRY
- **Action**: Create single `cleanup_widgets(qapp)` utility

### 2.2 Simplify Test Fixtures
- **Location**: `/tests/fixtures/`
- **Issue**: Over-engineered fixture system
- **Violations**: YAGNI, KISS
- **Action**: Remove unnecessary abstractions

---

## PHASE 3: CORE SIMPLIFICATIONS
**Time**: 4-6 hours
**Impact**: Reduces complexity by ~700 lines

### 3.1 Simplify Path Security
- **File**: `core/path_security.py`
- **Current**: 456 lines of enterprise-grade security
- **Target**: ~50 lines of basic validation
- **Violations**: YAGNI, KISS

### 3.2 Centralize Y-Axis Flip Logic
- **File**: `ui/curve_view_widget.py`
- **Duplicated**: 7 times (lines 459, 787, 945, 1160, 1210, 1245, 1558)
- **Violations**: DRY
- **Action**: Extract to helper methods

### 3.3 Extract Centering Logic
- **Methods**: `center_on_selection()`, `center_on_frame()`
- **Duplicated**: 20+ lines of identical logic
- **Violations**: DRY

### 3.4 Simplify Transform System
- **Location**: `services/transform_service.py`, `ui/curve_view_widget.py`
- **Issue**: LRU caching for trivial math operations
- **Violations**: KISS

---

## PHASE 4: ARCHITECTURAL REFACTORING
**Time**: 8-12 hours
**Impact**: Addresses fundamental design issues

### 4.1 Implement Dependency Injection
- **Current Issue**: Global singleton services
- **Files Affected**: All services and UI components
- **Violations**: SOLID (DIP)
- **Critical Priority**: Blocks proper testing and modularity

### 4.2 Simplify Service Architecture
- **Current**: 4 services + protocols + facade
- **Target**: 1-2 services or single data manager
- **Violations**: KISS, YAGNI, SOLID (SRP)

### 4.3 Refactor MainWindow Responsibilities
- **Current**: 1000+ lines doing too much
- **Violations**: SOLID (SRP)
- **Action**: Extract to appropriate services

### 4.4 Simplify Signal Management
- **File**: `core/signal_manager.py`
- **Size**: 245 lines reinventing Qt features
- **Violations**: YAGNI, KISS

---

## PHASE 5: PROTOCOL & INTERFACE CLEANUP
**Time**: 3-4 hours
**Impact**: Cleaner interfaces

### 5.1 Trim Protocol Interfaces
- **File**: `services/service_protocols.py`
- **Issue**: 427 lines, many unused methods
- **Violations**: SOLID (ISP), YAGNI

### 5.2 Simplify Exception Utilities
- **File**: `core/exception_utils.py`
- **Size**: 193 lines of wrapper functions
- **Violations**: KISS

---

## PHASE 6: FINAL POLISH
**Time**: 2-3 hours
**Impact**: Improved consistency

### 6.1 Complete Color System Migration
- **Status**: Partially done
- **Violations**: DRY

### 6.2 Consolidate Controller Pattern
- **Current**: 10 controllers
- **Target**: 3-4 controllers
- **Violations**: KISS

---

## EXPECTED OUTCOMES

### Quantitative Improvements:
- **Code Reduction**: 2,500-3,000 lines removed
- **Dependency Size**: -100MB (scipy removal)
- **Service Count**: 4 → 1-2
- **Controller Count**: 10 → 3-4
- **Protocol Complexity**: -50% methods

### Qualitative Improvements:
- **Maintainability**: Centralized logic, no duplication
- **Type Safety**: Proper dependency injection
- **Code Flow**: Simpler architecture, clearer paths
- **Testing**: Easier to test with DI
- **Performance**: Remove unnecessary caching

---

## RISK ASSESSMENT

### Low Risk:
- Phase 1: All dead code or clear duplications
- Phase 2: Test-only changes

### Medium Risk:
- Phase 3: Core simplifications (needs thorough testing)
- Phase 5-6: Interface changes

### High Risk:
- Phase 4: Architectural changes (needs careful planning)

---

## IMPLEMENTATION NOTES

1. **Run tests after each phase** to ensure nothing breaks
2. **Create feature branches** for each phase
3. **Document breaking changes** if any
4. **Consider backwards compatibility** for file formats
5. **Update CLAUDE.md** after major architectural changes

---

## METRICS TO TRACK

- Lines of code before/after
- Test execution time
- Type checking warnings
- Cyclomatic complexity
- Dependency graph complexity

---

*Generated by comprehensive multi-agent code review focusing on SOLID, DRY, KISS, and YAGNI principles*
