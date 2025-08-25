#!/usr/bin/env python
"""
Sprint 11.5 - Verify InteractionService.add_to_history() signature fix.
Tests that both calling patterns work correctly.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Qt to offscreen mode for testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from services import get_interaction_service  # noqa: E402


class MockMainWindow:
    """Mock main window for legacy signature testing."""

    def __init__(self):
        self.curve_widget = MockCurveWidget()
        self.curve_view = MockCurveWidget()  # Support both attribute names


class MockCurveWidget:
    """Mock curve widget."""

    def __init__(self):
        self.curve_data = [(1, 100, 100), (2, 200, 200)]
        self.points = self.curve_data  # Alternative attribute name


def test_legacy_signature():
    """Test legacy add_to_history(main_window) signature."""
    print("\n=== Testing Legacy Signature ===")

    service = get_interaction_service()
    mock_window = MockMainWindow()

    try:
        # Should work with just main_window parameter
        service.add_to_history(mock_window)
        print("✅ Legacy signature works: add_to_history(main_window)")
        return True
    except Exception as e:
        print(f"❌ Legacy signature failed: {e}")
        return False


def test_new_signature():
    """Test new add_to_history(view, state) signature."""
    print("\n=== Testing New Signature ===")

    service = get_interaction_service()
    mock_view = MockCurveWidget()

    state = {"points": [(1, 150, 150), (2, 250, 250)], "selection": {0}}

    try:
        # Should work with view and state parameters
        service.add_to_history(mock_view, state)
        print("✅ New signature works: add_to_history(view, state)")
        return True
    except Exception as e:
        print(f"❌ New signature failed: {e}")
        return False


def test_history_stats():
    """Test that history stats work after adding states."""
    print("\n=== Testing History Stats ===")

    service = get_interaction_service()

    # Add some states using both signatures
    mock_window = MockMainWindow()
    service.add_to_history(mock_window)

    mock_view = MockCurveWidget()
    state = {"points": [(3, 300, 300)], "selection": set()}
    service.add_to_history(mock_view, state)

    # Get stats
    stats = service.get_history_stats()

    if stats:
        print("✅ History stats available:")
        print(f"  Total states: {stats.get('total_states', 0)}")
        print(f"  Current index: {stats.get('current_index', 0)}")
        print(f"  Can undo: {stats.get('can_undo', False)}")
        print(f"  Can redo: {stats.get('can_redo', False)}")
        return True
    else:
        print("❌ History stats not available")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SPRINT 11.5 - HISTORY API SIGNATURE FIX VERIFICATION")
    print("=" * 60)

    results = []

    # Test both signatures
    results.append(test_legacy_signature())
    results.append(test_new_signature())
    results.append(test_history_stats())

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")

    if passed == total:
        print("\n✅ SUCCESS: InteractionService.add_to_history() signature fix complete!")
        print("Both legacy and new calling patterns are working correctly.")
    else:
        print("\n❌ FAILURE: Some signature patterns are not working.")
        print("Please review the implementation.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
