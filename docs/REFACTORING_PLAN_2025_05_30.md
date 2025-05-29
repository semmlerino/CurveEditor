# CurveEditor Refactoring Plan
## Date: 2025-05-30

## Overview

This document outlines the refactoring tasks identified through code review. The project is currently at 9.2/10 quality score, with most major refactoring completed. The focus is now on fixing type checking errors, completing the transformation system migration, and improving test coverage.

## Task Priority Matrix

### 🔴 Critical (Blocking Issues)

1. **Fix Type Checking Errors** - 9 mypy errors preventing type safety enforcement
   - analyze_imports.py: Missing type annotation for `imports` set
   - main_window.py: Protocol incompatibility issue with DialogService
   - services/transformation_integration.py: Duplicate import of UnifiedTransformationService
   - tests/test_centering_zoom.py: Multiple type assignment and redefinition errors

### 🟡 High Priority (Functional Improvements)

2. **Complete Transformation System Migration**
   - Remove dual system coexistence (TransformStabilizer + UnifiedTransformationService)
   - Update all transformation calls to use unified system exclusively
   - Remove legacy transformation code and compatibility layers
   - Validate all smoothing operations work with new system

3. **Test Coverage Improvement**
   - Install and configure pytest-cov
   - Run initial coverage analysis
   - Add tests for critical paths with low coverage
   - Establish 80% minimum coverage target

### 🟢 Medium Priority (Developer Experience)

4. **Pre-commit Configuration**
   - Create .pre-commit-config.yaml with:
     - Black (code formatting)
     - Flake8 (linting)
     - mypy (type checking)
     - isort (import sorting)
   - Document setup process

5. **Documentation Updates**
   - Add docstrings to all public methods
   - Generate API documentation with Sphinx
   - Update migration guide for transformation system

### 🔵 Low Priority (Nice to Have)

6. **Performance Monitoring**
   - Add performance benchmarks for transformation operations
   - Create profiling scripts for critical paths
   - Set up performance regression tests

7. **CI/CD Pipeline**
   - Configure GitHub Actions
   - Automated testing on pull requests
   - Coverage reporting integration

## Detailed Task Breakdown

### Task 1: Fix Type Checking Errors

#### 1.1 analyze_imports.py
- **Issue**: Line 110 - Missing type annotation for `imports` set
- **Fix**: Add proper type annotation: `imports: set[str] = set()`

#### 1.2 main_window.py
- **Issue**: Line 871 - Protocol incompatibility with DialogService.fill_gap()
- **Fix**: Ensure MainWindow implements all required methods of MainWindowProtocol

#### 1.3 transformation_integration.py
- **Issue**: Line 71 - Duplicate definition of UnifiedTransformationService
- **Fix**: Remove duplicate import or rename to avoid conflict

#### 1.4 test_centering_zoom.py
- **Issues**: Multiple type errors (lines 106, 110, 283, 415, 428, 441)
- **Fix**: Review and correct variable types and class definitions

### Task 2: Complete Transformation System Migration

#### 2.1 Identify Legacy Code
- Search for all references to old transformation system
- Document which files still use legacy methods
- Create migration checklist

#### 2.2 Update Core Services
- Modify services to use UnifiedTransformationService exclusively
- Remove TransformationIntegration compatibility layer
- Update all transform_point calls

#### 2.3 Validate Migration
- Run existing tests
- Create migration validation script
- Test smoothing operations thoroughly

### Task 3: Test Coverage Improvement

#### 3.1 Setup Coverage Tools
- Verify pytest-cov installation from requirements-dev.txt
- Create pytest.ini with coverage configuration
- Add coverage report generation to test runner

#### 3.2 Analyze Current Coverage
- Run: `pytest --cov=. --cov-report=html`
- Identify modules with low coverage
- Prioritize critical paths

#### 3.3 Write Missing Tests
- Focus on services with < 80% coverage
- Add edge case tests for transformation system
- Test error handling paths

## Implementation Schedule

### Week 1 (Immediate)
- [ ] Fix all type checking errors
- [ ] Create pre-commit configuration
- [ ] Run initial test coverage analysis

### Week 2
- [ ] Complete transformation system migration
- [ ] Remove legacy transformation code
- [ ] Update documentation

### Week 3
- [ ] Improve test coverage to 80%
- [ ] Set up CI/CD pipeline
- [ ] Performance benchmarking

## Success Metrics

1. **Type Safety**: 0 mypy errors
2. **Test Coverage**: ≥ 80% line coverage
3. **Performance**: No regression in transformation operations
4. **Code Quality**: All pre-commit checks passing
5. **Documentation**: 100% public API documented

## Risk Mitigation

1. **Transformation Migration**: Keep backup of current system until fully validated
2. **Type Changes**: Run full test suite after each type fix
3. **Performance**: Benchmark before and after changes
4. **Compatibility**: Test with existing curve files

## Notes

- The codebase is already in excellent shape (9.2/10)
- Most architectural refactoring is complete
- Focus is on polish and developer experience improvements
- Transformation system migration is the most complex remaining task
