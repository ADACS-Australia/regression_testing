#!/bin/bash
# Minimal POC test - focuses only on the batch job hook

echo "===================================="
echo "Minimal Batch Job Hook Test"
echo "===================================="
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

echo "Running direct hook test..."
$PYTHON test_hook_directly.py

echo
echo "===================================="
echo "Test Complete!"
echo "This minimal test shows the hook works"
echo "without needing the full regression framework"
echo "======================================"
