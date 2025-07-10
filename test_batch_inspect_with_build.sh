#!/bin/bash
# Test WITH FULL BUILD that keeps output files for inspection
# WARNING: This will clone and build Quokka, which takes several minutes

echo "===================================="
echo "Batch Job Hook Test WITH BUILD + Output"
echo "===================================="
echo "WARNING: This will clone and build Quokka!"
echo

cd /home/agray/src/cas/quokka/regression_testing

# Create output directory
mkdir -p test_output_build

# Use venv Python
PYTHON=/home/agray/src/cas/quokka/venv/bin/python

# Set Python path
export PYTHONPATH="/home/agray/src/cas/quokka/mk2025a/python:$PYTHONPATH"

echo "Running hook test with full build..."
$PYTHON test_hook_with_build.py inspect

echo
echo "Files are kept in test_output_build/ for inspection"
echo "To view: ls -la test_output_build/"
echo "To view build output: ls -la test_output_build/performance_test/*/quokka/build/"
echo "To clean up: rm -rf test_output_build/"