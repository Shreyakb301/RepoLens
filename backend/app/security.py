from __future__ import annotations

import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse


MAX_FILE_BYTES = 750_000
MAX_REPO_BYTES = 35_000_000
MAX_FILES = 4_000

IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "node_modules", "vendor",
    "dist", "build", "coverage", ".next", ".nuxt", ".cache", ".venv", "venv",
    "env", ".asl-python", "site-packages", "target", "out", "__pycache__", ".pytest_cache", ".mypy_cache",
}
IGNORED_FILES = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock",
}
IGNORED_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".7z", ".rar", ".exe", ".dll", ".so", ".dylib", ".woff", ".woff2",
    ".ttf", ".eot", ".mp3", ".mp4", ".mov", ".avi", ".db", ".sqlite", ".pyc",
}
SECRET_NAME = re.compile(r"(^|[._-])(secret|credential|private[_-]?key|token|password)([._-]|$)", re.I)


class UnsafeRepository(ValueError):
    pass


def validate_github_url(raw_url: str) -> tuple[str, str, str]:
    """Accept only canonical public GitHub HTTPS URLs and return owner/repo/url."""
    value = raw_url.strip()
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise UnsafeRepository("Only public https://github.com/owner/repository URLs are accepted.")
    if parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment:
        raise UnsafeRepository("The repository URL cannot contain credentials, ports, query strings, or fragments.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise UnsafeRepository("Use the repository root URL: https://github.com/owner/repository")
    owner, repo = parts
    repo = repo.removesuffix(".git")
    allowed = re.compile(r"^[A-Za-z0-9_.-]+$")
    if not allowed.fullmatch(owner) or not allowed.fullmatch(repo):
        raise UnsafeRepository("The GitHub owner or repository name is invalid.")
    return owner, repo, f"https://github.com/{owner}/{repo}.git"


def github_resolves_publicly() -> None:
    """Defense in depth against unexpected DNS changes/SSRF."""
    for info in socket.getaddrinfo("github.com", 443, type=socket.SOCK_STREAM):
        address = ipaddress.ip_address(info[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise UnsafeRepository("GitHub resolved to a non-public network address.")


def should_index(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    if path.is_symlink() or not path.is_file():
        return False
    if any(part in IGNORED_DIRS for part in relative.parts[:-1]):
        return False
    lower_name = path.name.lower()
    if lower_name in IGNORED_FILES or SECRET_NAME.search(lower_name):
        return False
    if path.suffix.lower() in IGNORED_SUFFIXES or path.stat().st_size > MAX_FILE_BYTES:
        return False
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return False
    with path.open("rb") as handle:
        sample = handle.read(4096)
    if b"\x00" in sample:
        return False
    return True


def safe_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None
