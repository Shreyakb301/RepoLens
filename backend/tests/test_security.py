import pytest

from app.security import UnsafeRepository, validate_github_url


@pytest.mark.parametrize("url", [
    "http://github.com/owner/repo",
    "https://gitlab.com/owner/repo",
    "https://github.com/owner/repo/issues",
    "https://user:password@github.com/owner/repo",
])
def test_rejects_unsafe_or_noncanonical_urls(url: str):
    with pytest.raises(UnsafeRepository):
        validate_github_url(url)


def test_accepts_canonical_github_url():
    owner, repo, clone_url = validate_github_url("https://github.com/openai/openai-python")
    assert (owner, repo) == ("openai", "openai-python")
    assert clone_url.endswith(".git")

