from __future__ import annotations

import shutil
import subprocess
import tempfile
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .security import MAX_FILES, MAX_REPO_BYTES, UnsafeRepository, github_resolves_publicly, should_index, validate_github_url


@contextmanager
def clone_public_repository(raw_url: str) -> Iterator[tuple[Path, str, str, str]]:
    owner, repo, clone_url = validate_github_url(raw_url)
    github_resolves_publicly()
    temp = Path(tempfile.mkdtemp(prefix="repolens-"))
    target = temp / "repository"
    try:
        command = [
            "git", "-c", "protocol.file.allow=never", "-c", "credential.helper=", "clone", "--depth", "12",
            "--single-branch", "--filter=blob:none", "--no-tags", clone_url, str(target),
        ]
        git_env = {
            "PATH": os.environ.get("PATH", ""),
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "never",
            "GIT_ASKPASS": "",
        }
        completed = subprocess.run(command, capture_output=True, text=True, timeout=90, env=git_env, stdin=subprocess.DEVNULL)
        if completed.returncode != 0:
            message = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "Git clone failed."
            if any(marker in message.lower() for marker in ("authentication", "username", "not found", "repository not found")):
                message = "Repository is private, unavailable, or does not exist. RepoLens currently accepts public repositories only."
            raise UnsafeRepository(message[:300])
        yield target, owner, repo, detect_branch(target)
    except subprocess.TimeoutExpired as exc:
        raise UnsafeRepository("Repository cloning exceeded the 90 second safety limit.") from exc
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def detect_branch(root: Path) -> str:
    result = subprocess.run(["git", "-C", str(root), "branch", "--show-current"], capture_output=True, text=True, timeout=5)
    return result.stdout.strip() or "main"


def open_local_repository(raw_path: str) -> tuple[Path, str, str, str, str]:
    """Validate a local Git checkout against configured filesystem roots."""
    requested = Path(raw_path).expanduser().resolve(strict=True)
    configured = os.getenv("REPOLENS_LOCAL_ROOTS", str(Path.home()))
    roots = [Path(item).expanduser().resolve(strict=True) for item in configured.split(os.pathsep) if item.strip()]
    if not requested.is_dir() or not any(requested == root or requested.is_relative_to(root) for root in roots):
        raise UnsafeRepository("That folder is outside the configured RepoLens local roots.")
    if not (requested / ".git").exists():
        raise UnsafeRepository("The selected local folder is not a Git repository.")
    branch = detect_branch(requested)
    remote_result = subprocess.run(
        ["git", "-C", str(requested), "config", "--get", "remote.origin.url"],
        capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL,
    )
    remote = remote_result.stdout.strip()
    owner = requested.parent.name
    repo = requested.name
    if remote:
        import re
        github_match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", remote)
        if github_match:
            owner, repo = github_match.group(1), github_match.group(2)
    return requested, owner, repo, remote or requested.as_uri(), branch


def find_local_checkout(raw_url: str) -> tuple[Path, str, str, str, str] | None:
    """Find a nearby checkout whose GitHub remote matches a failed clone URL."""
    owner, repo, expected_url = validate_github_url(raw_url)
    configured = os.getenv("REPOLENS_LOCAL_ROOTS", str(Path.home()))
    roots = [Path(item).expanduser().resolve(strict=True) for item in configured.split(os.pathsep) if item.strip()]
    candidates: list[Path] = []
    for root in roots:
        if root.name.lower() == repo.lower():
            candidates.append(root)
        candidates.extend(root.glob(repo))
        candidates.extend(root.glob(f"*/{repo}"))
        candidates.extend(root.glob(f"*/*/{repo}"))
    expected = expected_url.lower().removesuffix(".git")
    for candidate in dict.fromkeys(candidates):
        if not candidate.is_dir() or not (candidate / ".git").exists():
            continue
        result = subprocess.run(
            ["git", "-C", str(candidate), "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL,
        )
        remote = result.stdout.strip().lower().removesuffix(".git")
        normalized = remote.replace("git@github.com:", "https://github.com/")
        if normalized == expected:
            return open_local_repository(str(candidate))
    return None


def indexable_files(root: Path) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    warnings: list[str] = []
    total_bytes = 0
    for path in root.rglob("*"):
        if not should_index(root, path):
            continue
        size = path.stat().st_size
        if len(files) >= MAX_FILES:
            warnings.append(f"File limit reached ({MAX_FILES}); remaining files were skipped.")
            break
        if total_bytes + size > MAX_REPO_BYTES:
            warnings.append("Repository text limit reached (35 MB); remaining files were skipped.")
            break
        files.append(path)
        total_bytes += size
    return files, warnings
