# validation.py
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote, urlencode

import requests

from report_types import Report

GITLAB_BASE = "https://gitlab.rnl.tecnico.ulisboa.pt"

# Strict formats
# - Allow IST/ist/IsT... by using IGNORECASE
PROFILE_RE = re.compile(rf"^{re.escape(GITLAB_BASE)}/ist\d{{1,7}}$", re.IGNORECASE)
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


def _is_merge_or_revert_commit(commit: dict) -> bool:
    title = str(commit.get("title", "")).strip().lower()
    message = str(commit.get("message", "")).strip().lower()
    text = title or message
    return text.startswith("merge ") or text.startswith("revert ")


def _commit_closes_issue(message: str, issue_iid: int) -> bool:
    pattern = re.compile(rf"closes\s*#{issue_iid}", re.IGNORECASE)
    return pattern.search(message) is not None


def _has_master_closing_commit(base: str, token: str, project_path: str, issue_iid: int) -> bool | None:
    proj = quote(project_path, safe="")
    per_page = 100
    page = 1

    while True:
        params = {
            "ref_name": "master",
            "search": f"#{issue_iid}",
            "per_page": per_page,
            "page": page,
            "since": "2026-02-18T17:59:02Z"
        }
        q = urlencode(params)
        status, data = _gitlab_get_json(base, token, f"/api/v4/projects/{proj}/repository/commits?{q}")

        if status != 200 or not isinstance(data, list):
            return None

        if not data:
            return False

        for commit in data:
            if not isinstance(commit, dict):
                continue

            if _is_merge_or_revert_commit(commit):
                continue

            message = str(commit.get("message", ""))
            title = str(commit.get("title", ""))
            if _commit_closes_issue(message or title, issue_iid):
                return True

        if len(data) < per_page:
            return False

        page += 1


def _extract_usernames(users_field) -> set[str]:
    out: set[str] = set()
    if isinstance(users_field, list):
        for u in users_field:
            if isinstance(u, dict) and isinstance(u.get("username"), str):
                out.add(u["username"])
    return out


def _get_all_master_commits(base: str, token: str, project_path: str) -> list[dict] | None:
    """Fetch all non-merge/non-revert commits from master branch.
    
    Returns:
        list of commits or None if API error
    """
    proj = quote(project_path, safe="")
    per_page = 100
    page = 1
    all_commits = []

    while True:
        params = {
            "ref_name": "master",
            "per_page": per_page,
            "page": page,
            "since": "2026-02-18T17:59:02Z"
        }
        q = urlencode(params)
        status, data = _gitlab_get_json(base, token, f"/api/v4/projects/{proj}/repository/commits?{q}")

        if status != 200 or not isinstance(data, list):
            return None

        if not data:
            break

        for commit in data:
            if not isinstance(commit, dict):
                continue

            if not _is_merge_or_revert_commit(commit):
                all_commits.append(commit)

        if len(data) < per_page:
            break

        page += 1

    return all_commits


def _lint_commit_message_with_cli(message: str) -> bool:
    result = subprocess.run(
        ["commitlint", "--hide-input", message],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


# ----------------------------
# Main validation
# ----------------------------

def validate_report(
    report: Report,
    markdown_path: str,
    gitlab_token: Optional[str],
    gitlab_base: str = GITLAB_BASE,
) -> List[str]:
    """
    Strict, non-redundant checks:
      1) For EVERY link: must be correct in the report, then must exist (API / filesystem).
         - Profile URLs: must equal base/<ist_id> (case-insensitive), match PROFILE_RE, and user exists.
         - Issue URLs: must equal base/es/es26-cc-nn/-/issues/<id> (case-insensitive), and issue exists.
         - MR URLs: must equal base/es/es26-cc-nn/-/merge_requests/<id> (case-insensitive), and MR exists.
      2) Committer is a member of the group.
      3) Reviewer != committer, where committer is MR author (opener).
      4) Screenshot files must exist and be under images/ relative to the markdown folder.
      5) In task issues, each issue must have at least one non-merge/non-revert commit in master that closes it.
    """
    errors: List[str] = []

    if not gitlab_token or not gitlab_token.strip():
        return ["Missing GITLAB_TOKEN: required to verify link existence via GitLab API."]

    md_dir = Path(markdown_path).resolve().parent

    expected_suffix = f"{report['group']['campus'].lower()}-{report['group']['number']:02d}"
    project_path = f"es/es26-{expected_suffix}"

    member_ist_ids = {m["ist_id"] for m in report["group"]["members"]}
    checked_task_issue_ids: set[int] = set()

    # ----------------------------
    # 4) Screenshots
    # ----------------------------
    def check_image(path_str: str, context: str) -> None:
        if not IMAGE_RE.match(path_str):
            errors.append(f"{context}: screenshot path must be under images/ and end in .png: {path_str}")
            return
        full = md_dir / path_str
        if not full.is_file():
            errors.append(f"{context}: screenshot file not found: {path_str}")

    check_image(report["total_coverage"]["path"], "Total coverage")
    for task in report["tasks"]:
        for cov in task["coverage"]:
            check_image(cov["path"], f"Task {task['id']} coverage")

    # ----------------------------
    # 1) Members: profile + assigned issues
    # ----------------------------
    for member in report["group"]["members"]:
        expected_profile_url = f"{gitlab_base}/{member['ist_id']}"

        # One strict check (case-insensitive)
        if member["gitlab"].lower() != expected_profile_url.lower():
            errors.append(
                f"Member {member['ist_id']}: profile URL must be '{expected_profile_url}', got '{member['gitlab']}'"
            )
        elif not PROFILE_RE.match(member["gitlab"]):
            errors.append(f"Member {member['ist_id']}: invalid profile URL format: {member['gitlab']}")
        else:
            if not _user_exists(gitlab_base, gitlab_token, member["ist_id"]):
                errors.append(
                    f"Member {member['ist_id']}: GitLab user does not exist (or not visible): {member['gitlab']}"
                )

        for issue in member["issues"]:
            expected_issue_url = f"{gitlab_base}/es/es26-{expected_suffix}/-/issues/{issue['id']}"
            if issue["url"].lower() != expected_issue_url.lower():
                errors.append(
                    f"Member {member['ist_id']}: issue URL must be '{expected_issue_url}', got '{issue['url']}'"
                )
            else:
                if not _issue_exists(gitlab_base, gitlab_token, project_path, issue["id"]):
                    errors.append(f"Member {member['ist_id']}: issue does not exist (or no access): {issue['url']}")

    # ----------------------------
    # 2) + 1) + 3) Tasks
    # ----------------------------
    for task in report["tasks"]:
        if task["committer"] is None:
            errors.append(f"Task {task['id']}: missing committer.")
            continue

        comm = task["committer"]

        # 2) committer is member
        if comm["ist_id"] not in member_ist_ids:
            errors.append(f"Task {task['id']}: committer {comm['ist_id']} is not a group member.")

        # 1) committer profile strict + exists
        expected_comm_profile_url = f"{gitlab_base}/{comm['ist_id']}"
        if comm["gitlab"].lower() != expected_comm_profile_url.lower():
            errors.append(
                f"Task {task['id']}: committer profile URL must be '{expected_comm_profile_url}', got '{comm['gitlab']}'"
            )
        elif not PROFILE_RE.match(comm["gitlab"]):
            errors.append(f"Task {task['id']}: invalid committer profile URL format: {comm['gitlab']}")
        else:
            if not _user_exists(gitlab_base, gitlab_token, comm["ist_id"]):
                errors.append(
                    f"Task {task['id']}: committer user does not exist (or not visible): {comm['gitlab']}"
                )

        # task issues
        for issue in task["issues"]:
            expected_issue_url = f"{gitlab_base}/es/es26-{expected_suffix}/-/issues/{issue['id']}"
            if issue["url"].lower() != expected_issue_url.lower():
                errors.append(
                    f"Task {task['id']}: issue URL must be '{expected_issue_url}', got '{issue['url']}'"
                )
            else:
                if not _issue_exists(gitlab_base, gitlab_token, project_path, issue["id"]):
                    errors.append(f"Task {task['id']}: issue does not exist (or no access): {issue['url']}")
                elif issue["id"] not in checked_task_issue_ids:
                    checked_task_issue_ids.add(issue["id"])
                    has_master_close = _has_master_closing_commit(
                        gitlab_base, gitlab_token, project_path, issue["id"]
                    )
                    if has_master_close is None:
                        errors.append(
                            f"Issue #{issue['id']}: could not verify closing commits in master branch."
                        )
                    elif not has_master_close:
                        errors.append(
                            f"Issue #{issue['id']}: no non-merge/non-revert commit in master closes this issue."
                        )

        # MRs
        for mr in task["mrs"]:
            expected_mr_url = f"{gitlab_base}/es/es26-{expected_suffix}/-/merge_requests/{mr['id']}"
            if mr["url"].lower() != expected_mr_url.lower():
                errors.append(
                    f"Task {task['id']}: MR URL must be '{expected_mr_url}', got '{mr['url']}'"
                )
                continue

            mr_data = _get_mr(gitlab_base, gitlab_token, project_path, mr["id"])
            if mr_data is None:
                errors.append(f"Task {task['id']}: MR does not exist (or no access): {mr['url']}")
                continue

            # 3) MR author must be committer (case-insensitive)
            author = mr_data.get("author")
            author_username = author.get("username") if isinstance(author, dict) else None
            if not isinstance(author_username, str):
                errors.append(f"Task {task['id']}, MR !{mr['id']}: could not read MR author from API.")
            elif author_username.lower() != comm["ist_id"].lower():
                errors.append(
                    f"Task {task['id']}, MR !{mr['id']}: MR author must be the committer "
                    f"(expected {comm['ist_id']}, got {author_username})."
                )

            reviewers = _extract_usernames(mr_data.get("reviewers"))
            if not reviewers:
                reviewers = _extract_usernames(mr_data.get("assignees"))

            if not reviewers:
                errors.append(f"Task {task['id']}, MR !{mr['id']}: cannot determine reviewer (no reviewers/assignees).")
            elif comm["ist_id"].lower() in {r.lower() for r in reviewers}:
                errors.append(f"Task {task['id']}, MR !{mr['id']}: reviewer equals committer ({comm['ist_id']}).")

    # Get all non-merge/non-revert commits from master and validate with commitlint
    commits = _get_all_master_commits(gitlab_base, gitlab_token, project_path)
    if commits is not None:
        for commit in commits:
            message = str(commit.get("message", ""))
            commit_hash = commit.get("id", "?")

            try:
                is_valid = _lint_commit_message_with_cli(message)
            except FileNotFoundError:
                errors.append("commitlint CLI not found. Install with: pip install commitlint")
                break

            if is_valid:
                continue
            
            errors.append(f"Commit {commit_hash}: commitlint has not passed. Message: {message}")

    return _dedupe(errors)


def _dedupe(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out