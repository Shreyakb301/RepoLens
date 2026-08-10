from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Citation:
    path: str
    start_line: int
    end_line: int


@dataclass(slots=True)
class CodeChunk:
    id: str
    path: str
    language: str
    kind: str
    name: str
    start_line: int
    end_line: int
    content: str
    imports: list[str] = field(default_factory=list)

    @property
    def citation(self) -> Citation:
        return Citation(self.path, self.start_line, self.end_line)


@dataclass(slots=True)
class FileFact:
    path: str
    language: str
    role: str
    lines: int
    score: float
    summary: str
    imports: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AnalysisRecord:
    id: str
    repo: dict[str, str]
    summary: str
    stats: dict[str, Any]
    stack: list[str]
    entry_points: list[dict[str, Any]]
    important_files: list[FileFact]
    reading_order: list[FileFact]
    routes: list[dict[str, Any]]
    architecture: dict[str, list[dict[str, str]]]
    warnings: list[str]
    elapsed_ms: int
    repo_health: dict[str, Any] = field(default_factory=lambda: {"score": 0, "label": "Unavailable", "summary": "Repository health was not evaluated.", "categories": [], "findings": []})
    github_activity: dict[str, Any] = field(default_factory=lambda: {"status": "unavailable", "issues": [], "pull_requests": [], "reason": "GitHub activity was not requested."})
    recent_work: dict[str, Any] = field(default_factory=lambda: {"status": "unavailable", "commits": [], "contributors": [], "reason": "Recent Git history was not requested."})
    chunks: list[CodeChunk] = field(default_factory=list, repr=False)

    def public_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("chunks", None)
        return value
