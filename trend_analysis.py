#!/usr/bin/env python3
"""
Trend analysis module for Quokka regression testing.
Provides functions to analyze performance trends over time and weak scaling.
"""

import os
import io
import base64
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from web_utils import extract_performance_data
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def collect_trend_data(folder_path: str, timestamps: List[str]) -> Dict[str, pd.DataFrame]:
    """
    Collect performance data across all timestamps for trend analysis.
    
    Args:
        folder_path: Path to the folder containing performance test results
        timestamps: List of timestamp strings to analyze
        
    Returns:
        Dictionary mapping test configurations to time series DataFrames
    """
    trend_data = {}
    
    for ts in timestamps:
        perf_df = extract_performance_data(folder_path, ts)
        
        if perf_df is None or perf_df.empty:
            continue
            
        # Add timestamp column
        perf_df['timestamp'] = ts
        perf_df['datetime'] = pd.to_datetime(ts, format='%Y%m%d%H%M%S')
        
        # Process each test configuration
        for _, row in perf_df.iterrows():
            if pd.notna(row.get('zone_updates_per_sec_per_gpu')):
                # Create unique key for this test configuration
                test_key = f"{row.get('test_name', 'unknown')}_{row.get('cores', 0)}cores_{row.get('gpus_per_task', 0)}gpus"
                
                if test_key not in trend_data:
                    trend_data[test_key] = []
                
                trend_data[test_key].append({
                    'timestamp': ts,
                    'datetime': pd.to_datetime(ts, format='%Y%m%d%H%M%S'),
                    'test_name': row.get('test_name', 'unknown'),
                    'cores': row.get('cores', 0),
                    'gpus_per_task': row.get('gpus_per_task', 0),
                    'zone_updates_per_gpu': row.get('zone_updates_per_sec_per_gpu'),
                    'elapsed_time': row.get('elapsed_time', 0)
                })
    
    # Convert lists to DataFrames
    for key in trend_data:
        trend_data[key] = pd.DataFrame(trend_data[key]).sort_values('datetime')
    
    return trend_data


def create_performance_trend_plot(trend_data: Dict[str, pd.DataFrame], folder_name: str) -> str:
    """
    Create a plot showing performance trends over time using matplotlib.
    
    Args:
        trend_data: Dictionary mapping test configurations to time series DataFrames
        folder_name: Name of the folder being analyzed
        
    Returns:
        HTML string containing base64-encoded image
    """
    if not trend_data:
        return '<div style="padding: 20px; text-align: center; color: #666;">No trend data available</div>'
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Color palette
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Add a trace for each test configuration
    for idx, (config_name, df) in enumerate(trend_data.items()):
        if not df.empty and 'zone_updates_per_gpu' in df.columns:
            # Parse test info from config name
            parts = config_name.split('_')
            test_name = parts[0] if parts else 'unknown'
            cores = parts[1].replace('cores', '') if len(parts) > 1 else '?'
            gpus = parts[2].replace('gpus', '') if len(parts) > 2 else '?'
            
            label = f"{test_name} ({cores} cores, {gpus} GPU)"
            
            # Plot with scatter points only, no lines
            ax.semilogy(df['datetime'].values, 
                       df['zone_updates_per_gpu'].values,
                       marker='o', markersize=8, linestyle='none',
                       color=colors[idx % len(colors)],
                       label=label)
    
    # Format the plot
    ax.set_xlabel('Timestamp', fontsize=12)
    ax.set_ylabel('Zone Updates/sec/GPU', fontsize=12)
    ax.set_title(f'Performance Trends - {folder_name}', fontsize=14, fontweight='bold')
    ax.grid(True, which='both', alpha=0.3)
    
    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    plt.xticks(rotation=45, ha='right')
    
    # Position legend outside plot area
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f'<img src="data:image/png;base64,{img_base64}" style="max-width: 100%; height: auto;" alt="Performance Trends - {folder_name}">'


def calculate_trend_statistics(trend_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Calculate statistics about performance trends.
    
    Args:
        trend_data: Dictionary mapping test configurations to time series DataFrames
        
    Returns:
        Dictionary with trend statistics
    """
    stats = {
        'total_configurations': len(trend_data),
        'configurations': []
    }
    
    for config_name, df in trend_data.items():
        if len(df) < 2 or 'zone_updates_per_gpu' not in df.columns:
            continue
            
        config_stats = {
            'name': config_name,
            'data_points': len(df),
            'first_performance': df.iloc[0]['zone_updates_per_gpu'],
            'last_performance': df.iloc[-1]['zone_updates_per_gpu'],
            'mean_performance': df['zone_updates_per_gpu'].mean(),
            'std_performance': df['zone_updates_per_gpu'].std()
        }
        
        # Calculate trend (simple linear regression)
        if len(df) >= 2:
            x = np.arange(len(df))
            y = df['zone_updates_per_gpu'].values
            z = np.polyfit(x, y, 1)
            slope = z[0]
            
            # Classify trend
            relative_change = (df.iloc[-1]['zone_updates_per_gpu'] - df.iloc[0]['zone_updates_per_gpu']) / df.iloc[0]['zone_updates_per_gpu']
            
            if abs(relative_change) < 0.05:  # Less than 5% change
                config_stats['trend'] = 'stable'
            elif relative_change > 0:
                config_stats['trend'] = 'improving'
            else:
                config_stats['trend'] = 'degrading'
                
            config_stats['relative_change'] = relative_change * 100  # As percentage
        
        stats['configurations'].append(config_stats)
    
    return stats


def analyze_weak_scaling(folder_path: str, timestamp: str) -> pd.DataFrame:
    """
    Analyze weak scaling efficiency for a specific timestamp.
    
    Args:
        folder_path: Path to the folder containing performance test results
        timestamp: Timestamp to analyze
        
    Returns:
        DataFrame with weak scaling analysis
    """
    perf_df = extract_performance_data(folder_path, timestamp)
    
    if perf_df is None or perf_df.empty:
        return pd.DataFrame()
    
    # Check if zone_updates_per_sec_per_gpu column exists
    if 'zone_updates_per_sec_per_gpu' not in perf_df.columns:
        return pd.DataFrame()
    
    # Filter for valid performance data
    valid_df = perf_df[perf_df['zone_updates_per_sec_per_gpu'].notna()].copy()
    
    if valid_df.empty:
        return pd.DataFrame()
    
    # Group by test name to analyze scaling
    scaling_data = []
    for test_name in valid_df['test_name'].unique():
        test_df = valid_df[valid_df['test_name'] == test_name].sort_values('cores')
        
        if len(test_df) > 1:
            # Calculate scaling efficiency
            baseline = test_df.iloc[0]['zone_updates_per_sec_per_gpu']
            
            for _, row in test_df.iterrows():
                scaling_data.append({
                    'test_name': test_name,
                    'cores': row['cores'],
                    'gpus_per_task': row['gpus_per_task'],
                    'performance': row['zone_updates_per_sec_per_gpu'],
                    'scaling_efficiency': (row['zone_updates_per_sec_per_gpu'] / baseline) * 100 if baseline > 0 else 0
                })
    
    return pd.DataFrame(scaling_data)


def create_weak_scaling_plot(scaling_df: pd.DataFrame, folder_name: str) -> str:
    """
    Create a weak scaling plot showing how performance scales with core count using matplotlib.
    
    Args:
        scaling_df: DataFrame with weak scaling analysis
        folder_name: Name of the folder being analyzed
        
    Returns:
        HTML string containing base64-encoded image
    """
    if scaling_df.empty:
        return '<div style="padding: 20px; text-align: center; color: #666;">No completed runs for weak scaling analysis</div>'
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for idx, test_name in enumerate(scaling_df['test_name'].unique()):
        test_df = scaling_df[scaling_df['test_name'] == test_name].sort_values('cores')
        color = colors[idx % len(colors)]
        
        # Performance plot (left)
        ax1.loglog(test_df['cores'].values, 
                   test_df['performance'].values,
                   marker='o', markersize=8, linestyle='none',
                   color=color, label=test_name)
        
        # Efficiency plot (right)
        ax2.semilogx(test_df['cores'].values, 
                     test_df['scaling_efficiency'].values,
                     marker='o', markersize=8, linestyle='none',
                     color=color, label=test_name)
    
    # Add ideal scaling line to efficiency plot
    max_cores = scaling_df['cores'].max()
    ax2.semilogx([1, max_cores], [100, 100], 
                 'k--', linewidth=2, label='Ideal Scaling')
    
    # Format performance plot
    ax1.set_xlabel('Number of Cores', fontsize=12)
    ax1.set_ylabel('Zone Updates/sec/GPU', fontsize=12)
    ax1.set_title('Weak Scaling Performance', fontsize=13, fontweight='bold')
    ax1.grid(True, which='both', alpha=0.3)
    ax1.legend(loc='best', fontsize=9)
    
    # Format efficiency plot
    ax2.set_xlabel('Number of Cores', fontsize=12)
    ax2.set_ylabel('Efficiency (%)', fontsize=12)
    ax2.set_title('Scaling Efficiency', fontsize=13, fontweight='bold')
    ax2.set_ylim(0, 120)
    ax2.grid(True, which='both', alpha=0.3)
    ax2.legend(loc='best', fontsize=9)
    
    plt.suptitle(f'Weak Scaling Analysis - {folder_name}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f'<img src="data:image/png;base64,{img_base64}" style="max-width: 100%; height: auto;" alt="Weak Scaling Analysis - {folder_name}">'


if __name__ == "__main__":
    # Test code
    print("Trend analysis module loaded successfully")