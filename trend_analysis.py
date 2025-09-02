#!/usr/bin/env python3
"""
Trend analysis module for Quokka regression testing.
Provides functions to analyze performance trends over time and weak scaling.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from web_utils import extract_performance_data
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def collect_trend_data(folder_path: str, timestamps: List[str]) -> Dict[str, pd.DataFrame]:
    """
    Collect performance data across all timestamps for trend analysis.
    
    Args:
        folder_path: Path to the folder containing performance_test
        timestamps: List of timestamp strings to analyze
        
    Returns:
        Dictionary mapping test configurations to DataFrames with time series data
    """
    trend_data = {}
    
    for ts in timestamps:
        # Load performance data for this timestamp
        perf_df = extract_performance_data(folder_path, ts)
        
        if perf_df is not None and not perf_df.empty:
            # Add timestamp column
            perf_df['timestamp'] = ts
            perf_df['datetime'] = pd.to_datetime(ts, format='%Y%m%d%H%M%S')
            
            # Process each test configuration
            for _, row in perf_df.iterrows():
                if pd.notna(row.get('zone_updates_per_gpu')):
                    # Create unique key for this test configuration
                    test_key = f"{row.get('test_name', 'unknown')}_{row.get('n_cores', 0)}cores_{row.get('gpus_per_task', 0)}gpus"
                    
                    if test_key not in trend_data:
                        trend_data[test_key] = []
                    
                    trend_data[test_key].append({
                        'timestamp': ts,
                        'datetime': pd.to_datetime(ts, format='%Y%m%d%H%M%S'),
                        'test_name': row.get('test_name', 'unknown'),
                        'cores': row.get('n_cores', 0),
                        'gpus_per_task': row.get('gpus_per_task', 0),
                        'zone_updates_per_gpu': row.get('zone_updates_per_gpu'),
                        'elapsed_time': row.get('elapsed_time', 0)
                    })
    
    # Convert lists to DataFrames
    for key in trend_data:
        trend_data[key] = pd.DataFrame(trend_data[key]).sort_values('datetime')
    
    return trend_data


def create_performance_trend_plot(trend_data: Dict[str, pd.DataFrame], folder_name: str) -> str:
    """
    Create an interactive plot showing performance trends over time.
    
    Args:
        trend_data: Dictionary mapping test configurations to time series DataFrames
        folder_name: Name of the folder being analyzed
        
    Returns:
        HTML string containing the plotly plot
    """
    if not trend_data:
        return '<div style="padding: 20px; text-align: center; color: #666;">No trend data available</div>'
    
    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=[f"Performance Trends - {folder_name}"]
    )
    
    # Add a trace for each test configuration
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    for idx, (test_key, df) in enumerate(trend_data.items()):
        if len(df) > 0:
            # Parse test configuration from key
            parts = test_key.split('_')
            test_name = '_'.join(parts[:-2])  # Rejoin test name parts
            cores = parts[-2].replace('cores', '')
            gpus = parts[-1].replace('gpus', '')
            
            label = f"{test_name} ({cores} cores, {gpus} GPU)"
            color = colors[idx % len(colors)]
            
            # Add performance metric trace
            fig.add_trace(
                go.Scatter(
                    x=df['datetime'],
                    y=df['zone_updates_per_gpu'],
                    mode='lines+markers',
                    name=label,
                    line=dict(color=color, width=2),
                    marker=dict(size=8),
                    hovertemplate=(
                        f"<b>{label}</b><br>" +
                        "Time: %{x|%Y-%m-%d %H:%M}<br>" +
                        "Performance: %{y:.2e} zone updates/sec/GPU<br>" +
                        "<extra></extra>"
                    )
                )
            )
    
    # Update layout
    fig.update_layout(
        height=500,
        xaxis_title="Timestamp",
        yaxis_title="Zone Updates/sec/GPU",
        yaxis_type="log",  # Use log scale for performance metrics
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        margin=dict(r=200)  # Make room for legend
    )
    
    # Configure plot options
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': f'performance_trends_{folder_name}',
            'height': 500,
            'width': 1000,
            'scale': 1
        }
    }
    
    return fig.to_html(
        include_plotlyjs='https://cdn.plot.ly/plotly-latest.min.js',
        div_id="trend-plot",
        config=config
    )


def analyze_weak_scaling(folder_path: str, latest_timestamp: str) -> pd.DataFrame:
    """
    Analyze weak scaling for the latest timestamp.
    
    Args:
        folder_path: Path to the folder containing performance_test
        latest_timestamp: The latest timestamp to analyze
        
    Returns:
        DataFrame with weak scaling analysis
    """
    perf_df = extract_performance_data(folder_path, latest_timestamp)
    
    if perf_df is None or perf_df.empty:
        return pd.DataFrame()
    
    # Check if zone_updates_per_gpu column exists
    if 'zone_updates_per_gpu' not in perf_df.columns:
        return pd.DataFrame()
    
    # Filter for valid performance data
    valid_df = perf_df[perf_df['zone_updates_per_gpu'].notna()].copy()
    
    if valid_df.empty:
        return pd.DataFrame()
    
    # Group by test name to analyze scaling
    scaling_data = []
    for test_name in valid_df['test_name'].unique():
        test_df = valid_df[valid_df['test_name'] == test_name].sort_values('n_cores')
        
        if len(test_df) > 1:
            # Calculate scaling efficiency
            baseline = test_df.iloc[0]['zone_updates_per_gpu']
            
            for _, row in test_df.iterrows():
                scaling_data.append({
                    'test_name': test_name,
                    'cores': row['n_cores'],
                    'gpus_per_task': row['gpus_per_task'],
                    'performance': row['zone_updates_per_gpu'],
                    'scaling_efficiency': (row['zone_updates_per_gpu'] / baseline) * 100 if baseline > 0 else 0
                })
    
    return pd.DataFrame(scaling_data)


def create_weak_scaling_plot(scaling_df: pd.DataFrame, folder_name: str) -> str:
    """
    Create a weak scaling plot showing how performance scales with core count.
    
    Args:
        scaling_df: DataFrame with weak scaling analysis
        folder_name: Name of the folder being analyzed
        
    Returns:
        HTML string containing the plotly plot
    """
    if scaling_df.empty:
        return '<div style="padding: 20px; text-align: center; color: #666;">No completed runs for weak scaling analysis</div>'
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Weak Scaling Performance", "Scaling Efficiency"],
        horizontal_spacing=0.15
    )
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for idx, test_name in enumerate(scaling_df['test_name'].unique()):
        test_df = scaling_df[scaling_df['test_name'] == test_name].sort_values('cores')
        color = colors[idx % len(colors)]
        
        # Performance plot
        fig.add_trace(
            go.Scatter(
                x=test_df['cores'],
                y=test_df['performance'],
                mode='lines+markers',
                name=test_name,
                line=dict(color=color, width=2),
                marker=dict(size=10),
                legendgroup=test_name,
                showlegend=True,
                hovertemplate=(
                    f"<b>{test_name}</b><br>" +
                    "Cores: %{x}<br>" +
                    "Performance: %{y:.2e}<br>" +
                    "<extra></extra>"
                )
            ),
            row=1, col=1
        )
        
        # Efficiency plot
        fig.add_trace(
            go.Scatter(
                x=test_df['cores'],
                y=test_df['scaling_efficiency'],
                mode='lines+markers',
                name=test_name,
                line=dict(color=color, width=2, dash='dot'),
                marker=dict(size=10),
                legendgroup=test_name,
                showlegend=False,
                hovertemplate=(
                    f"<b>{test_name}</b><br>" +
                    "Cores: %{x}<br>" +
                    "Efficiency: %{y:.1f}%<br>" +
                    "<extra></extra>"
                )
            ),
            row=1, col=2
        )
    
    # Add ideal scaling line
    if not scaling_df.empty:
        max_cores = scaling_df['cores'].max()
        fig.add_trace(
            go.Scatter(
                x=[1, max_cores],
                y=[100, 100],
                mode='lines',
                name='Ideal Scaling',
                line=dict(color='gray', width=1, dash='dash'),
                showlegend=True,
                hoverinfo='skip'
            ),
            row=1, col=2
        )
    
    # Update axes
    fig.update_xaxes(title_text="Number of Cores", type="log", row=1, col=1)
    fig.update_xaxes(title_text="Number of Cores", type="log", row=1, col=2)
    fig.update_yaxes(title_text="Zone Updates/sec/GPU", type="log", row=1, col=1)
    fig.update_yaxes(title_text="Scaling Efficiency (%)", row=1, col=2)
    
    fig.update_layout(
        height=450,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        margin=dict(r=200),
        title_text=f"Weak Scaling Analysis - {folder_name}"
    )
    
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': f'weak_scaling_{folder_name}',
            'height': 450,
            'width': 1200,
            'scale': 1
        }
    }
    
    return fig.to_html(
        include_plotlyjs='https://cdn.plot.ly/plotly-latest.min.js',
        div_id="scaling-plot",
        config=config
    )


def generate_trend_statistics(trend_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Generate statistics about performance trends.
    
    Args:
        trend_data: Dictionary mapping test configurations to time series DataFrames
        
    Returns:
        Dictionary with trend statistics
    """
    stats = {
        'total_configurations': len(trend_data),
        'configurations': []
    }
    
    for test_key, df in trend_data.items():
        if len(df) > 1:
            # Calculate trend (simple linear regression on log scale)
            x = np.arange(len(df))
            y = np.log(df['zone_updates_per_gpu'].values)
            
            if len(x) > 1 and not np.any(np.isnan(y)):
                # Calculate trend
                z = np.polyfit(x, y, 1)
                trend_percent = (np.exp(z[0]) - 1) * 100  # Convert log slope to percentage
                
                config_stats = {
                    'name': test_key,
                    'data_points': len(df),
                    'latest_performance': df.iloc[-1]['zone_updates_per_gpu'],
                    'trend': 'improving' if trend_percent > 0 else 'degrading' if trend_percent < -0 else 'stable',
                    'trend_percent': abs(trend_percent),
                    'min_performance': df['zone_updates_per_gpu'].min(),
                    'max_performance': df['zone_updates_per_gpu'].max(),
                    'avg_performance': df['zone_updates_per_gpu'].mean()
                }
                
                stats['configurations'].append(config_stats)
    
    return stats