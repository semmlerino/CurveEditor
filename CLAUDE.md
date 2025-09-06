# CurveEditor Development Guide for Claude

This document contains important project-specific information for Claude to reference when working on the CurveEditor codebase.

## Project Overview

CurveEditor is a Python/PySide6 application for editing animation curves and tracking data. It uses a consolidated 4-service architecture for better maintainability.

## Architecture

### Dual Architecture Support (Feature Flag)

**CRITICAL DISCOVERY**: The project supports two architectures via environment variable:

```bash
# DEFAULT (consolidated architecture - 4 services)
export USE_LEGACY_SERVICES=false  # or unset

# OPTIONAL (Sprint 8 granular services - 10+ services)
export USE_LEGACY_SERVICES=true
```

⚠️ **Naming Confusion**: Despite the name, `USE_LEGACY_SERVICES=true` actually enables the OLD Sprint 8 services. This is a historical artifact where "new" referred to the Sprint 8 decomposition, which has since been superseded by consolidation.

### Core Services (DEFAULT - Consolidated)
When `USE_LEGACY_SERVICES=false` (default):
1. **TransformService** - Coordinate transformations and view state management
2. **DataService** - Data operations, analysis, file I/O, and image management
3. **InteractionService** - User interactions, point manipulation, and history
4. **UIService** - UI operations, dialogs, status updates, and component management

### Legacy Services (OPTIONAL - Sprint 8)
When `USE_LEGACY_SERVICES=true`:
- SelectionService
- PointManipulationService
- HistoryService
- EventHandlerService
- FileIOService
- ImageSequenceService
- (and others)

### Key Patterns
- Service singleton pattern with module-level instances
- Component Container Pattern in `ui/ui_components.py` (organizes 85+ UI attributes)
- Protocol-based interfaces for type safety
- Immutable Transform class for coordinate transformations

## Development Environment

### Virtual Environment
- Location: `./venv`
- Python version: 3.12
- Main dependency: PySide6==6.4.0

### Linting Tools

#### Ruff
- Configuration: `pyproject.toml`
- Run: `source venv/bin/activate && ruff check .`
- Auto-fix: `ruff check . --fix`
- Status: Ongoing style and formatting issues

#### Basedpyright (Type Checking)
- Configuration: `basedpyrightconfig.json`
- Version: 1.31.1

**⚠️ IMPORTANT: Basedpyright Shell Redirection Bug**

Basedpyright has a bug where it interprets the shell's file descriptor "2" from `2>&1` as a filename, causing:
```
File or directory "file:///mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/2" does not exist
```

**Solution: Use the `./bpr` wrapper script**
```bash
# ✅ WORKS - Use the wrapper
./bpr                          # Interactive with colors
./bpr | tail -5               # Piped output
./bpr 2>&1 | head            # With stderr redirection
./bpr ui/main_window.py      # Check specific files

# ❌ BROKEN - Don't use these
basedpyright . 2>&1          # Fails with "2" file error
basedpyright . | head        # Also fails
```

The `bpr` wrapper uses the `script` command to capture output without shell redirection, bypassing the bug entirely.

**Current Type Check Status:**
- Ongoing type errors requiring systematic resolution
- Many warnings from missing PySide6 type stubs (expected without stubs)
- Use `./bpr` to check current status

## Testing

### Run Tests
```bash
source venv/bin/activate
python -m pytest tests/
```

### Key Test Files

#### DEFAULT Architecture Tests (Priority)
- `tests/conftest.py` - Test fixtures and mocks
- `tests/test_curve_service.py` - Core service tests
- `tests/test_view_state.py` - Transformation tests
- `tests/test_data_pipeline.py` - Data service tests
- `tests/test_transform_service.py` - Transform service tests

#### LEGACY Sprint 8 Architecture Tests (Optional)
- `tests/test_sprint8_services_basic.py` - Sprint 8 services
- `tests/test_sprint8_history_service.py` - Legacy history service
- `tests/test_threading_safety.py` - Tests both architectures

## Common Tasks

### Run Linting
```bash
source venv/bin/activate
ruff check . --fix           # Auto-fix style issues
./bpr                        # Type checking
```

### Check Specific Files
```bash
./bpr ui/main_window.py services/data_service.py
ruff check ui/main_window.py
```

### Test Import Issues
```bash
python3 -m py_compile <file.py>  # Check syntax
python3 -c "from services import get_data_service"  # Test imports
```

## Known Issues

1. **PySide6 Type Stubs**: Not installed, causing many "unknown type" warnings in basedpyright
2. **Test Coverage**: Some service consolidation changes need updated tests
3. **Legacy Code**: Some files in `archive_obsolete/` should be removed after verification

## File Organization

```
CurveEditor/
├── core/           # Core data models and utilities
├── data/           # Data manipulation and curve operations
├── rendering/      # Rendering components
├── services/       # Consolidated service layer
├── ui/            # UI components and main window
├── tests/         # Test suite
├── venv/          # Virtual environment
├── main.py        # Application entry point
├── bpr            # Basedpyright wrapper (use this!)
└── CLAUDE.md      # This file
```

## Important Files

- `ui/main_window.py` - Main application window
- `services/__init__.py` - Service exports and initialization
- `data/curve_view.py` - Core curve visualization widget
- `basedpyrightconfig.json` - Type checker configuration
- `pyproject.toml` - Project and tool configuration

## Recent Major Changes (Aug 2025)

1. **Service Consolidation**: Reduced from ~15 services to 4 core services
2. **Fixed Critical Bugs**:
   - Missing `get_history_service` export
   - Wrong attribute references in `ui_components.py`
   - Missing methods in MainWindow (`set_centering_enabled`, `apply_smooth_operation`)
   - Incomplete implementations in `batch_edit.py`
3. **Basedpyright Configuration**: Fixed Python builtins recognition and created `bpr` wrapper
4. **Documentation Updates (Aug 12, 2025)**:
   - Discovered and documented dual architecture feature flag
   - Clarified DEFAULT vs LEGACY service architectures
   - Categorized tests by architecture type
   - Fixed misleading "USE_LEGACY_SERVICES" naming confusion

## Architectural Integration Methodology

### Overview

This section documents lessons learned from UI Components integration issues encountered in September 2025. The problems arose from mapping MainWindow widgets to UIComponents container attributes without proper validation, resulting in silent failures and type mismatches.

### Problem Categories

#### 1. **Silent Attribute Creation**
Python's dynamic nature allows assigning to non-existent attributes without errors:
```python
# This creates new attributes instead of failing
self.ui.timeline.frame_spinbox = widget  # ❌ frame_spinbox didn't exist
self.ui.visualization.point_size_slider = widget  # ❌ point_size_slider didn't exist
```

#### 2. **Type Mismatches**
Assigning widgets to incorrectly-typed container attributes:
```python
# UIComponents expected QLineEdit, MainWindow used QDoubleSpinBox
self.ui.point_edit.x_edit = self.point_x_spinbox  # ❌ Type mismatch
```

#### 3. **Incomplete Structure Analysis**
Assuming UIComponents structure matched MainWindow widgets without verification.

### Prevention Strategies

#### 1. **Structure-First Analysis**
Always analyze target structure before integration:
```bash
# Compare actual widget attributes
python3 -c "
from ui.ui_components import TimelineUIComponents
timeline = TimelineUIComponents()
attrs = [attr for attr in dir(timeline) if not attr.startswith('_')]
print('Available timeline attributes:', sorted(attrs))
"
```

#### 2. **Pre-Implementation Validation**
Create validation scripts before mapping:
```python
def validate_component_structure():
    from ui.ui_components import UIComponents
    from ui.main_window import MainWindow

    # Get expected structure
    ui = UIComponents(None)
    expected_timeline = dir(ui.timeline)

    # Compare with intended mappings
    intended_mappings = ['frame_spinbox', 'fps_spinbox']
    missing = [attr for attr in intended_mappings if attr not in expected_timeline]

    if missing:
        raise ValueError(f"Missing attributes in timeline: {missing}")
```

#### 3. **Type-Aware Mapping**
Verify widget types match container expectations:
```python
# Check types before mapping
assert isinstance(self.point_x_spinbox, QDoubleSpinBox)
# Verify container expects same type
from inspect import signature
expected_type = signature(UIComponents.point_edit.x_edit.fget).return_annotation
```

### Detection Methods

#### 1. **Runtime Assertions During Development**
Add temporary assertions after mappings:
```python
# In MainWindow.__init__ during development
assert hasattr(self.ui.timeline, 'frame_spinbox'), "Timeline mapping failed"
assert self.ui.timeline.frame_spinbox is not None, "Mapping not assigned"
```

#### 2. **Type Checking Integration**
Use basedpyright to catch type mismatches:
```bash
# This would catch type issues
./bpr ui/main_window.py ui/ui_components.py
```

#### 3. **Comprehensive Validation Testing**
Create specific tests for component mappings:
```python
def test_ui_component_mappings():
    window = MainWindow()

    # Test all expected mappings exist and have correct types
    assert hasattr(window.ui.timeline, 'frame_spinbox')
    assert isinstance(window.ui.point_edit.x_edit, QDoubleSpinBox)

    # Test no silent attribute creation
    mapping_count_before = len(dir(window.ui.timeline))
    window.ui.timeline.nonexistent_attr = "test"
    mapping_count_after = len(dir(window.ui.timeline))
    assert mapping_count_after > mapping_count_before  # Would catch dynamic creation
```

### Validation Approaches

#### 1. **Use Built-in Validation**
UIComponents has validation methods - use them:
```python
# After integration
missing = window.ui.validate_completeness()
if missing:
    raise ValueError(f"Missing critical components: {missing}")
```

#### 2. **Cross-Reference Validation**
Compare intended structure with actual structure:
```bash
# Validation command
python3 -c "
from ui.ui_components import UIComponents
from ui.main_window import MainWindow

# Create instances
ui = UIComponents(None)
window = MainWindow()

# Cross-validate mapping completeness
groups = ui.get_component_groups()
for group_name, group in groups.items():
    group_attrs = [attr for attr in dir(group) if not attr.startswith('_')]
    print(f'{group_name}: {len(group_attrs)} attributes available')
"
```

#### 3. **Integration Testing**
Test that mappings work in realistic scenarios:
```python
def test_component_integration():
    window = MainWindow()

    # Test that components are accessible through intended paths
    frame_widget = window.ui.timeline.frame_spinbox
    assert frame_widget is window.frame_spinbox  # Same instance

    # Test that property access works
    point_editor = window.ui.point_edit.x_edit
    assert hasattr(point_editor, 'setValue')  # Expected QDoubleSpinBox method
```

### Best Practices Checklist

**Before Integration:**
- [ ] Analyze target component structure thoroughly
- [ ] Compare with source widget attributes and types
- [ ] Create validation script for intended mappings
- [ ] Document expected component organization

**During Integration:**
- [ ] Add runtime assertions for critical mappings
- [ ] Use type checking tools (./bpr) continuously
- [ ] Test mappings in isolation before broader integration
- [ ] Verify no silent attribute creation occurs

**After Integration:**
- [ ] Run built-in validation methods
- [ ] Execute comprehensive test suite
- [ ] Validate component access patterns work as intended
- [ ] Document any architectural changes made

### Tools Reference

```bash
# Structure analysis
python3 -c "from ui.ui_components import TimelineUIComponents; print(dir(TimelineUIComponents()))"

# Type checking
./bpr ui/main_window.py ui/ui_components.py

# Integration validation
python3 -c "from ui.main_window import MainWindow; w=MainWindow(); print(w.ui.validate_completeness())"

# Test specific component integration
python -m pytest tests/test_ui_components_real.py -v

# Comprehensive testing
python -m pytest tests/ -x -q
```

### Key Takeaway

**Python's dynamic nature can mask architectural integration failures through silent attribute creation. Always validate structure compatibility before mapping, use type checking tools, and implement comprehensive validation testing.**

## Development Tips

1. **Always use the virtual environment**: `source venv/bin/activate`
2. **Use `./bpr` for type checking**, not `basedpyright` directly
3. **Check imports after refactoring**: Services have been consolidated
4. **Run syntax check first**: `python3 -m py_compile <file>` before running full linting
5. **Component Container Pattern**: Access UI components through `self.ui_components.<group>.<widget>`
6. **Follow architectural integration methodology**: Validate structure compatibility before component mapping

---
*Last Updated: September 6, 2025*
