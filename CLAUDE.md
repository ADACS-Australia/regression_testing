# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
This is the AMReX regression testing framework, used by Quokka and other AMReX-based applications to automatically build, run, and compare simulation results against benchmarks. It ensures code changes don't break existing functionality.

## Key Components
- **regtest.py** - Main regression testing script
- **Configuration files** (.ini) - Define test suites, build options, and test parameters
- **Benchmark management** - Stores and compares against reference solutions
- **Web reporting** - Generates HTML reports of test results

## Usage
```bash
# Show help and all options
./regtest.py -h

# Run regression tests
./regtest.py <config-file>.ini

# Generate initial benchmarks
./regtest.py --make_benchmarks "Initial benchmark creation" <config-file>.ini

# Update benchmarks after verified changes
./regtest.py --make_benchmarks "Updated physics module" <config-file>.ini

# Run only specific tests
./regtest.py --tests "test1 test2" <config-file>.ini

# Skip comparison (build and run only)
./regtest.py --no_compare <config-file>.ini
```

## Configuration File Structure
```ini
[main]
testTopDir = /path/to/test/directory    # Where tests are run
webTopDir = /path/to/web/output         # HTML report location
sourceTree = C_Src                      # AMReX source tree type
numMakeJobs = 8                         # Parallel build jobs
suiteName = TestSuiteName               # Descriptive name
COMP = g++                              # Compiler choice

[AMReX]
dir = /path/to/amrex                    # AMReX repository location
branch = development                    # Branch to test

[source]
dir = /path/to/application              # Application source (e.g., Quokka)
branch = main                           # Branch to test

[extra-repo1]                           # Additional dependencies
dir = /path/to/dependency
branch = main

# Individual test definitions
[test1]
buildDir = path/to/test/                # Relative to source dir
inputFile = inputs.test                 # Input parameter file
dim = 3                                 # Dimensionality
doVis = 0                              # Generate plots (0/1)
diffDir = final_plt                    # Directory to compare
```

## Test Workflow
1. **Setup** - Pull latest code from specified branches
2. **Build** - Compile each test with specified options
3. **Run** - Execute tests with their input files
4. **Compare** - Diff results against benchmarks
5. **Report** - Generate HTML summary of results

## Key Features
- **Parallel testing** - Run multiple tests simultaneously
- **Flexible comparison** - Compare plotfiles, checkpoint files, or custom outputs
- **Email notifications** - Send results to developers
- **Slack integration** - Post results to Slack channels
- **Custom commands** - Add pre/post processing steps

## Benchmark Management
- Benchmarks stored under `testTopDir/benchmarks/`
- Each benchmark tagged with date and commit hash
- Can maintain multiple benchmark sets
- Automatic benchmark rotation/cleanup options

## Debugging Failed Tests
```bash
# Check detailed output
cat testTopDir/Run/<test_name>/output

# Compare specific variables
fcompare.exe <benchmark_file> <test_file>

# Run single test in isolation
cd testTopDir/Run/<test_name>
./<executable> <inputfile>
```

## Integration with Quokka
- Quokka's tests defined in `regression/quokka-tests.ini`
- Tests cover various physics modules and problem setups
- Benchmarks ensure conservation, accuracy, and stability