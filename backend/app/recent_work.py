from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import subprocess
import urllib.parse


def unavailable(reason: str) -> dict:
    return {"status": "unavailable", "commits": [], "contributors": [], "reason": reason}


def _areas(title: str, files: list[str]) -> list[str]:
    haystack = " ".join([title, *files]).lower()
    scores: Counter[str] = Counter()
    rules = {
        "ASL and gesture recognition": ("asl", "signlanguage", "sign_language", "gesture", "mediapipe"),
        "AI and model pipeline": ("model", "training", "inference", "benchmark", "dataset", "aiworker"),
        "frontend experience": ("src/", ".tsx", ".jsx", ".css", "component", "ui"),
        "server and APIs": ("server/", "backend/", "api", "socket", "route"),
        "tests and reliability": ("test", "spec", "fixture", "ci"),
        "documentation": ("readme", "docs/", ".md"),
        "configuration and tooling": ("package.json", ".env", "config", "script", ".github/"),
        "data and persistence": ("database", "redis", "store", "schema", "migration"),
    }
    for area, needles in rules.items():
        scores[area] = sum(haystack.count(needle) for needle in needles)
    selected = [area for area, score in scores.most_common(3) if score]
    return selected or ["general repository maintenance"]


def parse_git_log(output: str, owner: str, repo: str) -> dict:
    commits: list[dict] = []
    for record in output.split("\x1e"):
        record = record.strip(" \t\r\n")
        if not record:
            continue
        # splitlines() treats the unit separator (\x1f) as a line boundary;
        # Git uses it here to delimit metadata fields, so split on LF only.
        lines = record.split("\n")
        metadata = lines[0].split("\x1f", 3)
        if len(metadata) != 4:
            continue
        sha, author, date, title = (item.strip() for item in metadata)
        files = [line.strip() for line in lines[1:] if line.strip() and not line.startswith("/")]
        areas = _areas(title, files)
        examples = ", ".join(f"`{path}`" for path in files[:3])
        explanation = f"{author} appears to be working on {', '.join(areas)}."
        if examples:
            explanation += f" This commit changes {len(files)} file{'s' if len(files) != 1 else ''}, including {examples}."
        safe_owner = urllib.parse.quote(owner, safe="")
        safe_repo = urllib.parse.quote(repo, safe="")
        commits.append({
            "sha": sha,
            "short_sha": sha[:7],
            "title": title or "Untitled commit",
            "author": author or "Unknown contributor",
            "date": date,
            "areas": areas,
            "files": files[:8],
            "file_count": len(files),
            "explanation": explanation,
            "url": f"https://github.com/{safe_owner}/{safe_repo}/commit/{sha}" if len(sha) >= 7 else "",
        })

    if not commits:
        return unavailable("No recent commits were available in this checkout.")

    by_author: dict[str, list[dict]] = defaultdict(list)
    for commit in commits:
        by_author[commit["author"]].append(commit)
    contributors = []
    for author, authored in sorted(by_author.items(), key=lambda item: (-len(item[1]), item[0].lower())):
        area_counts = Counter(area for commit in authored for area in commit["areas"])
        contributors.append({
            "name": author,
            "commits": len(authored),
            "areas": [area for area, _ in area_counts.most_common(3)],
            "summary": f"{author} has {len(authored)} recent commit{'s' if len(authored) != 1 else ''} focused on {', '.join(area for area, _ in area_counts.most_common(3))}.",
        })
    return {"status": "available", "commits": commits, "contributors": contributors, "reason": ""}


def collect_recent_work(root: Path, owner: str, repo: str, limit: int = 8) -> dict:
    """Read recent commit metadata and changed paths without executing repository code."""
    try:
        result = subprocess.run(
            [
                "git", "-C", str(root), "log", "-n", str(max(1, min(limit, 20))),
                "--date=iso-strict", "--no-renames",
                "--pretty=format:%x1e%H%x1f%an%x1f%ad%x1f%s", "--name-only",
            ],
            capture_output=True, text=True, timeout=8, stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return unavailable("Recent Git history could not be read safely.")
    if result.returncode != 0:
        return unavailable("Recent Git history is unavailable for this checkout.")
    return parse_git_log(result.stdout, owner, repo)
