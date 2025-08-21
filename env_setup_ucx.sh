#!/bin/bash
# Auto-generated environment setup script

# Clean up
# module purge

# Load modules

module load gcc/12.3.0

module load gompi/2023a ucx-cuda/1.14.1-cuda-12.1.1
module load cmake/3.26.3

module load ninja/1.11.1

module load hdf5/1.14.0

module load python/3.11.3


# Activate Python venv
source /home/agray/src/cas/quokka/venv/bin/activate  

