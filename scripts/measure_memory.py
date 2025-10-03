"""
Quick memory measurement script for Week 10 validation.

Measures memory usage of ApplicationState with typical 3-curve, 10K-point dataset.
"""

import sys
import tracemalloc
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from stores.application_state import get_application_state, reset_application_state


def measure_application_state_memory():
    """Measure memory usage with ApplicationState (NEW system)."""
    tracemalloc.start()

    # Reset to clean state
    reset_application_state()
    state = get_application_state()

    # Load typical dataset: 3 curves with 10,000 points each
    for i in range(3):
        curve_name = f"curve_{i}"
        data = [(j, float(j), float(j * 2), "normal") for j in range(10000)]
        state.set_curve_data(curve_name, data)

    # Take measurement
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return current, peak


def main():
    """Run memory measurements."""
    print("=" * 60)
    print("ApplicationState Memory Measurement (Week 10)")
    print("=" * 60)
    print()
    print("Test Dataset: 3 curves × 10,000 points = 30,000 total points")
    print()

    # Measure ApplicationState
    current, peak = measure_application_state_memory()

    print("ApplicationState Memory Usage:")
    print(f"  Current: {current / 1024 / 1024:.2f} MB")
    print(f"  Peak:    {peak / 1024 / 1024:.2f} MB")
    print()

    # Compare to old system targets
    print("Comparison to Pre-Migration Estimates:")
    print("  Old System (CurveDataStore + duplicates): ~28 MB")
    print("  Target (ApplicationState only): <15 MB")
    print(f"  Actual ApplicationState: {peak / 1024 / 1024:.2f} MB")

    if peak < 15 * 1024 * 1024:
        print(f"  ✅ PASSED: Memory under target ({(1 - peak / (28 * 1024 * 1024)) * 100:.1f}% reduction)")
    else:
        print("  ⚠️  WARNING: Memory over target")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
