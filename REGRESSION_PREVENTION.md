# Regression Prevention Guide

This guide documents strategies to prevent regressions like those encountered on Oct 26, 2025.

## Issues Encountered

### 1. File Format Regression (2DTrackDatav2.txt)
- **What**: Example file changed from text → JSON format
- **Impact**: File loading failed silently
- **Why Missed**: No integration test loading actual example files

### 2. Theme Not Applied (_theme_initialized)
- **What**: Class variable pre-declaration broke `hasattr()` logic
- **Impact**: Entire UI displayed in light theme instead of dark
- **Why Missed**: No smoke test validating theme application

## Prevention Strategies

### 1. Integration Tests for Critical Files ✅

**Location**: `tests/test_example_files_integration.py`

**What it does**:
- Loads actual example files from repository (2DTrackDatav2.txt, etc.)
- Validates file format (text vs JSON)
- Verifies multi-point data structure
- Ensures canonical examples remain loadable

**When to run**:
- Before every commit (via pre-commit hook)
- After any changes to example files
- Before releases

**Coverage**:
- 5 tests covering example file loading
- Format validation (text vs JSON detection)
- Structure validation (multi-point format)

### 2. Smoke Tests for UI Initialization ✅

**Location**: `tests/test_theme_smoke.py`

**What it does**:
- Validates dark theme stylesheet generation
- Verifies stylesheet applied to QApplication
- Checks theme initialization flag state
- Prevents pre-declaration bugs

**When to run**:
- Before every commit
- After UI/theme changes
- Before releases

**Coverage**:
- 5 tests covering theme application
- Prevents `_theme_initialized` pre-declaration bug
- Validates stylesheet >1000 chars
- Ensures theme not reapplied unnecessarily

### 3. Pre-Commit Validation

**Already configured** in `.pre-commit-config.yaml`:
```yaml
# Runs automatically before each commit:
- ruff check (linting)
- basedpyright (type checking)
- Custom hooks can be added
```

**Recommended additions**:
```bash
# Run critical smoke tests before commit
~/.local/bin/uv run pytest tests/test_example_files_integration.py tests/test_theme_smoke.py -q
```

### 4. Test Coverage Monitoring

**Current**: 3042 tests passing

**Gaps identified and filled**:
- ✅ Integration tests for example files (new)
- ✅ Smoke tests for theme application (new)
- ⚠️ Visual regression tests (future enhancement)

### 5. Example File Protection

**Best practices**:
1. **Never commit example files in wrong format**
   - `test_example_files_not_json` catches this

2. **Document example file purposes**
   - 2DTrackDatav2.txt: Canonical multi-point format
   - 2DTrackData_Point1_only.txt: Single-point example

3. **Validate before committing**
   ```bash
   # Quick check
   head -5 2DTrackDatav2.txt
   # Should show: version, Point1, 0, count, data
   # NOT: { or [
   ```

### 6. Code Review Checklist

When reviewing changes, verify:

**File Changes**:
- [ ] Example files maintain correct format (text, not JSON)
- [ ] Integration tests pass: `pytest tests/test_example_files_integration.py`

**UI/Theme Changes**:
- [ ] No class variables pre-declared as `False` that break `hasattr()` checks
- [ ] Theme smoke tests pass: `pytest tests/test_theme_smoke.py`
- [ ] Stylesheet application logic not modified without tests

**General**:
- [ ] All tests pass: `pytest tests/ -x`
- [ ] Type checking clean: `./bpr --errors-only`
- [ ] Linting clean: `ruff check .`

## Quick Commands

### Run All Prevention Tests
```bash
# Both integration and smoke tests
~/.local/bin/uv run pytest tests/test_example_files_integration.py tests/test_theme_smoke.py -v

# Expected: 10 tests passing in ~6 seconds
```

### Validate Example Files
```bash
# Check file format
head -10 2DTrackDatav2.txt

# Load test
~/.local/bin/uv run python3 -c "
from services.data_service import DataService
ds = DataService()
data = ds.load_tracked_data('2DTrackDatav2.txt')
print(f'Loaded {len(data)} points: {list(data.keys())[:3]}...')
"
```

### Validate Theme Application
```bash
# Quick theme check
~/.local/bin/uv run python3 -c "
from ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
window = MainWindow()
print(f'Theme applied: {MainWindow._theme_initialized}')
print(f'Stylesheet length: {len(app.styleSheet())} chars')
"
```

## Lessons Learned

### Issue #1: File Format Change
**Root cause**: Lack of integration tests for actual files
**Solution**: Test real files, not just programmatic data
**Takeaway**: Integration tests catch real-world usage issues

### Issue #2: Theme Pre-Declaration
**Root cause**: Type annotation as class variable broke runtime check
**Solution**: Document why variables shouldn't be pre-declared
**Takeaway**: Smoke tests catch initialization bugs

### General Principles
1. **Test the real thing**: Use actual example files, not mocks
2. **Test initialization**: Don't assume UI setup "just works"
3. **Add tests for bugs**: Each bug becomes a regression test
4. **Document anti-patterns**: Explain why certain code patterns fail

## Future Enhancements

### Visual Regression Testing
- Screenshot comparison for theme validation
- Detect unintended UI color/layout changes
- Tool: pytest-qt + image comparison

### Continuous Integration
- Run prevention tests on every push
- Block PRs if smoke tests fail
- Automated nightly full test runs

### Example File Versioning
- Track changes to example files explicitly
- Require explicit approval for format changes
- Version example files (v1, v2) if format evolves

## Maintenance

**Review this guide**:
- After each regression (add new prevention)
- Quarterly (update test counts, coverage)
- Before major releases (verify all protections active)

**Update test counts**:
- Example file tests: 5 tests
- Theme smoke tests: 5 tests
- Total prevention tests: 10 tests
- Total test suite: 3042+ tests

---

*Last Updated: October 26, 2025*
*After fixing 2DTrackDatav2.txt and _theme_initialized regressions*
