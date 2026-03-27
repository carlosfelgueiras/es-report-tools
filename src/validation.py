# validation.py
from __future__ import annotations

import json
import re
import subprocess
import requests

from pathlib import Path
from typing import List, Optional
from urllib.parse import quote, urlencode
from report_types import Report
from error_report import GlobalError, TaskError, GlobalErrorType, TaskErrorType

GITLAB_BASE = "https://gitlab.rnl.tecnico.ulisboa.pt"
FILES_PER_TASK_PATH = Path(__file__).with_name("files_per_task.json")

# Strict formats
IMAGE_RE = re.compile(r"^images/.+\.png$")


# ----------------------------
# GitLab API helpers
# ----------------------------

def _gitlab_get_json(base: str, token: str, path: str) -> tuple[int, object | None]:
    url = base.rstrip("/") + path
    try:
        r = requests.get(url, headers={"PRIVATE-TOKEN": token}, timeout=10)
    except requests.RequestException:
        return -1, None

    if r.status_code != 200:
        return r.status_code, None

    try:
        return 200, r.json()
    except ValueError:
        return 200, None


def _user_exists(base: str, token: str, username: str) -> bool:
    # Use lower() so IST/IsT/ist all query the same canonical username
    q = urlencode({"username": username.lower()})
    status, data = _gitlab_get_json(base, token, f"/api/v4/users?{q}")
    return status == 200 and isinstance(data, list) and len(data) > 0


def _issue_exists(base: str, token: str, project_path: str, iid: int) -> bool:
    proj = quote(project_path, safe="")
    status, _ = _gitlab_get_json(base, token, f"/api/v4/projects/{proj}/issues/{iid}")
    return status == 200


def _get_mr(base: str, token: str, project_path: str, iid: int) -> dict | None:
    proj = quote(project_path, safe="")
    status, data = _gitlab_get_json(base, token, f"/api/v4/projects/{proj}/merge_requests/{iid}")
    return data if status == 200 and isinstance(data, dict) else None


def _get_mr_commits(base: str, token: str, project_path: str, iid: int) -> list[dict] | None:
    proj = quote(project_path, safe="")
    status, data = _gitlab_get_json(base, token, f"/api/v4/projects/{proj}/merge_requests/{iid}/commits")
    return data if status == 200 and isinstance(data, list) else None


def _commit_closes_issue(message: str, issue_iid: int) -> bool:
    pattern = re.compile(rf"closes\s*#{issue_iid}(?!\d)", re.IGNORECASE)
    return pattern.search(message) is not None


def _get_mr_java_diffs(base: str, token: str, project_path: str, iid: int) -> list[str] | None:
    """Return all added/modified .java file paths in a MR. Returns None on API error."""
    proj = quote(project_path, safe="")
    per_page = 100
    page = 1
    java_files: list[str] = []

    while True:
        q = urlencode({"per_page": per_page, "page": page})
        status, data = _gitlab_get_json(base, token, f"/api/v4/projects/{proj}/merge_requests/{iid}/diffs?{q}")

        if status != 200 or not isinstance(data, list):
            return None

        if not data:
            break

        for diff in data:
            if not isinstance(diff, dict):
                continue

            new_path = str(diff.get("new_path", ""))
            if new_path.endswith(".java") and not diff.get("deleted_file", False):
                java_files.append(new_path)

        if len(data) < per_page:
            break

        page += 1

    return java_files


def _get_all_sprint_1_commits(base: str, token: str, project_path: str) -> list[dict] | None:
    proj = quote(project_path, safe="")
    per_page = 100
    page = 1
    all_commits = []

    while True:
        params = {
            "ref_name": "sprint-1",
            "per_page": per_page,
            "page": page,
            "since": "2026-02-18T17:59:02Z",
        }
        q = urlencode(params)
        status, data = _gitlab_get_json(base, token, f"/api/v4/projects/{proj}/repository/commits?{q}")

        if status != 200 or not isinstance(data, list):
            return None

        if not data:
            break

        for commit in data:
            if isinstance(commit, dict):
                all_commits.append(commit)

        if len(data) < per_page:
            break

        page += 1

    return all_commits


def _extract_usernames(users_field) -> set[str]:
    out: set[str] = set()
    if isinstance(users_field, list):
        for u in users_field:
            if isinstance(u, dict) and isinstance(u.get("username"), str):
                out.add(u["username"])
    return out


def _lint_commit_message_with_cli(message: str) -> bool:
    result = subprocess.run(
        ["commitlint", "--hide-input", message],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _load_expected_files_per_task() -> dict[str, set[str]]:
    """Load expected Java file names per task from files_per_task.json."""
    try:
        with FILES_PER_TASK_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}

    if not isinstance(raw, dict):
        return {}

    expected_files: dict[str, set[str]] = {}
    for task_id, files in raw.items():
        if not isinstance(task_id, str) or not isinstance(files, list):
            continue

        expected_files[task_id] = {
            file_name.strip()
            for file_name in files
            if isinstance(file_name, str) and file_name.strip()
        }

    return expected_files


def ist_id_fix(ist_id: str) -> str:
        ist_id = ist_id.strip()
        
        if ist_id.isdigit():
            return f"ist1{ist_id}"
        
        return ist_id

# ----------------------------
# Main validation
# ----------------------------

def validate_report(
    report: Report,
    markdown_path: str,
    gitlab_token: Optional[str],
    gitlab_base: str = GITLAB_BASE,
) -> dict[str, list]:
    """
    Strict, non-redundant checks:
      1) For EVERY link: must be correct in the report, then must exist (API / filesystem).
         - Profile URLs: must equal base/<ist_id> (case-insensitive), and user exists.
         - Issue URLs: must equal base/es/es26-cc-nn/-/issues/<id> (case-insensitive), and issue exists.
         - MR URLs: must equal base/es/es26-cc-nn/-/merge_requests/<id> (case-insensitive), and MR exists.
      2) Committer is a member of the group.
      3) Reviewer != committer, where committer is MR author (opener).
      4) Screenshot files must exist and be under images/ relative to the markdown folder.
            5) In each MR, at least one commit message must contain "Closes #<issue_id>" for the task issue, each message must be a convetiona commit and the e-mail must be from Técnico.
            6) For each task, only the first MR (lowest id) can change the Java files listed in files_per_task.json.
    """
    errors: dict[str, list] = {"global_errors": [], "task_errors": {}}

    if not gitlab_token or not gitlab_token.strip():
        return ["Missing GITLAB_TOKEN: required to verify link existence via GitLab API."]

    md_dir = Path(markdown_path).resolve().parent

    expected_suffix = f"{report['group']['campus'].lower()}-{report['group']['number']:02d}"
    project_path = f"es/es26-{expected_suffix}"

    member_ist_ids = {ist_id_fix(m["ist_id"]) for m in report["group"]["members"]}
    expected_files_per_task = _load_expected_files_per_task()

    # ----------------------------
    # 4) Screenshots
    # ----------------------------
    def check_image(path_str: str, task_id: str) -> None:
        if not IMAGE_RE.match(path_str):
            if task_id == None:
                errors["global_errors"].append(GlobalError(GlobalErrorType.CODE_COVERAGE,
                    f"Total coverage: screenshot path must be under images/ and end in .png: {path_str}"
                ))
            else:
                errors["task_errors"][task_id].append(TaskError(task_id, TaskErrorType.CODE_COVERAGE,
                    f"{task_id}: screenshot path must be under images/ and end in .png: {path_str}"
                ))
            return
        full = md_dir / path_str
        if not full.is_file():
            if task_id == None:
                errors["global_errors"].append(GlobalError(GlobalErrorType.CODE_COVERAGE,
                    f"Total coverage: screenshot file not found: {path_str}"
                ))
            else:
                errors["task_errors"][task_id].append(TaskError(task_id, TaskErrorType.CODE_COVERAGE,
                    f"T{task_id}: screenshotfile not found: {path_str}"
                ))

    check_image(report["total_coverage"]["path"], None)
    for task in report["tasks"]:
        errors["task_errors"][task['id']] = []
        if not task.get("coverage"):
            errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.CODE_COVERAGE,
                f"Task {task['id']}: no code coverage assigned to task."
            ))
        for cov in task["coverage"]:
            check_image(cov["path"], task['id'])

    # ----------------------------
    # 1) Members: profile + assigned issues
    # ----------------------------
    for member in report["group"]["members"]:
        expected_profile_url = f"{gitlab_base}/{ist_id_fix(member['ist_id'])}"

        # One strict check (case-insensitive)
        if member["gitlab"].lower() != expected_profile_url.lower():
            errors["global_errors"].append(GlobalError(GlobalErrorType.MEMBER,
                f"Member {ist_id_fix(member['ist_id'])}: profile URL must be '{expected_profile_url}', got '{member['gitlab']}'"
            ))
        else:
            if not _user_exists(gitlab_base, gitlab_token, ist_id_fix(member['ist_id'])):
                errors["global_errors"].append(GlobalError(GlobalErrorType.MEMBER,
                    f"Member {ist_id_fix(member['ist_id'])}: GitLab user does not exist (or not visible): {member['gitlab']}"
                ))

        for issue in member["issues"]:
            expected_issue_url = f"{gitlab_base}/es/es26-{expected_suffix}/-/issues/{issue['id']}"
            if issue["url"].lower() != expected_issue_url.lower():
                errors["global_errors"].append(GlobalError(GlobalErrorType.ISSUE,
                    f"Member {ist_id_fix(member['ist_id'])}: issue URL must be '{expected_issue_url}', got '{issue['url']}'"
                ))
            else:
                if not _issue_exists(gitlab_base, gitlab_token, project_path, issue["id"]):
                    errors["global_errors"].append(GlobalError(GlobalErrorType.ISSUE,
                        f"Member {ist_id_fix(member['ist_id'])}: issue does not exist (or no access): {issue['url']}"))

    # ----------------------------
    # 2) + 1) + 3) Tasks
    # ----------------------------
    for task in report["tasks"]:
        if task["committer"] is None:
            errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMITTER, 
                f"Task {task['id']}: Missing committer."
            ))
            continue
        
        if not task.get("committer"):
            errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMITTER,
                f"Task {task['id']}: no commiter assigned to task."
            ))

        comm = task["committer"]

        # 2) committer is member
        if ist_id_fix(comm["ist_id"]) not in member_ist_ids:
            errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMITTER,
                f"Task {task['id']}: committer {ist_id_fix(comm['ist_id'])} is not a group member."
            ))

        # 1) committer profile strict + exists
        expected_comm_profile_url = f"{gitlab_base}/{ist_id_fix(comm['ist_id'])}"
        if comm["gitlab"].lower() != expected_comm_profile_url.lower():
            errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMITTER,
                f"Task {task['id']}: committer profile URL must be '{expected_comm_profile_url}', got '{comm['gitlab']}'"
            ))
        else:
            if not _user_exists(gitlab_base, gitlab_token, ist_id_fix(comm['ist_id'])):
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMITTER,
                    f"Task {task['id']}: committer user does not exist (or not visible): {comm['gitlab']}"
                ))

        # task issues
        if not task.get("issues"):
            errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMIT,
                f"Task {task['id']}: no issue assigned to task."
            ))


        task_issue_id = task["issues"][0]["id"] if task["issues"] else None
        for issue in task["issues"]:
            expected_issue_url = f"{gitlab_base}/es/es26-{expected_suffix}/-/issues/{issue['id']}"
            if issue["url"].lower() != expected_issue_url.lower():
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMIT,
                    f"Task {task['id']}: issue URL must be '{expected_issue_url}', got '{issue['url']}'"
                ))
            else:
                if not _issue_exists(gitlab_base, gitlab_token, project_path, issue["id"]):
                    errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMIT, 
                        f"Task {task['id']}: issue does not exist (or no access): {issue['url']}"
                    ))

        # MRs
        if not task.get("mrs"):
            errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.MERGE_REQUEST,
                f"Task {task['id']}: no merge request assigned to task."
            ))

        first_mr = min(task["mrs"], key=lambda mr: mr["id"]) if task["mrs"] else None
        for mr in task["mrs"]:
            expected_mr_url = f"{gitlab_base}/es/es26-{expected_suffix}/-/merge_requests/{mr['id']}"
            if mr["url"].lower() != expected_mr_url.lower():
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.MERGE_REQUEST,
                    f"Task {task['id']}: MR URL must be '{expected_mr_url}', got '{mr['url']}'"
                ))
                continue

            mr_data = _get_mr(gitlab_base, gitlab_token, project_path, mr["id"])
            if mr_data is None:
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.MERGE_REQUEST,
                    f"Task {task['id']}: MR does not exist (or no access): {mr['url']}"
                ))
                continue

            # 3) MR author must be committer (case-insensitive)
            author = mr_data.get("author")
            author_username = author.get("username") if isinstance(author, dict) else None
            committer_ist_id = ist_id_fix(comm["ist_id"])
            if not isinstance(author_username, str) or author_username.lower() != committer_ist_id.lower():
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.MERGE_REQUEST,
                    f"Task {task['id']}, MR !{mr['id']}: MR author must be the committer "
                    f"(expected {committer_ist_id}, got {author_username})."
                ))
            
            # Assignee must be the same as commiter
            assignees = _extract_usernames(mr_data.get("assignees"))

            if not assignees:
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.REVIEW,
                    f"Task {task['id']}, MR !{mr['id']}: cannot determine assignee (no assignees)."
                ))
            elif committer_ist_id.lower() not in {a.lower() for a in assignees}:
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.REVIEW,
                    f"Task {task['id']}, MR !{mr['id']}: committer ({committer_ist_id}) must be an assignee."
                ))

            reviewers = _extract_usernames(mr_data.get("reviewers"))

            if not reviewers:
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.REVIEW,
                    f"Task {task['id']}, MR !{mr['id']}: cannot determine reviewer (no reviewers)."
                ))
            elif committer_ist_id.lower() in {r.lower() for r in reviewers}:
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.REVIEW,
                    f"Task {task['id']}, MR !{mr['id']}: reviewer equals committer ({committer_ist_id})."
                ))

            # Validate all commits in the MR
            mr_commits = _get_mr_commits(gitlab_base, gitlab_token, project_path, mr['id'])
            mr_java_diffs = _get_mr_java_diffs(gitlab_base, gitlab_token, project_path, mr['id'])
            if mr_commits is None:
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMIT,
                    f"Task {task['id']}, MR !{mr['id']}: could not fetch MR commits."
                ))
            else:
                has_closes_reference = False
                has_conventional_commit = False
                for commit in mr_commits:
                    if not isinstance(commit, dict):
                        continue
                    
                    commit_sha = str(commit.get("short_id", commit.get("id", "unknown")))
                    
                    # Validate conventional commits format
                    commit_message = str(commit.get("message", "") or "")
                    if commit_message and _lint_commit_message_with_cli(commit_message):
                        has_conventional_commit = True

                    if task_issue_id is not None and _commit_closes_issue(commit_message, task_issue_id):
                        has_closes_reference = True
                    
                    # Validate commit author email domain
                    commit_author_email = str(commit.get("author_email", "") or "")
                    if not commit_author_email.lower().endswith("@tecnico.ulisboa.pt") and not commit_author_email.lower().endswith("@rnl.tecnico.ulisboa.pt"):
                        errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMIT,
                            f"Task {task['id']}, MR !{mr['id']}, commit {commit_sha}: "
                            f"commit author email must be from Técnico, got {commit_author_email}."
                        ))

                if not has_conventional_commit:
                    errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMIT,
                        f"Task {task['id']}, MR !{mr['id']}: no commit message follows conventional commits format."
                    ))

                if task_issue_id is not None and not has_closes_reference:
                    sprint_1_commits = _get_all_sprint_1_commits(gitlab_base, gitlab_token, project_path)
                    sprint_1_closes = sprint_1_commits is not None and any(
                        _commit_closes_issue(str(c.get("message", "") or ""), task_issue_id)
                        for c in sprint_1_commits
                    )
                    if not sprint_1_closes:
                        errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.COMMIT,
                            f"Task {task['id']}, MR !{mr['id']}: no commit message contains "
                            f"'Closes #{task_issue_id}'."
                        ))

        # Check changed Java files only for the first MR (lowest MR id)
        if first_mr is not None:
            expected_task_files = expected_files_per_task.get(task["id"])
            if expected_task_files is None:
                errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.MR_FILES,
                    f"Task {task['id']}, MR !{first_mr['id']}: no expected files configured in files_per_task.json."
                ))
            else:
                changed_java_paths = _get_mr_java_diffs(gitlab_base, gitlab_token, project_path, first_mr["id"])
                if changed_java_paths is None:
                    errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.MR_FILES,
                        f"Task {task['id']}, MR !{first_mr['id']}: could not fetch changed Java files."
                    ))
                else:
                    changed_java_files = {Path(path).name for path in changed_java_paths}
                    expected_task_files_ci = {file_name.lower() for file_name in expected_task_files}

                    # Match files case-insensitively, but keep original casing for reporting.
                    changed_by_lower: dict[str, str] = {}
                    for file_name in sorted(changed_java_files):
                        changed_by_lower.setdefault(file_name.lower(), file_name)

                    unexpected_files = sorted(
                        original_name
                        for lower_name, original_name in changed_by_lower.items()
                        if lower_name not in expected_task_files_ci
                    )

                    if unexpected_files:
                        unexpected_count = len(unexpected_files)
                        errors["task_errors"][task['id']].append(TaskError(task['id'], TaskErrorType.MR_FILES,
                            f"Task {task['id']}, MR !{first_mr['id']}: contains {unexpected_count} unexpected changed "
                            f"file(s) not listed in files_per_task.json: {', '.join(unexpected_files)}."
                        ))

    return errors
