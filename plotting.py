#!/usr/bin/env python
"""
Plotting utilities for regression testing web reports.
Creates static plots using matplotlib for performance visualization.
"""

import os
import io
import base64
from typing import List, Dict, Optional, Tuple, Any
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import numpy as np


def create_performance_plot(data_entries: List[Dict], 
                          title: str = "Performance Scaling",
                          reference_data: Optional[List[Dict]] = None) -> str:
    """
    Create a performance plot showing zone updates/sec/GPU vs cores.
    
    Args:
        data_entries: List of dictionaries with performance data
        title: Plot title
        reference_data: Optional reference data for comparison
        
    Returns:
        HTML string containing the embedded base64 image
    """
    if not data_entries:
        return '<div style="padding: 20px; text-align: center; color: #666;">No performance data available</div>'
    
    # Filter entries with actual performance data
    valid_entries = [e for e in data_entries if e.get('zone_updates_per_sec_per_gpu') and e['zone_updates_per_sec_per_gpu'] != 'N/A']
    
    if not valid_entries:
        return '<div style="padding: 20px; text-align: center; color: #666;">No completed runs with performance data</div>'
    
    # Group data by test name
    test_groups = {}
    for entry in valid_entries:
        test_name = entry['test_name']
        if test_name not in test_groups:
            test_groups[test_name] = []
        test_groups[test_name].append(entry)
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Color palette for different tests
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Add traces for each test
    for i, (test_name, entries) in enumerate(test_groups.items()):
        # Sort by number of cores
        entries.sort(key=lambda x: x['cores'])
        
        cores = [e['cores'] for e in entries]
        performance = [float(e['zone_updates_per_sec_per_gpu']) for e in entries]
        
        # Always use scatter points without lines to avoid misleading connections
        ax.loglog(cores, performance, 
                  marker='o', markersize=8, linestyle='none',
                  color=colors[i % len(colors)], 
                  label=test_name)
    
    # Add reference data if provided
    if reference_data:
        valid_ref = [e for e in reference_data if e.get('zone_updates_per_sec_per_gpu') and e['zone_updates_per_sec_per_gpu'] != 'N/A']
        if valid_ref:
            ref_groups = {}
            for entry in valid_ref:
                test_name = entry['test_name']
                if test_name not in ref_groups:
                    ref_groups[test_name] = []
                ref_groups[test_name].append(entry)
            
            for test_name, entries in ref_groups.items():
                entries.sort(key=lambda x: x['cores'])
                cores = [e['cores'] for e in entries]
                performance = [float(e['zone_updates_per_sec_per_gpu']) for e in entries]
                
                ax.loglog(cores, performance,
                         marker='D', markersize=6, linestyle='none',
                         alpha=0.7,
                         label=f"{test_name} (reference)")
    
    # Update layout
    ax.set_xlabel('Number of Cores', fontsize=12)
    ax.set_ylabel('Zone Updates/sec/GPU', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, which="both", ls="-", alpha=0.2)
    ax.legend(loc='lower left', fontsize=10)
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f'<img src="data:image/png;base64,{img_base64}" style="max-width: 100%; height: auto;" alt="{title}">'


def create_comparison_plot(timestamps_data: Dict[str, List[Dict]], 
                         folder_name: str) -> str:
    """
    Create a comparison plot between multiple timestamps in the same folder.
    
    Args:
        timestamps_data: Dictionary mapping timestamp to list of performance entries
        folder_name: Name of the folder being compared
        
    Returns:
        HTML string containing the embedded base64 image
    """
    if not timestamps_data:
        return '<div style="padding: 20px; text-align: center; color: #666;">No data available for comparison</div>'
    
    # Create subplots for different test types if they exist
    all_test_names = set()
    for entries in timestamps_data.values():
        for entry in entries:
            if entry.get('zone_updates_per_sec_per_gpu') and entry['zone_updates_per_sec_per_gpu'] != 'N/A':
                all_test_names.add(entry['test_name'])
    
    if not all_test_names:
        return '<div style="padding: 20px; text-align: center; color: #666;">No completed runs for comparison</div>'
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Color palette for different timestamps
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Line styles for different tests
    line_styles = ['-', '--', '-.', ':']
    
    # Sort timestamps for consistent ordering
    sorted_timestamps = sorted(timestamps_data.keys())
    
    # Plot each timestamp's data
    plot_handles = []
    for t_idx, timestamp in enumerate(sorted_timestamps):
        entries = timestamps_data[timestamp]
        valid_entries = [e for e in entries if e.get('zone_updates_per_sec_per_gpu') and e['zone_updates_per_sec_per_gpu'] != 'N/A']
        
        if not valid_entries:
            continue
        
        # Group by test name
        test_groups = {}
        for entry in valid_entries:
            test_name = entry['test_name']
            if test_name not in test_groups:
                test_groups[test_name] = []
            test_groups[test_name].append(entry)
        
        # Format timestamp for display
        ts_display = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[8:10]}:{timestamp[10:12]}"
        
        # Plot each test
        for test_idx, (test_name, test_entries) in enumerate(test_groups.items()):
            test_entries.sort(key=lambda x: x['cores'])
            cores = [e['cores'] for e in test_entries]
            performance = [float(e['zone_updates_per_sec_per_gpu']) for e in test_entries]
            
            handle = ax.loglog(cores, performance,
                     marker='o', markersize=6, linestyle='none',
                     color=colors[t_idx % len(colors)],
                     label=f"{test_name} ({ts_display})")
            plot_handles.extend(handle)
    
    # Update layout
    ax.set_xlabel('Number of Cores', fontsize=12)
    ax.set_ylabel('Zone Updates/sec/GPU', fontsize=12)
    ax.set_title(f'Performance Comparison - {folder_name}', fontsize=14, fontweight='bold')
    ax.grid(True, which="both", ls="-", alpha=0.2)
    
    # Position legend outside plot area
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f'<img src="data:image/png;base64,{img_base64}" style="max-width: 100%; height: auto;" alt="Performance Comparison - {folder_name}">'


def create_trend_plot(historical_data: List[Tuple[str, List[Dict]]], 
                     test_filter: Optional[str] = None) -> str:
    """
    Create a trend plot showing performance over time for a specific test configuration.
    
    Args:
        historical_data: List of (timestamp, entries) tuples
        test_filter: Optional test name to filter for
        
    Returns:
        HTML string containing the embedded base64 image
    """
    if not historical_data:
        return '<div style="padding: 20px; text-align: center; color: #666;">No historical data available</div>'
    
    # Build time series data
    trend_data = {}  # {(test_name, cores): [(timestamp, performance), ...]}
    
    for timestamp, entries in historical_data:
        for entry in entries:
            if entry.get('zone_updates_per_sec_per_gpu') and entry['zone_updates_per_sec_per_gpu'] != 'N/A':
                if test_filter and entry['test_name'] != test_filter:
                    continue
                
                key = (entry['test_name'], entry['cores'])
                if key not in trend_data:
                    trend_data[key] = []
                
                # Parse timestamp to datetime string
                ts_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[8:10]}:{timestamp[10:12]}"
                perf = float(entry['zone_updates_per_sec_per_gpu'])
                trend_data[key].append((ts_str, timestamp, perf))
    
    if not trend_data:
        return '<div style="padding: 20px; text-align: center; color: #666;">No trend data available</div>'
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Color palette
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Plot each configuration
    for i, ((test_name, cores), data_points) in enumerate(trend_data.items()):
        # Sort by timestamp
        data_points.sort(key=lambda x: x[1])
        
        timestamps = [dp[0] for dp in data_points]
        performance = [dp[2] for dp in data_points]
        
        ax.semilogy(range(len(timestamps)), performance,
                   marker='o', markersize=8, linewidth=2,
                   color=colors[i % len(colors)],
                   label=f"{test_name} ({cores} cores)")
        
        # Set x-tick labels to timestamps
        if i == 0:  # Only set once
            ax.set_xticks(range(len(timestamps)))
            ax.set_xticklabels(timestamps, rotation=45, ha='right')
    
    # Update layout
    title = f"Performance Trend - {test_filter}" if test_filter else "Performance Trends"
    ax.set_xlabel('Timestamp', fontsize=12)
    ax.set_ylabel('Zone Updates/sec/GPU', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, which="both", ls="-", alpha=0.2)
    
    # Position legend outside plot area
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f'<img src="data:image/png;base64,{img_base64}" style="max-width: 100%; height: auto;" alt="{title}">'


def create_weak_scaling_plot(data_entries: List[Dict], baseline_cores: int = 1) -> str:
    """
    Create a weak scaling efficiency plot.
    
    Args:
        data_entries: List of dictionaries with performance data
        baseline_cores: Number of cores to use as baseline (default: 1)
        
    Returns:
        HTML string containing the embedded base64 image
    """
    if not data_entries:
        return '<div style="padding: 20px; text-align: center; color: #666;">No data available for weak scaling analysis</div>'
    
    # Filter and group data
    valid_entries = [e for e in data_entries if e.get('zone_updates_per_sec_per_gpu') and e['zone_updates_per_sec_per_gpu'] != 'N/A']
    
    if not valid_entries:
        return '<div style="padding: 20px; text-align: center; color: #666;">No completed runs for weak scaling analysis</div>'
    
    # Group by test name
    test_groups = {}
    for entry in valid_entries:
        test_name = entry['test_name']
        if test_name not in test_groups:
            test_groups[test_name] = []
        test_groups[test_name].append(entry)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Add ideal scaling line
    max_cores = max(e['cores'] for e in valid_entries)
    ideal_cores = [1, max_cores]
    ideal_efficiency = [100, 100]
    
    ax.semilogx(ideal_cores, ideal_efficiency,
                linestyle='--', linewidth=2, color='black',
                label='Ideal Scaling')
    
    # Calculate and plot efficiency for each test
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for i, (test_name, entries) in enumerate(test_groups.items()):
        entries.sort(key=lambda x: x['cores'])
        
        # Find baseline performance
        baseline_entry = next((e for e in entries if e['cores'] == baseline_cores), None)
        if not baseline_entry:
            # Use smallest core count as baseline
            baseline_entry = min(entries, key=lambda x: x['cores'])
        
        baseline_perf = float(baseline_entry['zone_updates_per_sec_per_gpu'])
        baseline_cores_actual = baseline_entry['cores']
        
        cores = []
        efficiency = []
        
        for entry in entries:
            if entry['cores'] >= baseline_cores_actual:
                cores.append(entry['cores'])
                current_perf = float(entry['zone_updates_per_sec_per_gpu'])
                # Weak scaling efficiency: performance should remain constant
                eff = (current_perf / baseline_perf) * 100
                efficiency.append(eff)
        
        if cores and efficiency:
            ax.semilogx(cores, efficiency,
                       marker='o', markersize=8, linewidth=2,
                       color=colors[i % len(colors)],
                       label=test_name)
    
    # Update layout
    ax.set_xlabel('Number of Cores', fontsize=12)
    ax.set_ylabel('Efficiency (%)', fontsize=12)
    ax.set_title('Weak Scaling Efficiency', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 120)
    ax.grid(True, which="both", ls="-", alpha=0.2)
    ax.legend(loc='lower left', fontsize=10)
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f'<img src="data:image/png;base64,{img_base64}" style="max-width: 100%; height: auto;" alt="Weak Scaling Efficiency">'


if __name__ == "__main__":
    # Test the plotting functions with sample data
    sample_data = [
        {'test_name': 'test_hydro3d_blast', 'cores': 1, 'gpus_per_task': 1, 
         'zone_updates_per_sec_per_gpu': 1.3e7, 'elapsed_time': '2.89'},
        {'test_name': 'test_hydro3d_blast', 'cores': 2, 'gpus_per_task': 1, 
         'zone_updates_per_sec_per_gpu': 1.08e7, 'elapsed_time': '7.28'},
        {'test_name': 'test_hydro3d_blast', 'cores': 4, 'gpus_per_task': 1, 
         'zone_updates_per_sec_per_gpu': 9.8e6, 'elapsed_time': '18.14'},
        {'test_name': 'test_hydro3d_blast', 'cores': 8, 'gpus_per_task': 1, 
         'zone_updates_per_sec_per_gpu': 7.5e6, 'elapsed_time': '18.40'},
    ]
    
    # Test basic performance plot
    html = create_performance_plot(sample_data, "Test Performance Plot")
    print("Generated performance plot HTML (length: {} chars)".format(len(html)))
    
    # Test comparison plot
    timestamps_data = {
        '20250830231131': sample_data,
        '20250831123050': sample_data[:2]
    }
    html = create_comparison_plot(timestamps_data, "TestFolder")
    print("Generated comparison plot HTML (length: {} chars)".format(len(html)))
    
    # Test trend plot
    historical = [
        ('20250830231131', sample_data),
        ('20250831123050', sample_data[:2])
    ]
    html = create_trend_plot(historical, 'test_hydro3d_blast')
    print("Generated trend plot HTML (length: {} chars)".format(len(html)))
    
    # Test weak scaling plot
    html = create_weak_scaling_plot(sample_data)
    print("Generated weak scaling plot HTML (length: {} chars)".format(len(html)))
    
    print("\nAll plotting functions tested successfully!")