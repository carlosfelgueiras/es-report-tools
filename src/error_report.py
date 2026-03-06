"""
Error report generator - creates a table view of validation errors by task.
"""
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum


class ErrorType(Enum):
    """Categories of validation errors."""
    MISSING_COMMITTER = "Missing Committer"
    COMMITTER_NOT_MEMBER = "Committer Not Member"
    COMMITTER_PROFILE_FORMAT = "Committer Profile Format"
    COMMITTER_NOT_EXISTS = "Committer Doesn't Exist"
    ISSUE_URL_FORMAT = "Issue URL Format"
    ISSUE_NOT_EXISTS = "Issue Doesn't Exist"
    MR_URL_FORMAT = "MR URL Format"
    MR_NOT_EXISTS = "MR Doesn't Exist"
    MR_AUTHOR_MISMATCH = "MR Author ≠ Committer"
    MR_NO_REVIEWER = "MR No Reviewer"
    MR_REVIEWER_EQUALS_COMMITTER = "Reviewer = Committer"
    COMMIT_FETCH_FAILED = "Commits Fetch Failed"
    COMMIT_MESSAGE_FORMAT = "Commit Not Conventional"
    COMMIT_NO_CLOSES = "Commit Missing 'Closes #'"
    COMMIT_EMAIL_NOT_TECNICO = "Commit Email Not Técnico"
    SCREENSHOT_NOT_FOUND = "Screenshot Missing"
    SCREENSHOT_PATH_FORMAT = "Screenshot Path Format"


ERROR_PATTERNS = {
    ErrorType.MISSING_COMMITTER: ["missing committer"],
    ErrorType.COMMITTER_NOT_MEMBER: ["committer", "not a group member"],
    ErrorType.COMMITTER_PROFILE_FORMAT: ["committer profile URL must be"],
    ErrorType.COMMITTER_NOT_EXISTS: ["committer user does not exist"],
    ErrorType.ISSUE_URL_FORMAT: ["issue URL must be"],
    ErrorType.ISSUE_NOT_EXISTS: ["issue does not exist"],
    ErrorType.MR_URL_FORMAT: ["MR URL must be"],
    ErrorType.MR_NOT_EXISTS: ["MR does not exist"],
    ErrorType.MR_AUTHOR_MISMATCH: ["MR author must be the committer"],
    ErrorType.MR_NO_REVIEWER: ["cannot determine reviewer"],
    ErrorType.MR_REVIEWER_EQUALS_COMMITTER: ["reviewer equals committer"],
    ErrorType.COMMIT_FETCH_FAILED: ["could not fetch MR commits"],
    ErrorType.COMMIT_MESSAGE_FORMAT: ["does not follow conventional commits format"],
    ErrorType.COMMIT_NO_CLOSES: ["no commit message contains", "Closes #"],
    ErrorType.COMMIT_EMAIL_NOT_TECNICO: ["commit author email must be from Técnico"],
    ErrorType.SCREENSHOT_NOT_FOUND: ["screenshot file not found"],
    ErrorType.SCREENSHOT_PATH_FORMAT: ["screenshot path must be under images"],
}


@dataclass
class TaskError:
    """Represents an error for a task."""
    task_id: str
    error_type: ErrorType
    message: str


def categorize_errors(errors: List[str]) -> Dict[str, List[TaskError]]:
    """
    Parse validation errors and categorize by task.
    
    Returns: Dict[task_id, List[TaskError]]
    """
    task_errors: Dict[str, List[TaskError]] = {}  # key: task_id
    
    for error in errors:
        task_id = None
        error_type = None
        
        # Extract task ID (format: "Task <id>: ..." or "Task <id>, MR !<mr>: ...")
        if error.startswith("Task "):
            parts = error.split(":")
            if parts:
                task_part = parts[0]  # e.g., "Task 1" or "Task 1, MR !5, commit abc123"
                task_id = task_part.split()[1].rstrip(",")
        
        # Categorize error by matching patterns
        for err_type, patterns in ERROR_PATTERNS.items():
            if all(pattern.lower() in error.lower() for pattern in patterns):
                error_type = err_type
                break
        
        if error_type is None:
            error_type = ErrorType.SCREENSHOT_PATH_FORMAT  # Default fall-through
        
        if task_id:
            if task_id not in task_errors:
                task_errors[task_id] = []
            task_errors[task_id].append(TaskError(task_id, error_type, error))
    
    return task_errors


def generate_error_table(errors: List[str], tasks: List[dict]) -> str:
    """
    Generate a formatted table of errors by task.
    
    Args:
        errors: List of error strings from validate_report()
        tasks: List of task dicts with 'id' and 'title' keys
    
    Returns:
        Formatted table string
    """
    categorized = categorize_errors(errors)
    
    # Define all error types to show as columns
    error_types = list(ErrorType)
    
    # Header
    header_cells = ["Task ID", "Task Title"] + [et.value for et in error_types]
    col_widths = [10, 25] + [16] * len(error_types)
    
    # Adjust column widths to fit content
    for task in tasks:
        task_id = str(task.get("id", ""))
        task_title = str(task.get("title", ""))
        col_widths[0] = max(col_widths[0], len(task_id))
        col_widths[1] = max(col_widths[1], len(task_title))
    
    # Build table
    lines = []
    
    # Header row
    header = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(header_cells))
    lines.append(header)
    lines.append("-" * len(header))
    
    # Data rows
    for task in tasks:
        task_id = str(task.get("id", ""))
        task_title = str(task.get("title", ""))
        row_cells = [task_id, task_title]
        
        for error_type in error_types:
            # Check if this task has this error type
            if task_id in categorized:
                errors_for_type = [
                    te for te in categorized[task_id]
                    if te.error_type == error_type
                ]
                if errors_for_type:
                    cell_value = "✗"
                else:
                    cell_value = "✓"
            else:
                cell_value = "✓"
            
            row_cells.append(cell_value)
        
        row = " | ".join(f"{str(c):<{col_widths[i]}}" for i, c in enumerate(row_cells))
        lines.append(row)
    
    return "\n".join(lines)


def generate_error_summary(errors: List[str], tasks: List[dict]) -> str:
    """
    Generate a detailed summary of errors by task.
    
    Args:
        errors: List of error strings from validate_report()
        tasks: List of task dicts with 'id' and 'title' keys
    
    Returns:
        Formatted summary string
    """
    categorized = categorize_errors(errors)
    task_ids = [str(t.get("id", "")) for t in tasks]
    task_map = {str(t.get("id", "")): t.get("title", "") for t in tasks}
    
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append("VALIDATION ERROR SUMMARY")
    lines.append("=" * 70)
    
    total_errors = len(errors)
    affected_tasks = len(categorized)
    
    lines.append(f"\nTotal Errors: {total_errors}")
    lines.append(f"Affected Tasks: {affected_tasks}/{len(task_ids)}")
    
    if not categorized:
        lines.append("\n✓ No errors found!")
        return "\n".join(lines)
    
    lines.append("\n" + "-" * 70)
    
    for task_id in task_ids:
        if task_id in categorized:
            task_title = task_map.get(task_id, "")
            task_errs = categorized[task_id]
            lines.append(f"\n[Task {task_id}: {task_title}] - {len(task_errs)} error(s):")
            
            # Group by error type
            by_type: Dict[ErrorType, List[str]] = {}
            for te in task_errs:
                if te.error_type not in by_type:
                    by_type[te.error_type] = []
                by_type[te.error_type].append(te.message)
            
            for error_type, msgs in by_type.items():
                lines.append(f"  • {error_type.value}:")
                for msg in msgs:
                    lines.append(f"    - {msg}")
    
    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


