#!/usr/bin/env python3
"""
Script to create test data for the Job Application Tracker.

This script generates realistic test data with various job applications,
statuses, and companies to showcase the application's functionality.
"""

import openpyxl
import os
from pathlib import Path


def create_test_data():
    """Create comprehensive test data for the job application tracker."""

    # Create a new workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Applications"

    # Headers matching the application structure
    headers = ["Status", "Date Applied", "Company", "Job Title", "Location", "Link"]
    ws.append(headers)

    # Comprehensive test data with variety of companies, positions, and statuses
    test_data = [
        ["Applied", "2024-01-15", "Google", "Senior Software Engineer", "Mountain View, CA", "https://careers.google.com/jobs/12345"],
        ["Phone Interview", "2024-01-12", "Microsoft", "Cloud Solutions Architect", "Seattle, WA", "https://careers.microsoft.com/us/en/job/67890"],
        ["Technical Interview", "2024-01-10", "Amazon", "Full Stack Developer", "Austin, TX", "https://amazon.jobs/en/jobs/11111"],
        ["Applied", "2024-01-18", "Meta", "Product Manager", "Menlo Park, CA", "https://careers.meta.com/jobs/22222"],
        ["Rejected", "2024-01-05", "Netflix", "Data Scientist", "Los Gatos, CA", "https://jobs.netflix.com/jobs/33333"],
        ["Applied", "2024-01-20", "Apple", "iOS Developer", "Cupertino, CA", "https://jobs.apple.com/en-us/details/44444"],
        ["No response", "2023-12-28", "Tesla", "Software Engineer", "Palo Alto, CA", "https://tesla.com/careers/55555"],
        ["Phone Interview", "2024-01-14", "Salesforce", "DevOps Engineer", "San Francisco, CA", "https://salesforce.com/careers/66666"],
        ["Applied", "2024-01-22", "Stripe", "Backend Engineer", "San Francisco, CA", "https://stripe.com/jobs/77777"],
        ["Technical Interview", "2024-01-08", "Airbnb", "Frontend Developer", "San Francisco, CA", "https://careers.airbnb.com/88888"],
        ["Applied", "2024-01-17", "Uber", "Machine Learning Engineer", "San Francisco, CA", "https://uber.com/careers/99999"],
        ["Applied", "2024-01-19", "Spotify", "Data Engineer", "New York, NY", "https://lifeatspotify.com/jobs/111111"],
        ["Rejected", "2024-01-03", "LinkedIn", "Software Engineer", "Sunnyvale, CA", "https://linkedin.com/jobs/222222"],
        ["Phone Interview", "2024-01-16", "Dropbox", "Site Reliability Engineer", "San Francisco, CA", "https://dropbox.com/jobs/333333"],
        ["Applied", "2024-01-21", "Slack", "Full Stack Engineer", "San Francisco, CA", "https://slack.com/careers/444444"],
        ["No response", "2023-12-30", "Twitter", "Security Engineer", "San Francisco, CA", "https://careers.twitter.com/555555"],
        ["Applied", "2024-01-23", "Adobe", "UX Engineer", "San Jose, CA", "https://adobe.com/careers/666666"],
        ["Technical Interview", "2024-01-11", "Atlassian", "Platform Engineer", "San Francisco, CA", "https://atlassian.com/careers/777777"],
        ["Applied", "2024-01-13", "Zoom", "Quality Assurance Engineer", "San Jose, CA", "https://zoom.us/careers/888888"],
        ["Applied", "2024-01-24", "Twilio", "API Developer", "San Francisco, CA", "https://twilio.com/careers/999999"]
    ]

    # Add all test data to the worksheet
    for row in test_data:
        ws.append(row)

    # Format the worksheet for better presentation
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Create output directory if it doesn't exist
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save the workbook
    output_path = output_dir / "job_applications.xlsx"
    wb.save(output_path)

    print(f"Test data created successfully at: {output_path}")
    print(f"Total applications: {len(test_data)}")

    # Print statistics
    status_counts = {}
    for row in test_data:
        status = row[0]
        status_counts[status] = status_counts.get(status, 0) + 1

    print("\nStatus breakdown:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    return output_path


if __name__ == "__main__":
    create_test_data()
