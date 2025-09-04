#!/usr/bin/env python3
"""
Module to programmatically set environment variables that would normally
be set by env_setup_ucx.sh. This allows regtest.py to run without
needing to source a bash script.
"""

import os
import sys
import json
from pathlib import Path

def load_environment_from_json(json_file="env_variables.json"):
    """
    Load environment variables from a JSON file.
    
    The JSON file should be created by exporting the environment after
    sourcing env_setup_ucx.sh:
    
    source env_setup_ucx.sh
    python3 -c "import os, json; print(json.dumps(dict(os.environ), indent=2))" > env_variables.json
    """
    if not os.path.exists(json_file):
        return False
    
    with open(json_file, 'r') as f:
        env_vars = json.load(f)
    
    # Set all environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    return True

def setup_minimal_environment():
    """
    Set up minimal environment variables needed for regtest.py to run.
    This is a fallback if the full environment isn't available.
    """
    # Base software directory
    software_base = "/apps/modules/software"
    
    # Key environment variables (simplified)
    minimal_env = {
        # CUDA
        "CUDA_HOME": f"{software_base}/CUDA/12.1.1",
        "CUDA_PATH": f"{software_base}/CUDA/12.1.1",
        "CUDA_ROOT": f"{software_base}/CUDA/12.1.1",
        
        # HDF5
        "HDF5_DIR": f"{software_base}/HDF5/1.14.0-gompi-2023a",
        
        # Python virtual environment
        "VIRTUAL_ENV": "/fred/oz420/agray/src/cas/quokka/venv",
        
        # Add key directories to PATH
        "PATH": ":".join([
            "/fred/oz420/agray/src/cas/quokka/venv/bin",
            f"{software_base}/Python/3.11.3-GCCcore-12.3.0/bin",
            f"{software_base}/OpenMPI/4.1.5-GCC-12.3.0/bin",
            f"{software_base}/CUDA/12.1.1/bin",
            f"{software_base}/CMake/3.26.3-GCCcore-12.3.0/bin",
            f"{software_base}/GCCcore/12.3.0/bin",
            os.environ.get("PATH", "/usr/bin:/bin")
        ]),
        
        # Library paths
        "LD_LIBRARY_PATH": ":".join([
            f"{software_base}/Python/3.11.3-GCCcore-12.3.0/lib",
            f"{software_base}/HDF5/1.14.0-gompi-2023a/lib",
            f"{software_base}/CUDA/12.1.1/lib",
            f"{software_base}/OpenMPI/4.1.5-GCC-12.3.0/lib",
            f"{software_base}/GCCcore/12.3.0/lib64",
            os.environ.get("LD_LIBRARY_PATH", "")
        ])
    }
    
    # Set the environment variables
    for key, value in minimal_env.items():
        os.environ[key] = value
    
    # Activate virtual environment programmatically
    venv_path = "/fred/oz420/agray/src/cas/quokka/venv"
    if os.path.exists(venv_path):
        # Update PATH to prioritize venv
        venv_bin = os.path.join(venv_path, "bin")
        os.environ["PATH"] = f"{venv_bin}:{os.environ['PATH']}"
        
        # Update sys.path for Python
        venv_site_packages = os.path.join(venv_path, "lib", "python3.11", "site-packages")
        if venv_site_packages not in sys.path:
            sys.path.insert(0, venv_site_packages)

def auto_setup_environment():
    """
    Automatically set up the environment by trying different methods:
    1. Load from JSON file if available
    2. Use minimal environment setup as fallback
    """
    # Try to load from JSON first
    json_files = [
        "env_variables.json",
        "../env_variables.json",
        "A/env_variables.json"
    ]
    
    for json_file in json_files:
        if os.path.exists(json_file):
            if load_environment_from_json(json_file):
                print(f"==> Loaded environment from {json_file}")
                return True
    
    # Fall back to minimal setup
    print("==> Using minimal environment setup")
    setup_minimal_environment()
    return True

def export_current_environment(output_file="env_variables.json"):
    """
    Export the current environment to a JSON file.
    Run this after sourcing env_setup_ucx.sh to create the JSON file:
    
    source A/env_setup_ucx.sh
    python3 -c "from load_environment import export_current_environment; export_current_environment()"
    """
    env_dict = dict(os.environ)
    
    with open(output_file, 'w') as f:
        json.dump(env_dict, f, indent=2, sort_keys=True)
    
    print(f"Environment exported to {output_file}")

if __name__ == "__main__":
    # If run directly, export the current environment
    export_current_environment()