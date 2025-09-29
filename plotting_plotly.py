#!/usr/bin/env python
"""
Plotting utilities for regression testing web reports.
Creates interactive plots using plotly for performance visualization.
"""

import os
import json
from typing import List, Dict, Optional, Tuple, Any
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from pathlib import Path
import numpy as np


def create_performance_plot(data_entries: List[Dict], 
                          title: str = "Performance Scaling",
                          reference_data: Optional[List[Dict]] = None) -> str:
    """
    Create an interactive performance plot showing zone updates/sec/GPU vs cores.
    
    Args:
        data_entries: List of dictionaries with performance data
        title: Plot title
        reference_data: Optional reference data for comparison
        
    Returns:
        HTML string containing the embedded plotly plot
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
    fig = go.Figure()
    
    # Color palette for different tests
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Add traces for each test
    for i, (test_name, entries) in enumerate(test_groups.items()):
        # Sort by number of cores
        entries.sort(key=lambda x: x['cores'])
        
        cores = [e['cores'] for e in entries]
        performance = [float(e['zone_updates_per_sec_per_gpu']) for e in entries]
        gpu_counts = [e.get('gpus_per_task', 1) for e in entries]
        elapsed_times = [e.get('elapsed_time', 'N/A') for e in entries]
        
        # Create hover text with more information
        hover_text = []
        for j, e in enumerate(entries):
            hover_info = (
                f"Test: {test_name}<br>"
                f"Cores: {e['cores']}<br>"
                f"GPUs/Task: {gpu_counts[j]}<br>"
                f"Performance: {performance[j]:.2e} zone updates/sec/GPU<br>"
                f"Elapsed Time: {elapsed_times[j]}"
            )
            hover_text.append(hover_info)
        
        fig.add_trace(go.Scatter(
            x=cores,
            y=performance,
            mode='lines+markers',
            name=test_name,
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=8),
            hovertemplate='%{text}',
            text=hover_text
        ))
    
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
                
                fig.add_trace(go.Scatter(
                    x=cores,
                    y=performance,
                    mode='lines+markers',
                    name=f"{test_name} (reference)",
                    line=dict(dash='dash', width=2),
                    marker=dict(size=6, symbol='diamond'),
                    opacity=0.7
                ))
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Number of Cores",
        yaxis_title="Zone Updates/sec/GPU",
        xaxis=dict(
            type='log',
            gridcolor='lightgray',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            type='log',
            gridcolor='lightgray',
            showgrid=True,
            zeroline=False,
            exponentformat='e'
        ),
        hovermode='closest',
        template='plotly_white',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="bottom",
            y=0.01,
            xanchor="right",
            x=0.99
        ),
        height=500
    )
    
    # Convert to HTML
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'performance_plot',
            'height': 500,
            'width': 800,
            'scale': 2
        }
    }
    
    # Use 'cdn' with latest plotly version
    return fig.to_html(include_plotlyjs='https://cdn.plot.ly/plotly-latest.min.js', 
                      div_id="performance-plot", config=config)


def create_comparison_plot(timestamps_data: Dict[str, List[Dict]], 
                         folder_name: str) -> str:
    """
    Create a comparison plot between multiple timestamps in the same folder.
    
    Args:
        timestamps_data: Dictionary mapping timestamp to list of performance entries
        folder_name: Name of the folder being compared
        
    Returns:
        HTML string containing the embedded plotly plot
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
    
    fig = go.Figure()
    
    # Color palette for different timestamps
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Sort timestamps for consistent ordering
    sorted_timestamps = sorted(timestamps_data.keys())
    
    # Plot each timestamp's data
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
        
        # Plot each test
        for test_name, test_entries in test_groups.items():
            test_entries.sort(key=lambda x: x['cores'])
            cores = [e['cores'] for e in test_entries]
            performance = [float(e['zone_updates_per_sec_per_gpu']) for e in test_entries]
            
            # Format timestamp for display
            ts_display = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[8:10]}:{timestamp[10:12]}"
            
            fig.add_trace(go.Scatter(
                x=cores,
                y=performance,
                mode='lines+markers',
                name=f"{test_name} ({ts_display})",
                line=dict(color=colors[t_idx % len(colors)], width=2),
                marker=dict(size=8),
                legendgroup=timestamp
            ))
    
    # Update layout
    fig.update_layout(
        title=f"Performance Comparison - {folder_name}",
        xaxis_title="Number of Cores",
        yaxis_title="Zone Updates/sec/GPU",
        xaxis=dict(
            type='log',
            gridcolor='lightgray',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            type='log',
            gridcolor='lightgray',
            showgrid=True,
            zeroline=False,
            exponentformat='e'
        ),
        hovermode='closest',
        template='plotly_white',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.01
        ),
        height=600
    )
    
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
    }
    
    return fig.to_html(include_plotlyjs='https://cdn.plot.ly/plotly-latest.min.js', 
                      div_id="comparison-plot", config=config)


def create_trend_plot(historical_data: List[Tuple[str, List[Dict]]], 
                     test_filter: Optional[str] = None) -> str:
    """
    Create a trend plot showing performance over time for a specific test configuration.
    
    Args:
        historical_data: List of (timestamp, entries) tuples
        test_filter: Optional test name to filter for
        
    Returns:
        HTML string containing the embedded plotly plot
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
    
    fig = go.Figure()
    
    # Color palette
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Plot each configuration
    for i, ((test_name, cores), data_points) in enumerate(trend_data.items()):
        # Sort by timestamp
        data_points.sort(key=lambda x: x[1])
        
        timestamps = [dp[0] for dp in data_points]
        performance = [dp[2] for dp in data_points]
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=performance,
            mode='lines+markers',
            name=f"{test_name} ({cores} cores)",
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=8)
        ))
    
    # Update layout
    title = f"Performance Trend - {test_filter}" if test_filter else "Performance Trends"
    fig.update_layout(
        title=title,
        xaxis_title="Timestamp",
        yaxis_title="Zone Updates/sec/GPU",
        xaxis=dict(
            gridcolor='lightgray',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            type='log',
            gridcolor='lightgray',
            showgrid=True,
            zeroline=False,
            exponentformat='e'
        ),
        hovermode='closest',
        template='plotly_white',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.01
        ),
        height=500
    )
    
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
    }
    
    return fig.to_html(include_plotlyjs='https://cdn.plot.ly/plotly-latest.min.js', 
                      div_id="trend-plot", config=config)


def create_weak_scaling_plot(data_entries: List[Dict], baseline_cores: int = 1) -> str:
    """
    Create a weak scaling efficiency plot.
    
    Args:
        data_entries: List of dictionaries with performance data
        baseline_cores: Number of cores to use as baseline (default: 1)
        
    Returns:
        HTML string containing the embedded plotly plot
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
    
    fig = go.Figure()
    
    # Add ideal scaling line
    max_cores = max(e['cores'] for e in valid_entries)
    ideal_cores = [1, max_cores]
    ideal_efficiency = [100, 100]
    
    fig.add_trace(go.Scatter(
        x=ideal_cores,
        y=ideal_efficiency,
        mode='lines',
        name='Ideal Scaling',
        line=dict(color='black', width=2, dash='dash'),
        showlegend=True
    ))
    
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
            fig.add_trace(go.Scatter(
                x=cores,
                y=efficiency,
                mode='lines+markers',
                name=test_name,
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=8)
            ))
    
    # Update layout
    fig.update_layout(
        title="Weak Scaling Efficiency",
        xaxis_title="Number of Cores",
        yaxis_title="Efficiency (%)",
        xaxis=dict(
            type='log',
            gridcolor='lightgray',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            gridcolor='lightgray',
            showgrid=True,
            zeroline=False,
            range=[0, 120]
        ),
        hovermode='closest',
        template='plotly_white',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        ),
        height=500
    )
    
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
    }
    
    return fig.to_html(include_plotlyjs='https://cdn.plot.ly/plotly-latest.min.js', 
                      div_id="weak-scaling-plot", config=config)


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