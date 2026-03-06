#!/usr/bin/env python3
"""
Example usage of the error reporting system.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from error_report import generate_error_table
from error_report_html import write_error_report_html


# Example errors from validation
EXAMPLE_ERRORS = [
    "Task 1: missing committer.",
    "Task 1: issue URL must be 'https://...-/issues/42', got 'https://...-/issues/43'",
    "Task 2, MR !5: reviewer equals committer (ist123456).",
    "Task 2, MR !5, commit abc123: commit message does not follow conventional commits format.",
    "Task 2, MR !5, commit abc123: commit author email must be from Técnico, got example@gmail.com.",
    "Task 2, MR !5: no commit message contains 'Closes #42'.",
    "Task 3: committer user does not exist (or not visible): https://...",
    "Task 3: MR does not exist (or no access): https://...",
    "Total coverage: screenshot file not found: images/coverage.png",
]

TASKS = [
    {"id": "1", "title": "Implement user authentication"},
    {"id": "2", "title": "Add database integration"},
    {"id": "3", "title": "Setup CI/CD pipeline"},
]


def main():
    output_file = "error_report.html"
    
    # Write to HTML file
    write_error_report_html(EXAMPLE_ERRORS, TASKS, output_file)
    print(f"✓ Error report written to: {output_file}")
    
    # Also print quick summary to console
    print("\n" + "=" * 70)
    print("ERROR REPORTING DEMO - Quick Preview")
    print("=" * 70)
    print("\n--- ERROR TABLE (✓ = no errors, ✗ = has errors) ---\n")
    table = generate_error_table(EXAMPLE_ERRORS, TASKS)
    print(table)
    print("\nOpen error_report.html in a browser for full details.")


if __name__ == "__main__":
    main()
