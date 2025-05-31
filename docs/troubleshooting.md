# CurveEditor Troubleshooting Guide

This guide addresses common issues that may arise when using CurveEditor and provides solutions.

## Application Issues

### Application Won't Start

**Problem**: The application fails to launch with Python import errors.

**Solutions**:
1. Verify you have all dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```
2. Check you're using Python 3.8+:
   ```bash
   python --version
   ```
3. On Windows, ensure you're running with the correct Python environment

### Performance Problems

**Problem**: The application becomes slow with large curve datasets.

**Solutions**:
1. Enable performance mode: View → Performance Mode
2. Reduce visualization complexity: View → Simple Display
3. Use batch transformations instead of individual operations

## Curve Editing Issues

### Points Drift During Operations

**Problem**: Points move unexpectedly during transformation operations.

**Solution**: 
- Use the stable transformation context manager in code:
  ```python
  from services import stable_transform_context
  
  with stable_transform_context(curve_view):
      # Your operations here
  ```

### Incorrect Curve Rendering

**Problem**: Curves display incorrectly or with artifacts.

**Solutions**:
1. Reset view: View → Reset View
2. Toggle rendering mode: View → Toggle Render Mode
3. Restart the application if issues persist

## File Operations

### Import Errors

**Problem**: Unable to import specific file formats.

**Solutions**:
1. Check file format compatibility
2. Use supported formats: TXT, CSV
3. Try the data conversion utility: File → Import → Convert Format

### Export Issues

**Problem**: Export fails or produces incorrect data.

**Solutions**:
1. Check file permissions in the target directory
2. Try exporting to a different location
3. Use File → Export Debug to generate a diagnostic report

## Development Issues

### Type Checking Errors

**Problem**: Mypy reports type errors during development.

**Solutions**:
1. Run the type error fix script:
   ```bash
   python fix_type_errors.py
   ```
2. Add appropriate type annotations as suggested
3. Use protocol-based interfaces for service classes

### Transformation System Migration

**Problem**: Issues with transformation system compatibility.

**Solution**:
- Ensure you're using the unified transformation system:
  ```python
  from services import get_transform, transform_points
  
  # Get a cached transform for the current view
  transform = get_transform(curve_view)
  
  # Transform multiple points efficiently
  qt_points = transform_points(curve_view, points)
  ```

## Getting More Help

If you encounter issues not covered in this guide:

1. Check the API reference documentation
2. Review the detailed transformation system documentation
3. Examine the console output for error messages
4. For development questions, refer to the architecture and design documents

---

*Last Updated: May 30, 2025*
