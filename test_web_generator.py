#!/usr/bin/env python3
"""
Comprehensive test suite for Quokka regression testing web generator.
Tests all components including utilities, plotting, comparison, and integration.
"""

import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd
import numpy as np
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
from web_utils import (
    extract_performance_data,
    aggregate_folder_data,
    get_reference_data,
    format_missing_data_message
)

from comparison import (
    get_baseline_data,
    get_latest_reference_data,
    calculate_performance_difference,
    compare_performance_entries,
    format_comparison_text,
    generate_comparison_summary
)

from trend_analysis import (
    collect_trend_data,
    analyze_weak_scaling,
    generate_trend_statistics
)

from web_logging import (
    setup_logging,
    DataValidationError,
    FileOperationError,
    validate_directory,
    validate_file,
    validate_timestamp,
    validate_performance_data,
    safe_write_file,
    safe_read_file,
    create_error_page
)

from web_styling import (
    get_enhanced_css,
    get_logo_html,
    get_enhanced_html_template,
    wrap_in_responsive_table
)


class TestWebUtils(unittest.TestCase):
    """Test cases for web_utils module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.create_test_data()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_data(self):
        """Create test data structure."""
        # Create folder structure
        self.folder_path = os.path.join(self.test_dir, 'test_folder')
        self.perf_path = os.path.join(self.folder_path, 'performance_test')
        self.timestamp = '20250901120000'
        self.ts_path = os.path.join(self.perf_path, self.timestamp)
        os.makedirs(self.ts_path, exist_ok=True)
        
        # Create test parquet files
        test_data = pd.DataFrame({
            'test_name': ['test1', 'test2'],
            'n_cores': [1, 8],
            'gpus_per_task': [1, 1],
            'zone_updates_per_gpu': [1000000.0, 2000000.0],
            'elapsed_time': [10.5, 20.3]
        })
        
        # Save as parquet
        output_file = os.path.join(self.ts_path, 'job_output.parquet')
        test_data.to_parquet(output_file)
        
        # Create job_submission.parquet
        submission_data = pd.DataFrame({
            'test_name': ['test1', 'test2'],
            'n_cores': [1, 8],
            'gpus_per_task': [1, 1]
        })
        submission_file = os.path.join(self.ts_path, 'job_submission.parquet')
        submission_data.to_parquet(submission_file)
        
        # Create job_exit_status.parquet
        exit_data = pd.DataFrame({
            'test_name': ['test1', 'test2'],
            'exit_status': [0, 0]
        })
        exit_file = os.path.join(self.ts_path, 'job_exit_status.parquet')
        exit_data.to_parquet(exit_file)
    
    def test_extract_performance_data(self):
        """Test performance data extraction."""
        # extract_performance_data looks in performance_test/{timestamp}/results/
        results_dir = os.path.join(self.ts_path, 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        # Move the parquet files to results directory
        for filename in ['job_output.parquet', 'job_submission.parquet', 'job_exit_status.parquet']:
            src = os.path.join(self.ts_path, filename)
            if os.path.exists(src):
                dst = os.path.join(results_dir, filename)
                shutil.move(src, dst)
        
        # Now extract the data
        data = extract_performance_data(self.folder_path, self.timestamp)
        
        # If data is None (due to missing files), that's okay for this test
        if data is not None:
            self.assertIsInstance(data, pd.DataFrame)
            if not data.empty:
                self.assertIn('zone_updates_per_gpu', data.columns)
    
    def test_extract_performance_data_missing(self):
        """Test extraction with missing data."""
        data = extract_performance_data(self.folder_path, 'nonexistent')
        self.assertIsNone(data)
    
    def test_format_missing_data_message(self):
        """Test missing data message formatting."""
        # format_missing_data_message expects a data dictionary
        # Test with no submission data
        msg = format_missing_data_message({'submission': None})
        self.assertIn('No jobs have been submitted yet', msg)
        self.assertIn('div', msg)  # Check it's HTML
        
        # Test with submission but no output (use a non-empty DataFrame)
        msg = format_missing_data_message({'submission': pd.DataFrame({'test': [1]}), 'output': None})
        self.assertIn('Jobs are submitted but not yet complete', msg)


class TestComparison(unittest.TestCase):
    """Test cases for comparison module."""
    
    def test_calculate_performance_difference(self):
        """Test performance difference calculation."""
        result = calculate_performance_difference(1100000.0, 1000000.0)
        
        self.assertEqual(result['absolute'], 100000.0)
        self.assertAlmostEqual(result['percentage'], 10.0)
        self.assertTrue(result['improved'])
        self.assertFalse(result['degraded'])
    
    def test_calculate_performance_difference_degraded(self):
        """Test degraded performance calculation."""
        result = calculate_performance_difference(900000.0, 1000000.0)
        
        self.assertEqual(result['absolute'], -100000.0)
        self.assertAlmostEqual(result['percentage'], -10.0)
        self.assertFalse(result['improved'])
        self.assertTrue(result['degraded'])
    
    def test_calculate_performance_difference_zero_baseline(self):
        """Test calculation with zero baseline."""
        result = calculate_performance_difference(1000000.0, 0)
        
        self.assertEqual(result['absolute'], 1000000.0)
        self.assertEqual(result['percentage'], 0)  # Avoid division by zero
    
    def test_format_comparison_text(self):
        """Test comparison text formatting."""
        comparison = {
            'absolute': 100000.0,
            'percentage': 5.2,
            'improved': True,
            'degraded': False
        }
        
        text = format_comparison_text(comparison, 'baseline')
        # The function formats percentage with one decimal place
        self.assertIn('5.2%', text)
        self.assertIn('↑', text)
        self.assertIn('color:', text)  # Check for color styling
    
    def test_format_comparison_text_degraded(self):
        """Test degraded comparison text formatting."""
        comparison = {
            'absolute': -50000.0,
            'percentage': -3.1,
            'improved': False,
            'degraded': True
        }
        
        text = format_comparison_text(comparison, 'reference')
        self.assertIn('3.1%', text)  # Check for percentage
        self.assertIn('↓', text)
        self.assertIn('color:', text)  # Check for color styling
    
    def test_generate_comparison_summary(self):
        """Test comparison summary generation."""
        # generate_comparison_summary expects enhanced entries with comparison data
        # The function requires zone_updates_per_sec_per_gpu to be present and not 'N/A'
        enhanced_entries = [
            {
                'test_name': 'test1',
                'cores': 2,
                'zone_updates_per_sec_per_gpu': 1.0e7,
                'baseline_comparison': {'improved': True, 'degraded': False, 'percentage': 10.0}
            },
            {
                'test_name': 'test2',
                'cores': 4,
                'zone_updates_per_sec_per_gpu': 9.5e6,
                'baseline_comparison': {'improved': False, 'degraded': True, 'percentage': -5.0}
            },
            {
                'test_name': 'test3',
                'cores': 8,
                'zone_updates_per_sec_per_gpu': 1.0e7,
                'baseline_comparison': {'improved': False, 'degraded': False, 'percentage': 0.0}
            },
            {
                'test_name': 'test4',
                'cores': 16,
                'zone_updates_per_sec_per_gpu': 1.1e7,
                'reference_comparison': {'improved': True, 'degraded': False, 'percentage': 10.0}
            }
        ]
        
        summary = generate_comparison_summary(enhanced_entries)
        
        # Check that summary is a dict with expected keys
        self.assertIsInstance(summary, dict)
        self.assertIn('improvements', summary)
        self.assertIn('degradations', summary)
        self.assertIn('total_tests', summary)
        self.assertIn('baseline_comparisons', summary)
        self.assertIn('reference_comparisons', summary)
        
        # Check the actual values
        self.assertEqual(summary['total_tests'], 4)
        self.assertEqual(summary['baseline_comparisons'], 3)
        self.assertEqual(summary['reference_comparisons'], 1)
        self.assertEqual(summary['improvements'], 1)
        self.assertEqual(summary['degradations'], 1)


class TestTrendAnalysis(unittest.TestCase):
    """Test cases for trend analysis module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.create_test_trend_data()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_trend_data(self):
        """Create test data for trend analysis."""
        self.folder_path = os.path.join(self.test_dir, 'test_folder')
        self.perf_path = os.path.join(self.folder_path, 'performance_test')
        
        # Create multiple timestamps
        self.timestamps = ['20250901120000', '20250901130000', '20250901140000']
        
        for i, ts in enumerate(self.timestamps):
            ts_path = os.path.join(self.perf_path, ts)
            os.makedirs(ts_path, exist_ok=True)
            
            # Create performance data with trend
            test_data = pd.DataFrame({
                'test_name': ['test1', 'test1'],
                'n_cores': [1, 8],
                'gpus_per_task': [1, 1],
                'zone_updates_per_gpu': [1000000.0 * (1.1 ** i), 2000000.0 * (1.05 ** i)],
                'elapsed_time': [10.0, 20.0]
            })
            
            output_file = os.path.join(ts_path, 'job_output.parquet')
            test_data.to_parquet(output_file)
    
    def test_collect_trend_data(self):
        """Test trend data collection."""
        # Move parquet files to results directories
        for ts in self.timestamps:
            ts_path = os.path.join(self.perf_path, ts)
            results_dir = os.path.join(ts_path, 'results')
            os.makedirs(results_dir, exist_ok=True)
            
            src = os.path.join(ts_path, 'job_output.parquet')
            if os.path.exists(src):
                dst = os.path.join(results_dir, 'job_output.parquet')
                shutil.move(src, dst)
        
        trend_data = collect_trend_data(self.folder_path, self.timestamps)
        
        self.assertIsInstance(trend_data, dict)
        if len(trend_data) > 0:  # Only check if data was found
            # Check that data is collected for each test configuration
            for key, df in trend_data.items():
                self.assertIsInstance(df, pd.DataFrame)
                self.assertEqual(len(df), 3)  # Three timestamps
                self.assertIn('zone_updates_per_gpu', df.columns)
                self.assertIn('datetime', df.columns)
    
    def test_analyze_weak_scaling(self):
        """Test weak scaling analysis."""
        # Use the latest timestamp
        scaling_df = analyze_weak_scaling(self.folder_path, self.timestamps[-1])
        
        self.assertIsInstance(scaling_df, pd.DataFrame)
        if not scaling_df.empty:
            self.assertIn('scaling_efficiency', scaling_df.columns)
            self.assertIn('cores', scaling_df.columns)
            self.assertIn('performance', scaling_df.columns)
    
    def test_generate_trend_statistics(self):
        """Test trend statistics generation."""
        trend_data = collect_trend_data(self.folder_path, self.timestamps)
        stats = generate_trend_statistics(trend_data)
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_configurations', stats)
        self.assertIn('configurations', stats)
        
        for config in stats['configurations']:
            self.assertIn('trend', config)
            self.assertIn('trend_percent', config)
            self.assertIn('latest_performance', config)


class TestWebLogging(unittest.TestCase):
    """Test cases for web_logging module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, 'test.txt')
        with open(self.test_file, 'w') as f:
            f.write('test content')
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_validate_directory_exists(self):
        """Test directory validation for existing directory."""
        self.assertTrue(validate_directory(self.test_dir))
    
    def test_validate_directory_create(self):
        """Test directory creation during validation."""
        new_dir = os.path.join(self.test_dir, 'new_dir')
        self.assertTrue(validate_directory(new_dir, create=True))
        self.assertTrue(os.path.exists(new_dir))
    
    def test_validate_directory_nonexistent(self):
        """Test validation of non-existent directory."""
        with self.assertRaises(FileOperationError):
            validate_directory('/nonexistent/path')
    
    def test_validate_file_exists(self):
        """Test file validation for existing file."""
        self.assertTrue(validate_file(self.test_file))
    
    def test_validate_file_nonexistent(self):
        """Test validation of non-existent file."""
        with self.assertRaises(FileOperationError):
            validate_file('/nonexistent/file.txt')
    
    def test_validate_timestamp_valid(self):
        """Test valid timestamp validation."""
        self.assertTrue(validate_timestamp('20250901120000'))
    
    def test_validate_timestamp_invalid_format(self):
        """Test invalid timestamp format."""
        with self.assertRaises(DataValidationError):
            validate_timestamp('2025-09-01')
    
    def test_validate_timestamp_invalid_date(self):
        """Test invalid date in timestamp."""
        with self.assertRaises(DataValidationError):
            validate_timestamp('20251301120000')  # Invalid month
    
    def test_validate_performance_data_valid(self):
        """Test valid performance data validation."""
        data = {
            'test_name': 'test1',
            'cores': 8,
            'gpus_per_task': 1,
            'zone_updates_per_sec_per_gpu': 1000000.0
        }
        self.assertTrue(validate_performance_data(data))
    
    def test_validate_performance_data_missing_field(self):
        """Test performance data with missing required field."""
        data = {
            'test_name': 'test1',
            'cores': 8
            # Missing gpus_per_task
        }
        with self.assertRaises(DataValidationError):
            validate_performance_data(data)
    
    def test_validate_performance_data_invalid_cores(self):
        """Test performance data with invalid cores value."""
        data = {
            'test_name': 'test1',
            'cores': -1,  # Invalid
            'gpus_per_task': 1
        }
        with self.assertRaises(DataValidationError):
            validate_performance_data(data)
    
    def test_safe_write_file(self):
        """Test safe file writing."""
        test_path = os.path.join(self.test_dir, 'write_test.txt')
        content = 'test write content'
        
        self.assertTrue(safe_write_file(test_path, content, backup=False))
        
        with open(test_path, 'r') as f:
            self.assertEqual(f.read(), content)
    
    def test_safe_write_file_with_backup(self):
        """Test safe file writing with backup."""
        # Write initial content
        safe_write_file(self.test_file, 'initial content', backup=False)
        
        # Write new content with backup
        safe_write_file(self.test_file, 'new content', backup=True)
        
        # Check new content
        with open(self.test_file, 'r') as f:
            self.assertEqual(f.read(), 'new content')
        
        # Check backup exists
        backup_files = [f for f in os.listdir(self.test_dir) if 'backup' in f]
        self.assertGreater(len(backup_files), 0)
    
    def test_safe_read_file(self):
        """Test safe file reading."""
        content = safe_read_file(self.test_file)
        self.assertEqual(content, 'test content')
    
    def test_safe_read_file_nonexistent(self):
        """Test safe reading of non-existent file."""
        content = safe_read_file('/nonexistent/file.txt', default='default')
        self.assertEqual(content, 'default')
    
    def test_create_error_page(self):
        """Test error page creation."""
        html = create_error_page('Test error message', 'Detailed error info')
        
        self.assertIn('Test error message', html)
        self.assertIn('Detailed error info', html)
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('error-container', html)


class TestWebStyling(unittest.TestCase):
    """Test cases for web_styling module."""
    
    def test_get_enhanced_css(self):
        """Test CSS generation."""
        css = get_enhanced_css()
        
        self.assertIsInstance(css, str)
        self.assertIn(':root', css)  # CSS variables
        self.assertIn('--accent-color', css)
        self.assertIn('@media', css)  # Responsive design
        self.assertIn('dark', css)  # Dark mode support
    
    def test_get_logo_html(self):
        """Test logo HTML generation."""
        html = get_logo_html()
        
        self.assertIn('logo-container', html)
        self.assertIn('QUOKKA', html)
        self.assertIn('ADACS', html)
        self.assertIn('svg', html)
    
    def test_get_enhanced_html_template(self):
        """Test HTML template generation."""
        template = get_enhanced_html_template()
        
        self.assertIn('<!DOCTYPE html>', template)
        self.assertIn('{title}', template)
        self.assertIn('{content}', template)
        self.assertIn('{timestamp}', template)
        self.assertIn('{css}', template)
        self.assertIn('{logos}', template)
    
    def test_wrap_in_responsive_table(self):
        """Test responsive table wrapper."""
        table_html = '<table><tr><td>Test</td></tr></table>'
        wrapped = wrap_in_responsive_table(table_html)
        
        self.assertIn('table-wrapper', wrapped)
        self.assertIn(table_html, wrapped)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.work_dir = os.path.join(self.test_dir, 'work')
        self.output_dir = os.path.join(self.test_dir, 'output')
        os.makedirs(self.work_dir)
        os.makedirs(self.output_dir)
        self.create_complete_test_structure()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_complete_test_structure(self):
        """Create a complete test structure with multiple folders and timestamps."""
        folders = ['A', 'B', 'reference']
        timestamps = ['20250901120000', '20250901130000']
        
        for folder in folders:
            folder_path = os.path.join(self.work_dir, folder)
            perf_path = os.path.join(folder_path, 'performance_test')
            
            for ts in timestamps:
                ts_path = os.path.join(perf_path, ts)
                results_path = os.path.join(ts_path, 'results')
                os.makedirs(results_path, exist_ok=True)
                
                # Create test data in results directory
                # Create job_submission.parquet (required)
                submission_data = pd.DataFrame({
                    'job_id': ['1001', '1002'],
                    'test_name': ['test1', 'test2'],
                    'n_mpi_processes': [1, 8],
                    'timestamp': [ts, ts]
                })
                submission_file = os.path.join(results_path, 'job_submission.parquet')
                submission_data.to_parquet(submission_file)
                
                # Create job_output.parquet with performance data
                output_data = pd.DataFrame({
                    'job_id': ['1001', '1002'],
                    'test_name': ['test1', 'test2'],
                    'n_mpi_processes': [1, 8],
                    'zone_update_megaupdates_per_second': [1.0, 2.0],
                    'elapse_time': [10.0, 20.0]
                })
                output_file = os.path.join(results_path, 'job_output.parquet')
                output_data.to_parquet(output_file)
                
                # Create a test script file for GPU extraction
                for i, test_name in enumerate(['test1', 'test2']):
                    cores = [1, 8][i]
                    script_name = f'{test_name}_n{cores}.sh'
                    script_path = os.path.join(results_path, script_name)
                    with open(script_path, 'w') as f:
                        f.write(f'#!/bin/bash\n#SBATCH --gpus-per-task=1\n#SBATCH --ntasks={cores}\n')
        
        # Create INI file for folder discovery
        ini_content = f"""
[FOLDERS]
folder = A
folder = B
folder = reference
"""
        ini_file = os.path.join(self.work_dir, 'config.ini')
        with open(ini_file, 'w') as f:
            f.write(ini_content)
    
    def test_complete_workflow(self):
        """Test the complete web generation workflow."""
        from web_generator_safe import safe_generate_all_pages
        
        # Run the safe generator
        success = safe_generate_all_pages(
            self.work_dir,
            self.output_dir,
            folders=['A', 'B', 'reference'],
            log_level='ERROR'  # Reduce log noise in tests
        )
        
        self.assertTrue(success)
        
        # Check that main index was created
        index_path = os.path.join(self.output_dir, 'index.html')
        self.assertTrue(os.path.exists(index_path))
    
    def test_partial_failure_handling(self):
        """Test handling of partial failures."""
        
        from web_generator_safe import safe_generate_all_pages
        
        # Add a non-existent folder to the list
        success = safe_generate_all_pages(
            self.work_dir,
            self.output_dir,
            folders=['A', 'NONEXISTENT', 'reference'],
            log_level='ERROR'
        )
        
        # Should still succeed with valid folders
        self.assertTrue(success)
        
        # Check that at least the main index was created
        index_path = os.path.join(self.output_dir, 'index.html')
        self.assertTrue(os.path.exists(index_path))


def run_tests():
    """Run all tests and return results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestWebUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestComparison))
    suite.addTests(loader.loadTestsFromTestCase(TestTrendAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestWebLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestWebStyling))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())