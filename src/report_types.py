from typing import Literal, TypedDict

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
    issues: list[Issue]
    mrs: list[MR]
    coverage: list[CoverageScreenshot]


class Report(TypedDict):
    group: Group
    total_coverage: CoverageScreenshot
    tasks: list[Task]