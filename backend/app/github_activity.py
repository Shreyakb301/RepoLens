from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

import certifi


def unavailable(reason: str) -> dict:
    return {"status": "unavailable", "issues": [], "pull_requests": [], "reason": reason}


def fetch_github_activity(owner: str, repo: str, limit: int = 12) -> dict:
    """Fetch open issues and PRs without making repository analysis depend on GitHub."""
    safe_owner = urllib.parse.quote(owner, safe="")
    safe_repo = urllib.parse.quote(repo, safe="")
    endpoint = f"https://api.github.com/repos/{safe_owner}/{safe_repo}/issues?state=open&sort=updated&direction=desc&per_page={limit}"
    headers = {
        "Accept": "application/vnd.github.text+json",
        "User-Agent": "RepoLens/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(endpoint, headers=headers)
    tls_context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(request, timeout=8, context=tls_context) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return unavailable("GitHub activity is private or unavailable. Add a read-only GITHUB_TOKEN to inspect private repositories.")
        if exc.code in {401, 403}:
            return unavailable("GitHub denied the activity request. Check the token permissions or API rate limit.")
        return unavailable(f"GitHub activity request failed with status {exc.code}.")
    except (OSError, ValueError, urllib.error.URLError):
        return unavailable("GitHub activity could not be reached; repository code analysis is still available.")

    if not isinstance(payload, list):
        return unavailable("GitHub returned an unexpected activity response.")

    issues: list[dict] = []
    pull_requests: list[dict] = []
    for raw in payload[:limit]:
        if not isinstance(raw, dict):
            continue
        is_pull_request = "pull_request" in raw
        body = str(raw.get("body_text") or raw.get("body") or "").strip()
        html_url = str(raw.get("html_url") or "")
        item = {
            "number": int(raw.get("number") or 0),
            "kind": "pull_request" if is_pull_request else "issue",
            "title": str(raw.get("title") or "Untitled GitHub item")[:240],
            "explanation": body[:1200] or "The author did not provide a description.",
            "url": html_url if html_url.startswith("https://github.com/") else "",
            "author": str((raw.get("user") or {}).get("login") or "unknown"),
            "labels": [str(label.get("name"))[:60] for label in raw.get("labels", []) if isinstance(label, dict) and label.get("name")][:6],
            "updated_at": str(raw.get("updated_at") or ""),
            "comments": int(raw.get("comments") or 0),
            "draft": bool(raw.get("draft", False)) if is_pull_request else False,
        }
        (pull_requests if is_pull_request else issues).append(item)
    return {"status": "available", "issues": issues, "pull_requests": pull_requests, "reason": ""}
