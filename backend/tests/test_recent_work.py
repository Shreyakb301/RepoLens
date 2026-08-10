import subprocess
from pathlib import Path
from unittest.mock import patch

from app.recent_work import collect_recent_work, parse_git_log


def test_recent_work_explains_commit_and_groups_contributor():
    output = (
        "\x1eabc123456789\x1fAda\x1f2026-08-09T12:00:00Z\x1ffeat: add ASL gesture tests\n"
        "src/asl/gesture.ts\ntests/gesture.test.ts\n"
        "\x1edef987654321\x1fAda\x1f2026-08-08T12:00:00Z\x1fdocs: explain model training\n"
        "docs/TRAINING.md\n"
    )
    result = parse_git_log(output, "owner", "repo")
    assert result["status"] == "available"
    assert result["commits"][0]["short_sha"] == "abc1234"
    assert "ASL and gesture recognition" in result["commits"][0]["areas"]
    assert result["commits"][0]["file_count"] == 2
    assert result["contributors"][0]["commits"] == 2
    assert result["commits"][0]["url"].startswith("https://github.com/owner/repo/commit/")


def test_recent_work_git_failure_is_nonfatal():
    failed = subprocess.CompletedProcess([], 128, "", "not a repository")
    with patch("app.recent_work.subprocess.run", return_value=failed):
        result = collect_recent_work(Path("/safe/repo"), "owner", "repo")
    assert result["status"] == "unavailable"
    assert result["commits"] == []
