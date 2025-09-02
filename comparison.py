#!/usr/bin/env python
"""
Comparison utilities for regression testing.
Provides functions to compare performance between timestamps and against reference data.
"""

import os
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from pathlib import Path


def get_baseline_data(folder_path: str, current_timestamp: str) -> Optional[Dict[str, List[Dict]]]:
    """
    Get the earliest timestamp data from a folder to use as baseline.
    
    Args:
        folder_path: Path to the folder
        current_timestamp: Current timestamp to exclude from baseline
        
    Returns:
        Dictionary mapping test names to their baseline performance data
    """
    from web_utils import extract_performance_data
    
    perf_test_dir = os.path.join(folder_path, 'performance_test')
    if not os.path.exists(perf_test_dir):
        return None
    
    # Get all timestamps and sort to find earliest
    timestamps = [d for d in os.listdir(perf_test_dir) 
                  if os.path.isdir(os.path.join(perf_test_dir, d)) and d.isdigit()]
    
    if not timestamps:
        return None
    
    timestamps.sort()  # Earliest first
    
    # Find the earliest timestamp with data (that's not the current one)
    for ts in timestamps:
        if ts == current_timestamp:
            continue
            
        # Try to get data for this timestamp
        data_df = extract_performance_data(folder_path, ts)
        if data_df is not None and not data_df.empty:
            # Convert to dict format grouped by test name
            baseline_data = {}
            for _, row in data_df.iterrows():
                test_name = row.get('test_name', 'unknown')
                if test_name not in baseline_data:
                    baseline_data[test_name] = []
                
                if pd.notna(row.get('zone_updates_per_gpu')):
                    entry = {
                        'cores': row.get('n_cores', 0),
                        'gpus_per_task': row.get('gpus_per_task', 0),
                        'zone_updates_per_sec_per_gpu': row.get('zone_updates_per_gpu'),
                        'elapsed_time': row.get('elapsed_time'),
                        'timestamp': ts
                    }
                    baseline_data[test_name].append(entry)
            
            if baseline_data:
                return baseline_data
    
    return None


def get_latest_reference_data(work_dir: str) -> Optional[Dict[str, List[Dict]]]:
    """
    Get the latest timestamp data from the reference folder.
    
    Args:
        work_dir: Base work directory
        
    Returns:
        Dictionary mapping test names to their reference performance data
    """
    from web_utils import extract_performance_data
    
    reference_path = os.path.join(work_dir, 'reference')
    if not os.path.exists(reference_path):
        return None
    
    perf_test_dir = os.path.join(reference_path, 'performance_test')
    if not os.path.exists(perf_test_dir):
        return None
    
    # Get all timestamps and sort to find latest
    timestamps = [d for d in os.listdir(perf_test_dir) 
                  if os.path.isdir(os.path.join(perf_test_dir, d)) and d.isdigit()]
    
    if not timestamps:
        return None
    
    timestamps.sort(reverse=True)  # Latest first
    
    # Get data from the latest timestamp
    for ts in timestamps:
        data_df = extract_performance_data(reference_path, ts)
        if data_df is not None and not data_df.empty:
            # Convert to dict format grouped by test name
            reference_data = {}
            for _, row in data_df.iterrows():
                test_name = row.get('test_name', 'unknown')
                if test_name not in reference_data:
                    reference_data[test_name] = []
                
                if pd.notna(row.get('zone_updates_per_gpu')):
                    entry = {
                        'cores': row.get('n_cores', 0),
                        'gpus_per_task': row.get('gpus_per_task', 0),
                        'zone_updates_per_sec_per_gpu': row.get('zone_updates_per_gpu'),
                        'elapsed_time': row.get('elapsed_time'),
                        'timestamp': ts
                    }
                    reference_data[test_name].append(entry)
            
            if reference_data:
                return reference_data
    
    return None


def calculate_performance_difference(current: float, baseline: float) -> Dict[str, Any]:
    """
    Calculate the performance difference between current and baseline.
    
    Args:
        current: Current performance value
        baseline: Baseline performance value
        
    Returns:
        Dictionary with absolute and percentage differences
    """
    absolute_diff = current - baseline
    if baseline != 0:
        percentage_diff = ((current - baseline) / baseline) * 100
    else:
        percentage_diff = 0
    
    return {
        'absolute': absolute_diff,
        'percentage': percentage_diff,
        'improved': absolute_diff > 0,
        'degraded': absolute_diff < 0
    }


def compare_performance_entries(
    current_data: List[Dict],
    baseline_data: Optional[Dict[str, List[Dict]]] = None,
    reference_data: Optional[Dict[str, List[Dict]]] = None
) -> List[Dict]:
    """
    Compare current performance data against baseline and reference.
    
    Args:
        current_data: List of current performance entries
        baseline_data: Optional baseline data grouped by test name
        reference_data: Optional reference data grouped by test name
        
    Returns:
        Enhanced list of entries with comparison information
    """
    enhanced_entries = []
    
    for entry in current_data:
        enhanced_entry = entry.copy()
        test_name = entry.get('test_name', 'unknown')
        cores = entry.get('cores', 0)
        current_perf = entry.get('zone_updates_per_sec_per_gpu')
        
        # Skip if no performance data
        if not current_perf or current_perf == 'N/A':
            enhanced_entries.append(enhanced_entry)
            continue
        
        # Convert to float if needed
        if isinstance(current_perf, str):
            try:
                current_perf = float(current_perf)
            except:
                enhanced_entries.append(enhanced_entry)
                continue
        
        # Compare with baseline
        if baseline_data and test_name in baseline_data:
            # Find matching configuration (same cores)
            for baseline_entry in baseline_data[test_name]:
                if baseline_entry['cores'] == cores:
                    baseline_perf = baseline_entry['zone_updates_per_sec_per_gpu']
                    if baseline_perf and baseline_perf != 'N/A':
                        diff = calculate_performance_difference(current_perf, baseline_perf)
                        enhanced_entry['baseline_comparison'] = {
                            'value': baseline_perf,
                            'timestamp': baseline_entry.get('timestamp'),
                            **diff
                        }
                    break
        
        # Compare with reference
        if reference_data and test_name in reference_data:
            # Find matching configuration (same cores)
            for ref_entry in reference_data[test_name]:
                if ref_entry['cores'] == cores:
                    ref_perf = ref_entry['zone_updates_per_sec_per_gpu']
                    if ref_perf and ref_perf != 'N/A':
                        diff = calculate_performance_difference(current_perf, ref_perf)
                        enhanced_entry['reference_comparison'] = {
                            'value': ref_perf,
                            'timestamp': ref_entry.get('timestamp'),
                            **diff
                        }
                    break
        
        enhanced_entries.append(enhanced_entry)
    
    return enhanced_entries


def format_comparison_text(comparison: Dict[str, Any], comparison_type: str = "baseline") -> str:
    """
    Format comparison data as human-readable text.
    
    Args:
        comparison: Comparison dictionary with difference data
        comparison_type: Type of comparison ("baseline" or "reference")
        
    Returns:
        Formatted HTML string showing the comparison
    """
    if not comparison:
        return ""
    
    percentage = comparison['percentage']
    abs_diff = comparison['absolute']
    
    # Determine color and symbol
    if comparison['improved']:
        color = "green"
        symbol = "↑"
    elif comparison['degraded']:
        color = "red"
        symbol = "↓"
    else:
        color = "gray"
        symbol = "="
    
    # Format the comparison text
    if abs(percentage) < 0.01:
        perf_text = "~same"
    else:
        perf_text = f"{symbol} {abs(percentage):.1f}%"
    
    label = "vs baseline" if comparison_type == "baseline" else "vs reference"
    
    return f'<span style="color: {color}; font-weight: bold;">{perf_text}</span> <span style="color: #666; font-size: 0.9em;">({label})</span>'


def generate_comparison_summary(enhanced_entries: List[Dict]) -> Dict[str, Any]:
    """
    Generate a summary of performance comparisons.
    
    Args:
        enhanced_entries: List of entries with comparison data
        
    Returns:
        Dictionary with summary statistics
    """
    summary = {
        'total_tests': 0,
        'baseline_comparisons': 0,
        'reference_comparisons': 0,
        'improvements': 0,
        'degradations': 0,
        'max_improvement': None,
        'max_degradation': None
    }
    
    for entry in enhanced_entries:
        if entry.get('zone_updates_per_sec_per_gpu') and entry['zone_updates_per_sec_per_gpu'] != 'N/A':
            summary['total_tests'] += 1
            
            # Check baseline comparison
            if 'baseline_comparison' in entry:
                summary['baseline_comparisons'] += 1
                pct = entry['baseline_comparison']['percentage']
                
                if entry['baseline_comparison']['improved']:
                    summary['improvements'] += 1
                    if summary['max_improvement'] is None or pct > summary['max_improvement']['percentage']:
                        summary['max_improvement'] = {
                            'test': entry['test_name'],
                            'cores': entry['cores'],
                            'percentage': pct
                        }
                elif entry['baseline_comparison']['degraded']:
                    summary['degradations'] += 1
                    if summary['max_degradation'] is None or pct < summary['max_degradation']['percentage']:
                        summary['max_degradation'] = {
                            'test': entry['test_name'],
                            'cores': entry['cores'],
                            'percentage': pct
                        }
            
            # Count reference comparisons
            if 'reference_comparison' in entry:
                summary['reference_comparisons'] += 1
    
    return summary


if __name__ == "__main__":
    # Test the comparison functions
    print("Testing comparison utilities...")
    
    # Test data
    current = [
        {'test_name': 'test1', 'cores': 2, 'zone_updates_per_sec_per_gpu': 1.1e7},
        {'test_name': 'test1', 'cores': 4, 'zone_updates_per_sec_per_gpu': 9.5e6},
    ]
    
    baseline = {
        'test1': [
            {'cores': 2, 'zone_updates_per_sec_per_gpu': 1.0e7, 'timestamp': '20250830000000'},
            {'cores': 4, 'zone_updates_per_sec_per_gpu': 1.0e7, 'timestamp': '20250830000000'},
        ]
    }
    
    # Test comparison
    enhanced = compare_performance_entries(current, baseline)
    
    print("\nEnhanced entries:")
    for entry in enhanced:
        print(f"  Test: {entry['test_name']}, Cores: {entry['cores']}")
        if 'baseline_comparison' in entry:
            comp = entry['baseline_comparison']
            print(f"    Baseline: {comp['percentage']:.1f}% {'better' if comp['improved'] else 'worse'}")
    
    # Test summary
    summary = generate_comparison_summary(enhanced)
    print(f"\nSummary: {summary}")
    
    print("\nComparison utilities tested successfully!")