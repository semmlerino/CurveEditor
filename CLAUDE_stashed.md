# CurveEditor Development Guide

Quick reference for the CurveEditor codebase - a single-user desktop application for editing animation curves with PySide6.

## Quick Start

```bash
source venv/bin/activate     # ALWAYS activate venv first
./bpr                        # Type check all (MUST use wrapper, NOT basedpyright directly)
./bpr ui/main_window.py     # Type check specific file
ruff check . --fix          # Lint and auto-fix
python -m pytest tests/     # Run tests
```

## Architecture
**TO BE COMPLETED**

```python
from services import get_data_service, get_transform_service, get_interaction_service, get_ui_service
```

Note: Controllers intentionally access some protected MainWindow methods as "friend classes".

## Critical Development Rules

### 1. Type Safety First
```python
# BAD - hasattr() destroys type information
if hasattr(self, 'main_window') and self.main_window:
    frame = self.main_window.current_frame  # Type lost!

# GOOD - Type preserved
if self.main_window is not None:
    frame = self.main_window.current_frame  # Type safe!
```

### 2. Use ./bpr Wrapper for Type Checking
```bash
./bpr                     # CORRECT - handles shell redirection properly
basedpyright . 2>&1      # WRONG - interprets "2" as filename due to bug
```

### 3. Service Access Pattern
Always use service getters, never instantiate directly:
```python
service = get_data_service()  # Singleton pattern
```

## Core Patterns

### Data Models
*TO BE COMPLETED

### Coordinate System
**TO BE COMPLETED**


### Validation Strategy
```python
from core.validation_strategy import get_validation_strategy

strategy = get_validation_strategy("adaptive")  # Production default
strategy.set_context(is_render_loop=True)       # Adjusts validation level
```

## Testing & Linting

### Commands
```bash
# Syntax check first
python3 -m py_compile file.py

# Type checking (MUST use wrapper)
./bpr                        # All files
./bpr | tail -10            # Summary only

# Linting
ruff check . --fix          # Auto-fix issues

# Testing
python -m pytest tests/ -x   # Stop on first failure
```

### Configuration Notes
- `basedpyright`: Configured to ignore Qt widget initialization patterns
- `ruff`: All checks should pass after recent fixes
- Protected member warnings in controllers are intentional (Strangler Fig)

## Known Issues & Gotchas



## Development Tips

1. Always activate venv before any operations
2. Use `./bpr` wrapper, never `basedpyright` directly
3. Check syntax with `python3 -m py_compile` before running
4. Prefer `is not None` checks over `hasattr()` for type safety
5. Respect the 4-service architecture

## References

For detailed technical information, see:
- `LINTING_TYPECHECKING_AGENTREPORT.md` - Recent code quality improvements
- `PROTECTED_MEMBER_REFACTORING.md` - Controller extraction details
- `docs/` directory - Architecture and migration guides

---

*Python 3.12, PySide6==6.4.0*
