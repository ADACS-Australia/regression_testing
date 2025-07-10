#!/bin/bash
# Test that keeps output files for inspection

echo "===================================="
echo "Batch Job Hook Test with Output"
echo "===================================="
echo

cd /home/agray/src/cas/quokka/regression_testing

# Create output directory
mkdir -p test_output_demo

# Use venv Python
PYTHON=/home/agray/src/cas/quokka/venv/bin/python

# Set Python path
export PYTHONPATH="/home/agray/src/cas/quokka/mk2025a/python:$PYTHONPATH"

$PYTHON test_hook_inspect.py

echo
echo "Files are kept in test_output_demo/ for inspection"
echo "To view: ls -la test_output_demo/"
echo "To clean up: rm -rf test_output_demo/"