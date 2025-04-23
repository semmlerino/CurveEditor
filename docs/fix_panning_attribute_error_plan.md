# Plan: Fix Panning AttributeError in InputService

**Date:** 2025-04-23

## Problem

An `AttributeError` occurs during mouse movement when panning (middle mouse button held down):

```
Traceback (most recent call last):
  File "C:\CustomScripts\Python\Work\Linux\CurveEditor\enhanced_curve_view.py", line 642, in mouseMoveEvent
    InputService.handle_mouse_move(self, event)
  File "C:\CustomScripts\Python\Work\Linux\CurveEditor\services\input_service.py", line 77, in handle_mouse_move
    ZoomOperations.pan_view(view, delta.x(), delta.y())
    ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: module 'centering_zoom_operations' has no attribute 'pan_view'
```

The error happens in `services/input_service.py` at line 77 within the `handle_mouse_move` method.

## Analysis

1.  **Code Review (`services/input_service.py`):**
    *   Line 11 imports `centering_zoom_operations as ZoomOperations`.
    *   Line 77 attempts to call `ZoomOperations.pan_view(view, delta.x(), delta.y())`.
    *   The panning logic is correctly triggered only when `view.pan_active` is true (set by middle mouse button press).

2.  **Code Review (`centering_zoom_operations.py`):**
    *   This module, imported as `ZoomOperations`, **does not** contain a function named `pan_view`. It handles centering, fitting, zooming, and resetting the view.

3.  **Code Review (`services/centering_zoom_service.py`):**
    *   This service acts as a facade for `centering_zoom_operations.py` and also **does not** define or contain a `pan_view` method.

4.  **Conclusion:** The `pan_view` function called in `InputService` does not exist in the module it's being called from. The panning logic was likely intended to be handled directly within `InputService` by modifying the view's offset attributes.

## Proposed Solution

Modify the `handle_mouse_move` method in `services/input_service.py`. Instead of calling the non-existent `ZoomOperations.pan_view`, directly update the view's offset attributes based on the mouse movement `delta` when `view.pan_active` is true.

**Specific Change:**

Replace line 77:
```python
            ZoomOperations.pan_view(view, delta.x(), delta.y())
```
with:
```python
            # Directly update view offsets for panning
            if hasattr(view, 'x_offset') and hasattr(view, 'y_offset'):
                view.x_offset += delta.x()
                view.y_offset += delta.y()
                view.update() # Trigger repaint
            else:
                # Log a warning or handle cases where offsets are missing
                print("Warning: View object missing x_offset or y_offset for panning.")
```
*(Note: Assumes `x_offset` and `y_offset` are the correct attributes in the `view` object for panning.)*

## Diagram

```mermaid
graph TD
    A[Mouse Move Event] --> B(InputService.handle_mouse_move);
    B -- Middle Button Pressed & Pan Active --> C[Calculate Delta];
    C -- Current Code --> D(Call ZoomOperations.pan_view);
    D -- Fails --> E(AttributeError);

    subgraph Proposed Fix
        C -- New Code --> F[Update view.x_offset += delta.x()];
        F --> G[Update view.y_offset += delta.y()];
        G --> H[Call view.update()];
        H --> I[Panning Works];
    end
```

## Next Steps

1.  Implement the proposed code change in `services/input_service.py`.
2.  Test middle-mouse button panning functionality thoroughly.