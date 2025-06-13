#!/usr/bin/env python3
"""
Test script for job parsing logic.

This module contains tests for the job parsing functionality.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.job_tracker.core.parser import (
    parse_job_info, _parse_job_title_fast, _parse_company_fast,
    _parse_location_fast, _is_valid_location, _clean_location,
    _is_valid_job_title, _clean_job_title
)


class TestJobParsing(unittest.TestCase):
    """Test cases for job parsing functionality."""

    def test_parse_job_info_with_valid_url(self):
        """Test parsing with a mock valid URL."""
        # This would require a full browser setup, so we'll mock it
        with patch('src.job_tracker.core.parser.get_browser') as mock_browser:
            # For now, just test that the function exists and handles errors
            result = parse_job_info("https://example.com/job")
            # Should return None or a dict with job info
            self.assertIsInstance(result, (dict, type(None)))

    def test_is_valid_location(self):
        """Test location validation logic."""
        from src.job_tracker.core.parser import _is_valid_location

        # Valid locations
        valid_locations = [
            "San Francisco, CA",
            "Remote",
            "New York, NY",
            "Work from home",
            "Chicago, IL",
            "Seattle, Washington"
        ]

        for location in valid_locations:
            with self.subTest(location=location):
                self.assertTrue(_is_valid_location(location),
                               f"Should recognize '{location}' as valid location")

        # Invalid locations
        invalid_locations = [
            "Apply now for this position",
            "Requirements: 5 years experience",
            "Job description and responsibilities",
            "",
            "a",
            "This is a very long text that contains way too many words to be a location"
        ]

        for location in invalid_locations:
            with self.subTest(location=location):
                self.assertFalse(_is_valid_location(location),
                                f"Should not recognize '{location}' as valid location")

    def test_clean_location(self):
        """Test location cleaning logic."""
        from src.job_tracker.core.parser import _clean_location

        test_cases = [
            ("Location: San Francisco, CA", "San Francisco, CA"),
            ("Based in New York", "New York"),
            ("Remote work from home", "Remote"),
            ("WFH opportunity", "Remote"),
            ("City: Chicago, IL", "Chicago, IL"),
            ("  Seattle, WA  ", "Seattle, WA")
        ]

        for input_location, expected in test_cases:
            with self.subTest(input_location=input_location):
                result = _clean_location(input_location)
                self.assertEqual(result, expected,
                               f"Expected '{expected}' but got '{result}'")

    def test_is_valid_job_title(self):
        """Test job title validation logic."""
        from src.job_tracker.core.parser import _is_valid_job_title

        # Valid job titles
        valid_titles = [
            "Software Engineer",
            "Senior Python Developer",
            "Data Scientist - Machine Learning",
            "Product Manager",
            "Marketing Coordinator",
            "Full Stack Developer"
        ]

        for title in valid_titles:
            with self.subTest(title=title):
                self.assertTrue(_is_valid_job_title(title),
                               f"Should recognize '{title}' as valid job title")

        # Invalid job titles
        invalid_titles = [
            "Apply now",
            "Click here to view",
            "Job search results",
            "Company profile information",
            "",
            "ab"
        ]

        for title in invalid_titles:
            with self.subTest(title=title):
                self.assertFalse(_is_valid_job_title(title),
                                f"Should not recognize '{title}' as valid job title")

    def test_clean_job_title(self):
        """Test job title cleaning logic."""
        from src.job_tracker.core.parser import _clean_job_title

        test_cases = [
            ("Job Title: Software Engineer", "Software Engineer"),
            ("Position: Data Scientist", "Data Scientist"),
            ("Apply for Product Manager", "Product Manager"),
            ("  Senior Developer  ", "Senior Developer"),
            ("Role: Marketing Specialist", "Marketing Specialist")
        ]

        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = _clean_job_title(input_title)
                self.assertEqual(result, expected,
                               f"Expected '{expected}' but got '{result}'")


class TestJobTypeValidation(unittest.TestCase):
    """Test cases for job type validation."""

    def test_job_type_patterns(self):
        """Test job type pattern recognition."""
        from src.job_tracker.core.parser import _is_valid_job_type, _clean_job_type

        # Test job type cleaning
        job_type_tests = [
            ("Full-time position", "Full-time"),
            ("Part time work", "Part-time"),
            ("Contract role", "Contract"),
            ("Temporary assignment", "Temporary"),
            ("Remote opportunity", "Remote"),
            ("Hybrid work model", "Hybrid")
        ]

        for input_type, expected in job_type_tests:
            with self.subTest(input_type=input_type):
                self.assertTrue(_is_valid_job_type(input_type),
                               f"Should recognize '{input_type}' as valid job type")
                cleaned = _clean_job_type(input_type)
                self.assertEqual(cleaned, expected,
                               f"Expected '{expected}' but got '{cleaned}'")


def run_manual_tests():
    """Run manual tests with actual URLs if provided."""
    print("\n" + "="*50)
    print("MANUAL TESTING")
    print("="*50)

    # Sample job URLs to test (replace with actual URLs for manual testing)
    test_urls = [
        # Add real job posting URLs here to test
        # "https://jobs.example.com/software-engineer",
        # "https://careers.company.com/data-scientist"
    ]

    if not test_urls:
        print("No test URLs provided.")
        print("To test with real URLs:")
        print("1. Add real job posting URLs to the test_urls list")
        print("2. Uncomment the URLs and run the tests")
        print("\nExample:")
        print('test_urls = [')
        print('    "https://jobs.example.com/software-engineer",')
        print('    "https://careers.company.com/data-scientist"')
        print(']')
        return

    for i, url in enumerate(test_urls, 1):
        print(f"\nTest {i}: {url}")
        print("-" * 40)

        try:
            info = parse_job_info(url)
            if info:
                print(f"✓ Job Title: {info.get('Job Title', 'Unknown')}")
                print(f"✓ Company: {info.get('Company', 'Unknown')}")
                print(f"✓ Location: {info.get('Location', 'Unknown')}")
            else:
                print("✗ Failed to parse job information")

        except Exception as e:
            print(f"✗ Error parsing job: {e}")


if __name__ == "__main__":
    # Run unit tests
    print("Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)

    # Run manual tests
    run_manual_tests()

    print("\n" + "="*50)
    print("TESTING COMPLETE")
    print("="*50)
    print("Ready to test with real job URLs!")
    print("Edit the test_urls list in run_manual_tests() and run again.")
