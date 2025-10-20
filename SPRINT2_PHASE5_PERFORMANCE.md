# Sprint 2 - Phase 5: Test Performance Optimization

## Current State (Baseline)

- **Total tests**: 2,748
- **Estimated runtime**: ~230 seconds (from plan)
- **Test speed**: ~11.9 tests/sec
- **Execution**: Sequential only
- **No pytest markers**: Tests not categorized by speed

## Goals

1. **Add pytest markers** for test categorization
2. **Enable parallel execution** with pytest-xdist
3. **Optimize slow tests** where possible
4. **Target**: <150 seconds total runtime (35% improvement)

## Task 5.1: Add Pytest Markers (1 hour)

###  Step 1: Identify Slow Tests

Run pytest with duration reporting:
```bash
pytest tests/ --durations=20
```

### Step 2: Add Markers to pytest.ini

```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks integration tests
    unit: marks unit tests
    performance: marks performance benchmark tests
    qt: marks tests requiring Qt event loop
```

### Step 3: Mark Slow Tests

Criteria:
- `@pytest.mark.slow`: Tests taking >1 second
- `@pytest.mark.integration`: Tests using multiple real components
- `@pytest.mark.performance`: Benchmark tests
- `@pytest.mark.qt`: Tests requiring Qt widgets/events

## Task 5.2: Enable Parallel Execution (2 hours)

### Step 1: Install pytest-xdist

Already in pyproject.toml dependencies

### Step 2: Test Parallel Safety

Check for:
- Shared state between tests
- File system conflicts
- Qt application instance issues
- Service singleton conflicts

### Step 3: Run Parallel Tests

```bash
pytest tests/ -n auto  # Use all CPU cores
pytest tests/ -n 4     # Use 4 workers
```

### Step 4: Measure Speedup

Compare:
- Sequential: `time pytest tests/`
- Parallel: `time pytest tests/ -n auto`
- Calculate speedup ratio

## Task 5.3: Optimize Slow Test Patterns (1 hour)

### Common Slow Patterns to Fix:

1. **Unnecessary sleeps**: Replace with Qt event processing
2. **Large datasets**: Use smaller representative data
3. **Redundant setup**: Cache expensive fixtures
4. **File I/O**: Use in-memory alternatives

### Example Optimizations:

```python
# BEFORE: Slow
def test_something():
    time.sleep(1)  # Wait for async operation

# AFTER: Fast
def test_something(qtbot):
    qtbot.waitUntil(lambda: condition_met(), timeout=1000)
```

```python
# BEFORE: Slow
@pytest.fixture
def large_dataset():
    return [generate_point() for _ in range(10000)]

# AFTER: Fast
@pytest.fixture
def large_dataset():
    return [generate_point() for _ in range(100)]  # Representative sample
```

## Progress Log

### 2025-10-20: Phase 5 Started

#### Baseline Measurement
- Need to run `pytest --durations=20` to identify slow tests
- Need to measure current total runtime
- Already have pytest-xdist installed

### Next Steps
1. Run duration analysis
2. Update pytest.ini with markers
3. Mark slow tests
4. Test parallel execution
5. Measure improvements
