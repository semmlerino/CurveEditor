# CurveEditor User Guide

## Overview

CurveEditor is a Python application for visualizing and editing 2D curve data with advanced transformation capabilities. This guide covers all features from basic usage to advanced operations.

## Getting Started

### Installation

1. **Prerequisites**:
   - Python 3.8 or higher
   - PySide6 6.4.0 or higher

2. **Setup**:
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd CurveEditor
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run the application
   python main.py
   ```

### Basic Operations

1. **Loading Data**:
   - File → Open to load curve data
   - Supported formats: TXT, CSV

2. **Navigation**:
   - **Zoom**: Mouse wheel
   - **Pan**: Middle-click drag
   - **Reset View**: View → Reset or press Home key

3. **Editing Points**:
   - **Select**: Click on point
   - **Move**: Click and drag selected point
   - **Multi-select**: Ctrl+Click or selection box
   - **Delete**: Select point(s) and press Delete

## Advanced Features

### Unified Transformation System

The application uses a high-performance transformation system for coordinate manipulation:

- **50-80% reduction** in transformation calculations through intelligent caching
- **30-50% faster** rendering with batch transformations
- **Stable memory usage** through cache size management

### Batch Operations

For processing multiple points efficiently:

1. Select multiple points using Ctrl+Click or selection box
2. Right-click → Batch Operations
3. Choose operation type and parameters
4. Apply to selected points

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open File | Ctrl+O |
| Save | Ctrl+S |
| Undo | Ctrl+Z |
| Redo | Ctrl+Y |
| Delete Point | Delete |
| Reset View | Home |
| Pan Mode | Space (hold) |
| Select Mode | S |

## Troubleshooting

See the separate [Troubleshooting Guide](troubleshooting.md) for solutions to common issues.

---

*Last Updated: May 30, 2025*
