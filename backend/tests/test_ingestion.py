from pathlib import Path

import pytest

from app import ingestion
from app.security import UnsafeRepository


def test_clone_disables_all_interactive_credentials(monkeypatch):
    observed = {}

    class FailedClone:
        returncode = 128
        stdout = ""
        stderr = "fatal: could not read Username for 'https://github.com': terminal prompts disabled"

    def fake_run(command, **kwargs):
        observed.update(kwargs)
        return FailedClone()

    monkeypatch.setattr(ingestion, "github_resolves_publicly", lambda: None)
    monkeypatch.setattr(ingestion.subprocess, "run", fake_run)
    with pytest.raises(UnsafeRepository, match="public repositories only"):
        with ingestion.clone_public_repository("https://github.com/example/private"):
            pass

    assert observed["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert observed["env"]["GCM_INTERACTIVE"] == "never"
    assert observed["stdin"] is ingestion.subprocess.DEVNULL


def test_local_repository_must_be_git_checkout_inside_allowed_root(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    repo = root / "private-project"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.setenv("REPOLENS_LOCAL_ROOTS", str(root))

    class GitResult:
        stdout = "main\n"

    monkeypatch.setattr(ingestion.subprocess, "run", lambda *args, **kwargs: GitResult())
    resolved, owner, name, url, branch = ingestion.open_local_repository(str(repo))
    assert resolved == repo
    assert name == "private-project"
    assert branch == "main"

    outside = tmp_path / "outside"
    (outside / ".git").mkdir(parents=True)
    with pytest.raises(UnsafeRepository, match="outside the configured"):
        ingestion.open_local_repository(str(outside))


def test_private_github_url_finds_matching_local_checkout(tmp_path, monkeypatch):
    repo = tmp_path / "Moodle"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.setenv("REPOLENS_LOCAL_ROOTS", str(tmp_path))

    class GitResult:
        def __init__(self, stdout):
            self.stdout = stdout

    def fake_run(command, **kwargs):
        if "remote.origin.url" in command:
            return GitResult("https://github.com/Sanjana-Gondariya/Moodle.git\n")
        return GitResult("main\n")

    monkeypatch.setattr(ingestion.subprocess, "run", fake_run)
    found = ingestion.find_local_checkout("https://github.com/Sanjana-Gondariya/Moodle")
    assert found is not None
    assert found[0] == repo
    assert found[1:3] == ("Sanjana-Gondariya", "Moodle")
