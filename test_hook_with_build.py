#!/usr/bin/env python3
"""Test batch job hook with full build execution"""

import os
import sys

# Mock test object
class MockTest:
    def __init__(self):
        self.name = "test_hydro_wave"
        self.executable = "test_hydro2d_wave"
        self.inputFile = "hydro_wave.in"
        self.buildDir = "."
        self.output_dir = "./test_output_build"
        self.numprocs = 1
        self.useBatch = 1
        
# Mock suite object
class MockSuite:
    def __init__(self):
        self.mk2025aPath = "../mk2025a"

# Create test directory
os.makedirs("test_output_build", exist_ok=True)

# We need to temporarily enable build execution in mk2025a
# This is done by importing and patching the regression_adapter
sys.path.insert(0, "../mk2025a/python")
from hpc_performance_testing import regression_adapter

# Save original submit method
original_submit = regression_adapter.RegressionTestConverter.submit_as_batch_job

def submit_with_build(self, test_dict, output_dir):
    """Modified version that runs the actual build"""
    print("\n" + "="*60)
    print("mk2025a REGRESSION ADAPTER: Processing test submission WITH BUILD")
    print("="*60)
    print(f"Test name: {test_dict.get('test_name', 'unknown')}")
    print(f"Output directory: {output_dir}")
    
    # Convert test to mk2025a config
    config = self.convert_test_to_config(test_dict)
    
    # Save config
    from pathlib import Path
    import yaml
    config_path = Path(output_dir) / "mk2025a_generated_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"Generated mk2025a config: {config_path}")
    
    # Create status file
    import json
    status_file_path = Path(output_dir) / "batch_job_status.json"
    status = {
        "job_id": f"poc_{self.timestamp}_{test_dict.get('test_name', 'test')}",
        "status": "READY",
        "message": "Test with build execution",
        "test_name": test_dict.get("test_name", "unknown"),
        "config_file": str(config_path),
        "timestamp": self.timestamp
    }
    
    with open(status_file_path, 'w') as f:
        json.dump(status, f, indent=2)
    print(f"Created status file: {status_file_path}")
    
    # Run actual build
    try:
        print("\n--- RUNNING FULL BUILD ---")
        from hpc_performance_testing.submit import JobCreator
        
        jobs = JobCreator(config)
        print("Generating and executing build script...")
        jobs.generate_build_file()  # This will actually run the build
        
        print("\n--- BUILD EXECUTION COMPLETE ---")
        
    except Exception as e:
        print(f"Build execution error (expected): {e}")
        import traceback
        traceback.print_exc()
        
    return status["job_id"], str(status_file_path)

# Patch the method
regression_adapter.RegressionTestConverter.submit_as_batch_job = submit_with_build

# Now run the test
try:
    from batch_job_hook import BatchJobHook
    
    print("Successfully imported BatchJobHook")
    
    # Create hook instance  
    hook = BatchJobHook("../mk2025a")
    print(f"Created BatchJobHook with mk2025a at: {hook.mk2025a_path}")
    
    # Create mock test
    test = MockTest()
    suite = MockSuite()
    
    # Check if test should run as batch
    if hook.should_run_as_batch(test):
        print("Test correctly identified as batch job")
        
        # Run the batch job hook
        print("\nCalling run_batch_job with BUILD...")
        success = hook.run_batch_job(test, suite)
        
        if success:
            print("\nBatch job hook completed!")
        else:
            print("\nBatch job hook failed")
    else:
        print("Test not identified as batch job")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Restore original method
    regression_adapter.RegressionTestConverter.submit_as_batch_job = original_submit

# Cleanup or keep based on script purpose
import shutil
if "minimal" in sys.argv[0]:
    # Cleanup for minimal version
    if os.path.exists("test_output_build"):
        shutil.rmtree("test_output_build")
else:
    # Keep for inspect version
    print(f"\nOutput kept in test_output_build/ for inspection")