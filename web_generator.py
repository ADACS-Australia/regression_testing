#!/usr/bin/env python3
"""
Web page generator for regression testing results.
Creates a three-tier structure of HTML pages with performance plots.
"""

import os
import json
import shutil
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd

# Import our data extraction utilities
from web_utils import (
    aggregate_folder_data,
    get_reference_data,
    extract_performance_data,
    format_missing_data_message
)

# Import plotting utilities
from plotting import (
    create_performance_plot,
    create_comparison_plot,
    create_trend_plot,
    create_weak_scaling_plot
)

# Import comparison utilities
from comparison import (
    get_baseline_data,
    get_latest_reference_data,
    compare_performance_entries,
    format_comparison_text,
    generate_comparison_summary
)
from trend_analysis import (
    collect_trend_data,
    create_performance_trend_plot,
    analyze_weak_scaling,
    create_weak_scaling_plot,
    calculate_trend_statistics
)
from web_styling import (
    get_enhanced_css,
    get_logo_html,
    get_enhanced_html_template,
    wrap_in_responsive_table,
    get_theme_toggle_html
)
from web_logging import (
    setup_logging,
    get_logger,
    log_exception,
    safe_execution,
    DataValidationError,
    FileOperationError,
    validate_directory,
    validate_file,
    validate_timestamp,
    validate_performance_data,
    safe_write_file,
    safe_read_file,
    ErrorRecovery,
    log_performance_metrics,
    create_error_page
)


@log_exception
def discover_folders_from_ini_files(work_dir: str) -> List[str]:
    """
    Discover folder names by reading all INI files in the work directory.
    
    Args:
        work_dir: Base work directory
        
    Returns:
        List of unique folder names found in INI files
    """
    import configparser
    import glob
    
    folders = set()
    ini_files = glob.glob(os.path.join(work_dir, '*.ini'))
    
    if not ini_files:
        print(f"Warning: No INI files found in {work_dir}")
        return []
    
    for ini_file in ini_files:
        try:
            config = configparser.ConfigParser()
            config.read(ini_file)
            
            if config.has_option('main', 'working_dir'):
                folder = config.get('main', 'working_dir').rstrip('/')
                folders.add(folder)
                print(f"  Found folder '{folder}' in {os.path.basename(ini_file)}")
        except Exception as e:
            print(f"Warning: Could not read {ini_file}: {e}")
            continue
    
    return sorted(list(folders))


def create_directory_structure(web_output_dir: str, folders: List[str] = None) -> None:
    """
    Create the necessary directory structure for web output.
    
    Args:
        web_output_dir: Base directory for web output
        folders: List of folder names to create subdirectories for
    """
    # Create main directory
    os.makedirs(web_output_dir, exist_ok=True)
    
    # Create assets directory for CSS, JS, etc.
    assets_dir = os.path.join(web_output_dir, 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    
    # Create subdirectories for each folder if specified
    if folders:
        for folder in folders:
            folder_dir = os.path.join(web_output_dir, folder)
            os.makedirs(folder_dir, exist_ok=True)


def get_html_template() -> str:
    """
    Return the base HTML template with enhanced styling.
    Now uses the enhanced template from web_styling module.
    """
    # Get the CSS but escape curly braces for format()
    css = get_enhanced_css().replace('{', '{{').replace('}', '}}')
    logos = get_logo_html()
    theme_toggle = get_theme_toggle_html()
    
    # Build template with enhanced styling
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Quokka Regression Testing Dashboard - Performance metrics and analysis">
    <meta name="author" content="QUOKKA Team">
    <title>{{title}}</title>
    <style>
{css}
    </style>
</head>
<body>
    {theme_toggle}
    <div class="container">
        <div class="header">
            <div>
                <h1>{{title}}</h1>
            </div>
            {logos}
        </div>
        
        {{content}}
        
        <div class="footer">
            <p>Generated on {{timestamp}} | Quokka Regression Testing Dashboard</p>
            <p>
                <a href="https://github.com/quokka-astro/quokka" target="_blank">Quokka on GitHub</a> | 
                <a href="https://adacs.org.au" target="_blank">ADACS</a>
            </p>
        </div>
    </div>
</body>
</html>"""

def get_html_template_old() -> str:
    """
    Legacy HTML template (kept for reference).
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .nav-links {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .nav-links a {{
            color: #007bff;
            text-decoration: none;
            margin: 0 10px;
        }}
        .nav-links a:hover {{
            text-decoration: underline;
        }}
        .folder-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .folder-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border: 1px solid #dee2e6;
            transition: transform 0.2s;
        }}
        .folder-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .folder-card h3 {{
            margin-top: 0;
            color: #495057;
        }}
        .folder-card a {{
            color: #007bff;
            text-decoration: none;
            font-weight: 500;
        }}
        .timestamp-list {{
            list-style: none;
            padding: 0;
        }}
        .timestamp-list li {{
            background: #f8f9fa;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }}
        .timestamp-list a {{
            color: #007bff;
            text-decoration: none;
            font-size: 1.1em;
        }}
        .timestamp-list .date {{
            color: #6c757d;
            font-size: 0.9em;
            margin-left: 15px;
        }}
        .performance-summary {{
            background: #e7f3ff;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .warning {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            color: #856404;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .plot-container {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background-color: #007bff;
            color: white;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
        <div class="footer">
            Generated on {timestamp} | Quokka Regression Testing
        </div>
    </div>
</body>
</html>"""


def create_index_page(work_dir: str, web_output_dir: str, folders: List[str]) -> None:
    """
    Create the top-level index page listing all folders.
    
    Args:
        work_dir: Base work directory with data
        web_output_dir: Output directory for web pages
        folders: List of folder names to include
    """
    # Collect summary information for each folder
    folder_summaries = []
    
    for folder in folders:
        folder_path = os.path.join(work_dir, folder)
        perf_test_dir = os.path.join(folder_path, 'performance_test')
        
        if os.path.exists(perf_test_dir):
            # Get timestamps
            timestamps = [d for d in os.listdir(perf_test_dir) 
                         if os.path.isdir(os.path.join(perf_test_dir, d)) and d.isdigit()]
            timestamps.sort()
            
            # Get aggregated data
            data = aggregate_folder_data(work_dir, folder)
            
            summary = {
                'name': folder,
                'timestamp_count': len(timestamps),
                'latest_timestamp': timestamps[-1] if timestamps else None,
                'total_entries': len(data) if not data.empty else 0,
                'has_performance_data': 'zone_updates_per_gpu' in data.columns if not data.empty else False
            }
            
            if summary['has_performance_data'] and not data.empty:
                summary['performance_range'] = (
                    f"{data['zone_updates_per_gpu'].min():.2e} - "
                    f"{data['zone_updates_per_gpu'].max():.2e}"
                )
            
            folder_summaries.append(summary)
    
    # Build HTML content
    content = f"""
        <h1>Quokka Regression Testing Results</h1>
        
        <div class="nav-links">
            <strong>Navigation:</strong>
            {' | '.join([f'<a href="{f}/index.html">{f}</a>' for f in folders])}
        </div>
        
        <h2>Test Folders</h2>
        <div class="folder-grid">
    """
    
    for summary in folder_summaries:
        card_class = "folder-card"
        if summary['name'] == 'reference':
            card_class += " reference"
            
        content += f"""
            <div class="{card_class}">
                <h3>{'📊 ' if summary['name'] == 'reference' else ''}{summary['name']}</h3>
                <p><strong>Timestamps:</strong> {summary['timestamp_count']}</p>
                <p><strong>Latest:</strong> {summary['latest_timestamp'] or 'N/A'}</p>
                <p><strong>Total Entries:</strong> {summary['total_entries']}</p>
                {f"<p><strong>Performance Range:</strong><br>{summary.get('performance_range', 'N/A')}</p>" 
                 if summary.get('performance_range') else ''}
                <p><a href="{summary['name']}/index.html">View Details →</a></p>
            </div>
        """
    
    content += """
        </div>
        
        <h2>Summary Statistics</h2>
        <table>
            <thead>
                <tr>
                    <th>Folder</th>
                    <th>Timestamps</th>
                    <th>Latest Timestamp</th>
                    <th>Total Entries</th>
                    <th>Has Performance Data</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for summary in folder_summaries:
        content += f"""
            <tr>
                <td><a href="{summary['name']}/index.html">{summary['name']}</a></td>
                <td>{summary['timestamp_count']}</td>
                <td>{summary['latest_timestamp'] or 'N/A'}</td>
                <td>{summary['total_entries']}</td>
                <td>{'✓' if summary['has_performance_data'] else '✗'}</td>
            </tr>
        """
    
    content += """
            </tbody>
        </table>
    """
    
    # Generate final HTML
    html = get_html_template().format(
        title="Quokka Regression Testing - Main Index",
        content=content,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Write to file
    index_path = os.path.join(web_output_dir, 'index.html')
    with open(index_path, 'w') as f:
        f.write(html)
    
    print(f"Created main index: {index_path}")


def create_folder_page(work_dir: str, web_output_dir: str, folder_name: str) -> None:
    """
    Create a folder-level page listing all timestamps.
    
    Args:
        work_dir: Base work directory
        web_output_dir: Output directory for web pages
        folder_name: Name of the folder (e.g., 'A', 'reference')
    """
    folder_path = os.path.join(work_dir, folder_name)
    perf_test_dir = os.path.join(folder_path, 'performance_test')
    
    if not os.path.exists(perf_test_dir):
        warnings.warn(f"No performance_test directory for {folder_name}")
        return
    
    # Get all timestamps
    timestamps = [d for d in os.listdir(perf_test_dir) 
                  if os.path.isdir(os.path.join(perf_test_dir, d)) and d.isdigit()]
    timestamps.sort(reverse=True)  # Most recent first
    
    # Build HTML content
    content = f"""
        <h1>Folder: {folder_name}</h1>
        
        <div class="nav-links">
            <a href="../index.html">← Back to Main Index</a>
        </div>
        
        <div class="performance-summary">
            <strong>Total Timestamps:</strong> {len(timestamps)}<br>
            <strong>Latest:</strong> {timestamps[0] if timestamps else 'N/A'}<br>
            <strong>Oldest:</strong> {timestamps[-1] if timestamps else 'N/A'}
        </div>
        
        <h2>Available Timestamps</h2>
        <ul class="timestamp-list">
    """
    
    for ts in timestamps:
        # Convert timestamp to readable date
        dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
        readable_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Get performance data for this timestamp
        data = extract_performance_data(os.path.join(folder_path, 'performance_test'), ts)
        
        entry_info = ""
        if data is not None:
            entry_count = len(data)
            perf_count = data['zone_updates_per_sec_per_gpu'].notna().sum() if 'zone_updates_per_sec_per_gpu' in data.columns else 0
            entry_info = f" - {entry_count} entries ({perf_count} with performance data)"
        
        content += f"""
            <li>
                <a href="{ts}/index.html">{ts}</a>
                <span class="date">{readable_date}</span>
                {entry_info}
            </li>
        """
    
    content += """
        </ul>
    """
    
    # Add comparison plot if we have multiple timestamps with data
    timestamps_with_data = {}
    for ts in timestamps:
        # Load performance data for this timestamp (returns DataFrame)
        perf_df = extract_performance_data(folder_path, ts)
        if perf_df is not None and not perf_df.empty:
            # Convert DataFrame to list of dicts for plotting
            perf_data = []
            for _, row in perf_df.iterrows():
                entry = {
                    'test_name': row.get('test_name', 'unknown'),
                    'cores': row.get('cores', 0),
                    'gpus_per_task': row.get('gpus_per_task', 0),
                    'zone_updates_per_sec_per_gpu': row.get('zone_updates_per_sec_per_gpu') if pd.notna(row.get('zone_updates_per_sec_per_gpu')) else 'N/A',
                    'elapsed_time': f"{row.get('elapsed_time', 0):.2f}" if pd.notna(row.get('elapsed_time')) else 'N/A'
                }
                perf_data.append(entry)
            
            if any(e.get('zone_updates_per_sec_per_gpu') and e['zone_updates_per_sec_per_gpu'] != 'N/A' for e in perf_data):
                timestamps_with_data[ts] = perf_data
    
    # Show performance plot if we have any data
    if len(timestamps_with_data) >= 1:
        if len(timestamps_with_data) > 1:
            # Multiple timestamps - show comparison
            comparison_plot = create_comparison_plot(timestamps_with_data, folder_name)
            content += f"""
            <h2>Performance Comparison</h2>
            <div class="plot-container">
                {comparison_plot}
            </div>
            """
        else:
            # Single timestamp - show regular performance plot
            single_ts = list(timestamps_with_data.keys())[0]
            single_data = timestamps_with_data[single_ts]
            perf_plot = create_performance_plot(single_data, 
                                               title=f"Performance - {folder_name}")
            content += f"""
            <h2>Performance</h2>
            <div class="plot-container">
                {perf_plot}
            </div>
            """
    
    content += """
        <h2>Trend Analysis</h2>
        <p><a href="trends.html">View Performance Trends →</a></p>
    """
    
    # Generate final HTML
    html = get_html_template().format(
        title=f"Quokka Regression Testing - {folder_name}",
        content=content,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Write to file
    folder_index_path = os.path.join(web_output_dir, folder_name, 'index.html')
    with open(folder_index_path, 'w') as f:
        f.write(html)
    
    print(f"Created folder index: {folder_index_path}")


def create_timestamp_page(
    work_dir: str, 
    web_output_dir: str, 
    folder_name: str, 
    timestamp: str
) -> None:
    """
    Create a timestamp-level page with performance data.
    Note: Plotting will be added in Step 7.
    
    Args:
        work_dir: Base work directory
        web_output_dir: Output directory for web pages
        folder_name: Name of the folder
        timestamp: Timestamp string
    """
    # Extract performance data
    folder_path = os.path.join(work_dir, folder_name)
    data = extract_performance_data(folder_path, timestamp)
    
    # Create timestamp directory
    timestamp_dir = os.path.join(web_output_dir, folder_name, timestamp)
    os.makedirs(timestamp_dir, exist_ok=True)
    
    # Build HTML content
    content = f"""
        <h1>{folder_name} - {timestamp}</h1>
        
        <div class="nav-links">
            <a href="../../index.html">← Main Index</a> | 
            <a href="../index.html">← {folder_name} Index</a>
        </div>
    """
    
    # Initialize folder_data and enhanced_folder_data
    folder_data = []
    enhanced_folder_data = []
    
    if data is None or data.empty:
        content += """
        <div class="warning">
            No performance data available for this timestamp.
        </div>
        """
    else:
        # Add summary statistics
        if 'zone_updates_per_sec_per_gpu' in data.columns:
            perf_data = data[data['zone_updates_per_sec_per_gpu'].notna()]
            if not perf_data.empty:
                content += f"""
                <div class="performance-summary">
                    <h3>Performance Summary</h3>
                    <strong>Total Entries:</strong> {len(data)}<br>
                    <strong>Entries with Performance Data:</strong> {len(perf_data)}<br>
                    <strong>Min Performance:</strong> {perf_data['zone_updates_per_sec_per_gpu'].min():.2e} zone updates/sec/GPU<br>
                    <strong>Max Performance:</strong> {perf_data['zone_updates_per_sec_per_gpu'].max():.2e} zone updates/sec/GPU<br>
                    <strong>Mean Performance:</strong> {perf_data['zone_updates_per_sec_per_gpu'].mean():.2e} zone updates/sec/GPU
                </div>
                """
        
        # Convert DataFrame to list of dicts for plotting
        if not data.empty:
            for _, row in data.iterrows():
                entry = {
                    'test_name': row.get('test_name', 'unknown'),
                    'cores': row.get('cores', 0),
                    'gpus_per_task': row.get('gpus_per_task', 0),
                    'zone_updates_per_sec_per_gpu': row.get('zone_updates_per_sec_per_gpu') if pd.notna(row.get('zone_updates_per_sec_per_gpu')) else 'N/A',
                    'elapsed_time': f"{row.get('elapsed_time', 0):.2f}" if pd.notna(row.get('elapsed_time')) else 'N/A',
                    'status': row.get('status', 'PENDING')
                }
                folder_data.append(entry)
        
        # Get comparison data
        baseline_data = get_baseline_data(folder_path, timestamp)
        reference_data_dict = get_latest_reference_data(work_dir)
        
        # Enhance entries with comparison data
        enhanced_folder_data = compare_performance_entries(
            folder_data,
            baseline_data,
            reference_data_dict
        )
        
        # Generate comparison summary
        comparison_summary = generate_comparison_summary(enhanced_folder_data)
        
        # Get reference data for plotting (convert dict back to list format)
        reference_data = None
        if reference_data_dict:
            reference_data = []
            for test_entries in reference_data_dict.values():
                reference_data.extend(test_entries)
        
        # Generate performance plot
        plot_html = create_performance_plot(
            folder_data, 
            title=f"Performance Scaling - {folder_name}/{timestamp}",
            reference_data=reference_data
        )
        
        content += f"""
        <div class="plot-container">
            <h3>Performance Plot</h3>
            {plot_html}
        </div>
        """
        
        # Add comparison summary if available
        if comparison_summary['baseline_comparisons'] > 0 or comparison_summary['reference_comparisons'] > 0:
            content += """
            <div class="performance-summary">
                <h3>Comparison Summary</h3>
            """
            
            if comparison_summary['baseline_comparisons'] > 0:
                content += f"""
                <strong>Baseline Comparisons:</strong> {comparison_summary['baseline_comparisons']} tests<br>
                <strong>Improvements:</strong> {comparison_summary['improvements']}<br>
                <strong>Degradations:</strong> {comparison_summary['degradations']}<br>
                """
                
                if comparison_summary['max_improvement']:
                    max_imp = comparison_summary['max_improvement']
                    content += f"""
                    <strong>Max Improvement:</strong> {max_imp['test']} ({max_imp['cores']} cores): +{max_imp['percentage']:.1f}%<br>
                    """
                
                if comparison_summary['max_degradation']:
                    max_deg = comparison_summary['max_degradation']
                    content += f"""
                    <strong>Max Degradation:</strong> {max_deg['test']} ({max_deg['cores']} cores): {max_deg['percentage']:.1f}%<br>
                    """
            
            if comparison_summary['reference_comparisons'] > 0:
                content += f"""
                <strong>Reference Comparisons:</strong> {comparison_summary['reference_comparisons']} tests<br>
                """
            
            content += "</div>"
        
    # Add data table with comparison columns
    content += """
        <h2>Performance Data</h2>
        <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Cores</th>
                    <th>GPUs/Task</th>
                    <th>Zone Updates/sec/GPU</th>
                    <th>vs Baseline</th>
                    <th>vs Reference</th>
                    <th>Elapsed Time (s)</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Use enhanced data for the table
    for entry in enhanced_folder_data:
        perf_value = entry.get('zone_updates_per_sec_per_gpu', 'N/A')
        if perf_value != 'N/A' and isinstance(perf_value, (int, float)):
            zone_updates = f"{perf_value:.2e}"
        else:
            zone_updates = 'N/A'
        
        elapsed = entry.get('elapsed_time', 'N/A')
        if elapsed != 'N/A' and elapsed != '0.00':
            elapsed_str = elapsed
        else:
            elapsed_str = 'N/A'
        
        # Format comparison columns
        baseline_comp = ""
        if 'baseline_comparison' in entry:
            baseline_comp = format_comparison_text(entry['baseline_comparison'], 'baseline')
        
        reference_comp = ""
        if 'reference_comparison' in entry:
            reference_comp = format_comparison_text(entry['reference_comparison'], 'reference')
        
        content += f"""
        <tr>
            <td>{entry.get('test_name', 'N/A')}</td>
            <td>{entry.get('cores', 'N/A')}</td>
            <td>{entry.get('gpus_per_task', 'N/A')}</td>
            <td>{zone_updates}</td>
            <td>{baseline_comp}</td>
            <td>{reference_comp}</td>
            <td>{elapsed_str}</td>
            <td><span class="status-badge status-{entry.get('status', 'pending').lower()}">{entry.get('status', 'N/A')}</span></td>
        </tr>
        """
        
    content += """
            </tbody>
        </table>
        </div>
        """
    
    # Generate final HTML
    html = get_html_template().format(
        title=f"Quokka Regression Testing - {folder_name}/{timestamp}",
        content=content,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Write to file
    timestamp_index_path = os.path.join(timestamp_dir, 'index.html')
    with open(timestamp_index_path, 'w') as f:
        f.write(html)
    
    print(f"Created timestamp page: {timestamp_index_path}")


def create_trends_page(work_dir: str, web_output_dir: str, folder_name: str) -> None:
    """
    Create a trends analysis page for a folder with enhanced trend analysis.
    
    Args:
        work_dir: Base work directory
        web_output_dir: Output directory for web pages
        folder_name: Name of the folder
    """
    folder_path = os.path.join(work_dir, folder_name)
    output_file = os.path.join(web_output_dir, folder_name, 'trends.html')
    
    # Get all timestamps with data
    perf_test_dir = os.path.join(folder_path, 'performance_test')
    if not os.path.exists(perf_test_dir):
        return
    
    timestamps = sorted([d for d in os.listdir(perf_test_dir) 
                        if os.path.isdir(os.path.join(perf_test_dir, d)) and d.isdigit()],
                       reverse=True)  # Most recent first
    
    # Collect trend data using the new trend analysis module
    trend_data = collect_trend_data(folder_path, timestamps)
    
    # Generate trend statistics
    trend_stats = calculate_trend_statistics(trend_data)
    
    # Build page content
    content = f"""
        <h1>Performance Trends - {folder_name}</h1>
        
        <div class="nav-links">
            <a href="../index.html">← Main Index</a> | 
            <a href="index.html">← {folder_name} Index</a>
        </div>
    """
    
    # Add trend statistics summary
    if trend_stats['configurations']:
        content += """
        <div class="performance-summary">
            <h3>Trend Summary</h3>
        """
        
        improving = sum(1 for c in trend_stats['configurations'] if c['trend'] == 'improving')
        degrading = sum(1 for c in trend_stats['configurations'] if c['trend'] == 'degrading')
        stable = sum(1 for c in trend_stats['configurations'] if c['trend'] == 'stable')
        
        content += f"""
            <strong>Total Test Configurations:</strong> {trend_stats['total_configurations']}<br>
            <strong>Improving:</strong> <span style="color: green;">{improving}</span><br>
            <strong>Degrading:</strong> <span style="color: red;">{degrading}</span><br>
            <strong>Stable:</strong> {stable}<br>
        </div>
        """
    
    # Add performance trend plot
    content += """
        <h2>Overall Performance Trends</h2>
        <div class="plot-container">
    """
    
    if trend_data:
        trend_plot = create_performance_trend_plot(trend_data, folder_name)
        content += trend_plot
    else:
        content += '<div style="padding: 20px; text-align: center; color: #666;">No trend data available</div>'
    
    content += """
        </div>
    """
    
    # Add weak scaling analysis for latest timestamp
    if timestamps:
        latest_timestamp = timestamps[0]  # Most recent (list is reversed)
        scaling_df = analyze_weak_scaling(folder_path, latest_timestamp)
        
        content += f"""
            <h2>Weak Scaling Analysis (Latest Run)</h2>
            <div class="plot-container">
                {create_weak_scaling_plot(scaling_df, folder_name)}
            </div>
            """
    
    # Generate final HTML
    html = get_html_template().format(
        title=f"Quokka Regression Testing - {folder_name} Trends",
        content=content,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"  Created trends page: {output_file}")


def generate_all_pages(work_dir: str, web_output_dir: str, folders: List[str] = None) -> None:
    """
    Generate all web pages for the regression testing results.
    
    Args:
        work_dir: Base work directory with data
        web_output_dir: Output directory for web pages
        folders: List of folder names to process (if None, will be auto-discovered)
    """
    # If no folders specified, try to auto-discover from INI files
    if folders is None:
        print("Discovering folders from INI files...")
        folders = discover_folders_from_ini_files(work_dir)
        if not folders:
            print("Error: No folders found in INI files")
            return
    
    print(f"Processing folders: {', '.join(folders)}")
    
    # Create directory structure
    create_directory_structure(web_output_dir, folders)
    
    # Create main index page
    create_index_page(work_dir, web_output_dir, folders)
    
    # Create folder pages and timestamp pages
    for folder in folders:
        folder_path = os.path.join(work_dir, folder)
        if not os.path.exists(folder_path):
            continue
            
        # Create folder index page
        create_folder_page(work_dir, web_output_dir, folder)
        
        # Get timestamps for this folder
        perf_test_dir = os.path.join(folder_path, 'performance_test')
        if os.path.exists(perf_test_dir):
            timestamps = [d for d in os.listdir(perf_test_dir) 
                         if os.path.isdir(os.path.join(perf_test_dir, d)) and d.isdigit()]
            
            # Create page for each timestamp
            for ts in timestamps:
                create_timestamp_page(work_dir, web_output_dir, folder, ts)
            
            # Create trends page if we have data
            if timestamps:
                create_trends_page(work_dir, web_output_dir, folder)
    
    print(f"\nWeb pages generated successfully in: {web_output_dir}")
    print(f"Open {os.path.join(web_output_dir, 'index.html')} to view the results.")


if __name__ == "__main__":
    # Test the web generator
    work_dir = "/home/agray/src/cas/quokka/work"
    web_output_dir = "/home/agray/src/cas/quokka/www"
    
    print("Generating web pages...")
    # Will auto-discover folders from INI files
    generate_all_pages(work_dir, web_output_dir)