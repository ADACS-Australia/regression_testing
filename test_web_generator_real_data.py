#!/usr/bin/env python3
"""
Test suite for web_generator using real parquet data from the work directory.
These tests validate that the web generation works correctly with actual data.
"""

import unittest
import os
import sys
import tempfile
import shutil
import pandas as pd
from pathlib import Path

# Add the regression_testing directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_generator import (
    create_index_page,
    create_folder_page,
    create_timestamp_page,
    discover_folders_from_ini_files
)
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
from web_generator_safe import safe_generate_all_pages


class TestRealDataExtraction(unittest.TestCase):
    """Test data extraction with real parquet files."""
    
    @classmethod
    def setUpClass(cls):
        """Set up paths to real data."""
        cls.work_dir = '/home/agray/src/cas/quokka/work'
        cls.test_folders = {
            'A': {
                'timestamps': ['20250830231131', '20250831123050'],
                'expected_output_records': {'20250830231131': 10, '20250831123050': 2}
            },
            'B': {
                'timestamps': ['20250831125137'],
                'expected_output_records': {'20250831125137': 2}
            },
            'C': {
                'timestamps': ['20250831125144'],
                'expected_output_records': {'20250831125144': 2}
            },
            'reference': {
                'timestamps': ['20250830231131', '20250831123050'],
                'expected_output_records': {'20250830231131': 10, '20250831123050': 0}
            }
        }
    
    def test_extract_performance_data_A_full(self):
        """Test extracting data from A/20250830231131 which has 10 records."""
        folder_path = os.path.join(self.work_dir, 'A', 'performance_test')
        data = extract_performance_data(folder_path, '20250830231131')
        
        self.assertIsNotNone(data)
        self.assertFalse(data.empty)
        # The data should have been merged and processed
        # We expect around 10-11 rows after merging
        self.assertGreaterEqual(len(data), 10)
        
        # Check that performance data is present
        self.assertIn('zone_updates_per_gpu', data.columns)
        self.assertIn('n_cores', data.columns)
        self.assertIn('test_name', data.columns)
    
    def test_extract_performance_data_reference_missing(self):
        """Test extracting data from reference/20250831123050 which has no output."""
        folder_path = os.path.join(self.work_dir, 'reference', 'performance_test')
        data = extract_performance_data(folder_path, '20250831123050')
        
        # Should return None or empty DataFrame when no output data exists
        if data is not None:
            self.assertTrue(data.empty or 'zone_updates_per_gpu' not in data.columns)
    
    def test_aggregate_folder_data_A(self):
        """Test aggregating all data from folder A."""
        folder_path = os.path.join(self.work_dir, 'A', 'performance_test')
        timestamps = ['20250830231131', '20250831123050']
        
        aggregated = aggregate_folder_data(folder_path, timestamps)
        
        self.assertIsNotNone(aggregated)
        self.assertFalse(aggregated.empty)
        # Should have data from both timestamps
        self.assertGreaterEqual(len(aggregated), 12)  # 10 + 2 records
    
    def test_format_missing_data_message_real(self):
        """Test missing data message with real missing data scenario."""
        # Simulate the reference/20250831123050 case
        data = {
            'job_submission': pd.DataFrame({'test': [1]}),
            'job_output': None
        }
        
        msg = format_missing_data_message(data)
        self.assertIn('Jobs are submitted but not yet complete', msg)


class TestRealDataComparison(unittest.TestCase):
    """Test comparison functionality with real data."""
    
    @classmethod
    def setUpClass(cls):
        """Set up paths to real data."""
        cls.work_dir = '/home/agray/src/cas/quokka/work'
    
    def test_get_baseline_data_A(self):
        """Test getting baseline data from folder A."""
        folder_path = os.path.join(self.work_dir, 'A', 'performance_test')
        current_timestamp = '20250831123050'
        
        baseline = get_baseline_data(folder_path, current_timestamp)
        
        self.assertIsNotNone(baseline)
        # Baseline should be from 20250830231131 (earliest timestamp)
        self.assertGreaterEqual(len(baseline), 10)
    
    def test_get_latest_reference_data(self):
        """Test getting reference data from reference folder."""
        reference_data = get_latest_reference_data(self.work_dir)
        
        self.assertIsNotNone(reference_data)
        # Should have data from reference/20250830231131
        # Data is returned as a dict keyed by test name
        self.assertIsInstance(reference_data, dict)
        
        # Check if we have test data
        total_entries = sum(len(entries) for entries in reference_data.values())
        self.assertGreaterEqual(total_entries, 10)
    
    def test_calculate_performance_difference_real(self):
        """Test performance difference calculation with real values."""
        # Use realistic values from the data
        current = 10803812.71  # From actual data
        baseline = 12962730.09  # From actual data
        
        diff = calculate_performance_difference(current, baseline)
        
        self.assertIn('absolute', diff)
        self.assertIn('percentage', diff)
        self.assertIn('degraded', diff)
        self.assertTrue(diff['degraded'])  # Performance decreased
        self.assertFalse(diff['improved'])
        self.assertLess(diff['percentage'], 0)  # Negative percentage


class TestRealDataTrendAnalysis(unittest.TestCase):
    """Test trend analysis with real data."""
    
    @classmethod
    def setUpClass(cls):
        """Set up paths to real data."""
        cls.work_dir = '/home/agray/src/cas/quokka/work'
    
    def test_collect_trend_data_A(self):
        """Test collecting trend data from folder A."""
        folder_path = os.path.join(self.work_dir, 'A', 'performance_test')
        timestamps = ['20250830231131', '20250831123050']
        
        trend_data = collect_trend_data(folder_path, timestamps)
        
        self.assertIsNotNone(trend_data)
        self.assertIsInstance(trend_data, dict)
        
        # Should have data for at least one test
        self.assertGreater(len(trend_data), 0)
        
        # Each test should have a DataFrame with timestamp data
        for test_name, df in trend_data.items():
            self.assertIsInstance(df, pd.DataFrame)
            self.assertIn('timestamp', df.columns)
            self.assertIn('zone_updates_per_gpu', df.columns)
    
    def test_analyze_weak_scaling_A(self):
        """Test weak scaling analysis with real data from A."""
        folder_path = os.path.join(self.work_dir, 'A', 'performance_test')
        timestamp = '20250830231131'  # This has full 1,2,4,8 core data
        
        scaling_data = analyze_weak_scaling(folder_path, timestamp)
        
        if scaling_data is not None and not scaling_data.empty:
            self.assertIn('n_cores', scaling_data.columns)
            self.assertIn('zone_updates_per_gpu', scaling_data.columns)
            
            # Should have multiple core counts
            core_counts = scaling_data['n_cores'].unique()
            self.assertGreater(len(core_counts), 1)
    
    def test_generate_trend_statistics_real(self):
        """Test trend statistics generation with real data."""
        folder_path = os.path.join(self.work_dir, 'A', 'performance_test')
        timestamps = ['20250830231131', '20250831123050']
        
        trend_data = collect_trend_data(folder_path, timestamps)
        stats = generate_trend_statistics(trend_data)
        
        self.assertIsNotNone(stats)
        self.assertIsInstance(stats, dict)
        
        # Should have statistics for tests
        for test_name, test_stats in stats.items():
            self.assertIn('mean_performance', test_stats)
            self.assertIn('std_performance', test_stats)
            self.assertIn('trend', test_stats)


class TestRealDataWebGeneration(unittest.TestCase):
    """Test complete web generation with real data."""
    
    def setUp(self):
        """Create temporary output directory."""
        self.test_dir = tempfile.mkdtemp()
        self.work_dir = '/home/agray/src/cas/quokka/work'
        self.output_dir = os.path.join(self.test_dir, 'output')
        os.makedirs(self.output_dir)
    
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_create_index_page_real_data(self):
        """Test creating main index page with real folder data."""
        folders = ['A', 'B', 'C', 'reference']
        
        success = create_index_page(self.work_dir, self.output_dir, folders)
        
        self.assertTrue(success)
        
        index_path = os.path.join(self.output_dir, 'index.html')
        self.assertTrue(os.path.exists(index_path))
        
        # Check content
        with open(index_path, 'r') as f:
            content = f.read()
        
        # Should list all folders
        for folder in folders:
            self.assertIn(folder, content)
        
        # Should have links to folder pages
        self.assertIn('href="A/index.html"', content)
        self.assertIn('href="reference/index.html"', content)
    
    def test_create_folder_page_A(self):
        """Test creating folder page for A with real timestamps."""
        folder_name = 'A'
        timestamps = ['20250830231131', '20250831123050']
        
        success = create_folder_page(
            self.work_dir, 
            self.output_dir, 
            folder_name, 
            timestamps
        )
        
        self.assertTrue(success)
        
        folder_page = os.path.join(self.output_dir, 'A', 'index.html')
        self.assertTrue(os.path.exists(folder_page))
        
        # Check content
        with open(folder_page, 'r') as f:
            content = f.read()
        
        # Should list timestamps
        for ts in timestamps:
            self.assertIn(ts, content)
        
        # Should have performance summary
        self.assertIn('Performance', content)
    
    def test_create_timestamp_page_with_data(self):
        """Test creating timestamp page with real performance data."""
        folder_name = 'A'
        timestamp = '20250830231131'
        
        success = create_timestamp_page(
            self.work_dir,
            self.output_dir,
            folder_name,
            timestamp
        )
        
        self.assertTrue(success)
        
        page_path = os.path.join(self.output_dir, 'A', '20250830231131', 'index.html')
        self.assertTrue(os.path.exists(page_path))
        
        # Check content
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Should have performance data
        self.assertIn('Zone Updates/sec/GPU', content)
        self.assertIn('test_hydro3d_blast', content)
        
        # Should have comparison columns
        self.assertIn('vs Baseline', content)
        self.assertIn('vs Reference', content)
        
        # Should have plotly
        self.assertIn('plotly', content)
    
    def test_complete_generation_with_real_data(self):
        """Test complete web generation using safe wrapper with real data."""
        # Use only a subset of folders for faster testing
        folders = ['A', 'reference']
        
        success = safe_generate_all_pages(
            self.work_dir,
            self.output_dir,
            folders=folders,
            log_level='ERROR'  # Reduce noise
        )
        
        self.assertTrue(success)
        
        # Check that key files were created
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, 'index.html')))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, 'A', 'index.html')))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, 'A', '20250830231131', 'index.html')))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, 'A', 'trends.html')))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, 'reference', 'index.html')))
    
    def test_handles_missing_reference_data(self):
        """Test that generation handles reference/20250831123050 missing data gracefully."""
        folder_name = 'reference'
        timestamp = '20250831123050'
        
        success = create_timestamp_page(
            self.work_dir,
            self.output_dir,
            folder_name,
            timestamp
        )
        
        self.assertTrue(success)
        
        page_path = os.path.join(self.output_dir, 'reference', '20250831123050', 'index.html')
        self.assertTrue(os.path.exists(page_path))
        
        # Check that it shows no data message
        with open(page_path, 'r') as f:
            content = f.read()
        
        self.assertIn('No performance data available', content)


class TestRealDataValidation(unittest.TestCase):
    """Validate specific aspects of the real data."""
    
    @classmethod
    def setUpClass(cls):
        """Set up paths to real data."""
        cls.work_dir = '/home/agray/src/cas/quokka/work'
    
    def test_parquet_file_counts(self):
        """Verify the expected number of parquet files exist."""
        parquet_files = []
        for root, dirs, files in os.walk(self.work_dir):
            for file in files:
                if file.endswith('.parquet'):
                    parquet_files.append(os.path.join(root, file))
        
        # Should have at least 13 parquet files based on analysis
        self.assertGreaterEqual(len(parquet_files), 13)
    
    def test_data_types_in_parquet(self):
        """Test that performance data can be converted to appropriate types."""
        # Test with A/20250830231131 which has complete data
        folder_path = os.path.join(self.work_dir, 'A', 'performance_test')
        data = extract_performance_data(folder_path, '20250830231131')
        
        if data is not None and not data.empty and 'zone_updates_per_gpu' in data.columns:
            # Check that we can work with the performance values
            perf_values = data['zone_updates_per_gpu']
            
            # Should be numeric or convertible to numeric
            numeric_values = pd.to_numeric(perf_values, errors='coerce')
            non_null_values = numeric_values.dropna()
            
            self.assertGreater(len(non_null_values), 0)
            
            # Values should be positive
            self.assertTrue((non_null_values > 0).all())
    
    def test_folder_discovery_from_ini_files(self):
        """Test that folder discovery finds all expected folders."""
        os.chdir(self.work_dir)
        folders = discover_folders_from_ini_files(self.work_dir)
        
        # Should find A, B, C, reference
        expected_folders = {'A', 'B', 'C', 'reference'}
        found_folders = set(folders)
        
        self.assertEqual(expected_folders, found_folders)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestRealDataExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestRealDataComparison))
    suite.addTests(loader.loadTestsFromTestCase(TestRealDataTrendAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestRealDataWebGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestRealDataValidation))
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("REAL DATA TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)