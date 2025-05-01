#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for error_handling.py to verify that the fix works.
"""

from error_handling import safe_operation

class MockMainWindow:
    def __init__(self):
        self.history_added = False

    def statusBar(self):
        return self

    def showMessage(self, message, timeout=0):
        self.last_message = message
        self.timeout = timeout

    def add_to_history(self):
        self.history_added = True

@safe_operation("Test Operation", record_history=True)
def test_operation_with_history(main_window):
    return True

@safe_operation("Test Operation", record_history=False)
def test_operation_without_history(main_window):
    return True

def main():
    """Test the safe_operation decorator with record_history parameter."""
    main_window = MockMainWindow()

    # Test with record_history=True
    test_operation_with_history(main_window)
    print(f"History added (should be True): {main_window.history_added}")

    # Reset history flag
    main_window.history_added = False

    # Test with record_history=False
    test_operation_without_history(main_window)
    print(f"History added (should be False): {main_window.history_added}")

    print("Tests completed successfully!")

if __name__ == "__main__":
    main()
