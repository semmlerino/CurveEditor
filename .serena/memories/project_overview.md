# CurveEditor Project Overview

## Purpose
CurveEditor is a professional Python/PySide6 application for editing animation curves and tracking data. It provides high-performance rendering and intuitive controls for VFX workflows, with compatibility for 3DEqualizer tracking data.

## Key Features
- Animation curve editing with keyframe interpolation
- Multi-point tracking with Insert Track functionality (3DEqualizer-style gap filling)
- Real-time visualization with 47x optimized rendering
- Full undo/redo system using command pattern
- Background image loading for rotoscoping
- Import/Export support for CSV, JSON, and custom formats
- Multi-curve display and editing

## Tech Stack
- **Language**: Python 3.12
- **UI Framework**: PySide6 (Qt for Python)
- **Dependency Management**: uv (run commands with `uv run`)
- **Testing**: pytest (1945+ test cases, 106 test files)
- **Linting**: ruff (120 char line length)
- **Type Checking**: basedpyright via `./bpr` wrapper script
- **Platform**: Linux (WSL2)

## Development Environment
- Virtual environment: `.venv/` (managed by uv)
- Python version: 3.12
- Dependencies: Defined in `pyproject.toml`
- Configuration: `basedpyrightconfig.json`, `pytest.ini` in pyproject.toml
