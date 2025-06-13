"""
Test cases for excel_handler module.

This module contains tests for Excel file operations and data handling.
"""

import sys
import os
import unittest
import tempfile
import shutil
from unittest.mock import patch, Mock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.job_tracker.core.excel_handler import (
    find_file, save_config, load_config, get_excel_path,
    init_excel, save_to_excel, get_all_applications,
    export_to_csv, import_from_csv, get_statistics
)
from src.job_tracker.core.constants import HEADERS


class TestExcelHandler(unittest.TestCase):
    """Test cases for Excel handler functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = tempfile.mkdtemp()
        self.test_excel_file = os.path.join(self.test_dir, "test_applications.xlsx")

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_find_file_existing(self):
        """Test finding an existing file."""
        # Create a test file
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("test")

        result = find_file("test.txt", self.test_dir)
        self.assertEqual(result, test_file)

    def test_find_file_non_existing(self):
        """Test finding a non-existing file."""
        result = find_file("nonexistent.txt", self.test_dir)
        self.assertIsNone(result)

    @patch('excel_handler.CONFIG_FILE')
    def test_save_and_load_config(self, mock_config_file):
        """Test saving and loading configuration."""
        config_file = os.path.join(self.test_dir, "config.json")
        mock_config_file.__str__ = lambda: config_file
        mock_config_file.parent.mkdir = Mock()

        # Mock the Path object behavior
        with patch('excel_handler.CONFIG_DIR') as mock_config_dir:
            mock_config_dir.mkdir = Mock()

            # Test saving config
            test_path = "/test/path/to/excel.xlsx"
            save_config(test_path)

            # Test loading config
            with patch('excel_handler.CONFIG_FILE') as mock_file:
                mock_file.exists.return_value = True
                with patch('builtins.open', unittest.mock.mock_open(
                    read_data='{"excel_path": "/test/path/to/excel.xlsx"}'
                )):
                    result = load_config()
                    self.assertEqual(result, test_path)

    def test_init_excel(self):
        """Test Excel file initialization."""
        with patch('excel_handler.EXCEL_PATH', self.test_excel_file):
            with patch('excel_handler._workbook_cache', None):
                init_excel()
                self.assertTrue(os.path.exists(self.test_excel_file))

    def test_get_statistics_empty(self):
        """Test statistics with no data."""
        with patch('excel_handler.get_all_applications', return_value=[]):
            stats = get_statistics()
            expected = {"total": 0, "companies": [], "locations": []}
            self.assertEqual(stats, expected)

    def test_get_statistics_with_data(self):
        """Test statistics with sample data."""
        sample_data = [
            ("Applied", "2024-01-01", "Company A", "Software Engineer", "San Francisco, CA", "http://example.com"),
            ("Applied", "2024-01-02", "Company B", "Data Scientist", "New York, NY", "http://example.com"),
            ("Applied", "2024-01-03", "Company A", "Product Manager", "San Francisco, CA", "http://example.com"),
        ]

        with patch('excel_handler.get_all_applications', return_value=sample_data):
            stats = get_statistics()

            self.assertEqual(stats["total"], 3)
            self.assertIn(("Company A", 2), stats["companies"])
            self.assertIn(("Company B", 1), stats["companies"])
            # Check that we have location data (location should be at index 4)
            self.assertTrue(len(stats["locations"]) > 0)
            # Check for specific locations in the data
            location_names = [loc[0] for loc in stats["locations"]]
            self.assertIn("San Francisco, CA", location_names)
            self.assertIn("New York, NY", location_names)


class TestExcelImportExport(unittest.TestCase):
    """Test cases for Excel import/export functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.test_csv_file = os.path.join(self.test_dir, "test_export.csv")

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_export_to_csv(self):
        """Test exporting data to CSV."""
        sample_data = [
            ("Applied", "2024-01-01", "Company A", "Software Engineer", "San Francisco, CA", "http://example.com"),
            ("Applied", "2024-01-02", "Company B", "Data Scientist", "New York, NY", "http://example.com"),
        ]

        with patch('excel_handler.get_all_applications', return_value=sample_data):
            result = export_to_csv(self.test_csv_file)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(self.test_csv_file))

            # Verify CSV content
            with open(self.test_csv_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn("Status,Date Applied,Company,Job Title,Location,Link", content)
                self.assertIn("Company A", content)
                self.assertIn("Company B", content)

    def test_import_from_csv(self):
        """Test importing data from CSV."""
        # Create test CSV file
        csv_content = """Status,Date Applied,Company,Job Title,Location,Link
Applied,2024-01-01,Test Company,Test Job,Test Location,http://test.com
Applied,2024-01-02,Another Company,Another Job,Another Location,http://test2.com"""

        with open(self.test_csv_file, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        with patch('excel_handler.batch_save_to_excel') as mock_save:
            result = import_from_csv(self.test_csv_file)
            self.assertEqual(result, 2)
            mock_save.assert_called_once()

            # Check that the correct data was passed to batch_save_to_excel
            call_args = mock_save.call_args[0][0]
            self.assertEqual(len(call_args), 2)
            self.assertEqual(call_args[0][2], "Test Company")  # Company field
            self.assertEqual(call_args[1][2], "Another Company")  # Company field


if __name__ == "__main__":
    unittest.main(verbosity=2)
