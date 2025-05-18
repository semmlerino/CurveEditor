# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd CurveEditor

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### 2. Basic Operations

#### Loading and Saving Files

```bash
# Start the application
python main.py

# Load curve data: File → Open
# Save changes: File → Save
# Export to CSV: File → Export CSV
```

#### Editing Curves

- **Select Points**: Click to select individual points, drag to select multiple
- **Move Points**: Drag selected points to new positions
- **Add Points**: Double-click on the curve line
- **Delete Points**: Select points and press Delete key

#### Navigation

- **Zoom**: Mouse wheel or + / - keys
- **Pan**: Middle-click drag or arrow keys
- **Center**: Double-click to center on a point
- **Reset View**: Spacebar to reset zoom and position

### 3. Using the New Transformation System

If you're developing or extending the CurveEditor, use the unified transformation system:

```python
# Import the integration layer
from services import get_transform, transform_points, install_unified_system

# Install in your curve view (one time setup)
install_unified_system(curve_view)

# Transform points efficiently
transform = get_transform(curve_view)
qt_points = transform_points(curve_view, points)
```

### 4. Example: Custom Paint Method

Replace inefficient transformations with the new system:

```python
# OLD (slow)
def paintEvent(self, event):
    painter = QPainter(self)
    for point in self.points:
        tx, ty = CurveService.transform_point(self, point[1], point[2])
        painter.drawEllipse(tx, ty, 3, 3)

# NEW (fast)
def paintEvent(self, event):
    painter = QPainter(self)
    if self.points:
        qt_points = transform_points(self, self.points)
        for qt_point in qt_points:
            painter.drawEllipse(qt_point, 3, 3)
```

### 5. Stable Operations

When modifying curve data programmatically:

```python
from services import stable_transform_operation

def apply_smoothing(curve_view):
    with stable_transform_operation(curve_view):
        # Your modification logic here
        curve_view.curve_data = smooth_curve_data(curve_view.curve_data)
        # Transformations automatically remain stable
```

## Performance Tips

- **Use batch transformations** for multiple points
- **Wrap data modifications** with stable contexts
- **Monitor cache performance** with debug logging
- **Avoid creating custom transformation logic**

## Next Steps

- **[Full API Reference](api-reference.md)**: Complete documentation of all services
- **[Transformation System](transformation-system.md)**: Deep dive into the coordinate system
- **[Architecture Guide](architecture.md)**: Understanding the codebase structure

## Troubleshooting

### Points drift during operations
Use the stable transformation context for any code that modifies curve data.

### Poor performance
Check if you're using individual point transformations instead of batch operations.

### Application won't start
Verify all dependencies are installed: `pip install -r requirements.txt`

Need more help? Check the full documentation in the `docs/` directory or create an issue in the repository.
