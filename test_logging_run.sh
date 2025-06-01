#!/bin/bash

cd /mnt/c/CustomScripts/Python/Work/Linux/CurveEditor
python3 verify_logging_fixes.py > logging_test_output.txt 2>&1

# Check the output
echo "Test output:"
cat logging_test_output.txt
