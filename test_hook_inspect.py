#!/usr/bin/env python3
"""Direct test of batch job hook - keeps output for inspection"""

import os
import sys

# Mock test object
class MockTest:
    def __init__(self):
        self.name = "test_hydro_wave"
        self.executable = "test_hydro2d_wave"
        self.inputFile = "hydro_wave.in"
        self.buildDir = "."
        self.output_dir = "./test_output_demo"
        self.numprocs = 1
        self.useBatch = 1
        
# Mock suite object
class MockSuite:
    def __init__(self):
        self.mk2025aPath = "../mk2025a"

# Create test directory
os.makedirs("test_output_demo", exist_ok=True)

# Import and test the hook
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
        print("\nCalling run_batch_job...")
        success = hook.run_batch_job(test, suite)
        
        if success:
            print("\nBatch job hook completed successfully!")
        else:
            print("\nBatch job hook failed")
    else:
        print("Test not identified as batch job")
        
    # Check for generated files
    print("\nChecking generated files:")
    for f in ["batch_config.json", "mk2025a_generated_config.yaml", "batch_job_status.json"]:
        path = os.path.join(test.output_dir, f)
        if os.path.exists(path):
            print(f"  - {f} created")
            
    # Show the mk2025a config
    config_path = os.path.join(test.output_dir, "mk2025a_generated_config.yaml")
    if os.path.exists(config_path):
        print("\nGenerated mk2025a configuration:")
        print("-" * 40)
        with open(config_path, "r") as f:
            print(f.read())
        print("-" * 40)
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# NO CLEANUP - keep output for inspection
print(f"\nOutput kept in {test.output_dir}/ for inspection")