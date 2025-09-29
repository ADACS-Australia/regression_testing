#!/usr/bin/env python3

"""
A simple regression test framework for a AMReX-based code

There are several major sections to this source: the runtime parameter
routines, the test suite routines, and the report generation routines.
They are separated as such in this file.

This test framework understands source based out of the AMReX framework.

"""


import email
import os
import shutil
import smtplib
import sys
import tarfile
import time
import re
import json
import configparser
import yaml

import params
import test_util
import test_report as report
import test_coverage as coverage

safe_flags = ['TEST', 'USE_CUDA', 'USE_ACC', 'USE_MPI', 'USE_OMP', 'DEBUG', 'USE_GPU']

def _check_safety(cs):
    try:
        flag = cs.split("=")[0]
        return flag in safe_flags
    except:
        return False

def check_realclean_safety(compile_strings):
    split_strings = compile_strings.strip().split()
    return all([_check_safety(cs) for cs in split_strings])

def find_build_dirs(tests):
    """ given the list of test objects, find the set of UNIQUE build
        directories.  Note if we have the useExtraBuildDir flag set """

    build_dirs = []
    last_safe = False

    for obj in tests:

        # keep track of the build directory and which source tree it is
        # in (e.g. the extra build dir)

        # first find the list of unique build directories
        dir_pair = (obj.buildDir, obj.extra_build_dir)
        if build_dirs.count(dir_pair) == 0:
            build_dirs.append(dir_pair)

        # re-make all problems that specify an extra compile argument,
        # and the test that comes after, just to make sure that any
        # unique build commands are seen.
        obj.reClean = 1
        if check_realclean_safety(obj.addToCompileString):
            if last_safe:
                obj.reClean = 0
            else:
                last_safe = True

    return build_dirs

def cmake_setup(suite):
    "Setup for cmake"

    #--------------------------------------------------------------------------
    # build AMReX with CMake
    #--------------------------------------------------------------------------
    # True:  install amrex and use install-tree
    # False: use directly build-tree
    install = False

    # Configure Amrex
    builddir, installdir = suite.cmake_config(name="AMReX",
                                              path=suite.amrex_dir,
                                              configOpts=suite.amrex_cmake_opts,
                                              install=install)
    if install:
        suite.amrex_install_dir = installdir
        target = 'install'
    else:
        suite.amrex_install_dir = builddir
        target = 'all'

    # Define additional env variable to point to AMReX install location
    env = {'AMReX_ROOT':suite.amrex_install_dir }

    rc, _ = suite.cmake_build(name="AMReX",
                              target=target,
                              path=builddir,
                              env=env)

    # If AMReX build fails, issue a catastrophic error
    if not rc == 0:
        errstr = "\n \nERROR! AMReX build failed \n"
        errstr += f"Check {suite.full_test_dir}AMReX.cmake.log for more information."
        sys.exit(errstr)


    #--------------------------------------------------------------------------
    # Configure main suite with CMake: build will be performed only when
    # needed for tests
    #--------------------------------------------------------------------------
    builddir, installdir = suite.cmake_config(name=suite.suiteName,
                                              path=suite.source_dir,
                                              configOpts=suite.source_cmake_opts,
                                              install=0,
                                              env=env)

    suite.source_build_dir = builddir

    return rc




def ini_to_yaml(ini_file, work_dir):
    """Convert INI file to YAML format for batch job submission"""
    config = configparser.ConfigParser()
    config.read(ini_file)
    
    # Extract main section data
    main = dict(config['main'])
    
    # Build YAML structure
    yaml_data = {}
    
    # HPC section
    yaml_data['hpc'] = {
        'cluster': main.get('cluster', ''),
        'scheduler': main.get('scheduler', ''),
        'gpu_build': main.get('gpu_build', ''),
        'shell': main.get('shell', '')
    }
    
    # Paths section
    working_dir = main.get('working_dir', '')
    environment = main.get('environment', '')
    test_inputs = main.get('test_inputs', '')
    
    # Since we'll be changing to the work directory before running submit_jobs,
    # we need to adjust the paths in the YAML to be relative to that directory
    if working_dir and working_dir != './':
        # We're going to cd to work_dir, so set YAML working_dir to ./
        yaml_working_dir = './'
        # Environment and test_inputs should be relative to the new working directory
        yaml_environment = environment
        yaml_test_inputs = test_inputs
    else:
        # No working_dir change needed
        yaml_working_dir = working_dir
        yaml_environment = environment
        yaml_test_inputs = test_inputs
    
    yaml_data['paths'] = {
        'working_dir': yaml_working_dir,
        'environment': yaml_environment,
        'test_inputs': yaml_test_inputs
    }
    
    # Global job settings
    yaml_data['global_job_settings'] = {
        'ntasks_per_node': int(main.get('ntasks_per_node', 1)),
        'mem_per_node': main.get('mem_per_node', '')
    }
    
    # Scaling section
    yaml_data['scaling'] = {
        'strategy': main.get('scaling_strategy', ''),
        'min_cores': None if main.get('min_cores', '1') == '1' else int(main.get('min_cores', 1)),
        'max_cores': int(main.get('max_cores', 1))
    }
    
    # Tests section
    tests = []
    for section in config.sections():
        if section != 'main':
            test_data = dict(config[section])
            
            # Parse cmake_cache string into list
            cmake_cache = test_data.get('cmake_cache', '').split() if test_data.get('cmake_cache') else []
            
            test = {
                'name': test_data.get('name', section),
                'target': test_data.get('target', ''),
                'input_file': test_data.get('inputfile', ''),
                'cmake_cache': cmake_cache,
                'job_settings': {
                    'walltime': test_data.get('walltime', ''),
                    'mem_per_node': test_data.get('mem_per_node', '')
                }
            }
            tests.append(test)
    
    yaml_data['tests'] = tests
    
    return yaml_data

def handle_batch_submit(args, ini_file, work_dir):
    """Handle the submit command for batch jobs"""
    # Read INI file to check for useBatch
    config = configparser.ConfigParser()
    config.read(ini_file)
    
    if not config.has_option('main', 'useBatch'):
        raise Exception(f"INI file {ini_file} does not have useBatch option in [main] section")
    
    use_batch = config.getboolean('main', 'useBatch')
    if not use_batch:
        raise Exception(f"useBatch is not True in {ini_file}. This command is only for batch jobs.")
    
    # Create work directory if it doesn't exist
    os.makedirs(work_dir, exist_ok=True)
    
    # Convert INI to YAML
    yaml_data = ini_to_yaml(ini_file, work_dir)
    
    # Save YAML file to work directory
    yaml_file = os.path.join(work_dir, 'config.yaml')
    with open(yaml_file, 'w') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)
    
    print(f"Created YAML configuration at {yaml_file}")
    
    # Import and run submit_jobs from hpc_performance_testing
    try:
        from hpc_performance_testing import submit_jobs
        
        # Setup logging to runtime_err.log in the current directory
        import subprocess
        import datetime
        runtime_log = 'runtime_err.log'
        
        # Log the start of submission
        with open(runtime_log, 'a') as log:
            log.write(f"\n{'='*60}\n")
            log.write(f"Starting batch job submission at {datetime.datetime.now()}\n")
            log.write(f"Config file: {ini_file}\n")
            log.write(f"Work directory: {work_dir}\n")
            log.flush()
        
        # Change to work directory if specified
        if work_dir and work_dir != './':
            actual_work_dir = os.path.abspath(work_dir)
            
            with open(runtime_log, 'a') as log:
                log.write(f"Changing to working directory: {actual_work_dir}\n")
                log.flush()
            
            original_dir = os.getcwd()
            os.chdir(actual_work_dir)
            
            try:
                # Run submit_jobs with stderr redirected to log file
                # Since we changed to the work directory, use relative path
                relative_yaml_file = 'config.yaml'
                # Need to use absolute path for runtime_log since we changed directories
                abs_runtime_log = os.path.join(original_dir, runtime_log)
                with open(abs_runtime_log, 'a') as log:
                    log.write(f"Calling submit_jobs with YAML: {relative_yaml_file}\n")
                    log.flush()
                    # Redirect stderr to the log file during submit_jobs
                    import sys
                    old_stderr = sys.stderr
                    sys.stderr = log
                    try:
                        submit_jobs(relative_yaml_file)
                    finally:
                        sys.stderr = old_stderr
                    log.write(f"submit_jobs completed at {datetime.datetime.now()}\n")
                    log.flush()
                print(f"Batch jobs submitted successfully from {yaml_file}")
            finally:
                os.chdir(original_dir)
        else:
            # No directory change needed
            with open(runtime_log, 'a') as log:
                log.write(f"Calling submit_jobs with YAML: {yaml_file}\n")
                log.flush()
                # Redirect stderr to the log file during submit_jobs
                import sys
                old_stderr = sys.stderr
                sys.stderr = log
                try:
                    submit_jobs(yaml_file)
                finally:
                    sys.stderr = old_stderr
                log.write(f"submit_jobs completed at {datetime.datetime.now()}\n")
                log.flush()
            print(f"Batch jobs submitted successfully from {yaml_file}")
    except ImportError as e:
        print(f"Error: Could not import hpc_performance_testing module: {e}")
        print("Make sure the mk2025a package is installed in your Python environment")
        sys.exit(1)
    except Exception as e:
        print(f"Error submitting batch jobs: {e}")
        sys.exit(1)

def handle_batch_check(args, ini_file, work_dir):
    """Handle the check command for batch jobs"""
    # Read INI file to check for useBatch
    config = configparser.ConfigParser()
    config.read(ini_file)
    
    if not config.has_option('main', 'useBatch'):
        raise Exception(f"INI file {ini_file} does not have useBatch option in [main] section")
    
    use_batch = config.getboolean('main', 'useBatch')
    if not use_batch:
        raise Exception(f"useBatch is not True in {ini_file}. This command is only for batch jobs.")
    
    # Check if work directory exists
    if not os.path.exists(work_dir):
        print(f"Error: Work directory {work_dir} does not exist. Run submit command first.")
        sys.exit(1)
    
    # Look for test_instance.yaml file in the work directory
    test_instance_file = os.path.join(work_dir, 'test_instance.yaml')
    if not os.path.exists(test_instance_file):
        print(f"Error: test_instance.yaml not found in {work_dir}. Run submit command first.")
        sys.exit(1)
    
    # Import and run check_jobs from hpc_performance_testing
    try:
        from hpc_performance_testing import check_jobs
        status = check_jobs(test_instance_file)
        print(f"Job status: {status}")
        return 0
    except ImportError as e:
        print(f"Error: Could not import hpc_performance_testing module: {e}")
        print("Make sure the mk2025a package is installed in your Python environment")
        sys.exit(1)
    except Exception as e:
        print(f"Error checking batch jobs: {e}")
        sys.exit(1)

def handle_batch_extract(args, ini_file, work_dir):
    """Handle the extract command for batch jobs"""
    # Read INI file to check for useBatch
    config = configparser.ConfigParser()
    config.read(ini_file)
    
    if not config.has_option('main', 'useBatch'):
        raise Exception(f"INI file {ini_file} does not have useBatch option in [main] section")
    
    use_batch = config.getboolean('main', 'useBatch')
    if not use_batch:
        raise Exception(f"useBatch is not True in {ini_file}. This command is only for batch jobs.")
    
    # Check if work directory exists
    if not os.path.exists(work_dir):
        print(f"Error: Work directory {work_dir} does not exist. Run submit command first.")
        sys.exit(1)
    
    # Look for test_instance.yaml file in the work directory
    test_instance_file = os.path.join(work_dir, 'test_instance.yaml')
    if not os.path.exists(test_instance_file):
        print(f"Error: test_instance.yaml not found in {work_dir}. Run submit command first.")
        sys.exit(1)
    
    # Import and run extract_results from hpc_performance_testing
    try:
        from hpc_performance_testing import extract_results
        extract_results(test_instance_file)
        print(f"Results extracted successfully from {test_instance_file}")
        
        # Check if results were created
        with open(test_instance_file, 'r') as f:
            test_instance = yaml.safe_load(f)
        
        if 'runtime' in test_instance and 'test_instance' in test_instance['runtime']:
            results_dir = os.path.join(test_instance['runtime']['test_instance'], 'results')
            if os.path.exists(results_dir):
                print(f"Results available in: {results_dir}")
                # List the parquet files
                parquet_files = [f for f in os.listdir(results_dir) if f.endswith('.parquet')]
                if parquet_files:
                    print("Generated parquet files:")
                    for pf in parquet_files:
                        print(f"  - {pf}")
        
        return 0
    except ImportError as e:
        print(f"Error: Could not import hpc_performance_testing module: {e}")
        print("Make sure the mk2025a package is installed in your Python environment")
        sys.exit(1)
    except Exception as e:
        print(f"Error extracting batch job results: {e}")
        sys.exit(1)

def handle_batch_setup(args, ini_file):
    """Handle the setup command - prepare the environment for regression testing
    
    This replaces the bash script regtest.setup.sh with Python implementation.
    """
    import shutil
    import glob
    import subprocess
    
    def print_msg(msg):
        print(f"==> {msg}")
    
    def print_error(msg):
        print(f"ERROR: {msg}", file=sys.stderr)
    
    def print_success(msg):
        print(f"✓ {msg}")
    
    # Check if config file exists
    if not os.path.exists(ini_file):
        print_error(f"Configuration file not found: {ini_file}")
        return 1
    
    # Read configuration
    config = configparser.ConfigParser()
    config.read(ini_file)
    
    # Get working_dir from INI file
    work_dir = config.get('main', 'working_dir', fallback='./')
    print_msg(f"Setting up regression testing environment")
    print_msg(f"Config file: {ini_file}")
    print_msg(f"Work directory: {work_dir}")
    
    # Step a: Create work directory if it doesn't exist
    if not os.path.exists(work_dir):
        print_msg(f"Creating work directory: {work_dir}")
        try:
            os.makedirs(work_dir, exist_ok=True)
            print_success("Work directory created")
        except Exception as e:
            print_error(f"Failed to create work directory: {e}")
            return 1
    else:
        print_msg(f"Work directory already exists: {work_dir}")
    
    # Get setupFromFolder and virtualEnvironment from INI file
    setup_folder = config.get('main', 'setupFromFolder', fallback=None)
    virtual_env = config.get('main', 'virtualEnvironment', fallback=None)
    
    env_script_name = None
    
    # Step b: Source environment module script if setupFromFolder is provided
    if setup_folder:
        print_msg(f"Setup folder specified: {setup_folder}")
        
        # Check if setup folder exists
        if not os.path.exists(setup_folder):
            print_error(f"Setup folder does not exist: {setup_folder}")
            return 1
        
        # Find env_*.sh script
        env_scripts = glob.glob(os.path.join(setup_folder, "env_*.sh"))
        if not env_scripts:
            print_error(f"No env_*.sh script found in {setup_folder}")
            return 1
        
        env_script = env_scripts[0]
        env_script_name = os.path.basename(env_script)
        print_msg(f"Found environment script: {env_script_name}")
        
        # Note: We cannot directly source bash scripts in Python
        # Instead, we'll copy the script for later use and inform the user
        print_msg("Note: Python cannot directly source bash scripts.")
        print_msg(f"The environment script '{env_script_name}' will be copied to the work directory.")
        print_msg("You will need to source it manually before running the tests:")
        print_msg(f"  source {os.path.join(work_dir, env_script_name)}")
        
        # Step d: Copy environment script to work directory if needed
        dest_env_script = os.path.join(work_dir, env_script_name)
        if not os.path.exists(dest_env_script):
            print_msg("Copying environment script to work directory")
            try:
                shutil.copy2(env_script, dest_env_script)
                print_success(f"Environment script copied: {env_script_name}")
            except Exception as e:
                print_error(f"Failed to copy environment script: {e}")
                return 1
        else:
            print_msg(f"Environment script already exists in work directory: {env_script_name}")
        
        # Step e: Copy tests_input folder if needed
        source_tests = os.path.join(setup_folder, "tests_input")
        dest_tests = os.path.join(work_dir, "tests_input")
        
        if os.path.exists(source_tests) or os.path.islink(source_tests):
            if not os.path.exists(dest_tests):
                print_msg("Copying tests_input folder to work directory")
                try:
                    # Use copytree with symlinks=False to follow links and copy actual content
                    shutil.copytree(source_tests, dest_tests, symlinks=False)
                    print_success("tests_input folder copied (followed symbolic links)")
                except Exception as e:
                    print_error(f"Failed to copy tests_input folder: {e}")
                    return 1
            else:
                print_msg("tests_input folder already exists in work directory")
        else:
            print_msg("No tests_input folder found in setup folder, skipping")
    else:
        print_msg("No setupFromFolder specified, skipping environment module setup")
    
    # Step c: Handle virtual environment if specified
    if virtual_env:
        print_msg(f"Virtual environment specified: {virtual_env}")
        
        # Check if virtual environment exists
        if not os.path.exists(virtual_env):
            print_error(f"Virtual environment does not exist: {virtual_env}")
            return 1
        
        activate_script = os.path.join(virtual_env, "bin", "activate")
        if not os.path.exists(activate_script):
            print_error(f"Virtual environment activation script not found: {activate_script}")
            return 1
        
        print_msg("Note: Python script cannot activate virtual environments for the parent shell.")
        print_msg("You will need to activate it manually before running the tests:")
        print_msg(f"  source {activate_script}")
    else:
        print_msg("No virtual environment specified, using current Python environment")
    
    # Create runtime error log file in current directory
    runtime_log = "runtime_err.log"
    if not os.path.exists(runtime_log):
        print_msg("Creating runtime error log file")
        try:
            open(runtime_log, 'a').close()
            print_success(f"Runtime error log created: {runtime_log}")
        except Exception as e:
            print_error(f"Failed to create runtime error log: {e}")
    else:
        print_msg(f"Runtime error log already exists: {runtime_log}")
    
    # Final check: Verify hpc_performance_testing is available
    print_msg("Checking for hpc_performance_testing module...")
    try:
        import hpc_performance_testing
        print_success("hpc_performance_testing module is available")
    except ImportError:
        print_error("hpc_performance_testing module not found")
        print("       Please ensure the mk2025a package is installed in your Python environment")
        return 1
    
    # Summary
    print()
    print_success("Setup completed successfully!")
    print(f"  Work directory: {work_dir}")
    if virtual_env:
        print(f"  Virtual environment: {virtual_env} (needs manual activation)")
    if setup_folder and env_script_name:
        print(f"  Environment script: {env_script_name} (needs manual sourcing)")
    print()
    print("Manual steps required before running tests:")
    if setup_folder and env_script_name:
        print(f"  1. source {os.path.join(work_dir, env_script_name)}")
    if virtual_env:
        activate_cmd = f"source {os.path.join(virtual_env, 'bin', 'activate')}"
        if setup_folder:
            print(f"  2. {activate_cmd}")
        else:
            print(f"  1. {activate_cmd}")
    print()
    print("You can then run regression tests with:")
    print(f"  python regression_testing/regtest.py submit {ini_file}")
    print(f"  python regression_testing/regtest.py check {ini_file}")
    print(f"  python regression_testing/regtest.py extract {ini_file}")
    print(f"  python regression_testing/regtest.py www {ini_file}")
    
    return 0


def handle_batch_www(args):
    """Handle the www command for batch jobs - generate web report from parquet files
    
    This command scans all INI files in the current directory to discover folders
    and generate a complete web report for all of them.
    """
    from pathlib import Path
    from datetime import datetime
    import glob
    
    # Import our web generator
    from web_generator import generate_all_pages
    
    # Get current working directory
    work_dir = os.getcwd()
    print(f"Scanning for INI files in: {work_dir}")
    
    # Find all INI files
    ini_files = glob.glob(os.path.join(work_dir, '*.ini'))
    if not ini_files:
        print(f"Error: No INI files found in {work_dir}")
        sys.exit(1)
    
    print(f"Found {len(ini_files)} INI file(s)")
    
    # Scan all INI files to collect folders and verify webOutputDir
    folders = set()
    web_output_dir = None
    
    for ini_file in ini_files:
        config = configparser.ConfigParser()
        config.read(ini_file)
        
        # Check for useBatch
        if not config.has_option('main', 'useBatch'):
            print(f"Warning: {os.path.basename(ini_file)} does not have useBatch option, skipping")
            continue
            
        use_batch = config.getboolean('main', 'useBatch')
        if not use_batch:
            print(f"Warning: {os.path.basename(ini_file)} has useBatch=False, skipping")
            continue
        
        # Get working_dir (folder name)
        if config.has_option('main', 'working_dir'):
            folder = config.get('main', 'working_dir').rstrip('/')
            folders.add(folder)
            print(f"  Found folder '{folder}' in {os.path.basename(ini_file)}")
        
        # Get webOutputDir and verify consistency
        if config.has_option('main', 'webOutputDir'):
            current_web_dir = config.get('main', 'webOutputDir')
            if web_output_dir is None:
                web_output_dir = current_web_dir
            elif web_output_dir != current_web_dir:
                print(f"Error: Inconsistent webOutputDir values:")
                print(f"  Expected: {web_output_dir}")
                print(f"  Found in {os.path.basename(ini_file)}: {current_web_dir}")
                print("All INI files must use the same webOutputDir")
                sys.exit(1)
    
    if not folders:
        print("Error: No valid folders found in INI files")
        sys.exit(1)
    
    if web_output_dir is None:
        print("Error: No webOutputDir found in any INI file")
        print("Please add webOutputDir = /path/to/web/output to your INI files")
        sys.exit(1)
    
    print(f"\nFolders to process: {', '.join(sorted(folders))}")
    print(f"Web output directory: {web_output_dir}")
    
    # Create web output directory if it doesn't exist
    web_output_path = Path(web_output_dir)
    try:
        web_output_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error creating web output directory {web_output_dir}: {e}")
        sys.exit(1)
    
    # Generate web pages for all discovered folders
    try:
        generate_all_pages(work_dir, web_output_dir, sorted(list(folders)))
        print(f"\nWeb report generated successfully!")
        print(f"View with: firefox {os.path.join(web_output_dir, 'index.html')}")
        return 0
    except Exception as e:
        print(f"Error generating web report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def copy_benchmarks(old_full_test_dir, full_web_dir, test_list, bench_dir, log):
    """ copy the last plotfile output from each test in test_list
        into the benchmark directory.  Also copy the diffDir, if
        it exists """
    td = os.getcwd()

    for t in test_list:
        wd = f"{old_full_test_dir}/{t.name}"
        os.chdir(wd)

        if t.compareFile == "" and t.outputFile == "":
            p = t.get_compare_file(output_dir=wd)
        elif not t.outputFile == "":
            if not os.path.exists(t.outputFile):
                p = test_util.get_recent_filename(wd, t.outputFile, ".tgz")
    
    try:
        # Read parquet files
        job_output = pd.read_parquet(job_output_file)
        exit_status = pd.read_parquet(job_exit_file)
        
        # Generate HTML report for each job
        html_files = []
        test_results = []
        
        for idx, row in job_output.iterrows():
            exit_row = exit_status[exit_status['job_id'] == row['job_id']].iloc[0] if len(exit_status[exit_status['job_id'] == row['job_id']]) > 0 else None
            
            # Extract metrics from actual column names and convert to numeric
            zone_updates_per_sec = float(row['zone_update_megaupdates_per_second']) * 1e6 if pd.notna(row.get('zone_update_megaupdates_per_second')) else 0
            microsec_per_update = float(row['zone_update_microseconds_per_update']) if pd.notna(row.get('zone_update_microseconds_per_update')) else 0
            wall_time = float(row['elapse_time']) if pd.notna(row.get('elapse_time')) else 0
            n_mpi = int(row['n_mpi_processes']) if pd.notna(row.get('n_mpi_processes')) else 1
            
            # Calculate total zone updates (updates/sec * time)
            zone_updates_total = int(zone_updates_per_sec * wall_time) if zone_updates_per_sec > 0 and wall_time > 0 else 0
            
            # Create test name from job_id
            test_name = f"test_hydro3d_blast_n{n_mpi}"
            
            # Parse exit code (format might be "0:0" or just "0")
            passed = False
            if exit_row is not None:
                exit_code_str = str(exit_row['exit_code'])
                # Handle "0:0" format or plain "0"
                exit_code = exit_code_str.split(':')[0] if ':' in exit_code_str else exit_code_str
                passed = (exit_code == '0' or exit_code == 0)
            
            test_results.append({
                'name': test_name,
                'mpi_processes': n_mpi,
                'wall_time': wall_time,
                'zone_updates': zone_updates_total,
                'zone_updates_per_sec': zone_updates_per_sec,
                'microsec_per_update': microsec_per_update,
                'status': 'PASSED' if passed else 'FAILED'
            })
        
        # Calculate scaling efficiency (using first test as baseline)
        if len(test_results) > 0:
            baseline = test_results[0]
            baseline_rate_per_proc = baseline['zone_updates_per_sec'] / baseline['mpi_processes']
            
            for test in test_results:
                expected_rate = baseline_rate_per_proc * test['mpi_processes']
                actual_rate = test['zone_updates_per_sec']
                test['scaling_efficiency'] = (actual_rate / expected_rate * 100) if expected_rate > 0 else 0
        
        # Generate main index.html
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Quokka Performance Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .passed {{ color: #4CAF50; font-weight: bold; }}
        .failed {{ color: #f44336; font-weight: bold; }}
        .timestamp {{ color: #999; font-size: 12px; }}
        .metric-box {{ display: inline-block; margin: 10px; padding: 15px; background-color: #f0f0f0; border-radius: 5px; }}
        .metric-value {{ font-size: 20px; font-weight: bold; color: #2196F3; }}
        .metric-label {{ font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Quokka Performance Test Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Test Summary</h2>
        <div>
            <div class="metric-box">
                <div class="metric-value">{len(test_results)}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{sum(1 for t in test_results if t['status'] == 'PASSED')}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{sum(1 for t in test_results if t['status'] == 'FAILED')}</div>
                <div class="metric-label">Failed</div>
            </div>
        </div>
        
        <h2>Test Results</h2>
        <table>
            <tr>
                <th>Test Name</th>
                <th>MPI Processes</th>
                <th>Wall Time (s)</th>
                <th>Zone Updates</th>
                <th>MZone-Updates/s</th>
                <th>μs per Update</th>
                <th>Scaling Efficiency</th>
                <th>Status</th>
            </tr>"""
        
        for test in test_results:
            status_class = 'passed' if test['status'] == 'PASSED' else 'failed'
            efficiency = f"{test.get('scaling_efficiency', 0):.1f}%" if 'scaling_efficiency' in test else 'N/A'
            html_content += f"""
            <tr>
                <td>{test['name']}</td>
                <td>{test['mpi_processes']}</td>
                <td>{test['wall_time']:.2f}</td>
                <td>{test['zone_updates']:,}</td>
                <td>{test['zone_updates_per_sec']/1e6:.2f}</td>
                <td>{test['microsec_per_update']:.3f}</td>
                <td>{efficiency}</td>
                <td class="{status_class}">{test['status']}</td>
            </tr>"""
        
        html_content += f"""
        </table>
        
        <h2>Performance Analysis</h2>
        <p>Performance metrics showing scaling behavior across different MPI process counts.</p>
        
        <hr style="margin-top: 50px;">
        <p style="text-align: center; color: #999; font-size: 12px;">
            Generated by Quokka Regression Testing Suite | 
            <a href="{results_dir}">View raw data</a>
        </p>
    </div>
</body>
</html>"""
        
        # Save the report
        index_file = os.path.join(www_dir, 'index.html')
        with open(index_file, 'w') as f:
            f.write(html_content)
        
        print(f"Web report generated successfully")
        print(f"Report available at: {index_file}")
        print(f"View with: firefox {index_file}")
        
        return 0
        
    except Exception as e:
        print(f"Error generating web report: {e}")
        sys.exit(1)

def copy_benchmarks(old_full_test_dir, full_web_dir, test_list, bench_dir, log):
    """ copy the last plotfile output from each test in test_list
        into the benchmark directory.  Also copy the diffDir, if
        it exists """
    td = os.getcwd()

    for t in test_list:
        wd = f"{old_full_test_dir}/{t.name}"
        os.chdir(wd)

        if t.compareFile == "" and t.outputFile == "":
            p = t.get_compare_file(output_dir=wd)
        elif not t.outputFile == "":
            if not os.path.exists(t.outputFile):
                p = test_util.get_recent_filename(wd, t.outputFile, ".tgz")
            else:
                p = t.outputFile
        else:
            if not os.path.exists(t.compareFile):
                p = test_util.get_recent_filename(wd, t.compareFile, ".tgz")
            else:
                p = t.compareFile

        if p != "" and p is not None:
            if p.endswith(".tgz"):
                try:
                    tg = tarfile.open(name=p, mode="r:gz")
                    tg.extractall()
                except:
                    log.fail("ERROR extracting tarfile")
                else:
                    tg.close()
                idx = p.rfind(".tgz")
                p = p[:idx]

            store_file = p
            if not t.outputFile == "":
                store_file = f"{t.name}_{p}"

            try:
                shutil.rmtree(f"{bench_dir}/{store_file}")
            except:
                pass
            shutil.copytree(p, f"{bench_dir}/{store_file}")

            with open(f"{full_web_dir}/{t.name}.status", 'w') as cf:
                cf.write(f"benchmarks updated.  New file:  {store_file}\n")

        else:   # no benchmark exists
            with open(f"{full_web_dir}/{t.name}.status", 'w') as cf:
                cf.write("benchmarks update failed")

        # is there a diffDir to copy too?
        if not t.diffDir == "":
            diff_dir_bench = f"{bench_dir}/{t.name}_{t.diffDir}"
            if os.path.isdir(diff_dir_bench):
                shutil.rmtree(diff_dir_bench)
                shutil.copytree(t.diffDir, diff_dir_bench)
            else:
                if os.path.isdir(t.diffDir):
                    try:
                        shutil.copytree(t.diffDir, diff_dir_bench)
                    except OSError:
                        log.warn(f"file {t.diffDir} not found")
                    else:
                        log.log(f"new diffDir: {t.name}_{t.diffDir}")
                else:
                    try:
                        shutil.copy(t.diffDir, diff_dir_bench)
                    except OSError:
                        log.warn(f"file {t.diffDir} not found")
                    else:
                        log.log(f"new diffDir: {t.name}_{t.diffDir}")

        os.chdir(td)

def get_variable_names(suite, plotfile):
    """ uses fvarnames to extract the names of variables
        stored in a plotfile """

    # Run fvarnames
    command = "{} {}".format(suite.tools["fvarnames"], plotfile)
    sout, serr, ierr = test_util.run(command)

    if ierr != 0:
        return serr

    # Split on whitespace
    tvars = re.split(r"\s+", sout)[2:-1:2]

    return set(tvars)

def process_comparison_results(stdout, tvars, test):
    """ checks the output of fcompare (passed in as stdout)
        to determine whether all relative errors fall within
        the test's tolerance """

    # Alternative solution - just split on whitespace
    # and iterate through resulting list, attempting
    # to convert the next two items to floats. Assume
    # the current item is a variable if successful.

    # Split on whitespace
    regex = r"\s+"
    words = re.split(regex, stdout)

    indices = filter(lambda i: words[i] in tvars, range(len(words)))

    for i in indices:
        _, abs_err, rel_err = words[i: i + 3]
        if abs(test.tolerance) < abs(float(rel_err)) and test.abs_tolerance < abs(float(abs_err)):
            return False

    return True

def test_performance(test, suite, runtimes):
    """ outputs a warning if the execution time of the test this run
        does not compare favorably to past logged times """

    if test.name not in runtimes:
        return
    runtimes = runtimes[test.name]["runtimes"]

    if len(runtimes) < 1:
        suite.log.log("no completed runs found")
        return

    num_times = len(runtimes)
    suite.log.log(f"{num_times} completed run(s) found")
    suite.log.log("checking performance ...")

    # Slice out correct number of times
    run_diff = num_times - test.runs_to_average
    if run_diff > 0:
        runtimes = runtimes[:-run_diff]
        num_times = test.runs_to_average
    else:
        test.runs_to_average = num_times

    test.past_average = sum(runtimes) / num_times

    # Test against threshold
    meets_threshold, percentage, compare_str = test.measure_performance()
    if meets_threshold is not None and not meets_threshold:
        warn_msg = "test ran {:.1f}% {} than running average of the past {} runs"
        warn_msg = warn_msg.format(percentage, compare_str, num_times)
        suite.log.warn(warn_msg)

def determine_coverage(suite):

    try:
        results = coverage.main(suite.full_test_dir)
    except:
        suite.log.warn("error generating parameter coverage reports, check formatting")
        return

    if not any([res is None for res in results]):

        suite.covered_frac = results[0]
        suite.total = results[1]
        suite.covered_nonspecific_frac = results[2]
        suite.total_nonspecific = results[3]

        spec_file = os.path.join(suite.full_test_dir, coverage.SPEC_FILE)
        nonspec_file = os.path.join(suite.full_test_dir, coverage.NONSPEC_FILE)

        shutil.copy(spec_file, suite.full_web_dir)
        shutil.copy(nonspec_file, suite.full_web_dir)

def test_suite(argv):
    """
    the main test suite driver
    """

    # parse the commandline arguments
    args = test_util.get_args(arg_string=argv)
    
    # Check if this is a batch job command
    if args.command == 'www':
        # www command doesn't need an INI file - it scans all INI files
        handle_batch_www(args)
        return 0
    elif args.command == 'setup':
        # setup command replaces the bash setup script
        if args.input_file is None:
            print(f"Error: setup command requires an INI file")
            return 1
            
        if isinstance(args.input_file, list):
            ini_file = args.input_file[0]
        else:
            ini_file = args.input_file
            
        return handle_batch_setup(args, ini_file)
    elif args.command in ['submit', 'check', 'extract']:
        # These commands still need an INI file
        if args.input_file is None:
            print(f"Error: {args.command} command requires an INI file")
            return 1
            
        if isinstance(args.input_file, list):
            ini_file = args.input_file[0]
        else:
            ini_file = args.input_file
        
        # Read working_dir from INI file
        config = configparser.ConfigParser()
        config.read(ini_file)
        work_dir = config.get('main', 'working_dir', fallback='./')
        
        if args.command == 'submit':
            handle_batch_submit(args, ini_file, work_dir)
            return 0
        elif args.command == 'check':
            handle_batch_check(args, ini_file, work_dir)
            return 0
        elif args.command == 'extract':
            handle_batch_extract(args, ini_file, work_dir)
            return 0

    # read in the test information
    suite, test_list = params.load_params(args)

    active_test_list = [t.name for t in test_list]

    test_list = suite.get_tests_to_run(test_list)

    suite.log.skip()
    suite.log.bold("running tests: ")
    suite.log.indent()
    for obj in test_list:
        suite.log.log(obj.name)
    suite.log.outdent()

    if not args.complete_report_from_crash == "":

        # make sure the web directory from the crash run exists
        suite.full_web_dir = "{}/{}/".format(
            suite.webTopDir, args.complete_report_from_crash)
        if not os.path.isdir(suite.full_web_dir):
            suite.log.fail("Crash directory does not exist")

        suite.test_dir = args.complete_report_from_crash

        # find all the tests that completed in that web directory
        tests = []
        test_file = ""
        was_benchmark_run = 0
        for sfile in os.listdir(suite.full_web_dir):
            if os.path.isfile(sfile) and sfile.endswith(".status"):
                index = sfile.rfind(".status")
                tests.append(sfile[:index])

                with open(suite.full_web_dir + sfile) as f:
                    for line in f:
                        if line.find("benchmarks updated") > 0:
                            was_benchmark_run = 1

            if os.path.isfile(sfile) and sfile.endswith(".ini"):
                test_file = sfile


        # create the report for this test run
        num_failed = report.report_this_test_run(suite, was_benchmark_run,
                                                 "recreated report after crash of suite",
                                                 "", tests, test_file)

        # create the suite report
        suite.log.bold("creating suite report...")
        report.report_all_runs(suite, active_test_list)
        suite.log.close_log()
        sys.exit("done")


    #--------------------------------------------------------------------------
    # check bench dir and create output directories
    #--------------------------------------------------------------------------
    all_compile = all([t.compileTest == 1 for t in test_list])

    if not all_compile:
        bench_dir = suite.get_bench_dir()

    if not args.copy_benchmarks is None:
        last_run = suite.get_last_run()

    suite.make_test_dirs()

    if suite.slack_post:
        if args.note == "" and suite.repos["source"].pr_wanted is not None:
            note = "testing PR-{}".format(suite.repos["source"].pr_wanted)
        else:
            note = args.note

        msg = "> {} ({}) test suite started, id: {}\n> {}".format(
            suite.suiteName, suite.sub_title, suite.test_dir, note)
        suite.slack_post_it(msg)

    if not args.copy_benchmarks is None:
        old_full_test_dir = suite.testTopDir + suite.suiteName + "-tests/" + last_run
        copy_benchmarks(old_full_test_dir, suite.full_web_dir,
                        test_list, bench_dir, suite.log)

        # here, args.copy_benchmarks plays the role of make_benchmarks
        num_failed = report.report_this_test_run(suite, args.copy_benchmarks,
                                                 "copy_benchmarks used -- no new tests run",
                                                 "",
                                                 test_list, args.input_file[0])
        report.report_all_runs(suite, active_test_list)

        if suite.slack_post:
            msg = f"> copied benchmarks\n> {args.copy_benchmarks}"
            suite.slack_post_it(msg)

        sys.exit("done")


    #--------------------------------------------------------------------------
    # figure out what needs updating and do the git updates, save the
    # current hash / HEAD, and make a ChangeLog
    # --------------------------------------------------------------------------
    now = time.localtime(time.time())
    update_time = time.strftime("%Y-%m-%d %H:%M:%S %Z", now)

    no_update = args.no_update.lower()
    if not args.copy_benchmarks is None:
        no_update = "all"

    # the default is to update everything, unless we specified a hash
    # when constructing the Repo object
    if no_update == "none":
        pass

    elif no_update == "all":
        for k in suite.repos:
            suite.repos[k].update = False

    else:
        nouplist = [k.strip() for k in no_update.split(",")]

        for repo in suite.repos.keys():
            if repo.lower() in nouplist:
                suite.repos[repo].update = False

    os.chdir(suite.testTopDir)

    for k in suite.repos:
        suite.log.skip()
        suite.log.bold(f"repo: {suite.repos[k].name}")
        suite.log.indent()

        if suite.repos[k].update or suite.repos[k].hash_wanted:
            suite.repos[k].git_update()

        suite.repos[k].save_head()

        if suite.repos[k].update:
            suite.repos[k].make_changelog()

        suite.log.outdent()


    # keep track if we are running on any branch that is not the suite
    # default
    branches = [suite.repos[r].get_branch_name() for r in suite.repos]
    if not all(suite.default_branch == b for b in branches):
        suite.log.warn("some git repos are not on the default branch")
        bf = open(f"{suite.full_web_dir}/branch.status", "w")
        bf.write("branch different than suite default")
        bf.close()

    #--------------------------------------------------------------------------
    # build the tools and do a make clean, only once per build directory
    #--------------------------------------------------------------------------
    suite.build_tools(test_list)

    all_build_dirs = find_build_dirs(test_list)

    suite.log.skip()
    suite.log.bold("make clean in...")

    for d, source_tree in all_build_dirs:

        if not source_tree == "":
            suite.log.log(f"{d} in {source_tree}")
            os.chdir(suite.repos[source_tree].dir + d)
            suite.make_realclean(repo=source_tree)
        else:
            suite.log.log(f"{d}")
            os.chdir(suite.source_dir + d)
            if suite.sourceTree in ["AMReX", "amrex"]:
                suite.make_realclean(repo="AMReX")
            else:
                suite.make_realclean()

    os.chdir(suite.testTopDir)


    #--------------------------------------------------------------------------
    # Setup Cmake if needed
    #--------------------------------------------------------------------------
    if suite.useCmake and not suite.isSuperbuild:
        cmake_setup(suite)


    #--------------------------------------------------------------------------
    # Get execution times from previous runs
    #--------------------------------------------------------------------------
    runtimes = suite.get_wallclock_history()

    #--------------------------------------------------------------------------
    # main loop over tests
    #--------------------------------------------------------------------------
    for test in test_list:

        suite.log.outdent()  # just to make sure we have no indentation
        suite.log.skip()
        suite.log.bold(f"working on test: {test.name}")
        suite.log.indent()

        if not args.make_benchmarks is None and (test.restartTest or test.compileTest or
                                                 test.selfTest):
            suite.log.warn(f"benchmarks not needed for test {test.name}")
            continue

        output_dir = suite.full_test_dir + test.name + '/'
        os.mkdir(output_dir)
        test.output_dir = output_dir


        #----------------------------------------------------------------------
        # compile the code
        #----------------------------------------------------------------------
        if not test.extra_build_dir == "":
            bdir = suite.repos[test.extra_build_dir].dir + test.buildDir
        else:
            bdir = suite.source_dir + test.buildDir

        # # For cmake builds, there is only one build dir
        # if ( suite.useCmake ): bdir = suite.source_build_dir

        os.chdir(bdir)

        if test.reClean == 1:
            # for one reason or another, multiple tests use different
            # build options, make clean again to be safe
            suite.log.log("re-making clean...")
            if not test.extra_build_dir == "":
                suite.make_realclean(repo=test.extra_build_dir)
            elif suite.sourceTree in ["AMReX", "amrex"]:
                suite.make_realclean(repo="AMReX")
            else:
                suite.make_realclean()

        # Register start time
        test.build_time = time.time()

        suite.log.log("building...")

        coutfile = f"{output_dir}/{test.name}.make.out"

        if suite.sourceTree == "C_Src" or test.testSrcTree == "C_Src":
            if suite.useCmake:
                comp_string, rc = suite.build_test_cmake(test=test, outfile=coutfile)
            else:
                comp_string, rc = suite.build_c(test=test, outfile=coutfile)

            executable = test_util.get_recent_filename(bdir, "", ".ex")

        test.comp_string = comp_string

        # make return code is 0 if build was successful
        if rc == 0:
            test.compile_successful = True
        # Compute compile time
        test.build_time = time.time() - test.build_time
        suite.log.log(f"Compilation time: {test.build_time:.3f} s")

        # copy the make.out into the web directory
        shutil.copy(f"{output_dir}/{test.name}.make.out", suite.full_web_dir)

        if not test.compile_successful:
            error_msg = "ERROR: compilation failed"
            report.report_single_test(suite, test, test_list, failure_msg=error_msg)

            # Print compilation error message (useful for CI tests)
            if suite.verbose > 0:
                with open(f"{output_dir}/{test.name}.make.out") as f:
                    print(f.read())

            continue

        if test.compileTest:
            suite.log.log("creating problem test report ...")
            report.report_single_test(suite, test, test_list)
            continue


        #----------------------------------------------------------------------
        # copy the necessary files over to the run directory
        #----------------------------------------------------------------------
        suite.log.log(f"run & test directory: {output_dir}")
        suite.log.log("copying files to run directory...")

        needed_files = []
        if executable is not None:
            needed_files.append((executable, "move"))

        if test.run_as_script:
            needed_files.append((test.run_as_script, "copy"))

        if test.inputFile:
            suite.log.log("path to input file: {}".format(test.inputFile))
            needed_files.append((test.inputFile, "copy"))
            # strip out any sub-directory from the build dir
            test.inputFile = os.path.basename(test.inputFile)

        if test.probinFile != "":
            needed_files.append((test.probinFile, "copy"))
            # strip out any sub-directory from the build dir
            test.probinFile = os.path.basename(test.probinFile)

        for auxf in test.auxFiles:
            needed_files.append((auxf, "copy"))

        # if any copy/move fail, we move onto the next test
        skip_to_next_test = 0
        for nfile, action in needed_files:
            if action == "copy":
                act = shutil.copy
            elif action == "move":
                act = shutil.move
            else:
                suite.log.fail("invalid action")

            try:
                act(nfile, output_dir)
            except OSError:
                error_msg = f"ERROR: unable to {action} file {nfile}"
                report.report_single_test(suite, test, test_list, failure_msg=error_msg)
                skip_to_next_test = 1
                break

        if skip_to_next_test:
            continue

        skip_to_next_test = 0
        for lfile in test.linkFiles:
            if not os.path.exists(lfile):
                error_msg = f"ERROR: link file {lfile} does not exist"
                report.report_single_test(suite, test, test_list, failure_msg=error_msg)
                skip_to_next_test = 1
                break

            else:
                link_source = os.path.abspath(lfile)
                link_name = os.path.join(output_dir, os.path.basename(lfile))
                try:
                    os.symlink(link_source, link_name)
                except OSError:
                    error_msg = f"ERROR: unable to symlink link file: {lfile}"
                    report.report_single_test(suite, test, test_list, failure_msg=error_msg)
                    skip_to_next_test = 1
                    break

        if skip_to_next_test:
            continue


        #----------------------------------------------------------------------
        # run the test
        #----------------------------------------------------------------------
        suite.log.log("running the test...")

        os.chdir(output_dir)

        test.wall_time = time.time()

        if suite.sourceTree == "C_Src" or test.testSrcTree == "C_Src":

            base_cmd = f"./{executable} {test.inputFile} "
            if suite.plot_file_name != "":
                base_cmd += f" {suite.plot_file_name}={test.name}_plt "
            if suite.check_file_name != "none":
                base_cmd += f" {suite.check_file_name}={test.name}_chk "

            # keep around the checkpoint files only for the restart runs
            if test.restartTest:
                if suite.check_file_name != "none":
                    base_cmd += " amr.checkpoint_files_output=1 amr.check_int=%d " % \
                        (test.restartFileNum)
            else:
                if suite.check_file_name != "none":
                    base_cmd += " amr.checkpoint_files_output=0"

            base_cmd += f" {suite.globalAddToExecString} {test.runtime_params}"

        if test.run_as_script:
            base_cmd = f"./{test.run_as_script} {test.script_args}"

        if test.customRunCmd is not None:
            base_cmd = test.customRunCmd

        if args.with_valgrind:
            base_cmd = "valgrind " + args.valgrind_options + " " + base_cmd


        suite.run_test(test, base_cmd)

        # if it is a restart test, then rename the final output file and
        # restart the test
        if (test.ignore_return_code == 1 or test.return_code == 0) and test.restartTest:
            skip_restart = False

            last_file = test.get_compare_file(output_dir=output_dir)

            if last_file == "":
                error_msg = "ERROR: test did not produce output.  Restart test not possible"
                skip_restart = True

            if len(test.find_backtrace()) > 0:
                error_msg = "ERROR: test produced backtraces.  Restart test not possible"
                skip_restart = True

            if skip_restart:
                # copy what we can
                test.wall_time = time.time() - test.wall_time
                shutil.copy(test.outfile, suite.full_web_dir)
                if os.path.isfile(test.errfile):
                    shutil.copy(test.errfile, suite.full_web_dir)
                    test.has_stderr = True
                suite.copy_backtrace(test)
                report.report_single_test(suite, test, test_list, failure_msg=error_msg)
                continue
            orig_last_file = f"orig_{last_file}"
            shutil.move(last_file, orig_last_file)

            if test.diffDir:
                orig_diff_dir = f"orig_{test.diffDir}"
                shutil.move(test.diffDir, orig_diff_dir)

            # get the file number to restart from
            restart_file = "%s_chk%5.5d" % (test.name, test.restartFileNum)

            suite.log.log(f"restarting from {restart_file} ... ")

            if suite.sourceTree == "C_Src" or test.testSrcTree == "C_Src":

                base_cmd = "./{} {} {}={}_plt amr.restart={} ".format(
                    executable, test.inputFile, suite.plot_file_name, test.name, restart_file)

                if suite.check_file_name != "none":
                    base_cmd += f" {suite.check_file_name}={test.name}_chk amr.checkpoint_files_output=0 "

                base_cmd += f" {suite.globalAddToExecString} {test.runtime_params}"

                if test.run_as_script:
                    base_cmd = f"./{test.run_as_script} {test.script_args}"
                    # base_cmd += " amr.restart={}".format(restart_file)

                if test.customRunCmd is not None:
                    base_cmd = test.customRunCmd
                    base_cmd += " amr.restart={}".format(restart_file)

                if args.with_valgrind:
                    base_cmd = "valgrind " + args.valgrind_options + " " + base_cmd

            suite.run_test(test, base_cmd)

        test.wall_time = time.time() - test.wall_time
        suite.log.log(f"Execution time: {test.wall_time:.3f} s")

        # Check for performance drop
        if (test.ignore_return_code == 1 or test.return_code == 0) and test.check_performance:
            test_performance(test, suite, runtimes)

        #----------------------------------------------------------------------
        # do the comparison
        #----------------------------------------------------------------------
        output_file = ""
        if (test.ignore_return_code == 1 or test.return_code == 0) and not test.selfTest:

            if test.outputFile == "":
                if test.compareFile == "":
                    compare_file = test.get_compare_file(output_dir=output_dir)
                else:
                    # we specified the name of the file we want to
                    # compare to -- make sure it exists
                    compare_file = test.compareFile
                    if not os.path.exists(compare_file):
                        compare_file = ""

                output_file = compare_file
            else:
                output_file = test.outputFile
                compare_file = test.name+'_'+output_file


            # get the number of levels for reporting
            if not test.run_as_script and "fboxinfo" in suite.tools:

                prog = "{} -l {}".format(suite.tools["fboxinfo"], output_file)
                stdout0, _, rc = test_util.run(prog)
                test.nlevels = stdout0.rstrip('\n')
                if not isinstance(params.convert_type(test.nlevels), int):
                    test.nlevels = ""

            if not test.doComparison:
                test.compare_successful = not test.crashed

            if args.make_benchmarks is None and test.doComparison:

                suite.log.log("doing the comparison...")
                suite.log.indent()
                suite.log.log(f"comparison file: {output_file}")

                test.compare_file_used = output_file

                if not test.restartTest:
                    bench_file = bench_dir + compare_file
                else:
                    bench_file = orig_last_file

                # see if it exists
                # note, with AMReX, the plotfiles are actually directories
                # switched to exists to handle the run_as_script case

                if not os.path.exists(bench_file):
                    suite.log.warn("no corresponding benchmark found")
                    bench_file = ""

                    with open(test.comparison_outfile, 'w') as cf:
                        cf.write("WARNING: no corresponding benchmark found\n")
                        cf.write("         unable to do a comparison\n")

                else:
                    if not compare_file == "":

                        suite.log.log(f"benchmark file: {bench_file}")

                        if test.run_as_script:

                            command = f"diff {bench_file} {output_file}"

                        else:

                            command = "{} --abort_if_not_all_found -n 0".format(suite.tools["fcompare"])

                            if test.tolerance is not None:
                                command += " --rel_tol {}".format(test.tolerance)

                            if test.abs_tolerance is not None:
                                command += " --abs_tol {}".format(test.abs_tolerance)

                            command += " {} {}".format(bench_file, output_file)

                        sout, _, ierr = test_util.run(command,
                                                      outfile=test.comparison_outfile,
                                                      store_command=True)

                        if test.run_as_script:

                            test.compare_successful = not sout

                        else:

                            # fcompare still reports success even if there were NaNs, so let's double check for NaNs
                            has_nan = 0
                            for line in sout:
                                if "< NaN present >" in line:
                                    has_nan = 1
                                    break

                            if has_nan == 0:
                                test.compare_successful = ierr == 0
                            else:
                                test.compare_successful = 0

                        if test.compareParticles:
                            for ptype in test.particleTypes.strip().split():
                                command = "{}".format(suite.tools["particle_compare"])

                                if test.particle_tolerance is not None:
                                    command += " --rel_tol {}".format(test.particle_tolerance)

                                if test.particle_abs_tolerance is not None:
                                    command += " --abs_tol {}".format(test.particle_abs_tolerance)

                                command += " {} {} {}".format(bench_file, output_file, ptype)

                                sout, _, ierr = test_util.run(command,
                                                              outfile=test.comparison_outfile, store_command=True)

                                test.compare_successful = test.compare_successful and not ierr

                    else:
                        suite.log.warn("unable to do a comparison")

                        with open(test.comparison_outfile, 'w') as cf:
                            cf.write("WARNING: run did not produce any output\n")
                            cf.write("         unable to do a comparison\n")

                suite.log.outdent()

                if not test.diffDir == "":
                    if not test.restartTest:
                        diff_dir_bench = bench_dir + '/' + test.name + '_' + test.diffDir
                    else:
                        diff_dir_bench = orig_diff_dir

                    suite.log.log("doing the diff...")
                    suite.log.log(f"diff dir: {test.diffDir}")

                    command = "diff {} -r {} {}".format(
                        test.diffOpts, diff_dir_bench, test.diffDir)

                    outfile = test.comparison_outfile
                    sout, serr, diff_status = test_util.run(command, outfile=outfile, store_command=True)

                    if diff_status == 0:
                        diff_successful = True
                        with open(test.comparison_outfile, 'a') as cf:
                            cf.write("\ndiff was SUCCESSFUL\n")
                    else:
                        diff_successful = False

                    test.compare_successful = test.compare_successful and diff_successful

            elif test.doComparison:   # make_benchmarks

                if not compare_file == "":

                    if not output_file == compare_file:
                        source_file = output_file
                    else:
                        source_file = compare_file

                    suite.log.log(f"storing output of {test.name} as the new benchmark...")
                    suite.log.indent()
                    suite.log.warn(f"new benchmark file: {compare_file}")
                    suite.log.outdent()

                    if test.run_as_script:
                        bench_path = os.path.join(bench_dir, compare_file)
                        try:
                            os.remove(bench_path)
                        except:
                            pass
                        shutil.copy(source_file, bench_path)

                    else:
                        try:
                            shutil.rmtree(f"{bench_dir}/{compare_file}")
                        except:
                            pass

                        shutil.copytree(source_file, f"{bench_dir}/{compare_file}")

                    with open(f"{test.name}.status", 'w') as cf:
                        cf.write(f"benchmarks updated.  New file:  {compare_file}\n")

                else:
                    with open(f"{test.name}.status", 'w') as cf:
                        cf.write("benchmarks failed")

                    # copy what we can
                    shutil.copy(test.outfile, suite.full_web_dir)
                    if os.path.isfile(test.errfile):
                        shutil.copy(test.errfile, suite.full_web_dir)
                        test.has_stderr = True
                    suite.copy_backtrace(test)
                    error_msg = "ERROR: runtime failure during benchmark creation"
                    report.report_single_test(suite, test, test_list, failure_msg=error_msg)


                if not test.diffDir == "":
                    diff_dir_bench = f"{bench_dir}/{test.name}_{test.diffDir}"
                    if os.path.isdir(diff_dir_bench):
                        shutil.rmtree(diff_dir_bench)
                        shutil.copytree(test.diffDir, diff_dir_bench)
                    else:
                        if os.path.isdir(test.diffDir):
                            shutil.copytree(test.diffDir, diff_dir_bench)
                        else:
                            shutil.copy(test.diffDir, diff_dir_bench)
                    suite.log.log(f"new diffDir: {test.name}_{test.diffDir}")

            else:  # don't do a pltfile comparison
                test.compare_successful = True

        elif (test.ignore_return_code == 1 or test.return_code == 0):   # selfTest

            if args.make_benchmarks is None:

                suite.log.log(f"looking for selfTest success string: {test.stSuccessString} ...")

                try:
                    of = open(test.outfile)
                except OSError:
                    suite.log.warn("no output file found")
                    out_lines = ['']
                else:
                    out_lines = of.readlines()

                    # successful comparison is indicated by presence
                    # of success string
                    for line in out_lines:
                        if line.find(test.stSuccessString) >= 0:
                            test.compare_successful = True
                            break

                    of.close()

                with open(test.comparison_outfile, 'w') as cf:
                    if test.compare_successful:
                        cf.write("SELF TEST SUCCESSFUL\n")
                    else:
                        cf.write("SELF TEST FAILED\n")


        #----------------------------------------------------------------------
        # do any requested visualization (2- and 3-d only) and analysis
        #----------------------------------------------------------------------
        if (test.ignore_return_code == 1 or test.return_code == 0) and not test.selfTest:
            if output_file != "":
                if args.make_benchmarks is None:

                    # get any parameters for the summary table
                    job_info_file = f"{output_file}/job_info"
                    if os.path.isfile(job_info_file):
                        test.has_jobinfo = 1

                    try:
                        jif = open(job_info_file)
                    except:
                        suite.log.warn("unable to open the job_info file")
                    else:
                        job_file_lines = jif.readlines()
                        jif.close()

                        if suite.summary_job_info_field1 != "":
                            for l in job_file_lines:
                                if l.startswith(suite.summary_job_info_field1.strip()) and l.find(":") >= 0:
                                    _tmp = l.split(":")[1]
                                    idx = _tmp.rfind("/") + 1
                                    test.job_info_field1 = _tmp[idx:]
                                    break

                        if suite.summary_job_info_field2 != "":
                            for l in job_file_lines:
                                if l.startswith(suite.summary_job_info_field2.strip()) and l.find(":") >= 0:
                                    _tmp = l.split(":")[1]
                                    idx = _tmp.rfind("/") + 1
                                    test.job_info_field2 = _tmp[idx:]
                                    break

                        if suite.summary_job_info_field3 != "":
                            for l in job_file_lines:
                                if l.startswith(suite.summary_job_info_field3.strip()) and l.find(":") >= 0:
                                    _tmp = l.split(":")[1]
                                    idx = _tmp.rfind("/") + 1
                                    test.job_info_field3 = _tmp[idx:]
                                    break

                    # visualization
                    if test.doVis:

                        if test.dim == 1:
                            suite.log.log(f"Visualization not supported for dim = {test.dim}")
                        else:
                            suite.log.log("doing the visualization...")
                            tool = suite.tools["fsnapshot"]
                            test_util.run('{} --palette {}/Palette --variable "{}" "{}"'.format(
                                tool, suite.f_compare_tool_dir, test.visVar, output_file))

                            # convert the .ppm files into .png files
                            ppm_file = test_util.get_recent_filename(output_dir, "", ".ppm")
                            if not ppm_file is None:
                                png_file = ppm_file.replace(".ppm", ".png")
                                from PIL import Image
                                with Image.open(ppm_file) as im:
                                    im.save(png_file)
                                test.png_file = png_file

                    # analysis
                    if not test.analysisRoutine == "":

                        suite.log.log("doing the analysis...")
                        analysis_start_time = time.time()
                        if not test.extra_build_dir == "":
                            tool = f"{suite.repos[test.extra_build_dir].dir}/{test.analysisRoutine}"
                        else:
                            tool = f"{suite.source_dir}/{test.analysisRoutine}"

                        shutil.copy(tool, os.getcwd())

                        if test.analysisMainArgs == "":
                            option = ""
                        else:
                            option = eval(f"suite.{test.analysisMainArgs}")

                        cmd_name = os.path.basename(test.analysisRoutine)
                        cmd_string = f"./{cmd_name} {option} {output_file}"
                        outfile = f"{test.name}.analysis.out"
                        _, _, rc = test_util.run(cmd_string, outfile=outfile, store_command=True)

                        if rc == 0:
                            analysis_successful = True
                        else:
                            analysis_successful = False
                            suite.log.warn("analysis failed...")

                            # Print analysis error message (useful for CI tests)
                            if suite.verbose > 0:
                                with open(outfile) as f:
                                    print(f.read())

                        analysis_time = time.time() - analysis_start_time
                        suite.log.log(f"Analysis time: {analysis_time:.3f} s")

                        test.analysis_successful = analysis_successful

            else:
                if test.doVis or test.analysisRoutine != "":
                    suite.log.warn("no output file.  Skipping visualization")

        #----------------------------------------------------------------------
        # if the test ran and passed, add its runtime to the dictionary
        #----------------------------------------------------------------------

        if (test.ignore_return_code == 1 or test.return_code == 0) and test.record_runtime(suite):
            test_dict = runtimes.setdefault(test.name, suite.timing_default)
            test_dict["runtimes"].insert(0, test.wall_time)
            test_dict["dates"].insert(0, suite.test_dir.rstrip("/"))

        #----------------------------------------------------------------------
        # move the output files into the web directory
        #----------------------------------------------------------------------
        # were any Backtrace files output (indicating a crash)
        suite.copy_backtrace(test)

        if args.make_benchmarks is None:
            shutil.copy(test.outfile, suite.full_web_dir)
            if os.path.isfile(test.errfile):
                shutil.copy(test.errfile, suite.full_web_dir)
                test.has_stderr = True
            if test.doComparison:
                try:
                    shutil.copy(test.comparison_outfile, suite.full_web_dir)
                except FileNotFoundError:
                    pass
            try:
                shutil.copy(f"{test.name}.analysis.out", suite.full_web_dir)
            except:
                pass

            if test.inputFile:
                shutil.copy(test.inputFile, "{}/{}.{}".format(
                    suite.full_web_dir, test.name, test.inputFile))

            if test.has_jobinfo:
                shutil.copy(job_info_file, "{}/{}.job_info".format(
                    suite.full_web_dir, test.name))

            if suite.sourceTree == "C_Src" and test.probinFile != "":
                shutil.copy(test.probinFile, "{}/{}.{}".format(
                    suite.full_web_dir, test.name, test.probinFile))

            for af in test.auxFiles:

                # strip out any sub-directory under build dir for the aux file
                # when copying
                shutil.copy(os.path.basename(af),
                            "{}/{}.{}".format(suite.full_web_dir,
                                              test.name, os.path.basename(af)))

            if not test.png_file is None:
                try:
                    shutil.copy(test.png_file, suite.full_web_dir)
                except OSError:
                    # visualization was not successful.  Reset image
                    test.png_file = None

            if not test.analysisRoutine == "":
                try:
                    shutil.copy(test.analysisOutputImage, suite.full_web_dir)
                except OSError:
                    suite.log.warn("unable to copy analysis image")
                    # analysis was not successful.  Reset the output image
                    test.analysisOutputImage = ""

        elif test.ignore_return_code == 1 or test.return_code == 0:
            if test.doComparison:
                shutil.copy(f"{test.name}.status", suite.full_web_dir)


        #----------------------------------------------------------------------
        # archive (or delete) the output
        #----------------------------------------------------------------------
        suite.log.log("archiving the output...")
        match_count = 0
        archived_file_list = []
        for pfile in os.listdir(output_dir):

            if (os.path.isdir(pfile) and
                re.match(f"{test.name}.*_(plt|chk)[0-9]+", pfile)):

                match_count += 1

                if suite.purge_output == 1 and not pfile == output_file:

                    # delete the plt/chk file
                    try:
                        shutil.rmtree(pfile)
                    except:
                        suite.log.warn(f"unable to remove {pfile}")

                elif suite.archive_output == 1:
                    # tar it up
                    try:
                        tarfilename = f"{pfile}.tgz"
                        tar = tarfile.open(tarfilename, "w:gz")
                        tar.add(f"{pfile}")
                        tar.close()
                        archived_file_list.append(tarfilename)

                    except:
                        suite.log.warn(f"unable to tar output file {pfile}")

                    else:
                        try:
                            shutil.rmtree(pfile)
                        except OSError:
                            suite.log.warn(f"unable to remove {pfile}")

        if suite.fail_on_no_output and match_count == 0:
            suite.log.fail("ERROR: test output could not be found!")


        #----------------------------------------------------------------------
        # write the report for this test
        #----------------------------------------------------------------------
        if args.make_benchmarks is None:
            suite.log.log("creating problem test report ...")
            report.report_single_test(suite, test, test_list)

        #----------------------------------------------------------------------
        # if test ran and passed, remove test directory if requested
        #----------------------------------------------------------------------
        test_successful = (test.return_code == 0 and test.analysis_successful and test.compare_successful)
        if (test.ignore_return_code == 1 or test_successful):
            if args.clean_testdir:
                # remove subdirectories
                suite.log.log("removing subdirectories from test directory...")
                for file_name in os.listdir(output_dir):
                    file_path = os.path.join(output_dir, file_name)
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)

                # remove archived plotfiles
                suite.log.log("removing compressed plotfiles from test directory...")
                for file_name in archived_file_list:
                    file_path = os.path.join(output_dir, file_name)
                    os.remove(file_path)

                # switch to the full test directory
                os.chdir(suite.full_test_dir)
            if args.delete_exe:
                suite.log.log("removing executable from test directory...")
                os.remove(executable)


    #--------------------------------------------------------------------------
    # Clean Cmake build and install directories if needed
    #--------------------------------------------------------------------------
    if suite.useCmake:
        suite.cmake_clean("AMReX", suite.amrex_dir)
        suite.cmake_clean(suite.suiteName, suite.source_dir)

    #--------------------------------------------------------------------------
    # jsonify and save runtimes
    #--------------------------------------------------------------------------
    file_path = suite.get_wallclock_file()
    with open(file_path, 'w') as json_file:
        json.dump(runtimes, json_file, indent=4)

    #--------------------------------------------------------------------------
    # parameter coverage
    #--------------------------------------------------------------------------
    if suite.reportCoverage:
        determine_coverage(suite)

    #--------------------------------------------------------------------------
    # write the report for this instance of the test suite
    #--------------------------------------------------------------------------
    suite.log.outdent()
    suite.log.skip()
    suite.log.bold("creating new test report...")
    num_failed = report.report_this_test_run(suite, args.make_benchmarks, args.note,
                                             update_time,
                                             test_list, args.input_file[0])

    # make sure that all of the files in the web directory are world readable
    for file in os.listdir(suite.full_web_dir):
        current_file = suite.full_web_dir + file

        if os.path.isfile(current_file):
            os.chmod(current_file, 0o644)

    # reset the branch to what it was originally
    suite.log.skip()
    suite.log.bold("reverting git branches/hashes")
    suite.log.indent()

    for k in suite.repos:
        if suite.repos[k].update or suite.repos[k].hash_wanted:
            suite.repos[k].git_back()

    suite.log.outdent()

    # For temporary run, return now without creating suite report.
    if args.do_temp_run:
        suite.delete_tempdirs()
        return num_failed

    # store an output file in the web directory that can be parsed easily by
    # external program
    name = "source"
    if suite.sourceTree in ["AMReX", "amrex"]:
        name = "AMReX"
    branch = ''
    if suite.repos[name].get_branch_name():
        branch = suite.repos[name].get_branch_name()

    with open("{}/suite.{}.status".format(suite.webTopDir, branch.replace("/", "_")), "w") as f:
        f.write("{}; num failed: {}; source hash: {}".format(
            suite.repos[name].name, num_failed, suite.repos[name].hash_current))


    #--------------------------------------------------------------------------
    # generate the master report for all test instances
    #--------------------------------------------------------------------------
    suite.log.skip()
    suite.log.bold("creating suite report...")
    report.report_all_runs(suite, active_test_list)

    # delete any temporary directories
    suite.delete_tempdirs()

    def email_developers():
        msg = email.message_from_string(suite.emailBody)
        msg['From'] = suite.emailFrom
        msg['To'] = ",".join(suite.emailTo)
        msg['Subject'] = suite.emailSubject

        server = smtplib.SMTP('localhost')
        server.sendmail(suite.emailFrom, suite.emailTo, msg.as_string())
        server.quit()

    if num_failed > 0 and suite.sendEmailWhenFail and not args.send_no_email:
        suite.log.skip()
        suite.log.bold("sending email...")
        email_developers()


    if suite.slack_post:
        suite.slack_post_it(f"> test complete, num failed = {num_failed}\n{suite.emailBody}")

    return num_failed


def parse_ssh_command():
    """
    Parse and validate SSH_ORIGINAL_COMMAND for restricted SSH key execution.
    
    Returns:
        List of validated command arguments or None if not in SSH context
    """
    ssh_cmd = os.environ.get('SSH_ORIGINAL_COMMAND')
    if not ssh_cmd:
        return None
    
    # Validate the command format: must be "regtest.py <command> [ini_file]"
    # where <command> is one of: submit, check, extract, www, setup
    # INI file is optional for www command
    valid_commands = ['submit', 'check', 'extract', 'www', 'setup']
    
    # Use regex to parse the command safely
    # Pattern: optional path/regtest.py followed by command and optional INI file
    pattern = r'^(?:.*/)?regtest\.py\s+(' + '|'.join(valid_commands) + r')(?:\s+([a-zA-Z0-9_\-./]+\.ini))?\s*$'
    match = re.match(pattern, ssh_cmd)
    
    if not match:
        print(f"ERROR: Invalid SSH command: {ssh_cmd}", file=sys.stderr)
        print(f"Valid format: regtest.py <command> [ini_file]", file=sys.stderr)
        print(f"Where <command> is one of: {', '.join(valid_commands)}", file=sys.stderr)
        print(f"INI file is required for submit, check, extract, setup; optional for www", file=sys.stderr)
        sys.exit(1)
    
    command = match.group(1)
    ini_file = match.group(2)
    
    # Check if INI file is required but not provided
    if command in ['submit', 'check', 'extract', 'setup'] and not ini_file:
        print(f"ERROR: INI file is required for command '{command}'", file=sys.stderr)
        sys.exit(1)
    
    # Security check: ensure INI file path doesn't contain suspicious patterns (if provided)
    if ini_file and ('..' in ini_file or ini_file.startswith('/')):
        print(f"ERROR: Invalid INI file path: {ini_file}", file=sys.stderr)
        print("INI file must be a relative path without '..'", file=sys.stderr)
        sys.exit(1)
    
    # Construct the validated argument list
    if ini_file:
        return [command, ini_file]
    else:
        return [command]


def change_to_ini_directory(ini_file):
    """
    Change to the directory containing the INI file for proper relative path resolution.
    
    Args:
        ini_file: Path to the INI file
    """
    ini_path = os.path.abspath(ini_file)
    if not os.path.exists(ini_path):
        print(f"ERROR: INI file not found: {ini_path}", file=sys.stderr)
        sys.exit(1)
    
    ini_dir = os.path.dirname(ini_path)
    if ini_dir:
        os.chdir(ini_dir)
        # Update the ini_file to just the filename since we're now in its directory
        return os.path.basename(ini_path)
    return ini_file


if __name__ == "__main__":
    # Check if running via restricted SSH
    ssh_args = parse_ssh_command()
    
    if ssh_args:
        # Running via SSH - use parsed and validated arguments
        args = ssh_args
        print(f"Running via SSH with command: {' '.join(args)}")
        
        # Change to the directory containing the INI file
        if len(args) > 1:
            args[1] = change_to_ini_directory(args[1])
    else:
        # Normal execution - use command line arguments
        args = sys.argv[1:]
    
    n = test_suite(args)
    sys.exit(n)
