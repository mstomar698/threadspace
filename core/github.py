"""Lightweight GitHub enrichment for repos attached to devlog posts.

Uses the public GitHub REST API (stdlib only). A token (``GITHUB_API_TOKEN``)
is optional and only raises the rate limit. Network calls go through
``fetch_repo_metadata`` so they can be mocked in tests.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Repo

GITHUB_API = "https://api.github.com"
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
CACHE_TTL = timedelta(hours=1)

_SEGMENT = r"[A-Za-z0-9_.-]+"
_FULL_NAME_RE = re.compile(rf"^(?P<owner>{_SEGMENT})/(?P<name>{_SEGMENT})$")


class RepoNotFound(Exception):
    pass


class RepoFetchError(Exception):
    pass


class OAuthError(Exception):
    pass


class RateLimited(RepoFetchError):
    """Raised when GitHub returns a rate-limit response (primary or secondary).

    ``reset_epoch`` is the unix time the limit resets (from ``X-RateLimit-Reset``)
    when GitHub provides it, else ``None``.
    """

    def __init__(self, reset_epoch: int | None = None):
        super().__init__("GitHub rate limit exceeded")
        self.reset_epoch = reset_epoch


def _stub_enabled() -> bool:
    return bool(getattr(settings, "GITHUB_STUB", False))


def _stub_repo(full_name: str) -> dict:
    owner, _, name = full_name.partition("/")
    return {
        "full_name": full_name,
        "name": name or full_name,
        "owner": {"login": owner, "avatar_url": "https://avatars.example/u.png"},
        "html_url": f"https://github.com/{full_name}",
        "description": f"Stubbed metadata for {full_name}.",
        "homepage": "",
        "language": "Python",
        "topics": ["stub", "e2e"],
        "stargazers_count": 42,
        "forks_count": 7,
        "open_issues_count": 3,
        "pushed_at": "2026-01-01T00:00:00Z",
    }


STUB_LOGIN = "octocat"


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
    if _stub_enabled():
        return _stub_repo(full_name)
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


def _apply_metadata(repo: Repo, data: dict, source: str | None = None) -> Repo:
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
    if source is not None:
        repo.source = source
    repo.save()
    return repo


def search_repositories(query: str, page: int = 1, per_page: int = 100, token: str = "") -> dict:
    """Call GitHub's repository search API (sorted by stars, descending).

    Returns the parsed JSON (``{'total_count', 'items': [...]}``). Raises
    :class:`RateLimited` on a rate-limit response and :class:`RepoFetchError`
    otherwise. Mocked in tests / no-op under ``GITHUB_STUB``.
    """
    if _stub_enabled():
        return {"total_count": 0, "items": []}
    params = urllib.parse.urlencode(
        {"q": query, "sort": "stars", "order": "desc", "per_page": per_page, "page": page}
    )
    request = urllib.request.Request(
        f"{GITHUB_API}/search/repositories?{params}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ThreadSpace",
        },
    )
    token = token or getattr(settings, "GITHUB_API_TOKEN", "")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        # 403 with remaining=0 (or 429) means rate limited; surface the reset time.
        remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
        if exc.code == 429 or (exc.code == 403 and remaining == "0"):
            reset = exc.headers.get("X-RateLimit-Reset") if exc.headers else None
            raise RateLimited(int(reset) if reset else None) from exc
        raise RepoFetchError(f"GitHub search returned {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RepoFetchError(str(exc)) from exc


def get_or_refresh_repo(identifier: str) -> Repo:
    """Resolve ``identifier`` to a cached Repo, refreshing stale metadata."""
    full_name = parse_repo_identifier(identifier)
    existing = Repo.objects.filter(full_name__iexact=full_name).first()
    if existing and timezone.now() - existing.fetched_at < CACHE_TTL:
        return existing

    data = fetch_repo_metadata(full_name)
    return _apply_metadata(existing or Repo(), data)


# --- OAuth ("Connect GitHub") -------------------------------------------------


def build_authorize_url(state: str, redirect_uri: str, allow_signup: bool = False) -> str:
    """Build the GitHub OAuth authorize URL the user is redirected to.

    ``allow_signup`` controls whether GitHub offers a "create an account" option
    on its login screen — enabled for the sign-in flow, off for linking.
    """
    scopes = (getattr(settings, "GITHUB_OAUTH_SCOPES", "") or "").replace(",", " ").strip()
    params = {
        "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
        "allow_signup": "true" if allow_signup else "false",
    }
    return f"{GITHUB_OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_oauth_code(code: str, redirect_uri: str) -> dict:
    """Exchange an OAuth ``code`` for an access token. Mocked in tests."""
    if _stub_enabled():
        return {"access_token": "stub-access-token", "scope": "read:user,public_repo"}
    data = urllib.parse.urlencode(
        {
            "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
            "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode()
    request = urllib.request.Request(
        GITHUB_OAUTH_TOKEN_URL,
        data=data,
        headers={"Accept": "application/json", "User-Agent": "ThreadSpace"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        raise OAuthError(str(exc)) from exc

    if payload.get("error") or not payload.get("access_token"):
        raise OAuthError(payload.get("error_description") or "OAuth token exchange failed")
    return payload


def _authed_get(path: str, token: str) -> dict | list:
    request = urllib.request.Request(
        f"{GITHUB_API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ThreadSpace",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise OAuthError("GitHub authorization failed or expired.") from exc
        raise RepoFetchError(f"GitHub returned {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RepoFetchError(str(exc)) from exc


def fetch_authenticated_user(token: str) -> dict:
    """Fetch the GitHub profile for the token owner. Mocked in tests."""
    if _stub_enabled():
        return {
            "id": 100001,
            "login": STUB_LOGIN,
            "avatar_url": "https://avatars.example/octocat.png",
            "email": "octocat@example.com",
        }
    return _authed_get("/user", token)


def list_authenticated_repos(token: str) -> list:
    """List repos owned by the token owner (most recently pushed first)."""
    if _stub_enabled():
        return [
            _stub_repo(f"{STUB_LOGIN}/hello-world"),
            _stub_repo(f"{STUB_LOGIN}/threadspace"),
            _stub_repo(f"{STUB_LOGIN}/dotfiles"),
        ]
    return _authed_get("/user/repos?per_page=100&sort=pushed&affiliation=owner", token)


def import_user_repos(token: str) -> list[Repo]:
    """Cache/refresh every repo owned by the token's GitHub user."""
    repos = []
    for data in list_authenticated_repos(token):
        if not data.get("full_name"):
            continue
        existing = Repo.objects.filter(full_name__iexact=data["full_name"]).first()
        repos.append(_apply_metadata(existing or Repo(), data))
    return repos
