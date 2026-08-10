import io
import json
import urllib.error
from unittest.mock import patch

from app.github_activity import fetch_github_activity


class FakeResponse:
    def __init__(self, payload):
        self.body = io.BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.body.read()


def test_activity_splits_issues_and_pull_requests():
    payload = [
        {"number": 4, "title": "Fix setup", "body_text": "Document Node versions", "html_url": "https://github.com/a/b/issues/4", "user": {"login": "ada"}, "labels": [{"name": "docs"}], "updated_at": "2026-08-09T00:00:00Z", "comments": 2},
        {"number": 7, "title": "Add doctor command", "body_text": "Adds preflight checks", "html_url": "https://github.com/a/b/pull/7", "user": {"login": "grace"}, "labels": [], "updated_at": "2026-08-09T01:00:00Z", "comments": 1, "pull_request": {"url": "api"}, "draft": True},
    ]
    with patch("app.github_activity.urllib.request.urlopen", return_value=FakeResponse(payload)):
        result = fetch_github_activity("a", "b")
    assert result["status"] == "available"
    assert result["issues"][0]["title"] == "Fix setup"
    assert result["pull_requests"][0]["draft"] is True
    assert result["pull_requests"][0]["explanation"] == "Adds preflight checks"


def test_private_activity_failure_is_nonfatal():
    error = urllib.error.HTTPError("https://api.github.com", 404, "Not found", {}, None)
    with patch("app.github_activity.urllib.request.urlopen", side_effect=error):
        result = fetch_github_activity("private", "repo")
    assert result["status"] == "unavailable"
    assert result["issues"] == []
    assert "GITHUB_TOKEN" in result["reason"]
