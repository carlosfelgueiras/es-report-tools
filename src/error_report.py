"""
Error report generator - creates a table view of validation errors by task.
"""
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum

class GlobalErrorType(Enum):
    """Categories of validation errors."""
    MEMBER_URL_FORMAT = "Member URL format"
    MEMBER_NOT_EXISTS = "Member does not exist"
    ISSUE_URL_FORMAT = "Issue URL format"
    ISSUE_NOT_EXISTS = "Issue does not exist"
    SCREENSHOT_NOT_FOUND = "Screenshot missing"
    SCREENSHOT_PATH_FORMAT = "Screenshot path format"

class TaskErrorType(Enum):
    """Categories of validation errors."""
    MISSING_COMMITTER = "Missing committer"
    COMMITTER_NOT_MEMBER = "Committer is not a member"
    COMMITTER_URL_FORMAT = "Committer URL format"
    COMMITTER_NOT_EXISTS = "Committer does not exist"
    ISSUE_URL_FORMAT = "Issue URL format"
    ISSUE_NOT_EXISTS = "Issue does not exist"
    MR_URL_FORMAT = "MR URL format"
    MR_NOT_EXISTS = "MR does not exist"
    MR_AUTHOR_MISMATCH = "MR Author ≠ Committer"
    MR_NO_REVIEWER = "MR has no reviewer"
    MR_REVIEWER_EQUALS_COMMITTER = "Reviewer = Committer"
    COMMIT_FETCH_FAILED = "Commits fetch failed"
    COMMIT_MESSAGE_FORMAT = "Commit not conventional"
    COMMIT_NO_CLOSES = "Commit missing 'Closes #'"
    COMMIT_EMAIL_NOT_TECNICO = "Commit Email Not Técnico"
    SCREENSHOT_NOT_FOUND = "Screenshot missing"
    SCREENSHOT_PATH_FORMAT = "Screenshot path format"

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