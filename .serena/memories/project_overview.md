# CurveEditor Project Overview

## Purpose
CurveEditor is a professional Python/PySide6 application for editing animation curves and tracking data. It provides high-performance rendering and intuitive controls for VFX workflows, with compatibility for 3DEqualizer tracking data.

## Key Features
- Animation curve editing with keyframe interpolation
- Multi-point tracking with Insert Track functionality (3DEqualizer-style gap filling)
- Real-time visualization with 47x optimized rendering
- Full undo/redo system using command pattern
- Background image loading for rotoscoping (EXR support via multiple backends)
- Import/Export support for CSV, JSON, and custom formats
- Multi-curve display and editing
- Gap handling with visual distinction (solid vs dashed lines)
- Thread-safe image caching with LRU eviction

## Tech Stack
- **Language**: Python 3.12
- **UI Framework**: PySide6 (Qt for Python)
- **Dependency Management**: uv (run commands with `uv run`)
- **Testing**: pytest (3100+ test cases, 174 test files)
- **Linting**: ruff (120 char line length)
- **Type Checking**: basedpyright via `./bpr` wrapper script
- **Platform**: Linux (WSL2)

## Architecture Highlights
- **4-Service Architecture**: DataService, InteractionService, TransformService, UIService
- **Protocol-Based Typing**: 16 UI protocols, data protocols, service protocols
- **Single Source of Truth**: ApplicationState for all data
- **13+ Specialized Controllers**: Separation of concerns in UI layer
- **Frame Change Coordinator**: Deterministic ordering eliminates race conditions

## Development Environment
- Virtual environment: `.venv/` (managed by uv)
- Python version: 3.12
- Dependencies: Defined in `pyproject.toml`
- Configuration: `basedpyrightconfig.json`, pytest config in `pyproject.toml`
