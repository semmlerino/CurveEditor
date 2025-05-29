#!/usr/bin/env python
"""Run mypy to check type errors in the project."""

import subprocess
import sys

def run_mypy():
    """Run mypy and display results."""
    try:
        # Run mypy with configuration
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "--config-file", "mypy.ini", "."],
            capture_output=True,
            text=True,
            cwd="/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor"
        )

        print("=== MyPy Type Checking Results ===\n")
        print(result.stdout)
        if result.stderr:
            print("\nErrors:")
            print(result.stderr)

        return result.returncode
    except Exception as e:
        print(f"Error running mypy: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_mypy()
    sys.exit(exit_code)
