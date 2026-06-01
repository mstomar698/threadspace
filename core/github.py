"""Lightweight GitHub enrichment for repos attached to devlog posts.

Uses the public GitHub REST API (stdlib only). A token (``GITHUB_API_TOKEN``)
is optional and only raises the rate limit. Network calls go through
``fetch_repo_metadata`` so they can be mocked in tests.
"""

import json
import re
import urllib.error
import urllib.request
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Repo

GITHUB_API = "https://api.github.com"
CACHE_TTL = timedelta(hours=1)

_SEGMENT = r"[A-Za-z0-9_.-]+"
_FULL_NAME_RE = re.compile(rf"^(?P<owner>{_SEGMENT})/(?P<name>{_SEGMENT})$")


class RepoNotFound(Exception):
    pass


class RepoFetchError(Exception):
    pass


def parse_repo_identifier(value: str) -> str:
    """Normalise a GitHub URL or ``owner/name`` string to ``owner/name``."""
    value = (value or "").strip()
    if not value:
        raise ValueError("Empty repository reference")

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise ValueError("Not a github.com URL")
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2:
            raise ValueError("URL does not point to a repository")
        owner, name = parts[0], parts[1]
        value = f"{owner}/{name}"

    if value.endswith(".git"):
        value = value[:-4]

    match = _FULL_NAME_RE.match(value)
    if not match:
        raise ValueError("Expected 'owner/name' or a GitHub repository URL")
    return f"{match.group('owner')}/{match.group('name')}"


def fetch_repo_metadata(full_name: str) -> dict:
    """Fetch repository metadata from the GitHub API. Mocked in tests."""
    request = urllib.request.Request(
        f"{GITHUB_API}/repos/{full_name}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ThreadSpace",
        },
    )
    token = getattr(settings, "GITHUB_API_TOKEN", "")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RepoNotFound(full_name) from exc
        raise RepoFetchError(f"GitHub returned {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RepoFetchError(str(exc)) from exc


def _apply_metadata(repo: Repo, data: dict) -> Repo:
    owner = data.get("owner") or {}
    repo.full_name = data["full_name"]
    repo.name = data.get("name", "")
    repo.owner_login = owner.get("login", "")
    repo.owner_avatar_url = owner.get("avatar_url", "") or ""
    repo.html_url = data.get("html_url", "")
    repo.description = data.get("description") or ""
    repo.homepage = data.get("homepage") or ""
    repo.language = data.get("language") or ""
    repo.topics = data.get("topics") or []
    repo.stargazers_count = data.get("stargazers_count", 0)
    repo.forks_count = data.get("forks_count", 0)
    repo.open_issues_count = data.get("open_issues_count", 0)
    pushed_at = data.get("pushed_at")
    repo.pushed_at = parse_datetime(pushed_at) if pushed_at else None
    repo.save()
    return repo


def get_or_refresh_repo(identifier: str) -> Repo:
    """Resolve ``identifier`` to a cached Repo, refreshing stale metadata."""
    full_name = parse_repo_identifier(identifier)
    existing = Repo.objects.filter(full_name__iexact=full_name).first()
    if existing and timezone.now() - existing.fetched_at < CACHE_TTL:
        return existing

    data = fetch_repo_metadata(full_name)
    return _apply_metadata(existing or Repo(), data)
