#!/bin/bash
# Minimal POC test WITH FULL BUILD - focuses on the batch job hook
# WARNING: This will clone and build Quokka, which takes several minutes

echo "====================================="
echo "Minimal Batch Job Hook Test WITH BUILD"
echo "====================================="
echo "WARNING: This will clone and build Quokka!"
echo

cd /home/agray/src/cas/quokka/regression_testing

# Use venv Python
PYTHON=/home/agray/src/cas/quokka/venv/bin/python

# Check for required Python modules
echo "Checking Python dependencies..."
$PYTHON -c "import yaml" 2>/dev/null || echo "Warning: PyYAML not installed (pip install pyyaml)"
$PYTHON -c "import jinja2" 2>/dev/null || echo "Warning: Jinja2 not installed (pip install jinja2)"

# Set Python path
export PYTHONPATH="/home/agray/src/cas/quokka/mk2025a/python:$PYTHONPATH"

echo "Running hook test with full build..."
$PYTHON test_hook_with_build.py minimal

echo
echo "====================================="
echo "Test Complete!"
echo "This test ran the full build process"
echo "====================================="