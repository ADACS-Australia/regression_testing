#!/bin/bash
# HPC environment setup script for Quokka builds
# This script loads necessary modules and sets up the build environment

# Load required modules
# First load Python with gcc/11.3.0
module load gcc/11.3.0
module load python/3.10.4-bare

# Then switch to gcc/12.3.0 for the build
module load gcc/12.3.0
module load openmpi/4.1.5
module load cmake/3.26.3
module load ninja/1.11.1
module load hdf5/1.14.0
module load cuda/12.4.1

# Ensure Python library path is preserved
export LD_LIBRARY_PATH=/apps/modules/software/Python/3.10.4-GCCcore-11.3.0-bare/lib:$LD_LIBRARY_PATH

# Activate Python virtual environment if it exists
if [ -f "/home/agray/src/cas/quokka/venv/bin/activate" ]; then
    source /home/agray/src/cas/quokka/venv/bin/activate
fi

# Set any additional environment variables
export CC=gcc
export CXX=g++
export CUDACXX=nvcc

# Print loaded modules for debugging
echo "Loaded modules:"
module list 2>&1

echo "Environment setup complete"