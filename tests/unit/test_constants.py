"""
Test cases for constants module.

This module contains tests for application constants and configuration.
"""

import sys
import os
import unittest

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.job_tracker.core.constants import (
    HEADERS, JOB_STATUS_OPTIONS, STATUS_COLORS,
    PRIMARY_BG, SECONDARY_BG, BUTTON_BG, BUTTON_FG, TEXT_COLOR,
    APP_CONFIG
)


class TestConstants(unittest.TestCase):
    """Test cases for application constants."""

    def test_headers_structure(self):
        """Test that headers are properly defined."""
        expected_headers = ["Status", "Date Applied", "Company", "Job Title", "Location", "Link"]
        self.assertEqual(HEADERS, expected_headers)
        self.assertEqual(len(HEADERS), 6)

    def test_job_status_options(self):
        """Test that job status options are properly defined."""
        self.assertIsInstance(JOB_STATUS_OPTIONS, list)
        self.assertTrue(len(JOB_STATUS_OPTIONS) > 0)

        # Check that all status options are strings
        for status in JOB_STATUS_OPTIONS:
            self.assertIsInstance(status, str)
            self.assertTrue(len(status) > 0)

    def test_status_colors_mapping(self):
        """Test that status colors are properly mapped."""
        self.assertIsInstance(STATUS_COLORS, dict)

        # Each status option should have a corresponding color
        for status in JOB_STATUS_OPTIONS:
            self.assertIn(status, STATUS_COLORS)

        # Each color should be a valid hex color or color name
        for color in STATUS_COLORS.values():
            self.assertIsInstance(color, str)
            self.assertTrue(len(color) > 0)

    def test_color_constants(self):
        """Test that color constants are properly defined."""
        colors = [PRIMARY_BG, SECONDARY_BG, BUTTON_BG, BUTTON_FG, TEXT_COLOR]

        for color in colors:
            self.assertIsInstance(color, str)
            self.assertTrue(len(color) > 0)
            # Should start with # for hex colors
            if color.startswith('#'):
                self.assertGreaterEqual(len(color), 4)  # At least #RGB
                self.assertLessEqual(len(color), 9)     # At most #RRGGBBAA

    def test_app_config_structure(self):
        """Test that app configuration is properly structured."""
        self.assertIsInstance(APP_CONFIG, dict)

        # Check for required configuration keys
        required_keys = ['window_title', 'min_window_size', 'default_window_size']
        for key in required_keys:
            self.assertIn(key, APP_CONFIG)

        # Test window title
        self.assertIsInstance(APP_CONFIG['window_title'], str)
        self.assertTrue(len(APP_CONFIG['window_title']) > 0)

        # Test window sizes
        self.assertIsInstance(APP_CONFIG['min_window_size'], (list, tuple))
        self.assertEqual(len(APP_CONFIG['min_window_size']), 2)

        self.assertIsInstance(APP_CONFIG['default_window_size'], (list, tuple))
        self.assertEqual(len(APP_CONFIG['default_window_size']), 2)

        # Test that sizes are positive integers
        for size in APP_CONFIG['min_window_size']:
            self.assertIsInstance(size, int)
            self.assertGreater(size, 0)

        for size in APP_CONFIG['default_window_size']:
            self.assertIsInstance(size, int)
            self.assertGreater(size, 0)

    def test_status_color_consistency(self):
        """Test that all status options have corresponding colors."""
        # Every status in JOB_STATUS_OPTIONS should have a color
        for status in JOB_STATUS_OPTIONS:
            self.assertIn(status, STATUS_COLORS,
                         f"Status '{status}' is missing a color mapping")

        # Every color should correspond to a valid status
        for status in STATUS_COLORS:
            self.assertIn(status, JOB_STATUS_OPTIONS,
                         f"Color for '{status}' exists but status is not in options")


if __name__ == "__main__":
    unittest.main(verbosity=2)
