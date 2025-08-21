# Batch Job Testing with Regression Testing Suite

This document describes how to use the batch job testing capabilities of the regression testing suite, which integrates with the hpc_performance_testing Python package.

The regression testing suite traditionally uses INI format configuration files, while the hpc_performance_testing package uses YAML format. The batch job commands handle this conversion automatically - you provide an INI file, and it gets converted to YAML internally for hpc_performance_testing compatibility.

## Quick Start

Example configuration files are provided for the Ngarrgu-Tindebeek (NT) HPC system:
- **`config_nt.ini`** - Example INI configuration file pre-configured for Ngarrgu-Tindebeek
- **`env_setup_ucx.sh`** - Environment setup script for loading required modules on Ngarrgu-Tindebeek

To run regression tests as batch jobs on an HPC cluster, follow these steps:

```bash
# 1. Setup the environment (must be sourced, not executed)
source regtest.setup.sh config_nt.ini batch_test/

# 2. Submit batch jobs to the cluster
python regtest.py submit config_nt.ini batch_test/

# 3. Check job status
python regtest.py check config_nt.ini batch_test/

# 4. Extract results after jobs complete
python regtest.py extract config_nt.ini batch_test/

# 5. Generate web report
python regtest.py www config_nt.ini batch_test/
```

The `batch_test/` directory is optional and defaults to `./` if omitted.

**Note for Ngarrgu-Tindebeek users**: The provided `config_nt.ini` and `env_setup_ucx.sh` files are ready to use. Simply adjust the paths in `config_nt.ini` to match your setup locations if needed.

## INI File Configuration

The following variables must be added to the `[main]` section of your INI file for batch job testing:

### Required Variables

- **`useBatch`**: Set to `True` to enable batch job mode. This triggers the use of hpc_performance_testing for job submission instead of local execution.

### Optional Variables

- **`setupFromFolder`**: Path to a directory containing environment setup scripts (`env_*.sh`) and test input files (`tests_input/`). The environment script will be sourced to load necessary modules.

- **`virtualEnvironment`**: Path to a Python virtual environment to activate. This should contain the hpc_performance_testing package and other dependencies.

### HPC Configuration

- **`cluster`**: Name of the HPC cluster (e.g., `NT`, `setonix`, `gadi`)
- **`scheduler`**: Job scheduler type (e.g., `slurm`, `pbs`)
- **`gpu_build`**: GPU build type if applicable (e.g., `cuda`, `hip`)
- **`shell`**: Shell to use for job scripts (e.g., `/bin/bash`)

### Path Configuration

- **`working_dir`**: Working directory for the batch job (usually `./`)
- **`environment`**: Name of environment setup script
- **`test_inputs`**: Path to test input files directory

### Job Settings

- **`ntasks_per_node`**: Number of MPI tasks per node
- **`mem_per_node`**: Memory allocation per node (e.g., `4G`)
- **`scaling_strategy`**: Scaling strategy for tests (e.g., `weak_3d`)
- **`min_cores`**: Minimum number of cores for scaling tests
- **`max_cores`**: Maximum number of cores for scaling tests

## Command Descriptions

### `source regtest.setup.sh config.ini [work_dir/]`

This command prepares the environment for batch job testing. It must be sourced (not executed) to preserve environment changes. The script performs the following actions:

1. Creates the work directory if it doesn't exist
2. Sources environment module scripts from the `setupFromFolder` path specified in the INI file
3. Deactivates any currently active Python virtual environment and activates the one specified in `virtualEnvironment`
4. Copies the environment setup script and `tests_input` folder to the work directory (without overwriting existing files)
5. Verifies that the `hpc_performance_testing` Python module is available

The script provides clear status messages and will stop with an error if any required resources are not found.

### `regtest.py submit config.ini [work_dir/]`

The submit command initiates batch job submission to the HPC cluster. This command:

1. Validates that `useBatch = True` is set in the INI file
2. Creates the work directory if it doesn't exist
3. Converts the INI configuration to YAML format required by hpc_performance_testing
4. Saves the YAML configuration as `config.yaml` in the work directory
5. Calls the hpc_performance_testing `submit_jobs()` function to submit jobs to the cluster
6. The hpc_performance_testing package creates a `test_instance.yaml` file containing runtime information and job IDs

After submission, jobs will be queued in the cluster's scheduler and will run when resources become available. Note that `test_instance.yaml` is different from `config.yaml` - it contains runtime metadata about the submitted jobs rather than the test configuration.

### `regtest.py check config.ini [work_dir/]`

The check command monitors the status of submitted batch jobs. This command:

1. Reads the `test_instance.yaml` file created during submission
2. Calls the hpc_performance_testing `check_jobs()` function to query job status from the scheduler
3. Reports the current status (e.g., `WAIT`, `RUNNING`, `COMPLETE`, `FAILED`)

This command can be run repeatedly to monitor job progress without affecting the running jobs.

### `regtest.py extract config.ini [work_dir/]`

The extract command processes completed job outputs to generate performance metrics. This command:

1. Verifies that jobs have completed by checking for the `test_instance.yaml` file
2. Calls the hpc_performance_testing `extract_results()` function to parse job output files
3. Generates three parquet files in `work_dir/performance_test/TIMESTAMP/results/` (where TIMESTAMP is a date/time string like `20250821182621`):
   - `job_submission.parquet`: Job submission metadata (created at submit time)
   - `job_output.parquet`: Performance metrics and timing data (created at extract time)
   - `job_exit_status.parquet`: Job completion status and exit codes (created when jobs complete)
4. Reports the location of generated files

The extract command should only be run after jobs have completed (status shows `COMPLETE`). The performance data is stored in the industry-standard parquet format for efficient storage and processing.

### `regtest.py www config.ini [work_dir/]`

The www command generates an HTML report from the extracted performance data. This command:

1. Reads the parquet files generated by the extract command
2. Processes performance metrics including:
   - Wall time for each test
   - Zone updates per second
   - Microseconds per update
   - Scaling efficiency calculations
3. Creates an HTML report at `work_dir/www/index.html` containing:
   - Summary of test results (passed/failed counts)
   - Detailed performance table for each test
   - Scaling efficiency percentages
   - Visual status indicators
4. Provides the path to view the report in a web browser

## Notes

### Example Files for Ngarrgu-Tindebeek (NT)

Two example files are provided specifically configured for the Ngarrgu-Tindebeek HPC system:

1. **`config_nt.ini`**: A complete INI configuration file with settings appropriate for Ngarrgu-Tindebeek, including:
   - SLURM scheduler configuration
   - CUDA GPU build settings
   - UCX-enabled MPI environment
   - Appropriate memory and processor allocations

2. **`env_setup_ucx.sh`**: Environment setup script that loads the required modules on Ngarrgu-Tindebeek, including:
   - Compiler modules
   - MPI libraries with UCX support
   - CUDA toolkit
   - Other dependencies required for Quokka

Users on other HPC systems can use these files as templates, modifying the cluster name, scheduler type, and environment modules as appropriate for their system.

### Important Considerations

1. **Environment Persistence**: The `regtest.setup.sh` script must be sourced (`source` command) rather than executed directly. This ensures that environment changes (module loads, virtual environment activation) persist in your shell session.

2. **Job Dependencies**: Commands should be run in order: setup → submit → check → extract → www. Each step depends on outputs from the previous step.

3. **Cluster Resources**: Job execution time depends on cluster queue wait times and resource availability. Use the check command to monitor progress.

4. **File Preservation**: The setup script will not overwrite existing files in the work directory. To update environment scripts or test inputs, remove them from the work directory first.

5. **Performance Metrics**: The performance data extracted includes:
   - Total zone updates performed
   - Updates per second (throughput)
   - Time per update (latency)
   - Memory usage
   - CPU efficiency

6. **Scaling Analysis**: The www report automatically calculates scaling efficiency by comparing multi-processor performance against a baseline (typically the single-processor run).

### Troubleshooting

- If `hpc_performance_testing` module is not found, ensure the package is installed in your Python environment
- If jobs fail to submit, check that environment modules are loaded correctly and the cluster configuration matches your system
- Exit codes in format "0:0" indicate successful completion; other values indicate errors
- Check job output files in `work_dir/performance_test/TIMESTAMP/results/test_name/` for detailed error messages

### Example INI File

```ini
[main]
useBatch = True
setupFromFolder = /home/user/quokka/setup
virtualEnvironment = /home/user/quokka/venv

cluster = NT
scheduler = slurm
gpu_build = cuda
shell = /bin/bash

working_dir = ./
environment = env_setup_ucx.sh
test_inputs = ./tests_input

ntasks_per_node = 4
mem_per_node = 4G
scaling_strategy = weak_3d
min_cores = 1
max_cores = 10

[test_hydro3d_blast]
name = test_hydro3d_blast
target = HydroBlast3D/test_hydro3d_blast
inputFile = blast_32.in
cmake_cache = -DCMAKE_BUILD_TYPE=Release -DQUOKKA_PYTHON=OFF -DAMReX_SPACEDIM=3
walltime = 00:10:00
mem_per_node = 4G
```