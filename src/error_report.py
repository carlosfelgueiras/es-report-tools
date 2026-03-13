"""
Error report generator - creates a table view of validation errors by task.
"""
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum

class GlobalErrorType(Enum):
    """Categories of validation errors."""
    MEMBER = "Member URL"
    ISSUE = "Issue URL"
    CODE_COVERAGE = "Code coverage"

class TaskErrorType(Enum):
    """Categories of validation errors."""
    COMMITTER = "Committer exists and is a member"
    MERGE_REQUEST = "Merge request"
    REVIEW = "Review"
    COMMIT = "Commit format and issue link"
    CODE_COVERAGE = "Code coverage"

@dataclass
class GlobalError:
    error_type: GlobalErrorType
    message: str

@dataclass
class TaskError:
    """Represents an error for a task."""
    task_id: str
    error_type: TaskErrorType
    message: str