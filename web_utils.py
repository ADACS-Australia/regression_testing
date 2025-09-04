#!/usr/bin/env python3
"""
Utility functions for web report generation from regression test data.
"""

import os
import re
import subprocess
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import warnings


def get_quokka_version(work_dir: str, folder_name: str, timestamp: str) -> Optional[str]:
    """
    Extract the Quokka git commit hash for a given timestamp.
    
    Args:
        work_dir: Base work directory
        folder_name: Folder name (e.g., 'A', 'B', 'C', 'reference')
        timestamp: Timestamp string
        
    Returns:
        6-character git commit hash or None if not found
    """
    quokka_path = os.path.join(work_dir, folder_name, 'performance_test', timestamp, 'quokka')
    
    if not os.path.exists(quokka_path):
        return None
    
    try:
        # Get the short commit hash (6 characters)
        result = subprocess.run(
            ['git', 'rev-parse', '--short=6', 'HEAD'],
            cwd=quokka_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def extract_gpu_count_from_script(script_path: str) -> Optional[int]:
    """
    Extract GPU count from a SLURM job script by parsing SBATCH directives.
    
    Args:
        script_path: Path to the job script file
        
    Returns:
        Number of GPUs per task, or None if not found
    """
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            
        # Look for --gpus-per-task directive
        match = re.search(r'#SBATCH\s+--gpus-per-task[=\s]+(\d+)', content)
        if match:
            return int(match.group(1))
            
        # Alternative: look for --gres=gpu:X
        match = re.search(r'#SBATCH\s+--gres=gpu:(\d+)', content)
        if match:
            return int(match.group(1))
            
        # If no GPU directives found, assume CPU-only (0 GPUs)
        return 0
        
    except Exception as e:
        warnings.warn(f"Could not read script {script_path}: {e}")
        return None


def calculate_zone_updates_per_gpu(
    zone_updates_per_sec: float,
    n_mpi_processes: int,
    gpus_per_task: int
) -> float:
    """
    Calculate zone updates per second per GPU.
    
    Args:
        zone_updates_per_sec: Total zone updates per second
        n_mpi_processes: Number of MPI processes (tasks)
        gpus_per_task: Number of GPUs per task
        
    Returns:
        Zone updates per second per GPU
    """
    if gpus_per_task > 0:
        total_gpus = n_mpi_processes * gpus_per_task
        return zone_updates_per_sec / total_gpus
    else:
        # CPU-only run, return per-process performance
        return zone_updates_per_sec / n_mpi_processes


def load_parquet_data(results_dir: str) -> Dict[str, Optional[pd.DataFrame]]:
    """
    Load all parquet files from a results directory.
    
    Args:
        results_dir: Path to the results directory
        
    Returns:
        Dictionary with keys 'submission', 'output', 'status' containing DataFrames or None
    """
    data = {}
    
    # Define expected parquet files
    files = {
        'submission': 'job_submission.parquet',
        'output': 'job_output.parquet',
        'status': 'job_exit_status.parquet'
    }
    
    for key, filename in files.items():
        filepath = os.path.join(results_dir, filename)
        if os.path.exists(filepath):
            try:
                data[key] = pd.read_parquet(filepath)
            except Exception as e:
                warnings.warn(f"Could not read {filename}: {e}")
                data[key] = None
        else:
            data[key] = None
            
    return data


def extract_performance_data(
    folder_path: str,
    timestamp: str
) -> Optional[pd.DataFrame]:
    """
    Extract performance data from a single timestamp folder.
    
    Args:
        folder_path: Path to the folder (e.g., '/work/A')
        timestamp: Timestamp string (e.g., '20250830231131')
        
    Returns:
        DataFrame with performance metrics or None if data is incomplete
    """
    # Build path to results directory
    # Check if folder_path already contains 'performance_test'
    if folder_path.endswith('performance_test'):
        results_dir = os.path.join(folder_path, timestamp, 'results')
    else:
        results_dir = os.path.join(folder_path, 'performance_test', timestamp, 'results')
    
    if not os.path.exists(results_dir):
        warnings.warn(f"Results directory not found: {results_dir}")
        return None
        
    # Load parquet data
    data = load_parquet_data(results_dir)
    
    # Check if we have the minimum required data
    if data['submission'] is None:
        warnings.warn(f"No submission data for {folder_path}/{timestamp}")
        return None
        
    # Initialize results DataFrame
    results = []
    
    # Get list of job scripts from subdirectories
    job_scripts = []
    for subdir in os.listdir(results_dir):
        subdir_path = os.path.join(results_dir, subdir)
        if os.path.isdir(subdir_path):
            # Look for .sh files in the subdirectory
            for f in os.listdir(subdir_path):
                if f.endswith('.sh'):
                    job_scripts.append(os.path.join(subdir, f))
    
    for script_file in job_scripts:
        script_path = os.path.join(results_dir, script_file)
        
        # Extract job info from script filename
        # Expected format: test_name_nX.sh or test_name_nX_JobID_XXXX.sh
        match = re.search(r'(.+?)_n(\d+)', script_file)
        if not match:
            continue
            
        test_name = match.group(1)
        n_cores = int(match.group(2))
        
        # Extract GPU count
        gpus_per_task = extract_gpu_count_from_script(script_path)
        if gpus_per_task is None:
            gpus_per_task = 0  # Default to CPU-only
        
        # Try to find job_id from output file in same directory
        job_id = None
        script_dir = os.path.dirname(script_path)
        for f in os.listdir(script_dir):
            if f.endswith('.out') and 'JobID_' in f:
                id_match = re.search(r'JobID_(\d+)', f)
                if id_match:
                    job_id = id_match.group(1)
                    break
                    
        # Find corresponding job in submission data
        job_info = {
            'test_name': test_name,
            'cores': n_cores,  # Changed from 'n_cores' to 'cores' to match expected field name
            'gpus_per_task': gpus_per_task,
            'timestamp': timestamp,
            'folder': os.path.basename(folder_path.rstrip('/'))
        }
        
        # Try to get performance data if available
        if data['output'] is not None and not data['output'].empty:
            # Try to match by job_id first, then fall back to n_mpi_processes
            output_row = None
            if job_id and 'job_id' in data['output'].columns:
                matches = data['output'][data['output']['job_id'] == job_id]
                if not matches.empty:
                    output_row = matches.iloc[0]
            
            # Fall back to matching by n_mpi_processes if no job_id match
            if output_row is None:
                matches = data['output'][data['output']['n_mpi_processes'].astype(str) == str(n_cores)]
                if not matches.empty:
                    # For multiple matches with same core count, try to pick one not already used
                    # This is a heuristic approach when job_id matching fails
                    output_row = matches.iloc[0]
            
            if output_row is not None:
                # Extract performance metrics
                if 'zone_update_megaupdates_per_second' in output_row:
                    zone_updates_per_sec = float(output_row['zone_update_megaupdates_per_second']) * 1e6
                elif 'zone_update' in output_row:
                    # Handle dict format
                    zone_data = output_row['zone_update']
                    if isinstance(zone_data, dict) and 'megaupdates_per_second' in zone_data:
                        zone_updates_per_sec = float(zone_data['megaupdates_per_second']) * 1e6
                    else:
                        zone_updates_per_sec = None
                else:
                    zone_updates_per_sec = None
                    
                if zone_updates_per_sec:
                    job_info['zone_updates_per_sec'] = zone_updates_per_sec
                    zone_updates_per_gpu = calculate_zone_updates_per_gpu(
                        zone_updates_per_sec, n_cores, gpus_per_task
                    )
                    job_info['zone_updates_per_sec_per_gpu'] = zone_updates_per_gpu
                    
                # Get elapsed time
                if 'elapse_time' in output_row:
                    job_info['elapsed_time'] = float(output_row['elapse_time'])
                    
        # Determine job status
        # If we have performance data, the job must be completed
        if job_info.get('zone_updates_per_sec_per_gpu') and job_info['zone_updates_per_sec_per_gpu'] != 'N/A':
            job_info['status'] = 'COMPLETED'
        elif data['status'] is not None and not data['status'].empty and job_id:
            # Check exit status data if available
            status_matches = data['status'][data['status']['job_id'] == job_id]
            if not status_matches.empty:
                job_info['status'] = status_matches.iloc[0].get('state', 'UNKNOWN')
            else:
                job_info['status'] = 'PENDING'
        else:
            job_info['status'] = 'PENDING'
            
        results.append(job_info)
        
    if results:
        return pd.DataFrame(results)
    else:
        return None


def aggregate_folder_data(work_dir: str, folder_name: str) -> pd.DataFrame:
    """
    Aggregate performance data from all timestamps in a folder.
    
    Args:
        work_dir: Base work directory
        folder_name: Name of the folder (e.g., 'A', 'reference')
        
    Returns:
        DataFrame with all performance data for the folder
    """
    folder_path = os.path.join(work_dir, folder_name)
    perf_test_dir = os.path.join(folder_path, 'performance_test')
    
    if not os.path.exists(perf_test_dir):
        warnings.warn(f"No performance_test directory in {folder_name}")
        return pd.DataFrame()
        
    # Get all timestamp directories
    timestamps = [d for d in os.listdir(perf_test_dir) 
                  if os.path.isdir(os.path.join(perf_test_dir, d)) and d.isdigit()]
    timestamps.sort()
    
    all_data = []
    for timestamp in timestamps:
        df = extract_performance_data(perf_test_dir, timestamp)
        if df is not None:
            all_data.append(df)
            
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame()


def get_reference_data(work_dir: str) -> Optional[pd.DataFrame]:
    """
    Get the latest reference data if available.
    
    Args:
        work_dir: Base work directory
        
    Returns:
        DataFrame with reference performance data or None
    """
    ref_data = aggregate_folder_data(work_dir, 'reference')
    
    if ref_data.empty:
        return None
        
    # Get the latest timestamp
    latest_timestamp = ref_data['timestamp'].max()
    return ref_data[ref_data['timestamp'] == latest_timestamp]


def get_comparison_data(
    current_data: pd.DataFrame,
    folder_name: str,
    work_dir: str
) -> Dict[str, pd.DataFrame]:
    """
    Get comparison data for plotting.
    
    Args:
        current_data: Current timestamp's data
        folder_name: Name of the current folder
        work_dir: Base work directory
        
    Returns:
        Dictionary with 'baseline' and 'reference' DataFrames (may be empty)
    """
    comparisons = {}
    
    # Get all data for this folder
    all_folder_data = aggregate_folder_data(work_dir, folder_name)
    
    if not all_folder_data.empty:
        # Get earliest timestamp for baseline comparison
        earliest_timestamp = all_folder_data['timestamp'].min()
        current_timestamp = current_data['timestamp'].iloc[0] if not current_data.empty else None
        
        if current_timestamp and current_timestamp != earliest_timestamp:
            comparisons['baseline'] = all_folder_data[all_folder_data['timestamp'] == earliest_timestamp]
        else:
            comparisons['baseline'] = pd.DataFrame()
    else:
        comparisons['baseline'] = pd.DataFrame()
        
    # Get reference data if this isn't the reference folder
    if folder_name != 'reference':
        ref_data = get_reference_data(work_dir)
        comparisons['reference'] = ref_data if ref_data is not None else pd.DataFrame()
    else:
        comparisons['reference'] = pd.DataFrame()
        
    return comparisons


def format_missing_data_message(data: Dict[str, Optional[pd.DataFrame]]) -> str:
    """
    Create a user-friendly message about missing data.
    
    Args:
        data: Dictionary with parquet DataFrames
        
    Returns:
        HTML string with status message
    """
    messages = []
    
    # Check for both possible key names (submission/job_submission, etc.)
    submission = data.get('submission')
    if submission is None:
        submission = data.get('job_submission')
    
    output = data.get('output')
    if output is None:
        output = data.get('job_output')
    
    status = data.get('status')
    if status is None:
        status = data.get('job_exit_status')
    
    if submission is None:
        messages.append("No jobs have been submitted yet.")
    elif output is None:
        messages.append("Jobs are submitted but not yet complete (no output data).")
    elif status is None:
        messages.append("Job status information is not available.")
        
    if messages:
        return f"<div class='warning'>Note: {' '.join(messages)}</div>"
    else:
        return ""


if __name__ == "__main__":
    # Test the utilities
    print("Testing web utilities...")
    
    # Test GPU extraction from a sample script
    test_dir = "/home/agray/src/cas/quokka/work/A/performance_test/20250830231131/results"
    if os.path.exists(test_dir):
        scripts = [f for f in os.listdir(test_dir) if f.endswith('.sh')]
        if scripts:
            script_path = os.path.join(test_dir, scripts[0])
            gpu_count = extract_gpu_count_from_script(script_path)
            print(f"GPU count from {scripts[0]}: {gpu_count}")
            
    # Test data aggregation
    work_dir = "/home/agray/src/cas/quokka/work"
    for folder in ['A', 'B', 'C', 'reference']:
        df = aggregate_folder_data(work_dir, folder)
        if not df.empty:
            print(f"\n{folder}: Found {len(df)} test results across {df['timestamp'].nunique()} timestamps")
            if 'zone_updates_per_gpu' in df.columns:
                print(f"  Performance range: {df['zone_updates_per_gpu'].min():.2e} - {df['zone_updates_per_gpu'].max():.2e} updates/sec/GPU")