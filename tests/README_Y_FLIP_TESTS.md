# Y-Flip Coordinate Transform Tests

## Overview
Tests for the Y-axis coordinate flipping functionality that converts 3DEqualizer's bottom-origin coordinates (Y=0 at bottom) to Qt's top-origin coordinate system (Y=0 at top).

## Test Coverage

### Unit Tests
- **DataService Y-flip**: Tests that `load_tracked_data()` and `_load_2dtrack_data()` correctly apply Y-flip (720 - y)
- **FileLoadWorker Y-flip**: Tests that `_load_2dtrack_data_direct()` respects the `flip_y` parameter
- **Transform calculations**: Tests that flipped coordinates display correctly through the transform pipeline

### Integration Tests
- **Full pipeline**: Tests from file loading through display
- **Multi-point tracking**: Verifies all tracking points are flipped
- **Edge cases**: Handles empty files, malformed data, negative values

## Key Test Cases

### Actual 3DEqualizer Data
- Point 01 at Y=211.3 (3DEqualizer) → Y=508.7 (Qt)
- Verifies alignment with meat patty in lower burger portion

### Parameterized Tests
- Top edge (0) → Bottom edge (720)
- Middle (360) → Middle (360)
- Bottom edge (720) → Top edge (0)

## Running the Tests

```bash
# Run Y-flip tests only
python -m pytest tests/test_y_flip_coordinate_transform.py -v

# Run with related integration tests
python -m pytest tests/test_y_flip_coordinate_transform.py tests/test_data_pipeline.py -v
```

## Test Results
✅ 18 tests, all passing
- Behavior-focused (not implementation)
- Real components with minimal mocking
- Thread-safe (follows Qt guidelines)
- No type ignores needed
