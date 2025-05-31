#!/bin/bash
# Run the coverage analysis script

cd /mnt/c/CustomScripts/Python/Work/Linux/CurveEditor

# Run coverage analysis
python3 coverage_analysis.py

# Store the exit code
exit_code=$?

# Exit with the same code
exit $exit_code
