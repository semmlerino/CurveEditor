# CurveEditor Development Guide for Claude

This document contains important project-specific information for Claude to reference when working on the CurveEditor codebase.

## Project Overview

CurveEditor is a Python/PySide6 application for editing animation curves and tracking data. It uses a consolidated 4-service architecture for better maintainability.

## Architecture

### Dual Architecture Support (Feature Flag)

**CRITICAL DISCOVERY**: The project supports two architectures via environment variable:

```bash
# DEFAULT (consolidated architecture - 4 services)
export USE_NEW_SERVICES=false  # or unset

# OPTIONAL (Sprint 8 granular services - 10+ services)  
export USE_NEW_SERVICES=true
```

⚠️ **Naming Confusion**: Despite the name, `USE_NEW_SERVICES=true` actually enables the OLD Sprint 8 services. This is a historical artifact where "new" referred to the Sprint 8 decomposition, which has since been superseded by consolidation.

### Core Services (DEFAULT - Consolidated)
When `USE_NEW_SERVICES=false` (default):
1. **TransformService** - Coordinate transformations and view state management
2. **DataService** - Data operations, analysis, file I/O, and image management  
3. **InteractionService** - User interactions, point manipulation, and history
4. **UIService** - UI operations, dialogs, status updates, and component management

### Legacy Services (OPTIONAL - Sprint 8)
When `USE_NEW_SERVICES=true`:
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
- Current status: 54 issues (mostly cosmetic/style)

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
- 424 errors (legitimate type issues)
- 5,129 warnings (mostly PySide6 unknown types - expected without stubs)
- 0 notes

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
   - Fixed misleading "USE_NEW_SERVICES" naming confusion

## Development Tips

1. **Always use the virtual environment**: `source venv/bin/activate`
2. **Use `./bpr` for type checking**, not `basedpyright` directly
3. **Check imports after refactoring**: Services have been consolidated
4. **Run syntax check first**: `python3 -m py_compile <file>` before running full linting
5. **Component Container Pattern**: Access UI components through `self.ui_components.<group>.<widget>`

---
*Last Updated: August 12, 2025*