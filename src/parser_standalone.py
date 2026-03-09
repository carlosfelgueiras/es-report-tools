import argparse
import re
import json
from typing import Literal, TypedDict, cast


class Issue(TypedDict):
    id: int
    url: str


class MR(TypedDict):
    id: int
    url: str


class CoverageScreenshot(TypedDict):
    path: str


class Member(TypedDict):
    name: str
    ist_id: str
    gitlab: str
    issues: list[Issue]


class Committer(TypedDict):
    name: str
    ist_id: str
    gitlab: str


class Group(TypedDict):
    campus: Literal["AL", "TP"]
    number: int
    members: list[Member]


class Task(TypedDict):
    id: str
    title: str
    committer: Committer | None
    commits: list[Issue]
    reviews: list[MR]
    coverage: list[CoverageScreenshot]


class Report(TypedDict):
    group: Group
    total_coverage: CoverageScreenshot
    tasks: list[Task]


Section = Literal["members", "coverage", "tasks"] | None
TaskSection = Literal["committer", "commits", "reviews", "coverage"] | None


def build_arg_parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(
        description="Parse and Validate a markdown report."
    )
    cli.add_argument(
        "input_path",
        help="Path to markdown report file.",
    )
    cli.add_argument(
        "--to-json",
        action="store_true",
        help="Print parsed report as JSON to stdout.",
    )
    return cli


def extract_markdown_link(text: str) -> tuple[str | None, str | None]:
    """
    Extracts `[label](url)`
    Returns (label, url)
    """
    match = re.search(r"\[(.*?)\]\((.*?)\)", text)
    if match:
        return match.group(1), match.group(2)
    return None, None


def parse_member_line(line: str) -> Member:
    # - Name, istID, [GitLab link](URL)
    line = line.strip()[2:]  # remove "- "
    parts = line.split(",")
    name = parts[0].strip()
    ist_id = parts[1].strip()

    _, url = extract_markdown_link(line)
    if url is None:
        raise ValueError("Invalid member line: missing or invalid GitLab link.")

    return {
        "name": name,
        "ist_id": ist_id,
        "gitlab": url,
        "issues": []
    }


def parse_committer_line(line: str) -> Committer:
    # - Name, istID, [GitLab link](URL)
    line = line.strip()[2:]  # remove "- "
    parts = line.split(",")
    name = parts[0].strip()
    ist_id = parts[1].strip()

    _, url = extract_markdown_link(line)
    if url is None:
        raise ValueError("Invalid committer line: missing or invalid GitLab link.")

    return {
        "name": name,
        "ist_id": ist_id,
        "gitlab": url,
    }


def parse_issue_line(line: str) -> list[Issue]:
    # + Issues assigned: [#23](...), [#1](...)
    issues: list[Issue] = []
    matches = re.findall(r"\[#(\d+)\]\((.*?)\)", line)
    for issue_id, url in matches:
        issues.append({
            "id": int(issue_id),
            "url": url
        })
    return issues


def parse_task_header(line: str) -> tuple[str, str]:
    # ### T1.1 - Title
    match = re.match(r"^###\s+(T\d+\.\d+)\s*-\s*(\S.*\S|\S)$", line.strip())
    if not match:
        raise ValueError(
            "Invalid task header syntax. Expected format: "
            "'### T<number>.<number> - <title>'."
        )
    return match.group(1), match.group(2)


def parse_coverage_links(line: str) -> list[CoverageScreenshot]:
    # + [Coverage Screenshot](images/screenshot.png)
    matches = re.findall(r"\[[^\]]*]\((.*?)\)", line)
    return [{"path": path} for path in matches]


def parse_commit_links(line: str) -> list[Issue]:
    # + [#23](...)
    matches = re.findall(r"\[#(\d+)\]\((.*?)\)", line)
    return [{"id": int(issue_id), "url": url} for issue_id, url in matches]


def parse_review_links(line: str) -> list[MR]:
    # + [MR #12](...)
    matches = re.findall(r"\[MR\s+#(\d+)\]\((.*?)\)", line)
    return [{"id": int(mr_id), "url": url} for mr_id, url in matches]


def parse_group_from_title(line: str) -> Group:
    # # ES2026 P1 Submission, Group AL-12
    match = re.search(r"Group\s+(AL|TP)-(\d+)\b", line.strip())
    if not match:
        raise ValueError(
            "Invalid report title: expected 'Group AL-<group-number>' or "
            "'Group TP-<group-number>'."
        )
    campus = match.group(1)
    number = int(match.group(2))
    if number <= 0:
        raise ValueError("Invalid group number: must be a positive integer.")
    return {
        "campus": cast(Literal["AL", "TP"], campus),
        "number": number,
        "members": []
    }


def parse_markdown_report(markdown: str) -> Report:
    lines = markdown.splitlines()

    group: Group | None = None
    members: list[Member] = []
    total_coverage: CoverageScreenshot | None = None
    tasks: list[Task] = []

    current_section: Section = None
    current_member: Member | None = None
    current_task: Task | None = None
    current_task_section: TaskSection = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("# "):
            group = parse_group_from_title(stripped)
            group["members"] = members

        elif stripped == "## Members":
            current_section = "members"

        elif stripped == "## Total Coverage":
            current_section = "coverage"

        elif stripped == "## Tasks":
            current_section = "tasks"

        elif stripped.startswith("###"):
            task_id, title = parse_task_header(stripped)
            current_task = {
                "id": task_id,
                "title": title,
                "committer": None,
                "commits": [],
                "reviews": [],
                "coverage": []
            }
            tasks.append(current_task)

        elif current_section == "members":
            if stripped.startswith("- "):
                current_member = parse_member_line(stripped)
                members.append(current_member)

            elif stripped.startswith("+ Issues assigned"):
                issues = parse_issue_line(stripped)
                if current_member is not None:
                    current_member["issues"] = issues

        elif current_section == "coverage":
            if "](images/" in stripped:
                _, url = extract_markdown_link(stripped)
                if url is not None:
                    total_coverage = {"path": url}

        elif current_section == "tasks" and current_task:
            if stripped.startswith("- Committer"):
                current_task_section = "committer"

            elif stripped.startswith("- Commit"):
                current_task_section = "commits"

            elif stripped.startswith("- Review"):
                current_task_section = "reviews"

            elif stripped.startswith("- Coverage"):
                current_task_section = "coverage"

            elif stripped.startswith("+"):
                if current_task_section == "committer":
                    # + Name, istID, [GitLab link](...)
                    committer = parse_committer_line(stripped.replace("+ ", "- "))
                    current_task["committer"] = committer

                elif current_task_section in ["commits", "reviews", "coverage"]:
                    if current_task_section == "commits":
                        commit_links = parse_commit_links(stripped)
                        current_task["commits"].extend(commit_links)
                    elif current_task_section == "reviews":
                        review_links = parse_review_links(stripped)
                        current_task["reviews"].extend(review_links)
                    elif current_task_section == "coverage":
                        coverage_links = parse_coverage_links(stripped)
                        current_task["coverage"].extend(coverage_links)

    if group is None:
        raise ValueError(
            "Missing report title with group identifier. Expected a line like "
            "'# ... Group AL-<positive int>' or '# ... Group TP-<positive int>'."
        )
    if total_coverage is None:
        raise ValueError(
            "Missing total coverage screenshot. Expected a markdown link under "
            "'## Total Coverage'."
        )

    return {
        "group": group,
        "total_coverage": total_coverage,
        "tasks": tasks
    }


def main() -> None:
    cli = build_arg_parser()
    args = cli.parse_args()

    with open(args.input_path, "r", encoding="utf-8") as f:
        content = f.read()

    result = parse_markdown_report(content)

    if args.to_json:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
